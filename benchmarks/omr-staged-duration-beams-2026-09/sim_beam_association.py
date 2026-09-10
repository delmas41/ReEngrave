"""Two association rules over ONE saved record -- no re-transcription.

⚠️ IT MEASURES A MECHANISM, IT DOES NOT SCORE ANYTHING. RULE A is the shipping
centre test; RULE B adds the stem tier. The point of running both against both
candidate policies is that RULE B is INSENSITIVE to the policy -- which is the
claim that the ambiguity was an artefact of the association and not a reading.

    python3 .../sim_beam_association.py <staged.json> "0:0-8=3.0,..."
"""
import json, sys
from collections import Counter

rec = json.load(open(sys.argv[1]))["record"]
obs, verds = rec["observations"], rec["verdicts"]
gbox = {o["subject"]: o for o in obs if o["quantity"] == "glyph_box"}
head = {}
for o in obs:
    if o["quantity"] == "notehead_class":
        head[o["subject"]] = o["value"]
dots = Counter(o["subject"] for o in obs if o["quantity"] == "aug_dot")
flags = Counter(o["subject"] for o in obs if o["quantity"] == "flag")
dur = {v["subject"]: v for v in verds if v["quantity"] == "duration"}
events = {v["subject"]: v for v in verds if v["quantity"] == "event"}
rests = {o["subject"] for o in obs if o["quantity"] == "rest" and o["value"] == "restWhole"}

beams, stems = {}, {}
for o in obs:
    if o["quantity"] == "beam_stroke":
        beams.setdefault(o["subject"], []).append(o)
    elif o["quantity"] == "stem":
        stems.setdefault(o["subject"], []).append(o)

HEAD_BEATS = {"noteheadWhole": 4.0, "noteheadHalf": 2.0,
              "noteheadBlack": 1.0, "noteheadDoubleWhole": 8.0}
def cellof(g): return "cell/" + "/".join(g.split("/")[1:5])

def kept(cell):
    rows = beams.get(cell, [])
    cv = [r for r in rows if r["reader"] == "cv_lines"]
    yo = [r for r in rows if r["reader"] == "detector"]
    out = list(cv)
    for b in yo:
        if not any(b["detail"]["x0"] <= s["detail"]["x1"]
                   and b["detail"]["x1"] >= s["detail"]["x0"] for s in cv):
            out.append(b)
    return out

Y_TOL = 4.0   # canonical px; a stroke's own thickness is ~48

def levels(g, rule):
    cell = cellof(g)
    bs = kept(cell)
    bx = gbox.get(g)
    if not bx: return (0, 0)
    v = bx["value"]; x0, w = v[1], v[3]; x1 = x0 + w; xc = x0 + w / 2.0
    if rule == "A":
        c = p = 0
        for b in bs:
            d = b["detail"]
            if d["x0"] <= xc <= d["x1"]: c += 1; p += 1
            elif d["x0"] - w <= xc <= d["x1"] + w: p += 1
        return (c, p)
    # RULE B
    st = [s for s in stems.get(cell, [])
          if s["detail"]["x0"] <= x1 + 2 and s["detail"]["x1"] >= x0 - 2]
    c = p = 0
    for b in bs:
        d = b["detail"]
        touch = False
        for s in st:
            sv = s["value"]; sy0, sy1 = sv[1], sv[1] + sv[3]
            if (d["x0"] <= s["detail"]["x1"] and d["x1"] >= s["detail"]["x0"]
                    and sy0 - Y_TOL <= d["y_center"] <= sy1 + Y_TOL):
                touch = True; break
        if touch or d["x0"] <= xc <= d["x1"]:
            c += 1; p += 1
        elif d["x0"] - w <= xc <= d["x1"] + w:
            p += 1
    return (c, p)

def beats_for(g, rule, policy="top"):
    h = head.get(g)
    if h is None: return None
    base = None
    for k, b in HEAD_BEATS.items():
        if str(h).startswith(k): base = b; break
    if base is None: return None
    c, p = levels(g, rule)
    n = dots.get(g, 0)
    def val(L):
        b = base / (2 ** L) if L else base
        t, add = b, b
        for _ in range(n):
            add /= 2.0; t += add
        return t
    if p > c:
        vals = [val(L) for L in range(c, p + 1)]
        return vals[0] if policy == "top" else min(vals)
    L = c
    if not L and flags.get(g): L = flags[g]
    return val(L)

# truth per (page, cell): "p:c0-c1=beats,..."
TRUTH = {}
for spec in sys.argv[2].split(","):
    where, beats = spec.split("=")
    pg, cells = where.split(":")
    a, _, b = cells.partition("-")
    for c in range(int(a), int(b or a) + 1):
        TRUTH[(int(pg), c)] = float(beats)
for rule in ("A", "B"):
    for policy in ("top", "lowest"):
        rows = []
        narrowed = 0
        for key, ev in events.items():
            if ev["outcome"] != "decided": continue
            _, p, sy, st, ce = key.split("/")
            if (int(p), int(ce)) not in TRUTH: continue
            gl = lambda i: f"glyph/{p}/{sy}/{st}/{ce}/{i}"
            evs = (ev.get("value") or {}).get("events") or []
            if any(gl(i) in rests for e in evs for i in (e.get("glyphs") or [])):
                continue
            total = 0.0
            for e in evs:
                bs = [beats_for(gl(i), rule, policy) for i in (e.get("glyphs") or [])]
                bs = [b for b in bs if b]
                if bs: total += Counter(bs).most_common(1)[0][0]
            if total > 0:
                rows.append((int(p), int(ce), round(total, 4)))
        for g in dur:
            c, pp = levels(g, rule)
            if pp > c: narrowed += 1
        bars = {}
        for pg, ce, t in rows: bars.setdefault((pg, ce), []).append(t)
        ok = tot = 0; detail = []
        for k in sorted(bars):
            L = bars[k]; mode, n = Counter(L).most_common(1)[0]
            if len(L) >= 3 and n / len(L) >= 0.5:
                tot += 1
                good = abs(mode - TRUTH[k]) < 1e-6
                ok += good
                detail.append(f"p{k[0]}c{k[1]}={mode}{'' if good else '*'}({n}/{len(L)})")
        print(f"rule {rule} / {policy:6s}: assessable {tot:2d}  correct {ok:2d}  "
              f"narrowed {narrowed:3d}   {' '.join(detail)}")
