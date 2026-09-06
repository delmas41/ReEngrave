#!/bin/bash
# Phase-1 span screen over the shortlist. One stream per argument list.
# Usage: screen.sh <stream-name> <edition-path> [<edition-path> ...]
set -u
HERE="$(cd "$(dirname "$0")/../../.." && pwd)"
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
OUT="$HERE/benchmarks/omr-span-reach-2026-09/out"
name="$1"; shift
for rel in "$@"; do
  tag="$(basename "$rel" .pdf)"
  echo "=== $tag" >&2
  python3 "$HERE/benchmarks/omr-span-reach-2026-09/probe/span_profile.py" \
      "$LIB/$rel" --out "$OUT/profiles/$tag.json" \
      --cache "$OUT/cache/$tag" 2>>"$OUT/logs/$name.err" \
      >>"$OUT/logs/$name.log"
done
echo "STREAM $name DONE" >>"$OUT/logs/$name.log"
