#!/bin/zsh
# ROADMAP 2.321: measure Litolff then Brahms, ONE slice at a time, waiting while any python process holds more than 4 GB (the box is shared).
# nohup zsh benchmarks/voice-line-of-time-2026-11/run.sh OUTDIR > OUTDIR/run.log 2>&1 &
cd "$(dirname "$0")/../.."
OUT=$1
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=.
wait_box() {
  while ps -axo rss,command | awk '/[Pp]ython/ && $1 > 4000000 {f=1} END {exit !f}'; do sleep 30; done
}
for p in litolff brahms; do
  wait_box
  echo "start $p $(date)"
  python3 benchmarks/voice-line-of-time-2026-11/measure.py $p $OUT/$p.json 2>&1 | grep -v -i "warn" | tail -5
  echo "done $p $(date)"
done
