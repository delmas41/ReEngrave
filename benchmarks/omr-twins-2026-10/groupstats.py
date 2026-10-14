import json, collections, statistics as st, sys
from pathlib import Path
OUT = Path(__file__).resolve().parent / "out"
a = json.load(open(OUT / "analysis_ranked.json"))
bg = json.load(open(OUT / "brahms_p0.json"))["glyphs"]
def med(xs):
    xs = [x for x in xs if x is not None]; return round(st.median(xs), 3) if xs else None
groups = collections.defaultdict(list)
for doc in a:
    T = {t["id"]: t for t in a[doc]["truth"]}
    for p in a[doc]["pairs"]:
        m, w = T[p["missed"]], T[p["written"]]
        groups[m["split_group"]].append((doc, m, w, p))
summary = {}
for g, lst in sorted(groups.items()):
    S = {"n": len(lst)}
    for side, idx in (("missed", 1), ("twin", 2)):
        ns = [x[idx]["nums"] for x in lst]
        S[side] = {f: med([n.get(f) for n in ns]) for f in ("conf", "w_sp", "h_sp", "ink", "cv_beams", "yolo_beams", "yolo_kept", "beams_not_by_ink", "flags_attached")}
        S[side]["w_sp_truthbox"] = med([x[idx]["w_sp"] for x in lst]); S[side]["h_sp_truthbox"] = med([x[idx]["h_sp"] for x in lst])
        S[side]["beam_evidence"] = dict(collections.Counter(n.get("beam_evidence") for n in ns))
        S[side]["dur_reason"] = dict(collections.Counter(n.get("dur_reason") for n in ns))
        S[side]["n_narrowed_in_bar_median"] = med([x[idx].get("n_narrowed_in_bar") for x in lst])
        S[side]["fate"] = dict(collections.Counter(x[idx]["code"] for x in lst))
        S[side]["guess_rule"] = dict(collections.Counter(n.get("guess_rule") for n in ns))
    summary[g] = S
# bar cascade for B and D
casc = {}
for g in ("B bar-sum hold-out", "D partial-bar gap"):
    c = collections.Counter(); notes = 0; wq = []
    for doc, m, w, p in groups[g]:
        notes += 1
        fates = dict(m["ctx"]["fates"]); 
        # remove this note's own fate
        own = m["code"]; 
        if own in fates: fates[own] -= 1
        others = {k: v for k, v in fates.items() if v > 0 and k not in ("written", own)}
        lost = {k: v for k, v in others.items() if k not in ("mark_group_duplicate", "owned_by_another_staff") and not k.startswith("held_bar") and k != "unread_gap_in_partial_bar"}
        if lost: c["another note in the bar was lost earlier (" + "+".join(sorted(lost)) + ")"] += 1
        else: c["no earlier loss among the boxed notes of the bar"] += 1
        bi = bg.get(m["box"], {}).get("bar_info") or {}
        if bi: wq.append((bi.get("want_quarters"), bi.get("voice_quarters")))
    casc[g] = {"n": notes, "cascade": dict(c), "bar_sums(want, per voice)": wq[:30]}
summary["_cascade"] = casc
json.dump(summary, open(OUT / "groupstats.json", "w"), indent=1, default=str)
print(json.dumps(summary, indent=1, default=str))
