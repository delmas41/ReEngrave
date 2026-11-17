"""ROADMAP 2.305 round 4 step 1 (MEASUREMENT): how the page pass sees an arc across a system break today.

    python3 edge_halves_2305.py PLATE REPLAYWORK GATHERED_PAGES

Every page-pass run that abstains `system_edge` with its OTHER end bound is a HALF: `right` (runs off the end of its system, its bound note is the first note) or `left`
(picks up at the start of its system, its bound note is the second). Its instrument = the PART the written file puts its bound note in (`rg` -> part id: the staff identity
the export uses). A right half on (page, system s) pairs with a left half of the same part on (page, s+1), or on (page+1, first system) when s is the page's last system;
counted: one-to-one pairs, ambiguous (two candidates on a side), no partner half on the next system, partner page not gathered, part unknown. Also: cross-system arcs the
written file already holds (start and stop in different systems).
"""
import collections
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-arc-binding-2026-10" / "page-ink-2026-11" / "step2"))
import arcs as A  # noqa: E402

plate, rw = sys.argv[1], pathlib.Path(sys.argv[2])
gathered = {int(x) for x in sys.argv[3].split(",")}
part_of = {}
systems = collections.defaultdict(set)
root = ET.fromstring((rw / ("%s.on.musicxml" % plate)).read_text())
for part in root.iter("part"):
    for el in part.iter("note"):
        rg = el.get("rg")
        if rg and rg.startswith("glyph/"):
            part_of[rg] = part.get("id")
            p = rg.split("/")
            systems[int(p[1])].add(int(p[2]))
halves = []
for v in json.load(open(rw / ("%s.on.extra.json" % plate))):
    pg = int(v["subject"].split("/")[1])
    for e in v["detail"]["runs"]:
        if e["status"] == "abstained" and e.get("edge") in ("left", "right") and e.get("edge_head"):
            h = e["edge_head"]
            halves.append(dict(page=pg, system=int(h.split("/")[2]), side=e["edge"], head=h, part=part_of.get(h), ordinal=e["ordinal"], staff=e.get("staff_key")))
c = collections.Counter((h["side"]) for h in halves)
print("== %s: halves right %d | left %d | part unknown (note not written) %d" % (plate, c["right"], c["left"], sum(1 for h in halves if h["part"] is None)))
L = collections.defaultdict(list)
for h in halves:
    if h["side"] == "left" and h["part"]:
        L[(h["page"], h["system"], h["part"])].append(h)
res = collections.Counter()
used = set()
for h in halves:
    if h["side"] != "right":
        continue
    if not h["part"]:
        res["right half: part unknown"] += 1
        continue
    last = max(systems.get(h["page"]) or {h["system"]})
    nxt = (h["page"], h["system"] + 1) if h["system"] < last else (h["page"] + 1, 0)
    if nxt[0] not in gathered:
        res["right half: partner page %d not gathered" % nxt[0] if False else "right half: partner page not gathered"] += 1
        continue
    cand = L.get((nxt[0], nxt[1], h["part"])) or []
    if not cand:
        res["right half: no left half of its part on the next system"] += 1
    elif len(cand) > 1:
        res["right half: two or more left halves (ambiguous)"] += 1
    else:
        res["pair one-to-one"] += 1
        used.add(id(cand[0]))
for h in halves:
    if h["side"] == "left" and id(h) not in used:
        prev_first = h["system"] == 0
        if prev_first and (h["page"] - 1) not in gathered:
            res["left half: previous page not gathered"] += 1
        else:
            res["left half: no right half paired on the previous system"] += 1
for k, v in sorted(res.items()):
    print("   %4d  %s" % (v, k))
arcs = A.arcs_of_xml((rw / ("%s.on.musicxml" % plate)).read_text())
cross = [a for a in arcs if a["start"].split("/")[1:3] != a["stop"].split("/")[1:3]]
print("   cross-system arcs in the written file today: %d (%s)" % (len(cross), dict(collections.Counter(a["kind"] for a in cross))))
