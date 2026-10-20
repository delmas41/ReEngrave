"""2.167e probe 14: the four populations again, but only in the bars written RED (the held bars, 2.173; red list from the 2.173 replay on the same
20261018-night record). usage: e14_red.py PLATE(lit|bra)"""
import json
import sys
import collections

pl = sys.argv[1]
here = "probe/2.167e/data/"
G = json.load(open(here + "%s_all.json" % pl))
red = json.load(open(here + "%s_red_rows.json" % pl))
redcells = {(b["page"], b["system"], b["staff"], b["cell"]) for b in red if not b.get("doubled_staff_copy")}
print(pl, "red bars", len(red), "distinct cells", len(redcells))


def cell_of(sub):
    p = sub.split("/")
    return tuple(int(x) for x in p[1:5])


cnt = collections.defaultdict(collections.Counter)
for sub, g in G.items():
    inred = cell_of(sub) in redcells
    for scope in (("all",) + (("red",) if inred else ())):
        c = cnt[scope]
        cls = str(g.get("cls", ""))
        V = g.get("V", {})
        if cls.startswith("notehead"):
            nn = V.get("notehead_is_not_a_notehead")
            if nn and nn[2] is True:
                continue
            hs = V.get("head_stem")
            c["heads_kept"] += 1
            if hs and hs[0] == "narr" and hs[1] == "unison_two_voices":
                c["unison_two_voices"] += 1
            if hs and hs[0] == "narr" and hs[1] == "two_stems":
                c["two_stems"] += 1
        if cls == "rest8th":
            r = V.get("rest_is_not_a_rest")
            c["rest8th_boxes"] += 1
            c["rest8th_" + ("kept" if r and r[2] is False else (r[1] if r else "noverdict"))] += 1
        if "aug_dot" in g and cls == "augmentationDot":
            v = V.get("dot_role")
            c["augdot_boxes"] += 1
            c["augdot_" + ("none" if not v else ("%s_%s" % (v[0], v[1] if v[0] != "deci" else v[2])))] += 1
        v = V.get("unboxed_ink_is_a_rest")
        if v and v[1] == "rest8th_shape":
            c["rescue_8th_rests"] += 1
for scope in ("all", "red"):
    print("==", scope)
    for k, n in sorted(cnt[scope].items()):
        print("  ", k, n)
