"""The ablation table (measure only): for each arm of a plate, the written ties / slurs / notes against the baseline, gained and lost BY PLACE of the end
heads, and the first-rule ledger counts. python3 ablation_table.py PLATE ARM [ARM ...]  (reads scratch/dd)"""
import collections
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ledger as LG
import written as W

D = pathlib.Path("scratch/dd")
plate = sys.argv[1]


def load(name):
    dump = json.load(open(D / ("%s.%s.arcs.json" % (plate, name))))
    xml = (D / ("%s.%s.musicxml" % (plate, name))).read_text()
    wr = W.parse(xml)
    heads = {h["subject"]: h["box"] for h in dump["heads"]}
    cp = set(dump["pages"])

    def place(k):
        b = heads.get(k)
        return None if not b else (int(k.split("/")[1]), round((b[0] + b[2]) / 2 / 10), round((b[1] + b[3]) / 2 / 10))

    def ks(pairs):
        c = collections.Counter()
        for a, b in pairs:
            if int(a.split("/")[1]) in cp:
                c[(place(a), place(b))] += 1
        return c
    res = LG.build(dump, xml)
    return dict(ties=ks(wr["ties"]), slurs=ks(wr["slurs"]), notes=sum(1 for k in wr["notes"] if int(k.split("/")[1]) in cp), res=res,
                fates=collections.Counter(r["fate"] for r in res["rows"]))


base = load("base")
print("%-12s %5s %5s | %-14s %-14s | %s" % ("arm", "ties", "slurs", "ties +/-", "slurs +/-", "notes  fates(written/dropped/wrong/two)"))
f = base["fates"]
print("%-12s %5d %5d | %-14s %-14s | %d  %d/%d/%d/%d" % ("base", sum(base["ties"].values()), sum(base["slurs"].values()), "", "", base["notes"],
                                                      f["written"], f["dropped"], f["wrong_note"], f["two_arcs"]))
for arm in sys.argv[2:]:
    try:
        a = load(arm)
    except FileNotFoundError:
        print(arm, "missing")
        continue
    tg, tl = sum((a["ties"] - base["ties"]).values()), sum((base["ties"] - a["ties"]).values())
    sg, sl = sum((a["slurs"] - base["slurs"]).values()), sum((base["slurs"] - a["slurs"]).values())
    f = a["fates"]
    print("%-12s %5d %5d | +%-4d -%-6d | +%-4d -%-6d | %d  %d/%d/%d/%d" % (arm, sum(a["ties"].values()), sum(a["slurs"].values()), tg, tl, sg, sl,
                                                                         a["notes"], f["written"], f["dropped"], f["wrong_note"], f["two_arcs"]))
