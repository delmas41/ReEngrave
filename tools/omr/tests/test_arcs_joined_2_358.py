"""ROADMAP 2.358: a tie or slur whose notes are both read is joined to them. STAGED. Every control is built from REAL marks: the arcs on Sean's three
2026-11-26 sheets (`out/print/step0-arcs/`, answers.json: "Everything else looks pretty straightforward" -- 69 of 72 a tie or slur; sheet 3 tile 14
"not an arc"), numbers copied from the 20261123-night record (sample pages), never a drawing.

  (i)   `OMR_ARC_END_AT_INK_HEAD` -- a head the page ink alone read at a stem end (`stem_end_ink_only`, written blue by EXPORT) is a note an arc may end
        at. Sheet 1 (Litolff, "unread ink at its end") tiles 1, 3, 6, 10, 11, 13, 18, 21, 22, 23: the "unread ink" at the arc's end is exactly such a
        head. NEVER: a head a key's claim narrowed; a box refused as a note; a note nobody read (blob ink) -- those stay "cannot tell".
  (iii) `OMR_ARC_JOIN_BY_HEIGHT` -- the piece that leaves a system and the piece that enters the next on the same staff, curved the same way at the
        same height, are one arc. Sheet 3 (Brahms, "runs to the edge of the system") tiles 5 + 18 (p19 staff 5), 10 + 12 (p5 staff 0). NEVER: tile 9
        (two cups both match one piece -- stacked, not joined), tile 13 (same staff, same curve, 3.35 spaces apart), opposite curves.
"""
from __future__ import annotations

import os
from unittest import mock

from tools.omr.staged import page_arc_bind as PB
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


def _on(**kw):
    env = {PB.ENV_END_AT_INK_HEAD: "1", PB.ENV_JOIN_BY_HEIGHT: "1"}
    env.update(kw)
    return mock.patch.dict(os.environ, env)


def _off():
    return mock.patch.dict(os.environ, {PB.ENV_END_AT_INK_HEAD: "0", PB.ENV_JOIN_BY_HEIGHT: "0"})


# ── (i) ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
#: Sheet 1 tile -> the head the binder called "unread ink" at the arc's end (`page_stroke:narrowed:<key>`), every one NARROWED `stem_end_ink_only`
#: in the 20261123-night record and written (blue) by EXPORT
SHEET1_INK_HEADS = {1: "glyph/16/0/1/9/3", 3: "glyph/4/0/2/3/11", 6: "glyph/6/1/2/0/11", 10: "glyph/10/1/4/3/5", 11: "glyph/11/0/1/11/3",
                    13: "glyph/2/1/2/10/8", 18: "glyph/10/1/3/0/13", 21: "glyph/16/0/4/10/4", 22: "glyph/6/1/2/0/11", 23: "glyph/4/0/2/3/11"}


class TestAnArcMayEndAtAHeadReadFromItsInk:
    def test_yes_every_sheet1_ink_head_is_a_note_an_arc_ends_at(self):
        with _on():
            for tile, key in SHEET1_INK_HEADS.items():
                assert OW._head_read(_Ev(_V(Outcome.NARROWED, reason="stem_end_ink_only")), key), tile

    def test_off_they_stay_unread(self):
        with _off():
            for key in SHEET1_INK_HEADS.values():
                assert not OW._head_read(_Ev(_V(Outcome.NARROWED, reason="stem_end_ink_only")), key)

    def test_never_a_box_a_keys_claim_narrowed(self):          # Sean's 2.305 r6 tile 5, Litolff p15 15/0/0/0/5 on the key signature
        with _on():
            assert not OW._head_read(_Ev(_V(Outcome.NARROWED, reason="claim_narrowed:key")), "glyph/15/0/0/0/5")

    def test_never_a_box_refused_as_a_note(self):
        with _on():
            assert not OW._head_read(_Ev(_V(Outcome.DECIDED, value=True, reason="stacked_head_duplicate")), "glyph/4/0/2/4/5")


# ── (iii) ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _piece(run, shape, y):
    return {"curve": "page_arc/" + run, "shape": shape, "y_end_spaces": y}


#: Brahms p19, staff 5, the break after system 0 (heights: spaces below the staff's top line at the piece's edge end; curve: the binder's side)
P19_RIGHT = [_piece("obs:1214860", "below", 4.51), _piece("obs:1214862", "below", 5.2), _piece("obs:1214864", "above", -0.1)]          # tiles 9, -, 5
P19_LEFT = [_piece("obs:1214719", "below", 4.95), _piece("obs:1214723", "above", -0.08)]                                                # -, tile 18
#: Brahms p5, staff 0 (tiles 10 and 12); obs:362367 is the staff's other entering piece, under the staff
P5_RIGHT = [_piece("obs:362530", "above", -5.02)]
P5_LEFT = [_piece("obs:362362", "above", -5.33), _piece("obs:362367", "above", 6.09)]


class TestTwoPiecesAcrossABreakAreOneArc:
    def test_yes_tiles_5_and_18_the_cap_over_staff_5(self):
        assert PB.pair_by_height(P19_RIGHT, P19_LEFT) == [(2, 1)]

    def test_yes_tiles_10_and_12_the_cap_over_staff_0(self):
        assert PB.pair_by_height(P5_RIGHT, P5_LEFT) == [(0, 0)]

    def test_never_tile_9_two_cups_that_both_fit_one_piece(self):          # stacked: obs:1214860 and obs:1214862 both 0.25-0.44 sp from obs:1214719
        assert all(i not in (0, 1) for i, _j in PB.pair_by_height(P19_RIGHT, P19_LEFT))

    def test_never_tile_13_same_staff_same_curve_far_apart(self):          # Brahms p5 staff 6: obs:362481 (-1.29) and tile 13 obs:362485 (-4.64)
        assert PB.pair_by_height([_piece("obs:362481", "below", -1.29)], [_piece("obs:362485", "below", -4.64)]) == []

    def test_never_opposite_curves_at_one_height(self):          # Brahms p25 staff 2: the cap obs:1560169 and the entering cup obs:1560072
        assert PB.pair_by_height([_piece("obs:1560169", "above", -0.72)], [_piece("obs:1560072", "below", -0.72)]) == []

    def test_never_a_piece_without_its_curve_or_height(self):          # a detector-curve edge (2.271) carries neither: never joined by this rule
        assert PB.pair_by_height([{"curve": "x"}], [{"curve": "y"}]) == []

    def test_the_flags_are_off_by_default(self):
        env = {k: v for k, v in os.environ.items() if k not in (PB.ENV_JOIN_BY_HEIGHT, PB.ENV_END_AT_INK_HEAD)}
        with mock.patch.dict(os.environ, env, clear=True):
            assert not PB.join_by_height_enabled() and not PB.end_at_ink_head_enabled()
