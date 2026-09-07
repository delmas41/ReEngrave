#!/bin/bash
# The whole harness, off committed artefacts.  ~10 seconds, no pipeline run,
# no weights, no venv, no network.  Nothing here changes a default.
set -u
cd "$(dirname "$0")/.." || exit 1
mkdir -p out

echo "=== THE GATE (exits non-zero if the harness cannot see a known fault)"
python3 probe/selftest.py | tee out/selftest.txt
GATE=${PIPESTATUS[0]}

echo "=== the report, every arm, per regime"
python3 probe/run_harness.py --pool > out/report.txt 2>&1

echo "=== the graded corpus, as records"
python3 probe/run_harness.py \
    --arms 'beet5/shipped' 'brahms1/fit=search,spans=on' \
    --records out/records.json > out/records.log 2>&1

echo "=== detail on the shipped arms"
python3 probe/run_harness.py \
    --arms 'beet5/shipped' 'brahms1/fit=search,spans=on' --detail \
    > out/shipped-detail.txt 2>&1

echo "=== forensics"
python3 probe/diff_arms.py 'beet5/groupmap=ordinal,spans=off' \
    'beet5/groupmap=map,spans=off'                 > out/diff-groupmap.txt 2>&1
python3 probe/diff_arms.py 'brahms1/fit=off,spans=on' \
    'brahms1/fit=search,spans=on'                  > out/diff-spanfit.txt 2>&1
python3 probe/diff_arms.py 'beet5/groupmap=map,spans=on' 'beet5/shipped' \
                                                   > out/diff-readpass.txt 2>&1
python3 probe/diff_arms.py 'beet5/front:fit=search,spans=on' \
    'beet5/groupmap=map,spans=on' --intersect      > out/diff-regime-front.txt 2>&1
python3 probe/diff_arms.py 'beet5/cross:fit=search,spans=on' \
    'beet5/groupmap=map,spans=on' --intersect      > out/diff-regime-cross.txt 2>&1

echo "=== calibration"
python3 probe/calibrate.py --json out/calibration-records.json \
    > out/calibration.txt 2>&1
tail -22 out/calibration.txt

echo
echo "GATE exit=$GATE"
exit "$GATE"
