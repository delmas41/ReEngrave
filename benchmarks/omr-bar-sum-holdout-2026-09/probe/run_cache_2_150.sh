#!/bin/sh
# ROADMAP 2.150: stream the Brahms and Litolff 20261014-night records into small row caches, one at a time,
# under the shared record-load lock (taken by the caller; released here).
R=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
P=benchmarks/omr-bar-sum-holdout-2026-09/probe/cache_2_150.py
mkdir -p out/2.150
python3 $P $R/brahms1-breitkopf-mvt1-whole-20261014-night.record.json out/2.150/brahms-rows.json > out/2.150/cache-brahms.log 2>&1
python3 $P $R/beethoven5-litolff-mvt1-whole-20261014-night.record.json out/2.150/litolff-rows.json > out/2.150/cache-litolff.log 2>&1
rmdir $R/.record-load.lock
echo done > out/2.150/cache.done
