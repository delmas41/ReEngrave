#!/usr/bin/env python3
"""Partition-level scoring of the live grouping rule against gt/gt.json.

Verdict vocabulary (adapted from
benchmarks/omr-system-grouping-2026-08/legato_crosscheck.py `classify()`,
extended with a `mixed` tier and a count-only branch for GT that has no
partition, per the build brief):

  staff_count_mismatch  predicted total staves != GT n_staves (GT has one).
                         Reported separately — this is a DETECTION confound,
                         never scored as a grouping error.
  agree                 GT has a partition (staves_per_system or
                         break_indices) and the predicted break-index set is
                         identical.
  we_merge               we lack >=1 break GT has, and add none GT lacks.
  we_split                we add >=1 break GT lacks, and lack none GT has.
  boundary_moved         exactly one break relocated (one missing + one
                         extra) — same rough shape, drawn one gap over.
  mixed                  more than one break disagrees on each side, or an
                         unequal number — a materially different partition,
                         not just a shifted boundary.
  count_agree/count_differ   GT has only a system COUNT (no partition):
                         predicted n_systems compared directly.
  error                  the page could not be rendered/detected, or a GT
                         break index doesn't fit today's detected staff count.
  no_gt                  reserved for callers that iterate pages without GT
                         (this script's own GT-driven loop never emits it).

Inputs: gt/gt.json (required) + a sweep JSONL (optional — only consulted for
a GT row whose `dpi` is null; every row imported by import_gt.py today has a
pinned dpi, so this script mostly runs the pipeline directly, per the build
brief: "it can run the pipeline directly for GT cases whose dpi is pinned").

Usage:
    python3 score.py [--gt gt/gt.json] [--sweep sweep.jsonl]
                      [--out-verdicts verdicts.jsonl] [--out-rollup ROLLUP.md]
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE_ROOT = HERE.parents[1]
sys.path.insert(0, str(WORKTREE_ROOT))
sys.path.insert(0, str(HERE))

import fitz  # noqa: E402

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402

import sweep as sweep_mod  # noqa: E402  (reuse compute_render_params + LIBRARY_ROOT)

DEFAULT_GT = HERE / "gt" / "gt.json"
DEFAULT_SWEEP = HERE / "sweep.jsonl"
DEFAULT_VERDICTS = HERE / "verdicts.jsonl"
DEFAULT_ROLLUP = HERE / "SCORE_ROLLUP.md"

VERDICT_ORDER = ["agree", "count_agree", "boundary_moved", "we_merge", "we_split",
                 "mixed", "count_differ", "staff_count_mismatch", "error", "no_gt"]

# ─── Publisher-token lookup for GT rows (many live OUTSIDE library/editions —
# the pre-library Gradus-Assets originals eval_grouping.py/fulldist.py/
# phase1-baseline still point at). Joined by IMSLP id extracted from the
# path, against every sidecar in the library — NOT hardcoded guesses. ───────

IMSLP_ID_RE = re.compile(r"imslp-?(\d+)", re.IGNORECASE)


def build_imslp_index():
    index = {}
    for json_path in sweep_mod.LIBRARY_ROOT.rglob("*.json"):
        try:
            d = json.loads(json_path.read_text())
        except Exception:
            continue
        iid = d.get("imslp_id")
        if iid:
            index[str(iid)] = {
                "publisher": d.get("publisher") or None,
                "publisher_token": d.get("variant") or None,
                "year": d.get("publisher_year") or None,
            }
    return index


def provenance_for_gt_pdf(pdf: str, imslp_index: dict):
    m = IMSLP_ID_RE.search(pdf)
    if m and m.group(1) in imslp_index:
        return imslp_index[m.group(1)]
    if "mahler_5" in pdf.lower():
        # Matches the catalog id already used for this file elsewhere in the
        # repo (corpus-inventory.md: "unidentified-scan-2016--local.pdf");
        # not a new claim, just carrying the documented "publisher unknown"
        # fact through to the rollup label.
        return {"publisher": None, "publisher_token": "unknown-scan-2016", "year": None}
    return {"publisher": None, "publisher_token": "unknown", "year": None}


# ─── Partition <-> break-index-set helpers ───────────────────────────────────
# Break index i (0-based) = "there is a system boundary between staff i and
# staff i+1", matching sweep.py's `gaps[i]` indexing and fulldist.py's
# `enumerate(profile(...))` convention.


def breaks_from_sizes(sizes):
    breaks = set()
    cum = -1
    for size in sizes[:-1]:
        cum += size
        breaks.add(cum)
    return breaks


def sizes_from_breaks(breaks, n):
    sizes = []
    start = 0
    for i in range(n - 1):
        if i in breaks:
            sizes.append(i - start + 1)
            start = i + 1
    sizes.append(n - start)
    return sizes


def classify_partition(gt_breaks: set, pred_breaks: set) -> str:
    missing = gt_breaks - pred_breaks   # true break we failed to draw -> merge
    extra = pred_breaks - gt_breaks     # break we drew that isn't true -> split
    if not missing and not extra:
        return "agree"
    if missing and not extra:
        return "we_merge"
    if extra and not missing:
        return "we_split"
    if len(missing) == 1 and len(extra) == 1:
        return "boundary_moved"
    return "mixed"


# ─── Prediction ───────────────────────────────────────────────────────────────


def predict_fresh(pdf: str, page: int, dpi: int):
    pi = render_page(pdf, page, dpi=dpi)
    pws = detect_staves(pi)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    sizes = [len(list(g)) for _, g in itertools.groupby(staves, key=lambda s: s.system_index)]
    return {"error": None, "dpi": dpi, "n_staves": len(staves), "staves_per_system": sizes}


def get_prediction(gt_row: dict, sweep_index: dict):
    """{error, dpi, n_staves, staves_per_system} for this GT row's (pdf, page).

    `dpi` pinned (not null, true of every row import_gt.py produces today) ->
    run the pipeline directly at that dpi, per the build brief. `dpi` null ->
    prefer a cached sweep.jsonl row for (pdf, page); else fall back to
    computing the same normalized dpi sweep.py would (reusing its own
    function — not a re-implementation of the pipeline's rule, just this
    script's own render-parameter helper) and running fresh.
    """
    pdf, page, dpi = gt_row["pdf"], gt_row["page"], gt_row["dpi"]
    try:
        if dpi is not None:
            return predict_fresh(pdf, page, dpi)

        key = (str(Path(pdf).resolve()), page)
        row = sweep_index.get(key)
        if row is not None:
            if row.get("error"):
                return {"error": row["error"], "dpi": row["dpi"], "n_staves": None, "staves_per_system": None}
            return {"error": None, "dpi": row["dpi"], "n_staves": row["n_staves"],
                    "staves_per_system": row["staves_per_system"]}

        doc = fitz.open(pdf)
        try:
            rect = doc[page].rect
        finally:
            doc.close()
        fresh_dpi, _ = sweep_mod.compute_render_params(rect.width, rect.height)
        return predict_fresh(pdf, page, fresh_dpi)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}", "dpi": dpi, "n_staves": None, "staves_per_system": None}


def load_sweep_index(sweep_path: Path):
    """(resolved_abs_pdf_path, page) -> sweep row, for GT rows with dpi=null."""
    index = {}
    if not sweep_path.exists():
        return index
    with sweep_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            pdf_rel = row["pdf_rel"]
            abs_path = Path(pdf_rel) if Path(pdf_rel).is_absolute() else sweep_mod.LIBRARY_ROOT / pdf_rel
            try:
                key = (str(abs_path.resolve()), row["page"])
            except OSError:
                continue
            index[key] = row
    return index


# ─── Classification ───────────────────────────────────────────────────────────


def classify_case(gt: dict, pred: dict) -> tuple:
    """-> (verdict, detail dict)."""
    if pred["error"] is not None:
        return "error", {"detail": pred["error"]}

    pred_n = pred["n_staves"]
    pred_sizes = pred["staves_per_system"] or []
    pred_breaks = breaks_from_sizes(pred_sizes) if len(pred_sizes) >= 1 else set()

    if gt["n_staves"] is not None:
        if pred_n != gt["n_staves"]:
            return "staff_count_mismatch", {"gt_n_staves": gt["n_staves"], "pred_n_staves": pred_n}
        gt_breaks = breaks_from_sizes(gt["staves_per_system"])
        verdict = classify_partition(gt_breaks, pred_breaks)
        return verdict, {"gt_breaks": sorted(gt_breaks), "pred_breaks": sorted(pred_breaks),
                          "gt_sizes": gt["staves_per_system"], "pred_sizes": pred_sizes}

    if gt["break_indices"] is not None:
        gt_breaks = set(gt["break_indices"])
        if pred_n is None or pred_n < 1 or (gt_breaks and max(gt_breaks) > pred_n - 2):
            return "error", {"detail": f"GT break index out of range for today's detected staff "
                                        f"count (pred_n_staves={pred_n}, gt_breaks={sorted(gt_breaks)}); "
                                        f"detection may have drifted since this GT was adjudicated."}
        verdict = classify_partition(gt_breaks, pred_breaks)
        return verdict, {"gt_breaks": sorted(gt_breaks), "pred_breaks": sorted(pred_breaks),
                          "gt_n_systems_derived": len(gt_breaks) + 1, "pred_sizes": pred_sizes}

    # Count-only GT (eval_grouping.py rows).
    pred_n_systems = len(pred_sizes) if pred_sizes else 0
    verdict = "count_agree" if pred_n_systems == gt["n_systems"] else "count_differ"
    return verdict, {"gt_n_systems": gt["n_systems"], "pred_n_systems": pred_n_systems, "pred_sizes": pred_sizes}


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", type=Path, default=DEFAULT_GT)
    ap.add_argument("--sweep", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--out-verdicts", type=Path, default=DEFAULT_VERDICTS)
    ap.add_argument("--out-rollup", type=Path, default=DEFAULT_ROLLUP)
    args = ap.parse_args()

    gt_doc = json.loads(args.gt.read_text())
    cases = gt_doc["cases"]
    sweep_index = load_sweep_index(args.sweep)
    imslp_index = build_imslp_index()

    verdict_rows = []
    for gt in cases:
        prov = provenance_for_gt_pdf(gt["pdf"], imslp_index)
        pred = get_prediction(gt, sweep_index)
        verdict, detail = classify_case(gt, pred)
        verdict_rows.append({
            "case_id": gt["case_id"],
            "pdf": gt["pdf"],
            "page": gt["page"],
            "publisher_token": prov["publisher_token"],
            "publisher": prov["publisher"],
            "source": gt["source"],
            "verdict": verdict,
            "detail": detail,
            "pred_dpi": pred["dpi"],
            "gt_dpi": gt["dpi"],
        })

    args.out_verdicts.write_text("\n".join(json.dumps(r) for r in verdict_rows) + "\n")

    # ─ Rollup ─
    overall = {}
    for r in verdict_rows:
        overall[r["verdict"]] = overall.get(r["verdict"], 0) + 1

    by_pub = {}
    for r in verdict_rows:
        tok = r["publisher_token"] or "unknown"
        by_pub.setdefault(tok, {}).setdefault(r["verdict"], 0)
        by_pub[tok][r["verdict"]] += 1

    lines = []
    lines.append("# Score rollup — system-grouping GT vs live pipeline")
    lines.append("")
    lines.append(f"{len(cases)} GT cases scored (`{args.gt}`).")
    lines.append("")
    lines.append("## Overall, by verdict")
    lines.append("")
    lines.append("| verdict | count |")
    lines.append("|---|--:|")
    for v in VERDICT_ORDER:
        if overall.get(v):
            lines.append(f"| {v} | {overall[v]} |")
    for v, n in overall.items():
        if v not in VERDICT_ORDER:
            lines.append(f"| {v} | {n} |")
    lines.append("")
    lines.append("## By publisher_token")
    lines.append("")
    all_verdicts_seen = sorted({v for d in by_pub.values() for v in d}, key=lambda v: VERDICT_ORDER.index(v) if v in VERDICT_ORDER else 99)
    header = "| publisher_token | n | " + " | ".join(all_verdicts_seen) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (2 + len(all_verdicts_seen)))
    for tok in sorted(by_pub.keys()):
        d = by_pub[tok]
        n = sum(d.values())
        row = f"| {tok} | {n} | " + " | ".join(str(d.get(v, "")) for v in all_verdicts_seen) + " |"
        lines.append(row)
    lines.append("")

    errors = [r for r in verdict_rows if r["verdict"] == "error"]
    if errors:
        lines.append("## Errors")
        lines.append("")
        for r in errors:
            lines.append(f"- `{r['case_id']}`: {r['detail'].get('detail')}")
        lines.append("")

    args.out_rollup.write_text("\n".join(lines) + "\n")

    print(f"{len(cases)} cases scored")
    for v in VERDICT_ORDER:
        if overall.get(v):
            print(f"  {v:22s} {overall[v]}")
    print(f"wrote {args.out_verdicts}")
    print(f"wrote {args.out_rollup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
