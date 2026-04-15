"""
MMON VM1 — Shodan Wrapper
Infrastructure scan + CVE feed via Shodan Python API.
Finding categories: infrastructure, cve
"""
from __future__ import annotations

import asyncio
from typing import Any

import structlog

from .base import FindingPayload, ToolWrapper

logger = structlog.get_logger(__name__)


class ShodanWrapper(ToolWrapper):
    """Wrapper per Shodan API — host lookup, search, CVE."""

    name = "shodan"
    timeout = 120

    def __init__(self, backend_url: str, api_key: str = "", **kwargs: Any):
        super().__init__(backend_url, **kwargs)
        self.api_key = api_key

    async def run(self, target: str, **kwargs: Any) -> dict:
        """Esegui query Shodan. scan_type: host | search | dns."""
        if not self.api_key:
            raise ValueError("Shodan API key non configurata")

        import shodan
        api = shodan.Shodan(self.api_key)
        scan_type = kwargs.get("scan_type", "host")

        if scan_type == "host":
            result = await asyncio.to_thread(api.host, target)
        elif scan_type == "search":
            result = await asyncio.to_thread(api.search, target)
        elif scan_type == "dns":
            result = await asyncio.to_thread(api.dns.resolve, target)
        else:
            result = await asyncio.to_thread(api.host, target)

        return {"result": result, "target": target, "scan_type": scan_type}

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Parsa risultati Shodan in findings infra + CVE."""
        findings: list[FindingPayload] = []
        target = raw.get("target", "")
        result = raw.get("result", {})
        scan_type = raw.get("scan_type", "host")

        if scan_type == "host":
            findings.extend(self._parse_host(result, target))
        elif scan_type == "search":
            for match in result.get("matches", []):
                findings.extend(self._parse_host(match, target))

        return findings

    def _parse_host(self, host: dict, target: str) -> list[FindingPayload]:
        """Parsa un singolo host Shodan."""
        findings: list[FindingPayload] = []
        ip = host.get("ip_str", target)

        # Servizi per porta
        for service in host.get("data", [host] if "port" in host else []):
            port = service.get("port", 0)
            product = service.get("product", "")
            version = service.get("version", "")
            banner = service.get("data", "")[:200]

            severity = "info"
            if port in {21, 23, 25, 445, 3389, 5900}:
                severity = "high"
            elif port in {22, 80, 443, 8080, 8443}:
                severity = "medium"

            findings.append(FindingPayload(
                source_tool=self.name,
                category="infrastructure",
                severity=severity,
                target_ref=target,
                raw_data={"port": port, "product": product, "version": version},
                clean_data={
                    "type": "service",
                    "ip": ip,
                    "port": port,
                    "service": product,
                    "version": version,
                    "banner": banner,
                },
                tags=["shodan", "service", f"port-{port}"],
            ))

        # CVE / vulnerabilità
        vulns = host.get("vulns", [])
        for cve_id in vulns:
            # Shodan fornisce ID CVE, severità da CVSS
            cvss = None
            cve_data = host.get("vulns_info", {}).get(cve_id, {})
            if isinstance(cve_data, dict):
                cvss = cve_data.get("cvss")

            severity = "info"
            if cvss is not None:
                if cvss >= 9.0:
                    severity = "critical"
                elif cvss >= 7.0:
                    severity = "high"
                elif cvss >= 4.0:
                    severity = "medium"
                else:
                    severity = "low"

            findings.append(FindingPayload(
                source_tool=self.name,
                category="cve",
                severity=severity,
                target_ref=target,
                raw_data={"cve_id": cve_id, "cvss": cvss, "ip": ip},
                clean_data={
                    "cve_id": cve_id,
                    "cvss_score": cvss,
                    "ip": ip,
                    "product": host.get("product", ""),
                },
                tags=["cve", "shodan", cve_id],
            ))

        return findings
