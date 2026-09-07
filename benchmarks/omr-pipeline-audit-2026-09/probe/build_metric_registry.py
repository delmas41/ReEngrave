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
    "norm": ROOT / "benchmarks/omr-headline-validity-2026-09/results-normalised-arm.json",
    "noop": ROOT / "benchmarks/omr-headline-validity-2026-09/engraved-normalise-noop.json",
    "one2one": ROOT / "benchmarks/omr-headline-validity-2026-09/engraved-1to1.json",
    "indep": HERE / "ceiling-engine-independence.json",
    "aud_eng": ROOT / "benchmarks/omr-vs-industry-2026-09/results.json",
    "aud_scan": ROOT / "benchmarks/omr-vs-industry-2026-09/results-audiveris-scan.json",
    "hairpin": ROOT / "benchmarks/omr-hairpin-cv-2026-09/results-scored-pages.json",
    "content": ROOT / "docs/progress-dashboard.content.json",
    "pct": HERE / "pct-of-achievable-prototype.json",
}
L = {k: json.loads(v.read_text()) for k, v in A.items()}
REL = {k: str(v.relative_to(ROOT)) for k, v in A.items()}


def pct_err(m, f):
    return round(100.0 * (1.0 - m) / (1.0 - f), 2)


def pct_rate(v, c):
    return round(100.0 * v / c, 2)


def row(**kw):
    base = {
        "id": None, "stage": None, "family": None,
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
    noise_floor={"value": None, "status": "unmeasured",
                 "note": "no repeat-run determinism probe exists for "
                         "orchestral_eval; the ±6 figure is the SCAN harness's"},
    summability_class="omr_ned_engraved", pool_key="engraved/orchestral-e2e/11",
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
                        "The measured floor exists for only 5 of these 20 rows "
                        "(hand map + engine corroboration); on that subset the "
                        "measured floor is 0.152 and the score is %.1f%% instead "
                        "of %.1f%%."
                        % (L["pct"]["scan"]["pool"]["pct_of_achievable"],
                           L["pct"]["scan"]["pool"]["pct_naive_no_ceiling"])},
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
           "33.8% of the edits on the normalisable subset are structural charge "
           "for a printing convention, not recognition error"]))

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
    pct_of_achievable=L["pct"]["scan"]["pool"]["pct_of_achievable"],
    n=L["pct"]["scan"]["pool"]["n_rows"], n_unit="pages",
    era_key="scan-e2e|graft09-arm|5rows|ceiling-corroborated|transform1.1.0",
    noise_floor={"value_edits": 6, "status": "measured"},
    summability_class="omr_ned_scan_ceilinged",
    pool_key="scan/ceiling-corroborated/5",
    scoreable=True, source=REL["pct"],
    flags=["5 of 20 rows, 3 of 6 works — NOT the headline, and it may not be "
           "differenced against the 20-row figure (different arm AND different era)"]))

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
    summability_class="omr_ned_engraved", pool_key=None,
    scoreable=True, source=REL["aud_eng"],
    companions={"ours": pct_err(dt["pooled"], 0.0),
                "we_are_ahead_by_points": round(pct_err(dt["pooled"], 0.0)
                                                - pct_err(aud_ned, 0.0), 2)}))

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
    id="human:review_cost", stage="(the purpose)", family="both",
    raw_metric="staff records a human must look at",
    native_direction="lower_is_better", value=None,
    ceiling={"kind": None, "value": None, "status": "unmeasured", "evidence": [],
             "control": None},
    n=None, n_unit="staff records",
    era_key=None, scoreable=False,
    why_not="⚠️ THE THING SEAN BUILT THIS PROJECT TO REDUCE, AND IT IS NOT ON THE "
            "BOARD. It has been measured exactly once, as a side result: between "
            "two identity passes accuracy moved 44 records and review cost moved 2 "
            "(197 -> 195). It has no ceiling, no era key, no harness of its own, "
            "and no artefact this registry can read. See backlog D4.",
    source="benchmarks/omr-identity-harness-2026-09/FINDINGS.md"))

# ───────────────────────────────────────────────────────────────────── assemble
scoreable = [r for r in rows if r["scoreable"]]
doc = {
    "schema_version": "0.1.0",
    "generated_by": "benchmarks/omr-pipeline-audit-2026-09/probe/build_metric_registry.py",
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
        "no_fabricated_100": "a row with no ceiling evidence AND no value gets "
                             "scoreable:false and renders as an explicit "
                             "'unscoreable — <reason>', never a number.",
        "pooling": "rows may be pooled only within one `pool_key`, and a pool is "
                   "recomputed FROM THE UNDERLYING COUNTS, never by averaging "
                   "percentages — a 3-bar excerpt and a 27-staff page must not "
                   "carry equal weight. A pool's trust is the MINIMUM of its "
                   "members' ceiling statuses.",
        "cross_era_refusal": "two scores may be differenced only if their "
                             "`era_key` strings are equal AND their ceiling value "
                             "and evidence pointers are equal. Anything else is "
                             "refused, in the shape accuracy_record.check() "
                             "already has.",
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
        "competitive": "best external system, our fixtures, our scorer",
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
