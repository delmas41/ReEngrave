"""ROADMAP 2.240 step 3 -- the later stages read the page owner (benchmarks/page-ledger-2026-10/FINDINGS.md "step 3").
Synthetic geometry; every CONTROL arm can fail."""
import ast
import os
import pathlib
import unittest
from unittest import mock

import numpy as np

from tools.omr.annotate import far_head_reader as FH
from tools.omr.annotate import ledger_grid as LG
from tools.omr.staged import page_owner as PO
from tools.omr.staged.record import ABSTAIN

SRC = pathlib.Path(PO.__file__)
A, B = "staff/0/0/1", "staff/0/0/2"
STAVES = [dict(key=A, lines=[100.0, 110.0, 120.0, 130.0, 140.0], x0=0.0, x1=1000.0, grid=None),
          dict(key=B, lines=[220.0, 230.0, 240.0, 250.0, 260.0], x0=0.0, x1=1000.0, grid=None)]


class AbstainVocabulary(unittest.TestCase):
    def test_every_abstain_reason_page_owner_files_is_declared(self):
        """Step 2 r2 filed `owner_box_not_one_head` without declaring it: a gather with OMR_PAGE_OWNER ON raised on the first wide head
        box (Litolff pp. 2,4,6,16). Every literal reason `mark_owner` abstains with, and the span abstention, must be in ABSTAIN."""
        tree = ast.parse(SRC.read_text())
        words = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "out" and node.args \
                    and isinstance(node.args[0], ast.Constant) and node.args[0].value == "abstain":
                words.add(node.args[2].value)
            if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "abstain":
                for kw in node.keywords:
                    if kw.arg == "reason" and isinstance(kw.value, ast.Constant):
                        words.add(kw.value.value)
        self.assertIn("owner_box_not_one_head", words)
        missing = sorted(w for w in words if w not in ABSTAIN.all())
        self.assertEqual(missing, [])


def _tile8_page():
    """A staff (lines 100..140, sp 10), a long row of ink one space under it (the slur of tile 8), and a head ON its own short ledger
    two spaces out (row 160)."""
    gray = np.full((400, 200), 255, np.uint8)
    lines = [100.0, 110.0, 120.0, 130.0, 140.0]
    for y in lines:
        gray[int(y) - 1:int(y) + 2, 20:180] = 0
    gray[149:152, 40:160] = 0
    gray[159:162, 85:115] = 0
    yy, xx = np.ogrid[:400, :200]
    gray[((xx - 100) / 7.0) ** 2 + ((yy - 160) / 5.0) ** 2 <= 1] = 0
    return gray, lines, (93.0, 155.0, 107.0, 165.0)


def _slur_row(y):
    return "arc_ink" if 147 <= y <= 153 else None


class GapLookHonoursTheFilter(unittest.TestCase):
    """Tile 8's cause: the owner's filter dropped the slur's row from the WALK's rungs, then the chain [staff edge, note line] had a gap
    with room for one ledger and `find_rung_in_gap` LOOKED at the raster there, found the same slur and counted it as ledger 1."""

    def test_unfiltered_reading_counts_the_row(self):
        gray, lines, box = _tile8_page()
        pos, _why = FH.read_absolute_position(gray, lines, box, "g", [], [], thickness_px=3.0)
        self.assertEqual(pos, 12)                     # ledger 2 below the staff, the row counted as ledger 1

    def test_filtered_reading_no_longer_counts_it(self):
        gray, lines, box = _tile8_page()
        d = {}
        pos, why = FH.read_absolute_position(gray, lines, box, "g", [], [], detail_out=d, thickness_px=3.0, not_ledger=_slur_row)
        self.assertIsNone(pos)
        self.assertIn("count_does_not_fit", why)
        self.assertEqual(d["note_first"]["between"], [])

    def test_CONTROL_step2_filter_alone_lets_the_gap_look_recount_it(self):
        gray, lines, box = _tile8_page()
        with mock.patch.object(LG, "_rung_ok_with", lambda rung_ok, not_ledger: rung_ok):
            pos, _why = FH.read_absolute_position(gray, lines, box, "g", [], [], thickness_px=3.0, not_ledger=_slur_row)
        self.assertEqual(pos, 12)                     # the arm without the fix reads exactly what tile 8 showed

    def test_none_filter_is_bit_identical(self):
        self.assertIsNone(LG._rung_ok_with(None, None))
        f = lambda y: True                            # noqa: E731
        self.assertIs(LG._rung_ok_with(f, None), f)


class FlatTraceIsNotArcInk(unittest.TestCase):
    """The known risk (Litolff p4 bar 3, tile 8's lower staff): the detector boxed the head's own ledger line as a 'tie' and the curve
    tracer followed it (glyph/4/1/1/3/10: 1.78 sp, left and right rows 2433.5) -- `arc_ink` then dropped a REAL ledger."""

    def _maker(self, trace, sp=10.0):
        return PO.not_ledger_maker([("glyph/0/0/1/3/10", "tie", {"trace": trace, "space_page_px": sp})], STAVES)(506.0, B, 4.0)

    def test_flat_short_trace_drops_nothing(self):
        flat = [[x, 199.0, 202.0] for x in range(492, 520)]
        self.assertIsNone(self._maker(flat)(200.5))
        self.assertAlmostEqual(PO.trace_bow_sp(flat, 10.0), 0.0)

    def test_CONTROL_a_bowed_trace_still_drops_its_rows(self):
        bowed = [[x, 199.0 - 3.0 * (1 - ((x - 506) / 14.0) ** 2), 202.0 - 3.0 * (1 - ((x - 506) / 14.0) ** 2)] for x in range(492, 521)]
        self.assertGreaterEqual(PO.trace_bow_sp(bowed, 10.0), PO.ARC_MIN_BOW_SP)
        self.assertEqual(self._maker(bowed)(197.5), "arc_ink")

    def test_unmeasured_spacing_keeps_step2_behaviour(self):
        flat = [[x, 199.0, 202.0] for x in range(492, 520)]
        self.assertEqual(PO.not_ledger_maker([("glyph/0/0/1/3/10", "tie", {"trace": flat})], STAVES)(506.0, B, 4.0)(200.5), "arc_ink")


class ConsumerOwner(unittest.TestCase):
    """Page marks only from boxes ADJUDICATE did not refuse (2.245 hand-off case 1), applied at the consumer by place."""
    DET = {"members": ["glyph/0/0/1/3/5", "glyph/0/0/2/3/3"], "candidates": [A, B],
           "witnesses": {"candidates": [A, B], "ledger": {"glyph/0/0/1/3/5": A, "glyph/0/0/2/3/3": B},
                         "stem": {"glyph/0/0/2/3/3": B}}}

    def test_nothing_refused_is_the_row(self):
        r = PO.consumer_owner("decided", B, "stem", self.DET, [])
        self.assertEqual((r["status"], r["owner"], r["reason"]), ("decided", B, "stem"))

    def test_every_member_refused_gives_no_owner(self):
        r = PO.consumer_owner("decided", A, "ledger", self.DET, self.DET["members"])
        self.assertEqual((r["status"], r["reason"]), ("abstain", "page_owner_all_refused"))

    def test_refused_members_witnesses_do_not_count(self):
        # as filed the two views' ledgers disagree (GUESSED); with the first view refused, the second's ledger + stem decide
        r = PO.consumer_owner("guessed", A, "ledger_views_disagree", self.DET, ["glyph/0/0/1/3/5"])
        self.assertEqual((r["status"], r["owner"], r["reason"]), ("decided", B, "ledger_and_stem:unrefused"))

    def test_CONTROL_inside_staff_is_not_moved_by_a_refused_twin(self):
        r = PO.consumer_owner("decided", A, "inside_staff", self.DET, ["glyph/0/0/1/3/5"])
        self.assertEqual((r["status"], r["owner"], r["reason"]), ("decided", A, "inside_staff"))

    def test_read_flag_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(PO.READ_ENV, None)
            self.assertFalse(PO.read_enabled())
            os.environ[PO.READ_ENV] = "1"
            self.assertEqual(PO.read_enabled(), PO.enabled())
            os.environ.pop(PO.READ_ENV, None)


class DeferredOwners(unittest.TestCase):
    """Tile 8's first cause: a page whose far heads wait for the document head-size pool was given owners BEFORE its ledger readings
    existed, so the record decided its far heads on the stem alone while a re-read of the finished record decided them on the ledger."""

    def test_gather_defers_a_held_page_and_files_it_after_the_pool(self):
        src = pathlib.Path(PO.__file__).with_name("gather.py").read_text()
        i_defer = src.index("_deferred_owners.append(_page_owner.defer_page_owners(")
        i_finish = src.index("    finish_far_head_ledger_positions(log, far_head_state)\n    if _deferred_owners:")
        self.assertLess(i_defer, i_finish)
        self.assertIn('if (_far_census or {}).get("held"):', src)

    def test_defer_keeps_frames_and_marks_only(self):
        class M:
            boxes = [object()]
        with mock.patch.object(PO, "enabled", return_value=True):
            d = PO.defer_page_owners([], {}, M())
        self.assertEqual(d[0], {})
        self.assertIsInstance(d[1], M)
        self.assertIsNone(PO.file_deferred_page_owners(None, None))


class GlyphOwnerReadsThePageOwner(unittest.TestCase):
    """ADJUDICATE's `glyph_owner` with `OMR_PAGE_OWNER_READ`: a contested head filed on B, the NEARER staff (distance would keep it on B),
    whose page owner GATHER decided is A."""

    def _run(self, owner_row, flag="1", refuse=False):
        from tools.omr.staged import adjudicate
        from tools.omr.staged import adjudicators  # noqa: F401
        from tools.omr.staged import record as R
        from tools.omr.staged.record import Log, Q, READERS
        from tools.omr.tests.test_stem_owner_2026_10_08 import A_KEY, B_KEY, LINES_A, LINES_B, SP, HEAD_CY
        log = Log()
        for key, lines in ((A_KEY, LINES_A), (B_KEY, LINES_B)):
            s = R.Subject.from_key(key)
            log.observe(s, Q.STAFF_LINES, lines, reader="cv_lines", frame="page")
            log.observe(s, Q.STAFF_SPACING, SP, reader="cv_lines", frame="page")
        g = R.glyph(0, 0, 1, 0, 0)
        cy = HEAD_CY
        log.observe(g, Q.GLYPH_BAND_DISTANCE, max(min(LINES_B) - cy, cy - max(LINES_B)) / SP, reader="geometry", frame="page",
                    candidate=B_KEY, own=True, position_in_candidate=-3.0)
        log.observe(g, Q.GLYPH_BAND_DISTANCE, max(min(LINES_A) - cy, cy - max(LINES_A)) / SP, reader="geometry", frame="page",
                    candidate=A_KEY, own=False, position_in_candidate=13.0)
        members = [g.to_key()]
        log.observe(g, Q.PAGE_MARK, 7, reader=READERS.CV_PAGE_MARKS, frame="page", family="head", members=members)
        status, reason = owner_row
        if status == "abstain":
            log.abstain(g, Q.PAGE_MARK_OWNER, reader=READERS.CV_PAGE_OWNER, frame="page", reason=reason, page_mark=7, family="head",
                        members=members, candidates=[A_KEY, B_KEY], witnesses={})
        else:
            log.observe(g, Q.PAGE_MARK_OWNER, A_KEY, reader=READERS.CV_PAGE_OWNER, frame="page", status=status, reason=reason,
                        page_mark=7, family="head", members=members, candidates=([A_KEY, B_KEY] if status == "guessed" else [A_KEY]),
                        witnesses={"ledger": {g.to_key(): A_KEY}})
        log.freeze()
        env = {PO.READ_ENV: flag}
        with mock.patch.dict(os.environ, env):
            return adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.GLYPH_OWNER], g), A_KEY, B_KEY

    def test_decided_page_owner_names_the_owner(self):
        v, a, _b = self._run(("decided", "ledger"))
        self.assertEqual((v.value, v.reason), (a, "page_owner"))

    def test_CONTROL_flag_off_the_old_tiers_decide(self):
        v, a, _b = self._run(("decided", "ledger"), flag="0")
        self.assertNotEqual(v.reason, "page_owner")

    def test_guessed_carries_both_staves(self):
        v, a, b = self._run(("guessed", "ledger_views_disagree"))
        self.assertEqual((v.value, v.reason), (a, "page_owner_guessed"))
        self.assertEqual(sorted(c.value for c in v.candidates), sorted([a, b]))

    def test_abstain_leaves_the_old_rule(self):
        v, _a, _b = self._run(("abstain", "owner_no_rungs"))
        self.assertNotIn(v.reason, ("page_owner", "page_owner_guessed"))


class ArcOwnerReadsThePageSpan(unittest.TestCase):
    """`arc_owner` with `OMR_PAGE_OWNER_READ`: an arc box filed on staff 1 that is a piece of a page-wide arc whose end notes are staff 2's."""

    def _run(self, status, flag="1"):
        from tools.omr.staged import adjudicate
        from tools.omr.staged import adjudicators  # noqa: F401
        from tools.omr.staged import record as R
        from tools.omr.staged.record import Log, Q, READERS
        log = Log()
        g = R.glyph(0, 0, 1, 3, 9)
        log.observe(g, Q.ARC_BOX, "slur", reader="detector", frame="page", bbox_page_px=[100.0, 150.0, 200.0, 160.0])
        log.observe(g, Q.PAGE_SPAN, "arc", reader=READERS.CV_PAGE_SPANS, frame="page", pieces=[g.to_key()],
                    owner={"status": status, "owner": B, "reason": "ends_agree" if status == "decided" else "one_end"})
        log.freeze()
        with mock.patch.dict(os.environ, {PO.READ_ENV: flag}):
            return adjudicate.adjudicate_one(log, adjudicate.REGISTRY[Q.ARC_OWNER], g)

    def test_decided_span_owner_names_the_staff(self):
        v = self._run("decided")
        self.assertEqual((v.value, v.reason), (B, "page_span_owner"))
        self.assertEqual(v.detail["moved_from"], A)

    def test_CONTROL_guessed_span_leaves_the_old_rule(self):
        self.assertNotEqual(self._run("guessed").reason, "page_span_owner")

    def test_CONTROL_flag_off(self):
        self.assertNotEqual(self._run("decided", flag="0").reason, "page_span_owner")


if __name__ == "__main__":
    unittest.main()
