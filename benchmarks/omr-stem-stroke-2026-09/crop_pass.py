"""THE CROP PASS THE STEM THREAD HAS NEVER HAD.

`docs/handoff-2026-09-17-the-ink-is-fused.md` §6, in terms: **"No note has
been checked against the print in any stem arm. Every accuracy figure is one
of our readings against another ... The crop pass is owed and has never been
done for stems."**

It is owed here specifically, because `stroke_arm.py` returns a result that
SPLITS and the split cannot be adjudicated from inside our own readings:

    variant `side`      recovered   convention agreement   the bar
    Litolff                   345                  82.5%     95.8%
    Breitkopf                 545                  95.7%     97.9%

82.5% reads two ways and they call for OPPOSITE decisions. Either roughly
29% of the Litolff recoveries are junk -- in which case the reader inherits
`width_cap_check.py`'s refusal, which was taken at 83.6% -- or the CONVENTION
PROBE is the thing failing on this population, in which case the bar is wrong
and the reader is better than it scores. **Nothing measured off the same
raster can tell those apart.** This renders the print.

WHAT IT ASKS OF THE EYE, deliberately narrow: *is a stem printed at this
notehead, and which way does it go?* Not whether our box is tight, not
whether the band's ends are right -- one question, answerable from ink.

⚠️ THE SAMPLE IS STRATIFIED AND THAT IS NOT OPTIONAL TO DECLARE. Drawing 24
crops at random from 345 recoveries would land ~4 disagreements and settle
nothing. So it draws equally from the AGREE and DISAGREE strata and the two
rates are reported APART; the pooled figure is a weighted recombination and
is stated as such, never as "24 of 24".

⚠️ WHAT IS DRAWN IS THE PRINT, NOT OUR READING OF IT. The window is placed
from the head's own `bbox_page_px` -- a record fact, not a re-derivation --
and the only mark added is that box. The band is NOT drawn: a probe that
draws its own answer on the evidence invites the eye to confirm it.

⚠️ THE FRAME CONTROL. `benchmarks/omr-second-publisher-pricing-2026-09`
records a crop pass that had to prove its window was on the right ink before
its verdicts counted (it passed "at +133 to +229 grey levels"). The same
check here: every tile prints the mean grey inside the head box against the
tile's own mean, and a tile whose head box is not DARKER than its surround is
flagged -- the window is then not on a notehead and its verdict is void.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import statistics
import sys
from pathlib import Path

import cv2
import fitz
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402

DPI, INK = 600, 128
COL_W, REACH, SWEEP_, TOUCH = 0.12, 10.0, 0.85, 0.35
MIN_ARM = 1.25
# ⚠️ THE ZOOM IS PART OF THE INSTRUMENT. The first run of this pass used
# 2.6 / 7.0 / 7.0 spaces and 300-px tiles, which put a ~1-space notehead at a
# fifteenth of the tile height -- unadjudicable, and it would have produced
# verdicts anyway. A stem is ~3.5 spaces, so +-5 spaces shows all of one with
# room for the beam, and nothing wider is needed.
PAD_X, PAD_UP, PAD_DN = 1.7, 5.0, 5.0      # staff spaces around the head
TILE = 420                                  # px per tile side, after scaling
COLS = 3
PER_SHEET = 6


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
    ap.add_argument("--label", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--n-per-stratum", type=int, default=6)
    ap.add_argument("--seed", type=int, default=20260918)
    ap.add_argument("--agree", type=float, default=0.25)
    a = ap.parse_args()

    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged.gather import _system_local
    from tools.omr.line_detection import (detect_stems, _binary_ink,
                                          _staff_line_spacing)
    from stroke_columns import read_strokes, anchor_to_heads

    heads, pboxes, lines_of = {}, {}, {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[o["subject"]] = sorted(float(x) for x in o["value"])
        elif q == "glyph_box":
            v = o.get("value")
            if isinstance(v, list) and len(v) == 5 and str(v[0]).startswith("notehead"):
                heads[o["subject"]] = (float(v[1]), float(v[2]),
                                       float(v[3]), float(v[4]))
                bp = (o.get("detail") or {}).get("bbox_page_px")
                if bp:
                    pboxes[o["subject"]] = [float(x) for x in bp]
    verdict = {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            verdict[v["subject"]] = ("DECIDED" if v.get("outcome") == "decided"
                                     else str(v.get("reason")))
    missing = {s for s, r in verdict.items() if r == "no_stem" and s in heads}

    pages = [int(x) for x in a.pages.split(",")]
    prepared = list(zip(prepare_pages(a.pdf, pages, dpi=600), pages))
    heads_by_cell = collections.defaultdict(list)
    for s, b in heads.items():
        heads_by_cell["cell/" + "/".join(s.split("/")[1:5])].append(b)

    off, on = {}, {}
    for (pws, cs), pg in prepared:
        local = _system_local(pws.staves)
        for c in cs:
            key = local.get(c.staff_index)
            if key is None:
                continue
            ck = f"cell/{pg}/{key[0]}/{key[1]}/{c.measure_index}"
            base = [(float(d.x_canonical), float(d.y_canonical),
                     float(d.width_canonical), float(d.height_canonical))
                    for d in detect_stems(c)]
            off[ck] = base
            src = (c.image_no_staff
                   if getattr(c, "image_no_staff", None) is not None
                   else c.image)
            sp = _staff_line_spacing(c)
            if src is None or src.size == 0 or sp <= 1.0:
                on[ck] = base
                continue
            bands = read_strokes(_binary_ink(src), sp, c.width,
                                 agree_spaces=a.agree)
            extra = []
            for st, _h, _s, _d in anchor_to_heads(bands, heads_by_cell.get(ck, []), sp):
                b = (float(st.x_canonical), float(st.y_canonical), float(st.width_canonical), float(st.height_canonical))
                if any(overlaps(b, e) for e in base) or any(
                        overlaps(b, e) for e in extra):
                    continue
                extra.append(b)
            on[ck] = base + extra

    got = {}
    for s in missing:
        ck = "cell/" + "/".join(s.split("/")[1:5])
        if any(overlaps(heads[s], st) for st in off.get(ck, [])):
            continue
        hit = [st for st in on.get(ck, []) if overlaps(heads[s], st)]
        if hit:
            got[s] = max(hit, key=lambda st: st[3])
    print(f"{a.label}: the `side` variant recovers {len(got)} heads")
    if not got:
        print("DEAD: nothing recovered, nothing to crop.", file=sys.stderr)
        return 2

    doc = fitz.open(a.pdf)
    pgimg: dict[int, np.ndarray] = {}

    def page(pg):
        if pg not in pgimg:
            pm = doc[pg].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            pgimg[pg] = np.frombuffer(pm.samples, dtype=np.uint8).reshape(
                pm.height, pm.width)
        return pgimg[pg]

    def space_of(s):
        p = s.split("/")
        L = lines_of.get(f"staff/{p[1]}/{p[2]}/{p[3]}")
        if not L or len(L) < 5:
            return None
        return statistics.fmean([L[i + 1] - L[i] for i in range(4)])

    def convention(s):
        if s not in pboxes:
            return None
        sp = space_of(s)
        if sp is None:
            return None
        img = page(int(s.split("/")[1]))
        x0, y0, x1, y1 = pboxes[s]
        cy = (y0 + y1) / 2
        w = max(2, int(COL_W * sp))
        ya, yb = max(0, int(cy - REACH * sp)), min(img.shape[0],
                                                   int(cy + REACH * sp))
        mid = int(cy) - ya
        if yb - ya < 8 or not (0 <= mid < yb - ya):
            return None
        best = {"up": 0.0, "down": 0.0}
        step = max(1, w // 2)
        for side, edge in (("L", x0), ("R", x1)):
            lo = int(edge - (TOUCH if side == "R" else SWEEP_) * sp)
            hi = int(edge + (SWEEP_ if side == "R" else TOUCH) * sp)
            for cx in range(lo, hi + 1, step):
                xa, xb = max(0, cx), min(img.shape[1], cx + w)
                if xb - xa < 1:
                    continue
                mask = (img[ya:yb, xa:xb] < INK).mean(axis=1) >= 0.8
                if not mask[mid]:
                    continue
                if side == "R":
                    best["up"] = max(best["up"], arm_len(mask, mid, True) / sp)
                else:
                    best["down"] = max(best["down"],
                                       arm_len(mask, mid, False) / sp)
        up, dn = best["up"] >= MIN_ARM, best["down"] >= MIN_ARM
        return ("up" if up else "down") if up != dn else None

    def stroke_dir(s, st):
        hx0, hy0, hw, hh = heads[s]
        return "up" if st[1] + st[3] / 2 < hy0 + hh / 2 else "down"

    strata = collections.defaultdict(list)
    for s, st in got.items():
        if s not in pboxes or space_of(s) is None:
            continue
        c = convention(s)
        k = ("silent" if c is None else
             ("agree" if c == stroke_dir(s, st) else "disagree"))
        strata[k].append(s)
    print("strata available:", {k: len(v) for k, v in strata.items()})

    rng = random.Random(a.seed)
    picked = []
    for k in ("agree", "disagree", "silent"):
        v = sorted(strata.get(k, []))
        rng.shuffle(v)
        picked += [(k, s) for s in v[:a.n_per_stratum]]
    print(f"sampled {len(picked)} tiles, seed {a.seed}, "
          f"{a.n_per_stratum} per stratum")

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    tiles, index, flagged = [], [], 0
    for i, (k, s) in enumerate(picked):
        sp = space_of(s)
        img = page(int(s.split("/")[1]))
        x0, y0, x1, y1 = pboxes[s]
        xa = max(0, int(x0 - PAD_X * sp))
        xb = min(img.shape[1], int(x1 + PAD_X * sp))
        ya = max(0, int(y0 - PAD_UP * sp))
        yb = min(img.shape[0], int(y1 + PAD_DN * sp))
        crop = img[ya:yb, xa:xb]
        if crop.size == 0:
            continue
        # ── FRAME CONTROL: the head box must be DARKER than its surround ──
        hb = img[max(0, int(y0)):int(y1), max(0, int(x0)):int(x1)]
        d = float(crop.mean() - hb.mean()) if hb.size else -1.0
        ok = d > 20.0
        if not ok:
            flagged += 1
        tile = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
        cv2.rectangle(tile, (int(x0) - xa, int(y0) - ya),
                      (int(x1) - xa, int(y1) - ya), (0, 0, 255), 3)
        sc = TILE / max(tile.shape[0], tile.shape[1])
        tile = cv2.resize(tile, (max(1, int(tile.shape[1] * sc)),
                                 max(1, int(tile.shape[0] * sc))))
        pad = np.full((TILE + 26, TILE, 3), 255, np.uint8)
        oy, ox = (TILE - tile.shape[0]) // 2, (TILE - tile.shape[1]) // 2
        pad[26 + oy:26 + oy + tile.shape[0], ox:ox + tile.shape[1]] = tile
        cv2.putText(pad, f"#{i}  we say {stroke_dir(s, got[s])}"
                    + ("" if ok else "  FRAME?"),
                    (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        tiles.append(pad)
        index.append({"i": i, "stratum": k, "subject": s,
                      "we_say": stroke_dir(s, got[s]),
                      "convention": convention(s),
                      "frame_delta_grey": round(d, 1), "frame_ok": ok})

    sheets = []
    for start in range(0, len(tiles), PER_SHEET):
        chunk = tiles[start:start + PER_SHEET]
        rows = []
        for r in range(0, len(chunk), COLS):
            row = chunk[r:r + COLS]
            while len(row) < COLS:
                row.append(np.full_like(chunk[0], 255))
            rows.append(np.hstack(row))
        sheet = np.vstack(rows)
        p = outdir / f"sheet-{len(sheets)}.png"
        cv2.imwrite(str(p), sheet)
        sheets.append(str(p))
        print(f"wrote {p}")

    print(f"\nframe control: {flagged} of {len(index)} tiles FLAGGED "
          f"(head box not darker than its surround)")
    if flagged > len(index) * 0.1:
        print("DEAD: too many windows are not on a notehead; the crops cannot "
              "be adjudicated.", file=sys.stderr)
        return 2
    print("\n== the index (adjudicate each # against its tile)")
    for r in index:
        print(f"  #{r['i']:<3} {r['stratum']:<9} we say {r['we_say']:<5} "
              f"convention {str(r['convention']):<5} {r['subject']}")
    Path(a.json).write_text(json.dumps(
        {"label": a.label, "seed": a.seed, "recovered": len(got),
         "strata": {k: len(v) for k, v in strata.items()},
         "sheets": sheets, "index": index}, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
