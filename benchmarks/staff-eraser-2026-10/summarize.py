"""ROADMAP 2.206: per-class table from reach.py outputs. usage: summarize.py reach_litolff.json reach_brahms.json"""
import json, sys
import numpy as np

GROUP = [("beam", ("beam",)), ("head black on line", ("noteheadBlackOnLine",)), ("head black in space", ("noteheadBlackInSpace",)),
         ("head half/whole", ("noteheadHalf", "noteheadWhole", "noteheadDouble")), ("rest whole/half", ("restWhole", "restHalf", "restHBar")),
         ("rest quarter", ("restQuarter",)), ("rest 8th/16th", ("rest8th", "rest16th", "rest32nd")), ("flag", ("flag",)),
         ("tie/slur", ("tie", "slur")), ("accidental/key", ("accidental", "keyFlat", "keySharp", "keyNatural")),
         ("dot/staccato", ("augmentationDot", "articStacc")), ("ledger line", ("ledgerLine",)), ("clef", ("clef",)),
         ("dynamic/text", ("dynamic", "fingering", "tuplet")), ("time sig", ("timeSig",))]
SKIP = ("staff", "brace", "arpeggiato")   # arpeggiato = the detector's name for barline/bracket strokes on these plates (crop look)


def group(cls):
    for g, pre in GROUP:
        if cls.startswith(pre):
            return g
    return None if cls.startswith(SKIP) else "other"


for path in sys.argv[1:]:
    d = json.load(open(path))
    cells = d["cells"]
    t = [l["t_sp"] for c in cells.values() for l in c["lines"]]
    cut = [l["cut_sp"] for c in cells.values() for l in c["lines"]]
    sat = sum(l["n_sat_erased"] for c in cells.values() for l in c["lines"])
    cols = sum(l["n_cols"] for c in cells.values() for l in c["lines"])
    print("\n%s: %d cells; line thickness sp p10/50/90 %s; cut sp p10/50/90 %s; columns erased although the walk was truncated: %d of %d (%.2f%%)"
          % (d["plate"], len(cells), np.round(np.percentile(t, [10, 50, 90]), 3).tolist(), np.round(np.percentile(cut, [10, 50, 90]), 3).tolist(),
             sat, cols, 100.0 * sat / max(cols, 1)))
    rows = {}
    for c in cells.values():
        for i, b in enumerate(c["main"]["boxes"]):
            if not b:
                continue
            g = group(b["cls"])
            if g is None:
                continue
            r = rows.setdefault(g, dict(n=0, sat=0, main=0, reach=0, band=0, h_main=[], h_reach=[], px_main=0, px_reach=0, resid_main=0, resid_reach=0))
            r["n"] += 1
            r["sat"] += b["sat_cols"] > 0
            for v in ("main", "reach", "band"):
                bv = c[v]["boxes"][i]
                if bv["over_px"] > 0:
                    r[v] += 1
                    if v != "band":
                        r["h_" + v].append(bv["over_colmax_sp"])
                if v != "band":
                    r["px_" + v] += bv["over_px"]
                    r["resid_" + v] += bv["resid_px"]
    print("| class | boxes | walk truncated in box | lose ink: main | reach | band* | median max loss sp main / reach | lost px main / reach |")
    print("|---|---|---|---|---|---|---|---|")
    for g, _ in GROUP + [("other", ())]:
        r = rows.get(g)
        if not r:
            continue
        med = lambda a: ("%.2f" % np.median(a)) if a else "-"
        print("| %s | %d | %d | %d | %d | %d | %s / %s | %d / %d |" % (g, r["n"], r["sat"], r["main"], r["reach"], r["band"], med(r["h_main"]), med(r["h_reach"]), r["px_main"], r["px_reach"]))
    for v in ("main", "reach", "band"):
        print("  %s: overcut px %d (unboxed %d); residue px %d; erased px %d" % (v, sum(c[v]["over"] for c in cells.values()), sum(c[v]["unboxed_over"] for c in cells.values()),
              sum(c[v]["resid"] for c in cells.values()), sum(c[v]["erased_px"] for c in cells.values())))
