#!/usr/bin/env python3
"""Scrape IMSLP work pages and update per-PDF metadata.yaml files.

For each Beethoven symphony PDF in tools/omr/training/data/imslp/beethoven-symphony-{N}/pdfs/imslp-{ID}/,
look up the file's IMSLP ID on the corresponding work page, extract publisher/year/plate/city/country,
and rewrite metadata.yaml. The raw publisher-info string is preserved verbatim under `raw_pub_info`
for cases where auto-parsing falls short.

Run from anywhere:
    python3 benchmarks/omr-imslp-pipeline/scrape_imslp_metadata.py
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

TARGET_ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp")
CACHE_DIR = Path("/tmp/imslp-scrape")
CACHE_DIR.mkdir(exist_ok=True)

BEETHOVEN_PAGES = {
    1: "Symphony_No.1,_Op.21_(Beethoven,_Ludwig_van)",
    2: "Symphony_No.2,_Op.36_(Beethoven,_Ludwig_van)",
    3: "Symphony_No.3,_Op.55_(Beethoven,_Ludwig_van)",
    4: "Symphony_No.4,_Op.60_(Beethoven,_Ludwig_van)",
    5: "Symphony_No.5,_Op.67_(Beethoven,_Ludwig_van)",
    6: "Symphony_No.6,_Op.68_(Beethoven,_Ludwig_van)",
    7: "Symphony_No.7,_Op.92_(Beethoven,_Ludwig_van)",
    8: "Symphony_No.8,_Op.93_(Beethoven,_Ludwig_van)",
    9: "Symphony_No.9,_Op.125_(Beethoven,_Ludwig_van)",
}

YEAR_RE = re.compile(r"\[(?:ca\.\s*)?(\d{4})\]|\((\d{4})\)|\b(1[789]\d{2}|20\d{2})\b")
PLATE_RE = re.compile(r"Plate\s+([^.\n]+?)\.")
CITY_RE = re.compile(
    r"\b(Leipzig|London|Paris|Berlin|Vienna|Wien|Mainz|"
    r"New York|Milano|Milan|Rome|Roma|Tokyo|M[uü]nchen|Munich|"
    r"Zurich|Z[uü]rich|Stuttgart|Amsterdam|Brussels|Madrid|Florence|"
    r"Frankfurt|Hamburg|Bonn|Boston|Philadelphia|Chicago|Moscow|"
    r"St\.\s*Petersburg|Prague|Praha|Budapest|Copenhagen|Stockholm)\b",
    re.I,
)
COUNTRY_BY_CITY = {
    "leipzig": "Germany", "berlin": "Germany", "mainz": "Germany", "stuttgart": "Germany",
    "münchen": "Germany", "munchen": "Germany", "munich": "Germany",
    "frankfurt": "Germany", "hamburg": "Germany", "bonn": "Germany",
    "london": "United Kingdom",
    "paris": "France",
    "vienna": "Austria", "wien": "Austria",
    "new york": "USA", "boston": "USA", "philadelphia": "USA", "chicago": "USA",
    "milan": "Italy", "milano": "Italy", "rome": "Italy", "roma": "Italy", "florence": "Italy",
    "tokyo": "Japan",
    "zurich": "Switzerland", "zürich": "Switzerland",
    "amsterdam": "Netherlands",
    "brussels": "Belgium",
    "madrid": "Spain",
    "moscow": "Russia", "st. petersburg": "Russia",
    "prague": "Czech Republic", "praha": "Czech Republic",
    "budapest": "Hungary",
    "copenhagen": "Denmark",
    "stockholm": "Sweden",
}

PUBLISHER_KEYWORDS = [
    ("breitkopf", "Breitkopf & Härtel"),
    ("eulenburg", "Eulenburg"),
    ("peters", "Peters"),
    ("schirmer", "G. Schirmer"),
    ("schott", "Schott"),
    ("ricordi", "Ricordi"),
    ("haslinger", "Tobias Haslinger"),
    ("augener", "Augener"),
    ("universal", "Universal Edition"),
    ("henle", "G. Henle Verlag"),
    ("simrock", "N. Simrock"),
    ("bote", "Bote & Bock"),
    ("litolff", "Litolff"),
    ("cranz", "Cranz"),
    ("senff", "Bartholf Senff"),
    ("hofmeister", "Hofmeister"),
    ("steingräber", "Steingräber"),
    ("steingraber", "Steingräber"),
    ("kalmus", "Edwin F. Kalmus"),
    ("dover", "Dover"),
    ("bärenreiter", "Bärenreiter"),
    ("barenreiter", "Bärenreiter"),
    ("philharmonia", "Philharmonia"),
    ("boosey", "Boosey & Hawkes"),
    ("cianchettini", "Cianchettini & Sperati"),
    ("heugel", "Heugel & Cie."),
    ("steiner", "S.A. Steiner & Co."),
    ("ongaku", "Ongaku No Tomo Sha"),
    ("wiener philharmonischer", "Wiener Philharmonischer Verlag"),
    ("philharmonischer verlag", "Wiener Philharmonischer Verlag"),
]


def http_get(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (ReEngrave research script)"})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def fetch_page(slug: str) -> str:
    cache = CACHE_DIR / f"{slug.replace('/', '_')}.html"
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    url = f"https://imslp.org/wiki/{slug}"
    print(f"  fetching {url}")
    text = http_get(url)
    cache.write_text(text, encoding="utf-8")
    time.sleep(2)
    return text


def slugify_publisher(name: str) -> str:
    if not name:
        return ""
    lower = name.lower()
    for keyword, _label in PUBLISHER_KEYWORDS:
        if keyword in lower:
            return keyword.split()[0]
    return re.sub(r"[^a-z0-9]+", "-", lower).strip("-")[:30]


def guess_publisher_name(pub_text: str) -> str:
    lower = pub_text.lower()
    for keyword, label in PUBLISHER_KEYWORDS:
        if keyword in lower:
            return label
    return ""


def parse_pub_info(pub_text: str) -> dict:
    year_match = YEAR_RE.search(pub_text)
    year = ""
    if year_match:
        year = next((g for g in year_match.groups() if g), "")

    plate_match = PLATE_RE.search(pub_text)
    plate = plate_match.group(1).strip() if plate_match else ""

    city_match = CITY_RE.search(pub_text)
    city = city_match.group(1).title() if city_match else ""

    country = COUNTRY_BY_CITY.get(city.lower(), "") if city else ""
    publisher = guess_publisher_name(pub_text)

    return {
        "publisher": publisher,
        "publisher_slug": slugify_publisher(publisher),
        "year": year,
        "plate": plate,
        "city": city,
        "country": country,
    }


def parse_work_page(html: str) -> dict[str, dict]:
    soup = BeautifulSoup(html, "lxml")
    result: dict[str, dict] = {}

    for file_div in soup.find_all("div", id=re.compile(r"^IMSLP\d+$")):
        file_id = file_div["id"].replace("IMSLP", "")

        edition_info = None
        cursor = file_div
        for _ in range(8):
            cursor = cursor.find_next_sibling()
            if cursor is None:
                break
            if cursor.name == "table" and "we_edition_info" in (cursor.get("class") or []):
                edition_info = cursor
                break
            if cursor.name == "div" and re.match(r"^IMSLP\d+$", cursor.get("id", "") or ""):
                # Hit another file — keep walking; multiple files can share an edition info
                continue

        if edition_info is None:
            # Try scanning forward in the document
            edition_info = file_div.find_next("table", class_="we_edition_info")

        pub_text = ""
        if edition_info is not None:
            for row in edition_info.find_all("tr"):
                th = row.find("th")
                if th and "Pub" in th.get_text():
                    td = row.find("td")
                    if td:
                        pub_text = td.get_text(" ", strip=True)
                    break

        parsed = parse_pub_info(pub_text)
        parsed["raw_pub_info"] = pub_text
        result[file_id] = parsed

    return result


def write_metadata_yaml(meta_file: Path, file_id: str, sym_n: int, info: dict, source_pdf_name: str) -> None:
    def q(v: str) -> str:
        if v is None:
            return '""'
        s = str(v).replace('"', "'")
        return f'"{s}"'

    lines = [
        f"imslp_id: {file_id}",
        f"imslp_url: https://imslp.org/wiki/Special:ReverseLookup/{file_id}",
        f"work: Beethoven Symphony No. {sym_n}",
        f"original_filename: {source_pdf_name}",
        f"publisher: {q(info.get('publisher', ''))}",
        f"publisher_slug: {q(info.get('publisher_slug', ''))}",
        f"year: {q(info.get('year', ''))}",
        f"plate_number: {q(info.get('plate', ''))}",
        f"city: {q(info.get('city', ''))}",
        f"country: {q(info.get('country', ''))}",
        f"raw_pub_info: {q(info.get('raw_pub_info', ''))}",
        # confirmed=true when we have publisher AND year (high confidence auto-fill);
        # otherwise leave at false so it shows up in the manual-research list.
        f"confirmed: {'true' if (info.get('publisher') and info.get('year')) else 'false'}",
        f"notes: \"\"",
        "",
    ]
    meta_file.write_text("\n".join(lines))


def main() -> int:
    total = updated = no_match = parse_failed = 0
    unconfirmed: list[tuple[int, str, str]] = []

    for sym_n, slug in BEETHOVEN_PAGES.items():
        sym_dir = TARGET_ROOT / f"beethoven-symphony-{sym_n}" / "pdfs"
        if not sym_dir.exists():
            continue
        edition_dirs = sorted(d for d in sym_dir.iterdir() if d.is_dir())
        if not edition_dirs:
            continue

        print(f"\n=== Beethoven {sym_n} ({len(edition_dirs)} editions) ===")
        html = fetch_page(slug)
        page_data = parse_work_page(html)
        print(f"  parsed {len(page_data)} file entries on page")

        for ed_dir in edition_dirs:
            m = re.match(r"imslp-(\d+)", ed_dir.name)
            if not m:
                continue
            file_id = m.group(1)
            total += 1

            info = page_data.get(file_id)
            if info is None:
                # Try stripped of leading zeros
                stripped = file_id.lstrip("0") or "0"
                info = page_data.get(stripped)

            meta_file = ed_dir / "metadata.yaml"
            old_meta = meta_file.read_text() if meta_file.exists() else ""
            source_pdf_name = ""
            m2 = re.search(r"original_filename:\s*(.+)", old_meta)
            if m2:
                source_pdf_name = m2.group(1).strip()

            if info is None:
                no_match += 1
                print(f"    {ed_dir.name}: NO MATCH on work page")
                unconfirmed.append((sym_n, ed_dir.name, "no match"))
                continue

            write_metadata_yaml(meta_file, file_id, sym_n, info, source_pdf_name)
            updated += 1
            pub_disp = (info.get("publisher") or "(?)")[:25]
            yr_disp = info.get("year") or "?"
            plate_disp = (info.get("plate") or "")[:25]
            tick = "✓" if (info.get("publisher") and info.get("year")) else "?"
            print(f"    {tick} {ed_dir.name:>20s}  {pub_disp:25s} {yr_disp:>5s}  {plate_disp}")
            if not (info.get("publisher") and info.get("year")):
                unconfirmed.append((sym_n, ed_dir.name, info.get("raw_pub_info", "")[:80]))

    print(f"\n=== SUMMARY ===")
    print(f"Total PDFs:  {total}")
    print(f"Updated:     {updated}")
    print(f"No match:    {no_match}")
    print(f"Confirmed:   {updated - len(unconfirmed)}")
    print(f"Need review: {len(unconfirmed)}")
    if unconfirmed:
        print("\nNeed manual review (publisher or year missing):")
        for sym_n, name, hint in unconfirmed:
            print(f"  Beethoven {sym_n}: {name}  →  {hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
