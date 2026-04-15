"""
MMON VM1 — Base Tool Wrapper.
Classe astratta per tutti i tool wrapper. Pipeline:
run_with_retry → parse_output → submit_findings
"""
from __future__ import annotations

import asyncio
import json
import shlex
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class FindingPayload:
    """Payload singolo finding da inviare al backend."""

    source_vm: str = "vm1"
    source_tool: str = ""
    category: str = "infrastructure"
    severity: str = "info"
    target_ref: str = ""
    raw_data: dict = field(default_factory=dict)
    clean_data: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_api_dict(self) -> dict:
        """Serializza per POST /api/v1/findings."""
        return {
            "source_vm": self.source_vm,
            "source_tool": self.source_tool,
            "category": self.category,
            "severity": self.severity,
            "target_ref": self.target_ref,
            "raw_data": self.raw_data,
            "clean_data": self.clean_data,
            "tags": self.tags,
        }


@dataclass
class ToolResult:
    """Risultato esecuzione tool."""

    success: bool
    findings_count: int = 0
    duration_seconds: float = 0.0
    error: str | None = None


class ToolWrapper(ABC):
    """Classe base astratta per wrapper tool OSINT."""

    name: str = "base"
    max_retries: int = 3
    retry_delay: float = 5.0
    timeout: int = 600  # 10 minuti default

    def __init__(self, backend_url: str, vm_name: str = "vm1"):
        self.backend_url = backend_url.rstrip("/")
        self.vm_name = vm_name
        self._http = httpx.AsyncClient(timeout=30)

    @abstractmethod
    async def run(self, target: str, **kwargs: Any) -> dict:
        """Esegui il tool sul target. Ritorna output raw."""
        ...

    @abstractmethod
    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Parsa output raw in lista di FindingPayload."""
        ...

    async def execute(self, target: str, **kwargs: Any) -> ToolResult:
        """Pipeline completa: run → parse → submit."""
        start = time.perf_counter()
        log = logger.bind(tool=self.name, target=target)

        try:
            log.info("tool.start")
            raw = await self._run_with_retry(target, **kwargs)
            findings = self.parse_output(raw)
            log.info("tool.parsed", findings_count=len(findings))

            submitted = 0
            for finding in findings:
                ok = await self._submit_finding(finding)
                if ok:
                    submitted += 1

            duration = time.perf_counter() - start
            log.info("tool.complete", submitted=submitted, duration=round(duration, 2))

            return ToolResult(
                success=True,
                findings_count=submitted,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.perf_counter() - start
            log.error("tool.failed", error=str(e), duration=round(duration, 2))
            return ToolResult(success=False, error=str(e), duration_seconds=duration)

    async def _run_with_retry(self, target: str, **kwargs: Any) -> dict:
        """Esegui run() con retry esponenziale."""
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await self.run(target, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait = self.retry_delay * attempt
                    logger.warning("tool.retry", tool=self.name, attempt=attempt, wait=wait, error=str(e))
                    await asyncio.sleep(wait)
        raise last_error  # type: ignore[misc]

    async def _submit_finding(self, finding: FindingPayload) -> bool:
        """Invia finding al backend via POST /api/v1/findings."""
        try:
            resp = await self._http.post(
                f"{self.backend_url}/api/v1/findings",
                json=finding.to_api_dict(),
                headers={
                    "X-VM-Name": self.vm_name,
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 201:
                return True
            logger.warning("finding.submit_failed", status=resp.status_code, body=resp.text[:200])
            return False
        except Exception as e:
            logger.error("finding.submit_error", error=str(e))
            return False

    async def run_command(
        self,
        cmd: list[str],
        timeout: int | None = None,
        cwd: str | None = None,
    ) -> tuple[str, str, int]:
        """
        Esegui comando subprocess (SENZA shell=True per prevenire injection).
        Ritorna (stdout, stderr, returncode).
        """
        timeout = timeout or self.timeout
        logger.debug("tool.exec", cmd=shlex.join(cmd))

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"Comando timeout dopo {timeout}s: {shlex.join(cmd)}")

        return (
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
            proc.returncode or 0,
        )

    async def run_command_json(self, cmd: list[str], **kwargs: Any) -> dict | list:
        """run_command + JSON parse dell'output."""
        stdout, stderr, rc = await self.run_command(cmd, **kwargs)
        if rc != 0:
            raise RuntimeError(f"Comando fallito (rc={rc}): {stderr[:500]}")
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            raise ValueError(f"Output non JSON: {stdout[:500]}")

    def create_temp_dir(self) -> Path:
        """Crea directory temporanea per output tool."""
        return Path(tempfile.mkdtemp(prefix=f"mmon_{self.name}_"))

    async def close(self) -> None:
        """Chiudi client HTTP."""
        await self._http.aclose()
