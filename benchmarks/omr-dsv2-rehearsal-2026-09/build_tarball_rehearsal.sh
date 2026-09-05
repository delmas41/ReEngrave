#!/usr/bin/env bash
# Pack the DSv2-rehearsal experiment for the rented box. Run from the
# dsv2-rehearsal worktree root. Adapted from build_cloud_tarball.sh with its
# two recorded rig lessons kept verbatim:
#   COPYFILE_DISABLE=1  — macOS bsdtar otherwise bundles ._* AppleDouble files
#                         the Linux label glob reads as .txt (UnicodeDecodeError)
#   cp -RL              — v2/v3/v4 store cell images as SYMLINKS into gitignored
#                         batch dirs; plain cp -R ships 101 of 136 dense-base
#                         cells as dangling links and ultralytics silently
#                         trains without the class breadth this round is about.
set -euo pipefail
OUT="${1:?usage: build_tarball_rehearsal.sh <out.tgz> <pkg-dir>}"
PKG="${2:?}"
STAGE="$(mktemp -d)/reengrave-cloud"
MAIN=/Users/seanjohnson/Desktop/ReEngrave

mkdir -p "$STAGE"/{weights,tools/omr/training,data}
touch "$STAGE/tools/__init__.py" "$STAGE/tools/omr/__init__.py"
cp tools/omr/training/__init__.py "$STAGE/tools/omr/training/" 2>/dev/null || \
  touch "$STAGE/tools/omr/training/__init__.py"
for f in train_yolo.py build_catalog_yaml.py verdicts_to_yolo_labels.py \
         prepare_yolo_data.py download_dataset.py deepscores_classes.py \
         deepscoresv2_208_classes.json; do
  cp "tools/omr/training/$f" "$STAGE/tools/omr/training/"
done
cp "$PKG/build_mix.py" "$PKG/run_rehearsal.sh" "$STAGE/"
chmod +x "$STAGE/run_rehearsal.sh"
cp benchmarks/omr-labeling-survey-2026-09/requirements-cloud.txt "$STAGE/"

# BOTH donors: the pre-hollow base (arm 1) and production (arm 2).
cp "$MAIN/omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt" "$STAGE/weights/"
cp "$MAIN/omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt" "$STAGE/weights/"

# The scan-label corpus, dereferenced, pruned to the admitted membership.
cp -RL data/user-labeled "$STAGE/data/user-labeled"
for d in "$STAGE"/data/user-labeled/v*; do
  v="$(basename "$d")"
  grep -qx "$v" data/user-labeled/catalog-versions.txt || rm -rf "$d"
done
rm -rf "$STAGE"/data/user-labeled/_nc208 "$STAGE"/data/user-labeled/catalog*.yaml \
       "$STAGE"/data/user-labeled/_catalog_*.txt

echo "== staged versions:"
ls -d "$STAGE"/data/user-labeled/v* | xargs -n1 basename
echo "== dangling-symlink check (must be 0):"
find "$STAGE" -type l ! -exec test -e {} \; -print | wc -l

COPYFILE_DISABLE=1 tar czf "$OUT" -C "$(dirname "$STAGE")" reengrave-cloud
echo "$OUT  $(du -h "$OUT" | cut -f1)"
md5 -q "$OUT" 2>/dev/null || md5sum "$OUT"
