#!/bin/bash
# ROADMAP 2.179 step 1: re-gather the sample pages through adjudicate with MAIN's defaults (2.172 small view ON).
# One gather at a time, serial. The movement's first page is included so the meter/key carry is read.
# usage (from the worktree root): OUT=dir TAG=base [extra env] benchmarks/omr-unseen-symbols-2026-10/probe/g1_regather.sh
set -uo pipefail
M=/Users/seanjohnson/Desktop/ReEngrave
OUT=${OUT:?}; TAG=${TAG:-base}
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0
LIT=$M/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
BRA=$M/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
echo "commit $(git rev-parse HEAD) tag $TAG start $(date -u +%FT%TZ)" >> "$OUT/summary.txt"
run() { # id pdf pages
  local t0=$(date +%s)
  python3 -m tools.omr.staged "$2" --pages "$3" --weights auto --through adjudicate --out "$OUT/$1.$TAG.record.json" > "$OUT/$1.$TAG.log" 2>&1
  local rc=$?
  grep -q "'duration':" "$OUT/$1.$TAG.log" || rc=3
  echo "$1 $TAG pages $3 exit $rc wall $(( $(date +%s)-t0 )) s" >> "$OUT/summary.txt"
}
if [ -z "${ONLY:-}" ] || [ "$ONLY" = litolff ]; then run litolff "$LIT" ${LIT_PAGES:-1,6,10,13,16}; fi
if [ -z "${ONLY:-}" ] || [ "$ONLY" = brahms ]; then run brahms "$BRA" ${BRA_PAGES:-0,1,6,23,24}; fi
echo "done $TAG $(date -u +%FT%TZ)" >> "$OUT/summary.txt"
