"""2.136: why does INFER's `_printed_meter_roots` answer None for 111 of the 179 Brahms N bars?

READ-ONLY, record as written (load_record). For each system holding a population bar, follow the
meter verdict's `used` chain exactly as `inferences._printed_meter_roots` does (a `carried` /
`carried_uncontested` verdict points at the previous system's meter verdict) and report the hop
count until a `voted` verdict, plus where the chain breaks. `_printed_meter_roots` gives up at
depth > 40; this prints how many population systems sit past that.

    python3 meter_depth_2_136.py RECORD GATES.json OUT.json
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.omr.staged.record_io import load_record  # noqa: E402

rec_path, gates_path, out_path = sys.argv[1:4]
gates = json.load(open(gates_path))
pop = [tuple(r["cell"]) for r in gates["rows"]]
doc = load_record(rec_path)
rec = doc["record"] if "record" in doc else doc
by_id = {}
live = {}
superseded = set()
for v in rec["verdicts"]:
    if v["quantity"] == "meter":
        by_id[v["id"]] = v
        if v.get("supersedes"):
            superseded.add(v["supersedes"])
for v in by_id.values():
    if v["id"] not in superseded:
        live[v["subject"]] = v


def chain(v):
    """hops to a `voted` verdict; how it ended."""
    depth = 0
    while True:
        if v["reason"] == "voted":
            return depth, "voted"
        if v["outcome"] != "decided" or v["reason"] not in ("carried", "carried_uncontested"):
            return depth, "reason:" + v["reason"]
        nxt = None
        for r in v.get("used") or ():
            src = by_id.get(r)
            if src is not None:
                nxt = src
                break
        if nxt is None:
            return depth, "no_meter_in_used"
        a, b = (nxt.get("value") or {}), (v.get("value") or {})
        if a.get("numerator") != b.get("numerator") or a.get("denominator") != b.get("denominator"):
            return depth, "changed_between_systems"
        v = nxt
        depth += 1


rows = []
hist = collections.Counter()
for c in pop:
    sub = f"system/{c[0]}/{c[1]}"
    v = live.get(sub)
    if v is None:
        rows.append({"cell": list(c), "end": "no_meter_verdict"})
        continue
    d, end = chain(v)
    segs = len((v.get("value") or {}).get("segments") or ())
    rows.append({"cell": list(c), "gate": next(r["gate"] for r in gates["rows"]
                                              if tuple(r["cell"]) == c),
                 "reason": v["reason"], "outcome": v["outcome"], "depth": d, "end": end,
                 "segments": segs})
    hist[(v["outcome"], v["reason"], "depth<=40" if d <= 40 else "depth>40", end)] += 1
# every system of the movement, for scale
allsys = collections.Counter()
for sub, v in live.items():
    if v["outcome"] == "decided" and v["reason"] in ("carried", "carried_uncontested"):
        d, end = chain(v)
        allsys["depth<=40" if d <= 40 else "depth>40"] += 1
out = {"hist": {str(k): n for k, n in hist.items()}, "all_carried_systems": dict(allsys),
       "max_depth_population": max((r.get("depth", 0) for r in rows), default=0), "rows": rows}
Path(out_path).write_text(json.dumps(out, indent=1))
for k, n in sorted(hist.items(), key=lambda kv: -kv[1]):
    print(n, k)
print("all decided-carried systems:", dict(allsys))
print("max depth among population systems:", out["max_depth_population"])
