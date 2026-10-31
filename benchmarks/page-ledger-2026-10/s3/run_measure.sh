#!/bin/sh
# 2.240 s2 round 2: both plates' measure from the lane_report arms' gathered records (moved to $W; 2.1 GB, not committed)
cd "$(dirname "$0")/../../.."
W=${W:-/private/tmp/s3work}
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=.
python3 benchmarks/page-ledger-2026-10/s3/measure.py litolff $W/litolff.off.gathered.record.json $W/litolff.on.gathered.record.json --pages 2,4 > benchmarks/page-ledger-2026-10/s3/measure_litolff.log 2>&1
python3 benchmarks/page-ledger-2026-10/s3/measure.py brahms $W/brahms.off.gathered.record.json $W/brahms.on.gathered.record.json --pages 4,5 > benchmarks/page-ledger-2026-10/s3/measure_brahms.log 2>&1
