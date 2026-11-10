"""2.283: crops for the audit report.  usage: crops.py OUTDIR  (reads out/ files of this benchmark; READ-ONLY, files nothing)
Arc-held head boxes (Litolff, from arc_trace_litolff.json) and Sean's Brahms p0 'text' labels that nothing claims. A thin orange box on the page
raster (no overlay of ours beyond the box), 4 staff spaces of air."""
import json
import os
import pathlib
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
from PIL import Image, ImageDraw                              # noqa: E402
from tools.omr.staged import claim_readout as CR              # noqa: E402
from tools.omr.staged import cell_map as CM                   # noqa: E402

here = pathlib.Path(__file__).parent
out = pathlib.Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
SL = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261104-night")


def page_image(plate, page):
    rows = CR.read_rows(SL / plate, [page])
    ed = CR.edition_info(rows)
    (pws, cells), = CM.load_prepared(CR.LIB / ed["edition_path"], [page], root=CM.ROOT_DEFAULT)
    return Image.fromarray(pws.page.rgb).convert("RGB"), rows


def crop(img, box, name, pad=70):
    x0, y0, x1, y1 = [int(v) for v in box]
    cx0, cy0, cx1, cy1 = max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad)
    t = img.crop((cx0, cy0, cx1, cy1)).copy()
    ImageDraw.Draw(t).rectangle([x0 - cx0, y0 - cy0, x1 - cx0, y1 - cy0], outline=(255, 140, 0), width=2)
    t.save(out / name)


# 1. Litolff: head boxes standing on arc-claimed strokes with the biggest off-trace share
arcs = [x for x in json.load(open(here / "out" / "arc_trace_litolff.json")) if x.get("heads")]
arcs.sort(key=lambda x: -x["off_trace_ink"])
need = {}
for x in arcs[:3]:
    need.setdefault(x["page"], []).append(x)
for page, lst in need.items():
    img, rows = page_image("litolff", page)
    box = {o["subject"]: o["detail"]["bbox_page_px"] for o in rows["observations"] if o["quantity"] == "glyph_box"}
    for k, x in enumerate(lst):
        s = x["heads"][0][0]
        crop(img, box[s], "arc_held_head_litolff_p%d_%s.png" % (page, s.replace("/", "-")))
# 2. Brahms p0: Sean's 'text' boxes that nothing claims
tr = json.load(open(here / "out" / "brahms" / "readout.json"))["per_page"]["0"]["truth"]["any"]["misses"]
img, rows = page_image("brahms", 0)
for k, m in enumerate(sorted(tr["text"], key=lambda m: -m["ink_px"])[:3]):
    crop(img, m["rect"], "text_unclaimed_brahms_p0_%d.png" % k, pad=90)
for cls in ("barlineDouble", "slur"):
    for k, m in enumerate(sorted(tr[cls], key=lambda m: -m["ink_px"])[:1]):
        crop(img, m["rect"], "%s_brahms_p0_%d.png" % (cls, k), pad=90)
print(sorted(p.name for p in out.iterdir()))
