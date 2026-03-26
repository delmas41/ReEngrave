"""
IMSLP search and download agent.
Uses the IMSLP MediaWiki API to find scores and download PDFs.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

IMSLP_API_BASE = "https://imslp.org/api.php"
IMSLP_BASE_URL = "https://imslp.org"

USER_AGENT = (
    "ReEngrave/0.1 (music score re-engraving tool; "
    "https://github.com/delmas41/ReEngrave) httpx/0.27"
)

# IMSLP requires accepting their ToS disclaimer before serving PDFs.
# Following the disclaimer accept URL sets a session cookie that unlocks downloads.
_DISCLAIMER_COOKIE = "imslpdisclaimeraccepted"
_DISCLAIMER_COOKIE_VALUE = "yes"


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

    Uses the MediaWiki API to find pages, fetches each work page to extract
    PDF download links and composer metadata.

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

    # Pre-seed the disclaimer cookie so PDF links are accessible
    cookies = {_DISCLAIMER_COOKIE: _DISCLAIMER_COOKIE_VALUE}

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=30.0,
        cookies=cookies,
    ) as client:
        for hit in search_hits[:max_results]:
            page_title: str = hit.get("title", "")
            page_url = f"{IMSLP_BASE_URL}/wiki/{quote(page_title.replace(' ', '_'))}"

            try:
                page_resp = await client.get(page_url)
                page_resp.raise_for_status()
                pdf_urls = _extract_pdf_links(page_resp.text, page_url, client)
                composer, description = _extract_page_metadata(page_resp.text)
            except httpx.HTTPError as exc:
                logger.warning("Failed to fetch IMSLP page %s: %s", page_url, exc)
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

    If the URL is an IMSLP disclaimer accept link, resolves it to the real
    PDF URL first. Returns the local file path.
    """
    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    # Resolve disclaimer links before downloading
    if "IMSLPDisclaimerAccept" in url or "imslp.org/wiki/Special:" in url:
        resolved = await _resolve_disclaimer_url(url)
        if resolved:
            url = resolved

    raw_name = url.split("/")[-1].split("?")[0] or "score.pdf"
    if not raw_name.lower().endswith(".pdf"):
        raw_name += ".pdf"
    local_path = os.path.join(dest_dir, raw_name)

    cookies = {_DISCLAIMER_COOKIE: _DISCLAIMER_COOKIE_VALUE}

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=120.0,
        cookies=cookies,
    ) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(local_path, "wb") as fh:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    fh.write(chunk)

    return local_path


def detect_era(composer: str, year: Optional[int]) -> str:
    """Heuristic era detection based on year or well-known composer names."""
    if year is not None:
        if year < 1750:
            return "baroque"
        elif year < 1820:
            return "classical"
        elif year < 1910:
            return "romantic"
        else:
            return "modern"

    baroque_composers = {
        "bach", "handel", "vivaldi", "telemann", "purcell", "monteverdi",
        "corelli", "scarlatti", "rameau", "couperin", "lully",
    }
    classical_composers = {
        "mozart", "haydn", "beethoven", "clementi", "salieri",
        "boccherini", "hummel", "dittersdorf",
    }
    romantic_composers = {
        "brahms", "chopin", "schumann", "liszt", "wagner", "verdi",
        "tchaikovsky", "dvorak", "schubert", "mendelssohn", "berlioz",
        "saint-saens", "franck", "grieg", "sibelius", "elgar", "mahler",
        "bruckner", "wolf", "strauss", "puccini",
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

    return "modern"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_pdf_links(
    html: str, base_url: str, client: httpx.AsyncClient | None = None
) -> list[str]:
    """Extract PDF download links from an IMSLP work page.

    Looks for:
    1. Direct .pdf hrefs
    2. Special:IMSLPDisclaimerAccept links (IMSLP's standard download gateway)
    3. Links in the file table rows (class="we_have_file")
    4. Links matching the IMSLP image server pattern
    """
    soup = BeautifulSoup(html, "lxml")
    pdf_links: list[str] = []
    seen: set[str] = set()

    def _add(href: str) -> None:
        full = urljoin(base_url, href)
        if full not in seen:
            seen.add(full)
            pdf_links.append(full)

    # Strategy 1: file table rows (most reliable for work pages)
    for row in soup.select("tr.we_have_file"):
        for a in row.find_all("a", href=True):
            href: str = a["href"]
            if "IMSLPDisclaimerAccept" in href or href.lower().endswith(".pdf"):
                _add(href)

    # Strategy 2: any IMSLPDisclaimerAccept link on the page
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "IMSLPDisclaimerAccept" in href:
            _add(href)

    # Strategy 3: direct .pdf hrefs
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            _add(href)

    # Strategy 4: IMSLP image server pattern
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"images/imslp\.org.*\.pdf", href, re.IGNORECASE):
            _add(href)

    return pdf_links[:5]


async def _resolve_disclaimer_url(disclaimer_url: str) -> Optional[str]:
    """Follow an IMSLP disclaimer accept URL to get the actual PDF URL.

    IMSLP's disclaimer URLs redirect (after setting an acceptance cookie)
    to the real file location. We follow the redirects and capture the
    final URL.
    """
    cookies = {_DISCLAIMER_COOKIE: _DISCLAIMER_COOKIE_VALUE}
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=30.0,
            cookies=cookies,
        ) as client:
            resp = await client.get(disclaimer_url)
            final_url = str(resp.url)

            # If the final URL looks like a PDF, return it directly
            if final_url.lower().endswith(".pdf"):
                return final_url

            content_type = resp.headers.get("content-type", "")
            if "pdf" in content_type:
                return final_url

            # Otherwise try to find a PDF link in the redirected page
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.lower().endswith(".pdf") or re.search(
                    r"images/imslp\.org.*\.pdf", href, re.IGNORECASE
                ):
                    return urljoin(final_url, href)
    except Exception as exc:
        logger.warning("Failed to resolve disclaimer URL %s: %s", disclaimer_url, exc)

    return None


def _extract_page_metadata(html: str) -> tuple[str, str]:
    """Extract composer name and description from IMSLP page HTML."""
    soup = BeautifulSoup(html, "lxml")

    composer = ""

    # IMSLP work pages have a structured infobox with a composer link
    # Pattern 1: infobox row labeled "Composer"
    for th in soup.find_all("th"):
        if th.get_text(strip=True).lower() == "composer":
            td = th.find_next_sibling("td")
            if td:
                composer = td.get_text(strip=True)
                break

    # Pattern 2: title tag — "Work Title (Composer Name)"
    if not composer:
        title_tag = soup.find("h1", class_="firstHeading")
        if title_tag:
            text = title_tag.get_text()
            match = re.search(r"\(([^)]+)\)$", text)
            if match:
                composer = match.group(1).strip()

    # Pattern 3: first Category link that looks like a person name
    if not composer:
        for a in soup.find_all("a", href=re.compile(r"/wiki/Category:")):
            text = a.get_text().strip()
            # Skip generic categories (era names, instruments, etc.)
            if text and not any(
                word in text.lower()
                for word in ("romantic", "baroque", "classical", "modern", "piano", "orchestra")
            ):
                composer = text
                break

    # Description: first substantive paragraph in the article body
    description = ""
    content_div = soup.find("div", class_="mw-parser-output")
    if content_div:
        for p in content_div.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 40:  # skip stub/empty paragraphs
                description = text[:300]
                break

    return composer, description
