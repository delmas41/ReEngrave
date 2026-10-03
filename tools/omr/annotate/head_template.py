"""Head TEMPLATE matching for far-head ledger evidence (ROADMAP lane
`lane-ledger-template`, 2026-10-02 -- DECISIONS task brief: "try
head-template matching for far heads" after the shape trace
(`ledger_shape_trace.py`) was measured NET NEGATIVE, held back).

Why this exists, and why the oval trace was the wrong primitive: on
Litolff, far heads are routinely FUSED with their own stem, a slur, a
neighbouring chord partner, or printed text -- `ledger_shape_trace.py`'s
own FINDINGS entry reads the regression tiles as "oval/centre mis-fit
onto fused or adjacent ink" (8 of 19) and "no ledger ink found anywhere
inside the trace's own search window" (6 of 19): fitting a FRESH oval
from the ink around *this* head, every time, keeps re-deriving a shape
that real plate ink routinely defeats. A TEMPLATE built once, from
CLEAN exemplars elsewhere on the SAME page (a chord-free, slur-free,
one-per-cell notehead, filled or hollow, already sitting on a line or in
a space with its own real printed context around it), sidesteps that:
matching asks "does the ink here look like a real head of this shape and
this on/space kind", never "fit a new outline to whatever is here".

Pipeline (task brief's own three steps):

  1. `build_templates` -- collect clean, isolated, on-staff exemplars
     from one page's own record + render, normalise each to a FIXED
     canonical grid (independent of the page's own spacing), and average
     them per (kind, variant) into `Template`s: `kind` in
     `{"filled", "hollow"}`, `variant` in `{"on_line", "in_space", "raw"}`.
  2. `match_head_template` -- for a far head, slide the `on_line` and
     `in_space` templates vertically over the real page ink at the
     head's own x (staff lines LEFT IN -- they are exactly the signal
     being matched for), scored by a correlation that only ever looks at
     the template's own HEAD pixels plus its LINE-ROW pixels -- ink
     elsewhere in the window (a neighbour's stem, a slur) never counts
     for or against the match.
  3. `template_middle_rung_evidence` -- the SAME 4-positional-argument
     drop-in contract `ledger_shape_trace.shape_trace_middle_rung_evidence`
     already gives `ledger_grid.derive_far_head_step`, so this module can
     be substituted into the SAME proven rung-counting harness by the
     SAME local monkeypatch `score_shape_trace.py` used -- `templates`/
     `stem_box`/`kind` bind per call via a closure, exactly like
     `staff_lines` did there.

Nothing here is wired into any product/default path. Measurement only
(CLAUDE.md rule 9); reuses `ledger_grid._otsu_threshold`,
`ledger_shape_trace._mask_stem_columns` and
`ledger_shape_trace._blank_excluded_boxes` rather than re-deriving them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .ledger_grid import _otsu_threshold
from .ledger_shape_trace import _mask_stem_columns, _blank_excluded_boxes
from ..staged.geometry import STANDARD_HEAD_WIDTH_SPACES, STANDARD_HEAD_HEIGHT_SPACES

try:
    import cv2
except ImportError:  # pragma: no cover -- cv2 is a hard repo dependency
    cv2 = None


# ─────────────────────────────────────────────────────────────────────────
# the canonical template grid -- fixed pixel size, independent of any one
# page's own DPI/spacing, so templates built on one page can be matched
# against a head on another (or the same) page at a DIFFERENT local
# spacing by resampling the CANDIDATE window to this same grid, never the
# template.
# ─────────────────────────────────────────────────────────────────────────

CANONICAL_PX_PER_SPACE = 30.0

WINDOW_HALF_WIDTH_HEAD_WIDTHS = 1.5
WINDOW_HALF_HEIGHT_HEAD_HEIGHTS = 0.6
WINDOW_HALF_HEIGHT_EXTRA_SPACES = 0.5

_CANON_HALF_W = (WINDOW_HALF_WIDTH_HEAD_WIDTHS * STANDARD_HEAD_WIDTH_SPACES
                 * CANONICAL_PX_PER_SPACE)
_CANON_HALF_H = ((WINDOW_HALF_HEIGHT_HEAD_HEIGHTS * STANDARD_HEAD_HEIGHT_SPACES
                  + WINDOW_HALF_HEIGHT_EXTRA_SPACES) * CANONICAL_PX_PER_SPACE)
CANONICAL_W = int(round(2 * _CANON_HALF_W))
CANONICAL_H = int(round(2 * _CANON_HALF_H))

# A ledger band is at most this many staff spaces tall (same cap
# `ledger_shape_trace.LEDGER_BAND_MAX_SPACES` uses).
LEDGER_BAND_MAX_SPACES = 0.35
# How far past the oval's own half-width a ledger reaches, scored as part
# of the "line row" mask (a ledger stub is real ink past the head on at
# least one side -- `ledger_grid.RUNG_BEYOND_BOX_MIN_SPACES` plus a
# margin so the mask comfortably covers a real stub).
LEDGER_REACH_HEAD_WIDTHS = 0.75

# Minimum real exemplars before a (kind, variant) template is trusted at
# all -- fewer than this and the average is noise, not a template
# (reported, never silently built).
MIN_TEMPLATE_EXEMPLARS = 3

# Below this normalised-correlation margin between the best on-line and
# best in-space match, the head is UNDECIDED (CLAUDE.md rule 8: "cannot
# tell" is never answered "yes, a line") -- stated up front, per the task
# brief ("below a margin you state in advance -> undecided").
MARGIN_UNDECIDED_THRESHOLD = 0.08

# Vertical slide range/step when matching (task brief: "+/-1.5 staff
# spaces in 1-px steps").
SLIDE_RANGE_SPACES = 1.5
SLIDE_STEP_PX = 1

# A hollow head's own INNER ink fraction (the open centre) stays below
# this; a filled head's is far higher. Used only when `kind` is not
# supplied to `match_head_template` -- a simple, cheap classifier over
# the head's own box, never a guess about ledgers.
HOLLOW_INNER_INK_MAX_FRACTION = 0.45


def _ellipse_mask(h: int, w: int, cx: float, cy: float, rx: float, ry: float
                  ) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w]
    return (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) <= 1.0


# The oval footprint, fixed once at canonical scale -- every template's
# "head" mask, regardless of kind/variant.
_HEAD_RX = STANDARD_HEAD_WIDTH_SPACES / 2.0 * CANONICAL_PX_PER_SPACE
_HEAD_RY = STANDARD_HEAD_HEIGHT_SPACES / 2.0 * CANONICAL_PX_PER_SPACE
HEAD_MASK = _ellipse_mask(CANONICAL_H, CANONICAL_W, CANONICAL_W / 2.0,
                          CANONICAL_H / 2.0, _HEAD_RX, _HEAD_RY)


def _line_row_band(center_row: float) -> np.ndarray:
    """A horizontal band `LEDGER_BAND_MAX_SPACES` tall at `center_row`,
    covering ONLY the STUB columns past the oval's own half-width on each
    side (never the columns over the oval's own body) -- the "line row"
    part of an on/space template's own score mask.

    ⚠️ Why the oval's own columns are EXCLUDED, not just de-emphasised: a
    FILLED notehead is solid ink across its own entire footprint, ledger
    or no ledger -- a band that also scores the oval's own interior
    cannot tell "a line crosses here" from "this is simply the inside of
    a filled head", so every filled far head measured a strong false
    `on_line` match regardless of where the real ledger sat (FINDINGS
    "lane-ledger-template", measured directly: the on-line band scored
    0.70 against a head with NO ledger anywhere near its own middle, from
    the oval's own body alone). The diagnostic signal a ledger gives is
    its reach PAST the head -- the same STUB convention
    `ledger_grid.head_middle_rung_evidence` already uses -- so this mask
    only ever covers that reach, both sides, same as a real stub probe."""
    mask = np.zeros((CANONICAL_H, CANONICAL_W), dtype=bool)
    half_h = max(1.0, LEDGER_BAND_MAX_SPACES / 2.0 * CANONICAL_PX_PER_SPACE)
    r0 = max(0, int(round(center_row - half_h)))
    r1 = min(CANONICAL_H, int(round(center_row + half_h)) + 1)
    reach = LEDGER_REACH_HEAD_WIDTHS * STANDARD_HEAD_WIDTH_SPACES * CANONICAL_PX_PER_SPACE
    cx = CANONICAL_W / 2.0
    left0 = max(0, int(round(cx - _HEAD_RX - reach)))
    left1 = max(0, int(round(cx - _HEAD_RX)))
    right0 = min(CANONICAL_W, int(round(cx + _HEAD_RX)))
    right1 = min(CANONICAL_W, int(round(cx + _HEAD_RX + reach)) + 1)
    mask[r0:r1, left0:left1] = True
    mask[r0:r1, right0:right1] = True
    return mask


# ON_LINE: one band at the window's own vertical centre (a ledger
# straight through the head's own middle). IN_SPACE: two bands, touching
# the window's own top and bottom edges (the ledgers bounding the space
# the head sits in, per the task brief's own template (b) description) --
# kept as SEPARATE components, never OR'd into one mask: a real far head
# routinely has only the NEAREST bounding ledger in view (the further one
# may be a half-step beyond where this window even looks), so the
# in-space line EVIDENCE is "does EITHER bounding band match", the same
# one-side-is-enough precedent `ledger_grid.head_middle_rung_evidence`
# already uses for a through-rung's own two stubs.
ON_LINE_LINE_MASK = _line_row_band(CANONICAL_H / 2.0)
_IN_SPACE_TOP_BAND = _line_row_band(LEDGER_BAND_MAX_SPACES / 2.0 * CANONICAL_PX_PER_SPACE)
_IN_SPACE_BOTTOM_BAND = _line_row_band(
    CANONICAL_H - LEDGER_BAND_MAX_SPACES / 2.0 * CANONICAL_PX_PER_SPACE)
IN_SPACE_LINE_MASK = _IN_SPACE_TOP_BAND | _IN_SPACE_BOTTOM_BAND

LINE_MASK_COMPONENTS: Dict[str, List[np.ndarray]] = {
    "on_line": [ON_LINE_LINE_MASK],
    "in_space": [_IN_SPACE_TOP_BAND, _IN_SPACE_BOTTOM_BAND],
    "raw": [],
}
# Kept for any caller that wants the full scored footprint (drawing, etc.)
SCORE_MASKS: Dict[str, np.ndarray] = {
    "on_line": HEAD_MASK | ON_LINE_LINE_MASK,
    "in_space": HEAD_MASK | IN_SPACE_LINE_MASK,
    "raw": HEAD_MASK,
}


@dataclass
class Template:
    img: np.ndarray       # canonical (H, W) float ink-fraction average, 0..1
    mask: np.ndarray      # canonical (H, W) bool -- HEAD_MASK | line mask
    line_mask_components: List[np.ndarray]  # the line band(s), SEPARATE
    n: int                # exemplar count that built this template
    kind: str             # "filled" | "hollow"
    variant: str          # "on_line" | "in_space" | "raw"


def classify_kind_from_class_name(class_name: Optional[str]) -> Optional[str]:
    """Detector class name -> `"filled"`/`"hollow"`/`None`. Used only for
    CLEAN, on-staff exemplar heads -- the class is reliable there; it is
    NOT trusted for the far/ambiguous heads this module exists to help
    read (those go through `_classify_kind_from_ink`)."""
    if not class_name:
        return None
    if "Black" in class_name:
        return "filled"
    if "Half" in class_name or "Whole" in class_name:
        return "hollow"
    return None


def _extract_canonical_patch(gray: np.ndarray, cx: float, cy: float,
                             spacing: float) -> Optional[np.ndarray]:
    """Crop the LOCAL window around `(cx, cy)` at `spacing`'s own native
    pixel scale, binarise (Otsu), resample to the fixed canonical grid.
    `None` where the window would be clipped by the page edge (never a
    template built from a truncated patch)."""
    if cv2 is None or gray is None or spacing is None or spacing <= 0:
        return None
    head_w = STANDARD_HEAD_WIDTH_SPACES * spacing
    head_h = STANDARD_HEAD_HEIGHT_SPACES * spacing
    half_w = WINDOW_HALF_WIDTH_HEAD_WIDTHS * head_w
    half_h = (WINDOW_HALF_HEIGHT_HEAD_HEIGHTS * head_h
              + WINDOW_HALF_HEIGHT_EXTRA_SPACES * spacing)
    h, w = gray.shape
    x0, x1 = cx - half_w, cx + half_w
    y0, y1 = cy - half_h, cy + half_h
    if x0 < 0 or y0 < 0 or x1 > w or y1 > h or x1 <= x0 or y1 <= y0:
        return None
    ix0, ix1 = int(round(x0)), int(round(x1))
    iy0, iy1 = int(round(y0)), int(round(y1))
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    window = gray[iy0:iy1, ix0:ix1]
    thr = _otsu_threshold(window)
    ink = (window <= thr).astype(np.float32)
    patch = cv2.resize(ink, (CANONICAL_W, CANONICAL_H), interpolation=cv2.INTER_AREA)
    return patch


def build_templates(
    gray: np.ndarray,
    exemplars: Sequence[Dict],
) -> Tuple[Dict[Tuple[str, str], Template], Dict[str, int]]:
    """Build templates from a page's own CLEAN exemplar heads.

    Each item of `exemplars` is a dict:
      `box` (x0,y0,x1,y1, page px), `spacing` (local staff spacing, px),
      `class_name` (detector class, e.g. "noteheadBlackOnLine"),
      `position` (int 0..8, on-staff staff position -- even=on a line,
      odd=in a space), `cell_key` (grouping key -- heads sharing one are
      a chord and are ALL excluded), `isolated` (bool -- caller has
      already checked: no other box overlaps it, and it is not near a
      beam/slur/tie/flag box).

    Returns `(templates, counts)` -- `counts["{kind}_{variant}"]` is the
    number of exemplars that built that template (reported, never
    hidden); a (kind, variant) with fewer than `MIN_TEMPLATE_EXEMPLARS`
    is NOT included in `templates` at all."""
    cell_counts: Dict[str, int] = {}
    for e in exemplars:
        cell_counts[e["cell_key"]] = cell_counts.get(e["cell_key"], 0) + 1

    sums: Dict[Tuple[str, str], np.ndarray] = {}
    counts: Dict[Tuple[str, str], int] = {}

    for e in exemplars:
        if not e.get("isolated", False):
            continue
        if cell_counts.get(e["cell_key"], 0) != 1:
            continue  # chord / multiple heads in this cell -- excluded
        kind = classify_kind_from_class_name(e.get("class_name"))
        if kind is None:
            continue
        pos = e.get("position")
        if pos is None:
            continue
        variant = "on_line" if (int(pos) % 2 == 0) else "in_space"
        x0, y0, x1, y1 = e["box"]
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        patch = _extract_canonical_patch(gray, cx, cy, e["spacing"])
        if patch is None:
            continue
        for key in ((kind, variant), (kind, "raw")):
            if key not in sums:
                sums[key] = np.zeros((CANONICAL_H, CANONICAL_W), dtype=np.float64)
                counts[key] = 0
            sums[key] += patch
            counts[key] += 1

    templates: Dict[Tuple[str, str], Template] = {}
    report: Dict[str, int] = {}
    for key, total in sums.items():
        kind, variant = key
        n = counts[key]
        report[f"{kind}_{variant}"] = n
        if n < MIN_TEMPLATE_EXEMPLARS:
            continue
        img = (total / n).astype(np.float32)
        templates[key] = Template(
            img=img, mask=SCORE_MASKS[variant],
            line_mask_components=LINE_MASK_COMPONENTS[variant],
            n=n, kind=kind, variant=variant,
        )
    return templates, report


# ─────────────────────────────────────────────────────────────────────────
# GEOMETRY templates (2026-10-02, Sean: "try the geometry version first")
# -- drawn directly from measured ellipse geometry rather than averaged
# from real exemplars. Sizes are the task brief's OWN stated numbers
# (outer ellipse 1.3 sp wide x 1.0 sp tall), which differ from ROADMAP
# 2.39's `STANDARD_HEAD_WIDTH_SPACES`/`_HEIGHT_SPACES` (1.4 x 1.1) --
# kept SEPARATE on purpose (`GEOM_HEAD_WIDTH_SPACES`/`_HEIGHT_SPACES`),
# never silently substituted for the exemplar path's own constants.
#
# Tilt is NEVER assumed here -- `measure_head_tilt.py` measures it from
# the real page first (CLAUDE.md rule 7); this module only draws whatever
# angle it is given. Calibration (`_draw_angle_deg`): empirically,
# `cv2.ellipse`'s own `angle` parameter of +N degrees measures back as
# `-N` through this module's own "up-and-to-the-right from horizontal"
# convention (`measure_head_tilt._angle_up_right`) -- verified by drawing
# a known ellipse and re-fitting it before relying on this anywhere.
# ─────────────────────────────────────────────────────────────────────────

GEOM_HEAD_WIDTH_SPACES = 1.3
GEOM_HEAD_HEIGHT_SPACES = 1.0


def _draw_angle_deg(up_right_tilt_deg: float) -> float:
    """Up-right-from-horizontal tilt -> the `cv2.ellipse` `angle` to pass
    to draw it (empirically calibrated, see module docstring above)."""
    return -up_right_tilt_deg


def build_geometry_template(
    kind: str, variant: str, outer_tilt_deg: float,
    slit_tilt_deg: Optional[float], line_thickness_px: float,
    slit_width_ratio: float = 0.55, slit_height_ratio: float = 0.70,
) -> Template:
    """Draw ONE template directly from geometry, at the canonical grid's
    own fixed scale (`CANONICAL_PX_PER_SPACE`) -- no real exemplar ink
    involved. `outer_tilt_deg`/`slit_tilt_deg` are MEASURED values from
    `measure_head_tilt.py`, never assumed; `line_thickness_px` is the
    page's own measured staff-line thickness, scaled to canonical.

    `variant`: `"on_line"` draws a line of `line_thickness_px` (canonical
    scale) through the window's own vertical centre, extending 0.5 sp
    past the outer ellipse on both sides; `"in_space"` draws two such
    lines touching the window's own top and bottom edges; `"raw"` draws
    the head alone. `kind="filled"` fills the outer ellipse solid;
    `"hollow"` draws a ring (outer ellipse minus an inner slit ellipse at
    `slit_tilt_deg`, sized `slit_width_ratio`/`slit_height_ratio` of the
    OUTER ellipse's own axes -- both MEASURED, `measure_head_tilt.py`'s
    own slit-vs-outer-axis ratio, never the old hardcoded 0.55/0.70
    default (manager review 2026-10-02: the hollow template must be
    "mostly ink" with a narrow, slanted slit, not a thin ring around a
    big empty centre))."""
    canvas = np.zeros((CANONICAL_H, CANONICAL_W), dtype=np.float32)
    cx, cy = CANONICAL_W / 2.0, CANONICAL_H / 2.0
    outer_w = GEOM_HEAD_WIDTH_SPACES * CANONICAL_PX_PER_SPACE
    outer_h = GEOM_HEAD_HEIGHT_SPACES * CANONICAL_PX_PER_SPACE
    axes = (int(round(outer_w / 2.0)), int(round(outer_h / 2.0)))
    angle = _draw_angle_deg(outer_tilt_deg)

    mask_u8 = np.zeros((CANONICAL_H, CANONICAL_W), dtype=np.uint8)
    cv2.ellipse(mask_u8, (int(round(cx)), int(round(cy))), axes, angle,
               0, 360, 255, -1)
    if kind == "hollow":
        slit_angle = _draw_angle_deg(slit_tilt_deg if slit_tilt_deg is not None
                                     else outer_tilt_deg)
        slit_axes = (max(1, int(round(axes[0] * slit_width_ratio))),
                    max(1, int(round(axes[1] * slit_height_ratio))))
        cv2.ellipse(mask_u8, (int(round(cx)), int(round(cy))), slit_axes,
                   slit_angle, 0, 360, 0, -1)
    canvas[mask_u8 > 0] = 1.0

    if variant in ("on_line", "in_space"):
        half_t = max(1, int(round(line_thickness_px / 2.0)))
        reach = int(round((outer_w / 2.0) + 0.5 * CANONICAL_PX_PER_SPACE))
        lx0, lx1 = max(0, int(round(cx - reach))), min(CANONICAL_W, int(round(cx + reach)) + 1)
        if variant == "on_line":
            r0 = max(0, int(round(cy - half_t)))
            r1 = min(CANONICAL_H, int(round(cy + half_t)) + 1)
            canvas[r0:r1, lx0:lx1] = 1.0
        else:
            for row_center in (half_t, CANONICAL_H - half_t):
                r0 = max(0, int(round(row_center - half_t)))
                r1 = min(CANONICAL_H, int(round(row_center + half_t)) + 1)
                canvas[r0:r1, lx0:lx1] = 1.0

    return Template(
        img=canvas, mask=SCORE_MASKS[variant],
        line_mask_components=LINE_MASK_COMPONENTS[variant],
        n=0, kind=kind, variant=variant,
    )


def build_geometry_templates(
    outer_tilt_deg: Dict[str, float], slit_tilt_deg: Dict[str, float],
    line_thickness_px: float,
    slit_ratio: Optional[Dict[str, Tuple[float, float]]] = None,
) -> Dict[Tuple[str, str], Template]:
    """Every `(kind, variant)` geometry template, `outer_tilt_deg`/
    `slit_tilt_deg`/`slit_ratio` keyed by `kind` (`"filled"`/`"hollow"`)
    -- each drawn fresh, never averaged (`n=0`, since no exemplar built
    it). `slit_ratio[kind]` is `(width_ratio, height_ratio)`, MEASURED
    (`measure_head_tilt.py`'s own slit-vs-outer axis report) -- omitted
    keys fall back to `build_geometry_template`'s own default."""
    out: Dict[Tuple[str, str], Template] = {}
    for kind in ("filled", "hollow"):
        for variant in ("on_line", "in_space", "raw"):
            kwargs = {}
            if slit_ratio and kind in slit_ratio:
                kwargs["slit_width_ratio"] = slit_ratio[kind][0]
                kwargs["slit_height_ratio"] = slit_ratio[kind][1]
            out[(kind, variant)] = build_geometry_template(
                kind, variant, outer_tilt_deg.get(kind, 0.0),
                slit_tilt_deg.get(kind), line_thickness_px, **kwargs,
            )
    return out


def _classify_kind_from_ink(gray: np.ndarray, head_box: Tuple[float, float, float, float]
                            ) -> str:
    """Cheap filled/hollow classifier over the head's OWN box -- a hollow
    head's inner ellipse is mostly white, a filled head's is mostly ink.
    Never guesses a ledger; only distinguishes notehead SHAPE, which the
    detector's own class already answers reliably for CLEAN heads (this
    is only used for far/contested heads where that class is exactly
    what is in question elsewhere in the pipeline, never here)."""
    x0, y0, x1, y1 = head_box
    h, w = gray.shape
    ix0, ix1 = max(0, int(x0)), min(w, int(x1) + 1)
    iy0, iy1 = max(0, int(y0)), min(h, int(y1) + 1)
    if ix1 <= ix0 or iy1 <= iy0:
        return "filled"
    window = gray[iy0:iy1, ix0:ix1]
    thr = _otsu_threshold(window)
    ink = window <= thr
    bh, bw = ink.shape
    mask = _ellipse_mask(bh, bw, bw / 2.0, bh / 2.0, bw * 0.3, bh * 0.3)
    if not mask.any():
        return "filled"
    frac = float(ink[mask].mean())
    return "hollow" if frac < HOLLOW_INNER_INK_MAX_FRACTION else "filled"


def _masked_ncc(template_img: np.ndarray, candidate_img: np.ndarray,
                mask: np.ndarray) -> Optional[float]:
    """Normalised correlation, restricted to `mask`. `None` where the mask
    selects nothing (never scored)."""
    if not mask.any():
        return None
    t = template_img[mask].astype(np.float64)
    c = candidate_img[mask].astype(np.float64)
    t = t - t.mean()
    c = c - c.mean()
    denom = float(np.sqrt((t * t).sum() * (c * c).sum()))
    if denom <= 0:
        return 0.0
    return float((t * c).sum() / denom)


# Weight on "does this look like a real head at all" (the HEAD mask,
# shared by every variant) vs "does the on/space-defining LINE evidence
# match" (the line mask ALONE) -- scored SEPARATELY, never pooled into
# one combined mask (pooling drowns the much smaller line band in the
# much larger head region's own correlation, measured near-zero margins
# on real on/space contrasts during this lane's own build). The HEAD term
# is weighted HIGHER: it is what anchors the match to the real head's own
# position at all -- without it dominant, a template can "cheat" by
# sliding the window to wherever in the +/-1.5-space range some OTHER
# line happens to sit, regardless of whether the head's own ink is still
# centred there (measured directly: an isolated single ledger a half-step
# off the head's own true centre otherwise out-scored the correctly
# centred match, FINDINGS "lane-ledger-template").
HEAD_TERM_WEIGHT = 0.75
LINE_TERM_WEIGHT = 0.25

# A small, explicit penalty against shifting the match window far from the
# head's own BOX centre (never zero -- the box is already decent evidence
# of where the head is) -- in correlation units per staff space shifted,
# subtracted from the combined score before comparing shifts/variants.
# Same purpose as the HEAD-term weighting above: stops a strong but
# off-centre line from winning purely by relocating the whole window.
SHIFT_PENALTY_PER_SPACE = 0.5


def _template_score(tmpl: Template, candidate: np.ndarray) -> Optional[float]:
    head_score = _masked_ncc(tmpl.img, candidate, HEAD_MASK)
    if head_score is None:
        return None
    if not tmpl.line_mask_components:
        return head_score
    # Either bounding band matching is enough (one-side-is-enough
    # precedent) -- take the BEST component, never require all of them.
    comp_scores = [
        s for s in (_masked_ncc(tmpl.img, candidate, m)
                    for m in tmpl.line_mask_components)
        if s is not None
    ]
    if not comp_scores:
        return head_score
    line_score = max(comp_scores)
    return HEAD_TERM_WEIGHT * head_score + LINE_TERM_WEIGHT * line_score


def match_head_template(
    img_gray: Optional[np.ndarray],
    head_box: Optional[Tuple[float, float, float, float]],
    spacing: Optional[float],
    templates: Optional[Dict[Tuple[str, str], Template]],
    exclude_boxes: Optional[Sequence[Tuple[float, float, float, float]]] = None,
    stem_box: Optional[Tuple[float, float, float, float]] = None,
    kind: Optional[str] = None,
) -> Optional[Dict]:
    """Slide the `on_line` and `in_space` templates of `kind` (classified
    from the ink where not given) vertically over the real page ink at
    the head's own x, `SLIDE_RANGE_SPACES` either way in `SLIDE_STEP_PX`
    steps. Returns `None` where nothing can be matched at all (no image,
    no templates for this kind); otherwise a dict:

      `kind`, `best_variant` ("on_line"|"in_space"), `center_y` (the
      best shift's own implied head-centre y), `score_on`, `score_space`
      (best correlation for each variant across every shift), `margin`
      (`|score_on - score_space|`), `undecided` (margin below
      `MARGIN_UNDECIDED_THRESHOLD`)."""
    if (cv2 is None or img_gray is None or head_box is None or templates is None
            or spacing is None or spacing <= 0):
        return None
    x0, y0, x1, y1 = head_box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    use_kind = kind or _classify_kind_from_ink(img_gray, head_box)

    tmpl_on = templates.get((use_kind, "on_line"))
    tmpl_space = templates.get((use_kind, "in_space"))
    if tmpl_on is None and tmpl_space is None:
        return dict(kind=use_kind, best_variant=None, center_y=cy,
                    score_on=None, score_space=None, margin=0.0,
                    undecided=True, reason="no_templates_for_kind")

    head_w = STANDARD_HEAD_WIDTH_SPACES * spacing
    head_h = STANDARD_HEAD_HEIGHT_SPACES * spacing
    half_w = WINDOW_HALF_WIDTH_HEAD_WIDTHS * head_w
    half_h = (WINDOW_HALF_HEIGHT_HEAD_HEIGHTS * head_h
              + WINDOW_HALF_HEIGHT_EXTRA_SPACES * spacing)
    slide_px = int(round(SLIDE_RANGE_SPACES * spacing))
    h, w = img_gray.shape

    ix0 = max(0, int(round(cx - half_w)))
    ix1 = min(w, int(round(cx + half_w)))
    iy0 = max(0, int(round(cy - half_h - slide_px)))
    iy1 = min(h, int(round(cy + half_h + slide_px)))
    if ix1 <= ix0 or iy1 <= iy0:
        return dict(kind=use_kind, best_variant=None, center_y=cy,
                    score_on=None, score_space=None, margin=0.0,
                    undecided=True, reason="window_off_page")

    band = img_gray[iy0:iy1, ix0:ix1]
    thr = _otsu_threshold(band)
    ink = (band <= thr).astype(np.float32)
    if exclude_boxes:
        ink_bool = ink > 0.5
        ink_bool = _blank_excluded_boxes(ink_bool, exclude_boxes, ix0, iy0)
        ink = ink_bool.astype(np.float32)
    stem_h, stem_w = ink.shape
    ink_bool = _mask_stem_columns(ink > 0.5, spacing, stem_box=stem_box, wx0=ix0)
    ink = ink_bool.astype(np.float32)

    lx0, lx1 = int(round(cx - half_w)) - ix0, int(round(cx + half_w)) - ix0

    def _best_for(tmpl: Optional[Template]) -> Tuple[Optional[float], Optional[int]]:
        if tmpl is None:
            return None, None
        best_score, best_shift = None, None
        for shift in range(-slide_px, slide_px + 1, SLIDE_STEP_PX):
            win_cy = cy + shift
            ly0 = int(round(win_cy - half_h)) - iy0
            ly1 = int(round(win_cy + half_h)) - iy0
            if ly0 < 0 or ly1 > ink.shape[0] or lx0 < 0 or lx1 > ink.shape[1] \
                    or ly1 <= ly0 or lx1 <= lx0:
                continue
            candidate = ink[ly0:ly1, lx0:lx1]
            if candidate.shape[0] != CANONICAL_H or candidate.shape[1] != CANONICAL_W:
                candidate = cv2.resize(candidate, (CANONICAL_W, CANONICAL_H),
                                       interpolation=cv2.INTER_AREA)
            score = _template_score(tmpl, candidate)
            if score is None:
                continue
            score -= SHIFT_PENALTY_PER_SPACE * (abs(shift) / spacing)
            if best_score is None or score > best_score:
                best_score, best_shift = score, shift
        return best_score, best_shift

    score_on, shift_on = _best_for(tmpl_on)
    score_space, shift_space = _best_for(tmpl_space)

    candidates = [(v, s) for v, s in
                  (("on_line", score_on), ("in_space", score_space)) if s is not None]
    if not candidates:
        return dict(kind=use_kind, best_variant=None, center_y=cy,
                    score_on=score_on, score_space=score_space, margin=0.0,
                    undecided=True, reason="no_valid_shift")
    best_variant, best_score = max(candidates, key=lambda vs: vs[1])
    best_shift = shift_on if best_variant == "on_line" else shift_space
    other_score = score_space if best_variant == "on_line" else score_on
    margin = (best_score - other_score) if other_score is not None else best_score
    undecided = margin < MARGIN_UNDECIDED_THRESHOLD

    return dict(
        kind=use_kind, best_variant=best_variant,
        center_y=cy + (best_shift or 0),
        score_on=score_on, score_space=score_space, margin=float(margin),
        undecided=bool(undecided), reason="matched",
    )


def decide_head_position_from_template(
    img_gray: np.ndarray,
    head_box: Tuple[float, float, float, float],
    spacing: float,
    templates: Optional[Dict[Tuple[str, str], Template]],
    exclude_boxes: Optional[Sequence[Tuple[float, float, float, float]]] = None,
    stem_box: Optional[Tuple[float, float, float, float]] = None,
    kind: Optional[str] = None,
) -> Dict:
    """Task-brief step 3: decide ON/SPACE from the matched template,
    never a guess below the stated margin. Returns `{"decision":
    "on"|"space"|None, "match": dict|None, "reason": str}`."""
    match = match_head_template(img_gray, head_box, spacing, templates,
                                exclude_boxes=exclude_boxes, stem_box=stem_box,
                                kind=kind)
    if match is None:
        return dict(decision=None, match=None, reason="no_match_possible")
    if match["undecided"] or match["best_variant"] is None:
        return dict(decision=None, match=match,
                    reason=f"margin {match['margin']:.3f} below "
                           f"{MARGIN_UNDECIDED_THRESHOLD} -- undecided")
    decision = "on" if match["best_variant"] == "on_line" else "space"
    return dict(decision=decision, match=match, reason=match["reason"])


def template_middle_rung_evidence(
    img_gray: Optional[np.ndarray],
    head_box: Optional[Tuple[float, float, float, float]],
    spacing: Optional[float],
    exclude_boxes: Optional[Sequence[Tuple[float, float, float, float]]] = None,
    templates: Optional[Dict[Tuple[str, str], Template]] = None,
    stem_box: Optional[Tuple[float, float, float, float]] = None,
    kind: Optional[str] = None,
) -> bool:
    """Drop-in replacement for `ledger_grid.head_middle_rung_evidence` /
    `ledger_shape_trace.shape_trace_middle_rung_evidence` -- the SAME
    4-positional-argument contract `derive_far_head_step` calls with;
    `templates`/`stem_box`/`kind` are extras a caller binds per head via
    `functools.partial` or a closure, exactly like `staff_lines` did for
    the shape trace. Same "no evidence possible -> False" contract
    (CLAUDE.md rule 8) -- including a margin below
    `MARGIN_UNDECIDED_THRESHOLD`, which is UNDECIDED, never a guessed
    "yes, a line"."""
    if templates is None or img_gray is None or head_box is None \
            or spacing is None or spacing <= 0:
        return False
    result = decide_head_position_from_template(
        img_gray, head_box, spacing, templates,
        exclude_boxes=exclude_boxes, stem_box=stem_box, kind=kind,
    )
    return result["decision"] == "on"
