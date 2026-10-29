"""final.py: auto-class (OUR marks) for every red bar, per-page counts, crop-label cross-tab (MY reading of the print, not Sean's)."""
import json, collections, sys
LAB = {
 "litolff": {
  "6/1/1/13": "CUT_BAR", "6/1/9/13": "CUT_BAR", "6/1/11/11": "UNCLEAR", "16/0/9/4": "REST_MISSING", "2/0/7/5": "HEAD_MISSING",
  "4/0/8/6": "REST_MISSING", "4/1/8/8": "VALUE", "16/0/7/12": "HEAD_MISSING", "11/0/8/14": "REST_MISSING", "16/1/10/2": "UNCLEAR",
  "16/1/4/3": "VOICES", "4/1/2/2": "VOICES",
  "1/0/0/3": "EXTRA", "10/1/4/7": "EXTRA", "9/1/6/11": "VALUE", "10/1/8/12": "EXTRA", "10/0/7/2": "VALUE", "9/1/9/5": "CUT_BAR",
  "6/0/0/10": "VALUE", "8/0/0/15": "EXTRA", "4/0/7/3": "VALUE", "9/1/1/5": "CUT_BAR", "6/1/3/1": "EXTRA"},
 "brahms": {
  "4/0/6/9": "VOICES", "8/0/3/3": "VOICES", "4/1/1/2": "VALUE", "8/1/1/3": "VALUE", "5/1/10/0": "VALUE", "12/0/6/9": "EXTRA",
  "0/0/4/3": "UNCLEAR", "14/1/4/3": "EXTRA", "19/0/0/6": "VALUE", "5/0/4/0": "EXTRA", "12/1/10/5": "EXTRA",
  "14/0/9/7": "HEAD_MISSING", "4/1/11/8": "VOICES", "19/1/8/7": "HEAD_MISSING", "8/0/8/12": "VALUE", "19/0/9/8": "VALUE"}}
PAGES = {"litolff": [1, 2, 4, 6, 8, 9, 10, 11, 16], "brahms": [0, 4, 5, 8, 12, 14, 19, 25]}
allc = {}
for plate in ("litolff", "brahms"):
    C = json.load(open("out/red-bars/work/%s.cls.json" % plate))
    F = {b["key"]: b for b in json.load(open("out/red-bars/work/%s.feat.json" % plate))}
    P = json.load(open("out/red-bars/work/%s.partition.json" % plate))
    cut = set(P["merged"]) | set(P["shifted"])
    for c in C:
        b = F[c["key"]]
        far = [r for r in b["rows"] if r["glyph"] and r["staffpos"] is not None and abs(r["staffpos"]) >= 8.0 and r["kind"] == "note"]
        if c["doubled"]: a = "doubled_copy"
        elif c["whole_rest_in_bar"]: a = "whole_rest_in_bar"
        elif c["key"] in cut: a = "cut_bar_pair"
        elif c["two_voice"]: a = "two_voice_written"
        elif c["over"]:
            rm, vf = bool(c["remove_one_fixes"]), bool(c["one_value_fixes"])
            a = "over_extra_or_value" if rm and vf else "over_one_extra" if rm else "over_one_value" if vf else "over_two_or_more"
        else:
            a = "short_one_event" if c["n_events"] == 1 else "short_std_gap" if c.get("gap_std") else "short_other"
        c["auto"] = a; c["far"] = bool(far); c["plate"] = plate
        allc[plate + ":" + c["key"]] = c
    n = len(PAGES[plate])
    cnt = collections.Counter(c["auto"] for c in C)
    print("== %s: %d red bars, %.1f per page (%d pages); over %d short %d" % (plate, len(C), len(C) / n, n, sum(c["over"] for c in C), sum(not c["over"] for c in C)))
    for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
        print("   %-22s %4d  %5.1f/page" % (k, v, v / n))
    pp = collections.Counter(c["page"] for c in C)
    print("   by page:", dict(sorted(pp.items())))
    lab = LAB[plate]
    print("   crop labels n=%d:" % len(lab), dict(collections.Counter(lab.values())))
    over_l = collections.Counter(v for k, v in lab.items() if allc[plate + ":" + k]["over"])
    short_l = collections.Counter(v for k, v in lab.items() if not allc[plate + ":" + k]["over"])
    print("   over  n=%d" % sum(over_l.values()), dict(over_l))
    print("   short n=%d" % sum(short_l.values()), dict(short_l))
    # cross-tab auto vs label
    xt = collections.Counter((allc[plate + ":" + k]["auto"], v) for k, v in lab.items())
    for (a, v), m in sorted(xt.items()):
        print("      auto %-22s -> print %-13s %d" % (a, v, m))
    # projected counts
    no, ns = sum(over_l.values()), sum(short_l.values())
    to, ts = sum(c["over"] for c in C), sum(not c["over"] for c in C)
    proj = collections.Counter()
    for k, m in over_l.items(): proj[k] += m / no * to
    for k, m in short_l.items(): proj[k] += m / ns * ts
    print("   projected from the crop sample (counts over all red bars; n=%d over, %d short, wide error):" % (no, ns), {k: round(v) for k, v in proj.most_common()})
json.dump(allc, open("out/red-bars/work/all.auto.json", "w"), default=str)
