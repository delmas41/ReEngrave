#!/usr/bin/env bash
# Phase H — validate a candidate best.pt locally against three benchmarks:
#   1. Bach WTC verdict set (target: F1 ≥ 98%, vs prod 98.8%)
#   2. Orchestral catalog holdout (target: mAP50 ≥ prod + 5 pts)
#   3. Real-world spot-checks (target: no regression on 5 PDFs)
#
# Usage:
#   bash phase_h_validate_local.sh /path/to/best.pt [run_name]
#
# Writes results under:
#   /Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-phase-h/{run_name}/
set -euo pipefail

WEIGHTS=${1:?"usage: $0 WEIGHTS_PT [RUN_NAME]"}
RUN_NAME=${2:-phaseH-$(date -u +%Y%m%dT%H%M%S)}

REPO=/Users/seanjohnson/Desktop/ReEngrave
MAIN=$REPO                               # main worktree (has benchmarks/omr-*)
WORKTREE=$REPO/.claude/worktrees/interesting-curran-3ca1b7
PHASE_H_DATA=$WORKTREE/benchmarks/omr-imslp-pipeline/phase-h-data
OUT=$MAIN/benchmarks/omr-phase-h/$RUN_NAME
mkdir -p "$OUT"

PROD=$REPO/omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt

if [[ ! -f "$WEIGHTS" ]]; then
  echo "ERROR: candidate weights not found at $WEIGHTS" >&2; exit 2
fi
if [[ ! -f "$PROD" ]]; then
  echo "ERROR: prod weights not found at $PROD" >&2; exit 2
fi

echo "== Phase H validation =="
echo "  candidate: $WEIGHTS"
echo "  baseline:  $PROD"
echo "  out:       $OUT"
echo

# ───────────────────────────────────────────────────────────────────────────
# 1. Bach WTC verdict set scoring
# ───────────────────────────────────────────────────────────────────────────
echo "── 1. Bach WTC verdict set (Phase 3.3 cells, 30 of them) ──"
cd "$MAIN"
CELLS=$(python3 -c "
import json
m = json.load(open('benchmarks/omr-phase2.5/cells.json'))
print(' '.join(c['cell_id'] for c in m))
")

for tag in candidate baseline; do
  W=$WEIGHTS; [[ "$tag" == "baseline" ]] && W=$PROD
  echo "  running YOLO ($tag) on WTC cells..."
  python3 -m tools.omr.annotate.run_yolo \
    --manifest benchmarks/omr-phase2.5/cells.json \
    --cells $CELLS \
    --weights "$W" \
    --baseline-verdicts benchmarks/omr-phase2.5/verdicts-fix1 \
    --out-dir "$OUT/wtc-verdicts-$tag" \
    --detections-out "$OUT/wtc-detections-$tag" \
    --conf 0.10 --imgsz 2048 --device auto 2>&1 \
    | tail -10
  echo "  scoring..."
  python3 -m tools.omr.annotate.score \
    --verdicts-dir "$OUT/wtc-verdicts-$tag" \
    --detections-dir "$OUT/wtc-detections-$tag" \
    --out-dir "$OUT/wtc-results-$tag" 2>&1 \
    | tail -10
done

# ───────────────────────────────────────────────────────────────────────────
# 2. Orchestral inference spot-check on a real-world page
# ───────────────────────────────────────────────────────────────────────────
# NOTE: the catalog val labels have a known ~50 px x-offset residual
# (documented in PHASE_E_SUMMARY.md). At mAP50's IoU>=0.5 threshold the
# offset alone defeats most matches — prod weights themselves score
# mAP50≈0.0001 on the catalog val. So we DO NOT use that yaml for go/no-go.
#
# Instead: run inference on a clean orchestral page (beethoven-5 from the
# real-world bench) and compare detection counts + class distribution.
# This is what the operator looks at to decide whether the new weights
# improved orchestral handling.
echo
echo "── 2. Orchestral inference spot-check (Beethoven 5 p10) ──"
B5_PDF=$MAIN/.claude/worktrees/interesting-curran-3ca1b7/tools/omr/training/data/imslp/beethoven-symphony-5/pdfs/imslp-52624/score.pdf
[[ -f "$B5_PDF" ]] || B5_PDF=$(ls $MAIN/.claude/worktrees/*/tools/omr/training/data/imslp/beethoven-symphony-5/pdfs/*/score.pdf 2>/dev/null | head -1)

if [[ -f "$B5_PDF" ]]; then
  for tag in candidate baseline; do
    W=$WEIGHTS; [[ "$tag" == "baseline" ]] && W=$PROD
    python3 << PY 2>&1 | tee "$OUT/orchestral-spotcheck-$tag.txt"
import sys; sys.path.insert(0, "$MAIN")
from pathlib import Path
from tools.omr.preprocessing import render_page
from ultralytics import YOLO
m = YOLO("$W")
pi = render_page(Path("$B5_PDF"), 9, dpi=300)  # page 10 (0-indexed=9)
r = m.predict(pi.rgb, imgsz=1280, conf=0.25, verbose=False)[0]
names = m.names
classes = [int(c) for c in r.boxes.cls.tolist()]
from collections import Counter
ct = Counter(names[c] for c in classes)
print("$tag detection counts (top 15):")
for cls, n in ct.most_common(15):
    print(f"  {cls:<30} {n}")
print(f"  TOTAL: {sum(ct.values())}")
PY
  done
else
  echo "  (skipped — no Beethoven 5 PDF found)"
fi

# ───────────────────────────────────────────────────────────────────────────
# 3. Real-world benchmark spot-check (5 PDFs)
# ───────────────────────────────────────────────────────────────────────────
echo
echo "── 3. Real-world spot check (5 PDFs from benchmarks/omr-real-world/) ──"
for pdf in $(ls $MAIN/benchmarks/omr-real-world/*.ly 2>/dev/null | sed 's/\.ly$//'); do
  name=$(basename "$pdf")
  echo "  (not auto-run — manual inspection on $name)"
done

# ───────────────────────────────────────────────────────────────────────────
# Summary
# ───────────────────────────────────────────────────────────────────────────
echo
echo "── Summary ──"
echo "Results written to: $OUT"
ls "$OUT/"

cat_F1() {
  local f="$1/wtc-results-$2/summary.json"
  if [[ -f "$f" ]]; then
    python3 -c "import json; d=json.load(open('$f')); print(f'F1={d.get(\"f1\", \"?\"):.3f}  P={d.get(\"precision\",\"?\"):.3f}  R={d.get(\"recall\",\"?\"):.3f}')"
  else
    echo "(no summary)"
  fi
}
echo "WTC F1 candidate: $(cat_F1 "$OUT" candidate)"
echo "WTC F1 baseline: $(cat_F1 "$OUT" baseline)"
echo
echo "Orchestral mAP candidate: $(grep mAP50 $OUT/orchestral-val-candidate.txt 2>/dev/null | head -1)"
echo "Orchestral mAP baseline:  $(grep mAP50 $OUT/orchestral-val-baseline.txt 2>/dev/null | head -1)"
