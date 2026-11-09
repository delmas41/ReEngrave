"""for each WRITTEN binder entry of ON: are its two heads in the file, is there ANY file arc on them, and what does the export report say about arcs it counted but did not write"""
import json
import collections
from load import *  # noqa

rec = record("on")
bind = [v for v in rec["verdicts"] if v["quantity"] == "page_arc_binding"][0]["detail"]["runs"]
notes = xml_notes("on")
gb = {o["subject"]: o["detail"]["bbox_page_px"] for o in rec["observations"] if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/0/")}
arcs = A.arcs_of_xml((WORK / "on.musicxml").read_text())
ends = collections.defaultdict(list)
for a in arcs:
    ends[a["start"]].append(a)
    ends[a["stop"]].append(a)
cnt = collections.Counter()
rows = []
for e in bind:
    if e["status"] != "written":
        continue
    s, t = e["start"], e["stop"]
    colx = lambda k: ((gb[k][0] + gb[k][2]) / 2) if k in gb else None
    sk = lambda k: tuple(k.split("/")[2:4])
    exact = [a for a in arcs if a["kind"] and sk(a["start"]) == sk(s) and sk(a["stop"]) == sk(t) and colx(a["start"]) is not None and abs(colx(a["start"]) - colx(s)) <= 35 and abs(colx(a["stop"]) - colx(t)) <= 35]
    anyc = [a for a in arcs if (sk(a["start"]) == sk(s) and abs(colx(a["start"]) - colx(s)) <= 35) or (sk(a["stop"]) == sk(t) and abs(colx(a["stop"]) - colx(t)) <= 35)]
    st = ("heads_in_file=%s/%s" % (s in notes, t in notes), "exact_arc=%s" % bool(exact), "any_arc_on_heads=%s" % bool(anyc))
    cnt[st] += 1
    rows.append((e["ordinal"], e.get("piece"), e["kind"], st))
for k, v in sorted(cnt.items(), key=lambda t: -t[1]):
    print(v, k)
print([r[0] for r in rows if r[3][1] == "exact_arc=False"])
rep = json.load(open(WORK / "on.report.json"))
for k, v in rep.items():
    if any(w in k for w in ("arc", "slur", "tie", "span", "page_bound")):
        print(k, str(v)[:300])
