"""Merge the COMPLETED cells into new versions — v13+, never mutating v7-v11.

Round 3 of the campaign. Each exported cell now carries, in one place:

  added_detections (HUMAN)   hollow noteheads (rounds 1-2)
                           + rests and accidentals (round 3)
                           + clefs (the 24-cell pooled pass)
  detections (MODEL, audited) black noteheads + augmentation dots (rounds 1-2)
                           + dynamics, slurs and ties (round 3, complete_marks.py)

⚠️ THIS WRITES NEW VERSIONS AND NEVER RE-RUNS THE CONVERTER OVER AN EXISTING ONE.
Re-running `verdicts_to_yolo_labels` to "heal" a version is a measured
data-loss footgun: the converter copies each cell's PNG from the batch's
gitignored `cells/` dir, and for v8 111 of 122 are gone from the main checkout,
so a re-run silently writes an 11-cell version over the 122-cell one AND EXITS
0. New version numbers sidestep the whole class of problem, and admitting them
is a separate, reviewable edit to catalog-versions.txt.

The prior model completions live in three different places, because three
different rounds put them there, and this is the one script that has to know:

  hollow3 batches   <batch>/completion/candidates/<cell>.json
  hollow2 (v8)      survey/v8-merged-verdicts/<cell>.verdict.json  -> .detections
  v7                <batch>/verdicts-merged/<cell>.verdict.json    -> .detections

⚠️ build_v8.py is NOT reused for the hollow2 batches even though it built their
merge, because it would pull the later Brahms completion-sweep boxes into the
result. The committed v8-merged-verdicts is read as a frozen artifact instead.

    python3 .../build_phase3_versions.py            # dry run
    python3 .../build_phase3_versions.py --write
"""
from __future__ import annotations
import argparse, json, glob, os, collections
from pathlib import Path

SURVEY = Path("benchmarks/omr-labeling-survey-2026-09")
OUT = SURVEY / "phase3-merged"

# batch -> (short tag, where its PRIOR model completions live)
BATCHES = {
    "benchmarks/omr-labeling-hollow-2026-08":
        ("v7-beet5-bolero", "merged:benchmarks/omr-labeling-hollow-2026-08/verdicts-merged"),
    "benchmarks/omr-labeling-hollow2-2026-09-litolff-hires":
        ("litolff", f"merged:{SURVEY}/v8-merged-verdicts"),
    "benchmarks/omr-labeling-hollow2-2026-09-peters-mahler5":
        ("peters", f"merged:{SURVEY}/v8-merged-verdicts"),
    "benchmarks/omr-labeling-hollow2-2026-09-eulenburg-scheherazade":
        ("eulenburg", f"merged:{SURVEY}/v8-merged-verdicts"),
    "benchmarks/omr-labeling-hollow2-2026-09-simrock-dvorak9":
        ("simrock", f"merged:{SURVEY}/v8-merged-verdicts"),
    "benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1":
        ("breitkopf", f"merged:{SURVEY}/v8-merged-verdicts"),
    "benchmarks/omr-labeling-hollow3-2026-09-universal-mahler1":
        ("mahler1", "cand:benchmarks/omr-labeling-hollow3-2026-09-universal-mahler1/completion/candidates"),
    "benchmarks/omr-labeling-hollow3-2026-09-novello-elgar1":
        ("elgar1", "cand:benchmarks/omr-labeling-hollow3-2026-09-novello-elgar1/completion/candidates"),
    "benchmarks/omr-labeling-hollow3-2026-09-durand-lamer":
        ("lamer", "cand:benchmarks/omr-labeling-hollow3-2026-09-durand-lamer/completion/candidates"),
}
# Tchaikovsky 1 (v12) is deliberately absent: the cloud ablation measured it
# HALVING the half-note gain — its low-res cells complete to zero black
# noteheads, so the blur defeats the detector. Defer low-res to its own method.

def _det_from_cand(rec):
    """A completion candidate -> a decided TP detection, the v8/v9-v12 shape."""
    out = []
    for i, c in enumerate(rec.get("candidates") or []):
        out.append({
            "id": c.get("id") or f"C{i}",
            "smufl_name": c["smufl_name"],
            "category": c.get("category"),
            "bbox": c["bbox"],
            "verdict": "TP",
            "confidence": c.get("confidence"),
            "notes": c.get("notes") or "model completion, audited",
        })
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    grand = collections.Counter()
    rows = []
    for batch, (tag, src) in BATCHES.items():
        mp = Path(batch, "cells.json")
        if not mp.exists():
            print(f"  !! no manifest: {batch}"); continue
        man = {e["cell_id"]: e for e in json.loads(mp.read_text())}
        kind, loc = src.split(":", 1)
        vdir = OUT / tag / "verdicts"
        if a.write: vdir.mkdir(parents=True, exist_ok=True)
        combined = []
        n_cell = n_hum = n_prior = n_marks = 0
        for cid, e in sorted(man.items()):
            vp = Path(batch, "verdicts", f"{cid}.verdict.json")
            if not vp.exists(): continue
            human = list((json.loads(vp.read_text()).get("added_detections") or []))
            # prior model completions
            prior = []
            if kind == "cand":
                p = Path(loc, f"{cid}.json")
                if p.exists(): prior = _det_from_cand(json.loads(p.read_text()))
            else:
                p = Path(loc, f"{cid}.verdict.json")
                if p.exists(): prior = list(json.loads(p.read_text()).get("detections") or [])
            # this round's marks
            mp2 = Path(batch, "marks-completion", "candidates", f"{cid}.json")
            marks = _det_from_cand(json.loads(mp2.read_text())) if mp2.exists() else []
            for m in marks: m["notes"] = "marks completion (dynamics/slurs/ties), audited"
            if not human and not prior and not marks:
                continue                       # nothing to train on; emits no label anyway
            if a.write:
                (vdir / f"{cid}.verdict.json").write_text(json.dumps({
                    "cell_id": cid, "schema_version": 2,
                    "detections": prior + marks, "added_detections": human}, indent=1))
            combined.append(e)
            n_cell += 1; n_hum += len(human); n_prior += len(prior); n_marks += len(marks)
        if a.write and combined:
            (OUT / tag / f"{tag}-cells.json").write_text(json.dumps(combined, indent=1))
        rows.append((tag, n_cell, n_hum, n_prior, n_marks))
        grand["cells"] += n_cell; grand["human"] += n_hum
        grand["prior"] += n_prior; grand["marks"] += n_marks
    print(f"{'tag':18s} {'cells':>6} {'human':>7} {'prior':>7} {'marks':>7} {'boxes':>7}")
    print("-" * 60)
    for t, c, h, p, m in rows:
        print(f"{t:18s} {c:6d} {h:7d} {p:7d} {m:7d} {h+p+m:7d}")
    print("-" * 60)
    print(f"{'TOTAL':18s} {grand['cells']:6d} {grand['human']:7d} {grand['prior']:7d} "
          f"{grand['marks']:7d} {grand['human']+grand['prior']+grand['marks']:7d}")
    print("\nwrote " + str(OUT) if a.write else "\ndry run — pass --write to apply")

if __name__ == "__main__":
    main()
