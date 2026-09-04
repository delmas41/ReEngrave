#!/usr/bin/env bash
# Serve ONE hollow batch for ONE completion pass (rests | accidentals).
#
#   ./serve_pass.sh <batch-dir-name> <rests|accidentals> [port]
#
# Why this exists rather than "swap batch_config.json by hand": the batch's own
# batch_config.json is the hollow-notehead pass and is a TRACKED file. This
# script parks it as batch_config.hollow.json the first time, installs the pass
# config, and REFUSES to start on a port another session already holds — several
# sessions run annotate servers at once, and killing someone else's labeling
# server loses their unsaved work.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BATCH="${1:?usage: serve_pass.sh <batch-dir-name> <rests|accidentals> [port]}"
PASS="${2:?usage: serve_pass.sh <batch-dir-name> <rests|accidentals> [port]}"
PORT="${3:-5052}"
DIR="$ROOT/benchmarks/$BATCH"
CFG="$ROOT/benchmarks/omr-labeling-survey-2026-09/pass-configs/$PASS.json"

[ -d "$DIR" ]  || { echo "no such batch: $DIR" >&2; exit 1; }
[ -f "$CFG" ]  || { echo "no such pass config: $CFG" >&2; exit 1; }
ls "$DIR"/cells/*.png >/dev/null 2>&1 || {
  echo "REFUSING: $BATCH has no cell PNGs (they are gitignored)." >&2
  echo "  python3 -m tools.omr.annotate.recut_cells --bench-dir benchmarks/$BATCH \\" >&2
  echo "      --pdf-root /Users/seanjohnson/Desktop/ReEngrave" >&2
  exit 1; }

if lsof -i ":$PORT" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "REFUSING: port $PORT is already LISTENing — probably another session's labeling server:" >&2
  lsof -i ":$PORT" -sTCP:LISTEN -n -P >&2
  echo "Pick a free port (3rd arg). Do NOT kill it." >&2
  exit 1
fi

# Park the hollow config once, then install this pass's config.
if [ ! -f "$DIR/batch_config.hollow.json" ] && [ -f "$DIR/batch_config.json" ]; then
  cp "$DIR/batch_config.json" "$DIR/batch_config.hollow.json"
  echo "parked existing batch_config.json -> batch_config.hollow.json"
fi
cp "$CFG" "$DIR/batch_config.json"
echo "installed pass '$PASS' into $BATCH"
echo "serving  http://127.0.0.1:$PORT   (Ctrl-C to stop)"
cd "$ROOT"
exec python3 -m tools.omr.annotate.server --bench-dir "benchmarks/$BATCH" --port "$PORT"
