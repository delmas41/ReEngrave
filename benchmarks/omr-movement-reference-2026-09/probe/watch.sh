#!/bin/bash
# Emit one line per arm as its JSON lands; stop when the whole-work arm named
# in $1 is done.
O=benchmarks/omr-movement-reference-2026-09/out
STOP="${1:-beet5-whole-OFF.json}"
seen=""
while true; do
  cur=$(ls "$O" 2>/dev/null | grep -E 'flag1\.json|whole-(OFF|ON)\.json' | sort)
  for f in $cur; do
    case " $seen " in *" $f "*) ;; *) echo "ready: $f" ;; esac
  done
  seen="$cur"
  case " $cur " in *" $STOP "*) echo "STOP-ARM-READY $STOP"; exit 0 ;; esac
  sleep 30
done
