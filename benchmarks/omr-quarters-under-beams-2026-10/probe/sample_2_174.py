"""2.174 step 2b: the population (first-verdict DECIDED quarters `head_and_marks`, written 1.0 no dots, head not open, whose cell holds a CV
or detector beam row), a seeded RANDOM sample of N per plate, and the JUDGED members (judged score notes + the 2.165 tiles).
usage: sample_2_174.py DOC N OUT.json"""
import collections
import json
import random
import sys

DOC, N, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
rows = json.load(open("scratch/census_%s.json" % DOC))["rows"]
pop = [r for r in rows if r["reason"] == "head_and_marks" and (r["cv"] or r["yolo"])]
stem = [r for r in pop if r["has_stem"]]
print(DOC, "population with beam evidence in the cell:", len(pop), "| own stem found", len(stem), "| no stem found", len(pop) - len(stem))
rnd = random.Random(2174)
sample = sorted(rnd.sample([r["subject"] for r in pop], N))
judged = {}
sc = {"litolff": "jl", "brahms": "jb"}[DOC]
for t in json.load(open("scratch/%s-20261018-night.json" % sc))["tiles"]:
    if t["note"].startswith("decided 1 beats (head_and_marks)"):
        for s in (t["subject"] if isinstance(t["subject"], list) else [t["subject"]]):
            judged[s] = dict(sean=t["answer"], status=t["status"], item=t["item"], tile=t["tile"])
A = json.load(open("out/print/2.165-review/answers.json"))["answers"]
for k in json.load(open("out/2.165/tiles-key.json")):
    if k["doc"] == DOC and k["role"] == "changed":
        judged["%s" % k["glyph"]] = dict(sean=A[str(k["n"])], status="2.165 tile (Sean %s)" % A[str(k["n"])], item="2.165-review", tile=k["n"])
by = {r["subject"]: r for r in rows}
jl = sorted(s for s in judged if s in by and by[s]["reason"] == "head_and_marks" and by[s]["written_ok" if False else "reason"])
json.dump(dict(population=len(pop), sample=sample, judged={s: dict(judged[s], row=by[s]) for s in jl}), open(OUT, "w"))
print("sample", len(sample), "| judged head_and_marks quarters in census", len(jl), collections.Counter(judged[s]["status"] for s in jl))
