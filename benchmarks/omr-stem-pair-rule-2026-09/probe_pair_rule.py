"""HYPOTHESIS B: is `_drop_paired_strokes` eating GENUINE stems on this plate?

Sean, 2026-09-17: *"...or the sharps and flats issue"*.

`line_detection._drop_paired_strokes` DELETES both members of any pair of
vertical strokes whose centres are within `accidental_pair_gap_lines` (0.9)
staff spaces and which overlap vertically by >= 0.6 of the shorter. It exists
because a sharp and a natural are each two parallel verticals. Its own
justification, `c2d640eb`:

    "A stem is single. Two noteheads a second apart share one stem rather than
     standing side by side, and successive notes are set further apart than an
     accidental's own strokes."

⚠️ THAT PREMISE IS WHAT THIS ARM TESTS, and its truth set cannot:
`benchmarks/omr-phase4-lines/hand-labeled-stems.json` is 15 hand-counted cells
on Bolero, Mahler 5, WTC and La Mer -- **not one of them is this Litolff
Beethoven 5 plate**, where the 793 stemless heads were measured. The rule has
never been validated on the document whose misses we are explaining.

THE ARM: re-run `detect_stems` over the same cells with the rule ON (shipped)
and OFF, and join what OFF recovers to the record's own head boxes with the
SAME attachment test the adjudicator uses (`_boxes_overlap`). A recovered
stroke that lands on a head currently abstaining `no_stem` is the rule's cost;
one that lands on a head that already has a stem, pointing the other way, is
its benefit.

⚠️ THIS IS A GATHER-STAGE ARM, so it is NOT a re-adjudication -- it reports
what the ADJUDICATOR WOULD SEE, not what the file would say. No export is
claimed.

CONTROLS, each able to fail:
  * STRUCTURAL -- the ON arm must reproduce the committed record's own
    `Q.STEM` rows cell for cell. If phase 1 cuts different cells, or the dpi
    differs, every number here is about a different page. (dpi 600 was
    confirmed against `staff/1/0/0`'s recorded `staff_lines` to the pixel.)
  * POSITIVE -- the OFF arm must differ from the ON arm. A harness that
    silently passed the same flag twice would report a clean, believable zero.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.line_detection import detect_stems                            # noqa: E402
from tools.omr.staged import record as R                                     # noqa: E402
from tools.omr.staged.gather import _system_local                            # noqa: E402
from tools.omr.staged.pipeline import prepare_pages                          # noqa: E402
from tools.omr.staged.adjudicators.rhythm import (                           # noqa: E402
    _boxes_overlap, _xywh_head, _Shim)
from tools.omr import transcribe as _legacy_stems                            # noqa: E402
from tools.omr.staged.record import Kind, Subject                            # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
       "symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")


def cell_of(k):
    return Subject.from_key(k).at(Kind.CELL).to_key()


def boxes(dets):
    return [(float(d.x_canonical), float(d.y_canonical),
             float(d.width_canonical), float(d.height_canonical)) for d in dets]


def direction(stem, heads):
    """The shipped `_project`, restated over plain boxes."""
    group = [_Shim(*h) for h in heads if _boxes_overlap(h, stem)]
    if not group:
        return None
    return _legacy_stems._stem_direction(_Shim(*stem), group)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--pdf", default=PDF)
    ap.add_argument("--pages", default="1,2,3,4")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--json", default=str(HERE / "out" / "pair-rule.json"))
    a = ap.parse_args()
    pages = [int(t) for t in a.pages.split(",")]

    # ── the two arms, over one rasterisation ──────────────────────────────
    t0 = time.time()
    prepared = prepare_pages(a.pdf, pages, dpi=a.dpi)
    print(f"== phase 1: {len(prepared)} pages in {time.time() - t0:.1f}s")

    on_of, off_of = {}, {}
    n_cells = 0
    for pws, cells in prepared:
        local = _system_local(pws.staves)
        for c in cells:
            key = local.get(c.staff_index)
            if key is None:
                continue
            sub = R.cell(c.page_index, key[0], key[1], c.measure_index).to_key()
            on_of[sub] = boxes(detect_stems(c))
            off_of[sub] = boxes(detect_stems(c, drop_accidental_pairs=False))
            n_cells += 1
    n_on = sum(len(v) for v in on_of.values())
    n_off = sum(len(v) for v in off_of.values())
    print(f"== REACH")
    print(f"   cells cut                       {n_cells:6d}")
    print(f"   stems, rule ON  (shipped)       {n_on:6d}")
    print(f"   stems, rule OFF                 {n_off:6d}")
    print(f"   strokes the rule DROPS          {n_off - n_on:6d}")
    if n_cells == 0:
        print("DEAD: no cells.")
        return 2
    if n_off == n_on:
        print("DEAD: POSITIVE CONTROL FAILED -- the two arms are identical, "
              "so the flag is not reaching `detect_stems`.")
        return 2

    # ── STRUCTURAL CONTROL: the ON arm against the committed record ────────
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc
    rec_stems = collections.defaultdict(list)
    box_of = {}
    heads_in = collections.defaultdict(list)
    space_of = {}
    for o in rec["observations"]:
        q = o["quantity"]
        if q == "stem":
            v = o.get("value")
            if isinstance(v, (list, tuple)) and len(v) == 4:
                rec_stems[cell_of(o["subject"])].append(
                    tuple(float(t) for t in v))
        elif q == "glyph_box":
            b = _xywh_head(o.get("value"))
            if b is not None:
                box_of[o["subject"]] = b
        elif q == "cell_staff_space":
            try:
                space_of[cell_of(o["subject"])] = float(o["value"])
            except (TypeError, ValueError):
                pass
    for o in rec["observations"]:
        if o["quantity"] == "notehead_class":
            b = box_of.get(o["subject"])
            if b is not None:
                heads_in[cell_of(o["subject"])].append((o["subject"], b))

    rec_total = sum(len(v) for v in rec_stems.values())
    shared = set(on_of) & set(rec_stems)
    exact = sum(1 for c in shared
                if sorted(on_of[c]) == sorted(rec_stems[c]))
    print(f"\n== STRUCTURAL CONTROL -- the ON arm vs the committed record")
    print(f"   record cells carrying stem ink  {len(rec_stems):6d}")
    print(f"   record stem rows                {rec_total:6d}")
    print(f"   cell subjects in BOTH           {len(shared):6d}")
    print(f"   cells where the box sets MATCH EXACTLY  {exact:6d}  "
          f"({100.0 * exact / max(1, len(shared)):.1f}%)")
    if exact < 0.95 * len(shared):
        print("   ⚠️ the arm is not reproducing the record's gather -- read "
              "every number below as being about a DIFFERENT cutting.")

    # ── what the recovered strokes would do to the adjudicator ────────────
    verdicts = [v for v in rec["verdicts"] if v["quantity"] == "stem_direction"]
    no_stem = {v["subject"] for v in verdicts if v["reason"] == "no_stem"}
    decided = {v["subject"]: v.get("value") for v in verdicts
               if v["outcome"] == "decided"}

    rescued, conflicted, agreed, landed_nowhere = set(), set(), set(), 0
    recovered_total = 0
    per_cell_recovered = collections.Counter()
    for c, off in off_of.items():
        on = on_of.get(c, [])
        rem = list(on)
        rec_only = []
        for b in off:
            if b in rem:
                rem.remove(b)
            else:
                rec_only.append(b)
        if not rec_only:
            continue
        recovered_total += len(rec_only)
        per_cell_recovered[c] = len(rec_only)
        hs = heads_in.get(c, [])
        hboxes = [b for _, b in hs]
        for s in rec_only:
            hit = [(sub, b) for sub, b in hs if _boxes_overlap(b, s)]
            if not hit:
                landed_nowhere += 1
                continue
            d = direction(s, hboxes)
            for sub, _b in hit:
                if sub in no_stem:
                    rescued.add(sub)
                elif sub in decided:
                    if d is not None and d != decided[sub]:
                        conflicted.add(sub)
                    else:
                        agreed.add(sub)

    print(f"\n== WHAT THE RULE COSTS, joined to the record's own heads")
    print(f"   strokes recovered with the rule off      {recovered_total:6d}")
    print(f"   ... landing on NO notehead               {landed_nowhere:6d}"
          f"  ({100.0 * landed_nowhere / max(1, recovered_total):5.1f}%)")
    print(f"   heads that would stop abstaining no_stem {len(rescued):6d}"
          f"  ({100.0 * len(rescued) / max(1, len(no_stem)):5.1f}% of "
          f"{len(no_stem)})")
    print(f"   already-decided heads gaining an AGREEING stem  "
          f"{len(agreed):6d}")
    print(f"   already-decided heads gaining a CONTRADICTING stem "
          f"(-> `stems_disagree`)  {len(conflicted):6d}")

    out = {"reach": {"cells": n_cells, "stems_on": n_on, "stems_off": n_off,
                     "dropped_by_the_rule": n_off - n_on},
           "structural_control": {"record_cells_with_stems": len(rec_stems),
                                  "record_stem_rows": rec_total,
                                  "cells_in_both": len(shared),
                                  "exact_box_set_match": exact},
           "recovered_total": recovered_total,
           "recovered_landing_on_no_notehead": landed_nowhere,
           "heads_rescued_from_no_stem": len(rescued),
           "decided_heads_gaining_agreeing_stem": len(agreed),
           "decided_heads_gaining_contradicting_stem": len(conflicted),
           "no_stem_population": len(no_stem),
           "decided_population": len(decided)}
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
