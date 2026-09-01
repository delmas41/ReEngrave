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
import html as html_mod
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


def page_for(imslp_id: str) -> tuple[str, str]:
    """ReverseLookup 302s to the work page.  Returns (page title, page HTML)."""
    final, body = _get(f"https://imslp.org/wiki/Special:ReverseLookup/{imslp_id}")
    path = urllib.parse.urlparse(final).path
    return urllib.parse.unquote(path.rsplit("/", 1)[-1]).replace("_", " "), body


def file_name_for(imslp_id: str, html: str) -> dict:
    """Which of the page's files IS this id.

    The wikitext never mentions the numeric file id, so matching on it there is
    guesswork — and guessing picked a modern typeset for a 2002 upload.  The
    rendered page states it: every file sits in ``<div id="IMSLP<id>">`` and
    links its own ``File:<name>``.  Read that, then use the name as the key.
    """
    # Ids render zero-padded on the oldest uploads ("IMSLP00033" for file 33).
    stripped = str(imslp_id).lstrip("0") or "0"
    m = re.search(rf'<div id="IMSLP0*{stripped}"(.*?)(?=<div id="IMSLP\d|\Z)', html, re.S)
    if not m:
        return {}
    block = m.group(1)
    out: dict = {}
    name = re.search(r'title="File:([^"]+)"', block)
    if name:
        # The link title renders underscores as spaces; the wikitext keeps them.
        out["file_name"] = html_mod.unescape(name.group(1))
    size = re.search(r"-\s*([\d.]+)\s*MB,\s*([\d]+)\s*pp", block)
    if size:
        out["listed_mb"] = float(size.group(1))
        out["listed_pages"] = int(size.group(2))
    desc = re.search(r'<span title="Download this file">.*?</span></span>([^<]+)</span>', block, re.S)
    if desc:
        out["listed_description"] = html_mod.unescape(desc.group(1)).strip()
    return out


def wikitext(title: str) -> str:
    url = (
        "https://imslp.org/api.php?action=parse&page="
        + urllib.parse.quote(title)
        + "&prop=wikitext&format=json"
    )
    _, body = _get(url)
    return json.loads(body)["parse"]["wikitext"]["*"]


def _name_key(name: str) -> str:
    """Compare filenames across renderings: MediaWiki shows spaces where the
    wikitext has underscores, and capitalises the first letter."""
    return re.sub(r"[\s_]+", "_", (name or "").strip()).lower()


#: IMSLP names its standard editions with a template instead of free text.  Only
#: the ones actually seen in this library are listed; anything else renders
#: generically rather than silently becoming "".
KNOWN_EDITIONS = {
    "mozartcomplete": "Breitkopf & Härtel (Mozart's Werke)",
    "mozartnma": "Bärenreiter (Neue Mozart-Ausgabe)",
    "beethovencomplete": "Breitkopf & Härtel (Beethoven's Werke)",
    "bachgesellschaft": "Breitkopf & Härtel (Bach-Gesellschaft Ausgabe)",
    "brahmscomplete": "Breitkopf & Härtel (Brahms Sämtliche Werke)",
    "mssau": "Manuscript, autograph",
    "mss": "Manuscript",
}


def _named_edition(name: str, args: list[str]) -> str:
    label = KNOWN_EDITIONS.get(name.lower(), name)
    # Editors write "VIII:<br>Symphonien" inside template args; a tag is not text.
    args = [re.sub(r"\s+", " ", re.sub(r"</?[^>]+>", " ", a)).strip() for a in args]
    year = next((a for a in args if re.fullmatch(r"1[5-9]\d{2}|20\d{2}", a)), "")
    volume = next((a for a in args if a and a != year and not a[:1].isdigit()), "")
    parts = [label]
    if volume:
        parts.append(volume)
    if year:
        parts.append(year)
    return ", ".join(parts)


def _publisher_template(body: str) -> str:
    """Render IMSLP's {{P|...}} publisher template as "Name, City, Year, plate N".

    Observed field order (positions are 1-based, empties are common):
        1 short/link name, 2 full name, 3 city, 5 year, 7 plate number.
    Anything unexpected falls back to joining the non-empty fields, so a template
    shape this does not know about degrades to readable text rather than to "".
    """
    # A nested template ({{HMB|1870|176}} as the date-of-publication reference)
    # carries its own pipes; splitting through it shifts every later field and
    # turned a year into a plate number.  Collapse nested braces first.
    flat = re.sub(r"\{\{[^{}]*\}\}", "<ref>", body)
    while "{{" in flat:
        reduced = re.sub(r"\{\{[^{}]*\}\}", "<ref>", flat)
        if reduced == flat:
            break
        flat = reduced
    f = [x.strip() for x in flat.split("|")]
    f += [""] * (7 - len(f))
    name = f[1] or f[0]
    city, year, plate = f[2], f[4], f[6]
    parts = [p for p in (name, city, year) if p and p != "<ref>"]
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
    # {{LinkEd|Knute|Snortum|1960|}} is an editor, given name first.
    m = re.match(r"\{\{LinkEd\|(.*?)\}\}\s*$", value, re.S | re.I)
    if m:
        f = [a.strip() for a in m.group(1).split("|")]
        name = " ".join(x for x in f[:2] if x)
        return f"{name} ({f[2]})" if len(f) > 2 and f[2] else name
    m = re.match(r"\{\{([A-Za-z][A-Za-z0-9]*)\|(.*?)\}\}\s*$", value, re.S)
    if m:
        return _named_edition(m.group(1), [a.strip() for a in m.group(2).split("|")])
    value = re.sub(r"\{\{FE\}\}", "First edition", value)
    value = re.sub(r"\[\[[^|\]]*\|([^\]]*)\]\]", r"\1", value)
    value = re.sub(r"\[\[([^\]]*)\]\]", r"\1", value)
    value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"</?[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip(" ,")


def file_metadata(imslp_id: str) -> dict:
    title, html = page_for(imslp_id)
    listed = file_name_for(imslp_id, html)
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
        "file_name": listed.get("file_name", ""),
        "listed_pages": listed.get("listed_pages"),
        "listed_description": listed.get("listed_description", ""),
    }

    # With the id's own filename in hand from the rendered page, the wikitext
    # block that names it is the right one and no heuristic is involved.
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

    wanted = _name_key(out.get("file_name", ""))
    if wanted:
        for entry in out.get("files", []):
            if _name_key(entry.get("file_name", "")) == wanted:
                out["file"] = entry
                break
    return out


def page_html(title: str) -> str:
    _, body = _get("https://imslp.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")))
    return body


def page_files(title: str) -> list[dict]:
    """Every file on a work page, id-matched to its metadata, in ONE page fetch.

    ``file_metadata`` re-fetches the page for each id, which is wasteful and rude
    when comparing the twenty editions a popular symphony has.  Same matching
    rule: the rendered page says which file an id is, the wikitext says what that
    file is.
    """
    html = page_html(title)
    text = wikitext(title)

    by_name: dict[str, dict] = {}
    for block in text.split("{{#fte:imslp"):
        for n in re.findall(r"\|File Name (\d+)\s*=", block):
            fname = _clean(re.search(rf"\|File Name {n}\s*=([^\n]*)", block).group(1))
            entry = {"file_name": fname}
            for field in FIELDS:
                mm = re.search(
                    rf"\|{re.escape(field)}(?: {n})?\s*=(.*?)(?=\n\|[A-Z]|\n\}}\}}|\Z)",
                    block, re.S)
                if mm and _clean(mm.group(1)):
                    entry[field.lower().replace(" ", "_").rstrip(".")] = _clean(mm.group(1))
            by_name[_name_key(fname)] = entry

    # Which section a file sits in ("Full Scores", "Parts", "Arrangements") is
    # only in the rendered page, and it matters: "Complete Score" appears under
    # Vocal Scores and Arrangements too, and those are not what we want to OMR.
    # Take the SPAN of the "Full Scores" heading rather than the nearest heading
    # above each file: IMSLP nests subsections ("Complete", "Selections") under
    # it, so the nearest heading is a subsection name and says nothing about
    # whether the file is a score, a recording or a piano arrangement.
    # Most works have a "Full Scores" subsection; works with only one kind of
    # score have a bare "Scores" header instead, and looking only for the former
    # silently returned nothing for them (Beethoven's first symphony among them).
    fs_start = html.find('id="Full_Scores"')
    if fs_start < 0:
        fs_start = html.find('id="Scores"')
    fs_end = len(html)
    if fs_start >= 0:
        for marker in ('id="Parts"', 'id="Arrangements', 'id="Vocal_Scores"',
                       'id="Sheet_Music"', 'id="Libretti"'):
            pos = html.find(marker, fs_start + 1)
            if pos >= 0:
                fs_end = min(fs_end, pos)

    out = []
    for m in re.finditer(r'<div id="IMSLP(\d+)"(.*?)(?=<div id="IMSLP\d|\Z)', html, re.S):
        fid = m.group(1)
        listed = file_name_for(fid, html)
        entry = dict(by_name.get(_name_key(listed.get("file_name", "")), {}))
        entry.update({k: v for k, v in listed.items() if v})
        entry["imslp_id"] = fid.lstrip("0") or fid
        entry["full_score"] = fs_start >= 0 and fs_start < m.start() < fs_end
        out.append(entry)
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
