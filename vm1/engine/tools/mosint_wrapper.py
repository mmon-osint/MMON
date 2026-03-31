"""
MMON — mosint wrapper
Email OSINT + breach check.

mosint è un tool Go che raccoglie informazioni su un indirizzo email:
breach check, social lookup, DNS verification, domain info.

Docs: https://github.com/alpkeskin/mosint
"""

import json
from typing import Any

from .base import (
    FindingCategory,
    FindingPayload,
    FindingSeverity,
    ToolWrapper,
)


class MosintWrapper(ToolWrapper):
    """Wrapper per mosint — Email OSINT e breach check."""

    tool_name = "mosint"
    category = FindingCategory.LEAK
    default_timeout = 120

    async def run(self, target: str, **kwargs: Any) -> dict:
        """
        Esegue mosint su un indirizzo email.

        Args:
            target: Indirizzo email da analizzare
        """
        cmd = ["mosint", target, "-o", "json"]

        returncode, stdout, stderr = await self.run_command(cmd)

        results = {
            "target": target,
            "breaches": [],
            "social": [],
            "dns_info": {},
            "raw_stdout": stdout,
        }

        # mosint restituisce JSON su stdout
        try:
            data = json.loads(stdout)
            results.update(data)
        except json.JSONDecodeError:
            # Fallback: parsare output testuale
            for line in stdout.splitlines():
                line = line.strip()
                if "breach" in line.lower() or "leak" in line.lower():
                    results["breaches"].append({"raw": line})
                elif "social" in line.lower() or "http" in line.lower():
                    results["social"].append({"raw": line})

        return results

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Converte output mosint in FindingPayload."""
        findings = []
        target = raw.get("target", "unknown")

        # Breach trovati
        for breach in raw.get("breaches", []):
            breach_name = breach.get("name", breach.get("raw", "unknown"))
            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=FindingCategory.LEAK.value,
                severity=FindingSeverity.HIGH.value,
                target_ref=target,
                raw_data=breach,
                clean_data={
                    "breach_name": breach_name,
                    "email": target,
                    "date": breach.get("date", ""),
                    "data_types": breach.get("data_types", []),
                },
                tags=["breach", "email", "leak"],
            ))

        # Account social trovati
        for social in raw.get("social", []):
            platform = social.get("platform", social.get("raw", ""))
            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=FindingCategory.SOCIAL.value,
                severity=FindingSeverity.INFO.value,
                target_ref=target,
                raw_data=social,
                clean_data={
                    "platform": platform,
                    "username": target.split("@")[0],
                    "profile_url": social.get("url", ""),
                    "status": "found",
                },
                tags=["social", "email"],
            ))

        # Se nessun breach trovato, creare finding info
        if not raw.get("breaches"):
            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=FindingCategory.LEAK.value,
                severity=FindingSeverity.INFO.value,
                target_ref=target,
                raw_data={"note": "nessun breach trovato"},
                clean_data={"email": target, "breach_name": "none"},
                tags=["email", "clean"],
            ))

        return findings


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="MMON mosint wrapper")
    parser.add_argument("--target", required=True, help="Email target")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    wrapper = MosintWrapper(api_base_url=args.api_url)
    result = asyncio.run(wrapper.execute(args.target))
    print(f"Completato: {result.findings_count} findings in {result.duration_seconds:.1f}s")
