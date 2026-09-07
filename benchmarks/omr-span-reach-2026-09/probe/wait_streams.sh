#!/bin/bash
# Block until N screen streams have written their DONE marker.
n="${1:-3}"
d="$(cd "$(dirname "$0")/../out/logs" && pwd)"
while true; do
  c=$(grep -l STREAM "$d"/*.log 2>/dev/null | wc -l | tr -d ' ')
  [ "$c" -ge "$n" ] && break
  sleep 20
done
echo "ALL $n STREAMS DONE"
