#!/usr/bin/env python3
"""l282_extract: ONE streamed read of a record -> every beam stroke (CV and detector), its ink
reading, and the cell's canonical->page calibration. ROADMAP 2.82. A reading probe: it decides
nothing and changes no product code.

WHY STREAMED. The overnight Brahms record is 5.3 GB (`record_io.load_record` is ~6.6x the file);
`ijson` over `record.observations.item` keeps only the rows named here. The same reader
`l281_extract.py` used (and bit-compared against `readout.load_run` there). The small
(GATHER+ADJUDICATE) records go through the same code, so the two are one measurement.

Per CELL (`cell/<page>/<system>/<staff>/<measure>`):
  strokes   {obs id: {box (canonical x,y,w,h), reader, score}}   (`Q.BEAM_STROKE`)
  ink       {beam_row_id: the `Q.BEAM_STROKE_INK` detail}         (thickness, line_px, ratio, sagitta, ends)
  ink_abs   {beam_row_id: reason}                                  (the readings that abstained)
  calib     [x0, y0, up]  page = (x0 + cx/up, y0 + cy/up): the page origin of the cell and its
            upscale, fitted by median over the cell's own `Q.GLYPH_BOX` rows (`_page_box`'s inverse;
            the record carries bbox_page_px per glyph, not the upscale)
  space     `Q.CELL_STAFF_SPACE` (canonical px)

    python3 l282_extract.py --record R --out ext.json [--pages 0,1]
"""
import argparse
import collections
import json
import statistics
import sys
import time
from pathlib import Path

import ijson

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged.record import Q  # noqa: E402


def page_of(subject):
    p = subject.split("/")
    try:
        return int(p[1])
    except (IndexError, ValueError):
        return None


def cell_key(subject):
    p = subject.split("/")
    return "cell/" + "/".join(p[1:5])


def extract(path, pages=None):
    strokes = collections.defaultdict(dict)
    ink = {}
    ink_abs = {}
    fits = collections.defaultdict(list)       # cell -> [(up, x0, y0)]
    heads = collections.defaultdict(list)      # cell -> [[x, y, w, h]] canonical, every notehead box
    space = {}
    n = 0
    t0 = time.time()
    with open(path, "rb") as fh:
        for o in ijson.items(fh, "record.observations.item", use_float=True):
            n += 1
            q = o["quantity"]
            if q not in (Q.BEAM_STROKE, Q.BEAM_STROKE_INK, Q.GLYPH_BOX, Q.CELL_STAFF_SPACE):
                continue
            s = o["subject"]
            if pages is not None and page_of(s) not in pages:
                continue
            if q == Q.BEAM_STROKE:
                strokes[cell_key(s)][o["id"]] = {"box": o["value"], "reader": o.get("reader"),
                                                 "score": o.get("score")}
            elif q == Q.BEAM_STROKE_INK:
                d = o.get("detail") or {}
                ink[d.get("beam_row_id")] = {"cell": cell_key(s), **{k: d.get(k) for k in (
                    "thickness_px", "line_px", "thickness_ratio", "thickness_spaces",
                    "sagitta_spaces", "end_stems", "columns", "cover", "band", "core")}}
            elif q == Q.GLYPH_BOX:
                v = o["value"]
                d = o.get("detail") or {}
                pb = d.get("bbox_page_px")
                if isinstance(v, list) and len(v) == 5 and str(v[0]).startswith("notehead"):
                    heads[cell_key(s)].append([v[1], v[2], v[3], v[4]])
                if not (isinstance(v, list) and len(v) == 5 and pb):
                    continue
                cw = v[3]
                pw = pb[2] - pb[0]
                if cw and cw > 4 and pw > 4:
                    up = cw / pw
                    fits[cell_key(s)].append((up, pb[0] - v[1] / up, pb[1] - v[2] / up))
            elif q == Q.CELL_STAFF_SPACE:
                space.setdefault(cell_key(s), o["value"])
    # abstentions of the ink reader
    with open(path, "rb") as fh:
        for a in ijson.items(fh, "record.abstentions.item", use_float=True):
            if a["quantity"] != Q.BEAM_STROKE_INK:
                continue
            if pages is not None and page_of(a["subject"]) not in pages:
                continue
            d = a.get("detail") or {}
            ink_abs[d.get("beam_row_id")] = {"cell": cell_key(a["subject"]), "reason": a.get("reason"),
                                             "note": d.get("note")}
    calib = {}
    for c, v in fits.items():
        calib[c] = [round(statistics.median(x[1] for x in v), 2), round(statistics.median(x[2] for x in v), 2),
                    round(statistics.median(x[0] for x in v), 5), len(v)]
    print(f"{n} observations, {sum(len(v) for v in strokes.values())} strokes in {len(strokes)} cells, "
          f"{len(ink)} ink rows, {len(ink_abs)} ink abstentions, {len(calib)} calibrated cells, "
          f"{time.time() - t0:.0f}s", flush=True)
    return {"strokes": strokes, "ink": ink, "ink_abs": ink_abs, "calib": calib, "space": space,
            "heads": heads}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", default=None)
    a = ap.parse_args()
    pages = {int(x) for x in a.pages.split(",")} if a.pages else None
    res = extract(a.record, pages)
    Path(a.out).write_text(json.dumps(res, separators=(",", ":"), default=str))
    print(f"wrote {a.out} ({Path(a.out).stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
