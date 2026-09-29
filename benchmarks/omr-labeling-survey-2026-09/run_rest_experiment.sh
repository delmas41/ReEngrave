#!/usr/bin/env bash
# The rest-specialist collapse experiment (Sean, 2026-09-29) -- see
# REST_SPECIALIST_EXPERIMENT.md for the design and the decision table this
# feeds. Runs entirely on THIS Mac (M1 Max, MPS), unattended, nohup'd.
#
# Arms, each trained with round 6's own recipe (run_specialist_sweep.sh's
# `specialist()`, freeze=22 head-only, 5 epochs, imgsz 896, batch 16, device
# mps, save_period 1 -- frz only: round 6's OWN rests-family collapse table
# ("rests (e0, frz) | rest8th 12 -> 0, restQuarter 7 -> 0") was measured with
# frz, so frz is what "reproduce round 6" means for this family; frz also
# isolates label-quality from feature-drift, which is exactly what arms
# A vs B/C are trying to discriminate):
#
#   A  baseline   -- round 6's own rests corpus, minus the held-out eval cells.
#                    Must collapse, or the rig itself differs from round 6.
#   B  completed  -- A's cells + every high-confidence, non-FP-mode unmatched
#                    teacher rest detection added as a label.
#   C  painted    -- A's cells/labels unchanged, every unmatched teacher rest
#                    region painted to paper color (neither label nor
#                    background).
#   D  hollow     -- positive control, unmodified (data/specialist-hollow, same
#                    as round 5/6). Must survive, or the rig is broken.
#   E  oversampled -- B's corpus, rest-positive cells oversampled x4 in TRAIN
#                    (rehearsal FINDINGS.md's "optimization dynamics, not the
#                    labels" reading motivates this arm specifically).
#
# Usage: nohup ./run_rest_experiment.sh > rest_experiment.log 2>&1 &
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SURVEY="benchmarks/omr-labeling-survey-2026-09"
PROD_W="omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"
CLASSES="tools/omr/training/deepscoresv2_208_classes.json"
DEVICE="mps"
export PYTHONPATH="$(pwd):$PYTHONPATH:$SURVEY"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "===== STEP 0: held-out split + truth ====="
if [ ! -f "$SURVEY/held_out_rests.json" ]; then
  python3 "$SURVEY/build_rest_experiment_corpora.py" --select-held-out --n-held-out 35
else
  log "held_out_rests.json exists, skipping selection"
fi
if [ ! -f "$SURVEY/held_out_truth.json" ]; then
  python3 "$SURVEY/build_held_out_truth.py"
else
  log "held_out_truth.json exists, skipping"
fi

log "===== STEP 1: build corpora A/B/C (D reuses the existing hollow corpus) ====="
for arm in baseline:A-baseline completed:B-completed painted:C-painted; do
  key="${arm%%:*}"; dir="${arm##*:}"
  out="data/rest-exp-$dir"
  if [ ! -d "$out" ]; then
    log "building $key -> $out"
    python3 "$SURVEY/build_rest_experiment_corpora.py" --arm "$key" --out "$out" --device "$DEVICE" \
      || { log "!! FATAL: corpus build failed for $key -- cannot proceed without it"; exit 1; }
  else
    log "$out exists, skipping"
  fi
done
if [ ! -d data/specialist-hollow ]; then
  python3 "$SURVEY/build_specialist_versions.py" --family hollow --out data/specialist-hollow
fi

log "===== STEP 1b: visual-check sheet #1 (Sean, 2026-09-29) -- B additions + C paint-outs ====="
mkdir -p "$SURVEY/out/rest-experiment"
python3 "$SURVEY/crop_visual_check_corpora.py" || log "!! visual-check sheet #1 failed (non-fatal)"

build_catalog () {   # $1 = data root, $2 = catalog dir
  local SRC="$1" ROOT="$2"
  local VERSIONS
  VERSIONS="$(grep -v '^#' "$SRC/catalog-versions.txt" | grep -v '^$' | tr '\n' ' ')"
  rm -rf "$ROOT"; mkdir -p "$ROOT"
  for v in $VERSIONS; do ln -sfn "$(pwd)/$SRC/$v" "$ROOT/$v"; done
  python3 -m tools.omr.training.build_catalog_yaml \
      --root "$ROOT" --versions $VERSIONS --fallback-class-names "$CLASSES"
}

log "===== STEP 2: catalogs ====="
build_catalog data/rest-exp-A-baseline  cat-rest-exp-A
build_catalog data/rest-exp-B-completed cat-rest-exp-B
build_catalog data/rest-exp-C-painted   cat-rest-exp-C
build_catalog data/specialist-hollow    cat-rest-exp-D
build_catalog data/rest-exp-B-completed cat-rest-exp-E
python3 "$SURVEY/oversample_positive_cells.py" --catalog cat-rest-exp-E/catalog.yaml --factor 4

log "===== STEP 3: train (freeze=22, 5 epochs, imgsz 896, batch 16, device $DEVICE) ====="
train () {   # $1=name $2=catalog.yaml
  if find runs -path "*$1*/weights/epoch4.pt" 2>/dev/null | grep -q .; then
    log "$1 already has epoch4.pt, skipping (delete runs/$1 to force a re-run)"
    return
  fi
  log "training $1 ..."
  python3 -m tools.omr.training.train_yolo \
    --data "$2" --weights "$PROD_W" --epochs 5 --imgsz 896 --batch 16 \
    --device "$DEVICE" --patience 99 --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0 \
    --extra-kwargs '{"save_period": 1, "freeze": 22}' --project runs --name "$1" \
    || log "!! TRAINING FAILED for $1 -- continuing with the remaining arms"
  log "$1 done (or failed -- see above)"
}
train rest-exp-A cat-rest-exp-A/catalog.yaml
train rest-exp-B cat-rest-exp-B/catalog.yaml
train rest-exp-C cat-rest-exp-C/catalog.yaml
train rest-exp-D cat-rest-exp-D/catalog.yaml
train rest-exp-E cat-rest-exp-E/catalog-4xpos.yaml

log "===== STEP 4: strip optimizer state ====="
python3 - <<'PYSTRIP'
import glob
from ultralytics.utils.torch_utils import strip_optimizer
for f in sorted(glob.glob("runs/**/weights/epoch*.pt", recursive=True)):
    try: strip_optimizer(f)
    except Exception as exc: print("strip failed", f, exc)
PYSTRIP

find_ckpt () {   # $1 = arm name, $2 = epoch file (epoch0.pt .. epoch4.pt)
  find runs -path "*$1*/weights/$2" 2>/dev/null | head -1
}

log "===== STEP 5: per-epoch rest eval (A/B/C/E) ====="
for arm in A B C E; do
  for ep in epoch0 epoch1 epoch2 epoch3 epoch4; do
    ck="$(find_ckpt "rest-exp-$arm" "$ep.pt")"
    if [ -n "$ck" ]; then
      log "eval $arm $ep -> $ck"
      python3 "$SURVEY/eval_rest_arm.py" --weights "$ck" --tag "$arm-$ep" --device "$DEVICE" || log "!! eval failed for $arm $ep"
      if [ "$ep" = "epoch0" ]; then
        log "visual-check sheet #2 for $arm-$ep"
        python3 "$SURVEY/crop_arm_predictions.py" --weights "$ck" --tag "rest-exp-$arm-$ep" --device "$DEVICE" \
          || log "!! sheet #2 failed for $arm $ep (non-fatal)"
      fi
    fi
  done
done

log "===== STEP 6: composability graft + gate-lite (epoch0 of each arm) ====="
mkdir -p "$SURVEY/out/rest-experiment"
for pair in "A=rests" "B=rests" "C=rests" "E=rests" "D=hollow"; do
  arm="${pair%%=*}"; fam="${pair##*=}"
  ck="$(find_ckpt "rest-exp-$arm" "epoch0.pt")"
  [ -z "$ck" ] && { log "!! no epoch0 checkpoint for $arm, skipping graft"; continue; }
  composite="$SURVEY/out/rest-experiment/composite-$arm.pt"
  log "grafting $fam from $arm epoch0 onto production -> $composite"
  PROD="$(pwd)/$PROD_W" "$SURVEY/compose_specialists.sh" "$composite" "$fam=$ck" \
      > "$SURVEY/out/rest-experiment/graft-$arm.log" 2>&1 || log "!! graft failed for $arm"
  if [ "$fam" = "rests" ] && [ -f "$composite" ]; then
    python3 "$SURVEY/eval_rest_arm.py" --weights "$composite" --tag "$arm-composite" --device "$DEVICE" \
      || log "!! composite eval failed for $arm"
  fi
done

log "===== STEP 7: composability screen -- non-family classes must be IDENTICAL to production ====="
CKPTS=""
for arm in A B C D E; do
  c="$SURVEY/out/rest-experiment/composite-$arm.pt"
  [ -f "$c" ] && CKPTS="$CKPTS $arm-composite=$c"
done
if [ -n "$CKPTS" ]; then
  (python3 "$SURVEY/probe_class_inventory.py" --baseline "prod=$PROD_W" --ckpts $CKPTS \
      --device "$DEVICE" --out "$SURVEY/out/rest-experiment/composability_screen.json" \
      | tee "$SURVEY/out/rest-experiment/composability_screen.txt") || log "!! composability screen failed (non-fatal)"
fi

log "===== DONE. Read benchmarks/omr-labeling-survey-2026-09/rest_experiment_results.json ====="
log "     and benchmarks/omr-labeling-survey-2026-09/out/rest-experiment/composability_screen.txt"
