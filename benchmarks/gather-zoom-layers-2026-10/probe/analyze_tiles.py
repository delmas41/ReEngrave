"""2.152 A -- Sean's judged tiles x the three context facts.
usage: analyze_tiles.py TILES.json OUT.json  (pickles in tmp_2152/: litolff.pkl brahms.pkl brahms_p0p3.pkl)
"""
import json
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import ctx  # noqa: E402

PK = "tmp_2152/%s.pkl"
tiles = json.load(open(sys.argv[1]))
docs = {}


def doc(name):
    if name not in docs:
        docs[name] = ctx.Doc(PK % name)
    return docs[name]


def inside(bb, pb, pad=0.15):
    if not pb:
        return True
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    w, h = pb[2] - pb[0], pb[3] - pb[1]
    return pb[0] - pad * w <= cx <= pb[2] + pad * w and pb[1] - pad * h <= cy <= pb[3] + pad * h


rows = []
seen = set()
SEL = {"2.150": "width", "2.145": "gate", "2.148": "head_size_mixed"}
for t in tiles:
    if (t["doc"], t["glyph"]) in seen:      # the same box asked in two galleries counts once (recent first)
        continue
    seen.add((t["doc"], t["glyph"]))
    D = doc(t["doc"])
    r = D.glyph.get(t["glyph"])
    row = dict(sel=SEL.get(t["item"], "other"), item=t["item"], n=t["n"], doc=t["doc"], glyph=t["glyph"], sean=t["sean"], skind=t["kind"],
               what=t["what"], role=t.get("role"))
    if r is None:
        row["status"] = "no_box"
        rows.append(row)
        continue
    if not inside(r["bb"], t.get("page_box")):
        row["status"] = "key_moved"
        rows.append(row)
        continue
    row.update(cls=r["cls"], cat=r["cat"], kept=r["kept"], conf=r["conf"], w=round(r["w"], 2), h=round(r["h"], 2),
               vd=round(r["vd"], 2))
    refusal = D.vrd.get((t["glyph"], "notehead_is_not_a_notehead" if r["cat"] == "notehead" else "rest_is_not_a_rest"))
    row["gate_reason"] = refusal[2] if refusal else None
    # ---- ours vs Sean
    dur = r["dur"]
    if r["cat"] in ("notehead", "rest") and r["kept"]:
        ours = "head" if r["cat"] == "notehead" else "rest"
    elif r["cat"] in ("notehead", "rest"):
        ours = "refused"
    else:
        ours = "other:" + r["cls"]
    row["ours"] = ours
    row["dur"] = dur[:3] if dur else None
    k = t["kind"]
    TWIN = ("stacked_head_duplicate", "notehead_is_a_duplicate_box", "rest_is_a_duplicate_box")
    if ours == "refused" and row["gate_reason"] in TWIN:
        st = "twin_refused"          # the note lives on its twin box: the snapshot key moved, not an error
    elif ours == "refused":
        st = "right_refused" if k in ("nonnote", "stem_for_rest") else "lost_" + k
    elif ours.startswith("other"):
        st = "box_not_head_or_rest"
    elif k == "note":
        if ours == "rest":
            st = "rest_for_note"
        elif dur and dur[0] == "decided" and dur[1] and dur[1].get("beats") is not None:
            st = "right" if abs(dur[1]["beats"] - t["what"]) < 1e-6 else "value_error"
        elif dur and dur[0] == "narrowed":
            st = "narrowed"
        else:
            st = "abstained"
    elif k == "rest":
        st = "right" if ours == "rest" else "rest_as_head"
    else:   # nonnote / stem_for_rest
        st = "phantom_" + ours
    row["status"] = st
    # ---- the fixed cut-offs already in the tree (baselines): 2.148 head-sized window, 2.150 quarter-rest width floor
    if r["cat"] == "notehead":
        row["f148"] = not (0.9 <= r["h"] <= 1.8 and 1.1 <= r["w"] <= 1.9)
    if r["cls"] == "restQuarter":
        row["f150"] = r["w"] < 0.7
    # ---- the facts
    for kk in (3.0, 4.0, 5.0):
        p = D.p1(t["glyph"], kk)
        row["p1_%g" % kk] = None if p is None else bool(p["flag"])
    p = D.p1(t["glyph"], 4.0)
    if p:
        row["p1_detail"] = {x: [round(v, 2) for v in p[x]] for x in ("w", "h")}
        row["p1_n"] = p["n"]
    pd_ = D.p1(t["glyph"], 4.0, "doc")
    row["p1doc_4"] = None if pd_ is None else bool(pd_["flag"])
    s1 = D.s1(t["glyph"])
    row.update({"s1_" + a: b for a, b in s1.items()})
    for tol in (1.0, 1.5, 3.0):
        s2 = D.s2(t["glyph"], tol)
        if s2 is not None:
            row["s2a_%g" % tol] = bool(s2["a"])
            if tol == 1.5:
                row["s2b"] = bool(s2["b"])
                row["s2_nev"] = s2["n_events"]
                row["s2_nhdr"] = s2["n_hdr"]
    rows.append(row)
json.dump(rows, open(sys.argv[2], "w"), indent=0)
print(Counter((r["doc"], r["status"]) for r in rows).most_common())
