#!/usr/bin/env python3
"""Resolve an IMSLP file id to its work page and that file's publisher metadata.

IMSLP gates *file downloads* behind a JavaScript redirect, but the wiki itself and
the MediaWiki API are open, so provenance can be read without touching the gate.

    python3 -m tools.library.imslp_meta 19118 24779

Prints one JSON object per id.  Requests are spaced by ``--delay`` seconds
(default 4) so a batch never looks like a scrape.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "ReEngrave-library/1.0 (personal score-catalogue tool; contact delmas41@gmail.com)"
FIELDS = (
    "File Description",
    "Publisher Information",
    "Editor",
    "Copyright",
    "Reprint",
    "Image Type",
    "Scanner",
    "Uploader",
    "Date Submitted",
    "Misc. Notes",
)


def _get(url: str) -> tuple[str, str]:
    """Return (final_url, body)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.geturl(), resp.read().decode("utf-8", "replace")


def page_title_for(imslp_id: str) -> str:
    """ReverseLookup 302s to the work page; the title is in the final URL."""
    final, _ = _get(f"https://imslp.org/wiki/Special:ReverseLookup/{imslp_id}")
    path = urllib.parse.urlparse(final).path
    return urllib.parse.unquote(path.rsplit("/", 1)[-1]).replace("_", " ")


def wikitext(title: str) -> str:
    url = (
        "https://imslp.org/api.php?action=parse&page="
        + urllib.parse.quote(title)
        + "&prop=wikitext&format=json"
    )
    _, body = _get(url)
    return json.loads(body)["parse"]["wikitext"]["*"]


def _publisher_template(body: str) -> str:
    """Render IMSLP's {{P|...}} publisher template as "Name, City, Year, plate N".

    Observed field order (positions are 1-based, empties are common):
        1 short/link name, 2 full name, 3 city, 5 year, 7 plate number.
    Anything unexpected falls back to joining the non-empty fields, so a template
    shape this does not know about degrades to readable text rather than to "".
    """
    f = [x.strip() for x in body.split("|")]
    f += [""] * (7 - len(f))
    name = f[1] or f[0]
    city, year, plate = f[2], f[4], f[6]
    parts = [p for p in (name, city, year) if p]
    if plate:
        parts.append(f"plate {plate}")
    if not parts:
        parts = [x for x in f if x]
    return ", ".join(parts)


def _clean(value: str) -> str:
    """Strip the wiki markup IMSLP uses inside metadata fields."""
    value = value.strip()
    # {{P|...}} and {{RC|...}} carry the publisher/recording facts we actually want.
    m = re.match(r"\{\{(P|RC)\|(.*?)\}\}\s*$", value, re.S)
    if m:
        return _publisher_template(m.group(2))
    value = re.sub(r"\{\{FE\}\}", "First edition", value)
    value = re.sub(r"\[\[[^|\]]*\|([^\]]*)\]\]", r"\1", value)
    value = re.sub(r"\[\[([^\]]*)\]\]", r"\1", value)
    value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"</?[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip(" ,")


def file_metadata(imslp_id: str) -> dict:
    title = page_title_for(imslp_id)
    text = wikitext(title)

    work = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
    composer = ""
    m = re.search(r"\(([^()]*,[^()]*)\)\s*$", title)
    if m:
        composer = m.group(1).strip()

    out = {
        "imslp_id": str(imslp_id),
        "imslp_page": title,
        "imslp_url": "https://imslp.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
        "permalink": f"https://imslp.org/wiki/Special:ReverseLookup/{imslp_id}",
        "work_title": work,
        "composer": composer,
    }

    # Locate the file block whose "File Name N" carries this id's PMLP filename.
    # The id itself is not in the wikitext, so match via the page's rendered anchor
    # ordering: every "#fte:imslpfile" block numbers its files, and the download
    # filename is IMSLP<id>-<File Name>.  Callers pass the PMLP stem when known.
    blocks = text.split("{{#fte:imslp")
    for block in blocks:
        for n in re.findall(r"\|File Name (\d+)\s*=", block):
            fname = _clean(re.search(rf"\|File Name {n}\s*=([^\n]*)", block).group(1))
            entry = {"file_name": fname}
            for field in FIELDS:
                mm = re.search(rf"\|{re.escape(field)}(?: {n})?\s*=(.*?)(?=\n\|[A-Z]|\n\}}\}}|\Z)", block, re.S)
                if mm:
                    raw = mm.group(1).strip()
                    val = _clean(raw)
                    if val:
                        key = field.lower().replace(" ", "_").rstrip(".")
                        entry[key] = val
                        if raw != val:
                            entry.setdefault("_raw", {})[key] = raw
            out.setdefault("files", []).append(entry)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--delay", type=float, default=4.0)
    args = ap.parse_args()

    for i, imslp_id in enumerate(args.ids):
        if i:
            time.sleep(args.delay)
        try:
            print(json.dumps(file_metadata(imslp_id), indent=2, ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001 - a bad id must not kill the batch
            print(json.dumps({"imslp_id": imslp_id, "error": str(exc)}), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
