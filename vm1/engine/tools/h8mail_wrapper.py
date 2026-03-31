"""
MMON — h8mail wrapper
Credential leak search — cerca password leakate associate a email.

Docs: https://github.com/khast3x/h8mail
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


class H8mailWrapper(ToolWrapper):
    """Wrapper per h8mail — credential leak search."""

    tool_name = "h8mail"
    category = FindingCategory.LEAK
    default_timeout = 180

    async def run(self, target: str, **kwargs: Any) -> dict:
        """
        Esegue h8mail su uno o più indirizzi email.

        Args:
            target: Email singola o lista separata da virgola
        """
        output_dir = self.create_temp_dir()
        output_file = output_dir / "h8mail_results.json"

        emails = [e.strip() for e in target.split(",") if e.strip()]

        cmd = [
            "h8mail",
            "-t", ",".join(emails),
            "--json", str(output_file),
        ]

        # Aggiungere API key se configurate
        config_file = self.config.get("h8mail_config")
        if config_file:
            cmd.extend(["--config", config_file])

        returncode, stdout, stderr = await self.run_command(cmd)

        results = {
            "target": target,
            "emails": emails,
            "leaks": [],
            "raw_stdout": stdout,
        }

        # Leggere output JSON
        if output_file.exists():
            try:
                with open(output_file) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        results["leaks"] = data
                    elif isinstance(data, dict):
                        results["leaks"] = data.get("targets", data.get("results", [data]))
            except json.JSONDecodeError:
                pass

        # Fallback: parsare stdout
        if not results["leaks"]:
            for line in stdout.splitlines():
                if "password" in line.lower() or "hash" in line.lower():
                    results["leaks"].append({"raw": line.strip()})

        shutil.rmtree(output_dir, ignore_errors=True)
        return results

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Converte output h8mail in FindingPayload."""
        findings = []
        target = raw.get("target", "unknown")

        for leak in raw.get("leaks", []):
            email = leak.get("target", leak.get("email", target))
            has_password = bool(leak.get("data", leak.get("password", "")))

            severity = FindingSeverity.CRITICAL.value if has_password else FindingSeverity.HIGH.value

            sources = leak.get("sources", [])
            if isinstance(sources, str):
                sources = [sources]

            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=FindingCategory.LEAK.value,
                severity=severity,
                target_ref=email,
                raw_data=leak,
                clean_data={
                    "email": email,
                    "has_password": has_password,
                    "sources": sources,
                    "breach_name": leak.get("source", "unknown"),
                },
                tags=["credential", "leak", "password" if has_password else "hash"],
            ))

        return findings


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="MMON h8mail wrapper")
    parser.add_argument("--target", required=True, help="Email(s) target")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    wrapper = H8mailWrapper(api_base_url=args.api_url)
    result = asyncio.run(wrapper.execute(args.target))
    print(f"Completato: {result.findings_count} findings")
