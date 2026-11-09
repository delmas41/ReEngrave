"""2.277: crops of given glyph subjects.  usage: look_subjects.py PLATE TAG OUTDIR subj [subj ...]"""
import json, os, pathlib, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from tools.omr.staged import lane_report as LR
plate, tag, out = sys.argv[1:4]
subs = sys.argv[4:]
bp = {}
for line in open(LR.slice_dir(plate, tag) / "observations.jsonl"):
    if '"glyph_box"' in line[:300]:
        o = json.loads(line)
        if o["quantity"] == "glyph_box" and o["subject"] in subs:
            bp[o["subject"]] = o["detail"]["bbox_page_px"]
items = [dict(plate=plate, page=int(s.split("/")[1]), box=bp[s], role="case", subject=s) for s in subs if s in bp]
print(LR.cut_tiles(items, pathlib.Path(out)))
for n, it in enumerate(items, 1):
    print(n, it["subject"])
