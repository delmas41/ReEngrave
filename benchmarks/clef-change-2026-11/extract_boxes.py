"""2.251 carry: every detector glyph box (class, score, page box) of chosen pages, streamed out of a night record (never loaded whole).

python3 work-2.251/extract_boxes.py RECORD PAGES OUT.jsonl     (PAGES "1-16" or "1,3,4,5")
"""
import json, pathlib, sys
sys.path.insert(0, ".")
from tools.omr.staged.judged import iter_array

rec, pages, out = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
want = set()
for part in pages.split(","):
    a, _, b = part.partition("-")
    want.update(range(int(a), int(b or a) + 1))
n = 0
with open(out, "w") as fh:
    for it in iter_array(rec, "observations"):
        if it.get("quantity") != "glyph_box":
            continue
        p = str(it.get("subject", "")).split("/")
        if len(p) < 6 or int(p[1]) not in want:
            continue
        bb = (it.get("detail") or {}).get("bbox_page_px")
        fh.write(json.dumps({"s": it["subject"], "c": it["value"][0], "sc": it.get("score"), "bb": bb}) + "\n")
        n += 1
print("kept", n)
