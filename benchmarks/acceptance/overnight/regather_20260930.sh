#!/bin/bash
# Overnight 2026-09-29→30 (Sean: "run on the machine overnight tests as long
# as it isn't using tokens"). Re-gathers both acceptance scans on a CLEAN
# checkout of origin/main with the SAME settings as the 20260929b records
# (provenance: pages 1-16 / 0-26, weight routing on, Surya on,
# OMR_DIRECTION_TEXT_SCAN_GATE=1, OMR_SURYA_KEEP_ALIVE=0), writes NEW
# records beside the old ones (never overwrites), then a small summary.
# Adopting them into manifest.json is a deliberate step for the next session.
set -uo pipefail
M=/Users/seanjohnson/Desktop/ReEngrave
WT=$M/.claude/worktrees/overnight-20260930
OUT=$M/library/_shared-records
LOG=$M/library/_shared-records/overnight-20260930
mkdir -p "$LOG"
cd "$M"
git fetch -q origin
git worktree remove --force "$WT" 2>/dev/null
git worktree add -q --detach "$WT" origin/main || exit 2
cd "$WT"
ln -sfn $M/.venv-surya .venv-surya; ln -sfn $M/.venv-omrned .venv-omrned; ln -sfn $M/omr-weights omr-weights
mkdir -p tools/omr/training/data && ln -sfn $M/tools/omr/training/data/weights tools/omr/training/data/weights
export OMR_DIRECTION_TEXT_SCAN_GATE=1 OMR_SURYA_KEEP_ALIVE=0 OMRNED_PYTHON=$M/.venv-omrned/bin/python
echo "commit $(git rev-parse HEAD) start $(date -u +%FT%TZ)" > "$LOG/summary.txt"
run() {  # id pdf pages
  local t0=$(date +%s)
  python3 -m tools.omr.staged "$2" --pages "$3" --out "$OUT/$1-mvt1-whole-20260930.record.json" > "$LOG/$1.log" 2>&1
  local rc=$?
  echo "$1 pages $3 exit $rc wall $(( ($(date +%s)-t0)/60 )) min" >> "$LOG/summary.txt"
}
run beethoven5-litolff $M/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf 1-16
run brahms1-breitkopf $M/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf 0-26
for f in beethoven5-litolff brahms1-breitkopf; do
  echo "== $f" >> "$LOG/summary.txt"
  grep -E "held|refus|unaccounted|written|DECIDED|NARROWED|ABSTAINED" "$LOG/$f.log" | tail -25 >> "$LOG/summary.txt"
done
echo "done $(date -u +%FT%TZ)" >> "$LOG/summary.txt"
