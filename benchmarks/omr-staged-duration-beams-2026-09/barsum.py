"""Assessable bar lengths off a saved record's OWN duration verdicts.

⚠️ ONLY ASSESSABLE BARS ARE THE METER MECHANISM'S ANSWERS -- >= 3 staves and
>= 50% agreeing. Reporting the modal length of EVERY cell overstates the
failure; the first draft of the FINDINGS this belongs to did exactly that.

    python3 .../barsum.py <staged.json> "0:0-8=3.0,1:0-2=3.0,1:3-8=4.0,2:0-8=4.0"
"""
import json, sys
from collections import Counter
rec = json.load(open(sys.argv[1]))["record"]
TRUTH = {}
for spec in sys.argv[2].split(","):
    where, b = spec.split("="); pg, cells = where.split(":")
    a, _, z = cells.partition("-")
    for c in range(int(a), int(z or a) + 1): TRUTH[(int(pg), c)] = float(b)
dur = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "duration"}
events = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "event"}
rests = {o["subject"] for o in rec["observations"]
         if o["quantity"] == "rest" and o["value"] == "restWhole"}
def beats(v):
    if v is None: return None
    if v["outcome"] == "decided": return (v.get("value") or {}).get("beats")
    c = v.get("candidates") or []
    return (c[0].get("value") or {}).get("beats") if c else None
bars = {}
for key, ev in events.items():
    if ev["outcome"] != "decided": continue
    _, p, sy, st, ce = key.split("/")
    if (int(p), int(ce)) not in TRUTH: continue
    gl = lambda i: f"glyph/{p}/{sy}/{st}/{ce}/{i}"
    evs = (ev.get("value") or {}).get("events") or []
    if any(gl(i) in rests for e in evs for i in (e.get("glyphs") or [])): continue
    total = 0.0
    for e in evs:
        bs = [beats(dur.get(gl(i))) for i in (e.get("glyphs") or [])]
        bs = [b for b in bs if b]
        if bs: total += Counter(bs).most_common(1)[0][0]
    if total > 0: bars.setdefault((int(p), int(ce)), []).append(round(total, 4))
ok = tot = 0; out = []
for k in sorted(bars):
    L = bars[k]; mode, n = Counter(L).most_common(1)[0]
    if len(L) >= 3 and n / len(L) >= 0.5:
        tot += 1; good = abs(mode - TRUTH[k]) < 1e-6; ok += good
        out.append(f"p{k[0]}c{k[1]}={mode}{'' if good else '*'}({n}/{len(L)})")
print(f"assessable {tot}  correct {ok}   " + " ".join(out))
