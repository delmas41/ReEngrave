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
      "weights":    "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt",
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
                  "key_signature": {
                      "sharps": 0,          # count of sharps in the key sig
                      "flats":  0,          # count of flats (mutually exclusive)
                      "alterations": {"F": "#", "C": "#"}  # letter -> '#'|'b'
                  },
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
                  "measures": [
                    {
                      "measure_index": 0,
                      "bbox_page_px": [x0, y0, x1, y1],
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
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .preprocessing import render_page
from .staff_detector import detect_staves
from .measure_extractor import detect_barlines, extract_measures, resegment_fused_measures
from .staff_line_removal import remove_staff_lines
from .types import MeasureCell
from .pitch_resolver import pitch_for_notehead, pitch_candidates_for_notehead
from .rhythm import (
    parse_time_signature,
    resolve_rhythms_for_cell,
    backfill_page_time_signatures,
    measure_length_beats,
)
from .line_detection import detect_lines
from .voicing import group_chords_in_measure, split_events_into_voices


# Default weights — Phase 3.3, F1 98.8% on the 25 verdict cells.
# Keep this in sync with the latest "production" weights.
DEFAULT_WEIGHTS = (
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
    """Map a DSv2 clef class name to a pitch_resolver clef key.

    Returns None for unpitched / octave-marker clefs (clef8 / clef15 are
    standalone glyphs that visually attach to a base clef; they're picked
    up separately by `_octave_shift_for_base_clef`).
    """
    if not smufl:
        return None
    s = smufl.lower()
    if "calto" in s:
        return "alto"
    if "ctenor" in s:
        return "tenor"
    if s.startswith("clefg") or s == "gclef":
        return "treble"
    if s.startswith("cleff") or s == "fclef":
        return "bass"
    if "percussion" in s or s in ("clef8", "clef15"):
        return None
    if s.startswith("clefc") or s == "cclef":  # generic C-clef → alto fallback
        return "alto"
    return None


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


def _stem_direction(notehead, stem) -> str:
    """Decide stem direction ('up' / 'down') from notehead position
    within the stem's y-range.

    Stem-up: stem extends ABOVE the notehead (notehead at bottom of stem).
    Stem-down: stem extends BELOW the notehead (notehead at top of stem).

    Compare the notehead's y_center to the stem's y midpoint.
    """
    nh_y_c = notehead.y_canonical + notehead.height_canonical // 2
    s_y_mid = stem.y_canonical + stem.height_canonical // 2
    return "up" if nh_y_c > s_y_mid else "down"


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


def _detect_key_sig_from_cell(dets) -> dict[str, str] | None:
    """Scan detections for keySharp / keyFlat markers (which the DSv2
    detector emits distinctly from inline accidentals). Returns the new
    alteration map, or None if no key-signature markers were seen (so the
    caller should keep the previous active key sig).
    """
    n_sharps = sum(
        1 for d in dets if d.smufl_name.lower().startswith("keysharp")
    )
    n_flats = sum(
        1 for d in dets if d.smufl_name.lower().startswith("keyflat")
    )
    if n_sharps == 0 and n_flats == 0:
        return None  # no update — keep whatever was active
    # Music never has both sharps + flats in one key sig; if the detector
    # somehow emits both, trust the larger count.
    if n_sharps >= n_flats:
        return _key_sig_alterations(n_sharps, 0)
    return _key_sig_alterations(0, n_flats)


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


def _detections_for_cell(
    detector,  # YoloDetector — passed in to avoid import at module import time
    cell: MeasureCell,
    *,
    conf_threshold: float,
    imgsz: int,
    iou_threshold: float,
    agnostic_nms: bool,
    active_clef: str | None,
    active_key_sig: dict[str, str],
    active_time_sig: dict[str, Any] | None,
    clef_reader=None,  # optional secondary YoloDetector — clef specialist
    read_clef: bool = False,
    clef_reader_conf: float = 0.30,
) -> tuple[list[dict[str, Any]], str | None, dict[str, str], dict[str, Any] | None]:
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

    Returns `(detection_dicts, new_active_clef, new_active_key_sig)`.
    """
    dets = detector.detect(
        cell,
        conf_threshold=conf_threshold,
        imgsz=imgsz,
        iou_threshold=iou_threshold,
        agnostic_nms=agnostic_nms,
    )

    # ── Clef pass: update active_clef from the highest-confidence clef
    #    detection in this cell, if any. If a clef8 / clef15 octave marker
    #    sits next to the chosen base clef, append the corresponding
    #    "_8va" / "_8vb" / "_15ma" / "_15mb" suffix so the pitch resolver
    #    picks up the right anchor (e.g. choral tenor on treble_8vb). ────
    best_clef_name: str | None = None
    best_clef_det = None
    best_clef_conf = -1.0
    for d in dets:
        if d.category != "clef":
            continue
        mapped = _clef_name_from_class(d.smufl_name)
        if mapped is None:
            continue
        if d.confidence > best_clef_conf:
            best_clef_name = mapped
            best_clef_det = d
            best_clef_conf = d.confidence
    if best_clef_name is not None:
        suffix = _octave_shift_for_base_clef(dets, best_clef_det)
        active_clef = best_clef_name + suffix

    # ── Decoupled clef reader (specialist override). Run a secondary,
    #    clef-specialized detector on this cell and let ITS clef win over the
    #    production detector's. The production model under-detects clefs on
    #    real orchestral scans (9% detection, 0% type → the "all-treble
    #    disease"); a model fine-tuned on real clef cells reads them well but
    #    collapses dense-notehead detection, so it can't be the main detector.
    #    Using ONLY its clef output — on the staff-start cell where the printed
    #    clef lives — gets the clef win with zero cost to notehead detection.
    #    See benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md. Runs before the
    #    pitch pass below so the corrected clef anchors every pitch in the cell.
    if read_clef and clef_reader is not None:
        clef_dets = clef_reader.detect(
            cell,
            conf_threshold=clef_reader_conf,
            imgsz=imgsz,
            iou_threshold=iou_threshold,
            agnostic_nms=agnostic_nms,
        )
        spec_name, spec_det, spec_conf = None, None, -1.0
        for d in clef_dets:
            if d.category != "clef":
                continue
            mapped = _clef_name_from_class(d.smufl_name)
            if mapped is None:
                continue
            if d.confidence > spec_conf:
                spec_name, spec_det, spec_conf = mapped, d, d.confidence
        if spec_name is not None:
            active_clef = spec_name + _octave_shift_for_base_clef(clef_dets, spec_det)

    # ── Key-signature pass: scan for keySharp / keyFlat. None ⇒ no update. ──
    new_key_sig = _detect_key_sig_from_cell(dets)
    if new_key_sig is not None:
        active_key_sig = new_key_sig

    # ── Time-signature pass: parse from timeSig0-9 / timeSigCommon detections.
    new_time_sig = parse_time_signature(dets)
    if new_time_sig is not None:
        active_time_sig = new_time_sig

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

    # ── Stem-direction inference. For each notehead, find its attached
    #    stem (classical-CV) and decide whether the stem goes up (above
    #    the notehead) or down (below). This drives voice splitting in
    #    Phase 4h: stem-up = voice 1 (upper), stem-down = voice 2 (lower).
    stem_direction_by_id: dict[int, str] = {}
    cv_stems = extra_lines.get("stems") or []
    if cv_stems:
        for d in dets:
            if getattr(d, "category", "") != "notehead":
                continue
            stem = _find_attached_stem(d, cv_stems)
            if stem is None:
                continue
            stem_direction_by_id[id(d)] = _stem_direction(d, stem)

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
        # Stem direction for noteheads (Phase 4h voice splitting).
        if id(d) in stem_direction_by_id:
            out_d["stem_direction"] = stem_direction_by_id[id(d)]
        # Tie flags (only emitted when present, to keep the JSON terser).
        if id(d) in ties_to_next:
            out_d["tied_to_next"] = True
        if id(d) in ties_from_prev:
            out_d["tied_from_prev"] = True
        out.append(out_d)
    return out, active_clef, active_key_sig, active_time_sig


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


def _pitch_to_midi(pitch: str | None) -> int | None:
    """Convert a pitch string ('F#3', 'Bb5', 'C4') to a MIDI number (C4 = 60),
    or None if unparseable. Accepts any run of #/b accidentals after the letter."""
    if not pitch or pitch[0] not in _NOTE_SEMITONE:
        return None
    semitone = _NOTE_SEMITONE[pitch[0]]
    i = 1
    while i < len(pitch) and pitch[i] in "#b":
        semitone += 1 if pitch[i] == "#" else -1
        i += 1
    try:
        octave = int(pitch[i:])
    except ValueError:
        return None
    return 12 * (octave + 1) + semitone


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


def transcribe(
    *,
    pdf_path: Path,
    pages: list[int],
    weights: str,
    conf_threshold: float = 0.25,
    imgsz: int = 2048,
    iou_threshold: float = 0.5,
    agnostic_nms: bool = True,
    dpi: int = 600,
    clef_weights: str | None = None,
    clef_reader_conf: float = 0.30,
    overlays_dir: Path | None = None,
    progress: bool = True,
) -> dict[str, Any]:
    """Run the full transcribe pipeline. Returns the structured dict.

    The defaults match what the Phase 3.3 evaluation used (conf=0.25,
    agnostic_nms=True). Lower conf_threshold (e.g. 0.10) for higher recall
    at the cost of more false positives.
    """
    # Lazy-import the YOLO wrapper so this module imports cheaply when the
    # caller doesn't actually need OMR (e.g. when listing pages).
    from .yolo_detector import YoloDetector

    detector = YoloDetector(weights, device="auto")
    # Optional decoupled clef specialist (see _detections_for_cell). Loaded
    # once and reused; None ⇒ clef comes from the production detector alone.
    clef_reader = YoloDetector(clef_weights, device="auto") if clef_weights else None

    out: dict[str, Any] = {
        "source_pdf": str(pdf_path),
        "weights": weights,
        "clef_weights": clef_weights,
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
    for p in pages:
        t_phase1 = time.perf_counter()
        page = render_page(pdf_path, p, dpi=dpi)
        pws = detect_staves(page)
        pws = detect_barlines(pws)
        cells = extract_measures(pws)
        # Phase 1i: locally re-split any cell that's already going to be
        # flagged as a >2x-median-width outlier below, if a genuine
        # internal barline can be found inside it. Conservative by
        # construction — see measure_extractor.resegment_fused_measures.
        cells = resegment_fused_measures(pws, cells)
        remove_staff_lines(cells)
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
                active_key_sig = active_key_sig_by_staff.get(
                    (p, sys_idx, staff_idx),
                    {},  # default: C major / A minor — no alterations
                )
                active_time_sig = active_time_sig_by_staff.get(
                    (p, sys_idx, staff_idx),
                    None,  # default: unknown — only set when detected
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
                    "n_measures": len(staff_cells),
                    "measures": [],
                }
                first_cell_effective_clef: str | None = None
                first_cell_effective_key_sig: dict[str, str] | None = None
                first_cell_effective_time_sig: dict[str, Any] | None = None
                for cell_idx, cell in enumerate(staff_cells):
                    detections, active_clef, active_key_sig, active_time_sig = (
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
                            read_clef=(cell_idx == 0),
                            clef_reader_conf=clef_reader_conf,
                        )
                    )
                    if cell_idx == 0:
                        first_cell_effective_clef = active_clef
                        first_cell_effective_key_sig = dict(active_key_sig)
                        first_cell_effective_time_sig = (
                            dict(active_time_sig) if active_time_sig else None
                        )
                    staff_dict["measures"].append({
                        "measure_index": cell.measure_index,
                        "bbox_page_px": list(cell.bbox_page_px),
                        "clef": active_clef,
                        "key_signature": _key_sig_summary(active_key_sig),
                        "time_signature": dict(active_time_sig) if active_time_sig else None,
                        "n_detections": len(detections),
                        "detections": detections,
                    })
                    out["n_detections_total"] += len(detections)
                    out["n_measures_total"] += 1

                # Staff-level effective state = whatever was in effect during
                # the first measure of the staff (post any leading detections).
                staff_dict["clef"] = first_cell_effective_clef
                staff_dict["key_signature"] = _key_sig_summary(
                    first_cell_effective_key_sig or {}
                )
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
        backfill_page_time_signatures(page_dict)

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
    ap.add_argument("--weights", default=DEFAULT_WEIGHTS,
                    help=f"YOLO weights path (default: {DEFAULT_WEIGHTS})")
    ap.add_argument("--clef-weights", default=None,
                    help="OPTIONAL clef-specialist weights. When set, a second "
                         "detector reads each staff's clef from its start cell "
                         "and overrides the main detector's clef (fixes the "
                         "all-treble disease on orchestral scans without touching "
                         "notehead detection). Env: OMR_CLEF_WEIGHTS.")
    ap.add_argument("--clef-reader-conf", type=float, default=0.30,
                    help="Min confidence for a clef-specialist detection to "
                         "override the main clef (default: 0.30)")
    ap.add_argument("--conf", type=float, default=0.25,
                    help="Detection confidence threshold (default: 0.25)")
    ap.add_argument("--imgsz", type=int, default=2048,
                    help="YOLO inference image size (default: 2048 — matches "
                         "the production weights' fine-tuning resolution)")
    ap.add_argument("--iou", type=float, default=0.5,
                    help="NMS IoU threshold (default: 0.5)")
    ap.add_argument("--no-agnostic-nms", action="store_true",
                    help="Disable agnostic NMS (default: enabled, collapses "
                         "overlapping boxes across classes)")
    ap.add_argument("--dpi", type=int, default=600,
                    help="Source-page render DPI (default: 600)")
    ap.add_argument("--overlays-dir", type=Path, default=None,
                    help="If set, write per-page overlay PNGs here")
    ap.add_argument("--quiet", action="store_true",
                    help="Suppress per-page progress logs")
    args = ap.parse_args(argv)

    if not args.pdf.exists():
        print(f"ERROR: PDF not found: {args.pdf}")
        return 2

    if not Path(args.weights).exists():
        print(f"ERROR: weights file not found: {args.weights}")
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

    if not args.quiet:
        print(f"transcribe: {args.pdf.name} ({n_pages} pages, processing {len(pages)})")
        print(f"  weights:  {args.weights}")
        if clef_weights:
            print(f"  clef:     {clef_weights} (specialist, conf {args.clef_reader_conf})")
        print(f"  conf:     {args.conf}, iou: {args.iou}, "
              f"agnostic_nms: {not args.no_agnostic_nms}, imgsz: {args.imgsz}")

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
