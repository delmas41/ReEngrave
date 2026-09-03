"""Merge Sean's hollow verdicts + the audited completion detections into
schema-v2 verdict files, and emit a combined manifest, for ONE v8 version.

  merged verdict = { added_detections: Sean's hollow (unchanged),
                     detections: [TP for each completion candidate] }

verdicts_to_yolo_labels then emits hollow (added) + black-notehead/dot (TP).
"""
import json, glob, os
from pathlib import Path

SURVEY = "benchmarks/omr-labeling-survey-2026-09"
MERGED = Path(SURVEY, "v8-merged-verdicts")
MERGED.mkdir(parents=True, exist_ok=True)
combined_manifest = []

n_cells = n_hollow = n_comp = 0
for b in sorted(glob.glob("benchmarks/omr-labeling-hollow2-2026-09-*")):
    manifest = {e["cell_id"]: e for e in json.load(open(os.path.join(b, "cells.json")))}
    for vf in sorted(glob.glob(os.path.join(b, "verdicts", "*.verdict.json"))):
        v = json.load(open(vf))
        hollow = v.get("added_detections", [])
        if not hollow:
            continue
        cid = v["cell_id"]
        cand_path = os.path.join(b, "completion", "candidates", f"{cid}.json")
        comp = json.load(open(cand_path))["candidates"] if os.path.exists(cand_path) else []
        detections = []
        for i, c in enumerate(comp):
            detections.append({
                "id": f"C{i}",
                "verdict": "TP",
                "model_predicted_class": c["smufl_name"],
                "model_bbox": c["bbox"],
            })
        merged = {
            "cell_id": cid,
            "schema_version": 2,
            "detections": detections,          # completion (black noteheads + dots)
            "added_detections": hollow,        # Sean's hollow noteheads
        }
        (MERGED / f"{cid}.verdict.json").write_text(json.dumps(merged, indent=2))
        combined_manifest.append(manifest[cid])
        n_cells += 1
        n_hollow += len(hollow)
        n_comp += len(detections)

Path(SURVEY, "v8-combined-cells.json").write_text(json.dumps(combined_manifest, indent=2))
print(f"merged {n_cells} cells: {n_hollow} hollow + {n_comp} completion = {n_hollow+n_comp} boxes")
print(f"wrote {MERGED}/ and {SURVEY}/v8-combined-cells.json")
