"""2.280 probe 18 (EXPLORATORY, ours; not the pre-registered micro test): run the SHIPPED head-anchored ruler (`gather.measure_head_stem`, 2.58d) on the page raster for
every stratum-A head (83: rests / accidentals / real heads by my label). What does it say, by label? usage: p18_ruler_all.py plate"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.pipeline import prepare_pages          # noqa: E402
from tools.omr.staged.gather import measure_head_stem        # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDFS = {"litolff": (LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 15.75),
        "brahms": (LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 27.3)}
plate = sys.argv[1]
PDF, SP = PDFS[plate]
R = json.load(open("out/2.280/rerunfull_%s.json" % plate))
L = json.load(open("out/2.280/labels_%s.json" % plate))
by_page = collections.defaultdict(list)
for s in L:
    by_page[R[s]["page"]].append(s)
ct = collections.Counter()
out = {}
for pg in sorted(by_page):
    (pws, cells), = prepare_pages(PDF, [pg])
    rgb = pws.page.rgb
    gray = rgb if rgb.ndim == 2 else rgb[..., :3].mean(axis=2)
    ink = gray < 128
    for s in by_page[pg]:
        res = measure_head_stem(ink, tuple(R[s]["page_box"]), SP)
        ct[(L[s], res["direction"])] += 1
        out[s] = dict(label=L[s], direction=res["direction"], up=res["up_ext"], down=res["down_ext"])
    print("p%d done" % pg, flush=True)
json.dump(out, open("out/2.280/ruler_%s.json" % plate, "w"))
print(plate, "shipped ruler on the 83, by my label (direction)")
for k, v in sorted(ct.items()):
    print("   %s %-5s %d" % (k[0], k[1], v))
