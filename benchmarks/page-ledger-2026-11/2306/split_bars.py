"""Bars where the divisi guard split heads at (nearly) one x into two events: per arm file, and whether the split heads include a copy owned elsewhere
(duration `owned_by_another_staff`). Usage: split_bars.py ARM.json [ARM2.json ...]"""
import sys, json, collections
for path in sys.argv[1:]:
    D = json.load(open(path))
    twin = {v["s"] for v in D["verdicts"] if v["q"] == "duration" and v["r"] == "owned_by_another_staff"}
    out = collections.Counter()
    ex = collections.defaultdict(list)
    for v in D["verdicts"]:
        if v["q"] != "event" or not isinstance(v["v"], dict):
            continue
        evs = [e for e in v["v"].get("events") or () if e.get("kind") == "chord"]
        evs.sort(key=lambda e: e.get("x") or 0)
        for a, b in zip(evs, evs[1:]):
            if abs((a.get("x") or 0) - (b.get("x") or 0)) <= 8:
                base = "glyph/" + v["s"].split("/", 1)[1] + "/"
                gs = [base + str(g) for g in (a.get("glyphs") or []) + (b.get("glyphs") or [])]
                k = "with a copy owned elsewhere" if any(g in twin for g in gs) else "own heads only"
                out[k] += 1
                ex[k].append(v["s"])
    print(path.split("/")[-1], dict(out), {k: v[:4] for k, v in ex.items()})
