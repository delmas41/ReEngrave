"""WHAT DOES THE PRINT HOLD in the bars Sean flagged?

⚠️ THIS IS THE QUESTION THE WIP BRANCH NEVER ASKED. `claude/note-where-silence-
is-printed` measures shape and position over ALL 2,347 gathered noteheads and
finds 20 that look like whole rests. Sean's population is 43 UNDERFULL BARS.
Those are different sets, and nothing on that branch joins them.

So: for each such bar, take the printed staff band out of the committed system
crop, erase the five staff-line rows, and count what is left. A bar the page
prints SILENT holds one small squat blob hanging under the fourth line; a bar
the page prints MUSIC holds several blobs, or one that is notehead-shaped.

⚠️ IT IS A CENSUS, NOT A CLASSIFIER, and the numbers are reported so a human
can look at the crop beside them. The shape thresholds only LABEL the rows;
nothing is decided on them and no code reads this.

⚠️ REACH: it can only run where the crop's own barline grid agrees with the
exporter's system map, because a bar index read off a grid that disagrees names
the wrong bar. On the committed crops that is page 4 system 0 and no other, so
this speaks about 13 of the 43 underfull bars and says so.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import scipy.ndimage as ndi
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bar_crop import barlines, staves_of  # noqa: E402
from locate import SYSMAP, index  # noqa: E402
from population import ARTEFACT, bars  # noqa: E402
from steps import step_of  # noqa: E402

#: A staff line's ink is SHORT in the vertical direction; a notehead's is not.
#: ⚠️ ERASING FIXED ROWS DOES NOT WORK ON THIS PLATE and the first version of
#: this probe did exactly that: CLAUDE.md records a scanned staff tilting and
#: bowing 8-17 page px across its width, so a constant comb leaves long
#: horizontal fragments, and the census then reported blobs 6-17 STAFF SPACES
#: WIDE -- staff-line residue wearing a glyph's name. The run-length rule is
#: tilt-independent because it asks about one column at a time. At this scale
#: a printed line measures 2-4 px and a notehead ~15.
LINE_MAX_RUN_PX = 6
#: Ink smaller than this is speck, not notation (a whole rest here is ~200 px).
MIN_BLOB_PX = 40


def _strip_lines(ink):
    """Delete every vertical ink run short enough to be a staff line."""
    out = ink.copy()
    h, w = ink.shape
    for x in range(w):
        col = ink[:, x]
        y = 0
        while y < h:
            if not col[y]:
                y += 1
                continue
            y2 = y
            while y2 < h and col[y2]:
                y2 += 1
            if y2 - y <= LINE_MAX_RUN_PX:
                out[y:y2, x] = False
            y = y2
    return out


def census(im, five, x0, x1, pad_spaces=0.6):
    """Every ink blob inside ONE bar of ONE staff, with the staff lines gone."""
    sp = (five[4] - five[0]) / 4.0
    y0 = int(five[0] - pad_spaces * sp)
    y1 = int(five[4] + pad_spaces * sp)
    a = np.asarray(im.convert("L"))[y0:y1, int(x0) + 3:int(x1) - 3]
    ink = _strip_lines(a < 128)
    lab, n = ndi.label(ink)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        if ys.size < MIN_BLOB_PX:
            continue
        hh = (ys.max() - ys.min() + 1) / sp
        ww = (xs.max() - xs.min() + 1) / sp
        cy = y0 + (ys.min() + ys.max()) / 2.0
        out.append(dict(h_spaces=round(hh, 2), w_spaces=round(ww, 2),
                        aspect=round(ww / hh, 2) if hh else None,
                        step=round((five[4] - cy) / (sp / 2.0), 2),
                        px=int(ys.size)))
    return sorted(out, key=lambda d: -d["px"])


def looks_like(b):
    """A LABEL for the human, never a decision.

    ⚠️⚠️ THE STAFF STEP IS DELIBERATELY NOT IN THIS RULE, AND THAT IS A
    MEASUREMENT RATHER THAN A CHOICE. A whole rest hangs under the fourth line
    from the bottom, so its centre should read step 5.5 in every bar of a
    staff. Measured on this crop it does not: on the Flute staff the SAME mark
    reads 3.78, 4.03, 4.29, 4.54, 4.80, 5.06, 5.18 across seven consecutive
    bars -- a MONOTONIC DRIFT of 1.4 steps left to right, which is the scan
    warp CLAUDE.md already prices at 8-17 page px across a staff's width,
    arriving in this probe's own straight five-line model. Between staves the
    offsets are larger still (the Oboe staff reads the same mark near step 0,
    the Trumpet staff near 6.5).

    So an absolute step read off this instrument carries systematic error of
    order a step and a half, which is more than the gap between a whole rest
    (5.5) and a half rest (4.5). It may not be used to tell those apart, and
    this rule does not try. What IS robust is the SHAPE -- a rest of any value
    is a squat wide bar and a notehead is not -- and the fact that the mark
    repeats in the same place bar after bar.
    """
    if b["h_spaces"] < 0.95 and b["aspect"] > 1.4:
        return "REST-SHAPED"
    if 0.7 <= b["h_spaces"] <= 1.6 and 0.6 <= b["aspect"] <= 1.8:
        return "notehead-shaped"
    return "other ink"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--crop", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--system", type=int, required=True)
    ap.add_argument("--xml", default=str(ARTEFACT))
    ap.add_argument("--sysmap", default=str(SYSMAP))
    ap.add_argument("--bl-frac", type=float, default=0.80)
    ap.add_argument("--json-out")
    a = ap.parse_args()

    where, _ = index(json.loads(Path(a.sysmap).read_text()))
    rows = bars(a.xml)
    want = []
    for r in rows:
        w = where.get((r["part"], r["number"]))
        if not w or w["page"] != a.page or w["system"] != a.system:
            continue
        if not (r["n_notes"] == 1 and r["n_pitched"] == 1):
            continue
        e = r["events"][0]
        if not (e["dur"] and r["barlen"] and e["dur"] < r["barlen"]):
            continue
        want.append((r, w, e))

    im = Image.open(a.crop)
    sts = staves_of(im)
    bl = barlines(im, sts[0][0], sts[-1][4], frac=a.bl_frac)
    n_staves_map = len({w["staff"] for (_, w, _) in
                        [(r, where[(r["part"], r["number"])], None)
                         for r in rows
                         if where.get((r["part"], r["number"]), {}).get("page") == a.page
                         and where.get((r["part"], r["number"]), {}).get("system") == a.system]})
    n_bars_map = max((w["n_bars_in_system"] for (_, w, _) in want), default=0)

    print(f"REACH  crop staves={len(sts)}  map staves={n_staves_map}")
    print(f"REACH  crop bars={len(bl)-1}  map bars={n_bars_map}")
    print(f"REACH  underfull lone-pitched bars on this system={len(want)}")
    if not want:
        print("DEAD: this system holds none of the population", file=sys.stderr)
        return 2
    if len(sts) != n_staves_map or len(bl) - 1 != n_bars_map:
        print("REFUSED: the crop's own grid disagrees with the exporter's map; "
              "a bar index read off it would name the wrong bar.", file=sys.stderr)
        return 3

    recs = []
    for r, w, e in sorted(want, key=lambda t: (t[1]["staff"], t[1]["bar_in_system"])):
        b = w["bar_in_system"]
        blobs = census(im, sts[w["staff"]], bl[b], bl[b + 1])
        rec = dict(part=r["part"], measure=r["number"], staff=w["staff"], bar=b,
                   ours_pitch=e["pitch"], ours_type=e["type"],
                   ours_step=step_of(e["pitch"], w.get("clef")),
                   n_blobs=len(blobs), blobs=blobs[:4])
        recs.append(rec)
        tags = "; ".join(looks_like(x) for x in blobs[:3])
        print(f"  {r['part']:>4} m{r['number']:<4} staff {w['staff']:<2} bar {b:<3}"
              f" ours={str(e['pitch']):<4} {str(e['type']):<8}"
              f" step={rec['ours_step']:<4} | print: {len(blobs)} blob(s)  {tags}")
        for x in blobs[:3]:
            print(f"        h={x['h_spaces']:<5} w={x['w_spaces']:<5} "
                  f"aspect={x['aspect']:<5} step={x['step']:<6} px={x['px']}")

    lone_rest = [r for r in recs if r["n_blobs"] == 1
                 and looks_like(r["blobs"][0]) == "REST-SHAPED"]
    print()
    print(f"bars whose PRINT holds exactly ONE blob and it is REST-SHAPED: "
          f"{len(lone_rest)} of {len(recs)}")
    print(f"bars whose PRINT holds two or more blobs               : "
          f"{sum(1 for r in recs if r['n_blobs'] >= 2)} of {len(recs)}")

    if a.json_out:
        Path(a.json_out).write_text(json.dumps(recs, indent=1))
        print(f"wrote {a.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
