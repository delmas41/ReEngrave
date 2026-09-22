#!/usr/bin/env python3
"""A bare transposing KEY is not a name — it is a MODIFIER of one printed elsewhere.

`probe_domain.py` shows the Brahms horn population the 2026-09-21 fact sheet
found is stopped at `no_usable_token`: every token of `'(C)'`, `'(Es)'` and
`'in C \\frac{1}{2}'` is shorter than `work_roster.MIN_KEPT_LETTERS`, so the
roster rule never reaches the suffix test. It is not a truncation and no
threshold makes it one.

**What it IS, and CLAUDE.md already says so** (the lexicon section): *"the
Brahms strings are the two HORN staves and the page prints `Hörner` once
braced across them, so abstaining is right and no lexicon can recover them."*
An engraver names a braced PAIR of like instruments once and distinguishes the
members by their transposing KEY. The second staff of the pair therefore
carries a key and no noun — by design, not by damage.

So this probe measures the class, not a rate:

    BARE KEY   the lexicon abstains, `instruments.parse_in_key` SUCCEEDS, and
               no token survives the roster rule's own two floors

and then prices the two rules that could name such a staff, which have very
different risk and are reported apart:

  (A) SLOT CARRY   some other staff of this document, at this staff's own
                   position, is named. The legacy path already does this
                   (`contextual.py:1527`, one name per SLOT stamped onto every
                   staff of that slot on every page). Needs no convention.
  (B) ADJACENCY    borrow from the neighbouring staff of the braced pair.
                   Cheap, needs no cross-system machinery — and this probe
                   exists to price its hazard, because a bare key standing
                   next to a DIFFERENT transposing instrument captures it.

    python3 benchmarks/omr-roster-truncation-reprice-2026-09/probe_bare_key.py
"""
from __future__ import annotations

import argparse
import collections
import functools
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import instruments                         # noqa: E402
from tools.omr import work_roster as wr                   # noqa: E402

LEXICON = ROOT / "benchmarks" / "omr-lexicon-2026-09"
lookup = functools.lru_cache(maxsize=None)(instruments.lookup)


def is_bare_key(text: str) -> bool:
    """No name, a readable transposing key, nothing the roster rule can use.

    All three conditions matter. Dropping the first would swallow `Hr. (Es)`,
    which already resolves; dropping the second would swallow `'2 V'` and
    `'Gr. C.'`, which are abbreviations with no key in them at all; dropping
    the third would claim labels the roster rule genuinely does reach.
    """
    if lookup(text) is not None:
        return False
    if instruments.parse_in_key(text) is None:
        return False
    known = wr._known_aliases()
    usable = [t for t in wr._tokens(text)
              if len(t) >= wr.MIN_KEPT_LETTERS and t not in known]
    return not usable


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(BENCH / "out" / "bare-key.json"))
    args = ap.parse_args()

    labels = json.loads((LEXICON / "labels.json").read_text())

    for rec in labels:
        rec["_hit"] = lookup(rec["text"])
        rec["_bare"] = is_bare_key(rec["text"])

    bare = [r for r in labels if r["_bare"]]
    print(f"{len(labels)} labels; BARE KEY = {len(bare)} "
          f"({len(bare)/len(labels):.1%}), "
          f"{len({r['text'] for r in bare})} distinct\n")

    per_src = collections.Counter(r["source"] for r in bare)
    print("  by document")
    for src, n in per_src.most_common():
        total = sum(1 for r in labels if r["source"] == src)
        print(f"    {src:30} {n:4d} of {total:4d}")

    print("\n  distinct strings")
    for t, n in collections.Counter(r["text"] for r in bare).most_common():
        print(f"    {n:4d}x {t!r:30} key={instruments.parse_in_key(t)}")

    # ---- (A) slot carry: does the document name a transposing instrument at all?
    print("\n  (A) SLOT CARRY — what the document says elsewhere")
    for src in per_src:
        named = collections.Counter(
            r["_hit"].instrument.name for r in labels
            if r["source"] == src and r["_hit"] is not None
            and r["_hit"].instrument.default_fifths_offset != 0
            or (r["source"] == src and r["_hit"] is not None
                and instruments.parse_in_key(r["text"]) is not None))
        print(f"    {src:30} transposing names read elsewhere: "
              f"{dict(named.most_common(6))}")

    # ---- (B) adjacency hazard, measured rather than asserted
    print("\n  (B) ADJACENCY — the nearest NAMED staff on the same page")
    by_page: dict[tuple, dict[int, dict]] = collections.defaultdict(dict)
    for r in labels:
        by_page[(r["source"], r["page_index"])][r["staff_index"]] = r
    hazard = collections.Counter()
    rows = []
    for r in bare:
        page = by_page[(r["source"], r["page_index"])]
        i = r["staff_index"]
        cand = []
        for d in (-1, 1):
            n = page.get(i + d)
            if n is not None and n["_hit"] is not None:
                cand.append((d, n["text"], n["_hit"].instrument.name))
        names = {c[2] for c in cand}
        if not names:
            verdict = "no named neighbour"
        elif len(names) == 1:
            verdict = f"unanimous -> {names.pop()}"
        else:
            verdict = "SPLIT -> " + " / ".join(
                f"{d:+d}{n}" for d, _, n in cand)
        hazard[verdict.split(" -> ")[0]] += 1
        rows.append({"source": r["source"], "page": r["page_index"],
                     "staff": r["staff_index"], "text": r["text"],
                     "neighbours": cand, "verdict": verdict})
        print(f"    {r['source'][:22]:22} p{r['page_index']:<3} s{i:<3} "
              f"{r['text']!r:26} {verdict}")
    print("\n    " + ", ".join(f"{k}: {v}" for k, v in hazard.most_common()))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(
        {"n_labels": len(labels), "n_bare": len(bare),
         "by_source": dict(per_src), "adjacency": dict(hazard),
         "rows": rows}, indent=1))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
