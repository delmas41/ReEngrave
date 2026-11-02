"""ROADMAP 2.251 step 2, the clef carry (STAGED EVALUATE `restate_pitch` / EXPORT): the clef in force at a head, and where the carry
must STOP (CLAUDE rule 8, §4): a clef-shaped candidate that was not read, standing after a change of another kind than the header's,
makes the heads after it unread -- never carried past ink that might be the return clef.
"""
import unittest

from tools.omr.staged import clef_pagewide as CP


class _Row:
    def __init__(self, x, kind=None, candidate=False, change=True, source=CP.SOURCE):
        self.value = [x, 0, x + 20, 50]
        self.detail = {"source": source, "change": change, "kind": kind}
        if candidate:
            self.detail = {"source": source, "candidate": True, "x_page": x}


class ClefInForce(unittest.TestCase):
    def setUp(self):
        self.changes = CP.changes_of([_Row(100, "tenor"), _Row(500, "bass")])

    def test_header_governs_before_any_change(self):
        self.assertIsNone(CP.clef_in_force(50, self.changes, [], "bass"))

    def test_change_governs_until_the_return(self):
        self.assertEqual(CP.clef_in_force(300, self.changes, [], "bass")[0], "tenor")
        self.assertEqual(CP.clef_in_force(600, self.changes, [], "bass")[0], "bass")

    def test_a_candidate_after_a_tenor_change_stops_the_carry(self):
        cands = CP.candidates_of([_Row(250, candidate=True)])
        self.assertEqual(CP.clef_in_force(200, self.changes, cands, "bass")[0], "tenor")
        got = CP.clef_in_force(300, self.changes, cands, "bass")
        self.assertIsNotNone(got)
        self.assertIsNone(got[0])                       # unread: no pitch, a red "clef?" bar -- never tenor, never the header
        self.assertEqual(CP.clef_in_force(600, self.changes, cands, "bass")[0], "bass")   # the next READ clef resumes

    def test_a_candidate_where_the_header_kind_is_in_force_changes_nothing(self):
        cands = CP.candidates_of([_Row(50, candidate=True), _Row(700, candidate=True)])
        self.assertIsNone(CP.clef_in_force(80, self.changes, cands, "bass"))      # before any change: the header governs
        self.assertEqual(CP.clef_in_force(800, self.changes, cands, "bass")[0], "bass")   # after the return to the header's kind

    def test_a_candidate_after_an_unread_change_keeps_it_unread(self):
        ch = CP.changes_of([_Row(100, None)])
        cands = CP.candidates_of([_Row(250, candidate=True)])
        self.assertIsNone(CP.clef_in_force(300, ch, cands, "bass")[0])

    def test_a_refusal_not_marked_candidate_is_no_candidate(self):
        r = _Row(250, candidate=True)
        r.detail["candidate"] = False
        self.assertEqual(CP.candidates_of([r]), [])


if __name__ == "__main__":
    unittest.main()
