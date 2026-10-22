#!/bin/bash
# 2.172 (e)+(f): small re-gather + export, flag OFF then ON, one run at a time. Litolff pdf pages 1-5 (count page 3 + 2 more), Brahms 0-3 (count page 1 + 2 more).
# Records and exports go to library/_shared-records/lane-2.172 (gitignored); one small summary line per run.
M=/Users/seanjohnson/Desktop/ReEngrave
WT=$M/.claude/worktrees/agent-aa6e5031bd6367fe7
OUT=$M/library/_shared-records/lane-2.172
mkdir -p "$OUT"
cd "$WT" || exit 2
export OMR_SURYA_KEEP_ALIVE=0 OMRNED_PYTHON=$M/.venv-omrned/bin/python
LIT=$M/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
BRA=$M/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
run() {  # plate pdf pages arm
  local t0=$(date +%s)
  if [ "$4" = on ]; then export OMR_DETECTOR_VIEWS=1; else unset OMR_DETECTOR_VIEWS; fi
  python3 -m tools.omr.staged "$2" --pages "$3" --weights auto --out "$OUT/$1-$4.record.json" --musicxml "$OUT/$1-$4.musicxml" > "$OUT/$1-$4.log" 2>&1
  echo "$1 $4 pages $3 exit $? wall $(( $(date +%s)-t0 )) s" >> "$OUT/summary.txt"
}
run lit "$LIT" 1-5 off
run lit "$LIT" 1-5 on
run bra "$BRA" 0-3 off
run bra "$BRA" 0-3 on
echo done >> "$OUT/summary.txt"
