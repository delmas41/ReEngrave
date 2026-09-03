"""Merge Sean's Phase-2 hollow verdicts + audited completion → schema-v2 merged
verdicts, PER BATCH, so each publisher/tradition becomes its own version.

  merged verdict = { added_detections: Sean's hollow (unchanged),
                     detections: [TP for each completion candidate] }

Writes, per batch, under <survey>/phase2-merged/<tag>/:
    verdicts/<cell>.verdict.json
    <tag>-cells.json                (combined manifest of the merged cells)

verdicts_to_yolo_labels then emits hollow (added) + black-notehead/dot (TP) for
each. Keeping the batches separate lets the ±Tchaikovsky ablation toggle just the
low-res version (v12) in the training mix.
"""
import json, glob, os
from pathlib import Path

SURVEY = "benchmarks/omr-labeling-survey-2026-09"
OUT = Path(SURVEY, "phase2-merged")
OUT.mkdir(parents=True, exist_ok=True)

# batch dir tag  ->  short tag used in output paths
BATCHES = {
    "benchmarks/omr-labeling-hollow3-2026-09-universal-mahler1": "mahler1",
    "benchmarks/omr-labeling-hollow3-2026-09-novello-elgar1": "elgar1",
    "benchmarks/omr-labeling-hollow3-2026-09-durand-lamer": "lamer",
    "benchmarks/omr-labeling-hollow3-2026-09-jurgenson-tchaikovsky1": "tchaikovsky1",
}

grand = {}
for b, tag in BATCHES.items():
    manifest = {e["cell_id"]: e for e in json.load(open(os.path.join(b, "cells.json")))}
    vdir = OUT / tag / "verdicts"
    vdir.mkdir(parents=True, exist_ok=True)
    combined = []
    n_cells = n_hollow = n_comp = 0
    for vf in sorted(glob.glob(os.path.join(b, "verdicts", "*.verdict.json"))):
        v = json.load(open(vf))
        hollow = v.get("added_detections", [])
        if not hollow:
            continue
        cid = v["cell_id"]
        cand_path = os.path.join(b, "completion", "candidates", f"{cid}.json")
        comp = json.load(open(cand_path))["candidates"] if os.path.exists(cand_path) else []
        detections = [{
            "id": f"C{i}", "verdict": "TP",
            "model_predicted_class": c["smufl_name"], "model_bbox": c["bbox"],
        } for i, c in enumerate(comp)]
        merged = {
            "cell_id": cid, "schema_version": 2,
            "detections": detections,       # completion (black noteheads + dots)
            "added_detections": hollow,     # Sean's hollow noteheads
        }
        (vdir / f"{cid}.verdict.json").write_text(json.dumps(merged, indent=2))
        combined.append(manifest[cid])
        n_cells += 1; n_hollow += len(hollow); n_comp += len(detections)
    Path(OUT / tag / f"{tag}-cells.json").write_text(json.dumps(combined, indent=2))
    grand[tag] = {"cells": n_cells, "hollow": n_hollow, "completion": n_comp}
    print(f"{tag:14s} cells={n_cells:3d}  hollow={n_hollow:3d}  completion={n_comp:3d}  total={n_hollow+n_comp:3d}")

tot_c = sum(g["cells"] for g in grand.values())
tot_h = sum(g["hollow"] for g in grand.values())
tot_k = sum(g["completion"] for g in grand.values())
print("=" * 70)
print(f"TOTAL cells={tot_c}  hollow={tot_h}  completion={tot_k}  boxes={tot_h+tot_k}")
Path(SURVEY, "phase2_merge_summary.json").write_text(json.dumps(grand, indent=2))
