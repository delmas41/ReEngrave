"""ROADMAP 2.305 r4 step 1 (MEASUREMENT): for each edge half with no partner half on the next (previous) system of the same page, every page-ink run and the page
pass's entry for it on the partner system's staff of the SAME PART near the system's start (end) -- is the other half traced at all, and if so what did the pass do with it?

    python3 edge_partners_2305.py PLATE REPLAYWORK GATHERWORK
"""
import collections
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.judged import iter_array  # noqa: E402

plate, rw, gw = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
part_of, staff_part = {}, collections.defaultdict(collections.Counter)
root = ET.fromstring((rw / ("%s.on.musicxml" % plate)).read_text())
for part in root.iter("part"):
    for el in part.iter("note"):
        rg = el.get("rg")
        if rg and rg.startswith("glyph/"):
            part_of[rg] = part.get("id")
            staff_part["/".join(rg.split("/")[1:4])][part.get("id")] += 1
ents, halves = {}, []
for v in json.load(open(rw / ("%s.on.extra.json" % plate))):
    pg = int(v["subject"].split("/")[1])
    for e in v["detail"]["runs"]:
        ents.setdefault(e["row"], []).append(dict(e, page=pg))
        if e["status"] == "abstained" and e.get("edge") in ("left", "right") and e.get("edge_head"):
            halves.append(dict(e, page=pg, part=part_of.get(e["edge_head"])))
runs = {}
for o in iter_array(gw / ("%s.on.gathered.record.json" % plate), "observations"):
    if o.get("quantity") == "page_arc" and o.get("value") == "run":
        runs[o["id"]] = (int(o["subject"].split("/")[1]), o["detail"])
pages = {h["page"] for h in halves}
sys_x = collections.defaultdict(lambda: [1e9, -1e9])
for k in part_of:
    p = k.split("/")
    # page/system x extent from the written notes (a lower bound of the system's width)
for rid, (pg, d) in runs.items():
    st = d.get("staff") or [None, None]
    xs = [p[0] for p in d["points"]]
    s = sys_x[(pg, st[0])]
    s[0], s[1] = min(s[0], min(xs)), max(s[1], max(xs))
c = collections.Counter()
for h in halves:
    pg, sy = int(h["edge_head"].split("/")[1]), int(h["edge_head"].split("/")[2])
    tgt_sys = sy + 1 if h["edge"] == "right" else sy - 1
    if tgt_sys < 0 or (pg, tgt_sys) not in sys_x:
        continue
    staves = [s for s, cnt in staff_part.items() if s.startswith("%d/%d/" % (pg, tgt_sys)) and cnt.most_common(1)[0][0] == h["part"]]
    if not staves:
        c["partner system: no staff of this part"] += 1
        continue
    st = int(staves[0].split("/")[2])
    x0, x1 = sys_x[(pg, tgt_sys)]
    near = []
    for rid, (rp, d) in runs.items():
        if rp != pg or list(d.get("staff") or []) != [tgt_sys, st]:
            continue
        xs = [p[0] for p in d["points"]]
        if (h["edge"] == "right" and min(xs) < x0 + 8 * d["space_page_px"]) or (h["edge"] == "left" and max(xs) > x1 - 8 * d["space_page_px"]):
            near.append([(e["status"], e.get("why"), e.get("edge")) for e in ents.get(rid, [])] or [("no entry",)])
    key = "half %s: partner-side runs on the same part's staff near the break: %s" % (h["edge"], "none" if not near else ", ".join(sorted({str(n) for n in near})))
    c[key] += 1
for k, v in sorted(c.items()):
    print("%3d  %s" % (v, k))
