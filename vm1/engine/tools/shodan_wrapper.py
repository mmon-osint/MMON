"""
MMON — Shodan API wrapper
Infrastructure scan — IP, porte, servizi, vulnerabilità.

Usa la libreria Python ufficiale shodan (non CLI).
Docs: https://shodan.readthedocs.io/
"""

from typing import Any

import shodan as shodan_lib

from .base import (
    FindingCategory,
    FindingPayload,
    FindingSeverity,
    ToolWrapper,
)


class ShodanWrapper(ToolWrapper):
    """Wrapper per Shodan API — infrastructure scanning."""

    tool_name = "shodan"
    category = FindingCategory.INFRASTRUCTURE
    default_timeout = 120

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._api_key = self.config.get("shodan_key", "")
        self._client: shodan_lib.Shodan | None = None

    def _get_shodan(self) -> shodan_lib.Shodan:
        """Lazy init del client Shodan."""
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("Shodan API key non configurata in mmon.conf")
            self._client = shodan_lib.Shodan(self._api_key)
        return self._client

    async def run(self, target: str, **kwargs: Any) -> dict:
        """
        Esegue query Shodan su IP o dominio.

        Args:
            target: IP singolo, lista IP separata da virgola, o dominio
            scan_type: "host" (default), "search", "dns"
        """
        import asyncio

        scan_type = kwargs.get("scan_type", "host")
        api = self._get_shodan()

        results = {
            "target": target,
            "scan_type": scan_type,
            "hosts": [],
            "dns_records": [],
        }

        targets = [t.strip() for t in target.split(",") if t.strip()]

        if scan_type == "host":
            for t in targets:
                try:
                    host = await asyncio.to_thread(api.host, t)
                    results["hosts"].append(host)
                except shodan_lib.APIError as e:
                    results["hosts"].append({"ip_str": t, "error": str(e)})

        elif scan_type == "search":
            try:
                search_results = await asyncio.to_thread(
                    api.search, f"hostname:{target}"
                )
                results["hosts"] = search_results.get("matches", [])
            except shodan_lib.APIError as e:
                results["error"] = str(e)

        elif scan_type == "dns":
            try:
                dns = await asyncio.to_thread(api.dns.domain_info, target)
                results["dns_records"] = dns.get("data", [])
            except shodan_lib.APIError as e:
                results["error"] = str(e)

        return results

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Converte output Shodan in FindingPayload."""
        findings = []
        target = raw.get("target", "unknown")

        for host in raw.get("hosts", []):
            if host.get("error"):
                continue

            ip = host.get("ip_str", "")
            org = host.get("org", "")
            os_name = host.get("os", "")
            vulns = host.get("vulns", [])

            # Finding per ogni porta/servizio
            for service in host.get("data", []):
                port = service.get("port")
                product = service.get("product", "")
                version = service.get("version", "")
                transport = service.get("transport", "tcp")

                severity = self._service_severity(port, product, vulns)

                findings.append(FindingPayload(
                    source_tool=self.tool_name,
                    category=FindingCategory.INFRASTRUCTURE.value,
                    severity=severity,
                    target_ref=target,
                    raw_data={
                        "port": port,
                        "transport": transport,
                        "product": product,
                        "version": version,
                        "banner": (service.get("data", ""))[:500],
                    },
                    clean_data={
                        "ip": ip,
                        "port": port,
                        "service": product or self._guess_service(port),
                        "version": version,
                        "os": os_name,
                        "org": org,
                    },
                    tags=["shodan", "infrastructure", transport],
                ))

            # Finding per CVE associate
            for vuln_id in vulns:
                findings.append(FindingPayload(
                    source_tool=self.tool_name,
                    category=FindingCategory.CVE.value,
                    severity=FindingSeverity.HIGH.value,
                    target_ref=target,
                    raw_data={"cve_id": vuln_id, "ip": ip},
                    clean_data={
                        "cve_id": vuln_id,
                        "technology": f"{org} infrastructure",
                        "nvd_url": f"https://nvd.nist.gov/vuln/detail/{vuln_id}",
                    },
                    tags=["cve", "shodan", "infrastructure"],
                ))

        return findings

    def _service_severity(
        self, port: int | None, product: str, vulns: list
    ) -> str:
        """Calcola severità basata su porta, prodotto e CVE."""
        if vulns:
            return FindingSeverity.HIGH.value

        critical_products = ["telnet", "ftp", "smb", "rdp"]
        if product and any(p in product.lower() for p in critical_products):
            return FindingSeverity.HIGH.value

        high_risk_ports = {21, 23, 25, 110, 135, 139, 445, 1433, 3306, 3389, 5432, 5900}
        if port in high_risk_ports:
            return FindingSeverity.HIGH.value

        return FindingSeverity.MEDIUM.value

    def _guess_service(self, port: int | None) -> str:
        services = {
            21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
            80: "http", 443: "https", 445: "smb", 3306: "mysql",
            3389: "rdp", 5432: "postgresql", 8080: "http-proxy",
        }
        return services.get(port, "unknown") if port else "unknown"


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="MMON Shodan wrapper")
    parser.add_argument("--target", required=True, help="IP o dominio")
    parser.add_argument("--api-key", required=True, help="Shodan API key")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    wrapper = ShodanWrapper(api_base_url=args.api_url, config={"shodan_key": args.api_key})
    result = asyncio.run(wrapper.execute(args.target))
    print(f"Completato: {result.findings_count} findings")
