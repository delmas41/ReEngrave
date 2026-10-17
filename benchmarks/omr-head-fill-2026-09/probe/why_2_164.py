"""ROADMAP 2.164 Phase 1 -- WHY was each 2.160 left-edge arc-tail candidate kept as a notehead? Read off the extracted
night-record rows (`extract_2_164.py`); nothing re-decided. For each candidate: detector class + confidence, box size in
staff spaces, every notehead gate in `adjudicate_notehead_is_not_a_notehead` and why it did not fire, the re-centre
reading, the arc's box against its own cell's right edge (the barline), and what later readers made of the box.
STAGED GATHER+ADJUDICATE (read-only).
usage: why_2_164.py EXT.json TAILS.json OUT.json"""
import collections
import json
import sys

EXT, TAILS, OUT = sys.argv[1:4]
d = json.load(open(EXT))
hits = json.load(open(TAILS))["hits"]
obs = collections.defaultdict(list)
abst = collections.defaultdict(list)
ver = collections.defaultdict(list)
for o in d["observations"]:
    obs[o["subject"]].append(o)
for o in d["abstentions"]:
    abst[o["subject"]].append(o)
for v in d["verdicts"]:
    ver[v["subject"]].append(v)


def first(rows, q):
    r = [x for x in rows if x["quantity"] == q]
    return r[-1] if r else None


def live(rows, q):
    ch = [x for x in rows if x["quantity"] == q]
    if not ch:
        return None
    sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
    return ([x for x in ch if x["id"] not in sup] or ch)[-1]


def cellof(g):
    return "cell/" + "/".join(g.split("/")[1:5])


SHAPE = {"too_narrow", "is_a_dot", "on_a_barline", "clipped_fragment"}
out = []
for h in hits:
    g = h["glyph"]
    o, a, v = obs[g], abst[g], ver[g]
    box = first(o, "glyph_box")
    cls, _x, _y, w_c, h_c = box["value"]
    cell = cellof(g)
    sp_row = first(obs[cell], "cell_staff_space")
    sp_c = sp_row["value"] if sp_row else None
    w_sp, h_sp = (w_c / sp_c, h_c / sp_c) if sp_c else (None, None)
    nn = live(v, "notehead_is_not_a_notehead")
    nnd = (nn or {}).get("detail") or {}
    ink = first(o, "notehead_ink")
    ind = (ink or {}).get("detail") or {}
    rec = first(o, "notehead_recentre")
    rec_ab = first(a, "notehead_recentre")
    cross = first(o, "notehead_stem_cross_ink")
    # gates, each: fired / why not
    gates = {}
    gates["too_narrow"] = ("not_black_class" if not str(cls).lower().startswith("noteheadblack")
                           else ("fires" if w_sp is not None and w_sp < 1.0 else "wide_enough"))
    gates["dot_2.59"] = ("fires" if (w_sp is not None and w_sp <= 0.75 and h_sp <= 0.75)
                         else "not_dot_sized")
    gates["on_a_barline"] = "inside_dot_rule_only" if gates["dot_2.59"] != "fires" else "asked"
    gates["slash_2.137"] = "no_stem_cross_row" if cross is None else "cross_row_read"
    gates["rest_twin_2.142"] = "no_rest_box_under" if "rest_twin" not in json.dumps(nnd) else "signal"
    gates["rest_shape_2.145"] = "rest_shape" in nnd and "read" or "not_rest_shaped_or_not_read"
    gates["recentre_2.115"] = ("re-centred" if rec else ("declined:" + (rec_ab or {}).get("reason", "no row")))
    gates["stroke_2.150b"] = "rest_boxes_only"
    stem = live(v, "head_stem")
    dur = live(v, "duration")
    pitch = live(v, "pitch")
    # arc vs its own cell's right edge
    arc = first(obs[h["arc_glyph"]], "arc_box")
    arc_pg = ((arc or {}).get("detail") or {}).get("bbox_page_px")
    acb = first(obs[cellof(h["arc_glyph"])], "cell_box")
    cb = first(obs[cell], "cell_box")
    sp_pg = h["sp"]
    arc_end_vs_cell = round((acb["value"][2] - arc_pg[2]) / sp_pg, 3) if (acb and arc_pg) else None
    # other noteheads standing in the cell (lone event?)
    others = []
    for sub, rows in obs.items():
        if sub.startswith("glyph/") and cellof(sub) == cell and sub != g:
            gb = first(rows, "glyph_box")
            if gb and (gb.get("detail") or {}).get("category") == "notehead":
                n2 = live(ver[sub], "notehead_is_not_a_notehead")
                if n2 is None or n2.get("value") is False:
                    others.append(sub)
    out.append(dict(
        glyph=g, cls=cls, conf=round(box.get("score") or 0, 3), w_sp=round(w_sp, 2) if w_sp else None,
        h_sp=round(h_sp, 2) if h_sp else None, not_a_head=(nn or {}).get("value"), nn_reason=(nn or {}).get("reason"),
        gates=gates, ink=(ink or {}).get("value"), ink_net=(ind.get("ink_net") or {}).get("best"),
        ink_net_center=((ind.get("ink_net") or {}).get("windows") or {}).get("center"),
        iw=ind.get("interior_white"), arc_kind=h["kind"], arc=h["arc_glyph"], arc_conf=h["arc_conf"],
        arc_end_to_barline_sp=arc_end_vs_cell, head_left_gap_sp=h["left_gap_sp"],
        head_x0_minus_cell_x0_px=round(h["box"][0] - cb["value"][0], 1) if cb else None,
        head_stem=(stem or {}).get("outcome"), head_stem_reason=(stem or {}).get("reason"),
        duration=dict(outcome=(dur or {}).get("outcome"), reason=(dur or {}).get("reason"),
                      decider=(dur or {}).get("decider"),
                      value=(dur or {}).get("value")) if dur else None,
        pitch=(pitch or {}).get("value"), pitch_reason=(pitch or {}).get("reason"),
        other_heads_in_cell=len(others)))
json.dump(out, open(OUT, "w"), indent=1, default=str)
C = collections.Counter
print("n", len(out))
print("class", C(r["cls"] for r in out).most_common())
print("not_a_notehead", C((r["not_a_head"], r["nn_reason"]) for r in out).most_common())
for k in ("too_narrow", "dot_2.59", "slash_2.137", "recentre_2.115", "rest_twin_2.142"):
    print(k, C(r["gates"][k] for r in out).most_common())
print("arc end to its barline (sp)", sorted(r["arc_end_to_barline_sp"] for r in out if r["arc_end_to_barline_sp"] is not None))
print("head_stem", C((r["head_stem"], r["head_stem_reason"]) for r in out).most_common())
print("duration", C(((r["duration"] or {}).get("outcome"), (r["duration"] or {}).get("reason")) for r in out).most_common(12))
print("pitch", C(r["pitch_reason"] for r in out).most_common())
print("lone (no other standing head in cell)", sum(1 for r in out if r["other_heads_in_cell"] == 0))
