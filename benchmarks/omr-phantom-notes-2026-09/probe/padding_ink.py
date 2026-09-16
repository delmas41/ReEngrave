"""What does the PRINT hold in the measure cell's PADDING, above and below?

⚠️⚠️ WHY THIS EXISTS: `print_ink.census` LOOKS AT THE STAFF BAND ONLY.  Its
band is `five[0] - 0.6*sp .. five[4] + 0.6*sp`, so "the print shows ONE
REST-SHAPED MARK and nothing else" is a statement about the five lines and a
sliver of air — **it never looked at the 4-6 staff spaces of padding a measure
cell is actually cut with**.  FINDINGS §4 partitions 14 phantom notes as
"OUTSIDE the staff entirely" and attributes them to that padding and *"the
neighbour it reaches"*; nothing has yet asked the print whether a neighbour is
there.

For the top staff of a system there IS no neighbour above, so the claim is
falsifiable in the strongest way available here: if the print holds nothing in
staff 0's upper padding at a bar where we write `A6`, the padding-from-a-
neighbour story does not cover that bar.

⚠️ IT REPORTS INK, NOT A CLASSIFICATION.  `print_ink.looks_like` records at
length that an absolute staff step read off this crop drifts 1.4 steps across
one system, so nothing here names a glyph.  It reports where blobs are and how
big, in the staff's own units, and leaves the reading to a human with the
`bar_crop.py` cut beside it.

⚠️ REACH IS PRINTED FIRST and `--check` exits non-zero when the crop's grid
disagrees with the exporter's map, because a bar index read off a disagreeing
grid names the wrong bar — `silent_bars.py`'s own refusal, inherited.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from bar_crop import barlines, staves_of          # noqa: E402
from locate import SYSMAP                          # noqa: E402
from print_ink import MIN_BLOB_PX, _strip_lines    # noqa: E402

import scipy.ndimage as ndi                        # noqa: E402

#: `measure_extractor.PAD_ABOVE_STAFF_LINES` -- the cell is the staff plus four
#: to six staff spaces of air.  Restated rather than imported for the reason
#: `contest_join.py` gives (importing the pipeline drags in the detector).
PAD_SPACES = 6.0

#: Ink this far outside the staff cannot be the staff's own notation and is
#: what the padding reaches.  0.6 is where `print_ink.census` stops looking.
BAND_EDGE_SPACES = 0.6


def padding_blobs(im, five, x0, x1, side, pad=PAD_SPACES):
    """Blobs in the padding on one side of a staff, in that staff's own units.

    `step` is measured from the staff's BOTTOM line, one step per half space,
    exactly as `print_ink.census` measures it -- so the numbers are comparable
    with the exported file's own steps even though neither is trustworthy to
    better than a step and a half (see `print_ink.looks_like`).
    """
    sp = (five[4] - five[0]) / 4.0
    if side == "above":
        y0 = int(five[0] - pad * sp)
        y1 = int(five[0] - BAND_EDGE_SPACES * sp)
    else:
        y0 = int(five[4] + BAND_EDGE_SPACES * sp)
        y1 = int(five[4] + pad * sp)
    # ⚠️⚠️ A CROP CAN SIMPLY NOT HAVE THE PADDING, AND THAT MUST NOT READ AS
    # "the print holds nothing there".  These crops are system images pulled
    # out of an HTML artefact; nobody promised them 6 staff spaces of air above
    # the top staff.  The available fraction is returned with the blobs, and a
    # band with less than half of what was asked for is reported TRUNCATED.
    want = y1 - y0
    cy0, cy1 = max(0, y0), min(im.height, y1)
    have = max(0, cy1 - cy0)
    if have <= 0:
        return {"blobs": [], "have_spaces": 0.0, "step_reach": None,
                "want_spaces": round(want / sp, 2), "truncated": True}
    y0, y1 = cy0, cy1
    a = np.asarray(im.convert("L"))[y0:y1, int(x0) + 3:int(x1) - 3]
    ink = _strip_lines(a < 128)
    lab, n = ndi.label(ink)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if ys.size < MIN_BLOB_PX:
            continue
        cy = y0 + (ys.min() + ys.max()) / 2.0
        out.append(dict(
            h_spaces=round((ys.max() - ys.min() + 1) / sp, 2),
            w_spaces=round((xs.max() - xs.min() + 1) / sp, 2),
            step=round((five[4] - cy) / (sp / 2.0), 2),
            px=int(ys.size)))
    reach = ((five[4] - y0) / (sp / 2.0) if side == "above"
             else (five[4] - y1) / (sp / 2.0))
    return {"blobs": sorted(out, key=lambda d: -d["px"]),
            "have_spaces": round(have / sp, 2),
            "want_spaces": round(want / sp, 2),
            "step_reach": round(reach, 1),
            "truncated": have < 0.5 * want}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--crop", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--system", type=int, required=True)
    ap.add_argument("--sysmap", default=str(SYSMAP))
    ap.add_argument("--bl-frac", type=float, default=0.70)
    ap.add_argument("--bars", default=None,
                    help="comma list of (staff:bar) to report, e.g. 0:9,0:10")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    im = Image.open(args.crop)
    five = staves_of(im)
    bl = barlines(im, five[0][0], five[-1][4], frac=args.bl_frac)

    smap = json.load(open(args.sysmap))
    sysrow = next((s for s in smap["systems"]
                   if s["page"] == args.page and s["system"] == args.system),
                  None)
    n_map_staves = len(sysrow["staves"]) if sysrow else 0
    n_map_bars = (max(st["n_measures"] for st in sysrow["staves"])
                  if sysrow else 0)
    n_bars = len(bl) - 1
    print(f"REACH  crop staves={len(five)} vs map {n_map_staves}; "
          f"crop bars={n_bars} vs map {n_map_bars}")
    ok = len(five) == n_map_staves and n_bars == n_map_bars
    if not ok:
        print("  REFUSED: a bar index read off a disagreeing grid names the "
              "wrong bar.")
        if args.check:
            return 2
        return 1

    targets = []
    if args.bars:
        for tok in args.bars.split(","):
            st, br = tok.split(":")
            targets.append((int(st), int(br)))
    else:
        targets = [(st, br) for st in range(len(five))
                   for br in range(n_bars)]

    print(f"\nPADDING INK  (staff band is step -1.2 .. 9.2; padding reported "
          f"out to +/-{PAD_SPACES} spaces = step +/-{PAD_SPACES * 2:.0f})")
    rows = []
    for st, br in targets:
        f = five[st]
        x0, x1 = bl[br], bl[br + 1]
        above = padding_blobs(im, f, x0, x1, "above")
        below = padding_blobs(im, f, x0, x1, "below")
        rows.append({"staff": st, "bar": br,
                     "above": above, "below": below})
        def fmt(r):
            tag = (f"[{r['have_spaces']:.1f}/{r['want_spaces']:.1f}sp, "
                   f"reaches step {r['step_reach']}"
                   + (", TRUNCATED]" if r["truncated"] else "]"))
            if not r["blobs"]:
                return f"{tag} nothing"
            return tag + " " + "; ".join(
                f"step{b['step']:+.1f} {b['w_spaces']}x{b['h_spaces']}sp "
                f"{b['px']}px" for b in r["blobs"][:4])
        print(f"  staff {st} bar {br:>2}")
        print(f"     above: {fmt(above)}")
        print(f"     below: {fmt(below)}")

    out = HERE.parent / "out" / f"padding-p{args.page}s{args.system}.json"
    out.write_text(json.dumps(rows, indent=1))
    print(f"\nwrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
