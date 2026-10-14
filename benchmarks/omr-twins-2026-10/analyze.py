"""2.119 steps 1-3: fates, twin pairs, split points. python3 analyze.py  -> out/fates_<doc>.json, out/pairs_<doc>.json, out/ranking.json"""
import json, re, sys, collections, math, statistics
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import match as M
from match import REPO, OUT

def jget(s, key):
    m = re.search(r'"%s":(-?[\d.]+)' % key, s or "")
    return float(m.group(1)) if m else None

def rows_of(g, q, stage=None):
    return [r for r in g["rows"] if r["q"] == q and (stage is None or r["stage"].startswith(stage))]

def last(g, q, stage=None):
    r = rows_of(g, q, stage); return r[-1] if r else None

# ---- per-note attributes ----------------------------------------------------------------------
def brahms_stems():
    sys.path.insert(0, str(REPO))
    from tools.omr.hand_truth import store as ST
    page = ST.load(REPO / "data/hand-truth/pages/imslp317803/0.json")
    cells = {c.id: c for c in page.cells}
    return [b.rect for b in page.boxes if b.cls == "stem"], cells

def stem_dir_truth(t, stems):
    x0, y0, x1, y1 = t["rect"]; w, h = x1-x0, y1-y0; cx = (x0+x1)/2
    best = None
    for s in stems:
        if s[3] < y0 - 0.4*h or s[1] > y1 + 0.4*h: continue
        sc = (s[0]+s[2])/2
        if not (x0 - 0.4*w <= sc <= x1 + 0.4*w): continue
        if abs(sc-cx) < 0.15*w and False: continue
        d = abs(sc - (x1 if sc > cx else x0))
        if best is None or d < best[0]: best = (d, "up" if sc > cx else "down")
    return best[1] if best else "none"

def pos_kind_brahms(t, cells):
    c = cells[t["cell"]]
    ys = c.staff_line_ys; sc = (c.rect[3]-c.rect[1]) / c.canonical_h   # canonical y -> page y (isotropic with x?)
    sx = (c.rect[2]-c.rect[0]) / c.canonical_w
    sp = sum(ys[i+1]-ys[i] for i in range(4)) / 4
    top = c.rect[1] + ys[0]*sc; bot = c.rect[1] + ys[4]*sc
    cy = (t["rect"][1]+t["rect"][3])/2; spp = sp*sc
    t["staff_top_page"], t["staff_bot_page"], t["space_y"] = top, bot, spp
    if cy < top - 0.6*spp or cy > bot + 0.6*spp: return "ledger"
    return t["pos"]

def box_numbers(g, glyphs, key):
    d = {"conf": round(g["score"], 3) if g["score"] is not None else None}
    adj = last(g, "notehead_is_not_a_notehead", "ADJU")
    if adj:
        d["w_sp"] = jget(adj["detail"], "width_spaces"); d["h_sp"] = jget(adj["detail"], "height_spaces")
        d["adj"] = f"{adj['outcome']}:{adj['reason']}:{adj['value']}"
        d["adj_detail"] = (adj["detail"] or "")[:420]
    ink = last(g, "notehead_ink", "GATH")
    d["ink"] = float(ink["value"]) if ink and ink["value"] not in (None, "null") else None
    for q, tag in (("duration", "dur"), ("stem_value", "stem_value"), ("head_stem", "head_stem"), ("stem_direction", "stem_dir"),
                   ("glyph_owner", "owner"), ("pitch", "pitch")):
        r = last(g, q)
        if r: d[tag] = f"{r['stage'][:4]}:{r['outcome']}:{r['reason']}:{r['value'][:90]}"
    inf = [r for r in g["rows"] if r["stage"].startswith("INFE") and r["q"] == "duration"]
    rn = g["rendered"] or {}
    if rn.get("guess"):
        gg = rn["guess"]; d["guess_rule"] = gg.get("rule"); d["guess_q"] = gg.get("quantity")
        d["guess_cands"] = [(c.get("written"), c.get("support")) for c in gg.get("candidates", [])]
    dr = last(g, "duration", "ADJU")
    if dr:
        dd = dr.get("detail") or ""
        d["dur_reason"] = f"{dr['outcome']}:{dr['reason']}"
        for f in ("cv_beams", "yolo_beams", "yolo_kept", "beams_not_by_ink", "flags_attached", "flag_levels", "levels_certain", "stems_attached", "beams_by_stem"):
            d[f] = jget(dd, f)
        m = re.search(r'"beam_evidence":"([^"]*)"', dd); d["beam_evidence"] = m.group(1) if m else None
        m = re.search(r'"beams_not_by_ink_why":(\{[^}]*\})', dd); d["not_by_ink_why"] = m.group(1) if m else None
        d["refused_stroke_at_tip"] = "bare_stem_refused_stroke_at_tip\":true" in dd
    if dr and dr["outcome"] == "narrowed":
        d["dur_candidates"] = dr["detail"][:300] if dr.get("detail") else None
    bi = g.get("bar_info")
    if bi: d["bar"] = {k: bi[k] for k in ("want_quarters", "voice_quarters", "plan_why", "n_events")}; d["bar_unplaced"] = [u["reason"] for u in bi["unplaced"]]
    return d

def cell_context(g, glyphs):
    """what else in this bar did not reach the file (note-like boxes only)."""
    key = (g["system"], g["staff"], g["cell"])
    c = collections.Counter(); n = 0
    for k, o in glyphs.items():
        if (o["system"], o["staff"], o["cell"]) != key or not (o["cls"] or "").startswith(("notehead", "rest")): continue
        n += 1
        if o["rendered"]: c["written"] += 1
        else: c[o["place"] if o["place"] != "written" else (o["bar_fate"] or "written_not_rendered")] += 1
    return {"n_note_like_boxes": n, "fates": dict(c)}

# ---- pairing ------------------------------------------------------------------------------------
def sig(t): return (t["kind"], t["stem"], t["posk"])

def sig2(t): return (t["kind"], t["posk"])

def make_pairs(notes, space_of):
    W = [t for t in notes if t["stage"] == 7 and not t.get("fragment")]; Mi = [t for t in notes if t["stage"] < 7 and not t.get("fragment")]
    pairs, un = _pairs(notes, W, Mi, space_of, sig, "strict")
    left = [t for t in Mi if t["id"] in set(un)]
    free = [t for t in W if t["id"] not in {p["written"] for p in pairs}]
    p2, un2 = _pairs(notes, free, left, space_of, sig2, "relaxed(stem ignored)")
    return pairs + p2, un2

def _pairs(notes, W, Mi, space_of, sigf, label):
    edges = []
    for m in Mi:
        for w in W:
            if sigf(m) != sigf(w): continue
            tier = 1 if (m["system"], m["staff"]) == (w["system"], w["staff"]) else (2 if m["system"] == w["system"] else 3)
            sp = space_of(m)
            dx = abs((m["rect"][0]+m["rect"][2])/2 - (w["rect"][0]+w["rect"][2])/2) / sp
            dsz = (abs((m["rect"][2]-m["rect"][0]) - (w["rect"][2]-w["rect"][0])) + abs((m["rect"][3]-m["rect"][1]) - (w["rect"][3]-w["rect"][1]))) / sp
            edges.append((tier, round(dsz, 3), round(dx, 2), m["id"], w["id"]))
    edges.sort()
    used_m, used_w, pairs = set(), set(), []
    byid = {t["id"]: t for t in notes}
    for tier, dsz, dx, mi, wi in edges:
        if mi in used_m or wi in used_w: continue
        used_m.add(mi); used_w.add(wi); pairs.append({"rule": label, "tier": tier, "size_diff_sp": dsz, "dx_sp": dx, "missed": mi, "written": wi})
    unpaired = [m["id"] for m in Mi if m["id"] not in used_m]
    return pairs, unpaired

def analyze(doc, glyphs, notes, space_of):
    for t in notes:
        stage, code, key = M.fate_of_truth(t, glyphs)
        t["stage"], t["code"], t["box"] = stage, code, key
        if key:
            g = glyphs[key]
            t["nums"] = box_numbers(g, glyphs, key); t["ctx"] = cell_context(g, glyphs)
            t["ncopies"] = len(t["cands"])
        else:
            t["nums"] = {}; t["ctx"] = {}
        t["w_sp"] = (t["rect"][2]-t["rect"][0]) / space_of(t); t["h_sp"] = (t["rect"][3]-t["rect"][1]) / space_of(t)
        t["fragment"] = bool(t["w_sp"] < 0.7 or t["h_sp"] < 0.7)   # Sean's own box is a sliver: not a look-alike of a whole head
        if t["box"]:
            c = t["ctx"].get("fates", {}) if t["ctx"] else {}
            t["n_narrowed_in_bar"] = c.get("duration_narrowed", 0)
    pairs, unp = make_pairs(notes, space_of)
    return pairs, unp
