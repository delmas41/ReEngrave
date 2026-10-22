"""2.119 steps 1-2: truth notes -> detector boxes -> fate. Reads out/*.json (extract.py) + Sean's truth. Writes out/fates_*.json"""
import json, sys, collections, statistics
from pathlib import Path
REPO = Path("/Users/seanjohnson/Desktop/ReEngrave")
S = Path(__file__).resolve().parent
OUT = S / "out"
HOLLOW = ("noteheadHalf", "noteheadWhole", "noteheadDoubleWhole")
STRUCT = ("stem", "ledgerLine", "beam", "staff", "slur", "tie", "barline", "brace", "bracket")

def kind_of(cls):
    if cls.startswith("noteheadBlack"): return "black"
    if cls.startswith(HOLLOW): return "hollow"
    return "other"
def pos_of(cls):
    return "line" if cls.endswith("OnLine") else ("space" if cls.endswith("InSpace") else "?")
def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    if i <= 0: return 0.0
    return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i)
def area(r): return (r[2]-r[0])*(r[3]-r[1])
def same(t, r):   # 2.4b/2.110 matcher (score_ab.same), unchanged
    if iou(t, r) >= 0.3: return True
    cx, cy = (t[0]+t[2])/2, (t[1]+t[3])/2
    return r[0] <= cx <= r[2] and r[1] <= cy <= r[3] and area(r) <= 2.0*area(t)

# ---- fate of ONE detector box ------------------------------------------------------------------
# stage order = the order the pipeline asks its questions; a larger number = went further.
STAGES = ["S0 not detected", "S1 detected, wrong class", "S2 refused as a notehead (ADJUDICATE)", "S3 owner / duplicate",
          "S4 duration not decided", "S5 pitch not decided", "S6 bar held / unread gap", "S7 written"]
def box_fate(g, truth_kind):
    """(stage_index, code, detail) for a detector notehead box g."""
    ck = kind_of(g["cls"] or "")
    if ck != truth_kind and ck != "other":
        return (1, "class_wrong:%s_called_%s" % (truth_kind, ck), "")
    pl = g["place"]
    if pl in ("written", "written_relocated"):
        r = g["rendered"]
        if r:
            return (7, "written_blue" if r.get("guess") else "written_plain", "")
        bf = g["bar_fate"]
        if bf: return (6, bf.split(":")[0] if bf.startswith("unread") else bf, bf)
        return (6, "written_not_rendered", "")
    if pl is None: return (-1, "no_place_fate", "")
    if pl.startswith("not_a_notehead") or pl == "ink_is_a_whole_rest": return (2, pl, "")
    if pl in ("owned_by_another_staff", "mark_group_duplicate", "staff_not_identified", "owner_staff_has_no_measures", "cell_past_the_last_bar", "bar_count_not_decided"): return (3, pl, "")
    if pl.startswith("duration") or pl in ("chord_value_undecided",): return (4, pl, "")
    if pl.startswith("no_pitch") or pl.startswith("pitch"): return (5, pl, "")
    return (-2, pl, "")

def truth_notes_brahms():
    sys.path.insert(0, str(REPO))
    from tools.omr.hand_truth import store as ST
    page = ST.load(REPO / "data/hand-truth/pages/imslp317803/0.json")
    cells = {c.id: c for c in page.cells}
    out = []
    unins = 0
    for b in page.boxes:
        k = kind_of(b.cls)
        if not b.cls.startswith("notehead") or k == "other": continue
        c = cells[b.cell_id]
        if "all-ink" not in c.inspected:
            unins += 1; continue
        ys = c.staff_line_ys; sc = (c.rect[2]-c.rect[0]) / c.canonical_w
        space = (sum(ys[i+1]-ys[i] for i in range(len(ys)-1))/(len(ys)-1))*sc
        out.append({"id": b.id, "cls": b.cls, "kind": k, "pos": pos_of(b.cls), "rect": list(b.rect), "cell": b.cell_id,
                    "origin": b.origin, "system": c.system, "staff": c.staff, "space": space, "key": ("p", tuple(map(round, b.rect)))})
    return out, unins

def match_brahms(glyphs, truth, shift=0.0):
    boxed = [(k, g) for k, g in glyphs.items() if g["box_page"] is not None]
    for t in truth:
        r = t["rect"]; tr = (r[0]+shift*t["space"], r[1], r[2]+shift*t["space"], r[3])
        t["cands"] = [k for k, g in boxed if (g["cls"] or "").startswith("notehead") and same(tr, g["box_page"])]
        t["others"] = [k for k, g in boxed if not (g["cls"] or "").startswith("notehead") and not (g["cls"] or "").startswith(STRUCT) and same(tr, g["box_page"])]
        t["touch"] = [k for k, g in boxed if (g["cls"] or "").startswith("notehead") and k not in t["cands"] and iou(tr, g["box_page"]) > 0.05]
    return truth

def litolff_truth():
    """Sean's TEST cells' hollow heads, canonical frame, CLEAN cells only (the 9 leaked cells of 2.112 dropped)."""
    TESTB = REPO / "benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10"
    LEAK = {(0,2,3),(0,3,11),(0,3,14),(0,3,6),(0,3,7),(0,3,8),(0,7,1),(0,8,8),(0,9,15)}   # 2.112 fixtures/leaked9 file names
    cells = {c["cell_id"]: c for c in json.loads((TESTB/"cells.json").read_text())}
    out = []; n_all = 0
    for vf in sorted((TESTB/"verdicts").glob("*.verdict.json")):
        v = json.loads(vf.read_text()); c = cells[v["cell_id"]]
        key = (c["system_index"], c["staff_index"], c["measure_index"])
        for d in v["added_detections"]:
            if d["human_class"].startswith(HOLLOW):
                n_all += 1
                if key in LEAK: continue
                b = d["bbox"]
                out.append({"id": f"{v['cell_id']}#{len(out)}", "cls": d["human_class"], "kind": "hollow", "pos": pos_of(d["human_class"]),
                            "rect": [b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]], "cell": key, "origin": "sean-hollow-test",
                            "system": key[0], "staff": key[1], "space": None})
    return out, n_all, len(cells), len(LEAK & set((c["system_index"], c["staff_index"], c["measure_index"]) for c in cells.values()))

def match_litolff(glyphs, truth, shift_frac=0.0, wmed=None):
    by = collections.defaultdict(list)
    for k, g in glyphs.items():
        if g["box_canon"] is not None: by[(g["system"], g["staff"], g["cell"])].append((k, g))
    for t in truth:
        r = t["rect"]; d = shift_frac * (wmed or 0)
        tr = (r[0]+d, r[1], r[2]+d, r[3])
        cl = by.get(t["cell"], [])
        t["cands"] = [k for k, g in cl if (g["cls"] or "").startswith("notehead") and same(tr, g["box_canon"])]
        t["others"] = [k for k, g in cl if not (g["cls"] or "").startswith("notehead") and not (g["cls"] or "").startswith(STRUCT) and same(tr, g["box_canon"])]
        t["touch"] = [k for k, g in cl if (g["cls"] or "").startswith("notehead") and k not in t["cands"] and iou(tr, g["box_canon"]) > 0.05]
    return truth

def fate_of_truth(t, glyphs):
    if not t["cands"]:
        if t["others"]:
            return (0, "detected_other_class:" + ",".join(sorted({glyphs[k]["cls"] for k in t["others"]})), None)
        if t["touch"]: return (0, "not_detected(weak_overlap_only)", None)
        return (0, "not_detected", None)
    best = None
    for k in t["cands"]:
        f = box_fate(glyphs[k], t["kind"])
        # prefer: furthest stage; among equals prefer plain over blue? both stage 7; prefer higher box score
        key = (f[0], f[1] == "written_plain", glyphs[k]["score"] or 0)
        if best is None or key > best[0]: best = (key, f, k)
    return (best[1][0], best[1][1], best[2])
