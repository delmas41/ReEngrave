import collections
import json
import sys

TOL = 1.0


def rate(rows, f):
    return sum(f(r) for r in rows)


def main():
    for plate in ("litolff", "brahms"):
        d = json.load(open("results/%s.cut.json" % plate))
        rows = d["rows"]
        led = json.load(open("../deep-dive-2026-11/results/%s.base.ledger.json" % plate))["rows"]
        lp = {}
        for lr in led:
            for p in lr["pieces"]:
                lp[p] = lr["fate"]
        lpages = {r["page"] for r in led}
        if len(sys.argv) > 1 and sys.argv[1] == "real":
            rows = [r for r in rows if r["key"] in lp and lp[r["key"]] != "not_an_arc"]
            print("   [real arcs only: ledger fate != not_an_arc; pages", sorted(lpages), "]")
        print("==", plate, "boxes", len(rows))
        for name, sub in (("all boxes", rows), ("boxes WITH a page curve", [r for r in rows if r["curve"]]),
                          ("boxes with NO page curve", [r for r in rows if not r["curve"]]),
                          ("slur/tie boxes, curve, width >= 1.5 sp", [r for r in rows if r["curve"] and r["w_sp"] >= 1.5])):
            if not sub:
                continue
            n = 2 * len(sub)
            # ends at a cell edge: any cell edge incl. system start/end (a barline too)
            ce = rate(sub, lambda r: r["l_edge"] <= TOL) + rate(sub, lambda r: r["r_edge"] <= TOL)
            cei = rate(sub, lambda r: r["l_edge"] <= TOL and r["l_interior"]) + rate(sub, lambda r: r["r_edge"] <= TOL and r["r_interior"])
            bl = rate(sub, lambda r: r["l_bar"] <= TOL) + rate(sub, lambda r: r["r_bar"] <= TOL)
            hd = rate(sub, lambda r: r["l_head"] <= TOL) + rate(sub, lambda r: r["r_head"] <= TOL)
            cc = sum(r["chance_cell"] for r in sub)
            cb = sum(r["chance_bar"] for r in sub)
            ch = sum(r["chance_head"] for r in sub)
            print("  %-40s ends %5d | at cell edge %5.1f%% (chance %4.1f%%, x%.1f) | at any barline of system %5.1f%% (chance %4.1f%%, x%.1f) | interior-edge only %5.1f%% | at a head %5.1f%% (chance %4.1f%%, x%.1f)" % (
                name, n, 100 * ce / n, 100 * cc / n, ce / max(cc, 1e-9), 100 * bl / n, 100 * cb / n, bl / max(cb, 1e-9), 100 * cei / n,
                100 * hd / n, 100 * ch / n, hd / max(ch, 1e-9)))
        # box ends that are interior-cut: pairs vs lone
        cutl = [r for r in rows if r["cut_l"]]
        cutr = [r for r in rows if r["cut_r"]]
        print("  cut ends (interior edges): left %d, right %d" % (len(cutl), len(cutr)))
        pairs = [r for r in rows if r["partner_r"]]
        lone_r = [r for r in rows if r["cut_r"] and not r["partner_r"]]
        lone_l = [r for r in rows if r["cut_l"] and not r["partner_l"]]
        print("  barline-crossing edge PAIRS (two boxes, one per side): %d | lone right-cut %d | lone left-cut %d" % (len(pairs), len(lone_r), len(lone_l)))
        # structural check: any box spanning an interior cell edge?
        print("  boxes wider than their cell: %d" % sum(1 for r in rows if r["w_sp"] > r["cellw_sp"] + 0.01))
        # with curves
        cur = d["curves"]
        multi = [k for k, v in cur.items() if v["cells"] and len(v["cells"]) > 1]
        npieces = collections.Counter(len(v["pieces"]) for v in cur.values())
        print("  page curves %d | spanning >1 cell %d (%.0f%%) | pieces per curve %s" % (len(cur), len(multi), 100 * len(multi) / max(len(cur), 1), dict(sorted(npieces.items()))))
        # of curves, how many contain a cut end
        pc = {r["key"]: r for r in rows}
        crossing_curves = [k for k, v in cur.items() if any((pc.get(p) or {}).get("cut_l") or (pc.get(p) or {}).get("cut_r") for p in v["pieces"])]
        print("  curves with a piece cut at an interior edge: %d ; of those joined across it (>1 cell): %d" % (len(crossing_curves), len([k for k in crossing_curves if len(cur[k]["cells"] or []) > 1])))
        # no-curve boxes
        nc = [r for r in rows if not r["curve"]]
        c = collections.Counter()
        for r in nc:
            at = ("cut_l" if r["cut_l"] else "") + ("+" if r["cut_l"] and r["cut_r"] else "") + ("cut_r" if r["cut_r"] else "")
            c[(r["absn"] or "no_row", at or "free")] += 1
        print("  boxes with no page curve row:", len(nc))
        for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:14]:
            print("     ", k, v)
        print("   share of no-curve boxes cut at an interior edge: %.1f%% ; of boxes WITH a curve: %.1f%%" % (
            100 * sum(1 for r in nc if r["cut_l"] or r["cut_r"]) / max(len(nc), 1),
            100 * sum(1 for r in rows if r["curve"] and (r["cut_l"] or r["cut_r"])) / max(sum(1 for r in rows if r["curve"]), 1)))


main()
