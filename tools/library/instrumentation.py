#!/usr/bin/env python3
"""What a WORK is scored for, read from IMSLP, keyed on ``work_id``.

A staff-identity layer works by acquiring the work's instrument ROSTER and
joining it to a page's staves in order.  Reading the roster off the printed page
succeeds most of the time; where it fails, an independent WORK-LEVEL source is
the escalation, and the IMSLP work page states one.  It costs one API call per
work — the same open MediaWiki API :mod:`tools.library.imslp_meta` already uses
for publisher and plate, never the JavaScript download gate.

Two fields, and only the second is a roster::

    |Instrumentation=orchestra
    |InstrDetail={{More}} piccolo, 2 flutes, 2 oboes, ... , timpani, strings {{MoreEnd}}

``Instrumentation`` is a genre bucket ("orchestra", "piano") and is captured for
completeness.  ``InstrDetail`` is the roster, and it arrives in **two dialects**:

``prose``     "piccolo, 2 flutes, 2 oboes, 2 clarinets, 2 bassoons, contrabassoon,
              2 horns, 2 trumpets, 3 trombones, timpani, strings"
``compact``   "2, 2, 2, 2+1 - 4, 2, 3, 0, timp, strs" — the standard orchestration
              shorthand: four wind slots, a dash, four brass slots, then extras.
              The SLOT ORDER is the convention (fl, ob, cl, bn — hn, tpt, tbn,
              tuba); the numbers alone carry no names, so a group that is not
              exactly four tokens long is a convention this does not know and is
              recorded unparsed rather than guessed at.

⚠️ **N instruments is not N staves.**  This describes the WORK.  A printed score
condenses (Flute 1+2 share a staff) and splits (divisi), and a sibling
workstream proved the condensed COUNT is a property of the ENCODING and cannot
be derived from the page.  A roster is evidence about *which parts exist and in
what order*, never about how many staves an edition prints.

⚠️ **PROVENANCE IS PER FACT.**  Every record carries ``source`` and
``source_kind``.  ``source_kind == "catalog"`` means the fact came from a
bibliographic source that is independent of any encoding we score against;
``"encoding"`` would mean it was derived from a MusicXML file, which is the same
substrate the accuracy benchmarks use as truth and therefore may NOT be read by
a measurement path.  This module only ever writes ``"catalog"``.  The
distinction is enforced by :func:`validate_fact`, not by convention.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.library.imslp_meta import _get  # noqa: E402
from tools.library.score_library import (  # noqa: E402
    CATALOG_PATH,
    load_catalog,
    save_catalog,
)
from tools.omr import instruments as lex  # noqa: E402

#: Where a fact came from, and whether a measurement path may read it.
#: A source not in this table is refused — the distinction has to be structural,
#: because it cannot be retrofitted onto facts already written.
SOURCE_KINDS = {
    "imslp": "catalog",      # bibliographic, independent of any encoding
    "hand": "catalog",       # a person read a printed score
    "musicxml": "encoding",  # derived from a reference file = benchmark truth
}

#: Terms that name a SECTION, not an instrument.  "strings" is one line on an
#: IMSLP page and five parts in a score, and how many desks or how it divides is
#: not stated — so it is recorded as a section with no count rather than
#: expanded into a guess.  Deliberately short: anything not here abstains.
SECTION_TERMS = {
    "strings": "Strings",
    "string": "Strings",
    "strs": "Strings",
    "str": "Strings",
    "archi": "Strings",
    "streicher": "Strings",
    "continuo": "Continuo",
    "basso continuo": "Continuo",
    "bc": "Continuo",
    "winds": "Winds",
    "brass": "Brass",
}

#: The compact dialect's slot order.  This IS the convention — the numbers carry
#: no names — so it is written out once, here, and a group of any other length
#: is refused rather than mapped.
COMPACT_WINDS = ("Flute", "Oboe", "Clarinet", "Bassoon")
COMPACT_BRASS = ("Horn", "Trumpet", "Trombone", "Tuba")

#: Abbreviations the compact dialect uses for the extras after the brass, where
#: the lexicon (written for printed margin labels) has no alias.
COMPACT_EXTRAS = {
    "hp": "Harp",
    "hrp": "Harp",
    "cel": "Celesta",
    "org": "Organ",
    "pf": "Piano",
    "pno": "Piano",
    "tmp": "Timpani",
    "prc": "Percussion",
}

_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

_COUNT_TOKEN = re.compile(r"^(\d+)(\+\d+)?(d\d*)?$", re.I)


# ---------------------------------------------------------------------------
# fetching
# ---------------------------------------------------------------------------


def _parse_api(title: str, *, _depth: int = 0) -> tuple[str, str, int | None]:
    """(resolved title, wikitext, revision id), following ``#REDIRECT``.

    Same redirect trap :func:`imslp_meta.wikitext` documents — ``action=parse``
    hands back the stub, not the target — plus the ``revid``, so a recorded fact
    names the page revision it was read from and can be re-checked later.
    """
    url = (
        "https://imslp.org/api.php?action=parse&page="
        + urllib.parse.quote(title)
        + "&prop=wikitext|revid&redirects=1&format=json"
    )
    _, body = _get(url)
    parsed = json.loads(body)["parse"]
    text = parsed["wikitext"]["*"]
    revid = parsed.get("revid")
    m = re.match(r"\s*#REDIRECT\s*\[\[([^\]]+)\]\]", text, re.I)
    if m and _depth < 3:
        return _parse_api(m.group(1).strip(), _depth=_depth + 1)
    return parsed.get("title", title), text, revid


def _field(text: str, name: str) -> str:
    """The value of one ``|Field=`` in the page's general-information block.

    Stops at the next ``|Field=`` at line start, so a value carrying ``<br>`` or
    a template with its own pipes survives whole.
    """
    m = re.search(
        rf"^\|{re.escape(name)}\s*=(.*?)(?=^\|[A-Z]|^\}}\}}|\Z)",
        text, re.S | re.M,
    )
    return m.group(1).strip() if m else ""


def fetch_work_instrumentation(title: str) -> dict:
    """Read one work page's instrumentation fields.  One HTTP call.

    Returns the RAW strings verbatim — they are the evidence, everything else in
    this module is derivative of them.
    """
    resolved, text, revid = _parse_api(title)
    return {
        "imslp_page": resolved,
        "imslp_url": "https://imslp.org/wiki/"
        + urllib.parse.quote(resolved.replace(" ", "_")),
        "imslp_revid": revid,
        "raw": {
            "Instrumentation": _field(text, "Instrumentation"),
            "InstrDetail": _field(text, "InstrDetail"),
        },
    }


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------


def _strip_markup(value: str) -> str:
    """Wiki markup out, words kept.  Never applied to what gets stored as raw."""
    value = re.sub(r"\{\{\s*(More|MoreEnd|LinkGen)[^{}]*\}\}", " ", value, flags=re.I)
    value = re.sub(r"<br\s*/?>", ", ", value, flags=re.I)
    value = re.sub(r"\[\[[^|\]]*\|([^\]]*)\]\]", r"\1", value)
    value = re.sub(r"\[\[([^\]]*)\]\]", r"\1", value)
    value = re.sub(r"\{\{[^{}]*\}\}", " ", value)
    value = re.sub(r"</?[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip(" ,;")


def _fragments(text: str) -> list[str]:
    parts = re.split(r"[,;]|\band\b|\+(?=\s)", text)
    return [p.strip(" .;:") for p in parts if p.strip(" .;:")]


def _split_count(fragment: str) -> tuple[int | None, str, str]:
    """("2 flutes") -> (2, "flutes", "").  The third field is a modifier kept
    verbatim ("2+1", "4d4") so nothing about the fragment is silently dropped."""
    m = re.match(r"^(\d+)\s*(\+\s*\d+|d\s*\d*)?\s*(.*)$", fragment, re.I)
    if m and m.group(3):
        mod = re.sub(r"\s+", "", m.group(2) or "")
        return int(m.group(1)), m.group(3).strip(), mod
    m = re.match(r"^([a-z]+)\s+(.*)$", fragment, re.I)
    if m and m.group(1).lower() in _WORD_NUMBERS:
        return _WORD_NUMBERS[m.group(1).lower()], m.group(2).strip(), ""
    return None, fragment.strip(), ""


def _singulars(name: str) -> list[str]:
    """"2 oboes" -> also try "oboe"; "double basses" -> also "double bass".

    ⚠️ The lexicon is written for printed MARGIN LABELS, where a part is named
    in Italian or German ("Oboi", "Celli") or abbreviated ("Ob."), so the plain
    ENGLISH PLURALS an IMSLP prose roster uses are simply not aliases: `oboes`,
    `cellos` and `double basses` all return None while `oboi`, `celli` and
    `violas` match.  Only the last word is de-pluralised, and a match that
    needed it is flagged in the item — this is an English-plural normalisation
    of OUR input, not a loosening of the lexicon's gate.
    """
    words = name.split()
    if not words:
        return []
    last = words[-1]
    out = []
    for stem in (last[:-2] if last.lower().endswith("es") else "",
                 last[:-1] if last.lower().endswith("s") else ""):
        if stem and stem.lower() != last.lower():
            out.append(" ".join(words[:-1] + [stem]))
    return out


def _resolve(name: str) -> dict | None:
    """One fragment's name -> a roster item, or None to abstain.

    Section first, because "strings" must NOT reach the instrument lexicon and
    come back as something with a clef.
    """
    key = re.sub(r"[^a-z ]+", "", name.lower()).strip()
    if key in SECTION_TERMS:
        return {"kind": "section", "section": SECTION_TERMS[key]}
    if key in COMPACT_EXTRAS:
        name = COMPACT_EXTRAS[key]
    for i, candidate in enumerate([name, *_singulars(name)]):
        match = lex.lookup(candidate)
        if match is None:
            continue
        item = {
            "kind": "instrument",
            "instrument": match.instrument.name,
            "family": match.instrument.family,
            "lexicon_alias": match.alias,
            "lexicon_confidence": match.confidence,
        }
        if i:
            item["lexicon_depluralized"] = True
        return item
    return None


def _is_compact(text: str) -> bool:
    """Is this the numeric shorthand, or prose that merely contains numbers?

    ⚠️ A COUNT OF NUMERIC TOKENS IS NOT ENOUGH, and the case that broke it is
    ordinary: Wagner writes "… harp, strings (16, 16, 12, 12, 8)" — five bare
    numbers of desk counts at the end of a plainly prose roster — and a
    three-numeric-token threshold sent all 21 fragments through the positional
    parser, which correctly abstained on every one of them.  A compact roster is
    MOSTLY numbers (Brahms 8 of 10, Mahler 8 of 12); Wagner's orchestra line is
    5 of 21.  The fraction separates them with nothing near the line.
    """
    tokens = [t.strip() for t in re.split(r"[-,]", text) if t.strip()]
    if len(tokens) < 4:
        return False
    numeric = sum(1 for t in tokens if _COUNT_TOKEN.match(t))
    return numeric >= 3 and numeric / len(tokens) >= 0.5


def _parse_compact(text: str) -> tuple[list[dict], list[str]]:
    """"2, 2, 2, 2+1 - 4, 2, 3, 0, timp, strs" by SLOT POSITION.

    A wind or brass group that is not exactly four tokens is a convention this
    does not know; the whole group goes to ``unparsed`` rather than being
    mapped off-by-one onto the slot names.
    """
    roster: list[dict] = []
    unparsed: list[str] = []
    halves = re.split(r"\s+-\s+|\s-\s", text, maxsplit=1)
    left = [t.strip() for t in halves[0].split(",") if t.strip()]
    right = [t.strip() for t in (halves[1].split(",") if len(halves) > 1 else []) if t.strip()]

    def slots(tokens: list[str], names: tuple[str, ...]) -> list[str]:
        if len(tokens) != len(names):
            unparsed.extend(tokens)
            return []
        for token, name in zip(tokens, names):
            m = _COUNT_TOKEN.match(token)
            if not m:
                unparsed.append(token)
                continue
            count = int(m.group(1))
            if count == 0:      # the slot is explicitly empty: parsed, not present
                continue
            item = _resolve(name)
            if item is None:    # cannot happen for the fixed slot names, but abstain
                unparsed.append(token)
                continue
            item.update({"count": count, "text": token, "slot": name})
            mod = "".join(p for p in (m.group(2), m.group(3)) if p)
            if mod:
                item["modifier"] = mod
            roster.append(item)
        return []

    brass_tokens = [t for t in right[:4] if _COUNT_TOKEN.match(t)]
    extras = right[len(brass_tokens):] if len(brass_tokens) == 4 else right
    slots(left, COMPACT_WINDS)
    if len(brass_tokens) == 4:
        slots(brass_tokens, COMPACT_BRASS)
    else:
        unparsed.extend(right)
        extras = []

    for token in extras:
        count, name, mod = _split_count(token)
        item = _resolve(name)
        if item is None:
            unparsed.append(token)
            continue
        _set_count(item, count, token)
        if mod:
            item["modifier"] = mod
        roster.append(item)
    return roster, unparsed


def _set_count(item: dict, count: int | None, text: str) -> None:
    """A SECTION has no count unless the page stated one.

    "strings" is one string of text and five parts of unknown desk count; giving
    it an implied ``count: 1`` would read as "one string player" to anything
    that sums the roster.  An instrument with no stated count is one player,
    which is the ordinary convention of the field.
    """
    item["text"] = text
    if count is not None:
        item["count"] = count
    elif item.get("kind") == "instrument":
        item["count"] = 1


def _parse_prose(text: str) -> tuple[list[dict], list[str]]:
    roster: list[dict] = []
    unparsed: list[str] = []
    for fragment in _fragments(text):
        count, name, mod = _split_count(fragment)
        item = _resolve(name)
        if item is None:
            unparsed.append(fragment)
            continue
        _set_count(item, count, fragment)
        if mod:
            item["modifier"] = mod
        roster.append(item)
    return roster, unparsed


def _parse_one(cleaned: str) -> dict:
    dialect = "compact" if _is_compact(cleaned) else "prose"
    roster, unparsed = (
        _parse_compact(cleaned) if dialect == "compact" else _parse_prose(cleaned)
    )
    total = len(roster) + len(unparsed)
    return {
        "dialect": dialect,
        "cleaned": cleaned,
        "roster": roster,
        "unparsed": unparsed,
        "parse_rate": round(len(roster) / total, 4) if total else None,
    }


def parse_roster(detail_raw: str) -> dict:
    """Parse an ``InstrDetail`` string.  Abstains fragment by fragment.

    Nothing is forced to a nearest match: a fragment the lexicon does not know
    lands in ``unparsed`` with its own text, so the raw string can always be
    reconstructed by a reader and the shortfall is countable.

    ⚠️ **One field can hold BOTH dialects.**  Bach's B minor Mass writes the
    compact line and then, after ``{{More}}``, the same forces spelled out —
    read as one string that is neither, and it scored 0 of 18.

    ⚠️ **AND AN OPERA'S FIELD IS MOSTLY NOT A ROSTER.**  Tannhäuser and Elektra
    open theirs with the dramatis personae under an italic ``''Cast''`` heading;
    the orchestra is 600 characters further down under ``''Orchestra''``, with
    an on-stage band after it.  Read whole, Tannhäuser parsed 0 of 54 — the
    knights and the ladies charged as abstentions while the roster we wanted sat
    in the same string.

    So the field is cut at ``{{More}}`` **and** at every ``''italic heading''``,
    each piece is parsed alone, and a piece headed *Orchestra* wins outright —
    otherwise the best-parsing piece does.  Everything not chosen is kept
    verbatim in ``segments_ignored``; nothing is dropped, and the raw field is
    stored untouched regardless.
    """
    parses = []
    for chunk in re.split(r"\{\{\s*More\s*\}\}", detail_raw or ""):
        # ''Heading'' markers alternate [text, heading, text, heading, text…]
        pieces = re.split(r"''+([^'\n]{1,60}?)''+", chunk)
        heading = ""
        for i, piece in enumerate(pieces):
            if i % 2 == 1:
                heading = piece.strip(" :")
                continue
            cleaned = _strip_markup(piece)
            if not cleaned:
                continue
            parsed = _parse_one(cleaned)
            parsed["heading"] = heading
            parses.append(parsed)
            heading = ""
    if not parses:
        return {"dialect": "empty", "roster": [], "unparsed": [], "parse_rate": None}
    orchestral = [p for p in parses if re.fullmatch(r"orchestra\w*", p["heading"], re.I)]
    pool = orchestral or parses
    best = max(pool, key=lambda p: (p["parse_rate"] or 0.0, len(p["roster"])))
    out = {k: v for k, v in best.items() if k != "heading"}
    if best["heading"]:
        out["roster_heading"] = best["heading"]
    ignored = [p["cleaned"] for p in parses if p is not best]
    if ignored:
        out["segments_ignored"] = ignored
    return out


# ---------------------------------------------------------------------------
# facts
# ---------------------------------------------------------------------------


def build_fact(fetched: dict, *, source: str = "imslp", when: str | None = None) -> dict:
    """A fetch plus its parse, tagged with where it came from."""
    # ⚠️ `Instrumentation` is a genre bucket on the symphonies ("orchestra") but
    # is the ROSTER ITSELF on smaller works — Brandenburg 2 has no `InstrDetail`
    # at all and writes "recorder*, oboe, trumpet, violin, strings, continuo"
    # here.  Reading only `InstrDetail` therefore abstains on exactly the works
    # whose roster is shortest and most reliable.  Which field a roster came
    # from is recorded, because the two are not equally trustworthy.
    detail = fetched["raw"].get("InstrDetail", "")
    field_used = "InstrDetail"
    if not _strip_markup(detail):
        detail = fetched["raw"].get("Instrumentation", "")
        field_used = "Instrumentation"
    parsed = parse_roster(detail)
    fact = {
        "roster_field": field_used if parsed.get("roster") else "",
        "source": source,
        "source_kind": SOURCE_KINDS[source],
        "evidence": "imslp work-page fields Instrumentation / InstrDetail",
        "fetched": when or date.today().isoformat(),
        "imslp_page": fetched.get("imslp_page", ""),
        "imslp_url": fetched.get("imslp_url", ""),
        "imslp_revid": fetched.get("imslp_revid"),
        "raw": fetched["raw"],
        "describes": "work",
        "note": "instrument counts describe the WORK; a printed edition may "
                "condense or split parts, so N instruments is not N staves",
    }
    fact.update({k: v for k, v in parsed.items() if k != "cleaned"})
    validate_fact(fact)
    return fact


def validate_fact(fact: dict) -> None:
    """Refuse a fact that cannot say where it came from.

    An instrumentation roster is legitimate production evidence *because* it is
    catalog-derived.  A fact with no ``source_kind``, or one whose kind
    disagrees with its source, is indistinguishable from an encoding-derived one
    downstream, so it never gets written.
    """
    source = fact.get("source")
    if source not in SOURCE_KINDS:
        raise ValueError(f"instrumentation fact has unknown source {source!r}")
    if fact.get("source_kind") != SOURCE_KINDS[source]:
        raise ValueError(
            f"source_kind {fact.get('source_kind')!r} disagrees with source {source!r}")
    if "raw" not in fact:
        raise ValueError("instrumentation fact has no raw evidence")


def catalog_works(catalog: dict) -> dict:
    return catalog.setdefault("works", {})


def record(catalog: dict, work_id: str, fact: dict) -> str:
    """Put a fact on a work.  Returns what happened, for the caller's report.

    ⚠️ Two IMSLP pages can land on one ``work_id`` — Clara Schumann's Op.7 and
    Robert Schumann's Op.54 are both ``schumann--piano-concerto`` — and the key
    is the catalog's own and is not to be forked.  So a second page's fact is
    kept BESIDE the first as a conflict and neither is trusted, rather than one
    silently overwriting the other.
    """
    validate_fact(fact)
    works = catalog_works(catalog)
    entry = works.setdefault(work_id, {"work_id": work_id})
    held = entry.get("instrumentation")
    if held and held.get("imslp_page") and fact.get("imslp_page") \
            and held["imslp_page"] != fact["imslp_page"]:
        others = entry.setdefault("instrumentation_conflicts", [])
        if not any(o.get("imslp_page") == fact["imslp_page"] for o in others):
            others.append(fact)
        entry["instrumentation_conflict"] = (
            "two IMSLP work pages share this work_id; neither roster is trusted")
        return "conflict"
    replaced = held is not None
    entry["instrumentation"] = fact
    return "updated" if replaced else "added"


# ---------------------------------------------------------------------------
# backfill
# ---------------------------------------------------------------------------


def pages_to_fetch(catalog: dict, *, refetch: bool = False) -> list[tuple[str, str]]:
    """(work_id, imslp page title) for every held IMSLP file, deduplicated.

    Deduplicated on the PAGE, not the file — 231 IMSLP files in this store sit
    on 225 pages — and skipping work_ids already recorded is what makes a
    backfill idempotent and resumable after an interruption.
    """
    works = catalog.get("works", {})
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for entry in catalog.get("entries", []):
        if entry.get("source") != "imslp":
            continue
        work_id = entry.get("work_id", "")
        page = (entry.get("raw") or {}).get("imslp_page", "")
        if not work_id or not page:
            continue
        if not refetch and works.get(work_id, {}).get("instrumentation"):
            # A second page on a recorded work_id must still be seen, so the
            # conflict above can fire; a repeat of the SAME page is skipped.
            if works[work_id]["instrumentation"].get("imslp_page") == page:
                continue
        if (work_id, page) in seen:
            continue
        seen.add((work_id, page))
        out.append((work_id, page))
    return out


def backfill(*, delay: float, dry_run: bool, limit: int | None = None,
             refetch: bool = False, catalog_path: Path | None = None) -> dict:
    catalog = load_catalog(catalog_path)
    targets = pages_to_fetch(catalog, refetch=refetch)
    if limit:
        targets = targets[:limit]
    report = {"targets": len(targets), "added": 0, "updated": 0,
              "conflict": 0, "errors": []}
    started = time.time()
    for i, (work_id, page) in enumerate(targets):
        if i:
            time.sleep(delay)
        try:
            fact = build_fact(fetch_work_instrumentation(page))
        except Exception as exc:  # noqa: BLE001 - one bad page must not kill a 45-minute run
            report["errors"].append({"work_id": work_id, "page": page, "error": str(exc)})
            print(f"  !! {work_id}: {exc}", file=sys.stderr)
            continue
        what = record(catalog, work_id, fact)
        report[what] += 1
        detail = fact["raw"].get("InstrDetail", "")
        print(f"  {what:8s} {work_id:40s} {fact['dialect']:7s} "
              f"{len(fact['roster']):2d} parsed / {len(fact['unparsed'])} not"
              + ("" if detail else "   (no InstrDetail)"))
        if not dry_run and i % 20 == 19:
            save_catalog(catalog, catalog_path)      # resumable: checkpoint as we go
    if not dry_run:
        save_catalog(catalog, catalog_path)
    report["seconds"] = round(time.time() - started, 1)
    return report


def reparse(*, dry_run: bool, catalog_path: Path | None = None) -> dict:
    """Re-derive every roster from the RAW string already held.  No network.

    This is what storing the raw field verbatim buys: the parser improved twice
    after the 25-minute backfill (both dialects in one field, then opera cast
    lists) and neither improvement cost IMSLP a single request.  The raw string
    and its provenance are never touched — only what is derived from them.
    """
    catalog = load_catalog(catalog_path)
    changed = 0
    for entry in catalog.get("works", {}).values():
        fact = entry.get("instrumentation")
        if not fact:
            continue
        before = json.dumps(fact.get("roster"), sort_keys=True)
        detail = fact["raw"].get("InstrDetail", "")
        field_used = "InstrDetail"
        if not _strip_markup(detail):
            detail = fact["raw"].get("Instrumentation", "")
            field_used = "Instrumentation"
        parsed = parse_roster(detail)
        for key in ("dialect", "roster", "unparsed", "parse_rate",
                    "segments_ignored", "roster_heading", "cleaned"):
            fact.pop(key, None)
        fact.update({k: v for k, v in parsed.items() if k != "cleaned"})
        fact["roster_field"] = field_used if parsed.get("roster") else ""
        validate_fact(fact)
        if json.dumps(fact.get("roster"), sort_keys=True) != before:
            changed += 1
    if not dry_run:
        save_catalog(catalog, catalog_path)
    return {"works": len(catalog.get("works", {})), "rosters_changed": changed}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--backfill", action="store_true",
                    help="re-query every held IMSLP edition's work page")
    ap.add_argument("--reparse", action="store_true",
                    help="re-derive rosters from the raw strings already held (no network)")
    ap.add_argument("--page", help="fetch and print one work page's fields")
    ap.add_argument("--delay", type=float, default=6.0,
                    help="seconds between API calls (default 6)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--refetch", action="store_true",
                    help="re-read works already recorded")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    args = ap.parse_args()

    if args.page:
        print(json.dumps(build_fact(fetch_work_instrumentation(args.page)),
                         indent=2, ensure_ascii=False))
        return 0
    if args.reparse:
        print(json.dumps(reparse(dry_run=args.dry_run, catalog_path=args.catalog),
                         indent=2))
        return 0
    if args.backfill:
        report = backfill(delay=args.delay, dry_run=args.dry_run,
                          limit=args.limit, refetch=args.refetch,
                          catalog_path=args.catalog)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1 if report["errors"] else 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
