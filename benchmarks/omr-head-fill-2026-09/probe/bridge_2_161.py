"""ROADMAP 2.161 -- PROBE (no detector, no gather): `gather.head_stem_bridge` (and the 2.148 slit on the bridged box) for
EVERY notehead box of a night slice with no `Q.STEM` row touching its box, on cells re-cut exactly as production cuts them
(`pipeline.prepare_pages`; stems_2_161.py's control: 62/62 cells re-cut reproduce the record's `Q.STEM` rows exactly).
This is the reading the lane's GATHER files as `Q.NOTEHEAD_INK.detail.stem_bridge`; the night records predate it, so the
replay injects it from here.
usage: bridge_2_161.py SLICEDIR DOC OUT.json [PAGES...]"""
import collections
import glob
import json
import os
import sys

sys.path.insert(0, ".")
from tools.omr.staged.pipeline import prepare_pages  # noqa: E402
from tools.omr.line_detection import _binary_ink  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged.geometry import stem_touches_head  # noqa: E402

PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
SD, DOC, OUT = sys.argv[1:4]
ONLY = {int(p) for p in sys.argv[4:]}
out = json.load(open(OUT)) if os.path.exists(OUT) else {}
cnt = collections.Counter()
for p in sorted(glob.glob(os.path.join(SD, DOC, "p*.observations.jsonl"))):
    pg = int(os.path.basename(p)[1:3])
    if ONLY and pg not in ONLY:
        continue
    cellrows = collections.defaultdict(lambda: collections.defaultdict(list))
    for line in open(p):
        if not any(q in line for q in ('"glyph_box"', '"stem"', '"cell_box"', '"cell_staff_space"')):
            continue
        o = json.loads(line)
        s = o["subject"]
        ck = s if s.startswith("cell/") else "cell/" + s[6:].rsplit("/", 1)[0]
        if o["quantity"] in ("glyph_box", "stem", "cell_box", "cell_staff_space"):
            cellrows[ck][o["quantity"]].append(o)
    (pws, cells), = prepare_pages(PDFS[DOC], [pg])
    for ck, cr in cellrows.items():
        if not cr["cell_box"] or not cr["cell_staff_space"]:
            continue
        cb = cr["cell_box"][0]["value"]
        cand = [c for c in cells if c.bbox_page_px and max(abs(a - b) for a, b in zip(c.bbox_page_px, cb)) < 2.0]
        if len(cand) != 1:
            cnt["cell_unmatched"] += 1
            continue
        c = cand[0]
        sp = float(cr["cell_staff_space"][0]["value"])
        stems = [tuple(o["value"]) for o in cr["stem"]]
        boxes = [(o["subject"], o["value"]) for o in cr["glyph_box"]]
        ink = None
        for s, (name, x, y, w, h) in boxes:
            if not str(name).lower().startswith("notehead"):
                continue
            hb = (x, y, w, h)
            cnt["heads"] += 1
            if any(stem_touches_head(st, hb) for st in stems):
                continue
            cnt["no_touching_stem"] += 1
            if ink is None:
                ink = _binary_ink(c.image_no_staff) if c.image_no_staff is not None else None
            others = [(n2, (x2, y2, w2, h2)) for s2, (n2, x2, y2, w2, h2) in boxes if s2 != s]
            b = G.head_stem_bridge(ink, hb, stems, sp, others)
            if b is None:
                continue
            cnt["bridged"] += 1
            iw = G.head_interior_white(getattr(c, "binary", None), b["bridged_box"])
            out[s] = {**b, "name": name, "sp": sp, "head_box": [x, y, w, h], "interior_white_bridged": iw}
    print(DOC, "p%02d" % pg, dict(cnt), flush=True)
    json.dump(out, open(OUT, "w"))
print(DOC, "done", dict(cnt))
