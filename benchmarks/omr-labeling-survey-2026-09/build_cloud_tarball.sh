#!/usr/bin/env bash
# Pack the round-5 method sweep for a rented CUDA box. Run from the repo root.
#
# ⚠️ COPYFILE_DISABLE=1 — macOS bsdtar otherwise bundles `._*` AppleDouble
# files, and the Linux side's label glob reads them as `.txt` and dies on
# UnicodeDecodeError. Learned the hard way in the round-3 handoff.
set -euo pipefail
OUT="${1:-/tmp/reengrave-round5.tgz}"
STAGE="$(mktemp -d)/reengrave-cloud"
MAIN=/Users/seanjohnson/Desktop/ReEngrave
SURVEY=benchmarks/omr-labeling-survey-2026-09

mkdir -p "$STAGE"/{weights,tools/omr/training,data}
# training modules only — the cloud box never imports the pipeline
touch "$STAGE/tools/__init__.py" "$STAGE/tools/omr/__init__.py"
cp tools/omr/training/__init__.py "$STAGE/tools/omr/training/" 2>/dev/null || \
  touch "$STAGE/tools/omr/training/__init__.py"
for f in train_yolo.py build_catalog_yaml.py verdicts_to_yolo_labels.py \
         deepscoresv2_208_classes.json; do
  cp "tools/omr/training/$f" "$STAGE/tools/omr/training/"
done
cp "$SURVEY/oversample_dense.py" "$SURVEY/run_method_sweep.sh" \
   "$SURVEY/requirements-cloud.txt" "$STAGE/"
cp "$MAIN/omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt" "$STAGE/weights/"

# The data roots. ⚠️ `cp -RL`, dereferencing, is load-bearing: v2/v3/v4 store
# their cell images as SYMLINKS into `benchmarks/omr-labeling-*/cells/` (only v1
# and the round-3 versions are copies), so a plain `cp -R` ships 101 of the 136
# dense-base cells as links to paths that do not exist on the rented box.
# ultralytics then skips them as "corrupt image/label" and trains on a mix with
# three quarters of its dense base missing — silently, in a warning stream
# thousands of lines long. The dense base is what carries the class breadth this
# whole round is about.
for root in data/user-labeled data/user-labeled-rehearsal \
            data/user-labeled-distill data/user-labeled-distill25; do
  [ -d "$root" ] && cp -RL "$root" "$STAGE/$root"
done
# the non-admitted versions are dead weight in the tarball
for d in "$STAGE"/data/user-labeled*/v*; do
  v="$(basename "$d")"
  grep -qx "$v" data/user-labeled/catalog-versions.txt || rm -rf "$d"
done
rm -rf "$STAGE"/data/user-labeled/_nc208 "$STAGE"/data/user-labeled/catalog*.yaml

COPYFILE_DISABLE=1 tar czf "$OUT" -C "$(dirname "$STAGE")" reengrave-cloud
echo "$OUT  $(du -h "$OUT" | cut -f1)"
