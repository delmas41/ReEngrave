#!/usr/bin/env python3
"""How often do the two instrumentation tiers disagree, and about WHAT?

Offline and recomputable — it reads the committed catalog and nothing else, so
it can be re-run after the parser or the comparison rule changes without
touching IMSLP or a single PDF.

    python3 benchmarks/omr-edition-instrumentation-2026-09/probe_tier_disagreement.py
    python3 ... --verdict edition_missing --limit 40     # the rows, for a human

⚠️ **THE HEADLINE IS THE MIX, NOT THE RATE.**  "Work says 12, edition reads 8"
is three findings wearing one shape — a genuine editorial variant, a
condensation, or a failed read — and a single disagreement percentage says which
of them nothing at all.  The report therefore splits every disagreement by the
read's own yield and by the edition's ``score_type``, and prints the rows so
they can be adjudicated by hand.  This script produces the INPUT to that
adjudication, never its conclusion; the conclusion of the first one is below.

── ACQUISITION, 2026-09-05 ───────────────────────────────────────────────────

Every held edition of >= 8 pages present on disk, one page per document where
the staff-identity sweep already said which page carries the roster::

    targets 234   acquired 189 (0.808)   not acquired 45   errors 0   68 min

⚠️ 0.808 is NOT comparable to that sweep's 0.735 — definitional, not an
improvement: its yield is named / EVERY STAFF ON THE PAGE, this one's is
named / THE STAVES OF THE SYSTEM the roster is taken from, and on a two-system
page those differ by a factor of two.

Edition-quality index (nothing else in the project holds one, and every field is
free — a by-product of the read that had to happen anyway): labels its staves
189/234; yield 1.00 x44, 0.75-0.99 x85, 0.50-0.74 x60; ⭑ **18 documents give up
their roster only on a page past p.2** — "page 1" is the wrong unit, confirmed
independently after the identity sweep found the same (14 of its 172).

── THE MIX, WHICH IS THE DELIVERABLE, NOT THE RATE ───────────────────────────

181 of the 234 are comparable (both tiers present).  A single "disagreement
rate" would be 0.79 and would mean nothing.  Hand-adjudicated::

    38  0.210  agrees
    80  0.442  read incomplete — the page read is partial
    38  0.210  LEXICON: a string staff read as a SINGER
     9  0.050  edition_extra, other
     8  0.044  shortfall on a COMPLETE read (all 9 opened by hand)
     5  0.028  work-tier gap: a choral work whose singers the page reads
     3  0.017  doubling
     0  0.000  ⭑ GENUINE EDITORIAL VARIANT

⚠️⚠️ **ZERO EDITORIAL VARIANTS, AND THAT IS A REAL ANSWER.**
``variant_suspected`` — a shortfall surviving a COMPLETE read, the bucket that
is supposed to mean a publisher changed the orchestration — has 9 rows and every
one was opened with ``show_disagreement.py``.  None is a variant:

    Beethoven 5 (Litolff)   Trombone            enters in the FINALE; we read mvt 1
    Haydn 100 "Military"    Clarinet, Percussion  Turkish percussion enters in mvt 2
    Haydn 88                Timpani, Trumpet    they play in mvts 3-4
    Haydn 45 "Farewell"     Bassoon             roster says "[bassoon]" — BRACKETED
                                                = optional, played off the bass line
    Mozart 25               Bassoon             doubles the bass, no staff of its own
    Mozart K525            Contrabass          page prints "Violoncello e
                                                Contrabasso" — ONE staff, two parts
    Rossini "Barbiere"      (cast list)         the work "roster" is the opera's
                                                dramatis personae

⚠️⚠️ **MOVEMENT SCOPE IS A THIRD SYSTEMATIC UNDER-REPORT and it was in nobody's
taxonomy.**  A work roster covers the WHOLE WORK; a page shows ONE MOVEMENT's
system.  Three of the nine are exactly that, and it is the same shape as
doubling — driven by WHICH PAGE WE READ, not by the printing.  Not implemented,
because this tier does not know which movement a page belongs to; the
discriminator would join ``quality.roster_page`` to a movement boundary.  Until
it exists, a ``variant_suspected`` row means "worth a human", never "a variant".

⚠️ **THE LARGEST SINGLE FAMILY IS ONE WORD IN THE LEXICON.**  ``Basso.`` ->
Bass VOICE, every orchestral score's bottom string staff: **35 rows carry it and
on 30 it is the only disagreement there is.**  The French ``ALTO.`` — the VIOLA,
printed between VIOLONS and VIOLONCELLES — is the same fault (Bizet, Lalo,
Chaminade), as is Alto/Tenore on trombone staves, which CLAUDE.md already
records for a different reader.  Correcting that one word moves the buckets
materially::

    now     edition_missing 73 · both 38 · agrees 38 · edition_extra 29
    fixed   edition_missing 85 · agrees 56 · both 25 · edition_extra 12

``tools/omr/instruments.py`` is READ-ONLY for this workstream, so the gap is
RECORDED, NOT MADE — the same discipline the work-tier capture used for its
missing ``cornet``.  The positional evidence a fix would need is already stored:
``raw.labels`` keeps every staff's text and index, and a Basso staff sits BELOW
the cellos while a French Alto sits BETWEEN the violins and the cellos.

── WHAT THIS CANNOT SEE ──────────────────────────────────────────────────────

⚠️ **No arrangements to test against.**  2 of 235 held editions are not full
scores and both are ``source: local``; ``arrangement_suspected`` fired ZERO
times and is exercised by unit tests only.  A corpus that cannot express the
case cannot price the rule.
⚠️ One system, one page, one movement — everything here is a property of the
system we happened to read, and both systematic under-reports follow from that.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from tools.library import edition_instrumentation as ed  # noqa: E402
from tools.library.score_library import CATALOG_PATH, load_catalog  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    ap.add_argument("--verdict", help="print the rows with this verdict")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", type=Path, default=HERE / "tier-disagreement.json")
    args = ap.parse_args()

    catalog = load_catalog(args.catalog)
    editions = catalog.get("editions", {})
    rows = ed.compare_catalog(catalog)
    n = len(rows)
    if not n:
        print("no edition facts in the catalog — run "
              "`python3 -m tools.library.edition_instrumentation --acquire` first")
        return 2

    print(f"{'='*74}\nWORK TIER vs EDITION TIER — {n} held editions\n{'='*74}")

    verdicts = Counter(r["verdict"] for r in rows)
    for verdict, count in verdicts.most_common():
        print(f"  {verdict:22s} {count:4d}  {count/n:6.3f}  {'#'*int(46*count/n)}")

    comparable = [r for r in rows
                  if r["verdict"] not in ("no_work_roster", "no_edition_roster")]
    print(f"\n  comparable (both tiers present)   {len(comparable):4d}"
          f"  ({len(comparable)/n:.3f})")
    if comparable:
        agree = sum(1 for r in comparable if r["verdict"] == "agrees")
        print(f"  of those, AGREE                   {agree:4d}"
              f"  ({agree/len(comparable):.3f})")

    print("\n  ⚠️ SHORTFALLS SPLIT BY THE READ'S OWN YIELD — this is the split "
          "that\n     separates 'our reader missed it' from 'this printing may "
          "not have it':")
    split = Counter(r.get("missing_explained_by") for r in comparable
                    if r.get("missing_explained_by"))
    for key, count in split.most_common():
        print(f"    {key:20s} {count:4d}")

    print("\n  BY SCORE TYPE (an arrangement is a KIND of edition, not an error):")
    by_type = defaultdict(Counter)
    for row in rows:
        by_type[editions[row["path"]]["instrumentation"]["score_type"]][
            row["verdict"]] += 1
    for score_type, counter in sorted(by_type.items(),
                                      key=lambda kv: -sum(kv[1].values())):
        total = sum(counter.values())
        print(f"    {score_type:12s} {total:4d}   " +
              "  ".join(f"{v}={c}" for v, c in counter.most_common()))

    print("\n  WHAT THE EDITION NAMES AND THE WORK DOES NOT (top 15) — as much a\n"
          "  work-tier LEXICON GAP as an editorial variant:")
    extra = Counter(name for r in comparable for name in r["edition_extra"])
    for name, count in extra.most_common(15):
        print(f"    {name:22s} {count:4d}")

    print("\n  WHAT THE WORK NAMES AND THE PAGE DOES NOT (top 15):")
    missing = Counter(name for r in comparable for name in r["edition_missing"])
    for name, count in missing.most_common(15):
        print(f"    {name:22s} {count:4d}")

    print("\n  EDITION-QUALITY INDEX (nothing else in the project holds one):")
    q = [editions[r["path"]]["instrumentation"]["quality"] for r in rows]
    got = [x for x in q if x["acquired"]]
    print(f"    labels its staves                 {len(got):4d}/{n}"
          f"  ({len(got)/n:.3f})")
    if got:
        buckets = Counter()
        for x in got:
            y = x["yield"] or 0.0
            buckets["1.00" if y >= 0.999 else "0.75-0.99" if y >= .75
                    else "0.50-0.74"] += 1
        for b in ("1.00", "0.75-0.99", "0.50-0.74"):
            print(f"      yield {b:10s}              {buckets.get(b,0):4d}")
        late = sum(1 for x in got if x["roster_page"] not in (0, 1, 2))
        print(f"    roster only past page 2           {late:4d}"
              f"  — 'page 1' is the wrong unit")

    if args.verdict:
        print(f"\n{'='*74}\nROWS: {args.verdict}\n{'='*74}")
        picked = [r for r in rows if r["verdict"] == args.verdict]
        for row in picked[: args.limit or len(picked)]:
            print(f"\n  {row['work_id']}  ({row['path'].split('/')[-1][:70]})")
            print(f"    jaccard {row.get('jaccard')}  yield "
                  f"{row.get('edition_yield')}  {row.get('score_type')}"
                  f"  {row.get('missing_explained_by','')}")
            if row.get("edition_extra"):
                print(f"    page only: {', '.join(row['edition_extra'])}")
            if row.get("edition_missing"):
                print(f"    work only: {', '.join(row['edition_missing'])}")

    args.out.write_text(json.dumps({"n": n, "verdicts": dict(verdicts),
                                    "rows": rows}, indent=1) + "\n")
    print(f"\n  wrote {args.out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
