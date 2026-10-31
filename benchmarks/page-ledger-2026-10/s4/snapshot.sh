#!/bin/sh
# 2.240 step 3: a frozen copy of one commit's tools/ to run a long GATHER from while the worktree keeps changing (a module imported
# lazily mid-run would otherwise load the newer code). ARG1 = commit. Prints the tree dir. data/ and the machine-local assets are linked.
cd "$(dirname "$0")/../../.."
R=/Users/seanjohnson/Desktop/ReEngrave
T=$R/library/_shared-records/lane-2.240-s4/tree-$1
rm -rf "$T"
mkdir -p "$T"
git archive "$1" tools data | tar -x -C "$T"
mkdir -p "$T/tools/omr/training/data"
ln -sfn $R/tools/omr/training/data/weights "$T/tools/omr/training/data/weights"
for a in omr-weights library .venv-surya .venv-omrned; do ln -sfn "$R/$a" "$T/$a"; done
echo "$T"
