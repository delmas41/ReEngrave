#!/usr/bin/env python3
"""How far a roster-constrained reading of margin labels REACHES, and on what.

*Reach before accuracy.* This project has repeatedly found a documented lever
unreachable — the written-range veto has never fired on a scan, `clef_correction`
fills 8.6% of staves — so the first question about a new one is how many labels
it can even touch.

Three corpora, per the standing rule
(`benchmarks/omr-lexicon-2026-09/FINDINGS.md`, "Validation — three corpora"):

    readers   every raw margin string thirteen editions actually produce
              (`benchmarks/omr-lexicon-2026-09/labels.json`, 1422 labels)
    reference every distinct part name in the 1745 reference encodings
              (`benchmarks/omr-lexicon-2026-09/part-names.json`, 1271 strings)
    fixtures  the engraved benchmark's own truncated labels
              (`benchmarks/omr-margin-window-truncation-2026-09/truncation.json`)

Each label is classified under the current lexicon and under the roster rule:

    unchanged   the roster changes nothing
    recovered   the lexicon abstained; exactly one roster instrument owns a tail
    vetoed      the lexicon resolved into a family the work does not have

    python3 benchmarks/omr-roster-constrained-labels-2026-09/probe_roster_reach.py
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import work_roster as wr                      # noqa: E402
from tools.omr import instruments                            # noqa: E402

# ⚠️ `instruments.lookup` costs ~0.6 s on a string that matches NOTHING — it
# walks all ~400 aliases twice, compiling a fresh regex per alias and thrashing
# `re`'s 512-entry cache. That is pre-existing and out of scope here, but it is
# the whole runtime of this probe (2,800 labels, ~300 of them unmatched), so the
# corpora are scored through a memo. Same answers, same code, one call per
# DISTINCT string.
_lookup_memo: dict[str, object] = {}


def lookup(text: str):
    if text not in _lookup_memo:
        _lookup_memo[text] = instruments.lookup(text)
    return _lookup_memo[text]

LEXICON = ROOT / "benchmarks" / "omr-lexicon-2026-09"
TRUNCATION = (ROOT / "benchmarks" / "omr-margin-window-truncation-2026-09"
              / "truncation.json")

#: The eleven engraved benchmark works, by the fixture stem `orchestral_eval`
#: writes, mapped to the score library's `work_id`. Written out rather than
#: derived: the dossier ids (`mozart-sym40-mvt1`) and the library ids
#: (`mozart--symphony-40`) are different keys and CLAUDE.md records a session
#: lost to conflating them.
FIXTURE_WORKS = {
    "beethoven-sym3-mvt1": "beethoven--symphony-3",
    "beethoven-sym5-mvt1": "beethoven--symphony-5",
    "brahms-sym1-mvt1": "brahms--symphony-1",
    "brahms-sym4-mvt1": "brahms--symphony-4",
    "bruckner-sym5-mvt1": "bruckner--symphony-5",
    "dvorak-sym9-mvt4": "dvorak--symphony-9",
    "mahler-sym5-mvt1": "mahler--symphony-5",
    "mozart-sym40-mvt1": "mozart--symphony-40",
    "mozart-sym41-mvt1": "mozart--symphony-41",
    "tchaikovsky-sym4-mvt2": "tchaikovsky--symphony-4",
    "tchaikovsky-sym6-mvt2": "tchaikovsky--symphony-6",
}


def reader_corpus() -> list[dict]:
    """The 1422 real margin strings, each tagged with its work."""
    labels = json.loads((LEXICON / "labels.json").read_text())
    pages = json.loads((LEXICON / "pages.json").read_text())
    work_of = {p["id"]: wr.work_id_for_pdf(p["pdf"]) for p in pages}
    out = []
    for rec in labels:
        out.append({"corpus": "readers", "source": rec["source"],
                    "text": rec["text"], "work_id": work_of.get(rec["source"])})
    return out


def reference_corpus() -> list[dict]:
    """Every distinct reference part name — the widest vocabulary, no work.

    ⚠️ These strings carry no work, so the roster layer CANNOT fire on them by
    construction. That is the point: it is the no-regression corpus, and a
    non-zero count here would be a bug in the wiring, not a result.
    """
    names = json.loads((LEXICON / "part-names.json").read_text())
    return [{"corpus": "reference", "source": "part-names", "text": t,
             "work_id": None} for t in names]


def fixture_corpus() -> list[dict]:
    """Every margin label the eleven engraved fixtures hand the lexicon.

    From `read_fixture_labels.py`, NOT from the truncation probe's span dump:
    that one joins spans without spaces and the production reader joins them
    with, and a token rule sees two different strings.
    """
    path = BENCH / "fixture-labels.json"
    if not path.is_file():
        return []
    out = []
    for row in json.loads(path.read_text()):
        wid = FIXTURE_WORKS.get(row["work"])
        for lab in row["labels"]:
            out.append({"corpus": "fixtures", "source": row["work"],
                        "text": lab["text"], "work_id": wid})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=BENCH / "reach.json")
    ap.add_argument("--detail", action="store_true")
    args = ap.parse_args(argv)

    records = reader_corpus() + reference_corpus() + fixture_corpus()
    rosters: dict[str, wr.WorkRoster | None] = {}
    counts: dict[tuple[str, str], int] = collections.Counter()
    fires: list[dict] = []
    no_roster: collections.Counter = collections.Counter()

    for rec in records:
        wid = rec["work_id"]
        if wid not in rosters:
            rosters[wid] = wr.work_roster(wid) if wid else None
        roster = rosters[wid]
        if wid and roster is None:
            no_roster[wid] += 1
        before = lookup(rec["text"])
        d = wr.decide(rec["text"], roster, hit=before)
        counts[(rec["corpus"], d.kind)] += 1
        counts[(rec["corpus"], "labels")] += 1
        if before is None:
            counts[(rec["corpus"], "unresolved_before")] += 1
        if roster is not None:
            counts[(rec["corpus"], "has_roster")] += 1
        if d.kind != "unchanged":
            fires.append({"corpus": rec["corpus"], "source": rec["source"],
                          "work_id": wid, "text": rec["text"], "kind": d.kind,
                          "before": (before.instrument.name if before else None),
                          "after": (d.match.instrument.name if d.match else None),
                          "alias": (d.match.alias if d.match else ""),
                          "reason": d.reason})

    print(f"{'corpus':12} {'labels':>7} {'roster':>7} {'unres':>7} "
          f"{'recovered':>10} {'disambig':>9} {'vetoed':>7}")
    for corpus in ("readers", "reference", "fixtures"):
        if not counts[(corpus, "labels")]:
            continue
        print(f"{corpus:12} {counts[(corpus,'labels')]:7d} "
              f"{counts[(corpus,'has_roster')]:7d} "
              f"{counts[(corpus,'unresolved_before')]:7d} "
              f"{counts[(corpus,'recovered')]:10d} "
              f"{counts[(corpus,'disambiguated')]:9d} "
              f"{counts[(corpus,'vetoed')]:7d}")

    if no_roster:
        print("\nworks named by a corpus but absent from the catalog `works` tier:")
        for wid, n in no_roster.most_common():
            print(f"  {n:5d}  {wid}")

    print(f"\n{len(fires)} firings")
    by = collections.Counter((f["kind"], f["text"], f["before"], f["after"],
                              f["source"]) for f in fires)
    for (kind, text, b, a, src), n in by.most_common():
        print(f"  {n:3d}x {kind:9} {text!r:34} {str(b):>14} -> {str(a):<14} {src}")

    args.out.write_text(json.dumps(
        {"counts": {f"{k[0]}.{k[1]}": v for k, v in counts.items()},
         "firings": fires}, indent=1) + "\n")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
