"""The reachable population, against the print — stratified by (head, STROKE).

⚠️⚠️ THIS REPLACES `crop_mid.py`, WHICH HAD A DEFECT ITS OWN CROPS EXPOSED.
That probe stratified by SUBJECT and stored one `frac` per head. A head can
overlap TWO strokes -- each of which is then a *solo* stroke, since the head is
the only one on it -- so such a head entered BOTH strata and the manifest kept
whichever frac was written last. Eleven of its twenty-four tiles were such
heads, and the tell was a tile labelled `MID` whose manifest `frac` read 0.061.
The unit of this question is the (head, stroke) PAIR, not the head.

⚠️ AND THE TILE NOW SHOWS THE STROKE. With two strokes on one head, *"is the
head at an end?"* has two answers and a tile that marks only the head cannot
be adjudicated at all. The stroke box is mapped canonical -> page with the
HEAD AS ITS OWN RULER (the per-cell affine CLAUDE.md records at residual
0.00 px), and the probe REPORTS that residual rather than assuming it.

⚠️ The tile still carries an opaque id and nothing else: no stratum, no
direction, no reader's answer.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reach import collect, overlap  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from omr_ledger_extrapolation_shim import stream_array  # noqa: E402

DPI = 600
PAD_X, PAD_Y = 7.0, 7.0
TILE, COLS, PER_SHEET = 560, 2, 4
MID_LO, MID_HI = 0.25, 0.75
END_LO, END_HI = 0.12, 0.88


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--n-per-stratum", type=int, default=12)
    ap.add_argument("--seed", type=int, default=20260921)
    a = ap.parse_args()

    stems, heads, _ = collect(a.record)
    pbox, lines_of = {}, {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "staff_lines":
            lines_of[o["subject"]] = o["value"]
        elif q == "glyph_box":
            d = o.get("detail") or {}
            if d.get("category") == "notehead" and d.get("bbox_page_px"):
                pbox[o["subject"]] = d["bbox_page_px"]

    # ── canonical -> page, per cell, with the HEAD AS ITS OWN RULER ─────────
    affine, resid = {}, []
    for c, hs in heads.items():
        pts = [(hb, pbox[s]) for s, _h, hb in hs if s in pbox]
        if not pts:
            continue
        sx = statistics.fmean([(p[2] - p[0]) / hb[2] for hb, p in pts if hb[2]])
        sy = statistics.fmean([(p[3] - p[1]) / hb[3] for hb, p in pts if hb[3]])
        ox = statistics.fmean([p[0] - hb[0] * sx for hb, p in pts])
        oy = statistics.fmean([p[1] - hb[1] * sy for hb, p in pts])
        affine[c] = (sx, sy, ox, oy)
        for hb, p in pts:
            resid.append(abs(hb[0] * sx + ox - p[0]) + abs(hb[1] * sy + oy - p[1]))

    pairs = []
    for c, hs in heads.items():
        for sid, sb in stems.get(c, []):
            members = [(s, hb) for s, _h, hb in hs if overlap(sb, hb)]
            if len(members) != 1:
                continue
            subj, hb = members[0]
            if subj not in pbox or c not in affine:
                continue
            f = ((hb[1] + hb[3] / 2.0) - sb[1]) / sb[3] if sb[3] > 0 else 0.5
            k = ("MID" if MID_LO < f < MID_HI
                 else ("END" if (f < END_LO or f > END_HI) else None))
            if k:
                pairs.append({"stratum": k, "subject": subj, "stem": sid,
                              "cell": c, "frac": round(f, 4),
                              "n_stems_on_this_head": sum(
                                  1 for s2, sb2 in stems.get(c, [])
                                  if overlap(sb2, hb)),
                              "stem_box_canonical": [round(x, 1) for x in sb]})

    byk = defaultdict(list)
    for p in pairs:
        byk[p["stratum"]].append(p)
    print(f"{a.label}: (head, stroke) pairs "
          f"{ {k: len(v) for k, v in byk.items()} }")
    print(f"canonical->page affine residual: mean {statistics.fmean(resid):.3f} px, "
          f"max {max(resid):.3f} px over {len(resid)} heads")
    if not byk.get("MID"):
        print("DEAD: no solo mid-stroke pair on this record.", file=sys.stderr)
        return 2

    rng = random.Random(a.seed)
    picked = []
    for k in ("MID", "END"):
        v = sorted(byk[k], key=lambda p: (p["subject"], p["stem"]))
        rng.shuffle(v)
        picked += v[:a.n_per_stratum]
    rng.shuffle(picked)

    doc = fitz.open(a.pdf)
    cache = {}

    def page(pg):
        if pg not in cache:
            pm = doc[pg].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            cache[pg] = np.frombuffer(pm.samples, dtype=np.uint8).reshape(
                pm.height, pm.width)
        return cache[pg]

    def space_of(s):
        p = s.split("/")
        L = lines_of.get(f"staff/{p[1]}/{p[2]}/{p[3]}")
        return statistics.fmean([L[i + 1] - L[i] for i in range(4)]) \
            if L and len(L) >= 5 else None

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    tiles, index, flagged = [], [], 0
    for i, p in enumerate(picked):
        s = p["subject"]
        sp = space_of(s)
        if sp is None:
            continue
        img = page(int(s.split("/")[1]))
        x0, y0, x1, y1 = pbox[s]
        sx, sy, ox, oy = affine[p["cell"]]
        bx, by, bw, bh = p["stem_box_canonical"]
        sX0, sY0 = bx * sx + ox, by * sy + oy
        sX1, sY1 = (bx + bw) * sx + ox, (by + bh) * sy + oy
        xa = max(0, int(min(x0, sX0) - PAD_X * sp))
        xb = min(img.shape[1], int(max(x1, sX1) + PAD_X * sp))
        ya = max(0, int(min(y0, sY0) - PAD_Y * sp))
        yb = min(img.shape[0], int(max(y1, sY1) + PAD_Y * sp))
        crop = img[ya:yb, xa:xb]
        if crop.size == 0:
            continue
        hb_img = img[max(0, int(y0)):int(y1), max(0, int(x0)):int(x1)]
        d = float(crop.mean() - hb_img.mean()) if hb_img.size else -1.0
        ok = d > 20.0
        flagged += 0 if ok else 1
        tile = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
        # BLUE = the stroke under test; RED = the head. Drawn as open
        # rectangles so no ink is hidden.
        cv2.rectangle(tile, (int(sX0) - xa, int(sY0) - ya),
                      (int(sX1) - xa, int(sY1) - ya), (255, 0, 0), 2)
        cv2.rectangle(tile, (int(x0) - xa, int(y0) - ya),
                      (int(x1) - xa, int(y1) - ya), (0, 0, 255), 2)
        sc = TILE / max(tile.shape[0], tile.shape[1])
        tile = cv2.resize(tile, (max(1, int(tile.shape[1] * sc)),
                                 max(1, int(tile.shape[0] * sc))),
                          interpolation=cv2.INTER_CUBIC)
        pad = np.full((TILE + 26, TILE, 3), 255, np.uint8)
        oy2, ox2 = (TILE - tile.shape[0]) // 2, (TILE - tile.shape[1]) // 2
        pad[26 + oy2:26 + oy2 + tile.shape[0],
            ox2:ox2 + tile.shape[1]] = tile
        cv2.putText(pad, f"P{i:02d}" + ("" if ok else "  FRAME?"),
                    (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        tiles.append(pad)
        index.append({"tile": f"P{i:02d}", **p,
                      "frame_delta_grey": round(d, 1), "frame_ok": ok,
                      "stem_box_page_px": [round(v, 1)
                                           for v in (sX0, sY0, sX1, sY1)],
                      "head_box_page_px": [round(v, 1) for v in pbox[s]],
                      "staff_space_px": round(sp, 2)})

    sheets = []
    for start in range(0, len(tiles), PER_SHEET):
        chunk = tiles[start:start + PER_SHEET]
        rows = []
        for r in range(0, len(chunk), COLS):
            row = chunk[r:r + COLS]
            while len(row) < COLS:
                row.append(np.full_like(chunk[0], 255))
            rows.append(np.hstack(row))
        pth = outdir / f"sheet-{len(sheets)}.png"
        cv2.imwrite(str(pth), np.vstack(rows))
        sheets.append(str(pth))
        print(f"wrote {pth}")

    print(f"frame control: {flagged} of {len(index)} tiles FLAGGED")
    if flagged > len(index) * 0.1:
        print("DEAD: too many windows are not on a notehead.", file=sys.stderr)
        return 2
    Path(a.json).write_text(json.dumps(
        {"label": a.label, "seed": a.seed, "pdf": a.pdf,
         "pairs_available": {k: len(v) for k, v in byk.items()},
         "affine_residual_px": {"mean": round(statistics.fmean(resid), 4),
                                "max": round(max(resid), 4), "n": len(resid)},
         "pad_x_spaces": PAD_X, "pad_y_spaces": PAD_Y,
         "sheets": sheets, "index": index}, indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
