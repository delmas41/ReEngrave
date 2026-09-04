#!/usr/bin/env bash
# Round 6 — the composability test, and one detector per symbol. Runs ON THE BOX.
#
# Two questions, one rental:
#
#   freeze22   ⚠️ THE COMPOSABILITY TEST. Round 5's graft restores a class's head
#              row from the base and the class comes back — but not all the way:
#              `ledgerLine` reads 11 against the base's 57, because the FEATURES
#              under the restored row moved. `freeze=10` was tried and did not
#              help (10 vs 11), and the reason is that it pins only the backbone
#              and leaves the NECK, layers 10-21, trainable. `freeze=22` pins
#              everything except `model.22`, the detect head itself, so the
#              features are bit-identical to the checkpoint we started from and
#              a restored row must return to exactly its old behaviour. If
#              `ledgerLine` comes back to ~31 here, head rows from any number of
#              specialists COMPOSE and the ensemble can be compiled into one set
#              of weights. If it does not, each graft is a one-off.
#
#   <family>_free / _frz   one detector per symbol family, from
#              `build_specialist_versions.py` — cells swept for that family,
#              labels filtered to it, nc=208 so the rows stay graftable. Trained
#              FROM PRODUCTION, not from the base, so the frozen arms share
#              production's features exactly and their rows drop straight in.
#              Every other class collapses during training and that is fine:
#              those rows are thrown away.
#
# ⚠️ The specialist corpora are 47-76% NEGATIVE cells by construction (a cell
# swept for ties that holds none is a true negative and belongs in the corpus).
# Do not read a low box count as a small corpus.
#
#   ./run_specialist_sweep.sh [arm ...]
set -euo pipefail
export PYTHONPATH="$(pwd)"
PROD_W="weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"
BASE_W="weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"
CLASSES="tools/omr/training/deepscoresv2_208_classes.json"

build_specialist_catalog () {   # $1 = data root, $2 = catalog dir
  local SRC="$1" ROOT="$2"
  local VERSIONS
  VERSIONS="$(grep -v '^#' "$SRC/catalog-versions.txt" | grep -v '^$' | tr '\n' ' ')"
  rm -rf "$ROOT"; mkdir -p "$ROOT"
  for v in $VERSIONS; do ln -sfn "$(pwd)/$SRC/$v" "$ROOT/$v"; done
  python3 -m tools.omr.training.build_catalog_yaml \
      --root "$ROOT" --versions $VERSIONS --fallback-class-names "$CLASSES"
}

train () {   # name data weights imgsz batch epochs extra
  echo "===== ARM $1  weights=$3 imgsz=$4 epochs=$6 extra=$7"
  python3 -m tools.omr.training.train_yolo \
    --data "$2" --weights "$3" --epochs "$6" --imgsz "$4" --batch "$5" \
    --device 0 --patience 99 --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0 \
    --extra-kwargs "$7" --project runs --name "$1"
}

specialist () {   # $1 = family
  build_specialist_catalog "data/specialist-$1" "cat-$1"
  train "${1}_free" "cat-$1/catalog.yaml" "$PROD_W" 896 16 5 '{"save_period": 1}'
  train "${1}_frz"  "cat-$1/catalog.yaml" "$PROD_W" 896 16 5 \
        '{"save_period": 1, "freeze": 22}'
}

ARMS=("$@")
[ ${#ARMS[@]} -eq 0 ] && ARMS=(freeze22 ties rests hollow slurs accidentals)

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

for arm in "${ARMS[@]}"; do
case "$arm" in
  freeze22)
    # the full round-5 mix, so the result is comparable to round 5's grafts
    DENSE="v1-2026-05-18-orchestral v2-2026-06-08-beet5 v3-2026-06-09-mahler5 v4-2026-06-10-la-mer"
    HOLLOW="v13-2026-09-03-complete-v7-beet5-bolero v14-2026-09-03-complete-litolff v15-2026-09-03-complete-peters v16-2026-09-03-complete-eulenburg v17-2026-09-03-complete-simrock v18-2026-09-03-complete-breitkopf v19-2026-09-03-complete-mahler1 v20-2026-09-03-complete-elgar1 v21-2026-09-03-complete-lamer v22-2026-09-04-simrock-dense"
    V="$DENSE $HOLLOW"
    rm -rf cat-f22; mkdir -p cat-f22
    for v in $V; do ln -sfn "$(pwd)/data/user-labeled-distill25/$v" "cat-f22/$v"; done
    python3 -m tools.omr.training.build_catalog_yaml --root cat-f22 --versions $V \
        --fallback-class-names "$CLASSES"
    python3 oversample_dense.py --catalog cat-f22/catalog.yaml --factor 6
    train freeze22 cat-f22/catalog-6xdense.yaml "$BASE_W" 896 16 5 \
        '{"save_period": 1, "freeze": 22}' ;;
  ties|rests|hollow|slurs|accidentals) specialist "$arm" ;;
  *) echo "unknown arm: $arm" >&2; exit 2 ;;
esac
done

python3 - <<'PYSTRIP'
import glob
from ultralytics.utils.torch_utils import strip_optimizer
for f in sorted(glob.glob("runs/**/weights/*.pt", recursive=True)):
    try: strip_optimizer(f)
    except Exception as exc: print("strip failed", f, exc)
PYSTRIP
echo "== DONE (all should be ~88 MB; smaller = truncated):"
ls -la runs/*/*/weights/*.pt 2>/dev/null || ls -la runs/*/weights/*.pt
