#!/bin/bash
# Reproduce every figure in FINDINGS.md.
#
#   bash benchmarks/omr-document-identity-2026-09/run_all.sh
#
# ⚠️ STEP 1 NEEDS ONLY THE COMMITTED CATALOG AND THE PDFs; steps 2+ need the
# weights symlink and the engraved fixture, and take ~5 min (engraved) and
# ~2 min (scan). The RECORDS are gitignored at 13-17 MB and are rebuilt here.
#
# ⚠️ THE STAGED CLI TAKES NO DEFAULT WEIGHTS — omit --weights and every cell
# abstains `reader_unavailable` while the run completes, which is honest and
# reads exactly like a bad page.
#
# ⚠️ NO --musicxml ON A GATHER: the exporter is imported AFTER the gather, so
# an edit to export.py mid-run reaches it. Export separately, below.
set -eu

B=benchmarks/omr-document-identity-2026-09
E=benchmarks/omr-staged-engraved-2026-09
F=$E/out/fixture/beethoven-sym5-mvt1-m1-24
WE=tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt
WS=tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
LIB=library/editions/beethoven/symphony-5-op67
SCAN=$LIB/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf

# ── 1. IS EVERY HELD EDITION A SCAN? (no weights, no gather, 16 s) ──────────
python3 $B/classify_library.py --out $B/out/library-domains.json

# ── 2. the gathers. OMR_DOCUMENT_IDENTITY is DEFAULT ON. ───────────────────
[ -f "$B/out/engraved-p0p2-identity.record.json" ] || \
  python3 -u -m tools.omr.staged $F.pdf --pages 0-2 --dpi 300 --weights $WE \
      --out $B/out/engraved-p0p2-identity.record.json
[ -f "$B/out/litolff-p1-identity.record.json" ] || \
  python3 -u -m tools.omr.staged $SCAN --pages 1 --dpi 600 --weights $WS \
      --out $B/out/litolff-p1-identity.record.json

# ── 3. the CONTROL first: the rebuild must reproduce the record ────────────
python3 benchmarks/omr-staged-duration-beams-2026-09/readjudicate.py \
    $B/out/engraved-p0p2-identity.record.json --control

# ── 4. the A/B. It prints REACH first and exits DEAD at zero reach. ────────
python3 $B/keysig_domain_arm.py \
    --record $B/out/engraved-p0p2-identity.record.json \
    --truth-xml $F.musicxml --json-out $B/out/keysig-domain-arm.json

# ⚠️ EXPECTED TO EXIT 2 (DEAD) — the scan measures `scanned`, so the one-sided
# tier is a no-op there BY DESIGN. That is the fall-through working, and the
# arm says so rather than printing a clean table over an empty domain.
python3 $B/keysig_domain_arm.py \
    --record $B/out/litolff-p1-identity.record.json || true

# ── 5. what it does to the FILE ────────────────────────────────────────────
for f in 0 1; do
  OMR_ENGRAVED_KEYSIG=$f python3 \
      benchmarks/omr-staged-duration-beams-2026-09/readjudicate.py \
      $B/out/engraved-p0p2-identity.record.json --out $B/out/arm-$f.record.json
  python3 $E/export_record.py --record $B/out/arm-$f.record.json \
      --out $B/out/arm-$f.musicxml
  python3 $E/note_accuracy.py --ours $B/out/arm-$f.musicxml --truth $F.musicxml \
      --bars 20 --truth-first-bar 1 --json-out $B/out/note-accuracy-arm-$f.json
done

# ── 6. the scan fall-through, with its own vacuity control ────────────────
python3 $B/scan_is_untouched.py --record $B/out/litolff-p1-identity.record.json \
    --json-out $B/out/scan-untouched.json

# ── 7. every number in FINDINGS.md, re-derived (no weights, no library) ───
python3 $B/verify_findings.py

# ── 8. the battery ─────────────────────────────────────────────────────────
python3 $B/mutate.py
