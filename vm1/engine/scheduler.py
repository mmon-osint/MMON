"""
MMON VM1 — Scheduler / Orchestrator.
Esegue scan plan basato su mmon.conf, gestisce concorrenza e loop.
"""
from __future__ import annotations

import argparse
import asyncio
import configparser
import os
import signal
import sys
import time
from typing import Any

import structlog

from .tools import TOOL_REGISTRY
from .tools.base import ToolResult, ToolWrapper

logger = structlog.get_logger(__name__)


class Scheduler:
    """Orchestratore scan VM1."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        self.backend_url = self._get_backend_url()
        self.max_concurrent = int(self.config.get("scheduler", "max_concurrent_tools", fallback="3"))
        self._shutdown = False

    def _load_config(self) -> configparser.ConfigParser:
        """Carica mmon.conf."""
        cp = configparser.ConfigParser()
        cp.read(self.config_path)
        return cp

    def _get_backend_url(self) -> str:
        """Costruisci URL backend da config."""
        ip = self.config.get("infrastructure", "backend_ip", fallback="127.0.0.1")
        return f"http://{ip}:8000"

    def build_scan_plan(self) -> list[dict[str, Any]]:
        """Costruisci piano di scan basato su target configurati."""
        plan: list[dict[str, Any]] = []

        domains = [d.strip() for d in self.config.get("target", "domains", fallback="").split(",") if d.strip()]
        public_ips = [ip.strip() for ip in self.config.get("target", "public_ips", fallback="").split(",") if ip.strip()]
        emails = [e.strip() for e in self.config.get("target", "emails", fallback="").split(",") if e.strip()]
        usernames = [u.strip() for u in self.config.get("social", "usernames", fallback="").split(",") if u.strip()]
        full_names = [n.strip() for n in self.config.get("social", "full_names", fallback="").split(",") if n.strip()]
        company = self.config.get("target", "company_name", fallback="")

        # bbot: per ogni dominio
        for domain in domains:
            plan.append({"tool": "bbot", "target": domain})

        # mosint: per ogni email
        for email in emails:
            plan.append({"tool": "mosint", "target": email, "kwargs": {"scan_type": "email"}})

        # mosint: per ogni username
        for username in usernames:
            plan.append({"tool": "mosint", "target": username, "kwargs": {"scan_type": "username"}})

        # shodan: per ogni IP pubblico
        shodan_key = self.config.get("api_keys", "shodan", fallback="")
        if shodan_key:
            for ip in public_ips:
                plan.append({"tool": "shodan", "target": ip, "kwargs": {"api_key": shodan_key}})
            for domain in domains:
                plan.append({"tool": "shodan", "target": domain, "kwargs": {"scan_type": "search", "api_key": shodan_key}})

        # theHarvester: per ogni dominio
        for domain in domains:
            plan.append({"tool": "theharvester", "target": domain})

        # trufflehog: se ci sono domini con possibili repo
        if company:
            plan.append({"tool": "trufflehog", "target": company, "kwargs": {"scan_type": "github_org"}})

        # dorks: per ogni dominio
        for domain in domains:
            plan.append({"tool": "dorks", "target": domain, "kwargs": {"names": full_names}})

        return plan

    async def run_plan(self, plan: list[dict[str, Any]]) -> list[ToolResult]:
        """Esegui piano con concorrenza limitata."""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        results: list[ToolResult] = []

        async def run_task(task: dict) -> ToolResult:
            async with semaphore:
                if self._shutdown:
                    return ToolResult(success=False, error="Shutdown richiesto")

                tool_name = task["tool"]
                target = task["target"]
                kwargs = task.get("kwargs", {})

                tool_cls = TOOL_REGISTRY.get(tool_name)
                if not tool_cls:
                    return ToolResult(success=False, error=f"Tool '{tool_name}' non registrato")

                # Kwargs speciali per tool che richiedono parametri extra
                init_kwargs: dict[str, Any] = {"backend_url": self.backend_url}
                if "api_key" in kwargs:
                    init_kwargs["api_key"] = kwargs.pop("api_key")

                wrapper = tool_cls(**init_kwargs)
                try:
                    return await wrapper.execute(target, **kwargs)
                finally:
                    await wrapper.close()

        tasks = [run_task(t) for t in plan]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Converti eccezioni in ToolResult
        final: list[ToolResult] = []
        for r in results:
            if isinstance(r, Exception):
                final.append(ToolResult(success=False, error=str(r)))
            else:
                final.append(r)

        return final

    async def run_single_tool(self, tool_name: str, target: str, **kwargs: Any) -> ToolResult:
        """Esegui un singolo tool."""
        plan = [{"tool": tool_name, "target": target, "kwargs": kwargs}]
        results = await self.run_plan(plan)
        return results[0] if results else ToolResult(success=False, error="No result")

    async def run_loop(self) -> None:
        """Loop continuo: scan → sleep → repeat."""
        interval_h = int(self.config.get("scheduler", "scan_interval_hours", fallback="24"))
        interval_s = interval_h * 3600

        logger.info("scheduler.loop_start", interval_hours=interval_h)

        while not self._shutdown:
            plan = self.build_scan_plan()
            logger.info("scheduler.cycle_start", tasks=len(plan))

            start = time.perf_counter()
            results = await self.run_plan(plan)
            duration = time.perf_counter() - start

            # Report
            success = sum(1 for r in results if r.success)
            total_findings = sum(r.findings_count for r in results)
            logger.info(
                "scheduler.cycle_complete",
                total=len(results), success=success, failed=len(results) - success,
                findings=total_findings, duration_min=round(duration / 60, 1),
            )

            # Sleep fino al prossimo ciclo
            logger.info("scheduler.sleeping", next_run_hours=interval_h)
            for _ in range(interval_s):
                if self._shutdown:
                    break
                await asyncio.sleep(1)

    def shutdown(self) -> None:
        """Segnala shutdown graceful."""
        logger.info("scheduler.shutdown_requested")
        self._shutdown = True


def _print_report(results: list[ToolResult], plan: list[dict]) -> None:
    """Stampa report formattato dei risultati."""
    print("\n" + "=" * 60)
    print("  MMON — Scan Report")
    print("=" * 60)

    for i, (task, result) in enumerate(zip(plan, results)):
        status = "✓" if result.success else "✗"
        tool = task["tool"]
        target = task["target"][:30]
        findings = result.findings_count
        duration = f"{result.duration_seconds:.1f}s"
        error = f" — {result.error[:40]}" if result.error else ""

        print(f"  {status} {tool:15} {target:30} {findings:3} findings  {duration:>8}{error}")

    total_ok = sum(1 for r in results if r.success)
    total_findings = sum(r.findings_count for r in results)
    print(f"\n  Total: {total_ok}/{len(results)} success, {total_findings} findings")
    print("=" * 60 + "\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="MMON VM1 Scheduler")
    parser.add_argument("--run-all", action="store_true", help="Singolo ciclo scan completo")
    parser.add_argument("--tool", type=str, help="Esegui solo un tool specifico")
    parser.add_argument("--target", type=str, help="Target per --tool")
    parser.add_argument("--loop", action="store_true", help="Loop continuo")
    args = parser.parse_args()

    config_path = os.environ.get("MMON_CONFIG", "/opt/mmon/config/mmon.conf")
    scheduler = Scheduler(config_path)

    # Signal handling
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, scheduler.shutdown)

    if args.tool:
        target = args.target or ""
        if not target:
            print("Errore: --target richiesto con --tool")
            sys.exit(1)
        result = await scheduler.run_single_tool(args.tool, target)
        print(f"{'✓' if result.success else '✗'} {args.tool}: {result.findings_count} findings ({result.duration_seconds:.1f}s)")
        if result.error:
            print(f"  Error: {result.error}")

    elif args.loop:
        await scheduler.run_loop()

    else:
        # Default: singolo ciclo
        plan = scheduler.build_scan_plan()
        if not plan:
            print("Nessun target configurato. Esegui il wizard prima.")
            sys.exit(1)

        logger.info("scheduler.single_run", tasks=len(plan))
        results = await scheduler.run_plan(plan)
        _print_report(results, plan)


if __name__ == "__main__":
    asyncio.run(main())
