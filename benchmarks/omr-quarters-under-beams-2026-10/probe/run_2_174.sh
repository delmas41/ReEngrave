# usage: sh run_2_174.sh litolff|brahms   (run from the repo root; slices from pages_2_165.py in scratch/slices)
mkdir -p scratch/out174
python3 benchmarks/omr-quarters-under-beams-2026-10/probe/replay_2_174.py $1 scratch/slices scratch/out174 off,on > scratch/out174/$1.log 2>&1
python3 benchmarks/omr-quarters-under-beams-2026-10/probe/compare_2_174.py $1 scratch/out174 scratch/out174/$1.cmp.json > scratch/out174/$1.cmp.txt 2>&1
echo DONE >> scratch/out174/$1.log
