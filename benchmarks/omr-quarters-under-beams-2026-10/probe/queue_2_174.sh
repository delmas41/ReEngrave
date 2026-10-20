# usage: sh queue_2_174.sh PLATE...   waits while any python is over 10 GB, then runs run_2_174.sh for each plate in turn
for p in "$@"; do
  while [ -n "$(ps -axo rss,command | grep -i 'MacOS/Python' | grep -v grep | awk '$1>10000000')" ]; do sleep 30; done
  sh benchmarks/omr-quarters-under-beams-2026-10/probe/run_2_174.sh $p
done
