"""GO AND LOOK AT THE INK -- render the actual bar behind each candidate.

Joins an exported bar `(part, measure)` back to the CELL it came from, through
`export.build`'s own StaffRuns (called, never re-derived, so the join cannot
drift from the file), and crops that cell's `Q.CELL_BOX` page rectangle out of
a render of the PDF at the gather's own DPI.

⚠️ It prints, beside every crop, EVERY detection the record holds inside that
cell with its class and confidence -- because the question is not only "what
does the page print" but "what did the detector fire on". A crop with no
inventory beside it cannot answer the second half.

⚠️ POSITIVE CONTROL: it reports how many candidate bars it could locate a
CELL_BOX for before it crops anything. `Q.CELL_BOX` abstains on some cells, and
a silently skipped bar is how a crop set comes to show only the easy cases.

    python3 .../crops.py --record R.json --pdf P.pdf --cands C.json --out DIR
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as sx           # noqa: E402
from tools.omr.staged.record import Q               # noqa: E402

GATHER_DPI = 600   # tools/omr/staged/__main__.py's own default


def locate(result):
    """{(part_id, measure): (page, system, staff, cell_index, box)}"""
    rec = sx.Record(result)
    parts = sx.build(rec)[0]
    out = {}
    for pi, part in enumerate(parts):
        n = 0
        for run in part:
            for c in range(run.n_measures):
                n += 1
                out[(f"P{pi + 1}", n)] = (run.page, run.system, run.staff, c,
                                          run.cell_boxes.get(c))
    return out


def detections_by_cell(result):
    """{(page, system, staff, cell): [(class, conf, bbox)]} from the RECORD."""
    boxes = collections.defaultdict(list)
    conf = {}
    for o in result["record"]["observations"]:
        if o["quantity"] == Q.GLYPH_CONF:
            conf[o["subject"]] = o["value"]
    for o in result["record"]["observations"]:
        if o["quantity"] != Q.GLYPH_BOX:
            continue
        # glyph/<page>/<system>/<staff>/<cell>/<glyph>
        bits = o["subject"].split("/")
        if bits[0] != "glyph" or len(bits) < 6:
            continue
        key = (int(bits[1]), int(bits[2]), int(bits[3]), int(bits[4]))
        # value is [class, x0, y0, x1, y1] in CANONICAL cell coordinates;
        # detail carries the page pixels.
        cls, *bbox = o["value"]
        pagebox = (o.get("detail") or {}).get("bbox_page_px")
        boxes[key].append((cls, conf.get(o["subject"]), pagebox or bbox,
                           o["subject"]))
    return boxes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--cands", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", help="comma list of part:measure to crop")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--pad", type=int, default=40)
    a = ap.parse_args()

    result = json.load(open(a.record))
    where = locate(result)
    dets = detections_by_cell(result)
    cands = json.load(open(a.cands))

    print(f"candidate bars                      {len(cands)}")
    located = [c for c in cands if (c["part"], c["measure"]) in where]
    print(f"  located in the exporter's runs    {len(located)}")
    boxed = [c for c in located if where[(c["part"], c["measure"])][4]]
    print(f"  carrying a Q.CELL_BOX             {len(boxed)}")
    if not boxed:
        raise SystemExit("no candidate carries a cell box -- dead instrument")

    want = None
    if a.only:
        want = set()
        for t in a.only.split(","):
            p, m = t.split(":")
            want.add((p, int(m)))

    import fitz  # PyMuPDF
    from PIL import Image
    import io
    doc = fitz.open(a.pdf)
    zoom = GATHER_DPI / 72.0
    rendered = {}
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)

    shown = 0
    for c in boxed:
        key = (c["part"], c["measure"])
        if want is not None and key not in want:
            continue
        if want is None and shown >= a.limit:
            break
        page, system, staff, cell, box = where[key]
        if page not in rendered:
            pm = doc[page].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            rendered[page] = Image.open(io.BytesIO(pm.tobytes("png")))
        img = rendered[page]
        x0, y0, x1, y1 = box
        clip = (max(0, int(x0) - a.pad), max(0, int(y0) - a.pad),
                min(img.width, int(x1) + a.pad),
                min(img.height, int(y1) + a.pad))
        name = f"{c['part']}-m{c['measure']}-p{page}s{system}st{staff}c{cell}.png"
        img.crop(clip).save(str(outdir / name))
        inv = dets.get((page, system, staff, cell), [])
        print(f"\n--- {name}")
        print(f"    exported: {c['sounding']}/{c['bar_len']} "
              f"{[(e['type'], e['pitch']) for e in c['events']]}")
        print(f"    cell box page px: {[round(v) for v in box]}")
        print(f"    {len(inv)} detections in the record:")
        for cls, cf, bbox, sub_key in sorted(
                inv, key=lambda t: -(t[1] or 0)):
            bb = [round(v) for v in bbox] if bbox else None
            cfs = "-" if cf is None else f"{cf:.3f}"
            print(f"      {str(cls):<28} {cfs:<7} {bb}")
        shown += 1

    print(f"\ncropped {shown} bars -> {outdir}")


if __name__ == "__main__":
    main()
