"""YOLOv8 symbol detector — Phase 3 MVP wrapper.

Wraps an Ultralytics YOLO model so it produces `SymbolDetection` objects
compatible with the existing template-matcher scoring infrastructure.

This is an MVP — minimum viable detector. The intent is to get YOLO
producing detections in the SAME shape the template matcher produces, so
the existing `tools/omr/annotate/score.py` can directly compare them.

Weights:
    - DeepScoresV2-pretrained YOLOv8 weights are NOT publicly available
      as of Phase 3 (verified by searching huggingface.co for "deepscores"
      and "yolo music" — no music-symbol-trained YOLOv8 weights found).
    - Falling back to plain COCO-pretrained `yolov8m.pt` weights. These
      were trained on 80 generic object categories (person, car, donut,
      frisbee, etc.) and will NOT detect music symbols correctly. The
      point of using them in this MVP is to exercise the wrapper code
      end-to-end so that swapping in domain-trained weights later (when
      acquired or trained on DeepScoresV2) requires only a weights-path
      change, not a code change.

Public:
    YoloDetector(weights_path).detect(cell, conf_threshold=...) -> list[SymbolDetection]

When `category` cannot be inferred from the model's class names, the
detector emits `category="unknown"` and puts the raw YOLO class label in
`smufl_name`. The scorer treats unknown-category detections as
non-noteheads (no pitch resolution).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from .class_aliases import canonicalize_names
from .template_matcher import SymbolDetection
from .types import MeasureCell


# ---------------------------------------------------------------------------
# YOLO class name → SMuFL category mapping
# ---------------------------------------------------------------------------
#
# Data-driven expansion (2026-05-15): the original map covered only ~50 of
# DeepScoresV2's ~147 classes, which left ~37% of detections (342/916 on
# our 30 verdict cells) flagged as `unknown`. Counting class-label
# frequencies across `benchmarks/omr-phase3/r2/detections/*.json` showed
# that almost all the "unknown" mass came from a small set of recurring
# names: `beam` (202), `staff` (38), `dynamicF` (38), `tie` (17),
# `slur` (15), `augmentationDot` (10), `dynamicP` (5), `articStaccatoAbove`
# (5), `coda` (4), `articAccentBelow` (2), `arpeggiato` (2), `dynamicZ`,
# `segno`, `ornamentTurnInverted`, `ornamentMordent`. Cross-referenced
# against `tools/omr/training/deepscores_classes.py` so that the prefix
# rules (e.g. `dynamic` → dynamic, `ornament` → ornament, `artic` →
# ornament) also catch the long tail of unseen-but-related variants.
#
# Three new top-level categories were added: `structural` (beam, staff,
# tie, slur, augmentationDot, ledger lines, brackets, repeat/coda/segno
# markers), `dynamic` (any dynamicX), and `ornament` (ornament*,
# articulation marks, grace notes, fermata, tremolo, arpeggiato,
# caesura). If a class name still does not match anything here, the
# detector falls back to `category="unknown"` and puts the raw class name
# in `smufl_name`.
#
# Ordering matters: the substring fallback in `_class_name_to_category`
# iterates `_CATEGORY_MAP` in insertion order and returns the first match.
# Long/specific keys go first so that e.g. `graceNote...StemUp` matches
# `gracenote` (→ ornament) before it can match `stem`.

_CATEGORY_MAP = {
    # ---- specific compound names first (substring fallback order matters) ----
    # ornaments / grace notes / articulations (must precede the short
    # `stem` key, since gracenote names contain "stem")
    "gracenote": "ornament",
    "ornament": "ornament",
    "arpeggiato": "ornament",
    "fermata": "ornament",
    "tremolo": "ornament",
    "caesura": "ornament",
    "artic": "ornament",
    "augmentationdot": "structural",
    # dynamics — `dynamic` substring catches dynamicP/M/F/S/Z/R, hairpins, etc.
    "dynamic": "dynamic",
    # noteheads
    "noteheadblack": "notehead",
    "noteheadhalf": "notehead",
    "noteheadwhole": "notehead",
    "noteheaddoublewhole": "notehead",
    "notehead": "notehead",
    # rests
    "restwhole": "rest",
    "resthalf": "rest",
    "restquarter": "rest",
    "rest8th": "rest",
    "rest16th": "rest",
    "rest32nd": "rest",
    "rest64th": "rest",
    "rest128th": "rest",
    "rest": "rest",
    # accidentals (incl. key-signature variants via `keyflat`/`keysharp`/`keynatural`)
    "accidentalsharp": "accidental",
    "accidentalflat": "accidental",
    "accidentalnatural": "accidental",
    "accidentaldoublesharp": "accidental",
    "accidentaldoubleflat": "accidental",
    "keyflat": "accidental",
    "keysharp": "accidental",
    "keynatural": "accidental",
    "sharp": "accidental",
    "flat": "accidental",
    "natural": "accidental",
    # clefs
    "gclef": "clef",
    "fclef": "clef",
    "cclef": "clef",
    "clef": "clef",
    # flags
    "flag8thup": "flag",
    "flag8thdown": "flag",
    "flag16thup": "flag",
    "flag16thdown": "flag",
    "flag": "flag",
    # time-sig digits
    "timesig0": "time_sig_digit",
    "timesig1": "time_sig_digit",
    "timesig2": "time_sig_digit",
    "timesig3": "time_sig_digit",
    "timesig4": "time_sig_digit",
    "timesig5": "time_sig_digit",
    "timesig6": "time_sig_digit",
    "timesig7": "time_sig_digit",
    "timesig8": "time_sig_digit",
    "timesig9": "time_sig_digit",
    "timesigcommon": "time_sig_digit",
    "timesigcuttime": "time_sig_digit",
    "timesigcutcommon": "time_sig_digit",
    "tuplet": "structural",  # tuplet0-9 (digits painted on tuplet brackets)
    "fingering": "ornament",  # fingering0-5 (small annotation marks)
    "strings": "ornament",  # stringsUpBow, stringsDownBow (bowing direction)
    "keyboardpedal": "ornament",  # keyboardPedalPed, keyboardPedalUp
    # barlines
    "barline": "barline",
    "barlinesingle": "barline",
    "barlinedouble": "barline",
    "barlinefinal": "barline",
    "barlineheavy": "barline",
    # structural / non-symbol marks (beams, staff lines, ties, slurs,
    # navigation marks, brackets, ledger lines)
    "beam": "structural",
    "staff": "structural",
    "tie": "structural",
    "slur": "structural",
    "ledgerline": "structural",
    "brace": "structural",
    "coda": "structural",
    "segno": "structural",
    "repeatdot": "structural",
    "tupletbracket": "structural",
    "ottavabracket": "structural",
    # stems (kept as its own category for backward compatibility — see
    # gracenote ordering note above)
    "stem": "stem",
}


def _class_name_to_category(name: str) -> str:
    """Map a YOLO class name to a SMuFL category. Falls back to 'unknown'."""
    key = "".join(ch for ch in name.lower() if ch.isalnum())
    if key in _CATEGORY_MAP:
        return _CATEGORY_MAP[key]
    # Substring fallback — DeepScoresV2 names tend to be compound
    # ("noteheadBlackOnLine") so try a contains match on the bases.
    for k, cat in _CATEGORY_MAP.items():
        if k in key:
            return cat
    return "unknown"


# ---------------------------------------------------------------------------
# Inference scale
# ---------------------------------------------------------------------------
#
# A detector does not see pixels, it sees a staff space. `imgsz` is only a
# pixel budget; what decides whether the model recognises a notehead is how
# large that notehead is once the image has been letterboxed to `imgsz`.
#
# The pipeline feeds this detector CELLS, not pages, and `measure_extractor`
# has already rescaled every cell so its staff SPAN is 400 px — a staff space
# of 100. Running such a cell at `imgsz=2048` (chosen because the weights were
# fine-tuned on DeepScoresV2 pages at 2048) enlarges it again, and the model is
# shown a staff space of 100-200 px. It was never shown anything like that.
#
# The failure is not a graceful loss of recall. Past roughly 25 px the model
# stops finding noteheads and starts finding *fragments* of them: boxes a
# quarter of a notehead tall, stacked in columns up the vertical stroke of a
# time signature or a clef. On the authored end-to-end fixtures the note count
# then runs at 1.4-1.9x truth while the true notes go missing underneath.
#
# Measured on `benchmarks/omr-detector-scale/` — 30 measures of authored music
# whose note counts are exact — the response is a broad plateau and then a
# cliff:
#
#     staff space shown     ratio got/truth     measures exactly right
#            8 - 22             0.88-0.89              24/30
#              26               0.96                   17/30
#              50               1.77                    3/30
#          100 - 150          1.41-1.91                1-3/30
#
# 16 sits in the middle of the plateau, with about a factor of two of margin on
# either side, and is where notehead confidence peaks (0.91). At 16 the clef
# and time-signature counts on those fixtures are also exactly right (7 clefs
# on 7 staves, 14 digits on 7 "4/4" marks), where the wide end finds neither.
TARGET_STAFF_SPACE_PX = 16

# YOLO strides by 32; anything else is padded up to a multiple anyway.
_IMGSZ_STRIDE = 32
_MIN_AUTO_IMGSZ = 64
_MAX_AUTO_IMGSZ = 2048


# ---------------------------------------------------------------------------
# ROADMAP 2.12g — role-twin channels, one piece of ink, collapsed before a
# caller ever sees two boxes for it.
# ---------------------------------------------------------------------------
#
# `benchmarks/omr-shape-role-2026-09/FINDINGS.md` §5 row 4 / §(e): a YOLOv8
# detect head is per-class in its last layer, so `noteheadBlackOnLine` and
# `noteheadBlackInSpace` are two output channels scoring the SAME ink —
# `detect()` is called with class-wise NMS (`agnostic_nms=False`), so nothing
# stops both surviving their own class's suppression and reaching the caller
# as two boxes for one head. 859 such visible pairs were measured on the two
# scan records at the time of the audit. This does not reach the INVISIBLE
# half (a head whose evidence split across both channels and left BOTH under
# `conf_threshold`) — that needs the raw per-class score tensor before NMS
# runs at all (FINDINGS §(c): `ultralytics 8.4.50`'s `results.boxes` carries
# only the post-NMS argmax class and its own score, not every class's score
# per anchor), which is a larger, unbuilt change. This collapses the
# ALREADY-EMITTED twin pairs instead — the cheap half that needs no raw
# tensor access and no re-gather of the model itself.
#
# ⚠️ SHAPE stays, ROLE goes. The suffix is stripped to find the twin; the
# SURVIVING box keeps the higher-scoring twin's own class name (so a
# consumer reading `smufl_name`'s PREFIX, as `rhythm._HEAD_BEATS` and
# `Q.NOTEHEAD_STAFF_POSITION` already do per the audit, sees exactly what it
# saw before) and the dropped twin's class name is recorded on
# `detector_role` so nothing downstream loses it — see that field's own
# docstring on `SymbolDetection`. The role itself is never read from either
# spelling by anything in the product path today (2.12's own principle:
# shape from the class, role from the geometry — `Q.NOTEHEAD_STAFF_POSITION`,
# `articulation_owner`'s measured side, `stem_direction`'s measured flag
# direction).
#
# ⚠️ THE SUFFIX TABLE IS A SUFFIX TEST, NOT A HAND-LISTED CLASS-PAIR TABLE —
# the `_CLEF_CLASSES_INCUMBENT` lesson (`gather.py:259-268`: a hand-written
# second list admitted the spelling that never occurs and dropped the two
# that do). Any class ending in one of these six strings is a candidate;
# which OTHER class it twins with is derived by stripping the suffix and
# matching the remaining shape core, never spelled out per-class.
#
# ⚠️ `key*`/`accidental*` is explicitly OUT OF SCOPE here (unlike the
# ROADMAP one-liner's own paraphrase): FINDINGS §5's 2.12g entry (the
# authoritative, measured scope) describes the NARROWER arm as exactly these
# three suffix families, and 2.12a already gives the accidental/key role a
# GATHER-level answer (the header-window join) that does not depend on two
# detector classes existing for one mark — collapsing them here before NMS
# would remove the second class 2.12a's own join reads.
_ROLE_TWIN_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("OnLine", "InSpace"),
    ("Above", "Below"),
    ("Up", "Down"),
)

#: A role-twin merge only ever claims to be the SAME ink, never a chord's
#: second member drawn beside it. Both gates must agree, same shape as
#: `notehead_precision._same_mark_centres` (ROADMAP 2.30) — a dy_spaces and
#: dx_head_widths test, not IoU alone, because IoU alone is exactly what
#: that rule's own docstring warns is unsafe for a legitimate chord second.
_TWIN_MAX_DY_STAFF_SPACES = 0.25
_TWIN_MAX_DX_HEAD_WIDTHS = 0.5


def _twin_shape_core(class_name: str) -> tuple[str | None, str | None]:
    """`(shape_core, suffix)` if `class_name` ends in a role-twin suffix,
    else `(None, None)`. The suffix test IS the derivation — see the module
    comment above on why this is not a hand-listed class-pair table."""
    for a, b in _ROLE_TWIN_SUFFIXES:
        if class_name.endswith(a):
            return class_name[: -len(a)], a
        if class_name.endswith(b):
            return class_name[: -len(b)], b
    return None, None


def _same_ink_twin(a: "SymbolDetection", b: "SymbolDetection",
                    spacing_canonical: float) -> bool:
    """Do `a` and `b` box the SAME piece of ink, never a chord's second
    member drawn beside it at the same x? Ported unchanged in SHAPE from
    `notehead_precision._same_mark_centres` (ROADMAP 2.30) — centres, not
    IoU alone."""
    if spacing_canonical <= 0:
        return False
    ay = a.y_canonical + a.height_canonical / 2.0
    by = b.y_canonical + b.height_canonical / 2.0
    dy_spaces = abs(ay - by) / spacing_canonical
    if dy_spaces >= _TWIN_MAX_DY_STAFF_SPACES:
        return False
    head_width = (a.width_canonical + b.width_canonical) / 2.0
    if head_width <= 0:
        return False
    ax = a.x_canonical + a.width_canonical / 2.0
    bx = b.x_canonical + b.width_canonical / 2.0
    dx = abs(ax - bx)
    return dx < _TWIN_MAX_DX_HEAD_WIDTHS * head_width


def _cell_spacing_canonical(cell: MeasureCell) -> float | None:
    """The same per-cell staff-space measurement `imgsz_for_cell` uses — a
    position test must measure LOCALLY (CLAUDE.md §10), never against a
    page- or bar-wide constant."""
    ys = getattr(cell, "staff_line_ys_canonical", None) or []
    if len(ys) < 2:
        return None
    space = (ys[-1] - ys[0]) / (len(ys) - 1)
    return space if space > 0 else None


def _collapse_role_twins(
    detections: list["SymbolDetection"], cell: MeasureCell,
) -> list["SymbolDetection"]:
    """One piece of ink is one reading (ROADMAP 2.12g). Merge same-ink
    role-twin pairs (see module comment above), keeping the higher-scoring
    box and recording the dropped twin's class on `detector_role`.

    MERGES, never DELETES: a pair that does not pass `_same_ink_twin`'s
    geometry gate is left exactly as emitted, same as a pair of genuinely
    different shapes, or two real chord members. No geometry to measure
    against (`_cell_spacing_canonical` returns `None`) abstains the whole
    cell from this merge rather than guessing (CLAUDE.md rule 8) — the
    pre-2.12g behaviour, unchanged.
    """
    if len(detections) < 2:
        return detections
    spacing = _cell_spacing_canonical(cell)
    if spacing is None:
        return detections
    n = len(detections)
    dropped: set[int] = set()
    survivor_role: dict[int, str] = {}
    for i in range(n):
        if i in dropped:
            continue
        di = detections[i]
        core_i, suf_i = _twin_shape_core(di.smufl_name)
        if core_i is None:
            continue
        for j in range(i + 1, n):
            if j in dropped:
                continue
            dj = detections[j]
            core_j, suf_j = _twin_shape_core(dj.smufl_name)
            if core_j is None or core_j != core_i or suf_j == suf_i:
                continue
            if not _same_ink_twin(di, dj, spacing):
                continue
            if di.confidence >= dj.confidence:
                winner_idx, loser_idx = i, j
            else:
                winner_idx, loser_idx = j, i
            dropped.add(loser_idx)
            survivor_role[winner_idx] = detections[loser_idx].smufl_name
            # the loser is gone; stop comparing IT against later boxes, but
            # the winner (possibly `dj`) keeps comparing against the rest —
            # re-bind di/suf_i if the winner just became j.
            if winner_idx == j:
                di, core_i, suf_i = dj, core_j, suf_j
    if not dropped:
        return detections
    out: list[SymbolDetection] = []
    for idx, d in enumerate(detections):
        if idx in dropped:
            continue
        role = survivor_role.get(idx)
        out.append(d if role is None else
                    SymbolDetection(
                        cell=d.cell, smufl_name=d.smufl_name,
                        category=d.category, x_canonical=d.x_canonical,
                        y_canonical=d.y_canonical,
                        width_canonical=d.width_canonical,
                        height_canonical=d.height_canonical,
                        confidence=d.confidence, pitch=d.pitch,
                        detector_role=role))
    return out


def imgsz_for_cell(
    cell: MeasureCell,
    target_staff_space_px: float = TARGET_STAFF_SPACE_PX,
) -> int:
    """The `imgsz` that shows the model a staff space of `target_staff_space_px`.

    Derived from the cell's OWN canonical staff spacing rather than from the
    page, because that is the number the model is shown: ultralytics scales the
    longest side to `imgsz`, so

        staff space shown = canonical staff space * imgsz / longest side.

    Falls back to `_MAX_AUTO_IMGSZ` for a cell with no usable staff lines —
    there is nothing to calibrate against, and that is the historical default.
    """
    ys = getattr(cell, "staff_line_ys_canonical", None) or []
    if len(ys) < 2:
        return _MAX_AUTO_IMGSZ
    space = (ys[-1] - ys[0]) / (len(ys) - 1)
    if space <= 0:
        return _MAX_AUTO_IMGSZ
    image = getattr(cell, "image", None)
    if image is None:
        return _MAX_AUTO_IMGSZ
    long_side = max(image.shape[0], image.shape[1])
    raw = target_staff_space_px * long_side / space
    rounded = int(round(raw / _IMGSZ_STRIDE)) * _IMGSZ_STRIDE
    return max(_MIN_AUTO_IMGSZ, min(_MAX_AUTO_IMGSZ, rounded))


# ---------------------------------------------------------------------------
# Detector wrapper
# ---------------------------------------------------------------------------


class YoloDetector:
    """Ultralytics YOLO wrapped to produce SymbolDetection objects.

    Lazy-loads the model on first detect() call to keep import-time cheap.
    """

    def __init__(self, weights_path: str | Path, device: str = "auto"):
        self.weights_path = str(weights_path)
        self.device = device
        self._model = None
        self._class_names: dict[int, str] | None = None

    # --------------- model lifecycle ---------------

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        # Import here so users without ultralytics installed can still
        # import this module.
        from ultralytics import YOLO  # type: ignore
        self._model = YOLO(self.weights_path)
        names = getattr(self._model, "names", None)
        if isinstance(names, dict):
            raw = {int(k): str(v) for k, v in names.items()}
        elif isinstance(names, list):
            raw = {i: str(v) for i, v in enumerate(names)}
        else:
            raw = {}
        # The 208-class space spells 32 glyphs under a second, coarser name that
        # no consumer in this pipeline knows (`dynamicLetterF` for `dynamicF`),
        # so a detection under one is read and under the other is dropped in
        # silence. Renamed HERE, at the one place the model's own vocabulary is
        # read, so every consumer downstream sees a single spelling and no call
        # site has to know. See `class_aliases` for the table, what is
        # deliberately NOT renamed, and why.
        self._class_names = canonicalize_names(raw)

    # --------------- inference ---------------

    def detect(
        self,
        cell: MeasureCell,
        conf_threshold: float = 0.25,
        imgsz: int | None = None,
        iou_threshold: float = 0.7,
        agnostic_nms: bool = False,
    ) -> list[SymbolDetection]:
        """Run YOLO on `cell.image` and return SymbolDetection objects in
        canonical-image coordinates.

        Uses `cell.image` (the original, with staff lines intact) — YOLO is
        trained on full notation, not on staff-removed images.

        Args:
            conf_threshold: minimum detection confidence (0-1).
            imgsz: inference image size. None (the default) picks it per cell
                so the model is shown a staff space of
                `TARGET_STAFF_SPACE_PX`; pass a number to override. See
                `imgsz_for_cell` for why a fixed value is the wrong knob here.
            iou_threshold: NMS IoU threshold. Lower = more aggressive
                suppression of overlapping boxes.
            agnostic_nms: if True, NMS suppresses across classes (one box
                per region regardless of class). Useful for music notation
                where the same region can fire multiple semantically-similar
                class predictions (e.g., `dynamicF` + `dynamicFF` on one
                `ff` mark).
        """
        self._ensure_loaded()
        assert self._model is not None

        img = cell.image
        if img is None:
            return []
        # YOLO expects 3-channel RGB. Cell image may be grayscale.
        if img.ndim == 2:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            # cv2 reads BGR; YOLO accepts BGR fine, but normalize for safety.
            img_rgb = img if img.shape[2] == 3 else cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)

        if imgsz is None:
            imgsz = imgsz_for_cell(cell)

        # MPS device hint on Apple Silicon; "auto" lets ultralytics pick.
        results = self._model.predict(
            source=img_rgb,
            conf=conf_threshold,
            iou=iou_threshold,
            agnostic_nms=agnostic_nms,
            imgsz=imgsz,
            device=self.device if self.device != "auto" else None,
            verbose=False,
        )
        if not results:
            return []
        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return []

        # Each box: xyxy, conf, cls
        xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes.xyxy, "cpu") else np.asarray(boxes.xyxy)
        confs = boxes.conf.cpu().numpy() if hasattr(boxes.conf, "cpu") else np.asarray(boxes.conf)
        clses = boxes.cls.cpu().numpy() if hasattr(boxes.cls, "cpu") else np.asarray(boxes.cls)

        detections: list[SymbolDetection] = []
        for (x0, y0, x1, y1), conf, cls in zip(xyxy, confs, clses):
            x = int(round(float(x0)))
            y = int(round(float(y0)))
            w = max(1, int(round(float(x1) - float(x0))))
            h = max(1, int(round(float(y1) - float(y0))))
            class_id = int(cls)
            class_name = (self._class_names or {}).get(class_id, f"cls_{class_id}")
            category = _class_name_to_category(class_name)
            # If category is unknown (e.g. COCO classes like "donut"),
            # we still emit the detection so the scorer can see it — the
            # raw class label goes in `smufl_name`.
            smufl_name = class_name if category != "unknown" else class_name
            detections.append(SymbolDetection(
                cell=cell,
                smufl_name=smufl_name,
                category=category,
                x_canonical=x,
                y_canonical=y,
                width_canonical=w,
                height_canonical=h,
                confidence=float(conf),
                pitch=None,
            ))
        # ROADMAP 2.12g: one piece of ink is one reading. See the module
        # comment above `_collapse_role_twins` for scope and why this is
        # the cheap half of the fix, not the invisible-half one.
        return _collapse_role_twins(detections, cell)

    # --------------- diagnostics ---------------

    def time_detect(
        self,
        cell: MeasureCell,
        conf_threshold: float = 0.25,
        n_runs: int = 5,
    ) -> dict:
        """Run detect() N times and return timing stats. Skips the first
        run (warmup) when N >= 2."""
        runs: list[float] = []
        first: list[SymbolDetection] | None = None
        for i in range(n_runs):
            t0 = time.perf_counter()
            dets = self.detect(cell, conf_threshold=conf_threshold)
            t1 = time.perf_counter()
            if first is None:
                first = dets
            runs.append(t1 - t0)
        timed = runs[1:] if len(runs) >= 2 else runs
        return {
            "n_runs": n_runs,
            "n_detections": len(first or []),
            "all_times_s": runs,
            "median_s_excluding_warmup": float(np.median(timed)) if timed else None,
            "mean_s_excluding_warmup": float(np.mean(timed)) if timed else None,
        }
