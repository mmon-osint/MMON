"""
MMON VM1 — bbot Wrapper
Subdomain enumeration, attack surface discovery.
Finding category: infrastructure
"""
from __future__ import annotations

import json
from typing import Any

from .base import FindingPayload, ToolWrapper


# Porte ad alto rischio
HIGH_RISK_PORTS = {21, 22, 23, 25, 110, 135, 139, 445, 1433, 1521, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 9200}


class BbotWrapper(ToolWrapper):
    """Wrapper per bbot — subdomain enum e attack surface."""

    name = "bbot"
    timeout = 900  # 15 minuti

    async def run(self, target: str, **kwargs: Any) -> dict:
        """Esegui bbot scan su dominio target."""
        tmp_dir = self.create_temp_dir()
        output_file = tmp_dir / "output.json"

        cmd = [
            "bbot",
            "-t", target,
            "-p", "subdomain-enum",
            "-o", str(tmp_dir),
            "--output-module", "json",
            "-y",  # auto-confirm
        ]

        stdout, stderr, rc = await self.run_command(cmd)

        # Leggi output JSON (bbot scrive un evento per riga)
        events = []
        for json_file in tmp_dir.rglob("*.json"):
            try:
                with open(json_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                events.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            except Exception:
                continue

        # Fallback su stdout
        if not events:
            for line in stdout.splitlines():
                line = line.strip()
                if line.startswith("{"):
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        return {"events": events, "target": target}

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Parsa eventi bbot in findings."""
        findings: list[FindingPayload] = []
        target = raw.get("target", "")
        seen: set[str] = set()

        for event in raw.get("events", []):
            event_type = event.get("type", "")
            event_data = event.get("data", "")

            if not event_data or str(event_data) in seen:
                continue
            seen.add(str(event_data))

            if event_type == "DNS_NAME":
                findings.append(FindingPayload(
                    source_tool=self.name,
                    category="infrastructure",
                    severity="info",
                    target_ref=target,
                    raw_data=event,
                    clean_data={"type": "subdomain", "host": str(event_data)},
                    tags=["subdomain", "dns"],
                ))

            elif event_type == "IP_ADDRESS":
                findings.append(FindingPayload(
                    source_tool=self.name,
                    category="infrastructure",
                    severity="low",
                    target_ref=target,
                    raw_data=event,
                    clean_data={"type": "ip", "ip": str(event_data)},
                    tags=["ip"],
                ))

            elif event_type == "OPEN_TCP_PORT":
                host_port = str(event_data)
                port = int(host_port.split(":")[-1]) if ":" in host_port else 0
                severity = "high" if port in HIGH_RISK_PORTS else "medium" if port < 1024 else "low"

                findings.append(FindingPayload(
                    source_tool=self.name,
                    category="infrastructure",
                    severity=severity,
                    target_ref=target,
                    raw_data=event,
                    clean_data={
                        "type": "open_port",
                        "host": host_port,
                        "port": port,
                        "service": _guess_service(port),
                    },
                    tags=["port", "exposure"],
                ))

        return findings


def _guess_service(port: int) -> str:
    """Mappa porta → servizio probabile."""
    services = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 135: "RPC", 139: "NetBIOS", 143: "IMAP",
        443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
        1433: "MSSQL", 1521: "Oracle", 3306: "MySQL", 3389: "RDP",
        5432: "PostgreSQL", 5900: "VNC", 6379: "Redis",
        8080: "HTTP-Alt", 8443: "HTTPS-Alt", 9200: "Elasticsearch",
    }
    return services.get(port, f"port-{port}")
