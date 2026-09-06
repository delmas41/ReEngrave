#!/bin/bash
# Everything this benchmark reports, from one report-mode run. $1 = tag, $2 = work
set -u
BENCH="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$BENCH/../.." && pwd)"
TAG="$1"; WORK="${2:-beet5}"
cd "$ROOT" || exit 1
J="$BENCH/out/$TAG.json"
[ -s "$J" ] || { echo "REFUSING: $J missing or empty"; exit 1; }
python3 "$BENCH/probe/extract.py" "$J" "$BENCH/out/$TAG.extract.json"
E="$BENCH/out/$TAG.extract.json"
echo; python3 "$BENCH/probe/impossible_instruments.py" "$E"
echo; python3 "$BENCH/probe/score_full_systems.py" "$WORK" "$E"
echo; python3 "$BENCH/probe/sweep_window.py" "$E" "--work=$WORK" --max-window=45
