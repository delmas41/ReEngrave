"""2.306 r13 study, Q2 + Q5: the sample of heads OLD stems and NEW refuses (30 per plate), my print look (my_look_A.json, a LEAD) joined with the
trace and the swap experiment. Tallied by the DIFFERENCE between the readers that decides the head, not by NEW's reason word.
Usage: tally_A.py"""
import json, os, collections
from common import *
HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(HERE, "my_look_A.json")))
for pl in ("lit", "bra"):
    T = {r["g"]: r for r in json.load(open(S + "/r13/%s.trace.json" % pl))}
    SW = json.load(open(S + "/r13/%s.swap.json" % pl))
    gl = json.load(open(S + "/r13/%s.samples.json" % pl))["A"]
    c, ink, hd = collections.Counter(), collections.Counter(), collections.Counter()
    note = collections.Counter()
    for i, g in enumerate(gl, 1):
        lab = L[pl]["A%d" % i]
        r = T[g]
        note[lab[0]] += 1
        if lab[0] != "yes":
            c["(not a note / unclear: no stem to lose)"] += 0
            continue
        sw = SW.get(g, "")
        how = r["new_how"]
        fb = [f.split(":")[0] for f in r.get("fixed_by") or () if not f.startswith("ALL")] if r.get("replay_ok") else []
        held = r.get("map_held") or {h.get("owner"): 1 for h in (r.get("new_held") or [])}
        cov = r.get("map_vertical_cover") or 0
        if "claim holds it" in sw or (held and ("claims" in fb or how == "no_stroke") and cov >= 0.5):
            k = "CLAIM ORDER: the stem's stroke is held by another claim (%s); OLD knows no claims" % ",".join(sorted(str(x) for x in held) or ["?"])
        elif how in ("stroke_read_both_ways", "stroke_held_by_inked_heads", "stroke_held_by_its_head_end"):
            k = "ONE STROKE, ONE DIRECTION: another head box reads the same stroke the other way; OLD lets every box that touches a stem have it"
        elif how in ("two_candidates", "contact_two_candidates"):
            k = "UNIQUENESS: two strokes fit the head's side; OLD's finder filed only one of them as a stem"
        elif how == "contact_at_middle":
            k = "SIDE: the stem meets the head's ink at its middle; OLD has no side test"
        elif "no vertical run" in sw or cov < 0.5:
            k = "INK: the page map has no vertical piece on the stem (fused into a blob / curve / beam)"
        elif "side" in fb:
            k = "SIDE: the stem stands more than 0.4 sp off the head BOX edge (box narrower than / off the head); OLD only needs the boxes to touch"
        elif "reach" in fb:
            k = "REACH: the stem's piece at this head is shorter than 1.5 sp past the head (cut at a chord mate); OLD's stem box runs through the chord"
        else:
            k = "no_stroke, a free vertical touches the head box: side test, cause not isolated (%s)" % ("replay differs" if not r.get("replay_ok") else "no single relaxation")
        c[k] += 1
        ink["whole free vertical" if cov >= 0.9 and not held else ("vertical, held by a claim" if held and cov >= 0.5 else ("vertical on part of the stem" if cov >= 0.3 else "no vertical (blob / curve)"))] += 1
        hd["oval on the head's ink" if r["has_oval"] else "no oval: detector box"] += 1
    print(pl, "sample 30:", dict(note))
    for k, v in c.most_common():
        if v:
            print("  %3d  %s" % (v, k))
    print("   the stem's ink in the page map (real notes):", dict(ink))
    print("   the head as NEW received it (real notes):", dict(hd))

    # the same sorting over ALL heads OLD stems and NEW refuses (no print look: our own output), and the oval rate against all real heads
    allA = [r for r in T.values() if r["old_stem"] and r["new_read"] is False and r["new_how"] != "two_voices" and not r.get("not_real")]
    c2 = collections.Counter()
    x = collections.Counter()
    for r in allA:
        sw = SW.get(r["g"], "")
        how = r["new_how"]
        fb = [f.split(":")[0] for f in r.get("fixed_by") or () if not f.startswith("ALL")] if r.get("replay_ok") else []
        held = r.get("map_held") or {h.get("owner"): 1 for h in (r.get("new_held") or [])}
        cov = r.get("map_vertical_cover") or 0
        if "claim holds it" in sw or (held and ("claims" in fb or how == "no_stroke") and cov >= 0.5):
            k = "claim order"
        elif how in ("stroke_read_both_ways", "stroke_held_by_inked_heads", "stroke_held_by_its_head_end"):
            k = "one stroke, one direction"
        elif how in ("two_candidates", "contact_two_candidates"):
            k = "uniqueness (two strokes fit)"
        elif how == "contact_at_middle":
            k = "side: contact at the middle"
        elif "no vertical run" in sw or cov < 0.5:
            k = "ink: no vertical piece in the page map"
        elif "side" in fb:
            k = "side: off the head box edge"
        elif "reach" in fb:
            k = "reach"
        else:
            k = "no_stroke with a free vertical touching the box, not isolated"
        c2[k] += 1
        if r["g"] in gl:
            x[(k, L[pl]["A%d" % (gl.index(r["g"]) + 1)][0])] += 1
    print("   ALL %d (unlooked):" % len(allA), dict(c2.most_common()))
    real = [r for r in T.values() if not r.get("not_real")]
    print("   heads with an oval on their ink: all real heads %d of %d; in this set %d of %d" % (sum(1 for r in real if r["has_oval"]), len(real), sum(1 for r in allA if r["has_oval"]), len(allA)))
    print("   sample, bucket x my look (note yes/no/unclear):")
    for k in c2:
        print("      %-62s yes %d  no %d  unclear %d" % (k, x[(k, "yes")], x[(k, "no")], x[(k, "unclear")]))
