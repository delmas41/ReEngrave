#!/usr/bin/env python3
"""What ONE PUBLISHED EDITION is scored for, read from its own printed pages.

:mod:`tools.library.instrumentation` records the roster of a WORK, from the
IMSLP catalog, keyed on ``work_id``.  That tier is complete (223 of 223) and it
is generic on purpose — it describes the piece.  **It is confidently wrong about
a real population of the files we actually run OMR on.**  Bruckner's symphonies
exist in versions with different orchestration; Mahler retouched Beethoven and
Schumann; publishers add, absorb and re-cast parts; and most starkly the same
``work_id`` can hold a full score AND a piano reduction — same piece, entirely
different lineup.  Two of this store's own 235 editions are exactly that
(``handel--messiah`` is held as a vocal reduction and as a lead sheet).

So there are two tiers, one schema, told apart by PROVENANCE:

==========  ====================================  ==========  ==========================
tier        source                                coverage    authority
==========  ====================================  ==========  ==========================
work        IMSLP catalog (``instrumentation``)   223/223     generic; right about the piece
edition     this edition's own printed pages      partial     authoritative for THIS PDF
==========  ====================================  ==========  ==========================

⚠️ **A PAGE-DERIVED FACT IS A THIRD SOURCE KIND.**  ``source_kind`` already
separates ``catalog`` (bibliographic, safe for a measurement path) from
``encoding`` (derived from the MusicXML the benchmarks score against, and
therefore off limits).  A roster read off the edition's own raster is neither:
it is an OMR output, so a measurement path that scores OMR must not read it back
as truth either.  It gets its own value, ``page``, in
:data:`instrumentation.SOURCE_KINDS`, rather than being filed under an existing
one.

⚠️ **NEITHER TIER MAY IMPLY A STAFF COUNT.**  The work tier says so already
(``describes: "work"``); the edition tier is the one that would be believed, and
it must not be.  A printed score condenses (``Flauti`` is two players on one
staff) and splits (divisi), and a sibling workstream proved the condensed count
is a property of the ENCODING and cannot be derived from the page.  So an
edition item carries ``staves`` (how many staves on the roster page printed this
name — an observation) SEPARATELY from ``count`` (how many players the printed
label itself claims, e.g. ``2 Flöten`` — a quotation), and never sums one into
the other.

⚠️ **THE ROSTER IS ONE SYSTEM'S, NOT ONE PAGE'S.**  Reading every staff on a
page reads the roster twice where the page holds two systems: Brahms 1 /
Breitkopf p.1 gives 27 staves and would report Flute, Oboe, Clarinet … twice
over.  The roster is taken from the SYSTEM with the most named staves.

The disagreement between the tiers is a first-class output, not a diagnostic:
:func:`compare_tiers` classifies it, because "work says 12, edition reads 8" is
either an editorial variant worth recording, an arrangement worth triaging, or a
failed read worth escalating — and until now nothing in this project could tell
those apart.  See its docstring for the vocabulary and
``benchmarks/omr-edition-instrumentation-2026-09/`` for the measured mix.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.library import instrumentation as work_tier  # noqa: E402
from tools.library.score_library import (  # noqa: E402
    CATALOG_PATH,
    library_root,
    load_catalog,
    save_catalog,
)

#: Pages to try, in the order a reader would.  Same list the identity
#: workstream's availability sweep used, and for its reason: a movement's first
#: page is usually early but is not always the PDF's first page.  ⚠️ 14 of its
#: 172 acquired rosters came only from pages 3/5/8/12 — "page 1" is the wrong
#: unit.  A recorded ``hit_page`` from that sweep is tried FIRST, which is what
#: makes acquisition one page per document instead of seven.
PROBE_PAGES = (1, 2, 0, 3, 5, 8, 12)
MIN_STAVES = 4
#: named labels / staves on the chosen system.  Same bar the sweep used, so the
#: two measurements are comparable.
HIT_YIELD = 0.50
DEFAULT_DPI = 300

#: What KIND of edition this is.  An arrangement contradicting the work roster
#: wholesale is the strongest signal available that the PDF is not a full score
#: — that is triage, never a bad read, and the record has to be able to say so.
#: Derived from the file's own provenance, and ``unknown`` is a legitimate
#: answer: 216 of this store's 235 editions say only "Complete Score", which is
#: evidence of a full score and of nothing finer.
#: ⚠️ ``\b`` IS THE WRONG BOUNDARY HERE.  These strings are FILENAMES as often
#: as prose, and ``_`` is a word character — so ``\breduction\b`` does not match
#: ``Haendel_Messiah_reduction.pdf``, which is one of exactly two non-full-scores
#: this store holds.  The boundary has to be "not a letter".
SCORE_TYPE_PATTERNS = (
    ("vocal_score", r"vocal[-_ ]?score|klavierauszug|vocal[-_ ]?reduction"),
    ("reduction", r"(?<![a-z])reduction(?![a-z])|piano[-_ ]?reduc|reduktion"),
    ("lead_sheet", r"lead[-_ ]?sheet|fake[-_ ]?book"),
    ("arrangement", r"(?<![a-z])arrang|(?<![a-z])transcri|for piano|"
                    r"piano *(4|four)[-_ ]?hands?|(?<![a-z])duets?(?![a-z])"),
    ("part", r"(?<![a-z])parts?(?![a-z])(?! *of)|stimmen"),
    ("full_score", r"complete score|conductor'?s score|full score|partitur"),
)

#: A work roster says ``strings`` in one word and a page prints four or five
#: staves for it.  Without this every symphony in the corpus would be reported
#: as an edition-side disagreement, which would say nothing about editions and
#: everything about the vocabulary.  Deliberately a COVERAGE relation, not an
#: expansion: a section is satisfied by any of its members, and never asserts
#: that all of them are present.
SECTION_MEMBERS = {
    "Strings": {"Violin", "Viola", "Cello", "Contrabass", "Bass"},
    "Continuo": {"Cello", "Contrabass", "Harpsichord", "Organ", "Bassoon"},
    "Winds": {"Flute", "Piccolo", "Oboe", "English horn", "Clarinet",
              "Bass clarinet", "Bassoon", "Contrabassoon"},
    "Brass": {"Horn", "Trumpet", "Trombone", "Tuba", "Cornet"},
}


# ---------------------------------------------------------------------------
# what kind of document this is
# ---------------------------------------------------------------------------


def classify_score_type(entry: dict) -> dict:
    """full score / reduction / arrangement …, with the string that decided it.

    ⚠️ **IMSLP provenance does not carry this for every file.**  The two
    non-full-scores in this store are ``source: local`` with no
    ``file_description`` at all — their only evidence is the filename and the
    variant slug somebody chose.  So every field that could say is read, the
    winning pattern's own match is recorded, and a document with no evidence
    gets ``unknown`` rather than a default of ``full_score``.
    """
    raw = entry.get("raw") or {}
    fields = {
        "file_description": raw.get("file_description") or "",
        "misc_notes": raw.get("misc_notes") or "",
        "variant": entry.get("variant") or "",
        "original_filename": entry.get("original_filename") or "",
        "notes": entry.get("notes") or "",
    }
    for kind, pattern in SCORE_TYPE_PATTERNS:
        for name, value in fields.items():
            m = re.search(pattern, value, re.I)
            if m:
                return {"score_type": kind, "score_type_field": name,
                        "score_type_match": m.group(0)}
    return {"score_type": "unknown", "score_type_field": "", "score_type_match": ""}


# ---------------------------------------------------------------------------
# reading one edition's roster off its own pages
# ---------------------------------------------------------------------------


def _roster_from_labels(labels, staves) -> dict:
    """Margin labels for ONE page -> the roster of its best SYSTEM.

    Merging by instrument is what makes ``staves`` meaningful: Brahms prints
    ``1.Viol.`` and ``2.Viol.`` on two staves and the instrument is one, so the
    item says ``Violin, staves 2`` and does not invent two instruments.  The
    printed label's own count (``2 Flöten``) is kept beside it, quoted, never
    added to it.
    """
    by_system: dict[int, list] = {}
    for staff in staves:
        by_system.setdefault(staff.system_index, []).append(staff)
    label_of = {l.staff_index: l for l in labels}

    best_system, best_named = None, -1
    for system_index, sys_staves in sorted(by_system.items()):
        named = sum(1 for s in sys_staves
                    if label_of.get(s.staff_index) and label_of[s.staff_index].instrument)
        if named > best_named:
            best_system, best_named = system_index, named
    sys_staves = sorted(by_system.get(best_system, []), key=lambda s: s.top_y)

    items: list[dict] = []
    by_name: dict[str, dict] = {}
    unparsed: list[dict] = []
    unlabeled = 0
    for staff in sys_staves:
        label = label_of.get(staff.staff_index)
        if label is None or not (label.text or "").strip():
            unlabeled += 1
            continue
        if label.instrument is None:
            unparsed.append({"staff_index": staff.staff_index, "text": label.text})
            continue
        count, _name, _mod = work_tier._split_count(label.text.strip())
        name = label.instrument.name
        item = by_name.get(name)
        if item is None:
            item = {"kind": "instrument", "instrument": name,
                    "family": label.instrument.family, "staves": 0,
                    "texts": [], "staff_indices": [],
                    "lexicon_confidence": label.confidence}
            by_name[name] = item
            items.append(item)
        item["staves"] += 1
        item["texts"].append(label.text)
        item["staff_indices"].append(staff.staff_index)
        if count is not None:
            # A QUOTATION of what the label claims, per staff.  Not summed into
            # ``staves`` and not summed across staves: "2 Flöten" twice is two
            # staves each claiming two, which is a fact about the printing.
            item.setdefault("count_printed", []).append(count)
    n = len(sys_staves)
    named = sum(i["staves"] for i in items)
    return {
        "roster": items,
        "unparsed": unparsed,
        "unlabeled_staves": unlabeled,
        "system_index": best_system,
        "system_staves": n,
        "named_staves": named,
        "yield": round(named / n, 4) if n else None,
    }


def read_page_roster(pdf_path: Path, page_index: int, *, dpi: int = DEFAULT_DPI) -> dict:
    """One page -> its roster, plus the raw label strings that produced it.

    Imports are function-local and read-only: ``tools.omr`` is owned by the
    staff-identity workstream and is mid-build, so this module depends on its
    public reading surface and on nothing else.
    """
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr import staff_labels_surya as surya

    pws = detect_staves(render_page(pdf_path, page_index, dpi=dpi))
    if len(pws.staves) < MIN_STAVES:
        return {"page_index": page_index, "staves": len(pws.staves),
                "reason": "too few staves", "roster": [], "yield": 0.0}
    labels = surya.read_staff_labels_surya(pws)
    out = _roster_from_labels(labels, pws.staves)
    out["page_index"] = page_index
    out["staves"] = len(pws.staves)
    # The verbatim OCR strings are the evidence; everything above is derived
    # from them, and the work tier already paid for storing raw (its parser
    # improved twice after a 25-minute backfill at no further cost).
    out["labels_raw"] = [{"staff_index": l.staff_index, "text": l.text,
                          "instrument": l.instrument.name if l.instrument else None,
                          "confidence": l.confidence} for l in labels]
    return out


def acquire(entry: dict, *, hint_page: int | None = None, dpi: int = DEFAULT_DPI,
            pages: tuple[int, ...] = PROBE_PAGES) -> dict:
    """Read one edition's roster.  Returns a fact, acquired or honestly not."""
    pdf = library_root() / entry["path"]
    order = ([hint_page] if hint_page is not None else []) + \
            [p for p in pages if p != hint_page]
    n_pages = entry.get("pages") or 0
    tried: list[dict] = []
    best: dict | None = None
    started = time.time()
    for page_index in order:
        if n_pages and page_index >= n_pages:
            continue
        try:
            read = read_page_roster(pdf, page_index, dpi=dpi)
        except Exception as exc:  # noqa: BLE001 - one bad page must not kill a 30-minute run
            tried.append({"page": page_index, "error": repr(exc)[:160]})
            continue
        tried.append({"page": page_index, "staves": read.get("staves", 0),
                      "named": read.get("named_staves", 0),
                      "yield": read.get("yield") or 0.0})
        if best is None or (read.get("yield") or 0.0) > (best.get("yield") or 0.0):
            best = read
        if (read.get("yield") or 0.0) >= HIT_YIELD:
            break
    return build_fact(entry, best, tried, dpi=dpi,
                      seconds=round(time.time() - started, 1))


# ---------------------------------------------------------------------------
# the fact
# ---------------------------------------------------------------------------


def build_fact(entry: dict, read: dict | None, tried: list[dict], *,
               dpi: int = DEFAULT_DPI, seconds: float | None = None,
               source: str = "page") -> dict:
    """A read plus its provenance plus the operational facts that fall out.

    ``quality`` is an EDITION-QUALITY INDEX and nothing else in this project
    holds one: does this edition label its staves, on which page, at what yield,
    over how many pages.  It is free — every field is a by-product of the read
    that had to happen anyway — and it is the thing that says which of 235 PDFs
    a staff-identity layer can serve at all.
    """
    read = read or {}
    acquired = bool(read.get("roster")) and (read.get("yield") or 0.0) >= HIT_YIELD
    fact = {
        "source": source,
        "source_kind": work_tier.SOURCE_KINDS[source],
        "evidence": "instrument labels printed in this edition's own margins, "
                    "read with surya",
        "reader": "surya",
        "fetched": date.today().isoformat(),
        "describes": "edition",
        "note": "the roster of THIS PRINTING.  staves is an observation of this "
                "page; count_printed quotes the label.  Neither is a part count "
                "and neither implies how many staves another page prints.",
        "acquired": acquired,
        "roster": read.get("roster", []) if acquired else [],
        "unparsed": read.get("unparsed", []) if acquired else [],
        "raw": {"labels": read.get("labels_raw", []),
                "page_index": read.get("page_index"),
                "system_index": read.get("system_index")},
        "quality": {
            "acquired": acquired,
            "roster_page": read.get("page_index") if acquired else None,
            "yield": read.get("yield"),
            "system_staves": read.get("system_staves"),
            "named_staves": read.get("named_staves"),
            "unlabeled_staves": read.get("unlabeled_staves"),
            "page_staves": read.get("staves"),
            "pages": entry.get("pages"),
            "pages_tried": tried,
            "dpi": dpi,
            "seconds": seconds,
        },
    }
    fact.update(classify_score_type(entry))
    work_tier.validate_fact(fact)
    return fact


def catalog_editions(catalog: dict) -> dict:
    return catalog.setdefault("editions", {})


def record(catalog: dict, entry: dict, fact: dict) -> str:
    """Put an edition fact on the catalog, keyed on the file's own PATH.

    ⚠️ Not on ``work_id`` — the whole point of this tier is that one work_id
    holds several editions that disagree.  Not on the catalog ENTRY either: the
    entries are rebuilt from the store's sidecars, and a fact written onto one
    would be destroyed by the next ``ingest catalog``.  So this is a top-level
    map beside ``works``, carried forward by the same rebuild, and the entries
    stay byte-identical.

    ``sha256`` rides along so a replaced or re-scanned PDF's stale roster is
    detectable rather than silently wrong about a file it never read.
    """
    work_tier.validate_fact(fact)
    editions = catalog_editions(catalog)
    held = editions.setdefault(entry["path"], {"path": entry["path"]})
    held["work_id"] = entry.get("work_id", "")
    held["sha256"] = entry.get("sha256", "")
    replaced = "instrumentation" in held
    held["instrumentation"] = fact
    return "updated" if replaced else "added"


# ---------------------------------------------------------------------------
# the disagreement — the point of holding two tiers
# ---------------------------------------------------------------------------


def _names(roster: list[dict]) -> tuple[set[str], set[str]]:
    """(instrument names, section names) of a roster from either tier."""
    instruments = {i["instrument"] for i in roster if i.get("kind") == "instrument"}
    sections = {i["section"] for i in roster if i.get("kind") == "section"}
    return instruments, sections


def _covered_by_section(name: str, sections: set[str]) -> bool:
    return any(name in SECTION_MEMBERS.get(s, ()) for s in sections)


def compare_tiers(work_fact: dict | None, edition_fact: dict | None) -> dict:
    """Work roster vs edition roster.  **The verdict is the deliverable.**

    "Work says 12 instruments, edition reads 8" is three different findings
    wearing one shape, and before this nothing in the project could separate
    them:

    ``agrees``              every instrument the edition read is in the work
                            roster, and the work roster is covered.
    ``edition_extra``       the edition prints instruments the work roster does
                            not name.  A candidate editorial variant — and just
                            as often a work-tier LEXICON GAP, since that roster
                            abstains on anything ``tools.omr.instruments`` cannot
                            spell.  ``unparsed`` on the work fact is the tell.
    ``edition_missing``     the work names instruments the page did not.
                            **Split by the read's own yield**: a partial read
                            (``yield < 1``) explains a shortfall by itself and is
                            reported ``read_incomplete``; a COMPLETE read that
                            still lacks them is ``variant_suspected`` and is the
                            escalation worth a human.
    ``arrangement_suspected``  the rosters barely intersect and the edition's is
                            small.  A piano reduction contradicting an
                            orchestral work wholesale is not a failed read; it is
                            the strongest available evidence that this PDF is not
                            a full score, and ``score_type`` usually agrees.
    ``no_edition_roster``   the edition never yielded one.  A fact about the
                            EDITION (or about our reader), not a disagreement.
    ``no_work_roster``      nothing to compare against.

    ⚠️ **A SECTION IS SATISFIED BY ANY MEMBER, NOT EXPANDED INTO ALL OF THEM.**
    A work roster says ``strings`` in one token and the page prints four or five
    staves for it; expanding the token would assert a lineup the page never
    stated, and not relating them at all would report every symphony in the
    corpus as a disagreement.
    """
    if not work_fact or not work_fact.get("roster"):
        return {"verdict": "no_work_roster"}
    if not edition_fact or not edition_fact.get("acquired"):
        return {"verdict": "no_edition_roster",
                "score_type": (edition_fact or {}).get("score_type", "unknown")}

    work_names, work_sections = _names(work_fact["roster"])
    ed_names, _ = _names(edition_fact["roster"])

    extra = sorted(n for n in ed_names - work_names
                   if not _covered_by_section(n, work_sections))
    missing = sorted(work_names - ed_names)
    shared = ed_names & work_names
    union = ed_names | work_names
    jaccard = round(len(shared) / len(union), 4) if union else 0.0
    yld = edition_fact.get("quality", {}).get("yield") or 0.0
    score_type = edition_fact.get("score_type", "unknown")

    if len(ed_names) <= 3 and jaccard <= 0.2 and len(work_names) >= 5:
        verdict = "arrangement_suspected"
    elif extra and missing:
        verdict = "both"
    elif extra:
        verdict = "edition_extra"
    elif missing:
        verdict = "edition_missing"
    else:
        verdict = "agrees"

    out = {
        "verdict": verdict,
        "jaccard": jaccard,
        "edition_extra": extra,
        "edition_missing": missing,
        "shared": sorted(shared),
        "edition_yield": yld,
        "score_type": score_type,
        "work_unparsed": len(work_fact.get("unparsed") or []),
    }
    if missing:
        out["missing_explained_by"] = (
            "read_incomplete" if yld < 1.0 else "variant_suspected")
    return out


def compare_catalog(catalog: dict) -> list[dict]:
    """Every held edition's verdict.  Derived, offline, recomputable."""
    works = catalog.get("works", {})
    rows = []
    for path, held in sorted(catalog.get("editions", {}).items()):
        fact = held.get("instrumentation")
        work_fact = (works.get(held.get("work_id"), {}) or {}).get("instrumentation")
        row = {"path": path, "work_id": held.get("work_id")}
        row.update(compare_tiers(work_fact, fact))
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------


def _hints(path: Path | None) -> dict:
    """``(work_id, publisher[:60], pages) -> hit_page`` from the identity
    workstream's availability sweep, so acquisition costs ONE page per document
    instead of seven.

    ⚠️ It is a HINT and only a hint: the sweep's rows record no path, and two of
    this store's 234 eligible documents share a (work_id, publisher, pages) key
    with a sibling.  An ambiguous or absent hint falls back to the full probe
    order, so a wrong join costs time and never a wrong fact.
    """
    if not path or not path.exists():
        return {}
    loaded = json.loads(path.read_text())
    # Either the sweep's own output, or the compact projection of it committed
    # beside this workstream (four fields per row, 158 kB -> 12 kB, and it does
    # not pretend to be a copy of another branch's measurement).
    rows = loaded.get("rows", loaded) if isinstance(loaded, dict) else loaded
    seen: dict[tuple, int | None] = {}
    for row in rows:
        key = (row.get("work_id"), (row.get("publisher") or "")[:60], row.get("pages"))
        if key in seen:
            seen[key] = None          # ambiguous: no hint rather than a guess
            continue
        seen[key] = row.get("hit_page") if row.get("acquired") else None
    return {k: v for k, v in seen.items() if v is not None}


def eligible_editions(catalog: dict) -> list[dict]:
    root = library_root()
    out = []
    for entry in catalog.get("entries", []):
        if entry.get("kind") != "edition":
            continue
        if (entry.get("pages") or 0) < 8:
            continue
        if not (root / entry["path"]).exists():
            continue
        out.append(entry)
    return out


def acquire_all(*, dry_run: bool, limit: int | None = None, dpi: int = DEFAULT_DPI,
                availability: Path | None = None, refetch: bool = False,
                catalog_path: Path | None = None,
                only_hinted: bool = False) -> dict:
    catalog = load_catalog(catalog_path)
    hints = _hints(availability)
    held = catalog.get("editions", {})
    targets = []
    for entry in eligible_editions(catalog):
        if not refetch and held.get(entry["path"], {}).get("instrumentation"):
            continue
        hint = hints.get((entry.get("work_id"),
                          (entry.get("publisher") or "")[:60], entry.get("pages")))
        if only_hinted and hint is None:
            continue
        targets.append((entry, hint))
    if limit:
        targets = targets[:limit]
    report = {"targets": len(targets), "added": 0, "updated": 0,
              "acquired": 0, "not_acquired": 0, "errors": []}
    started = time.time()
    for i, (entry, hint) in enumerate(targets, 1):
        try:
            fact = acquire(entry, hint_page=hint, dpi=dpi)
        except Exception as exc:  # noqa: BLE001
            report["errors"].append({"path": entry["path"], "error": str(exc)})
            print(f"  !! {entry['path']}: {exc}", file=sys.stderr)
            continue
        report[record(catalog, entry, fact)] += 1
        report["acquired" if fact["acquired"] else "not_acquired"] += 1
        print(f"  [{i}/{len(targets)}] {'ROSTER' if fact['acquired'] else 'none  '} "
              f"p{fact['quality']['roster_page']} "
              f"y={fact['quality']['yield'] or 0:.2f} "
              f"{len(fact['roster']):2d} instr  {fact['score_type']:11s} "
              f"{entry['path'][:64]}", flush=True)
        if not dry_run and i % 10 == 0:
            save_catalog(catalog, catalog_path)     # resumable checkpoint
    if not dry_run:
        save_catalog(catalog, catalog_path)
    report["seconds"] = round(time.time() - started, 1)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--acquire", action="store_true",
                    help="read every held edition's roster off its own pages")
    ap.add_argument("--compare", action="store_true",
                    help="classify work-tier vs edition-tier disagreement (offline)")
    ap.add_argument("--path", help="read one edition by its catalog path")
    ap.add_argument("--availability", type=Path,
                    help="roster-availability.json from the identity sweep, "
                         "used only to hint which page to read first")
    ap.add_argument("--only-hinted", action="store_true",
                    help="skip documents that sweep found no roster for")
    ap.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--refetch", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    args = ap.parse_args()

    if args.path:
        catalog = load_catalog(args.catalog)
        entry = next((e for e in catalog["entries"] if e.get("path") == args.path), None)
        if entry is None:
            print(f"no catalog entry at {args.path}", file=sys.stderr)
            return 2
        print(json.dumps(acquire(entry, dpi=args.dpi), indent=2, ensure_ascii=False))
        return 0
    if args.compare:
        print(json.dumps(compare_catalog(load_catalog(args.catalog)),
                         indent=1, ensure_ascii=False))
        return 0
    if args.acquire:
        report = acquire_all(dry_run=args.dry_run, limit=args.limit, dpi=args.dpi,
                             availability=args.availability, refetch=args.refetch,
                             catalog_path=args.catalog,
                             only_hinted=args.only_hinted)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1 if report["errors"] else 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
