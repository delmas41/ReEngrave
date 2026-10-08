"""ROADMAP 2.56b: which staff owns a far head -- read off its LEDGERS.

Sean (CLAUDE.md §10, 2026-09-28/29): the ledger lines name the owner and are
authoritative; a far note has ledgers TOWARD its own staff and none toward the
other; nearness is only a hint; "no rungs either way" is our failure.

Three layers, each with a control that can fail:

  * `far_head_owner` -- the note-first look run toward EACH candidate staff:
    exactly one fitting staff owns the head; both or neither say nothing.
  * `gather` -- files one `Q.FAR_HEAD_OWNER_LEDGER` row per candidate, only
    behind `OMR_FARHEAD_OWNER_LEDGERS` (default ON since 2026-10-07).
  * `adjudicate_glyph_owner` -- reads it AHEAD of distance, and stays silent
    (the older tiers run as before) where the witness cannot say.

RUN RED FIRST: against the tree before this item there is no
`far_head_owner`, no `Q.FAR_HEAD_OWNER_LEDGER`, no `FARHEAD_OWNER_ENV`.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import cv2
import numpy as np

from tools.omr.annotate import far_head_owner as FO
from tools.omr.annotate import far_head_reader as FH
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401 -- registers decisions
from tools.omr.staged import gather
from tools.omr.staged.record import (Log, Outcome, Q, cell as R_cell,
                                     glyph as R_glyph)

SP = 20.0
TOP_A = 200.0
TOP_B = 560.0                                # 18 spaces below A's top line
LINES_A = [TOP_A + SP * i for i in range(5)]  # 200..280
LINES_B = [TOP_B + SP * i for i in range(5)]  # 560..640
HEAD_W, HEAD_H = 28.0, 21.0
SHAPE = dict(long_sp=1.4, short_sp=1.05, tilt=28.0)
CX = 300.0
A_KEY, B_KEY = "staff/0/0/0", "staff/0/0/1"


def _page(*, owner, ledgers=True, n_below_a=4, n_above_b=4):
    """A white page: staff A over staff B, 18 spaces apart. A far head either
    `n_below_a` half-steps below A (owner 'A', its ledgers drawn toward A) or
    `n_above_b` half-steps above B (owner 'B', its ledgers drawn toward B).
    Returns (gray, box)."""
    img = np.full((900, 600), 255, np.uint8)
    for y in LINES_A + LINES_B:
        img[int(y) - 1:int(y) + 2, 40:560] = 0
    if owner == "A":
        pos = 8 + n_below_a
        cy = TOP_A + pos * SP / 2.0
        if ledgers:
            for p in range(10, pos + 1, 2):
                y = int(TOP_A + p * SP / 2.0)
                img[y - 1:y + 2, int(CX - 22):int(CX + 22)] = 0
    else:
        pos = -n_above_b
        cy = TOP_B + pos * SP / 2.0
        if ledgers:
            for p in range(-2, pos - 1, -2):
                y = int(TOP_B + p * SP / 2.0)
                img[y - 1:y + 2, int(CX - 22):int(CX + 22)] = 0
    cv2.ellipse(img, (int(CX), int(cy)), (int(HEAD_W / 2), int(HEAD_H / 2)), -28,
                0, 360, 0, -1)
    return img, (CX - HEAD_W / 2, cy - HEAD_H / 2, CX + HEAD_W / 2, cy + HEAD_H / 2)


class _PooledPage(FH.FarHeadPage):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.samples = [dict(SHAPE)] * 8
        self.adopt(FH.pooled_shape(self.samples), "test")


STAVES = [dict(key=A_KEY, lines=LINES_A, x0=40.0, x1=560.0),
          dict(key=B_KEY, lines=LINES_B, x0=40.0, x1=560.0)]


def _ctx(gray, box, own):
    own_lines = LINES_A if own == A_KEY else LINES_B
    top, bot = min(own_lines), max(own_lines)
    cy = (box[1] + box[3]) / 2.0
    pos = int(round((cy - top) / (SP / 2.0)))
    head = dict(subject="glyph/0/0/%s/0/0" % A_KEY[-1], box=box, pos=pos,
                cls="noteheadBlackOnLine", score=0.9, global_lines=own_lines)
    return _PooledPage(gray, [head], [(head["subject"], head["cls"], box)],
                       {A_KEY: LINES_A, B_KEY: LINES_B}), head


class TestTheWitness(unittest.TestCase):
    def _owner(self, gray, box, filed_on):
        ctx, head = _ctx(gray, box, filed_on)
        return FO.owner_by_ledgers(ctx, head["subject"], box, head["cls"],
                                   filed_on, STAVES)

    def test_a_head_filed_on_the_wrong_staff_is_given_to_the_one_its_ledgers_reach(self):
        gray, box = _page(owner="B")                  # B's head, cut from A's cell
        r = self._owner(gray, box, A_KEY)
        self.assertEqual(r["owner"], B_KEY, r)
        self.assertFalse(r["candidates"][A_KEY]["fits"])
        self.assertTrue(r["candidates"][B_KEY]["fits"])

    def test_a_head_filed_on_its_own_staff_stays(self):
        """The positive control: the SAME rule keeps a right head where it is."""
        gray, box = _page(owner="A")
        r = self._owner(gray, box, A_KEY)
        self.assertEqual(r["owner"], A_KEY, r)

    def test_nearness_does_not_decide_when_no_ledger_reaches_either_staff(self):
        """The control that can fail: the same heads with their ledgers ERASED
        are NOT given to the nearer staff -- 'no rungs either way' is our
        failure, and the witness is silent."""
        for who in ("A", "B"):
            gray, box = _page(owner=who, ledgers=False, n_below_a=6, n_above_b=6)
            r = self._owner(gray, box, A_KEY)
            self.assertIsNone(r["owner"], (who, r))

    def test_a_head_on_a_candidates_first_space_needs_no_ledger_there(self):
        gray, box = _page(owner="B", ledgers=False, n_above_b=1)
        r = self._owner(gray, box, A_KEY)
        self.assertEqual(r["owner"], B_KEY, r)
        self.assertEqual(r["candidates"][B_KEY]["reason"], FO.NO_LEDGER_NEEDED)

    def test_a_candidate_that_could_not_be_looked_at_is_not_refuted(self):
        per = {A_KEY: dict(fits=False, unread=True, reason="no_page_shape"),
               B_KEY: dict(fits=True, unread=False, reason="x")}
        self.assertEqual(FO.decide(per), (None, "unread"))

    def test_ledger_ink_that_cannot_be_assembled_is_not_a_refutation(self):
        """A gap under one ledger pitch is two marks of one ledger: there ARE
        rungs toward that staff. (brahms 5/1/2/3/20, tile 12 of the abstain
        sheet, was moved to the neighbour without this.) A gap with room for a
        MISSING ledger, and no rung at all, still refute."""
        too_narrow = "count_does_not_fit (gaps 1.28, 0.66 sp)"
        self.assertTrue(FO.is_unread(too_narrow, {"gaps": [1.28, 0.66]}))
        self.assertFalse(FO.is_unread("count_does_not_fit (gaps 3.0 sp)", {"gaps": [3.0]}))
        self.assertFalse(FO.is_unread("no_rungs", None))
        self.assertTrue(FO.is_unread("no_page_shape", None))
        per = {A_KEY: dict(fits=False, unread=True), B_KEY: dict(fits=True, unread=False)}
        self.assertIsNone(FO.decide(per)[0])

    def test_both_or_neither_is_silent(self):
        both = {A_KEY: dict(fits=True), B_KEY: dict(fits=True)}
        neither = {A_KEY: dict(fits=False), B_KEY: dict(fits=False)}
        self.assertEqual(FO.decide(both)[0], None)
        self.assertEqual(FO.decide(neither)[0], None)

    def test_the_neighbour_is_the_next_staff_in_the_heads_direction(self):
        gray, box = _page(owner="B")
        self.assertEqual(FO.neighbour_staff(box, A_KEY, STAVES)["key"], B_KEY)
        # the same ink, cut from B's cell, looks UP to A
        self.assertEqual(FO.neighbour_staff(box, B_KEY, STAVES)["key"], A_KEY)
        # a head far below B has no staff beyond it
        self.assertIsNone(FO.neighbour_staff((286, 780, 314, 800), B_KEY, STAVES))
        # a head beside its own staff has no direction
        self.assertIsNone(FO.neighbour_staff((286, 230, 314, 250), A_KEY, STAVES))


# --------------------------------------------------------------- the gather
class _Det:
    def __init__(self, box):
        self.smufl_name, self.category, self.confidence = "noteheadBlackOnLine", "notehead", 0.9
        self.x_canonical, self.y_canonical = box[0], box[1]
        self.width_canonical, self.height_canonical = box[2] - box[0], box[3] - box[1]


class _Cell:
    def __init__(self):
        self.page_index, self.staff_index, self.measure_index = 0, 0, 0
        self.bbox_page_px = (0.0, 0.0, 600.0, 900.0)
        self.upscale_factor = 1.0


class _Staff:
    def __init__(self, i, lines):
        self.staff_index, self.line_ys = i, lines
        self.x_start, self.x_end = 40, 560


class _Page_:
    page_index = 0

    def __init__(self, gray):
        self.rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)


class _Pws:
    def __init__(self, gray):
        self.page = _Page_(gray)
        self.staves = [_Staff(0, LINES_A), _Staff(1, LINES_B)]


def _gather(gray, box, *, owner_on):
    log = Log()
    g = R_glyph(0, 0, 0, 0, 0)
    cy = (box[1] + box[3]) / 2.0
    pos = (cy - TOP_A) / (SP / 2.0)
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, pos, reader="geometry",
                frame="cell:0", residual=0.0, rounded=int(round(pos)))
    dets = {R_cell(0, 0, 0, 0).to_key(): [_Det(box)]}
    env = {gather.FARHEAD_OWNER_ENV: "1" if owner_on else "0"}   # default ON since 2026-10-07
    with mock.patch.object(FH, "FarHeadPage", _PooledPage), \
            mock.patch.dict(os.environ, env):
        gather.gather_far_head_ledger_positions(
            log, _Pws(gray), [_Cell()], {0: (0, 0), 1: (0, 1)}, dets, None)
    return log, g


class TestTheGather(unittest.TestCase):
    def test_off_files_nothing(self):
        gray, box = _page(owner="B")
        log, g = _gather(gray, box, owner_on=False)
        self.assertEqual(log.rows(Q.FAR_HEAD_OWNER_LEDGER, g), ())
        self.assertEqual(log.refusals(Q.FAR_HEAD_OWNER_LEDGER, g), ())

    def test_on_files_one_row_per_candidate_under_its_own_reader(self):
        gray, box = _page(owner="B")      # filed on A; A's ladder does not exist
        log, g = _gather(gray, box, owner_on=True)
        rows = log.rows(Q.FAR_HEAD_OWNER_LEDGER, g)
        refs = log.refusals(Q.FAR_HEAD_OWNER_LEDGER, g)
        self.assertEqual([r.detail["candidate"] for r in rows], [B_KEY])
        self.assertEqual(rows[0].reader, "ledger_owner_note_first")
        self.assertEqual(rows[0].value, -4)
        self.assertEqual([(r.detail["candidate"], r.reason) for r in refs],
                         [(A_KEY, "ledger_not_read")])
        self.assertFalse(refs[0].detail["unread"])
        # the position row of the OWN staff is still filed beside it, untouched
        self.assertEqual(log.rows(Q.FAR_HEAD_LEDGER_POSITION, g), ())

    def test_a_head_on_its_own_ladder_files_the_own_row_and_refutes_the_neighbour(self):
        gray, box = _page(owner="A")
        log, g = _gather(gray, box, owner_on=True)
        rows = log.rows(Q.FAR_HEAD_OWNER_LEDGER, g)
        self.assertEqual([r.detail["candidate"] for r in rows], [A_KEY])


# ------------------------------------------------------------ the decision
def _contest(own_distance, other_distance, rows):
    """A glyph filed on A, contested by B; `rows`: [(candidate, position|None,
    unread)] -- the FAR_HEAD_OWNER_LEDGER rows."""
    log = Log()
    g = R_glyph(0, 0, 0, 0, 0)
    for key, dist, own in ((A_KEY, own_distance, True), (B_KEY, other_distance, False)):
        log.observe(g, Q.GLYPH_BAND_DISTANCE, dist, reader="geometry",
                    frame="page", candidate=key, own=own, position_in_candidate=0.0)
    for key, pos, unread in rows:
        if pos is not None:
            log.observe(g, Q.FAR_HEAD_OWNER_LEDGER, pos,
                        reader="ledger_owner_note_first", frame="cell:0",
                        candidate=key, ledger_reason="x",
                        how="note_first")
        else:
            log.abstain(g, Q.FAR_HEAD_OWNER_LEDGER,
                        reader="ledger_owner_note_first", frame="cell:0",
                        reason="ledger_not_read", candidate=key,
                        unread=unread, ledger_reason="x")
    log.freeze()
    return adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.GLYPH_OWNER], g)


class TestTheDecision(unittest.TestCase):
    def test_the_witness_is_declared_and_read(self):
        spec = adjudicate.REGISTRY[Q.GLYPH_OWNER]
        self.assertIn(Q.FAR_HEAD_OWNER_LEDGER, spec.wants)

    def test_the_ladder_beats_distance_both_ways(self):
        """B is the NEARER staff by distance, A holds the only ladder -> A.
        And the mirror: A is nearer, B holds the ladder -> B. Nearness is only
        a hint (CLAUDE.md §10)."""
        v = _contest(9.0, 3.0, [(A_KEY, 12, False), (B_KEY, None, False)])
        self.assertEqual((v.outcome, v.value, v.reason),
                         (Outcome.DECIDED, A_KEY, "ledger_note_first"))
        v = _contest(3.0, 9.0, [(A_KEY, None, False), (B_KEY, -4, False)])
        self.assertEqual((v.outcome, v.value, v.reason),
                         (Outcome.DECIDED, B_KEY, "ledger_note_first"))

    def test_without_the_rows_the_old_tiers_decide_as_before(self):
        """The control that can fail: no witness rows (flag off) -> the verdict
        is NOT `ledger_note_first`."""
        v = _contest(3.0, 9.0, [])
        self.assertNotEqual(v.reason, "ledger_note_first")

    def test_both_fitting_is_silent(self):
        v = _contest(3.0, 9.0, [(A_KEY, 12, False), (B_KEY, -4, False)])
        self.assertNotEqual(v.reason, "ledger_note_first")

    def test_an_unread_candidate_is_silent(self):
        v = _contest(3.0, 9.0, [(A_KEY, None, True), (B_KEY, -4, False)])
        self.assertNotEqual(v.reason, "ledger_note_first")


if __name__ == "__main__":
    unittest.main()


class TestDefault(unittest.TestCase):
    def test_default_is_on(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(gather.FARHEAD_OWNER_ENV, None)
            self.assertTrue(gather._farhead_owner_enabled())
            os.environ[gather.FARHEAD_OWNER_ENV] = "0"
            self.assertFalse(gather._farhead_owner_enabled())
