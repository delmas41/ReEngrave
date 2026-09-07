"""Shared types for the OMR pipeline. Module boundaries pass these around so
each step has a clear input/output contract.

Phase 1 (image foundation):
    PDF path → PageImage[] → PageWithStaves[] → MeasureCell[]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class PageImage:
    """One rendered page from a PDF. Image is a numpy array, dtype uint8.
    `binary` is the Sauvola-binarized image (0=ink, 255=paper)."""

    pdf_path: Path
    page_index: int          # 0-based
    dpi: int
    rgb: np.ndarray          # H×W×3 uint8 — original render
    binary: np.ndarray       # H×W uint8 — binarized (255=paper, 0=ink)
    skew_correction_deg: float = 0.0

    @property
    def height(self) -> int:
        return self.rgb.shape[0]

    @property
    def width(self) -> int:
        return self.rgb.shape[1]


@dataclass
class Staff:
    """One staff on a page, in page-pixel coordinates — five lines, or the
    single rule of a percussion part.

    `line_ys` is the staff as the rest of the pipeline models it: five ideal
    horizontal lines at integer rows. `line_thickness_px` and `line_wander_px`
    record how far the printed staff departs from that model — how much ink
    each line actually occupies, and how far it strays from its nominal row.
    Both are measurements of what staff-line REMOVAL destroys, kept because
    the erased image can no longer answer either question, and because on the
    prints that matter the departure is large: a line 0.3 staff spaces thick
    is not a line, it is a band, and treating it as a row is what leaves most
    of the staff behind.
    """

    page_index: int
    staff_index: int            # 0-based within the page
    line_ys: list[int]          # 5 y-coordinates, top → bottom
    x_start: int                # left edge of staff content (after clef margin)
    x_end: int                  # right edge
    system_index: int = 0       # which system this staff belongs to (group of staves played together)
    group_index: int = 0        # bracket group within the system (winds | brass | strings) — see system_grouping.py
    slot_index: int = -1        # stable part identity across systems/pages, -1 = unassigned — see slots.py
    # Measured, not assumed — see staff_detector.measure_line_geometry. None
    # when the lines were too faint or broken to trace.
    line_thickness_px: list[float] | None = None   # per line, top → bottom
    line_wander_px: float | None = None            # max departure from nominal
    # The page's staff spacing, carried for a staff that has none of its own.
    # A one-line percussion staff is a single printed rule: it has a position
    # but no internal pitch, and everything downstream that sizes a window,
    # a padding or a kernel does so in staff spaces. Without this the scale
    # would fall back to one pixel and every such window would be wrong.
    nominal_line_spacing_px: float | None = None

    @property
    def median_line_thickness_px(self) -> float | None:
        """One number for how heavily this staff is printed, or None if the
        lines were never traced."""
        if not self.line_thickness_px:
            return None
        return float(sorted(self.line_thickness_px)[len(self.line_thickness_px) // 2])

    @property
    def top_y(self) -> int:
        return self.line_ys[0]

    @property
    def bottom_y(self) -> int:
        return self.line_ys[-1]

    @property
    def span_px(self) -> int:
        """Pixel distance from top staff line to bottom staff line."""
        return self.bottom_y - self.top_y

    @property
    def line_spacing_px(self) -> float:
        """Average spacing between adjacent staff lines.

        A one-line staff has no adjacent lines, so it answers with the page's
        spacing (`nominal_line_spacing_px`) — the scale it was detected
        against — rather than with zero.
        """
        if len(self.line_ys) < 2:
            return float(self.nominal_line_spacing_px or 0.0)
        gaps = [self.line_ys[i + 1] - self.line_ys[i] for i in range(len(self.line_ys) - 1)]
        return sum(gaps) / len(gaps)


@dataclass
class Barline:
    """A vertical line dividing measures on a staff system.

    ⚠️ **The first five fields are all COORDINATES, and until 2026-09-06 they
    were the whole record.** `measure_extractor.detect_barlines` weighs a
    column on four independent pieces of evidence — how many staves voted for
    it, whether ink runs through the gaps between those staves, whether the
    column spans the system top to bottom, and which acceptance prong it
    finally cleared — and every one of them was discarded at this constructor.
    Downstream (`_measure_x_boundaries`, `_drop_close_outliers`,
    `resegment_fused_measures`, `transcribe`'s measure-count consistency
    check) then received a bare integer x and had to re-decide with nothing.
    `_drop_close_outliers`' own docstring is the confession: it picks which of
    an implausibly close pair is spurious by DEFAULTING TO THE LEFT ONE,
    because the evidence that could have told it was gone.

    The fields below are that evidence, recorded. They change no decision
    today, deliberately — recording is a separate act from consuming, and
    consuming is a change that has to be measured. What each is FOR:

    ``n_votes`` / ``n_staves_in_system`` / ``min_votes``
        How many of the system's five-line staves independently detected this
        column, out of how many, against the tiered threshold that was
        applied. **Consumer that wants it:** `_drop_close_outliers` — of two
        columns a bar-width apart, the one nine staves saw is the barline and
        the one two staves saw is a stem alignment; it currently cannot ask.
        Also `resegment_fused_measures`, which is looking for the barline the
        vote MISSED and would benefit from knowing how nearly it passed, and
        `transcribe._flag_measure_count_inconsistency`, which can only report
        that staves disagree and not which reading is thin.

    ``connectivity``
        `_intersystem_connectivity`: the fraction of inter-staff gaps this
        column is inked through, on the fitted (not vertical) line. A real
        systemic barline runs through the gaps; a chord-stem coincidence stops
        at each staff. Thresholded at 0.4 / 0.7 inside `detect_barlines` and
        then destroyed. ⚠️ **`None` is not zero** — it means the number was
        never computed for this column (open-score systems skip it, and so
        does the small-system path), and a consumer that reads `None` as 0.0
        would rank an open score's every barline as junk. **Consumer:**
        `_drop_close_outliers` again, and any future confidence on the
        measure-count check.

    ``span_ink``
        `_spans_system`: the weakest band of ink along the fitted line from
        the top of the system's first staff to the bottom of its last. Only
        computed on 1-2 staff (braced piano) systems, where it is the rescue
        that separates a real barline (1.00 across the brace gap) from a
        fugue's long stem (0.00). `None` everywhere else, for the same reason
        as above: not measured, not zero.

    ``accept_prong``
        WHICH of the four acceptance rules admitted this column —
        ``vote_small_system``, ``span_rescue_small_system``,
        ``vote_open_score``, ``vote_and_connectivity``, ``connectivity_rescue``.
        A rescued barline is a weaker claim than a voted one and nothing
        downstream could tell them apart. **Consumer:** a resegmentation or
        outlier pass that wants to prefer dropping a rescue over dropping a
        consensus.

    ``barlines_cross_gaps`` / ``choir_cue_c_override``
        The SYSTEM-level verdict, stamped onto each of its barlines because
        nothing else carries a system. `barlines_cross_gaps` False means the
        page was read as an OPEN SCORE (one staff per voice, barlines stopping
        at each staff), so connectivity was not allowed to filter and the
        votes stood alone — which is why `connectivity` is `None` on those
        rows. `choir_cue_c_override` True means `OMR_CHOIR_GROUPING`'s cue C
        flipped that verdict back (a rhythm-unison tutti whose aligned stems
        out-voted its own barlines). **Consumer:** anything that wants to know
        how much a column's evidence is worth before comparing two of them —
        the two verdicts are not commensurable, and today no consumer can even
        see which regime it is in.

    Every field defaults to `None`, so the four test/fixture construction
    sites and any future one keep working unannotated. ⚠️ An unannotated
    barline is indistinguishable from one whose evidence was genuinely not
    computed; that is why the fields are documented as *not measured* rather
    than as a floor.

    ⚠️⚠️ **TWO REACH LIMITS, both real, both stated here so the next reader
    does not discover them by writing a consumer that cannot see the data.**

    1. **`_drop_close_outliers` runs BEFORE this constructor.** It is handed
       `accepted`, a `list[int]`, and the `Barline`s are built from what it
       returns — so putting evidence on `Barline` does not reach it, and no
       amount of adding fields here will. What DOES reach it is the
       `evidence` map `detect_barlines` now builds alongside `accepted`,
       keyed by the same x; making that pass evidence-aware is a signature
       change plus a measured decision, and is deliberately not done here.
       The named consumers that DO receive `list[Barline]` and can read these
       fields today are `_measure_x_boundaries`, `extract_measures` and
       `resegment_fused_measures`.
    2. **Barlines are not serialised.** `transcribe` writes no barline record
       into the result JSON at all (`grep -n barline tools/omr/transcribe.py`
       finds prose and call sites, no emission), so a consumer outside the
       process — the measure-count consistency check's reporting, any
       benchmark — cannot see these fields until something writes them out.
       That is a change in `transcribe.py`, which this file's owner does not
       own.
    """

    page_index: int
    x: int                       # page-pixel x-coordinate
    y_top: int                   # top of barline (usually top staff of system)
    y_bottom: int                # bottom of barline
    system_index: int

    # ── Acceptance evidence (populated only by detect_barlines) ─────────
    n_votes: int | None = None
    n_staves_in_system: int | None = None
    min_votes: int | None = None
    connectivity: float | None = None
    span_ink: float | None = None
    accept_prong: str | None = None
    barlines_cross_gaps: bool | None = None
    choir_cue_c_override: bool | None = None


@dataclass
class PageWithStaves:
    """A PageImage annotated with detected staves and barlines."""

    page: PageImage
    staves: list[Staff]
    barlines: list[Barline] = field(default_factory=list)

    def staves_in_system(self, system_index: int) -> list[Staff]:
        return [s for s in self.staves if s.system_index == system_index]


@dataclass
class MeasureCell:
    """One (staff × measure) cell extracted from a page, normalized to a
    canonical maximum size for downstream symbol detection.

    The `image` is in CANONICAL coordinates (staff span = ~CANONICAL_STAFF_SPAN_PX),
    not page coordinates. The `bbox` records the original page-pixel location
    so downstream output can be mapped back to the source PDF for visualization.
    """

    page_index: int
    system_index: int
    staff_index: int            # within the page
    measure_index: int          # 0-based within the staff
    image: np.ndarray           # canonical-size cell (BGR or grayscale uint8)
    image_no_staff: np.ndarray | None  # same image with staff lines removed
    bbox_page_px: tuple[int, int, int, int]  # (x0, y0, x1, y1) in original page pixels
    staff_line_ys_canonical: list[int]       # staff line y-coords in CANONICAL image
    upscale_factor: float       # canonical_h / page_h_of_cell
    # How thick the printed staff lines are, in THIS cell's canonical pixels —
    # i.e. how much ink `image_no_staff` had to remove per line. None when the
    # staff's lines were never traced. See Staff.line_thickness_px.
    staff_line_thickness_canonical: float | None = None

    @property
    def width(self) -> int:
        return self.image.shape[1]

    @property
    def height(self) -> int:
        return self.image.shape[0]
