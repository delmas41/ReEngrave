"""ROADMAP 2.305 round 5 (STAGED EXPORT, `_with_across_system_joins`; the page pass's joins sit behind `OMR_PAGE_ARC_WRITE`, default OFF).

Built from the REAL rows of Sean's r4 tile 4 (Brahms p11, part P4, Fag., answered "tie"): `glyph/11/0/3/9/2` -> `glyph/11/0/3/10/3` is the record's tie
inside system 0 (F#4, bar 9 -> bar 10), and the page pass joined `glyph/11/0/3/10/3` -> `glyph/11/1/3/0/1` across the break as a TIE (both F#4, both
at rounded position -1, nothing between). The r4 tree refused that tie because the bar-10 note already ENDED a tie, and the older box pairing's
SLUR on the same two notes was written instead. A tie chain's middle note ends one tie and starts the next; the join decides the kind.
Fails on the r4 tree (the file held a slur and no tie across the break)."""
import collections
import unittest

from tools.omr.staged import export as E


def _det(key, x0, pitch="F#4"):
    return {"glyph": key, "category": "notehead", "bbox_page": [x0, 0, 40, 30], "pitch": pitch}


BAR9 = _det("glyph/11/0/3/9/2", 4880.5)
BAR10 = _det("glyph/11/0/3/10/3", 5229.4)
NEXT = _det("glyph/11/1/3/0/1", 926.6)
IN_SYSTEM_TIE = ((17, 4901.8), (17, 5250.9), BAR9, BAR10)
JOIN = ((17, 5250.9), (18, 945.9), BAR10, NEXT)
OLD_SLUR = ((17, 5250.9), (18, 945.9), BAR10, NEXT)          # the older box pairing's span on the same two notes


def _pairs(spans):
    return [(s[2]["glyph"], s[3]["glyph"]) for s in spans]


class TestTieChainAcrossTheBreak(unittest.TestCase):
    def test_the_join_tie_is_written_after_a_tie_that_ends_on_its_first_note(self):
        c = collections.Counter({"tie_spans_across_systems": 1})
        ties = E._with_across_system_joins("tie", [IN_SYSTEM_TIE], [], [JOIN], c)
        self.assertIn(("glyph/11/0/3/10/3", "glyph/11/1/3/0/1"), _pairs(ties))
        self.assertEqual(len(ties), 2)
        self.assertEqual(c["arc_across_systems_end_already_spanned"], 0)

    def test_the_older_slur_on_the_same_two_notes_is_not_written(self):
        c = collections.Counter()
        slurs = E._with_across_system_joins("slur", [OLD_SLUR], [], [JOIN], c)
        self.assertEqual(slurs, [])
        self.assertEqual(c["arc_across_systems_other_kind_span_replaced"], 1)

    def test_a_note_never_starts_two_ties(self):
        # the twin that must still refuse: a tie already STARTS on the bar-10 note inside the system
        other = ((17, 5250.9), (17, 5400.0), BAR10, _det("glyph/11/0/3/10/9", 5380.0))
        c = collections.Counter({"tie_spans_across_systems": 1})
        ties = E._with_across_system_joins("tie", [other], [], [JOIN], c)
        self.assertNotIn(("glyph/11/0/3/10/3", "glyph/11/1/3/0/1"), _pairs(ties))
        self.assertEqual(c["arc_across_systems_end_already_spanned"], 1)

    def test_a_slur_join_with_no_competitor_stands(self):
        # Sean's r4 tile 6 shape (Vcl. F#2 -> B2, a slur join): nothing of the other kind on its notes, written as before
        a, b = _det("glyph/11/0/12/10/6", 5228.9, "F#2"), _det("glyph/11/1/12/0/0", 930.4, "B2")
        j = ((17, 5249.9), (18, 950.3), a, b)
        c = collections.Counter({"slur_spans_across_systems": 1})
        self.assertEqual(_pairs(E._with_across_system_joins("slur", [], [j], [], c)), [("glyph/11/0/12/10/6", "glyph/11/1/12/0/0")])


if __name__ == "__main__":
    unittest.main()
