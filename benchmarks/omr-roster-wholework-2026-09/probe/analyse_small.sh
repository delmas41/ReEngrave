#!/bin/bash
# Derived reports for every transcription JSON present.
BENCH="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BENCH/../.." || exit 1
export PYTHONPATH=.
for j in "$BENCH"/out/*.json; do
  case "$(basename "$j")" in *staffprofile*) continue ;; esac
  b="${j%.json}"
  python3 "$BENCH/probe/report_roster.py"  "$j" > "$b.roster.txt"  2>&1
  python3 "$BENCH/probe/dump_slots.py"     "$j" > "$b.slots.txt"   2>&1
  python3 "$BENCH/probe/audit_identity.py" "$j" > "$b.audit.txt"   2>&1
  case "$(basename "$j")" in
    beet5*)   python3 "$BENCH/probe/score_full_systems.py" beet5   "$j" > "$b.score.txt" 2>&1 ;;
    dvorak9*) python3 "$BENCH/probe/score_full_systems.py" dvorak9 "$j" > "$b.score.txt" 2>&1 ;;
  esac
  echo "wrote reports for $(basename "$j")"
done
