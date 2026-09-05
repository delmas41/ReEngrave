#!/bin/zsh
# Re-export every work's recorded .omr.json with the CURRENT tree's exporter,
# then dump musicdiff ops against the same truths. Valid A/B for export-only
# changes — the beam-gap session established (2026-09-04) that the unmodified
# exporter reproduces the recorded .omr.musicxml byte-identically.
# Usage: reexport_and_score.sh <tag>
set -e
TAG=${1:?tag}
ROOT=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a5db9c4b9aa5bfecb
FIX=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/sad-austin-7e16e7/benchmarks/omr-orchestral-e2e/fixtures
OUT=$ROOT/benchmarks/omr-arc-attribution-2026-09/pred-$TAG
OPS=$ROOT/benchmarks/omr-arc-attribution-2026-09/ops-$TAG
mkdir -p "$OUT" "$OPS"
cd $ROOT
for w in beethoven-sym3-mvt1 beethoven-sym5-mvt1 brahms-sym1-mvt1 \
         brahms-sym4-mvt1 bruckner-sym5-mvt1 dvorak-sym9-mvt4 \
         mahler-sym5-mvt1 mozart-sym40-mvt1 mozart-sym41-mvt1 \
         tchaikovsky-sym4-mvt2 tchaikovsky-sym6-mvt2; do
  python3 -m tools.omr.export "$FIX/$w.omr.json" --format musicxml \
      --out "$OUT/$w.musicxml" > /dev/null
  /Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python \
    /Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-ned-2026-08/dump_ops.py \
    "$OUT/$w.musicxml" "$FIX/$w.musicxml" \
    --json "$OPS/$w.json" > "$OPS/$w.txt" 2>&1 || echo "FAILED $w"
done
echo ALL_DONE
