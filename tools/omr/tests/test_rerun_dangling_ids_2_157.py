"""ROADMAP 2.157 -- the replay harness (`review.rerun.rebuild_gather`) re-points every row id a GATHER row carries.

Found by 2.153 (holdout FINDINGS 2.153-0): a SLICE of named systems has sparse GATHER ids, the rebuild numbers densely,
and it re-pointed only `basis`. `detail.stem_row_id` / `beam_row_id` then named the wrong row or none, the stem-tip
readers (`rhythm._stem_tip_flag_ink`, the 2.146 tip decision) read nothing, and a slice replay showed 16 judged tiles
"broken" that the record's own commit reproduced. Tooling only: no pipeline output changes.

The end-to-end case is the 2.146 fixture (an up-stem head whose own clean tip decides `stem_tip_reads_no_beam` through
`Q.STEM_TIP_INK.stem_row_id` and `Q.BEAM_STEM_LEVELS.stem_row_id`), sliced the way a slice is cut: an earlier row of
another system dropped. Fails on origin/main d9353217 (the slice replay narrows), passes with the fix."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import READERS, Log, Outcome, Q, Subject, is_row_id, ROW_ID_PREFIXES
from tools.omr.staged.review import rerun as RR
from tools.omr.tests.test_staged_stem_tip_decides_beam_2_146 import _discounted

FLAG = rhythm.STEM_TIP_DECIDES_BEAM_ENV


def _sliced_record():
    """The 2.146 fixture behind one row of ANOTHER system, then that row cut out: sparse ids, as a slice has."""
    log = Log()
    log.observe(R.staff(9, 0, 0), Q.STAFF_LINES, [1.0, 2.0, 3.0, 4.0, 5.0], reader=READERS.GEOMETRY, frame="page")
    g = _discounted(log, tip_found=False, runs=())
    rec = log.to_json()
    rec["observations"] = [o for o in rec["observations"] if not o["subject"].startswith("staff/9/")]
    return rec, g


def _decide(log):
    with mock.patch.dict(os.environ, {FLAG: "1"}):
        adjudicate.run(log)


class TestTheSliceReplaysFaithfully(unittest.TestCase):

    def test_control_the_whole_fixture_decides_from_the_tip(self):
        log = Log()
        g = _discounted(log, tip_found=False, runs=())
        _decide(log)
        self.assertEqual(log.verdict(Q.DURATION, g).reason, "stem_tip_reads_no_beam")

    def test_the_slice_is_sparse(self):
        """The fixture must actually renumber, or the next test proves nothing."""
        rec, _ = _sliced_record()
        _, id_map = RR.rebuild_gather(rec)
        self.assertTrue(any(k != v for k, v in id_map.items()))

    def test_a_sliced_replay_decides_what_the_whole_one_does(self):
        """THE 2.153 CASE. Before the fix `stem_row_id` kept its old id, named another row, and the head narrowed."""
        rec, g = _sliced_record()
        log, _ = RR.rebuild_gather(rec)
        _decide(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "stem_tip_reads_no_beam")

    def test_every_carried_id_names_the_same_row_after_the_rebuild(self):
        """Not a key list: every id-shaped string in a rebuilt row's detail names the row the old id named."""
        rec, _ = _sliced_record()
        log, id_map = RR.rebuild_gather(rec)
        back = {v: k for k, v in id_map.items()}
        old = {r["id"]: r for r in rec["observations"] + rec["abstentions"]}
        n = 0
        for r in log.to_json()["observations"]:
            for k, x in r["detail"].items():
                if is_row_id(x):
                    n += 1
                    self.assertIsNotNone(log.row(x), (r["id"], k, x))
                    self.assertEqual(old[back[x]]["quantity"], log.row(x).quantity)
                    self.assertEqual(old[back[r["id"]]]["detail"][k], back[x])
        self.assertGreaterEqual(n, 2)          # STEM_TIP_INK and BEAM_STEM_LEVELS both carry one


class TestUnresolvableIdsRaise(unittest.TestCase):

    def _rec(self):
        log = Log()
        s = log.observe(R.cell(0, 0, 0, 0), Q.STEM, (1, 2, 3, 4), reader=READERS.CV_LINES, frame="cell:0")
        log.observe(R.cell(0, 0, 0, 0), Q.STEM_TIP_INK, False, reader=READERS.CV_STEM_TIP, frame="cell:0",
                    stem_row_id=s.id, end="top")
        return log.to_json(), s.id

    def test_a_detail_id_cut_out_of_the_slice_raises(self):
        rec, sid = self._rec()
        rec["observations"] = [o for o in rec["observations"] if o["id"] != sid]
        with self.assertRaises(RR.DanglingRowId):
            RR.rebuild_gather(rec)

    def test_a_basis_id_cut_out_raises_never_drops(self):
        rec, sid = self._rec()
        rec["observations"][1]["basis"] = [sid]
        rec["observations"] = [o for o in rec["observations"] if o["id"] != sid]
        with self.assertRaises(RR.DanglingRowId):
            RR.rebuild_gather(rec)

    def test_a_verdict_id_the_record_does_not_hold_raises(self):
        rec, _ = self._rec()
        rec["observations"][1]["detail"]["stem_row_id"] = "vrd:000099"
        with self.assertRaises(RR.DanglingRowId):
            RR.rebuild_gather(rec)

    def test_a_parent_verdict_id_is_kept_verbatim(self):
        """A human stance names the verdict he was SHOWN in the parent; verdicts are not replayed, so it stays."""
        rec, _ = self._rec()
        rec["verdicts"] = [{"id": "vrd:000099"}]
        rec["observations"][1]["detail"]["verdict_id"] = "vrd:000099"
        log, _ = RR.rebuild_gather(rec)
        self.assertEqual(log.to_json()["observations"][1]["detail"]["verdict_id"], "vrd:000099")
        rec["observations"][1]["basis"] = ["vrd:000099"]             # but never as a basis
        with self.assertRaises(RR.DanglingRowId):
            RR.rebuild_gather(rec)

    def test_a_frame_is_not_an_id_and_ids_are_found_at_any_depth(self):
        rec, sid = self._rec()
        rec["observations"][1]["detail"]["cell_frame"] = "cell:0"
        rec["observations"][1]["detail"]["nested"] = {sid: [sid]}
        log, id_map = RR.rebuild_gather(rec)
        d = log.to_json()["observations"][1]["detail"]
        self.assertEqual(d["cell_frame"], "cell:0")
        self.assertEqual(d["nested"], {id_map[sid]: [id_map[sid]]})


class TestTheGrammarIsTheLogs(unittest.TestCase):

    def test_every_id_a_log_writes_is_a_row_id(self):
        log = Log()
        o = log.observe(Subject.from_key("staff/0/0/0"), Q.STAFF_LINES, [1.0], reader=READERS.GEOMETRY, frame="page")
        self.assertTrue(is_row_id(o.id))
        self.assertTrue(is_row_id(log._next_id("vrd")))          # noqa: SLF001
        self.assertFalse(is_row_id("cell:0"))
        self.assertFalse(is_row_id("header:0"))

    def test_an_unknown_prefix_is_refused_at_the_write(self):
        with self.assertRaises(ValueError):
            Log()._next_id("xyz")                                 # noqa: SLF001
        self.assertEqual(set(ROW_ID_PREFIXES), {"obs", "abs", "vrd"})


if __name__ == "__main__":
    unittest.main()
