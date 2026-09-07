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
        then destroyed. **Consumer:** `_drop_close_outliers`, and any future
        confidence on the measure-count check.

        ⚠️⚠️ **THIS NUMBER IS NOT COMPARABLE ACROSS PAGES, AND ITS SIGN CAN
        INVERT. `barlines_cross_gaps` IS THE DISCRIMINATOR — never
        `connectivity is None`.** Measured 2026-09-06 on the two verification
        pages of this change:

        ==========================  ======  ==================  ==============
        page                        n       connectivity        culled by >=0.4
        ==========================  ======  ==================  ==============
        Beethoven 5 scan (Litolff)  17      0.818 - 1.000        0 of 17
        Brahms 1 engraved (LilyPond) 8      1.0 x1, **0.0 x7**   **7 of 8**
        ==========================  ======  ==================  ==============

        Every one of those eight Brahms barlines is REAL and carries a
        unanimous **21 of 21** votes. The page is an open score — LilyPond
        bars per staff — so the gap ink a conductor's page shows simply is not
        printed, and `barlines_cross_gaps` came back False, which is exactly
        why the 0.4 filter was not allowed to run there. A consumer that
        ranked columns by `connectivity` across both pages would throw away
        seven of eight unanimous barlines on one of them.

        ⚠️ **On `barlines_cross_gaps=False` rows the value is usually a REAL
        NUMBER that gated nothing** — it was computed for the open-score TEST
        and then not used — so a real `0.0` here is indistinguishable by value
        alone from "measured and terrible". Read the regime first.

        ⚠️ Separately, **`None` is not zero either**: it means the number was
        never computed at all, which happens on the 1-staff small-system path
        (`connectivity_of` is empty below two staves). Both hazards point the
        same way — the value alone never tells you what it is worth.

    ``span_ink``
        `_spans_system`: the weakest band of ink along the fitted line from
        the top of the system's first staff to the bottom of its last. Only
        computed on 1-2 staff (braced piano) systems, where it is the rescue
        that separates a real barline (1.00 across the brace gap) from a
        fugue's long stem (0.00). `None` everywhere else, for the same reason
        as above: not measured, not zero.

        ⚠️ **COVERAGE LIMIT, recorded rather than papered over:** neither
        verification page exercises this field — both are >=3-staff systems,
        so it is `None` on 0 of 17 and 0 of 8. It is covered synthetically
        (`test_span_rescue_records_the_span_score_it_was_rescued_by`, which
        goes red when the population is removed) and by construction it is the
        only value the small-system rescue can accept on, but **no real page
        has yet been measured through it.** One braced-piano page would close
        that.

    ``accept_prong``
        WHICH of the five acceptance rules admitted this column —
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
    """A PageImage annotated with detected staves and barlines.

    ``deletion_counts`` is a census of what Phase 1 THREW AWAY on this page,
    keyed by site and reason. An audit of this area on 2026-09-06 found that
    most of its deletion sites wrote no counter at all — a candidate staff, a
    candidate barline or a measure cell would vanish with nothing recording
    that it had ever existed, so the only deletions anyone could reason about
    were the handful someone had already gone looking at. Every entry is a
    reason, not a total: `n_barline_components_dropped_too_wide` and
    `n_barline_components_dropped_not_skinny` are separate keys because they
    are separate mistakes to make.

    ⚠️ **Diagnostic only, and no consumer reads it today.** It is written by
    `staff_detector.detect_staves`, `measure_extractor.detect_barlines`,
    `extract_measures` and `resegment_fused_measures`, all of which mutate the
    page they were handed. **Who could consume it:** a benchmark asking why a
    page lost a staff (`n_staves_dropped_as_body_text` is a real regression
    shape — see `_line_ink_runs_per_space`), the measure-count consistency
    check wanting to know whether a short staff is short because a barline was
    dropped as a close outlier, and `transcribe`'s per-page summary, which
    already serialises four counters of exactly this shape
    (`n_clipped_notehead_fragments_dropped` and friends) and would only need
    to copy this dict across. ⚠️ It is NOT serialised yet: `transcribe.py`
    writes no `PageWithStaves` field into the result JSON, and that file's
    owner is not this file's owner.

    ⚠️ A key is ABSENT when its site never fired on this page, which is not
    the same as the site not existing. Read with `.get(key, 0)`.

    **The size of the census, defined so it is reproducible from the tree**
    (a bare count of "sites" is not — it depends on what you call one):

        python3 - <<'EOF'
        import ast
        for p in ("tools/omr/measure_extractor.py", "tools/omr/staff_detector.py"):
            t = ast.parse(open(p).read())
            calls = [n for n in ast.walk(t) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Name) and n.func.id == "_bump"]
            print(p, len(calls), "call sites")
        EOF

    As of 2026-09-06 that reports **16 + 10 = 26 `_bump` call sites** writing
    **27 distinct keys** (25 named at the site, plus the one key
    `_build_measure_cell` takes from its caller, which resolves to two).

    ⚠️ **26 call sites is NOT 26 deletions**, and the earlier figure of "19
    deletion sites" quoted in this branch's first census commit was counting
    something narrower without saying so. Three groups make up the difference,
    and they are worth separating because they answer different questions:

    * **Deletions** — a candidate staff, barline or measure cell that existed
      and was discarded. `n_*_dropped_*`, `n_*_rejected_*`.
    * **Exclusions** — never a candidate in the first place, by design: the
      `n_one_line_staves_excluded_from_*` pair. A percussion rule is kept out
      of the barline vote deliberately; counting it says "this page has
      percussion", not "this page lost something".
    * **Not a deletion at all** — `n_measure_tails_absorbed`, where the tail is
      folded into the previous measure precisely SO THAT nothing is lost. It is
      here because it removes a boundary, and a page with many of them has a
      problem at its right edge.

    Prefer the reproducible 26/27 over any hand-counted total.
    """

    page: PageImage
    staves: list[Staff]
    barlines: list[Barline] = field(default_factory=list)
    deletion_counts: dict[str, int] = field(default_factory=dict)

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
    # THE PAD THIS CELL WAS CUT WITH, in staff spaces, above and below —
    # `measure_extractor._build_measure_cell`'s own `grown()` values, not the
    # module constants it started from.
    #
    # ⚠️ PER-CELL, NOT PER-MODULE, and the difference is not cosmetic. The pad
    # starts at `PAD_ABOVE_STAFF_LINES` / `PAD_BELOW_STAFF_LINES` and GROWS to
    # `PAD_MAX_STAFF_LINES` on whichever side the neighbouring staff is far
    # enough away — so on one ordinary page the top staff is cut at 6 above and
    # 4 below while its neighbour below is cut at 4 on both. Reading the module
    # constant would be wrong exactly where the growth happens, which is the
    # case the growth exists for (CLAUDE.md: "the cell pad is 4 spaces or 6,
    # never in between").
    #
    # WHY IT IS RECORDED. Every saved label box lives in the cell's CANONICAL
    # frame, and a cell re-cut at a different pad is not a slightly different
    # picture — it is the same music at a different scale, with every box in
    # the batch landing somewhere else and nothing downstream saying so. The
    # labeling cutter (`annotate/select_cells_orchestral`) monkey-patches those
    # module constants to 5.0, so a labeled batch and a pipeline run disagree
    # about the frame, and the fact was never written down: today
    # `annotate/recut_cells.choose_mode_and_cut` DERIVES which pad was used, by
    # cutting the page under each candidate mode and keeping the one whose
    # output reproduces the manifest's recorded width, height and canonical
    # staff-line ys. That derivation exists only because this field did not.
    #
    # ⚠️ IT IS NOT YET REPLACED, deliberately. `recut_cells`' abort-on-frame-
    # mismatch is a safety property over irreplaceable human verdicts, and
    # every batch cut before this field existed has a manifest that records no
    # pad at all — so the derivation is still the only thing that can read
    # those. This is a record, not a decision.
    #
    # ⚠️ The pad the cut ASKED for. `y0`/`y1` are additionally clamped to the
    # page, so a staff near the paper edge got less than this; what it actually
    # got is `bbox_page_px` against the staff's own line_ys. None on a cell
    # built by hand (most test fixtures) rather than cut from a page.
    pad_above_staff_lines: float | None = None
    pad_below_staff_lines: float | None = None

    @property
    def width(self) -> int:
        return self.image.shape[1]

    @property
    def height(self) -> int:
        return self.image.shape[0]
