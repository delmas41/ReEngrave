"""Port template-matcher verdicts onto YOLO detections so the existing
scorer can grade YOLO on the same human-annotated ground truth.

This is the cross-engine cousin of `port_user_verdicts.py`. Both implement
the same matching loop ("for each old verdict, find the closest new
detection of the same category within PROXIMITY_PX"). The difference:

  port_user_verdicts.py   — same engine (TM), different bbox set (regen).
                            Suppressed-by-matcher orphans are dropped.
  port_verdicts_to_yolo   — different engine (TM → YOLO). Orphans become
                            FN candidates for YOLO recall.

For each cell with hand-annotated TM verdicts:
  1. Load TM verdicts (.verdict.json) and TM detections (.json) so we
     have x/y/w/h/category for each verdicted detection.
  2. Load YOLO detections.
  3. For each TM verdict, find the closest unused YOLO detection of the
     same category within PROXIMITY_PX. Match → YOLO det inherits the
     verdict. No match → orphan.
       - TM verdict was TP: orphan is logged as a YOLO FN (TM said
         there's a real symbol here; YOLO didn't find it).
       - TM verdict was FP: orphan is dropped (YOLO correctly didn't
         hallucinate something that wasn't real).
  4. YOLO detections with no matching TM verdict stay pending — they
     fall outside the ground-truth subset we can score.
  5. Write a phase3.1/verdicts-yolo/<cid>.verdict.json compatible with
     `tools.omr.annotate.score`. FNs go in fn_noteheads so the scorer's
     recall calc picks them up (the field is mis-named — it's used for
     any-category misses here).

CLI:
    python3 -m tools.omr.annotate.port_verdicts_to_yolo \\
        --tm-verdicts-dir benchmarks/omr-phase2.5/verdicts \\
        --tm-detections-dir benchmarks/omr-phase2.5/detections \\
        --yolo-detections-dir benchmarks/omr-phase3/r2/detections \\
        --out-dir benchmarks/omr-phase3.1/verdicts-yolo \\
        --report benchmarks/omr-phase3.1/port_report.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


PROXIMITY_PX = 30  # canonical coords


def _load_detections(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("detections", [])


def _build_tm_rows(
    tm_dets: list[dict],
    tm_verdicts: list[dict],
) -> list[dict]:
    """Returns one row per TM detection that has a filled verdict.
    Pulls coords/category from the detections file (the verdict file
    only carries id + smufl_name + verdict). Pending/unsure are skipped.
    """
    vmap = {v["detection_id"]: v for v in tm_verdicts}
    rows: list[dict] = []
    for d in tm_dets:
        v = vmap.get(d["id"])
        if not v:
            continue
        raw = (v.get("verdict") or "").strip().upper()
        if raw not in {"TP", "FP"}:
            continue
        rows.append({
            "tm_id": d["id"],
            "x": d.get("x", 0),
            "y": d.get("y", 0),
            "w": d.get("w", 0),
            "h": d.get("h", 0),
            "x_center": d.get("x_center", d.get("x", 0) + d.get("w", 0) / 2),
            "y_center": d.get("y_center", d.get("y", 0) + d.get("h", 0) / 2),
            "category": d.get("category", ""),
            "tm_smufl_name": d.get("smufl_name", ""),
            "verdict": raw,
            "wrong_pitch": v.get("wrong_pitch"),
            "actual_label": v.get("actual_label"),
        })
    return rows


def _nearest_yolo(
    tm_row: dict,
    yolo_dets: list[dict],
    used: set[str],
) -> tuple[dict | None, float | None]:
    cx_tm = tm_row["x_center"]
    cy_tm = tm_row["y_center"]
    best = None
    best_d = math.inf
    for yd in yolo_dets:
        if yd["id"] in used:
            continue
        if yd.get("category", "") != tm_row["category"]:
            continue
        cx = yd.get("x_center", yd.get("x", 0) + yd.get("w", 0) / 2)
        cy = yd.get("y_center", yd.get("y", 0) + yd.get("h", 0) / 2)
        d = math.hypot(cx - cx_tm, cy - cy_tm)
        if d < best_d and d <= PROXIMITY_PX:
            best = yd
            best_d = d
    return best, (best_d if best is not None else None)


def port_cell(
    cell_id: str,
    tm_verdicts_dir: Path,
    tm_dets_dir: Path,
    yolo_dets_dir: Path,
    out_dir: Path,
) -> dict:
    tm_v_path = tm_verdicts_dir / f"{cell_id}.verdict.json"
    tm_d_path = tm_dets_dir / f"{cell_id}.json"
    y_d_path = yolo_dets_dir / f"{cell_id}.json"

    if not tm_v_path.exists():
        return {"cell_id": cell_id, "status": "no-tm-verdict"}
    if not tm_d_path.exists():
        return {"cell_id": cell_id, "status": "no-tm-detections"}
    if not y_d_path.exists():
        return {"cell_id": cell_id, "status": "no-yolo-detections"}

    tm_dets = _load_detections(tm_d_path)
    yolo_dets = _load_detections(y_d_path)
    tm_state = json.loads(tm_v_path.read_text())
    tm_verdicts = tm_state.get("verdicts", [])

    tm_rows = _build_tm_rows(tm_dets, tm_verdicts)
    if not tm_rows:
        return {"cell_id": cell_id, "status": "no-filled-tm-verdicts"}

    # Initialize all YOLO detections as pending.
    yolo_verdict_state = {
        "cell_id": cell_id,
        "verdicts": [
            {
                "detection_id": d["id"],
                "smufl_name": d.get("smufl_name", ""),
                "verdict": "",
            }
            for d in yolo_dets
        ],
        "fn_noteheads": [],
    }
    yvmap = {v["detection_id"]: v for v in yolo_verdict_state["verdicts"]}

    used: set[str] = set()
    n_ported_tp = n_ported_fp = 0
    n_orphan_tp = n_orphan_fp = 0
    per_cat = {}  # cat → {ported_tp, ported_fp, orphan_tp, orphan_fp}
    matched_pairs = []  # for the audit report
    orphan_tps = []     # for fn_noteheads + audit
    orphan_fps = []     # audit only

    for row in tm_rows:
        cat = row["category"] or "unknown"
        bucket = per_cat.setdefault(
            cat, {"ported_tp": 0, "ported_fp": 0, "orphan_tp": 0, "orphan_fp": 0}
        )
        match, dist = _nearest_yolo(row, yolo_dets, used)
        if match is None:
            if row["verdict"] == "TP":
                n_orphan_tp += 1
                bucket["orphan_tp"] += 1
                orphan_tps.append({
                    "tm_id": row["tm_id"],
                    "category": cat,
                    "tm_smufl_name": row["tm_smufl_name"],
                    "x_canonical": int(row["x_center"]),
                    "y_canonical": int(row["y_center"]),
                })
            else:
                n_orphan_fp += 1
                bucket["orphan_fp"] += 1
                orphan_fps.append({
                    "tm_id": row["tm_id"],
                    "category": cat,
                    "tm_smufl_name": row["tm_smufl_name"],
                    "x_canonical": int(row["x_center"]),
                    "y_canonical": int(row["y_center"]),
                })
            continue
        used.add(match["id"])
        v_entry = yvmap[match["id"]]
        v_entry["verdict"] = row["verdict"]
        if row.get("wrong_pitch"):
            v_entry["wrong_pitch"] = row["wrong_pitch"]
        if row.get("actual_label"):
            v_entry["actual_label"] = row["actual_label"]
        if row["verdict"] == "TP":
            n_ported_tp += 1
            bucket["ported_tp"] += 1
        else:
            n_ported_fp += 1
            bucket["ported_fp"] += 1
        matched_pairs.append({
            "tm_id": row["tm_id"],
            "yolo_id": match["id"],
            "category": cat,
            "tm_smufl_name": row["tm_smufl_name"],
            "yolo_smufl_name": match.get("smufl_name", ""),
            "verdict": row["verdict"],
            "distance_px": round(dist, 2) if dist is not None else None,
        })

    # Orphan TM-TPs are YOLO false negatives. Park them in fn_noteheads so
    # the scorer's recall denominator picks them up. (The scorer's name
    # field is unfortunate — it counts everything in this block, not just
    # noteheads.)
    yolo_verdict_state["fn_noteheads"] = orphan_tps

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{cell_id}.verdict.json").write_text(
        json.dumps(yolo_verdict_state, indent=2)
    )

    return {
        "cell_id": cell_id,
        "status": "ported",
        "n_tm_filled": len(tm_rows),
        "n_yolo_detections": len(yolo_dets),
        "n_ported_tp": n_ported_tp,
        "n_ported_fp": n_ported_fp,
        "n_orphan_tp_fn_for_yolo": n_orphan_tp,
        "n_orphan_fp_dropped": n_orphan_fp,
        "n_yolo_pending_unverdicted": sum(
            1 for v in yolo_verdict_state["verdicts"] if not v["verdict"]
        ),
        "per_category": per_cat,
        "matched_pairs": matched_pairs,
        "orphan_tps": orphan_tps,
        "orphan_fps": orphan_fps,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tm-verdicts-dir", default="benchmarks/omr-phase2.5/verdicts")
    ap.add_argument("--tm-detections-dir", default="benchmarks/omr-phase2.5/detections")
    ap.add_argument("--yolo-detections-dir",
                    default="benchmarks/omr-phase3/r2/detections")
    ap.add_argument("--out-dir", default="benchmarks/omr-phase3.1/verdicts-yolo")
    ap.add_argument("--report", default="benchmarks/omr-phase3.1/port_report.json")
    args = ap.parse_args()

    tm_v = Path(args.tm_verdicts_dir)
    tm_d = Path(args.tm_detections_dir)
    y_d = Path(args.yolo_detections_dir)
    out = Path(args.out_dir)

    # Discover cells from TM verdict files.
    candidates: set[str] = {
        p.name.removesuffix(".verdict.json")
        for p in tm_v.glob("*.verdict.json")
    }

    all_reports = []
    print(f"porting {len(candidates)} cells from {tm_v} → YOLO ({y_d})")
    for cid in sorted(candidates):
        r = port_cell(cid, tm_v, tm_d, y_d, out)
        all_reports.append(r)
        if r["status"] == "ported":
            print(
                f"  {cid}: tm_filled={r['n_tm_filled']:>3}  "
                f"ported_tp={r['n_ported_tp']:>3}  ported_fp={r['n_ported_fp']:>2}  "
                f"orphan_tp(=YOLO_FN)={r['n_orphan_tp_fn_for_yolo']:>3}  "
                f"orphan_fp(dropped)={r['n_orphan_fp_dropped']:>2}  "
                f"yolo_pending={r['n_yolo_pending_unverdicted']:>3}"
            )
        else:
            print(f"  {cid}: {r['status']}")

    # Aggregate.
    agg = {
        "n_cells": sum(1 for r in all_reports if r["status"] == "ported"),
        "n_tm_filled_total": sum(r.get("n_tm_filled", 0) for r in all_reports),
        "n_ported_tp": sum(r.get("n_ported_tp", 0) for r in all_reports),
        "n_ported_fp": sum(r.get("n_ported_fp", 0) for r in all_reports),
        "n_orphan_tp_fn_for_yolo": sum(
            r.get("n_orphan_tp_fn_for_yolo", 0) for r in all_reports
        ),
        "n_orphan_fp_dropped": sum(
            r.get("n_orphan_fp_dropped", 0) for r in all_reports
        ),
    }

    per_cat_agg: dict[str, dict] = {}
    for r in all_reports:
        for cat, c in r.get("per_category", {}).items():
            ag = per_cat_agg.setdefault(
                cat, {"ported_tp": 0, "ported_fp": 0, "orphan_tp": 0, "orphan_fp": 0}
            )
            for k, v in c.items():
                ag[k] += v
    agg["per_category"] = per_cat_agg

    rpt_path = Path(args.report)
    rpt_path.parent.mkdir(parents=True, exist_ok=True)
    rpt_path.write_text(json.dumps(
        {"aggregate": agg, "per_cell": all_reports}, indent=2
    ))
    print(f"\nwrote {rpt_path}")
    print(f"\naggregate:")
    print(f"  tm_filled_total = {agg['n_tm_filled_total']}")
    print(f"  ported_tp       = {agg['n_ported_tp']} "
          f"(YOLO confirmed real symbols at TM locations)")
    print(f"  ported_fp       = {agg['n_ported_fp']} "
          f"(YOLO replicated a TM mistake — also a YOLO FP)")
    print(f"  orphan_tp       = {agg['n_orphan_tp_fn_for_yolo']} "
          f"(TM said real, YOLO didn't find it → YOLO FN)")
    print(f"  orphan_fp       = {agg['n_orphan_fp_dropped']} "
          f"(TM mistake YOLO didn't repeat — YOLO win, not counted)")


if __name__ == "__main__":
    main()
