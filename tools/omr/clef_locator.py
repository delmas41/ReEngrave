"""Find the C clef at the start of a staff with classical CV, when the detector
can't see one at all.

`clef_geometry` fixes *which* clef a detection is. This module fixes the case
where there is no detection to fix. On the material that motivated it —
19th-century engravings like Nottebohm's *Beethovens Studien*, whose
counterpoint exercises are written throughout in C clefs — the production model
and the clef-specialist model between them find **zero** C clefs on a page that
has one on every staff, even at confidence 0.03. The glyph is an archaic
"ladder" C clef that looks nothing like the modern fonts DeepScoresV2 was
rendered from, so no confidence threshold reaches it: a domain gap, not a
calibration problem. Every staff then falls back to the position default and
the whole page transcribes as treble, which is how a page of soprano-, alto-
and tenor-clef counterpoint comes out as nonsense.

Classical CV doesn't care what font a clef is set in. This is the division of
labour Phase 4f already settled on for stems and beams, and that barlines use:
hand the geometric, font-independent problems to morphology and leave YOLO the
ones that are genuinely about appearance.

## Why C clefs only

The locator identifies **C clefs and nothing else**, on purpose. A C clef is
the one clef with a shape signature that survives any engraving style: it is
vertically symmetric about the line it names, because that is what the glyph
is for. That symmetry is both how we recognise it and how we read it — the
centre of the ink IS the named line, so recognising the glyph and deciding
between soprano, alto and tenor are the same measurement.

G and F clefs are deliberately left alone. They have no comparably robust
font-independent signature, they are what the detector already reads *well*,
and the cost of being wrong is asymmetric: a missed clef leaves a staff on the
default it would have had anyway, but a wrongly-invented one transposes every
pitch on that staff. So a cluster that doesn't look like a C clef yields
nothing, and the existing behaviour stands.

## How it works

Take the staff-start cell; erase the vertical rules (the barline and bracket
that sit immediately left of the clef, often only a few pixels away) and the
horizontal ones (staff lines and the residue upstream removal leaves behind);
group what's left in the header strip into glyph-sized clusters; and test the
leftmost one for the C-clef signature — right size, and symmetric top-to-bottom.
Then hand its box to `clef_geometry`, which snaps the centre to a staff line
and names the clef.

## What it will not do

It only ever speaks when the detectors are silent (see `transcribe.py`), so a
score that reads correctly today cannot be made worse by it. And it abstains
rather than guesses: no cluster, an off-signature shape, an ambiguous snap, or
a staff without clean 5-line geometry all return None.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .clef_geometry import ClefGeometryConfig, ClefRead, DEFAULT_CONFIG, resolve_clef
# The rule-stripping and clustering primitives live in header_ink so this
# locator and the key-signature locator cannot drift apart about what counts as
# ink. `_ink_mask` below stays here: it rescales the cell to a fixed analysis
# spacing, which is right for this locator's tuned kernels and wrong to impose
# on a caller that measures positions in the cell's own coordinates.
from .header_ink import (
    cluster_components as _cluster_components,
    drop_flat_residue as _drop_flat_residue,
    staff_metrics as _staff_metrics,
    strip_horizontal_rules as _strip_horizontal_rules,
    strip_vertical_rules as _strip_vertical_rules,
)
from .types import MeasureCell


@dataclass(frozen=True)
class ClefLocatorConfig:
    """Shape gates for the header C-clef locator. Every length is in staff
    spaces (the distance between adjacent staff lines) so the thresholds hold
    at any DPI or engraving size.
    """

    header_frac: float = 0.30       # left fraction of the start cell to search
    # A clef is printed at the HEAD of the staff, so a candidate has to start
    # near it. A generous backstop rather than the main defence — on orchestral
    # scores the clef can sit several spaces in, behind a bracket and the
    # stacked instrument numbers engravers print to the left of it, so a tight
    # bound here would cost real viola and trombone clefs. The load-bearing
    # rule is "stop at the first glyph-sized cluster", below.
    max_start_spaces: float = 6.0
    # Narrower than this and it is a barline, a bracket or a stem, not a clef —
    # and, crucially, not worth STOPPING the search for either (see the width
    # test in locate_clef).
    min_width_spaces: float = 0.55
    max_width_spaces: float = 4.5
    # A C clef spans about 4 spaces in modern fonts and about 3 in the older
    # narrow engravings; the ceiling is what keeps a G clef (≈7) out.
    min_height_spaces: float = 2.2
    max_height_spaces: float = 5.0
    # ── ROADMAP 2.11: the band a C clef's ink ACTUALLY occupies ─────────────
    # Sean, 2026-09-23 (docs/DECISIONS.md): *"the size of clefs are consistent
    # to the staff and the edge of the first measure on the system"*. The pair
    # above is a GENEROUS accept/stop bound — it has to be, because it decides
    # whether to keep looking. This pair is the MEASURED band, and it is used
    # for one thing only: deciding whether a cluster is clef-sized enough to
    # survive a notehead box standing on it (`_overridable_occupancy`).
    #
    # ⚠️ MEASURED, NOT GUESSED, AND NARROWER THAN THE PAIR ABOVE ON PURPOSE.
    # `benchmarks/omr-clef-geometry-2026-09/probe/price_occupied.py` takes the
    # height of every clef this locator SUCCESSFULLY read, in staff spaces, on
    # the three acceptance documents' records, from the `cell:0` arm (the one
    # arm whose divisor the record carries exactly):
    #
    #     document      n    min    max    median
    #     Litolff      22   3.36   4.63     4.43
    #     Breitkopf    60   3.91   4.50     4.30
    #     engraved      3   4.09   4.09     4.09
    #     pooled       85   3.36   4.63     4.32
    #
    # Rounded OUTWARD to one decimal: 3.3 .. 4.7. It is narrower than
    # 2.2 .. 5.0 deliberately — if the two were equal, every cluster that can
    # reach the occupancy test would be in band and the veto would become dead
    # code for the only class that can ever raise it (rule 7: a control must
    # be able to fail). On the two scan records 4 of 47 / 2 of 27 `occupied`
    # clusters fall OUTSIDE this band and keep their veto.
    #
    # ⚠️ WOULD BE FALSIFIED BY: a plate whose C clef measures outside 3.3-4.7
    # staff spaces, which would show up as a clef the locator reads and this
    # band then refuses to defend. The roadmap's own prose guesses
    # (`alto ~= 4-4.5`) are close but not the measurement; the measurement is.
    # ⚠️ THE LOCATOR IS A C-CLEF LOCATOR, so this band is the C-clef family's
    # and no other. A treble-sized cluster never reaches the occupancy test at
    # all — `max_height_spaces` stops the search first.
    clef_family_min_height_spaces: float = 3.3
    clef_family_max_height_spaces: float = 4.7
    min_symmetry: float = 0.70      # the C-clef signature — see _refine_symmetry_axis
    # A rarer answer has to be better evidenced, and mezzosoprano is the rarest
    # of the five C clefs by a long way — essentially absent from the orchestral
    # and keyboard repertoire this reads. Measured over 101 located candidates on
    # a scanned Beethoven 5 (`beethoven5-clef-sweep.json`), it is named five
    # times and is WRONG ALL FIVE: four are G clefs whose surviving fragment
    # balances about line 2 — which is the line a G clef curls around, so the
    # misread is not random — and one is an F clef.
    #
    # The separation is wide and it is in symmetry. The one real mezzosoprano in
    # any corpus, engraved by LilyPond on the reference sheet, scores 0.981; the
    # five misreads score 0.712 to 0.815, all under the general 0.70 floor's
    # nearest neighbours. So the answer is not to ban the clef — that would cost
    # the real one — but to ask more of it than of the others.
    #
    # Nottebohm, twenty pages of vocal-clef counterpoint, names mezzosoprano
    # ZERO times with clustering on or off, so this floor cannot cost it
    # anything.
    min_symmetry_mezzosoprano: float = 0.90
    # How far the measured axis of symmetry may sit from the box centre. Big
    # enough to undo a stray fragment's pull, small enough that it can never
    # reach the next staff line (half a space would be the tipping point).
    axis_refine_spaces: float = 0.35
    min_ink_fraction: float = 0.10  # of the cluster's bbox — rejects stray rules
    cluster_gap_spaces: float = 0.6  # x-gap that still counts as one glyph
    # Vertical counterpart of the above, and the reason a clef in a 19th-century
    # header is found at all. A staff header is a narrow column that also holds
    # whatever is printed above and below the staff, and grouping ink by its
    # x-gap alone strung the clef together with the movement heading, the
    # rehearsal letter and the neighbouring staff into one column far too big
    # to be a clef — 55% of all header cells, measured. Requiring vertical
    # proximity as well leaves the clef standing on its own.
    #
    # The value is bounded on both sides by measurement, and the lower bound is
    # the dangerous one. Stripping the staff lines cuts a glyph's vertical
    # strokes at every line it crosses, so one glyph arrives as pieces about a
    # line-thickness apart; below 0.2 those pieces separate, and a piece of a
    # TREBLE clef is the size and shape of a C clef — braced piano music in all
    # fifteen keys produces 11-15 invented C clefs at 0.15 and none at 0.2.
    # Above 0.4 the heading text starts fusing back on and coverage falls.
    # 0.3 is the middle of that window, as far from inventing clefs as from
    # losing them.
    # Vertical counterpart of the x-gap.
    #
    # What it does: a staff header is a narrow column that also holds whatever
    # is printed above and below the staff, and grouping ink by its x-gap alone
    # strings the clef together with the movement heading, the rehearsal letter
    # and the neighbouring staff into one column far too big to be a clef —
    # 55% of all header cells, measured. Requiring vertical proximity as well
    # leaves the clef standing on its own, and it is worth a lot of coverage:
    # Nottebohm 61 -> 72 located of 205 headers, Beethoven 5 27 -> 33 of 396,
    # nothing else on either page changing.
    #
    # It applies ONLY to ink standing clear of the staff's own five lines (see
    # `on_staff` in `header_ink.cluster_components`). Ink that touches the
    # staff belongs to whatever glyph is printed there, however the morphology
    # broke it up, and is never separated. Without that restriction the rule
    # takes a scanned treble clef apart at the waist and reads the upper half
    # as an alto clef — seventeen invented clefs over twenty pages of
    # Beethoven 5. The tolerance is then bounded by two well-separated
    # populations: a glyph's own internal gaps are under half a space (the G
    # clef's tail detaches at 0.49), a heading stands 1.68 spaces clear at the
    # median, and 1.0 sits between them.
    #
    # It was held back for two sessions on the strength of "14 staves right and
    # 5 wrong", a count taken when no corpus could see either number — the four
    # corpora of the day contained no bass clef the locator was liable to
    # misread, so they reported FALSE POSITIVES 0 whatever it did. Measured
    # against `beethoven5-clef-sweep.json`, which is built from the locator's
    # own reads and therefore cannot have that blind spot:
    #
    #     arm            located   orch misses   sweep misses   FALSE POS
    #     off                 69             6             10           6
    #     ON (this)           77             5              7           7
    #
    # Eight more located clefs and four fewer misses for ONE more false
    # positive. The RATE is what this layer trades on — 6/69 against 7/77, flat
    # — and "coverage bought at a worse precision than the layer already has"
    # is the trade it refuses; this is not that. Nottebohm coverage 69 -> 77 of
    # 206 headers, reference 5/5 and piano 0 unchanged.
    cluster_y_gap_spaces: float | None = 1.0
    min_component_area_spaces: float = 0.02  # speck filter, in (staff space)²
    vertical_rule_max_width_spaces: float = 0.5   # thinner ⇒ a rule, not a glyph
    vertical_rule_min_height_spaces: float = 2.0
    # A system barline or bracket is drawn heavier than a plain barline — wide
    # enough to clear the width test above — but it runs the whole height of
    # the system, joining staff to staff. Nothing that long can be part of a C
    # clef, so length identifies it where width alone cannot. The floor is the
    # tallest a C clef is allowed to be (`max_height_spaces`), which keeps the
    # two rules from ever disagreeing about the same object.
    heavy_rule_max_width_spaces: float = 1.2
    heavy_rule_min_height_spaces: float = 5.0
    # Ink with less vertical extent than this is a staff-line fragment, not
    # part of a glyph — see _drop_flat_residue.
    min_ink_height_spaces: float = 0.2
    # An F clef's two dots: round, of this size, sitting in the right-hand
    # part of the glyph, aligned in x and about one staff space apart —
    # because they straddle the line the clef names. See _has_f_clef_dots.
    dot_min_size_spaces: float = 0.22
    dot_max_size_spaces: float = 0.75
    # A worn dot is not round: the staff-line stripper leaves a stub where the
    # line ran under it and the dot inherits it, so the pair on Beethoven 5
    # p.54 staff 8 measures 0.59 x 0.86 and 0.64 x 1.00 — widths still exactly
    # dot-sized, heights half again too big. Loosening the HEIGHT bound alone
    # (to ~1.15, with a matching-widths test to pay for it) does veto that F
    # clef, and it was measured and NOT shipped: it costs two real orchestral C
    # clefs and one Nottebohm cell, while its benefit appears in no corpus,
    # because none contains a bass clef read as a C clef. See RESULTS.md —
    # "the veto could not see the dots". The corpus is the next step, not the
    # threshold.
    dot_max_height_spaces: float = 0.75
    dot_min_aspect: float = 0.65
    dot_max_aspect: float = 1.5
    dot_pair_max_width_diff_spaces: float | None = None
    dot_right_fraction: float = 0.55   # dots sit right of the glyph's middle
    # A SECOND, looser reading of the same two dots, admitted only where they
    # stand clear of the body — past its right edge rather than merely right of
    # its middle. Everything the strict bounds above accept is still accepted
    # exactly as before, so this can only ever ADD a veto.
    #
    # This is what the earlier height loosening got wrong, and the corpora now
    # say so in one line. Loosening the height alone, at the old 0.55 position,
    # vetoes 5 misreads and costs 3 real C clefs; requiring the same dots to sit
    # past the body's right edge costs **zero** real clefs at EVERY height and
    # aspect tried, on both editions:
    #
    #     position    height   aspect      false pos. vetoed   real clefs lost
    #     >= 0.55w      0.95    <= 1.5              5                 3
    #     >= 0.55w      1.15    <= 1.5              5                 4
    #     >= 1.00w      0.95    <= 1.5              5                 0
    #     >= 1.00w      1.15    <= 2.2              8                 0
    #     >= 1.00w      1.40    <= 3.0              8                 0
    #
    # The reason is structural rather than lucky. A C clef's near-pair is made
    # of fragments of its OWN strokes, which live inside the glyph; an F clef's
    # dots are printed clear of it. Position separates the two populations
    # completely, which is why the cost column is identically zero across the
    # whole grid — so the shape bounds below only govern how many F clefs are
    # caught, never how many C clefs are lost, and being generous with them
    # risks a missed veto rather than a wrong one.
    #
    # The height reaches 1.25 because a worn dot is not round: the staff-line
    # stripper leaves a stub where the line ran under it, and the pair on
    # Beethoven 5 p.54 staff 8 measures 0.86 and 1.00 tall against widths of
    # 0.59 and 0.64. The aspect reaches 2.2 for the mirror case, a dot the
    # stripper has cut flat. Both sit inside a plateau rather than at its edge.
    dot_clear_right_fraction: float = 1.0
    dot_clear_max_height_spaces: float = 1.25
    dot_clear_max_aspect: float = 2.2
    # NOT loosened, and measured: dropping `dot_min_aspect` from 0.65 to 0.45
    # costs 2 real C clefs and to 0.30 costs 4, at every height. A shape that
    # tall and narrow is a stroke, not a dot, wherever it stands.
    dot_clear_min_aspect: float = 0.65
    # Accept ONE dot standing clear of the body, without its partner.
    #
    # OFF. It was taken deliberately on 2026-08-31 and reverted the same day,
    # when a wider ground truth showed the trade running the other way — and
    # the reason the first measurement misled is worth more than the rule.
    #
    # The sweep corpora said it removed 8 false positives for 16 declined C
    # clefs: a bad ratio, but defensible, because a declined C clef leaves its
    # staff on the default it would have had anyway while an accepted F clef
    # transposes every note on it.
    #
    # Then `orchestral-clef-truth.json` widened from 4 pages to 10 — every
    # staff on the page read by eye rather than only the ones the locator fires
    # on — and measured the same rule against an unbiased population:
    #
    #                                   veto on   veto off
    #     C clefs located                     8         13
    #     false positives                     0          1
    #     C clefs lost to this veto           6          0
    #
    # FIVE real C clefs for ONE false positive, recall a third of the page
    # against more than half. **A sweep corpus is built from the candidates the
    # locator FIRES on, so it oversamples exactly the staves where it produces
    # something, and it cannot answer "what does this rule cost in the wild".**
    # It was the wrong instrument, read carefully.
    #
    # The mechanism stays because it is measured and the arm is worth being
    # able to reproduce: `probe_cluster_too_big.py --single-dot` turns it on.
    # Only a CLEAR-tier dot ever counted — a lone dot-shaped component inside
    # the body is a C clef's own stroke fragment, and 109 of 123 real clefs
    # have one.
    dot_single_clear_is_enough: bool = False
    dot_max_dx_spaces: float = 0.30
    dot_min_dy_spaces: float = 0.60
    dot_max_dy_spaces: float = 1.50
    # How far PAST the candidate's own box to look for those dots.
    #
    # They are part of the glyph but they are not always part of the candidate:
    # what bounds a candidate is the clustering and the `header_frac` strip, and
    # neither knows about F clefs. Measured on Beethoven 5 p.54 staff 8 — a bass
    # clef read as an alto clef — the body ends exactly at the strip's right
    # edge and both dots sit beyond it, so the veto was being asked to find them
    # in pixels it had never been shown. Nothing was merged and no threshold was
    # wrong; the evidence was simply outside the frame.
    #
    # 1.5 spaces reaches the dots of every F clef in the corpora and stops well
    # short of the first notehead. The search also runs on the FULL mask rather
    # than the header strip, for the same reason.
    dot_search_right_spaces: float = 1.5
    # Staff spacing, in pixels, that the shape analysis is done at. Cells
    # arrive at whatever scale their measure width happened to force — a
    # narrow measure is upscaled far more than a wide one — and morphology is
    # not scale-free in practice even when its kernels are: heavy upscaling
    # interpolates ink fatter, and glyphs that stand apart at one scale fuse
    # at another. Normalising first means every constant above describes the
    # same thing on every page. 22px keeps the archaic clef's thinnest stroke
    # a few pixels wide, which is enough to survive and thin enough to stay
    # separate from its neighbours.
    analysis_spacing_px: float = 22.0
    # How far beyond the staff's own lines a component may be centred and
    # still belong to this staff — see the band filter in locate_clef. A C
    # clef on the bottom line reaches about two spaces below it; anything
    # centred further out belongs to the neighbouring staff.
    staff_band_spaces: float = 2.2
    # A clef is printed ON the staff. A cluster that ends before the staff's
    # own five lines begin is standing in the margin, so whatever it is, it is
    # not this staff's clef — and it is skipped rather than stopped for, on
    # exactly the reasoning the ink-fraction and minimum-width tests already
    # use: a cluster is only worth STOPPING for if it could be the clef, and
    # the real one is further right.
    #
    # This exists because a second edition showed a false-positive family the
    # first could not. Edition Peters prints the stacked instrument numbers
    # (1/2, 1/2/3) and the brace's curl to the LEFT of the system's bracket,
    # close enough to fall inside the header window — and a column of two or
    # three numerals is glyph-sized and vertically symmetric, because a column
    # of numerals is. No shape gate can refuse them; they really are symmetric.
    # Their POSITION is what gives them away. Twenty-four of the forty-one
    # false positives on `mahler5-clef-sweep.json` are that family, and none
    # appear in `beethoven5-clef-sweep.json` at all.
    #
    # `probe_false_positive_geometry.py` measured the ceiling before this was
    # written: 27 of Mahler's 40 removed for 2 of its 64 real clefs, and
    # exactly neutral on Beethoven, whose false positives are all real clefs
    # misread in the place a clef belongs. Set False to measure the other arm.
    require_cluster_on_staff: bool = True
    # How the staff's left edge is found: the leftmost horizontal run at least
    # this many spaces long. Length is what identifies a staff line, and the
    # bound is not cosmetic — at analysis scale a bold serif's crossbar clears
    # a 1.5-space horizontal opening, so the instrument name and the numerals
    # themselves leave "horizontal" fragments at the very left of the window.
    # Taking the leftmost horizontal ink instead reported that EVERY staff
    # begins at column 0, and the rule did nothing.
    staff_line_min_length_spaces: float = 4.0
    # How far into its own header window a staff may appear to begin before
    # the measurement is disbelieved and the margin test abstains.
    #
    # It exists because the one genuine clef this rule cost was p48 s12 of the
    # Mahler sweep, where the printed lines are so broken at the head of the
    # system that no run four spaces long exists until 6.8 spaces in — past
    # the clef — so the clef was judged to be in the margin. The window is
    # biased left by half a space plus the bracket and the instrument name; a
    # staff that seems to start further in than THAT has not been measured, it
    # has been lost.
    #
    # Measured over all 174 staves of both sweep corpora: every one of them
    # lands between 0 and 3.55 spaces except p48 s12, which lands at 6.77.
    # The next-highest value is 3.55 and the gap above it is 3.2 spaces wide —
    # wider than the whole spread of the rest of the population — so unlike
    # the tenor symmetry floor this bound is not fitted to one edition's ink.
    # It abstains on exactly one staff in two editions, and that staff is
    # precisely the one where the measurement is known to be wrong.
    #
    # The alternative was to fix the OPERATOR — measure the staff's left edge
    # from the band ink profile the way `staff_header._walk_left` does, so a
    # broken line is bridged. That was built and measured, and every version
    # of it that recovered p48 s12 cost more false positives than it saved:
    # the ink that lets you follow a broken staff line is the same ink that
    # lets an instrument name look like one. See RESULTS.md.
    staff_left_max_spaces: float = 4.0


DEFAULT_LOCATOR_CONFIG = ClefLocatorConfig()


@dataclass(frozen=True)
class LocatedClef:
    """A C clef found by shape alone.

    read:      the resolved clef, line included — the same `ClefRead` type the
               detector path produces.
    bbox:      (x, y, w, h) of the ink cluster, canonical coordinates.
    symmetry:  how symmetric the cluster's vertical ink profile is, 0…1.
    """

    read: ClefRead
    bbox: tuple[int, int, int, int]
    symmetry: float
    #: Indices into the caller's `occupied_boxes` that this read OVERRODE —
    #: notehead boxes standing on clef-sized ink at the header (ROADMAP 2.11).
    #: Empty on every ordinary read, so a caller that ignores it sees no
    #: change. It is the CONNECTION the notehead refusal reads: the boxes
    #: named here are the ones the clef says are not noteheads.
    overrode_occupied: tuple[int, ...] = ()


def _analysis_scale(spacing: float, config: ClefLocatorConfig) -> float:
    """Factor to resize a cell by so its staff spacing becomes the analysis
    spacing. Never upscales — inventing pixels cannot add detail, and the
    tuned kernels behave fine on a cell that is already small.
    """
    if spacing <= 0:
        return 1.0
    return min(1.0, config.analysis_spacing_px / spacing)


def _ink_mask(
    cell: MeasureCell, spacing: float, config: ClefLocatorConfig
) -> np.ndarray | None:
    """Binary ink mask (255 = ink) for the cell, with rules removed.

    Starts from the staff-line-removed variant when there is one, but does not
    rely on it: on old engravings with thick, uneven lines it leaves most of
    the staff behind — which is exactly the material this locator exists for.
    Vertical rules go first, while the barline is still whole; stripping the
    horizontals first would cut it into short pieces that no longer look like
    a rule.
    """
    img = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    if img is None or img.size == 0:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    scale = _analysis_scale(spacing, config)
    if scale < 1.0:
        gray = cv2.resize(
            gray,
            (max(1, int(round(gray.shape[1] * scale))),
             max(1, int(round(gray.shape[0] * scale)))),
            interpolation=cv2.INTER_AREA,
        )
        spacing = spacing * scale
    # Phase 1 convention: 255 = paper, 0 = ink.
    _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    mask = _strip_vertical_rules(mask, spacing, config)
    mask = _strip_horizontal_rules(mask, spacing)
    return _drop_flat_residue(mask, spacing, config)


def _staff_left_column(
    cell: MeasureCell, spacing: float, config: ClefLocatorConfig
) -> int | None:
    """The column where this staff's printed lines begin, in ANALYSIS space,
    or None when they cannot be found.

    Deliberately measured on `cell.image` and not on the staff-line-removed
    variant `_ink_mask` prefers: here the lines ARE the measurement. On the
    prints this locator exists for the removal leaves most of them behind
    anyway, but relying on that would make the answer depend on how well an
    upstream step worked.

    A staff line is identified by LENGTH — it is the one horizontal that runs
    the width of the cell. See `staff_line_min_length_spaces` for what happens
    when it is identified by position instead.
    """
    img = cell.image
    if img is None or img.size == 0:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    # The same resize `_ink_mask` performs, so the column it returns is
    # directly comparable with a cluster's bbox.
    scale = _analysis_scale(spacing, config)
    if scale < 1.0:
        gray = cv2.resize(
            gray,
            (max(1, int(round(gray.shape[1] * scale))),
             max(1, int(round(gray.shape[0] * scale)))),
            interpolation=cv2.INTER_AREA,
        )
        spacing = spacing * scale
    _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    k = max(3, int(round(1.5 * spacing)))
    horiz = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1))
    )
    n, _labels, stats, _c = cv2.connectedComponentsWithStats(horiz, connectivity=8)
    long_enough = config.staff_line_min_length_spaces * spacing
    lefts = [int(stats[i, cv2.CC_STAT_LEFT]) for i in range(1, n)
             if stats[i, cv2.CC_STAT_WIDTH] >= long_enough]
    if not lefts:
        return None
    left = min(lefts)
    if left > config.staff_left_max_spaces * spacing:
        # Further in than any staff plausibly starts inside its own header
        # window: the lines are too broken to be followed, and this is a
        # failed measurement rather than a staff that begins late. Abstain —
        # the margin test is off for this cell — instead of rejecting a clef
        # on it. See `staff_left_max_spaces`.
        return None
    return left


def _refine_symmetry_axis(
    mask: np.ndarray, bbox: tuple[int, int, int, int], max_shift: float
) -> tuple[float, float]:
    """Find the axis a cluster balances about, and how well it balances there.
    Returns `(axis_y, score)` — the axis in mask coordinates, and the score in
    0 … 1. The search is confined to `max_shift` pixels either side of the
    box's centre.

    This answers both of the locator's questions at once, because for a C clef
    they are one question. The glyph exists to mark a staff line and is drawn
    balanced about it, so the axis of best symmetry IS the line it names, and
    how well the ink balances there is the evidence that it is a C clef at all.
    A G clef (long tail below) or an F clef (heavy head, dots to one side) has
    no axis that scores well.

    Scoring by mirror OVERLAP rather than correlation is what makes the score
    trustworthy as a gate: ink with no mirror partner adds to the denominator
    only, so a stray fragment that survived the rule stripping is charged
    against the fit instead of quietly moving the answer.

    The bound matters in both directions, and both were learned the hard way.
    Searching WITHOUT one flatters lopsided glyphs — every shape half-balances
    about something — and on real pages it read treble clefs as tenor clefs, 20
    of them across ten pages of Bach. But insisting on the box centre exactly
    is just as wrong the other way, because the centre carries a pixel or two
    of error from whatever ink survived the stripping, and at these sizes a
    pixel or two moved a real clef from 0.77 to 0.70 and lost it. A window
    narrower than half a line spacing forgives the pixel without ever letting
    the axis reach a neighbouring staff line.
    """
    x, y, w, h = bbox
    sub = mask[y : y + h, x : x + w]
    profile = (sub > 0).sum(axis=1).astype(float)
    total = float(profile.sum())
    centre = (len(profile) - 1) / 2.0
    if total <= 0 or len(profile) == 0:
        return float(y + centre), 0.0

    n = len(profile)
    indices = np.arange(n)
    best_axis, best_score = centre, -1.0
    # Half-pixel steps: a glyph balanced between two rows is common at these
    # scales, and rounding it to one of them is itself a measurable error.
    lo = int(np.floor((centre - max_shift) * 2))
    hi = int(np.ceil((centre + max_shift) * 2))
    for doubled_axis in range(lo, hi + 1):
        axis = doubled_axis / 2.0
        mirrored = np.rint(2 * axis - indices).astype(int)
        valid = (mirrored >= 0) & (mirrored < n)
        overlap = np.zeros(n)
        overlap[valid] = np.minimum(profile[valid], profile[mirrored[valid]])
        score = float(overlap.sum() / total)
        if score > best_score:
            best_axis, best_score = axis, score
    return float(y + best_axis), max(0.0, best_score)


def _has_f_clef_dots(
    mask: np.ndarray,
    bbox: tuple[int, int, int, int],
    spacing: float,
    config: ClefLocatorConfig,
) -> bool:
    """Whether a candidate carries an F clef's two dots.

    This is the one veto that catches an F clef reliably, and it works because
    the dots are not decoration: they straddle the line the clef names, which
    is what makes it an F clef. So they are always a pair, always round, always
    about one staff space apart, always aligned in x, and always to the right
    of the body — in any font and any century.

    Needed because an F clef is otherwise a plausible C clef by the numbers.
    Measured on Nottebohm p.31, a bass clef came in at width 2.50, height 2.73
    and symmetry 0.81 — inside the range of every real C clef on the page
    (0.76-0.85). No size or symmetry threshold separates them; the dots do,
    cleanly, and on that page they are the only candidate that has them.

    A wrong clef transposes every note on its staff, so this is worth a veto
    even though it costs nothing on C clefs.
    """
    x, y, w, h = bbox
    if w <= 0:
        return False
    # Look across the body AND a little way past it: the dots belong to the
    # glyph but need not belong to the candidate — see `dot_search_right_spaces`.
    right = min(mask.shape[1], x + w + int(round(config.dot_search_right_spaces * spacing)))
    sub = mask[y : y + h, x:right]
    if sub.size == 0:
        return False
    n, _labels, stats, _c = cv2.connectedComponentsWithStats(sub, connectivity=8)
    dots: list[tuple[float, float]] = []
    for i in range(1, n):
        bw = stats[i, cv2.CC_STAT_WIDTH] / spacing
        bh = stats[i, cv2.CC_STAT_HEIGHT] / spacing
        if not (config.dot_min_size_spaces <= bw <= config.dot_max_size_spaces):
            continue
        aspect = bw / max(bh, 1e-6)
        cx = stats[i, cv2.CC_STAT_LEFT] + stats[i, cv2.CC_STAT_WIDTH] / 2.0
        # Two readings of the same dot, and a component only has to satisfy one.
        #
        # The strict one is unchanged, and is measured against the BODY's
        # middle rather than the widened search window — the test is about
        # where the dots sit on the glyph, and widening the window must not
        # quietly move the line it is measured against.
        #
        # The loose one asks for more position and less shape: a dot standing
        # clear of the body, past its right edge, may be as worn as the
        # staff-line stripper leaves it. A C clef has no ink out there, so
        # nothing is risked; see `dot_clear_right_fraction`.
        strict = (
            config.dot_min_size_spaces <= bh <= config.dot_max_height_spaces
            and config.dot_min_aspect <= aspect <= config.dot_max_aspect
            and cx / w >= config.dot_right_fraction
        )
        clear = (
            config.dot_min_size_spaces <= bh <= config.dot_clear_max_height_spaces
            and config.dot_clear_min_aspect <= aspect <= config.dot_clear_max_aspect
            and cx / w >= config.dot_clear_right_fraction
        )
        if not (strict or clear):
            continue
        if clear and config.dot_single_clear_is_enough:
            # One dot standing clear of the body is enough on its own — the
            # partner is often lost to the morphology on a worn print, and on
            # four staves of the Mahler sweep it does not survive as a separate
            # component at any dilation or search window. See
            # `dot_single_clear_is_enough` for the trade this makes.
            return True
        dots.append((cx, stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] / 2.0, bw))
    for i in range(len(dots)):
        for j in range(i + 1, len(dots)):
            dx = abs(dots[i][0] - dots[j][0]) / spacing
            dy = abs(dots[i][1] - dots[j][1]) / spacing
            dw = abs(dots[i][2] - dots[j][2])
            if (dx <= config.dot_max_dx_spaces
                    and config.dot_min_dy_spaces <= dy <= config.dot_max_dy_spaces
                    and (config.dot_pair_max_width_diff_spaces is None
                         or dw <= config.dot_pair_max_width_diff_spaces)):
                return True
    return False


def _overlaps_any(
    bbox: tuple[int, int, int, int],
    boxes: list[tuple[int, int, int, int]] | None,
) -> bool:
    """Whether `bbox` shares any area with a box the detector already claimed."""
    return bool(_overlapping(bbox, boxes))


def _overlapping(
    bbox: tuple[int, int, int, int],
    boxes: list[tuple[int, int, int, int]] | None,
) -> list[int]:
    """WHICH of `boxes` share area with `bbox`, by index.

    ⚠️ The predicate is unchanged; `_overlaps_any` now asks this one whether
    the list is empty, so there is exactly one intersection test in the module
    and the refusal downstream cites the same boxes the veto would have.
    """
    if not boxes:
        return []
    x, y, w, h = bbox
    out: list[int] = []
    for i, (bx, by, bw, bh) in enumerate(boxes):
        if x < bx + bw and bx < x + w and y < by + bh and by < y + h:
            out.append(i)
    return out


def _overridable_occupancy(
    bbox: tuple[int, int, int, int],
    spacing: float,
    hits: list[int],
    occupied_boxes: list[tuple[float, float, float, float]],
    occupied_classes: list[str] | None,
    claimed_boxes: list[tuple[float, float, float, float]] | None,
    config: ClefLocatorConfig,
) -> tuple[bool, dict]:
    """ROADMAP 2.11 — may this clef-sized cluster survive the boxes on it?

    Sean, 2026-09-23 (`docs/DECISIONS.md`): *"it also looks like the clef box
    is too small. the size of clefs are consistent to the staff and the edge
    of the first measure on the system"*. On Litolff Beethoven 5 p.3 the alto
    C clef of the Viola staff is merged into the staff lines by the plate; the
    detector draws TWO `noteheadBlackOnLine` boxes on it at confidence 0.64
    and 0.36, and a 1-space symbol then vetoes a 4.5-space read. The whole
    staff dies: 48 noteheads boxed, 0 written, every one refused `no_pitch`
    (`benchmarks/omr-notehead-funnel-2026-09/FINDINGS.md`).

    FOUR conditions, and each can fail:

    1. **The caller opted in.** `occupied_classes is None` -> never override.
       The legacy path and `key_signature_locator` pass boxes without classes
       and are bit-identical after this change, which is what keeps a FROZEN
       path frozen (CLAUDE.md §3).
    2. **Every overlapping box is notehead-class.** A rest, a dynamic, an
       accidental or a detected clef standing on this ink is a different
       claim and the veto stands for it.
    3. **Every overlapping box is NOTEHEAD-SIZED, i.e. shorter than a clef.**
       This is Sean's sentence made a test: a box that is ITSELF inside the
       clef height band is not "too small", so it is not obviously the error
       and the veto stands. A notehead is about one staff space tall and 1.3
       wide (CLAUDE.md §10).
    4. **The detector drew NO CLEF BOX on this ink.** ⚠️⚠️ THIS CONDITION WAS
       NOT IN THE FIRST BUILD AND THE MEASUREMENT PUT IT THERE. On Brahms 1
       p.6 `staff/6/1/3` the rule as first written took a staff the detector
       had already read `clefG` at 0.688 and flipped it to `tenor` — a READ
       clef changed, which is the one thing ROADMAP 2.11's gate forbids. The
       detector's clef box sat at x_center 227 and the cluster at 213: the
       SAME INK, claimed by a clef box, not by a notehead box. Sean's
       complaint is that *a notehead box on clef ink is too small to be what
       the ink is*; where the box on that ink IS a clef, the complaint does
       not apply and which clef it is belongs to the clef contest, not to a
       geometric override. `staff/6/0/9` on the same page and `staff/3/0/9`
       on Litolff p.3 — the two staves 2.11 exists for — both have
       `Q.CLEF_GLYPH` ABSTAINED `no_detections`, so the two populations
       separate exactly rather than by a threshold.
       ⚠️ A clef box REFUSES THE OVERRIDE and does NOT become a veto of its
       own: `occupied_boxes` stays notehead-only, so a caller that does not
       opt in to 2.11 is still bit-identical.

    The cluster's own height being in the measured clef band is checked by the
    caller, which is also where `w_spaces`/`h_spaces` are already computed.

    ⚠️ WHAT THIS DOES NOT DO. It does not weaken the symmetry gate, the
    F-clef dot veto or the snap: an overridden cluster still has to pass all
    three to be READ. The occupancy test was a cheap short-circuit in front of
    them, and this removes the short-circuit for one named population only.

    Returns `(allowed, detail)`; `detail` is trace material either way.
    """
    _x, _y, _w, h = bbox
    h_sp = h / spacing if spacing else 0.0
    detail: dict = {
        "n_occupied": len(hits),
        "occupied_classes": ([str(occupied_classes[i]) for i in hits]
                             if occupied_classes else None),
        "occupied_h_spaces": [round(occupied_boxes[i][3] / spacing, 2)
                              for i in hits] if spacing else [],
    }
    if occupied_classes is None:
        detail["override_refused"] = "caller_supplied_no_classes"
        return False, detail
    if not (config.clef_family_min_height_spaces <= h_sp
            <= config.clef_family_max_height_spaces):
        detail["override_refused"] = "cluster_height_outside_clef_band"
        return False, detail
    claimed = _overlapping(bbox, claimed_boxes)
    if claimed:
        detail["override_refused"] = "the_detector_already_boxed_a_clef_here"
        detail["clef_boxes_on_the_cluster"] = len(claimed)
        return False, detail
    for i in hits:
        if i >= len(occupied_classes):
            detail["override_refused"] = "classes_shorter_than_boxes"
            return False, detail
        if not str(occupied_classes[i]).lower().startswith("notehead"):
            detail["override_refused"] = "an_occupying_box_is_not_a_notehead"
            return False, detail
        if spacing and (occupied_boxes[i][3] / spacing
                        >= config.clef_family_min_height_spaces):
            detail["override_refused"] = "an_occupying_box_is_itself_clef_sized"
            return False, detail
    return True, detail


def locate_clef(
    cell: MeasureCell,
    *,
    occupied_boxes: list[tuple[int, int, int, int]] | None = None,
    occupied_classes: list[str] | None = None,
    clef_boxes: list[tuple[int, int, int, int]] | None = None,
    config: ClefLocatorConfig = DEFAULT_LOCATOR_CONFIG,
    geometry: ClefGeometryConfig = DEFAULT_CONFIG,
    trace: dict | None = None,
) -> LocatedClef | None:
    """Locate a C clef at the start of `cell` and name it, or return None.

    `cell` must be a staff-START cell — the clef only appears there, and on an
    interior measure this would happily nominate the first notehead cluster.

    `occupied_boxes` are canonical (x, y, w, h) boxes the detector has already
    identified as noteheads. A clef never overlaps one, so a candidate that
    does is rejected. This matters
    where a cell begins PAST its clef (see NOTES.md on staff x-extent): the
    first cluster is then real notation, and a stacked chord in particular is
    tall, glyph-sized and vertically symmetric enough to pass for a C clef.
    Reusing the detector's own output costs nothing and settles it.

    `occupied_classes`, when given, must be the SMuFL class name of each box
    in `occupied_boxes`, same order. It is what lets ROADMAP 2.11 override the
    rejection above for one named case — notehead-sized boxes standing on
    clef-sized ink at the header, where the box is the error and not the ink
    (`_overridable_occupancy`). Omit it and this call behaves exactly as it
    did before 2.11; the frozen legacy path and `key_signature_locator` omit
    it, so neither changes.

    `clef_boxes` are canonical boxes the detector already called a CLEF. One
    overlapping the cluster REFUSES the 2.11 override — the ink is already
    claimed by a clef, so "the box is too small" is not the complaint and
    which clef it is belongs to the clef contest. It is never a veto in its
    own right, so omitting it also changes nothing.

    `trace`, when given, is filled with why this call came out the way it did —
    the branch that ended it and the geometry of the cluster that ended it, in
    staff spaces. It exists so the coverage measurements in
    `benchmarks/omr-clef-geometry/` are taken from the code that ships rather
    than from a copy of it, which is how the fused-cluster share was first
    mis-attributed to width.
    """
    def _note(reason: str, **fields) -> None:
        if trace is not None:
            trace["reason"] = reason
            trace.update(fields)

    metrics = _staff_metrics(cell)
    if metrics is None:
        _note("no_staff_metrics")
        return None
    spacing, top_y, bottom_y = metrics
    mask = _ink_mask(cell, spacing, config)
    if mask is None:
        _note("no_mask")
        return None
    # Everything below is measured in ANALYSIS space — the cell resized so its
    # staff spacing is `analysis_spacing_px`. Convert the inputs into it, and
    # the one output (the named line) back out at the end.
    scale = _analysis_scale(spacing, config)
    spacing *= scale
    top_y *= scale
    bottom_y *= scale
    staff_line_ys = [y * scale for y in sorted(cell.staff_line_ys_canonical)]
    occupied_boxes = [
        (x * scale, y * scale, w * scale, h * scale)
        for (x, y, w, h) in (occupied_boxes or [])
    ]
    clef_boxes = [
        (x * scale, y * scale, w * scale, h * scale)
        for (x, y, w, h) in (clef_boxes or [])
    ]
    cell_width = mask.shape[1]

    # Search the header strip only. The clef is the first thing on the staff,
    # and limiting the x-range keeps note ink from ever becoming a candidate.
    hw = max(1, int(round(cell_width * config.header_frac)))
    strip = mask[:, :hw]

    n, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        strip, connectivity=8
    )
    min_area = config.min_component_area_spaces * spacing * spacing
    # A cell is taller than its own staff, so it catches ink from the staves
    # above and below — on closely-spaced systems their clefs and noteheads
    # land in this crop too, and grouping them in produces one tall blob that
    # looks like nothing. Keep only components CENTRED on this staff's band.
    # Note the test is on the centre, not the extent: a glyph is measured at
    # its true full height afterwards, so a tall G clef still reads as a tall
    # G clef and gets rejected on height, instead of being clipped to the band
    # and passing as a C clef.
    band_margin = config.staff_band_spaces * spacing
    band_top, band_bottom = top_y - band_margin, bottom_y + band_margin
    boxes: list[tuple[int, int, int, int, int]] = []
    for i in range(1, n):  # 0 is background
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        y_i = int(stats[i, cv2.CC_STAT_TOP])
        h_i = int(stats[i, cv2.CC_STAT_HEIGHT])
        if not (band_top <= y_i + h_i / 2.0 <= band_bottom):
            continue
        boxes.append(
            (
                int(stats[i, cv2.CC_STAT_LEFT]),
                y_i,
                int(stats[i, cv2.CC_STAT_WIDTH]),
                h_i,
                area,
            )
        )

    clusters = _cluster_components(
        boxes,
        max_gap=config.cluster_gap_spaces * spacing,
        max_y_gap=(
            None if config.cluster_y_gap_spaces is None
            else config.cluster_y_gap_spaces * spacing
        ),
        on_staff=(top_y, bottom_y),
    )
    if trace is not None:
        trace["spacing_px"] = round(spacing, 2)
        trace["clusters"] = [
            {"x": round(cx / spacing, 2), "y": round(cy / spacing, 2),
             "w": round(cw / spacing, 2), "h": round(ch / spacing, 2)}
            for cx, cy, cw, ch in clusters
        ]
    if not clusters:
        _note("no_clusters")
        return None

    # Where the staff itself starts, for the margin test below. Measured once
    # per cell rather than per cluster, and only when the test is on.
    staff_left = (
        _staff_left_column(cell, metrics[0], config)
        if config.require_cluster_on_staff else None
    )
    skipped_off_staff = 0

    for bbox in clusters:
        x, y, w, h = bbox
        w_sp, h_sp = w / spacing, h / spacing
        if staff_left is not None and x + w <= staff_left:
            # In the margin, before the staff's lines begin — the instrument
            # numbers, the brace's curl, the part name. Not this staff's clef,
            # and not worth stopping for either: the clef is further right,
            # behind the bracket. See `require_cluster_on_staff`.
            skipped_off_staff += 1
            continue
        if x / spacing > config.max_start_spaces:
            # Too far in to be a clef, and everything further right is further
            # still — whatever is at the head of this staff, we didn't find it.
            _note("too_far_right", start_spaces=round(x / spacing, 2))
            return None
        ink = int(np.count_nonzero(strip[y : y + h, x : x + w]))
        if w * h == 0 or ink / float(w * h) < config.min_ink_fraction:
            # Not a glyph at all — scattered specks that x-clustering has
            # drawn one box around. This test comes BEFORE the size test on
            # purpose. A cluster is only worth stopping for if it is a glyph,
            # and stripping the system brace leaves a trail of fragments down
            # the left edge that are individually far too small to be anything:
            # on Nottebohm p.164 five specks totalling 6% of their bounding box
            # made a 0.8 x 6.0-space "cluster", the size test read it as a G
            # clef and stopped, and the real C clef 1.5 spaces to its right —
            # 2.3 x 3.2 spaces, textbook — was never looked at.
            continue
        if w_sp < config.min_width_spaces:
            # Narrower than any clef, whatever its height — so it cannot be the
            # G or F clef the size test below is meant to stop for. Same
            # reasoning as the ink test above, and the same failure without it:
            # a 0.55 x 6.5-space rule remnant at the very left of the header
            # read as "bigger than any C clef", stopped the search, and the
            # textbook 2.1 x 2.9-space clef two spaces to its right was never
            # looked at.
            continue
        if h_sp > config.max_height_spaces or w_sp > config.max_width_spaces:
            # Glyph-sized but bigger than any C clef — overwhelmingly a G clef,
            # which is exactly two-thirds of all clefs. STOP here rather than
            # look past it. Scanning on was the locator's one dangerous bug: a
            # treble clef would be skipped for being too tall and the key
            # signature's sharp behind it — narrow, tall, and beautifully
            # symmetric — would be read as the staff's clef instead. A real
            # clef is solid enough to clear the ink test above, so it still
            # stops here.
            _note(
                "too_big",
                w_spaces=round(w_sp, 2),
                h_spaces=round(h_sp, 2),
                too_tall=h_sp > config.max_height_spaces,
                too_wide=w_sp > config.max_width_spaces,
            )
            return None
        if h_sp < config.min_height_spaces:
            continue  # debris: a fragment, a speck, a rule that survived

        overrode: tuple[int, ...] = ()
        hits = _overlapping(bbox, occupied_boxes)
        if hits:
            allowed, occ_detail = _overridable_occupancy(
                bbox, spacing, hits, occupied_boxes, occupied_classes,
                clef_boxes, config)
            if not allowed:
                # The head of this staff is a notehead or a rest, so the clef
                # is not in this cell at all. Stop, exactly as for a G clef.
                _note("occupied", w_spaces=round(w_sp, 2),
                      h_spaces=round(h_sp, 2), **occ_detail)
                return None
            # ROADMAP 2.11 — the boxes are too small to be what this ink is.
            # Keep going: symmetry, the F-clef dots and the snap still have to
            # agree before anything is read.
            overrode = tuple(hits)

        # Measure symmetry about the axis the ink actually balances on, searched
        # within a bounded window around the box centre. Bounded matters both
        # ways: an UNCONSTRAINED search flatters lopsided glyphs — every shape
        # half-balances about something — and on real pages that read treble
        # clefs as tenor clefs. But insisting on the box centre exactly is just
        # as wrong in the other direction, because the box centre carries a
        # pixel or two of error from whatever ink survived the stripping, and
        # at these sizes a pixel or two was enough to flip a real clef from
        # 0.77 to 0.70 and lose it. The window is narrower than half a line
        # spacing, so the axis can never reach a neighbouring staff line.
        axis_y, symmetry = _refine_symmetry_axis(
            strip, bbox, max_shift=config.axis_refine_spaces * spacing
        )
        if symmetry < config.min_symmetry:
            # Not a C clef. Stop rather than look further right: whatever sits
            # at the head of the staff is what the clef would have been, and
            # scanning on would only find noteheads to misread.
            _note("asymmetric", w_spaces=round(w_sp, 2), h_spaces=round(h_sp, 2),
                  symmetry=round(symmetry, 3))
            return None
        if _has_f_clef_dots(mask, bbox, spacing, config):
            _note("f_clef_dots", w_spaces=round(w_sp, 2), h_spaces=round(h_sp, 2),
                  symmetry=round(symmetry, 3))
            return None  # an F clef wearing a C clef's proportions

        # Hand the measurement to the same resolver the detector path uses, so
        # a located clef is named exactly as a detected one is — the only
        # difference being that here the named line was measured from the ink
        # rather than inferred from a box.
        read = resolve_clef(
            "cClefAlto",
            anchor_y=axis_y,
            staff_line_ys=staff_line_ys,
            config=geometry,
        )
        if read is None or read.source != "geometry":
            _note("ambiguous_snap", w_spaces=round(w_sp, 2), h_spaces=round(h_sp, 2),
                  symmetry=round(symmetry, 3))
            return None  # the snap was ambiguous — abstain
        if (read.name == "mezzosoprano"
                and symmetry < config.min_symmetry_mezzosoprano):
            _note("mezzosoprano_symmetry", w_spaces=round(w_sp, 2),
                  h_spaces=round(h_sp, 2), symmetry=round(symmetry, 3))
            return None  # see `min_symmetry_mezzosoprano`
        # Report the box in the cell's own coordinates, not analysis space.
        # ⚠️ `w_spaces`/`h_spaces` ARE RECORDED ON THE READ, not only on the
        # refusals. Until 2.11 a successful read carried a canonical bbox and
        # nothing else, so the only way to ask how tall a located clef was in
        # STAFF SPACES was to divide by a spacing the record does not carry
        # for the header crop — which reads back heights ABOVE this locator's
        # own ceiling. The measurement that produced `clef_family_*` had to
        # throw the header arm away for exactly that reason.
        _note("located", w_spaces=round(w_sp, 2), h_spaces=round(h_sp, 2),
              symmetry=round(symmetry, 3), clef=read.name)
        inv = 1.0 / scale if scale else 1.0
        return LocatedClef(
            read=read,
            bbox=tuple(int(round(v * inv)) for v in bbox),
            symmetry=round(symmetry, 4),
            overrode_occupied=overrode,
        )

    if skipped_off_staff:
        # Reported apart from `only_debris` because the cause is different and
        # the remedy would be too: there WAS glyph-sized ink in this header,
        # standing in the margin rather than on the staff.
        _note("off_staff_only", skipped_off_staff=skipped_off_staff)
        return None
    _note("only_debris")
    return None
