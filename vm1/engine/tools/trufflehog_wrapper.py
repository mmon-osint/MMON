"""
MMON — trufflehog wrapper
Secret/token leak detection su repository pubblici e org GitHub.

Docs: https://github.com/trufflesecurity/trufflehog
"""

import json
from typing import Any

from .base import (
    FindingCategory,
    FindingPayload,
    FindingSeverity,
    ToolWrapper,
)


class TrufflehogWrapper(ToolWrapper):
    """Wrapper per trufflehog — secret e token leak su repo pubblici."""

    tool_name = "trufflehog"
    category = FindingCategory.LEAK
    default_timeout = 600

    async def run(self, target: str, **kwargs: Any) -> dict:
        """
        Esegue trufflehog scan.

        Args:
            target: URL repo git, org GitHub, o dominio
            scan_type: "github_org", "git_repo", "s3". Default: "github_org"
        """
        scan_type = kwargs.get("scan_type", "github_org")

        cmd = ["trufflehog", "--json", "--no-update"]

        if scan_type == "github_org":
            cmd.extend(["github", "--org", target])
        elif scan_type == "git_repo":
            cmd.extend(["git", target])
        elif scan_type == "s3":
            cmd.extend(["s3", "--bucket", target])
        else:
            cmd.extend(["github", "--org", target])

        returncode, stdout, stderr = await self.run_command(cmd)

        results = {
            "target": target,
            "scan_type": scan_type,
            "secrets": [],
        }

        # trufflehog restituisce JSON line-by-line su stdout
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                secret = json.loads(line)
                results["secrets"].append(secret)
            except json.JSONDecodeError:
                continue

        return results

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Converte output trufflehog in FindingPayload."""
        findings = []
        target = raw.get("target", "unknown")

        for secret in raw.get("secrets", []):
            detector = secret.get("DetectorName", secret.get("detectorName", "unknown"))
            verified = secret.get("Verified", secret.get("verified", False))

            severity = FindingSeverity.CRITICAL.value if verified else FindingSeverity.HIGH.value

            # Estrarre info dal source metadata
            source_meta = secret.get("SourceMetadata", secret.get("sourceMetadata", {}))
            data = source_meta.get("Data", source_meta.get("data", {}))
            github_data = data.get("Github", data.get("github", {}))

            repo = github_data.get("repository", "")
            file_path = github_data.get("file", "")
            commit = github_data.get("commit", "")

            # Mascherare il secret effettivo (non salvare in chiaro)
            raw_secret = secret.get("Raw", secret.get("raw", ""))
            masked = raw_secret[:4] + "****" if len(raw_secret) > 4 else "****"

            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=FindingCategory.LEAK.value,
                severity=severity,
                target_ref=target,
                raw_data={
                    "detector": detector,
                    "verified": verified,
                    "repo": repo,
                    "file": file_path,
                    "commit": commit[:12],
                },
                clean_data={
                    "secret_type": detector,
                    "verified": verified,
                    "masked_value": masked,
                    "repository": repo,
                    "file_path": file_path,
                },
                tags=["secret", "leak", detector.lower(), "verified" if verified else "unverified"],
            ))

        return findings


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="MMON trufflehog wrapper")
    parser.add_argument("--target", required=True, help="GitHub org o repo URL")
    parser.add_argument("--scan-type", default="github_org", choices=["github_org", "git_repo", "s3"])
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    wrapper = TrufflehogWrapper(api_base_url=args.api_url)
    result = asyncio.run(wrapper.execute(args.target, scan_type=args.scan_type))
    print(f"Completato: {result.findings_count} secret trovati")
