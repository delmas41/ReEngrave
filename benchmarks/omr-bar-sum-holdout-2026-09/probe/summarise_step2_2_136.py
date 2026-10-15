"""2.136 step 2: summarise out/2.136-step2/{lit,brah}.json; compare the ON settlements with Sean's 12
step-1 answers (out/print/2.136-review/answers.json).   python3 summarise_step2_2_136.py"""
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
B = HERE.parent
ROOT = HERE.parents[2]
O = B / "out" / "2.136-step2"
name = {1.0: "4", 1.5: "dot4", 0.5: "8", 0.75: "dot8", 0.25: "16", 2.0: "2", 3.0: "dot2"}
ans = {t["tile"]: t for t in json.load(open(ROOT / "out/print/2.136-review/answers.json"))["tiles"]}
man = json.load(open(ROOT / "out/print/2.136-review/manifest.json"))
for lab in ("lit", "brah"):
    d = json.load(open(O / f"{lab}.json"))
    on = {tuple(r["cell"]): r for r in d["rows"] if r["flag"] == "1"}
    c, lv, ca = collections.Counter(), collections.Counter(), collections.Counter()
    for r in on.values():
        for b, l in r["settled"].values():
            c[name.get(b, b)] += 1
            lv[(name.get(b, b), l)] += 1
    for x in d["added"]:
        if "new" in x:
            ca[x["was_declined"]] += len(x["new"])
    print(lab, "OFF", d["off"]["bars_fully_released"], "bars,", d["off"]["notes_settled"], "notes;",
          "ON", d["on"]["bars_fully_released"], "bars,", d["on"]["notes_settled"], "notes")
    print("  settled values", dict(c), "(value, beam levels)", dict(lv))
    print("  notes freed, by what OFF declined them for", dict(ca))
d = json.load(open(O / "brah.json"))
on = {tuple(r["cell"]): r for r in d["rows"] if r["flag"] == "1"}
off = {tuple(r["cell"]): r for r in d["rows"] if r["flag"] == "0"}
ok = 0
for t in man["tiles"]:
    c, n = tuple(t["cell"]), t["n"]
    s = ans[n]
    r = on.get(c)
    if t["role"] == "refused_pair":
        got = sorted(name.get(v[0], v[0]) for v in r["settled"].values()) if r else None
        want = sorted(s["sean"])
        ok += got == want
        print(f"tile {n:2d} {c} ON settled {got} Sean {want} OFF declined {off[c]['decline'] if c in off else None}"
              f" -> {'MATCH' if got == want else 'DIFF'} (ON decline {r and r['decline']})")
    else:
        print(f"tile {n:2d} CONTROL {c}: narrowed-head row exists={c in on}"
              f" settled={on[c]['settled'] if c in on else {}} (Sean: {s['sean']})")
print("refused pairs matching Sean:", ok, "of", sum(1 for t in man["tiles"] if t["role"] == "refused_pair"))
