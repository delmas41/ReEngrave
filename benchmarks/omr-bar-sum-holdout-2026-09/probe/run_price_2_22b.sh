#!/bin/sh
# ROADMAP 2.22b pricing: base (a `git archive HEAD` copy, $1) vs arm (this
# worktree) on the engraved control, Litolff p1-4 and Brahms p0-3, each
# re-decided in-process (no re-gather). Poll out/r222/*-22b.log.
BASE="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
ARM="$(cd "$HERE/../../.." && pwd)"
S=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
E="$ARM/benchmarks/omr-staged-engraved-2026-09/out/engraved-p0p2-20260928.record.json"
for pair in "eng22b:$E" "lit4_22b:$S/beethoven5-p1-p4.record.json" "brahms4_22b:$S/brahms1-breitkopf-p0-p3.record.json"; do
  L="${pair%%:*}"; REC="${pair#*:}"
  sh "$HERE/run_arm_2_22.sh" "$BASE" "$L-base" "$REC"
  sh "$HERE/run_arm_2_22.sh" "$ARM" "$L-arm" "$REC"
done
