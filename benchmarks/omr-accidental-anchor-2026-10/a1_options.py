"""2.199 A1: for every accidental glyph whose OWNER was decided or `no_candidate` on the frozen-sample view (tree B of 2.197), what would each ANCHOR option do?
The control: option `class` (today's rule) must reproduce the live verdict exactly. Offline replay of the owner's head search on the filed rows; it changes no verdict.
usage: a1_options.py VIEW.json OUT.json"""
import json, sys, collections
sys.path.insert(0, __file__.rsplit("/", 1)[0])
DX, DY, AMB = 1.75, 1.4, 0.5
d = json.load(open(sys.argv[1])); rec = d.get("record", d)
obs, ver = rec["observations"], rec["verdicts"]
chains = collections.defaultdict(list)
for v in ver: chains[(v["subject"], v["quantity"])].append(v)
live = {}
for k, ch in chains.items():
    sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
    live[k] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
acc, heads, hpos, space = {}, collections.defaultdict(dict), {}, {}
for o in obs:
    q = o["quantity"]
    if q == "accidental_staff_position": acc[o["subject"]] = o
    elif q == "notehead_staff_position" and isinstance(o["value"], (int, float)): hpos[o["subject"]] = float(o["value"])
    elif q == "glyph_box" and (o.get("detail") or {}).get("category") == "notehead" and isinstance(o["value"], list) and len(o["value"]) >= 5:
        s = o["subject"].split("/"); heads[tuple(s[1:5])][o["subject"]] = o["value"]
    elif q == "cell_staff_space":
        try: space[tuple(o["subject"].split("/")[1:5])] = float(o["value"])
        except Exception: pass

def head_pool(sub, own_staff_key):
    cell = tuple(sub.split("/")[1:5]); out = {}
    for hk, val in heads.get(cell, {}).items():
        nv = live.get((hk, "notehead_is_not_a_notehead"))
        if nv and nv["outcome"] == "decided" and nv["value"] is True: continue
        ow = live.get((hk, "glyph_owner"))
        if ow and ow["outcome"] == "decided" and isinstance(ow["value"], str) and ow["value"] != own_staff_key: continue
        out[hk] = val
    return cell, out

def search(sub, ax1, apos, pool, sp):
    cands = []
    for hk, (_c, hx, hy, hw, hh) in pool.items():
        if hx + hw < ax1: continue
        if max(0.0, hx - ax1) / sp > DX: continue
        if hk not in hpos: continue
        dp = abs(hpos[hk] - apos)
        if dp > DY: continue
        cands.append((dp, hk, hx, hw, hpos[hk]))
    if not cands: return ("none", None)
    cands.sort(); b = cands[0]
    ws = sorted(v[3] for v in pool.values()); nw = ws[len(ws) // 2] or 1.0
    for o in cands[1:]:
        if o[0] - b[0] >= AMB: break
        if abs((o[2] + o[3] / 2) - (b[2] + b[3] / 2)) <= nw and abs(o[4] - b[4]) < 0.5: continue
        return ("ambiguous", None)
    return ("head", b[1])

FR = {"accidentalflat": 0.715, "accidentaldoubleflat": 0.714, "accidentalsharp": 0.501, "accidentalnatural": 0.504, "accidentaldoublesharp": 0.504}
rows = []; ctl = collections.Counter()
for sub, o in acc.items():
    ov = live.get((sub, "accidental_owner"))
    if not ov or (ov["outcome"], ov["reason"]) not in (("decided", "immediately_right_same_position"), ("abstained", "no_candidate")): continue
    dt = o["detail"]; staff = "/".join(["staff"] + sub.split("/")[1:4])
    cell, pool = head_pool(sub, "staff/" + "/".join(sub.split("/")[1:4]))
    sp = space.get(cell)
    if not sp: continue
    ax1 = float(dt["x1"]); cls = str(dt["detector_class"]); ctr = float(dt["box_centre_position"]); apos = float(o["value"])
    h = float(dt["y1"]) - float(dt["y0"])
    half = sp / 2.0
    if ov["outcome"] == "decided" and (ov.get("detail") or {}).get("accidental_position") is not None:
        apos = float((ov["detail"])["accidental_position"])      # the position the live rule used (a shape switch moves it): makes the control exact
    res = {"class": search(sub, ax1, apos, pool, sp), "centre": search(sub, ax1, ctr, pool, sp)}
    # (b) union over the offered classes' anchors (rivals) -- all must name the same head
    pbc = dt.get("position_by_class") or {}
    ap = [apos] + [float(v["position"]) for v in pbc.values()]
    outs = [search(sub, ax1, a, pool, sp) for a in ap]
    res["union_offered"] = outs[0] if len({r for r in outs}) == 1 else ("disagree", None)
    # (c) the measured shape's class anchor: shape bl/tr class -> anchor fraction on this box
    shp = dt.get("shape") or {}
    sc = {"flat": "accidentalflat", "natural": "accidentalnatural", "sharp": "accidentalsharp"}.get(shp.get("shape"))
    if sc:
        # position under that class: box centre + (frac-0.5)*box height / half-space
        res["shape_class"] = search(sub, ax1, ctr + (FR[sc] - 0.5) * h / half, pool, sp)
    else: res["shape_class"] = ("unread", None)
    # fallback-only: today's class anchor, else the centre when the class anchor finds NO head
    res["fallback_centre"] = res["class"] if res["class"][0] != "none" else res["centre"]
    live_head = ov["value"] if ov["outcome"] == "decided" else None
    got = res["class"]
    ok = (got[0] == "head" and got[1] == live_head) if live_head else (got[0] == "none")
    ctl["control_ok" if ok else "control_FAIL"] += 1
    rows.append(dict(sub=sub, cls=cls, live=ov["reason"], live_head=live_head, shape=shp.get("shape"), shape_margin=shp.get("margin"), res=res,
                     centre_off=round(ctr - apos, 2), h_pos=round(h / half, 2)))
print("control (option class == live verdict):", dict(ctl))
def tab(sel, label):
    t = collections.Counter()
    for r in rows:
        if not sel(r): continue
        for opt in ("centre", "union_offered", "shape_class", "fallback_centre"):
            k, hk = r["res"][opt]
            if r["live"] == "immediately_right_same_position":
                t[(opt, "same head" if hk == r["live_head"] else ("other head" if k == "head" else k))] += 1
            else:
                t[(opt, "RECOVERED" if k == "head" else k)] += 1
    print("\n" + label)
    for k in sorted(t): print("  ", k, t[k])
tab(lambda r: r["live"].startswith("immediately"), "ALREADY DECIDED today -> option says:")
tab(lambda r: r["live"] == "no_candidate", "no_candidate today -> option says:")
for cl in ("accidentalFlat", "accidentalSharp", "accidentalNatural"):
    tab(lambda r, cl=cl: r["live"] == "no_candidate" and r["cls"] == cl, "no_candidate, class %s:" % cl)
json.dump(rows, open(sys.argv[2], "w"))
