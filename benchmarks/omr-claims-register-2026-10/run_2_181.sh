#!/bin/zsh
# ROADMAP 2.181 -- unattended replay, Litolff then Brahms, OFF then ON, one python at a time; waits while two or more pythons over
# 10 GB run (other lanes replay on the same box). usage: run_2_181.sh SLICEDIR OUTDIR
SD=$1; OUT=$2
mkdir -p $OUT
wait_mem() {
  while true; do
    n=$(ps -axo rss,command | awk '/[Pp]ython/ && $1 > 10000000 {c++} END {print c+0}')
    [ "$n" -lt 2 ] && break
    sleep 60
  done
}
# JOBS: "doc.arm ..." (default all four)
for job in ${=JOBS:-litolff.off litolff.on brahms.off brahms.on}; do
  doc=${job%.*}; arm=${job#*.}
  wait_mem
  python3 benchmarks/omr-claims-register-2026-10/replay_2_181.py $doc $SD $OUT $arm > $OUT/$doc.$arm.log 2>&1
done
echo done > $OUT/DONE
