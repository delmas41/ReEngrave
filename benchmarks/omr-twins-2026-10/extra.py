import json, collections, statistics as st, sys, re
from pathlib import Path
OUT = Path(__file__).resolve().parent / "out"
a = json.load(open(OUT / "analysis_ranked.json")); bg = json.load(open(OUT / "brahms_p0.json"))["glyphs"]
res = {}
# 1. funnel
for doc in ("brahms", "litolff"):
    T = a[doc]["truth"]; c = collections.Counter(t["code"] for t in T)
    res[f"funnel_{doc}"] = dict(c.most_common()); res[f"n_truth_{doc}"] = len(T)
    res[f"stage_counts_{doc}"] = dict(sorted(collections.Counter(t["stage"] for t in T).items()))
    res[f"blue_rules_{doc}"] = dict(collections.Counter(t["nums"].get("guess_rule") for t in T if t["code"] == "written_blue"))
    res[f"copies_{doc}"] = dict(collections.Counter(t["ncopies"] if "ncopies" in t else 0 for t in T))
# 2. A: whole-page narrowed notes: INFER collapsed (blue) vs lost, by number narrowed in the bar
cell_narrowed = collections.Counter()
for k, g in bg.items():
    if (g["cls"] or "").startswith("notehead") and g["place"] == "duration_narrowed" or (g["cls"] or "").startswith("notehead") and any(r["q"] == "duration" and r["stage"].startswith("ADJU") and r["outcome"] == "narrowed" for r in g["rows"]):
        cell_narrowed[(g["system"], g["staff"], g["cell"])] += 1
rows = []
for k, g in bg.items():
    if not (g["cls"] or "").startswith("notehead") or g["adj"] != "narrowed": continue
    if g["place"] not in ("duration_narrowed", "written", "written_relocated") and not g["rendered"]: continue
    fate = "collapsed_by_INFER_written_blue" if (g["rendered"] and (g["rendered"].get("guess") or {}).get("quantity") == "duration") else ("written_other" if g["rendered"] else g["place"] if g["place"] != "written" else (g["bar_fate"] or "?"))
    rows.append((fate, cell_narrowed[(g["system"], g["staff"], g["cell"])]))
tab = collections.defaultdict(list)
for f, n in rows: tab[f].append(n)
res["narrowed_notes_whole_page_by_fate"] = {f: {"n": len(v), "median_narrowed_in_bar": st.median(v), "share_alone_in_bar": round(sum(x == 1 for x in v)/len(v), 2)} for f, v in tab.items()}
# 3. A twins/misses: beam candidates
A = [(t, [x for x in a['brahms']['truth'] if x['id'] == p['written']][0]) for t in a['brahms']['truth'] for p in a['brahms']['pairs'] if p['missed'] == t['id'] and t['split_group'].startswith('A')]
res["A_missed_yolo_beam_boxes_cv_none"] = sum(1 for m, w in A if (m['nums'].get('yolo_beams') or 0) >= 1 and (m['nums'].get('cv_beams') or 0) == 0)
res["A_n"] = len(A)
res["A_missed_beam_evidence_none"] = sum(1 for m, w in A if m['nums'].get('beam_evidence') == 'none_over_this_note')
res["A_missed_other_narrowed_in_bar>=1"] = sum(1 for m, w in A if (m.get('n_narrowed_in_bar') or 0) >= 2)
res["A_twin_decided_without_a_beam_or_flag_read"] = sum(1 for m, w in A if w['nums'].get('beam_evidence') == 'none_over_this_note')
res["A_twin_noread_yolo_zero"] = sum(1 for m, w in A if w['nums'].get('beam_evidence') == 'none_over_this_note' and (w['nums'].get('yolo_beams') or 0) == 0)
res["A_twin_read_or_flag"] = sum(1 for m, w in A if w['nums'].get('beam_evidence') in ('read', 'flag'))
# 4. owner: decided owner staff vs truth cell staff, written truth notes
mis = []
for t in a["brahms"]["truth"]:
    if not t["box"]: continue
    g = bg[t["box"]]
    for r in reversed(g["rows"]):
        if r["q"] == "glyph_owner" and r["stage"].startswith("ADJU"):
            v = r["value"].strip('"')
            if r["outcome"] == "decided" and v != f"staff/0/0/{t['staff']}": mis.append((t["id"], t["code"], v, t["staff"]))
            elif r["outcome"] != "decided": mis.append((t["id"], t["code"], r["outcome"], t["staff"]))
            break
res["owner_not_the_cell_staff_brahms"] = {"n": len(mis), "rows": mis[:20]}
json.dump(res, open(OUT / "extra.json", "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
# 5. A: detector beam boxes KEPT near the stem but no CV beam read vs twins
mk = sum(1 for m, w in A if (m['nums'].get('yolo_kept') or 0) >= 1)
mk0 = sum(1 for m, w in A if (m['nums'].get('yolo_kept') or 0) >= 1 and (m['nums'].get('cv_beams') or 0) == 0)
wk = sum(1 for m, w in A if (w['nums'].get('yolo_kept') or 0) >= 1)
wk_dec = sum(1 for m, w in A if (w['nums'].get('yolo_kept') or 0) >= 1 and (w['nums'].get('dur_reason') or '').startswith('decided'))
res2 = {"A_missed_yolo_kept_ge1": mk, "A_missed_yolo_kept_ge1_and_cv0": mk0, "A_twin_yolo_kept_ge1": wk, "A_twin_yolo_kept_ge1_and_decided": wk_dec,
        "A_missed_cv_beams_median": st.median([m['nums'].get('cv_beams') or 0 for m, w in A]), "A_twin_cv_beams_median": st.median([w['nums'].get('cv_beams') or 0 for m, w in A]),
        "A_missed_cv_beams_zero": sum(1 for m, w in A if (m['nums'].get('cv_beams') or 0) == 0), "A_twin_cv_beams_zero": sum(1 for w in [w for m, w in A] if (w['nums'].get('cv_beams') or 0) == 0)}
print(json.dumps(res2)); res.update(res2); json.dump(res, open(OUT / "extra.json", "w"), indent=1, default=str)
