#!/bin/bash
# ONE gather, INFER'd once, exported twice.
#
# ⚠️ The arms differ ONLY in whether INFER ran. The gather is shared (so no
# detector jitter), the adjudication is shared (so no adjudication jitter),
# and both arms go through the same `export_arm.py` one process apart.
#
# ⚠️ `--control` runs FIRST and the script stops if it fails: a rebuild that
# does not reproduce the record is not a control, and every number after it
# would be a measurement of the harness.
#
#   bash benchmarks/omr-infer-stage-2026-09/run_arms.sh <record.json>
set -euo pipefail
cd "$(dirname "$0")/../.."

REC="${1:-benchmarks/omr-cleanup-count-2026-09/out/record-p1-p4.json}"
OUT=benchmarks/omr-infer-stage-2026-09/out
B=benchmarks/omr-infer-stage-2026-09
mkdir -p "$OUT"

echo "══ REACH, BEFORE ANYTHING ════════════════════════════════════════"
python3 "$B/probe/reach.py" "$REC" --json "$OUT/reach.json" | tail -40 || true

echo
echo "══ CONTROL: does the rebuild reproduce the record? ═══════════════"
python3 "$B/reinfer.py" "$REC" --control

echo
echo "══ ARM ON: INFER alone over that record ══════════════════════════"
python3 "$B/reinfer.py" "$REC" --out "$OUT/record-inferred.json" \
    --json "$OUT/infer-summary.json"

echo
echo "══ EXPORT, both arms, same script ════════════════════════════════"
python3 "$B/export_arm.py" "$REC" --out "$OUT/export-off.musicxml"
python3 "$B/export_arm.py" "$OUT/record-inferred.json" \
    --out "$OUT/export-on.musicxml"

echo
echo "══ SELF-CHECK: an invariant the rule did NOT read ════════════════"
python3 "$B/probe/self_check.py" --off "$OUT/export-off.musicxml" \
    --on "$OUT/export-on.musicxml" --bar-beats 2.0 || true

echo
echo "══ BYTE CONTROL: identical outside what INFER moved ══════════════"
python3 "$B/probe/byte_control.py" "$OUT/export-off.musicxml" \
    "$OUT/export-on.musicxml" || true
