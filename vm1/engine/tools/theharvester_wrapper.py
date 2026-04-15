"""
MMON VM1 — theHarvester Wrapper
Multi-source OSINT: email gathering, subdomain discovery, host info.
Finding categories: social, infrastructure
"""
from __future__ import annotations

import json
import re
from typing import Any

from .base import FindingPayload, ToolWrapper


class TheHarvesterWrapper(ToolWrapper):
    """Wrapper per theHarvester — multi-source OSINT aggregator."""

    name = "theharvester"
    timeout = 600

    # Sorgenti da usare (evitare Google per rate limiting)
    DEFAULT_SOURCES = "baidu,bing,certspotter,crtsh,duckduckgo,hackertarget,rapiddns,sublist3r,urlscan,virustotal"

    async def run(self, target: str, **kwargs: Any) -> dict:
        """Esegui theHarvester su dominio target."""
        sources = kwargs.get("sources", self.DEFAULT_SOURCES)
        tmp_dir = self.create_temp_dir()
        output_file = tmp_dir / "results"

        cmd = [
            "theHarvester",
            "-d", target,
            "-b", sources,
            "-f", str(output_file),
            "-l", "500",  # limit risultati
        ]

        stdout, stderr, rc = await self.run_command(cmd)

        # theHarvester produce file JSON e XML
        results: dict = {"emails": [], "hosts": [], "ips": [], "target": target}

        json_file = tmp_dir / "results.json"
        if json_file.exists():
            try:
                with open(json_file) as f:
                    data = json.load(f)
                results["emails"] = data.get("emails", [])
                results["hosts"] = data.get("hosts", [])
                results["ips"] = data.get("ips", [])
                results["asns"] = data.get("asns", [])
                results["interesting_urls"] = data.get("interesting_urls", [])
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: parse stdout
        if not results["emails"] and not results["hosts"]:
            results = self._parse_stdout(stdout, target)

        return results

    def _parse_stdout(self, stdout: str, target: str) -> dict:
        """Fallback parser per stdout di theHarvester."""
        emails: list[str] = []
        hosts: list[str] = []
        ips: list[str] = []

        email_re = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
        ip_re = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

        current_section = ""
        for line in stdout.splitlines():
            line = line.strip()
            if "Emails found" in line:
                current_section = "emails"
            elif "Hosts found" in line:
                current_section = "hosts"
            elif "IPs found" in line:
                current_section = "ips"
            elif line.startswith("[*]") or line.startswith("---"):
                continue
            elif current_section == "emails" and email_re.search(line):
                emails.extend(email_re.findall(line))
            elif current_section == "hosts" and line:
                hosts.append(line.split(":")[0] if ":" in line else line)
            elif current_section == "ips":
                ips.extend(ip_re.findall(line))

        return {"emails": emails, "hosts": hosts, "ips": ips, "target": target}

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Parsa risultati theHarvester in findings."""
        findings: list[FindingPayload] = []
        target = raw.get("target", "")
        seen: set[str] = set()

        # Email → social category
        for email in raw.get("emails", []):
            email = email.strip().lower()
            if not email or email in seen:
                continue
            seen.add(email)

            findings.append(FindingPayload(
                source_tool=self.name,
                category="social",
                severity="info",
                target_ref=target,
                raw_data={"email": email},
                clean_data={
                    "type": "email",
                    "email": email,
                    "username": email.split("@")[0],
                    "domain": email.split("@")[-1],
                },
                tags=["email", "social", "theharvester"],
            ))

        # Host/subdomain → infrastructure
        for host in raw.get("hosts", []):
            host = host.strip().lower()
            if not host or host in seen:
                continue
            seen.add(host)

            # Separa host:ip se presente
            parts = host.split(":")
            hostname = parts[0]
            ip = parts[1] if len(parts) > 1 else ""

            findings.append(FindingPayload(
                source_tool=self.name,
                category="infrastructure",
                severity="info",
                target_ref=target,
                raw_data={"host": hostname, "ip": ip},
                clean_data={
                    "type": "subdomain",
                    "host": hostname,
                    "ip": ip,
                },
                tags=["subdomain", "theharvester"],
            ))

        # IP → infrastructure
        for ip in raw.get("ips", []):
            ip = ip.strip()
            if not ip or ip in seen:
                continue
            seen.add(ip)

            findings.append(FindingPayload(
                source_tool=self.name,
                category="infrastructure",
                severity="low",
                target_ref=target,
                raw_data={"ip": ip},
                clean_data={"type": "ip", "ip": ip},
                tags=["ip", "theharvester"],
            ))

        # Interesting URLs
        for url in raw.get("interesting_urls", []):
            if not url or url in seen:
                continue
            seen.add(url)

            findings.append(FindingPayload(
                source_tool=self.name,
                category="infrastructure",
                severity="medium",
                target_ref=target,
                raw_data={"url": url},
                clean_data={"type": "interesting_url", "url": url},
                tags=["url", "interesting", "theharvester"],
            ))

        return findings
