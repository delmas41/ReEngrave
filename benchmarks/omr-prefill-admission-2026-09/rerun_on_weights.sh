#!/bin/zsh
# Re-measure the MXL pre-fill on ONE checkpoint, without touching the batch.
#
#   ./rerun_on_weights.sh /abs/path/to/checkpoint.pt TAG [outdir]
#
# Transcribes the Brahms 1 / Breitkopf batch's three pages with the given
# weights, builds a SCRATCH bench (the real batch by symlink, this arm's
# reading as its transcription.json), and runs the dry-run pre-fill, the
# six-cell --score and probe_admission.py against it. Nothing is written
# inside the batch: every command is --dry-run and the bench is symlinks.
#
# Run one arm per checkpoint and diff the outputs. This is the harness the
# "pre-fill precision is downstream of recognition" claim is tested with —
# see FINDINGS.md "Phase B".
#
# ⚠️ Run arms SEQUENTIALLY. Two ultralytics processes on one Mac's MPS
# contend and the timings stop meaning anything.
set -e
CKPT="$1"; TAG="$2"
OUT="${3:-${0:a:h}/out-$TAG}"
[ -f "$CKPT" ] || { echo "no such checkpoint: $CKPT"; exit 2 }
[ -n "$TAG" ] || { echo "usage: $0 <checkpoint.pt> <tag> [outdir]"; exit 2 }

REPO="${0:a:h}/../.."
B="$REPO/benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1"
# The score library is machine-local and gitignored; `library_root()` resolves
# it to the MAIN checkout even from inside a worktree, so ask it rather than
# assuming the store sits under this tree.
PDF="$(cd "$REPO" && python3 -c 'from tools.library.score_library import library_root
print(library_root() / "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")')"
[ -f "$PDF" ] || { echo "the Brahms 1 edition is not in this machine's score library: $PDF"; exit 2 }
CELLS=(brahms1-p2-sys0-s3-m4 brahms1-p2-sys0-s9-m0 brahms1-p3-sys0-s5-m5
       brahms1-p3-sys0-s9-m1 brahms1-p4-sys0-s0-m3 brahms1-p4-sys0-s10-m5)
mkdir -p "$OUT"
cd "$REPO"

# The OCR and contextual rungs are downstream of everything the pre-fill
# reads, and the margin reader alone costs ~70 s of model load per run —
# off on BOTH arms, so the comparison is of the detector and nothing else.
python3 -m tools.omr.transcribe "$PDF" --pages 1-3 \
    --out "$OUT/transcription.json" --weights "$CKPT" \
    --no-direction-text --no-contextual

SB="$OUT/bench"; rm -rf "$SB"; mkdir -p "$SB"
for f in cells.json detections verdicts reference.mxl windows.json batch_config.json; do
    [ -e "$B/$f" ] && ln -s "$B/$f" "$SB/$f"
done
ln -s "$OUT/transcription.json" "$SB/transcription.json"

python3 -m tools.omr.training.mxl_verdicts --bench-dir "$SB" \
    --transcription "$SB/transcription.json" --truth "$SB/reference.mxl" \
    --windows "$SB/windows.json" --dry-run > "$OUT/dryrun.txt" 2>&1
python3 -m tools.omr.training.mxl_verdicts --bench-dir "$SB" \
    --transcription "$SB/transcription.json" --truth "$SB/reference.mxl" \
    --windows "$SB/windows.json" --score --score-classes all --dry-run \
    --cells $CELLS > "$OUT/score.txt" 2>&1
python3 benchmarks/omr-prefill-admission-2026-09/probe_admission.py \
    --bench-dir "$SB" > "$OUT/probe.txt" 2>&1

echo "== $TAG: batch totals ==";   head -3 "$OUT/dryrun.txt"
echo "== $TAG: six-cell score =="; grep -E "precision|by admission" "$OUT/score.txt"
echo "== $TAG: probe =="; sed -n '/admission policies/,$p' "$OUT/probe.txt" | head -12
