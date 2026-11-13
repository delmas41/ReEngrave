"""head_stem OFF decided -> ON decided: same stem row id or another? (consumers key chords and shared values on the id)"""
import sys, json, collections
pre = sys.argv[1]
A = {(v["s"]): v for v in json.load(open(pre + ".off.json"))["verdicts"] if v["q"] == "head_stem"}
B = {(v["s"]): v for v in json.load(open(pre + ".on.json"))["verdicts"] if v["q"] == "head_stem"}
c = collections.Counter()
for s, b in B.items():
    a = A.get(s)
    if not a or a["o"] != "decided" or b["o"] != "decided":
        continue
    rows_a = set((a.get("d") or {}).get("stem_rows") or [a["v"]])
    c[("same id" if a["v"] == b["v"] else ("same physical stem, other row" if b["v"] in rows_a else "other stem"), a["r"], b["r"])] += 1
for k, n in c.most_common(12):
    print(n, k)
