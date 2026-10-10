#!/bin/bash
# Regenerates every artefact of UNDECIDED.md from the two nights' records. Machine-local: needs
# library/_shared-records (the records and the saved first-two-stages diffs) and the editions.
# Run from the repo root of a worktree with the four assets symlinked (CLAUDE.md 5a).
# Peak memory: under 1 GB (the ijson reader). Wall time: about 10 minutes.
set -euo pipefail
R=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
C=$R/overnight-20261010-night/compare
P=benchmarks/acceptance/overnight/20261010-night/probe
U=benchmarks/acceptance/overnight/20261010-night/undecided
S=out/scratch-lud
O=out/print/overnight-20261010-undecided
mkdir -p $S $U $O
for D in brahms1-breitkopf beethoven5-litolff; do
  # tonight, everything (boxes, staves, cells, bar totals, duration verdicts); last night, duration verdicts only
  python3 $P/lud_extract.py --stream --record $R/$D-mvt1-whole-20261010-night.record.json --diff $C/$D-first-two-stages.json --out $S/extract-$D.json
  python3 $P/lud_extract.py --stream --dur-only --side a --record $R/$D-mvt1-whole-20261009-all.record.json --diff $C/$D-first-two-stages.json --out $S/extractA-$D.json
  python3 $P/lud_bars.py $D --out-dir $U --extract $S/extract-$D.json
  python3 $P/lud_thickness.py $D $R/$D-mvt1-whole-20261010-night.record.json > $U/thickness-$D.txt
done
python3 $P/lud_attrib.py brahms1-breitkopf --systems 13/1,22/0,16/0 --extract-b $S/extract-brahms1-breitkopf.json --extract-a $S/extractA-brahms1-breitkopf.json --out $U/attribution-brahms1-breitkopf.txt --csv $U/changed-notes-brahms1-breitkopf.csv
python3 $P/lud_attrib.py beethoven5-litolff --systems 15/1 --extract-b $S/extract-beethoven5-litolff.json --extract-a $S/extractA-beethoven5-litolff.json --out $U/attribution-beethoven5-litolff.txt --csv $U/changed-notes-beethoven5-litolff.csv
python3 $P/lud_rollup.py
python3 $P/lud_side_check.py brahms1-breitkopf > $U/side-only-brahms1-breitkopf.txt
python3 $P/lud_side_check.py beethoven5-litolff > $U/side-only-beethoven5-litolff.txt
# the control between the two readers (needs the load_record reader, ~5.4 GB resident, on the SMALL record only)
python3 $P/lud_extract.py --no-basis --record $R/beethoven5-litolff-mvt1-whole-20261010-night.record.json --diff $C/beethoven5-litolff-first-two-stages.json --out $S/ctl-loaded.json
python3 $P/lud_extract.py --stream --record $R/beethoven5-litolff-mvt1-whole-20261010-night.record.json --diff $C/beethoven5-litolff-first-two-stages.json --out $S/ctl-stream.json
python3 $P/lud_compare_json.py $S/ctl-loaded.json $S/ctl-stream.json | tee $U/reader-control.txt
# the images
python3 $P/lud_render.py brahms1-breitkopf --extract $S/extract-brahms1-breitkopf.json --systems 13/1,22/0,16/0 --start-index 1 --scale 1 --out-dir $O
python3 $P/lud_render.py beethoven5-litolff --extract $S/extract-beethoven5-litolff.json --systems 15/1 --start-index 4 --scale 2 --out-dir $O
python3 $P/lud_frame_control.py brahms1-breitkopf --extract $S/extract-brahms1-breitkopf.json --systems 13/1,22/0,16/0 --out-dir $O --tag brahms
python3 $P/lud_frame_control.py beethoven5-litolff --extract $S/extract-beethoven5-litolff.json --systems 15/1 --out-dir $O --tag litolff
python3 $P/lud_sample.py --doc brahms1-breitkopf --extract $S/extract-brahms1-breitkopf.json --notes-csv $U/changed-notes-brahms1-breitkopf.csv --n 20 --cols 5 --out $O/sample_random_brahms.png
python3 $P/lud_sample.py --doc beethoven5-litolff --extract $S/extract-beethoven5-litolff.json --notes-csv $U/changed-notes-beethoven5-litolff.csv --n 10 --cols 5 --out $O/sample_random_litolff.png
B=brahms1-breitkopf:$S/extract-brahms1-breitkopf.json
python3 $P/lud_printed_numbers.py --item $B:13/1 --item $B:22/0 --item $B:16/0 --item beethoven5-litolff:$S/extract-beethoven5-litolff.json:15/1 --out $O/printed_bar_numbers.png
