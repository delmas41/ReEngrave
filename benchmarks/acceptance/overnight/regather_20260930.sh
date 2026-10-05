#!/bin/bash
# Overnight 2026-09-29→30 (Sean: "run on the machine overnight tests as long
# as it isn't using tokens"). Re-gathers both acceptance scans on a CLEAN
# checkout of origin/main with the SAME settings as the 20260929b records
# (provenance: pages 1-16 / 0-26, weight routing on, Surya on,
# OMR_DIRECTION_TEXT_SCAN_GATE=1, OMR_SURYA_KEEP_ALIVE=0), writes NEW
# records beside the old ones (never overwrites), then a small summary.
# Adopting them into manifest.json is a deliberate step for the next session.
#
# ⚠️ 2026-09-30: the first run of this script OMITTED `--weights auto`, so the
# detector never ran (every cell READER_UNAVAILABLE; 0 notes exported) and
# both runs exited 0. Those records were renamed *.NO-WEIGHTS.record.json.
# Fixed below, tagged by $TAG, and a run with no duration decisions now
# exits 3 instead of 0 (a control that can fail).
#
# THROUGH (Sean, 2026-09-30): the full re-gather runs only as far as the
# stage currently being refined, and later nights add stages progressively
# (adjudicate -> evaluate -> infer). Default: adjudicate (the first two
# stages). A through-adjudicate record is read with `tools.omr.staged.readout`;
# `tools.omr.acceptance` needs a through-infer record.
set -uo pipefail
TAG=${TAG:-20260930b}
THROUGH=${THROUGH:-adjudicate}
REF=${REF:-origin/main}   # 2026-10-04: a branch may be re-gathered before it is merged
M=/Users/seanjohnson/Desktop/ReEngrave
WT=$M/.claude/worktrees/overnight-$TAG
OUT=$M/library/_shared-records
LOG=$M/library/_shared-records/overnight-$TAG
mkdir -p "$LOG"
cd "$M"
git fetch -q origin
git worktree remove --force "$WT" 2>/dev/null
git worktree add -q --detach "$WT" "$REF" || exit 2
cd "$WT"
ln -sfn $M/.venv-surya .venv-surya; ln -sfn $M/.venv-omrned .venv-omrned; ln -sfn $M/omr-weights omr-weights
mkdir -p tools/omr/training/data && ln -sfn $M/tools/omr/training/data/weights tools/omr/training/data/weights
export OMR_DIRECTION_TEXT_SCAN_GATE=1 OMR_SURYA_KEEP_ALIVE=0 OMRNED_PYTHON=$M/.venv-omrned/bin/python
echo "ref $REF commit $(git rev-parse HEAD) through $THROUGH start $(date -u +%FT%TZ)" > "$LOG/summary.txt"
run() {  # id pdf pages
  local t0=$(date +%s)
  python3 -m tools.omr.staged "$2" --pages "$3" --weights auto --through "$THROUGH" --out "$OUT/$1-mvt1-whole-$TAG.record.json" > "$LOG/$1.log" 2>&1
  local rc=$?
  # a gather whose detector never fired still exits 0 -- refuse it here
  grep -q "'duration':" "$LOG/$1.log" || rc=3
  echo "$1 pages $3 exit $rc wall $(( ($(date +%s)-t0)/60 )) min" >> "$LOG/summary.txt"
}
run beethoven5-litolff $M/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf 1-16
run brahms1-breitkopf $M/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf 0-26
for f in beethoven5-litolff brahms1-breitkopf; do
  echo "== $f" >> "$LOG/summary.txt"
  grep -E "held|refus|unaccounted|written|DECIDED|NARROWED|ABSTAINED" "$LOG/$f.log" | tail -25 >> "$LOG/summary.txt"
done
echo "done $(date -u +%FT%TZ)" >> "$LOG/summary.txt"
