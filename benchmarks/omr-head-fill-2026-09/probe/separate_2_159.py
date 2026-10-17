"""ROADMAP 2.159 -- Sean's question (2026-10-17): "Are we still using the split rule for hollow heads? I thought we found
that the ink percentage was a better rule?"  On Sean's judged heads (both plates), how well does EACH stored head
measure alone separate hollow (he said half/whole, value >= 2) from black (value <= 1.5)?  Best single cut, errors at it.
usage: separate_2_159.py OUTDIR"""
import json
import os
import sys

CENTER_SHRINK = 0.30
CORE = (1 - 2 * CENTER_SHRINK) ** 2      # the 2.23 centre window's share of the box


def measures(h):
    ni = (h.get("notehead_ink") or {}).get("detail") or {}
    iw = ni.get("interior_white") or {}
    out = {}
    if iw.get("rows_read"):
        out["rows_share (2.148 slit)"] = iw["rows_share"]
        out["hole_share (2.148 hole)"] = iw["hole_share"]
    for k, name in (("ink_raw", "2.23 centre ink, raw"), ("ink_off_line", "2.23 centre ink, line rows out")):
        w = (ni.get(k) or {}).get("windows") or {}
        if w.get("center") is not None:
            out[name] = w["center"]
    w = (ni.get("ink_net") or {}).get("windows") or {}
    if w.get("center") is not None and w.get("ring") is not None:
        out["whole-head ink, lines erased"] = round(CORE * w["center"] + (1 - CORE) * w["ring"], 4)
    w = (ni.get("ink_raw") or {}).get("windows") or {}
    if w.get("center") is not None and w.get("ring") is not None:
        out["whole-head ink, raw"] = round(CORE * w["center"] + (1 - CORE) * w["ring"], 4)
    return out


HIGHER_IS_HOLLOW = {"rows_share (2.148 slit)", "hole_share (2.148 hole)"}


def gate(h):
    b = (h.get("glyph_box") or {}).get("value")
    sp = h.get("space")
    if not b or not sp:
        return None
    w, hh = b[3] / sp, b[4] / sp
    return (0.9 <= hh <= 1.8 and 1.1 <= w <= 1.9), round(w, 2), round(hh, 2)


def in_box(h, j):
    pb = ((h.get("glyph_box") or {}).get("detail") or {}).get("bbox_page_px")
    tb = j.get("page_box")
    if not pb or not tb:
        return True     # no box to check against: kept, counted below
    cx, cy = (pb[0] + pb[2]) / 2, (pb[1] + pb[3]) / 2
    return tb[0] - 40 <= cx <= tb[2] + 40 and tb[1] - 40 <= cy <= tb[3] + 40


def best_cut(pairs, higher):
    """pairs: [(x, is_hollow)] -> (cut, errors, hollow_missed, black_called_hollow)"""
    xs = sorted({x for x, _ in pairs})
    cands = [xs[0] - 1e-6] + [(a + b) / 2 for a, b in zip(xs, xs[1:])] + [xs[-1] + 1e-6]
    best = None
    for c in cands:
        hm = sum(1 for x, y in pairs if y and not (x >= c if higher else x <= c))
        bh = sum(1 for x, y in pairs if not y and (x >= c if higher else x <= c))
        if best is None or hm + bh < best[1]:
            best = (round(c, 4), hm + bh, hm, bh)
    return best


def main():
    OUT = sys.argv[1]
    report = {}
    for doc in ("litolff", "brahms"):
        H = json.load(open(os.path.join(OUT, "heads_%s.json" % doc)))
        rows, skipped = [], 0
        for s, h in H.items():
            for j in h.get("judged", []):
                if not in_box(h, j):
                    skipped += 1
                    continue
                cls = ((h.get("notehead_class") or {}).get("value")) or ""
                if not cls.startswith("noteheadBlack"):
                    continue        # the fill question only arises on a BLACK-classed box
                rows.append(dict(subject=s, value=j["value"], hollow=j["value"] >= 2.0, m=measures(h), gate=gate(h),
                                 item=j["item"], tile=j["tile"]))
        seen, uniq = set(), []
        for r in rows:
            if r["subject"] not in seen:
                seen.add(r["subject"])
                uniq.append(r)
        report[doc] = {"heads": len(uniq), "hollow": sum(r["hollow"] for r in uniq), "skipped_box_mismatch": skipped,
                       "rows": uniq}
    allrows = report["litolff"]["rows"] + report["brahms"]["rows"]
    names = sorted({k for r in allrows for k in r["m"]})
    print("judged BLACK-classed heads: litolff %d (%d hollow), brahms %d (%d hollow); box mismatches skipped %d/%d" % (
        report["litolff"]["heads"], report["litolff"]["hollow"], report["brahms"]["heads"], report["brahms"]["hollow"],
        report["litolff"]["skipped_box_mismatch"], report["brahms"]["skipped_box_mismatch"]))
    res = {}
    for scope, rr in (("litolff", report["litolff"]["rows"]), ("brahms", report["brahms"]["rows"]), ("both", allrows)):
        for n in names:
            for gated in (False, True):
                pairs = [(r["m"][n], r["hollow"]) for r in rr if n in r["m"] and (not gated or (r["gate"] or (0,))[0])]
                if not pairs or not any(y for _, y in pairs) or all(y for _, y in pairs):
                    continue
                c = best_cut(pairs, n in HIGHER_IS_HOLLOW)
                res[(scope, n, gated)] = c
                print("%-8s %-34s %-10s n=%3d (hollow %2d)  best cut %s  errors %d  (hollow missed %d, black called hollow %d)"
                      % (scope, n, "head-sized" if gated else "all boxes", len(pairs), sum(y for _, y in pairs), c[0], c[1],
                         c[2], c[3]))
    json.dump({"report": report, "cuts": {"|".join(map(str, k)): v for k, v in res.items()}},
              open(os.path.join(OUT, "separation.json"), "w"), indent=0)


if __name__ == "__main__":
    main()
