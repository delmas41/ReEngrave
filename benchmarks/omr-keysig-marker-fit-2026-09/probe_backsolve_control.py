"""Which y_center spelling reproduces the record exactly? Zero spread wins."""
import json, sys, collections, statistics
rec = json.load(open(sys.argv[1])); obs = rec["record"]["observations"]
half, box, pos = {}, {}, {}
for r in obs:
    q, s, d = r.get("quantity"), r.get("subject"), (r.get("detail") or {})
    if q == "cell_staff_space": half[s] = d.get("half_step")
    elif q == "glyph_box":      box[s] = r.get("value")
    elif q == "notehead_staff_position": pos[s] = r.get("value")
cell_of = lambda g: "cell/" + "/".join(g.split("/")[1:5])

for name, yc in (("float  y + h/2.0", lambda y, h: y + h / 2.0),
                 ("floor  y + h//2 ", lambda y, h: y + h // 2)):
    per = collections.defaultdict(list)
    for g, pf in pos.items():
        b, h = box.get(g), half.get(cell_of(g))
        if not b or h is None or pf is None: continue
        _, x, y, w, ht = b
        per[cell_of(g)].append(yc(float(y), float(ht)) - float(pf) * float(h))
    sp = sorted(max(v) - min(v) for v in per.values() if len(v) >= 2)
    exact = sum(1 for s in sp if s < 1e-9)
    print(f"{name}:  cells {len(sp):4d}   EXACT(spread<1e-9) {exact:4d}   max spread {max(sp):.6f}")
