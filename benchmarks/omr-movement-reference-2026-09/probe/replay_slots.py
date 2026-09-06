"""Replay the SLOT ASSIGNMENT of a whole document, without transcribing it.

`slots.assign_slots` is a pure function of (staves, margin labels). Both are
cheap: staff detection is ~0.8 s a page and the margin ladder ~1-2 s with the
Surya server resident, against ~50 s a page for a full transcription. So the
mechanism under test can be run over 88 pages in minutes, and both arms share
one detection pass, which also removes detector jitter from the comparison.

⚠️ **WHAT THIS DOES AND DOES NOT MODEL.** It reproduces exactly the identity
that comes from the REFERENCE's own labels — `instrument_source: "label"` in a
real run — which is where the bug lives: on the whole-work run every one of
page 23's three spurious trombones is `src=label`, i.e. the name of the slot the
staff was aligned to. It does NOT model the score-order prior or the roster
fill, which need clefs from a transcription. So its counts are over
slot-label-sourced identity only, and it is VALIDATED against the full run
before being believed (`--validate`), not trusted on its face.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr import assist as assist_mod                      # noqa: E402
from tools.omr.contextual import _instrument_by_slot, _labels_for_page  # noqa: E402
from tools.omr.preprocessing import render_page                 # noqa: E402
from tools.omr.slots import assign_slots, labels_by_staff       # noqa: E402
from tools.omr.staff_detector import detect_staves              # noqa: E402

FINALE_ONLY = {"Piccolo", "Contrabassoon", "Trombone"}
FINALE_FIRST_PAGE = 44


def read(pdf: Path, pages, dpi: int):
    staved, labels = [], []
    budget = [0]
    tiers = [0, 0, 0, 0, 0]
    a = assist_mod.Assist("none")     # free readers only — no paid rung
    for i in pages:
        pws = detect_staves(render_page(pdf, i, dpi=dpi))
        staved.append(pws)
        read_labels = _labels_for_page(pws, pdf, i, assist=a, budget=budget,
                                       tiers=tiers)
        labels.append(read_labels)
        print(f"  page {i}: {len(pws.staves)} staves, "
              f"{sum(1 for l in read_labels if l.matched)} labels",
              file=sys.stderr)
    return staved, labels


def arm(staved, labels, page_indices, flag: str):
    os.environ["OMR_MOVEMENT_REFERENCE"] = flag
    for pws in staved:
        for st in pws.staves:
            st.slot_index = -1
    reference = assign_slots(staved, [labels_by_staff(l) for l in labels])
    by_slot = _instrument_by_slot(reference)
    rows = []
    for page_index, pws in zip(page_indices, staved):
        for st in pws.staves:
            inst = by_slot.get(st.slot_index)
            rows.append((page_index, st.system_index, st.staff_index,
                         inst.name if inst else None))
    return reference, rows


def impossible(rows):
    before = [r for r in rows if r[0] < FINALE_FIRST_PAGE]
    bad = [r for r in before if r[3] in FINALE_ONLY]
    return before, bad


def report(tag, reference, rows):
    before, bad = impossible(rows)
    print(f"\n=== {tag} ===")
    print(f"  reference slots  : {len(reference)}  "
          f"[{', '.join(str(s.instrument) for s in reference)}]")
    print(f"  staff records    : {len(rows)}  (before the finale: {len(before)})")
    print(f"  IMPOSSIBLE       : {len(bad)}  "
          f"({len(bad)/max(1,len(before)):.4f})")
    for k, v in collections.Counter(r[3] for r in bad).most_common():
        print(f"      {v:4d}  {k}")
    print(f"  on pages         : {sorted({r[0] for r in bad})}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="0-87")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pages = []
    for part in args.pages.split(","):
        lo, hi = (part.split("-") + [None])[:2]
        pages += list(range(int(lo), int(hi) + 1)) if hi else [int(lo)]
    pages = sorted(set(pages))
    pdf = Path(args.pdf)

    print(f"reading {len(pages)} pages of {pdf.name} …", file=sys.stderr)
    staved, labels = read(pdf, pages, args.dpi)

    ref_off, rows_off = arm(staved, labels, pages, "0")
    ref_on, rows_on = arm(staved, labels, pages, "1")
    print("INPUT ASSERTION: the two arms share ONE detection pass, so any "
          "difference is the flag and nothing else")
    bad_off = report("flag OFF (document-wide reference)", ref_off, rows_off)
    bad_on = report("flag ON (movement-local reference)", ref_on, rows_on)

    changed = [(k, v) for k, v in zip(rows_off, rows_on) if k[3] != v[3]]
    print(f"\nchanged staff records: {len(changed)}")
    kinds = collections.Counter((a[3], b[3]) for a, b in changed)
    for (x, y), n in kinds.most_common(20):
        print(f"  {n:5d}  {str(x):16s} -> {y}")
    print(f"\nIMPOSSIBLE: {len(bad_off)} -> {len(bad_on)}")

    if args.out:
        json.dump({"pages": pages,
                   "reference_off": [s.instrument for s in ref_off],
                   "reference_on": [s.instrument for s in ref_on],
                   "rows_off": rows_off, "rows_on": rows_on},
                  open(args.out, "w"))
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
