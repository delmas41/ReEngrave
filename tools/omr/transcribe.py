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
import time
from pathlib import Path
from typing import Any

from .preprocessing import render_page
from .staff_detector import detect_staves
from .measure_extractor import detect_barlines, extract_measures
from .staff_line_removal import remove_staff_lines
from .types import MeasureCell
from .pitch_resolver import pitch_for_notehead
from .rhythm import parse_time_signature, resolve_rhythms_for_cell
from .line_detection import detect_lines


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

    Returns None for unpitched / octave-marker clefs (we don't resolve pitches
    on those — leaves the noteheads' pitch field as null).
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
    #    detection in this cell, if any. ──────────────────────────────────────
    best_clef_name: str | None = None
    best_clef_conf = -1.0
    for d in dets:
        if d.category != "clef":
            continue
        mapped = _clef_name_from_class(d.smufl_name)
        if mapped is None:
            continue
        if d.confidence > best_clef_conf:
            best_clef_name = mapped
            best_clef_conf = d.confidence
    if best_clef_name is not None:
        active_clef = best_clef_name

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
        out.append(out_d)
    return out, active_clef, active_key_sig, active_time_sig


def transcribe(
    *,
    pdf_path: Path,
    pages: list[int],
    weights: str,
    conf_threshold: float = 0.25,
    imgsz: int = 640,
    iou_threshold: float = 0.5,
    agnostic_nms: bool = True,
    dpi: int = 600,
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

    out: dict[str, Any] = {
        "source_pdf": str(pdf_path),
        "weights": weights,
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
    # (until a change is detected). NOT carried across pages — the
    # courtesy clef + key sig + time sig at the start of a new page should
    # re-establish them; if the detector misses, defaults kick in.
    active_clef_by_staff: dict[tuple[int, int, int], str | None] = {}
    active_key_sig_by_staff: dict[tuple[int, int, int], dict[str, str]] = {}
    active_time_sig_by_staff: dict[tuple[int, int, int], dict[str, Any] | None] = {}

    t_total = time.perf_counter()
    for p in pages:
        t_phase1 = time.perf_counter()
        page = render_page(pdf_path, p, dpi=dpi)
        pws = detect_staves(page)
        pws = detect_barlines(pws)
        cells = extract_measures(pws)
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
            for position_in_system, staff_idx in enumerate(staff_keys):
                staff_cells = systems[sys_idx][staff_idx]
                # Pick a default clef for this staff. Will be overridden the
                # moment a clef detection appears (which on engraved music is
                # typically inside the very first cell).
                active_clef = active_clef_by_staff.get(
                    (p, sys_idx, staff_idx),
                    _default_clef_for_position(position_in_system, len(staff_keys)),
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
                sys_dict["staves"].append(staff_dict)
                out["n_staves_total"] += 1
            page_dict["systems"].append(sys_dict)
            out["n_systems_total"] += 1
        out["runtime"]["yolo_s"] += time.perf_counter() - t_yolo

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
    ap.add_argument("--conf", type=float, default=0.25,
                    help="Detection confidence threshold (default: 0.25)")
    ap.add_argument("--imgsz", type=int, default=640,
                    help="YOLO inference image size (default: 640)")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
