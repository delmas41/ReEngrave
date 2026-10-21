"""2.185: cut named groups of clusters out of rows.json (tables.py --rows) for targeted crops. usage: groups.py ROWS.json FATES.json|none OUTPREFIX
Writes OUTPREFIX.<group>.json in census format (crops.py input); member 'why' carries the EXPORT fate when FATES is given (Litolff)."""
import json, sys
rows = json.load(open(sys.argv[1])); fates = json.load(open(sys.argv[2])) if sys.argv[2] != "none" else {}
W = ("written", "written_relocated")
def efate(m): return fates.get(m["subject"], "n/a") if fates else "n/a"
def mk(x):
    ms = []
    for m in x["members"]:
        m = dict(m); m["why"] = (m["fate"] + ":" + m["why"] + " | export=" + efate(m))[:150]; ms.append(m)
    return dict(members=ms, cells=1, staffs=1)
G = {}
def add(g, x): G.setdefault(g, []).append(mk(x))
for x in rows:
    ms = x["members"]; fam = x["fam"]
    ex = [efate(m) for m in ms if efate(m) != "n/a"]
    nw = sum(e in W for e in ex)
    if fam == "head" and fates and ex and nw == 0: add("head_lost_in_file", x)
    if fam == "head" and x["ct"] == "diff_class" and x["out"] in ("multi_kept", "one_alive"): add("head_diff_class", x)
    if fam == "X:arc+beam" and x["out"] == "multi_kept": add("arc_beam_both_kept", x)
    if fam == "X:head+rest" and x["cause"].startswith("same_cell"): add("head_rest_same_cell", x)
    if fam == "X:arpeggiato+rest": add("arpeggiato_rest", x)
    if fam == "accidental" and x["out"] == "multi_kept": add("accidental_both_kept", x)
    if fam == "dynamic" and x["out"] == "multi_kept": add("dynamic_both_kept", x)
    if fam == "dynamic" and x["out"] == "all_dead": add("dynamic_lost", x)
    if fam == "accidental" and x["out"] == "all_dead": add("accidental_lost", x)
    if fam == "rest" and x["out"] == "all_dead": add("rest_lost", x)
    if fam == "arc" and x["out"] == "all_dead": add("arc_lost", x)
    if fam == "head" and x["out"] == "all_dead": add("head_all_refused", x)
    if fam == "head" and x["out"] == "all_dead" and any(("duplicate" in m["why"]) for m in x["members"]): add("head_all_dead_dup", x)
    if fam == "head" and x["out"] == "all_dead" and not any(("duplicate" in m["why"]) for m in x["members"]): add("head_all_dead_nodup", x)
    if x["cause"].startswith("view_small"): add("view_small", x)
    if x["cause"].startswith("stem_end"): add("stem_end_head", x)
    if x["cause"].startswith("same_cell_samec_iou_ge_07"): add("anomaly_samec_ge07", x)
for g, v in G.items():
    json.dump(dict(clusters=v), open("%s.%s.json" % (sys.argv[3], g), "w")); print(g, len(v))
