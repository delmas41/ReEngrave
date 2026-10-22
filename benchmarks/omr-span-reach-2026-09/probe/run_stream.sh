#!/bin/bash
# Run one stream list produced by make_streams.py.
set -u
HERE="$(cd "$(dirname "$0")/../../.." && pwd)"
OUT="$HERE/benchmarks/omr-span-reach-2026-09/out"
name="$1"
while read -r rel; do
  [ -z "$rel" ] && continue
  tag="$(basename "$rel" .pdf)"
  python3 "$HERE/benchmarks/omr-span-reach-2026-09/probe/span_profile.py" \
      "/Users/seanjohnson/Desktop/ReEngrave/library/$rel" \
      --out "$OUT/profiles/$tag.json" --cache "$OUT/cache/$tag" \
      2>>"$OUT/logs/$name.err" >>"$OUT/logs/$name.log"
done < "$OUT/streams/$name.txt"
echo "STREAM $name DONE" >>"$OUT/logs/$name.log"
