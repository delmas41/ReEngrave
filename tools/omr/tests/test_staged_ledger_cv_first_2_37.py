"""ROADMAP 2.37 — ledger lines are read by CV FIRST, on every off-staff
notehead, not only a contested one.

Sean, 2026-09-29 (quoted verbatim, overriding the lane's own draft wording):
*"there is no such thing as a far note with no ledger line."* Every notehead
beyond the space just outside the staff (not on the outer line, not in the
first space above/below it) ALWAYS has ledger lines toward its own staff --
standard engraving practice (a printed ledger line is required the moment a
note sits a full space or more past the staff; the exempt first space is the
same convention CLAUDE.md §10 already states for the rest of the ladder
arithmetic, `LEDGER_ROUND_UP`). Three consequences, each pinned below:

1. **Reach.** Before this lane, `gather._observe_ladder`/`_observe_ledger_
   rung_ink` ran ONLY inside a cross-staff CONTEST (`gather.
   gather_ownership_evidence`'s `contests` loop) -- a note the padded cell
   reaches but with no overlapping same-category twin on a neighbour staff
   never had its OWN ladder walked at all. Priced 2026-09-29 against the
   committed acceptance records (`ledger237_price.py`, read-only, one ijson
   stream per record): 1,597 of 4,369 off-staff Litolff noteheads and 3,110
   of 9,110 Brahms were NEVER ASKED. `TestOwnStaffOnlyWalk` below pins the
   fix directly against the real gatherer, and `test_staged_contest_domain.
   py`/`test_staged_dedupe.py` were updated in the same commit (their old
   "a lone glyph produces NO band-distance row" assertions are superseded
   by this ROADMAP item; the SAFETY property those files actually protect
   -- a lone glyph's row can never name a candidate other than its own
   filed staff -- is asserted there directly and still holds).
2. **Ink wins.** A detector `ledgerLine` box is now a corroborating witness
   at a step, never the only one: where this candidate's OWN ink cleanly
   read (never declined) NO thin run at that exact position, the box is
   dropped before the ladder is even walked -- CLAUDE.md's own weight-AB
   survey measured an older checkpoint boxing 58 of 110 sampled Breitkopf
   STAFF LINES as ledgers, so a box with no ink under it is exactly the
   false witness this repairs (`TestInkOverridesAStrayDetectorBox`).
3. **Elimination.** A candidate whose entire required ladder was read
   CLEANLY (never declined) and found NOTHING is REFUTED outright (the
   print always carries those rungs toward the TRUE staff): where every
   rival but one is refuted, the survivor FOLLOWS (`ledger_refuted`, a
   DECIDED verdict, not a guess); where every candidate is refuted, that is
   a READER FAILURE -- a missed rung, a misread head, or a note that is not
   really this far -- counted apart from a legitimate reading gap
   (`ledger_all_refuted`, never `far_no_rungs`) and still never written at
   a guess (CLAUDE.md rule 8). `TestElimination` pins both outcomes and the
   boundary case (the exempt first space needs no ledger and can never be
   refuted).

⚠️ RUN RED FIRST against the tree before this lane (`5173d91c`):
`ownership._ink_refutes_side`, `ownership._ink_overridden_rungs`,
`ownership._ink_clean_negative_ys` and `ownership._eliminate` do not exist,
`ownership.ledger_direction` takes no `refuted=` parameter, and
`gather.gather_ownership_evidence` files a `Q.GLYPH_BAND_DISTANCE` row only
inside a contest -- every test below either fails to import or fails on the
old, narrower behaviour.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import ownership as OWN
from tools.omr.staged.record import Log, Outcome, Q, READERS

# ─────────────────────────────────────────────────────────────────────────────
# Part 1 — the boundary arithmetic: the exempt first space, factored so
# GATHER's new call site and the old ones cannot compute it differently.
# ─────────────────────────────────────────────────────────────────────────────


class TestLedgerExpectedBoundary(unittest.TestCase):

    LINES = [100.0, 110.0, 120.0, 130.0, 140.0]     # spacing 10
    SP = 10.0

    def test_inside_the_staff_is_zero(self):
        self.assertEqual(G._ledger_expected(120.0, self.LINES, self.SP), 0)

    def test_on_the_outer_line_is_zero(self):
        self.assertEqual(G._ledger_expected(140.0, self.LINES, self.SP), 0)

    def test_the_exempt_first_space_is_zero(self):
        """A note 0.5 spaces past the outer line -- standard engraving: no
        ledger is printed for the space immediately outside the staff."""
        self.assertEqual(G._ledger_expected(145.0, self.LINES, self.SP), 0)

    def test_just_past_the_first_space_needs_one_rung(self):
        """0.9 spaces out crosses `LEDGER_ROUND_UP`'s own floor -- a note
        THIS close to the first ledger line already needs it printed."""
        self.assertEqual(G._ledger_expected(149.0, self.LINES, self.SP), 1)

    def test_two_spaces_out_needs_two(self):
        self.assertEqual(G._ledger_expected(160.0, self.LINES, self.SP), 2)

    def test_above_the_staff_is_symmetric(self):
        self.assertEqual(G._ledger_expected(95.0, self.LINES, self.SP), 0)
        self.assertEqual(G._ledger_expected(90.0, self.LINES, self.SP), 1)


class TestSeansThreeStates(unittest.TestCase):
    """Sean, 2026-09-29 (quoted, relayed via the coordinator): *"Any note
    outside of the staff is either touching the outside staff lines,
    touching a ledger line or has one going through it. Any distance more
    than a notehead above the staff has ledger lines involved."* Three
    states, and only the first needs zero ledgers:

      (a) touching the outer staff line, or in the first space outside it
          -- NO ledger. A real notehead sits only at a LINE or a SPACE
          position (gap an integer or half-integer multiple of a staff
          space) -- never in between -- so this state is exactly the two
          discrete positions gap=0 (on the line) and gap=0.5 spaces (the
          first space), never a continuum.
      (b) sitting in the space just beyond a ledger, touching it -- gap =
          1.5, 2.5, ... spaces (an odd half-integer): needs exactly as
          many ledgers as the one it rests against.
      (c) a ledger through its centre -- gap = 1.0, 2.0, ... spaces (a
          whole integer): needs exactly that many.

    `_ledger_expected`'s own `+ LEDGER_ROUND_UP` (0.25) rounding puts its
    zero/one boundary at gap = 0.75 spaces -- exactly midway between the
    two REAL discrete positions on either side of it (0.5 and 1.0), so it
    reproduces Sean's three states exactly: state (a)'s two positions both
    round to 0, and both halves of state (b)/(c) at the very next position
    out (1.0 exactly, 1.5) already round to 1 -- "any distance more than a
    notehead" (~1 space) above the staff always lands past this boundary.
    """

    LINES = [100.0, 110.0, 120.0, 130.0, 140.0]     # spacing 10, outer=140
    SP = 10.0

    def test_state_a_on_the_line(self):
        self.assertEqual(G._ledger_expected(140.0, self.LINES, self.SP), 0)

    def test_state_a_first_space(self):
        self.assertEqual(G._ledger_expected(145.0, self.LINES, self.SP), 0)

    def test_state_c_through_its_centre_first_ledger(self):
        self.assertEqual(G._ledger_expected(150.0, self.LINES, self.SP), 1)

    def test_state_b_space_just_beyond_the_first_ledger(self):
        self.assertEqual(G._ledger_expected(155.0, self.LINES, self.SP), 1)

    def test_state_c_through_its_centre_second_ledger(self):
        self.assertEqual(G._ledger_expected(160.0, self.LINES, self.SP), 2)

    def test_state_b_space_just_beyond_the_second_ledger(self):
        self.assertEqual(G._ledger_expected(165.0, self.LINES, self.SP), 2)


# ─────────────────────────────────────────────────────────────────────────────
# Part 2 — GATHER reach: every off-staff notehead, contested or not.
# ─────────────────────────────────────────────────────────────────────────────

class _Det:
    def __init__(self, name, x, y, w, h, category="notehead"):
        self.smufl_name = name
        self.category = category
        self.x_canonical = x
        self.y_canonical = y
        self.width_canonical = w
        self.height_canonical = h
        self.confidence = 0.8


class _Staff:
    def __init__(self, staff_index, line_ys):
        self.staff_index = staff_index
        self.line_ys = line_ys


class _Cell:
    def __init__(self, staff_index, measure_index):
        self.page_index = 0
        self.staff_index = staff_index
        self.measure_index = measure_index
        self.bbox_page_px = [0.0, 0.0, 2000.0, 2000.0]
        self.upscale_factor = 1.0
        self.image_no_staff = None       # no raster: the ink reader ABSTAINS


class _P:
    page_index = 0


class _PWS:
    def __init__(self, staves):
        self.staves = staves
        self.page = _P()


def _lone_notehead(y_canonical, *, h=18.0):
    """One staff, one notehead, NO rival on any other staff -- the exact
    shape 1,597 (Litolff) / 3,110 (Brahms) real notes had on 2026-09-29."""
    log = Log()
    staves = [_Staff(0, [1100.0, 1110.0, 1120.0, 1130.0, 1140.0])]
    cells = [_Cell(0, 0)]
    dets = {R.cell(0, 0, 0, 0).to_key():
            [_Det("noteheadBlackInSpace", 200.0, y_canonical, 20.0, h)]}
    G.gather_ownership_evidence(
        log, _PWS(staves), cells, {0: (0, 0)}, dets)
    return log


class TestOwnStaffOnlyWalk(unittest.TestCase):
    """ROADMAP 2.37's own-staff-only pass in `gather_ownership_evidence`."""

    def test_a_far_lone_note_now_gets_its_own_ladder_walked(self):
        """y=1213.5 -> 7.35 spaces below the outer line: off-staff, no
        rival anywhere. Before this lane: zero rows. Now: one band-distance
        row (candidate == own staff, `own=True`), and the ink reader is
        ASKED (it abstains for lack of a raster in this fixture, which
        still proves reach -- `TestGatherIntegration` in `test_staged_
        ledger_rung_ink.py` already pins what a REAL raster credits)."""
        log = _lone_notehead(1200.0)          # y_center 1209.0
        log.freeze()
        band = log.rows(Q.GLYPH_BAND_DISTANCE, R.glyph(0, 0, 0, 0, 0))
        self.assertEqual(len(band), 1)
        self.assertEqual(band[0].detail["candidate"], "staff/0/0/0")
        self.assertTrue(band[0].detail["own"])
        ink_rows = log.rows(Q.LEDGER_RUNG_INK, R.glyph(0, 0, 0, 0, 0))
        ink_abstentions = log.refusals(
            Q.LEDGER_RUNG_INK, R.glyph(0, 0, 0, 0, 0))
        self.assertTrue(ink_rows or ink_abstentions,
                        "the ink reader must be ASKED, found or declined")

    def test_a_note_in_the_first_space_needs_no_ledger_and_is_never_asked(self):
        """0.5 spaces below the outer line (y_center 1145.0): the exempt
        first space. No ownership question is raised at all -- there is
        nothing to refute, and Sean's convention does not apply here."""
        log = _lone_notehead(1136.0)           # y_center 1145.0
        log.freeze()
        self.assertEqual(
            log.rows(Q.GLYPH_BAND_DISTANCE, R.glyph(0, 0, 0, 0, 0)), ())
        self.assertEqual(
            log.rows(Q.LEDGER_RUNG_INK, R.glyph(0, 0, 0, 0, 0)), ())
        self.assertEqual(
            log.refusals(Q.LEDGER_RUNG_INK, R.glyph(0, 0, 0, 0, 0)), ())

    def test_an_on_staff_note_is_unaffected(self):
        log = _lone_notehead(1111.0)           # inside the band
        log.freeze()
        self.assertEqual(
            log.rows(Q.GLYPH_BAND_DISTANCE, R.glyph(0, 0, 0, 0, 0)), ())


# ─────────────────────────────────────────────────────────────────────────────
# Part 3 — elimination: refute-and-decide, refute-all-and-abstain.
# ─────────────────────────────────────────────────────────────────────────────

UP = R.staff(0, 0, 0)
DOWN = R.staff(0, 0, 1)
HEAD = R.glyph(0, 0, 0, 0, 0)
UP_LINES = [100.0, 110.0, 120.0, 130.0, 140.0]
DOWN_LINES = [200.0, 210.0, 220.0, 230.0, 240.0]
SP = 10.0


def _cv_row(log, *, candidate, step, want_y, found):
    log.observe(HEAD, Q.LEDGER_RUNG_INK, found, reader=READERS.CV_LEDGER,
                frame="page", candidate=candidate, step=step,
                want_y_page=want_y,
                window_page_px=[490.0, want_y - 1.0, 522.0, want_y + 1.0],
                center=(0.0 if not found else 0.9),
                left=(0.0 if not found else 0.9),
                right=(0.0 if not found else 0.9), adjacent=0.1)


def _cv_decline(log, *, candidate, step):
    log.abstain(HEAD, Q.LEDGER_RUNG_INK, reader=READERS.CV_LEDGER,
                frame="page", reason=R.ABSTAIN.NO_STAFF_GEOMETRY,
                candidate=candidate, step=step, note="window off raster")


def _contest(head_y, *, up_cv=None, down_cv=None):
    """`HEAD` at `head_y`, contested between UP and DOWN, no detector boxes
    anywhere. `up_cv`/`down_cv`: `{step: True|False|"decline"}` -- the SAME
    per-step vocabulary `_observe_ledger_rung_ink` itself writes."""
    log = Log()
    for st, lines in ((UP, UP_LINES), (DOWN, DOWN_LINES)):
        log.observe(st, Q.STAFF_LINES, list(lines), reader=READERS.GEOMETRY,
                    frame="page")
        log.observe(st, Q.STAFF_SPACING, SP, reader=READERS.GEOMETRY,
                    frame="page")
    log.observe(HEAD, Q.GLYPH_BOX, ("noteheadBlackInSpace", 0, 0, 10, 10),
                reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                bbox_page_px=[500.0, head_y - 5.0, 512.0, head_y + 5.0],
                x_center_page=506.0, y_center_page=head_y)
    for st, lines in ((UP, UP_LINES), (DOWN, DOWN_LINES)):
        top, bottom = min(lines), max(lines)
        gap = (top - head_y) if head_y < top else (head_y - bottom)
        log.observe(HEAD, Q.GLYPH_BAND_DISTANCE, max(0.0, gap / SP),
                    reader=READERS.GEOMETRY, frame="page",
                    candidate=st.to_key(), own=(st == UP),
                    position_in_candidate=(head_y - top) / (SP / 2))
    up_bottom = max(UP_LINES)
    down_top = min(DOWN_LINES)
    for k, v in (up_cv or {}).items():
        want = up_bottom + k * SP
        if v == "decline":
            _cv_decline(log, candidate=UP.to_key(), step=k)
        else:
            _cv_row(log, candidate=UP.to_key(), step=k, want_y=want, found=v)
    for k, v in (down_cv or {}).items():
        want = down_top - k * SP
        if v == "decline":
            _cv_decline(log, candidate=DOWN.to_key(), step=k)
        else:
            _cv_row(log, candidate=DOWN.to_key(), step=k, want_y=want,
                   found=v)
    log.freeze()
    adjudicate._ensure_decisions()
    return adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.GLYPH_OWNER],
                                     HEAD)


class TestElimination(unittest.TestCase):
    """`ownership._eliminate`/`_ink_refutes_side`, through the REAL
    `glyph_owner` decision -- head at 176.0: 3.6 spaces below UP (needs 3
    rungs), 2.4 above DOWN (needs 2); both `>= FAR_MIN_RUNGS`."""

    def test_one_side_fully_refuted_the_other_survives_decides_by_elimination(self):
        """UP's all 3 required steps are read CLEANLY and find nothing --
        REFUTED outright. DOWN has no ink coverage at all (an ordinary
        reading gap, not a refutation): it is the only survivor and
        FOLLOWS, not a guess."""
        v = _contest(176.0, up_cv={1: False, 2: False, 3: False})
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, DOWN.to_key())
        self.assertEqual(v.reason, "ledger_refuted")

    def test_both_sides_fully_refuted_abstains_as_a_reader_failure(self):
        """Both ladders read CLEANLY and find nothing -- Sean, 2026-09-29:
        this is never a legitimate `far_no_rungs` gap, it is a READER
        FAILURE, and it is exported exactly like one (`OWNER_NOT_READ_
        REASONS`) but counted under its own name."""
        v = _contest(176.0, up_cv={1: False, 2: False, 3: False},
                    down_cv={1: False, 2: False})
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "ledger_all_refuted")
        self.assertNotEqual(v.reason, "far_no_rungs")

    def test_an_incomplete_reading_never_refutes(self):
        """UP has two of its three steps read False and the THIRD
        DECLINED (the window fell off the raster) -- CLAUDE.md rule 8:
        *cannot tell* never becomes *not there*. Coverage is incomplete, so
        UP is NOT refuted, both sides survive, and the ordinary
        `far_no_rungs` reading gap (unchanged from before this lane) still
        applies."""
        v = _contest(176.0, up_cv={1: False, 2: False, 3: "decline"})
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "far_no_rungs")

    def test_a_found_rung_can_never_be_on_a_refuted_side(self):
        """POSITIVE CONTROL: giving UP one TRUE step among its three makes
        it a genuine (if incomplete) ladder, never `ledger_all_refuted` --
        refutation and a real hit are mutually exclusive by construction."""
        v = _contest(176.0, up_cv={1: True, 2: False, 3: False})
        self.assertNotEqual(v.reason, "ledger_all_refuted")


class TestSingleCandidateElimination(unittest.TestCase):
    """ROADMAP 2.37's own degenerate case -- a far note with NO rival at
    all (the reach fix in Part 2), exercised through the full harness."""

    def _single(self, *, up_cv):
        log = Log()
        log.observe(UP, Q.STAFF_LINES, list(UP_LINES), reader=READERS.GEOMETRY,
                    frame="page")
        log.observe(UP, Q.STAFF_SPACING, SP, reader=READERS.GEOMETRY,
                    frame="page")
        head_y = 176.0
        log.observe(HEAD, Q.GLYPH_BOX, ("noteheadBlackInSpace", 0, 0, 10, 10),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                    bbox_page_px=[500.0, head_y - 5.0, 512.0, head_y + 5.0],
                    x_center_page=506.0, y_center_page=head_y)
        top = min(UP_LINES)
        gap = head_y - max(UP_LINES)
        log.observe(HEAD, Q.GLYPH_BAND_DISTANCE, max(0.0, gap / SP),
                    reader=READERS.GEOMETRY, frame="page",
                    candidate=UP.to_key(), own=True,
                    position_in_candidate=(head_y - top) / (SP / 2))
        up_bottom = max(UP_LINES)
        for k, v in up_cv.items():
            want = up_bottom + k * SP
            _cv_row(log, candidate=UP.to_key(), step=k, want_y=want, found=v)
        log.freeze()
        adjudicate._ensure_decisions()
        return adjudicate.adjudicate_one(
            log, adjudicate.REGISTRY[Q.GLYPH_OWNER], HEAD)

    def test_refuted_with_no_rival_abstains_rather_than_writing_a_guess(self):
        """No candidate to hand it to, and its OWN staff is refuted --
        CLAUDE.md rule 8: abstain, never invent an owner."""
        v = self._single(up_cv={1: False, 2: False, 3: False})
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "ledger_all_refuted")

    def test_not_refuted_with_no_rival_is_decided_exactly_as_before(self):
        """POSITIVE CONTROL: the ordinary (no-contest) scoring already
        decides a lone glyph onto its own staff; this lane must not change
        THAT outcome, only add a new way to abstain."""
        v = self._single(up_cv={1: True, 2: False, 3: False})
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, UP.to_key())


# ─────────────────────────────────────────────────────────────────────────────
# Part 4 — ink wins: a detector box with no ink under it is not a rung.
# ─────────────────────────────────────────────────────────────────────────────

class TestInkOverridesAStrayDetectorBox(unittest.TestCase):

    def test_a_clean_negative_drops_the_detector_rung_at_that_y(self):
        log = Log()
        _cv_row(log, candidate=UP.to_key(), step=1, want_y=150.0,
               found=False)
        log.freeze()
        adjudicate._ensure_decisions()
        ev = adjudicate.Evidence(log, HEAD, adjudicate.REGISTRY[Q.GLYPH_OWNER])
        box_rung = OWN.Rung(key="glyph/x", x0=490.0, x1=522.0, y=150.0,
                            source="detector")
        cv_rung = OWN.Rung(key="cv:1", x0=490.0, x1=522.0, y=999.0,
                           source="cv_ink")
        kept = OWN._ink_overridden_rungs([box_rung, cv_rung], ev,
                                        UP.to_key(), SP)
        self.assertEqual(kept, [cv_rung])

    def test_no_clean_negative_keeps_the_box(self):
        """POSITIVE CONTROL: with no ink reading at all at this Y, the box
        stands -- the override never fires on silence."""
        log = Log()
        log.freeze()
        adjudicate._ensure_decisions()
        ev = adjudicate.Evidence(log, HEAD, adjudicate.REGISTRY[Q.GLYPH_OWNER])
        box_rung = OWN.Rung(key="glyph/x", x0=490.0, x1=522.0, y=150.0,
                            source="detector")
        kept = OWN._ink_overridden_rungs([box_rung], ev, UP.to_key(), SP)
        self.assertEqual(kept, [box_rung])

    def test_a_found_true_reading_never_drops_its_own_box(self):
        """The override only ever fires on a CLEAN False -- a `found=True`
        row (already merged in via `cv_rungs`) must never remove anything."""
        log = Log()
        _cv_row(log, candidate=UP.to_key(), step=1, want_y=150.0, found=True)
        log.freeze()
        adjudicate._ensure_decisions()
        ev = adjudicate.Evidence(log, HEAD, adjudicate.REGISTRY[Q.GLYPH_OWNER])
        box_rung = OWN.Rung(key="glyph/x", x0=490.0, x1=522.0, y=150.0,
                            source="detector")
        kept = OWN._ink_overridden_rungs([box_rung], ev, UP.to_key(), SP)
        self.assertEqual(kept, [box_rung])

    def _two_rung_contest(self, *, refute_step1):
        """UP needs 2 rungs at head_y=160.0 (2.0 spaces below its outer
        line). TWO detector `ledgerLine` boxes: step 2 (y=160.0) sits
        exactly at the head -- its OWN line, which `ladder_side` never
        counts `toward` a staff (CLAUDE.md: "a rung within half a space of
        the head is its own line and names no staff") -- and step 1
        (y=150.0), the ONE rung whose presence is what actually decides
        whether UP's ladder points at all. `refute_step1`: whether the ink
        cleanly reads NO thin run at that exact step."""
        log = Log()
        for st, lines in ((UP, UP_LINES), (DOWN, DOWN_LINES)):
            log.observe(st, Q.STAFF_LINES, list(lines),
                        reader=READERS.GEOMETRY, frame="page")
            log.observe(st, Q.STAFF_SPACING, SP, reader=READERS.GEOMETRY,
                        frame="page")
        head_y = 160.0
        log.observe(HEAD, Q.GLYPH_BOX,
                    ("noteheadBlackInSpace", 0, 0, 10, 10),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                    bbox_page_px=[500.0, head_y - 5.0, 512.0, head_y + 5.0],
                    x_center_page=506.0, y_center_page=head_y)
        for st, lines in ((UP, UP_LINES), (DOWN, DOWN_LINES)):
            top, bottom = min(lines), max(lines)
            gap = (top - head_y) if head_y < top else (head_y - bottom)
            log.observe(HEAD, Q.GLYPH_BAND_DISTANCE, max(0.0, gap / SP),
                        reader=READERS.GEOMETRY, frame="page",
                        candidate=st.to_key(), own=(st == UP),
                        position_in_candidate=(head_y - top) / (SP / 2))
        # the detector's OWN `ledgerLine` boxes, their own glyph subjects
        # nested under HEAD's own cell (`cell_rungs` reads `Q.GLYPH_BOX`
        # SELF_AND_DESCENDANTS off the cell, exactly as the real gatherer
        # files a `ledgerLine` detection).
        for gi, y in ((1, 150.0), (2, 160.0)):
            log.observe(R.glyph(0, 0, 0, 0, gi), Q.GLYPH_BOX,
                        ("ledgerLine", 0, 0, 10, 2), reader=READERS.DETECTOR,
                        frame="cell:0", score=0.8,
                        bbox_page_px=[494.0, y - 1.0, 518.0, y + 1.0],
                        category="ledgerLine")
        if refute_step1:
            _cv_row(log, candidate=UP.to_key(), step=1, want_y=150.0,
                   found=False)
        log.freeze()
        adjudicate._ensure_decisions()
        return adjudicate.adjudicate_one(
            log, adjudicate.REGISTRY[Q.GLYPH_OWNER], HEAD)

    def test_end_to_end_a_refuted_box_no_longer_wins_the_contest(self):
        """The SAME two boxes as the control below, but the ink cleanly
        refutes the one rung that actually matters (step 1) -- UP's
        ladder is no longer complete (found=1, and that one is only its
        OWN line), so it never `points`, unlike the control."""
        v = self._two_rung_contest(refute_step1=True)
        self.assertFalse(v.outcome == Outcome.DECIDED and v.value == UP.to_key()
                         and v.reason in ("ladder", "ledger_direction"),
                         f"UP must not win off the refuted box: {v}")

    def test_CONTROL_the_same_two_boxes_with_no_ink_reading_DOES_win(self):
        """POSITIVE CONTROL: identical geometry, the SAME two boxes, but no
        CV row at all -- both boxes stand uncontradicted, UP's ladder is
        complete (2 of 2, one of them its own line, one genuinely
        `toward`), and it points, exactly as before this lane."""
        v = self._two_rung_contest(refute_step1=False)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, UP.to_key())
        self.assertEqual(v.reason, "ledger_direction")


if __name__ == "__main__":
    unittest.main()
