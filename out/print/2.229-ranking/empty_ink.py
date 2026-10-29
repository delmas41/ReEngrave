"""2.229: of the unread-empty bars with no head/rest glyph, how many have ink in the cell (GATHER's cv_ink row), how many sit in a tacet span.
usage: empty_ink.py WORKDIR PLATE SLICEDIR"""
import json, collections, sys
work, plate, sl = sys.argv[1:4]
D = json.load(open("%s/%s.fates.json" % (work, plate)))
R = json.load(open("%s/%s.saved.report.json" % (work, plate)))
tac = [(s["part"], s["systems"]) for s in R["tacet_padding"]["spans"]]
tacsys = {(p, tuple(map(int, s.split("/")))) for p, ss in tac for s in ss}
ub = {(b["page"], b["system"], b["staff"], b["cell"]): b for b in R["unread_empty_bars"]["list"]}
cells = {tuple(map(int, o["key"].split("/"))) for o in D["bars"] if o["kind"] == "no_head_or_rest_glyph"}
ink = {}
for l in open("%s/%s/observations.jsonl" % (sl, plate)):
    if '"quantity": "ink"' in l or '"quantity": "cell_ink_pieces"' in l:
        o = json.loads(l); p = o["subject"].split("/")
        if p[0] != "cell": continue
        k = tuple(int(x) for x in p[1:5])
        if k in cells:
            ink.setdefault(k, {})[o["quantity"]] = o["value"]
c = collections.Counter()
for k in cells:
    b = ub[k]; t = (b["part"], (k[0], k[1])) in tacsys
    c[("ink=" + str(ink.get(k, {}).get("ink")), "tacet_span" if t else "not_tacet")] += 1
print(dict(c))
ex = sorted(k for k in cells if ink.get(k, {}).get("ink") == "ink" and (ub[k]["part"], (k[0], k[1])) not in tacsys)
print("ink, not tacet:", len(ex), ["/".join(map(str, k)) for k in ex[:15]])
ex2 = sorted(k for k in cells if (ub[k]["part"], (k[0], k[1])) in tacsys)
print("tacet:", len(ex2), ["/".join(map(str, k)) for k in ex2[:6]])
