"""ROADMAP 2.176b census -- from the per-page probe JSONs (probe_2_176b_tile8.py; CURRENT main code, 2.173 ON), list every
notehead-class box (any class) that is NOT refused and lies on a printed meter's numerals, by witness:
  a  the box covers >= 0.5 of the smaller of itself and a `timeSig*` box of the same cell (any staff of the system)
  d  (timeSig boxes AND boxes 2.173 already refused as `on_a_read_meter` mark the column)
  d  the box's page-x centre is within 0.8 of its width of the centre of a `timeSig*` box another staff of the system has at this cell index
only in a cell where a meter reader READ a meter (cell 0: meter_template / meter_ocr at any staff of the system; cell k: *_at_bar with that cell).
Also lists the controls the rule must NOT touch: unrefused heads in a meter-read cell whose left edge is within CTRL_GAP page px of the right edge of
the numeral column (the first note after a meter).
usage: census_2_176b.py PROBE_DIR DOC OUT.json"""
import glob
import json
import re
import sys
from collections import defaultdict

PD, DOC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
rows = []
for p in sorted(glob.glob("%s/probe_%s_*.json" % (PD, DOC)), key=lambda s: int(re.findall(r"_(\d+)\.json", s)[0])):
    pg = int(re.findall(r"_(\d+)\.json", p)[0])
    d = json.load(open(p))
    read_cells = defaultdict(set)  # (page, system) -> {cell}
    for subj, q, val, cell in d["meters"]:
        s = subj.split("/")
        key = (int(s[1]), int(s[2]))
        if q in ("meter_template", "meter_ocr"):
            read_cells[key].add(0)
        elif cell is not None:
            read_cells[key].add(int(cell))
    ts = defaultdict(list)  # (page, system, cell) -> [(staff, xc, w, subject)]
    heads = []
    for g, (val, bb) in d["boxes"].items():
        s = g.split("/")
        if len(s) < 6 or not bb:
            continue
        key = (int(s[1]), int(s[2]), int(s[4]))
        cls = str(val[0])
        if cls.startswith("timeSig"):
            ts[key].append((int(s[3]), (bb[0] + bb[2]) / 2.0, bb[2] - bb[0], g, bb))
        elif cls.startswith("notehead"):
            heads.append((g, key, int(s[3]), cls, bb))
    for g, key, staff, cls, bb in heads:  # witness m below: boxes 2.173 already refused as meter ink also mark the column
        pass
    for g, key, staff, cls, bb in heads:
        r0 = d["refusal"].get(g)
        if r0 and r0[0] is True and r0[1] == "on_a_read_meter":
            ts[key].append((staff, (bb[0] + bb[2]) / 2.0, bb[2] - bb[0], g, bb))
    for g, key, staff, cls, bb in heads:
        if key[2] not in read_cells.get(key[:2], ()):
            continue
        ref = d["refusal"].get(g)
        if ref and ref[0] is True:
            continue
        w = bb[2] - bb[0]
        xc = (bb[0] + bb[2]) / 2.0
        wit = None
        for st, tx, tw, tg, tb in ts.get(key, []):
            ix = max(0.0, min(bb[2], tb[2]) - max(bb[0], tb[0]))
            iy = max(0.0, min(bb[3], tb[3]) - max(bb[1], tb[1]))
            small = min((bb[2] - bb[0]) * (bb[3] - bb[1]), (tb[2] - tb[0]) * (tb[3] - tb[1]))
            if small > 0 and ix * iy / small >= 0.5:
                wit = "a"
                break
        if wit is None:
            for st, tx, tw, tg, tb in ts.get(key, []):
                if st != staff and abs(tx - xc) <= 0.8 * w:
                    wit = "d"
                    break
        ratio = min([abs(tx - xc) / w for st, tx, tw, tg, tb in ts.get(key, []) if st != staff] or [None], key=lambda v: 9e9 if v is None else v)
        dur = d["duration"].get(g)
        rows.append(dict(page=pg, glyph=g, cls=cls, bbox=bb, witness=wit, dur=dur, ratio=ratio))
json.dump(rows, open(OUT, "w"))
from collections import Counter  # noqa: E402
w = [r for r in rows if r["witness"]]
print(DOC, "unrefused heads in meter-read cells", len(rows), "with a witness", len(w))
print(Counter((r["witness"], r["cls"]) for r in w).most_common())
print(Counter((r["witness"], (r["dur"] or [None])[0]) for r in w).most_common())

ctl = [r for r in rows if not r["witness"] and r["ratio"] is not None]
for lim in (1.2, 1.6, 2.4):
    print("controls (no witness) with column ratio <= %.1f: %d  (by duration %s)" % (lim, sum(1 for r in ctl if r["ratio"] <= lim),
          Counter((r["dur"] or [None])[0] for r in ctl if r["ratio"] <= lim).most_common(3)))
