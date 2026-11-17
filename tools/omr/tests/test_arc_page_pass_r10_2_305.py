"""ROADMAP 2.305 r10: three causes of the real arcs round 9 left unread (Sean's r9 tiles, `benchmarks/arcs-combined-2026-11/answers/answers-2.305-r9.json`).
STAGED. Every control is built from the REAL marks of his answered tiles (numbers copied from the r10 gathers, page pixels), never a drawing.

  _head_read          tile 5 (Brahms p0 9/0/7 -> 9/0/9, "tie, connected to the right notes"; also r7b tile 4, "the notes are correct"): a note a WORD's
                      claimed area covers is read (EXPORT writes it, guessed); NEVER a head a KEY's claim narrowed (r6 tile 5, Litolff p15) or one narrowed
                      for its own ink (`stem_end_ink_only`, r6 tile 2).
  ink_ends_on         tile 9 (Brahms p0 12/0/4 -> 12/1/1, "the correct length of the slur, and the notes are right"): two notes about equally near the
                      ink's end, the traced ink running onto 12/1/1's head -> 12/1/1; NEVER a point inside no head or inside two.
  unclaimed_header_boxes_dropped   tile 4 (Litolff p13 13/1/5/10/0 -> 11/2, "tie, connected to the right notes"): the detector boxed the tie as a
                      "timeSig1" and a "clefF"; no page-wide header claim holds them, so they blank nothing; NEVER a clef box its page claim holds.
"""
from __future__ import annotations

from tools.omr.staged import page_arc_bind as PB
from tools.omr.staged import page_arcs as PA
from tools.omr.staged.adjudicators import ownership as OW
from tools.omr.staged.record import Outcome


class _V:
    def __init__(self, outcome, value=None, reason=None):
        self.outcome, self.value, self.reason = outcome, value, reason


class _Ev:
    def __init__(self, v):
        self._v = v

    def verdict(self, q, subject=None):
        return self._v


class TestANoteUnderAWordIsRead:
    def test_yes_tile5_start_note_narrowed_by_a_words_claim(self):          # Brahms p0 glyph/0/0/9/0/7, `claim_narrowed:word`
        assert OW._head_read(_Ev(_V(Outcome.NARROWED, reason="claim_narrowed:word")), "glyph/0/0/9/0/7")

    def test_never_a_box_a_keys_claim_narrowed(self):          # r6 tile 5, Litolff p15 15/0/0/0/5 on the key signature
        assert not OW._head_read(_Ev(_V(Outcome.NARROWED, reason="claim_narrowed:key")), "glyph/15/0/0/0/5")

    def test_never_a_head_held_in_doubt_for_its_own_ink(self):          # r6 tile 2, Litolff p13 13/0/3/14/7
        assert not OW._head_read(_Ev(_V(Outcome.NARROWED, reason="stem_end_ink_only")), "glyph/13/0/3/14/7")


def _h(key, box):
    x0, y0, x1, y1 = box
    return {"key": key, "cx": (x0 + x1) / 2.0, "cy": (y0 + y1) / 2.0, "w": x1 - x0, "h": y1 - y0}


TILE9 = [_h("glyph/0/0/12/1/1", [2602.88, 6343.04, 2646.72, 6381.76]), _h("glyph/0/0/12/1/15", [2571.2, 6443.2, 2611.84, 6481.28]),
         _h("glyph/0/0/12/1/2", [2549.76, 6357.76, 2592.0, 6395.52])]


class TestTheInkEndsOnANote:
    def test_yes_tile9_the_slur_runs_onto_its_note(self):
        d = {"x_right_ext": 2646.0, "y_right_ext": 6361.0}          # run obs:029031's own traced end
        assert PB.ink_ends_on(d, "right", TILE9)["key"] == "glyph/0/0/12/1/1"

    def test_never_a_point_inside_no_head(self):
        d = {"x_right_ext": 2600.0, "y_right_ext": 6320.0}
        assert PB.ink_ends_on(d, "right", TILE9) is None

    def test_never_a_point_inside_two_heads(self):
        twin = TILE9 + [_h("glyph/0/0/12/1/9", [2600.0, 6340.0, 2650.0, 6380.0])]          # a second head drawn over the same place
        assert PB.ink_ends_on({"x_right_ext": 2646.0, "y_right_ext": 6361.0}, "right", twin) is None


TILE4_BOXES = [("timeSig1", [1925.0, 2826.0, 1951.0, 2847.0]), ("clefF", [1956.0, 2832.0, 2003.4, 2848.0]),
               ("noteheadHalfOnLine", [1987.0, 2858.0, 2014.0, 2881.0])]
TILE4_AREAS = [("key_signature", [2003.0, 2806.0, 2026.0, 2864.0])]


class TestAnUnclaimedHeaderBoxBlanksNoArc:
    def test_yes_tile4_the_tie_boxed_as_a_meter_and_a_clef(self):
        kept = PA.unclaimed_header_boxes_dropped(TILE4_BOXES, TILE4_AREAS)
        assert [c for c, _b in kept] == ["noteheadHalfOnLine"]

    def test_never_a_clef_its_page_claim_holds(self):          # Brahms p0 staff 0's clef, held by its page claim
        boxes = [("clefG", [1271.83, 1527.33, 1362.42, 1764.70])]
        assert PA.unclaimed_header_boxes_dropped(boxes, [("clef", [1272.0, 1527.0, 1363.0, 1765.0])]) == boxes
