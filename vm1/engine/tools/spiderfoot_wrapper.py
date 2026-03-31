"""
MMON — spiderfoot wrapper
Multi-source OSINT aggregation — correla dati da centinaia di fonti.

Docs: https://github.com/smicallef/spiderfoot
"""

import json
import shutil
from typing import Any

from .base import (
    FindingCategory,
    FindingPayload,
    FindingSeverity,
    ToolWrapper,
)


class SpiderfootWrapper(ToolWrapper):
    """Wrapper per spiderfoot — OSINT multi-source aggregation."""

    tool_name = "spiderfoot"
    category = FindingCategory.INFRASTRUCTURE
    default_timeout = 900  # 15 minuti — scan lunghi

    # Mappatura tipi evento spiderfoot → categoria finding
    EVENT_CATEGORY_MAP = {
        "EMAILADDR": FindingCategory.SOCIAL.value,
        "EMAILADDR_COMPROMISED": FindingCategory.LEAK.value,
        "SOCIAL_MEDIA": FindingCategory.SOCIAL.value,
        "USERNAME": FindingCategory.SOCIAL.value,
        "IP_ADDRESS": FindingCategory.INFRASTRUCTURE.value,
        "INTERNET_NAME": FindingCategory.INFRASTRUCTURE.value,
        "TCP_PORT_OPEN": FindingCategory.INFRASTRUCTURE.value,
        "VULNERABILITY_CVE_CRITICAL": FindingCategory.CVE.value,
        "VULNERABILITY_CVE_HIGH": FindingCategory.CVE.value,
        "VULNERABILITY_CVE_MEDIUM": FindingCategory.CVE.value,
        "VULNERABILITY_CVE_LOW": FindingCategory.CVE.value,
        "VULNERABILITY_GENERAL": FindingCategory.CVE.value,
        "COMPANY_NAME": FindingCategory.COMPETITOR.value,
        "DARKNET_MENTION_CONTENT": FindingCategory.LEAK.value,
        "LEAKSITE_CONTENT": FindingCategory.LEAK.value,
    }

    EVENT_SEVERITY_MAP = {
        "VULNERABILITY_CVE_CRITICAL": FindingSeverity.CRITICAL.value,
        "VULNERABILITY_CVE_HIGH": FindingSeverity.HIGH.value,
        "VULNERABILITY_CVE_MEDIUM": FindingSeverity.MEDIUM.value,
        "EMAILADDR_COMPROMISED": FindingSeverity.HIGH.value,
        "DARKNET_MENTION_CONTENT": FindingSeverity.HIGH.value,
        "LEAKSITE_CONTENT": FindingSeverity.CRITICAL.value,
        "TCP_PORT_OPEN": FindingSeverity.MEDIUM.value,
    }

    async def run(self, target: str, **kwargs: Any) -> dict:
        """
        Esegue spiderfoot CLI scan.

        Args:
            target: Dominio, IP, email o username
            modules: Lista moduli specifici (opzionale)
        """
        output_dir = self.create_temp_dir()
        output_file = output_dir / "sf_results.json"

        cmd = [
            "spiderfoot",
            "-s", target,
            "-o", "json",
            "-q",  # quiet mode
        ]

        modules = kwargs.get("modules")
        if modules:
            cmd.extend(["-m", ",".join(modules)])

        returncode, stdout, stderr = await self.run_command(cmd)

        results = {
            "target": target,
            "events": [],
        }

        # Parsare JSON output
        try:
            data = json.loads(stdout)
            if isinstance(data, list):
                results["events"] = data
            elif isinstance(data, dict):
                results["events"] = data.get("results", data.get("events", []))
        except json.JSONDecodeError:
            # Fallback: provare line-by-line
            for line in stdout.splitlines():
                try:
                    results["events"].append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

        shutil.rmtree(output_dir, ignore_errors=True)
        return results

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Converte eventi spiderfoot in FindingPayload."""
        findings = []
        target = raw.get("target", "unknown")

        seen = set()  # dedup

        for event in raw.get("events", []):
            event_type = event.get("type", event.get("event_type", ""))
            data = event.get("data", event.get("event_data", ""))
            module = event.get("module", event.get("source", "spiderfoot"))

            # Determinare categoria e severità
            category = self.EVENT_CATEGORY_MAP.get(
                event_type, FindingCategory.INFRASTRUCTURE.value
            )
            severity = self.EVENT_SEVERITY_MAP.get(
                event_type, FindingSeverity.INFO.value
            )

            # Dedup
            dedup_key = f"{event_type}:{data}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=category,
                severity=severity,
                target_ref=target,
                raw_data={
                    "event_type": event_type,
                    "data": str(data)[:1000],
                    "module": module,
                },
                clean_data=self._build_clean_data(event_type, data),
                tags=["spiderfoot", event_type.lower()],
            ))

        return findings

    def _build_clean_data(self, event_type: str, data: str) -> dict:
        """Costruisce clean_data strutturato in base al tipo di evento."""
        if event_type in ("IP_ADDRESS", "TCP_PORT_OPEN"):
            parts = str(data).rsplit(":", 1)
            return {
                "ip": parts[0],
                "port": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None,
            }
        elif event_type in ("EMAILADDR", "EMAILADDR_COMPROMISED"):
            return {"email": data}
        elif "VULNERABILITY" in event_type:
            return {
                "cve_id": data if data.startswith("CVE-") else "",
                "technology": "detected by spiderfoot",
                "description": str(data)[:500],
            }
        elif event_type in ("SOCIAL_MEDIA", "USERNAME"):
            return {"platform": "", "username": data, "profile_url": ""}
        elif event_type == "COMPANY_NAME":
            return {"name": data}
        else:
            return {"raw": str(data)[:500]}


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="MMON spiderfoot wrapper")
    parser.add_argument("--target", required=True, help="Target (dominio, IP, email)")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    wrapper = SpiderfootWrapper(api_base_url=args.api_url)
    result = asyncio.run(wrapper.execute(args.target))
    print(f"Completato: {result.findings_count} findings")
