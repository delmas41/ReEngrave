#!/bin/bash
# One arm on the SHIPPED defaults, off the veto-pricing session's committed
# read-pass cache. The cache is the margin read, which is flag-independent by
# construction, so this is the same read every other arm in this thread saw and
# the only difference is the tree.
#
# ⚠️ `--tag` needs `=`. Two arms sharing a fixtures dir with an empty tag reuse
# the first arm's output and the second never runs (CLAUDE.md, "a cached A/B
# reports identical on every row"). The tell is wall time, which is printed.
set -u
cd "$(dirname "$0")/../../.." || exit 1
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
CACHE=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-abe066cff5c6c7283/benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/cache600
OUT=benchmarks/omr-brahms-tuba-2026-09/out/run
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0
echo "=== START $(date -u +%FT%TZ)"
python3 -u benchmarks/omr-spans-veto-composition-2026-09/probe/compose.py \
    "$PDF" --out-dir "$OUT" --pages 0-85 --dpi 600 --cache "$CACHE" \
    --veto report --tag="-shipped" 2>&1 | tail -12
echo "=== DONE  $(date -u +%FT%TZ)"
ls -la "$OUT"
