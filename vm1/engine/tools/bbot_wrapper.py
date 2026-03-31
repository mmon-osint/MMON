"""
MMON — bbot wrapper
Subdomain enumeration e attack surface discovery.

bbot è il tool principale per scoprire subdomini, IP, servizi esposti
e la superficie d'attacco di un dominio target.

Uso standalone:
    python -m vm1.engine.tools.bbot_wrapper --target example.com

Docs: https://github.com/blacklanternsecurity/bbot
"""

import json
import shutil
from pathlib import Path
from typing import Any

from .base import (
    FindingCategory,
    FindingPayload,
    FindingSeverity,
    ToolWrapper,
)


class BbotWrapper(ToolWrapper):
    """Wrapper per bbot — subdomain enumeration e attack surface."""

    tool_name = "bbot"
    category = FindingCategory.INFRASTRUCTURE
    default_timeout = 600  # 10 minuti

    async def run(self, target: str, **kwargs: Any) -> dict:
        """
        Esegue bbot scan su un dominio target.

        Args:
            target: Dominio da scansionare (es. "example.com")
            scan_type: Tipo di scan ("subdomain", "full"). Default: "subdomain"

        Returns:
            dict con risultati parsati dal JSON output di bbot
        """
        scan_type = kwargs.get("scan_type", "subdomain")
        output_dir = self.create_temp_dir()

        # Costruire comando bbot
        cmd = [
            "bbot",
            "-t", target,
            "--output-dir", str(output_dir),
            "--output-format", "json",
            "--yes",  # non chiedere conferma
        ]

        # Moduli in base al tipo di scan
        if scan_type == "subdomain":
            cmd.extend(["-p", "subdomain-enum"])
        elif scan_type == "full":
            cmd.extend(["-p", "subdomain-enum", "web-basic"])

        returncode, stdout, stderr = await self.run_command(cmd)

        # Raccogliere risultati dal JSON output
        results = {
            "target": target,
            "scan_type": scan_type,
            "subdomains": [],
            "ips": [],
            "open_ports": [],
            "services": [],
            "raw_events": [],
        }

        # bbot scrive eventi JSON line-by-line in output/
        json_files = list(output_dir.rglob("*.json"))
        for jf in json_files:
            try:
                with open(jf, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                            results["raw_events"].append(event)
                            self._classify_event(event, results)
                        except json.JSONDecodeError:
                            continue
            except (OSError, IOError):
                continue

        # Fallback: parsare stdout se nessun file JSON trovato
        if not results["raw_events"] and stdout:
            for line in stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    results["raw_events"].append(event)
                    self._classify_event(event, results)
                except json.JSONDecodeError:
                    continue

        # Cleanup
        shutil.rmtree(output_dir, ignore_errors=True)

        return results

    def _classify_event(self, event: dict, results: dict) -> None:
        """Classifica un evento bbot nelle categorie di risultato."""
        event_type = event.get("type", "").upper()
        data = event.get("data", "")

        if event_type in ("DNS_NAME", "SUBDOMAIN"):
            if data and data not in results["subdomains"]:
                results["subdomains"].append(data)

        elif event_type == "IP_ADDRESS":
            if data and data not in results["ips"]:
                results["ips"].append(data)

        elif event_type == "OPEN_TCP_PORT":
            if data and data not in results["open_ports"]:
                results["open_ports"].append(data)

        elif event_type in ("HTTP_RESPONSE", "PROTOCOL"):
            results["services"].append({
                "host": event.get("host", data),
                "port": event.get("port"),
                "service": event.get("service", ""),
                "data": data,
            })

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Converte output bbot in FindingPayload."""
        findings = []
        target = raw.get("target", "unknown")

        # Subdomini trovati
        for subdomain in raw.get("subdomains", []):
            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=FindingCategory.INFRASTRUCTURE.value,
                severity=FindingSeverity.INFO.value,
                target_ref=subdomain,
                raw_data={"type": "subdomain", "parent_domain": target},
                clean_data={
                    "ip": subdomain,
                    "service": "subdomain",
                },
                tags=["subdomain", "dns"],
            ))

        # Porte aperte
        for port_entry in raw.get("open_ports", []):
            # port_entry è tipo "192.168.1.1:443"
            parts = str(port_entry).rsplit(":", 1)
            ip = parts[0] if len(parts) > 1 else port_entry
            port = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

            severity = self._port_severity(port)

            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=FindingCategory.INFRASTRUCTURE.value,
                severity=severity,
                target_ref=target,
                raw_data={"type": "open_port", "raw": port_entry},
                clean_data={
                    "ip": ip,
                    "port": port,
                    "service": self._guess_service(port),
                },
                tags=["open_port", "network"],
            ))

        # IP scoperti
        for ip in raw.get("ips", []):
            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=FindingCategory.INFRASTRUCTURE.value,
                severity=FindingSeverity.INFO.value,
                target_ref=target,
                raw_data={"type": "ip_address", "ip": ip},
                clean_data={"ip": ip},
                tags=["ip", "infrastructure"],
            ))

        return findings

    def _port_severity(self, port: int | None) -> str:
        """Stima severità in base alla porta aperta."""
        if port is None:
            return FindingSeverity.INFO.value
        high_risk = {21, 23, 25, 110, 135, 139, 445, 1433, 3306, 3389, 5432, 5900}
        medium_risk = {22, 80, 443, 8080, 8443}
        if port in high_risk:
            return FindingSeverity.HIGH.value
        if port in medium_risk:
            return FindingSeverity.MEDIUM.value
        return FindingSeverity.LOW.value

    def _guess_service(self, port: int | None) -> str:
        """Indovina il servizio dalla porta."""
        services = {
            21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
            53: "dns", 80: "http", 110: "pop3", 143: "imap",
            443: "https", 445: "smb", 1433: "mssql", 3306: "mysql",
            3389: "rdp", 5432: "postgresql", 5900: "vnc",
            8080: "http-proxy", 8443: "https-alt",
        }
        return services.get(port, "unknown") if port else "unknown"


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="MMON bbot wrapper")
    parser.add_argument("--target", required=True, help="Dominio target")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    wrapper = BbotWrapper(api_base_url=args.api_url)
    result = asyncio.run(wrapper.execute(args.target))
    print(f"Completato: {result.findings_count} findings in {result.duration_seconds:.1f}s")
    if result.error_message:
        print(f"Errore: {result.error_message}")
