"""2.174 step 4: OFF vs ON per plate on the replayed (EXPORTED) arms: notes in file, held bars, blue notes, and the glyphs whose STANDING duration
verdict moved (by kind of move). usage: compare_2_174.py DOC REPLAYDIR OUT.json"""
import collections
import json
import sys

DOC, RD, OUT = sys.argv[1:4]
off = json.load(open("%s/%s.off.json" % (RD, DOC)))
on = json.load(open("%s/%s.on.json" % (RD, DOC)))


def kind(v):
    if v is None:
        return "none"
    if v["rest"]:
        return "rest"
    if v["outcome"] == "decided":
        return "decided:%s" % v["beats"]
    return v["outcome"]


moves = collections.Counter()
moved = {}
for g, a in off["glyphs"].items():
    b = on["glyphs"].get(g)
    if a is None or b is None:
        continue
    ka, kb = kind(a), kind(b)
    if ka != kb or a.get("reason") != b.get("reason"):
        moves[(ka, kb)] += 1
        moved[g] = dict(off=dict(outcome=a["outcome"], beats=a["beats"], reason=a["reason"], decider=a["decider"]),
                        on=dict(outcome=b["outcome"], beats=b["beats"], reason=b["reason"], decider=b["decider"]))
cov = lambda d: dict(notes_in_xml=d["notes_in_xml"], notes_reaching_file=d["coverage"]["written"]["notes"],
                     held_bars=d["coverage"]["bars_held_out_sum"].get("bars"), blue=d["coverage"]["guessed"]["notes"],
                     blue_by_rule=d["coverage"]["guessed"]["by_rule"], partial=d["coverage"]["partial_bars"].get("written"))
print(DOC, "OFF", json.dumps(cov(off), default=str))
print(DOC, "ON ", json.dumps(cov(on), default=str))
print(DOC, "standing duration verdicts that moved:", sum(moves.values()))
for k, n in moves.most_common(25):
    print("  ", n, k)
json.dump(dict(off=cov(off), on=cov(on), moves={"%s -> %s" % k: n for k, n in moves.items()}, moved=moved), open(OUT, "w"), default=str)
