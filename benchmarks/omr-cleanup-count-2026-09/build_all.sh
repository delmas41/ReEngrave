#!/bin/bash
# record -> file -> map -> proposals -> sheet -> side-by-side, in order.
# Each step refuses rather than papers over: `export_arm` exits non-zero when
# the system map disagrees with the emitted file, and `build_sheet` exits
# non-zero when its per-system decomposition disagrees with the exporter's own
# totals. A green run of this script is therefore a claim that both controls
# passed, which is the only reason to chain them with `&&` at all -- a chain
# verifies that each step EXITED ZERO and nothing more, a lesson this repo
# paid for with a `&& echo LANDED` that printed LANDED over a failed assertion.
set -euo pipefail
cd "$(dirname "$0")/../.."
TAG="${1:-p1-p4}"
D=benchmarks/omr-cleanup-count-2026-09

python3 "$D/export_arm.py" --record "$D/out/record-$TAG.json" --tag "$TAG"
python3 "$D/build_sheet.py" --tag "$TAG"
python3 "$D/build_sidebyside.py" --tag "$TAG"
