"""Does the attribution fault appear in the LONG strokes, where it was found?

⚠️⚠️ THIS IS THE QUESTION THE WHOLE LANE TURNS ON. Measured over both shared
records, the shipped `Q.STEM` rows almost never put a head part-way along a
stroke: of 2,225 SOLO (head, stroke) pairs only ~24 sit further than 0.8 head
heights from an end. But the two lanes that found the fault were both looking
at strokes the SHIPPED reader does not emit -- `OMR_STEM_STROKE`'s column
profile, default OFF, whose recoveries are by construction heads with no
shipped stem.

A component reader fuses a stem into the notehead it touches, so what
`detect_stems` emits is often a short FRAGMENT: on the 24 crops the shipped
strokes ran 1.39-2.20 head heights, where a printed stem is ~3.5 staff spaces.
A fragment that short cannot cross a neighbouring head part-way. A full-length
stroke can.

So this runs the column profile over the same cells and asks the SAME
scale-free question of ITS strokes. If the fault is a property of long strokes
the prediction is a visible mid-stroke tail here and none in the shipped rows.

⚠️ It re-cuts the cells from the PDF -- no weights needed -- and it CHANGES
NOTHING: the reader is imported and run read-only, and no record is written.
⚠️ It is a GATHER-side measurement, so it says nothing about any file.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-stem-stroke-2026-09"))
sys.path.insert(0, str(ROOT / "benchmarks"))
from omr_ledger_extrapolation_shim import stream_array  # noqa: E402


def overlaps(a, b) -> bool:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    return (min(ax0 + aw, bx0 + bw) - max(ax0, bx0) > 0
            and min(ay0 + ah, by0 + bh) - max(ay0, by0) > 0)


def _stats(v):
    v = sorted(v)
    if not v:
        return {}
    def q(p):
        return round(v[min(len(v) - 1, int(p * len(v)))], 3)
    return {"n": len(v), "p25": q(.25), "p50": q(.50), "p75": q(.75),
            "p90": q(.90), "p95": q(.95), "p99": q(.99),
            "max": round(v[-1], 3)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--agree", type=float, default=0.25)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged.gather import _system_local
    from tools.omr.line_detection import (detect_stems, _binary_ink,
                                          _staff_line_spacing)
    from stroke_columns import read_strokes, anchor_to_heads

    pages = []
    for part in a.pages.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            pages += list(range(int(lo), int(hi) + 1))
        else:
            pages.append(int(part))

    heads_by_cell = collections.defaultdict(list)
    shipped_by_cell = collections.defaultdict(list)
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        s = o.get("subject", "")
        if q == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead":
            v = o["value"]
            heads_by_cell["cell/" + "/".join(s.split("/")[1:5])].append(
                tuple(float(x) for x in v[1:5]))
        elif q == "stem":
            v = o.get("value")
            if isinstance(v, (list, tuple)) and len(v) >= 4:
                shipped_by_cell["cell/" + "/".join(s.split("/")[1:5])].append(
                    tuple(float(x) for x in v[:4]))

    def gaps(strokes_by_cell, tag):
        solo, grouped, n_pairs, heights = [], [], 0, []
        for ck, hs in heads_by_cell.items():
            for st in strokes_by_cell.get(ck, []):
                members = [hb for hb in hs if overlaps(st, hb)]
                if not members:
                    continue
                for hb in members:
                    hh = max(hb[3], 1e-6)
                    hcy = hb[1] + hb[3] / 2.0
                    g = min(abs(hcy - st[1]), abs(hcy - (st[1] + st[3]))) / hh
                    (solo if len(members) == 1 else grouped).append(g)
                    heights.append(st[3] / hh)
                    n_pairs += 1
        return {"tag": tag, "pairs": n_pairs,
                "SOLO": _stats(solo), "GROUPED": _stats(grouped),
                "stroke_height_in_head_heights": _stats(heights),
                "solo_beyond": {f"{t:.1f}": sum(1 for x in solo if x > t)
                                for t in (0.8, 1.0, 1.5, 2.0, 3.0)},
                "solo_beyond_frac": {
                    f"{t:.1f}": (round(sum(1 for x in solo if x > t) / len(solo), 4)
                                 if solo else None)
                    for t in (0.8, 1.0, 1.5, 2.0, 3.0)}}

    print("cutting cells ...", flush=True)
    profile_by_cell = collections.defaultdict(list)
    recut_by_cell = collections.defaultdict(list)
    n_cells = 0
    for (pws, cs), pg in zip(prepare_pages(a.pdf, pages, dpi=600), pages):
        local = _system_local(pws.staves)
        for c in cs:
            key = local.get(c.staff_index)
            if key is None:
                continue
            ck = f"cell/{pg}/{key[0]}/{key[1]}/{c.measure_index}"
            n_cells += 1
            recut_by_cell[ck] = [
                (float(d.x_canonical), float(d.y_canonical),
                 float(d.width_canonical), float(d.height_canonical))
                for d in detect_stems(c)]
            src = (c.image_no_staff
                   if getattr(c, "image_no_staff", None) is not None
                   else c.image)
            sp = _staff_line_spacing(c)
            if src is None or src.size == 0 or sp <= 1.0:
                continue
            bands = read_strokes(_binary_ink(src), sp, c.width,
                                 agree_spaces=a.agree)
            for st, _h, _s, _d in anchor_to_heads(
                    bands, heads_by_cell.get(ck, []), sp):
                profile_by_cell[ck].append(
                    (float(st.x_canonical), float(st.y_canonical),
                     float(st.width_canonical), float(st.height_canonical)))
    print(f"cut {n_cells} cells", flush=True)

    out = {"label": a.label, "record": a.record, "pdf": a.pdf,
           "pages": pages, "cells_cut": n_cells,
           "SHIPPED_from_record": gaps(shipped_by_cell, "record"),
           "SHIPPED_recut_control": gaps(recut_by_cell, "recut"),
           "PROFILE_OMR_STEM_STROKE": gaps(profile_by_cell, "profile")}
    print(json.dumps(out, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
