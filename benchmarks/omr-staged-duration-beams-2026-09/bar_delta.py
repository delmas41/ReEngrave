"""Which BARS moved between two adjudications of ONE gather, and which way.

⚠️ A NET IMPROVEMENT CAN HIDE A REGRESSION, which is the whole reason this
prints the moves rather than a total. A bar that was RIGHT with the rule off
and is WRONG with it on is a false attachment showing up where it matters —
on a scan that is the risk the engraved fixture cannot price, because a scan's
classical-CV stems are fewer and worse.

    python3 .../bar_delta.py <off.json> <on.json> <truth-beats>
"""
import json
import sys
from collections import Counter


def bars(path):
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
            out.setdefault((int(p), int(ce)), []).append(round(total, 4))
    assessable = {}
    for k, L in out.items():
        mode, n = Counter(L).most_common(1)[0]
        if len(L) >= 3 and n / len(L) >= 0.5:
            assessable[k] = (mode, n, len(L))
    return assessable


def main():
    off, on, truth = bars(sys.argv[1]), bars(sys.argv[2]), float(sys.argv[3])
    keys = sorted(set(off) | set(on))
    tally = Counter()
    lines = []
    for k in keys:
        a, b = off.get(k), on.get(k)
        ra = a is not None and abs(a[0] - truth) < 1e-6
        rb = b is not None and abs(b[0] - truth) < 1e-6
        if a is None and b is None:
            continue
        if a is None:
            tally["became assessable, RIGHT" if rb else
                  "became assessable, wrong"] += 1
        elif b is None:
            tally["stopped being assessable (was right)" if ra else
                  "stopped being assessable (was wrong)"] += 1
        elif ra and not rb:
            tally["⚠️ RIGHT -> WRONG"] += 1
        elif rb and not ra:
            tally["wrong -> RIGHT"] += 1
        elif a[0] != b[0]:
            tally["wrong -> wrong (moved)"] += 1
        else:
            tally["unchanged"] += 1
        if a != b:
            fa = f"{a[0]}({a[1]}/{a[2]})" if a else "-"
            fb = f"{b[0]}({b[1]}/{b[2]})" if b else "-"
            lines.append(f"   p{k[0]}c{k[1]:<3} {fa:>14s} -> {fb:<14s}"
                         f" {'RIGHT' if rb else ('was right' if ra else '')}")
    def score(d):
        return sum(1 for v in d.values() if abs(v[0] - truth) < 1e-6)
    print(f"OFF: {len(off)} assessable, {score(off)} correct")
    print(f"ON : {len(on)} assessable, {score(on)} correct   (truth {truth})")
    for k, n in tally.most_common():
        print(f"   {n:4d}  {k}")
    if lines:
        print("  bars that moved:")
        print("\n".join(lines))


if __name__ == "__main__":
    main()
