"""read_box on every clef* box of the Litolff slice pages (clef-sized), with the cell map lines (uncorrected raster: a few px off)."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251")); sys.path.insert(0, os.getcwd())
import crops
from tools.omr.staged import clef_pagewide as CP
plate = sys.argv[1]
seen = set(); inks = {}
for line in open(f"library/_shared-records/lane-report-slices-20261029-night/{plate}/observations.jsonl"):
    if '"glyph_box"' not in line or '"clef' not in line:
        continue
    r = json.loads(line)
    if r["quantity"] != "glyph_box" or not r["value"][0].startswith("clef"):
        continue
    _, pg, s, sl, c, gi = r["subject"].split("/"); pg, s, sl = int(pg), int(s), int(sl)
    bb = r["detail"]["bbox_page_px"]
    key = (pg, s, sl, round(bb[0] / 8))
    if key in seen:
        continue
    seen.add(key)
    d = crops.cmap(plate, pg)
    st = sorted([t for t in d["staves"] if t["system_index"] == s], key=lambda t: t["line_ys"][0])
    if sl >= len(st):
        continue
    ly = st[sl]["line_ys"]; sp = (ly[4] - ly[0]) / 4
    if (bb[3] - bb[1]) / sp < 2.0:
        continue
    if pg not in inks:
        inks[pg] = np.asarray(crops.page_img(plate, pg).convert("L")) < 128
    ll = CP.local_lines(inks[pg], ly, sp, bb[0])
    got = CP.read_box(r["value"][0], bb, inks[pg], ll, sp)
    print(pg, s, sl, c, round(bb[0]), r["value"][0], round(r["score"], 2), got["passed"], got["why"], got["kind"])
