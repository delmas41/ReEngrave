"""2.186 analysis of the replay outputs (full2/<doc>.{off,on}.json) + slices + glyph_owner extract.
usage: analyse_2_186.py DOC REPLAYDIR SLICEDIR GOWN.jsonl KEY2182a.json OUT.json"""
import collections, glob, json, os, statistics, sys
sys.path.insert(0, ".")
from tools.omr.staged import one_ink as OI
DOC, RD, SD, GOWN, K182, OUT = sys.argv[1:7]
off = json.load(open(os.path.join(RD, DOC + ".off.json")))
on = json.load(open(os.path.join(RD, DOC + ".on.json")))
R = {}
R["control_off_equals_stored"] = off["control"]
def pick(d):
    c = d.get("accidental_census") or {}
    w = d.get("written") or {}
    return dict(notes_in_file=d["xml"]["notes"], pitched=d["xml"]["pitched"], rests_written=d["xml"]["rests"], rests_guessed_blue=d["xml"]["guessed_rests"],
                accidentals_printed=d["xml"]["accidentals"], notes_guessed_blue=d["xml"]["guessed_notes_blue"], beams=d["xml"]["beams"],
                red_bars=d["bars_written_red"], red_rows=d["red_rows"], notes_not_written_total=d["notes_not_written_total"],
                bars_add_up_exact=d["bars_add_up"].get("exact"), bars_add_up_n=d["bars_add_up"].get("n"),
                heads_owned=c.get("heads_owned"), heads_contradicted=c.get("heads_contradicted"), owner_decided=c.get("owner_decided"),
                accidental_applied=c.get("applied"), owned_by_another_staff=c.get("owned_by_another_staff"), ownership_undecided=c.get("ownership_undecided"),
                accidental_unaccounted=c.get("unaccounted"), heads_balanced=c.get("heads_balanced"),
                guessed_by_one_ink=d.get("guessed_by_one_ink"), flags_in_file_beams=d["xml"]["beams"],
                rest_dup_refused=(d["notes_not_written"] or {}).get("not_a_rest:rest_is_a_duplicate_box"))
R["off"], R["on"] = pick(off), pick(on)
vo, vn = off["verdicts"], on["verdicts"]
# key signature unchanged
ks_o, ks_n = vo.get("key_signature", {}), vn.get("key_signature", {})
R["key_signature_verdicts"] = dict(off=len(ks_o), on=len(ks_n), differ=sum(1 for g in set(ks_o) | set(ks_n) if ks_o.get(g, [None])[:3] != ks_n.get(g, [None])[:3]))
# flags: duration reasons that name a flag disagreement
dur_o = collections.Counter(v[2] for v in vo["duration"].values()); dur_n = collections.Counter(v[2] for v in vn["duration"].values())
R["duration_reasons_flag"] = {k: (dur_o.get(k, 0), dur_n.get(k, 0)) for k in ("flags_disagree", "hooks_counted", "open_head_flag_contradiction")}
R["duration_verdicts_differing_off_vs_on"] = sum(1 for g in set(vo["duration"]) | set(vn["duration"]) if vo["duration"].get(g, [None] * 3)[:3] != vn["duration"].get(g, [None] * 3)[:3])
# rests
rn = collections.Counter(); rfate = collections.Counter()
for g, v in vn["rest_is_not_a_rest"].items():
    if v[4]:
        rn["merged_rest_winners"] += 1
        rfate[(v[0], v[1], v[2])] += 1
R["rest_merged_winner_fate_on"] = {str(k): n for k, n in rfate.items()}
R["rest_reason_counts"] = dict(off={k: n for k, n in collections.Counter(v[2] for v in vo["rest_is_not_a_rest"].values()).items()},
                               on={k: n for k, n in collections.Counter(v[2] for v in vn["rest_is_not_a_rest"].values()).items()})
# accidentals
ao, an = vo["accidental_owner"], vn["accidental_owner"]
ch = collections.Counter()
for g in set(ao) | set(an):
    o, n = ao.get(g), an.get(g)
    if o is None or n is None:
        ch["only_" + ("off" if o else "on")] += 1; continue
    if o[0] == "deci" and n[0] == "abst":
        ch["decided_to_abstained:" + str(n[2])] += 1
    elif o[0] == "abst" and n[0] == "deci":
        ch["abstained_to_decided"] += 1
    elif o[0] == "deci" and n[0] == "deci":
        ch["decided_same_head" if o[1] == n[1] else "decided_other_head"] += 1
        if o[5] != n[5]:
            ch["alteration_changed"] += 1
    else:
        ch["abstained_both" + ("" if o[2] == n[2] else ":reason_changed")] += 1
R["accidental_owner_off_vs_on"] = dict(ch)
R["accidental_owner_merged_on"] = sum(1 for v in an.values() if v[4])
# heads contradicted by head, from the verdict briefs (alteration index 5)
def contradicted(a):
    alt = collections.defaultdict(set)
    for g, v in a.items():
        if v[0] == "deci":
            alt[v[1]].add(v[5])
    return sum(1 for s in alt.values() if len(s) > 1), len(alt)
R["heads_contradicted_from_verdicts"] = dict(off=contradicted(ao), on=contradicted(an))
# merged inks: margin distribution (every merge, incl. later-refused ones), from the slices
margins = collections.defaultdict(list); pairs = collections.Counter()
cells = collections.defaultdict(list)
for p in sorted(glob.glob(os.path.join(SD, DOC, "p*.observations.jsonl"))):
    for l in open(p):
        if '"glyph_box"' in l:
            o = json.loads(l)
            if o["quantity"] == "glyph_box" and o["reader"] == "detector" and isinstance(o["value"], list):
                cells["/".join(o["subject"].split("/")[:5])].append(o)
for cell, bs in cells.items():
    bs.sort(key=lambda o: int(o["subject"].split("/")[5]))
    pl = OI.plan([(o["value"][0], o["value"][1], o["value"][2], o["value"][3], o["value"][4], o["score"] or 0.0) for o in bs])
    for i, info in pl.items():
        fam = OI.family_of(bs[i]["value"][0])
        margins[fam].append(info["margin"])
        pairs[(fam, bs[i]["value"][0] + "<-" + "+".join(sorted(r["class"] for r in info["rivals"])))] += 1
def dist(m):
    m = sorted(m)
    if not m: return {}
    q = lambda f: m[min(len(m) - 1, int(f * len(m)))]
    bins = collections.Counter(min(int(x / 0.1), 9) for x in m)
    return dict(n=len(m), min=m[0], p10=q(.1), p25=q(.25), median=q(.5), p75=q(.75), p90=q(.9), max=m[-1],
                hist_0p1_bins={"%.1f-%.1f" % (b / 10, (b + 1) / 10): bins.get(b, 0) for b in range(10)})
R["margin_distribution"] = {f: dist(m) for f, m in margins.items()}
R["merge_pairs_top"] = {"%s %s" % k: n for k, n in pairs.most_common(14)}
# 2.182a tiles: fate of the 9 cases + 3 controls
key = json.load(open(K182)); ans = json.load(open(K182.replace("2.182a-key.json", "2.182a-answers.json")))
sa = {t["tile"]: t["answer"] for t in ans["tiles"]}
tl = []
for t in key:
    if t["doc"] != DOC: continue
    row = dict(tile=t["tile"], kind=t["kind"], sean=sa.get(t["tile"]), detector=[(d["cls"], d["conf"]) for d in t["detector"]])
    for g in t["glyphs"]:
        row[g] = dict(off=vo["rest_is_not_a_rest"].get(g, [None, None, None])[:3], on=vn["rest_is_not_a_rest"].get(g, [None, None, None])[:3])
    tl.append(row)
R["tiles_2_182a_fate"] = tl
json.dump(R, open(OUT, "w"), indent=1, default=str)
print(json.dumps({k: R[k] for k in R if k not in ("tiles_2_182a_fate", "merge_pairs_top")}, indent=1, default=str)[:6000])
