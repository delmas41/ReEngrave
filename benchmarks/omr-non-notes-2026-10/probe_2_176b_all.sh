#!/bin/bash
# ROADMAP 2.176b: run probe_2_176b_tile8.py page by page (one fresh process per page, serial) over page slices of each DOC given.
# usage: probe_2_176b_all.sh SLICES_DIR(parent of DOC) OUT_PARENT DOC [DOC...]   (run from the repo root)
SL=$1; OUT=$2; shift 2
for DOC in "$@"; do
  mkdir -p "$OUT"
  for f in "$SL/$DOC"/p*.observations.jsonl; do
    p=$(basename "$f" .observations.jsonl); n=$((10#${p#p}))
    [ -f "$OUT/probe_${DOC}_$n.json" ] && continue
    W="$OUT/w_$DOC"; rm -rf "$W"; mkdir -p "$W/$DOC"
    ln -s "$SL/$DOC"/common.*.jsonl "$W/$DOC/"
    ln -s "$SL/$DOC/$p.observations.jsonl" "$SL/$DOC/$p.abstentions.jsonl" "$W/$DOC/"
    python3 benchmarks/omr-non-notes-2026-10/probe_2_176b_tile8.py "$W" "$DOC" "$n" > /dev/null 2>&1 && mv "$W/probe_${DOC}_$n.json" "$OUT/"
  done
  echo done > "$OUT/DONE_$DOC"
done
