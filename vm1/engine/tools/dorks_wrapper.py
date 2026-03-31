"""
MMON — Custom Google Dorks scraper
Cerca informazioni esposte sui motori di ricerca usando dork query.

NON usa API Google ufficiali (rate limit troppo stretto).
Usa requests con delay randomizzati e rotazione user-agent.
Supporta Google, Bing, DuckDuckGo.
"""

import asyncio
import random
import re
import time
from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from .base import (
    FindingCategory,
    FindingPayload,
    FindingSeverity,
    ToolWrapper,
)


# User agents realistici per rotazione
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class DorksWrapper(ToolWrapper):
    """Custom scraper per Google Dorks su motori di ricerca multipli."""

    tool_name = "dorks"
    category = FindingCategory.KEYWORD
    default_timeout = 600
    max_retries = 1  # Non retry su dorks — rischio ban

    # Template dork per tipo di informazione
    DORK_TEMPLATES = {
        "exposed_files": [
            'site:{domain} filetype:pdf',
            'site:{domain} filetype:xlsx OR filetype:csv',
            'site:{domain} filetype:doc OR filetype:docx',
            'site:{domain} filetype:sql OR filetype:bak',
            'site:{domain} filetype:env OR filetype:config',
            'site:{domain} filetype:log',
        ],
        "sensitive_pages": [
            'site:{domain} inurl:admin',
            'site:{domain} inurl:login',
            'site:{domain} inurl:dashboard',
            'site:{domain} inurl:api',
            'site:{domain} intitle:"index of"',
            'site:{domain} inurl:wp-admin OR inurl:wp-login',
        ],
        "credentials_exposure": [
            'site:{domain} intext:password filetype:txt',
            'site:{domain} intext:"api_key" OR intext:"api-key"',
            '"{domain}" intext:password site:pastebin.com OR site:github.com',
        ],
        "error_messages": [
            'site:{domain} intext:"sql syntax" OR intext:"mysql_fetch"',
            'site:{domain} intext:"Warning:" filetype:php',
            'site:{domain} intitle:"500 Internal Server Error"',
        ],
        "person_search": [
            '"{name}" site:linkedin.com',
            '"{name}" "{company}"',
            '"{name}" email OR contact',
        ],
    }

    async def run(self, target: str, **kwargs: Any) -> dict:
        """
        Esegue Google Dorks su un target.

        Args:
            target: Dominio da scansionare
            dork_types: Lista di categorie dork. Default: tutte.
            names: Lista di nomi da cercare (opzionale).
            max_results_per_dork: Max risultati per query. Default: 10.
        """
        dork_types = kwargs.get("dork_types", list(self.DORK_TEMPLATES.keys()))
        names = kwargs.get("names", [])
        max_per_dork = kwargs.get("max_results_per_dork", 10)
        company = kwargs.get("company", target)

        results = {
            "target": target,
            "dork_results": [],
            "total_queries": 0,
            "total_results": 0,
        }

        queries = self._build_queries(target, dork_types, names, company)
        results["total_queries"] = len(queries)

        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            verify=True,
        ) as client:
            for query_info in queries:
                query = query_info["query"]
                dork_type = query_info["type"]

                # Delay randomizzato anti-ban
                await asyncio.sleep(random.uniform(3.0, 8.0))

                search_results = await self._search_duckduckgo(
                    client, query, max_per_dork
                )

                for sr in search_results:
                    sr["dork_type"] = dork_type
                    sr["query"] = query
                    results["dork_results"].append(sr)

                results["total_results"] += len(search_results)

        return results

    def _build_queries(
        self,
        domain: str,
        dork_types: list[str],
        names: list[str],
        company: str,
    ) -> list[dict]:
        """Genera lista di query dai template."""
        queries = []

        for dtype in dork_types:
            templates = self.DORK_TEMPLATES.get(dtype, [])
            for template in templates:
                if "{name}" in template:
                    for name in names:
                        q = template.format(domain=domain, name=name, company=company)
                        queries.append({"query": q, "type": dtype})
                else:
                    q = template.format(domain=domain, company=company)
                    queries.append({"query": q, "type": dtype})

        return queries

    async def _search_duckduckgo(
        self,
        client: httpx.AsyncClient,
        query: str,
        max_results: int,
    ) -> list[dict]:
        """
        Esegue ricerca su DuckDuckGo HTML (meno aggressivo di Google).

        Returns:
            Lista di dict con title, url, snippet
        """
        results = []

        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return results

            soup = BeautifulSoup(response.text, "html.parser")

            # DuckDuckGo HTML results
            for result_div in soup.select(".result"):
                title_tag = result_div.select_one(".result__title a")
                snippet_tag = result_div.select_one(".result__snippet")

                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                href = title_tag.get("href", "")

                # DuckDuckGo wrappa i link — estrarre URL reale
                if "uddg=" in href:
                    from urllib.parse import parse_qs, urlparse
                    parsed = urlparse(href)
                    qs = parse_qs(parsed.query)
                    href = qs.get("uddg", [href])[0]

                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                results.append({
                    "title": title,
                    "url": href,
                    "snippet": snippet[:300],
                    "engine": "duckduckgo",
                })

                if len(results) >= max_results:
                    break

        except httpx.HTTPError:
            pass

        return results

    def parse_output(self, raw: dict) -> list[FindingPayload]:
        """Converte risultati dork in FindingPayload."""
        findings = []
        target = raw.get("target", "unknown")

        for result in raw.get("dork_results", []):
            dork_type = result.get("dork_type", "")

            # Severità in base al tipo di dork
            severity_map = {
                "credentials_exposure": FindingSeverity.CRITICAL.value,
                "exposed_files": FindingSeverity.HIGH.value,
                "sensitive_pages": FindingSeverity.MEDIUM.value,
                "error_messages": FindingSeverity.MEDIUM.value,
                "person_search": FindingSeverity.LOW.value,
            }
            severity = severity_map.get(dork_type, FindingSeverity.INFO.value)

            findings.append(FindingPayload(
                source_tool=self.tool_name,
                category=FindingCategory.KEYWORD.value,
                severity=severity,
                target_ref=target,
                raw_data=result,
                clean_data={
                    "query": result.get("query", ""),
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", ""),
                    "engine": result.get("engine", "duckduckgo"),
                },
                tags=["dork", dork_type, result.get("engine", "")],
            ))

        return findings


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MMON Google Dorks scraper")
    parser.add_argument("--target", required=True, help="Dominio target")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--names", nargs="*", default=[], help="Nomi da cercare")
    args = parser.parse_args()

    wrapper = DorksWrapper(api_base_url=args.api_url)
    result = asyncio.run(wrapper.execute(args.target, names=args.names))
    print(f"Completato: {result.findings_count} risultati da {len(args.names) or 'N/A'} nomi")
