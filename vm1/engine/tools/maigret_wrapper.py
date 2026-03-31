"""
MMON — maigret wrapper
Username/social account tracking su centinaia di piattaforme.

Docs: https://github.com/soxoj/maigret
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


class MaigretWrapper(ToolWrapper):
    """Wrapper per maigret — username e social tracking."""

    tool_name = "maigret"
    category = FindingCategory.SOCIAL
    default_timeout = 300

    async def run(self, target: str, **kwargs: Any) -> dict:
        """
        Esegue maigret su uno o più username.

        Args:
            target: Username singolo o lista separata da virgola
        """
        output_dir = self.create_temp_dir()
        output_file = output_dir / "maigret_results.json"

        usernames = [u.strip() for u in target.split(",") if u.strip()]

        results = {
            "target": target,
            "usernames": usernames,
            "accounts": [],
        }

        for username in usernames:
            cmd = [
                "maigret", username,
                "--json", "simple",
                "--output", str(output_dir / f"{username}"),
                "--no-color",
                "--timeout", "10",
            ]

            returncode, stdout, stderr = await self.run_command(cmd)

            # Leggere JSON output
            json_file = output_dir / f"{username}.json"
            if json_file.exists():
                try:
                    with open(json_file) as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            for site_name, site_data in data.items():
                                if isinstance(site_data, dict) and site_data.get("status", "") == "Claimed":
                                    results["accounts"].append({
                                        "username": username,
                                        "platform": site_name,
                                        "url": site_data.get("url_user", ""),
                                        "status": "found",
                                    })
                        elif isinstance(data, list):
                            for entry in data:
                                if entry.get("status") == "Claimed":
                                    results["accounts"].append({
                                        "username": username,
                                        "platform": entry.get("site_name", ""),
                                        "url": entry.get("url_user", ""),
                                        "status": "found",
                                    })
                except json.JSONDecodeError:
                    pass

            # Fallback: parsare stdout
            if not any(a["username"] == username for a in results["accounts"]):
                for line in stdout.splitlines():
                    line = line.strip()
                    if "[+]" in line or "Claimed" in line:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            results["accounts"].append({
                                "username": username,
                                "platform": parts[0].strip().replace("[+]", "").strip(),
                                "url": parts[-1].strip() if "http" in parts[-1] else "",
                                "status": "found",
                            })

        shutil.rmtree(output_dir, ignore_errors=True)
        return results

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Converte output maigret in FindingPayload."""
        findings = []

        for account in raw.get("accounts", []):
            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=FindingCategory.SOCIAL.value,
                severity=FindingSeverity.INFO.value,
                target_ref=account.get("username", raw.get("target", "")),
                raw_data=account,
                clean_data={
                    "platform": account.get("platform", ""),
                    "username": account.get("username", ""),
                    "profile_url": account.get("url", ""),
                    "status": account.get("status", "found"),
                },
                tags=["social", "username", account.get("platform", "").lower()],
            ))

        return findings


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="MMON maigret wrapper")
    parser.add_argument("--target", required=True, help="Username(s) target")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    wrapper = MaigretWrapper(api_base_url=args.api_url)
    result = asyncio.run(wrapper.execute(args.target))
    print(f"Completato: {result.findings_count} profili trovati")
