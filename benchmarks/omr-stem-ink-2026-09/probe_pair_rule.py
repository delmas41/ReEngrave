"""IS `_drop_paired_strokes` DELETING REAL STEMS? Sean's "later stages" idea,
aimed at the one filter whose premise is a claim about SPACING.

`line_detection._drop_paired_strokes` rejects two vertical strokes whose
centres are within `accidental_pair_gap_lines = 0.9` staff spaces and which
overlap vertically by `0.6` of the shorter -- on the ground that a sharp and a
natural are two parallel verticals half a space apart, and that *"successive
notes are set further apart than an accidental's own strokes"*. **Both members
are dropped.**

That premise is a claim about how widely this plate sets its notes, and it was
measured on 14 hand-counted cells. A conductor's page sets notes tightly. So:
evaluate the SAME predicate on the raster, at every head, and ask how often a
head's own stem has a second vertical run close enough to pair with it.

⚠️ The reference is the heads whose stem we DID read: whatever rate THEY show
is the rate at which the rule fires harmlessly, and only an excess over that
is evidence of it costing us stems.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

import fitz
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "benchmarks"
                       / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402

DPI, INK = 600, 128
COL_W, REACH, SWEEP, TOUCH = 0.12, 10.0, 0.85, 0.35
MIN_ARM = 1.25
PAIR_GAP = 0.9        # line_detection.accidental_pair_gap_lines
PAIR_OVERLAP = 0.6    # line_detection.accidental_pair_overlap
SCAN = 2.2            # how far sideways to look for a partner, staff spaces


def run_through(mask, mid):
    if not mask[mid]:
        return None
    lo = hi = mid
    while lo > 0 and mask[lo - 1]:
        lo -= 1
    while hi < len(mask) - 1 and mask[hi + 1]:
        hi += 1
    return lo, hi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    lines_of, pbox, klass = {}, {}, {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[o["subject"]] = sorted(float(x) for x in o["value"])
        elif q == "notehead_class":
            klass[o["subject"]] = str(o.get("value"))
        elif q == "glyph_box":
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp:
                pbox[o["subject"]] = [float(x) for x in bp]
    verdict = {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            verdict[v["subject"]] = ("DECIDED" if v.get("outcome") == "decided"
                                     else str(v.get("reason")))

    doc = fitz.open(a.pdf)
    pages: dict[int, np.ndarray] = {}
    tally = collections.defaultdict(collections.Counter)
    for s, reason in verdict.items():
        if s not in pbox or "Whole" in klass.get(s, ""):
            continue
        p = s.split("/")
        L = lines_of.get(f"staff/{p[1]}/{p[2]}/{p[3]}")
        if not L or len(L) < 5:
            continue
        pg = int(p[1])
        if pg not in pages:
            pm = doc[pg].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            pages[pg] = np.frombuffer(pm.samples, dtype=np.uint8).reshape(
                pm.height, pm.width)
        img = pages[pg]
        space = statistics.fmean([L[i + 1] - L[i] for i in range(4)])
        x0, y0, x1, y1 = pbox[s]
        cy = (y0 + y1) / 2
        w = max(2, int(COL_W * space))
        ya = max(0, int(cy - REACH * space)); yb = min(img.shape[0], int(cy + REACH * space))
        if yb - ya < 8:
            continue
        mid = int(cy) - ya
        if not (0 <= mid < yb - ya):
            continue
        # locate THIS head's stem by the convention, and keep its extent
        stem = None
        step = max(1, w // 2)
        for side, edge in (("L", x0), ("R", x1)):
            lo_x = int(edge - (TOUCH if side == "R" else SWEEP) * space)
            hi_x = int(edge + (SWEEP if side == "R" else TOUCH) * space)
            for cx in range(lo_x, hi_x + 1, step):
                xa, xb = max(0, cx), min(img.shape[1], cx + w)
                if xb - xa < 1:
                    continue
                mask = (img[ya:yb, xa:xb] < INK).mean(axis=1) >= 0.8
                r = run_through(mask, mid)
                if r is None:
                    continue
                lo, hi = r
                up, dn = (mid - lo) / space, (hi - mid) / space
                ok = (side == "R" and up >= MIN_ARM and dn < MIN_ARM) or \
                     (side == "L" and dn >= MIN_ARM and up < MIN_ARM)
                if ok and (stem is None or (hi - lo) > (stem[2] - stem[1])):
                    stem = (cx, lo, hi)
        if stem is None:
            continue
        cx, lo, hi = stem
        # now look sideways for a PARTNER that would pair with it
        paired = False
        for dx in range(-int(SCAN * space), int(SCAN * space) + 1, step):
            if abs(dx) < max(1, int(0.15 * space)):
                continue
            if abs(dx) / space > PAIR_GAP:
                continue                     # the rule's own gap bound
            xa, xb = max(0, cx + dx), min(img.shape[1], cx + dx + w)
            if xb - xa < 1:
                continue
            mask = (img[ya:yb, xa:xb] < INK).mean(axis=1) >= 0.8
            for st in range(len(mask)):
                if not mask[st] or (st and mask[st - 1]):
                    continue
                en = st
                while en < len(mask) - 1 and mask[en + 1]:
                    en += 1
                if (en - st) / space < 2.0:      # min_height_lines
                    continue
                ov = min(hi, en) - max(lo, st)
                if ov <= 0:
                    continue
                shorter = min(hi - lo, en - st)
                if ov / max(1.0, shorter) >= PAIR_OVERLAP:
                    paired = True
                    break
            if paired:
                break
        tally[reason]["paired" if paired else "single"] += 1

    print(f"{a.label}")
    print(f"\n== would `_drop_paired_strokes` fire on this head's own stem?")
    print(f"{'stem_direction says':<20} {'n':>6} {'would PAIR':>12} {'share':>8}")
    out = {"label": a.label, "groups": {}}
    for reason in sorted(tally, key=lambda r: -sum(tally[r].values())):
        c = tally[reason]
        n = sum(c.values())
        out["groups"][reason] = {"n": n, "paired": c["paired"],
                                 "share": round(c["paired"] / n, 4)}
        print(f"{reason:<20} {n:>6} {c['paired']:>12} {c['paired']/n:>8.1%}")
    ref = out["groups"].get("DECIDED", {}).get("share")
    ns = out["groups"].get("no_stem", {}).get("share")
    if ref is None or ns is None:
        print("\nDEAD: one of the two groups is empty", file=sys.stderr)
        return 2
    print(f"\n   reference (stems we DID read) {ref:.1%}   "
          f"missing {ns:.1%}   excess {ns - ref:+.1%}")
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
