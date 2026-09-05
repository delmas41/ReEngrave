#!/usr/bin/env python3
"""At what P(name) does an OVERRIDE beat leaving the read clef alone — and how
many staves are above that bar?

MEASUREMENT ONLY. Consumes the held-out-label corpus built by
`build_calibration_corpus.py`.

WHY THIS QUESTION AND NOT A GENERAL ONE. FILL is dead (`probe_fill_reach.py`:
it can only touch the 8.6% of staves whose clef went unread, and the documented
clef ceiling is about clefs read WRONG). So OVERRIDE is the only path from
identity to that ceiling, and a calibrated probability is no longer general
infrastructure looking for a consumer — it exists to argue for or against
widening the gate at `clef_correction.py:599`.

⚠️ BOTH HALVES ARE REQUIRED. A well-calibrated 0.99 bar that admits four
staves is the FILL result again in a different costume. This probe reports the
ADMISSIBLE POPULATION beside every threshold, and prints the population first.

THE SAFETY CRITERION IS AGREEMENT WITH THE MARGIN LABEL, which is precisely
the standard the shipped gate already accepts: it admits identity whose source
is a read label. So the question "is a derived identity safe enough to
override" becomes the measurable "how often does the derived identity agree
with what the label would have said, ON THE STAVES AN OVERRIDE WOULD ACT ON".
Restricting to that population matters — `TREBLE_OVERRIDE_INSTRUMENTS` is
("Viola", "Bassoon", "Contrabassoon", "Timpani"), and a rate computed over all
staves is not a rate about these.

⚠️ THE EXPECTED ANSWER IS A HIGH BAR WITH A THIN POPULATION, and the held-out
arm already says why: Viola->Violin was its largest error family (x3), the same
failure `clef_correction.py:477` names. Those are exactly the staves an
override acts on. Effort already spent is not an argument for a lower bar.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_override_threshold.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST                    # noqa: E402
from tools.omr.score_layouts import LAYOUTS, align_to_layout, fit_layouts  # noqa: E402
from tools.omr.clef_correction import TREBLE_OVERRIDE_INSTRUMENTS  # noqa: E402

CACHE = HERE / "corpus-cache"
RAW_CLEF_SOURCES = {"detector", "detector_header", "specialist", "cv_locator"}
THRESHOLDS = (0.80, 0.90, 0.95, 0.99)
PRIOR_STRENGTH = 2.0


def canonical(name):
    m = INST.lookup(str(name)) if name else None
    return m.instrument.name if m else None


def acceptable(name):
    m = INST.lookup(str(name)) if name else None
    if not m:
        return frozenset()
    c = INST.candidates_for_alias(m.alias)
    return frozenset(x.name for x in c) if c else frozenset({m.instrument.name})


def staves_of(result):
    for page in result.get("pages", []):
        for sysd in page.get("systems", []):
            yield sysd.get("system_index"), sorted(
                sysd.get("staves", []),
                key=lambda s: (s.get("staff_geometry") or {})
                .get("line_ys_page", [0])[0])


def build():
    """One record per staff: derived identity (labels hidden) vs label truth."""
    blobs = sorted(CACHE.glob("*.json"))
    if not blobs:
        raise SystemExit(f"no corpus; run build_calibration_corpus.py ({CACHE})")
    recs = []
    pages = 0
    join = Counter()
    for p in blobs:
        b = json.loads(p.read_text())
        pages += 1
        # Label truth, keyed by the staff_index the reader used.
        truth = {l["staff_index"]: l for l in b["labels"] if l.get("instrument")}
        # ⚠️ JOIN INTEGRITY. The labels come from a SECOND `detect_staves` call
        # (build_calibration_corpus.read_labels) and are keyed on ITS
        # staff_index. If the two calls disagree about the staff set, every
        # record joins to the wrong label or to none -- and a total failure to
        # join looks exactly like "this page had no labels", i.e. a clean
        # negative. Counted per page and asserted below, never assumed.
        idx_in_result = {s.get("staff_index")
                         for _, staves in staves_of(b["result"]) for s in staves}
        join["label_staves"] += len(truth)
        join["result_staves"] += len(idx_in_result)
        join["joined"] += len(set(truth) & idx_in_result)
        join["label_only"] += len(set(truth) - idx_in_result)
        if not (set(truth) & idx_in_result) and truth:
            join["pages_with_zero_join"] += 1
        for sys_idx, staves in staves_of(b["result"]):
            n = len(staves)
            clefs = {i: s["clef"] for i, s in enumerate(staves)
                     if s.get("clef_source") in RAW_CLEF_SOURCES and s.get("clef")}
            fit = fit_layouts(n, labels=None, clefs=clefs or None)
            union = [set() for _ in range(n)]
            for layout in LAYOUTS:
                _, a = align_to_layout(layout, n, None, clefs or None)
                for i, nm in enumerate(a):
                    if nm:
                        union[i].add(nm)
            for i, st in enumerate(staves):
                t = truth.get(st.get("staff_index"))
                if not t:
                    continue          # no printed label -> no truth, excluded
                derived = fit.assignment[i] if fit else None
                recs.append({
                    "house": b["house"], "plate": b["plate"], "work": b["work"],
                    "page_index": b["page_index"], "system_index": sys_idx,
                    "ordinal": i, "n_staves": n,
                    "truth_coverage": b["truth_coverage"],
                    "TRUTH": canonical(t["instrument"]),
                    "TRUTH_acceptable": sorted(acceptable(t["instrument"])),
                    "TRUTH_text": t["text"],
                    "derived": derived,
                    "clef_read": clefs.get(i),
                    "set_size": len(union[i]),
                    "truth_in_set": bool(acceptable(t["instrument"]) & union[i]),
                })
    return recs, pages, join


def override_eligible(r):
    """Would an override even ACT here? Mirrors clef_correction.py:599.

    read clef is treble, the identity names an instrument in the override
    table, and that instrument's default clef is not treble.
    """
    if r["clef_read"] != "treble" or not r["derived"]:
        return False
    if r["derived"] not in TREBLE_OVERRIDE_INSTRUMENTS:
        return False
    m = INST.lookup(r["derived"])
    return bool(m and m.instrument.default_clef
                and m.instrument.default_clef != "treble")


def estimate(train, feats):
    glob = [0, 0]; tier = defaultdict(lambda: [0, 0])
    for r in train:
        k = tuple(r[f] for f in feats)
        for acc in (glob, tier[k]):
            acc[0] += bool(r["ok"]); acc[1] += 1
    g = (glob[0] + 1) / (glob[1] + 2) if glob[1] else 0.5

    def p(r):
        h, n = tier[tuple(r[f] for f in feats)]
        return (h + PRIOR_STRENGTH * g) / (n + PRIOR_STRENGTH) if n else g
    return p


def main():
    recs, pages, join = build()
    for r in recs:
        r["ok"] = bool(r["derived"]) and r["derived"] in r["TRUTH_acceptable"]
    print(f"corpus pages {pages}   staff records with label truth {len(recs)}")
    print(f"JOIN INTEGRITY  label staves {join['label_staves']}  "
          f"result staves {join['result_staves']}  joined {join['joined']}  "
          f"label-only {join['label_only']}  "
          f"pages joining nothing {join['pages_with_zero_join']}")
    if join["label_staves"] and join["joined"] / join["label_staves"] < 0.5:
        raise SystemExit(
            "REFUSING to report: fewer than half the read labels join to a "
            "staff in the transcription. The two detect_staves calls disagree, "
            "and every figure below would be a measurement of that.")
    print(f"  by house: "
          f"{ {h: sum(1 for r in recs if r['house'] == h) for h in sorted({r['house'] for r in recs})} }")
    print(f"  by plate: {len({(r['house'], r['plate']) for r in recs})} plates")
    if not recs:
        raise SystemExit("REFUSING to report: no records.")

    named = [r for r in recs if r["derived"]]
    right = [r for r in named if r["ok"]]
    print(f"\nDERIVED TIER, held-out labels, whole corpus")
    print(f"  coverage  {len(named)}/{len(recs)} = {len(named)/len(recs):.3f}")
    print(f"  precision {len(right)}/{len(named)} = "
          f"{len(right)/len(named):.3f}" if named else "  no named records")
    for h in sorted({r["house"] for r in recs}):
        g = [r for r in recs if r["house"] == h]
        gn = [r for r in g if r["derived"]]
        cov = r"n/a" if not g else f"{len(gn)/len(g):.3f}"
        pr = "n/a" if not gn else f"{sum(1 for r in gn if r['ok'])/len(gn):.3f}"
        note = ("  ⚠️ truth coverage 0.64 — WINDS AND BRASS ONLY, strings "
                "unscoreable" if h == "Litolff" else "")
        print(f"    {h:11s} n={len(g):4d}  coverage {cov}  precision {pr}{note}")

    # ── THE POPULATION FIRST ────────────────────────────────────────────────
    elig = [r for r in recs if override_eligible(r)]
    print(f"\n{'='*68}\nOVERRIDE-ELIGIBLE POPULATION  (the half that decides)\n{'='*68}")
    print(f"  staves an override would ACT on: {len(elig)} of {len(recs)}"
          f"  = {len(elig)/len(recs):.4f}")
    print(f"  by named instrument: "
          f"{dict(Counter(r['derived'] for r in elig))}")
    if elig:
        ok = sum(1 for r in elig if r["ok"])
        print(f"  of those, derived identity AGREES with the label: "
              f"{ok}/{len(elig)} = {ok/len(elig):.3f}")
        print(f"  disagreements: "
              f"{dict(Counter((r['TRUTH'], r['derived']) for r in elig if not r['ok']))}")
    if not elig:
        print("\n  ⚠️ THE POPULATION IS EMPTY. No threshold can be argued for,"
              "\n     because there is nothing above any of them. That is the"
              "\n     FILL result again: a consumer whose reach is zero.")
        return 0

    # ── then the threshold, calibrated HOUSE-HELD-OUT ───────────────────────
    print(f"\n{'='*68}\nTHRESHOLD  (P(name) estimated with the HOUSE held out)\n{'='*68}")
    pairs = []
    for held in sorted({r["house"] for r in recs}):
        train = [r for r in recs if r["house"] != held]
        f = estimate(train, ("clef_read", "set_size"))
        pairs += [(f(r), r) for r in recs if r["house"] == held]
    el_pairs = [(p, r) for p, r in pairs if override_eligible(r)]
    print(f"  {'threshold':>9s} {'admitted':>9s} {'right':>6s} {'precision':>10s}"
          f" {'share of all staves':>20s}")
    for t in THRESHOLDS:
        adm = [(p, r) for p, r in el_pairs if p >= t]
        ok = sum(1 for _, r in adm if r["ok"])
        pr = f"{ok/len(adm):.3f}" if adm else "n/a"
        print(f"  {t:9.2f} {len(adm):9d} {ok:6d} {pr:>10s} "
              f"{len(adm)/len(recs):20.4f}")
    print("\n  ⚠️ Read the ADMITTED column before the precision column. A high"
          "\n     bar with a thin population is not a licence to override; it"
          "\n     is the FILL result wearing a different hat.")
    (HERE / "override-threshold.json").write_text(json.dumps({
        "pages": pages, "n_records": len(recs), "n_eligible": len(elig),
        "records": recs}, indent=1))


if __name__ == "__main__":
    main()
