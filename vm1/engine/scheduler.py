"""
MMON — VM1 Scheduler
Orchestratore che legge mmon.conf e lancia tool OSINT in sequenza/parallelo.

Modalità:
    - Scan completo schedulato (intervallo da mmon.conf)
    - Scan singolo tool (via job trigger dal backend)

Esecuzione:
    python -m engine.scheduler                    # loop continuo
    python -m engine.scheduler --run-all          # scan singolo e uscita
    python -m engine.scheduler --tool bbot        # singolo tool
"""

import argparse
import asyncio
import configparser
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog

from tools import TOOL_REGISTRY, ToolResult, ToolWrapper

logger = structlog.get_logger()


class Scheduler:
    """
    Orchestratore scan VM1.
    Legge configurazione, istanzia wrapper, esegue scan, gestisce risultati.
    """

    def __init__(self, config_path: str = "/opt/mmon/config/mmon.conf"):
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self.api_base_url = "http://127.0.0.1:8000"
        self.vm_name = "vm1"
        self.scan_interval_hours = 24
        self.max_concurrent = 3
        self._running = True
        self._load_config()

    def _load_config(self) -> None:
        """Carica configurazione da mmon.conf."""
        parser = configparser.ConfigParser()

        if Path(self.config_path).exists():
            parser.read(self.config_path)

            self.api_base_url = (
                f"http://{parser.get('infrastructure', 'backend_ip', fallback='127.0.0.1')}:8000"
            )
            self.scan_interval_hours = parser.getint(
                "scheduler", "scan_interval_hours", fallback=24
            )
            self.max_concurrent = parser.getint(
                "scheduler", "max_concurrent_tools", fallback=3
            )

            # Config per i tool
            self.config = {
                "shodan_key": parser.get("api_keys", "shodan_key", fallback=""),
                "domains": [
                    d.strip()
                    for d in parser.get("target", "domains", fallback="").split(",")
                    if d.strip()
                ],
                "public_ips": [
                    ip.strip()
                    for ip in parser.get("target", "public_ips", fallback="").split(",")
                    if ip.strip()
                ],
                "emails": [
                    e.strip()
                    for e in parser.get("target", "emails", fallback="").split(",")
                    if e.strip()
                ],
                "usernames": [
                    u.strip()
                    for u in parser.get("social", "usernames", fallback="").split(",")
                    if u.strip()
                ],
                "full_names": [
                    n.strip()
                    for n in parser.get("social", "full_names", fallback="").split(",")
                    if n.strip()
                ],
                "company_name": parser.get("target", "company_name", fallback=""),
                "industry": parser.get("sector", "industry", fallback=""),
            }
        else:
            logger.warning("config_not_found", path=self.config_path)

    def _create_wrapper(self, tool_name: str) -> ToolWrapper:
        """Istanzia un tool wrapper dal registry."""
        wrapper_class = TOOL_REGISTRY.get(tool_name)
        if wrapper_class is None:
            raise ValueError(f"Tool '{tool_name}' non trovato nel registry")

        return wrapper_class(
            api_base_url=self.api_base_url,
            vm_name=self.vm_name,
            config=self.config,
        )

    # =============================================================
    # SCAN PLAN
    # =============================================================

    def build_scan_plan(self) -> list[dict]:
        """
        Costruisce il piano di scan basato sulla configurazione.
        Ogni entry è un dict con tool_name, target e kwargs.
        """
        plan = []

        domains = self.config.get("domains", [])
        emails = self.config.get("emails", [])
        usernames = self.config.get("usernames", [])
        public_ips = self.config.get("public_ips", [])
        full_names = self.config.get("full_names", [])
        company = self.config.get("company_name", "")

        # bbot — scan per ogni dominio
        for domain in domains:
            plan.append({
                "tool": "bbot",
                "target": domain,
                "kwargs": {"scan_type": "subdomain"},
            })

        # mosint — scan per ogni email
        for email in emails:
            plan.append({
                "tool": "mosint",
                "target": email,
            })

        # h8mail — tutte le email insieme
        if emails:
            plan.append({
                "tool": "h8mail",
                "target": ",".join(emails),
            })

        # maigret — scan per ogni username
        if usernames:
            plan.append({
                "tool": "maigret",
                "target": ",".join(usernames),
            })

        # trufflehog — scan org GitHub se presente
        if company:
            plan.append({
                "tool": "trufflehog",
                "target": company.lower().replace(" ", ""),
                "kwargs": {"scan_type": "github_org"},
            })

        # shodan — scan per ogni IP
        if public_ips and self.config.get("shodan_key"):
            plan.append({
                "tool": "shodan",
                "target": ",".join(public_ips),
            })

        # spiderfoot — scan dominio principale
        if domains:
            plan.append({
                "tool": "spiderfoot",
                "target": domains[0],
            })

        # trape — tracking exposure per ogni dominio
        for domain in domains:
            plan.append({
                "tool": "trape",
                "target": domain,
            })

        # dorks — per ogni dominio con nomi
        for domain in domains:
            plan.append({
                "tool": "dorks",
                "target": domain,
                "kwargs": {
                    "names": full_names,
                    "company": company,
                },
            })

        logger.info("scan_plan_built", total_tasks=len(plan))
        return plan

    # =============================================================
    # ESECUZIONE
    # =============================================================

    async def run_single_tool(self, tool_name: str, target: str, **kwargs: Any) -> ToolResult:
        """Esegue un singolo tool."""
        wrapper = self._create_wrapper(tool_name)
        try:
            result = await wrapper.execute(target, **kwargs)
            return result
        finally:
            await wrapper.close()

    async def run_all(self) -> list[ToolResult]:
        """Esegue scan completo — tutti i tool secondo il piano."""
        plan = self.build_scan_plan()
        results: list[ToolResult] = []

        if not plan:
            logger.warning("scan_plan_empty")
            return results

        logger.info("scan_start", total_tasks=len(plan))
        start_time = time.monotonic()

        # Eseguire in batch con concurrency limitata
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def run_task(task: dict) -> ToolResult:
            async with semaphore:
                tool_name = task["tool"]
                target = task["target"]
                kwargs = task.get("kwargs", {})
                return await self.run_single_tool(tool_name, target, **kwargs)

        tasks = [run_task(t) for t in plan]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Filtrare eccezioni in ToolResult falliti
        clean_results = []
        for r in results:
            if isinstance(r, ToolResult):
                clean_results.append(r)
            elif isinstance(r, Exception):
                clean_results.append(ToolResult(
                    tool_name="unknown",
                    success=False,
                    error_message=str(r),
                ))

        duration = time.monotonic() - start_time
        total_findings = sum(r.findings_count for r in clean_results if r.success)
        failed = sum(1 for r in clean_results if not r.success)

        logger.info(
            "scan_complete",
            duration=f"{duration:.1f}s",
            total_findings=total_findings,
            tools_ok=len(clean_results) - failed,
            tools_failed=failed,
        )

        # Report
        self._print_report(clean_results, duration)

        return clean_results

    def _print_report(self, results: list[ToolResult], duration: float) -> None:
        """Stampa report finale dello scan."""
        print("\n" + "=" * 60)
        print("  MMON SCAN REPORT")
        print("=" * 60)
        print(f"  Duration: {duration:.1f}s")
        print(f"  Tools: {len(results)}")
        print("-" * 60)

        for r in results:
            status = "OK" if r.success else "FAIL"
            icon = "+" if r.success else "!"
            print(
                f"  [{icon}] {r.tool_name:<16} "
                f"{status:<6} "
                f"{r.findings_count:>4} findings  "
                f"{r.duration_seconds:.1f}s"
            )
            if r.error_message:
                print(f"      Error: {r.error_message[:80]}")

        total = sum(r.findings_count for r in results if r.success)
        print("-" * 60)
        print(f"  Total findings: {total}")
        print("=" * 60 + "\n")

    # =============================================================
    # LOOP CONTINUO
    # =============================================================

    async def run_loop(self) -> None:
        """Loop continuo: scan → sleep → scan → ..."""
        logger.info(
            "scheduler_start",
            interval_hours=self.scan_interval_hours,
        )

        # Gestione signal per shutdown graceful
        def handle_signal(sig, frame):
            logger.info("scheduler_shutdown_signal")
            self._running = False

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        while self._running:
            try:
                await self.run_all()
            except Exception as e:
                logger.error("scan_cycle_error", error=str(e))

            # Sleep con check periodico per shutdown
            sleep_seconds = self.scan_interval_hours * 3600
            logger.info("scheduler_sleep", next_scan_in=f"{self.scan_interval_hours}h")

            slept = 0
            while slept < sleep_seconds and self._running:
                await asyncio.sleep(min(60, sleep_seconds - slept))
                slept += 60

        logger.info("scheduler_stopped")


# =============================================================
# ENTRYPOINT
# =============================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="MMON VM1 Scheduler")
    parser.add_argument(
        "--config",
        default=os.environ.get("MMON_CONFIG", "/opt/mmon/config/mmon.conf"),
        help="Path a mmon.conf",
    )
    parser.add_argument("--run-all", action="store_true", help="Scan singolo e uscita")
    parser.add_argument("--tool", help="Esegui singolo tool")
    parser.add_argument("--target", help="Target per singolo tool")

    args = parser.parse_args()

    scheduler = Scheduler(config_path=args.config)

    if args.tool:
        target = args.target
        if not target:
            # Usa primo target disponibile dalla config
            domains = scheduler.config.get("domains", [])
            target = domains[0] if domains else "example.com"
        result = asyncio.run(scheduler.run_single_tool(args.tool, target))
        print(f"\n{args.tool}: {'OK' if result.success else 'FAIL'} — "
              f"{result.findings_count} findings in {result.duration_seconds:.1f}s")
        sys.exit(0 if result.success else 1)

    elif args.run_all:
        results = asyncio.run(scheduler.run_all())
        failed = any(not r.success for r in results)
        sys.exit(1 if failed else 0)

    else:
        asyncio.run(scheduler.run_loop())


if __name__ == "__main__":
    main()
