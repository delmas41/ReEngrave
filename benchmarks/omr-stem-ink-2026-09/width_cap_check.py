"""ARE THE 217 REAL? The width cap is the biggest single filter cost on this
document, and a recall number alone is not a reason to move a constant.

`filter_sweep_arm.py`: relaxing `max_width_lines` 0.6 -> 1.5 recovers 217 of
793 heads for 175 new strokes, only 4 of which stand on an accidental. Cheap
-- but "not an accidental" is not "is a stem". A wider component on a
low-res bitonal plate is exactly what a stem MERGED with its own notehead, a
beam stub or a neighbour looks like, and this repo already records Litolff as
the plate that MERGES where Breitkopf shatters.

So the newly admitted strokes are put to an INDEPENDENT reader: the engraving
convention, off the raster. A stem is attached on the RIGHT going UP or on
the LEFT going DOWN; that reader agrees with the stems we already read 95.9%
of the time on this document, measured before any of this. If the recovered
strokes agree with it at that rate they are stems; if they agree at chance
they are blobs.

⚠️ The two are not independent of the PAGE, only of each other's METHOD: one
is a connected component on the erased image, the other a run of ink on the
original. That is weaker than a print check and stronger than a recall count.
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
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402

DPI, INK = 600, 128
COL_W, REACH, SWEEP, TOUCH = 0.12, 10.0, 0.85, 0.35
MIN_ARM = 1.25


def overlaps(a, b) -> bool:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    return (min(ax0 + aw, bx0 + bw) - max(ax0, bx0) > 0
            and min(ay0 + ah, by0 + bh) - max(ay0, by0) > 0)


def arm_len(mask, mid, up):
    n, i = 0, mid
    while 0 <= i < len(mask) and mask[i]:
        n += 1
        i += -1 if up else 1
    return max(0, n - 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged.gather import _system_local
    from tools.omr.line_detection import detect_stems

    heads, pboxes, lines_of, klass = {}, {}, {}, {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[o["subject"]] = sorted(float(x) for x in o["value"])
        elif q == "notehead_class":
            klass[o["subject"]] = str(o.get("value"))
        elif q == "glyph_box":
            v = o.get("value")
            if isinstance(v, list) and len(v) == 5 and str(v[0]).startswith("notehead"):
                heads[o["subject"]] = (float(v[1]), float(v[2]),
                                       float(v[3]), float(v[4]))
                bp = (o.get("detail") or {}).get("bbox_page_px")
                if bp:
                    pboxes[o["subject"]] = [float(x) for x in bp]
    verdict, value = {}, {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            dec = v.get("outcome") == "decided"
            verdict[v["subject"]] = "DECIDED" if dec else str(v.get("reason"))
            if dec:
                value[v["subject"]] = str(v.get("value"))

    pages = [int(x) for x in a.pages.split(",")]
    prepared = list(zip(prepare_pages(a.pdf, pages, dpi=600), pages))
    base, wide = {}, {}
    for (pws, cells), pg in prepared:
        local = _system_local(pws.staves)
        for c in cells:
            key = local.get(c.staff_index)
            if key is None:
                continue
            ck = f"cell/{pg}/{key[0]}/{key[1]}/{c.measure_index}"
            for store, kw in ((base, {}), (wide, {"max_width_lines": 1.5})):
                store[ck] = [(float(d.x_canonical), float(d.y_canonical),
                              float(d.width_canonical),
                              float(d.height_canonical))
                             for d in detect_stems(c, **kw)]

    # the heads the width cap recovers, and the stroke that recovered each
    got: dict[str, tuple] = {}
    for s, r in verdict.items():
        if r != "no_stem" or s not in heads:
            continue
        p = s.split("/")
        ck = "cell/" + "/".join(p[1:5])
        if ck not in wide:
            continue
        if any(overlaps(heads[s], st) for st in base.get(ck, [])):
            continue
        hit = [st for st in wide[ck] if overlaps(heads[s], st)]
        if hit:
            got[s] = max(hit, key=lambda st: st[3])
    print(f"heads the width cap recovers: {len(got)}")

    # ── the CONVENTION, off the raster, on those heads and on a reference ──
    doc = fitz.open(a.pdf)
    pgimg: dict[int, np.ndarray] = {}

    def convention(s):
        if s not in pboxes:
            return None
        p = s.split("/")
        L = lines_of.get(f"staff/{p[1]}/{p[2]}/{p[3]}")
        if not L or len(L) < 5:
            return None
        pg = int(p[1])
        if pg not in pgimg:
            pm = doc[pg].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            pgimg[pg] = np.frombuffer(pm.samples, dtype=np.uint8).reshape(
                pm.height, pm.width)
        img = pgimg[pg]
        space = statistics.fmean([L[i + 1] - L[i] for i in range(4)])
        x0, y0, x1, y1 = pboxes[s]
        cy = (y0 + y1) / 2
        w = max(2, int(COL_W * space))
        ya, yb = max(0, int(cy - REACH * space)), min(img.shape[0],
                                                      int(cy + REACH * space))
        mid = int(cy) - ya
        if yb - ya < 8 or not (0 <= mid < yb - ya):
            return None
        best = {"up": 0.0, "down": 0.0}
        step = max(1, w // 2)
        for side, edge in (("L", x0), ("R", x1)):
            lo = int(edge - (TOUCH if side == "R" else SWEEP) * space)
            hi = int(edge + (SWEEP if side == "R" else TOUCH) * space)
            for cx in range(lo, hi + 1, step):
                xa, xb = max(0, cx), min(img.shape[1], cx + w)
                if xb - xa < 1:
                    continue
                mask = (img[ya:yb, xa:xb] < INK).mean(axis=1) >= 0.8
                if not mask[mid]:
                    continue
                if side == "R":
                    best["up"] = max(best["up"], arm_len(mask, mid, True) / space)
                else:
                    best["down"] = max(best["down"],
                                       arm_len(mask, mid, False) / space)
        up, dn = best["up"] >= MIN_ARM, best["down"] >= MIN_ARM
        return ("up" if up else "down") if up != dn else None

    def stroke_dir(s, st):
        hx0, hy0, hw, hh = heads[s]
        return "up" if st[1] + st[3] / 2 < hy0 + hh / 2 else "down"

    tally = collections.Counter()
    for s, st in got.items():
        c = convention(s)
        if c is None:
            tally["convention silent"] += 1
        else:
            tally["AGREES" if c == stroke_dir(s, st) else "disagrees"] += 1

    ref = collections.Counter()
    for s, r in list(verdict.items()):
        if r != "DECIDED" or s not in heads:
            continue
        c = convention(s)
        if c is None:
            ref["convention silent"] += 1
        else:
            ref["AGREES" if c == value.get(s) else "disagrees"] += 1

    print("\n== do the RECOVERED strokes agree with the engraving convention?")
    for k, n in tally.most_common():
        print(f"   {k:<22} {n:>5}")
    t = tally["AGREES"] + tally["disagrees"]
    r = ref["AGREES"] + ref["disagrees"]
    print(f"\n   recovered:  {tally['AGREES']}/{t} = "
          f"{tally['AGREES']/max(1,t):.1%}")
    print(f"   REFERENCE (stems we already read): {ref['AGREES']}/{r} = "
          f"{ref['AGREES']/max(1,r):.1%}   <- the bar")
    out = {"recovered": len(got), "agreement": dict(tally),
           "reference": dict(ref)}
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
