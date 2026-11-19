"""ROADMAP 2.326 small test (read-only, scratch): ranges / gaps per plate and measure, the wrong / refused fill cases, and a
histogram image per plate. Reads work/heads-<doc>.json.  python3 benchmarks/notehead-fill-by-page-2026-11/report.py litolff
"""
import json
import pathlib
import sys

import numpy as np

W = pathlib.Path(__file__).parent / "work"
#: measure -> (cut(s) today, which side is hollow)
MEASURES = {
    "slit": ("2.148 slit rows_share on the detector box: hollow >= 0.18, black <= 0.06", "hi"),
    "hi_slit": ("2.220 Q.HEAD_INK slit on the trimmed head (same 0.18 / 0.06)", "hi"),
    "raw_c": ("2.23 centre window, raw raster: hollow <= 0.75 (+ ring gap), filled >= 0.85 / 0.9", "lo"),
    "off_c": ("2.23 centre window, line rows left out", "lo"),
    "hole_share": ("2.148 enclosed hole share of the detector box (filed, decides nothing)", "hi"),
    "in_dark": ("candidate: ink inside the inner ellipse of the trimmed head (= share of page solid median, which is 1.0)", "lo"),
    "hull_paper": ("candidate: paper inside the hull of the head's own ink", "hi"),
    "hole_paper": ("candidate: paper ENCLOSED by the head's ink / its filled outline", "hi"),
    "hull_paper_minus_ref": ("candidate, page-relative: hull paper minus the page's solid-head median", "hi"),
}


def rng(v):
    v = [x for x in v if x is not None]
    if not v:
        return "n=0"
    a = np.array(v, float)
    return "n=%d min %.3f p5 %.3f med %.3f p95 %.3f max %.3f" % (len(a), a.min(), np.percentile(a, 5), np.median(a),
                                                                  np.percentile(a, 95), a.max())


def gap(hol, sol, side):
    hol = [x for x in hol if x is not None]
    sol = [x for x in sol if x is not None]
    if not hol or not sol:
        return None
    if side == "hi":
        return round(min(hol) - max(sol), 4), sum(x <= max(sol) for x in hol), sum(x >= min(hol) for x in sol)
    return round(min(sol) - max(hol), 4), sum(x >= min(sol) for x in hol), sum(x <= max(hol) for x in sol)


def main(doc, src_filter=None):
    H = json.load(open(W / ("heads-%s.json" % doc)))["heads"]
    if src_filter:
        H = [h for h in H if h["src"].startswith(src_filter)]
    # a tile's old key that lands on a non-head in this record is not that mark (dropped, counted); one head asked twice counts once
    dropped = [h for h in H if not str(h.get("cls")).startswith("notehead")]
    seen, conflicts, keep = {}, [], []
    for h in H:
        if h in dropped:
            continue
        if h["subject"] in seen:
            if seen[h["subject"]] != h["truth"]:
                conflicts.append(h["subject"])
            continue
        seen[h["subject"]] = h["truth"]
        keep.append(h)
    H = [h for h in keep if h["subject"] not in conflicts]
    print("dropped (key lands on a non-head): %d; asked twice: %d; answers disagree: %d" % (
        len(dropped), sum(1 for _ in seen) and len([1 for h in keep]) and 0, len(conflicts)))
    hol = [h for h in H if h["truth"] == "hollow"]
    sol = [h for h in H if h["truth"] == "solid"]
    print("== %s%s: hollow %d (of which whole-valued answers %d), solid %d" % (
        doc, " [" + src_filter + "]" if src_filter else "", len(hol),
        sum(1 for h in hol if "Whole" in str(h.get("answer")) or str(h.get("answer")).strip() in ("1", "whole")), len(sol)))
    for k, (what, side) in MEASURES.items():
        g = gap([h.get(k) for h in hol], [h.get(k) for h in sol], side)
        print("  %-22s %s" % (k, what))
        print("      hollow %s" % rng([h.get(k) for h in hol]))
        print("      solid  %s" % rng([h.get(k) for h in sol]))
        print("      gap (hollow side minus solid side; <0 = overlap), hollow heads inside solid range, solid inside hollow range: %s" % (g,))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ks = ["slit", "hi_slit", "raw_c", "off_c", "in_dark", "hull_paper", "hole_paper"]
        fig, axs = plt.subplots(len(ks), 1, figsize=(7, 1.7 * len(ks)))
        cuts = {"slit": (0.06, 0.18), "hi_slit": (0.06, 0.18), "raw_c": (0.75, 0.85, 0.9), "off_c": (0.75, 0.85, 0.9)}
        for ax, k in zip(axs, ks):
            bins = np.linspace(0, 1, 51)
            ax.hist([h[k] for h in sol if h[k] is not None], bins=bins, color="#555555", alpha=0.8, label="solid (Sean)")
            ax.hist([h[k] for h in hol if h[k] is not None], bins=bins, color="#1F6FEB", alpha=0.7, label="hollow (Sean)")
            for c in cuts.get(k, ()):
                ax.axvline(c, color="#C62828", lw=1)
            ax.set_yscale("symlog")
            ax.set_title(k, fontsize=8, loc="left")
            ax.tick_params(labelsize=7)
        axs[0].legend(fontsize=7)
        fig.suptitle("%s: fill measures on Sean's judged/labelled heads (red = today's cuts)" % doc, fontsize=9)
        fig.tight_layout()
        fig.savefig(W.parent / ("hist-%s%s.png" % (doc, "-" + src_filter.strip(":") if src_filter else "")), dpi=110)
    except Exception as e:      # noqa
        print("no histogram:", e)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
