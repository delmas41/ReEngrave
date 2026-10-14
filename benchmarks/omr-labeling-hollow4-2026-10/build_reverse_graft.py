"""ROADMAP 2.4b re-assembly: REVERSE graft = the fine-tune's everything, PRODUCTION's class rows put back.
 arm A = restore only the measured-damaged classes (>10% box-count drop vs production on Litolff p1 or Brahms p0, base >= 3 boxes,
         from ab/class-counts-raw.json (raw fine-tune records)) + the plan's named set (beam, ledgerLine, augmentationDot, timeSig*, flag*, stem*)
 arm B = restore EVERY class except the taught hollow heads (idx 28-39: Half/Whole/DoubleWhole x OnLine/InSpace x {,Small})
 usage: build_reverse_graft.py --ft last.pt --label withv24 [--counts-key rawft]
Uses merge_class_head.py unchanged: --export-rows from PRODUCTION (--keep names), --import-rows onto the FINE-TUNE as --base; its
self-check proves every other tensor is bit-identical to the fine-tune."""
import argparse, json, subprocess, sys
from pathlib import Path
R = Path.cwd(); MC = R / "benchmarks/omr-labeling-survey-2026-09/merge_class_head.py"
names = json.loads((R / "tools/omr/training/deepscoresv2_208_classes.json").read_text())
PROD = R / "omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
HOLLOW_IDX = set(range(28, 40)); hollow_names = {names[i] for i in HOLLOW_IDX}
ap = argparse.ArgumentParser(); ap.add_argument("--ft", required=True); ap.add_argument("--label", required=True)
ap.add_argument("--counts-key", required=True); a = ap.parse_args()
cc = json.loads((R / "benchmarks/omr-labeling-hollow4-2026-10/ab/class-counts-raw.json").read_text())
base, ft = cc["production"], cc[a.counts_key]
damaged = set()
for pg in ("lit", "bra"):
    for k, b in base[pg].items():
        if b >= 3 and (b - ft[pg].get(k, 0)) / b > 0.10: damaged.add(k)
named = {n for n in names if n.startswith(("beam", "ledgerLine", "augmentationDot", "timeSig", "flag", "stem"))}
A = (damaged | named) - hollow_names
B = set(names) - hollow_names
for lab, S in (("A", A), ("B", B)):
    rows = R / f"runs/2.4b/revgraft-{a.label}-{lab}-prodrows.npz"
    out = R / f"omr-weights/candidates/hollow4-2.4b-REVERSE-{a.label}-arm{lab}-2026-10-13.pt"
    keep = sorted(S)
    r = subprocess.run([sys.executable, str(MC), "--ft", str(PROD), "--base", str(PROD), "--out", "/dev/null", "--export-rows", str(rows), "--keep", *keep], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    r = subprocess.run([sys.executable, str(MC), "--base", a.ft, "--import-rows", str(rows), "--out", str(out)], capture_output=True, text=True)
    print(f"arm {lab} ({a.label}): restores {len(keep)} names; ->", out.name); print(r.stdout[-400:], r.stderr[-300:])
    if lab == "A": print("  damaged-set:", sorted(damaged), "\n  named:", sorted(named))
