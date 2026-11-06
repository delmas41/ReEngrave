"""The numbers for the FINDINGS (real arcs only = ledger fate != not_an_arc; Litolff 8 sample pages, Brahms the ledger's p0+p5).

    python3 final.py > results/final.txt
"""
import collections
import json
import re

SLICE = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261104-night/%s/abstentions.jsonl"

for plate in ("litolff", "brahms"):
    led = json.load(open("../deep-dive-2026-11/results/%s.base.ledger.json" % plate))["rows"]
    fate = {p: r["fate"] for r in led for p in r["pieces"]}
    lpages = {r["page"] for r in led}
    d = json.load(open("results/%s.cut.json" % plate))
    eb = json.load(open("results/edge_is_barline.%s.json" % plate))["edges"]
    allrows = d["rows"]
    rows = [r for r in allrows if fate.get(r["key"]) not in (None, "not_an_arc")]
    print("==", plate, "real arc boxes", len(rows), "pages", sorted(lpages))
    # printed barline at the edge
    def is_bar(r, side):
        ck = "cell/" + "/".join(r["key"].split("/")[1:5])
        return eb.get("%s|%s" % (ck, side))
    nb = sum(1 for r in rows if is_bar(r, "l")) + sum(1 for r in rows if is_bar(r, "r"))
    print("  cell edges of these boxes that are a printed barline: %.1f%% of %d" % (100 * nb / (2 * len(rows)), 2 * len(rows)))
    ends = 2 * len(rows)
    at = sum(1 for r in rows if r["l_edge"] <= 1 and is_bar(r, "l")) + sum(1 for r in rows if r["r_edge"] <= 1 and is_bar(r, "r"))
    ch = sum(r["chance_cell"] for r in rows)
    print("  Q2a ends within 1 sp of a PRINTED barline at the cell edge: %d of %d = %.1f%% | chance (box slid in its cell) %.1f%% | ratio x%.2f" % (at, ends, 100 * at / ends, 100 * ch / ends, at / ch))
    for side, f in (("left", "l"), ("right", "r")):
        o = sum(1 for r in rows if r[f + "_edge"] <= 0.25 and is_bar(r, f))
        c = sum(r["chance_%s25" % f] for r in rows)
        print("     %-5s end within 0.25 sp of a printed barline: %.1f%% vs chance %.1f%% (x%.1f)" % (side, 100 * o / len(rows), 100 * c / len(rows), o / c))
    # pairs among real boxes only
    cut_l = {r["key"] for r in rows if r["cut_l"] and is_bar(r, "l")}
    cutr = [r for r in rows if r["cut_r"] and is_bar(r, "r")]
    byst = collections.defaultdict(list)
    for r in rows:
        byst[r["staff"]].append(r)
    pair = 0
    for r in cutr:
        ok = False
        for b in byst[r["staff"]]:
            if b["cell"] == r["cell"] + 1 and b["key"] in cut_l and r["box"][1] - 0.5 * r["sp"] <= b["box"][3] and b["box"][1] - 0.5 * r["sp"] <= r["box"][3]:
                ok = True
        pair += ok
    lone_r = len(cutr) - pair
    lone_l = len(cut_l) - pair
    print("  Q2b barline-cut real boxes: right-cut %d, left-cut %d. Edge PAIRS (a box each side of one barline, y overlapping): %d; right-cut with no box on the far side: %d; left-cut with none on the near side: %d" % (
        len(cutr), len(cut_l), pair, lone_r, lone_l))
    print("      crossing arcs seen as >=2 pieces: %d ; seen as one piece with the other half never boxed: %d (%.0f%%)" % (pair, lone_r + lone_l, 100 * (lone_r + lone_l) / max(pair + lone_r + lone_l, 1)))
    print("      a box wider than its cell: %d (a box cannot cross a cell edge)" % sum(1 for r in allrows if r["w_sp"] > r["cellw_sp"] + 0.01))
    # curves
    ledc = [r for r in led if r["fate"] != "not_an_arc"]
    withc = [r for r in ledc if r["has_curve"]]
    print("  Q2c page curves of real arcs: %d; joined across a cell edge (>1 cell): %d (%.0f%%); curves holding a barline-cut piece: %d, of which joined across it: %d" % (
        len(withc), sum(1 for r in withc if r["cells"] and len(r["cells"]) > 1), 100 * sum(1 for r in withc if r["cells"] and len(r["cells"]) > 1) / len(withc),
        sum(1 for r in withc if any((p in {x["key"] for x in rows if x["cut_l"] or x["cut_r"]}) for p in r["pieces"])),
        sum(1 for r in withc if r["cells"] and len(r["cells"]) > 1 and any((p in {x["key"] for x in rows if x["cut_l"] or x["cut_r"]}) for p in r["pieces"]))))
    # Q4 no curve
    nocurve = [r for r in rows if not r["curve"]]
    nk = {r["key"] for r in nocurve}
    notes = collections.Counter()
    for l in open(SLICE % plate):
        o = json.loads(l)
        if o["quantity"] == "system_arc" and o["subject"] in nk:
            n = (o.get("detail") or {}).get("note", "")
            notes[re.sub(r"[0-9.]+", "#", n)[:70]] += 1
    cutn = sum(1 for r in nocurve if (r["cut_l"] and is_bar(r, "l")) or (r["cut_r"] and is_bar(r, "r")))
    wc = [r for r in rows if r["curve"]]
    cutc = sum(1 for r in wc if (r["cut_l"] and is_bar(r, "l")) or (r["cut_r"] and is_bar(r, "r")))
    print("  Q4 real boxes with NO page curve row: %d; cut at a printed barline: %d (%.0f%%) [boxes WITH a curve: %.0f%%]" % (len(nocurve), cutn, 100 * cutn / len(nocurve), 100 * cutc / len(wc)))
    print("      both ends cut: %d; ends: left-only %d, right-only %d, neither %d" % (
        sum(1 for r in nocurve if r["cut_l"] and r["cut_r"]), sum(1 for r in nocurve if r["cut_l"] and not r["cut_r"]),
        sum(1 for r in nocurve if r["cut_r"] and not r["cut_l"]), sum(1 for r in nocurve if not r["cut_l"] and not r["cut_r"])))
    print("      why no curve (abstention note):", notes.most_common(5))
    print("      width of no-curve boxes: median %.1f sp (with-curve boxes %.1f sp)" % (sorted(r["w_sp"] for r in nocurve)[len(nocurve) // 2], sorted(r["w_sp"] for r in wc)[len(wc) // 2]))
