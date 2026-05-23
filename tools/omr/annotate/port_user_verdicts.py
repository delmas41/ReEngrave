"""Port user verdicts from .verdict.json (and pre-filled .md) onto a new
detection set, after the matcher has been regenerated.

For each detection in the OLD detection set:
  - if it has a verdict (either from user JSON or pre-filled MD)
  - find the closest NEW detection (same category, within PROXIMITY_PX)
  - if found: assign the old verdict to the new D-ID
  - if not found: the old detection has been suppressed by matcher improvements
    (e.g., a Phase 2.6+ filter removed it). The verdict is dropped — its
    implicit meaning ("FP") is now realized by the detection simply being
    absent.

Detections in the NEW set with no matching OLD entry are left empty (to be
reviewed in the web UI).

CLI:
    python3 -m tools.omr.annotate.port_user_verdicts \
        --backup-dir benchmarks/omr-phase2.5/verdicts-backup-pre-regen-<...> \
        --new-detections-dir benchmarks/omr-phase2.5/detections \
        --out-dir benchmarks/omr-phase2.5/verdicts
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .score import parse_verdict_markdown


PROXIMITY_PX = 30  # canonical coords


def _load_new_detections(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("detections", [])


def _classify(verdict_text: str) -> str:
    v = verdict_text.lower().split()[0] if verdict_text else ""
    if v in {"tp", "true", "correct"}:
        return "TP"
    if v in {"fp", "false", "wrong"}:
        return "FP"
    if v in {"wrong_pitch", "wrong-pitch", "wrongpitch"}:
        return "WP"  # internal: a TP with wrong pitch
    if v in {"unsure", "skip", "?", "??"}:
        return "unsure"
    return ""


def _build_old_index(old_dets: list[dict], old_verdicts: list[dict]) -> list[dict]:
    """Return a list of detection-row dicts for old detections that have a
    non-empty verdict. Preserves wrong_pitch and actual_label so the FP
    confusion table survives regenerations."""
    out = []
    vmap = {v["detection_id"]: v for v in old_verdicts}
    for d in old_dets:
        v = vmap.get(d["id"])
        if not v or not v.get("verdict"):
            continue
        out.append({
            "x": d.get("x", 0),
            "y": d.get("y", 0),
            "w": d.get("w", 0),
            "h": d.get("h", 0),
            "category": d.get("category", ""),
            "smufl_name": d.get("smufl_name", ""),
            "verdict": v.get("verdict"),
            "wrong_pitch": v.get("wrong_pitch"),
            "actual_label": v.get("actual_label"),
        })
    return out


def _bootstrap_from_md(md_text: str, old_dets: list[dict]) -> list[dict]:
    """When the old verdict format was Markdown (the 3 pre-filled cells),
    parse it and bootstrap an old-style verdict-row list."""
    parsed = parse_verdict_markdown(md_text)
    md_by_id = {d.id: d for d in parsed.detections}
    rows = []
    vmap_synth = []
    for d in old_dets:
        md_det = md_by_id.get(d["id"])
        if md_det is None or not md_det.verdict:
            continue
        cls = md_det.classification
        if cls == "pending":
            continue
        if cls == "tp":
            v = "TP"
        elif cls == "fp":
            v = "FP"
        elif cls == "wrong_pitch":
            v = "TP"
        else:
            v = ""
        wp = parsed.wrong_pitch_corrections.get(d["id"])
        if not v:
            continue
        vmap_synth.append({
            "x": d.get("x", 0),
            "y": d.get("y", 0),
            "w": d.get("w", 0),
            "h": d.get("h", 0),
            "category": d.get("category", ""),
            "smufl_name": d.get("smufl_name", ""),
            "verdict": v,
            "wrong_pitch": wp,
            "actual_label": None,  # markdown format never had this field
        })
    return vmap_synth


def _nearest_new(old_row: dict, new_dets: list[dict], used: set[str]) -> dict | None:
    """Find the closest unused new detection of the same category, within
    PROXIMITY_PX of the old detection's center."""
    cx_old = old_row["x"] + old_row["w"] / 2
    cy_old = old_row["y"] + old_row["h"] / 2
    best = None
    best_d = math.inf
    for nd in new_dets:
        if nd["id"] in used:
            continue
        if nd.get("category", "") != old_row["category"]:
            continue
        cx = nd.get("x", 0) + nd.get("w", 0) / 2
        cy = nd.get("y", 0) + nd.get("h", 0) / 2
        dx = cx - cx_old
        dy = cy - cy_old
        d = math.hypot(dx, dy)
        if d < best_d and d <= PROXIMITY_PX:
            best = nd
            best_d = d
    return best


def port_cell(
    cell_id: str,
    backup_dir: Path,
    new_dets_dir: Path,
    out_dir: Path,
) -> dict:
    """Returns a small report dict for this cell."""
    new_path = new_dets_dir / f"{cell_id}.json"
    if not new_path.exists():
        return {"cell_id": cell_id, "status": "no-new-detections"}
    new_dets = _load_new_detections(new_path)

    # Find old source. Prefer .verdict.json; fall back to .md.
    json_backup = backup_dir / f"{cell_id}.verdict.json"
    md_backup = backup_dir / f"{cell_id}.md"
    old_dets_backup = backup_dir / "old-detections" / f"{cell_id}.json"

    if not old_dets_backup.exists():
        return {"cell_id": cell_id, "status": "no-old-detections-backup"}
    old_dets = _load_new_detections(old_dets_backup)

    if json_backup.exists():
        old_state = json.loads(json_backup.read_text())
        old_rows = _build_old_index(old_dets, old_state.get("verdicts", []))
        fn_noteheads = old_state.get("fn_noteheads", [])
        source = "json"
    elif md_backup.exists():
        old_rows = _bootstrap_from_md(md_backup.read_text(), old_dets)
        fn_noteheads = []
        source = "md"
    else:
        return {"cell_id": cell_id, "status": "no-old-verdicts"}

    if not old_rows:
        return {"cell_id": cell_id, "status": "no-filled-verdicts"}

    # Build new verdict state. Initialize all new detections as pending.
    new_state = {
        "cell_id": cell_id,
        "verdicts": [
            {
                "detection_id": d["id"],
                "smufl_name": d.get("smufl_name", ""),
                "verdict": "",
            }
            for d in new_dets
        ],
        "fn_noteheads": fn_noteheads,
    }
    verdicts_by_id = {v["detection_id"]: v for v in new_state["verdicts"]}

    # Port each old row to its closest new detection.
    used: set[str] = set()
    n_ported = 0
    n_orphan = 0
    for row in old_rows:
        match = _nearest_new(row, new_dets, used)
        if match is None:
            n_orphan += 1
            continue
        used.add(match["id"])
        v = verdicts_by_id[match["id"]]
        v["verdict"] = row["verdict"]
        if row.get("wrong_pitch"):
            v["wrong_pitch"] = row["wrong_pitch"]
        if row.get("actual_label"):
            v["actual_label"] = row["actual_label"]
        n_ported += 1

    # Persist.
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{cell_id}.verdict.json"
    out_path.write_text(json.dumps(new_state, indent=2))

    return {
        "cell_id": cell_id,
        "status": "ported",
        "source": source,
        "n_old_filled": len(old_rows),
        "n_new_detections": len(new_dets),
        "n_ported": n_ported,
        "n_orphan_suppressed_by_matcher": n_orphan,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Port user verdicts to new detection set")
    ap.add_argument("--backup-dir", required=True,
                    help="Backup dir with old .verdict.json and .md files + old-detections/")
    ap.add_argument("--new-detections-dir", default="benchmarks/omr-phase2.5/detections")
    ap.add_argument("--out-dir", default="benchmarks/omr-phase2.5/verdicts")
    args = ap.parse_args()

    backup = Path(args.backup_dir)
    new_d = Path(args.new_detections_dir)
    out = Path(args.out_dir)

    # Discover which cells have backups.
    candidates: set[str] = set()
    for p in backup.glob("*.verdict.json"):
        candidates.add(p.stem.replace(".verdict", ""))
    for p in backup.glob("*.md"):
        candidates.add(p.stem)

    print(f"porting {len(candidates)} cells from {backup}")
    for cid in sorted(candidates):
        report = port_cell(cid, backup, new_d, out)
        print(f"  {cid}: {report}")


if __name__ == "__main__":
    main()
