"""Build `metric-registry.json` — every measurement this project makes today,
converted to ONE unit, with its ceiling, its trustworthiness and its era.

Every value is READ from a committed artefact. Nothing here is typed by hand
except the prose fields (`why_not`, ceiling notes), and every one of those names
the artefact its claim rests on.

    python3 benchmarks/omr-pipeline-audit-2026-09/probe/build_metric_registry.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "metric-registry.json"

A = {
    "record": ROOT / "benchmarks/omr-ned-2026-08/current-accuracy.json",
    "reading": ROOT / "benchmarks/omr-reading-vs-reproduction-2026-09/results.json",
    "gate20": ROOT / "benchmarks/omr-scan-e2e-2026-09/results-reconciliation.json",
    "norm": ROOT / "benchmarks/omr-page-normalise-fixes-2026-09/results-normalised-arm-20row.json",
    "noop": ROOT / "benchmarks/omr-headline-validity-2026-09/engraved-normalise-noop.json",
    "one2one": ROOT / "benchmarks/omr-headline-validity-2026-09/engraved-1to1.json",
    "indep": HERE / "ceiling-engine-independence.json",
    "aud_eng": ROOT / "benchmarks/omr-vs-industry-2026-09/results.json",
    "aud_scan": ROOT / "benchmarks/omr-vs-industry-2026-09/results-audiveris-scan.json",
    "hairpin": ROOT / "benchmarks/omr-hairpin-cv-2026-09/results-scored-pages.json",
    "floor": HERE / "structural-floor-measured.json",
    "inputceil": HERE / "input-ceiling-from-labels.json",
    "retro": HERE / "retro-stamp.json",
    "scancmp": ROOT / "benchmarks/omr-vs-industry-2026-09/scan-comparison.json",
    "hairpinceil": HERE / "hairpin-ceiling-value.json",
    "humancost": HERE / "human-cost-identity.json",
    "noisefloor": HERE / "engraved-noise-floor.json",
    "content": ROOT / "docs/progress-dashboard.content.json",
    "pct": HERE / "pct-of-achievable-prototype.json",
}
L = {k: json.loads(v.read_text()) for k, v in A.items()}
REL = {k: str(v.relative_to(ROOT)) for k, v in A.items()}


#: A head-to-head key names (fixtures, row set, scorer) — never a system. Both
#: sides of a comparison must carry the SAME string, so each is declared ONCE
#: here rather than typed at two call sites. ⚠️ The round-2 defect this fixes:
#: `engraved:omr_ned` carried the key and `competitive:engraved:audiveris`
#: carried none, so the pair had ONE member, the renderer's grouping found no
#: pair, and it fell back to grouping on `ceiling.kind == "competitive"` — which
#: swept in a pre-registered admission bar under a heading reading "different
#: system". A one-sided key is worse than no key: it looks satisfied.
H2H_ENGRAVED = "engraved|orchestral-e2e-fixtures|11works|musicdiff-AllObjects"
H2H_SCAN = "scan|scan-e2e-fixtures|10rows|musicdiff-AllObjects"


def pct_err(m, f):
    return round(100.0 * (1.0 - m) / (1.0 - f), 2)


def pct_rate(v, c):
    return round(100.0 * v / c, 2)


def row(**kw):
    base = {
        "id": None, "stage": None, "family": None,
        "comparable_as": {"time_series": None, "head_to_head": None},
        # ⚠️ SCHEMA-ENFORCED. A row whose number is easy to misread beside its
        # neighbours carries the sentence that disambiguates it, and a renderer
        # may not drop it. See `rules.mandatory_caption`.
        "mandatory_caption": None,
        "raw_metric": None, "native_direction": None,
        "native_worst": None, "native_best": None,
        "value": None,
        "transform": None,
        "ceiling": {"kind": None, "value": None, "status": None,
                    "evidence": [], "control": None},
        "pct_of_achievable": None,
        "n": None, "n_unit": None,
        "era_key": None,
        "noise_floor": None,
        "summability_class": None,
        "pool_key": None,
        "scoreable": False,
        "why_not": None,
        "source": None,
    }
    base.update(kw)
    return base


rows = []

# ─────────────────────────────────────────────────────────── ENGRAVED, end to end
dt = L["record"]["runs"]["direction_text"]
bm = L["record"]["benchmark"]
ERA_ENG = "orchestral-e2e|%s|%dworks|direction_text|%s" % (
    bm["since"], len(bm["works"]), dt["commit"])
rows.append(row(
    id="engraved:omr_ned", stage="= finished file", family="engraved",
    raw_metric="OMR-NED (musicdiff 5.2)", native_direction="lower_is_better",
    native_worst=1.0, native_best=0.0, value=dt["pooled"],
    transform="pct = 100 * (1 - M) / (1 - F)",
    ceiling={
        "kind": "structural", "value": 0.0, "status": "measured",
        "evidence": [REL["noop"]],
        "control": "the page-normalising transform is a NO-OP on all 11 works "
                   "(is_a_no_op: true) — these fixtures are 1:1, so no part of "
                   "this figure is a charge for a printing convention. The "
                   "control COULD have failed: on the scan side the same "
                   "transform removes 33.8% of the edits.",
    },
    pct_of_achievable=pct_err(dt["pooled"], 0.0),
    n=len(dt["works"]), n_unit="works",
    era_key=ERA_ENG,
    noise_floor={
        "value_edits": 0,
        "status": "measured_on_a_2_work_subset",
        "evidence": "benchmarks/omr-pipeline-audit-2026-09/"
                    "engraved-noise-floor.json",
        "note": "two arms of `orchestral_eval --omr-ned --no-direction-text` "
                "over mahler-sym5-mvt1 + brahms-sym1-mvt1 on one unchanged "
                "tree, run serially: 40/40 and 518/518, and the exports are "
                "BYTE-IDENTICAL rather than merely equal-scoring. Both arms "
                "demonstrably ran (415 s vs 270 s wall, and per-work pipeline "
                "runtime 341.9 s vs 206.7 s).",
        "⚠️_scope": "n=2 works, direction text OFF. It does NOT license a zero "
                    "floor for the eleven-work pool or for the default "
                    "configuration: the scan harness measured exactly 0 on its "
                    "five-row era and ±6 on its twenty-row era, so a floor is a "
                    "property of the POOL as much as of the pipeline. A delta "
                    "on this row still may not be gated.",
    },
    summability_class="omr_ned_engraved", pool_key="engraved/orchestral-e2e/11",
    comparable_as={"time_series": "orchestral-e2e|2026-09-02|11works|direction_text",
                   "head_to_head": H2H_ENGRAVED},
    scoreable=True, source=REL["record"],
    companions={"edits": dt["edits"], "truth_symbols": dt["truth_symbols"],
                "pred_symbols": dt["pred_symbols"]},
))

for w in dt["works"]:
    rows.append(row(
        id="engraved:omr_ned:" + w["work_id"], stage="= finished file",
        family="engraved", raw_metric="OMR-NED", native_direction="lower_is_better",
        native_worst=1.0, native_best=0.0, value=w["omr_ned"],
        transform="pct = 100 * (1 - M) / (1 - F)",
        ceiling={"kind": "structural", "value": 0.0, "status": "measured",
                 "evidence": [REL["noop"]], "control": "per-work no-op, delta_edits 0"},
        pct_of_achievable=pct_err(w["omr_ned"], 0.0),
        n=1, n_unit="works", era_key=ERA_ENG,
        noise_floor={"value": None, "status": "unmeasured"},
        summability_class="omr_ned_engraved", pool_key="engraved/orchestral-e2e/11",
        scoreable=True, source=REL["record"],
        companions={"edits": w["edits"]},
        flags=(["denominator is a 3-bar excerpt, a third of every other row — "
                "noisiest ratio in the set"] if w["work_id"] == "dvorak-sym9-mvt4"
               else ["~41% of notes land in `order` bars with every pitch present "
                     "on both sides — a divisi voice-split convention, not "
                     "recognition"] if w["work_id"] == "mozart-sym40-mvt1" else []),
    ))

# ─────────────────────────────────────────── ENGRAVED, stage 1 reading (page truth)
agg = {}
for w in L["reading"]["stage1_reading"].values():
    for fam, v in w["tolerances"]["0.5"]["per_family"].items():
        a = agg.setdefault(fam, [0, 0, 0])
        a[0] += v["truth"]; a[1] += v["pred"]; a[2] += v["matched"]


def f1(t, p, m):
    if not t or not p:
        return None
    pr, rc = m / p, m / t
    return (2 * pr * rc / (pr + rc)) if pr + rc else 0.0


ERA_READ = "page-truth|verovio-render|300dpi|tol0.5spaces|11works"
UNRELIABLE = {"accidental": ("render",
                             "Verovio draws one accidental per <alter>, not per "
                             "<accidental> — the rendered page carries ink a real "
                             "engraver would never print (Brahms 1: 54 <accidental>, "
                             "149 <alter>, 149 drawn). page_truth.render_fidelity "
                             "declares the family unreliable.")}
FRAME = {"barline": "CV-detected in CELL-relative coordinates and never expressed "
                    "in page coordinates — 45 printed against 0 comparable. A frame "
                    "mismatch, not a miss."}
pool = [0, 0, 0]
for fam in sorted(agg):
    t, p, m = agg[fam]
    v = f1(t, p, m)
    if fam in FRAME:
        rows.append(row(
            id="reading:" + fam, stage="3 measure + barline", family="engraved",
            raw_metric="detection F1 vs exact page truth",
            native_direction="higher_is_better", native_best=1.0, native_worst=0.0,
            value=None,
            ceiling={"kind": "visibility", "value": None, "status": "measured",
                     "evidence": [REL["reading"]], "control": FRAME[fam]},
            n=t, n_unit="printed symbols", era_key=ERA_READ,
            summability_class="reading_f1", pool_key=None,
            scoreable=False, why_not=FRAME[fam], source=REL["reading"]))
        continue
    if fam in UNRELIABLE:
        kind, why = UNRELIABLE[fam]
        rows.append(row(
            id="reading:" + fam, stage="4 symbol detection", family="engraved",
            raw_metric="detection F1 vs exact page truth",
            native_direction="higher_is_better", native_best=1.0, native_worst=0.0,
            value=v,
            ceiling={"kind": kind, "value": None, "status": "measured_unreliable",
                     "evidence": [REL["reading"], "tools/omr/page_truth.py "
                                                  "render_fidelity"],
                     "control": why},
            n=t, n_unit="printed symbols", era_key=ERA_READ,
            summability_class="reading_f1", pool_key=None,
            scoreable=False,
            why_not="the FIXTURE is unreadable for this family — a score here "
                    "measures Verovio, not the pipeline", source=REL["reading"]))
        continue
    pooled_member = fam != "beam"
    rows.append(row(
        id="reading:" + fam, stage="4 symbol detection", family="engraved",
        raw_metric="detection F1 vs exact page truth",
        native_direction="higher_is_better", native_best=1.0, native_worst=0.0,
        value=v, transform="pct = 100 * V / C",
        ceiling={"kind": "assumed", "value": 1.0, "status": "assumed",
                 "evidence": [], "control": "no measurement says a perfect reader "
                                            "could not reach F1 1.000 here; C=1 is "
                                            "the assumption-direction default and "
                                            "can only UNDERSTATE the score"},
        pct_of_achievable=pct_rate(v, 1.0),
        n=t, n_unit="printed symbols", era_key=ERA_READ,
        noise_floor={"value": None, "status": "unmeasured",
                     "note": "re-rendering at 600 dpi moved Brahms 1 0.854->0.868 "
                             "and Tchaikovsky 4 0.787->0.789 (FINDINGS controls)"},
        summability_class="reading_f1",
        pool_key="engraved/page-truth/reading" if pooled_member else None,
        scoreable=True, source=REL["reading"],
        companions={"truth": t, "pred": p, "matched": m},
        flags=([] if pooled_member else
               ["held out of the pooled F1: CV-detected, unit is a STROKE not a "
                "per-note-per-level <beam>"]),
    ))
    if pooled_member:
        pool[0] += t; pool[1] += p; pool[2] += m

rows.append(row(
    id="reading:POOLED", stage="4 symbol detection", family="engraved",
    raw_metric="detection F1 vs exact page truth, pooled",
    native_direction="higher_is_better", native_best=1.0, native_worst=0.0,
    value=f1(*pool), transform="pct = 100 * V / C",
    ceiling={"kind": "assumed", "value": 1.0, "status": "assumed",
             "evidence": [], "control": "the RENDER ceiling is enacted as an "
                                        "EXCLUSION, not as C<1: including the "
                                        "render-unreliable accidental family "
                                        "would read %.4f instead of %.4f"
                                        % (L["pct"]["engraved_reading"]
                                           ["if_render_unreliable_family_included"],
                                           L["pct"]["engraved_reading"]
                                           ["as_shipped_excludes_render_unreliable"])},
    pct_of_achievable=pct_rate(f1(*pool), 1.0),
    n=pool[0], n_unit="printed symbols", era_key=ERA_READ,
    summability_class="reading_f1", pool_key="engraved/page-truth/reading",
    scoreable=True, source=REL["reading"],
    companions={"truth": pool[0], "pred": pool[1], "matched": pool[2]}))

# ─────────────────────────────────────────────────── ENGRAVED, structure + naming
o = L["one2one"]["works"]
ok = sum(1 for w in o if w["our_parts"] == w["truth_parts"])
rows.append(row(
    id="engraved:structure", stage="1 render + staff detection", family="engraved",
    raw_metric="works whose part count equals the truth's",
    native_direction="higher_is_better", native_best=1.0, native_worst=0.0,
    value=ok / len(o), transform="pct = 100 * V / C",
    ceiling={"kind": "structural", "value": 1.0, "status": "measured",
             "evidence": [REL["one2one"]],
             "control": "these fixtures are 1:1 BY CONSTRUCTION — every truth part "
                        "gets its own printed staff — so 1.0 is genuinely reachable "
                        "and this stage is never asked the hard question a "
                        "conductor's page asks"},
    pct_of_achievable=pct_rate(ok / len(o), 1.0),
    n=len(o), n_unit="works", era_key=ERA_READ,
    summability_class="structure_rate", pool_key=None,
    mandatory_caption="These fixtures are 1:1 BY CONSTRUCTION — every truth "
                      "part gets its own printed staff. A conductor's page "
                      "condenses and splits; this stage is never asked that "
                      "question here.",
    scoreable=True, source=REL["one2one"],
    flags=["EASY BY CONSTRUCTION — a 100 here does not predict a conductor's page"]))

# ───────────────────────────────────────────────────────── SCAN, 20-row headline
g = L["gate20"]["pooled"]
ERA_SCAN20 = "scan-e2e|20rows|reconciliation|dpi600|no-dossier|UNSTAMPED-COMMIT"
den20 = g["truth_symbols"] + g["pred_symbols"]
rows.append(row(
    id="scan:omr_ned", stage="= finished file", family="scan",
    raw_metric="OMR-NED (musicdiff 5.2)", native_direction="lower_is_better",
    native_worst=1.0, native_best=0.0, value=g["omr_ned"],
    transform="pct = 100 * (1 - M) / (1 - F)",
    ceiling={"kind": "assumed", "value": 0.0, "status": "assumed",
             "evidence": [REL["norm"], REL["indep"]],
             "control": "F=0 is the assumption-direction default and UNDERSTATES. "
                        "A measured floor now exists for 15 of these 20 rows, on "
                        "THIS arm (the 20-row normalised artefact's raw pool is "
                        "exactly the canonical 0.8444). Over those 15 the floor is "
                        "0.134 and the score is %.1f%% instead of %.1f%%. The "
                        "pooled 20-row row keeps F=0 because 5 rows have no map "
                        "and a pool's trust is the MINIMUM of its members'."
                        % (L["pct"]["scan"]["pool_all_normalisable"]
                           ["pct_of_achievable"],
                           L["pct"]["scan"]["pool_all_normalisable"]
                           ["pct_naive_no_ceiling"])},
    pct_of_achievable=pct_err(g["omr_ned"], 0.0),
    n=g["n_rows"], n_unit="hand-verified pages", era_key=ERA_SCAN20,
    noise_floor={"value_edits": 6, "value_pct_points": round(600.0 / den20, 3),
                 "status": "measured",
                 "note": "±6 edits pooled; on a single row the same 6 edits are "
                         "worth ~0.5 pct-points. Source: CLAUDE.md, "
                         "beethoven-984073-p4 4673 then 4679 on one tree."},
    summability_class="omr_ned_scan", pool_key="scan/scan-e2e/20",
    scoreable=True, source=REL["gate20"],
    companions={"edits": g["omr_ed"], "truth_symbols": g["truth_symbols"],
                "pred_symbols": g["pred_symbols"]},
    flags=["the artefact carries NO commit and NO machine-checked era stamp",
           "34.5% of the edits on the 15 normalisable rows are structural charge "
           "for a printing convention, not recognition error"]))

# ── ROUND 2: the floor is now MEASURED, not estimated.
fl = L["floor"]["pooled"]
rows.append(row(
    id="scan:omr_ned:page_fidelity_15rows", stage="= finished file", family="scan",
    raw_metric="OMR-NED", native_direction="lower_is_better",
    native_worst=1.0, native_best=0.0,
    value=L["pct"]["scan"]["pool_all_normalisable"]["pooled_omr_ned"],
    transform="pct = 100 * (1 - M) / (1 - F)",
    ceiling={"kind": "structural", "value": fl["floor_unpaired_parts_only"],
             "status": "measured_directly",
             "constraint": "PAGE FIDELITY. The metric's unconstrained floor is "
                           "ZERO — emitting the ENCODING rather than the page "
                           "scores 0, which is exactly what OMR_CONDENSED_PARTS "
                           "would harvest and what CLAUDE.md calls an "
                           "anti-feature. This floor is the price of an output "
                           "faithful to the printed page, which is the output "
                           "Sean asked for. Every scan % below is therefore "
                           "'% of achievable UNDER PAGE FIDELITY'.",
             "evidence": ["benchmarks/omr-pipeline-audit-2026-09/"
                          "structural-floor-measured.json"],
             "control": "the derived truth is scored AS THE PREDICTION against "
                        "the raw truth, so no output of ours appears in the "
                        "measurement at all. Controls: the three identity-"
                        "transform rows (Dvorak, 15 parts into 15 staves) score "
                        "EXACTLY 0 edits; all 15 derived truths reproduce the "
                        "committed control's canonical hashes; every truth "
                        "fixture's sha256 equals the canonical arm's."},
    pct_of_achievable=round(pct_err(
        L["pct"]["scan"]["pool_all_normalisable"]["pooled_omr_ned"],
        fl["floor_unpaired_parts_only"]), 2),
    n=fl["n_rows"], n_unit="pages",
    era_key="scan-e2e|20rows|reconciliation|normalised-transform1.2.0|afea84ba",
    noise_floor={"value_edits": 6, "status": "measured",
                 "applies_to": "M only — F contains no prediction of ours, so "
                               "arm-to-arm noise cannot move it"},
    summability_class="omr_ned_scan_ceilinged", pool_key="scan/page-fidelity/15",
    comparable_as={"time_series": "scan-e2e|20rows|reconciliation|"
                                  "normalised-transform1.2.0",
                   "head_to_head": None},
    scoreable=True, source="benchmarks/omr-pipeline-audit-2026-09/"
                          "structural-floor-measured.json",
    companions={"floor_unpaired_parts": fl["floor_unpaired_parts_only"],
                "floor_structural": fl["floor_structural_only"],
                "floor_total": fl["floor_total"],
                "residue_share_of_total_floor": fl["residue_share_of_total_floor"]},
    flags=["the floor is the MOST CONSERVATIVE rung of a three-rung ladder "
           "(0.2123 unpaired-parts / 0.4982 structural / 0.6348 total). A larger "
           "floor raises the score, so the ladder is climbed only as far as the "
           "evidence is unambiguous.",
           "15 of 20 rows: the four Mahler and one Bach rows have no hand-read "
           "staves map and are not guessed at"]))

# tier B: every normalisable row of the canonical arm, single-source estimator
pb = L["pct"]["scan"]["pool_all_normalisable"]
rows.append(row(
    id="scan:omr_ned:ceiling_measured_15rows", stage="= finished file",
    family="scan", raw_metric="OMR-NED", native_direction="lower_is_better",
    native_worst=1.0, native_best=0.0, value=pb["pooled_omr_ned"],
    transform="pct = 100 * (1 - M) / (1 - F)",
    ceiling={"kind": "structural", "value": pb["pooled_floor_low"],
             "status": "measured_single_source",
             "evidence": [REL["norm"],
                          "benchmarks/omr-scan-e2e-2026-09/works.json (hand-read map)",
                          REL["indep"]],
             "control": "the QUANTITY is defined by (reference truth, hand-read page "
                        "map) and is independent of our output; the ESTIMATOR is the "
                        "MINIMUM `entire staff` charge over every engine measured on "
                        "each row, which is our own on 10 of the 15. On the other 5 "
                        "an independent engine produces the identical number."},
    pct_of_achievable=round(pb["pct_of_achievable"], 2),
    n=pb["n_rows"], n_unit="pages",
    era_key="scan-e2e|20rows|reconciliation|normalised-transform1.2.0|afea84ba",
    noise_floor={"value_edits": 6, "status": "measured"},
    summability_class="omr_ned_scan_ceilinged",
    pool_key="scan/ceiling-measured/15",
    scoreable=True, source=REL["pct"],
    flags=["15 of 20 rows: the five Mahler/Bach rows have no hand-read staves map "
           "and are not guessed at"]))

rows.append(row(
    id="scan:omr_ned:ceiling_corroborated_subset", stage="= finished file",
    family="scan", raw_metric="OMR-NED", native_direction="lower_is_better",
    native_worst=1.0, native_best=0.0,
    value=L["pct"]["scan"]["pool"]["pooled_omr_ned"],
    transform="pct = 100 * (1 - M) / (1 - F)",
    ceiling={"kind": "structural",
             "value": L["pct"]["scan"]["pool"]["pooled_floor_low"],
             "status": "measured_and_corroborated",
             "evidence": [REL["norm"], REL["indep"],
                          "benchmarks/omr-scan-e2e-2026-09/works.json (hand-read map)"],
             "control": "the ceiling is bit-identical for an INDEPENDENT engine "
                        "(Audiveris 5.11) on all 5 rows. The control fired: it is "
                        "NOT identical on 3 further rows, which are therefore "
                        "excluded — every one of those is a two-system page."},
    pct_of_achievable=round(L["pct"]["scan"]["pool"]["pct_of_achievable"], 2),
    n=L["pct"]["scan"]["pool"]["n_rows"], n_unit="pages",
    era_key="scan-e2e|20rows|reconciliation|ceiling-corroborated-5|transform1.2.0|afea84ba",
    noise_floor={"value_edits": 6, "status": "measured"},
    summability_class="omr_ned_scan_ceilinged",
    pool_key="scan/ceiling-corroborated/5",
    scoreable=True, source=REL["pct"],
    flags=["5 of 20 rows, 3 of 6 works — NOT the headline. Since 2026-09-07 it is "
           "on the SAME arm as the headline (the 20-row normalised artefact), so "
           "the arm mismatch that made this incomparable is closed; the ROW-SET "
           "mismatch stands and still refuses the difference."]))

# ─────────────────────────────────────────────────────────── SCAN, structural stages
gr = L["gate20"]["rows"]
st_ok = sum(1 for r in gr if r["printed"]["staves"] == r["detected"]["staves"])
sy_ok = sum(1 for r in gr if r["printed"]["systems"] == r["detected"]["systems"])
for rid, stage, ok_n, note in (
        ("scan:staves", "1 render + staff detection", st_ok,
         "staves detected == staves printed, hand-read"),
        ("scan:systems", "2 system grouping", sy_ok,
         "systems detected == systems printed, hand-read")):
    rows.append(row(
        id=rid, stage=stage, family="scan",
        raw_metric="rows exact", native_direction="higher_is_better",
        native_best=1.0, native_worst=0.0, value=ok_n / len(gr),
        transform="pct = 100 * V / C",
        ceiling={"kind": "input", "value": 1.0, "status": "measured",
                 "evidence": [REL["gate20"]],
                 "control": "the printed counts are HAND-READ off the scan, so "
                            "1.0 is what the page actually contains"},
        pct_of_achievable=pct_rate(ok_n / len(gr), 1.0),
        n=len(gr), n_unit="pages", era_key=ERA_SCAN20,
        summability_class="structure_rate", pool_key=None,
        scoreable=True, source=REL["gate20"], companions={"exact_rows": ok_n}))

acc = {}
for key in ("exact", "step", "with_duration"):
    t = p = m = 0
    for r in gr:
        n = (r.get("notes") or {}).get("pooled")
        if n:
            t += n[key]["truth"]; p += n[key]["omr"]; m += n[key]["matched"]
    acc[key] = (t, p, m)
n_scored = sum(1 for r in gr if (r.get("notes") or {}).get("pooled"))
rows.append(row(
    id="scan:pitch", stage="6 pitch resolution", family="scan",
    raw_metric="staff-position recall vs truth notes",
    native_direction="higher_is_better", native_best=1.0, native_worst=0.0,
    value=acc["step"][2] / acc["step"][0], transform="pct = 100 * V / C",
    ceiling={"kind": "assumed", "value": 1.0, "status": "assumed", "evidence": [],
             "control": "no measurement of how much ink is genuinely unrecoverable "
                        "on these scans exists — the INPUT ceiling is unmeasured, "
                        "so C=1 under the assumption-direction rule"},
    pct_of_achievable=pct_rate(acc["step"][2] / acc["step"][0], 1.0),
    n=acc["step"][0], n_unit="truth notes", era_key=ERA_SCAN20,
    summability_class="note_recall", pool_key="scan/scan-e2e/20",
    scoreable=True, source=REL["gate20"],
    companions={"rows_with_hand_map": n_scored,
                "spelled_pitch_recall": acc["exact"][2] / acc["exact"][0]}))
rows.append(row(
    id="scan:duration", stage="7 rhythm / durations", family="scan",
    raw_metric="of pitch-matched notes, share whose duration is also right",
    native_direction="higher_is_better", native_best=1.0, native_worst=0.0,
    value=acc["with_duration"][2] / acc["exact"][2], transform="pct = 100 * V / C",
    ceiling={"kind": "assumed", "value": 1.0, "status": "assumed", "evidence": [],
             "control": None},
    pct_of_achievable=pct_rate(acc["with_duration"][2] / acc["exact"][2], 1.0),
    n=acc["exact"][2], n_unit="pitch-matched notes", era_key=ERA_SCAN20,
    summability_class="duration_rate", pool_key="scan/scan-e2e/20",
    scoreable=True, source=REL["gate20"]))

# ─────────────────────────────────────────────────────────── SCAN, detector probes
hp = L["hairpin"]
truth = sum(v["truth_hairpins"] for v in hp.values())
yolo = sum(v["yolo"] for v in hp.values())
rows.append(row(
    id="scan:hairpin_detect", stage="4 symbol detection", family="scan",
    raw_metric="hairpins the YOLO detector finds",
    native_direction="higher_is_better", native_best=1.0, native_worst=0.0,
    value=yolo / truth, transform="pct = 100 * V / C",
    ceiling={"kind": "input", "value": 1.0, "status": "assumed",
             "evidence": [REL["hairpin"]],
             "control": "against exact engraved page truth the same detector scores "
                        "F1 1.000 (n=3), so the ink IS readable in principle — but "
                        "nothing measures how much of a hairpin survives a bitonal "
                        "600 dpi scan, so C=1 is assumed"},
    pct_of_achievable=pct_rate(yolo / truth, 1.0),
    mandatory_caption="Scores the DETECTOR only — a classical-CV reader added "
                      "later carries 118 of 198 <wedge> into the file, so this "
                      "is not what reaches a user. The ceiling it is measured "
                      "against (≥0.80) comes from ONE edition, Breitkopf & "
                      "Härtel, Brahms 1.",
    n=truth, n_unit="truth hairpins", era_key="hairpin-cv|11 scanned pages",
    summability_class="detector_recall", pool_key=None,
    scoreable=True, source=REL["hairpin"],
    flags=["the classical-CV reader added later carries 118 of 198 <wedge> into "
           "the file — this row scores the DETECTOR only"]))

# ────────────────────────────────────────────────────────── COMPETITIVE ceilings
aud_e = L["aud_eng"]["engines"]["audiveris"]
okw = {k: v for k, v in aud_e.items() if v.get("status") == "ok"}
aud_ed = sum(v["omr_ed"] for v in okw.values())
aud_den = sum(v["truth_symbols"] + v["pred_symbols"] for v in okw.values())
aud_ned = aud_ed / aud_den
rows.append(row(
    id="competitive:engraved:audiveris", stage="= finished file", family="engraved",
    raw_metric="OMR-NED of Audiveris 5.11, our fixtures, our scorer",
    native_direction="lower_is_better", native_worst=1.0, native_best=0.0,
    value=aud_ned, transform="pct = 100 * (1 - M) / (1 - F)",
    ceiling={"kind": "competitive", "value": 0.0, "status": "measured",
             "evidence": [REL["aud_eng"]],
             "control": "same fixtures, same musicdiff bridge — the only valid "
                        "comparison. Published paper figures are pooled over other "
                        "corpora and are context, never comparison."},
    pct_of_achievable=pct_err(aud_ned, 0.0),
    n=len(okw), n_unit="works", era_key=ERA_ENG.replace("|" + dt["commit"], "|audiveris-5.11"),
    comparable_as={"time_series": None, "head_to_head": H2H_ENGRAVED},
    summability_class="omr_ned_engraved", pool_key=None,
    scoreable=True, source=REL["aud_eng"],
    companions={"ours": pct_err(dt["pooled"], 0.0),
                "we_are_ahead_by_points": round(pct_err(dt["pooled"], 0.0)
                                                - pct_err(aud_ned, 0.0), 2)}))

# ── OUR side of the scan head-to-head. It has to exist as a ROW, or the pair is
# one-sided and a renderer can only print "ours —". ⚠️ It may NOT be
# `scan:omr_ned`: that is the 20-row era and Audiveris covers 10 rows of the
# 11-row era, so pairing them would be a false head-to-head between different
# row sets — the failure the comparability rule exists to refuse. The figure is
# the one the industry arm itself computed over exactly the rows Audiveris
# scored.
_sc = L["scancmp"]["ours_current"]
rows.append(row(
    id="scan:omr_ned:same_10_rows_as_audiveris", stage="= finished file",
    family="scan", raw_metric="OMR-NED over exactly the 10 scan rows Audiveris "
                              "completed", native_direction="lower_is_better",
    native_worst=1.0, native_best=0.0, value=_sc["omr_ned"],
    transform="pct = 100 * (1 - M) / (1 - F)",
    ceiling={"kind": "assumed", "value": 0.0, "status": "assumed", "evidence": [],
             "control": "F=0 by the assumption-direction rule. This row exists to "
                        "make the head-to-head two-sided on a shared row set; it "
                        "is not a ceilinged figure and must not be read as one."},
    pct_of_achievable=round(pct_err(_sc["omr_ned"], 0.0), 2),
    n=L["scancmp"]["audiveris"]["n_rows"], n_unit="pages",
    era_key="scan-e2e|11rows|restamp-composed|10 rows Audiveris completed",
    noise_floor={"value_edits": 6, "status": "measured"},
    comparable_as={"time_series": None, "head_to_head": H2H_SCAN},
    summability_class="omr_ned_scan", pool_key=None,
    mandatory_caption="A 10-row subset of the retired 11-row scan era, kept only "
                      "so the Audiveris comparison has two sides. It is NOT the "
                      "headline and may not be differenced against the 20-row "
                      "figure.",
    scoreable=True, source=REL["scancmp"],
    companions={"edits": _sc["omr_ed"]},
    flags=["Audiveris is AHEAD of us here — 20.81%% against our %.2f%%. Recorded, "
           "not hidden." % pct_err(_sc["omr_ned"], 0.0)]))

asc = L["aud_scan"]["pooled"]
rows.append(row(
    id="competitive:scan:audiveris", stage="= finished file", family="scan",
    raw_metric="OMR-NED of Audiveris 5.11 on the 11-row scan era",
    native_direction="lower_is_better", native_worst=1.0, native_best=0.0,
    value=asc["omr_ned"], transform="pct = 100 * (1 - M) / (1 - F)",
    ceiling={"kind": "competitive", "value": 0.0, "status": "assumed",
             "evidence": [REL["aud_scan"]],
             "control": "⚠️ this arm covers the ELEVEN-row scan era; the headline "
                        "moved to 20 rows on 2026-09-04 and the arm was not "
                        "widened. Comparable to our 11-row 0.8345 only."},
    pct_of_achievable=pct_err(asc["omr_ned"], 0.0),
    n=asc["n_rows"], n_unit="pages",
    era_key="scan-e2e|11rows|restamp-composed|audiveris-5.11",
    comparable_as={"time_series": None, "head_to_head": H2H_SCAN},
    summability_class="omr_ned_scan", pool_key=None,
    scoreable=True, source=REL["aud_scan"],
    flags=["Audiveris is AHEAD of us on this pool (0.7919 vs our 0.8345 on the "
           "same 10 rows) — recorded, not hidden",
           "on 7 of 10 rows its structural charge is bit-identical to ours, which "
           "is how we know that charge is a ceiling and not a defect"]))

# ─────────────────────────────────────────────── UNSCOREABLE — visibility ceilings
content = L["content"]
for s in content["pipeline"]["stages"]:
    for fam in ("engraved", "scan"):
        cell = s.get(fam) or {}
        if cell.get("metric") or cell.get("rate") is not None:
            continue
        rows.append(row(
            id="%s:stage%s" % (fam, s["n"]), stage="%s %s" % (s["n"], s["name"]),
            family=fam, raw_metric=None,
            native_direction=None, value=None,
            ceiling={"kind": "visibility", "value": None, "status": "measured",
                     "evidence": [cell.get("source", "")],
                     "control": cell.get("detail", "")[:400]},
            n=0, n_unit="observations",
            era_key=ERA_ENG if fam == "engraved" else ERA_SCAN20,
            summability_class=None, pool_key=None,
            scoreable=False,
            why_not="the harness cannot see this stage at all — %s. A ceiling of "
                    "ZERO INFORMATION is not a score of 0 and not a score of 100."
                    % cell.get("display"),
            source=REL["content"]))

# ────────────────────────────────────────── UNSCOREABLE — no ceiling evidence yet
ic = L["inputceil"]
rows.append(row(
    id="ceiling:input:notehead:scan", stage="4 symbol detection", family="scan",
    raw_metric="reference notes a HUMAN could box on a real scan, per reference note",
    native_direction="higher_is_better", native_best=1.0, native_worst=0.0,
    value=ic["ratios"]["human_boxes_per_reference_note"],
    ceiling={"kind": "input", "value": None, "status": "bounded_above",
             "evidence": ["benchmarks/omr-pipeline-audit-2026-09/"
                          "input-ceiling-from-labels.json",
                          ic["batch"]],
             "control": "the labeler drew boxes on the same scanned cells the "
                        "detector saw, with no reference to our output — the MXL "
                        "says what the MUSIC is, a human's box says what the INK "
                        "is. Restricted to the ONE batch carrying a COMPLETION "
                        "pass, because a single-symbol sweep leaves every other "
                        "class unboxed by instruction."},
    n=ic["counts"]["reference_notes_in_those_bars"], n_unit="reference notes",
    era_key="labeling|breitkopf-brahms1|completion-pass|47 cells",
    summability_class=None, pool_key=None,
    scoreable=False,
    why_not="an UPPER BOUND, not a ceiling to score against. 201 human "
            "noteheads against 207 reference notes is a ratio of COUNTS, not a "
            "matched recall: grace notes are on the page and absent from the "
            "encoding (0 in 28,579), so human boxes are inflated and the true "
            "figure is at or below 0.971. What it DOES establish is that C = 1.0 "
            "is very nearly right for noteheads on this print — so `scan:pitch` "
            "at 83.4%% is an achievement number, not a fixture artefact. One "
            "batch, one publisher, density-selected cells.",
    source="benchmarks/omr-pipeline-audit-2026-09/input-ceiling-from-labels.json"))

rows.append(row(
    id="ceiling:input:hairpin:scan", stage="4 symbol detection", family="scan",
    raw_metric="can a human see a hairpin on these scans at all?",
    native_direction="higher_is_better", value=None,
    ceiling={"kind": "input", "value": 0.80, "status": "bounded_below",
             "evidence": ["benchmarks/omr-pipeline-audit-2026-09/"
                          "input-ceiling-from-labels.json",
                          "benchmarks/omr-pipeline-audit-2026-09/"
                          "hairpin-ceiling-value.json"],
             "edition": "Breitkopf & Härtel, Brahms 1 mvt 1 — ONE EDITION, "
                        "irreducibly so today (only one batch in the corpus has "
                        "a COMPLETION pass). Quote with the publisher NAMED; it "
                        "is not a claim about scans in general.",
             "control": "counted directly: over 55 completion-swept cells a "
                        "human drew 13 dynamicCrescendoHairpin + 4 "
                        "dynamicDiminuendoHairpin = SEVENTEEN. At bar level, of "
                        "the 5 swept bars where the encoding STARTS a hairpin, a "
                        "human found ink in 4 — a bar recall of 0.80 at n=5. "
                        "The count ratio (17 human / 11 reference starts = "
                        "1.545) is NOT usable: a barline cuts one hairpin into "
                        "two boxes and a three-bar hairpin is one start drawn "
                        "across three cells, so the two units are biased in "
                        "opposite directions."},
    n=5, n_unit="swept bars carrying a reference hairpin start",
    mandatory_caption="Measured on ONE edition — Breitkopf & Härtel, Brahms 1 "
                      "mvt 1 — and irreducibly so today: only one labeling batch "
                      "in the corpus carries a completion pass. Not a claim "
                      "about scans in general.",
    era_key="labeling|breitkopf-brahms1|completion-pass|55 cells",
    scoreable=False,
    why_not="A BOUND, not a point, so it is not scored — but it is now a "
            "ceiling rather than a refutation. `scan:hairpin_detect` reads "
            "1.01%% against a ceiling measured at AT LEAST 0.80 on this "
            "edition, so the detector is at roughly one part in eighty of what "
            "a reader recovers. ⚠️ AND THE MATCHED COMPARISON IS WORSE THAN THE "
            "CORPUS RATE: on the SAME three pages the human swept, the "
            "transcription contains 10,523 detections and ZERO of either "
            "hairpin class. The 1-of-99 is not a thin-sample artefact — on this "
            "edition it is zero. n = 5 bars is the whole sample the corpus can "
            "offer; the same sweep drew 62 ties and 27 slurs, the other two "
            "families a fine-tune is documented to delete.",
    source="benchmarks/omr-pipeline-audit-2026-09/input-ceiling-from-labels.json"))

rows.append(row(
    id="scan:input_ceiling:hollow_noteheads", stage="4 symbol detection",
    family="scan", raw_metric="half-noteheads detected on Beethoven 5 p.1",
    native_direction="higher_is_better", value=None,
    ceiling={"kind": "input", "value": None, "status": "unmeasured",
             "evidence": ["CLAUDE.md · benchmarks/omr-first-run-2026-08/DURATIONS.md"],
             "control": None},
    n=68, n_unit="printed half notes",
    era_key="ad-hoc|beethoven-sym5-mvt1-984073-p1",
    scoreable=False,
    why_not="the page prints 68 half notes and the detector found 8, now 31 — but "
            "NOTHING measures how many of those counters are actually closed at "
            "600 dpi bitonal, so there is no denominator of 'recoverable ink'. An "
            "INPUT ceiling is the one kind this project has never measured.",
    source="CLAUDE.md"))

rows.append(row(
    id="flag:OMR_CONDENSED_PARTS:oracle_ceiling", stage="11 export", family="scan",
    raw_metric="oracle ceiling quoted in CLAUDE.md's knobs table (-4,557 scan edits)",
    native_direction="lower_is_better", value=None,
    ceiling={"kind": None, "value": None, "status": "unmeasured", "evidence": [],
             "control": None},
    n=None, n_unit="edits", era_key=None, scoreable=False,
    why_not="⚠️ THE CEILING GRADES A CONFIGURATION THAT CANNOT OCCUR. Verified in "
            "this tree 2026-09-07: `condensed_parts` is READ at export.py:3331 "
            "(`s.get(\"condensed_parts\")`) and WRITTEN nowhere in tools/omr, so "
            "every staff reports 1 and the flag is inert even when set. The "
            "-4,557 figure was measured with ORACLE counts. A quoted ceiling for "
            "an unreachable configuration is the mirror image of a fabricated "
            "100%: it makes a gap look bigger than the pipeline can act on.",
    source="tools/omr/export.py:3278-3331 (grep: only reader, no writer)"))

# ── M1: three estates the round-1 registry omitted entirely.
rows.append(row(
    id="identity:calibration:ECE", stage="10 staff -> slot, part identity",
    family="scan", raw_metric="Expected Calibration Error of P(name)",
    native_direction="lower_is_better", native_worst=None, native_best=0.0,
    value=0.1277,
    ceiling={"kind": None, "value": None, "status": "unmeasured", "evidence": [],
             "control": None},
    n=197, n_unit="graded records",
    era_key="staff-identity-layer|2026-09-05|n197",
    scoreable=False,
    why_not="⚠️ NEITHER TRANSFORM CAN EXPRESS THIS, and forcing it would be "
            "worse than omitting it. `pct = 100*(W-M)/(W-F)` needs a defensible "
            "WORST CASE. OMR-NED has one (predict nothing scores exactly 1). A "
            "calibration error has none: ECE's arithmetic maximum is 1.0 but "
            "that is unreachable in practice and carries no meaning, so a "
            "percentage against it would be a number with no referent — the "
            "exact defect this unit exists to remove. A THIRD transform kind "
            "would need an empirical worst case (e.g. the ECE of a constant "
            "predictor on this corpus), which nobody has measured. Note also "
            "that the estate's own finding is that the ECE improvement from "
            "n=197 to n=1571 is NOT calibration — Brier skill vs a constant "
            "predictor is +0.0004 and 95.8%% of mass sits in one bin — so a "
            "score here would be worse than absent. Blocked on WORKS, not "
            "records (backlog D5).",
    source="docs/backlog-2026-09-07-open-items.md D5; "
           "benchmarks/omr-staff-identity-layer-2026-09/"))

rows.append(row(
    id="labeling:ledger_zone:screening_rate", stage="(labeling QA)", family="scan",
    raw_metric="ledger-zone labels FLAGGED by the parity auditor",
    native_direction="lower_is_better", native_worst=1.0, native_best=0.0,
    value=0.069, transform="pct = 100 * (1 - M) / (1 - F)",
    ceiling={"kind": "visibility", "value": None, "status": "not_a_defect_rate",
             "evidence": ["benchmarks/omr-snap-ledger-2026-09/"
                          "LEDGER_ZONE_LABEL_AUDIT_2026-09-03.md"],
             "control": None},
    n=102, n_unit="ledger-zone labels",
    era_key="labeling-audit|simrock-dvorak9|2026-09-03",
    scoreable=False,
    why_not="⚠️ A SCREENING RATE IS NOT A DEFECT RATE, AND THIS IS THE CLEAREST "
            "CASE IN THE PROJECT OF THE CONFUSION THIS UNIT EXISTS TO FIX. The "
            "auditor flags 7 of 102 (6.9%%); hand adjudication found ONE real "
            "error (~0.9%%) — a 7x gap, and six of the seven share one mechanism "
            "(a printed ledger line print-merging into the notehead's connected "
            "component, pulling the centroid up to a half-step). Both numbers are "
            "percentages; only one is a quality figure. A dashboard that prints "
            "either alone is wrong: 6.9%% overstates the defect sevenfold, and "
            "0.9%% understates the reviewer's workload sevenfold. The registry's "
            "answer is that they are TWO ROWS with different `stage` semantics "
            "— a SCREEN and a DEFECT — never one, and a screen is never "
            "scoreable on the achievement axis.",
    source="benchmarks/omr-snap-ledger-2026-09/"
           "LEDGER_ZONE_LABEL_AUDIT_2026-09-03.md"))

rows.append(row(
    id="labeling:ledger_zone:defect_rate", stage="(labeling QA)", family="scan",
    raw_metric="ledger-zone labels ADJUDICATED wrong by a human",
    native_direction="lower_is_better", native_worst=1.0, native_best=0.0,
    value=1/102, transform="pct = 100 * (1 - M) / (1 - F)",
    ceiling={"kind": "assumed", "value": 0.0, "status": "assumed", "evidence": [],
             "control": "F=0 assumed: a perfect labeling pass has no defects. "
                        "Conservative by the assumption-direction rule."},
    pct_of_achievable=round(pct_err(1/102, 0.0), 2),
    n=102, n_unit="ledger-zone labels",
    era_key="labeling-audit|simrock-dvorak9|2026-09-03",
    comparable_as={"time_series": "labeling-audit|ledger-zone|adjudicated",
                   "head_to_head": None},
    summability_class="label_defect_rate", pool_key=None,
    scoreable=True,
    source="benchmarks/omr-snap-ledger-2026-09/"
           "LEDGER_ZONE_LABEL_AUDIT_2026-09-03.md",
    companions={"screening_rate": 0.069,
                "screen_to_defect_ratio": round(0.069 / (1/102), 1)},
    flags=["ALWAYS render beside `labeling:ledger_zone:screening_rate`. The two "
           "differ by 7x and both are percentages; showing either alone "
           "misleads in a named direction."]))

rows.append(row(
    id="prefill:precision:blind_out_of_sample", stage="(labeling pre-fill)",
    family="scan", raw_metric="exact-class precision of reference-driven "
                              "pre-filled verdicts, blind sample",
    native_direction="higher_is_better", native_best=1.0, native_worst=0.0,
    value=0.915, transform="pct = 100 * V / C",
    ceiling={"kind": "decision_rule", "value": 0.97, "status": "pre_registered",
             "evidence": ["benchmarks/omr-prefill-admission-2026-09/FINDINGS.md",
                          "benchmarks/omr-prefill-admission-2026-09/"
                          "PHASE_C_CELLS.json"],
             "control": "0.97 is the ADMISSION BAR set in advance, and the cells "
                        "were pre-registered at seed 20260903 with their status "
                        "recorded BEFORE labeling; the pass was run blind "
                        "(annotate.server --blind). The measurement came in "
                        "UNDER the bar and pre-filled verdicts stayed a queue "
                        "rather than becoming labels — a control that fired."},
    pct_of_achievable=round(pct_rate(0.915, 0.97), 2),
    n=141, n_unit="pre-filled boxes",
    era_key="prefill|brahms1-breitkopf|phase-C|blind|2026-09-03",
    comparable_as={"time_series": "prefill|brahms1-breitkopf|phase-C|blind",
                   "head_to_head": None},
    summability_class="prefill_precision", pool_key=None,
    scoreable=True,
    source="benchmarks/omr-prefill-admission-2026-09/FINDINGS.md",
    companions={"pre_registered_25_cells": 0.838, "other_24_cells": 1.0,
                "noteheads": 0.943, "rests": 0.722},
    flags=["a rare case where the CEILING IS A DECISION RULE rather than a "
           "physical limit — the bar a human set in advance for admitting the "
           "output without review. That is the most useful ceiling kind for "
           "anything gated on human trust, and the only pre-registered one in "
           "the registry."]))

rows.append(row(
    id="human:review_cost:identity", stage="(the purpose)", family="both",
    raw_metric="share of staff records a human must open — unnamed, "
               "categorically impossible, not-in-this-work, or contradicted by "
               "the staff's own margin label",
    native_direction="lower_is_better", native_worst=1.0, native_best=0.0,
    value=L["humancost"]["arms"][0]["human_cost_rate"] * 0 + (
        sum(a["human_cost_records"] for a in L["humancost"]["arms"])
        / sum(a["n_records"] for a in L["humancost"]["arms"])),
    transform="pct = 100 * (1 - M) / (1 - F)",
    ceiling={"kind": "assumed", "value": 0.0, "status": "assumed",
             "evidence": ["benchmarks/omr-pipeline-audit-2026-09/"
                          "human-cost-identity.json"],
             "control": "W = 1.0 is REAL, not a convention: a pipeline that "
                        "names nothing leaves every staff to the reviewer. "
                        "F = 0 is assumed and conservative. ⚠️ The floor is NOT "
                        "zero and is now LOCATED: a CONDENSED staff "
                        "(`Violoncello e Basso`) has a margin label and a slot "
                        "name that disagree and are BOTH RIGHT, and costs a look "
                        "no pipeline work removes. Neither edition here "
                        "condenses that way, which is a fact about two "
                        "publishers, not about the floor."},
    n=sum(a["n_records"] for a in L["humancost"]["arms"]), n_unit="staff records",
    pct_of_achievable=round(pct_err(
        sum(a["human_cost_records"] for a in L["humancost"]["arms"])
        / sum(a["n_records"] for a in L["humancost"]["arms"]), 0.0), 2),
    era_key="identity-harness|2026-09-07|1571 committed records|2 arms|"
            "clef-regime MIXED",
    comparable_as={"time_series": "identity-harness|human-cost|identity-axis|"
                                  "2 committed arms",
                   "head_to_head": None},
    summability_class="human_cost_rate", pool_key=None,
    mandatory_caption="Staff NAMING only. The reviewer's larger load — "
                      "note-level diffs — has no harness at all, so this is not "
                      "a measure of how much review a score needs.",
    scoreable=True,
    source="benchmarks/omr-pipeline-audit-2026-09/human-cost-identity.json",
    companions={"human_cost_records": sum(a["human_cost_records"]
                                          for a in L["humancost"]["arms"]),
                "n_records": sum(a["n_records"] for a in L["humancost"]["arms"]),
                "decomposition": {
                    k: sum(a["decomposition"][k] for a in L["humancost"]["arms"])
                    for k in ("unnamed", "impossible", "not_in_this_work",
                              "contradicted")}},
    flags=["⚠️⚠️ IDENTITY AXIS ONLY. This scores staff NAMING. The reviewer's "
           "larger load is note-level diffs and has no harness at all, so a high "
           "number here must never be read as 'review is nearly free'. Rendering "
           "it beside `scan:omr_ned` without that caption would be the most "
           "misleading pairing on the board.",
           "2 of the harness's 59 arms are exported, which is why this is 46 of "
           "1,571 while FINDINGS reports 197 of 3,543 — a COVERAGE gap, not a "
           "schema gap (round 2 called it a schema gap and was wrong).",
           "58 of 59 arms are clef-blind REPLAYS and one is a transcription; a "
           "cost figure that mixes regimes is not one figure (backlog F)"]))

# ───────────────────────────────────────────────────────────────────── assemble
# ── schema self-checks. Both FAIL the build rather than warn: a registry that
# can be built with a droppable caption is a registry whose rule is advisory.
#
# ⚠️ An unscoreable row MAY carry a caption. The first version of this check
# refused that, which was wrong — an unscoreable row still RENDERS (as an
# explicit "unscoreable — <reason>"), so its scope can still mislead.
_bad = [r["id"] for r in rows
        if r.get("mandatory_caption") is not None
        and not str(r["mandatory_caption"]).strip()]
if _bad:
    raise SystemExit("mandatory_caption is set but empty on: %s" % _bad)

# A ONE-SIDED HEAD-TO-HEAD IS WORSE THAN NONE: it looks satisfied, the pair has
# one member, and a renderer that groups on the key finds nothing and falls back
# to something weaker. This defect survived two review rounds because nothing
# checked it — it was found only by reading a rendered page. Now the build
# refuses it.
_h2h = {}
for r in rows:
    k = (r.get("comparable_as") or {}).get("head_to_head")
    if k:
        _h2h.setdefault(k, []).append(r["id"])
_lonely = {k: v for k, v in _h2h.items() if len(v) < 2}
if _lonely:
    raise SystemExit(
        "one-sided head_to_head key(s) — a comparison needs two sides: %s\n"
        "  Either add the counterpart row or drop the key. A key with one "
        "member is not a weaker comparison, it is a false claim that one "
        "exists." % _lonely)

# THE EDITION CLAUSE. A ceiling measured on one edition is a claim about that
# edition; the publisher has to ride the mechanism a renderer cannot drop.
_missing = []
for r in rows:
    ed = (r.get("ceiling") or {}).get("edition")
    if not ed:
        continue
    house = str(ed).split(",")[0].split("&")[0].strip()
    cap = str(r.get("mandatory_caption") or "")
    if house and house not in cap:
        _missing.append((r["id"], house))
if _missing:
    raise SystemExit(
        "ceiling.edition is set but the edition is not named in "
        "mandatory_caption on: %s\n"
        "  A single-edition ceiling must carry its publisher on the caption "
        "mechanism, not only in `ceiling.edition` — see rules."
        "mandatory_caption.edition_clause." % _missing)

scoreable = [r for r in rows if r["scoreable"]]
doc = {
    "schema_version": "0.4.0",
    #: ⚠️ WHAT A CONSUMER MUST GATE ON. A renderer written against 0.2.0 read
    #: 0.3.0 without a word and silently dropped `mandatory_caption` and
    #: `ceiling.edition` — the two fields whose entire purpose is that they
    #: cannot be dropped. Declare the versions understood, refuse anything else
    #: with a non-zero exit naming the version, and never forward-compat
    #: silently: an unknown minor may have added a field that MUST be shown.
    "consumer_contract": {
        "current": "0.4.0",
        "understood_by_a_conforming_consumer": ["0.4.0"],
        "superseded": {
            "0.3.0": "added `mandatory_caption` + `rules.mandatory_caption` and "
                     "`ceiling.edition`; a 0.2.0 consumer drops both silently",
            "0.2.0": "added `comparable_as`; a 0.1.0 consumer cannot tell a "
                     "head-to-head from a delta",
        },
        "must_fail_loudly_on": "any schema_version not in "
                               "`understood_by_a_conforming_consumer`",
        "fields_a_consumer_may_never_drop": [
            "mandatory_caption", "ceiling.edition (via the edition clause)",
        ],
    },
    "generated_by": "benchmarks/omr-pipeline-audit-2026-09/probe/build_metric_registry.py",
    "round": 5,
    "changes_since_0_3_0": [
        "FIXED: the one-sided head-to-head keys. `engraved:omr_ned` carried a "
        "key and `competitive:engraved:audiveris` carried NONE, so the pair had "
        "one member and a renderer fell back to grouping on `ceiling.kind == "
        "competitive` — which filed a pre-registered admission bar under a "
        "heading reading 'different system'. Both keys are now declared once, "
        "as H2H_ENGRAVED / H2H_SCAN, so the two sides cannot drift apart.",
        "ADDED `scan:omr_ned:same_10_rows_as_audiveris` — our own side of the "
        "scan head-to-head. Pairing Audiveris's 10 rows against our 20-row "
        "headline would have been a false comparison across row sets.",
        "FIXED: `prefill:precision:blind_out_of_sample` was `ceiling.kind = "
        "competitive`. It is a bar a human set in advance, not another system; "
        "the new kind is `decision_rule`.",
        "ADDED the EDITION CLAUSE: a row whose `ceiling.edition` is set must "
        "name that edition in its `mandatory_caption`, enforced at build time. "
        "A renderer built against 0.2.0 printed `Breitkopf` zero times because "
        "`ceiling.edition` was a field it did not read.",
        "RELAXED the caption self-check: an UNSCOREABLE row may carry a "
        "mandatory_caption. It still renders, so its scope can still mislead.",
        "ADDED `consumer_contract` so a version gate has something to gate on.",
    ],
    "changes_since_0_2_0": [
        "human review cost — the project's PURPOSE — is on the board: 46 of "
        "1,571 records, 97.07% of achievable. Round 2's 'irreproducible' "
        "verdict is WITHDRAWN: score.py derives `impossible`/`not-in-this-work` "
        "from corpus.py, which is committed, and work/page/emitted are all on "
        "the record. The fields were absent; the information was not.",
        "the hairpin `input` ceiling has a VALUE (bar recall 0.80, n=5) and the "
        "matched comparison round 2 never made: ZERO hairpin detections in "
        "10,523 on the same three pages a human swept",
        "every probe that globs now takes OMR_FIXTURE_ROOT and exits non-zero "
        "on an empty glob, per the verifier's endorsed fix",
    ],
    "changes_since_0_1_0": [
        "the scan structural floor is MEASURED (probe_structural_floor.py) "
        "instead of estimated; it is a CONSTRAINED floor — the price of page "
        "fidelity — and every scan % is now '% of achievable under page "
        "fidelity'",
        "`comparability` replaces the single `era_key` equality test, which "
        "forbade the competitive comparison this registry prints (M2)",
        "the `input` ceiling is no longer wholly empty: bounded above for "
        "noteheads (<= 0.971) and REFUTED as an explanation for hairpins",
        "three omitted estates added — calibration (scoreable:false, no "
        "defensible worst case), the ledger-zone screen/defect pair, and "
        "pre-fill precision against a PRE-REGISTERED ceiling",
    ],
    "_comment": "PROPOSAL, not yet wired into anything. Every value is read from a "
                "committed artefact named in `source`. Nothing here changes "
                "pipeline behaviour.",
    "unit": {
        "name": "% of achievable",
        "range": [0, 100],
        "direction": "higher_is_better",
        "why": "Sean, 2026-09-07: today 1.000 means perfect in one table and "
               "catastrophic in the next. One unit, one direction, every row.",
    },
    "transforms": {
        "error": {"formula": "pct = 100 * (W - M) / (W - F)",
                  "inverse": "M = W - (pct/100) * (W - F)",
                  "W_for_omr_ned": 1.0,
                  "why_W_is_1": "OMR-NED of an empty prediction is "
                                "truth/(truth+0) = 1 exactly, so the metric has a "
                                "natural worst case and the span is well defined"},
        "rate": {"formula": "pct = 100 * V / C", "inverse": "V = C * pct / 100"},
    },
    "rules": {
        "independence_guard": "a ceiling may ONLY be derived from an artefact "
                              "independent of our own output — a truth file, a "
                              "render, an external engine. A ceiling inferred from "
                              "what we currently produce lets the pipeline grade "
                              "itself against its own limitations and reach 100 by "
                              "standing still.",
        "assumption_direction": "where a ceiling is unknown it is assumed at the "
                                "value that MINIMISES the score (F=0 for an error "
                                "metric, C=1 for a rate). A missing ceiling can "
                                "therefore never manufacture a high number. Such a "
                                "row is stamped status 'assumed'.",
        "mandatory_caption": {
            "_why": "⚠️ A ROW CAN BE INDIVIDUALLY CORRECT AND COLLECTIVELY "
                    "MISLEADING. `human:review_cost:identity` reads 97.07 and "
                    "`scan:omr_ned` reads 15.56, on one axis, in one unit, in "
                    "one table — and the first scores staff NAMING while the "
                    "second scores everything. A reader takes the pair to mean "
                    "'naming is nearly solved, reading is not'; what it "
                    "actually means is that one of them has a harness and the "
                    "reviewer's real load (note-level diffs) has none. No "
                    "amount of care in the renderer fixes that, because the "
                    "mistake is not made in the renderer.",
            "rule": "a row carrying a non-null `mandatory_caption` MUST be "
                    "rendered with that text visible beside the number — not in "
                    "a tooltip, not on hover, not behind a disclosure. A "
                    "renderer that cannot show it MUST NOT show the row.",
            "enforcement": "this is a SCHEMA constraint, not a rendering "
                           "convention. If the renderer can drop the caption "
                           "the schema is wrong, not the renderer — so a "
                           "consumer that omits captions should fail its own "
                           "build rather than degrade silently.",
            "when_to_set_it": "when the row's SCOPE is narrower than its "
                              "neighbours' and the unit hides the difference. "
                              "Not for ordinary caveats — those are `flags`.",
            "edition_clause": "⚠️ ANY row whose `ceiling.edition` is set MUST "
                              "name that edition inside its "
                              "`mandatory_caption`, and the build FAILS "
                              "otherwise. This exists because "
                              "`ceiling.edition` was added in 0.3.0 and the "
                              "renderer built against 0.2.0 simply did not read "
                              "it, so `Breitkopf` — which a standing reporting "
                              "rule says must accompany the hairpin ceiling "
                              "every time it is quoted — appeared ZERO times on "
                              "the rendered page and nothing said so. A fact "
                              "that must always travel with a number belongs on "
                              "the mechanism that cannot be dropped, not in a "
                              "field a consumer may not know about.",
        },
        "no_fabricated_100": "a row with no ceiling evidence AND no value gets "
                             "scoreable:false and renders as an explicit "
                             "'unscoreable — <reason>', never a number.",
        "pooling": "rows may be pooled only within one `pool_key`, and a pool is "
                   "recomputed FROM THE UNDERLYING COUNTS, never by averaging "
                   "percentages — a 3-bar excerpt and a 27-staff page must not "
                   "carry equal weight. A pool's trust is the MINIMUM of its "
                   "members' ceiling statuses.",
        "comparability": {
            "_why": "⚠️ CORRECTED IN ROUND 2. The round-1 rule was a single "
                    "`era_key` equality test, and it FORBADE the competitive "
                    "comparison this very registry prints: we and Audiveris are "
                    "different systems and so can never share an era key, yet on "
                    "the same fixtures through the same scorer we are exactly "
                    "comparable. Comparability is not one relation.",
            "time_series": "may difference only if `comparable_as.time_series` "
                           "is equal AND `ceiling.value` and `ceiling.evidence` "
                           "are equal AND the arm (which predictions) is the "
                           "same. This is the accuracy_record.check() shape and "
                           "it answers 'are we improving'.",
            "head_to_head": "may compare only if `comparable_as.head_to_head` is "
                            "equal — same fixtures, same scorer, same row set, "
                            "different SYSTEM. It answers 'are we better than "
                            "them' and says nothing about direction over time.",
            "neither": "a pair sharing neither key may not be put in one "
                       "sentence with an arrow between them.",
            "worked_example": "`engraved:omr_ned` and "
                              "`competitive:engraved:audiveris` share a "
                              "head_to_head key and no time_series key: 88.78 vs "
                              "87.48 is a valid head-to-head and NOT a delta. "
                              "`scan:omr_ned` and "
                              "`scan:omr_ned:page_fidelity_15rows` share "
                              "neither: different row sets and different "
                              "ceilings.",
        },
        "dilution_guard": "a delta on an error-rate metric is REFUSED as an "
                          "improvement when the ratio falls while `companions."
                          "edits` rises — that is under-prediction being rewarded "
                          "by a symmetric metric, not recognition. Live example in "
                          "MEASUREMENT_SYSTEM.md §A6.",
        "noise_floor": "a delta smaller than the row's own measured noise floor is "
                       "reported as 'within noise', not as a direction. A row whose "
                       "noise floor is unmeasured may not carry a delta at all.",
    },
    "ceiling_kinds": {
        "structural": "the truth encodes what the page does not print",
        "render": "the fixture carries ink no reader could have read, or lost ink "
                  "it should have",
        "visibility": "the harness cannot see the stage — a ceiling of ZERO "
                      "INFORMATION, not of 100%",
        "input": "the ink is genuinely gone",
        "competitive": "best external system, our fixtures, our scorer. ⚠️ This "
                       "kind means ANOTHER SYSTEM and nothing else. Grouping a "
                       "head-to-head on `ceiling.kind` instead of on "
                       "`comparable_as.head_to_head` is what filed a "
                       "pre-registered admission bar under a heading reading "
                       "\"different system\" — group on the key, never on the kind.",
        "decision_rule": "a bar somebody set IN ADVANCE for accepting the output "
                         "without review — not a physical limit and not another "
                         "system. The right ceiling kind for anything gated on "
                         "human trust, and the only pre-registered one here.",
        "assumed": "no evidence; set by the assumption-direction rule",
    },
    "coverage": {
        "n_rows": len(rows),
        "n_scoreable": len(scoreable),
        "n_unscoreable": len(rows) - len(scoreable),
        "by_ceiling_status": {},
    },
    "rows": rows,
}
for r in rows:
    k = (r["ceiling"] or {}).get("status") or "none"
    doc["coverage"]["by_ceiling_status"][k] = \
        doc["coverage"]["by_ceiling_status"].get(k, 0) + 1

OUT.write_text(json.dumps(doc, indent=1) + "\n")
print("wrote %s — %d rows, %d scoreable, %d unscoreable"
      % (OUT.relative_to(ROOT), len(rows), len(scoreable), len(rows) - len(scoreable)))
print(json.dumps(doc["coverage"]["by_ceiling_status"], indent=1))
print()
for r in rows:
    if r["scoreable"]:
        print("  %-52s %6.2f%%  ceiling=%-24s n=%s"
              % (r["id"], r["pct_of_achievable"],
                 "%s/%s" % ((r["ceiling"] or {}).get("kind"),
                            (r["ceiling"] or {}).get("status")), r["n"]))
print()
for r in rows:
    if not r["scoreable"]:
        print("  %-52s UNSCOREABLE (%s)" % (r["id"], (r["ceiling"] or {}).get("kind")))
