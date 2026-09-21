"""THE NOTEHEAD GATE, END TO END ON A REAL PLATE — the run §4 of
`benchmarks/omr-stem-pair-rule-2026-09/FINDINGS.md` says has never happened.

That lane measured the gate's SHAPE on the rule's own hand count and left
this: *"The proposed gate has never been run end to end, and
`readjudicate`/`reexport_arm` are structurally blind to it."* They are: the
gate lives in GATHER, so a saved record cannot be re-adjudicated into it.
This arm therefore RE-CUTS the page and runs `detect_stems` twice, on the
SHIPPED code, with nothing but `OMR_STEM_NOTEHEAD_GATE` between the arms.

⚠️⚠️ THE FAITHFULNESS CONTROL COMES FIRST AND IT CAN FAIL. The OFF arm must
reproduce the committed shared record's stem set — 1,920 strokes on Litolff
Beethoven 5 pp.1-4, 2,305 on Breitkopf Brahms 1 pp.0-3 — because that is what
every stem arm in this repo proves before reporting a delta. If it does not,
the two arms are not comparable to anything and the arm exits 2. The count is
NOT hard-coded as a pass condition on its own: `--expect` is optional, and
without it the arm still reports the OFF total so a reader can check it.

⚠️ POSITIVE CONTROL: the two arms must DIFFER. Two identical arms is exactly
what a flag that does not reach the code produces, and it would read as *the
gate is harmless*.

⚠️ THE GATE NEEDS THE DETECTOR, so this is not a pure-CV arm and it is as good
as the weights. Where the detector misses a notehead the gate cannot protect
that stroke — which fails toward the SHIPPED behaviour, never toward a new
one.

Reported APART per document: this thread's two plates behave differently
throughout and pooling them would hide it.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.line_detection import (                                # noqa: E402
    detect_stems, stem_notehead_gate_enabled, STEM_NOTEHEAD_GATE_ENV)
from tools.omr.staged.pipeline import prepare_pages                   # noqa: E402

WEIGHTS = ("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
           "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")

#: The two shared records' own stem totals, from this thread's committed
#: figures. ⚠️ A DEFAULT, not an assertion: `--expect` overrides and omitting
#: the document from this table simply prints the total without checking it.
EXPECTED = {
    "litolff-beethoven5-p1-p4": 1920,
    "breitkopf-brahms1-p0-p3": 2305,
}


def key(d):
    return (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical)


def heads_of(dets):
    return [(float(d.x_canonical), float(d.y_canonical),
             float(d.width_canonical), float(d.height_canonical))
            for d in (dets or [])
            if "notehead" in str(getattr(d, "smufl_name", "")).lower()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True,
                    help="comma list of 0-based PDF page indices")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--weights", default=WEIGHTS)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--expect", type=int, default=None,
                    help="the OFF arm's stem total this document must "
                         "reproduce; defaults to the EXPECTED table")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    if not Path(a.pdf).exists():
        print(f"DEAD: no pdf at {a.pdf}")
        return 2
    if not Path(a.weights).exists():
        print(f"DEAD: no weights at {a.weights}")
        return 2
    # ⚠️ THE ARM MUST NOT INHERIT THE FLAG FROM THE SHELL. It sets the variable
    # per arm below; a value already in the environment would make both arms
    # the same one, which is the hazard CLAUDE.md records twice (`zsh does not
    # word-split env $3`; *three harnesses expressed off by POPPING the
    # variable*). Refuse rather than silently measure two ON arms.
    if STEM_NOTEHEAD_GATE_ENV in os.environ:
        print(f"DEAD: {STEM_NOTEHEAD_GATE_ENV} is already set in the "
              f"environment ({os.environ[STEM_NOTEHEAD_GATE_ENV]!r}); this "
              f"arm sets it itself and will not measure two identical arms.")
        return 2

    pages = [int(p) for p in a.pages.split(",")]
    t0 = time.time()
    # ⚠️ `prepare_pages` returns [(pws, cells)] per PAGE, not a flat cell list.
    cells = [c for _pws, cs in prepare_pages(str(a.pdf), pages, dpi=a.dpi)
             for c in cs]
    print(f"== phase 1: {len(pages)} pages, {len(cells)} cells "
          f"in {time.time() - t0:.1f}s")

    from tools.omr.yolo_detector import YoloDetector
    det = YoloDetector(a.weights)

    n_off = n_on = n_heads = 0
    cells_with_heads = 0
    cells_changed = 0
    rescued = []          # strokes the gate KEEPS that the shipped rule drops
    lost = []             # strokes the shipped rule keeps that the gate drops
    rescued_on_head = 0
    t0 = time.time()
    for i, c in enumerate(cells):
        if i and i % 200 == 0:
            print(f"   ... {i}/{len(cells)} cells, {time.time() - t0:.0f}s")
        heads = heads_of(det.detect(c))
        n_heads += len(heads)
        cells_with_heads += 1 if heads else 0

        # ⚠️ THE FLAG IS SET PER ARM AND THE DEFAULT IS CHECKED, so a flag that
        # does not reach `detect_stems` cannot look like a gate that does
        # nothing.
        os.environ[STEM_NOTEHEAD_GATE_ENV] = "0"
        assert not stem_notehead_gate_enabled()
        off = detect_stems(c, noteheads=heads)
        os.environ[STEM_NOTEHEAD_GATE_ENV] = "1"
        assert stem_notehead_gate_enabled()
        on = detect_stems(c, noteheads=heads)
        del os.environ[STEM_NOTEHEAD_GATE_ENV]

        n_off += len(off)
        n_on += len(on)
        ks_off = {key(d) for d in off}
        ks_on = {key(d) for d in on}
        if ks_off != ks_on:
            cells_changed += 1
        for d in on:
            if key(d) not in ks_off:
                rescued.append(key(d))
                if any(min(d.x_canonical + d.width_canonical, hx + hw)
                       - max(d.x_canonical, hx) > 0
                       and min(d.y_canonical + d.height_canonical, hy + hh)
                       - max(d.y_canonical, hy) > 0
                       for hx, hy, hw, hh in heads):
                    rescued_on_head += 1
        for d in off:
            if key(d) not in ks_on:
                lost.append(key(d))

    print(f"\n== REACH  ({a.tag})")
    print(f"   cells cut                               {len(cells):6d}")
    print(f"   cells holding a detected notehead       {cells_with_heads:6d}")
    print(f"   noteheads detected                      {n_heads:6d}")
    print(f"   stems, gate OFF (shipped)               {n_off:6d}")
    print(f"   stems, gate ON                          {n_on:6d}")
    print(f"   cells whose stem SET changes            {cells_changed:6d}")
    print(f"   strokes the gate KEEPS that OFF drops   {len(rescued):6d}")
    print(f"   ... of those, standing on a notehead    {rescued_on_head:6d}")
    print(f"   strokes the gate DROPS that OFF keeps   {len(lost):6d}")

    if len(cells) == 0:
        print("DEAD: no cells.")
        return 2
    if n_heads == 0:
        print("DEAD: the detector found NO noteheads -- the gate cannot be "
              "exercised and the ON arm is just the OFF arm.")
        return 2

    expect = a.expect if a.expect is not None else EXPECTED.get(a.tag)
    ok = True
    if expect is None:
        print(f"\n== FAITHFULNESS: no expected total for tag {a.tag!r} -- "
              f"REPORTED, NOT CHECKED (OFF arm = {n_off})")
    elif n_off != expect:
        print(f"\n== FAITHFULNESS FAILED: the OFF arm reads {n_off} stems "
              f"where the shared record holds {expect}. The two arms are not "
              f"comparable to anything committed.")
        ok = False
    else:
        print(f"\n== FAITHFULNESS: OFF arm reproduces the shared record's "
              f"{expect} stems EXACTLY.")

    if len(rescued) == 0 and len(lost) == 0:
        print("== POSITIVE CONTROL FAILED: the two arms are identical. The "
              "flag is not reaching the code, or the gate is inert here.")
        ok = False

    # ⚠️ The gate is one-sided BY CONSTRUCTION -- it only ever REMOVES a
    # condemnation -- so `lost` must be zero. Stated as a check rather than
    # asserted in prose: if it ever fires, the relation has been changed in a
    # way this arm's author did not intend.
    if lost:
        print(f"== STRUCTURAL CHECK FAILED: the gate DROPPED {len(lost)} "
              f"strokes the shipped rule keeps. It is supposed to be "
              f"one-sided (it can only ever un-condemn).")
        ok = False
    else:
        print("== STRUCTURAL: the gate is one-sided -- it dropped nothing the "
              "shipped rule keeps (0).")

    out = {
        "tag": a.tag, "pdf": a.pdf, "pages": pages, "dpi": a.dpi,
        "weights": a.weights, "cells": len(cells),
        "cells_with_a_notehead": cells_with_heads, "noteheads": n_heads,
        "stems_off": n_off, "stems_on": n_on,
        "cells_changed": cells_changed,
        "rescued": len(rescued), "rescued_on_a_notehead": rescued_on_head,
        "lost": len(lost),
        "expected_off": expect, "faithful": expect is None or n_off == expect,
    }
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(out, indent=1))
        print(f"\nwrote {a.json}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
