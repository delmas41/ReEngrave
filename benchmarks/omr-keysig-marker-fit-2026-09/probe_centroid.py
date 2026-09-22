"""WHICH POINT of a flat's box is its notated position?

A flat is not vertically symmetric -- bowl low, ascender high -- so the box
CENTRE (what `_staff_positions_for` and the staged marker row both use) should
read HIGH of the slot. Test: recompute every measurable staff's offset using
several reference points and see which minimises |median offset|.

CONFIRMED IF one non-centre reference point drives the pooled median to ~0 on
BOTH publishers. REFUTED IF no reference point does, or if the two publishers
want different ones.
"""
import json, sys, statistics, collections
sys.path.insert(0, ".")
from tools.omr.key_signature_geometry import slot_positions

REC = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/beethoven5-p1-p4-ink-identity.record.json",
       "breitkopf": "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/brahms1-breitkopf-p0-p3.record.json"}
OUT = {"litolff": "benchmarks/omr-keysig-marker-fit-2026-09/out/litolff.json",
       "breitkopf": "benchmarks/omr-keysig-marker-fit-2026-09/out/brahms1-breitkopf.json"}

# reference point as a fraction f of the box height measured DOWN from the top:
#   y_ref = y_top + f*h    (f=0.5 is the centre the pipeline uses)
FRACS = [0.5, 0.6, 0.65, 0.7, 0.75, 0.8]

for tag in ("litolff", "breitkopf"):
    rec = json.load(open(REC[tag]))["record"]
    rows = json.load(open(OUT[tag]))["rows"]
    half, box, pos = {}, {}, {}
    for r in rec["observations"]:
        q, s, d = r.get("quantity"), r.get("subject"), (r.get("detail") or {})
        if   q == "cell_staff_space": half[s] = d.get("half_step")
        elif q == "glyph_box":        box[s] = r.get("value")
        elif q == "notehead_staff_position": pos[s] = r.get("value")
    cell_of = lambda g: "cell/" + "/".join(g.split("/")[1:5])
    agree = collections.defaultdict(list)
    for g, pf in pos.items():
        c = cell_of(g); b, h = box.get(g), half.get(c)
        if not b or h is None or pf is None: continue
        _, x, y, w, ht = b
        agree[c].append((float(y) + float(ht)//2) - float(pf)*float(h))
    top = {c: v[0] for c, v in agree.items() if max(v)-min(v) < 1e-6}

    # key-marker glyph boxes, per cell
    bycell = collections.defaultdict(list)
    for g, b in box.items():
        try: nm, x, y, w, h = b
        except Exception: continue
        if str(nm).lower().startswith(("keyflat", "keysharp")):
            bycell[cell_of(g)].append((float(x), float(y), float(w), float(h), str(nm)))

    print(f"\n######## {tag} ########")
    res = {f: [] for f in FRACS}
    n_boxes = 0
    for r in rows:
        p = r["staff"].split("/")
        c0 = f"cell/{p[1]}/{p[2]}/{p[3]}/0"
        h, ty = half.get(c0), top.get(c0)
        if h is None or ty is None: continue
        marks = sorted(bycell.get(c0, []), key=lambda m: m[0])
        marks = [m for m in marks if abs(((m[1]+m[3]/2)-ty)/h) < 10]   # drop junk
        if not marks: continue
        slots = slot_positions(r["clef"], "b")
        if not slots: continue
        s = sorted(slots[:len(marks)])
        n_boxes += len(marks)
        for f in FRACS:
            obs = sorted(((m[1] + f*m[3]) - ty)/h for m in marks)
            res[f].extend(o - sl for o, sl in zip(obs, s))
    print(f"   marker boxes used: {n_boxes}")
    for f in FRACS:
        v = res[f]
        if not v: continue
        lab = "  <- pipeline (box centre)" if f == 0.5 else ""
        print(f"   f={f:<5}  median {statistics.median(v):+.3f}   "
              f"spread {max(v)-min(v):.2f}   n={len(v)}{lab}")
