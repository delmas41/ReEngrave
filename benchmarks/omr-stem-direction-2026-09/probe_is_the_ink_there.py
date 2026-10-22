"""IS THE STEM MISSING, MISLABELLED, OR MERELY NOT ATTACHED?

Sean, 2026-09-17: *"is the point that we don't see the ink or that we were
mislabeling it or that it was being disregarded?"*

⚠️⚠️ I DID NOT MEASURE THIS AND THE DISTINCTION DECIDES THE WHOLE REPAIR.
`adjudicate_stem_direction` abstains `no_stem` when no stem row OVERLAPS the
head's box. That is one test doing two jobs, and it cannot tell apart:

  ABSENT      the CV rung found no stem ink anywhere near this head -- the
              scan lost it, and no downstream rule can recover what was never
              read;
  UNATTACHED  a stem row IS there, a few pixels off, and the box-overlap test
              refused it -- in which case the repair is the ATTACHMENT and
              the whole beam-mate tier is treating a symptom.

The second would be much the better thing to fix, so it gets asked first.

It also settles a fact about the population: a WHOLE note carries no stem, but
a HALF note does -- hollow head, stem attached. If this document's half notes
are mostly stemless in the record, they are misses and not convention.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.adjudicators.rhythm import _xywh_head      # noqa: E402
from tools.omr.staged.record import Kind, Subject                # noqa: E402


def cell_of(k):
    return Subject.from_key(k).at(Kind.CELL).to_key()


def box4(v):
    if not isinstance(v, (list, tuple)) or len(v) != 4:
        return None
    try:
        return tuple(float(t) for t in v)
    except (TypeError, ValueError):
        return None


def gap(head, stem):
    """Shortest distance between the two boxes, 0 if they touch."""
    hx0, hy0, hx1, hy1 = head[0], head[1], head[0] + head[2], head[1] + head[3]
    sx0, sy0, sx1, sy1 = stem[0], stem[1], stem[0] + stem[2], stem[1] + stem[3]
    dx = max(sx0 - hx1, hx0 - sx1, 0.0)
    dy = max(sy0 - hy1, hy0 - sy1, 0.0)
    return (dx * dx + dy * dy) ** 0.5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "is-the-ink-there.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc

    box_of, cls_of, space_of = {}, {}, {}
    stems = collections.defaultdict(list)
    for o in rec["observations"]:
        q = o["quantity"]
        if q == "glyph_box":
            b = _xywh_head(o.get("value"))
            if b is not None:
                box_of[o["subject"]] = b
        elif q == "notehead_class":
            cls_of[o["subject"]] = str(o["value"])
        elif q == "stem":
            b = box4(o.get("value"))
            if b is not None:
                stems[cell_of(o["subject"])].append(b)
        elif q == "cell_staff_space":
            try:
                space_of[cell_of(o["subject"])] = float(o["value"])
            except (TypeError, ValueError):
                pass

    verdicts = [v for v in rec["verdicts"] if v["quantity"] == "stem_direction"]
    no_stem = [v["subject"] for v in verdicts if v["reason"] == "no_stem"]
    decided = [v["subject"] for v in verdicts if v["outcome"] == "decided"]

    # ── the fact about half notes, from the record rather than from memory ──
    def head_kind(sub):
        c = cls_of.get(sub, "")
        return ("whole" if "Whole" in c else "half" if "Half" in c
                else "black" if "Black" in c else "other")
    print("── does a head of this kind get a stem on this document?")
    print(f"{'kind':<8} {'stem found':>11} {'no stem':>9} {'share stemless':>15}")
    tbl = {}
    for kind in ("whole", "half", "black", "other"):
        d = sum(1 for s in decided if head_kind(s) == kind)
        n = sum(1 for s in no_stem if head_kind(s) == kind)
        if d + n == 0:
            continue
        tbl[kind] = {"stem_found": d, "no_stem": n,
                     "share_stemless": round(n / (d + n), 3)}
        print(f"{kind:<8} {d:>11} {n:>9} {n / (d + n):>15.3f}")

    # ── ABSENT or UNATTACHED? ──────────────────────────────────────────────
    bands = collections.Counter()
    gaps = []
    no_stem_in_cell = 0
    for sub in no_stem:
        head = box_of.get(sub)
        if head is None:
            continue
        c = cell_of(sub)
        near = stems.get(c) or []
        if not near:
            bands["no stem ink ANYWHERE in the bar"] += 1
            no_stem_in_cell += 1
            continue
        sp = space_of.get(c) or 0.0
        g = min(gap(head, s) for s in near)
        gs = (g / sp) if sp else None
        if gs is None:
            bands["no staff-space unit to judge with"] += 1
            continue
        gaps.append(gs)
        band = ("touching (0)" if gs <= 0.01 else
                "within 0.25 space" if gs <= 0.25 else
                "0.25-1 space" if gs <= 1.0 else
                "1-3 spaces" if gs <= 3.0 else "further than 3 spaces")
        bands[band] += 1

    print(f"\n── the {len(no_stem)} `no_stem` heads: how far is the NEAREST "
          f"stem row in the same bar?")
    order = ["touching (0)", "within 0.25 space", "0.25-1 space",
             "1-3 spaces", "further than 3 spaces",
             "no stem ink ANYWHERE in the bar", "no staff-space unit to judge with"]
    for band in order:
        if bands.get(band):
            print(f"   {bands[band]:6d}  ({100.0 * bands[band] / len(no_stem):5.1f}%)  {band}")
    if gaps:
        gaps.sort()
        print(f"\n   median gap {statistics.median(gaps):.2f} spaces, "
              f"p10 {gaps[int(0.1 * len(gaps))]:.2f}, "
              f"p90 {gaps[int(0.9 * len(gaps))]:.2f}")

    out = {"by_head_kind": tbl, "bands": dict(bands),
           "median_gap_spaces": round(statistics.median(gaps), 3) if gaps else None}
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
