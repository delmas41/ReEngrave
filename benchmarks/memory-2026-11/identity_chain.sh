#!/bin/bash
# ROADMAP 2.249 identity + memory proof: main (BASE worktree) vs this branch, SERIAL, nothing else running (the Surya
# rung's 20 s per-crop guard makes OCR readings load-sensitive, so two arms run side by side are not comparable).
# usage: identity_chain.sh BASE_WT BRANCH_WT OUT
set -uo pipefail
BASE=$1; BR=$2; OUT=$3; mkdir -p "$OUT"
M=/Users/seanjohnson/Desktop/ReEngrave
BRAHMS=$M/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
LIT=$M/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
export OMR_SURYA_KEEP_ALIVE=0
H=$BR/benchmarks/memory-2026-11
S=$OUT/summary.txt
echo "start $(date -u +%FT%TZ) base $BASE branch $BR" > $S
arm() { # label wt pdf pages
  python3 $H/mem_run.py "$2" "$OUT" "$1" "$3" "$4" --cache "$OUT/detcache" > "$OUT/$1.log" 2>&1
  echo "$1 exit $? $(grep '^MEM' $OUT/$1.log)" >> $S
}
arm base-lit1-4 $BASE $LIT 1-4
arm br-lit1-4 $BR $LIT 1-4
arm base-b0-5 $BASE $BRAHMS 0-5
arm br-b0-5 $BR $BRAHMS 0-5
for p in lit1-4 b0-5; do
  echo "== $p" >> $S
  python3 $H/row_diff.py $OUT/base-$p.record.json $OUT/br-$p.record.json >> $S 2>&1; echo "row_diff exit $?" >> $S
  cmp $OUT/base-$p.musicxml $OUT/br-$p.musicxml >> $S 2>&1 && echo "musicxml IDENTICAL" >> $S
done
echo "done $(date -u +%FT%TZ)" >> $S
