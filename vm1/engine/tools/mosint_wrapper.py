"""
MMON VM1 — mosint Wrapper
Email OSINT, breach detection, credential leak, username/social tracking.
Finding categories: social, leak
"""
from __future__ import annotations

import json
from typing import Any

from .base import FindingPayload, ToolWrapper


class MosintWrapper(ToolWrapper):
    """
    Wrapper per mosint v3 — copre:
    - Email OSINT + breach detection
    - Credential leak
    - Username / social tracking
    """

    name = "mosint"
    timeout = 300

    async def run(self, target: str, **kwargs: Any) -> dict:
        """Esegui mosint su email o username."""
        scan_type = kwargs.get("scan_type", "email")  # email | username

        if scan_type == "email":
            cmd = ["mosint", target, "--json"]
        else:
            # mosint v3 supporta lookup per username
            cmd = ["mosint", target, "--json"]

        stdout, stderr, rc = await self.run_command(cmd)

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            data = {"raw_stdout": stdout, "target": target}

        data["_target"] = target
        data["_scan_type"] = scan_type
        return data

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Parsa output mosint in findings social + leak."""
        findings: list[FindingPayload] = []
        target = raw.get("_target", "")

        # ── Breach / Leak findings ──
        breaches = raw.get("breaches", raw.get("data_breaches", []))
        if isinstance(breaches, list):
            for breach in breaches:
                name = breach if isinstance(breach, str) else breach.get("name", str(breach))
                has_password = False
                if isinstance(breach, dict):
                    has_password = breach.get("password", False) or breach.get("has_password", False)

                findings.append(FindingPayload(
                    source_tool=self.name,
                    category="leak",
                    severity="critical" if has_password else "high",
                    target_ref=target,
                    raw_data=breach if isinstance(breach, dict) else {"breach": name},
                    clean_data={
                        "breach_name": name,
                        "has_password": has_password,
                        "email": target,
                    },
                    tags=["breach", "leak"] + (["credential"] if has_password else []),
                ))

        # ── Social account findings ──
        socials = raw.get("social", raw.get("social_media", raw.get("accounts", [])))
        if isinstance(socials, list):
            for account in socials:
                if isinstance(account, dict):
                    platform = account.get("platform", account.get("site", "unknown"))
                    url = account.get("url", account.get("link", ""))
                    username = account.get("username", target)
                else:
                    platform = str(account)
                    url = ""
                    username = target

                findings.append(FindingPayload(
                    source_tool=self.name,
                    category="social",
                    severity="info",
                    target_ref=target,
                    raw_data=account if isinstance(account, dict) else {"platform": platform},
                    clean_data={
                        "platform": platform,
                        "username": username,
                        "profile_url": url,
                    },
                    tags=["social", "account"],
                ))

        # ── DNS / Domain info ──
        dns = raw.get("dns", raw.get("domain_info", {}))
        if isinstance(dns, dict) and dns:
            findings.append(FindingPayload(
                source_tool=self.name,
                category="infrastructure",
                severity="info",
                target_ref=target,
                raw_data=dns,
                clean_data={
                    "type": "email_domain_info",
                    "domain": target.split("@")[-1] if "@" in target else target,
                    "records": dns,
                },
                tags=["dns", "email_domain"],
            ))

        # ── Related emails ──
        related = raw.get("related_emails", raw.get("related", []))
        if isinstance(related, list):
            for email in related:
                email_str = email if isinstance(email, str) else email.get("email", str(email))
                findings.append(FindingPayload(
                    source_tool=self.name,
                    category="social",
                    severity="low",
                    target_ref=target,
                    raw_data={"related_email": email_str},
                    clean_data={"type": "related_email", "email": email_str},
                    tags=["email", "related"],
                ))

        return findings
