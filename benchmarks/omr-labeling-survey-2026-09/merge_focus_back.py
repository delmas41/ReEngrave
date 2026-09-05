"""Merge a pooled focus batch's verdicts back to the batches the cells came from.

A focus batch (`omr-labeling-marks-focus-2026-09`, `omr-labeling-clefs-2026-09`)
gathers cells from several batches so one server covers a whole sweep. The
cells are COPIES; the batch each came from is the human record, and the
converter reads that. So the sweep has to be written home.

Additive by construction, because a campaign sweeps the same cells many times
and an earlier pass's boxes must survive a later one:
  * added_detections are merged by (class, bbox) identity — a box already home
    is not duplicated, and a box only at home is never dropped;
  * inspected_passes is unioned;
  * nothing else in the home verdict is touched.

    python3 .../merge_focus_back.py --focus benchmarks/omr-labeling-marks-focus-2026-09 [--write]
"""
from __future__ import annotations
import argparse, json, os
from pathlib import Path

def key(b):
    bb = b.get("bbox") or {}
    return (b.get("human_class"), bb.get("x"), bb.get("y"), bb.get("w"), bb.get("h"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--focus", required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    focus = Path(a.focus)
    origin = json.loads((focus / "origin.json").read_text())
    added = passes = touched = skipped = 0
    for cid, o in sorted(origin.items()):
        fp = focus / "verdicts" / f"{cid}.verdict.json"
        hp = Path(o["batch"]) / "verdicts" / f"{cid}.verdict.json"
        if not fp.exists():
            skipped += 1; continue
        fv = json.loads(fp.read_text())
        if not hp.exists():
            print(f"  !! no home verdict for {cid} at {hp}"); skipped += 1; continue
        hv = json.loads(hp.read_text())
        home = list(hv.get("added_detections") or [])
        have = {key(b) for b in home}
        new = [b for b in (fv.get("added_detections") or []) if key(b) not in have]
        hp_passes = list(hv.get("inspected_passes") or [])
        new_passes = [p for p in (fv.get("inspected_passes") or []) if p not in hp_passes]
        if not new and not new_passes:
            continue
        hv["added_detections"] = home + new
        hv["inspected_passes"] = hp_passes + new_passes
        added += len(new); passes += len(new_passes); touched += 1
        if a.write:
            hp.write_text(json.dumps(hv, indent=1))
    verb = "wrote" if a.write else "would write"
    print(f"{verb}: {touched} home verdicts · +{added} boxes · +{passes} pass stamps"
          f" · {skipped} skipped")
    if not a.write:
        print("dry run — pass --write to apply")

if __name__ == "__main__":
    main()
