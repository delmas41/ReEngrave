"""Put the REACHABLE population to the print.

⚠️⚠️ THIS EXISTS BECAUSE THE TRUTH THIS THREAD ALREADY OWNS CANNOT REACH THE
RULE. All 44 heads adjudicated against the print on this thread -- the crop
pass's 26-head standoff and the stroke lane's 18 crops -- have NO overlapping
stem in either shared record, and the record's own verdict for all 44 is
`no_stem`. An end rule on `_stems_on` only ever REMOVES an attribution, so it
cannot move a head that has none. The population it CAN move has never been
looked at, and this looks at it.

Two strata, and the control is not optional:

  MID  -- a stroke claimed by exactly ONE head, with that head part-way ALONG
          it. The rule's own population.
  END  -- a stroke claimed by exactly one head, at one of its ends. Textbook,
          and the CONTROL: if these cannot be adjudicated either, the crops
          are measuring the plate and not the rule. (The 2026-09-18 handoff
          records ~60% `cannot_tell` on Litolff for exactly this reason.)

⚠️ THE STRIP IS WIDE ON PURPOSE. That handoff's method warning -- *"at tile
magnification the adjudicator read two heads WRONG and a wide strip corrected
both; a crop centred on a head cannot tell you the head is a NUMERAL"* -- is
why `PAD_X` here is 7.0 staff spaces against the stroke lane's 1.7. The fault
under test is *the head sits on a NEIGHBOUR's stem*, which is invisible unless
the neighbour is in frame.

⚠️ THE TILE CARRIES AN OPAQUE ID AND NOTHING ELSE. The stroke lane's tiles
printed `we say <direction>` on the image; a verdict written under that is not
independent of the reader. What each tile's readers said is written to the
manifest, which is not needed to adjudicate.
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
PAD_X, PAD_Y = 7.0, 7.0      # staff spaces around the head -- WIDE, see above
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

    # page boxes and staff lines come from the record, not re-measured
    pbox, lines_of = {}, {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "staff_lines":
            lines_of[o["subject"]] = o["value"]
        elif q == "glyph_box":
            d = o.get("detail") or {}
            if d.get("category") == "notehead" and d.get("bbox_page_px"):
                pbox[o["subject"]] = d["bbox_page_px"]   # CORNERS x0,y0,x1,y1

    per_stem = defaultdict(list)
    for c, hs in heads.items():
        for sid, sb in stems.get(c, []):
            for subj, _hid, hb in hs:
                if overlap(sb, hb):
                    per_stem[sid].append((subj, hb, sb))

    strata = defaultdict(list)
    info = {}
    for sid, members in per_stem.items():
        if len(members) != 1:
            continue                      # chords are out of this rule's reach
        subj, hb, sb = members[0]
        if subj not in pbox:
            continue
        f = ((hb[1] + hb[3] / 2.0) - sb[1]) / sb[3] if sb[3] > 0 else 0.5
        k = ("MID" if MID_LO < f < MID_HI
             else ("END" if (f < END_LO or f > END_HI) else None))
        if k:
            strata[k].append(subj)
            info[subj] = {"frac": round(f, 4), "stem": sid,
                          "stem_box_canonical": [round(x, 1) for x in sb]}

    print(f"{a.label}: strata available "
          f"{ {k: len(v) for k, v in strata.items()} }")
    if not strata.get("MID"):
        print("DEAD: no solo mid-stroke head on this record.", file=sys.stderr)
        return 2

    rng = random.Random(a.seed)
    picked = []
    for k in ("MID", "END"):
        v = sorted(strata.get(k, []))
        rng.shuffle(v)
        picked += [(k, s) for s in v[:a.n_per_stratum]]
    # ⚠️ SHUFFLE THE SHEET ORDER so the strata are not in blocks: a tile's
    # position on the sheet must not tell the adjudicator which stratum it is.
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
        if not L or len(L) < 5:
            return None
        return statistics.fmean([L[i + 1] - L[i] for i in range(4)])

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    tiles, index, flagged = [], [], 0
    for i, (k, s) in enumerate(picked):
        sp = space_of(s)
        if sp is None:
            continue
        img = page(int(s.split("/")[1]))
        x0, y0, x1, y1 = pbox[s]
        xa, xb = max(0, int(x0 - PAD_X * sp)), min(img.shape[1],
                                                   int(x1 + PAD_X * sp))
        ya, yb = max(0, int(y0 - PAD_Y * sp)), min(img.shape[0],
                                                   int(y1 + PAD_Y * sp))
        crop = img[ya:yb, xa:xb]
        if crop.size == 0:
            continue
        hb_img = img[max(0, int(y0)):int(y1), max(0, int(x0)):int(x1)]
        d = float(crop.mean() - hb_img.mean()) if hb_img.size else -1.0
        ok = d > 20.0
        flagged += 0 if ok else 1
        tile = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
        cv2.rectangle(tile, (int(x0) - xa, int(y0) - ya),
                      (int(x1) - xa, int(y1) - ya), (0, 0, 255), 2)
        sc = TILE / max(tile.shape[0], tile.shape[1])
        tile = cv2.resize(tile, (max(1, int(tile.shape[1] * sc)),
                                 max(1, int(tile.shape[0] * sc))),
                          interpolation=cv2.INTER_CUBIC)
        pad = np.full((TILE + 26, TILE, 3), 255, np.uint8)
        oy, ox = (TILE - tile.shape[0]) // 2, (TILE - tile.shape[1]) // 2
        pad[26 + oy:26 + oy + tile.shape[0], ox:ox + tile.shape[1]] = tile
        # ⚠️ AN OPAQUE ID AND THE FRAME FLAG. Nothing else -- no stratum, no
        # direction, nothing a reader could agree with instead of the ink.
        cv2.putText(pad, f"T{i:02d}" + ("" if ok else "  FRAME?"),
                    (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        tiles.append(pad)
        index.append({"tile": f"T{i:02d}", "stratum": k, "subject": s,
                      **info[s], "frame_delta_grey": round(d, 1),
                      "frame_ok": ok,
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
        p = outdir / f"sheet-{len(sheets)}.png"
        cv2.imwrite(str(p), np.vstack(rows))
        sheets.append(str(p))
        print(f"wrote {p}")

    print(f"frame control: {flagged} of {len(index)} tiles FLAGGED")
    if flagged > len(index) * 0.1:
        print("DEAD: too many windows are not on a notehead.", file=sys.stderr)
        return 2
    Path(a.json).write_text(json.dumps(
        {"label": a.label, "seed": a.seed, "pdf": a.pdf,
         "strata_available": {k: len(v) for k, v in strata.items()},
         "pad_x_spaces": PAD_X, "pad_y_spaces": PAD_Y,
         "sheets": sheets, "index": index}, indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
