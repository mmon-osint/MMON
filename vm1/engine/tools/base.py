"""
MMON — Base class per tutti i tool wrapper VM1.
Ogni tool OSINT estende ToolWrapper e implementa run() e parse_output().

Uso:
    class BbotWrapper(ToolWrapper):
        tool_name = "bbot"
        category = FindingCategory.INFRASTRUCTURE

        async def run(self, target: str, **kwargs) -> dict:
            ...

        def parse_output(self, raw: dict) -> list[FindingPayload]:
            ...
"""

import abc
import asyncio
import json
import logging
import shlex
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import httpx
import structlog

logger = structlog.get_logger()


class FindingCategory(str, Enum):
    SOCIAL = "social"
    INFRASTRUCTURE = "infrastructure"
    CVE = "cve"
    KEYWORD = "keyword"
    LEAK = "leak"
    COMPETITOR = "competitor"
    DEEPWEB = "deepweb"
    TELEGRAM = "telegram"
    THREAT_ACTOR = "threat_actor"


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class FindingPayload:
    """Singolo finding pronto per l'invio al backend API."""
    source_tool: str
    category: str
    severity: str
    target_ref: str
    raw_data: dict = field(default_factory=dict)
    clean_data: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_api_dict(self, source_vm: str = "vm1") -> dict:
        """Converte in payload JSON per POST /api/v1/findings."""
        return {
            "source_vm": source_vm,
            "source_tool": self.source_tool,
            "category": self.category,
            "severity": self.severity,
            "target_ref": self.target_ref,
            "raw_data": self.raw_data,
            "clean_data": self.clean_data,
            "sanitized": False,
            "tags": self.tags,
        }


@dataclass
class ToolResult:
    """Risultato aggregato di un'esecuzione tool."""
    tool_name: str
    success: bool
    findings_count: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    raw_output: Optional[dict] = None


class ToolWrapper(abc.ABC):
    """
    Classe base astratta per wrapper tool OSINT.

    Ogni sottoclasse deve definire:
        - tool_name: str — nome univoco del tool
        - category: FindingCategory — categoria dei findings prodotti
        - run(target, **kwargs) -> dict — esecuzione del tool
        - parse_output(raw) -> list[FindingPayload] — parsing output

    La classe base gestisce:
        - Invio findings al backend API
        - Retry logic
        - Logging strutturato
        - Esecuzione comandi CLI in modo sicuro
        - Timeout e error handling
    """

    tool_name: str = "base"
    category: FindingCategory = FindingCategory.INFRASTRUCTURE
    default_timeout: int = 300  # 5 minuti default
    max_retries: int = 2
    retry_delay: float = 5.0

    def __init__(
        self,
        api_base_url: str = "http://127.0.0.1:8000",
        vm_name: str = "vm1",
        config: Optional[dict] = None,
    ):
        """
        Args:
            api_base_url: URL del backend FastAPI
            vm_name: Nome della VM (vm1, vm2, vm3)
            config: Dizionario di configurazione (da mmon.conf)
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.vm_name = vm_name
        self.config = config or {}
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy init del client HTTP."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=self.api_base_url,
                timeout=30.0,
                headers={
                    "X-VM-Name": self.vm_name,
                    "Content-Type": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        """Chiude il client HTTP."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    # =============================================================
    # METODI ASTRATTI
    # =============================================================

    @abc.abstractmethod
    async def run(self, target: str, **kwargs: Any) -> dict:
        """
        Esegue il tool su un target.

        Args:
            target: Stringa target (dominio, email, username, IP, ecc.)
            **kwargs: Parametri aggiuntivi specifici del tool

        Returns:
            Dizionario con output grezzo del tool
        """
        ...

    @abc.abstractmethod
    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """
        Parsa l'output grezzo del tool in lista di FindingPayload.

        Args:
            raw: Output grezzo da run()

        Returns:
            Lista di FindingPayload pronti per l'invio al backend
        """
        ...

    # =============================================================
    # ESECUZIONE COMPLETA
    # =============================================================

    async def execute(self, target: str, **kwargs: Any) -> ToolResult:
        """
        Pipeline completa: run → parse → submit findings.

        Args:
            target: Stringa target
            **kwargs: Parametri aggiuntivi

        Returns:
            ToolResult con risultato aggregato
        """
        start_time = time.monotonic()
        log = logger.bind(tool=self.tool_name, target=target)

        log.info("tool_start")

        try:
            # Run con retry
            raw_output = await self._run_with_retry(target, **kwargs)

            # Parse
            findings = self.parse_output(raw_output)
            log.info("tool_parsed", findings_count=len(findings))

            # Submit
            submitted = 0
            for finding in findings:
                success = await self._submit_finding(finding)
                if success:
                    submitted += 1

            duration = time.monotonic() - start_time
            log.info("tool_complete", submitted=submitted, duration=f"{duration:.1f}s")

            return ToolResult(
                tool_name=self.tool_name,
                success=True,
                findings_count=submitted,
                duration_seconds=duration,
                raw_output=raw_output,
            )

        except Exception as e:
            duration = time.monotonic() - start_time
            log.error("tool_failed", error=str(e), duration=f"{duration:.1f}s")

            return ToolResult(
                tool_name=self.tool_name,
                success=False,
                duration_seconds=duration,
                error_message=str(e),
            )

    # =============================================================
    # RETRY LOGIC
    # =============================================================

    async def _run_with_retry(self, target: str, **kwargs: Any) -> dict:
        """Esegue run() con retry in caso di errore."""
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return await self.run(target, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(
                    "tool_retry",
                    tool=self.tool_name,
                    attempt=attempt,
                    max=self.max_retries,
                    error=str(e),
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)

        raise RuntimeError(
            f"{self.tool_name}: fallito dopo {self.max_retries} tentativi. "
            f"Ultimo errore: {last_error}"
        )

    # =============================================================
    # SUBMIT FINDING
    # =============================================================

    async def _submit_finding(self, finding: FindingPayload) -> bool:
        """
        Invia un singolo finding al backend via POST /api/v1/findings.

        Returns:
            True se invio riuscito, False altrimenti
        """
        try:
            client = await self._get_client()
            payload = finding.to_api_dict(source_vm=self.vm_name)

            response = await client.post("/api/v1/findings", json=payload)

            if response.status_code == 201:
                return True
            else:
                logger.warning(
                    "finding_submit_failed",
                    tool=self.tool_name,
                    status=response.status_code,
                    body=response.text[:200],
                )
                return False

        except Exception as e:
            logger.error("finding_submit_error", tool=self.tool_name, error=str(e))
            return False

    # =============================================================
    # UTILITY: esecuzione comandi CLI sicura
    # =============================================================

    async def run_command(
        self,
        cmd: list[str],
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
    ) -> tuple[int, str, str]:
        """
        Esegue un comando CLI in modo sicuro (no shell=True).

        Args:
            cmd: Lista di argomenti (NON stringa, per prevenire injection)
            timeout: Timeout in secondi (default: self.default_timeout)
            cwd: Working directory
            env: Variabili d'ambiente aggiuntive

        Returns:
            Tupla (return_code, stdout, stderr)

        Raises:
            asyncio.TimeoutError se il comando eccede il timeout
        """
        if timeout is None:
            timeout = self.default_timeout

        # Sanitize: ogni elemento del cmd deve essere stringa
        cmd = [str(c) for c in cmd]

        logger.debug("run_command", cmd=cmd[:3], timeout=timeout)

        import os
        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=run_env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise asyncio.TimeoutError(
                f"Comando {cmd[0]} ha ecceduto il timeout di {timeout}s"
            )

        return (
            process.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    async def run_command_json(
        self,
        cmd: list[str],
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
    ) -> dict:
        """
        Esegue un comando e parsa stdout come JSON.

        Returns:
            Dizionario parsato da stdout

        Raises:
            RuntimeError se il comando fallisce o l'output non è JSON
        """
        returncode, stdout, stderr = await self.run_command(
            cmd, timeout=timeout, cwd=cwd
        )

        if returncode != 0:
            raise RuntimeError(
                f"{cmd[0]} exit code {returncode}: {stderr[:500]}"
            )

        try:
            return json.loads(stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"{cmd[0]} output non è JSON valido: {e}\n"
                f"stdout (primi 500 char): {stdout[:500]}"
            )

    def create_temp_dir(self) -> Path:
        """Crea directory temporanea per output tool."""
        tmp = Path(tempfile.mkdtemp(prefix=f"mmon_{self.tool_name}_"))
        return tmp
