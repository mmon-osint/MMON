"""
MMON VM1 — trufflehog Wrapper
Secret/token leak detection in Git repos, S3, GitHub orgs.
Finding category: keyword
"""
from __future__ import annotations

import json
from typing import Any

from .base import FindingPayload, ToolWrapper


class TrufflehogWrapper(ToolWrapper):
    """Wrapper per trufflehog v3 — secret detection."""

    name = "trufflehog"
    timeout = 600

    async def run(self, target: str, **kwargs: Any) -> dict:
        """Esegui trufflehog su target (git repo, github org, s3)."""
        scan_type = kwargs.get("scan_type", "git_repo")

        cmd = ["trufflehog", "--json", "--no-update"]

        if scan_type == "github_org":
            cmd += ["github", "--org", target]
        elif scan_type == "git_repo":
            cmd += ["git", target]
        elif scan_type == "s3":
            cmd += ["s3", "--bucket", target]
        else:
            cmd += ["git", target]

        stdout, stderr, rc = await self.run_command(cmd)

        # trufflehog produce un JSON per riga
        results = []
        for line in stdout.splitlines():
            line = line.strip()
            if line and line.startswith("{"):
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return {"results": results, "target": target, "scan_type": scan_type}

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Parsa risultati trufflehog in findings."""
        findings: list[FindingPayload] = []
        target = raw.get("target", "")

        for result in raw.get("results", []):
            detector = result.get("DetectorName", result.get("SourceMetadata", {}).get("DetectorName", "unknown"))
            verified = result.get("Verified", False)
            raw_secret = result.get("Raw", "")

            # MASCHERA secret — mai memorizzare in chiaro
            masked = _mask_secret(raw_secret)

            source_meta = result.get("SourceMetadata", {})
            file_path = source_meta.get("Data", {}).get("Filesystem", {}).get("file", "")
            commit = source_meta.get("Data", {}).get("Git", {}).get("commit", "")

            severity = "critical" if verified else "high"

            findings.append(FindingPayload(
                source_tool=self.name,
                category="keyword",
                severity=severity,
                target_ref=target,
                raw_data={
                    "detector": detector,
                    "verified": verified,
                    "file": file_path,
                    "commit": commit[:12] if commit else "",
                },
                clean_data={
                    "type": "secret_leak",
                    "detector": detector,
                    "verified": verified,
                    "masked_secret": masked,
                    "file_path": file_path,
                },
                tags=["secret", "leak", detector.lower()] + (["verified"] if verified else []),
            ))

        return findings


def _mask_secret(secret: str) -> str:
    """Maschera un secret: mostra solo primi 4 caratteri."""
    if not secret or len(secret) < 5:
        return "****"
    return secret[:4] + "****" + ("" if len(secret) < 12 else f" ({len(secret)} chars)")
