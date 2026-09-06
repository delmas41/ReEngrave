"""End-to-end OMR transcription: PDF → structured symbol detections.

This is the **simplest entry point** for running the ReEngrave OMR pipeline
on a music PDF. Combines Phase 1 (staff + measure detection) with Phase 3.3
(YOLOv8l symbol detection at 98.8% F1 on the Bach WTC verdict set) into a
single command that writes a structured JSON report.

CLI:

    python3 -m tools.omr.transcribe path/to/score.pdf --out out.json

    # Specific pages, with overlays
    python3 -m tools.omr.transcribe score.pdf --pages 0-4 --out out.json \\
        --overlays-dir overlays/

    # Specify a different weights file
    python3 -m tools.omr.transcribe score.pdf \\
        --weights tools/omr/training/data/weights/<other>.pt \\
        --out out.json

Output schema (JSON):

    {
      "source_pdf": "score.pdf",
      "weights":    "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt",
      "weight_routing": {"mode": "routed", "verdict": "scanned", ...} | null,
      "conf_threshold": 0.25,
      "n_pages_processed": 3,
      "n_systems_total": 6,
      "n_staves_total": 30,
      "n_measures_total": 84,
      "n_detections_total": 1923,
      "n_noteheads_total": 412,             # all detections with category=="notehead"
      "n_noteheads_pitched_total": 405,     # those for which pitch resolution succeeded
      "runtime": {"phase1_s": 8.2, "yolo_s": 4.1, "total_s": 12.3},
      "pages": [
        {
          "page_index": 0,        # 0-based, matches pdf2image/fitz numbering
          "page_size_px": [w, h], # at the source render DPI (default 600)
          "n_systems": 2,
          "systems": [
            {
              "system_index": 0,
              "n_staves": 5,
              "staves": [
                {
                  "staff_index": 0,
                  "clef": "treble",         # effective clef for the staff (after
                                            # absorbing any clef detection in the
                                            # very first measure)
                  "clef_source": "cv_locator",  # OPTIONAL — which reader read
                                            # this clef: "detector",
                                            # "specialist" (--clef-weights), or
                                            # "cv_locator" (shape-located C clef,
                                            # tools/omr/clef_locator.py). ABSENT
                                            # = nothing read a clef here; the
                                            # staff carries an inherited clef or
                                            # the position default.
                  "key_signature_source": "header_vote",  # OPTIONAL — only when
                                            # the key signature came from the
                                            # staff-header pass (detector markers
                                            # fitted to the slot table, or the CV
                                            # locator) and was reconciled across
                                            # the page. Absent when the measure
                                            # pass supplied it. See
                                            # tools/omr/key_signature_locator.py
                                            # and key_signature_vote.py.
                  "key_signature_reason": "carried: agrees with the system's 3 flats",
                                            # OPTIONAL — accompanies
                                            # key_signature_source: what the
                                            # cross-page vote decided, and why.
                  "key_signature": {
                      "sharps": 0,          # count of sharps in the key sig
                      "flats":  0,          # count of flats (mutually exclusive)
                      "alterations": {"F": "#", "C": "#"}  # letter -> '#'|'b'
                  },
                  "key_signature_read": True,  # whether the zeros above are a
                                            # READING. False = nothing could
                                            # read this staff's signature, and
                                            # 0/0 is the empty default rather
                                            # than a finding — the distinction
                                            # a C minor page reporting "0
                                            # sharps, 0 flats" on every staff
                                            # depends on.
                  "key_signature_unread_reason": "no clef was read on this staff…",
                                            # OPTIONAL — present exactly when
                                            # key_signature_read is False.
                  "clef_final": "bass",     # OPTIONAL — only if clef changed
                                            # mid-staff (rare)
                  "key_signature_final": {...},  # OPTIONAL — only if key changed
                  "n_measures": 4,
                  "measure_count_warning": {   # OPTIONAL — only when this staff's
                                            # measure count disagrees with a STRICT
                                            # majority of the other staves in its
                                            # system (barlines run through the whole
                                            # system, so a deviation localizes a
                                            # missed or spurious barline). See
                                            # _flag_measure_count_inconsistency.
                      "staff_measures": 3,  # this staff's n_measures
                      "system_mode": 4,     # the count the majority of staves share
                      "agreement": "5/6",   # staves at the mode / total staves
                      "deviation": -1,      # signed: <0 too few (missed barline /
                                            #   condensed multi-measure rest),
                                            #   >0 too many (spurious barline)
                      "confidence": 0.833,  # consensus strength (mode fraction)
                      "confidence_label": "high",  # low | medium | high
                      "phase1_corroborated": true, # short staff + a >2×-median
                                            # cell WITH noteheads — a fused pair
                                            # of real measures (missed barline)
                      "likely_multimeasure_rest": false  # short staff whose gap
                                            # is a wide NOTE-EMPTY cell (condensed
                                            # multi-measure rest / tacet) — always
                                            # down-weighted to low, never promoted
                  },
                  "key_signature_warning": {   # OPTIONAL — only when this staff's
                                            # key signature can't be reconciled
                                            # with the concert key the majority of
                                            # staves share, via any standard
                                            # instrument transposition. See
                                            # _flag_key_signature_inconsistency.
                      "staff_key": "5 sharps",   # this staff's written key sig
                      "staff_fifths": 5,         # signed circle-of-fifths position
                      "concert_key": "C major",  # concert key explaining the majority
                      "consistent_written_fifths": [-3, 0, 1, 2, 3],  # allowed set
                      "agreement": "6/7",   # staves fitting the concert key / total
                                            #   with a (non-zero) key signature
                      "circle_distance": 2, # fifths from the nearest allowed value
                      "confidence": 0.857,
                      "confidence_label": "high"  # low | medium | high
                  },
                  "clef_register_warning": {   # OPTIONAL, ADVISORY — this (lower)
                                            # staff resolves an octave+ above the
                                            # staff above it: a possible clef
                                            # error, voice-crossing, or high
                                            # instrument. See
                                            # _flag_clef_register_inversion.
                      "lower_staff_index": 3, "upper_staff_index": 2,
                      "lower_staff_median_midi": 74, "upper_staff_median_midi": 55,
                      "register_gap_semitones": 15,  # p25(lower) - p75(upper)
                      "lower_staff_clef": "bass", "upper_staff_clef": "treble",
                      "confidence_label": "advisory"
                  },
                  "time_signature_disagreement": {  # OPTIONAL — only when this
                                            # staff's genuinely-DETECTED meter
                                            # disagrees with the rest of the
                                            # system (all staves share one meter,
                                            # so a detected disagreement is a
                                            # mis-read). See
                                            # _flag_time_signature_disagreement.
                      "staff_time_signature": "3/4",
                      "system_detected_meters": ["3/4", "4/4"],
                      "majority_meter": "4/4",  # null on a near-even split
                      "agreement": "3/4", "confidence": 0.75,
                      "confidence_label": "medium"
                  },
                  "time_signature": {"numerator": 4, "denominator": 4, "raw": "4/4"},
                                            # null if no time-sig markers seen
                  "group_index": 0,         # bracket block within the system
                                            # (winds | brass | strings). The
                                            # PAGE's own family grouping.
                                            # ⚠️ PRECISE BUT UNDER-RECALLED
                                            # (22/22 precise, 22/39 recalled):
                                            # anchor a family boundary where
                                            # present, ABSTAIN where absent.
                  "staff_geometry": {       # the five lines every geometric
                                            # reading above was measured
                                            # against. null when the staff was
                                            # not read as a clean 5-line staff.
                      "line_ys_page": [268, 291, 314, 337, 360],  # top → bottom
                      "line_spacing_px": 23.0,
                      "x_start": 186, "x_end": 1755,
                      # What those five ideal rows cost. Both are measured
                      # (staff_detector.measure_line_geometry) and both are
                      # null when the lines were too faint to trace.
                      "line_thickness_px": [4.0, 5.0, 4.0, 5.0, 4.0],
                                            # ink per line — what staff-line
                                            # removal has to erase
                      "line_wander_px": 1.5 # how far the printed line strays
                                            # from its nominal row
                  },
                  "measures": [
                    {
                      "measure_index": 0,
                      "bbox_page_px": [x0, y0, x1, y1],
                      "staff_line_ys_canonical": [100, 200, 300, 400, 500],
                                            # the same five lines in THIS
                                            # cell's canonical frame — the one
                                            # detections[].bbox is in. Cells
                                            # are scaled independently, so the
                                            # staff-level page geometry does
                                            # not describe this frame.
                      "upscale_factor": 2.13,   # canonical px per page px
                      "clef": "treble",     # active clef AT this measure
                      "key_signature": {...},  # active key sig at this measure
                      "time_signature": {...},  # active time sig at this measure
                      "n_detections": 12,
                      "detections": [
                        {
                          "class":      "noteheadBlack",
                          "category":   "notehead",
                          "bbox":       [x, y, w, h],  # in cell-local (canonical) coords
                          "bbox_page":  [x, y, w, h],  # in page-pixel coords
                          "confidence": 0.87,
                          "pitch":      "F#4",          # chromatic — key sig + inline
                                                        # accidentals applied
                          "duration_beats": 0.25,       # in quarter notes (1.0=quarter)
                          "duration_type":  "sixteenth",
                          "dots":           0           # number of augmentation dots
                        },
                        ...
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }

The "simplest transcription" path for a future agent / user:

    1. Render the PDF, find staves + measures (the OMR scaffolding).
    2. For each measure-cell, run YOLOv8l to detect notation symbols.
    3. Group detections by (system, staff, measure) and emit a JSON file.
    4. Optionally render overlay PNGs for visual inspection.

For richer downstream output (MusicXML, MIDI, LilyPond), this JSON is the
intermediate representation that other tools can consume.

Defaults are tuned for clean engraved PDFs (typeset music). Quality
degrades on handwritten or low-quality scanned scores; the model was
trained on the synthetic DeepScoresV2 corpus + ~60 hand-labeled real
orchestral cells. See benchmarks/omr-phase3.3/comparison-trained-v3.md
for the F1 numbers.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .preprocessing import render_page
from .staff_detector import detect_staves
from .measure_extractor import (detect_barlines, extract_measures,
                                majority_bars_by_system, resegment_fused_measures)
from .staff_line_removal import remove_staff_lines
from .types import MeasureCell, PageWithStaves, Staff
from .pitch_resolver import (pitch_candidates_for_notehead, pitch_for_notehead,
                             pitch_to_midi)
from .clef_geometry import clef_name_from_class, resolve_clef_for_detection
from .clef_locator import locate_clef
from .key_signature_geometry import (
    KeySignatureFitConfig,
    alterations_for_fifths,
    fit_key_signature,
)
from .key_signature_locator import locate_key_signature
from .key_signature_template import (
    read_key_signature as read_key_signature_by_template,
)
from .key_signature_vote import StaffCandidate, reconcile
from .staff_header import (
    HEADER_MEASURE_INDEX,
    HeaderWindow,
    header_cells_for_page,
    header_windows_for_page,
)
from .time_signature_locator import read_system_time_signatures
from .rhythm import (
    parse_time_signature,
    resolve_rhythms_for_cell,
    backfill_page_time_signatures,
    measure_length_beats,
    # The beam-level duration table and the dot arithmetic, so the meter→rhythm
    # correction below re-derives a duration exactly the way rhythm.py did.
    _BEAM_COUNT_DURATIONS,
    _dot_multiplier,
    _name_for_dots,
)
from .line_detection import detect_lines
from .voicing import group_chords_in_measure, split_events_into_voices
from .dossier import (
    apply_meter,
    slot_facts_for_page,
    slot_facts_for_system,
    check_total_measures,
    resolve_dossier,
    summarize as summarize_dossier_warnings,
    verify_page,
)


# Default weights — hollow head-graft + confidence floor (2026-09-04). NOT a
# training run: rounds 3-5 measured that fine-tuning on the scan-label corpus
# DELETES whole classes (tie/slur/beam/augmentationDot/... -> exactly 0) under
# every method tried, so this ship keeps only the hollow fine-tune's seven
# notehead-class head rows, grafts them onto the 09-03 production, and bakes a
# per-class confidence floor into those rows' biases (bias-shift 0.9 =
# threshold 0.25 -> 0.45). Beats the 09-03 hollow-ft on all three gate axes:
# half-noteheads 27 -> 31, pitch+duration recall 0.435 -> 0.510, dense recall
# 0.941 -> 1.000, scan-e2e pooled 0.7517 -> 0.7493 on a byte-deterministic
# harness, 28 classes with 0 collapsed. Record: ROUND5_METHOD_2026-09-04.md in
# benchmarks/omr-labeling-survey-2026-09/ (lands with branch
# claude/scan-weights-round4-continue-074940). The 09-03 hollow-ft and the
# imgsz-2048 checkpoint are kept alongside.
DEFAULT_WEIGHTS = (
    "tools/omr/training/data/weights/"
    "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
)

# Weights for DIGITALLY ENGRAVED input (vector PDFs), used by weight routing
# when the caller doesn't pin `weights`. The hollow ship run measured the two
# domains preferring different checkpoints: these prior production weights
# score 0.1399 pooled on the 11-work engraved benchmark against the hollow
# fine-tune's 0.1421 (no-direction-text, SHIP_RESULTS.md §4c), while the
# hollow fine-tune wins on scans (half-notes 8 -> 27 on beet5-p1). Routing
# lets each domain keep its best-measured weights instead of one slot paying
# the other's cost. Env override: OMR_ENGRAVED_WEIGHTS; kill switch:
# OMR_WEIGHT_ROUTING=0. See benchmarks/omr-weight-routing-2026-09/FINDINGS.md.
ENGRAVED_WEIGHTS = (
    "tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"
)


# ---------------------------------------------------------------------------
# Clef inference helpers (Phase 4a — pitch resolution)
# ---------------------------------------------------------------------------
#
# Each notehead's pitch depends on the active clef of its staff. The detector
# emits clef detections (clefG → treble, clefF → bass, clefCAlto → alto, etc.)
# and we maintain an `active_clef` per staff that updates whenever a new clef
# detection appears. Default per-position heuristics handle the case where the
# first cell of a staff has no detected clef (rare on engraved music, but
# possible on a continuation page where the courtesy clef wasn't picked up).


def _clef_name_from_class(smufl: str) -> str | None:
    """Map a DSv2 clef class name to a pitch_resolver clef key, from the class
    label ALONE.

    This is the weak reading: it cannot tell an alto clef from a tenor one any
    better than the detector can, because they are the same glyph on different
    lines. It survives as the fallback for when geometry can't run (see
    `clef_geometry.resolve_clef`), and returns None for unpitched /
    octave-marker clefs (clef8 / clef15 attach to a base clef and are picked up
    by `_octave_shift_for_base_clef`).
    """
    return clef_name_from_class(smufl)


def _octave_shift_for_base_clef(dets, base_clef_det) -> str:
    """Look for clef8 / clef15 detections positioned near `base_clef_det`
    (the chosen base-clef detection in a cell). Returns the pitch_resolver
    suffix to append to the base clef name:

      ""       — no octave marker
      "_8va"   — clef8 ABOVE the base clef (sounds an octave higher)
      "_8vb"   — clef8 BELOW the base clef (octave lower)
      "_15ma"  — clef15 ABOVE (two octaves higher)
      "_15mb"  — clef15 BELOW (two octaves lower)

    Pairing heuristic: an octave glyph "belongs to" a base clef if their
    x-centers are within one base-clef-width of each other. Above vs
    below is decided by y-center.

    Returns "" if `base_clef_det` is None or no octave marker is found.
    """
    if base_clef_det is None:
        return ""
    base_xc = base_clef_det.x_canonical + base_clef_det.width_canonical / 2.0
    base_yc = base_clef_det.y_canonical + base_clef_det.height_canonical / 2.0
    x_tolerance = max(base_clef_det.width_canonical, 50)

    best_marker = None  # (kind, dx, is_above)
    for d in dets:
        s = (d.smufl_name or "").lower()
        if s not in ("clef8", "clef15"):
            continue
        m_xc = d.x_canonical + d.width_canonical / 2.0
        m_yc = d.y_canonical + d.height_canonical / 2.0
        dx = abs(m_xc - base_xc)
        if dx > x_tolerance:
            continue
        # Pick whichever octave marker is closest horizontally
        if best_marker is None or dx < best_marker[1]:
            best_marker = (s, dx, m_yc < base_yc)

    if best_marker is None:
        return ""
    kind, _dx, is_above = best_marker
    if kind == "clef8":
        return "_8va" if is_above else "_8vb"
    # clef15
    return "_15ma" if is_above else "_15mb"


def _notehead_fill_ratio(notehead, cell) -> float | None:
    """Sample the inner pixels of a notehead's bbox and report the
    fraction that are dark (ink). Used to disambiguate the YOLO model's
    occasional misclassification of HOLLOW noteheads (half/whole) as
    filled (black).

    Returns None if the cell image is missing or the crop is empty.
    """
    img = getattr(cell, "image", None)
    if img is None or img.size == 0:
        return None
    if img.ndim == 3:
        import cv2 as _cv
        gray = _cv.cvtColor(img, _cv.COLOR_BGR2GRAY)
    else:
        gray = img
    x = notehead.x_canonical
    y = notehead.y_canonical
    w = notehead.width_canonical
    h = notehead.height_canonical
    # Inset 20% to avoid notehead-edge ink (the outline of hollow noteheads
    # is dark, but the center is paper).
    ix = max(1, int(w * 0.20))
    iy = max(1, int(h * 0.20))
    x0, y0 = max(0, x + ix), max(0, y + iy)
    x1 = min(gray.shape[1], x + w - ix)
    y1 = min(gray.shape[0], y + h - iy)
    if x1 <= x0 or y1 <= y0:
        return None
    crop = gray[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    return float((crop < 128).sum() / crop.size)


def _correct_notehead_class_by_fill(
    notehead, cell, has_stem: bool = True
) -> None:
    """If a notehead's inner-pixel fill ratio contradicts its class
    (e.g., classified as 'noteheadBlack*' but mostly hollow), rewrite
    `notehead.smufl_name` to the correct hollow class. Mutates in place.

    Calibrated thresholds (from Handel-Messiah-reduction pixel survey):
      fill > 0.75: filled → noteheadBlack*  (keep)
      0.35 ≤ fill ≤ 0.75: hollow → noteheadHalf* OR noteheadWhole*
                            depending on `has_stem` (whole notes have
                            no stem; halves do)
      fill < 0.35: clearly empty → noteheadWhole*

    `has_stem` is computed by the caller from the classical-CV stem
    detector. Passing it through here disambiguates the 'borderline
    hollow' cases (fill 0.35–0.75) that could be either a half or
    a whole.

    Only swaps WITHIN the Black/Half/Whole family. Doubles, smalls,
    and other notehead variants are left alone.
    """
    name = getattr(notehead, "smufl_name", "") or ""
    lname = name.lower()
    if not lname.startswith("notehead"):
        return
    suffix = ""
    for candidate in ("OnLineSmall", "InSpaceSmall", "OnLine", "InSpace", "Small"):
        if name.endswith(candidate):
            suffix = candidate
            break
    if "black" not in lname:
        return

    fill = _notehead_fill_ratio(notehead, cell)
    if fill is None:
        return
    if fill > 0.75:
        return  # really is filled — no change
    # Hollow notehead. Whole notes have no stem; halves do.
    if has_stem:
        target = f"noteheadHalf{suffix}" if suffix else "noteheadHalf"
    else:
        target = f"noteheadWhole{suffix}" if suffix else "noteheadWhole"
    notehead.smufl_name = target


# ---------------------------------------------------------------------------
# Ink clipped at a cell's edge is not a notehead (2026-09-01)
# ---------------------------------------------------------------------------
#
# A cell is the staff plus four staff spaces of air above and below
# (`measure_extractor.PAD_ABOVE_STAFF_LINES`), and on a conductor's page four
# spaces reaches into whatever the neighbouring staff printed. Whatever is
# sitting there gets sliced by the crop, and a wide flat sliver of ink is
# exactly what a hollow notehead looks like.
#
# Measured on the engraved Brahms 1 benchmark page, where the truth contains no
# whole note at all: SEVEN `noteheadWholeInSpace` detections, and every one of
# them is a fragment flush against a cell's top or bottom edge — no whole
# notehead was detected anywhere in the interior of any cell. Reading the pixels
# back says what each one really is:
#
#     staff  5 m0   the bowl of the "g" in the word "legato", printed between staves
#     staff  6 m0   the same "g", one staff down
#     staff  8 m0   the lower bowl of the "8" of the 6/8 above it
#     staff 11 m0   the top of Eb Horn 4's notehead, one staff BELOW
#     staff 11 m2   C Horn 2's dotted half, one staff ABOVE — three times
#
# So the fault is geometric, not a header misread: `WRONG_NOTE_ATTRIBUTION`
# filed these under "the clef and key signature sit in the first bar", which is
# true of only three of the seven and is not what any of them are.
#
# The discriminator is the one thing a notehead cannot vary: it is a staff space
# tall, because that is what a notehead IS. Measured over the 594 noteheads
# wholly inside their cell across the three benchmark works, heights run
# 0.61-1.12 spaces and only three are below 0.80; the fragments run 0.29-0.56.
# Notes that legitimately touch a cell edge — Flute 1's and Violin 1's F6 — are
# 0.77-0.99, because a note the crop only grazes is still nearly all there. So
# the constant below is not tuned to a corpus: it sits in an empty band, and the
# two groups differ in kind rather than degree.
# (`benchmarks/omr-ned-2026-08/probe_edge_fragments.py` re-measures this.)
#
# Restricted to detections that TOUCH an edge, which is the mechanism. A short
# notehead in the middle of a cell is some other problem and this must not have
# an opinion about it. Nothing is reclassified: a fragment is not a smaller
# notehead, it is not one.

#: Below this fraction of a staff space, an edge-touching notehead is a slice of
#: something else. It sits in the empty band between the largest fragment (0.56)
#: and the smallest genuine EDGE-TOUCHING notehead (0.77) on the benchmark.
_CLIPPED_NOTEHEAD_MAX_SPACES = 0.6

#: How close to the crop boundary counts as touching it. A detection whose box
#: starts on row 0 was cut by the crop; one a pixel in was not necessarily.
_CELL_EDGE_TOLERANCE_PX = 1


def _drop_clipped_notehead_fragments(
    dets: list, cell: MeasureCell, *,
    max_height_spaces: float = _CLIPPED_NOTEHEAD_MAX_SPACES,
) -> tuple[list, int]:
    """Drop noteheads that are a sliver of ink cut off by the cell boundary.

    Returns `(kept, n_dropped)`. Abstains — returns everything — when the cell
    carries no usable staff-line geometry to measure a staff space with.
    """
    ys = sorted(cell.staff_line_ys_canonical or [])
    if len(ys) < 2:
        return dets, 0
    spacing = (ys[-1] - ys[0]) / (len(ys) - 1)
    if spacing <= 0:
        return dets, 0
    limit = max_height_spaces * spacing
    height = cell.image.shape[0]
    kept, dropped = [], 0
    for d in dets:
        if getattr(d, "category", "") == "notehead" and d.height_canonical < limit:
            top = d.y_canonical
            bottom = top + d.height_canonical
            if (top <= _CELL_EDGE_TOLERANCE_PX
                    or bottom >= height - _CELL_EDGE_TOLERANCE_PX):
                dropped += 1
                continue
        kept.append(d)
    return kept, dropped


# ---------------------------------------------------------------------------
# Tremolo / arpeggiato / ornament stem-rejection (audit follow-up, 2026-07)
# ---------------------------------------------------------------------------
#
# line_detection.detect_stems finds tall, narrow, near-vertical ink runs —
# a shape tremolo slash marks and arpeggiato squiggles also have. Verified
# on real orchestral pages (Debussy "La Mer", Edition Peters/IMSLP scan):
# the classical-CV stem detector picks up arpeggiato glyphs as extra
# "stems" whose bbox overlaps 40-95% of a YOLO-detected arpeggiato glyph's
# area, and on 6/8 sampled cells where this fired, removing the phantom
# stem changed which real stem `_stem_for_notehead` / `_find_attached_stem`
# picked (and therefore the notehead's beam-anchored duration and/or
# inferred stem direction) — i.e. this is not just theoretical, the
# phantom stems do get selected as a notehead's "closest" stem in
# practice on dense pages. Since YOLO reliably detects these glyphs
# (tremolo1-5, arpeggiato, the ornament* trill/turn/mordent marks — all
# DSv2 classes under yolo_detector._CATEGORY_MAP's "ornament" category),
# we can reject any CV stem whose bbox is substantially covered by one.

_TREMOLO_ORNAMENT_CLASSES = frozenset({
    "tremolo1", "tremolo2", "tremolo3", "tremolo4", "tremolo5",
    "arpeggiato",
    "ornamenttrill", "ornamentturn", "ornamentturninverted", "ornamentmordent",
})


def _is_tremolo_or_ornament_det(d) -> bool:
    name = "".join(ch for ch in (getattr(d, "smufl_name", "") or "").lower() if ch.isalnum())
    return name in _TREMOLO_ORNAMENT_CLASSES


def _bbox_overlap_area(a, b) -> int:
    """Intersection area (canonical px^2) between two bbox-like objects
    exposing x_canonical/y_canonical/width_canonical/height_canonical."""
    ax0, ay0 = a.x_canonical, a.y_canonical
    ax1, ay1 = ax0 + a.width_canonical, ay0 + a.height_canonical
    bx0, by0 = b.x_canonical, b.y_canonical
    bx1, by1 = bx0 + b.width_canonical, by0 + b.height_canonical
    iw = max(0, min(ax1, bx1) - max(ax0, bx0))
    ih = max(0, min(ay1, by1) - max(ay0, by0))
    return iw * ih


def _filter_stems_overlapping_tremolo(
    stems: list, dets, *, min_overlap_fraction: float = 0.3
) -> list:
    """Drop CV stem candidates that are actually tremolo / arpeggiato /
    ornament ink rather than a real note stem.

    A stem is rejected when its bbox overlaps a YOLO tremolo/arpeggiato/
    ornament detection (`_TREMOLO_ORNAMENT_CLASSES`) by at least
    `min_overlap_fraction` of the STEM's own area. Using the stem's area
    (not the ornament glyph's, which is often much bigger — e.g. an
    arpeggio squiggle spanning a whole chord) as the denominator keeps
    this conservative: only a stem candidate that is substantially
    "inside" the ornament glyph gets dropped, not one that merely grazes
    one at the edge.

    No-op when `dets` has no tremolo/arpeggiato/ornament detections — the
    overwhelmingly common case (most pages/cells have none) is completely
    unaffected.
    """
    if not stems:
        return stems
    ornament_dets = [d for d in dets if _is_tremolo_or_ornament_det(d)]
    if not ornament_dets:
        return stems
    kept = []
    for s in stems:
        s_area = max(1, s.width_canonical * s.height_canonical)
        if any(
            _bbox_overlap_area(s, o) / s_area >= min_overlap_fraction
            for o in ornament_dets
        ):
            continue
        kept.append(s)
    return kept


def _find_attached_stem(notehead, stems):
    """Pair a notehead to its stem (classical-CV stems).

    A stem touches a notehead if:
      - its x is within 0.6 notehead-widths of the notehead's x-edge
      - its y-range overlaps the notehead's y-range

    Among candidates, prefer the closest (smallest x-gap).
    """
    nh_x_l = notehead.x_canonical
    nh_x_r = notehead.x_canonical + notehead.width_canonical
    nh_y_top = notehead.y_canonical
    nh_y_bot = notehead.y_canonical + notehead.height_canonical
    max_dx = max(notehead.width_canonical * 0.6, 12)
    best = None
    best_dx = float("inf")
    for s in stems:
        s_x_l = s.x_canonical
        s_x_r = s.x_canonical + s.width_canonical
        if s_x_r < nh_x_l:
            dx = nh_x_l - s_x_r
        elif s_x_l > nh_x_r:
            dx = s_x_l - nh_x_r
        else:
            dx = 0
        if dx > max_dx:
            continue
        s_y_top = s.y_canonical
        s_y_bot = s.y_canonical + s.height_canonical
        if s_y_bot < nh_y_top - 5 or s_y_top > nh_y_bot + 5:
            continue
        if dx < best_dx:
            best_dx = dx
            best = s
    return best


def _stem_direction(stem, noteheads) -> str:
    """Decide a STEM's direction ('up' / 'down') from where it projects past
    the noteheads hanging on it.

    Stem-up: the stem extends ABOVE the notes (they sit at its foot).
    Stem-down: it extends BELOW them.

    DIRECTION BELONGS TO THE STEM, NOT TO EACH NOTEHEAD, which is why this
    takes all the noteheads attached to one stem at once. It used to compare a
    single notehead's centre against the stem's MIDPOINT, one notehead at a
    time — and a double stop is two noteheads on one stem, so for any interval
    wider than the stem is long the same stem came out above the lower note's
    centre and below the upper one's. The two members of one chord were then
    handed opposite directions.

    That reads as divisi. `voicing.group_chords_in_measure` refuses to merge
    noteheads whose directions disagree, on the sound principle that a real
    chord shares one physical stem — so the chord was split into two voices and
    exported through a `<backup>`, one note per voice. Measured on Brahms's
    Viola, which plays double stops throughout: `C4/C5` (an octave) came out as
    `C4` and then `C5` at the end of the bar, and `A♭3/C5` (a tenth) likewise.
    Thirds were unaffected, which is what made the fault look intermittent.

    Comparing the projections rather than the midpoint also generalises the old
    rule rather than replacing it: for a single notehead the stem overhangs on
    exactly one side, and the answer is the same one it always gave.
    """
    heads = list(noteheads) if isinstance(noteheads, (list, tuple)) else [noteheads]
    if not heads:
        return "up"
    top = min(nh.y_canonical for nh in heads)
    bottom = max(nh.y_canonical + nh.height_canonical for nh in heads)
    above = top - stem.y_canonical
    below = (stem.y_canonical + stem.height_canonical) - bottom
    return "up" if above > below else "down"


def _default_clef_for_position(position_in_system: int, system_size: int) -> str:
    """Best-guess clef before we see any clef detection.

    Piano-style (2 staves per system): top = treble, bottom = bass.
    Single-staff or anything-else default = treble. The first detected clef
    in the staff overrides this, so the default only matters when the
    detector misses the courtesy clef at the start of the staff.
    """
    if system_size == 2 and position_in_system == 1:
        return "bass"
    return "treble"


class _ClefContinuity:
    """Track the last effective clef at each staff ROLE (vertical position
    within a system) so a continuation system/page that doesn't re-print a
    clef can inherit it by role, instead of falling back to the position
    default (treble, or bass for staff-2-of-2) and silently transposing a
    whole staff. Only inherits from a same-sized previous system (a differing
    staff count means the layout changed and roles no longer line up); a
    detected clef always overrides the starting value. Threaded through the
    system/staff loops in `transcribe`.

    For 2-staff piano the inherited clef equals the position default (top
    treble / bottom bass), so clean piano output is unaffected.
    """

    def __init__(self) -> None:
        self._by_role: dict[int, str] = {}   # role -> last system's clef
        self._prev_size: int | None = None
        self._inherit: dict[int, str] = {}   # what THIS system may inherit
        self._current: dict[int, str] = {}   # this system's roles, building
        self._size: int | None = None

    def start_system(self, system_size: int) -> None:
        self._inherit = self._by_role if self._prev_size == system_size else {}
        self._current = {}
        self._size = system_size

    def starting_clef(self, position: int, default: str) -> str:
        """Clef to start a staff with before its cells are read (a detected
        clef overrides). The inherited clef for this role, else `default`."""
        inherited = self._inherit.get(position)
        return inherited if inherited is not None else default

    def record(self, position: int, effective_clef: str) -> None:
        """Store a staff's effective clef (after its cells) for its role."""
        self._current[position] = effective_clef

    def end_system(self) -> None:
        self._by_role = self._current
        self._prev_size = self._size


# ---------------------------------------------------------------------------
# Key signature + accidental helpers (Phase 4b — chromatic pitch)
# ---------------------------------------------------------------------------
#
# Layered alteration logic when resolving a notehead's final pitch:
#
#   1. Inline accidental immediately to the left of THIS notehead  → wins
#   2. Earlier inline accidental on the same letter+octave in this measure
#      (accidentals carry through the rest of the measure until a barline) → next
#   3. Key signature alteration on this letter → fallback
#   4. Otherwise → diatonic pitch unchanged
#
# Standard order of sharps / flats in key signatures:
#   sharps: F# C# G# D# A# E# B#
#   flats:  Bb Eb Ab Db Gb Cb Fb
# Counting keySharp / keyFlat detections in the cell + this order gives us the
# full key signature.

_SHARP_ORDER = ["F", "C", "G", "D", "A", "E", "B"]
_FLAT_ORDER = ["B", "E", "A", "D", "G", "C", "F"]


def _key_sig_alterations(n_sharps: int, n_flats: int) -> dict[str, str]:
    """Build the {letter: '#'|'b'} alteration map for a key signature.

    Caller picks n_sharps XOR n_flats (the other should be 0). If both are
    0 returns {} (C major / A minor — no alterations).
    """
    if n_sharps > 0:
        return {letter: "#" for letter in _SHARP_ORDER[:n_sharps]}
    if n_flats > 0:
        return {letter: "b" for letter in _FLAT_ORDER[:n_flats]}
    return {}


# A detected keySharp / keyFlat is a glyph the model recognised, so a set of
# them with one stray is a good signature plus noise — see max_outliers.
_DETECTOR_FIT_CONFIG = KeySignatureFitConfig(max_outliers=1)


def _detect_key_sig_from_cell(dets, cell=None, clef: str | None = None) -> dict[str, str] | None:
    """Read the key signature from the detector's keySharp / keyFlat markers
    (which DSv2 emits distinctly from inline accidentals). Returns the new
    alteration map, or None if no markers were seen (so the caller keeps the
    previous active key sig).

    Where the geometry can run — a cell with clean 5-line staff geometry and a
    clef with a slot table — the markers' POSITIONS decide, not their count.
    Counting is what this used to do, and counting is wrong in a specific,
    common way: it believes exactly what the detector saw. Measured on WTC p.17
    (E major, four sharps, a clean modern engraving where the detector fires on
    every staff), counting reads 6 of 10 staves right and the four failures are
    +1, +1, +2 and +5 — three truncated counts and one spurious extra, on a page
    where every staff prints the same four sharps.

    The slot fit catches all four shapes: sharps found at slots 1, 2 and 4 are
    four sharps with the third missed rather than three, and a marker that sits
    on no slot at all stops counting toward the total. See
    `key_signature_geometry`.

    Falls back to the count when geometry can't run or the fit abstains, so a
    reading is never lost — only improved on.
    """
    sharps = [d for d in dets if d.smufl_name.lower().startswith("keysharp")]
    flats = [d for d in dets if d.smufl_name.lower().startswith("keyflat")]
    if not sharps and not flats:
        return None  # no update — keep whatever was active
    # Music never has both sharps and flats in one key signature; if the
    # detector emits both, the larger group is the real one.
    markers, accidental = (sharps, "#") if len(sharps) >= len(flats) else (flats, "b")

    positions = _staff_positions_for(markers, cell)
    if positions is not None:
        # One stray marker may be set aside here; the locator's noisier
        # clusters get no such licence. See KeySignatureFitConfig.max_outliers.
        read = fit_key_signature(
            positions, clef, accidental, _DETECTOR_FIT_CONFIG,
        )
        if read is not None and read.fifths:
            return alterations_for_fifths(read.fifths)

    n = len(markers)
    return _key_sig_alterations(n, 0) if accidental == "#" else _key_sig_alterations(0, n)


def _key_sig_read_from_dets(dets, cell, clef: str | None):
    """Fit the detector's key-signature markers to the slot table.

    Returns the `KeySignatureRead` (so a caller can see how many slots were
    actually matched, which is what the cross-page vote weights by), or None
    when there are no markers, no usable staff geometry, no slot table for the
    clef, or nothing that fits.
    """
    sharps = [d for d in dets if d.smufl_name.lower().startswith("keysharp")]
    flats = [d for d in dets if d.smufl_name.lower().startswith("keyflat")]
    if not sharps and not flats:
        return None
    markers, accidental = (sharps, "#") if len(sharps) >= len(flats) else (flats, "b")
    positions = _staff_positions_for(markers, cell)
    if positions is None:
        return None
    return fit_key_signature(positions, clef, accidental, _DETECTOR_FIT_CONFIG)


def _staff_positions_for(detections, cell) -> list[float] | None:
    """Detection box centres as diatonic steps below the top staff line, in
    x-order — the unit `key_signature_geometry`'s slot tables use.

    None when the cell has no usable 5-line geometry, which is the signal to
    fall back rather than fit against a staff we can't measure.
    """
    if cell is None or not detections:
        return None
    ys = cell.staff_line_ys_canonical
    if not ys or len(ys) != 5:
        return None
    lines = sorted(float(y) for y in ys)
    spacing = (lines[-1] - lines[0]) / 4.0
    if spacing <= 0:
        return None
    half = spacing / 2.0
    ordered = sorted(detections, key=lambda d: d.x_canonical)
    return [
        ((d.y_canonical + d.height_canonical / 2.0) - lines[0]) / half
        for d in ordered
    ]


def _parse_inline_accidental(smufl: str) -> str | None:
    """Map an accidentalSharp / Flat / Natural / DoubleSharp / DoubleFlat
    class name to a short alteration string ('#', 'b', '##', 'bb', 'natural').
    Returns None if `smufl` isn't an inline accidental class.
    """
    if not smufl:
        return None
    s = smufl.lower()
    if not s.startswith("accidental"):
        return None
    if "doublesharp" in s:
        return "##"
    if "doubleflat" in s:
        return "bb"
    if "sharp" in s:
        return "#"
    if "flat" in s:
        return "b"
    if "natural" in s:
        return "natural"
    return None


def _pair_accidentals_to_noteheads(dets) -> dict[int, str]:
    """Pair each inline accidental detection with the nearest notehead to
    its right at roughly the same vertical position. Returns {id(notehead):
    alteration_str}.

    Geometry rule:
      - notehead must be at or to the right of the accidental's right edge
      - notehead's y-center must be within ~0.6 × accidental height of the
        accidental's y-center (i.e. on the same staff line / space)
      - among candidates, pick the one with the smallest weighted distance
        (3× y-penalty + x-penalty) — prefer same-line, very-close
    """
    accidentals = []
    noteheads = []
    for d in dets:
        if d.category == "accidental":
            alt = _parse_inline_accidental(d.smufl_name)
            if alt is not None:
                accidentals.append((d, alt))
        elif d.category == "notehead":
            noteheads.append(d)

    result: dict[int, str] = {}
    for acc, alt in accidentals:
        acc_right = acc.x_canonical + acc.width_canonical
        acc_y_center = acc.y_canonical + acc.height_canonical // 2
        acc_height = max(1, acc.height_canonical)

        best: Any = None
        best_score = float("inf")
        for nh in noteheads:
            # Notehead must reach to or past the accidental's right edge.
            if nh.x_canonical + nh.width_canonical < acc_right:
                continue
            nh_y_center = nh.y_canonical + nh.height_canonical // 2
            y_dist = abs(nh_y_center - acc_y_center)
            if y_dist > acc_height * 0.6:
                continue
            x_dist = max(0, nh.x_canonical - acc_right)
            score = x_dist + 3 * y_dist
            if score < best_score:
                best_score = score
                best = nh
        if best is not None:
            result[id(best)] = alt
    return result


def _parse_diatonic_pitch(pitch: str) -> tuple[str, int] | None:
    """Parse 'G4' / 'A2' into (letter, octave). pitch_for_notehead always
    returns just letter+octave (no accidentals) so this is straightforward.
    """
    if not pitch or len(pitch) < 2 or pitch[0] not in "ABCDEFG":
        return None
    try:
        return pitch[0], int(pitch[1:])
    except ValueError:
        return None


def _build_pitch(letter: str, alteration: str | None, octave: int) -> str:
    """('G', '#', 4) → 'G#4'.  ('A', None, 2) → 'A2'."""
    return f"{letter}{alteration or ''}{octave}"


def _key_sig_fifths(alterations: dict[str, str]) -> int:
    """An alteration map as a signed circle-of-fifths position (+N sharps /
    −N flats), the form `key_signature_vote` speaks."""
    return sum(1 for v in alterations.values() if v == "#") - sum(
        1 for v in alterations.values() if v == "b"
    )


def _key_sig_summary(alterations: dict[str, str]) -> dict[str, Any]:
    """Friendly summary of an alteration map for the output JSON.

    Returns {sharps, flats, alterations} where sharps/flats are counts and
    alterations is the raw {letter: '#'|'b'} dict.
    """
    n_sharps = sum(1 for v in alterations.values() if v == "#")
    n_flats = sum(1 for v in alterations.values() if v == "b")
    return {
        "sharps": n_sharps,
        "flats": n_flats,
        "alterations": dict(alterations),
    }


def _staff_geometry(staff: Staff | None) -> dict[str, Any] | None:
    """The staff's own five lines, in page pixels, for the output JSON.

    Every geometric reading in this pipeline is a measurement against these
    lines: which line a clef names (`clef_geometry`), which line or space a
    notehead sits on (`pitch_resolver`), where a key signature's accidentals
    fall in the slot table (`key_signature_geometry`). The *readings* were
    emitted; the frame they were measured in was not, so nothing downstream
    could check a clef against the staff it sits on, re-derive a pitch from a
    box, or repeat any snap — the geometry lived only for the length of the
    run. This block is that frame, written down.

    Returns None for a staff without a clean 5-line reading, matching the
    abstain-when-blind rule the geometric readers themselves follow: the
    line-numbering the clef table and the slot tables are defined on only
    means anything on five lines.
    """
    if staff is None or len(staff.line_ys) != 5:
        return None
    geom: dict[str, Any] = {
        "line_ys_page": [int(y) for y in staff.line_ys],
        "line_spacing_px": round(float(staff.line_spacing_px), 3),
        "x_start": int(staff.x_start),
        "x_end": int(staff.x_end),
    }
    # What the five ideal rows above cost: how much ink each printed line
    # actually occupies, and how far it strays from its row. Both are
    # measurements of what staff-line removal erases (`measure_line_geometry`);
    # null when the lines were too faint or broken to trace.
    geom["line_thickness_px"] = (
        [round(float(t), 3) for t in staff.line_thickness_px]
        if staff.line_thickness_px
        else None
    )
    geom["line_wander_px"] = (
        round(float(staff.line_wander_px), 3)
        if staff.line_wander_px is not None
        else None
    )
    return geom


def parse_pages(spec: str, n_pages: int) -> list[int]:
    """Accept '0,4,9' or '0-4' or '' (default all)."""
    if not spec:
        return list(range(n_pages))
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return [p for p in out if 0 <= p < n_pages]


# ---------------------------------------------------------------------------
# Header-crop DPI normalization for the clef specialist
# ---------------------------------------------------------------------------
#
# `_build_measure_cell` already rescales every cell -- header crops included --
# to a FIXED canonical staff span (measure_extractor.CANONICAL_STAFF_SPAN_PX)
# regardless of source DPI, so the SCALE the specialist is shown never varies
# with the page's render DPI: measured identical (40.0 canonical px of "shown"
# staff space per `yolo_detector.imgsz_for_cell`'s own formula) at dpi 300 and
# dpi 600 on the same staff. That rules out imgsz as the cause.
#
# What DOES vary is TEXTURE. The raw crop's pixel resolution is proportional
# to render DPI, so the upscale factor needed to reach the fixed canonical
# span is inversely proportional to it (measured: 12.9x at dpi 300, 6.45x at
# dpi 600 on the same staff -- exactly 2x apart, matching the 2x DPI gap).
# `cv2.INTER_CUBIC` at a large upscale factor from a low-res source smooths
# heavily; the same target size reached with half the upscale factor from an
# already-higher-res source stays sharp and aliased. Measured Laplacian-
# variance sharpness of the identical clef glyph: 2.61 (dpi 300) vs 36.56
# (dpi 600) -- ~14x. The specialist's own tuning scripts (tune_header_reader.py,
# clef_ground_truth_eval.py) all default to dpi=300, so that heavily-smoothed
# texture is the only regime the checkpoint has ever been tuned against.
#
# Measured end to end on Beethoven 5 p.48 (17 staves, deepscoresv2-yolov8l-
# clef-ft-boxfix-2026-07-13.pt): dpi 300 -> 17/17 clef-category detections;
# dpi 600 via the normal page-render-then-canonical-upscale path -> 0/17, at
# any confidence down to 0.05 -- the checkpoint finds no clef-shaped ink at
# all there, not just low-confidence ones. A post-hoc blur of the already-
# rendered dpi-600 raster does NOT recover it (tried: 2x INTER_AREA down /
# INTER_CUBIC back up -- 0 recovered on 6 staves): MuPDF's own resampling at
# render time produces a different antialiasing signature than filtering an
# already-hard-edged raster after the fact.
#
# Fix: re-render the SAME header window straight from the PDF at the
# reference DPI -- a fresh MuPDF rasterization of that one small region, not
# a resample of the already-rendered full-page raster -- then run the
# ordinary canonical upscale on THAT. Recovers all 17/17 detections on the
# same page (conf >= 0.10, median clef confidence ~0.7).

HEADER_SPECIALIST_REFERENCE_DPI = 300


def _rerender_header_at_reference_dpi(
    cell: MeasureCell,
    *,
    pdf_path: Path | str | None,
    page_dpi: int | None,
    reference_dpi: int = HEADER_SPECIALIST_REFERENCE_DPI,
) -> MeasureCell | None:
    """Re-render `cell`'s page region straight from the PDF at `reference_dpi`
    and re-run the canonical upscale on it, for the clef SPECIALIST only.

    Returns None (caller falls back to `cell` unchanged) when there is
    nothing to fix (`page_dpi` already at or below the reference, or no PDF
    to go back to) or the re-render fails for any reason -- this is a texture
    correction for one opt-in reader, never a reason to break a transcription.
    Never mutates `cell`; `key_signature_locator` / `clef_locator` and every
    other consumer of the same header cell keep seeing the original image.
    """
    if pdf_path is None or page_dpi is None or page_dpi <= reference_dpi:
        return None
    if cell.image is None or cell.upscale_factor <= 0:
        return None
    x0, y0, x1, y1 = cell.bbox_page_px
    if x1 <= x0 or y1 <= y0:
        return None
    try:
        import fitz  # PyMuPDF
        import numpy as np

        from .measure_extractor import _upscale_to_canonical, CANONICAL_STAFF_SPAN_PX

        pt_scale = 72.0 / page_dpi
        rect = fitz.Rect(x0 * pt_scale, y0 * pt_scale, x1 * pt_scale, y1 * pt_scale)
        doc = fitz.open(str(pdf_path))
        try:
            pix = doc[cell.page_index].get_pixmap(
                dpi=reference_dpi, clip=rect, alpha=False,
            )
        finally:
            doc.close()
        if pix.width <= 0 or pix.height <= 0:
            return None
        raw = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n,
        )
        if pix.n == 4:
            raw = raw[:, :, :3]
        elif pix.n == 1:
            raw = np.repeat(raw, 3, axis=2)
        # The raw (pre-canonical) staff span this cell was built from, scaled
        # to what it would be at `reference_dpi` -- CANONICAL_STAFF_SPAN_PX /
        # upscale_factor recovers it exactly, since `_upscale_to_canonical`'s
        # own `scale` is CANONICAL_STAFF_SPAN_PX / staff_span_px.
        raw_span_at_page_dpi = CANONICAL_STAFF_SPAN_PX / cell.upscale_factor
        raw_span_at_reference = raw_span_at_page_dpi * (reference_dpi / page_dpi)
        up_rgb, scale, _ = _upscale_to_canonical(
            np.ascontiguousarray(raw), raw_span_at_reference, [],
            max(raw.shape[1] * 20, CANONICAL_STAFF_SPAN_PX * 20),
        )
    except Exception:
        return None
    return dataclasses.replace(
        cell, image=up_rgb, image_no_staff=None, upscale_factor=scale,
    )


def _read_staff_header(
    clef_reader,
    cell: MeasureCell,
    *,
    conf: float,
    imgsz: int | None,
    header_frac: float,
    iou_threshold: float,
    agnostic_nms: bool,
    pdf_path: Path | str | None = None,
    page_dpi: int | None = None,
) -> tuple[str | None, dict[str, Any] | None]:
    """Run the clef/header specialist on the LEFT `header_frac` of a staff-start
    cell — the region holding the clef, key signature, and time signature — and
    return `(clef, time_sig)` read from it (`None` for whatever isn't found).

    Cropping to the header does two things: it removes the dense note ink to the
    right (fewer distractions for a specialist that collapses on dense scenes),
    and it keeps the header glyphs large so the specialist can run at a much
    SMALLER imgsz than a full cell — cheaper and, because the clef then sits near
    its training scale, actually more accurate (see the imgsz sweep in
    benchmarks/omr-clef-demo/tune_header_reader.py: on a 0.42 crop, imgsz 640
    beats 1280). Cropping from x=0 preserves canonical x-coordinates, so the
    octave-marker pairing and the left-edge time-sig filter still apply unchanged.

    One inference serves both readers — clef and time signature share the crop.
    """
    if cell.image is None:
        return None, None
    # A cell from `staff_header` is already the header; cropping it again would
    # cut into the key signature. Only a full measure cell needs the fraction.
    if cell.measure_index == HEADER_MEASURE_INDEX:
        header_frac = 1.0
    # DPI-normalize BEFORE the header_frac crop, from the full window, so the
    # crop fraction still means "the left 42% of the header" either way. See
    # `_rerender_header_at_reference_dpi` for why: past `reference_dpi` this
    # checkpoint stops recognising the sharper canonical texture a smaller
    # cubic-upscale factor produces, not just less confidently -- it finds no
    # clef-shaped ink at all. None (unset pdf_path/page_dpi, or page_dpi at or
    # below the reference) leaves `cell` untouched.
    source_cell = _rerender_header_at_reference_dpi(
        cell, pdf_path=pdf_path, page_dpi=page_dpi,
    ) or cell
    hw = max(1, int(round(source_cell.width * header_frac)))
    header_cell = dataclasses.replace(
        source_cell, image=source_cell.image[:, :hw], image_no_staff=None
    )
    dets = clef_reader.detect(
        header_cell,
        conf_threshold=conf,
        imgsz=imgsz,
        iou_threshold=iou_threshold,
        agnostic_nms=agnostic_nms,
    )
    # Clef: highest-confidence clef detection (+ any octave-marker suffix),
    # with its named staff line resolved geometrically — see clef_geometry.
    # The crop keeps canonical y-coordinates, so the cell's staff-line
    # positions still line up with the detection boxes.
    best_read, best_det, best_conf = None, None, -1.0
    for d in dets:
        if d.category != "clef":
            continue
        read = resolve_clef_for_detection(d)
        if read is None:
            continue
        if d.confidence > best_conf:
            best_read, best_det, best_conf = read, d, d.confidence
    clef = None if best_read is None else best_read.name + _octave_shift_for_base_clef(dets, best_det)
    # Time signature: the standard digit parser (drops left-edge instrument
    # misreads, resolves common/cut-common) on the same header detections.
    time_sig = parse_time_signature(dets)
    return clef, time_sig


# ---------------------------------------------------------------------------
# The staff-header pass
# ---------------------------------------------------------------------------
#
# One pass, before the measures are read, that looks at the start of every staff
# on the page — the strip holding the clef, the key signature and the time
# signature. It exists because the header is not reliably inside the staff-START
# measure cell: `Staff.x_start` is the longest unbroken run on the middle staff
# line, and on a faded print that run begins AFTER the clef, so the cell does
# too (NOTES.md, and measured on Beethoven 5 p.2 where a whole system's cells
# began past the clef and past all three key-signature flats). `staff_header`
# measures the window instead, and this pass hands it to the readers.
#
# What it produces is a key signature per staff, reconciled across the page by
# `key_signature_vote`. It never overrides the detector: the reading is a SEED,
# used as the staff's starting key signature, and any keySharp / keyFlat the
# detector finds in the music replaces it — the same "only speaks when the
# detector is silent" rule the CV clef locator follows.


#: How much a key signature read against a DEFAULTED clef is DISCOUNTED by.
#:
#: It used to REPLACE the reading's weight rather than discount it, and that is
#: the whole of the Beethoven 5 p.15 defect: a template reading of three flats
#: and a template reading of one flat both arrived at the vote as 0.5, so the
#: one measure of evidence the vote has — how many accidentals were actually
#: matched — was destroyed for exactly the readings that needed it.
#: `_modal_reference` then dropped all of them together for weighing under 1.0,
#: and a 22-staff page took its reference from the only two readings left, both
#: of which had under-counted the same signature as one flat. Three staves that
#: read the correct three flats were rejected for departing from it. See
#: benchmarks/omr-keysig-from-music-2026-09/PHASE1.md.
#:
#: A guessed clef halves what a reading is worth; it does not erase what the
#: reading saw, so three matched accidentals still outweigh one.
DEFAULTED_CLEF_WEIGHT = 0.5

#: The cap that keeps the ORIGINAL invariant true for a signature of any size:
#: `key_signature_vote._trustworthy` may never accept a defaulted-clef reading
#: as a transposing DEPARTURE from the system's modal signature — it may only
#: agree with it, or vote for it. Discounting alone would break that at four
#: matched accidentals (4 × 0.5 = 2.0, which is `VoteConfig.strong_weight`), so
#: the discount is capped below it. `test_transcribe_helpers` pins the relation
#: rather than the number, because it is the relation that matters.
DEFAULTED_CLEF_MAX_WEIGHT = 1.5


def _key_sig_richer(candidate, current) -> bool:
    """Is `candidate` a fuller key-signature reading than `current`?

    Fuller means more accidentals actually matched to slots. The asymmetry is
    the one `key_signature_vote` documents: `key_signature_geometry` requires
    the first slot to be observed and cannot extend past the last observation,
    so no reader here can invent an accidental, while every one of them can lose
    one to a broken glyph. Where two readings disagree, the longer is the one to
    keep — and a reading of nothing never displaces a reading of something.
    """
    if candidate is None or not candidate.fifths:
        return False
    if current is None:
        return True
    return len(candidate.matched_slots) > len(current.matched_slots)


def _header_key_signatures(
    pws: PageWithStaves,
    header_cells: dict[int, MeasureCell],
    clef_for_staff: dict[int, str | None],
    dets_for_staff: dict[int, tuple[list, MeasureCell]],
) -> tuple[dict[int, int], dict[int, str], dict[int, str]]:
    """Read and reconcile this page's key signatures.

    Returns `({staff_index: fifths}, {staff_index: reason})` for the staves the
    vote is willing to speak for, and `{staff_index: why}` for the staves it
    could not — because "no signature was read here" and "the signature read
    here is empty" are different statements, and only the first is honest about
    a page nothing could be read on.

    Both readings feed the same vote, which is the point of doing it here. The
    DETECTOR's markers are used where it found any — its boxes are real glyphs,
    fitted to the slot table rather than counted. The CV LOCATOR is the fallback
    where the detector is silent, which on degraded prints is nearly everywhere.
    Reconciling them together is what lets a page decide: on WTC p.17, three
    staves whose FIRST sharp went undetected read +1, +1 and +2 against a page
    that plainly prints four, and only a cross-page view can say so.

    `clef_for_staff` supplies each staff's KNOWN clef; a staff mapped to None
    has nothing but the position default behind it and is skipped, because a
    signature fitted against a guessed clef is a guess squared — measurably so:
    on Beethoven 5 p.2 with every staff defaulted to treble, two bass staves
    carrying three flats fitted cleanly as two sharps.

    This makes key-signature reading inherit the clef problem. On material where
    clefs read well it speaks for most staves; on the degraded orchestral prints
    where the detector reads every staff as treble, it stays quiet — which is
    the right failure, but it means the two features improve together.
    """
    candidates: list[StaffCandidate] = []
    unread: dict[int, str] = {}
    for system_index in sorted({st.system_index for st in pws.staves}):
        staves = sorted(
            (st for st in pws.staves if st.system_index == system_index),
            key=lambda st: st.top_y,
        )
        for ordinal, staff in enumerate(staves):
            cell = header_cells.get(staff.staff_index)
            clef = clef_for_staff.get(staff.staff_index)
            read, source = None, ""
            if not clef:
                unread[staff.staff_index] = (
                    "no clef was read on this staff, and the slot table a "
                    "signature is fitted against is chosen by the clef"
                )
            elif cell is None:
                unread[staff.staff_index] = "no header window was measured"
            if clef:
                dets, dets_cell = dets_for_staff.get(staff.staff_index, ([], None))
                if dets_cell is not None:
                    read = _key_sig_read_from_dets(dets, dets_cell, clef)
                    source = "detector"
                if (read is None or not read.fifths) and cell is not None:
                    located = locate_key_signature(cell, clef)
                    read = located.read if located else None
                    source = "cv_locator"
                # The template reader. It matches the Bravura outlines instead
                # of reassembling ink into components, which is what the locator
                # cannot do on a scan whose staff-line removal leaves every
                # glyph in pieces — measured on Beethoven 5 p.1, where the
                # locator reads 2 of 12 staves given the correct clef and this
                # reads 11.
                #
                # It speaks ONLY where the other two found nothing, and that
                # restraint was measured rather than assumed. Letting the FULLER
                # reading win instead — which the vote's own asymmetry argues
                # for, since a reader loses accidentals rather than inventing
                # them — gains 1 staff on Beethoven 5 p.2 and 2 on the Pastoral
                # and costs a WRONG reading on WTC I p.17, the cleanest page in
                # the corpus, where the detector was already right. This reader
                # is the one source here that can over-count, so the asymmetry
                # the argument rests on does not hold for it. Gaps only.
                if (read is None or not read.fifths) and cell is not None:
                    templated = read_key_signature_by_template(cell, clef)
                    if templated is not None and templated.fifths:
                        read, source = templated, "template"
            # No clef was read: the staff is carrying the positional default,
            # and a signature fitted against a guessed clef is a guess squared
            # — measured, bass staves defaulted to treble read three flats as
            # two sharps. That is why every reader above is gated on a real
            # clef, and this does not lift the gate so much as move who checks
            # it. The template reader runs against the default, and the reading
            # is entered with a weight too small to justify a DEPARTURE, so the
            # vote can only keep it where it agrees with what the rest of the
            # system printed. A staff whose default clef is wrong disagrees, and
            # is abstained on exactly as before.
            if not clef and cell is not None:
                fallback = _default_clef_for_position(ordinal, len(staves))
                templated = read_key_signature_by_template(cell, fallback)
                if templated is not None and templated.fifths:
                    read, source = templated, "template_default_clef"
                    unread.pop(staff.staff_index, None)
            if clef and cell is not None and read is None:
                unread[staff.staff_index] = (
                    "neither the detector's markers nor the CV locator found "
                    "key-signature accidentals in this staff's header"
                )
            candidates.append(StaffCandidate(
                staff_index=staff.staff_index,
                system_index=system_index,
                ordinal=ordinal,
                fifths=read.fifths if read else None,
                weight=(
                    # A guessed clef DISCOUNTS the accidental count; it does
                    # not replace it. Capped so the reading can still only ever
                    # agree with the system, never depart from it.
                    min(len(read.matched_slots) * DEFAULTED_CLEF_WEIGHT,
                        DEFAULTED_CLEF_MAX_WEIGHT)
                    if source == "template_default_clef"
                    else float(len(read.matched_slots))
                ) if read else 0.0,
                source=source if read else "",
                # The template reader can over-count, so its readings stay on
                # their own staff — see StaffCandidate.can_carry.
                can_carry=not source.startswith("template"),
            ))
    result = reconcile(candidates)
    fifths: dict[int, int] = {}
    reasons: dict[int, str] = {}
    for staff_index, verdict in result.verdicts.items():
        if verdict.action == "unread":
            unread.setdefault(
                staff_index,
                f"the cross-page vote did not speak for this staff: "
                f"{verdict.reason}" if verdict.reason else
                "the cross-page vote did not speak for this staff",
            )
            continue
        # A rejected staff is recorded too, with fifths 0: the vote judged its
        # reading untrustworthy, and that judgement has to reach the measure
        # pass or the same reading simply reappears there.
        fifths[staff_index] = verdict.fifths or 0
        reasons[staff_index] = f"{verdict.action}: {verdict.reason}"
        unread.pop(staff_index, None)
    return fifths, reasons, unread


def _header_detections(
    detector,
    header_cell: MeasureCell,
    *,
    conf_threshold: float,
    imgsz: int | None,
    iou_threshold: float,
    agnostic_nms: bool,
):
    """One detector pass over a staff's header crop.

    A crop a few staff spaces wide, run once before the measures are, and read
    twice: for the clef (which chooses the key signature's slot table) and for
    the key-signature markers themselves. Neither result is written to the
    output directly — the clef is re-read by the measure pass in its own way,
    and the signature goes through the cross-page vote first.
    """
    return detector.detect(
        header_cell,
        conf_threshold=conf_threshold,
        imgsz=imgsz,
        iou_threshold=iou_threshold,
        agnostic_nms=agnostic_nms,
    )


def _clef_from_dets(dets) -> str | None:
    """The highest-confidence clef among some detections, or None.

    None means "clef unknown", which callers treat as a reason to abstain
    rather than to fall back on a guess.
    """
    best, best_conf = None, -1.0
    for d in dets:
        if d.category != "clef":
            continue
        read = resolve_clef_for_detection(d)
        if read is not None and d.confidence > best_conf:
            best, best_conf = read.name, d.confidence
    return best


def _header_cell_beats_measure_cell(
    window: HeaderWindow | None, staff: Staff, measure_cell: MeasureCell | None
) -> bool:
    """Whether the measured header window reaches material the staff-start
    measure cell does not.

    The clef readers are pointed at the header cell ONLY when this is true. The
    measure cell is what they were tuned and validated on, so switching input
    unconditionally would re-open a settled question on every score; switching
    only where the measure cell demonstrably starts past the header fixes the
    documented failure and leaves everything else exactly as it was.
    """
    if measure_cell is None or window is None:
        return False
    spacing = max(1.0, staff.line_spacing_px)
    return measure_cell.bbox_page_px[0] - window.x0 > spacing


def _detections_for_cell(
    detector,  # YoloDetector — passed in to avoid import at module import time
    cell: MeasureCell,
    *,
    conf_threshold: float,
    imgsz: int | None,
    iou_threshold: float,
    agnostic_nms: bool,
    active_clef: str | None,
    active_key_sig: dict[str, str],
    active_time_sig: dict[str, Any] | None,
    clef_reader=None,  # optional secondary YoloDetector — staff-header specialist
    header_cell: MeasureCell | None = None,
    prefer_header: bool = False,
    skip_key_sig_detection: bool = False,
    read_clef: bool = False,
    clef_reader_conf: float = 0.30,
    clef_reader_imgsz: int = 640,
    clef_reader_header_frac: float = 0.42,
    locate_c_clefs: bool = True,
    forced_clef: str | None = None,
    forced_fifths: int | None = None,
    clef_overrides: list[dict[str, Any]] | None = None,
    pdf_path: Path | str | None = None,
    page_dpi: int | None = None,
) -> tuple[
    list[dict[str, Any]], str | None, dict[str, str], dict[str, Any] | None, str | None
]:
    """Run YOLO on a single cell, resolve chromatic pitches for each
    notehead, and emit cleaned-up detection dicts.

    Beyond a raw YOLO call this layers in three musical-notation passes:

    1. **Clef tracking.** Highest-confidence clef detection in the cell
       updates the active clef. Carried across to subsequent measures via
       the return value.
    2. **Key-signature tracking.** keySharp / keyFlat detections (distinct
       from inline accidentals in the DSv2 class set) update the active
       key signature. Also carried across measures via the return value.
    3. **Per-notehead pitch resolution.** For each notehead, in x-order:
         a) start with the diatonic pitch from `pitch_for_notehead`
         b) apply inline accidental (paired via _pair_accidentals_to_noteheads)
         c) otherwise apply any accidental carried over from earlier in
            this measure on the same letter+octave
         d) otherwise apply the active key-signature alteration on that letter
         e) otherwise leave the pitch diatonic

    Returns `(detection_dicts, new_active_clef, new_active_key_sig,
    new_active_time_sig, clef_source, n_clipped_dropped)`, where `clef_source`
    names which reader supplied a clef IN THIS CELL — "detector", "specialist",
    "cv_locator", or None when the clef was carried in rather than read here,
    and `n_clipped_dropped` is how many notehead detections were discarded as
    ink the crop cut off (`_drop_clipped_notehead_fragments`).
    """
    if clef_overrides is None:
        clef_overrides = []
    dets = detector.detect(
        cell,
        conf_threshold=conf_threshold,
        imgsz=imgsz,
        iou_threshold=iou_threshold,
        agnostic_nms=agnostic_nms,
    )

    # Ink the crop cut in half is not a notehead — see
    # `_drop_clipped_notehead_fragments`. First, so nothing downstream (pitch,
    # rhythm, the cross-staff deduper) ever sees a fragment.
    dets, n_clipped_dropped = _drop_clipped_notehead_fragments(dets, cell)

    # ── Clef pass: update active_clef from the highest-confidence clef
    #    detection in this cell, if any. If a clef8 / clef15 octave marker
    #    sits next to the chosen base clef, append the corresponding
    #    "_8va" / "_8vb" / "_15ma" / "_15mb" suffix so the pitch resolver
    #    picks up the right anchor (e.g. choral tenor on treble_8vb). ────
    best_clef_read = None
    best_clef_det = None
    best_clef_conf = -1.0
    for d in dets:
        if d.category != "clef":
            continue
        # Geometry, not the class label, decides WHICH line a C clef names —
        # alto and tenor are the same glyph one line apart, so the label can't
        # know. See tools/omr/clef_geometry.py.
        read = resolve_clef_for_detection(d)
        if read is None:
            continue
        if d.confidence > best_clef_conf:
            best_clef_read = read
            best_clef_det = d
            best_clef_conf = d.confidence
    # Which reader supplied this cell's clef, if any — the locator below only
    # speaks when this is still None. Note it tracks THIS cell's reading, not
    # the inherited `active_clef`: a staff carrying a clef forward from an
    # earlier system has nothing detected here, and is exactly the case where
    # a shape-located clef is worth having.
    clef_source: str | None = None
    if best_clef_read is not None:
        suffix = _octave_shift_for_base_clef(dets, best_clef_det)
        active_clef = best_clef_read.name + suffix
        clef_source = "detector"

    # ── Key-signature pass: scan for keySharp / keyFlat. None ⇒ no update. ──
    #
    # Skipped on the staff's FIRST cell when the cross-page vote has already
    # ruled on this staff. The vote saw these same markers — the header pass
    # reads them from the header crop and feeds them in — plus the rest of the
    # page, so re-reading them here in isolation can only discard that context.
    # It is what let three WTC staves whose first sharp went undetected report
    # +1, +1 and +2 on a page that plainly prints four. Later cells still run,
    # so a genuine mid-staff key change is still picked up.
    if not skip_key_sig_detection:
        new_key_sig = _detect_key_sig_from_cell(dets, cell, active_clef)
        if new_key_sig is not None:
            active_key_sig = new_key_sig

    # ── Time-signature pass: parse from timeSig0-9 / timeSigCommon detections.
    new_time_sig = parse_time_signature(dets)
    if new_time_sig is not None:
        active_time_sig = new_time_sig

    # ── Classical-CV C-clef locator. Both the production detector and the
    #    (optional) specialist below read a clef by appearance, so both go
    #    blind on engravings whose glyphs aren't in their training
    #    distribution — on 19th-century C-clef counterpoint prints they find
    #    no clef at all, at any confidence, and every staff silently defaults
    #    to treble. Shape-based location doesn't depend on the font, and it
    #    ONLY identifies C clefs — never treble or bass — so where it fires it
    #    is the more specific evidence: `clef_geometry` measures which line
    #    the clef names rather than classifying it, and that measurement does
    #    not depend on a training distribution the way a model label does.
    #    Runs BEFORE the specialist for exactly that reason: it must get a
    #    chance to speak for its narrow domain before a broader-but-fuzzier
    #    appearance model can claim the staff. It still runs only when nothing
    #    ABOVE it (the production detector) already produced a clef, so it
    #    remains "add a reading where there was none" with respect to the
    #    detector — it can only ever ADD a reading, never overturn one, EXCEPT
    #    the specialist's below, which is now the one thing it outranks. See
    #    tools/omr/clef_locator.py.
    if read_clef and locate_c_clefs and clef_source is None:
        # Hand the locator the noteheads the detector is already sure about, so
        # it can't nominate a notehead stack as a clef.
        #
        # Noteheads only, deliberately. Rests were in this list once and had to
        # come out: an archaic C clef is two heavy horizontal bars, which the
        # detector reads as `restHBar` with high confidence (0.6-0.86 on
        # Nottebohm), sitting exactly on top of the clef and vetoing every one
        # of them. A rest is a poor veto anyway — the shapes that could be
        # confused with a clef are the ones the detector misreads AS a clef,
        # and rests are small enough to fail the size gates on their own.
        occupied = [
            (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical)
            for d in dets
            if d.category == "notehead"
        ]
        # `prefer_header`, not merely `header_cell is not None`: the header
        # cell is now supplied on every staff so the detector fallback below
        # can use it, and only `_header_cell_beats_measure_cell` decides
        # whether a reader should look there INSTEAD of the measure cell.
        use_header = prefer_header and header_cell is not None
        located = locate_clef(
            header_cell if use_header else cell,
            # The detector's boxes belong to the measure cell's frame; they only
            # describe the header cell when it IS the measure cell.
            occupied_boxes=None if use_header else occupied,
        )
        if located is not None:
            active_clef = located.read.name
            clef_source = "cv_locator"

    # ── The production detector, a second time, on the measured header crop.
    #
    #    GAP-FILL ONLY, and it runs after the locator so neither of them loses
    #    precedence. The detector reads the MEASURE cell above and that stays
    #    the primary reading — on WTC p.17 the header crop is strictly worse
    #    for this model, which is why `_header_detections` is pointed at the
    #    measure cell and why this is a fallback rather than a switch.
    #
    #    But a crop that is worse on average is not worse everywhere, and where
    #    the measure cell yields NOTHING there is nothing to lose. Measured
    #    over the 113 staves of the hand-read orchestral corpus
    #    (`probe_detector_reach.py`): the measure cell reads no clef on 45 of
    #    them, the header crop reads one on 8 of those 45, and **all 8 are
    #    right** — seven trebles and one C clef the positional default would
    #    have called treble. It contradicts a measure-cell reading on zero
    #    staves, because it is never consulted when there is one.
    #
    #    Note the header cell is supplied here whatever
    #    `_header_cell_beats_measure_cell` decided: that gate chooses which
    #    crop the locator and specialist READ INSTEAD of the measure cell, and
    #    half of these eight sit on staves it leaves alone.
    if read_clef and clef_source is None and header_cell is not None:
        header_clef = _clef_from_dets(
            detector.detect(
                header_cell,
                conf_threshold=conf_threshold,
                imgsz=imgsz,
                iou_threshold=iou_threshold,
                agnostic_nms=agnostic_nms,
            )
        )
        if header_clef is not None:
            active_clef = header_clef
            clef_source = "detector_header"

    # ── Decoupled staff-header specialist (clef + time-sig override). The
    #    production detector under-detects clefs on real orchestral scans (9%
    #    detection, 0% type → the "all-treble disease") and time-sig digits
    #    (mostly null). A model fine-tuned on real staff cells reads them well
    #    but collapses dense-notehead detection, so it can't be the main
    #    detector. Using ONLY its clef + time-sig read of the staff-START header
    #    crop (where they're printed) gets those wins with zero cost to notehead
    #    detection. Runs after the production header pass and the CV locator, so
    #    it can improve on the detector's guess but NOT the locator's — the
    #    locator only speaks for C clefs and abstains otherwise, so a staff it
    #    claimed is the one case where a model label should not get the last
    #    word. Measured end to end on Beethoven 5, IMSLP score imslp-575951,
    #    page_index 68 (dpi 600): staves 4 and 5 both read as a C clef by the
    #    locator ("tenor") and, wired to run first, flipped by the specialist
    #    to an incorrect "bass" — the old ordering (specialist unconditional,
    #    locator gated on `clef_source is None`) can never recover from that,
    #    since the locator never gets to run once the specialist has already
    #    spoken. With the locator running first, as here, both staves read
    #    "tenor" from `cv_locator` instead. Runs before the pitch pass either
    #    way (so the corrected clef anchors every pitch). See
    #    benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md. ──
    if read_clef and clef_reader is not None:
        spec_clef, spec_time_sig = _read_staff_header(
            clef_reader,
            header_cell if (prefer_header and header_cell is not None) else cell,
            conf=clef_reader_conf,
            imgsz=clef_reader_imgsz,
            header_frac=clef_reader_header_frac,
            iou_threshold=iou_threshold,
            agnostic_nms=agnostic_nms,
            pdf_path=pdf_path,
            page_dpi=page_dpi,
        )
        # GAP-FILL ONLY. The specialist supplies a clef where no other reader
        # spoke, and never overwrites one that did. Measured over 179 pages of
        # the corpus sweep (benchmarks/omr-corpus-sweep-2026-08/, two arms):
        # allowed to overwrite, it takes 90% of WTC staves and 83% of
        # handel-red's from a detector that was already reading 100% of their
        # clefs, and on the 52-staff hand-read set it scores 96% against that
        # detector's 97% — so every one of those substitutions is a slightly
        # losing trade made for nothing. All of its value is in the gaps:
        # staves blind before/after are beet5 79%->25%, lamer 59%->27%, and
        # 30%->19% corpus-wide, none of which requires overwriting anybody.
        #
        # Clef and time-sig precedence are independent: the locator has no
        # opinion on meter, so another reader's claim on the clef doesn't block
        # the specialist's time-sig read.
        if spec_clef is not None and clef_source is None:
            active_clef = spec_clef
            clef_source = "specialist"
        if spec_time_sig is not None:
            active_time_sig = spec_time_sig

    # ── Dossier override. The work's own written clef and key signature, when
    #    the caller supplied a dossier AND the part→staff join was safe enough
    #    to establish one (dossier.slot_facts_for_system decides that, not us).
    #
    #    It runs LAST, after every reader, because unlike them it is not an
    #    opinion: it is what the page says, taken from the score. Every other
    #    ordering here is "later reader wins where earlier ones were silent";
    #    this one wins even where they spoke, because a reader that disagrees
    #    with the work is wrong. Measured on an engraved Brahms 1 excerpt the
    #    detector read a bass staff and a tenor staff as treble, and those two
    #    clefs alone mis-pitched 98 of the page's notes.
    #
    #    What each reader said is still returned via `clef_source`, so an
    #    override is visible rather than silent.
    if forced_clef is not None and forced_clef != active_clef:
        overridden_clef = active_clef if clef_source else None
        active_clef = forced_clef
        clef_source = "dossier"
        if overridden_clef is not None:
            clef_overrides.append({"read": overridden_clef, "used": forced_clef})
    elif forced_clef is not None:
        clef_source = clef_source or "dossier"

    if forced_fifths is not None:
        active_key_sig = alterations_for_fifths(forced_fifths)

    # ── Classical-CV line detection: stems + cleaner beams. The YOLO
    #    Phase 3.3 model misses stems entirely and emits beam bboxes
    #    with imprecise endpoints; classical morphology + connected
    #    components produces both with millisecond-scale latency and
    #    no GPU. See tools/omr/line_detection.py.
    extra_lines = detect_lines(cell)
    # Reject CV "stems" that are actually tremolo/arpeggiato/ornament ink
    # (see _filter_stems_overlapping_tremolo docstring above for the
    # root-cause rationale). Filtering here, right where extra_lines is
    # produced, means every downstream consumer of the stem list —
    # rhythm-resolution below, the fill-based notehead reclassification,
    # and stem-direction inference — sees the cleaned-up stems. No-op
    # when the cell has no tremolo/arpeggiato/ornament YOLO detections.
    extra_lines["stems"] = _filter_stems_overlapping_tremolo(
        extra_lines.get("stems") or [], dets
    )
    cv_stems_for_class_check = extra_lines.get("stems") or []

    # ── Notehead class correction by inner-pixel fill ratio + stem
    #    presence. YOLO occasionally classifies a HOLLOW notehead
    #    (half/whole) as BLACK because the model's understanding of
    #    the hollow center is fragile under certain rendering /
    #    scaling conditions. Inspecting the actual pixels disambiguates
    #    black ↔ hollow; the CV stem detection disambiguates half
    #    (has stem) ↔ whole (no stem).
    for d in dets:
        if getattr(d, "category", "") == "notehead":
            stem = _find_attached_stem(d, cv_stems_for_class_check)
            _correct_notehead_class_by_fill(d, cell, has_stem=stem is not None)

    # ── Stem-direction inference. Pair each notehead to its attached stem
    #    (classical-CV), then decide the direction ONCE PER STEM from all the
    #    noteheads on it. This drives voice splitting in Phase 4h: stem-up =
    #    voice 1 (upper), stem-down = voice 2 (lower).
    #
    #    Deciding per stem rather than per notehead is what keeps a double stop
    #    together. Its two noteheads share one stem, so they must share its
    #    direction; resolved one notehead at a time they could disagree, and a
    #    chord whose members disagree is exactly what `voicing` treats as
    #    divisi. See `_stem_direction`.
    stem_direction_by_id: dict[int, str] = {}
    cv_stems = extra_lines.get("stems") or []
    if cv_stems:
        heads_by_stem: dict[int, list] = {}
        stems_by_key: dict[int, Any] = {}
        for d in dets:
            if getattr(d, "category", "") != "notehead":
                continue
            stem = _find_attached_stem(d, cv_stems)
            if stem is None:
                continue
            heads_by_stem.setdefault(id(stem), []).append(d)
            stems_by_key[id(stem)] = stem
        for key, heads in heads_by_stem.items():
            direction = _stem_direction(stems_by_key[key], heads)
            for d in heads:
                stem_direction_by_id[id(d)] = direction

    # ── Rhythm pass: resolve duration_beats / duration_type / dots per
    #    notehead and rest. Uses beams + flags + augmentationDot geometry.
    #    Passes extra_lines so rhythm.py can use the classical-CV stems
    #    + beams (much more accurate than YOLO's beams alone).
    rhythm_map = resolve_rhythms_for_cell(dets, cell, extra_lines=extra_lines)

    # ── Pair inline accidentals to their target noteheads. ─────────────────
    inline_map = _pair_accidentals_to_noteheads(dets)

    # ── Resolve final pitch per notehead, walking left-to-right and
    #    tracking accidentals that carry through this measure. ─────────────
    explicit_in_measure: dict[tuple[str, int], str | None] = {}
    pitch_by_id: dict[int, str | None] = {}
    candidates_by_id: dict[int, list[tuple[str, float]]] = {}
    if active_clef is not None:
        noteheads_sorted = sorted(
            (d for d in dets if d.category == "notehead"),
            key=lambda d: d.x_canonical,
        )
        for nh in noteheads_sorted:
            diatonic = pitch_for_notehead(nh, clef=active_clef)
            if diatonic is None:
                pitch_by_id[id(nh)] = None
                continue
            parsed = _parse_diatonic_pitch(diatonic)
            if parsed is None:
                pitch_by_id[id(nh)] = diatonic
                continue
            letter, octave = parsed

            # Priority: inline > carried-in-measure > key-sig > none
            if id(nh) in inline_map:
                alt = inline_map[id(nh)]
                if alt == "natural":
                    explicit_in_measure[(letter, octave)] = None
                    final_alt: str | None = None
                else:
                    explicit_in_measure[(letter, octave)] = alt
                    final_alt = alt
            elif (letter, octave) in explicit_in_measure:
                final_alt = explicit_in_measure[(letter, octave)]
            elif letter in active_key_sig:
                final_alt = active_key_sig[letter]
            else:
                final_alt = None

            pitch_by_id[id(nh)] = _build_pitch(letter, final_alt, octave)

            # ── M4: compute top-N pitch candidates with the same accidental
            #    treatment, so a re-ranking step (maestro_bridge re-rank)
            #    can break ties by harmonic context. Candidates inherit the
            #    inline / carried / key-sig accidental of the primary —
            #    imperfect for some edge cases but a reasonable default; the
            #    re-rank step only kicks in for noteheads maestro already
            #    flagged as suspect anyway.
            raw_candidates = pitch_candidates_for_notehead(nh, clef=active_clef)
            final_candidates: list[tuple[str, float]] = []
            for cand_diatonic, weight in raw_candidates:
                cand_parsed = _parse_diatonic_pitch(cand_diatonic)
                if cand_parsed is None:
                    final_candidates.append((cand_diatonic, weight))
                    continue
                cand_letter, cand_octave = cand_parsed
                if id(nh) in inline_map:
                    a = inline_map[id(nh)]
                    cand_alt: str | None = None if a == "natural" else a
                elif (cand_letter, cand_octave) in explicit_in_measure:
                    cand_alt = explicit_in_measure[(cand_letter, cand_octave)]
                elif cand_letter in active_key_sig:
                    cand_alt = active_key_sig[cand_letter]
                else:
                    cand_alt = None
                final_candidates.append(
                    (_build_pitch(cand_letter, cand_alt, cand_octave), weight)
                )
            candidates_by_id[id(nh)] = final_candidates

    # ── Tie pairing. For each `tie` glyph in this cell, find the two
    #    noteheads it connects (left edge + right edge of the tie bbox,
    #    at roughly the same y as the tie's vertical center). Marks
    #    `tied_to_next` on the left notehead and `tied_from_prev` on the
    #    right one. Cross-cell ties (final note of measure N tied to
    #    first of measure N+1) are not handled in this pass — the YOLO
    #    detector emits the tie glyph in whichever cell contains most
    #    of it, and we can only see one cell's noteheads here. Within-
    #    measure syncopation ties (the common case for keyboard /
    #    string passage work) are covered.
    ties_to_next: set[int] = set()
    ties_from_prev: set[int] = set()
    _pair_ties_in_cell(dets, ties_to_next, ties_from_prev)

    # Articulations, matched to the notehead they are printed against. Same
    # shape as the tie pass above and for the same reason: the mark and its
    # note are separate detections and only geometry joins them.
    articulations: dict[int, list[str]] = {}
    _attach_articulations_in_cell(dets, articulations)

    # ── Build output dicts. Convert cell-local bbox → page-pixel bbox. ────
    out: list[dict[str, Any]] = []
    cell_x0, cell_y0, cell_x1, cell_y1 = cell.bbox_page_px
    cell_page_w = cell_x1 - cell_x0
    cell_page_h = cell_y1 - cell_y0
    canonical_w = max(1, cell.width)
    canonical_h = max(1, cell.height)
    for d in dets:
        cx = d.x_canonical
        cy = d.y_canonical
        cw = d.width_canonical
        ch = d.height_canonical
        page_x = cell_x0 + int(round(cx * cell_page_w / canonical_w))
        page_y = cell_y0 + int(round(cy * cell_page_h / canonical_h))
        page_w = max(1, int(round(cw * cell_page_w / canonical_w)))
        page_h = max(1, int(round(ch * cell_page_h / canonical_h)))

        pitch: str | None = pitch_by_id.get(id(d))

        out_d: dict[str, Any] = {
            "class": d.smufl_name,
            "category": d.category,
            "bbox": [cx, cy, cw, ch],
            "bbox_page": [page_x, page_y, page_w, page_h],
            "confidence": round(float(d.confidence), 3),
            "pitch": pitch,
        }
        # M4: top-N pitch candidates for re-ranking. Only emitted for
        # noteheads that have any candidates (keeps JSON terser).
        cand = candidates_by_id.get(id(d))
        if cand:
            out_d["pitch_candidates"] = [
                {"pitch": p, "weight": round(w, 3)} for p, w in cand
            ]
        # Attach rhythm info for noteheads + rests (other categories never
        # appear in rhythm_map — keeps the JSON terser for them).
        rinfo = rhythm_map.get(id(d))
        if rinfo is not None:
            out_d["duration_beats"] = rinfo["duration_beats"]
            out_d["duration_type"] = rinfo["duration_type"]
            out_d["dots"] = rinfo["dots"]
            # Only carried when the duration actually rests on beams, so the
            # JSON stays terser for everything else. `_reconcile_measure_to_meter`
            # needs it to know which durations are the fragile ones.
            if rinfo.get("beam_levels"):
                out_d["beam_levels"] = rinfo["beam_levels"]
            # Tuplets, same policy: only carried when there is one. `tuplet`
            # is the ratio the exporters write as <time-modification>;
            # `tuplet_group` is which bracket it belongs to, so start/stop land
            # on the right notes without re-deriving the grouping.
            if rinfo.get("tuplet"):
                out_d["tuplet"] = rinfo["tuplet"]
                out_d["tuplet_group"] = rinfo["tuplet_group"]
        # Articulations printed against this notehead. Only carried when there
        # are some, to keep the JSON terser — the same policy as beams, tuplets
        # and the tie flags below.
        if id(d) in articulations:
            out_d["articulations"] = articulations[id(d)]
        # THE ACCIDENTAL THAT WAS PRINTED, which is not the same fact as the
        # pitch. `inline_map` already pairs each accidental detection to its
        # notehead and the alteration is folded into `pitch` above — but the
        # pitch says what SOUNDS and an `<accidental>` says what the engraver
        # DREW, and MusicXML carries them separately (`<alter>` against
        # `<accidental>`). A natural is the clearest case: the pitch is
        # unaltered either way, and the glyph is the whole of the difference.
        # Recorded here because the pairing is computed here and was, until
        # now, consumed and discarded.
        if id(d) in inline_map:
            out_d["accidental"] = inline_map[id(d)]
        # Stem direction for noteheads (Phase 4h voice splitting).
        if id(d) in stem_direction_by_id:
            out_d["stem_direction"] = stem_direction_by_id[id(d)]
        # Tie flags (only emitted when present, to keep the JSON terser).
        if id(d) in ties_to_next:
            out_d["tied_to_next"] = True
        if id(d) in ties_from_prev:
            out_d["tied_from_prev"] = True
        out.append(out_d)
    return (out, active_clef, active_key_sig, active_time_sig, clef_source,
            n_clipped_dropped)


def _pair_ties_in_staff(staff_dict: dict[str, Any]) -> int:
    """Cross-cell tie pairing for a single staff.

    Pairs tie glyphs with their two flanking noteheads using page-pixel
    coordinates (`bbox_page`), so ties spanning a barline (most ties in
    real music — the canonical use connects the final note of measure N
    to the first of measure N+1) get caught. Complements the within-cell
    pass in `_pair_ties_in_cell`; flag-setting is idempotent so the two
    passes don't fight.

    Mutates `staff_dict` in place. Returns the number of NEW pairs
    created (pairs already set by the within-cell pass aren't counted).
    """
    measures = staff_dict.get("measures", [])
    if not measures:
        return 0

    # Collect every notehead and every tie across the staff, with their
    # page-pixel centers. Page coords are the only coordinate system
    # shared across cells (each cell has its own cell-local origin).
    nh_list: list[tuple[float, float, int, dict[str, Any]]] = []
    tie_list: list[tuple[list[int], dict[str, Any]]] = []
    for m in measures:
        for det in m.get("detections", []):
            bp = det.get("bbox_page")
            if not bp or len(bp) != 4:
                continue
            xc = bp[0] + bp[2] / 2.0
            yc = bp[1] + bp[3] / 2.0
            nh_w = bp[2]
            if det.get("category") == "notehead":
                nh_list.append((xc, yc, nh_w, det))
            elif (det.get("class") or "").lower() == "tie":
                tie_list.append((bp, det))

    if not tie_list or len(nh_list) < 2:
        return 0

    avg_nh_h = sum(
        det.get("bbox_page", [0, 0, 0, 0])[3] for _, _, _, det in nh_list
    ) / len(nh_list)
    y_tol = max(avg_nh_h * 3, 30)

    n_new_pairs = 0
    for tie_bp, _tie_det in tie_list:
        tx0, ty0, tw, th = tie_bp
        tie_left = tx0
        tie_right = tx0 + tw
        tie_yc = ty0 + th / 2.0

        best_left = None
        best_left_dx = float("inf")
        best_right = None
        best_right_dx = float("inf")

        for xc, yc, w, det in nh_list:
            if abs(yc - tie_yc) > y_tol:
                continue
            # Start notehead: x-center at or just left of tie's left edge.
            # The window is generous (3× notehead width) so cross-barline
            # ties still pair even when the next-measure notehead is a
            # bit further away due to the barline space.
            dx_left = tie_left - xc
            if 0 <= dx_left < w * 3 and dx_left < best_left_dx:
                best_left = det
                best_left_dx = dx_left
            # Stop notehead: x-center at or just right of tie's right edge
            dx_right = xc - tie_right
            if 0 <= dx_right < w * 3 and dx_right < best_right_dx:
                best_right = det
                best_right_dx = dx_right

        if (
            best_left is not None
            and best_right is not None
            and best_left is not best_right
        ):
            was_already_paired = (
                best_left.get("tied_to_next") and best_right.get("tied_from_prev")
            )
            best_left["tied_to_next"] = True
            best_right["tied_from_prev"] = True
            if not was_already_paired:
                n_new_pairs += 1

    return n_new_pairs


#: DSv2's ten articulation classes are five marks on two sides, and the side is
#: part of the class name rather than something to infer.
_ARTICULATION_KINDS = frozenset(
    {"staccato", "staccatissimo", "accent", "marcato", "tenuto"})

#: How far along x a mark may sit from the notehead it belongs to, in NOTEHEAD
#: WIDTHS — the unit, not the mark's own bounding box, which is the mistake the
#: augmentation-dot gate made and paid 193 edits for.
#:
#: NOT a tuned value. Swept over eight engraved works, scoring each placement
#: against the truth by index (`benchmarks/omr-corpus-widening-2026-09/probe_articulations.py`):
#:
#:     0.30   106 placed, precision 0.962, placement rate 0.486
#:     0.50   197 placed, precision 0.980, placement rate 0.904
#:     0.75   197 placed, precision 0.980, placement rate 0.904   <- chosen
#:     1.00   197 placed, precision 0.980, placement rate 0.904
#:     1.50   197 placed, precision 0.980, placement rate 0.904
#:     2.50   197 placed, precision 0.980, placement rate 0.904
#:
#: A flat plateau from 0.50 to 2.50, identical to the mark, with a cliff below
#: it: a mark is x-centred on its notehead to within half a width, and on the
#: correct side there is nothing else within two and a half. 0.75 sits in the
#: middle of the plateau rather than on either edge of it.
_ARTIC_MAX_DX_NOTEHEAD_WIDTHS = 0.75


def articulation_kind(class_name: str) -> tuple[str, bool] | None:
    """`("staccato", True)` for `articStaccatoAbove`. None if not one.

    The bool is whether the mark is printed ABOVE the notehead, which the class
    name states and geometry then has to agree with — a mark labelled `Above`
    that sits below every notehead in the cell belongs to none of them.
    """
    norm = "".join(ch for ch in (class_name or "").lower() if ch.isalnum())
    if not norm.startswith("artic"):
        return None
    body = norm[len("artic"):]
    for suffix, above in (("above", True), ("below", False)):
        if body.endswith(suffix):
            kind = body[: -len(suffix)]
            return (kind, above) if kind in _ARTICULATION_KINDS else None
    return None


def _attach_articulations_in_cell(dets, out: dict[int, list[str]]) -> int:
    """Give each articulation mark to the notehead it is printed against.

    THE SEVENTH SIGNAL DETECTED AND NEVER EXPORTED. `export.py` contained the
    string "articulation" once, in a docstring, while the detector fired 102
    staccati on one engraved Mozart 40 page — and musicdiff charged back
    exactly 102 `insarticulation` edits, 28% of that work's whole budget. The
    three works the benchmark used to consist of print 0, 2 and 6 of them,
    which is why nothing saw it.

    The rule is the one the engraving makes true: a staccato or accent is
    printed directly above or below its notehead, so the mark is matched to the
    notehead nearest it in X, on the side its own class names, within
    `_ARTIC_MAX_DX_NOTEHEAD_WIDTHS`. A mark with no notehead on the correct side
    is left unattached rather than given to the nearest thing available — 21 of
    218 across the corpus, and abstaining there is why precision is 0.980.

    Mutates `out` (notehead id -> list of MusicXML articulation names) and
    returns the number of marks placed.
    """
    noteheads = [d for d in dets if (d.category or "") == "notehead"]
    if not noteheads:
        return 0
    marks = [(d, k) for d in dets
             if (k := articulation_kind(d.smufl_name or "")) is not None]
    if not marks:
        return 0

    widths = sorted(n.width_canonical for n in noteheads)
    nh_width = widths[len(widths) // 2] or 1.0
    limit = nh_width * _ARTIC_MAX_DX_NOTEHEAD_WIDTHS

    placed = 0
    for mark, (kind, above) in marks:
        mx = mark.x_canonical + mark.width_canonical / 2.0
        my = mark.y_canonical + mark.height_canonical / 2.0
        best = None
        for n in noteheads:
            ny = n.y_canonical + n.height_canonical / 2.0
            # Larger canonical y is LOWER on the page, so a mark printed above
            # its notehead has the smaller y of the two.
            if above and my >= ny:
                continue
            if not above and my <= ny:
                continue
            dx = abs(mx - (n.x_canonical + n.width_canonical / 2.0))
            if dx > limit:
                continue
            if best is None or dx < best[0]:
                best = (dx, n)
        if best is None:
            continue
        out.setdefault(id(best[1]), []).append(kind)
        placed += 1
    return placed


def _pair_ties_in_cell(dets, ties_to_next: set, ties_from_prev: set) -> None:
    """Pair tie detections with their two flanking noteheads in the same
    cell. Mutates `ties_to_next` / `ties_from_prev` in place (adds id()s
    of the noteheads on the start / stop side respectively).

    Pairing heuristic:
      - A tie's left edge sits near the right edge of the start notehead;
        its right edge sits near the left edge of the stop notehead.
      - Vertical alignment: the tie's y-center is within ~3 notehead
        heights of the notehead y-centers.
      - Pitch match: not checked (and not available — pitches are
        resolved into a separate id-keyed dict in `_detections_for_cell`,
        not onto `SymbolDetection.pitch`). Geometry alone is fine here
        because real tied notes are at the same y-position by definition.
    """
    noteheads = [d for d in dets if (d.category or "") == "notehead"]
    ties = [d for d in dets if (d.smufl_name or "").lower() == "tie"]
    if not ties or len(noteheads) < 2:
        return

    avg_nh_h = (
        sum(n.height_canonical for n in noteheads) / len(noteheads)
        if noteheads else 20
    )
    y_tolerance = max(avg_nh_h * 3, 30)

    for tie in ties:
        tie_left = tie.x_canonical
        tie_right = tie.x_canonical + tie.width_canonical
        tie_yc = tie.y_canonical + tie.height_canonical / 2.0

        best_left = None
        best_left_dx = float("inf")
        best_right = None
        best_right_dx = float("inf")

        for nh in noteheads:
            nh_xc = nh.x_canonical + nh.width_canonical / 2.0
            nh_yc = nh.y_canonical + nh.height_canonical / 2.0
            if abs(nh_yc - tie_yc) > y_tolerance:
                continue
            # Start notehead: x-center is at or before tie's left edge
            dx_left = tie_left - nh_xc
            if 0 <= dx_left < nh.width_canonical * 2 and dx_left < best_left_dx:
                best_left = nh
                best_left_dx = dx_left
            # Stop notehead: x-center is at or after tie's right edge
            dx_right = nh_xc - tie_right
            if 0 <= dx_right < nh.width_canonical * 2 and dx_right < best_right_dx:
                best_right = nh
                best_right_dx = dx_right

        if best_left is not None and best_right is not None and best_left is not best_right:
            ties_to_next.add(id(best_left))
            ties_from_prev.add(id(best_right))


# ---------------------------------------------------------------------------
# Per-measure rhythm-sum check (audit follow-up to Phase 4c/g)
# ---------------------------------------------------------------------------

_RHYTHM_SUM_TOLERANCE = 1.0 / 64  # beats (quarter-note units)


def _measure_rhythm_sum_warning(
    detections: list[dict[str, Any]],
    time_sig: dict[str, Any] | None,
    *,
    tolerance: float = _RHYTHM_SUM_TOLERANCE,
) -> dict[str, float] | None:
    """Compare a measure's chord-grouped event durations against its
    active time signature. Returns `{"expected_beats": X, "actual_beats":
    Y}` when the sum is off by more than `tolerance` beats, or None when
    it matches (or no time signature is known — the check is skipped
    entirely rather than guessing against a default 4/4).

    Reuses `voicing.group_chords_in_measure` / `split_events_into_voices`
    instead of re-summing durations directly, so multi-voice measures
    (stem-up vs stem-down) are checked per voice — each voice should
    independently sum to the measure length. When there's more than one
    voice, this reports whichever voice deviates the most.
    """
    if not time_sig:
        return None
    num = time_sig.get("numerator")
    den = time_sig.get("denominator")
    if not num or not den:
        return None
    expected_beats = num * 4.0 / den

    events = group_chords_in_measure(detections)
    voices = split_events_into_voices(events)

    actual_beats = 0.0
    max_deviation = -1.0
    for voice_events in voices:
        voice_beats = sum(ev["duration_beats"] for ev in voice_events)
        deviation = abs(voice_beats - expected_beats)
        if deviation > max_deviation:
            max_deviation = deviation
            actual_beats = voice_beats

    if max_deviation <= tolerance:
        return None
    return {
        "expected_beats": round(expected_beats, 4),
        "actual_beats": round(actual_beats, 4),
    }


# ---------------------------------------------------------------------------
# One glyph, one staff
# ---------------------------------------------------------------------------
#
# A measure cell is cut 4 staff-spaces above and below its staff
# (`measure_extractor.PAD_ABOVE_STAFF_LINES`) so that ledger-line notes are not
# sliced off. On a keyboard score, where staves sit far apart, those bands do
# not meet. On a conductor's score they overlap, and NOTHING arbitrated between
# them: the detector ran on both cells, found the same ink twice, and both
# staves kept it.
#
# Measured on an engraved Mahler 5 page whose truth is 22 notes: staves 14 and
# 15 reported 24 and 29 noteheads, and 16 of them were the SAME notehead at
# IoU > 0.5 — counted once for each staff. The page is almost entirely rests, so
# this was most of its false-positive mass.
#
# The rule is the obvious one: a glyph belongs to the staff it is nearest, by
# distance from its centre to the staff's own five-line band. That keeps a
# genuine ledger-line note on its own staff whenever the neighbouring staff is
# further away, which is the case the padding exists for, and it only ever
# REMOVES a duplicate — the surviving copy is untouched, so a page whose bands
# never overlap is byte-identical.


# ─── Which staff a LEDGER note belongs to ───────────────────────────────────
#
# Distance to the nearer band is the wrong rule for the one case the padding
# exists for, and the Brahms fixture is that case. Its Violin 1 plays up to B6,
# five spaces above its own top line, and LilyPond opened the gap above the
# staff to fit those ledger notes — so the note sits nearer the TIMPANI band
# above it than its own. Measured: the notehead at y 7392 is 133px below the
# timpani's band and 188px above the violin's, and exported as `Ab1` on a
# timpani while Violin 1's bars 3 and 4 came out empty.
#
# The physical fact distance ignores is that a ledger note is JOINED to its
# staff by a ladder of ledger lines, and joined to nothing in the other
# direction. On that page the violin's cells carry three rungs per note-column
# at y 7455/7497/7538 — exactly the 3rd/2nd/1st ledger positions above a top
# line at 7580 — and there is no rung anywhere between the note and the timpani.
#
# So read the ladder. A rung counts when a `ledgerLine` detection sits within
# a third of a space of where that staff's k-th ledger line would be AND
# overlaps the notehead in x.
#
# COMPLETENESS ONLY, because that is what makes a ladder a ladder. A note four
# spaces out with all four rungs present is JOINED to that staff; a note with
# three of four has a gap in it, and a gap is what you see when the rungs
# belong to something else that happens to lie in the way. The same cut runs
# the other way: one rung found out of three expected is what you see when
# that one rung belongs to the OTHER staff's note — on the Beethoven bassoon
# pair, the ghost's single rung was the real C4's own ledger line, counted
# from the wrong staff's anchor, and comparing broken ladders by rung count
# handed the contest to the ghost before the range veto was ever consulted.
# So an unbroken ladder outranks anything broken, and two broken ladders are
# not evidence either way — the pair falls through to range, then distance,
# so a page with no ledger lines behaves exactly as before.
#
# NOTEHEADS ONLY. A contested accidental or rest has no ladder of its own, and
# inheriting one from a neighbour is the kind of inference that would need its
# own measurement.
_LEDGER_RUNG_Y_TOL_SPACES = 0.35
_LEDGER_RUNG_MIN_X_OVERLAP = 0.25

#: A note ON the k-th ledger line sits k.0 spacings past the staff edge; a note
#: in the space above it sits k.5. Truncating the ratio put a note printed ON
#: the first ledger — 0.994 spacings out on the Beethoven bassoon pair, one
#: pixel of jitter from 1.018 in the bar beside it — at ZERO expected rungs,
#: so the same note read as needing its ledger in one bar and not in the next.
#: 0.25 sits halfway between the two populations a notehead can occupy.
_LEDGER_RUNG_EXPECTED_SLACK = 0.25


# ─── ... and what the INSTRUMENT says about it ──────────────────────────────
#
# A ladder is evidence about the glyph; an instrument's range is evidence about
# the part, and a reader uses both. Measured on the engraved Beethoven 5
# fixture, where the ladder has nothing to say because the note is near the
# staff:
#
#     Bassoon 1 m7   truth C4        read as `Ab1` AND `C4`
#     Bassoon 2 m7   truth C4        read as nothing
#
# Two adjacent bassoon staves contested one notehead, distance awarded it to
# the upper one, and the reading it kept was `Ab1` — MIDI 32, below the
# bassoon's written range of (34, 72) — while the reading it discarded was C4,
# squarely inside it. A player cannot sound the note we chose, and the note we
# threw away is the one that was printed.
#
# `instruments.Instrument.written_range` already carries a generous written
# range for every instrument in the lexicon. What is missing at this point in
# the run is WHICH instrument each staff is: the contextual pass names the
# parts, and it runs after this. So the names come from the DOSSIER instead,
# on the same terms the rest of the dossier layer uses — only where the page's
# staff count equals the work's part count, and abstaining otherwise. Without a
# dossier there is no verdict here and the rule below is exactly what it was.
#
# GENEROUS ON PURPOSE. This is a veto on the impossible, not a judgement of the
# unlikely: it fires only when one reading is outside the range and the other
# is inside, so a part playing at the edge of its range is never touched.


def _pitch_midi(pitch: str | None) -> int | None:
    """MIDI number for a `C#4`-style pitch name, or None if unparseable."""
    if not pitch or len(pitch) < 2:
        return None
    letter = pitch[0].upper()
    step = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}.get(letter)
    if step is None:
        return None
    i = 1
    alter = 0
    while i < len(pitch) and pitch[i] in "#b":
        alter += 1 if pitch[i] == "#" else -1
        i += 1
    try:
        octave = int(pitch[i:])
    except ValueError:
        return None
    return (octave + 1) * 12 + step + alter


def _in_written_range(pitch: str | None,
                      rng: tuple[int, int] | None) -> bool | None:
    """True/False if the pitch is inside the part's range, None if unknown."""
    if rng is None:
        return None
    midi = _pitch_midi(pitch)
    if midi is None:
        return None
    return rng[0] <= midi <= rng[1]


def _staff_written_ranges(
    page: dict[str, Any], dossier: dict[str, Any] | None,
) -> dict[int, tuple[int, int]]:
    """staff_index -> the written MIDI range of the part printed on it.

    Empty unless the dossier's part count matches the page's staff count, which
    is the same join `dossier.slot_facts_for_page` makes and abstains on.
    """
    if not dossier:
        return {}
    staves = [st for sys_ in page.get("systems", [])
              for st in sys_.get("staves", [])]
    facts = slot_facts_for_page(len(staves), dossier)
    if not facts or len(facts) != len(staves):
        return {}
    from .instruments import lookup as lookup_instrument  # noqa: PLC0415

    out: dict[int, tuple[int, int]] = {}
    for staff, fact in zip(sorted(staves, key=lambda s: s.get("staff_index", 0)),
                           facts):
        name = (fact or {}).get("part")
        if not name:
            continue
        match = lookup_instrument(name)
        rng = getattr(getattr(match, "instrument", None), "written_range", None)
        if rng:
            out[staff.get("staff_index")] = tuple(rng)
    return out


def _ledger_rows(page: dict[str, Any]) -> list[tuple[float, float, float]]:
    """Every ledger-line detection on the page as `(x0, x1, y_centre)`.

    Collected across ALL staves without deduplication: this only ever answers
    "is there a rung here", so a rung seen from two cells is not a problem.
    """
    rows: list[tuple[float, float, float]] = []
    for sys_ in page.get("systems", []):
        for staff in sys_.get("staves", []):
            for measure in staff.get("measures", []):
                for det in measure.get("detections", []):
                    if det.get("class") != "ledgerLine":
                        continue
                    box = det.get("bbox_page")
                    if not box or len(box) != 4:
                        continue
                    rows.append((box[0], box[0] + box[2], box[1] + box[3] / 2.0))
    return rows


def _ledger_ladder(
    box: Sequence[float],
    band: tuple[float, ...],
    ledgers: Sequence[tuple[float, float, float]],
) -> tuple[int, int]:
    """`(complete, rungs)` for the ladder joining this staff to the glyph.

    `complete` is 1 only when EVERY rung the glyph's distance calls for is
    present, so it sorts an unbroken ladder above a broken one of any length.
    Both are 0 for a glyph inside the staff, which needs no ladder.
    """
    if len(band) < 3:
        return (0, 0)
    top, bottom, spacing = band[0], band[1], band[2]
    if spacing <= 0:
        return (0, 0)
    x0, y0, w, h = box[0], box[1], box[2], box[3]
    y_centre = y0 + h / 2.0
    if y_centre < top:
        anchor, sign = top, -1.0
    elif y_centre > bottom:
        anchor, sign = bottom, 1.0
    else:
        return (0, 0)       # inside the staff — no ladder, and none needed
    n_expected = int(abs(y_centre - anchor) / spacing
                     + _LEDGER_RUNG_EXPECTED_SLACK)
    if n_expected <= 0:
        return (0, 0)
    tol = _LEDGER_RUNG_Y_TOL_SPACES * spacing
    min_overlap = _LEDGER_RUNG_MIN_X_OVERLAP * max(1.0, w)
    found = 0
    for k in range(1, n_expected + 1):
        rung_y = anchor + sign * k * spacing
        for lx0, lx1, ly in ledgers:
            if abs(ly - rung_y) > tol:
                continue
            if min(lx1, x0 + w) - max(lx0, x0) < min_overlap:
                continue
            found += 1
            break
    return (1 if found == n_expected else 0, found)


# Two boxes this far into each other are the same glyph seen from two staves,
# not two glyphs that happen to touch. Swept over all three orchestral works at
# 0.25/0.3/0.4/0.5 (benchmarks/omr-orchestral-e2e/DEDUPE_THRESHOLD.md): 0.3 is
# best on Brahms, tied-best on Beethoven, near-best on Mahler, and is the
# LOWEST value that costs no correctly-matched note on any of them — 0.25 drops
# three on Brahms by starting to merge genuinely distinct neighbours.
_CROSS_STAFF_DUPLICATE_IOU = 0.3

# A hairpin is printed in the GAP below its own staff, so — unlike a ledger
# notehead, which sits nearer whichever staff it belongs to — a contested
# hairpin's centre falls roughly midway between the two staves bracketing that
# gap, and DISTANCE is close to a coin flip. Measured on the Mahler 5 fixture
# (benchmarks/omr-hairpins-2026-09/FINDINGS.md §2): three of its four hairpins
# landed on staff 18 by 5-62 px, which has ZERO detected noteheads anywhere on
# the page, while staff 17 above it — the Trumpet staff the hairpins actually
# belong to — carries notes in every one of those bars. A hairpin has no
# ledger ladder, so this is a separate veto rather than a variant of it.
_WEDGE_HAIRPIN_CLASSES = {"dynamicCrescendoHairpin", "dynamicDiminuendoHairpin"}


def _bbox_center_y(det: dict[str, Any]) -> float:
    x, y, w, h = det["bbox_page"]
    return y + h / 2.0


def _bbox_iou_xywh(a: list[int], b: list[int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x0, y0 = max(ax, bx), max(ay, by)
    x1, y1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    inter = (x1 - x0) * (y1 - y0)
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _distance_to_band(y: float, top: float, bottom: float) -> float:
    """0 inside the staff's band, else the distance to its nearer edge."""
    if y < top:
        return top - y
    if y > bottom:
        return y - bottom
    return 0.0


def _roster_range_veto_mode() -> str:
    """`OMR_ROSTER_RANGE_VETO` — feed tier 2 from roster identity, not a dossier.

    `off` (default) · `label` (identity sourced `label` or `roster` only) ·
    `all` (also accept the `score_order` prior).

    ⚠️ **The two are measured separately and the difference is not cosmetic.**
    A `score_order` identity is a hypothesis about where a staff SITS, wrong
    about one staff in ten — and a wrong identity here does not merely fail to
    help, it DELETES A REAL NOTE. `label` is the conservative arm.
    """
    raw = os.environ.get("OMR_ROSTER_RANGE_VETO", "0").strip().lower()
    if raw in ("0", "", "off", "false", "no"):
        return "off"
    if raw == "all":
        return "all"
    return "label"


#: Identity provenances trustworthy enough to delete a note on. `roster` is a
#: name PRINTED on the document's own roster system; `label` is printed on this
#: staff. `score_order` is deduced from position and is admitted only by `all`.
_RANGE_VETO_READ_SOURCES = frozenset({"label", "roster", "score_order_ambiguity"})


def _contest_dump_enabled() -> bool:
    """`OMR_CONTEST_DUMP` — record contested notehead pairs onto the page dict.

    Instrumentation for the range-veto reach probe
    (`benchmarks/omr-range-veto-2026-09/`). Off by default and verdict-neutral:
    it only ever APPENDS to a list, so a run with it on removes exactly the same
    detections as a run with it off.
    """
    return os.environ.get(
        "OMR_CONTEST_DUMP", "0").strip().lower() in ("1", "true", "yes", "on")


def _dedupe_cross_staff_detections(
    page: dict[str, Any],
    bands: dict[int, tuple[int, ...]],
    *,
    iou_threshold: float = _CROSS_STAFF_DUPLICATE_IOU,
    dossier: dict[str, Any] | None = None,
    deferred: list[dict[str, Any]] | None = None,
) -> int:
    """Drop glyphs claimed by more than one staff. Returns how many went.

    `bands` maps a staff index to `(top, bottom)` or `(top, bottom, spacing)`.
    The spacing is what places a staff's ledger rungs, so a band given without
    one simply falls back to distance — which is what the rule was before the
    ledger arbitration and still is for every glyph with no ladder either way.
    """
    entries: list[tuple[int, dict[str, Any], list[dict[str, Any]]]] = []
    for sys_ in page.get("systems", []):
        for staff in sys_.get("staves", []):
            idx = staff.get("staff_index")
            if idx not in bands:
                continue
            for measure in staff.get("measures", []):
                for det in measure.get("detections", []):
                    entries.append((idx, det, measure["detections"]))

    # Bucket by vertical position so this stays linear-ish on a dense page
    # instead of comparing every glyph with every other one.
    buckets: dict[int, list[int]] = {}
    BUCKET = 64
    for i, (_idx, det, _lst) in enumerate(entries):
        key = int(_bbox_center_y(det)) // BUCKET
        for k in (key - 1, key, key + 1):
            buckets.setdefault(k, []).append(i)

    # Rungs are only consultable where every band carries a spacing; otherwise
    # this is the old distance-only rule, unchanged.
    ledgers = (_ledger_rows(page)
               if all(len(b) >= 3 for b in bands.values()) else None)
    ranges = _staff_written_ranges(page, dossier)
    contests: list[dict[str, Any]] = []
    pair_meta: list[dict[str, Any]] = []

    # PAIRWISE, and a cluster-winner refactor was measured and REJECTED.
    # Grouping every overlapping copy and letting the group pick one winner is
    # the tidier formulation and it scored worse — 0.2275 against 0.2263 — for
    # a reason worth recording: IoU overlap is not transitive, so A-B and B-C
    # chain A and C into one cluster even where they are genuinely different
    # glyphs, and the group then throws one of them away. Removing one of each
    # overlapping PAIR cannot make that mistake.
    #
    # STRONGEST VERDICT FIRST, though, which is what pairing alone got wrong.
    # Deciding pairs in whatever order the buckets produced let an arbitrary
    # distance call eliminate a copy before a pair that actually KNEW the
    # answer was ever looked at: measured on Beethoven's two bassoons, one bar
    # resolved on the range veto and the next, identical in shape, did not.
    # So every contested pair is judged first, then applied in order of how
    # much the judgement rests on.
    verdicts: list[tuple[int, int, int]] = []   # (rank, loser, winner)
    seen: set[tuple[int, int]] = set()
    for idxs in buckets.values():
        for pos_a in range(len(idxs)):
            i = idxs[pos_a]
            for pos_b in range(pos_a + 1, len(idxs)):
                j = idxs[pos_b]
                pair = (i, j) if i < j else (j, i)
                if pair in seen:
                    continue
                seen.add(pair)
                si, di, lst_i = entries[i]
                sj, dj, lst_j = entries[j]
                if si == sj or di.get("category") != dj.get("category"):
                    continue
                if _bbox_iou_xywh(di["bbox_page"], dj["bbox_page"]) <= iou_threshold:
                    continue
                # Same glyph, two staves. Four kinds of evidence, in the order
                # a reader uses them: the LADDER is about this glyph — an
                # unbroken run of ledger lines physically joins it to a staff;
                # the RANGE is about the part — a player cannot sound a note
                # outside it; NOTES-IN-BAR is about a hairpin specifically — it
                # has nothing to attach to on a staff with no note in this bar;
                # DISTANCE is the tie-break and, on a page with none of the
                # above, still the whole rule.
                is_note = di.get("category") == "notehead"
                is_hairpin = (di.get("class") in _WEDGE_HAIRPIN_CLASSES
                              and dj.get("class") in _WEDGE_HAIRPIN_CLASSES)
                rank, loser = 0, None
                if is_note and ledgers is not None:
                    ladder_i = _ledger_ladder(di["bbox_page"], bands[si], ledgers)
                    ladder_j = _ledger_ladder(dj["bbox_page"], bands[sj], ledgers)
                    # Completeness alone: a broken ladder is not evidence (its
                    # rungs may belong to the other staff's note), so unless
                    # exactly one side is unbroken the pair falls through.
                    if ladder_i[0] != ladder_j[0]:
                        rank, loser = 2, (i if ladder_i[0] < ladder_j[0] else j)
                if loser is None and is_note and ranges:
                    # A veto on the IMPOSSIBLE, not a judgement of the
                    # unlikely: it fires only when one reading falls outside
                    # its part's range and the other falls inside its own, so
                    # a part playing at the edge of its range is never touched.
                    fit_i = _in_written_range(di.get("pitch"), ranges.get(si))
                    fit_j = _in_written_range(dj.get("pitch"), ranges.get(sj))
                    if fit_i is not None and fit_j is not None and fit_i != fit_j:
                        rank, loser = 1, (i if not fit_i else j)
                if loser is None and is_hairpin:
                    # `annotate_wedges_in_slot` anchors a hairpin to noteheads
                    # on its OWN staff at both ends (see export.py) — a staff
                    # with no notehead in this bar can never export it, so it
                    # is never the right side of a contest a note-bearing
                    # staff is also in. Same "veto on the impossible" shape as
                    # the range check above, just keyed on presence rather
                    # than pitch.
                    has_i = any(d.get("category") == "notehead" for d in lst_i)
                    has_j = any(d.get("category") == "notehead" for d in lst_j)
                    if has_i != has_j:
                        rank, loser = 1, (i if not has_i else j)
                if loser is None:
                    ti, bi = bands[si][0], bands[si][1]
                    tj, bj = bands[sj][0], bands[sj][1]
                    loser = (
                        i if _distance_to_band(_bbox_center_y(di), ti, bi)
                        > _distance_to_band(_bbox_center_y(dj), tj, bj)
                        else j
                    )
                winner = j if loser == i else i
                verdicts.append((rank, loser, winner))
                if deferred is not None and is_note and rank == 0:
                    # DEFERRED RE-ARBITRATION. Tier 2 wants the staff's
                    # instrument, and on a dossier-free run that identity does
                    # not exist yet — `apply_contextual_analysis` runs after
                    # every page is built. So a pair distance alone decided is
                    # parked here with references to the two detections, and
                    # re-judged once identity exists.
                    #
                    # ⚠️ ONLY rank 0. A ladder-decided pair is NOT parked: the
                    # ladder is tier 2 above the range in the existing order,
                    # and an unbroken run of ledger lines physically joining a
                    # glyph to a staff is stronger evidence than what the part
                    # can play. Re-opening those would invert the tiers.
                    pair_meta.append({
                        "loser": loser, "winner": winner,
                        "staff_loser": si if loser == i else sj,
                        "staff_winner": sj if loser == i else si,
                    })
                if _contest_dump_enabled():
                    # REACH INSTRUMENTATION ONLY (OMR_CONTEST_DUMP=1), and it
                    # changes no verdict — it records the contest so a probe can
                    # ask, after the contextual pass has named the staves, how
                    # many of these a roster-sourced range veto could speak on.
                    # Written per pair, both sides, with the tier that actually
                    # decided it, because "would tier 2 have reached this" is
                    # only interesting where the ladder did NOT already settle it.
                    contests.append({
                        "staff_i": si, "staff_j": sj,
                        "category": di.get("category"),
                        "class_i": di.get("class"), "class_j": dj.get("class"),
                        "pitch_i": di.get("pitch"), "pitch_j": dj.get("pitch"),
                        "conf_i": di.get("confidence"),
                        "conf_j": dj.get("confidence"),
                        "decided_by": {2: "ladder", 1: "range_or_hairpin"}.get(
                            rank, "distance"),
                        "loser_staff": si if loser == i else sj,
                    })

    if _contest_dump_enabled():
        page["contested_notehead_pairs"] = contests

    doomed: set[int] = set()
    for _rank, loser, winner in sorted(verdicts, key=lambda v: -v[0]):
        if loser in doomed or winner in doomed:
            continue
        doomed.add(loser)

    if deferred is not None:
        # A parked pair is only real where the distance call ACTUALLY killed
        # this loser and left this winner standing. A pair whose loser was
        # already doomed by a stronger verdict, or whose winner died elsewhere,
        # has nothing for the range tier to reverse.
        page_index = page.get("page_index")
        for meta in pair_meta:
            lo, wi = meta["loser"], meta["winner"]
            if lo not in doomed or wi in doomed:
                continue
            deferred.append({
                "page_index": page_index,
                "staff_loser": meta["staff_loser"],
                "staff_winner": meta["staff_winner"],
                "det_loser": entries[lo][1],
                "det_winner": entries[wi][1],
                "list_loser": entries[lo][2],
                "list_winner": entries[wi][2],
            })

    for i in sorted(doomed, reverse=True):
        _idx, det, lst = entries[i]
        try:
            lst.remove(det)
        except ValueError:  # already gone
            pass
    return len(doomed)


def _apply_roster_range_veto(
    result: dict[str, Any],
    deferred: list[dict[str, Any]],
    *,
    mode: str,
) -> dict[str, Any]:
    """Re-judge distance-decided notehead contests against roster identity.

    Tier 2 of `_dedupe_cross_staff_detections` — the instrument's written range
    — has never fired on a scan: `_staff_written_ranges` returns `{}` when there
    is no dossier, and the scan gate runs dossier-free by protocol. `OMR_ROSTER`
    now supplies per-staff identity read from the PAGE, so the tier can be fed
    without one; it just arrives too late, because the contextual pass runs
    after every page is built. This is that tier, deferred.

    ⚠️ **A VETO ON THE IMPOSSIBLE, NEVER ON THE UNLIKELY**, which is the
    existing rule for this tier and is load-bearing. A swap happens only where
    the kept reading falls OUTSIDE its own part's written range and the dropped
    one falls INSIDE its own — a part playing at the edge of its range is never
    touched, and neither is a pair where both readings are possible. Widening
    this into a preference would make the tier a soft prior.

    ⚠️ **Written pitch, not concert.** `written_range` follows the project's
    written-pitch convention, and the detections carry what is printed; a
    concert-pitch comparison would false-veto every transposing staff.
    """
    from .instruments import lookup as lookup_instrument  # noqa: PLC0415

    identity: dict[tuple[Any, Any], dict[str, Any]] = {}
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                name = staff.get("instrument")
                if not name:
                    continue
                identity[(page.get("page_index"), staff.get("staff_index"))] = {
                    "instrument": name,
                    "source": staff.get("instrument_source"),
                }

    ranges: dict[str, tuple[int, int] | None] = {}

    def _range(name: str) -> tuple[int, int] | None:
        if name not in ranges:
            match = lookup_instrument(name)
            rng = getattr(getattr(match, "instrument", None),
                          "written_range", None)
            ranges[name] = tuple(rng) if rng else None
        return ranges[name]

    def _usable(key: tuple[Any, Any]) -> dict[str, Any] | None:
        ident = identity.get(key)
        if ident is None:
            return None
        if mode != "all" and ident["source"] not in _RANGE_VETO_READ_SOURCES:
            return None
        return ident

    swaps: list[dict[str, Any]] = []
    # One detection may sit in several parked pairs. A detection already moved
    # is off the table for the rest, so a swap can never be undone by the next
    # pair or applied twice.
    touched: list[int] = []
    for rec in deferred:
        det_w, det_l = rec["det_winner"], rec["det_loser"]
        if id(det_w) in touched or id(det_l) in touched:
            continue
        id_w = _usable((rec["page_index"], rec["staff_winner"]))
        id_l = _usable((rec["page_index"], rec["staff_loser"]))
        if not (id_w and id_l):
            continue
        fit_w = _in_written_range(det_w.get("pitch"), _range(id_w["instrument"]))
        fit_l = _in_written_range(det_l.get("pitch"), _range(id_l["instrument"]))
        if fit_w is None or fit_l is None or fit_w or not fit_l:
            continue                      # both possible, both impossible, or
                                          # the kept reading is already the fine
                                          # one — nothing to veto.
        if det_w not in rec["list_winner"]:
            continue                      # something downstream already took it
        rec["list_winner"].remove(det_w)
        rec["list_loser"].append(det_l)
        touched.extend((id(det_w), id(det_l)))
        swaps.append({
            "page_index": rec["page_index"],
            "kept_staff": rec["staff_loser"],
            "kept_instrument": id_l["instrument"],
            "kept_pitch": det_l.get("pitch"),
            "kept_source": id_l["source"],
            "dropped_staff": rec["staff_winner"],
            "dropped_instrument": id_w["instrument"],
            "dropped_pitch": det_w.get("pitch"),
            "dropped_source": id_w["source"],
        })
    return {"mode": mode, "n_parked": len(deferred),
            "n_swapped": len(swaps), "swaps": swaps}


# ─── A notehead outside the staff must hang on SOMETHING ────────────────────
#
# The edge-fragment rule (`_drop_clipped_notehead_fragments`) catches the
# sliver a crop cuts; a letter bowl printed BETWEEN staves is whole, notehead-
# sized, and lands in the cell's interior, so it sails past that rule. On the
# benchmark: the descender bowl of the "g" in "Allegro" read as a whole note
# on Beethoven's Flute 1, the "legato" between Brahms's oboe staves as a D6, a
# key-signature flat's bowl as an Ab4, and a bare ledger line as a G2.
#
# What separates them is that a real note outside the staff is HELD there —
# by the ledger ladder the engraver drew for it — and the detector believed
# in it. Neither signal is enough alone: ledger recall is imperfect, so real
# notes with ZERO found rungs exist (all at confidence 0.82+ on the three
# works), and low confidence alone would starve dense pages. Together they
# separate cleanly: the four fakes run 0.45-0.53, the lowest real outside-
# staff notehead is 0.76. The constant sits mid-gap.
#
# The veto needs ALL of: centre outside the five-line band, at least one rung
# expected, none found, confidence below the bar. Inside-staff detections are
# never touched, whatever their confidence.
_UNLADDERED_NOTEHEAD_MAX_CONF = 0.65


def _drop_furniture_measures(page: dict[str, Any]) -> int:
    """Take out the measure columns that are system furniture, not music.

    A system's opening rule and the bracket or brace beside it are two vertical
    strokes a barline's width apart, and `detect_barlines` reads them as two
    barlines with a measure between. Dvorak 9's Simrock print is the clean case:
    a cell 56 px wide — 2.2 staff spaces, narrower than a notehead and its stem,
    on a page whose real measures run 299 to 731 px — holding one `brace`
    detection at confidence 0.33, on all fifteen staves. Every staff then emits
    nine measures where the page prints eight.

    ⚠️ **WIDTH IS NOT THE TEST, and it was checked before being rejected**
    (`benchmarks/omr-scan-e2e-2026-09/RESULTS.md` §1): genuine measures on those
    five pages run 4.2 to 28.7 staff spaces against 2.2 and 3.5 for the two
    spurious ones. A 0.7-space gap on a five-page corpus is a threshold to tune,
    not a cliff to sit on — and it would also miss the WTC case below, which is
    12.5 spaces wide and just as spurious.

    CONTENT is the test, asked at the level the answer lives at. **A barline
    spans the system**, so a column is furniture for every staff of a system or
    for none of them; per-staff emptiness says nothing, because any staff may be
    tacet, while a column where not one staff of fifteen carries a notehead or a
    rest is a different object. A genuine measure on even a fully tacet staff
    contains its whole-bar rest.

    Measured over **243 measure columns, 27 systems, 20 committed
    transcriptions** of many publishers
    (`benchmarks/omr-scan-e2e-2026-09/probe_furniture_columns.py`): exactly
    **two** columns carry no notehead and no rest on any staff — 0.82% — and
    both are furniture. The second was not one of the two RESULTS.md found:
    WTC I p.17 system 1 opens with a 463 px cell holding `clef ×2,
    accidental ×8` and no notes, where every other system on that page carries
    its clef and key signature inside a first measure that also plays.

    "Has music" is `voicing.group_chords_in_measure` — the EXPORTER's own test
    for whether a measure needs a whole-bar rest — so the rule and the thing it
    protects cannot drift apart.

    ⚠️ **Leading and trailing columns only.** Furniture is what sits OUTSIDE the
    music, at the ends a system's rules bound. A silent column in the MIDDLE is
    a different animal: a spurious barline there splits one bar into two halves
    that both still hold notes, so a music-free middle column is much more
    likely a bar the detector failed on — and dropping it would splice its
    neighbours together and shift every measure after it. Those are kept.

    Returns `(cells removed, detections removed with them)`, so the page's
    running totals stay true rather than counting glyphs that are no longer in
    the output.
    """
    dropped = 0
    dropped_detections = 0
    for system in page.get("systems", []):
        staves = system.get("staves", [])
        if not staves:
            continue
        width = max((len(s.get("measures", [])) for s in staves), default=0)
        if width < 2:
            continue

        def _has_music(m: int) -> bool:
            return any(
                group_chords_in_measure(
                    s["measures"][m].get("detections") or [])
                for s in staves if m < len(s.get("measures", []))
            )

        voiced = [m for m in range(width) if _has_music(m)]
        if not voiced:
            # Nothing to anchor on. A system the detector read no music in at
            # all is a recognition failure, not a furniture question, and
            # deleting its measures would turn a bad reading into no reading.
            continue
        keep = set(range(voiced[0], voiced[-1] + 1))
        if len(keep) == width:
            continue
        lead_dropped = voiced[0] > 0
        for staff in staves:
            measures = staff.get("measures", [])
            kept = [m for i, m in enumerate(measures) if i in keep]
            dropped += len(measures) - len(kept)
            dropped_detections += sum(
                len(m.get("detections") or [])
                for i, m in enumerate(measures) if i not in keep
            )
            for new_index, measure in enumerate(kept):
                measure["measure_index"] = new_index
            staff["measures"] = kept
            staff["n_measures"] = len(kept)
            # The staff-level summary is "what was in effect during the staff's
            # FIRST measure", and dropping a leading column moves which measure
            # that is. Leaving it stale is not cosmetic: `_lily_staff_block`
            # emits one `\clef` per staff from this field, so on Dvorak it would
            # print treble for the bassoon and both trombones — and, worse, it
            # would do so only AFTER this pass removed the furniture cell that
            # `export._first_clef_bearing_measure` was recovering the clef from.
            # A fix must not disarm the other fix that covers it.
            if lead_dropped and kept:
                for field in ("clef", "key_signature", "time_signature"):
                    if kept[0].get(field) is not None:
                        staff[field] = kept[0][field]
        system["n_measures_dropped_as_furniture"] = width - len(keep)
    return dropped, dropped_detections


def _drop_unladdered_noteheads(
    page: dict[str, Any],
    bands: dict[int, tuple[int, ...]],
    *,
    max_conf: float = _UNLADDERED_NOTEHEAD_MAX_CONF,
) -> int:
    """Drop low-confidence outside-staff noteheads with no ledger ladder.

    Returns how many went. Abstains entirely unless every band carries a
    spacing — the same gate the dedupe's ladder arbitration uses.
    """
    if not bands or not all(len(b) >= 3 for b in bands.values()):
        return 0
    ledgers = _ledger_rows(page)
    n_dropped = 0
    for sys_ in page.get("systems", []):
        for staff in sys_.get("staves", []):
            idx = staff.get("staff_index")
            if idx not in bands:
                continue
            top, bottom, spacing = bands[idx][0], bands[idx][1], bands[idx][2]
            if spacing <= 0:
                continue
            for measure in staff.get("measures", []):
                dets = measure.get("detections", [])
                for det in list(dets):
                    if det.get("category") != "notehead":
                        continue
                    if det.get("confidence", 1.0) >= max_conf:
                        continue
                    box = det.get("bbox_page")
                    if not box or len(box) != 4:
                        continue
                    y_centre = box[1] + box[3] / 2.0
                    dist = _distance_to_band(y_centre, top, bottom)
                    n_expected = int(dist / spacing
                                     + _LEDGER_RUNG_EXPECTED_SLACK)
                    if n_expected < 1:
                        continue
                    _, found = _ledger_ladder(box, bands[idx], ledgers)
                    if found == 0:
                        dets.remove(det)
                        n_dropped += 1
    return n_dropped


# ---------------------------------------------------------------------------
# Meter → rhythm feedback (the loop that was open)
# ---------------------------------------------------------------------------
#
# Until now the meter was derived FROM the durations and then used only to
# complain about them: `resolve_rhythms_for_cell` takes no time signature at
# all, `backfill_page_time_signatures` votes a meter out of the durations the
# pipeline already committed to, and `_annotate_column_rhythm_warnings` writes
# a warning. A 4/4 bar summing to 4.53 beats was flagged and shipped, and
# nothing ever re-read the note that made it 4.53.
#
# This closes that loop for the one duration input fragile enough to be worth
# arbitrating: the BEAM LEVEL. A notehead's duration comes from counting beam
# strokes clustered by y-position, so one extra or one missing cluster halves
# or doubles it — and a half-or-double error in one beamed group is exactly
# the kind of error a known bar length can pin down.
#
# It is deliberately narrow, because the repository's history is full of
# plausible corrections that made things worse:
#
#   * It only ever RE-READS a beam level by ±1. It never adds, deletes or
#     re-pitches a note, so it cannot paper over the over-detection thread.
#   * It requires the corrected bar to land EXACTLY on the meter, within the
#     same tolerance the warning uses.
#   * It requires the answer to be UNIQUE. If two different groups could each
#     be adjusted to make the sum work, we do not know which is right, so
#     nothing is changed and the warning stands.
#   * It runs on single-voice measures only. Deciding which voice a beam group
#     belongs to is its own unsolved join, and orchestral staves — the case
#     this is for — are overwhelmingly single-voice anyway.
#
# Every change is recorded on the measure as `rhythm_reconciliation`, so a run
# can be audited for what the meter talked the pipeline out of.

_BEAM_LEVEL_MIN, _BEAM_LEVEL_MAX = 1, 4


def _det_x_center(det: dict[str, Any]) -> int:
    """x-centre of a detection in cell-local coords.

    `bbox` is [x, y, w, h] — not [x0, y0, x1, y1] — and this matches
    `voicing._x_center` exactly, so beam grouping and chord grouping agree on
    where a notehead sits. They have to: the correction below is scored against
    a bar sum that voicing computed.
    """
    bbox = det.get("bbox", [0, 0, 0, 0])
    return bbox[0] + bbox[2] // 2


def _beam_groups(detections: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Cluster beamed noteheads into groups that plausibly share one beam.

    A group is a run of noteheads carrying the same `beam_levels`, adjacent in
    x with no differently-beamed note between them. That is what a beam group
    looks like on the page, and it is the unit whose level is right or wrong
    together.
    """
    beamed = [
        d for d in detections
        if d.get("category") == "notehead" and d.get("beam_levels")
        # A tuplet note is excluded, not because re-reading its beam level is
        # meaningless but because `_duration_for_level` re-derives a duration
        # from beam count and dots alone and would silently drop the tuplet
        # ratio. The bar sum below still counts the tuplet's scaled durations,
        # so another group in the same bar can still be arbitrated.
        and not d.get("tuplet")
    ]
    if not beamed:
        return []
    beamed.sort(key=_det_x_center)
    groups: list[list[dict[str, Any]]] = [[beamed[0]]]
    for d in beamed[1:]:
        if d["beam_levels"] == groups[-1][-1]["beam_levels"]:
            groups[-1].append(d)
        else:
            groups.append([d])
    return groups


def _duration_for_level(det: dict[str, Any], level: int) -> tuple[float, str] | None:
    """What this notehead's duration would be at `level` beams, dots included."""
    base = _BEAM_COUNT_DURATIONS.get(level)
    if base is None:
        return None
    base_beats, base_type = base
    n_dots = int(det.get("dots", 0) or 0)
    return (
        base_beats * _dot_multiplier(n_dots),
        f"{_name_for_dots(n_dots)}{base_type}",
    )


def _reconcile_measure_to_meter(
    measure: dict[str, Any],
    *,
    tolerance: float = _RHYTHM_SUM_TOLERANCE,
) -> dict[str, Any] | None:
    """Re-read one beam level so the bar sums to its meter. See above.

    Mutates `measure` and returns a record of what changed, or None when
    nothing could be decided (which is the common case, and the safe one).
    """
    ts = measure.get("time_signature")
    if not ts:
        return None
    num, den = ts.get("numerator"), ts.get("denominator")
    if not num or not den:
        return None
    expected = num * 4.0 / den

    detections = measure.get("detections", [])
    events = group_chords_in_measure(detections)
    voices = split_events_into_voices(events)
    if len(voices) != 1:
        return None  # see the note above on the voice join
    actual = sum(ev["duration_beats"] for ev in voices[0])
    if abs(actual - expected) <= tolerance:
        return None

    groups = _beam_groups(detections)
    if not groups:
        return None

    candidates: list[dict[str, Any]] = []
    for gi, group in enumerate(groups):
        level = int(group[0]["beam_levels"])
        # A chord's noteheads share one stem and one duration, so the bar sum
        # counts the group's duration once per EVENT, not once per notehead.
        # Collapse by x so a chord is not counted twice.
        by_x = {}
        for d in group:
            by_x.setdefault(_det_x_center(d), d)
        distinct = list(by_x.values())
        current = sum(float(d.get("duration_beats", 0.0)) for d in distinct)
        for delta in (-1, 1):
            new_level = level + delta
            if not (_BEAM_LEVEL_MIN <= new_level <= _BEAM_LEVEL_MAX):
                continue
            replacement = 0.0
            ok = True
            for d in distinct:
                nd = _duration_for_level(d, new_level)
                if nd is None:
                    ok = False
                    break
                replacement += nd[0]
            if not ok:
                continue
            if abs((actual - current + replacement) - expected) <= tolerance:
                candidates.append({
                    "group_index": gi,
                    "from_level": level,
                    "to_level": new_level,
                    "n_noteheads": len(group),
                })

    if len(candidates) != 1:
        # Nothing to do, or more than one way to do it. Either way the meter
        # has not identified a single note, so the measure is left as read and
        # `_annotate_column_rhythm_warnings` still flags it.
        return None

    choice = candidates[0]
    for d in groups[choice["group_index"]]:
        nd = _duration_for_level(d, choice["to_level"])
        if nd is None:
            continue
        d["duration_beats"], d["duration_type"] = round(nd[0], 4), nd[1]
        d["beam_levels"] = choice["to_level"]

    record = {
        **choice,
        "expected_beats": round(expected, 4),
        "beats_before": round(actual, 4),
        "meter_source": ts.get("source", "detected"),
    }
    measure["rhythm_reconciliation"] = record
    return record


def _reconcile_page_to_meter(page: dict[str, Any]) -> int:
    """Run the meter→rhythm correction over every measure of a page."""
    n = 0
    for sys_ in page.get("systems", []):
        for staff in sys_.get("staves", []):
            for measure in staff.get("measures", []):
                if _reconcile_measure_to_meter(measure) is not None:
                    n += 1
    return n


# Ported verbatim from the dossier-verification track so the column rhythm
# verifier is implemented ONCE, parameterized by meter-source (it reads each
# measure's `time_signature`, which `backfill_page_time_signatures` populates
# from beat-sum inference here, or a dossier there). Body kept byte-identical
# to that branch's copy for clean reconciliation — do not edit divergently.
def _annotate_column_rhythm_warnings(
    page: dict[str, Any], *, tolerance: float = _RHYTHM_SUM_TOLERANCE
) -> None:
    """Notation-math verifier, reshaped for dossier-back-filled pages (mutates
    `page` in place, writing `rhythm_sum_warning` onto measure dicts).

    The naive per-staff-per-measure check (`_measure_rhythm_sum_warning`) is
    fine when a meter was genuinely detected/inferred, but it over-fires
    catastrophically once a dossier *force-fills* a meter onto a sparse
    orchestral page: an empty/resting staff-measure sums to 0 and would flag
    `{expected:3, actual:0}`, and even correctly-transcribed sparse bars sum
    short because rests are under-detected (Boléro p.1's real 3/4 bars mostly
    sum to ~2.0). Forcing the per-staff check there would flag nearly every
    staff-measure — useless.

    So aggregate to the measure COLUMN across all staves of a system (mirroring
    the per-column MAX that beat-sum *inference* already uses,
    `rhythm._page_column_lengths`):

    * **Over-sum** (a voice longer than its bar): high-confidence. Extra beats
      mean a fused barline (cross-referenced via `phase1_warning`) or
      over-detected notes. Flag each over-long *staff-measure* (that's the cell
      to inspect).
    * **Under-sum**: flag only when the FULLEST voice across the WHOLE column
      still falls short — never a resting/sparse staff whose column-mates fill
      the bar. Low-confidence (usually an under-detected rest). Attached to the
      fullest measure in the column.
    * A column whose fullest voice reaches the bar does **not** flag at all,
      even though its individual sparse staves sum short. This is the precision
      win over the naive path.

    Columns with no note anywhere (all rest/empty) carry no rhythm evidence and
    are skipped. Only measures whose `time_signature` is known participate.
    """
    for system in page.get("systems", []):
        # Group this system's measures into time-columns. Staves within a
        # system share a renumbered `measure_index`, so it keys the columns.
        columns: dict[int, list[dict[str, Any]]] = {}
        for staff in system.get("staves", []):
            for md in staff.get("measures", []):
                ts = md.get("time_signature")
                if not ts:
                    continue
                num, den = ts.get("numerator"), ts.get("denominator")
                if not num or not den:
                    continue
                length, has_note = measure_length_beats(md.get("detections", []))
                columns.setdefault(md.get("measure_index", 0), []).append({
                    "md": md,
                    "length": length,
                    "has_note": has_note,
                    "expected": num * 4.0 / den,
                })

        for idx, members in columns.items():
            # Over-sum: a real (note-bearing) voice longer than its bar. A
            # rest-only measure's length is meaningless (a whole rest fills any
            # bar), so it can't over-flag.
            over = [
                m for m in members
                if m["has_note"] and m["length"] > m["expected"] + tolerance
            ]
            if over:
                for m in over:
                    md = m["md"]
                    md["rhythm_sum_warning"] = {
                        "expected_beats": round(m["expected"], 4),
                        "actual_beats": round(m["length"], 4),
                        "kind": "over_sum",
                        "severity": "high",
                        "column": idx,
                        "fused_suspected": bool(md.get("phase1_warning")),
                    }
                continue  # column already flagged; don't also under-flag it

            # Under-sum: only if the fullest voice in the whole column is short.
            noted = [m for m in members if m["has_note"] and m["length"] > 0]
            if not noted:
                continue  # all-resting column — no evidence, never flag
            fullest = max(noted, key=lambda m: m["length"])
            if fullest["length"] < fullest["expected"] - tolerance:
                md = fullest["md"]
                md["rhythm_sum_warning"] = {
                    "expected_beats": round(fullest["expected"], 4),
                    "actual_beats": round(fullest["length"], 4),
                    "kind": "under_sum",
                    "severity": "low",
                    "column": idx,
                }


# ---------------------------------------------------------------------------
# Cross-staff measure-count consistency (deterministic internal double-check)
# ---------------------------------------------------------------------------
#
# Barlines are engraved vertically through EVERY staff of a system, so after
# resegment_fused_measures renumbers measure_index 0..N-1 within a system
# (measure_extractor.py:693-696), every staff in that system must contain the
# same number of measures. A staff whose n_measures deviates from its siblings
# therefore localizes a segmentation error: TOO FEW measures means a barline was
# missed and two real measures were fused into one cell (or, benignly, the staff
# holds a condensed multi-measure rest — indistinguishable here without an
# external anchor); TOO MANY means a spurious barline split one measure in two.
#
# This is a pure integer invariant the pipeline already computed — ZERO meter /
# clef / register / transposition reasoning — which makes it the always-on,
# zero-external-input floor beneath the (planned) dossier-guided layer
# (docs/dossier-verification-plan.md, the `total_measures`/`structure_warning`
# row). With no external ground truth this check can only say "these staves
# disagree, at most one matches the true count": when a STRICT majority of staves
# agree it points at the minority as the anomaly, but it deliberately ABSTAINS on
# near-even splits (a 2-2 piano disagreement, a 3-3 tie) rather than guess which
# side is right — resolving those is exactly the job of the dossier layer's known
# measures-per-system.
#
# Multi-measure-rest / tacet false positives. The dominant false positive on real
# orchestral scores: a resting instrument prints a CONDENSED multi-measure rest —
# one wide bar spanning many measures — so its staff has far fewer cells than its
# playing siblings and its wide cell trips phase1_warning, looking exactly like a
# missed barline. We separate the two by NOTE CONTENT, which the pipeline already
# has: a fused pair of real measures is note-DENSE (music crammed in — 9-27
# noteheads observed on real fused cells), while a multi-measure rest is a wide,
# note-EMPTY cell (0 noteheads; a real Beethoven-5 tacet cell measured 2.2×-wide
# with zero detections). So a short staff is only promoted to high ("confirmed
# fused measure") when its wide cell CONTAINS noteheads; a short staff whose gap
# is a note-empty wide cell is flagged `likely_multimeasure_rest` and DOWN-WEIGHTED
# to low (still surfaced — it could be a note-suppressed fusion — but never
# high, even under strong consensus). Independently-barred systems remain an
# unresolved FP class the confidence grading (not a hard error) hedges against.

# Consensus -> label thresholds shared by the cross-staff consistency checks
# (measure-count below + key-signature further down): the fraction of the
# agreeing majority needed to call a flag high vs medium.
_CONSENSUS_HIGH = 0.8       # e.g. a lone dissenter among 5+ staves
_CONSENSUS_MED = 2.0 / 3    # a 2:1-or-better majority


def _measure_has_notehead(measure: dict[str, Any]) -> bool:
    """True if a measure cell contains at least one detected notehead — i.e. it
    holds real note content, not just rests / an empty wide multi-measure-rest
    bar. Used to tell a fused missed-barline cell (note-dense) apart from a
    condensed multi-measure rest (note-empty)."""
    return any(
        d.get("category") == "notehead" for d in measure.get("detections", [])
    )


def _flag_measure_count_inconsistency(system: dict[str, Any]) -> None:
    """Flag staves whose measure count disagrees with a strict majority of the
    other staves in the same system, mutating each deviating staff dict in
    place with a ``measure_count_warning``. See the module comment above.

    Pure additive post-pass: writes a key ONLY on a genuine cross-staff
    disagreement, so a system whose staves all agree — or a single-staff
    system, which has nothing to cross-check — is left byte-identical.

    Abstains entirely unless one measure count is held by a strict majority
    (more than half) of the staves; a tie or bare plurality gives no basis to
    call one staff the anomaly.
    """
    staves = system.get("staves") or []
    if len(staves) < 2:
        return  # a single staff has no sibling to cross-check against

    counts = [st.get("n_measures", 0) for st in staves]
    total = len(counts)
    mode_value, mode_k = Counter(counts).most_common(1)[0]

    # Strict majority required. mode_k * 2 > total means the modal group holds
    # MORE than half the staves, so the modal count is the unique mode and the
    # remaining (deviating) staves are unambiguously the minority. A 2-2 / 3-3 /
    # 1-1 split fails this and we abstain — never assert which side is wrong.
    if mode_k * 2 <= total:
        return

    consensus_strength = mode_k / total
    agreement = f"{mode_k}/{total}"

    for st in staves:
        n = st.get("n_measures", 0)
        if n == mode_value:
            continue
        deviation = n - mode_value  # signed: <0 too few, >0 too many

        # A SHORT staff's shortfall may be localized to a >2×-median (phase1)
        # cell. Split that case by note content (see module comment):
        #  - a phase1 cell WITH noteheads  -> a fused pair of real measures
        #    (missed barline). Corroborated -> promote to high; we can point a
        #    human at the exact cell to re-segment.
        #  - a phase1 cell with NO noteheads -> a wide note-empty bar, i.e. a
        #    condensed multi-measure rest / tacet staff (the dominant orchestral
        #    FP). Flag it, but DOWN-WEIGHT to low and never promote — even when
        #    the consensus is strong (e.g. a lone resting instrument among many).
        wide_cells = [m for m in st.get("measures", []) if "phase1_warning" in m]
        dense_wide = deviation < 0 and any(_measure_has_notehead(m) for m in wide_cells)
        empty_wide = deviation < 0 and any(not _measure_has_notehead(m) for m in wide_cells)
        phase1_corroborated = dense_wide
        likely_multimeasure_rest = empty_wide and not dense_wide

        if phase1_corroborated:
            label = "high"
        elif likely_multimeasure_rest:
            label = "low"   # down-weight the known multi-measure-rest FP class
        elif consensus_strength >= _CONSENSUS_HIGH:
            label = "high"
        elif consensus_strength >= _CONSENSUS_MED:
            label = "medium"
        else:
            label = "low"

        st["measure_count_warning"] = {
            "staff_measures": n,
            "system_mode": mode_value,
            "agreement": agreement,
            "deviation": deviation,
            "confidence": round(consensus_strength, 3),
            "confidence_label": label,
            "phase1_corroborated": phase1_corroborated,
            "likely_multimeasure_rest": likely_multimeasure_rest,
        }


# ---------------------------------------------------------------------------
# Cross-staff key-signature consistency (transposition-aware)
# ---------------------------------------------------------------------------
#
# A naive "all staves in a system share one key signature" check is useless on
# an orchestral score, because TRANSPOSING instruments legitimately print
# DIFFERENT written key signatures for the same concert key. The relationship is
# a fixed offset on the circle of fifths (sharps +, flats -): the written key =
# concert key + the instrument's offset. The common families —
#
#     C  (non-transposing)              offset  0   (writes concert C as C)
#     F  (horn, English horn)           offset +1   (...as G, 1 sharp)
#     Bb (clarinet, trumpet, tenor sax) offset +2   (...as D, 2 sharps)
#     Eb (alto sax, Eb clarinet)        offset +3   (...as A, 3 sharps)
#     A  (clarinet in A)                offset -3   (...as Eb, 3 flats)
#
# So for ANY concert key K the internally-consistent written key signatures are
# the SET {K-3, K, K+1, K+2, K+3} — for concert C that is {3b, 0, 1#, 2#, 3#},
# i.e. only ~5 distinct signatures, all mutually consistent. This check asks:
# does a SINGLE concert key K explain every staff's key signature via one of
# those offsets? If yes the system is consistent (even when the raw signatures
# differ — e.g. a clarinet at 2# beside a flute at 0). A staff that fits no such
# key alongside the strict majority is the outlier — a likely mis-detected key.
#
# Two deliberate conservatism choices (this is a precision-first check):
#  * A staff with NO key signature (0 accidentals) is a WILDCARD — it never
#    flags and never constrains K. Parts are routinely written with no key
#    signature and all-inline accidentals (horns, trumpets, timpani, and whole
#    modern scores), so 0 must not be treated as "must be concert C".
#  * An outlier only one fifth outside the consistent set (circle_distance == 1)
#    is capped below "high": it may be a rarer transposition not in the common
#    set (e.g. a D instrument at offset -2) rather than an error.

_TRANSPOSITION_FIFTHS_OFFSETS = (-3, 0, 1, 2, 3)   # A, C, F, Bb, Eb (see table above)
_FIFTHS_TO_MAJOR = {
    0: "C", 1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "F#", 7: "C#",
    -1: "F", -2: "Bb", -3: "Eb", -4: "Ab", -5: "Db", -6: "Gb", -7: "Cb",
}


def _staff_key_fifths(staff: dict[str, Any]) -> int:
    """A staff's key signature as a signed circle-of-fifths position: +N for N
    sharps, -N for N flats, 0 for none (a standard key sig has only one kind)."""
    ks = staff.get("key_signature") or {}
    return (ks.get("sharps") or 0) - (ks.get("flats") or 0)


def _fifths_key_name(c: int) -> str:
    return f"{_FIFTHS_TO_MAJOR.get(c, '?')} major"


def _fifths_accidentals(c: int) -> str:
    if c > 0:
        return f"{c} sharp{'s' if c != 1 else ''}"
    if c < 0:
        return f"{-c} flat{'s' if c != -1 else ''}"
    return "no accidentals"


def _flag_key_signature_inconsistency(system: dict[str, Any]) -> None:
    """Flag staves whose key signature can't be reconciled — via any standard
    instrument transposition — with the concert key that explains the strict
    majority of the system's staves. Mutates each outlier staff dict in place
    with a ``key_signature_warning``. See the module comment above.

    Pure additive post-pass: a system whose signatures are all consistent with
    one concert key (the common case, incl. a whole orchestra of transposing
    instruments) is left byte-identical. Abstains when fewer than two staves
    carry a key signature, or when no single concert key covers a strict
    majority (scattered / unreliable detection).
    """
    staves = system.get("staves") or []
    if len(staves) < 2:
        return

    # 0 (no key signature) is a wildcard — drop it (see module comment).
    nonzero = [(st, c) for st in staves if (c := _staff_key_fifths(st)) != 0]
    if len(nonzero) < 2:
        return  # nothing to cross-check
    values = [c for _, c in nonzero]

    # Candidate concert keys: every K that could place at least one staff on a
    # known transposition. Pick the K whose consistent set covers the most.
    candidates = sorted({c - off for c in values for off in _TRANSPOSITION_FIFTHS_OFFSETS})
    best_k, best_n = None, -1
    for k in candidates:
        n = sum(1 for c in values if (c - k) in _TRANSPOSITION_FIFTHS_OFFSETS)
        # Max coverage; ties broken toward the concert key nearest C (fewest
        # accidentals — the more likely reading, and a stable report).
        if best_k is None or n > best_n or (n == best_n and abs(k) < abs(best_k)):
            best_n, best_k = n, k

    total = len(values)
    # Strict majority must agree on one concert key, else we can't say which
    # staves are the outliers — abstain (mirrors the measure-count check).
    if best_n * 2 <= total:
        return

    consensus = best_n / total
    consistent_set = sorted(best_k + off for off in _TRANSPOSITION_FIFTHS_OFFSETS)
    for st, c in nonzero:
        if (c - best_k) in _TRANSPOSITION_FIFTHS_OFFSETS:
            continue
        distance = min(abs(c - s) for s in consistent_set)
        if consensus >= _CONSENSUS_HIGH:
            label = "high"
        elif consensus >= _CONSENSUS_MED:
            label = "medium"
        else:
            label = "low"
        # One fifth outside the set may be a rarer transposition, not an error.
        if distance == 1 and label == "high":
            label = "medium"
        st["key_signature_warning"] = {
            "staff_key": _fifths_accidentals(c),
            "staff_fifths": c,
            "concert_key": _fifths_key_name(best_k),
            "consistent_written_fifths": consistent_set,
            "agreement": f"{best_n}/{total}",
            "circle_distance": distance,
            "confidence": round(consensus, 3),
            "confidence_label": label,
        }


# ---------------------------------------------------------------------------
# Clef-from-pitch register inversion (ADVISORY only)
# ---------------------------------------------------------------------------
#
# The weakest of the internal-consistency checks, and deliberately advisory. A
# wrong clef shifts every notehead on a staff by a constant diatonic offset, so
# a single staff gives ZERO evidence: the mis-read pitches AND the (wrong) clef
# field shift together and stay internally self-consistent. The only internal
# signal is RELATIONAL — a staff resolving into the wrong register relative to
# its neighbours. Staves in a system run (roughly) high-to-low, so a LOWER staff
# whose notes sit well ABOVE the staff above it is suspicious: a possible clef
# error (the classic "a nominally-bass staff resolving above the treble above
# it"), OR a genuine voice-crossing / a high instrument (piccolo).
#
# Real limits (why this stays advisory, and why the dossier's per-instrument
# RANGE is what makes clef-from-pitch actually reliable):
#  * Adjacent instruments overlap heavily in range, and a clef shift (~an octave)
#    often does NOT push a staff cleanly outside its neighbours — so recall is
#    low by construction. Calibrated on the repo's real scores, benign adjacent
#    pairs reach a p25(lower)-vs-p75(upper) separation of +9 semitones with no
#    clef error present; a FULL octave (12) of separation is required to flag, so
#    the flag never fires on those. It catches only GROSS inversions.
#  * Voice-crossing and high solo instruments are real false positives.
# So: never more than "advisory", and it points at an inverted PAIR (at most one
# staff has a wrong clef) rather than asserting which staff or that it's an error.

_NOTE_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_CLEF_MIN_NOTEHEADS = 6      # per staff — fewer gives an unreliable register
_CLEF_INVERSION_GAP = 12     # semitones (an octave) of p25/p75 separation to flag


def _direction_text_default() -> bool:
    """Whether the direction reader runs when the caller expressed no opinion.

    On since 2026-09-02. `OMR_DIRECTION_TEXT=0` turns it off for a deployment
    that would rather not spend the OCR — the backend passes no flag, so an env
    knob is the only lever it has, which is why every other OMR default has one
    (`OMR_LEFT_EDGE_SPLIT`, `OMR_CONF_THRESHOLD`, `OMR_IMGSZ`). Same spelling of
    "off" as `system_grouping._left_edge_split_enabled`.
    """
    return os.environ.get("OMR_DIRECTION_TEXT", "1").strip().lower() not in (
        "0", "", "false", "no", "off",
    )


def _pitch_to_midi(pitch: str | None) -> int | None:
    """Convert a pitch string ('F#3', 'Bb5', 'C4') to a MIDI number (C4 = 60),
    or None if unparseable. Thin alias — the implementation lives in
    pitch_resolver so the clef-correction pass shares exactly this parse."""
    return pitch_to_midi(pitch)


def _staff_notehead_midis(staff: dict[str, Any]) -> list[int]:
    """MIDI numbers of every resolved notehead pitch on a staff (register
    evidence). Skips unresolved / non-notehead detections."""
    out: list[int] = []
    for md in staff.get("measures", []):
        for det in md.get("detections", []):
            if det.get("category") == "notehead":
                m = _pitch_to_midi(det.get("pitch"))
                if m is not None:
                    out.append(m)
    return out


def _percentile(sorted_vals: list[int], q: float) -> int:
    """Value at quantile q of a pre-sorted, non-empty list (nearest-rank)."""
    return sorted_vals[min(len(sorted_vals) - 1, int(q * len(sorted_vals)))]


def _flag_clef_register_inversion(system: dict[str, Any]) -> None:
    """Advisory flag on a lower staff whose register sits an octave+ above the
    staff directly above it — a possible clef error (or voice-crossing / a high
    instrument). Mutates the lower staff dict with a ``clef_register_warning``.
    See the module comment above; this is advisory-only by design.

    Pure additive post-pass: writes nothing unless a gross inversion exists, so
    a normally-ordered system is byte-identical. Only staves with enough
    resolved noteheads for a reliable register estimate participate.
    """
    staves = system.get("staves") or []
    if len(staves) < 2:
        return
    midis = [_staff_notehead_midis(st) for st in staves]
    for i in range(len(staves) - 1):
        upper_m, lower_m = midis[i], midis[i + 1]
        if len(upper_m) < _CLEF_MIN_NOTEHEADS or len(lower_m) < _CLEF_MIN_NOTEHEADS:
            continue
        upper_sorted, lower_sorted = sorted(upper_m), sorted(lower_m)
        # Robust separation: the lower staff's near-bottom (p25) above the upper
        # staff's near-top (p75). Percentiles absorb a stray crossing note.
        gap = _percentile(lower_sorted, 0.25) - _percentile(upper_sorted, 0.75)
        if gap < _CLEF_INVERSION_GAP:
            continue
        upper, lower = staves[i], staves[i + 1]
        lower["clef_register_warning"] = {
            "lower_staff_index": lower.get("staff_index"),
            "upper_staff_index": upper.get("staff_index"),
            "lower_staff_median_midi": _percentile(lower_sorted, 0.5),
            "upper_staff_median_midi": _percentile(upper_sorted, 0.5),
            "register_gap_semitones": gap,
            "lower_staff_clef": lower.get("clef"),
            "upper_staff_clef": upper.get("clef"),
            "confidence_label": "advisory",
        }


# ---------------------------------------------------------------------------
# Cross-staff time-signature agreement (check e)
# ---------------------------------------------------------------------------
#
# (A cross-system clef-continuity flag was prototyped here and dropped: a
# post-pass that majority-votes each role's FINAL clef across same-sized systems
# is unreliable — on reduction/condensed scores same-sized systems aren't the
# same instruments, so it false-fires, and majority-clef != correct-clef so it
# can even flag the RIGHT staff. The sound signal ("a DETECTED clef overrode the
# inherited one") is only visible inside _ClefContinuity during transcription,
# or from the dossier's expected per-role clef — deferred to there.)


def _flag_time_signature_disagreement(system: dict[str, Any]) -> None:
    """Flag staves whose genuinely-DETECTED time signature disagrees with the
    rest of the system. Every staff of a system shares one meter, so a
    disagreement among *detected* meters is a hard mis-read (unlike a
    measure-count deviation, at most one detected meter can be right).

    Only genuinely-detected (source-less) staff meters participate — a meter
    tagged with a `source` was back-filled / propagated by inference, not read,
    so it is not evidence. Additive: writes nothing when the detected meters
    agree (or fewer than two staves detected one).
    """
    staves = system.get("staves") or []
    if len(staves) < 2:
        return
    detected: list[tuple[dict[str, Any], tuple[int, int]]] = []
    for st in staves:
        ts = st.get("time_signature")
        if ts and not ts.get("source"):
            num, den = ts.get("numerator"), ts.get("denominator")
            if num and den:
                detected.append((st, (num, den)))
    if len(detected) < 2:
        return
    meters = [m for _, m in detected]
    mode_meter, mode_k = Counter(meters).most_common(1)[0]
    total = len(meters)
    if mode_k == total:
        return  # all detected meters agree

    consensus = mode_k / total
    strict = mode_k * 2 > total
    distinct = sorted(f"{a}/{b}" for a, b in set(meters))
    for st, m in detected:
        if strict and m == mode_meter:
            continue  # the majority-detected meter — not the outlier
        if strict and consensus >= _CONSENSUS_HIGH:
            label = "high"
        elif strict and consensus >= _CONSENSUS_MED:
            label = "medium"
        else:
            label = "low"   # near-even split: can't say which meter is right
        st["time_signature_disagreement"] = {
            "staff_time_signature": f"{m[0]}/{m[1]}",
            "system_detected_meters": distinct,
            "majority_meter": f"{mode_meter[0]}/{mode_meter[1]}" if strict else None,
            "agreement": f"{mode_k}/{total}",
            "confidence": round(consensus, 3),
            "confidence_label": label,
        }


def _resolve_clef_weights(clef_weights: str | None) -> str | None:
    """`clef_weights` if given, else the `OMR_CLEF_WEIGHTS` environment
    variable, else None.

    `main()` already does this same resolution for the CLI (so `--clef-weights`
    wins over the env var, and it can print what was picked up before the run
    starts). This is what makes it work for a caller that invokes `transcribe()`
    directly instead — `backend/modules/local_omr.py` never passes
    `clef_weights` at all, the same way it never passes most of the other
    OMR_* knobs it resolves from the environment itself; this closes that one
    remaining gap by having `transcribe()` resolve it, matching what
    CLAUDE.md's env-var table already documents as a backend knob.
    """
    if clef_weights is not None:
        return clef_weights
    return os.environ.get("OMR_CLEF_WEIGHTS") or None


def _repo_root() -> Path:
    """The repo root, derived from this file's own location — so weight
    routing resolves the same files no matter the caller's working directory
    (the relative `DEFAULT_WEIGHTS` string only ever resolved from the root)."""
    return Path(__file__).resolve().parents[2]


def _weight_routing_enabled() -> bool:
    """`OMR_WEIGHT_ROUTING` env, default ON; '0'/'false'/'no'/'off' disable."""
    raw = os.environ.get("OMR_WEIGHT_ROUTING", "").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _route_weights(
    pdf_path: Path,
    pages: list[int],
    *,
    classify: Any = None,
) -> tuple[str, dict[str, Any]]:
    """Pick the weights by input domain, for a caller that didn't pin them.

    The two domains measured different best weights on the day the hollow
    fine-tune shipped (SHIP_RESULTS.md §4b/§4c): scans want `DEFAULT_WEIGHTS`
    (half-notes 8 -> 27 on beet5-p1), digitally engraved PDFs want
    `ENGRAVED_WEIGHTS` (11-work OMR-NED 0.1399 vs 0.1421). The verdict comes
    from `input_domain.classify_pdf_domain` — where the ink comes from, raster
    image vs vector drawings — over the pages this run will transcribe.

    Every non-engraved outcome lands on `DEFAULT_WEIGHTS`, and the asymmetry
    is the design: routing an engraved input to the scan weights costs the
    measured +0.0022 pooled; routing a scan to the engraved weights forfeits
    the half-note gains. So `unknown` abstains to the default, and an
    `engraved` verdict whose weights file is missing falls back to the
    default with one stderr line rather than failing the run.

    Returns `(weights_path, provenance)`; the provenance dict is recorded in
    the result as `weight_routing` so the JSON says why this model ran.
    `classify` is injectable for tests (same reason `_resolve_clef_weights`
    is a seam); default is the real classifier.
    """
    default = str(_repo_root() / DEFAULT_WEIGHTS)
    if not _weight_routing_enabled():
        return default, {
            "mode": "disabled",
            "weights": default,
            "reason": "OMR_WEIGHT_ROUTING is off -> default weights",
        }

    from .input_domain import DEFAULT_CLASSIFY_PAGES, ENGRAVED, SCANNED
    if classify is None:
        from .input_domain import classify_pdf_domain as classify

    # Any-scan-wins saturates quickly, so the sample is capped the same way
    # classify_pdf_domain caps its own default page walk.
    sample = list(pages)[:DEFAULT_CLASSIFY_PAGES]
    classification = classify(pdf_path, page_indices=sample)
    prov: dict[str, Any] = {
        "mode": "routed",
        "verdict": classification.verdict,
        "classification": classification.to_dict(),
    }

    if classification.verdict == ENGRAVED:
        candidate = (os.environ.get("OMR_ENGRAVED_WEIGHTS", "").strip()
                     or str(_repo_root() / ENGRAVED_WEIGHTS))
        if Path(candidate).is_file():
            prov["weights"] = candidate
            prov["reason"] = "engraved input -> engraved weights"
            return candidate, prov
        prov["weights"] = default
        prov["reason"] = (f"engraved input, but engraved weights missing at "
                          f"{candidate} -> default weights")
        print(f"transcribe: weight routing: engraved weights not found at "
              f"{candidate}; falling back to default weights",
              file=sys.stderr, flush=True)
        return default, prov

    prov["weights"] = default
    prov["reason"] = ("scanned input -> default (scan-tuned) weights"
                      if classification.verdict == SCANNED
                      else "input domain unknown -> default weights")
    return default, prov


def _optional_pass_failure(
    name: str, exc: BaseException, *, progress: bool,
) -> dict[str, Any]:
    """The record an optional enrichment leaves behind when it could not run.

    A transcription that succeeded must not be lost because an optional
    enrichment failed, so nothing here re-raises. But NOT RAISING IS NOT THE
    SAME AS NOT TELLING ANYONE, and that distinction is the whole reason this
    function exists.

    The contextual pass went dark behind exactly this `except`. The callee
    renamed a parameter, the caller kept the old name, and the resulting
    TypeError was filed as `reason` and returned as an ordinary "unavailable" —
    indistinguishable, to every reader and every benchmark, from the honest
    abstentions this pass makes all the time (no text layer, no five-line
    geometry, no Surya venv). The suite stayed green, the OMR-NED number did not
    move, and the only surviving trace was one line of stderr that
    `orchestral_eval` — which runs `progress=False` — never printed.

    It was live on main for HOURS, not weeks: it arrived with an integration
    merge and was fixed the same day. That is not reassurance. In those hours it
    passed a five-branch merge queue and a full benchmark run untouched, and
    nothing about the mechanism limited it to hours — it was found because
    somebody happened to read stderr from a different benchmark.

    So a failure is classified. An ABSTENTION is the pass saying it had nothing
    to work with; a BUG is the code being wrong, and a bug is announced on
    stderr whether or not the caller asked for progress, because a caller who
    silenced progress asked not to be told about NOTES, not about defects.
    `error_class` is recorded either way so a benchmark can assert on it.
    """
    # A missing optional dependency is an environment fact, not a defect: the
    # Surya and musicdiff venvs are meant to be absent on a fresh clone.
    bug = isinstance(exc, (TypeError, AttributeError, NameError,
                           KeyError, IndexError, ValueError))
    record = {
        "available": False,
        "reason": f"{type(exc).__name__}: {exc}",
        "error_class": type(exc).__name__,
        "looks_like_a_bug": bug,
    }
    if bug:
        print(f"  {name} FAILED WITH WHAT LOOKS LIKE A BUG, not an abstention: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    elif progress:
        print(f"  {name} unavailable: {type(exc).__name__}: {exc}", flush=True)
    return record


def _contextual_call_kwargs(
    *,
    pdf_path: Path,
    dpi: int,
    dossier: dict[str, Any] | None,
    vision_fallback: bool,
) -> dict[str, Any]:
    """The keyword arguments `transcribe` hands to `apply_contextual_analysis`.

    A separate function so a test can BIND them against the real signature.
    This seam broke silently once: `apply_contextual_analysis` replaced its
    `vision_fallback` flag with the `Assist` object and the call here kept the
    old name — a TypeError the try/except around the call dutifully filed into
    `contextual.reason`, turning the documented on-by-default pass into a no-op
    on every transcription until someone read the JSON. The flag maps onto the
    two assist modes that spend no attention: vision when the caller opted into
    paying for it, none otherwise — free tiers only, abstain where they fall
    short, which is exactly what `vision_fallback=False` always meant.
    """
    from .assist import Assist

    return {
        "pdf_path": pdf_path,
        "dpi": dpi,
        "dossier": dossier,
        "assist": Assist("vision" if vision_fallback else "none"),
        # OMR_INSTRUMENT_CLEF_DEFAULT (default OFF): let a READ margin label's
        # instrument correct the two verified clef failure shapes on scans —
        # a detected-treble header on a Viola/Bassoon/Timpani staff, and an
        # implausible mid-staff clef change (violin→bass, viola→bass). See
        # clef_correction.py and benchmarks/omr-clef-string-staves-2026-09.
        "instrument_clef_default": os.environ.get(
            "OMR_INSTRUMENT_CLEF_DEFAULT", "0").strip().lower()
        not in ("0", "", "false", "no", "off"),
    }


def transcribe(
    *,
    pdf_path: Path,
    pages: list[int],
    weights: str | None = None,
    conf_threshold: float = 0.25,
    imgsz: int | None = None,
    iou_threshold: float = 0.5,
    agnostic_nms: bool = True,
    dpi: int = 600,
    clef_weights: str | None = None,
    clef_reader_conf: float = 0.30,
    clef_reader_imgsz: int = 640,
    clef_reader_header_frac: float = 0.42,
    locate_c_clefs: bool = True,
    read_headers: bool = True,
    dossier: dict[str, Any] | None = None,
    dossier_seeding: bool = True,
    contextual: bool = True,
    contextual_vision_fallback: bool = False,
    read_direction_text: bool | None = None,
    overlays_dir: Path | None = None,
    progress: bool = True,
) -> dict[str, Any]:
    """Run the full transcribe pipeline. Returns the structured dict.

    The defaults match what the Phase 3.3 evaluation used (conf=0.25,
    agnostic_nms=True). Lower conf_threshold (e.g. 0.10) for higher recall
    at the cost of more false positives.

    `imgsz=None` (the default) lets the detector pick an inference size per
    cell, so the model is shown a staff space near the one it recognises
    noteheads at. A fixed value is the wrong knob for cell-based inference:
    the cells have already been rescaled to a canonical staff span, so one
    `imgsz` means a different staff space in every cell. See
    `yolo_detector.imgsz_for_cell`.

    Everything needed to read a staff's header — its clef and key signature —
    is on by default and needs no extra files: `read_headers` measures each
    staff's header window and reads the key signature from it with classical CV,
    and `locate_c_clefs` does the same for C clefs. `clef_weights` is an
    OPTIONAL second detector that reads clefs better on some material; the
    pipeline is complete without it, and passing a path that isn't a
    clef-trained checkpoint makes clefs worse, not better.

    `clef_weights=None` (the default) falls back to the `OMR_CLEF_WEIGHTS`
    environment variable, same as the CLI — this is what lets a caller that
    invokes `transcribe()` directly (`backend/modules/local_omr.py`, which
    never passes `clef_weights`) still pick it up, matching how every other
    OMR_* knob in that module already works. Pass `clef_weights` explicitly to
    override the environment either way (including `clef_weights=""` to force
    it off regardless of what's set).

    `weights=None` (the default) ROUTES by input domain: scanned PDFs get
    `DEFAULT_WEIGHTS` (the hollow fine-tune, which wins on scans), digitally
    engraved PDFs get `ENGRAVED_WEIGHTS` (the prior production checkpoint,
    which wins on engraved input) — see `_route_weights` for the measured
    rationale. An explicit `weights` path pins the model and skips
    classification entirely; `OMR_WEIGHT_ROUTING=0` pins everything to
    `DEFAULT_WEIGHTS`. Either way the result records what ran (`weights`)
    and, when routing ran, why (`weight_routing`).
    """
    # Lazy-import the YOLO wrapper so this module imports cheaply when the
    # caller doesn't actually need OMR (e.g. when listing pages).
    from .yolo_detector import YoloDetector

    clef_weights = _resolve_clef_weights(clef_weights)

    weight_routing: dict[str, Any] | None = None
    if weights is None:
        weights, weight_routing = _route_weights(pdf_path, pages)
        if progress:
            print(f"  weights routed: {weight_routing.get('verdict', '?')} "
                  f"-> {Path(weights).name}", flush=True)

    detector = YoloDetector(weights, device="auto")
    # Optional decoupled clef specialist (see _detections_for_cell). Loaded
    # once and reused; None ⇒ clef comes from the production detector alone.
    clef_reader = YoloDetector(clef_weights, device="auto") if clef_weights else None

    out: dict[str, Any] = {
        "source_pdf": str(pdf_path),
        "weights": weights,
        "weight_routing": weight_routing,
        "clef_weights": clef_weights,
        "locate_c_clefs": locate_c_clefs,
        "read_headers": read_headers,
        "conf_threshold": conf_threshold,
        "iou_threshold": iou_threshold,
        "agnostic_nms": agnostic_nms,
        "imgsz": imgsz,
        "dpi": dpi,
        "n_pages_processed": 0,
        "n_systems_total": 0,
        "n_staves_total": 0,
        "n_measures_total": 0,
        "n_detections_total": 0,
        # How many notehead detections were a sliver of a neighbouring staff's
        # ink cut by the crop. Kept so a page can be audited for how much the
        # rule is doing rather than having to re-run it — see
        # `_drop_clipped_notehead_fragments`.
        "n_clipped_notehead_fragments_dropped": 0,
        "n_noteheads_total": 0,
        "n_noteheads_pitched_total": 0,
        "n_noteheads_with_duration_total": 0,
        "n_rests_total": 0,
        "n_rests_with_duration_total": 0,
        "runtime": {"phase1_s": 0.0, "yolo_s": 0.0, "total_s": 0.0},
        "pages": [],
    }

    # Active clef + key signature + time signature per (page_idx,
    # system_idx, staff_idx). Each survives across cells within a staff so
    # a clef / key sig / time sig stays in effect through a whole line
    # (until a change is detected). Key sig + time sig are NOT carried across
    # pages — the courtesy accidentals / meter at a new page re-establish
    # them; if the detector misses, defaults kick in. Clef IS carried, by
    # role, via `clef_by_role` below (clefs aren't re-printed every page, so
    # a missed continuation clef is the higher-blast-radius failure).
    active_clef_by_staff: dict[tuple[int, int, int], str | None] = {}
    active_key_sig_by_staff: dict[tuple[int, int, int], dict[str, str]] = {}
    active_time_sig_by_staff: dict[tuple[int, int, int], dict[str, Any] | None] = {}
    #: The meter in effect, carried onto pages that print none.
    carried_meter: dict[str, Any] | None = None

    # Clef CONTINUITY (Task-2 clef-stability pass). The last EFFECTIVE clef
    # seen at each staff ROLE (vertical position within its system), carried
    # across systems AND pages. When a continuation system/page doesn't
    # re-print a clef and the detector catches nothing, the staff inherits the
    # clef its role had last time instead of silently defaulting to treble
    # (or bass for staff-2-of-2) — which on a 16-staff orchestral system would
    # transpose whole instruments (violas/celli/basses). Only trusted when the
    # layout is stable (same staff count as the system it inherits from); a
    # detected clef always overrides it. For 2-staff piano the inherited clef
    # equals the position default (top treble / bottom bass), so clean piano
    # output is unaffected.
    clef_continuity = _ClefContinuity()

    t_total = time.perf_counter()
    # Kept for the contextual post-pass, which needs the SAME staves that go
    # into the result — re-detecting them there would risk attaching slot
    # indices to a different set. Bounded by OMR_MAX_PAGES (5 by default).
    staved_pages: list[Any] = []
    # Contested notehead pairs that DISTANCE alone decided, parked for the
    # roster-fed range veto that runs after the contextual pass names the
    # staves. `None` unless the flag is on, which keeps the dedupe path — and
    # its output — byte-identical by construction when it is off.
    _range_veto_mode = _roster_range_veto_mode()
    _range_veto_deferred: list[dict[str, Any]] | None = (
        [] if _range_veto_mode != "off" else None)
    for p in pages:
        t_phase1 = time.perf_counter()
        page = render_page(pdf_path, p, dpi=dpi)
        pws = detect_staves(page)
        staved_pages.append(pws)
        pws = detect_barlines(pws)
        cells = extract_measures(pws)
        # Phase 1i: locally re-split any cell that's already going to be
        # flagged as a >2x-median-width outlier below, if a genuine
        # internal barline can be found inside it. Conservative by
        # construction — see measure_extractor.resegment_fused_measures.
        # Then steer that pass with the system's OWN majority bar count. Every
        # staff in a system is printed against the same barlines, so when one
        # staff reads fewer bars than the rest, the majority is the count and
        # that staff has a fused pair. The conservative pass only splits cells
        # wide enough to be flagged outright; steering re-examines the narrower
        # ones on the short staves, still refusing to split without genuine
        # barline ink and never past the majority.
        #
        # The count comes from the page, not from a dossier. That was the other
        # option and it is the wrong one: a dossier here is generated from
        # MusicXML, whose page and system breaks describe the ENGRAVER'S
        # edition, not the scan being read — the right bar counts for the wrong
        # page. The page's own staves are the only witnesses to how THIS print
        # is barred, and they are available on every page rather than on the
        # ~97 works a dossier exists for.
        cells = resegment_fused_measures(
            pws, cells,
            expected_bars_by_system=majority_bars_by_system(cells),
        )
        remove_staff_lines(cells)

        # The staff-header pass. Header cells are cheap (one crop per staff) and
        # are what the clef readers and the key-signature locator work from.
        header_windows = header_windows_for_page(pws) if read_headers else {}
        header_cells = (
            header_cells_for_page(pws, windows=header_windows) if read_headers else {}
        )
        out["runtime"]["phase1_s"] += time.perf_counter() - t_phase1

        # Group cells by (system, staff). Keep them in measure_index order
        # within each group.
        systems: dict[int, dict[int, list[MeasureCell]]] = {}
        for c in cells:
            systems.setdefault(c.system_index, {}).setdefault(c.staff_index, []).append(c)
        for sys_idx in systems:
            for staff_idx in systems[sys_idx]:
                systems[sys_idx][staff_idx].sort(key=lambda c: c.measure_index)

        # Run YOLO on each cell + build the nested structure.
        page_dict: dict[str, Any] = {
            "page_index": p,
            "page_size_px": [page.width, page.height],
            "skew_corrected_deg": page.skew_correction_deg,
            "n_systems": len(systems),
            "systems": [],
        }

        # The clef each staff's key signature will be read against. The slot
        # table is chosen by it, so this has to be settled before the signature
        # is fitted — and it has to be a clef that was actually READ, not a
        # default.
        #
        # That gate is load-bearing. The plan had been that a wrong clef costs
        # recall rather than correctness: the slot patterns of treble, bass and
        # alto are the same shape a constant apart, so a signature fitted
        # against the wrong one should push the solved offset past tolerance and
        # be dropped. Measured end-to-end on Beethoven 5 p.2, that does not
        # hold — with every staff defaulted to treble, two bass staves carrying
        # three flats came back as TWO SHARPS, a different accidental type
        # fitting a different prefix well inside tolerance. Reading a key
        # signature against a guessed clef is guessing twice.
        #
        # So the clef is read here from the header crop: one production-detector
        # inference per staff on an image a few staff spaces wide, against the
        # hundreds the measures need. It chooses the slot table and nothing
        # else — it is not written to the output, and the measure pass below
        # still reads the clef its own way. A staff left at None had no clef
        # read at all, and `_header_key_signatures` skips it.
        #
        # Clef CONTINUITY is deliberately not consulted: the main loop has not
        # initialised its per-system state yet, so reading it here would pick up
        # the previous system's roles.
        clef_estimate: dict[int, str | None] = {}
        header_dets: dict[int, tuple[list, MeasureCell]] = {}
        if read_headers:
            for sys_idx in sorted(systems.keys()):
                staff_keys = sorted(systems[sys_idx].keys())
                for staff_idx in staff_keys:
                    estimate = active_clef_by_staff.get((p, sys_idx, staff_idx))
                    hc = header_cells.get(staff_idx)
                    # The DETECTOR reads the staff-start MEASURE cell, not the
                    # header crop, and the difference is total. Measured on WTC
                    # p.17: on the header cell the model finds ZERO
                    # key-signature markers at imgsz 640, 1280 and 2048 alike,
                    # and almost no clefs; on the measure cell it finds four or
                    # five markers and the right clef. A narrow crop is better
                    # input for classical CV, which doesn't care what scale ink
                    # arrives at, and worse for a model, which was trained on
                    # whole cells and sees a letterboxed sliver as nothing it
                    # knows. So each reader gets the picture it can read.
                    start_cells = systems[sys_idx][staff_idx]
                    if start_cells:
                        header_dets[staff_idx] = (
                            _header_detections(
                                detector, start_cells[0],
                                conf_threshold=conf_threshold,
                                imgsz=imgsz,
                                iou_threshold=iou_threshold,
                                agnostic_nms=agnostic_nms,
                            ),
                            start_cells[0],
                        )
                        detected = _clef_from_dets(header_dets[staff_idx][0])
                        if detected is not None:
                            estimate = detected
                    estimate_from_locator = False
                    if estimate is None and locate_c_clefs and hc is not None:
                        found = locate_clef(hc)
                        if found is not None:
                            estimate = found.read.name
                            estimate_from_locator = True
                    # The specialist's read of this same header crop, on the
                    # same terms as the measure-loop pass below: it can
                    # improve on the production detector's guess (or the lack
                    # of one) but not on a locator finding, which is the more
                    # specific evidence for the C clefs it recognises. Before
                    # this, the specialist's clef never reached here at all —
                    # `clef_estimate` was built from only the detector and the
                    # locator, so a staff whose key signature it would have
                    # unblocked stayed unread regardless of what the specialist
                    # found later in the measure loop. Measured with
                    # `benchmarks/omr-key-signature/eval_key_signatures.py`
                    # (OMR_CLEF_WEIGHTS=deepscoresv2-yolov8l-clef-ft-boxfix-
                    # 2026-07-13.pt): pastoral-p2 end-to-end key signatures the
                    # vote could speak for 10/20 -> 12/20 staves (2 more
                    # correct, 0 new wrong); beet5-p2 and wtc-p17 unchanged —
                    # this only ever adds a clef where the detector and locator
                    # were both silent, so it cannot make an already-read page
                    # worse.
                    if clef_reader is not None and hc is not None and not estimate_from_locator:
                        spec_clef, _ = _read_staff_header(
                            clef_reader, hc,
                            conf=clef_reader_conf,
                            imgsz=clef_reader_imgsz,
                            header_frac=clef_reader_header_frac,
                            iou_threshold=iou_threshold,
                            agnostic_nms=agnostic_nms,
                            pdf_path=pdf_path,
                            page_dpi=dpi,
                        )
                        if spec_clef is not None:
                            estimate = spec_clef
                    clef_estimate[staff_idx] = estimate
            voted_fifths, voted_reasons, key_sig_unread_reasons = (
                _header_key_signatures(
                    pws, header_cells, clef_estimate, header_dets
                )
            )
            key_sig_default_unread = "no reader spoke for this staff"
            # The meter, read from the same header crops and voted across each
            # system's staves. The detector cannot supply this on a real scan —
            # on Beethoven 5 p.1 it finds no time-signature digit in any header
            # and the five it does fire are barline fragments mid-bar, which
            # `_dominant_detected_meter` then propagates as common time over a
            # 2/4 page. See tools/omr/time_signature_locator.py.
            header_meters = read_system_time_signatures(
                header_cells,
                {sys_idx: sorted(systems[sys_idx].keys())
                 for sys_idx in sorted(systems.keys())},
            )
        else:
            voted_fifths, voted_reasons = {}, {}
            key_sig_unread_reasons = {}
            key_sig_default_unread = "header reading is off (--no-header-reading)"
            header_meters = {}

        # Dossier slot facts for the whole page, used when per-system grouping
        # is too fragmented to join (which is the normal case — see
        # dossier.slot_facts_for_page). Consumed by a running top-to-bottom
        # index across systems, which is the order the staves were detected in.
        page_staff_total = sum(len(systems[k]) for k in systems)
        page_slot_facts = (
            slot_facts_for_page(page_staff_total, dossier)
            if (dossier is not None and dossier_seeding) else None
        )
        page_slot_cursor = 0

        t_yolo = time.perf_counter()
        for sys_idx in sorted(systems.keys()):
            staff_keys = sorted(systems[sys_idx].keys())
            sys_dict: dict[str, Any] = {
                "system_index": sys_idx,
                "n_staves": len(systems[sys_idx]),
                "staves": [],
            }
            # Clef continuity: this system may inherit per-role clefs from a
            # same-sized previous system, and builds its own role map as it goes.
            clef_continuity.start_system(len(staff_keys))
            # Per-staff written clef + key from the dossier, or None when there
            # is no dossier, seeding is off, or the part→staff join is unsafe.
            system_slot_facts = (
                slot_facts_for_system(len(staff_keys), dossier)
                if (dossier is not None and dossier_seeding) else None
            )
            for position_in_system, staff_idx in enumerate(staff_keys):
                staff_cells = systems[sys_idx][staff_idx]
                # Pick a starting clef for this staff. A clef detection in the
                # cells overrides it (engraved music prints one at each system
                # start); it only matters when the detector misses. Prefer the
                # clef this role carried from a stable previous system, else
                # the position-based default.
                role_default = _default_clef_for_position(
                    position_in_system, len(staff_keys)
                )
                active_clef = active_clef_by_staff.get(
                    (p, sys_idx, staff_idx),
                    clef_continuity.starting_clef(position_in_system, role_default),
                )
                # The work's own clef and key for this staff, when a dossier was
                # given and its parts join 1:1 to this system's staves. None
                # everywhere else, which leaves the readers in charge.
                if system_slot_facts is not None:
                    slot = system_slot_facts[position_in_system]
                elif page_slot_facts is not None:
                    slot = page_slot_facts[page_slot_cursor]
                else:
                    slot = None
                page_slot_cursor += 1
                forced_clef = slot["clef"] if slot else None
                forced_fifths = slot["fifths"] if slot else None
                staff_clef_overrides: list[dict[str, Any]] = []
                # Seed from the located + reconciled reading when there is one.
                # A keySharp / keyFlat the detector finds in the music replaces
                # it, so this only decides staves the detector says nothing about
                # — which, on real prints, is nearly all of them.
                seeded_fifths = voted_fifths.get(staff_idx)
                active_key_sig = active_key_sig_by_staff.get(
                    (p, sys_idx, staff_idx),
                    alterations_for_fifths(seeded_fifths or 0),
                )
                # A meter carried over from the previous system, else the one
                # the header reader voted for THIS system, else unknown. The
                # carry-over comes first because a system that prints no time
                # signature is still in the meter the last one established, and
                # the reader abstains on those systems rather than contradicting
                # it. A seed is a SEED: any meter the detector reads in the
                # music replaces it, the same rule the clef locator and the
                # key-signature vote follow.
                active_time_sig = active_time_sig_by_staff.get(
                    (p, sys_idx, staff_idx),
                    dict(header_meters[sys_idx]) if sys_idx in header_meters else None,
                )
                staff_obj = next(
                    (st for st in pws.staves if st.staff_index == staff_idx), None
                )
                staff_dict: dict[str, Any] = {
                    "staff_index": staff_idx,
                    # clef + key_signature + time_signature get filled in
                    # after the first cell is processed so they reflect the
                    # EFFECTIVE state of the staff (after any leading
                    # detections in the first measure are absorbed).
                    "clef": None,
                    "key_signature": None,
                    "time_signature": None,
                    # The lines every reading above was measured against.
                    "staff_geometry": _staff_geometry(staff_obj),
                    # The bracket block this staff sits in, as `staff_detector`
                    # grouped it — the PAGE's own statement of family grouping,
                    # and the only one that needs no lexicon and no template.
                    #
                    # It lived on the `Staff` dataclass and never reached the
                    # dict, so every consumer downstream of a transcription saw
                    # 0 of 396 staves carrying it
                    # (`benchmarks/omr-staff-identity-layer-2026-09/
                    # probe_relational_context.py`). Emitting it is additive:
                    # nothing reads it yet, and a staff whose block could not be
                    # determined serialises `None` rather than a guess.
                    #
                    # ⚠️ Measured properties a consumer must respect: bracket
                    # blocks are PRECISE and UNDER-RECALLED (22/22 precise,
                    # 22/39 recalled; family purity 0.872 within-block against
                    # 0.039 page-wide). So they may ANCHOR a family boundary
                    # where present and must ABSTAIN where absent — never
                    # assign.
                    "group_index": getattr(staff_obj, "group_index", None),
                    "n_measures": len(staff_cells),
                    "measures": [],
                }
                # Point the clef readers at the measured header only where the
                # staff-start measure cell actually misses it — see
                # `_header_cell_beats_measure_cell`.
                # The header cell is supplied on EVERY staff, because the
                # detector's gap-fill pass reads it wherever the measure cell
                # yielded no clef. The gate decides something narrower: whether
                # the locator and the specialist should look there INSTEAD of
                # the measure cell.
                header_cell_for_clef = (
                    header_cells.get(staff_idx) if read_headers else None
                )
                prefer_header_cell = bool(
                    read_headers
                    and staff_cells
                    and staff_obj is not None
                    and _header_cell_beats_measure_cell(
                        header_windows.get(staff_idx), staff_obj, staff_cells[0]
                    )
                )

                first_cell_effective_clef: str | None = None
                first_cell_clef_source: str | None = None
                first_cell_effective_key_sig: dict[str, str] | None = None
                first_cell_effective_time_sig: dict[str, Any] | None = None
                for cell_idx, cell in enumerate(staff_cells):
                    (
                        detections,
                        active_clef,
                        active_key_sig,
                        active_time_sig,
                        cell_clef_source,
                        cell_clipped_dropped,
                    ) = (
                        _detections_for_cell(
                            detector,
                            cell,
                            conf_threshold=conf_threshold,
                            imgsz=imgsz,
                            iou_threshold=iou_threshold,
                            agnostic_nms=agnostic_nms,
                            active_clef=active_clef,
                            active_key_sig=active_key_sig,
                            active_time_sig=active_time_sig,
                            clef_reader=clef_reader,
                            header_cell=header_cell_for_clef,
                            prefer_header=prefer_header_cell,
                            skip_key_sig_detection=(
                                cell_idx == 0 and staff_idx in voted_fifths
                            ),
                            read_clef=(cell_idx == 0),
                            forced_clef=forced_clef,
                            forced_fifths=forced_fifths,
                            clef_overrides=staff_clef_overrides,
                            clef_reader_conf=clef_reader_conf,
                            clef_reader_imgsz=clef_reader_imgsz,
                            clef_reader_header_frac=clef_reader_header_frac,
                            locate_c_clefs=locate_c_clefs,
                            pdf_path=pdf_path,
                            page_dpi=dpi,
                        )
                    )
                    if cell_idx == 0:
                        first_cell_effective_clef = active_clef
                        first_cell_clef_source = cell_clef_source
                        first_cell_effective_key_sig = dict(active_key_sig)
                        first_cell_effective_time_sig = (
                            dict(active_time_sig) if active_time_sig else None
                        )
                    staff_dict["measures"].append({
                        "measure_index": cell.measure_index,
                        "bbox_page_px": list(cell.bbox_page_px),
                        # The staff lines in THIS cell's canonical frame — the
                        # frame `detections[].bbox` is in. Each cell is scaled
                        # independently, so the staff-level page geometry does
                        # not describe it; without these a canonical box cannot
                        # be placed on the staff at all.
                        "staff_line_ys_canonical": [
                            int(y) for y in cell.staff_line_ys_canonical
                        ],
                        "upscale_factor": round(float(cell.upscale_factor), 6),
                        "clef": active_clef,
                        "key_signature": _key_sig_summary(active_key_sig),
                        "time_signature": dict(active_time_sig) if active_time_sig else None,
                        "n_detections": len(detections),
                        "detections": detections,
                    })
                    out["n_clipped_notehead_fragments_dropped"] += (
                        cell_clipped_dropped
                    )
                    out["n_detections_total"] += len(detections)
                    out["n_measures_total"] += 1

                # Staff-level effective state = whatever was in effect during
                # the first measure of the staff (post any leading detections).
                staff_dict["clef"] = first_cell_effective_clef
                # Say which reader supplied the clef. Absent means nothing read
                # one here and the staff is carrying an inherited clef or the
                # position default — which is the single most useful thing to
                # know when judging a page's pitches, since a defaulted clef
                # transposes every note on the staff.
                if first_cell_clef_source is not None:
                    staff_dict["clef_source"] = first_cell_clef_source
                # What the readers said where the dossier overruled them. Kept
                # so a seeded run can still be audited for detector quality —
                # seeding must not hide how well the page was actually read.
                if staff_clef_overrides:
                    staff_dict["clef_overridden_by_dossier"] = staff_clef_overrides[0]
                staff_dict["key_signature"] = _key_sig_summary(
                    first_cell_effective_key_sig or {}
                )
                # Whether that signature is a READING or a silence. Zero sharps
                # and zero flats is the correct answer for a horn part in C and
                # the only answer available for a staff nothing could read, and
                # the two were indistinguishable in this output — which is how
                # Beethoven 5 p.15, a C minor movement, came to report "0
                # sharps / 0 flats" on all of its staves as though that were a
                # finding. A staff counts as read when something produced its
                # alterations, or when the cross-page vote spoke for it (even
                # to reject a reading — that is still a judgement about this
                # staff). Otherwise it is unread, and says why.
                # A staff the vote REJECTED is not a staff that was read. The
                # vote records a rejection as fifths 0 so the measure pass does
                # not simply re-read the same thing, and that zero is a
                # judgement about a reading it did not trust — not a finding
                # that the staff carries no accidentals. Counting it as read
                # made Beethoven 5 p.15 report two staves as "0 sharps, 0
                # flats, read" on a page printing one flat and three.
                rejected = voted_reasons.get(staff_idx, "").startswith("rejected")
                if first_cell_effective_key_sig or (
                    staff_idx in voted_fifths and not rejected
                ):
                    staff_dict["key_signature_read"] = True
                else:
                    staff_dict["key_signature_read"] = False
                    staff_dict["key_signature_unread_reason"] = (
                        voted_reasons.get(staff_idx) if rejected else
                        key_sig_unread_reasons.get(
                            staff_idx, key_sig_default_unread
                        )
                    )
                # Say where a key signature came from when it wasn't the
                # detector, so a reader can tell a located-and-voted signature
                # from a detected one without re-running the pipeline. Only
                # written when the seed actually survived into the output.
                if (
                    staff_idx in voted_fifths
                    and _key_sig_fifths(first_cell_effective_key_sig or {})
                    == (seeded_fifths or 0)
                ):
                    staff_dict["key_signature_source"] = "header_vote"
                    staff_dict["key_signature_reason"] = voted_reasons.get(staff_idx, "")
                staff_dict["time_signature"] = first_cell_effective_time_sig

                # Cross-cell tie pairing — runs after every cell of this
                # staff has been processed. Catches ties whose start
                # notehead is in measure N and stop notehead in measure
                # N+1 (the canonical use across a barline). Works in
                # page-pixel coords (the only frame shared across cells).
                _pair_ties_in_staff(staff_dict)

                # Flag measures that are anomalously wide (Phase 1 likely
                # missed an internal barline so the cell contains multiple
                # actual measures fused). These cells will have inflated
                # beat counts; downstream consumers should treat them with
                # caution. Heuristic: width > 2.0 × median width of this
                # staff's measures.
                widths = [
                    md["bbox_page_px"][2] - md["bbox_page_px"][0]
                    for md in staff_dict["measures"]
                ]
                if widths:
                    sorted_w = sorted(widths)
                    median_w = sorted_w[len(sorted_w) // 2]
                    for md in staff_dict["measures"]:
                        w = md["bbox_page_px"][2] - md["bbox_page_px"][0]
                        if median_w > 0 and w > median_w * 2.0:
                            md["phase1_warning"] = (
                                "measure width is >2× the staff median — "
                                "Phase 1 likely missed a barline; this cell "
                                "may contain multiple real measures fused"
                            )

                # (The per-measure rhythm-sum check runs later, in a
                # page-level pass — AFTER time-signature inference back-fills
                # measures whose meter detection failed, so the check can
                # fire on inferred meters too. See below.)
                # If clef or key sig changed by the end of the staff, surface
                # the final state too so a clef-change / key-change is visible.
                if active_clef != first_cell_effective_clef:
                    staff_dict["clef_final"] = active_clef
                if active_key_sig != (first_cell_effective_key_sig or {}):
                    staff_dict["key_signature_final"] = _key_sig_summary(active_key_sig)
                if active_time_sig != first_cell_effective_time_sig:
                    staff_dict["time_signature_final"] = (
                        dict(active_time_sig) if active_time_sig else None
                    )
                active_clef_by_staff[(p, sys_idx, staff_idx)] = active_clef
                active_key_sig_by_staff[(p, sys_idx, staff_idx)] = active_key_sig
                active_time_sig_by_staff[(p, sys_idx, staff_idx)] = active_time_sig
                # Record this role's effective clef for the next system/page.
                clef_continuity.record(position_in_system, active_clef)
                sys_dict["staves"].append(staff_dict)
                out["n_staves_total"] += 1
            clef_continuity.end_system()
            page_dict["systems"].append(sys_dict)
            out["n_systems_total"] += 1
        out["runtime"]["yolo_s"] += time.perf_counter() - t_yolo

        # ── Time-signature inference + back-fill (audit lever, 2026-07) ──
        # Detection of time-sig digits is unreliable (DSv2 misclassifies
        # them), so most measures carry time_signature=None. Infer the page
        # meter by majority-voting the per-measure resolved lengths, then
        # back-fill it onto the null measures/staves. Conservative: a no-op
        # unless one length wins a strong plurality (see
        # rhythm.backfill_page_time_signatures), so a clean page whose meter
        # WAS detected — or a noisy page with no clear mode — is untouched.
        # ── One glyph, one staff ──
        # Runs before anything counts, sums or infers from the detections, so
        # every downstream number sees each glyph once. Cells overlap by design
        # (4 staff-spaces of padding each way) and on a conductor's score those
        # bands meet. See _dedupe_cross_staff_detections.
        _bands = {
            st.staff_index: (st.top_y, st.bottom_y, st.line_spacing_px)
            for st in pws.staves
        }
        n_unladdered = _drop_unladdered_noteheads(page_dict, _bands)
        if n_unladdered:
            page_dict["n_unladdered_noteheads_dropped"] = n_unladdered
            out["n_unladdered_noteheads_dropped"] = (
                out.get("n_unladdered_noteheads_dropped", 0) + n_unladdered
            )
            out["n_detections_total"] -= n_unladdered
        n_deduped = _dedupe_cross_staff_detections(
            page_dict, _bands, dossier=dossier,
            deferred=_range_veto_deferred)
        if n_deduped:
            page_dict["n_cross_staff_duplicates_removed"] = n_deduped
            out["n_cross_staff_duplicates_removed"] = (
                out.get("n_cross_staff_duplicates_removed", 0) + n_deduped
            )
            out["n_detections_total"] -= n_deduped

        # ── System furniture read as a measure ──
        # After the two dedupers, so the content test sees the detections
        # everything downstream will see; before the meter passes, so a
        # courtesy meter or a system rule caught as a bar cannot vote on the
        # page's time signature or be counted as one of its measures.
        n_furniture, n_furniture_dets = _drop_furniture_measures(page_dict)
        if n_furniture:
            page_dict["n_furniture_measure_cells_dropped"] = n_furniture
            out["n_furniture_measure_cells_dropped"] = (
                out.get("n_furniture_measure_cells_dropped", 0) + n_furniture
            )
            out["n_measures_total"] -= n_furniture
            out["n_detections_total"] -= n_furniture_dets

        # A dossier meter is KNOWN, so it is applied before inference runs and
        # inference is left with nothing to guess at. It also overrules a
        # DETECTED meter that disagrees — on a constant-meter work a detected
        # 7/24 is not a competing opinion, it is a misread digit — and reports
        # every override it made. See dossier.apply_meter.
        if dossier is not None:
            meter_warnings = apply_meter(page_dict, dossier)
            if meter_warnings:
                out.setdefault("dossier_warnings", []).extend(meter_warnings)
                page_dict.setdefault("dossier_warnings", []).extend(meter_warnings)

        page_meter = backfill_page_time_signatures(page_dict)
        # A meter, once printed, is in effect until it changes — that is what a
        # time signature MEANS, and it is printed at the start of a movement and
        # nowhere else. Everything above works a page at a time, so page 2 of a
        # 2/4 movement had no meter at all and the exporter fell back to 4/4 on
        # it. Carry the last page's meter onto a page that read none, tagged so
        # it is never mistaken for something this page said.
        if page_meter is None and carried_meter is not None:
            for system in page_dict.get("systems", []):
                for staff in system.get("staves", []):
                    if not staff.get("time_signature"):
                        staff["time_signature"] = dict(carried_meter)
                    for measure in staff.get("measures", []):
                        if not measure.get("time_signature"):
                            measure["time_signature"] = dict(carried_meter)
            page_dict["inferred_time_signature"] = dict(carried_meter)
        elif page_meter is not None:
            carried_meter = {
                **{k: v for k, v in page_meter.items()
                   if k in ("numerator", "denominator", "raw")},
                "source": "carried_from_previous_page",
            }

        # ── Meter → rhythm feedback ──
        # Runs after the meter is settled (dossier, detected or inferred) and
        # BEFORE the warning below, so a measure the meter can actually repair
        # is repaired rather than merely flagged. Narrow and unique-answer-only
        # by construction — see _reconcile_measure_to_meter.
        n_reconciled = _reconcile_page_to_meter(page_dict)
        if n_reconciled:
            page_dict["n_rhythm_reconciliations"] = n_reconciled
            out["n_rhythm_reconciliations"] = (
                out.get("n_rhythm_reconciliations", 0) + n_reconciled
            )

        # ── Rhythm-sum notation-math check (column-aggregated) ──
        # Runs here (not in the staff loop) so it sees the meters
        # backfill_page_time_signatures just inferred, and can fire on those
        # back-filled measures too. Aggregated to the measure COLUMN so a
        # resting/sparse staff never false-flags against a meter force-filled
        # onto it — only a column whose FULLEST voice mis-sums flags (over-sum
        # high = extra beats / fused barline; under-sum low). This supersedes
        # the naive per-staff _measure_rhythm_sum_warning (retained for its
        # unit tests + the dossier track). Measures still lacking a time
        # signature don't participate. See _annotate_column_rhythm_warnings.
        _annotate_column_rhythm_warnings(page_dict)

        # ── Cross-staff consistency checks (additive, zero external input) ──
        # Both write a warning key only on a genuine disagreement, so a clean
        # page is byte-identical.
        #  - measure count: barlines run through the whole system, so every
        #    staff must share the same count; a deviating staff localizes a
        #    missed/spurious barline. See _flag_measure_count_inconsistency.
        #  - key signature: transposing instruments legitimately differ, so a
        #    staff is flagged only when no single concert key reconciles it with
        #    the majority via a standard transposition. See
        #    _flag_key_signature_inconsistency.
        #  - clef/register (ADVISORY): a lower staff resolving an octave+ above
        #    the staff above it — a possible clef error, voice-crossing, or high
        #    instrument. See _flag_clef_register_inversion.
        #  - time-signature: staves of a system share one meter, so genuinely
        #    DETECTED meters that disagree are a mis-read. See
        #    _flag_time_signature_disagreement.
        for sys_d in page_dict["systems"]:
            _flag_measure_count_inconsistency(sys_d)
            _flag_key_signature_inconsistency(sys_d)
            _flag_clef_register_inversion(sys_d)
            _flag_time_signature_disagreement(sys_d)

        # ── Dossier checks (external truth, when a dossier was supplied) ──
        # The four checks above can only ask whether the page agrees with
        # itself, which is why a page where every staff reads treble passes
        # them. These compare it against what the work actually contains.
        # See tools/omr/dossier.py for why most of them avoid a part→staff
        # join rather than attempting one.
        if dossier is not None:
            dossier_warnings = verify_page(page_dict, dossier)
            if dossier_warnings:
                page_dict["dossier_warnings"] = dossier_warnings
                out.setdefault("dossier_warnings", []).extend(dossier_warnings)

        out["pages"].append(page_dict)
        out["n_pages_processed"] += 1

        if progress:
            n_dets = sum(
                m["n_detections"]
                for s in page_dict["systems"]
                for st in s["staves"]
                for m in st["measures"]
            )
            page_noteheads = sum(
                1
                for s in page_dict["systems"]
                for st in s["staves"]
                for m in st["measures"]
                for d in m["detections"]
                if d["category"] == "notehead"
            )
            page_pitched = sum(
                1
                for s in page_dict["systems"]
                for st in s["staves"]
                for m in st["measures"]
                for d in m["detections"]
                if d["category"] == "notehead" and d["pitch"] is not None
            )
            page_durations = sum(
                1
                for s in page_dict["systems"]
                for st in s["staves"]
                for m in st["measures"]
                for d in m["detections"]
                if d["category"] == "notehead" and d.get("duration_beats") is not None
            )
            print(
                f"  page {p}: {len(systems)} systems, "
                f"{sum(len(staves) for staves in systems.values())} staves, "
                f"{sum(len(c) for staves in systems.values() for c in staves.values())} measures, "
                f"{n_dets} detections "
                f"({page_pitched}/{page_noteheads} pitched, "
                f"{page_durations}/{page_noteheads} durations)",
                flush=True,
            )

        # Overlay rendering (optional)
        if overlays_dir is not None:
            from .visualize import write_overlay
            overlays_dir.mkdir(parents=True, exist_ok=True)
            write_overlay(pws, overlays_dir / f"page{p:03d}-overlay.png", cells=cells)

    # Final pass: count noteheads + pitch-resolved + rhythm-resolved. Cheap
    # (linear over the already-built output) and saves consumers from doing it.
    n_noteheads = 0
    n_pitched = 0
    n_with_duration = 0
    n_rests = 0
    n_rests_with_duration = 0
    for page_d in out["pages"]:
        for sys_d in page_d["systems"]:
            for st_d in sys_d["staves"]:
                for m_d in st_d["measures"]:
                    for det in m_d["detections"]:
                        if det["category"] == "notehead":
                            n_noteheads += 1
                            if det.get("pitch") is not None:
                                n_pitched += 1
                            if det.get("duration_beats") is not None:
                                n_with_duration += 1
                        elif det["category"] == "rest":
                            n_rests += 1
                            if det.get("duration_beats") is not None:
                                n_rests_with_duration += 1
    out["n_noteheads_total"] = n_noteheads
    out["n_noteheads_pitched_total"] = n_pitched
    out["n_noteheads_with_duration_total"] = n_with_duration
    out["n_rests_total"] = n_rests
    out["n_rests_with_duration_total"] = n_rests_with_duration

    # Whole-run dossier check. Kept out of the per-page loop because it is the
    # only check that needs every page: a partial run legitimately reads fewer
    # measures than the work has, so only an OVER-count means anything.
    if dossier is not None:
        out["dossier"] = {
            "work_id": dossier.get("work_id"),
            "total_measures": dossier.get("total_measures"),
            "n_parts": dossier.get("n_parts"),
        }
        run_warnings = check_total_measures(out, dossier)
        if run_warnings:
            out.setdefault("dossier_warnings", []).extend(run_warnings)
        out["dossier_warning_summary"] = summarize_dossier_warnings(
            out.get("dossier_warnings", [])
        )

    # ── Direction text ──────────────────────────────────────────────────────
    #
    # The words printed inside a system — `legato`, `Allegro con brio`. A
    # post-pass for the same reason `contextual` is one: it works by
    # SUBTRACTING every detection from the page's ink, so it needs the finished
    # detections, and it adds a key to measures that already exist rather than
    # changing any of them. A result read without it serialises identically.
    #
    # ON by default since 2026-09-02. It was off, on the grounds that OCR is a
    # cost a caller should ask for, and the measurement that settled the
    # question took most of that cost away (`DEFAULT_2026-09-02.md`):
    #
    #   * THE MODEL IS USUALLY ALREADY LOADED. The ~70 s to spawn llama.cpp was
    #     the real objection, and it belongs to whoever loads Surya first — which
    #     on any page WITHOUT a PDF text layer is the margin-label reader, on by
    #     default since it shipped. Measured with this reader off, a scan page
    #     reports `label_tiers = {'text_layer': 0, 'surya': 12}`.
    #   * WHAT IS LEFT IS BOUNDED AND SMALL: 0.5-0.8 s per candidate crop across
    #     both OCR rungs, so 0.25-11.7 s per engraved work and 15.6-21.5 s on a
    #     dense scan page, measured twice each in isolation.
    #   * IT IS WORTH 144 EDITS on the engraved orchestral benchmark, 18.8% of
    #     the pooled figure, and `wrong direction` is the third-largest bucket.
    #   * IT IS ADDITIVE. Every word placed reaches the file and the export is
    #     identical outside its `<direction>` blocks — checked per page, on
    #     engravings and on a scan.
    #
    # A machine with neither `.venv-surya` nor Tesseract still gets nothing:
    # `read_directions` returns `[]` with `reason="no OCR rung available"`, the
    # same degradation `staff_labels_surya` has always had. Its twin reader has
    # the identical dependency and has been on by default all along; this was
    # the odd one out.
    if (_direction_text_default() if read_direction_text is None
            else read_direction_text):
        t_dir = time.perf_counter()
        try:
            from .direction_text import attach_to_page, read_directions

            n_placed = 0
            report: list[dict[str, Any]] = []
            for page_dict, pws_page in zip(out["pages"], staved_pages):
                directions, info = read_directions(pws_page, page_dict)
                n_placed += attach_to_page(page_dict, directions)
                report.append(info)
            out["direction_text"] = {
                "available": True,
                "n_placed": n_placed,
                "pages": report,
            }
        except Exception as exc:                              # noqa: BLE001
            out["direction_text"] = _optional_pass_failure(
                "direction text", exc, progress=progress)
        out["runtime"]["direction_text_s"] = round(time.perf_counter() - t_dir, 2)

    # ── Contextual post-pass ────────────────────────────────────────────────
    #
    # Part identity, and the clefs that follow from it. This lived outside the
    # pipeline until 2026-08-31 — `apply_contextual_analysis` was reachable only
    # from benchmarks, so the clef numbers this repo quotes (48/52 -> 49/52 with
    # continuity, 50/52 with a dossier) described a path no transcription ever
    # took. Wiring it in is what makes those numbers true of the output.
    #
    # It is a POST-PASS over the built page dicts: a clef hypothesis is
    # arithmetic on already-resolved pitches, so nothing about detection, rhythm
    # or segmentation changes, and a score where it finds nothing serialises
    # unchanged. It runs last for that reason, and its failure is recorded
    # rather than raised — a transcription that succeeded must not be lost
    # because an optional enrichment could not run.
    if contextual:
        t_ctx = time.perf_counter()
        try:
            from .contextual import apply_contextual_analysis
            out["contextual"] = apply_contextual_analysis(
                out,
                staved=staved_pages,
                **_contextual_call_kwargs(
                    pdf_path=pdf_path,
                    dpi=dpi,
                    dossier=dossier,
                    vision_fallback=contextual_vision_fallback,
                ),
            )
        except Exception as exc:                              # noqa: BLE001
            out["contextual"] = _optional_pass_failure(
                "contextual analysis", exc, progress=progress)
        out["runtime"]["contextual_s"] = round(time.perf_counter() - t_ctx, 2)

    # ── Range veto, fed from roster identity (OMR_ROSTER_RANGE_VETO) ────────
    #
    # Strictly after the contextual pass, because that is what names the
    # staves — and named staves are the whole input. See
    # `_apply_roster_range_veto`. Wrapped like the other optional passes: a
    # transcription that succeeded is never lost to an enrichment, and a
    # failure that looks like a DEFECT is still reported loudly by
    # `_optional_pass_failure`.
    if _range_veto_deferred is not None:
        try:
            out["roster_range_veto"] = _apply_roster_range_veto(
                out, _range_veto_deferred, mode=_range_veto_mode)
        except Exception as exc:                              # noqa: BLE001
            out["roster_range_veto"] = _optional_pass_failure(
                "roster range veto", exc, progress=progress)

    out["runtime"]["total_s"] = round(time.perf_counter() - t_total, 2)
    out["runtime"]["phase1_s"] = round(out["runtime"]["phase1_s"], 2)
    out["runtime"]["yolo_s"] = round(out["runtime"]["yolo_s"], 2)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="End-to-end OMR transcription: PDF → JSON detections.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "    python3 -m tools.omr.transcribe score.pdf --out result.json\n"
            "    python3 -m tools.omr.transcribe score.pdf --pages 0-4 \\\n"
            "        --overlays-dir overlays/ --out result.json\n"
        ),
    )
    ap.add_argument("pdf", type=Path, help="Source PDF path")
    ap.add_argument("--out", type=Path, default=None,
                    help="Output JSON file (default: stdout)")
    ap.add_argument("--pages", default="",
                    help="Pages to process: e.g. '0,4,9' or '0-4' (default: all)")
    ap.add_argument("--weights", default=None,
                    help="YOLO weights path. Default: route by input domain — "
                         "scanned PDFs get the production (scan-tuned) "
                         f"weights ({Path(DEFAULT_WEIGHTS).name}), digitally "
                         "engraved PDFs the prior production weights "
                         f"({Path(ENGRAVED_WEIGHTS).name}), which measure "
                         "better there. Passing a path pins the model and "
                         "skips routing. Env: OMR_WEIGHT_ROUTING=0 disables "
                         "routing; OMR_ENGRAVED_WEIGHTS overrides the "
                         "engraved file.")
    ap.add_argument("--clef-weights", default=None,
                    help="OPTIONAL. Path to a CLEF-SPECIALIST checkpoint — a "
                         "model fine-tuned to read clefs. You do not need it: "
                         "header reading (clef + key signature) is on by default "
                         "and needs no extra files. When set, this second "
                         "detector reads each staff's clef from its header and "
                         "overrides the main detector's, which helps on some "
                         "orchestral scans. Pointing it at ordinary detection "
                         "weights makes clefs WORSE, not better. "
                         "Env: OMR_CLEF_WEIGHTS.")
    ap.add_argument("--clef-reader-conf", type=float, default=0.30,
                    help="Min confidence for a clef-specialist detection to "
                         "override the main clef (default: 0.30)")
    ap.add_argument("--clef-reader-imgsz", type=int, default=640,
                    help="Inference imgsz for the clef/header specialist on its "
                         "crop (default: 640 — lower than main imgsz keeps the "
                         "header glyphs near training scale; see tune_header_reader.py)")
    ap.add_argument("--clef-reader-header-frac", type=float, default=0.42,
                    help="Left fraction of the staff-start cell the specialist "
                         "reads — the clef/key/time header (default: 0.42)")
    ap.add_argument("--no-header-reading", action="store_true",
                    help="Disable the staff-header pass: measuring each staff's "
                         "header window and reading its key signature from it "
                         "(tools/omr/staff_header.py, key_signature_locator.py). "
                         "On by default and needs no weights. The reading only "
                         "seeds staves where the detector finds no key-signature "
                         "accidental, so turning it off cannot fix a wrong "
                         "detected signature — it only removes the fallback.")
    ap.add_argument("--dossier", type=str, default=None,
                    help="Known facts about this work to check the reading "
                         "against — either a path to a dossier JSON or a bare "
                         "work_id resolved under data/dossiers/ (e.g. "
                         "'beethoven-sym5-mvt1'). Supplies the meter, and "
                         "flags clefs, key signatures and measure counts the "
                         "work does not contain. Build them from MusicXML with "
                         "tools.omr.training.build_dossiers. See "
                         "tools/omr/dossier.py.")
    ap.add_argument("--no-contextual", action="store_true",
                    help="Skip the contextual post-pass. By default the run "
                         "names each staff's part (text layer, then Surya "
                         "locally where .venv-surya exists), assigns stable "
                         "slots across systems, and fills in clefs the detector "
                         "never read — reported under `contextual` in the JSON. "
                         "It is a post-pass over resolved pitches: nothing "
                         "about detection, rhythm or segmentation changes.")
    ap.add_argument("--direction-text", action=argparse.BooleanOptionalAction,
                    default=True,
                    help="Read the words printed inside a system — `legato`, "
                         "`Allegro con brio` — by subtracting every detection "
                         "from the page's ink and OCRing what is left with "
                         "Surya, then gating the result on a lexicon of "
                         "musical terms. Emitted as MusicXML `<words>`. ON by "
                         "default since 2026-09-02: worth 144 edits on the "
                         "orchestral benchmark, additive, and 0.5-0.8 s per "
                         "candidate crop. Self-disables where no OCR rung "
                         "exists. `--no-direction-text` turns it off.")
    ap.add_argument("--contextual-vision", action="store_true",
                    help="Let the contextual pass fall back to reading the "
                         "margin with Claude when the text layer and Surya both "
                         "come back empty. COSTS MONEY (~$0.01 per system, "
                         "capped at 3 systems per work) and needs "
                         "ANTHROPIC_API_KEY.")
    ap.add_argument("--no-dossier-seeding", action="store_true",
                    help="With --dossier, CHECK the reading against the work "
                         "but do not seed from it. By default a dossier also "
                         "supplies each staff's written clef and key signature "
                         "— the thing clef detection is worst at — but only "
                         "where its parts join 1:1 to the system's staves. Use "
                         "this to measure what the detector reads unaided.")
    ap.add_argument("--no-clef-locator", action="store_true",
                    help="Disable the classical-CV C-clef locator. It runs only "
                         "where no model read a clef, and only recognises C "
                         "clefs, so it can add a reading but never overturn "
                         "one; turn it off to reproduce pre-locator output "
                         "exactly. See tools/omr/clef_locator.py.")
    ap.add_argument("--conf", type=float, default=0.25,
                    help="Detection confidence threshold (default: 0.25)")
    ap.add_argument("--imgsz", type=int, default=None,
                    help="YOLO inference image size. Default: chosen per cell, "
                         "so the model is shown a staff space it recognises "
                         "noteheads at. --imgsz 512 is the best fixed value "
                         "measured; --imgsz 2048 reproduces pre-2026-08-28 "
                         "output. See benchmarks/omr-detector-scale/")
    ap.add_argument("--iou", type=float, default=0.5,
                    help="NMS IoU threshold (default: 0.5)")
    ap.add_argument("--no-agnostic-nms", action="store_true",
                    help="Disable agnostic NMS (default: enabled, collapses "
                         "overlapping boxes across classes)")
    ap.add_argument("--dpi", type=int, default=600,
                    help="Source-page render DPI (default: 600). Coupled to "
                         "--imgsz, and the best pair DIFFERS BY TEXTURE: 300 "
                         "wins on sparse authored fixtures, 600 wins on dense "
                         "orchestral pages (Mahler recall 0.042 -> 0.208). The "
                         "backend runs 300 for latency, so the two entry points "
                         "genuinely differ. Do not 'unify' them without "
                         "measuring BOTH families — see "
                         "benchmarks/omr-dpi-imgsz-2026-08/RESULTS.md.")
    ap.add_argument("--overlays-dir", type=Path, default=None,
                    help="If set, write per-page overlay PNGs here")
    ap.add_argument("--quiet", action="store_true",
                    help="Suppress per-page progress logs")
    args = ap.parse_args(argv)

    if not args.pdf.exists():
        print(f"ERROR: PDF not found: {args.pdf}")
        return 2

    if args.weights is not None and not Path(args.weights).exists():
        print(f"ERROR: weights file not found: {args.weights}")
        return 2
    if args.weights is None and not (_repo_root() / DEFAULT_WEIGHTS).exists():
        # Every non-engraved routing verdict lands on this file, so a routed
        # run cannot proceed without it — same fail-fast the explicit path
        # gets. (A missing ENGRAVED_WEIGHTS is soft: the router falls back.)
        print(f"ERROR: default weights not found: {_repo_root() / DEFAULT_WEIGHTS}"
              f" (weight routing needs them; pass --weights to pin a file)")
        return 2

    # Clef specialist: CLI flag wins, else OMR_CLEF_WEIGHTS env.
    clef_weights = args.clef_weights or os.environ.get("OMR_CLEF_WEIGHTS")
    if clef_weights and not Path(clef_weights).exists():
        print(f"ERROR: clef-weights file not found: {clef_weights}")
        return 2

    # Count pages
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(args.pdf)
        n_pages = doc.page_count
        doc.close()
    except ImportError:
        from pdf2image import pdfinfo_from_path
        info = pdfinfo_from_path(str(args.pdf))
        n_pages = int(info.get("Pages", 0))

    pages = parse_pages(args.pages, n_pages)
    if not pages:
        print(f"ERROR: no valid pages selected from {args.pages!r} (doc has {n_pages})")
        return 2

    # Resolved before the run so a typo in --dossier fails immediately rather
    # than after several minutes of inference.
    dossier = resolve_dossier(args.dossier)
    if args.dossier and dossier is None:
        print(f"ERROR: no dossier found for {args.dossier!r}. Build one with "
              f"python3 -m tools.omr.training.build_dossiers --only <work_id>")
        return 2

    if not args.quiet:
        print(f"transcribe: {args.pdf.name} ({n_pages} pages, processing {len(pages)})")
        print(f"  weights:  {args.weights or 'auto (scan/engraved routing)'}")
        if dossier is not None:
            print(f"  dossier:  {dossier['work_id']} — "
                  f"{dossier['n_parts']} parts, {dossier['total_measures']} "
                  f"measures, meter {dossier['starting_meter']}, "
                  f"clefs {dossier['clefs_used']}")
        if clef_weights:
            print(f"  clef:     {clef_weights} (header specialist, conf "
                  f"{args.clef_reader_conf}, imgsz {args.clef_reader_imgsz}, "
                  f"frac {args.clef_reader_header_frac})")
        print(f"  conf:     {args.conf}, iou: {args.iou}, "
              f"agnostic_nms: {not args.no_agnostic_nms}, "
              f"imgsz: {args.imgsz if args.imgsz else 'per-cell'}")

    result = transcribe(
        pdf_path=args.pdf,
        pages=pages,
        weights=args.weights,
        conf_threshold=args.conf,
        imgsz=args.imgsz,
        iou_threshold=args.iou,
        agnostic_nms=not args.no_agnostic_nms,
        dpi=args.dpi,
        clef_weights=clef_weights,
        clef_reader_conf=args.clef_reader_conf,
        clef_reader_imgsz=args.clef_reader_imgsz,
        clef_reader_header_frac=args.clef_reader_header_frac,
        locate_c_clefs=not args.no_clef_locator,
        read_headers=not args.no_header_reading,
        dossier=dossier,
        dossier_seeding=not args.no_dossier_seeding,
        contextual=not args.no_contextual,
        contextual_vision_fallback=args.contextual_vision,
        read_direction_text=args.direction_text,
        overlays_dir=args.overlays_dir,
        progress=not args.quiet,
    )

    if args.out is None:
        print(json.dumps(result, indent=2))
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2))
        if not args.quiet:
            print(f"\nwrote {args.out}")
            print(f"  pages={result['n_pages_processed']}  "
                  f"systems={result['n_systems_total']}  "
                  f"staves={result['n_staves_total']}  "
                  f"measures={result['n_measures_total']}  "
                  f"detections={result['n_detections_total']}")
            print(f"  noteheads={result['n_noteheads_total']}  "
                  f"pitched={result['n_noteheads_pitched_total']}  "
                  f"({100 * result['n_noteheads_pitched_total'] // max(1, result['n_noteheads_total'])}% pitch coverage)")
            print(f"  with_duration={result['n_noteheads_with_duration_total']}  "
                  f"({100 * result['n_noteheads_with_duration_total'] // max(1, result['n_noteheads_total'])}% rhythm coverage)  "
                  f"rests={result['n_rests_with_duration_total']}/{result['n_rests_total']}")
            print(f"  runtime: phase1={result['runtime']['phase1_s']}s  "
                  f"yolo={result['runtime']['yolo_s']}s  "
                  f"total={result['runtime']['total_s']}s")
            if result.get("n_rhythm_reconciliations"):
                print(f"  meter->rhythm: "
                      f"{result['n_rhythm_reconciliations']} measure(s) "
                      f"re-read a beam level to match the meter")
            if result.get("dossier_warning_summary"):
                summary = result["dossier_warning_summary"]
                print(f"  dossier: {sum(summary.values())} disagreement(s) — "
                      + (", ".join(f"{k}={v}" for k, v in sorted(summary.items()))
                         or "none"))
            # Per-page warning summary: measures + how many carry a
            # phase1_warning (Phase 1 likely fused/missed a barline) or a
            # rhythm_sum_warning (beat count doesn't match the time sig).
            for page_d in result["pages"]:
                page_measures = [
                    m
                    for sys_d in page_d["systems"]
                    for st in sys_d["staves"]
                    for m in st["measures"]
                ]
                n_phase1 = sum(1 for m in page_measures if "phase1_warning" in m)
                n_rhythm = sum(1 for m in page_measures if "rhythm_sum_warning" in m)
                print(f"  page {page_d['page_index']}: "
                      f"{len(page_measures)} measures, "
                      f"{n_phase1} phase1_warnings, "
                      f"{n_rhythm} rhythm_sum_warnings")
                # Say out loud how much of the page's key signature is a
                # reading. Silence here used to look exactly like C major.
                staves_d = [st for sys_d in page_d["systems"]
                            for st in sys_d["staves"]]
                n_read = sum(1 for st in staves_d
                             if st.get("key_signature_read"))
                if staves_d and n_read < len(staves_d):
                    print(f"    key signatures: read on {n_read}/{len(staves_d)}"
                          f" staves; the rest report 0 sharps / 0 flats because"
                          f" nothing read them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
