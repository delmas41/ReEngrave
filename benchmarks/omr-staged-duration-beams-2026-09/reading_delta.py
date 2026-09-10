"""Per-STAFF bar readings that moved, toward the truth or away from it.

⚠️ FINER THAN THE BAR MODE, AND THAT IS THE POINT. A bar's modal length can
sit still while the staves under it move, and a rule that helps on balance can
still be pushing individual readings the wrong way. This counts every
(page, cell, staff) reading, not every bar.

    python3 .../reading_delta.py <off.json> <on.json> <truth-beats>
"""
import json
import sys
from collections import Counter


def readings(path):
    rec = json.load(open(path))["record"]
    dur = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "duration"}
    events = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "event"}
    rests = {o["subject"] for o in rec["observations"]
             if o["quantity"] == "rest" and o["value"] == "restWhole"}

    def beats(v):
        if v is None:
            return None
        if v["outcome"] == "decided":
            return (v.get("value") or {}).get("beats")
        c = v.get("candidates") or []
        return (c[0].get("value") or {}).get("beats") if c else None

    out = {}
    for key, ev in events.items():
        if ev["outcome"] != "decided":
            continue
        _, p, sy, st, ce = key.split("/")
        gl = lambda i: f"glyph/{p}/{sy}/{st}/{ce}/{i}"
        evs = (ev.get("value") or {}).get("events") or []
        if any(gl(i) in rests for e in evs for i in (e.get("glyphs") or [])):
            continue
        total = 0.0
        for e in evs:
            bs = [beats(dur.get(gl(i))) for i in (e.get("glyphs") or [])]
            bs = [b for b in bs if b]
            if bs:
                total += Counter(bs).most_common(1)[0][0]
        if total > 0:
            out[key] = round(total, 4)
    return out


def main():
    off, on, truth = readings(sys.argv[1]), readings(sys.argv[2]), float(sys.argv[3])
    t = Counter()
    for k in set(off) | set(on):
        a, b = off.get(k), on.get(k)
        ra = a is not None and abs(a - truth) < 1e-6
        rb = b is not None and abs(b - truth) < 1e-6
        if a == b:
            t["unchanged (right)" if ra else "unchanged (wrong)"] += 1
        elif ra and not rb:
            t["⚠️ RIGHT -> wrong"] += 1
        elif rb and not ra:
            t["wrong -> RIGHT"] += 1
        else:
            t["wrong -> wrong"] += 1
    tot = sum(t.values())
    for k, n in t.most_common():
        print(f"   {n:5d}  ({n/tot:5.1%})  {k}")
    print(f"   {sum(1 for v in off.values() if abs(v-truth)<1e-6):5d} right OFF"
          f"  ->  {sum(1 for v in on.values() if abs(v-truth)<1e-6):5d} right ON"
          f"   of {tot} readings")


if __name__ == "__main__":
    main()
