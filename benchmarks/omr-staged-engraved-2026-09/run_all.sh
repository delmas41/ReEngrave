#!/bin/bash
# Reproduce every figure this lane reports, from the committed fixture.
#
#   bash benchmarks/omr-staged-engraved-2026-09/run_all.sh
#
# The fixture (MusicXML excerpt, SVGs, PNGs, PDF, page truth) is COMMITTED, so
# steps 1 and 2 need neither the score library nor gradus; steps 3+ need the
# weights (symlink tools/omr/training/data/weights) and take ~8 min.
#
# ⚠️ THE DPI IS THE SAME NUMBER EVERYWHERE OR NOTHING MATCHES. `page_truth`
# emits its boxes in image pixels at --dpi and the pipeline rasterises the PDF
# at its own --dpi; two different values differ by a pure scale factor and the
# failure looks like a recognition result (counts agree, positions do not).
#
# ⚠️ THE STAGED CLI DOES NO WEIGHT ROUTING — `staged/__main__.py` hands
# --weights straight to YoloDetector. This PDF classifies ENGRAVED on all 3
# pages, so the engraved-side checkpoint is pinned here, which is what routing
# would have chosen. The legacy arm pins the same file so the two compare.
set -eu

B=benchmarks/omr-staged-engraved-2026-09
F=$B/out/fixture/beethoven-sym5-mvt1-m1-24
W=tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt
DPI=300

# ── 1. the fixture (committed; re-run only to rebuild it) ────────────────────
# python3 $B/render_fixture.py --work beethoven-sym5-mvt1 --first 1 --last 24 \
#     --out-dir $B/out/fixture --dpi $DPI

# ── 2. the gathers ───────────────────────────────────────────────────────────
# ⚠️ NO --musicxml ON A GATHER. `staged/__main__.py` imports the exporter AFTER
# the gather, so an edit to export.py mid-run reaches it and can kill a
# finished gather with a NameError. Export separately, below.
#
# ⚠️ THE THREE-PAGE RUN IS THE CANONICAL ONE. Gathered a page at a time there is
# no previous system for OMR_METER_CARRY to carry from, so pages 1 and 2 abstain
# `bars_name_a_length_without_a_form`, every whole rest is written at the 4.0
# fallback in a 2.0 bar, and the note accuracy collapses. That is the recorded
# "one-page cut disables every page-spanning mechanism" hazard, not a reader
# fault. The single-page records are kept for the per-page reading scores, which
# are IDENTICAL either way (pages 0 and 2 reproduce to the symbol).
for P in 0 1 2; do
  [ -f "$B/out/engraved-p$P.record.json" ] || \
    python3 -u -m tools.omr.staged $F.pdf --pages $P --dpi $DPI --weights $W \
        --out $B/out/engraved-p$P.record.json
done
[ -f "$B/out/engraved-p0p2.record.json" ] || \
  python3 -u -m tools.omr.staged $F.pdf --pages 0-2 --dpi $DPI --weights $W \
      --out $B/out/engraved-p0p2.record.json

# the cross-reader arm: the LEGACY path, same page, same weights, same dpi
for P in 0 2; do
  [ -f "$B/out/legacy-p$P.omr.json" ] || \
    python3 -u -m tools.omr.transcribe $F.pdf --pages $P --dpi $DPI \
        --no-contextual --no-direction-text --weights $W \
        --out $B/out/legacy-p$P.omr.json
done

# ── 3. exports ───────────────────────────────────────────────────────────────
for P in 0 1 2 0p2; do
  python3 $B/export_record.py --record $B/out/engraved-p$P.record.json \
      --out $B/out/engraved-p$P.musicxml
done

# ── 4. READING — the staged gather against exact page truth ──────────────────
# --apply-ownership is the arm comparable to the legacy path, which DELETES the
# losing copy of a cross-staff contest where the staged path files a verdict.
for P in 0 1 2; do
  python3 $B/staged_reading.py --record $B/out/engraved-p0p2.record.json \
      --truth $F.pagetruth.json --page $P --apply-ownership \
      --json-out $B/out/reading-combined-p$P.json
done
for P in 0 2; do
  python3 $B/staged_reading.py --legacy $B/out/legacy-p$P.omr.json \
      --truth $F.pagetruth.json --page $P \
      --json-out $B/out/reading-legacy-p$P.json
done

# ── 5. where the staged path's extra ink comes from ──────────────────────────
for P in 0 2; do
  python3 $B/attribute_extras.py --record $B/out/engraved-p$P.record.json \
      --legacy $B/out/legacy-p$P.omr.json --page $P \
      --json-out $B/out/extras-p$P.json
done

# ── 6. the funnel, and the false `no_ink` claims ─────────────────────────────
for P in 0 1 2; do
  python3 -m tools.omr.staged.trace --run $B/out/engraved-p$P.record.json \
      --family note --export
  python3 -m tools.omr.staged.trace --run $B/out/engraved-p$P.record.json \
      --empty-claims
done

# ── 7. NOTE ACCURACY against the source encoding ─────────────────────────────
# ⚠️ --bars and --truth-first-bar come from the RENDER, not from a guess:
#    grep -c 'class="measure"' $F-p{1,2,3}.svg  ->  7 / 9 / 8
python3 $B/note_accuracy.py --ours $B/out/engraved-p0.musicxml --truth $F.musicxml \
    --bars 7 --truth-first-bar 1 --json-out $B/out/note-accuracy-p0.json
python3 $B/note_accuracy.py --ours $B/out/engraved-p0p2.musicxml --truth $F.musicxml \
    --bars 24 --truth-first-bar 1 --json-out $B/out/note-accuracy-p0p2.json
python3 $B/note_accuracy.py --ours $B/out/engraved-p0p2.musicxml --truth $F.musicxml \
    --bars 20 --truth-first-bar 1 \
    --json-out $B/out/note-accuracy-p0p2-bars1-20.json

# ── 8. <beam> and <alter> ────────────────────────────────────────────────────
python3 $B/beam_alter_check.py --ours $B/out/engraved-p0.musicxml \
    --truth $F.musicxml --bars 7 --truth-first-bar 1 \
    --json-out $B/out/beam-alter-p0.json
python3 $B/beam_alter_check.py --ours $B/out/engraved-p0p2.musicxml \
    --truth $F.musicxml --bars 24 --truth-first-bar 1 \
    --json-out $B/out/beam-alter-p0p2.json

# ── 9. the key signature: two readers on the same header crop ────────────────
python3 $B/alter_gap.py --record $B/out/engraved-p0.record.json \
    --json-out $B/out/alter-gap-p0.json
python3 $B/locator_vs_template.py --pdf $F.pdf --page 0 --dpi $DPI \
    --truth-xml $F.musicxml --record $B/out/engraved-p0.record.json \
    --dump-staff 0 --dump-x 450 780 \
    --json-out $B/out/locator-vs-template-p0.json
