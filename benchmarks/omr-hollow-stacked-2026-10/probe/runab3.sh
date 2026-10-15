#!/bin/bash
SP=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad/2.132
cd $SP/tree; ARMS="on off"
busy() { ps -eo command | grep -E "^[^ ]*[Pp]ython[^ ]* -m tools.omr.staged" | grep -v grep >/dev/null; }
waitfree() { while busy; do sleep 20; done; sleep 20; busy && waitfree; }
BRA=library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
LIT=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
for spec in "lit 0-3 $LIT" "bra21 21 $BRA" "bra01 0-1 $BRA" "bra12 12 $BRA" "bra18 18 $BRA" "bra10 10 $BRA" "bra25 25 $BRA" "bra8 8 $BRA" "bra7 7 $BRA" "bra3 3 $BRA"; do
  set -- $spec; tag=$1; pg=$2; pdf=$3
  for arm in $ARMS; do
    [ -f $SP/runs/$tag-$arm.json ] && continue
    waitfree
    v=0; [ $arm = on ] && v=1
    echo "=== $tag $arm $(date +%H:%M:%S)" >> $SP/runs/progress3.log
    OMR_STACKED_HOLLOW_PAIR=$v PYTHONDONTWRITEBYTECODE=1 nice -n 10 python3 -m tools.omr.staged $pdf --pages $pg --weights auto --no-surya --no-ocr --out $SP/runs/$tag-$arm.json --musicxml $SP/runs/$tag-$arm.musicxml > $SP/runs/$tag-$arm.log 2>&1
    echo "done $tag $arm exit $? $(date +%H:%M:%S)" >> $SP/runs/progress3.log
  done
done
echo ALLDONE3 >> $SP/runs/progress3.log
