"""2.197 C4: follow every truth accidental through GATHER -> ADJUDICATE -> EXPORT on ONE view (one tree's rows).
usage: c4_census.py TRUTH.json VIEW.json XML OUT.json [unit_px]
TRUTH items: page system staff(local) cell type label_family box [+ optional role]; TRUTH heads: hand-boxed noteheads/rests (page boxes).
Stage outcomes per item:
 G (gather):    not_boxed | boxed_key_class_only | boxed (acc* class box with an accidental_staff_position row); boxes on the ink listed; the class of the
                box that survives (accidental_staff_position.detail.detector_class / one_ink winner) is compared with the truth type.
 A (adjudicate): in-bar roles: accidental_owner decided (head) / abstained:<reason>; head correct = owner head overlaps the truth head.
                 key roles: marker rows in the staff's cell 0, key_signature verdict (outcome, value, reason).
 E (export):    in-bar: the owner head's <note>: <accidental> text and alter vs the truth type. key: key_signature value vs the truth count of key accidentals."""
import json, sys, collections
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from census_lib import View, iou, fam, kind, ALT
truth = json.load(open(sys.argv[1])); view = View(sys.argv[2], sys.argv[3]); out = sys.argv[4]
UNIT = float(sys.argv[5]) if len(sys.argv) > 5 else 32.0
heads = collections.defaultdict(list)
for h in truth["heads"]: heads[(h["page"], h["system"], h["staff"], h["cell"])].append(h)
# ---- truth-side: key counts per staff cell 0 (trusted only where the source swept: v18)
key_truth = collections.Counter()
for it in truth["items"]:
    if it["label_family"] == "key": key_truth[(it["src"], it["page"], it["system"], it["staff"])] += 1
res = []
for it in truth["items"]:
    if it["page"] not in view.boxes: continue          # a page this view does not hold
    tb = it["box"]; cx = (tb[0] + tb[2]) / 2; w = tb[2] - tb[0]; hgt = tb[3] - tb[1]
    cellk = (it["page"], it["system"], it["staff"], it["cell"])
    r = dict(it)
    r.pop("cell_rect", None)
    # ---- role (geometry on the hand-boxed heads of the same cell)
    frac = 0.715 if it["type"] in ("flat", "dflat") else 0.5
    ay = tb[1] + frac * hgt
    hs = [h for h in heads.get(cellk, ()) if "notehead" in h["cls"].lower()]
    cand = []
    for h in hs:
        hb = h["box"]; hx = (hb[0] + hb[2]) / 2; hy = (hb[1] + hb[3]) / 2
        dx = (hb[0] - tb[2]) / UNIT
        if hx > tb[2] - 0.3 * w and dx <= 4.0 and abs(hy - ay) <= 0.8 * UNIT:
            cand.append((abs(hy - ay) + 2 * max(dx, 0) * 0, dx, h))
    cand.sort(key=lambda c: (c[1] if c[1] > -0.5 else 99, c[0]))
    nearest = None
    if cand:
        cand.sort(key=lambda c: (abs(c[0]) / UNIT, c[1]))
        nearest = cand[0][2]
    r["truth_head"] = nearest["box"] if nearest else None
    crect = view.cellbox.get(cellk)
    xl = (tb[0] - crect[0]) / UNIT if crect else None          # distance from the cell's left edge, staff spaces
    r["x_from_cell_left_sp"] = round(xl, 2) if xl is not None else None
    if it["label_family"] == "key": role = "1_key_signature"
    elif it["cell"] == 0 and xl is not None and (xl <= 9.0 or any(
            k["label_family"] == "key" and (k["page"], k["system"], k["staff"], k["cell"]) == cellk and abs((k["box"][0] + k["box"][2]) / 2 - cx) <= 2.5 * UNIT
            for k in truth["items"])): role = "1b_key_accidental_labelled_accidental"   # inside the header band the key boxes occupy (5.4-8.3 sp)
    elif nearest is not None: role = "3_in_bar"
    else: role = "2or4_no_head_at_height"
    r["role"] = role
    # ---- END-TO-END at the TRUTH head (independent of which glyph the pipeline named as owner): the note the file wrote on the head Sean boxed
    r["E2"] = None
    if nearest is not None:
        best = None
        for g in view.boxes.get(it["page"], ()):
            if g.get("category") != "notehead": continue
            v = iou(nearest["box"], g["box"])
            if v >= 0.3 and g["key"] in view.xml_notes and (best is None or v > best[0]): best = (v, g)
        if best is None:
            r["E2"] = "truth_head_not_written"
        else:
            xn = view.xml_notes[best[1]["key"]]
            exp_alter = {"flat": "-1", "sharp": "1", "natural": "0", "dsharp": "2", "dflat": "-2"}[it["type"]]
            want_elem = {"dsharp": "double-sharp", "dflat": "flat-flat"}.get(it["type"], it["type"])
            r["E2"] = ("alter_right" if xn["alter"] == exp_alter else "alter_WRONG") + "/" + ("elem_right" if xn["accidental"] == want_elem else ("elem_absent" if not xn["accidental"] else "elem_wrong:" + xn["accidental"]))
            r["E2_note"] = xn
    # ---- GATHER
    gb = []
    for g in view.boxes.get(it["page"], ()):
        v = iou(tb, g["box"])
        if v >= 0.3: gb.append((v, g))
    gb.sort(key=lambda t: -t[0])
    famb = [(v, g) for v, g in gb if fam(g["cls"])]
    other = [(g["cls"], g["reader"], round(v, 2)) for v, g in gb if not fam(g["cls"])]
    r["boxes_on_ink"] = [dict(cls=g["cls"], iou=round(v, 3), conf=round(g["conf"] or 0, 3), reader=g["reader"], key=g["key"], cell=g["cell"], staff=g["staff"], box=g["box"]) for v, g in famb]
    r["other_on_ink"] = other
    if not famb:
        any_near = [(g["cls"], g["reader"], round(iou(tb, g["box"]), 2)) for g in view.boxes.get(it["page"], ()) if iou(tb, g["box"]) >= 0.1 or
                    (tb[0] <= (g["box"][0] + g["box"][2]) / 2 <= tb[2] and tb[1] <= (g["box"][1] + g["box"][3]) / 2 <= tb[3])]
        r["G"] = "not_boxed"; r["on_ink_any"] = any_near
        res.append(r); continue
    offered_kinds = sorted({kind(g["cls"]) for v, g in famb})
    r["offered_kinds"] = offered_kinds; r["offered_right_kind"] = it["type"] in offered_kinds
    accb = [(v, g) for v, g in famb if fam(g["cls"]) == "accidental" and g["key"] in view.accpos]
    # the glyphs on this ink that stand as ACCIDENTALS in the record (own cell/staff first)
    r["acc_glyphs"] = []
    for v, g in accb:
        row = view.accpos[g["key"]]; dt = row.get("detail") or {}
        own = view.verdict(g["key"], "accidental_owner"); gown = view.verdict(g["key"], "glyph_owner")
        r["acc_glyphs"].append(dict(key=g["key"], cls=g["cls"], conf=round(g["conf"] or 0, 3), alteration=dt.get("alteration"), detector_class=dt.get("detector_class"),
                                   absorbed=bool(dt.get("one_ink_absorbed")), one_ink=bool(dt.get("one_ink")), chosen_by=(dt.get("one_ink") or {}).get("chosen_by"),
                                   candidates=[(dt.get("one_ink") or {}).get("winner")] + list((dt.get("one_ink") or {}).get("rivals") or []) if dt.get("one_ink") else None,
                                   shape=((dt.get("shape") or {}).get("bl"), (dt.get("shape") or {}).get("tr")) if dt.get("shape") else None,
                                   owner=(own["outcome"], own["reason"], own.get("value")) if own else None,
                                   owner_alteration=((own.get("detail") or {}).get("alteration") if own and own["outcome"] == "decided" else None),
                                   shape_check=((own.get("detail") or {}).get("shape_check") if own and own["outcome"] == "decided" else None),
                                   glyph_owner=(gown["outcome"], gown["reason"], gown.get("value")) if gown else None,
                                   cell=g["cell"], staff=g["staff"]))
    r["G"] = "boxed" if accb else "boxed_key_class_only"
    # ---- ADJUDICATE / EXPORT, in-bar roles
    if it["label_family"] == "accidental" or accb:
        live = [a for a in r["acc_glyphs"] if a["owner"] and a["owner"][0] == "decided"]
        if live:
            a = live[0]; alt_used = a["owner_alteration"] or a["alteration"]    # the OWNER's alteration (2.190's shape check may have switched the class)
            r["A"] = "owner_decided"; r["A_alteration"] = alt_used; r["A_type_right"] = ALT.get(alt_used) == it["type"]; r["A_shape_switched"] = bool((a.get("shape_check") or {}).get("switched_from"))
            hk = a["owner"][2]; hg = view.by_key.get(hk)
            r["owner_head"] = hk
            if r["truth_head"] and hg:
                r["A_head_right"] = iou(r["truth_head"], hg["box"]) >= 0.3
            else:
                r["A_head_right"] = None
            xn = view.xml_notes.get(hk)
            if xn is None: r["E"] = "head_not_written"
            else:
                r["E_note"] = xn
                qa = view.verdict(hk, "accidental"); r["Qacc"] = (qa["value"], qa["reason"]) if qa else None
                exp_alter = {"flat": "-1", "sharp": "1", "natural": "0", "dsharp": "2", "dflat": "-2"}[it["type"]]
                r["E_alter_right"] = (xn["alter"] == exp_alter)
                got = xn["accidental"]
                r["E"] = "accidental_right" if got == {"dsharp": "double-sharp", "dflat": "flat-flat"}.get(it["type"], it["type"]) else ("no_accidental_elem" if not got else "accidental_wrong:" + got)
        elif r["acc_glyphs"]:
            reasons = sorted({(a["owner"][1] if a["owner"] else "no_verdict") for a in r["acc_glyphs"]})
            r["A"] = "abstained:" + "+".join(reasons)
        else:
            r["A"] = "no_accidental_row"
    # ---- key: marker rows and key_signature verdict of the staff
    skey = "staff/%d/%d/%d" % (it["page"], it["system"], it["staff"])
    ks = view.verdict(skey, "key_signature")
    if ks: r["KS"] = (ks["outcome"], ks["reason"], ks.get("value"))
    r["marker_rows"] = [(m["value"], (m.get("detail") or {}).get("detector_class"), (m.get("detail") or {}).get("detector_role")) for m in view.markers.get(skey, ())]
    res.append(r)
json.dump(res, open(out, "w"), default=str)
c = collections.Counter(r["G"] for r in res); print(dict(c))
