"""
MMON VM1 — Custom Dorks Scraper
Search engine dorks su DuckDuckGo (no Google per ban aggressivi).
Finding category: keyword
"""
from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from .base import FindingPayload, ToolWrapper

logger = structlog.get_logger(__name__)

# User agents per rotazione
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# Template dork per categoria
DORK_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "exposed_files": [
        {"query": 'site:{domain} filetype:sql', "severity": "high"},
        {"query": 'site:{domain} filetype:env', "severity": "critical"},
        {"query": 'site:{domain} filetype:log', "severity": "medium"},
        {"query": 'site:{domain} filetype:bak', "severity": "high"},
        {"query": 'site:{domain} filetype:conf', "severity": "medium"},
        {"query": 'site:{domain} filetype:xml inurl:config', "severity": "high"},
    ],
    "sensitive_pages": [
        {"query": 'site:{domain} intitle:"index of"', "severity": "medium"},
        {"query": 'site:{domain} inurl:admin', "severity": "medium"},
        {"query": 'site:{domain} inurl:login', "severity": "low"},
        {"query": 'site:{domain} inurl:phpinfo', "severity": "high"},
        {"query": 'site:{domain} inurl:.git', "severity": "critical"},
    ],
    "credentials_exposure": [
        {"query": 'site:{domain} intext:password filetype:txt', "severity": "critical"},
        {"query": 'site:{domain} intext:"api_key" OR intext:"apikey"', "severity": "high"},
        {"query": '"{domain}" intext:password site:pastebin.com', "severity": "critical"},
        {"query": '"{domain}" intext:password site:github.com', "severity": "critical"},
    ],
    "error_messages": [
        {"query": 'site:{domain} "SQL syntax" OR "mysql_fetch"', "severity": "high"},
        {"query": 'site:{domain} "Fatal error" OR "Stack trace"', "severity": "medium"},
        {"query": 'site:{domain} "not found" inurl:wp-content', "severity": "low"},
    ],
    "person_search": [
        {"query": '"{name}" site:linkedin.com', "severity": "info"},
        {"query": '"{name}" site:twitter.com OR site:x.com', "severity": "info"},
        {"query": '"{name}" "{domain}"', "severity": "info"},
    ],
}


class DorksWrapper(ToolWrapper):
    """Custom Google Dorks scraper via DuckDuckGo HTML."""

    name = "dorks"
    timeout = 900
    max_retries = 2

    async def run(self, target: str, **kwargs: Any) -> dict:
        """Esegui dork queries per il target."""
        categories = kwargs.get("categories", list(DORK_TEMPLATES.keys()))
        names = kwargs.get("names", [])  # Per person_search
        domain = target

        all_results: list[dict] = []

        for cat in categories:
            templates = DORK_TEMPLATES.get(cat, [])
            for tmpl in templates:
                query = tmpl["query"].format(domain=domain, name=names[0] if names else domain)

                # Delay randomizzato (3-8s) per evitare ban
                await asyncio.sleep(random.uniform(3.0, 8.0))

                results = await self._search_ddg(query)
                for r in results:
                    r["dork_category"] = cat
                    r["dork_severity"] = tmpl["severity"]
                    r["dork_query"] = query
                all_results.extend(results)

                logger.info("dork.query", category=cat, query=query[:50], results=len(results))

        return {"results": all_results, "target": target}

    async def _search_ddg(self, query: str) -> list[dict]:
        """Cerca su DuckDuckGo HTML e parsa risultati."""
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                resp = await client.post(url, data={"q": query}, headers=headers)

            if resp.status_code != 200:
                logger.warning("ddg.status", status=resp.status_code)
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            for r in soup.select(".result"):
                title_el = r.select_one(".result__title a")
                snippet_el = r.select_one(".result__snippet")

                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                results.append({
                    "title": title,
                    "url": href,
                    "snippet": snippet,
                })

            return results[:10]  # Max 10 risultati per query

        except Exception as e:
            logger.error("ddg.error", error=str(e))
            return []

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Parsa risultati dork in findings keyword."""
        findings: list[FindingPayload] = []
        target = raw.get("target", "")
        seen: set[str] = set()

        for result in raw.get("results", []):
            url = result.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)

            severity = result.get("dork_severity", "info")
            category_name = result.get("dork_category", "")

            findings.append(FindingPayload(
                source_tool=self.name,
                category="keyword",
                severity=severity,
                target_ref=target,
                raw_data=result,
                clean_data={
                    "type": "dork_result",
                    "keyword": result.get("dork_query", ""),
                    "matched_keyword": category_name,
                    "url": url,
                    "title": result.get("title", ""),
                    "context": result.get("snippet", ""),
                },
                tags=["dork", category_name, "search"],
            ))

        return findings
