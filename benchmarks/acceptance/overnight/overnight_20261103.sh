#!/bin/bash
# Overnight 20261103-night (Sean 2026-11-03: "send an agent out to start the full overnight regathers").
# One chain, one large process at a time, same settings as 20261031-night (THROUGH=infer, tree defaults for every flag,
# OMR_SURYA_KEEP_ALIVE=0, records beside the old ones in library/_shared-records):
#   1 re-gather Litolff, 2 re-gather Brahms (regather_20260930.sh does both, sequentially; one failing never stops the other),
#   3 compare Litolff vs 20261031-night, 4 compare Brahms vs 20261029-night (the last Brahms record; 19.6 GB, loaded alone, LAST),
#   5 stop any OCR server this chain left behind, by PID.
# Run from a COPY (so a cleaned lane worktree cannot pull it away):
#   D=$R/overnight-20261103-night; cp overnight_20261103.sh regather_20260930.sh $D/; nohup bash $D/overnight_20261103.sh > $D/chain.out 2>&1 &
set -uo pipefail
TAG=20261103-night
BASE_L=20261031-night      # last Litolff record
BASE_B=20261029-night      # last Brahms record (the 20261031-night Brahms was killed for memory; no record)
M=/Users/seanjohnson/Desktop/ReEngrave
R=$M/library/_shared-records
LOG=$R/overnight-$TAG
CW=$M/.claude/worktrees/overnight-compare-$TAG       # stable checkout the compares run in (not the gather's: acceptance rewrites tracked files)
mkdir -p "$LOG"
RL=$LOG/run-log.txt
say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$RL"; }
export OMR_SURYA_KEEP_ALIVE=0 OMRNED_PYTHON=$M/.venv-omrned/bin/python
PRE=$(pgrep -f llama-server | sort | tr '\n' ' ')
say "chain start TAG=$TAG; llama-server PIDs already running (not ours): [$PRE]"

# 1+2. the gathers (the script fetches origin/main, makes worktree overnight-$TAG, writes $LOG/summary.txt)
say "gather start: THROUGH=infer REF=origin/main"
TAG=$TAG THROUGH=infer bash "$LOG/regather_20260930.sh" >> "$LOG/regather.out" 2>&1
say "gather script exit $?; summary: $(tr '\n' '|' < "$LOG/summary.txt" 2>/dev/null | cut -c1-300)"

# compare checkout at the exact commit the night ran
TC=$(sed -n 's/.*commit \([0-9a-f]\{40\}\).*/\1/p' "$LOG/summary.txt" | head -1)
git -C "$M" worktree remove --force "$CW" 2>/dev/null
if [ -n "$TC" ] && git -C "$M" worktree add -q --detach "$CW" "$TC"; then
  for l in library omr-weights .venv-surya .venv-omrned; do ln -sfn "$M/$l" "$CW/$l"; done
  mkdir -p "$CW/tools/omr/training/data" && ln -sfn "$M/tools/omr/training/data/weights" "$CW/tools/omr/training/data/weights"
  do_compare() {  # docs base outdir sumdir
    say "compare start: $1 vs $2"
    ( cd "$CW" && WT="$CW" TAG=$TAG BASE=$2 DOCS="$1" OUT="$3" SUM="$4" bash benchmarks/acceptance/overnight/compare_20261029.sh >> "$LOG/compare.out" 2>&1 )
    say "compare $1 vs $2 exit $? (README: $4/README.txt)"
  }
  # a movement whose gather failed is skipped by the compare itself (no exit line / no record); each runs on its own
  do_compare beethoven5-litolff $BASE_L "$LOG/compare" "$CW/benchmarks/acceptance/overnight/$TAG"
  do_compare brahms1-breitkopf  $BASE_B "$LOG/compare-brahms" "$CW/benchmarks/acceptance/overnight/$TAG-brahms-vs-$BASE_B"
else
  say "could not make the compare worktree at '$TC' -- compares NOT run"
fi

# 5. OCR servers: only ones that were not there at the start AND are orphaned (PPID 1); by PID, never pkill
for p in $(pgrep -f llama-server); do
  case " $PRE " in *" $p "*) continue ;; esac
  pp=$(ps -o ppid= -p "$p" | tr -d ' ')
  if [ "$pp" = 1 ]; then say "stopping leftover llama-server PID $p"; kill "$p"; else say "llama-server PID $p new but has a live parent $pp -- left alone"; fi
done
say "chain done"
