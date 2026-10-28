"""ROADMAP 2.218 -- the lane report counts a judged answer OFF left unwritten that ON writes wrong (unwritten->wrong).
Each positive has a twin that must not fire; the known cases are re-scored from the saved 2.204 outputs by hand
(see the lane's report), not here (no saved outputs in the fast tier)."""
from __future__ import annotations

import unittest

from tools.omr.staged import lane_report as L


def host(rg, pitch="C4", typ="quarter", cx=100, cy=500):
    return dict(kind="note", part="P5", measure="36", rg=rg, page=4, cx=cx, cy=cy, box=[cx - 5, cy - 10, cx + 5, cy + 10],
                type=typ, pitch=pitch, blue=False, sub={}, chord=False, onset="0", voice="1")


def tile(status, note, item="t", n="1", sub="glyph/4/0/4/3/8"):
    return dict(item=item, tile=n, subject=sub, answer="half", status=status, note=note)


ON_WRITES = [host("glyph/4/0/4/3/8")]


class TestUnwrittenToWrong(unittest.TestCase):
    def moves(self, off_t, on_t, off_hosts, on_hosts=ON_WRITES):
        rep = L.compare_judged([off_t], [on_t])
        return L.by_place(rep, {}, off_hosts, on_hosts)

    def test_narrowed_off_then_wrong_on_is_counted(self):
        r = self.moves(tile("narrowed", "narrowed [0.5, 1.0], answer in set"), tile("wrong", "decided 1 beats"), [])
        self.assertEqual(len(r["unwritten_wrong"]), 1)
        self.assertEqual(r["worse"], [])

    def test_off_narrowed_to_a_set_missing_the_answer_is_still_unwritten(self):
        r = self.moves(tile("wrong", "narrowed [0.5, 1.0], answer NOT in set"), tile("wrong", "decided 1 beats"), [])
        self.assertEqual(len(r["unwritten_wrong"]), 1)

    def test_unwritten_then_right_is_counted_right(self):
        r = self.moves(tile("abstained", "abstained (x)"), tile("right", "decided 2 beats"), [])
        self.assertEqual((len(r["unwritten_wrong"]), len(r["unwritten_right"])), (0, 1))

    def test_off_wrote_this_note_there_is_not_unwritten(self):
        r = self.moves(tile("narrowed", "narrowed"), tile("wrong", "decided 1 beats"), [host("glyph/4/0/4/3/2")])
        self.assertEqual(r["unwritten_wrong"], [])

    def test_a_different_pitch_at_the_slot_does_not_hide_it(self):
        r = self.moves(tile("narrowed", "narrowed"), tile("wrong", "decided 1 beats"), [host("glyph/4/0/4/3/2", pitch="E4")])
        self.assertEqual(len(r["unwritten_wrong"]), 1)

    def test_off_wrong_decided_is_a_changed_note_not_unwritten(self):
        r = self.moves(tile("wrong", "decided 1 beats"), tile("wrong", "decided 0.5 beats"), [])
        self.assertEqual(r["unwritten_wrong"], [])

    def test_on_writing_nothing_is_not_found(self):
        r = self.moves(tile("narrowed", "narrowed"), tile("wrong", "decided 1 beats"), [], on_hosts=[])
        self.assertEqual((r["unwritten_wrong"], len(r["not_found"])), ([], 1))

    def test_landing_line_fails_on_a_nonzero_count(self):
        j = dict(worse=[], unwritten_wrong=[1], unwritten_right=[])
        self.assertIn("FAILS", L.landing_line(dict(plates={"litolff": dict(judged=j)})))
        j = dict(worse=[], unwritten_wrong=[], unwritten_right=[1])
        self.assertNotIn("FAILS", L.landing_line(dict(plates={"litolff": dict(judged=j)})))


class TestInvented(unittest.TestCase):
    def idx(self, text="part of an ff", kind="other"):
        return dict(tiles=[dict(item="t", tile="7", doc="litolff", subject="glyph/4/0/4/3/8", subjects=None, followup=False,
                                subject_kind="glyph", answer=text, answer_kind=kind, question_kind="unknown")])

    def test_says_not_a_note(self):
        for t in ("part of ff", "part of a 4 rest", "beams", "nothing", "part of a C clef"):
            self.assertTrue(L.says_not_a_note(dict(answer=t, answer_kind="other", question_kind="unknown")), t)
        self.assertTrue(L.says_not_a_note(dict(answer="sharp", answer_kind="not_a_note", question_kind="unknown")))
        self.assertFalse(L.says_not_a_note(dict(answer="chord below", answer_kind="other", question_kind="owner")))
        self.assertFalse(L.says_not_a_note(dict(answer="half", answer_kind="duration", question_kind="duration")))

    def test_note_made_of_non_note_ink_is_invented_and_fails_the_landing(self):
        r = L.invented_moves(dict(unwritten_wrong=[]), self.idx(), "litolff", {}, [], ON_WRITES)
        self.assertEqual([w.get("invented") for w in r["unwritten_wrong"]], [True])
        self.assertIn("FAILS", L.landing_line(dict(plates={"p": dict(judged=dict(worse=[], **r))})))

    def test_off_wrote_it_too_is_not_invented(self):
        r = L.invented_moves(dict(unwritten_wrong=[]), self.idx(), "litolff", {}, [host("glyph/4/0/4/3/2")], ON_WRITES)
        self.assertEqual(r["unwritten_wrong"], [])

    def test_off_note_dropped_by_on_is_invented_removed_not_wrong(self):
        r = L.invented_moves(dict(unwritten_wrong=[]), self.idx("sharp", "not_a_note"), "litolff", {}, ON_WRITES, [])
        self.assertEqual((r["unwritten_wrong"], len(r["invented_removed"])), ([], 1))


if __name__ == "__main__":
    unittest.main()
