#!/usr/bin/env bash
# Round 5 — a METHOD sweep, not a data sweep. Runs ON THE RENTED BOX.
#
# Rounds 3 and 4 established that the labels are not the blocker: completing
# them moved predicted symbols 3262 -> 3364 against production's 4350. Round 5
# step 1 then measured WHAT is lost (FORGETTING_2026-09-04.md): not confidence —
# every fine-tune's median confidence is HIGHER than production's — but whole
# class families at exactly zero. tie 249 -> 0, slur 184 -> 0, beam 188 -> 0,
# augmentationDot 150 -> 0, accidentalFlat 80 -> 0, ledgerLine 288 -> 14, while
# noteheads and dynamics — the two families the campaign swept — hold at
# 80-100%. So this sweep varies HOW the model is trained, and the two data arms
# in it are about the corpus's SILENCE rather than its content.
#
#   prod896    the production recipe (imgsz 896) on the ROUND-4 data, at the
#              ship's DENSE RATIO rather than its dense FACTOR. The 896 ship
#              oversampled 2x and got 70% dense / 30% hollow because it had 119
#              hollow cells; rounds 3-4 have 359, so 2x there is 43/57 and the
#              hollow cells are the MAJORITY — the density-prior narrowing that
#              collapsed dense noteheads 2506 -> 114 in the clef fine-tune. 6x
#              restores 69/31. This is the control the last session never ran
#              — 896 was queued behind 1408 when the box was destroyed — and
#              the only arm that isolates "same recipe, better labels".
#   plain2     no teacher at the 2x dense ratio — the MATCHED control for
#              `distill` and `rehearsal`, which run at 2x because the teacher
#              boxes are what they vary. Without it, "rehearsal at 2x" would
#              only ever be comparable to "no teacher at 6x", and the dense
#              ratio and the teacher would move together.
#   distill25  the ALL scope built at the teacher's conf 0.25 instead of 0.50 —
#              the pipeline's OWN operating threshold, so the student is asked
#              to reproduce what production actually emits rather than only its
#              confident half. 3417 teacher boxes against distill's 1423, and
#              it is the only arm that gets the never-labeled structural
#              classes to a real count (beam 450, ledgerLine 350, tie 336).
#              It also inherits the most false positives, which is the trade.
#   distill6 /  the two rehearsal scopes at the 6x ratio, so each also has a
#   rehearsal6  same-ratio partner among the plain arms.
#   dense6     the same 6x ratio for 5 epochs, no teacher. Separates "more of
#              the dense base" from "the teacher speaks", because v1 and v2
#              carry beam, ledgerLine, slur and tie boxes of their own and
#              oversampling them IS a rehearsal of a sort.
#   freeze     backbone frozen (freeze=10). Preserves the base's features by
#              construction; tests whether the drift is in the features.
#   lowlr      lr0=1e-5 held flat (lrf=1). optimizer=auto chose AdamW at
#              4.7e-05.
#   nowarmup   default LR, but warmup OFF. The arithmetic that makes this the
#              first suspect: one epoch of this corpus is ~31 optimizer steps
#              at batch 16, and 31 steps at 4.7e-05 cannot zero a class — yet
#              imgsz512 e1 already reads no ties, slurs or whole rests. What
#              CAN do it in 31 steps is ultralytics' warmup, which drives BIAS
#              parameters at `warmup_bias_lr` 0.1 for the first
#              `warmup_epochs` 3.0 — so a 1-5 epoch fine-tune is ENTIRELY
#              warmup, and the classification biases of every class the corpus
#              does not contain get pushed down at 2000x the nominal rate.
#              `warmup_epochs: 0, warmup_bias_lr: 0`.
#   gentle     nowarmup and lowlr together.
#   rehearsal  teacher-completed labels, PASS scope (build_rehearsal_versions.py
#              --scope pass) — the base speaks for every class no pass stamped
#              on that cell ever looked for, so those classes are refreshed
#              instead of pushed to background.
#   distill    the same at ALL scope: every teacher box no human box overlaps,
#              on every cell. The student is trained to reproduce production
#              everywhere except where a human corrected it — which is exactly
#              "production, plus the hollow noteheads it misses", stated as a
#              training target.
#   reh2048 /  the two rehearsal scopes at the native imgsz-2048 training
#   distill2048  scale, which held dense recall over 30 epochs where 896
#              collapsed after one.
#   rehfreeze  rehearsal and a frozen backbone at once.
#
# save_period=1 throughout: the shipping lever on this project has twice been
# WHICH EPOCH, not which recipe.
#
#   ./run_method_sweep.sh [arm ...]        (default: all)
set -euo pipefail
export PYTHONPATH="$(pwd)"
BASE_W="weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"
CLASSES="tools/omr/training/deepscoresv2_208_classes.json"

DENSE="v1-2026-05-18-orchestral v2-2026-06-08-beet5 v3-2026-06-09-mahler5 v4-2026-06-10-la-mer"
HOLLOW="v13-2026-09-03-complete-v7-beet5-bolero v14-2026-09-03-complete-litolff v15-2026-09-03-complete-peters v16-2026-09-03-complete-eulenburg v17-2026-09-03-complete-simrock v18-2026-09-03-complete-breitkopf v19-2026-09-03-complete-mahler1 v20-2026-09-03-complete-elgar1 v21-2026-09-03-complete-lamer v22-2026-09-04-simrock-dense"
VERSIONS="$DENSE $HOLLOW"

# build_catalog for a given data root ($1 = source data dir, $2 = catalog dir,
# $3 = dense oversample factor)
build_catalog () {
  local SRC="$1" ROOT="$2" FACTOR="$3"
  rm -rf "$ROOT"; mkdir -p "$ROOT"
  for v in $VERSIONS; do ln -sfn "$(pwd)/$SRC/$v" "$ROOT/$v"; done
  python3 -m tools.omr.training.build_catalog_yaml \
      --root "$ROOT" --versions $VERSIONS --fallback-class-names "$CLASSES"
  python3 oversample_dense.py --catalog "$ROOT/catalog.yaml" --factor "$FACTOR"
}

train () {
  local NAME="$1" DATA="$2" IMGSZ="$3" BATCH="$4" EPOCHS="$5" EXTRA="$6"
  echo "===== ARM $NAME  imgsz=$IMGSZ batch=$BATCH epochs=$EPOCHS extra=$EXTRA"
  python3 -m tools.omr.training.train_yolo \
    --data "$DATA" --weights "$BASE_W" \
    --epochs "$EPOCHS" --imgsz "$IMGSZ" --batch "$BATCH" --device 0 --patience 99 \
    --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0 \
    --extra-kwargs "$EXTRA" \
    --project runs --name "$NAME"
  ls -la "runs/$NAME/weights/" || true
}

ARMS=("$@")
[ ${#ARMS[@]} -eq 0 ] && ARMS=(prod896 nowarmup gentle distill distill25 rehearsal plain2 distill6 distill25_6 rehearsal6 dense6 freeze lowlr distill2048 reh2048 rehfreeze)

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

for arm in "${ARMS[@]}"; do
case "$arm" in
  prod896)
    build_catalog data/user-labeled cat-plain 6
    train prod896 cat-plain/catalog-6xdense.yaml 896 16 3 '{"save_period": 1}' ;;
  dense6)
    build_catalog data/user-labeled cat-plain 6
    train dense6 cat-plain/catalog-6xdense.yaml 896 16 5 '{"save_period": 1}' ;;
  freeze)
    build_catalog data/user-labeled cat-plain 6
    train freeze cat-plain/catalog-6xdense.yaml 896 16 5 '{"save_period": 1, "freeze": 10}' ;;
  lowlr)
    build_catalog data/user-labeled cat-plain 6
    train lowlr cat-plain/catalog-6xdense.yaml 896 16 5 \
      '{"save_period": 1, "lr0": 1e-5, "lrf": 1.0, "optimizer": "AdamW"}' ;;
  nowarmup)
    build_catalog data/user-labeled cat-plain 6
    train nowarmup cat-plain/catalog-6xdense.yaml 896 16 5 \
      '{"save_period": 1, "warmup_epochs": 0.0, "warmup_bias_lr": 0.0}' ;;
  gentle)
    build_catalog data/user-labeled cat-plain 6
    train gentle cat-plain/catalog-6xdense.yaml 896 16 5 \
      '{"save_period": 1, "warmup_epochs": 0.0, "warmup_bias_lr": 0.0, "lr0": 1e-5, "lrf": 1.0, "optimizer": "AdamW"}' ;;
  rehearsal)
    build_catalog data/user-labeled-rehearsal cat-reh 2
    train rehearsal cat-reh/catalog-2xdense.yaml 896 16 5 '{"save_period": 1}' ;;
  reh2048)
    build_catalog data/user-labeled-rehearsal cat-reh 3
    train reh2048 cat-reh/catalog-3xdense.yaml 2048 4 5 '{"save_period": 1}' ;;
  rehfreeze)
    build_catalog data/user-labeled-rehearsal cat-reh 2
    train rehfreeze cat-reh/catalog-2xdense.yaml 896 16 5 \
      '{"save_period": 1, "freeze": 10}' ;;
  distill)
    build_catalog data/user-labeled-distill cat-dis 2
    train distill cat-dis/catalog-2xdense.yaml 896 16 5 '{"save_period": 1}' ;;
  distill25)
    build_catalog data/user-labeled-distill25 cat-d25 2
    train distill25 cat-d25/catalog-2xdense.yaml 896 16 5 '{"save_period": 1}' ;;
  distill25_6)
    build_catalog data/user-labeled-distill25 cat-d25 6
    train distill25_6 cat-d25/catalog-6xdense.yaml 896 16 5 '{"save_period": 1}' ;;
  plain2)
    build_catalog data/user-labeled cat-plain 2
    train plain2 cat-plain/catalog-2xdense.yaml 896 16 5 '{"save_period": 1}' ;;
  distill6)
    build_catalog data/user-labeled-distill cat-dis 6
    train distill6 cat-dis/catalog-6xdense.yaml 896 16 5 '{"save_period": 1}' ;;
  rehearsal6)
    build_catalog data/user-labeled-rehearsal cat-reh 6
    train rehearsal6 cat-reh/catalog-6xdense.yaml 896 16 5 '{"save_period": 1}' ;;
  distill2048)
    build_catalog data/user-labeled-distill cat-dis 3
    train distill2048 cat-dis/catalog-3xdense.yaml 2048 4 5 '{"save_period": 1}' ;;
  *) echo "unknown arm: $arm" >&2; exit 2 ;;
esac
done

# Strip the optimizer state before the transfer home. ultralytics writes a
# ~350 MB checkpoint (weights + EMA + optimizer); the inference model is ~88 MB,
# and a save_period=1 sweep is otherwise 8 GB over a rented box's uplink.
# ⚠️ Stripping is what the last session's TRUNCATED e1_768.pt was really about
# — a short transfer that still looked like a file. Sizes are printed so a
# truncation is visible on arrival.
python3 - <<'PYSTRIP'
import glob
from ultralytics.utils.torch_utils import strip_optimizer
for f in sorted(glob.glob("runs/*/weights/*.pt")):
    try:
        strip_optimizer(f)
    except Exception as exc:
        print("strip failed", f, exc)
PYSTRIP

echo "== DONE. checkpoints (all should be ~88 MB — a smaller one is truncated):"
ls -la runs/*/weights/*.pt
md5sum runs/*/weights/*.pt > runs/CHECKSUMS.md5
cat runs/CHECKSUMS.md5
