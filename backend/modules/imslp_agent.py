"""
IMSLP search and download agent.
Uses the IMSLP MediaWiki API to find scores and download PDFs.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup

IMSLP_API_BASE = "https://imslp.org/api.php"
IMSLP_BASE_URL = "https://imslp.org"

USER_AGENT = (
    "ReEngrave/0.1 (music score re-engraving tool; "
    "https://github.com/your-org/reengrave) httpx/0.27"
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class IMSLPSearchResult:
    title: str
    composer: str
    era: str
    url: str
    pdf_urls: list[str] = field(default_factory=list)
    description: str = ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def search_imslp(
    query: str, max_results: int = 10
) -> list[IMSLPSearchResult]:
    """Search IMSLP for scores matching *query*.

    Uses the MediaWiki API (action=query, list=search) to find pages,
    then fetches each page to extract PDF download links.

    Returns up to *max_results* IMSLPSearchResult objects.
    """
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": max_results,
        "format": "json",
        "srnamespace": "0",
    }

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30.0
    ) as client:
        resp = await client.get(IMSLP_API_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    search_hits = data.get("query", {}).get("search", [])
    results: list[IMSLPSearchResult] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30.0
    ) as client:
        for hit in search_hits[:max_results]:
            page_title: str = hit.get("title", "")
            page_url = f"{IMSLP_BASE_URL}/wiki/{quote(page_title.replace(' ', '_'))}"

            # TODO: Parse IMSLP page HTML to extract:
            #   - Composer name from the work page infobox
            #   - PDF download links (IMSLP uses a special file serve URL)
            #   - Year / era information
            # IMSLP pages have a complex structure with JavaScript-rendered
            # file tables. Consider using the IMSLP Extras API endpoint for
            # richer metadata: https://imslp.org/wiki/IMSLP:API

            try:
                page_resp = await client.get(page_url)
                page_resp.raise_for_status()
                pdf_urls = _extract_pdf_links(page_resp.text, page_url)
                composer, description = _extract_page_metadata(page_resp.text)
            except httpx.HTTPError:
                pdf_urls = []
                composer = ""
                description = ""

            era = detect_era(composer, year=None)

            results.append(
                IMSLPSearchResult(
                    title=page_title,
                    composer=composer,
                    era=era,
                    url=page_url,
                    pdf_urls=pdf_urls,
                    description=description,
                )
            )

    return results


async def download_score(url: str, dest_dir: str) -> str:
    """Download a PDF from *url* into *dest_dir*.

    Sets a proper User-Agent header and follows redirects.
    Returns the local file path.
    """
    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    # Derive a filename from the URL
    raw_name = url.split("/")[-1].split("?")[0] or "score.pdf"
    if not raw_name.lower().endswith(".pdf"):
        raw_name += ".pdf"
    local_path = os.path.join(dest_dir, raw_name)

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=120.0,
    ) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(local_path, "wb") as fh:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    fh.write(chunk)

    return local_path


def detect_era(composer: str, year: Optional[int]) -> str:
    """Heuristic era detection based on year or well-known composer names.

    Thresholds: baroque < 1750, classical < 1820, romantic < 1910, modern >= 1910.
    """
    if year is not None:
        if year < 1750:
            return "baroque"
        elif year < 1820:
            return "classical"
        elif year < 1910:
            return "romantic"
        else:
            return "modern"

    # TODO: Expand this lookup with a more comprehensive composer database
    baroque_composers = {"bach", "handel", "vivaldi", "telemann", "purcell", "monteverdi"}
    classical_composers = {"mozart", "haydn", "beethoven", "clementi", "salieri"}
    romantic_composers = {
        "brahms", "chopin", "schumann", "liszt", "wagner", "verdi",
        "tchaikovsky", "dvorak", "schubert", "mendelssohn",
    }

    composer_lower = composer.lower()
    for name in baroque_composers:
        if name in composer_lower:
            return "baroque"
    for name in classical_composers:
        if name in composer_lower:
            return "classical"
    for name in romantic_composers:
        if name in composer_lower:
            return "romantic"

    return "modern"  # default


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_pdf_links(html: str, base_url: str) -> list[str]:
    """Extract PDF download links from an IMSLP work page.

    TODO: IMSLP serves PDFs through a special redirect mechanism.
    The actual download URLs are constructed server-side and may require
    cookie-based session handling. This stub returns direct href matches.
    """
    soup = BeautifulSoup(html, "lxml")
    pdf_links: list[str] = []

    for a_tag in soup.find_all("a", href=True):
        href: str = a_tag["href"]
        if href.lower().endswith(".pdf") or "Special:IMSLPDisclaimerAccept" in href:
            full_url = urljoin(base_url, href)
            pdf_links.append(full_url)

    # TODO: Parse the IMSLP file table which uses dynamic JS loading.
    # The canonical approach is to use the IMSLP Extras API or scrape
    # the #tablewrap element after JS execution (requires playwright/selenium).

    return pdf_links[:5]  # Limit to 5 PDFs per work


def _extract_page_metadata(html: str) -> tuple[str, str]:
    """Extract composer name and description from IMSLP page HTML.

    TODO: Parse the IMSLP infobox/work header for structured metadata.
    """
    soup = BeautifulSoup(html, "lxml")

    # Try to find composer in page title or infobox
    composer = ""
    title_tag = soup.find("h1", class_="firstHeading")
    if title_tag:
        text = title_tag.get_text()
        # IMSLP titles often follow pattern "Work Title (Composer Name)"
        match = re.search(r"\(([^)]+)\)$", text)
        if match:
            composer = match.group(1).strip()

    # Fallback: look for a composer link
    if not composer:
        comp_link = soup.find("a", href=re.compile(r"/wiki/Category:"))
        if comp_link:
            composer = comp_link.get_text().strip()

    # Description: first paragraph of page content
    description = ""
    content_div = soup.find("div", class_="mw-parser-output")
    if content_div:
        first_p = content_div.find("p")
        if first_p:
            description = first_p.get_text(strip=True)[:300]

    return composer, description
