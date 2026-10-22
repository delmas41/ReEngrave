"""2.167e probe 17: pick the crops to look at. usage: e17_pick.py WHAT OUT.json"""
import json
import random
import sys

what, out = sys.argv[1], sys.argv[2]
d = "probe/2.167e/data/"
random.seed(167)
items = []
if what == "whole":
    L = json.load(open(d + "lit_whole.json"))
    B = json.load(open(d + "bra_whole.json"))
    inv = lambda r: r["filled"] or r["stem_ink"]
    Lw = [r for r in L if inv(r)]
    Bs = [r for r in B if inv(r) and r["stem_ink"]]
    Bn = [r for r in B if inv(r) and not r["stem_ink"]]
    pick = [("lit", r) for r in random.sample(Lw, 4)] + [("bra", r) for r in random.sample(Bs, min(4, len(Bs)))] + [("bra", r) for r in random.sample(Bn, 4)]
    for pl, r in pick:
        items.append([pl, r["sub"], "%s %s c%.2f ctr%s st%s" % (pl, r["cls"][9:], r["conf"], r["center"], r["stem_ink"])])
    ctrl = [r for r in B if not inv(r)]
    for r in random.sample(ctrl, 2):
        items.append(["bra", r["sub"], "CONTROL hollow no stem c%.2f ctr%s" % (r["conf"], r["center"])])
elif what == "rests":
    A = json.load(open(d + "bra_all.json"))
    for reason in ("rest_clipped_by_crop", "rest_is_a_meter_digit", "rest_in_a_key_signature_slot", "rest_outside_its_staff"):
        sel = [s for s, g in A.items() if g.get("cls") == "rest8th" and g.get("V", {}).get("rest_is_not_a_rest", [0, 0, 0])[1] == reason]
        for s in random.sample(sel, min(3, len(sel))):
            items.append(["bra", s, "%s %.2f" % (reason[5:], A[s]["conf"])])
elif what == "wedge":
    A = json.load(open(d + "bra_all.json"))
    sel = [s for s, g in A.items() if g.get("cls") == "augmentationDot" and g.get("V", {}).get("dot_role", [0, 0, 0])[1] == "wedge_without_a_head"]
    for s in random.sample(sel, 9):
        items.append(["bra", s, "wedge_without_a_head %.2f" % A[s]["conf"]])
elif what == "unison":
    A = json.load(open(d + "lit_all.json"))
    sel = [s for s, g in A.items() if str(g.get("cls", "")).startswith("notehead") and g.get("V", {}).get("head_stem", [0, 0])[1] == "two_stems"]
    for s in random.sample(sel, 6):
        items.append(["lit", s, "two_stems"])
    sel = [s for s, g in A.items() if str(g.get("cls", "")).startswith("notehead") and g.get("V", {}).get("head_stem", [0, 0])[1] == "unison_two_voices"]
    for s in random.sample(sel, 6):
        items.append(["lit", s, "unison_two_voices"])
json.dump(items, open(out, "w"))
print(len(items))
