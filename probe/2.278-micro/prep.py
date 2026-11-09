"""2.278 micro: pull from one saved sample record (OMR_PAGE_BEAMS + CLAIM_NAMES on, through adjudicate) exactly what the group reader needs, and the
narrowed heads with their verdicts, into a small pickle. READ-ONLY on the record; one instrumented export for the `fates` (as probe/2.278/diag.py).

usage: python3 probe/2.278-micro/prep.py brahms|litolff OUT.pkl
"""
import sys, json, pickle, collections, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from load import load, BRAHMS, LITOLFF, EXPORT
from tools.omr.staged.record import Q

which, out = sys.argv[1], sys.argv[2]
d, R = load(BRAHMS if which == "brahms" else LITOLFF)
CAP = {}
orig = EXPORT._place_notes
def place(rec, runs, **kw):
    CAP["fates"] = kw.get("fates"); return orig(rec, runs, **kw)
EXPORT._place_notes = place
t = time.time()
xml, report = EXPORT.to_musicxml(d)
fates = CAP["fates"]
print("export", round(time.time() - t), "notes_not_written_total", report.get("notes_not_written_total"), flush=True)

obs = R.observations
pages = {}
def page_of_sub(s):
    p = s.split("/")
    if p[0] == "page": return int(p[1])
    return int(p[1])
for o in obs:
    q = o["quantity"]
    if q == "page_stroke":
        pg = page_of_sub(o["subject"]); dd = o["detail"]
        pages.setdefault(pg, {"strokes": {}, "claimed": {}, "tips": [], "pbeams": []})["strokes"][dd["ordinal"]] = dict(
            kind=o["value"], bbox=dd["bbox_page_px"], ends=dd.get("ends"), thick=dd.get("thickness_spaces"), length=dd.get("length_spaces"),
            profile=dd.get("profile_sixteenths"), sp=dd.get("staff_space_local_px"), staff=dd.get("staff"), touches=dd.get("touches"),
            sagitta=dd.get("sagitta_spaces"), angle=dd.get("angle_deg"), fill=dd.get("fill"))
    elif q == "page_beam_tip":
        pg = page_of_sub(o["subject"]); dd = o["detail"]
        pages.setdefault(pg, {"strokes": {}, "claimed": {}, "tips": [], "pbeams": []})["tips"].append(
            dict(stem=dd["stem"], stem_rows=dd["stem_rows"], end=dd["end"], tip_y=dd["tip_y"], n=o["value"], stem_beamed=dd["stem_beamed"],
                 tip_clean=dd["tip_clean"], hooks=dd["hooks"], beams=dd["beams"], joined=dd["joined"], staff=dd.get("staff")))
    elif q == "page_beam":
        pg = page_of_sub(o["subject"]); dd = o["detail"]
        if o["value"] == "census": continue
        if o["value"] == "views": continue
        pages.setdefault(pg, {"strokes": {}, "claimed": {}, "tips": [], "pbeams": []})["pbeams"].append(
            dict(ordinal=dd["ordinal"], role=o["value"], stems=dd["stems"], group=dd.get("group"), claimed_by=dd.get("claimed_by"), thick=dd["thickness_spaces"]))
    elif q == "claimed_area":
        dd = o["detail"] or {}
        if dd.get("page_strokes") and dd.get("unit") == "page_ink":
            pg = page_of_sub(o["subject"])
            pages.setdefault(pg, {"strokes": {}, "claimed": {}, "tips": [], "pbeams": []})["claimed"].setdefault(str(dd.get("owner")), set()).update(int(x) for x in dd["page_strokes"])
# claim ORDER: first claim wins (claim_order.layers), as page_beams does
from tools.omr.staged import claim_order as CO
claimed_first = collections.defaultdict(dict)
named = collections.defaultdict(list)
for o in obs:
    if o["quantity"] == "claimed_area":
        dd = o["detail"] or {}
        if dd.get("page_strokes"):
            pg = page_of_sub(o["subject"])
            lay = CO.layer_of(str(dd.get("owner") or ""))
            named[pg].append((lay if lay is not None else 99, len(named[pg]), dd))
for pg, lst in named.items():
    for _l, _k, dd in sorted(lst, key=lambda t: (t[0], t[1])):
        for s in dd["page_strokes"]:
            claimed_first[pg].setdefault(int(s), str(dd.get("owner") or "?"))
for pg in pages:
    pages[pg]["claimed"] = dict(claimed_first.get(pg, {}))
    pages[pg].pop("claimed_sets", None)

# row id -> page stem stroke ordinal, per page
rowmap = {}
for pg, P in pages.items():
    for t in P["tips"]:
        for r in t["stem_rows"]:
            rowmap[r] = (pg, t["stem"])

# heads: glyph subject -> page, bbox, stem row; duration verdict; fate
heads = {}
for sub in sorted({v["subject"] for v in R.verdicts_of(Q.DURATION)}):
    if not sub.startswith("glyph/"): continue
    fate = fates.get(sub)
    v = R.verdict(Q.DURATION, sub)
    nn = R.verdict("notehead_is_not_a_notehead", sub)
    gb = R.obs(Q.GLYPH_BOX, sub)
    hs = R.verdict(Q.HEAD_STEM, sub)
    sd = R.verdict(Q.STEM_DIRECTION, sub)
    rec = dict(fate=fate, page=page_of_sub(sub), not_a_notehead=(nn["value"] if nn and nn["outcome"] == "decided" else None),
               not_a_notehead_why=(nn["reason"] if nn else None))
    if gb:
        dd = gb[-1].get("detail") or {}
        rec["bbox"] = dd.get("bbox_page_px"); rec["cls"] = gb[-1]["value"][0] if gb[-1].get("value") else None
    if v:
        rec["outcome"] = v["outcome"]; rec["reason"] = v["reason"]; rec["value"] = v.get("value")
        rec["cands"] = [(c["value"].get("written"), c["value"].get("beam_levels"), c["value"].get("dots"), c.get("support")) for c in (v.get("candidates") or []) if isinstance(c.get("value"), dict)]
        dt = v.get("detail") or {}
        rec["d"] = {k: dt.get(k) for k in ("head", "head_is_open", "beam_evidence", "cv_beams", "yolo_kept", "stems_attached", "levels_certain", "levels_possible",
                                           "beam_side", "bare_stem_tip_window_clean", "bare_stem_likelihood", "refused_strokes", "beams_from_strokes", "flags_attached")}
    if hs and hs["outcome"] == "decided":
        rec["stem_row"] = hs["value"]
        rec["stem_ref"] = rowmap.get(hs["value"])
    if sd and sd["outcome"] == "decided":
        rec["stem_dir"] = sd["value"]
    heads[sub] = rec
print("pages", sorted(pages), "heads", len(heads), collections.Counter(h["fate"] for h in heads.values()).most_common(8))
cell_levels = {o["detail"]["stem_row_id"]: o["value"] for o in obs if o["quantity"] == "beam_stem_levels"}
pickle.dump(dict(cell_levels=cell_levels, pages=pages, heads=heads, args=d["provenance"]["settings"]["args"]["pages"]), open(out, "wb"))
print("wrote", out)
