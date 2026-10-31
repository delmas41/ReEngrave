"""Debug crops (not tiles): head box orange, hairpin box blue, for the first N hairpin disagreements of a plate's measure json.
    python3 benchmarks/page-ledger-2026-10/s3/peek.py brahms OUTDIR N"""
import json
import pathlib
import sys

from PIL import Image, ImageDraw

from tools.omr.staged import cell_map as CM
from tools.omr.staged import claim_readout as CR
from tools.omr.staged import page_owner as PO

plate, out, n = sys.argv[1], pathlib.Path(sys.argv[2]), int(sys.argv[3])
r = json.load(open(pathlib.Path(__file__).parent / ("measure_%s.json" % plate)))
out.mkdir(parents=True, exist_ok=True)
on = {"brahms": "/private/tmp/s3work/brahms.on.gathered.record.json", "litolff": "/private/tmp/s3work/litolff.on.gathered.record.json"}[plate]
src = CR.resolve_source(on)
rows_all = CR.read_rows(src, r["pages"])
pdf = CR.LIB / CR.edition_info(rows_all)["edition_path"]
imgs = {}
for i, d in enumerate(r["hairpin_disagreements"][:n]):
    pg = d["page"]
    if pg not in imgs:
        (pws, cells), = CM.load_prepared(pdf, [pg], root=CM.ROOT_DEFAULT)
        imgs[pg] = Image.fromarray(pws.page.rgb).convert("RGB")
    b = d["box"]
    hp = [s for s in json.load(open(pathlib.Path(__file__).parent / ("measure_%s.json" % plate)))["arcs"]["rows"] if False]
    x0, y0, x1, y1 = int(b[0] - 250), int(b[1] - 200), int(b[2] + 250), int(b[3] + 200)
    c = imgs[pg].crop((x0, y0, x1, y1)).copy()
    ImageDraw.Draw(c).rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=(255, 140, 0), width=3)
    c.save(out / ("dis_%02d_p%d.png" % (i, pg)))
    print(i, pg, d["key"], d["candidates"])
