"""The WHOLE far-from-an-end population, against the print.

⚠️⚠️ THIS IS THE THIRD CROP TOOL ON THIS LANE AND THE FIRST AIMED AT THE RIGHT
POPULATION. `crop_mid.py` stratified by SUBJECT and mixed two strata for heads
carrying two strokes; `crop_pairs.py` fixed that but still selected on `frac`,
which the crops themselves then refuted -- a head at the end of a SHORT stroke
scores mid-`frac` by arithmetic, so that sample was drawn from short strokes
rather than from misattributed heads. The scale-free quantity is the distance
from the head's centre to the NEARER END of the stroke in units of the head's
own height, and this selects on that.

⚠️ IT IS A CENSUS, NOT A SAMPLE. On the shipped records the population is
small enough to crop ENTIRELY (8 on Breitkopf, 15 on Litolff above 0.8 head
heights), so there is no sampling error to argue about and no seed to declare.
A matched CONTROL stratum is drawn from the heads that ARE at an end, because
a pass that cannot adjudicate the easy case is measuring the plate.

⚠️ `--source profile` asks the same of `OMR_STEM_STROKE`'s column profile,
where the population is ~10x larger and is where the two lanes that found this
fault were looking.
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
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-stem-stroke-2026-09"))
from reach import collect, end_gap, overlap  # noqa: E402
from omr_ledger_extrapolation_shim import stream_array  # noqa: E402

DPI = 600
PAD_X, PAD_Y = 7.0, 7.0
TILE, COLS, PER_SHEET = 560, 2, 4


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--gap", type=float, default=0.8,
                    help="head-heights from the nearer end; FAR stratum is >")
    ap.add_argument("--source", choices=["record", "profile"],
                    default="record")
    ap.add_argument("--n-control", type=int, default=8)
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

    pages = []
    for part in a.pages.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            pages += list(range(int(lo), int(hi) + 1))
        else:
            pages.append(int(part))

    if a.source == "profile":
        from tools.omr.staged.pipeline import prepare_pages
        from tools.omr.staged.gather import _system_local
        from tools.omr.line_detection import _binary_ink, _staff_line_spacing
        from stroke_columns import read_strokes, anchor_to_heads
        strokes = collections.defaultdict(list)
        hbc = collections.defaultdict(list)
        for c, hs in heads.items():
            for _s, _h, hb in hs:
                hbc[c].append(hb)
        print("cutting cells for the profile reader ...", flush=True)
        for (pws, cs), pg in zip(prepare_pages(a.pdf, pages, dpi=600), pages):
            local = _system_local(pws.staves)
            for c in cs:
                key = local.get(c.staff_index)
                if key is None:
                    continue
                ck = f"cell/{pg}/{key[0]}/{key[1]}/{c.measure_index}"
                src = (c.image_no_staff
                       if getattr(c, "image_no_staff", None) is not None
                       else c.image)
                sp = _staff_line_spacing(c)
                if src is None or src.size == 0 or sp <= 1.0:
                    continue
                for st, _h, _s, _d in anchor_to_heads(
                        read_strokes(_binary_ink(src), sp, c.width),
                        hbc.get(ck, []), sp):
                    strokes[ck].append(
                        (f"profile:{ck}:{len(strokes[ck])}",
                         (float(st.x_canonical), float(st.y_canonical),
                          float(st.width_canonical),
                          float(st.height_canonical))))
    else:
        strokes = stems

    far, near = [], []
    for c, hs in heads.items():
        for sid, sb in strokes.get(c, []):
            members = [(s, hb) for s, _h, hb in hs if overlap(sb, hb)]
            if len(members) != 1:
                continue
            subj, hb = members[0]
            if subj not in pbox or c not in affine:
                continue
            hh = max(hb[3], 1e-6)
            g = end_gap(hb, sb)
            rec = {"subject": subj, "stem": sid, "cell": c,
                   "gap_head_heights": round(g, 3),
                   "stroke_in_head_heights": round(sb[3] / hh, 3),
                   "stem_box_canonical": [round(x, 1) for x in sb]}
            (far if g > a.gap else near).append(rec)

    print(f"{a.label} [{a.source}]: FAR (gap > {a.gap}) = {len(far)} "
          f"— cropped ENTIRE; at-an-end pool = {len(near)}")
    if not far:
        print("DEAD: nothing beyond the cut on this record.", file=sys.stderr)
        return 2
    rng = random.Random(a.seed)
    ctrl = sorted(near, key=lambda r: (r["subject"], str(r["stem"])))
    rng.shuffle(ctrl)
    picked = ([{**r, "stratum": "FAR"} for r in far]
              + [{**r, "stratum": "END"} for r in ctrl[:a.n_control]])
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
        sX0, sY0, sX1, sY1 = (bx * sx + ox, by * sy + oy,
                              (bx + bw) * sx + ox, (by + bh) * sy + oy)
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
        cv2.putText(pad, f"G{i:02d}" + ("" if ok else "  FRAME?"),
                    (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        tiles.append(pad)
        index.append({"tile": f"G{i:02d}", **p,
                      "frame_delta_grey": round(d, 1), "frame_ok": ok,
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
    Path(a.json).write_text(json.dumps(
        {"label": a.label, "source": a.source, "gap_cut": a.gap,
         "seed": a.seed, "pdf": a.pdf,
         "FAR_population_size": len(far), "cropped_all_of_FAR": True,
         "affine_residual_px": {"mean": round(statistics.fmean(resid), 4),
                                "max": round(max(resid), 4)},
         "sheets": sheets, "index": index}, indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
