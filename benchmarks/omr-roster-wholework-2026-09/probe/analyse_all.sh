#!/bin/bash
# Run every report over whatever whole-work JSONs exist, writing .txt beside them.
BENCH="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BENCH/../.." || exit 1
export PYTHONPATH=.
for j in "$BENCH"/out/*whole*.json; do
  [ -e "$j" ] || continue
  b="${j%.json}"
  echo "== $(basename "$j")"
  python3 "$BENCH/probe/wholework_report.py" "$j" > "$b.report.txt" 2>&1
  python3 "$BENCH/probe/audit_identity.py"   "$j" > "$b.audit.txt"  2>&1
  case "$(basename "$j")" in
    beet5*)   W=beet5 ;;
    dvorak9*) W=dvorak9 ;;
    *)        W="" ;;
  esac
  if [ -n "$W" ]; then
    python3 "$BENCH/probe/score_full_systems.py" "$W" "$j" > "$b.score.txt" 2>&1
    head -14 "$b.score.txt"
  fi
done
