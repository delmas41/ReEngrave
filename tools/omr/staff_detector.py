"""Phase 1.2 — Staff line detection and system grouping.

Algorithm:
  1. Compute the horizontal projection profile of the binary image (sum of
     ink pixels per row). Staff line rows have high values because the line
     spans the full page width.
  2. Find peaks in the profile. Each peak is a candidate staff-line row.
  3. Cluster consecutive peaks into groups of 5 — one staff = 5 lines, the
     gaps between them are roughly equal.
  3b. Re-read the page as a comb at the spacing step 3 measured, which recovers
     staves whose lines were too lightly printed to clear step 2's gates, and
     drop groups whose spacing says they are one line borrowed from each of
     several staves rather than one staff.
  3c. Admit one-line percussion staves — a single printed rule between the
     page's staves, which step 3 cannot see because it only accepts five.
  4. Group staves into systems: staves whose horizontal x-extent overlaps
     and whose vertical separation is small (typically < 3× line spacing)
     belong to the same system (e.g., piano grand staff = treble + bass).

Public surface:
    detect_staves(page) -> PageWithStaves
"""

from __future__ import annotations

import statistics
from typing import Sequence

import numpy as np
from scipy.signal import find_peaks

from .header_ink import measure_staff_line
from .system_grouping import assign_systems as assign_systems_by_bridging
from .types import PageImage, Staff, PageWithStaves


# ─── Tuning ──────────────────────────────────────────────────────────────────
# These work for typical 600 DPI printed scores. Adjust if very small/large
# staff sizes show up in your input.

MIN_PEAK_DISTANCE_PX = 4         # staff lines won't be closer than this
MIN_LINE_LENGTH_FRAC = 0.35      # staff line spans >= 35% of page width
PEAK_PROMINENCE_FRAC = 0.30      # peak must be 30% of (max - min) profile range
GROUP_LINE_SPACING_TOLERANCE = 0.30  # ±30% gap variation within a 5-line group
MAX_SYSTEM_GAP_FACTOR = 6.0      # fallback if auto-bipartition fails
STAFF_LINE_MAX_GAP_SPACES = 1.0  # a break this wide is still the same staff line
# How far above and below its nominal row a printed staff line is looked for,
# in staff spaces. It has to cover the line's own thickness plus how far it
# wanders — measured at 3px and 2px on Beethoven 5 p.15 at 300 DPI, against a
# spacing of 8 — and stay well inside the one-space gap to the next line.
STAFF_LINE_BAND_SPACES = 0.35
# How many of a staff's five lines must carry ink in a column for it to count
# as part of the staff. Two is not enough: an instrument name in the margin
# crosses two line rows and drags the left edge into it.
STAFF_EXTENT_MIN_LINES = 3
SYSTEM_BREAK_GAP_FACTOR = 2.5    # gap this many × the typical within-system gap = a break
MAX_LINE_INK_RUNS_PER_SPACE = 1.7  # above this the "lines" are rows of text, not staff lines

# The comb pass (step 3b below) admits a candidate row on a much weaker ink
# threshold than the first pass, because it does not have to decide alone: a row
# only becomes a staff line if four more rows sit at the page's own staff
# spacing behind it. The gate is a fraction of the median ink of a line in a
# CONFIDENTLY detected staff, so it calibrates to the page's own printing
# weight rather than to an absolute pixel count.
#
# Measured on the corpus (Beethoven 5 pp. 2 & 10, WTC p.5, Mahler 5 p.11,
# Boléro p.31, La Mer p.25, Kirchhoff p.10): every value in 0.20-0.35 gives
# identical, correct counts on all seven pages; below 0.20 false staves appear
# (Beethoven 5 p.2 gains a 23rd, La Mer a 21st). 0.30 sits inside that plateau,
# toward the strict end.
STAFF_COMB_POOL_FRAC = 0.30
# How far a line may sit from the position the comb predicts, in staff spaces.
# Engraving is regular; this only has to absorb rasterisation and a scan's skew.
STAFF_COMB_TOLERANCE = 0.25
# A group whose line spacing is a large multiple of the page's spacing is not a
# staff — it is one line borrowed from each of several staves (see
# `_reject_spacing_outliers`). Real size variation on a page (ossia staves,
# a reduced cue staff) is always SMALLER than the main staves, never 60% larger.
STAFF_SPACING_OUTLIER_FACTOR = 1.6

# ─── One-line percussion staves (step 3c) ───────────────────────────────────
# A single printed rule is admitted as a staff only if no other staff-line row
# sits within this many staff spaces of it. Four spaces is the height of a
# whole staff: any closer and the two rows could be lines of one FIVE-line
# staff whose others were never detected, which is a far commoner page than a
# percussion part. Precision matters more than recall here, because a staff
# invented between two real ones corrupts slot identity exactly as a missing
# one does — every staff below it shifts by one.
SINGLE_LINE_CLEARANCE_SPACES = 4.0
# The rule must also be a staff's worth of line: this fraction of the page's
# median staff width, and overlapping the x-window the page's staves occupy.
# A hairpin, a bracket edge or a fragment of text is shorter than this.
SINGLE_LINE_MIN_WIDTH_FRAC = 0.5
SINGLE_LINE_MIN_OVERLAP_FRAC = 0.6
# ...and only if the rows where a five-line staff's OTHER lines would fall are
# empty of line. This is the test that matters: on a pocket score at 300 DPI a
# real staff can lose four of its five lines to the peak gates, and the
# survivor is alone, full width, and between its neighbours — indistinguishable
# from a percussion rule by every property of the row itself. The other four
# lines are still PRINTED, though, whether or not the row pass saw them, so the
# question is asked of the page rather than of the peak list.
SINGLE_LINE_NEIGHBOUR_RUN_FRAC = 0.5
# Before the clearance rule above is applied, drop candidates far SHORTER than
# the longest in their own cluster. The clearance rule rejects every row in a
# tight group, which is right when they are two lines of one broken staff and
# wrong when a non-rule has wandered in between two real percussion parts —
# and it takes both real ones down with it.
#
# Measured 2026-08-31 on Mahler 5 p10 (Edition Peters): the candidates are the
# Gr.Tr. rule (width 1857), the long WAVY TRILL LINE printed between the two
# parts (1410), and the Kl.Tr. rule (1858). The two rules are 62 px apart and
# would clear each other's 52 px clearance easily; the trill sits 37 px from one
# and 25 px from the other, so all three were rejected and the page reported 18
# staves instead of 20. Boléro p2 is the same shape — a full-width `Tamb.` rule
# at 3112 px with 59 px and 142 px fragments beside it, in all four systems.
#
# A printed rule is as long as the staves around it, which is what
# SINGLE_LINE_MIN_WIDTH_FRAC already says in absolute terms; this says it
# RELATIVELY, so an interloper is judged against the rules it is interfering
# with rather than against the page. 0.9 because the real rules on these pages
# agree to within 0.1% of each other while the interlopers are at 0.76, 0.02
# and 0.05 of them — the gap is enormous and the constant is nowhere near it.
SINGLE_LINE_CLUSTER_WIDTH_FRAC = 0.9

# ─── Misaligned five-line windows (step 3d) ─────────────────────────────────
# A group whose FIRST or LAST line is far thicker than the rest is not a staff
# with one fat line — it is a window that locked onto something else and slid
# by a space. Measured on the engraved Brahms 1 fixture, staff 20 (Contrabass):
#
#     line_ys_page      [9287, 9327, 9368, 9408, 9451]
#     line_thickness_px [18.0,  5.0,  5.0,  5.0,  5.0]
#
# The 18 px "line" is a BEAM. The window is internally consistent — spacing 41,
# span 164, both normal for the page — which is why nothing downstream ever
# questioned it, and every note on the staff then resolved one space low: truth
# 42 x C3 read as Ab2, the key signature supplying the flat. That single staff
# produced 42 of the page's 65 wrong pitches
# (`benchmarks/omr-ned-2026-08/BRAHMS_ATTRIBUTION_2026-09-01.md`).
#
# ONLY AN END LINE CAN BE THIS. A thick line in the MIDDLE is pinned by the
# lines either side of it, so it is a beam crossing a correctly-placed staff —
# Brahms staff 8 is exactly that, and must not be touched.
#
# Thickness ratio against the group's median: 19 of the 21 staves on that page
# sit at 1.0-1.8, the two outliers at 3.6 and 4.0. 2.5 is the gap.
MISFIT_THICKNESS_RATIO = 2.5
# The replacement row must actually carry a printed line, judged the same way
# the first pass judges one: a long horizontal run at the staff's own width.
MISFIT_MIN_RUN_FRAC = 0.5

# ─── The same fault, told by COVERAGE instead (step 3d, second signal) ───────
# Thickness catches a window that locked onto a BEAM, because a beam is fat.
# It does not catch one that locked onto LEDGER LINES, because those are printed
# at staff-line weight. Brahms's Violin 1 is the second kind:
#
#     window            [7498, 7539, 7580, 7621, 7662]
#     line_thickness_px [   9,    8,    5,    4,    5]     ratio 1.8, no outlier
#     true staff        [7578, 7620, 7661, 7703, 7744]
#
# It sits TWO spaces high, and its top two rows are ledger lines under a high
# violin line. 35 of that part's 39 notes then came out four staff positions
# low, and it cost 263 OMR-NED edits — more than any other part in the
# benchmark and more than the whole of Beethoven
# (`benchmarks/omr-ned-2026-08/WRONG_NOTE_ATTRIBUTION_2026-09-01.md`).
#
# What separates the impostors is not how thick they are but HOW FAR THEY RUN.
# A printed staff line spans the staff; those two rows cover 4% and 6% of it.
# `_longest_row_run` already measures exactly that and was already used here —
# as the confirmation gate, never as the thing that fires.
#
# MEASURED OVER 270 STAVES, 5 editions plus the three engraved fixtures
# (`benchmarks/omr-phase1-baseline/probe_line_coverage.py`), as the worse END
# line's coverage divided by the staff's own median:
#
#     0.041  brahms-e2e  staff 16   [0.041, 0.055, 1.0, 1.0, 1.0]
#     0.055  bolero-p31  staff 11   [0.055, 0.026, 1.0, 1.0, 1.0]
#     0.076  beet5-p2    staff 18   [0.05, 0.655, 0.694, 0.758, 0.659]
#     0.107  bolero-p5   staff 12   [0.107, 1.0, 1.0, 1.0, 1.0]
#     0.109  bolero-p5   staff 21   [0.109, 1.0, 1.0, 1.0, 1.0]
#     0.112  bolero-p5   staff  3   [0.112, 1.0, 1.0, 1.0, 1.0]
#     ---------------------------------------- 6x gap, nothing in between ----
#     0.682  lamer-p25   staff 16   [0.746, 0.743, 0.878, 0.773, 0.509]
#     0.784  beet5-p2    staff  2   [0.485, 0.664, 0.573, 0.619, 0.645]
#
# Every one of the first six was confirmed misfitted by reading the page's own
# ink profile; both of the next two are correctly placed staves on faint scans
# (lamer's last row is 2px off its line, not a space). RELATIVE to the staff's
# own median rather than absolute, because a faint scan's real lines only cover
# 0.5-0.7 and an absolute floor would either miss them or condemn them.
MISFIT_COVERAGE_FRAC = 0.35
# A window three or more spaces off shares no line with the true staff, so
# there is no evidence it is the same staff; the measured cases are 1 and 2.
MISFIT_MAX_SHIFT = 2


# ─── Step 1: projection profile + peak detection ─────────────────────────────


def _ink_profile(binary: np.ndarray) -> np.ndarray:
    """Per-row count of ink pixels (where binary == 0). Staff line rows have
    much higher values than text/notehead rows because the line is long."""
    return np.sum(binary == 0, axis=1)


def _candidate_staff_rows(profile: np.ndarray, page_width: int) -> np.ndarray:
    """Find rows that look like staff lines: long horizontal black runs."""
    min_run = int(page_width * MIN_LINE_LENGTH_FRAC)
    # Floor: every peak must clear the min_run threshold (so a row contains
    # at least one long line). Prominence makes peaks stand out vs neighbors.
    prom = max(1, int((profile.max() - profile.min()) * PEAK_PROMINENCE_FRAC))
    peaks, _ = find_peaks(
        profile,
        height=min_run,
        distance=MIN_PEAK_DISTANCE_PX,
        prominence=prom,
    )
    return peaks


# ─── Step 2: group peaks into 5-line staves ──────────────────────────────────


def _group_into_staves(peaks: np.ndarray) -> list[list[int]]:
    """Cluster peak rows into groups of 5 with roughly equal spacing.

    Strategy: slide through the peaks looking for any 5-peak window whose
    inter-peak gaps are all within ±tolerance of their mean. Greedy: once
    a 5-peak group is accepted, skip past it.
    """
    if len(peaks) < 5:
        return []
    peaks = list(map(int, peaks))
    groups: list[list[int]] = []
    i = 0
    while i + 4 < len(peaks):
        window = peaks[i:i + 5]
        gaps = [window[j + 1] - window[j] for j in range(4)]
        mean_gap = sum(gaps) / 4
        if mean_gap <= 0:
            i += 1
            continue
        max_dev = max(abs(g - mean_gap) for g in gaps) / mean_gap
        if max_dev <= GROUP_LINE_SPACING_TOLERANCE:
            groups.append(window)
            i += 5
        else:
            i += 1
    return groups


# ─── Step 3b: recover staves the ink gates missed, using the page's own comb ──


def _page_line_spacing(groups: list[list[int]]) -> float:
    """The page's characteristic staff-line spacing, taken as the median over
    already-detected staves. Robust to a phantom group or two because those are
    a minority and sit far above the median."""
    if not groups:
        return 0.0
    spacings = [(g[-1] - g[0]) / 4.0 for g in groups]
    return float(np.median(spacings))


def _reject_spacing_outliers(groups: list[list[int]], spacing: float) -> list[list[int]]:
    """Drop groups whose line spacing is far above the page's.

    Five evenly spaced rows are not necessarily a staff. When the ink gates
    reject most of a staff's lines — which happens wherever the print is
    lighter than the page's densest music — the survivors are one line from
    each of several DIFFERENT staves, and they are as evenly spaced as the
    staves themselves are. The greedy grouper then accepts that as one staff.

    Measured on Beethoven 5 p.10: five wind staves lost all but one line each,
    and their survivors (rows 455, 573, 742, 885, 1025) were grouped into a
    single "staff" of spacing 142.5 on a page whose real spacing is 15.8. Five
    staves became one, and the page reported 18 staves where it has 22 — which
    is exactly the number `test_pipeline.py` asserted, so the bug held a green
    test in place.

    Only the high side is rejected. A page may legitimately carry staves
    smaller than its main ones (ossia, cue staves); none carries a staff whose
    lines are 60% further apart than the page's median.
    """
    if spacing <= 0:
        return groups
    return [
        g for g in groups
        if (g[-1] - g[0]) / 4.0 <= spacing * STAFF_SPACING_OUTLIER_FACTOR
    ]


def _comb_match_staves(
    profile: np.ndarray, page_width: int, spacing: float, reference_ink: float,
) -> list[list[int]]:
    """Find five-line staves by matching the page's own spacing as a comb.

    The first pass has to decide row by row whether ink looks like a staff
    line, and it gets that wrong wherever the printing is lighter than the
    page's densest passage: a row's prominence is measured against a threshold
    set by the whole page, and a wind staff engraved above dense strings never
    clears it. On Beethoven 5 p.10 the missed rows carry 1000-1350 ink against a
    1013 floor and a 695 prominence requirement — they are not faint in any
    absolute sense, only faint relative to the strings below them.

    Knowing the spacing removes the need to make that judgement per row. A
    staff is five rows at a known pitch, so a row can be admitted on much
    weaker evidence and then required to stand in that pattern. Candidates are
    scored by how closely their lines land on the comb and resolved
    greedily — best fit first, no two staves overlapping in y.
    """
    if spacing <= 0 or reference_ink <= 0:
        return []
    gate = max(1.0, STAFF_COMB_POOL_FRAC * reference_ink)
    peaks, _ = find_peaks(profile, height=gate, distance=MIN_PEAK_DISTANCE_PX)
    if len(peaks) < 5:
        return []
    rows = np.asarray(peaks, dtype=int)
    tol = STAFF_COMB_TOLERANCE * spacing

    candidates: list[tuple[float, float, list[int]]] = []
    for first in rows:
        lines = [int(first)]
        deviations: list[float] = []
        for k in range(1, 5):
            target = first + k * spacing
            near = rows[np.abs(rows - target) <= tol]
            if len(near) == 0:
                break
            pick = int(near[np.argmin(np.abs(near - target))])
            if pick <= lines[-1]:
                break
            deviations.append(abs(pick - target) / spacing)
            lines.append(pick)
        if len(lines) == 5:
            # Best fit first; ink breaks ties so that where two combs fit
            # equally well the more strongly printed one wins.
            candidates.append(
                (float(np.mean(deviations)), -float(profile[lines].sum()), lines)
            )

    candidates.sort(key=lambda c: (c[0], c[1]))
    accepted: list[list[int]] = []
    for _, _, lines in candidates:
        if any(not (lines[-1] < a[0] or lines[0] > a[-1]) for a in accepted):
            continue
        accepted.append(lines)
    accepted.sort(key=lambda g: g[0])
    return accepted


def _merge_staff_groups(
    strict: list[list[int]], comb: list[list[int]],
) -> list[list[int]]:
    """Add comb staves only where the strict pass found nothing.

    The comb is a RECOVERY pass, not a replacement. Where the strict pass
    already read a staff, its rows are kept: they were confirmed by prominence,
    which is real evidence the comb does not have, and re-deciding them would
    churn the output of every page that already works. (Measured: letting the
    comb win on overlap moved two cells on Boléro p.5 for no reason.)

    So the comb only speaks where nothing was heard. The phantom must therefore
    be rejected from `strict` BEFORE this merge — otherwise a phantom spanning
    five staves' worth of page would block the very staves it stands in for.
    """
    out = list(strict)
    for g in comb:
        if any(not (g[-1] < a[0] or g[0] > a[-1]) for a in out):
            continue
        out.append(g)
    out.sort(key=lambda g: g[0])
    return out


# ─── Step 3c: one-line percussion staves ────────────────────────────────────


def _longest_row_run(
    binary: np.ndarray, y: int, spacing: float,
    x_lo: int = 0, x_hi: int | None = None,
) -> tuple[int, int, int]:
    """The longest horizontal ink run on row `y`, bridging print dropouts of up
    to one staff space. Returns (x_start, x_end, length); length 0 if no ink.

    `_staff_x_extent` does the same thing for a whole staff, taking its gap
    tolerance from the staff's own spacing. A single row has no spacing of its
    own, so the page's is passed in.
    """
    h, w = binary.shape
    if not (0 <= y < h):
        return 0, 0, 0
    x_hi = w if x_hi is None else min(w, x_hi)
    x_lo = max(0, x_lo)
    if x_hi - x_lo < 2:
        return 0, 0, 0
    band = binary[max(0, y - 1):min(h, y + 2), x_lo:x_hi].min(axis=0)
    ink_x = np.flatnonzero(band == 0)
    if ink_x.size == 0:
        return 0, 0, 0
    max_gap = max(1, int(round(STAFF_LINE_MAX_GAP_SPACES * spacing)))
    breaks = np.flatnonzero(np.diff(ink_x) > max_gap + 1)
    starts = np.concatenate(([0], breaks + 1))
    ends = np.concatenate((breaks, [ink_x.size - 1]))
    best = int(np.argmax(ink_x[ends] - ink_x[starts]))
    x0 = int(ink_x[starts[best]]) + x_lo
    x1 = int(ink_x[ends[best]]) + x_lo
    return x0, x1, x1 - x0


def _has_the_rest_of_a_staff(
    binary: np.ndarray, y: int, spacing: float, x0: int, x1: int,
    ignore_rows: Sequence[int] = (),
) -> bool:
    """Is there line where a five-line staff's other lines would be?

    A lone inked row is ambiguous by itself: it is what a percussion staff
    looks like, and equally what is left of a lightly printed five-line staff
    after four of its lines failed the peak gates. Measured on Beethoven 5 at
    300 DPI, that second case is the common one — a clarinet staff and a violin
    staff both arrived as a single full-width row.

    So look for the rest of the staff on the page. Whether the row pass saw
    them or not, the other lines are printed, and printed lines are long: the
    test is a run of line-like length at one or two staff spaces above or
    below, over the candidate's own x-range.

    `ignore_rows` are rows the caller has ALREADY judged not to be printed
    rules — the short interlopers `_single_line_staff_rows` drops. Without this
    the same piece of ink is charged twice: on Mahler 5 p10 the wavy trill line
    printed between Gr.Tr. and Kl.Tr. is dropped as an interloper, and then
    reappears here as "the rest of a staff" two spacings above Kl.Tr. (row 1743,
    run 1410 against a 929 threshold) and rejects it. A row that is not
    line-like enough to be a staff on its own is not evidence of one.

    The exclusion is deliberately narrow — only rows this page's own clustering
    already rejected, never a general tolerance — so the broken-five-line-staff
    case the gate exists for is untouched: those survivors are full width, so
    they are never dropped as interlopers in the first place.
    """
    width = x1 - x0
    if width <= 0:
        return False
    # Tolerance for matching a probe row to an ignored one: the probe lands on
    # `round(y + k * spacing)`, which need not be the exact peak row.
    tol = max(2, int(round(spacing * 0.25)))
    for k in (-2, -1, 1, 2):
        row = int(round(y + k * spacing))
        if any(abs(row - int(skip)) <= tol for skip in ignore_rows):
            continue
        _, _, run = _longest_row_run(binary, row, spacing, x0, x1 + 1)
        if run >= SINGLE_LINE_NEIGHBOUR_RUN_FRAC * width:
            return True
    return False


def _single_line_staff_rows(
    binary: np.ndarray,
    peaks: np.ndarray,
    groups: list[list[int]],
    spacing: float,
) -> list[int]:
    """Rows that are a one-line percussion staff rather than part of any five.

    `_group_into_staves` accepts only five-peak windows, so a single-line
    percussion staff produces no `Staff` at all — and every staff below it then
    carries a `staff_index` one lower than its true slot. That is how a missing
    rule becomes a wrong instrument, a wrong clef and wrong pitches for the
    whole lower half of an orchestral system.

    A one-line staff cannot be found the way the others are: it has no internal
    spacing to calibrate against, and one inked row on its own is also what a
    page border, a rehearsal rule and the single surviving line of a badly
    printed five-line staff look like. What identifies it is the company it
    keeps — a rule as long as the page's staves, standing between them, with
    nothing else at staff-line pitch anywhere near it.

    Candidates come from the STRICT peak pass, so each has already cleared the
    length and prominence gates; this only decides which of the leftovers stand
    alone. Returns the accepted rows, sorted.
    """
    if spacing <= 0 or not groups or len(peaks) == 0:
        return []

    # The x-window and width the page's own staves occupy, which a percussion
    # rule shares — it is set to the same margins as everything above it.
    extents = [_staff_x_extent(binary, g) for g in groups]
    med_start = float(np.median([x0 for x0, _ in extents]))
    med_end = float(np.median([x1 for _, x1 in extents]))
    med_width = med_end - med_start
    if med_width <= 0:
        return []

    accepted_lines = sorted(y for g in groups for y in g)
    top, bottom = accepted_lines[0], accepted_lines[-1]
    clearance = SINGLE_LINE_CLEARANCE_SPACES * spacing

    # Only rows BETWEEN the first and last staff line on the page. A percussion
    # staff sits inside the system with the rest of the parts; a page border, a
    # title rule or a footer sits outside it, and this is what separates them
    # without a threshold on any of their other properties.
    candidates = [
        int(y) for y in peaks
        if top < int(y) < bottom
        and min(abs(int(y) - a) for a in accepted_lines) >= clearance
    ]

    # Drop the interlopers FIRST. A row much shorter than the longest candidate
    # is not a printed rule — it is a trill line, a hairpin, a fragment of text
    # — and leaving it in the list makes the clearance rule below reject the
    # genuine rules on either side of it along with it.
    runs = {y: _longest_row_run(binary, y, spacing)[2] for y in candidates}
    longest = max(runs.values(), default=0)
    interlopers: list[int] = []
    if longest > 0:
        keep = SINGLE_LINE_CLUSTER_WIDTH_FRAC * longest
        interlopers = [y for y in candidates if runs[y] < keep]
        candidates = [y for y in candidates if runs[y] >= keep]

    out: list[int] = []
    for y in candidates:
        # Two lone rows within a staff's height of each other are more likely
        # two lines of one five-line staff than two percussion parts, so
        # neither is admitted.
        if any(other != y and abs(other - y) < clearance for other in candidates):
            continue
        x0, x1, width = _longest_row_run(binary, y, spacing)
        if width < SINGLE_LINE_MIN_WIDTH_FRAC * med_width:
            continue
        overlap = min(x1, med_end) - max(x0, med_start)
        if overlap < SINGLE_LINE_MIN_OVERLAP_FRAC * width:
            continue
        if _has_the_rest_of_a_staff(binary, y, spacing, x0, x1, interlopers):
            continue
        out.append(y)
    return sorted(out)


# ─── Step 3: find horizontal extent of each staff ────────────────────────────


def _staff_x_extent(
    binary: np.ndarray, line_ys: list[int], spacing_hint: float | None = None,
) -> tuple[int, int]:
    """Find the left/right edges of the staff lines themselves.

    Two things make this harder than reading one row of the image.

    **The line is dashed.** Printed lines drop out and scans lose ink, so the
    longest strictly-contiguous run is whichever fragment happens to be
    longest, not the line. Breaks up to `STAFF_LINE_MAX_GAP_SPACES` of a staff
    space are therefore bridged — far wider than any printing dropout, far
    narrower than the gap between two staves set side by side on one row, which
    is the case the tolerance must not merge.

    **The line is not straight, and it is not one pixel thick.** This is what
    the version before 2026-08-28 got wrong. It read a fixed ±2px band around
    the MIDDLE line's nominal row, and on a wide orchestral page the print
    wanders further than that: Beethoven 5 p.15 measures 3px of line thickness
    and 2px of wander at 300 DPI, so the middle line leaves the band and comes
    back, and the longest surviving run starts hundreds of pixels in — past the
    clef, past the key signature, sometimes past the first notes. Nine of the
    twelve staves in that page's first system started between x=274 and x=773
    on a system whose staves all begin at x≈172, and the header layer above
    this cannot read a clef that was never in the window.

    So the band scales with the staff (`STAFF_LINE_BAND_SPACES`, still well
    inside the one-space gap to the neighbouring line), and all five lines
    vote: a column belongs to the staff when `STAFF_EXTENT_MIN_LINES` of them
    carry ink there. Dropouts are independent per line, so the vote survives
    what any single line does — while still refusing the margin, where a
    two-line vote follows the instrument name (measured: x=127 into "Fag.",
    against a true edge of 172).

    Measured over five pages: Beethoven 5 p.15 system 0 goes from 3 of 12
    staves agreeing on the system's left edge to 12 of 12, p.10 from 3 of 10
    and 1 of 11 to all of both, Boléro p.31 from 1 of 29 to 29 of 29. WTC p.5,
    a clean modern engraving that was already right, moves by at most 4px.

    `spacing_hint` supplies the page's staff spacing for a staff that has no
    spacing of its own — a one-line percussion rule.
    """
    h, w = binary.shape
    if len(line_ys) >= 2:
        spacing = (max(line_ys) - min(line_ys)) / (len(line_ys) - 1)
    else:
        spacing = float(spacing_hint or 0.0)

    band = max(1, int(round(STAFF_LINE_BAND_SPACES * spacing))) if spacing > 0 else 2
    votes = np.zeros(w, dtype=np.int16)
    for y in line_ys:
        y0 = max(0, int(y) - band)
        y1 = min(h, int(y) + band + 1)
        if y1 <= y0:
            continue
        votes += (binary[y0:y1] == 0).any(axis=0)

    # A staff with fewer than five detected lines cannot spare any of them.
    need = min(STAFF_EXTENT_MIN_LINES, len(line_ys))
    ink_x = np.flatnonzero(votes >= need)
    if ink_x.size == 0:
        return 0, w - 1

    # Gap tolerance in pixels, from this staff's own line spacing, so the rule
    # holds at any DPI or engraving size.
    max_gap = max(1, int(round(STAFF_LINE_MAX_GAP_SPACES * spacing)))

    # Split the ink into runs, allowing gaps of up to `max_gap` blank pixels.
    # Consecutive ink pixels differ by 1, so a run of `g` blanks shows up as a
    # difference of g + 1.
    breaks = np.flatnonzero(np.diff(ink_x) > max_gap + 1)
    starts = np.concatenate(([0], breaks + 1))
    ends = np.concatenate((breaks, [ink_x.size - 1]))
    best = int(np.argmax(ink_x[ends] - ink_x[starts]))
    return int(ink_x[starts[best]]), int(ink_x[ends[best]])


# ─── Step 4: group staves into systems ───────────────────────────────────────


def _bipartition_threshold(values: list[float]) -> float | None:
    """Given a 1D list of values that fall into two clusters (small/large),
    return a threshold that separates them via 1D k-means (Lloyd's, k=2,
    Otsu-like). Returns None if values look unimodal."""
    if len(values) < 2:
        return None
    arr = np.asarray(values, dtype=float)
    arr_min, arr_max = float(arr.min()), float(arr.max())
    if arr_max - arr_min < 1e-6:
        return None
    # 1D Lloyd's algorithm
    c1, c2 = arr_min, arr_max
    for _ in range(20):
        mask = arr <= (c1 + c2) / 2
        if mask.all() or (~mask).all():
            return None  # all values in one cluster → unimodal
        new_c1 = float(arr[mask].mean())
        new_c2 = float(arr[~mask].mean())
        if abs(new_c1 - c1) < 1e-6 and abs(new_c2 - c2) < 1e-6:
            break
        c1, c2 = new_c1, new_c2
    # Require the gap between clusters to be at least 2x the spread of the
    # smaller cluster — otherwise this isn't really bimodal.
    intra_spread = float(np.std(arr[arr <= (c1 + c2) / 2])) or 1.0
    if (c2 - c1) < 2.0 * intra_spread:
        return None
    return (c1 + c2) / 2


def _assign_systems(staves: list[Staff]) -> list[Staff]:
    """A 'system' is a group of staves that are read together (e.g. grand
    staff, full orchestral score). Algorithm:

      1. Compute all inter-staff vertical gaps on the page.
      2. If the gaps cleanly bipartition into "small" (intra-system) and
         "large" (inter-system) clusters, use the midpoint as the threshold.
      3. Otherwise fall back to MAX_SYSTEM_GAP_FACTOR × line_spacing.

    Also requires horizontal overlap > 50% for two staves to be in the same
    system (catches multi-column scores).
    """
    if not staves:
        return staves
    staves_sorted = sorted(staves, key=lambda s: s.top_y)
    if len(staves_sorted) == 1:
        staves_sorted[0].system_index = 0
        return staves_sorted

    gaps = [staves_sorted[i + 1].top_y - staves_sorted[i].bottom_y
            for i in range(len(staves_sorted) - 1)]
    threshold = _bipartition_threshold(gaps)
    mean_spacing = float(np.mean([s.line_spacing_px for s in staves_sorted]))
    if threshold is None:
        threshold = mean_spacing * MAX_SYSTEM_GAP_FACTOR

    # Secondary MAD-based threshold: catches mid-magnitude system breaks
    # that bipartition merges with the small-gap cluster. Common on
    # orchestral scores where there's a clearly-bigger-than-normal gap
    # between bracketed sub-systems (e.g., winds vs brass vs strings)
    # but it's still much smaller than the page-spanning system break.
    # Rule: a gap > 2.0 × median + max(0, gap > min(fallback, ...)) is
    # also a break. This is additive — a gap counts as break if EITHER
    # threshold fires.
    if gaps:
        median_gap = float(np.median(gaps))
        mad_threshold = median_gap * 2.0
    else:
        mad_threshold = float("inf")

    # Third threshold, against a statistic the breaks cannot contaminate.
    # Both rules above are computed over ALL gaps, so on a page where system
    # breaks are a large share of them — a monograph laying out many short
    # music examples between paragraphs, say — the breaks drag the median and
    # the bipartition up past themselves and the page reads as one system.
    # (Observed on Nottebohm p.90: gaps of 65, 65, 65, 341, 394, 830, where a
    # median of 203 puts both thresholds above the 341 and 394 breaks.)
    #
    # Staves WITHIN a system are set at a consistent small distance, so the
    # low quartile of the gaps estimates that distance whatever fraction of
    # the page is system breaks — and a break is a clear multiple of it.
    if gaps:
        typical_within_system = float(np.percentile(gaps, 25))
        quartile_threshold = max(
            typical_within_system * SYSTEM_BREAK_GAP_FACTOR,
            mean_spacing * 2.0,   # floor: never split on a hair's difference
        )
    else:
        quartile_threshold = float("inf")

    current_system = 0
    staves_sorted[0].system_index = 0
    for i in range(1, len(staves_sorted)):
        prev = staves_sorted[i - 1]
        cur = staves_sorted[i]
        gap = cur.top_y - prev.bottom_y
        overlap = min(prev.x_end, cur.x_end) - max(prev.x_start, cur.x_start)
        min_extent = min(prev.x_end - prev.x_start, cur.x_end - cur.x_start)
        x_overlap_frac = overlap / max(1, min_extent)
        is_break = (
            gap >= threshold
            or gap >= mad_threshold
            or gap >= quartile_threshold
            or x_overlap_frac <= 0.5
        )
        if is_break:
            current_system += 1
        cur.system_index = current_system
    return staves_sorted


def _line_ink_runs_per_space(binary: np.ndarray, staff: Staff) -> float:
    """How many separate ink runs lie along this staff's lines, per staff-space
    of line length (median over the five lines).

    This is the test for whether a detected "staff" is a staff at all. The
    row-projection detector finds staves by looking for rows with a lot of ink,
    and a row of justified body text has a lot of ink — enough to clear the
    line-length threshold — while five consecutive text baselines are evenly
    enough spaced to pass the 5-line grouping. So paragraphs become staves,
    complete with a clef and measures of their own.

    What actually separates them is not how MUCH ink is in the row but how it
    is arranged. A staff line is one continuous stroke: a handful of runs over
    its whole length even on a scan that has broken it into dashes. A text
    baseline is one run per letter. Measured over 310 staves on seven scores
    and 20 text blocks, the two do not come close to overlapping — music tops
    out at 1.39 runs per staff-space and text starts at 2.02, with the bulk two
    orders of magnitude apart (music median 0.017, text median 2.59).

    Note this deliberately does NOT test ink coverage, the obvious near-miss.
    Coverage does separate on clean pages but overlaps on real ones: heavy
    notation ink interrupts the line, so genuine staves in Beethoven 5 and
    La Mer fall to 0.62-0.70, right on top of body text at 0.62-0.72.
    """
    height = binary.shape[0]
    spacing = max(staff.line_spacing_px, 1.0)
    length_spaces = max((staff.x_end - staff.x_start + 1) / spacing, 1e-6)
    per_line: list[float] = []
    for y in staff.line_ys:
        band = binary[max(0, y - 1) : min(height, y + 2), staff.x_start : staff.x_end + 1]
        if band.size == 0:
            per_line.append(float("inf"))
            continue
        ink = (band == 0).any(axis=0).astype(np.int8)
        # A run starts at each 0→1 transition, plus one if the line opens in ink.
        runs = int(np.count_nonzero(np.diff(ink) == 1)) + (1 if ink[0] else 0)
        per_line.append(runs / length_spaces)
    return float(np.median(per_line)) if per_line else float("inf")


# ─── Step 4: measure what the lines actually are ─────────────────────────────


def measure_line_geometry(
    binary: np.ndarray, line_ys: list[int], x_start: int, x_end: int
) -> tuple[list[float], float] | None:
    """Measure how thick each staff line is printed and how far it wanders.

    Returns `(thickness_per_line, max_wander)` in page pixels, or None when
    the lines are too faint or broken to trace.

    Everything downstream models a staff line as one integer row. That model
    is what staff-line removal erases along, and where the print disagrees
    with it the removal misses: on 19th-century engravings the lines run
    0.15–0.31 staff spaces thick against roughly 0.08 for a modern one, so a
    band sized for a modern line leaves most of an old one behind, in pieces.
    The pipeline had no way to say which case it was in — `line_ys` looks the
    same either way — and these two numbers are that missing fact.

    The measuring is `header_ink.measure_staff_line`, which follows the line
    column by column rather than assuming it is straight, and reads it only
    where no glyph is sitting on it; this runs it on the page instead of on a
    header crop, over the staff's own x-extent, where the lines are the thing
    being measured rather than something to strip away.
    """
    if len(line_ys) < 2 or x_end <= x_start:
        return None
    spacing = (max(line_ys) - min(line_ys)) / (len(line_ys) - 1)
    if spacing <= 0:
        return None

    # `trace_staff_line` wants 255=ink; Phase 1's binary is 0=ink. Crop to the
    # staff's own band first — tracing needs a window of about a third of a
    # staff space around each line, so copying the whole page per staff would
    # be most of a page image thrown away five times over.
    height, width = binary.shape
    y_lo = max(0, int(min(line_ys) - spacing))
    y_hi = min(height, int(max(line_ys) + spacing) + 1)
    x_lo = max(0, x_start)
    x_hi = min(width, x_end + 1)
    if y_hi - y_lo < 2 or x_hi - x_lo < 2:
        return None
    band = np.where(binary[y_lo:y_hi, x_lo:x_hi] == 0, 255, 0).astype(np.uint8)

    thicknesses: list[float] = []
    wanders: list[float] = []
    for y in line_ys:
        measured = measure_staff_line(band, float(y - y_lo), spacing)
        if measured is None:
            return None  # all five or nothing — a partial read would mislead
        thickness, wander = measured
        thicknesses.append(round(thickness, 3))
        wanders.append(wander)
    return thicknesses, round(max(wanders), 3)


def _line_coverage(
    binary: np.ndarray, line_ys: Sequence[int], spacing: float,
    x_start: int, x_end: int,
) -> list[float]:
    """How much of the staff's own width each of its lines actually inks."""
    width = max(1, x_end - x_start)
    return [
        _longest_row_run(binary, int(y), spacing, x_start, x_end + 1)[2] / width
        for y in line_ys
    ]


def _coverage_shift(coverage: Sequence[float]) -> int:
    """How many spacings the window is out, from the coverage alone.

    Positive k: the first k rows are not staff lines, so slide DOWN by k.
    Negative k: the last |k| are not, so slide UP. Zero: no verdict.

    The bad rows must ALL be at one end and form a run from it. A bad row in
    the MIDDLE is a real line the print lost, and a bad row at each end is not
    a misplaced window but a group assembled out of two different staves —
    neither is something a slide can fix.
    """
    if not coverage:
        return 0
    median = statistics.median(coverage)
    if median <= 0:
        return 0
    bad = [c < MISFIT_COVERAGE_FRAC * median for c in coverage]
    n_bad = sum(bad)
    if n_bad == 0 or n_bad == len(bad):
        return 0
    leading = 0
    while leading < len(bad) and bad[leading]:
        leading += 1
    trailing = 0
    while trailing < len(bad) and bad[-1 - trailing]:
        trailing += 1
    if leading and trailing:
        return 0
    k = leading or trailing
    if k > MISFIT_MAX_SHIFT or n_bad != k:
        return 0
    return k if leading else -k


def _slide_window(
    binary: np.ndarray, line_ys: list[int], k: int,
    x_start: int, x_end: int, spacing: float,
) -> list[int] | None:
    """Drop |k| rows off one end of the window and grow |k| onto the other.

    The step comes from the lines being KEPT, not from the page's spacing: the
    kept lines are the ones known to be real, and on a page whose staves differ
    slightly the page median can place a new row a pixel or two off its line.
    Each new row is then snapped to the best-covered row within a small window,
    bounded well inside a quarter of a space so a snap can never cross to a
    neighbour.
    """
    kept = line_ys[k:] if k > 0 else line_ys[:k]
    if len(kept) < 2:
        return None
    step = (kept[-1] - kept[0]) / (len(kept) - 1)
    if step <= 0:
        return None
    snap = max(1, int(min(2.0, step / 4.0)))
    height = binary.shape[0]

    grown: list[int] = []
    for i in range(1, abs(k) + 1):
        nominal = int(round(kept[-1] + i * step if k > 0 else kept[0] - i * step))
        best_row, best_cover = None, -1.0
        for row in range(nominal - snap, nominal + snap + 1):
            if not (0 <= row < height):
                continue
            cover = _line_coverage(binary, [row], spacing, x_start, x_end)[0]
            if cover > best_cover:
                best_row, best_cover = row, cover
        if best_row is None:
            return None
        grown.append(best_row)
    return sorted(kept + grown)


def _refit_misaligned_group(
    binary: np.ndarray, line_ys: list[int], spacing: float,
) -> list[int] | None:
    """Slide a five-line window back onto the staff it missed, or None.

    TWO SIGNALS FOR ONE FAULT, because the fault has two shapes. A window that
    locked onto a BEAM has an end line far THICKER than the rest (Brahms's
    contrabass, 18px against 5px). A window that locked onto LEDGER LINES has
    end lines printed at staff weight that do not RUN (Brahms's Violin 1, 4%
    and 6% of the staff's width, thickness ratio 1.8 and invisible to the first
    test). Either fires; the acceptance below is the same for both and
    demands the candidate be clean on BOTH.

    Returns None on anything unclear. A staff invented in the wrong place is
    worse than a staff read a space low, because the second at least keeps its
    notes in one voice.
    """
    if len(line_ys) != 5 or spacing <= 0:
        return None
    x_start, x_end = _staff_x_extent(binary, line_ys, spacing)
    measured = measure_line_geometry(binary, line_ys, x_start, x_end)
    if measured is None:
        return None
    thickness = measured[0]
    median = statistics.median(thickness)
    coverage = _line_coverage(binary, line_ys, spacing, x_start, x_end)

    shift = 0
    fired = ""
    if median > 0 and max(thickness) >= MISFIT_THICKNESS_RATIO * median:
        worst = int(np.argmax(thickness))
        # A thick line in the MIDDLE is pinned by the lines either side of it,
        # so it is a beam crossing a correctly-placed staff. Brahms staff 8 is
        # exactly that and must not be touched.
        if worst == 0:
            shift = 1
        elif worst == len(thickness) - 1:
            shift = -1
        fired = "thickness" if shift else ""
    if shift == 0:
        shift = _coverage_shift(coverage)
        fired = "coverage" if shift else ""
    if shift == 0:
        return None

    candidate = _slide_window(binary, line_ys, shift, x_start, x_end, spacing)
    if candidate is None or len(candidate) != 5:
        return None
    if candidate == line_ys:
        return None

    new_x0, new_x1 = _staff_x_extent(binary, candidate, spacing)
    new_coverage = _line_coverage(binary, candidate, spacing, new_x0, new_x1)
    new_median_cover = statistics.median(new_coverage)
    if new_median_cover <= 0:
        return None
    # The rows we moved onto have to carry a real line — the same demand the
    # old rule made of its single replacement row.
    if min(new_coverage) < MISFIT_MIN_RUN_FRAC * new_median_cover:
        return None
    # Each signal must IMPROVE on the one that fired it, so a slide is never
    # accepted for merely being different. Coverage is checked only when
    # coverage fired: a beam runs the full width of the staff it crosses, so a
    # thickness-detected misfit can have perfect coverage on both sides and
    # demanding an improvement there would veto the case the rule was built for.
    if fired == "coverage" and min(new_coverage) <= min(coverage):
        return None

    remeasured = measure_line_geometry(binary, candidate, new_x0, new_x1)
    if remeasured is None:
        return None
    new_thickness = remeasured[0]
    new_median = statistics.median(new_thickness)
    if new_median <= 0:
        return None
    if max(new_thickness) >= MISFIT_THICKNESS_RATIO * new_median:
        return None                      # no better than what we had
    return candidate


# ─── Public entry point ──────────────────────────────────────────────────────


def detect_staves(page: PageImage) -> PageWithStaves:
    """Detect every five-line staff on the page, group into systems."""
    profile = _ink_profile(page.binary)
    peaks = _candidate_staff_rows(profile, page.width)
    groups = _group_into_staves(peaks)

    # The strict pass above is the page's own calibration: whatever it found
    # confidently tells us the staff spacing and how much ink a printed line
    # carries here. The comb pass then re-reads the page with those two
    # numbers, which is what recovers staves in lightly printed regions.
    spacing = _page_line_spacing(groups)
    if spacing > 0:
        reference_ink = float(np.median([profile[y] for g in groups for y in g]))
        # Reject phantoms first: a phantom spans the staves it was assembled
        # from, so leaving it in would block their recovery on overlap.
        groups = _reject_spacing_outliers(groups, spacing)
        comb = _comb_match_staves(profile, page.width, spacing, reference_ink)
        groups = _merge_staff_groups(groups, comb)
        # A percussion part is one rule, and the five-peak grouper cannot see
        # it at all. Added last, so the page's own staves decide the spacing,
        # the x-window and the vertical extent it is judged against.
        for row in _single_line_staff_rows(page.binary, peaks, groups, spacing):
            groups.append([row])
        groups.sort(key=lambda g: g[0])

    # Step 3d: slide any window that locked onto a beam back onto its staff.
    if spacing > 0:
        groups = [(_refit_misaligned_group(page.binary, g, spacing) or g)
                  for g in groups]
        groups.sort(key=lambda g: g[0])

    staves: list[Staff] = []
    for idx, line_ys in enumerate(groups):
        x_start, x_end = _staff_x_extent(page.binary, line_ys, spacing)
        measured = measure_line_geometry(page.binary, line_ys, x_start, x_end)
        staves.append(Staff(
            page_index=page.page_index,
            staff_index=idx,
            line_ys=line_ys,
            x_start=x_start,
            x_end=x_end,
            system_index=0,
            line_thickness_px=measured[0] if measured else None,
            line_wander_px=measured[1] if measured else None,
            nominal_line_spacing_px=spacing if len(line_ys) < 2 else None,
        ))

    # Drop the "staves" that are paragraphs of body text (see
    # _line_ink_runs_per_space). Done before system assignment so the surviving
    # staves are numbered contiguously, and before x-extent matters downstream.
    staves = [
        st for st in staves
        if _line_ink_runs_per_space(page.binary, st) <= MAX_LINE_INK_RUNS_PER_SPACE
    ]
    for idx, st in enumerate(staves):
        st.staff_index = idx

    # System grouping from vertical connectivity (barlines + bracket run
    # through a system; nothing crosses the gap between two systems). The
    # gap-size heuristic is the fallback for pages whose barlines and bracket
    # are too faint to see at all — on a conductor's score it splits at
    # bracket-GROUP gaps and reports one system as several. See
    # system_grouping.py for the measured comparison.
    staves, used_bridging = assign_systems_by_bridging(page.binary, staves)
    if not used_bridging:
        staves = _assign_systems(staves)
    return PageWithStaves(page=page, staves=staves)


# ─── CLI / smoke test ────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse
    from .preprocessing import render_page

    ap = argparse.ArgumentParser(description="Detect staves on a PDF page")
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    pi = render_page(args.pdf, args.page, dpi=args.dpi)
    print(f"page {args.page}: {pi.width}x{pi.height} @ {args.dpi} DPI")
    pws = detect_staves(pi)
    print(f"detected {len(pws.staves)} staves in {1 + max((s.system_index for s in pws.staves), default=-1)} systems")
    for s in pws.staves:
        print(f"  staff {s.staff_index} sys={s.system_index}: "
              f"y={s.top_y}..{s.bottom_y} (span {s.span_px}px, spacing {s.line_spacing_px:.1f}px) "
              f"x={s.x_start}..{s.x_end}")
