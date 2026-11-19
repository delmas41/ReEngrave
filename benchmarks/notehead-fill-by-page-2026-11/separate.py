"""ROADMAP 2.326 small test (read-only, scratch): per plate and measure, how many of Sean's heads fall on the wrong side of
today's cut(s), the best single cut on that plate, and whether ONE cut serves both plates; plus today's outcome per head.
    python3 benchmarks/notehead-fill-by-page-2026-11/separate.py
"""
import json
import pathlib
from collections import Counter

import numpy as np

W = pathlib.Path(__file__).parent / "work"
#: measure, hollow side, today's (hollow cut, solid cut) -- between them is "not decided"
M = {"slit": ("hi", 0.18, 0.06), "hi_slit": ("hi", 0.18, 0.06), "raw_c": ("lo", 0.75, 0.85), "off_c": ("lo", 0.75, 0.85),
     "hole_share": ("hi", None, None), "in_dark": ("lo", None, None), "hull_paper": ("hi", None, None),
     "hole_paper": ("hi", None, None), "hull_paper_minus_ref": ("hi", None, None)}


def load(doc):
    H = json.load(open(W / ("heads-%s.json" % doc)))["heads"]
    seen, out = set(), []
    for h in H:
        if not str(h.get("cls")).startswith("notehead") or h["subject"] in seen:
            continue
        seen.add(h["subject"])
        out.append(h)
    return out


def errs(H, k, side, cut):
    """(hollow called solid, solid called hollow) at one cut; hollow side is >= cut ('hi') or <= cut ('lo')."""
    hv = [h[k] for h in H if h["truth"] == "hollow" and h.get(k) is not None]
    sv = [h[k] for h in H if h["truth"] == "solid" and h.get(k) is not None]
    if side == "hi":
        return sum(x < cut for x in hv), sum(x >= cut for x in sv), len(hv), len(sv)
    return sum(x > cut for x in hv), sum(x <= cut for x in sv), len(hv), len(sv)


def best(Hs, k, side):
    vals = sorted({round(h[k], 4) for H in Hs for h in H if h.get(k) is not None})
    cands = [(a + b) / 2 for a, b in zip(vals, vals[1:])] or vals
    res = []
    for c in cands:
        e = [errs(H, k, side, c) for H in Hs]
        res.append((sum(a + b for a, b, _, _ in e), c, e))
    return min(res) if res else None


def main():
    P = {d: load(d) for d in ("litolff", "brahms")}
    for d, H in P.items():
        print("\n=== %s: %d hollow, %d solid (Sean)" % (d, sum(h["truth"] == "hollow" for h in H), sum(h["truth"] == "solid" for h in H)))
        for k, (side, hc, sc) in M.items():
            line = "  %-22s" % k
            if hc is not None:
                hv = [h[k] for h in H if h["truth"] == "hollow" and h.get(k) is not None]
                sv = [h[k] for h in H if h["truth"] == "solid" and h.get(k) is not None]
                if side == "hi":
                    hh, hb, hs = sum(x >= hc for x in hv), sum(sc < x < hc for x in hv), sum(x <= sc for x in hv)
                    sh, sb, ss = sum(x >= hc for x in sv), sum(sc < x < hc for x in sv), sum(x <= sc for x in sv)
                else:
                    hh, hb, hs = sum(x <= hc for x in hv), sum(hc < x < sc for x in hv), sum(x >= sc for x in hv)
                    sh, sb, ss = sum(x <= hc for x in sv), sum(hc < x < sc for x in sv), sum(x >= sc for x in sv)
                line += " today's cuts: hollow heads -> hollow %d / between %d / solid %d;  solid heads -> hollow %d / between %d / solid %d" % (
                    hh, hb, hs, sh, sb, ss)
            b = best([H], k, side)
            if b:
                line += "\n      best cut on this plate %.3f: errors %d (hollow->solid %d, solid->hollow %d)" % (
                    b[1], b[0], b[2][0][0], b[2][0][1])
            print(line)
    print("\n=== ONE cut for both plates")
    for k, (side, hc, sc) in M.items():
        b = best(list(P.values()), k, side)
        if b:
            print("  %-22s cut %.3f: litolff hollow->solid %d solid->hollow %d | brahms hollow->solid %d solid->hollow %d" % (
                k, b[1], b[2][0][0], b[2][0][1], b[2][1][0], b[2][1][1]))
    print("\n=== today's outcome per plate (truth, fill written, how)")
    for d, H in P.items():
        c = Counter()
        for h in H:
            how = h["how_today"].split(":")[0]
            ft = h["fill_today"]
            if ft in ("hollow", "solid"):
                ok = "right" if ft == h["truth"] else "WRONG"
            elif ft and "/" in ft:
                ok = "both_in_set"
            else:
                ok = "no_fill"
            c[(h["truth"], ok, how)] += 1
        print(" ", d)
        for k, v in sorted(c.items()):
            print("     %-8s %-12s %-30s %d" % (k[0], k[1], k[2], v))


if __name__ == "__main__":
    main()
