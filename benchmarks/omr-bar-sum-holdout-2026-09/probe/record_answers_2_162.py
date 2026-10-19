"""ROADMAP 2.162 -- record Sean's 22 tile answers (2026-10-17) and score them against the key, per condition:
  main  = base (flag off) -> mine (flag on), 2.153 off
  b153  = b153 (2.153 on alone) -> both (2.153 on + 2.162 on)
Writes out/print/2.162-review/{answers,manifest}.json (the manifest names each tile's glyph and doc), then
`python3 -m tools.omr.staged.judged build`. Status per arm: right / wrong / narrowed-holding (his value among the candidates) /
narrowed-without.
usage: record_answers_2_162.py"""
import collections
import json
import re
import subprocess
import sys

VERBATIM = ("J - 1.8 2.8 3.dot 4 4.4 5.2 6.dot 4 7.8 8.dot4 9.2 10.2 11.dot4 12.8 13.dot 4 14.8 15.dot 4 16.8 17.4 "
            "18.dot 4 19. 4 20.4 21.8 22.4")
BEATS = {"2": 2.0, "4": 1.0, "8": 0.5, "16": 0.25}
G = "out/print/2.162-review"
key = json.load(open("out/2.162/tiles-key.json"))
body = VERBATIM.split("-", 1)[1]
ans = {}
for m in re.finditer(r"(\d+)\.\s*(dot\s*)?(\d+)", body):
    n, dot, v = int(m.group(1)), bool(m.group(2)), m.group(3)
    ans[n] = ("dotted %s" % v if dot else v, BEATS[v] * (1.5 if dot else 1.0))
assert sorted(ans) == list(range(1, 23)), sorted(ans)


def status(b, want):
    if b is None:
        return "none"
    if b["outcome"] == "decided":
        return "right" if abs((b["beats"] or 0) - want) < 1e-6 else "wrong"
    return "narrowed-holding" if any(abs(c - want) < 1e-6 for c in (b["cands"] or ())) else "narrowed-without"


def kind(a, b):
    if a is None or b is None:
        return "?"
    if a["outcome"] == b["outcome"] == "decided":
        return "decided -> another value" if a["beats"] != b["beats"] else "same value, another decider"
    return "%s -> %s" % (a["outcome"], b["outcome"])


tiles, rows = [], []
for r in key:
    sean, want = ans[r["n"]]
    t = dict(n=r["n"], doc=r["doc"], glyph=r["glyph"], role=r["role"], sean=sean,
             **{a: r[a] for a in ("base", "mine", "b153", "both")})
    tiles.append(t)
    rows.append(dict(n=r["n"], doc=r["doc"], role=r["role"], sean=sean, want=want,
                     **{a: status(r[a], want) for a in ("base", "mine", "b153", "both")},
                     kind_main=kind(r["base"], r["mine"]), kind_b153=kind(r["b153"], r["both"]),
                     reason_on=(r["mine"] or {}).get("reason")))
q = "What is the written value of the note in the blue box (4, dotted 4, 8 ...)?"
json.dump(dict(answered="2026-10-17", verbatim=VERBATIM, question=q, tiles=tiles), open(G + "/answers.json", "w"), indent=1)
json.dump(dict(question=q, tiles=[dict(n=t["n"], doc=t["doc"], glyph=t["glyph"]) for t in tiles], blue="the note asked about",
               nothing_else_drawn=True), open(G + "/manifest.json", "w"), indent=1)
subprocess.check_call([sys.executable, "-m", "tools.omr.staged.judged", "build"])
idx = json.load(open("benchmarks/acceptance/judged-tiles.json"))
mine_rows = [x for x in idx["tiles"] if x["item"] == "2.162-review"]
print("index rows for 2.162-review:", len(mine_rows), collections.Counter(x["answer_kind"] for x in mine_rows))
for cond, A, B, kk in (("main (2.153 off): flag off -> on", "base", "mine", "kind_main"),
                       ("2.153 on: without -> with 2.162", "b153", "both", "kind_b153")):
    print("==", cond)
    by = collections.defaultdict(collections.Counter)
    for x in rows:
        grp = "control" if x["role"] == "control" else x[kk]
        by[grp]["%s -> %s" % (x[A], x[B])] += 1
    for g, c in sorted(by.items()):
        print("  ", g, dict(c))
for x in rows:
    print(x["n"], x["doc"], x["role"], "Sean", x["sean"], "| base", x["base"], "mine", x["mine"], "| b153", x["b153"],
          "both", x["both"], "|", x["kind_main"], "/", x["kind_b153"])
json.dump(rows, open("out/2.162/scored.json", "w"), indent=1)
