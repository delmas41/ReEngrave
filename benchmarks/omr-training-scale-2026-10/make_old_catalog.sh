#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ROOT="$(pwd)"; source benchmarks/omr-training-scale-2026-10/mix.sh
make_catalog "$ROOT/data/user-labeled-distill25" runs/2.110/cat-old
