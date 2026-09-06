#!/bin/bash
# Identity layer only, no detector. $1 = tag, $2 = pdf, $3 = optional --pages spec
set -u
BENCH="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$BENCH/../.." && pwd)"
TAG="$1"; PDF="$2"; PAGES="${3:-}"
export OMR_ABSENT_INSTRUMENT_VETO=report
# ⚠️ KEEP-ALIVE DELIBERATELY OFF. One machine has one Surya server and it is
# SHARED with every other agent on the box, so attaching to it couples this run
# to their lifecycle: a sibling's cleanup `pkill -f llama-server` took the daemon
# out from under a three-hour run here (fixed against itself in 395e2193), and a
# separate, still-UNDIAGNOSED stall left this probe at 0.0% CPU for 18 minutes
# with the server up and answering. Three explanations for that stall have each
# been falsified by measurement (CPU starvation, retained page rasters, one bad
# page) — do not adopt any of them.
#
# Spawning a worker per page costs ~15s a page and owns its own process, which
# for an unattended run is the cheaper half of the trade. The recovery the
# keep-alive path needs (`--stop && --serve`) is not available to an agent that
# cannot know whether a sibling is mid-read.
export OMR_SURYA_KEEP_ALIVE=0
export PYTHONUNBUFFERED=1
cd "$ROOT" || exit 1
ARGS=("$BENCH/probe/identity_only.py" "$PDF" "$BENCH/out/$TAG.json")
[ -n "$PAGES" ] && ARGS+=("--pages=$PAGES")
echo "=== $TAG start $(date -u +%FT%TZ)" > "$BENCH/out/$TAG.log"
S=$(date +%s)
nice -n 10 python3 "${ARGS[@]}" >>"$BENCH/out/$TAG.log" 2>&1
echo "=== $TAG rc=$? wall=$(( $(date +%s) - S ))s" >> "$BENCH/out/$TAG.log"
