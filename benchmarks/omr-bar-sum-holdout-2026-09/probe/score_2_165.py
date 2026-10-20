"""ROADMAP 2.165 -- score the replay arms per plate ON THE EXPORTED FILE: notes reaching file, bars held out, blue notes in the file by
rule, notes the rule changed (and how many reached the file blue), judged right/wrong/narrowed (judged.score on the replayed
mini-record) and which judged tiles moved vs OFF, plus Set B (from out/2.162/tiles-key-b.json and Sean's typed answers).
usage: score_2_165.py DOC OFFJSON ARM=JSON [ARM=JSON ...]"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, ".")
from tools.omr.staged import judged as J  # noqa: E402

DOC = sys.argv[1]
arms = {"off": sys.argv[2]}
for a in sys.argv[3:]:
    k, v = a.split("=", 1)
    arms[k] = v
SETB = {1: .5, 2: .5, 3: 1.0, 4: .5, 5: 1.5, 6: 1.5, 7: .5, 8: 1.0, 9: .5, 10: .5}
key_b = {k["glyph"]: k for k in json.load(open("out/2.162/tiles-key-b.json")) if k["doc"] == DOC}
idx = json.loads(J.INDEX_PATH.read_text())
res, status = {}, {}
for name, path in arms.items():
    d = json.load(open(path))
    cov = d["coverage"]
    sc = J.score(idx, pathlib.Path(path.replace(".json", ".record.json")), DOC)
    st = {(t["item"], t["tile"]): t["status"] for t in sc["tiles"]}
    status[name] = st
    chg = d["changed"]
    g = cov["guessed"]["by_rule"]
    # which changed notes sit in a bar the file holds out? (page, system, staff, cell)
    held = {tuple(h) for h in d["held_bars"]}
    in_held = sum(1 for c in chg if tuple(int(x) for x in c["glyph"].split("/")[1:5]) in held)
    setb = {n: None for n in SETB}
    for gl, k in key_b.items():
        b = d["glyphs"].get(gl)
        setb[k["n"]] = (b["beats"] if b else None)
    res[name] = dict(notes_reaching_file=cov["written"]["notes"], bars_held_out=cov["bars_held_out_sum"]["bars"],
                     bars_partial=cov["partial_bars"].get("written"), blue_total=cov["guessed"]["notes"],
                     blue_by_rule={k: v for k, v in g.items() if k in ("bar_corrects_one_note", "bar_disagrees_with_decided", "reconcile_duration")},
                     changed_in_record=len(chg), changed_in_held_bar=in_held, changed_blue_in_file=g.get("bar_corrects_one_note", 0),
                     judged=sc["totals"], refusals=d.get("refusals"), setB_beats=setb)
print(json.dumps(res, indent=1, default=str))
for name in arms:
    if name == "off":
        continue
    moved = []
    for k, s in status[name].items():
        if status["off"].get(k) != s:
            moved.append((k, status["off"].get(k), s))
    print(name, "judged tiles that move vs off:", moved)
    sb = []
    for n, b in res[name]["setB_beats"].items():
        o = res["off"]["setB_beats"][n]
        if b is not None and o != b:
            sb.append((n, o, b, SETB[n], "right" if b == SETB[n] else "wrong"))
    print(name, "Set B tiles whose value moves:", sb)
json.dump(res, open("/dev/stdout", "w") if False else open(arms["off"].replace(".off.json", ".scored.json"), "w"), default=str)
