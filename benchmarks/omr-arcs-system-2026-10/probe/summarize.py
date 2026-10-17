"""ROADMAP 2.166 -- fold the page A/Bs (out/2.166/ab_<doc>_p<page>.json) into the FINDINGS numbers.
usage: summarize.py AB.json ...   writes out/2.166/summary.json and prints it"""
import collections
import json
import sys

sys.path.insert(0, ".")

T164 = {  # 2.164's refused tails (Sean 18/18 "Tie") and its 2 controls
    "litolff": ["glyph/3/1/5/3/1", "glyph/3/1/5/3/3", "glyph/3/1/5/15/2", "glyph/4/0/5/12/14", "glyph/5/1/4/2/1",
                "glyph/12/1/10/11/4", "glyph/13/0/1/10/9"],
}
judged = json.load(open("benchmarks/acceptance/judged-tiles.json"))["tiles"]
judged_glyphs = collections.defaultdict(list)
for t in judged:
    for g in ([t.get("subject")] + list(t.get("subjects") or [])):
        if g and str(g).startswith("glyph/"):
            judged_glyphs[(t.get("doc"), g)].append(t)

out = {}
for f in sys.argv[1:]:
    d = json.load(open(f))
    doc = d["doc"]
    o = out.setdefault(doc, collections.Counter())
    o["pages"] += 1
    o["pieces"] += d["pieces_read"] + sum(d["abstained"].values())
    o["pieces_read"] += d["pieces_read"]
    o["pieces_abstained"] += sum(d["abstained"].values())
    o["arcs"] += d["arcs"]
    o["arcs_joined_across_barline"] += d["joined_across_barline"]
    for s, n in d["shapes"].items():
        o["shape:" + s] += n
    so = [t for a in d["sysarc"] for t in a["detail"]["through_boxes"] if t["stroke_only"]]
    o["stroke_only_head_boxes"] += sum(1 for t in so if t["class"].startswith("notehead"))
    o["stroke_only_beam_boxes"] += sum(1 for t in so if t["class"].startswith("beam"))
    o["arcs_run_past_their_boxes"] += sum(1 for a in d["sysarc"] if a["detail"]["beyond_boxes_spaces"] >= 1.0)
    o["tie_pair_changed"] += int(d["tie_pair_off"] != d["tie_pair_on"])
    o["arc_kind_changed"] += int(d["arc_kind_off"] != d["arc_kind_on"])
    o["glyphs_changed"] += d["n_changed_glyphs"]
    for g, ch in d["changed"].items():
        for q, v in ch.items():
            o["changed:%s:%s->%s" % (q, (v["off"] or [None])[0], (v["on"] or [None])[0])] += 1
        if judged_glyphs.get((doc, g)):
            o["judged_glyphs_changed"] += 1
            print("JUDGED CHANGED", doc, g, ch, [(t.get("answer"), t.get("item")) for t in judged_glyphs[(doc, g)]])
    for g in T164.get(doc, []):
        if g.split("/")[1] == str(d["page"]):
            o["t164_tails_on_page"] += 1
            o["t164_tails_stroke_only"] += int(any(t["glyph"] == g for t in so))
            if g in d["changed"]:
                o["t164_tails_verdict_changed"] += 1
    # judged glyphs present on this page and erased ink inside their box
    o["judged_glyphs_on_page"] += sum(1 for (dd, g) in judged_glyphs if dd == doc and g.split("/")[1] == str(d["page"]))
    for g, ch in d["changed"].items():
        print("CHANGED", doc, g, {q: (v["off"], v["on"]) for q, v in ch.items()})
res = {k: dict(v) for k, v in out.items()}
json.dump(res, open("out/2.166/summary.json", "w"), indent=1)
print(json.dumps(res, indent=1))
