"""2.306 r13 study: for every real head, both readers' answers side by side and -- where OLD stems and NEW refuses -- which DIFFERENCE between the
two readers decides it, found by experiment on ONE gather: NEW is re-run offline with one of its own tests relaxed at a time; the relaxation that
makes NEW name OLD's stem (same column, same direction) is the difference that mattered. Where no relaxation does, what the page map holds where
OLD's stem box stands is recorded (no vertical piece / part / held). Our own output: a lead until print-checked (look.py).
Usage (cwd = repo root): trace.py lit|bra  -> scratch r13/<plate>.trace.json"""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import replay as RP
from tools.omr.staged import page_stems as PS

plate = sys.argv[1]
D = load(plate)
ups = cell_up(D)
BASE = dict(EDGE_SP=PS.EDGE_SP, GAP_SP=PS.GAP_SP, REACH_SP=PS.REACH_SP, HEAD_END_SP=PS.HEAD_END_SP, CONTACT_MID_SP=PS.CONTACT_MID_SP, NEAR_SP=PS.NEAR_SP)
VARIANTS = collections.OrderedDict([
    ("side: the stem must stand within 0.4 sp of the head BOX edge", dict(EDGE_SP=1.3, NEAR_SP=1.6)),
    ("gap: the stem's head end within 2 sp of the head centre", dict(GAP_SP=8.0)),
    ("reach: the stem runs 1.5 sp past the head centre", dict(REACH_SP=0.4)),
    ("head end: a stroke ending >0.5 sp past the head is another head's", dict(HEAD_END_SP=4.0)),
    ("contact at the head's middle names no side", dict(CONTACT_MID_SP=0.0)),
    ("claims: a stroke another claim holds is never a stem", dict(_held=False)),
])


def read_with(inp, over):
    for k, v in BASE.items():
        setattr(PS, k, over.get(k, v))
    try:
        held = inp["held"] if over.get("_held", True) else {}
        return PS.read(inp["heads"], inp["verticals"], held, crossers=inp["crossers"], strokes=inp["strokes"])
    finally:
        for k, v in BASE.items():
            setattr(PS, k, v)


def same_column(a, b, sp):
    """a, b = (x0, y0, x1, y1): one column, sharing at least half the shorter's length."""
    if a is None or b is None:
        return False
    ov = min(a[3], b[3]) - max(a[1], b[1])
    return abs((a[0] + a[2]) / 2.0 - (b[0] + b[2]) / 2.0) <= max(3.0, 0.35 * sp) and ov >= 0.5 * min(a[3] - a[1], b[3] - b[1])


def gives_old(res, hid, old_box, old_dir, sp):
    r = res["heads"].get(hid)
    if not r or r.get("state") not in ("one", "second") or r.get("stroke") is None:
        return False
    st = res["stems"].get(r["stroke"])
    if not st:
        return False
    return same_column(st["box"], old_box, sp) and (old_dir is None or r["direction"] == old_dir)


rows = []
for p in D["pages"]:
    inp = RP.run(D, p)
    gh = {m: h["id"] for h in inp["heads"] for m in h["members"]}
    hbox = {h["id"]: h for h in inp["heads"]}
    var_res = {name: read_with(inp, over) for name, over in VARIANTS.items()}
    all_over = {}
    for over in VARIANTS.values():
        all_over.update(over)
    var_res["ALL relaxed together"] = read_with(inp, all_over)
    ps = D["pstrokes"][p]
    for g in sorted(D["heads"]):
        if pg(g) != p or not is_real(D, g, "on"):
            continue
        o, n = old_answer(D, g), new_answer(D, g)
        hid = gh.get(g)
        sp = staff_sp(D, g)
        ob = stem_page_box(D, ups, o["stem"]) if o["stem"] else None
        row = dict(g=g, page=p, hid=hid, head_box=D["heads"][g]["box"], new_head_box=list(hbox[hid]["box"]) if hid in hbox else None, has_oval=bool(hid in hbox and hbox[hid]["ink"]),
                   cls=D["cls"].get(g), old_stem=o["stem"], old_why=o["why"], old_dir=o["direction"], old_dir_why=o["dir_why"], old_box=ob,
                   old_xfrac=(o["detail"] or {}).get("x_frac"), new_read=n["read"], new_how=n["how"], new_dir=n["direction"], new_stroke=n["stroke"],
                   new_box=(n["row"] or {}).get("stem_box"), new_held=(n["row"] or {}).get("held"), new_cands=(n["row"] or {}).get("candidates"), sp=sp,
                   written_off=g in D["written_off"], written_on=g in D["written_on"])
        if hid is not None:
            rr = inp["res"]["heads"].get(hid) or {}
            row["replay_ok"] = bool(rr.get("how") == n["how"] and rr.get("stroke") == n["stroke"])
        if o["stem"] and n["read"] is False and ob is not None and hid is not None:
            # what the page map holds along OLD's stem box
            cover, kinds, held_by = [], collections.Counter(), collections.Counter()
            xc = (ob[0] + ob[2]) / 2.0
            for i, s in ps.items():
                b = s["box"]
                if b[0] - 2 <= xc <= b[2] + 2 and min(b[3], ob[3]) - max(b[1], ob[1]) > 0:
                    share = (min(b[3], ob[3]) - max(b[1], ob[1])) / max(1.0, ob[3] - ob[1])
                    kinds[s["kind"]] += share
                    if s["kind"] == "vertical":
                        cover.append((max(b[1], ob[1]), min(b[3], ob[3])))
                        if i in inp["held"]:
                            held_by[inp["held"][i]] += share
            edge, tot = ob[1], 0.0
            for a, b in sorted(cover):
                a = max(a, edge)
                if b > a:
                    tot += b - a
                    edge = b
            row["map_vertical_cover"] = round(tot / max(1.0, ob[3] - ob[1]), 2)
            row["map_kinds"] = {k: round(v, 2) for k, v in kinds.items()}
            row["map_held"] = {k: round(v, 2) for k, v in held_by.items()}
            row["fixed_by"] = [name for name, res in var_res.items() if gives_old(res, hid, ob, o["direction"], sp)]
        rows.append(row)
json.dump(rows, open("%s/r13/%s.trace.json" % (S, plate), "w"))
A = [r for r in rows if r["old_stem"] and r["new_read"] is False and r["new_how"] != "two_voices"]
print(plate, "real heads", len(rows), "| OLD stems, NEW refuses", len(A), "| of those the offline replay reproduces NEW", sum(1 for r in A if r.get("replay_ok")))
c = collections.Counter()
for r in A:
    fb = [f for f in r.get("fixed_by") or () if not f.startswith("ALL")]
    if len(fb) == 1:
        c[fb[0]] += 1
    elif len(fb) > 1:
        c["any one of: " + " | ".join(sorted(f.split(":")[0] for f in fb))] += 1
    elif "ALL relaxed together" in (r.get("fixed_by") or ()):
        c["only with several tests relaxed together"] += 1
    else:
        cov = r.get("map_vertical_cover", 0)
        held = r.get("map_held") or {}
        if held:
            c["no relaxation; the vertical there is held by: " + ",".join(sorted(held))] += 1
        elif cov >= 0.6:
            c["no relaxation; a free vertical stands on OLD's stem"] += 1
        elif cov > 0:
            c["no relaxation; only PART of OLD's stem is a vertical piece in the page map"] += 1
        else:
            c["no relaxation; NO vertical piece in the page map on OLD's stem (%s)" % ",".join(sorted(r.get("map_kinds") or {"nothing": 1}))] += 1
for k, v in c.most_common():
    print("  %4d  %s" % (v, k))
