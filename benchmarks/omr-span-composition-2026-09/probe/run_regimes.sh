#!/bin/bash
# THE THREE REGIMES, both works, three arms. See regime_report.py for why three.
set -u
cd "$(dirname "$0")/../../.." || exit 1
BR=/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
BE=/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
BRC=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-abe066cff5c6c7283/benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/cache600
BEC=benchmarks/omr-slot-alignment-2026-09/out/cache-beet5
OUT=benchmarks/omr-span-composition-2026-09/out/regimes
COMPOSE=benchmarks/omr-spans-veto-composition-2026-09/probe/compose.py
REPORT=benchmarks/omr-span-composition-2026-09/probe/regime_report.py
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0

run() {   # run WORK PDF CACHE REGIME PAGES
  for ARM in off refuse search; do
    OMR_SPAN_REFERENCE_FIT=$ARM python3 -u "$COMPOSE" "$2" --out-dir "$OUT" \
      --pages "$5" --dpi 600 --cache "$3" --veto report \
      --tag="-$1-$4-$ARM" >/dev/null 2>&1 \
      || echo "   !! $1 $4 $ARM FAILED"
  done
}

echo "=== running  $(date -u +%FT%TZ)"
run brahms "$BR" "$BRC" front   0-4
run brahms "$BR" "$BRC" cross   40-49
run brahms "$BR" "$BRC" adhoc   30,45
run beet5  "$BE" "$BEC" front   0-4
run beet5  "$BE" "$BEC" cross   39-48
run beet5  "$BE" "$BEC" adhoc   23,44

for W in brahms beet5; do
  if [ "$W" = brahms ]; then FIN=45; IMP=Trombone,Tuba; RG="front cross adhoc";
  else FIN=44; IMP=Piccolo,Contrabassoon,Trombone; RG="front cross adhoc"; fi
  echo
  echo "############ $W   (impossible = $IMP before page $FIN)"
  ARGS=()
  for R in $RG; do
    for ARM in off refuse search; do
      for S in off on; do
        ARGS+=("$R/$ARM/spans-$S=$OUT/-$W-$R-$ARM-spans-$S.json")
      done
    done
  done
  python3 "$REPORT" --finale-page "$FIN" --impossible "$IMP" "${ARGS[@]}"
done
echo "=== DONE $(date -u +%FT%TZ)"
