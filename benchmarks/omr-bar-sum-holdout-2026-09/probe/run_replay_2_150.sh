#!/bin/sh
# ROADMAP 2.150: base vs arm (OMR_REST_WIDTH_FLOOR off/on) on named systems of the 20261014-night records, one record at
# a time, under the shared record-load lock (retry every 30 s; released at the end).
R=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
P=benchmarks/omr-bar-sum-holdout-2026-09/probe
until mkdir $R/.record-load.lock 2>/dev/null; do sleep 30; done
python3 $P/replay_2_150.py $R/brahms1-breitkopf-mvt1-whole-20261014-night.record.json out/2.150/brah-replay.json \
  "0,0;1,0;1,1;15,0;21,0;11,1;9,1" > out/2.150/brah-replay.log 2>&1
python3 $P/replay_2_150.py $R/beethoven5-litolff-mvt1-whole-20261014-night.record.json out/2.150/lit-replay.json \
  "14,1;14,0;5,1" > out/2.150/lit-replay.log 2>&1
rmdir $R/.record-load.lock
echo done > out/2.150/replay.done
