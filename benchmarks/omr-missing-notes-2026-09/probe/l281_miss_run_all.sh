#!/usr/bin/env bash
# l281_miss_run_all: regenerate the 2.81 MISS images (`out/print/2.81-misses/`) and the manager's table.
# MACHINE-LOCAL (shared overnight records, edition PDFs, venv/weights symlinks per CLAUDE.md 5a). The two
# overnight records are STREAMED with `ijson` (nothing is loaded whole); each page is re-adjudicated from its
# own saved GATHER rows and checked against the saved verdicts (`l281_miss_rebuild.py`: the control).
#
#   SCRATCH=/some/dir probe/l281_miss_run_all.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
LIB=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
SCRATCH="${SCRATCH:-/tmp/l281m}"
OUT="$HERE/out/l281"
mkdir -p "$SCRATCH" "$OUT"
cd "$REPO"
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python OMR_SURYA_KEEP_ALIVE=0

BR="$LIB/brahms1-breitkopf-mvt1-whole-20261010-night.record.json"
LI="$LIB/beethoven5-litolff-mvt1-whole-20261010-night.record.json"

# 1. the pages the misses stand on, streamed out of the overnight records
[ -f "$SCRATCH/rows-brahms.json" ]  || python3 "$HERE/l281_miss_rows.py" --record "$BR" --pages 0,2,7,20,24,25 --out "$SCRATCH/rows-brahms.json"
[ -f "$SCRATCH/rows-litolff.json" ] || python3 "$HERE/l281_miss_rows.py" --record "$LI" --pages 10,13,15 --out "$SCRATCH/rows-litolff.json"

# 2. page 0 of the overnight Brahms record on the CORRECTED hand-truth page: which members are wrong
if [ ! -f "$SCRATCH/b0-scored.json" ]; then
  for w in obs abs ver prov; do
    python3 "$HERE/l281_extract.py" --what "$w" --record "$BR" --pages 0 --out "$SCRATCH/b0-$w.json" > /dev/null
  done
  python3 "$HERE/l281_score.py" --tag b0 --ext "$SCRATCH" --json "$SCRATCH/b0-scored.json" > "$OUT/miss-hand-truth-score.txt"
fi

# 3. per page: which stroke each filter refused (the control runs first; exit 1 if an asked head differs)
HT=$(python3 "$HERE/l281_miss_list.py" --scored "$SCRATCH/b0-scored.json" --print-keys)
python3 "$HERE/l281_miss_rebuild.py" --rows "$SCRATCH/rows-brahms.json" --page 0 --keys "$HT" --out "$SCRATCH/cap-brahms-p0.json" | tee "$OUT/miss-rebuild-control.txt"
python3 "$HERE/l281_miss_rebuild.py" --rows "$SCRATCH/rows-brahms.json" --page 2  --keys glyph/2/0/9/2/4    --out "$SCRATCH/cap-brahms-p2.json"  | grep CONTROL | tee -a "$OUT/miss-rebuild-control.txt"
python3 "$HERE/l281_miss_rebuild.py" --rows "$SCRATCH/rows-brahms.json" --page 7  --keys glyph/7/0/0/2/10   --out "$SCRATCH/cap-brahms-p7.json"  | grep CONTROL | tee -a "$OUT/miss-rebuild-control.txt"
python3 "$HERE/l281_miss_rebuild.py" --rows "$SCRATCH/rows-brahms.json" --page 20 --keys glyph/20/0/11/2/3  --out "$SCRATCH/cap-brahms-p20.json" | grep CONTROL | tee -a "$OUT/miss-rebuild-control.txt"
python3 "$HERE/l281_miss_rebuild.py" --rows "$SCRATCH/rows-brahms.json" --page 24 --keys glyph/24/1/12/7/3  --out "$SCRATCH/cap-brahms-p24.json" | grep CONTROL | tee -a "$OUT/miss-rebuild-control.txt"
python3 "$HERE/l281_miss_rebuild.py" --rows "$SCRATCH/rows-brahms.json" --page 25 --keys glyph/25/0/12/1/0  --out "$SCRATCH/cap-brahms-p25.json" | grep CONTROL | tee -a "$OUT/miss-rebuild-control.txt"
python3 "$HERE/l281_miss_rebuild.py" --rows "$SCRATCH/rows-litolff.json" --page 10 --keys glyph/10/1/9/7/5  --out "$SCRATCH/cap-litolff-p10.json" | grep CONTROL | tee -a "$OUT/miss-rebuild-control.txt"
python3 "$HERE/l281_miss_rebuild.py" --rows "$SCRATCH/rows-litolff.json" --page 13 --keys glyph/13/1/2/9/1  --out "$SCRATCH/cap-litolff-p13.json" | grep CONTROL | tee -a "$OUT/miss-rebuild-control.txt"
python3 "$HERE/l281_miss_rebuild.py" --rows "$SCRATCH/rows-litolff.json" --page 15 --keys glyph/15/0/5/0/6  --out "$SCRATCH/cap-litolff-p15.json" | grep CONTROL | tee -a "$OUT/miss-rebuild-control.txt"
# the control that must FAIL: every stroke on page 0 made thick; the page's narrowed heads must move
python3 "$HERE/l281_miss_rebuild.py" --rows "$SCRATCH/rows-brahms.json" --page 0 --keys glyph/0/0/0/3/3 --out "$SCRATCH/cap-break.json" --break-control | tail -2 | tee -a "$OUT/miss-rebuild-control.txt"

# 4. the images + the manager's table
python3 "$HERE/l281_miss_images.py" --scratch "$SCRATCH" --scored "$SCRATCH/b0-scored.json" \
  --out "$REPO/out/print/2.81-misses" --cache "$SCRATCH/p0_rgb.npy"
echo "done"
