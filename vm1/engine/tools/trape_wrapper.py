"""
MMON — trape wrapper
Tracking exposure — analizza come un target è tracciabile online.

Docs: https://github.com/jofpin/trape
"""

import json
from typing import Any

from .base import (
    FindingCategory,
    FindingPayload,
    FindingSeverity,
    ToolWrapper,
)


class TrapeWrapper(ToolWrapper):
    """Wrapper per trape — tracking exposure analysis."""

    tool_name = "trape"
    category = FindingCategory.SOCIAL
    default_timeout = 180

    async def run(self, target: str, **kwargs: Any) -> dict:
        """
        Esegue analisi trape su un target.

        Args:
            target: Dominio o URL da analizzare per tracking exposure
        """
        # trape è tipicamente un server web — usiamo la modalità CLI/scan
        cmd = [
            "python3", "-m", "trape",
            "--target", target,
            "--output", "json",
        ]

        returncode, stdout, stderr = await self.run_command(cmd)

        results = {
            "target": target,
            "trackers": [],
            "third_party_resources": [],
            "cookies": [],
            "headers": [],
        }

        try:
            data = json.loads(stdout)
            results.update(data)
        except json.JSONDecodeError:
            # Parsare output testuale
            for line in stdout.splitlines():
                line = line.strip()
                if "tracker" in line.lower():
                    results["trackers"].append({"raw": line})
                elif "cookie" in line.lower():
                    results["cookies"].append({"raw": line})
                elif "third" in line.lower() or "external" in line.lower():
                    results["third_party_resources"].append({"raw": line})

        return results

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Converte output trape in FindingPayload."""
        findings = []
        target = raw.get("target", "unknown")

        # Tracker trovati
        for tracker in raw.get("trackers", []):
            tracker_name = tracker.get("name", tracker.get("raw", "unknown"))
            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=FindingCategory.SOCIAL.value,
                severity=FindingSeverity.MEDIUM.value,
                target_ref=target,
                raw_data=tracker,
                clean_data={
                    "platform": tracker_name,
                    "username": target,
                    "status": "tracking_detected",
                },
                tags=["tracking", "privacy", "trape"],
            ))

        # Risorse third-party
        for resource in raw.get("third_party_resources", []):
            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=FindingCategory.INFRASTRUCTURE.value,
                severity=FindingSeverity.LOW.value,
                target_ref=target,
                raw_data=resource,
                clean_data={
                    "ip": resource.get("domain", ""),
                    "service": "third-party-resource",
                },
                tags=["third_party", "tracking"],
            ))

        return findings


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="MMON trape wrapper")
    parser.add_argument("--target", required=True, help="Dominio o URL target")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    wrapper = TrapeWrapper(api_base_url=args.api_url)
    result = asyncio.run(wrapper.execute(args.target))
    print(f"Completato: {result.findings_count} findings")
