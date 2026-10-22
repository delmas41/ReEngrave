"""IS THAT VERTICAL INK A STEM, OR IS IT A BARLINE?

`probe_stem_ink_raster.py` finds a vertical run beside 95.8% of the heads
whose stem direction abstains -- and beside 100% of the heads that got one,
which is the problem: on a conductor's page something vertical stands near
almost every notehead, so "there is ink" is nearly content-free.

A STEM AND A BARLINE HAVE DIFFERENT SHAPES, and the difference is the one an
engraver guarantees. **A stem is attached to its head and goes ONE WAY** --
up from the right side or down from the left -- so the ink is strongly
asymmetric about the head's centre. A barline passes THROUGH and continues
both ways. A neighbouring staff's stem does not touch this head at all.

So the test is not "is there ink" but "does the ink beside this head have the
same SHAPE as the ink beside a head we already read a stem from". The heads
with a decided stem are the reference distribution; they are not a guess.

Reported for each group:
  attached  -- the run crosses the head's own vertical centre
  one-way   -- of its length, the share lying on the longer side
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
COL_W, REACH, SWEEP = 0.12, 3.5, 0.85
MIN_STEM = 1.75


def runs(mask: np.ndarray):
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(mask) - 1))
    return out


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
    rec: dict[str, list[tuple[float, float, bool]]] = collections.defaultdict(list)
    for s, reason in verdict.items():
        if s not in pbox:
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
        ya = max(0, int(cy - REACH * space))
        yb = min(img.shape[0], int(cy + REACH * space))
        if yb - ya < 4:
            continue
        mid = int(cy) - ya
        best = None
        step = max(1, w // 2)
        for edge in (x0, x1):
            for cx in range(int(edge - SWEEP * space),
                            int(edge + SWEEP * space) + 1, step):
                xa, xb = max(0, cx), min(img.shape[1], cx + w)
                if xb - xa < 1:
                    continue
                mask = (img[ya:yb, xa:xb] < INK).mean(axis=1) >= 0.8
                for lo, hi in runs(mask):
                    ln = (hi - lo + 1) / space
                    if ln < MIN_STEM:
                        continue
                    attached = lo <= mid <= hi
                    up = (mid - lo) / space
                    dn = (hi - mid) / space
                    share = max(up, dn) / max(up + dn, 1e-6)
                    cand = (ln, share, attached)
                    if best is None or ln > best[0]:
                        best = cand
        if best:
            rec[reason].append(best)

    print(f"{a.label}")
    print(f"\n{'stem_direction says':<22} {'n':>6} {'attached':>9} "
          f"{'one-way >=0.80':>15} {'BOTH':>8}")
    out = {"label": a.label, "groups": {}}
    for reason in sorted(rec, key=lambda r: -len(rec[r])):
        v = rec[reason]
        att = sum(1 for _, _, t in v if t)
        one = sum(1 for _, sh, _ in v if sh >= 0.80)
        both = sum(1 for _, sh, t in v if t and sh >= 0.80)
        out["groups"][reason] = {
            "n": len(v), "attached": round(att / len(v), 4),
            "one_way": round(one / len(v), 4),
            "stem_shaped": round(both / len(v), 4),
            "median_share": round(statistics.median(sh for _, sh, _ in v), 3)}
        print(f"{reason:<22} {len(v):>6} {att / len(v):>8.1%} "
              f"{one / len(v):>15.1%} {both / len(v):>8.1%}")
    dec = out["groups"].get("DECIDED", {}).get("stem_shaped")
    if dec is None or dec < 0.5:
        print("\nDEAD: the reference group is not stem-shaped either; this "
              "probe cannot tell the two apart.", file=sys.stderr)
        return 2
    print(f"\nPOSITIVE CONTROL: heads with a READ stem are stem-shaped "
          f"{dec:.1%} of the time -- that is the bar the others are held to.")

    ns = [c for s, c in ((s, c) for s in verdict for c in [])]
    # the no_stem group by notehead class: a WHOLE note correctly has none
    byc = collections.Counter()
    for s, reason in verdict.items():
        if reason == "no_stem":
            byc[klass.get(s, "?")] += 1
    print("\n== the `no_stem` heads, by what the detector called them")
    for k, n in byc.most_common():
        note = "  <- correctly has NO stem" if "Whole" in k else ""
        print(f"  {k:<28} {n:>5}{note}")
    out["no_stem_by_class"] = dict(byc)
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
