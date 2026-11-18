"""ROADMAP 2.314 r5 (`OMR_TWO_STEMS_TWO_NOTES`): the three clean-ups, each control cut from REAL record rows of the Litolff sample
(the export's own events, glyph keys, stem ids, read directions and boxes as the saved record gives them).

A. A rest, or one stem's note, alone at its moment speaks for both players: written once, the other voice carried with <forward>.
   Litolff P1 m20 (2/0/0/3): a unison quarter with stems both ways, then a quarter rest -- "counted 2 / 1" through round 4.
B. Two stems at one place pointing the same way are never two players: Sean's tile 2 (2/0/10/2, both stems read DOWN -- the record's
   reading; the page shows the upper stem up) and a real all-down eighth run (4/1/7/5) are written as flag OFF writes them.
   A lone down stem in a split bar is player 2: Sean's tile 4 (16/0/0/0) now adds up.
C. A head of a split bar touching a read dynamic letter's box is never written by the flag: Litolff 4/1/5/4/5 (an `f` curl on the
   `dynamicF` box 4/1/5/4/0) declines its bar.
"""
import collections
import os
import unittest
from unittest import mock

from tools.omr.staged import export as E
from tools.omr.staged import one_chord
from tools.omr.voicing import split_events_into_voices

D = 8
TWO_FOUR = {"numerator": 2, "denominator": 4}


def _head(glyph, stem, direction, read, beats, bbox):
    return {"glyph": "glyph/" + glyph, "stem_id": stem, "stem_direction": direction, "stem_direction_read": read,
            "duration_beats": beats, "bbox": bbox}


def _chord(x, beats, *heads):
    return {"kind": "chord", "x_position": x, "duration_beats": beats, "noteheads": list(heads),
            "stem_direction": heads[0]["stem_direction"]}


def _rest(x, beats, cls="restQuarter"):
    return {"kind": "rest", "x_position": x, "duration_beats": beats, "rest": {"class": cls}, "noteheads": []}


class _Cell:
    def __init__(self, events):
        self.detections = [h for e in events for h in e["noteheads"]] or [{}]
        self.unplaced = ()
        self._events = events


class _Rec:
    """The two `Q.GLYPH_BOX` rows rule C reads (real page boxes, Litolff p4)."""
    def __init__(self, rows=()):
        self.rows = list(rows)

    def obs_of(self, q):
        return self.rows if q == E.Q.GLYPH_BOX else []


def _split(rec, run, i, evs, why=None):
    """The split `_voice_split` makes on these bars: the flag's stem pairs first, else 2.90's divisi split."""
    return E._stem_pair_streams(evs) or (split_events_into_voices(evs) if E._divisi_pairs(evs) else None)


# --- the real rows -------------------------------------------------------------------------------------------------------------------
def p1_m20():
    h = ("2/0/0/3/0", None)
    return [_chord(183, 1.0, _head(h[0], None, "up", None, 1.0, [112, 351, 143, 131])),
            _chord(183, 1.0, _head(h[0], None, "down", None, 1.0, [112, 351, 143, 131])),
            _rest(443, 1.0)]


def tile_2():
    return [_chord(157, 2.0, _head("2/0/10/2/13", "obs:037667", "down", "down", 2.0, [20, 598, 274, 126])),
            _chord(231, 1.0, _head("2/0/10/2/1", "obs:037666", "down", "down", 1.0, [143, 234, 176, 137])),
            _rest(455, 1.0)]


def eighth_run_all_down():
    return [_chord(161, 0.5, _head("4/1/7/5/7", "obs:078510", "down", "down", 0.5, [91, 166, 140, 140])),
            _chord(344, 0.5, _head("4/1/7/5/6", "obs:078509", "down", "down", 0.5, [258, 103, 173, 133])),
            _chord(483, 0.5, _head("4/1/7/5/13", "obs:078511", "down", "down", 0.5, [416, 172, 134, 134])),
            _chord(760, 0.5, _head("4/1/7/5/3", "obs:078512", "down", "down", 0.5, [678, 216, 164, 140]))]


def tile_4():
    return [_chord(1111, 1.0, _head("16/0/0/0/8", "obs:263298", None, "down", 1.0, [1037, 343, 148, 134])),
            _chord(1118, 2.0, _head("16/0/0/0/24", "obs:263296", None, None, 2.0, [1042, 188, 153, 137])),
            _chord(1329, 1.0, _head("16/0/0/0/3", "obs:263299", None, "down", 1.0, [1252, 290, 155, 136]))]


def f_curl_bar():
    return [_chord(182, 1.0, _head("4/1/5/4/3", None, "up", None, 1.0, [108, 339, 148, 136])),
            _chord(182, 1.0, _head("4/1/5/4/3", None, "down", None, 1.0, [108, 339, 148, 136])),
            _chord(380, 1.0, _head("4/1/5/4/5", "obs:x", None, None, 1.0, [324, 653, 113, 83]))]


F_ROWS = [{"subject": "glyph/4/1/5/4/5", "value": ["noteheadBlackOnLine"],
           "detail": {"bbox_page_px": [1089.84, 2886.48, 1107.92, 2899.76]}},
          {"subject": "glyph/4/1/5/4/0", "value": ["dynamicF"], "detail": {"bbox_page_px": [1043.76, 2886.8, 1097.04, 2934.64]}}]


class R5(unittest.TestCase):
    def setUp(self):
        for p in (mock.patch.dict(os.environ, {one_chord.STEMS_APART_ENV: "1"}),
                  mock.patch.object(E, "_bar_quarters", lambda m: 2.0 if m else None)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(one_chord.bar_declines, False)

    def verdict(self, events, rec=None):
        cell = _Cell(events)
        with mock.patch.object(E, "_events", lambda c: c._events if c is not None else []), \
                mock.patch.object(E, "_voice_split", _split):
            return E._two_stems_bar_verdict(rec if rec is not None else _Rec(), None, 0, cell, TWO_FOUR, D)

    # A
    def test_A_p1_m20_shared_rest_is_written_once_and_the_bar_adds_up(self):
        evs = p1_m20()
        self.assertIsNone(self.verdict(evs))
        placed = E._two_stems_streams(_split(None, None, 0, evs), TWO_FOUR, D, (), collections.Counter())
        kinds = [[e["kind"] for e in st] for st in placed]
        self.assertEqual(kinds, [["chord", "rest"], ["chord", E.FORWARD_KIND]])
        self.assertEqual([sum(E._event_units(e, D) for e in st) for st in placed], [16, 16])

    def test_A_control_fails_on_round_4s_per_voice_rest_once(self):
        # the same bar written as round 4 wrote it (rest to voice 1 only, no <forward>): voice 2 is short -> it was declined
        evs = p1_m20()
        streams = E._rests_to_the_silent_voice(_split(None, None, 0, evs), TWO_FOUR, D, collections.Counter())
        self.assertIsNotNone(E._bar_holds_out(evs, streams, D, TWO_FOUR))

    def test_A_a_lone_mark_carries_the_other_voice(self):
        # unison quarter, then one up-stem quarter alone, then one down-stem quarter alone, in 3/4: three moments, no overlap
        u = _head("x/0", None, "up", None, 1.0, [100, 300, 140, 130])
        d = dict(u, stem_direction="down")
        a = _chord(100, 1.0, _head("x/1", "s1", "up", "up", 1.0, [300, 300, 140, 130]))
        b = _chord(500, 1.0, _head("x/2", "s2", "down", "down", 1.0, [500, 300, 140, 130]))
        a["x_position"], b["x_position"] = 300, 500
        streams = [[_chord(100, 1.0, u), a], [_chord(100, 1.0, d), b]]
        placed = E._place_columns([(e, v) for v, st in enumerate(streams) for e in st], 24, D)
        self.assertNotIsInstance(placed, str)
        self.assertEqual([sum(E._event_units(e, D) for e in st) for st in placed], [24, 24])
        self.assertEqual([e["kind"] for e in placed[1]], ["chord", E.FORWARD_KIND, "chord"])

    def test_A_a_later_place_is_a_later_moment(self):
        # an up-stem quarter, then a down-stem quarter further right: never both at beat 1 -- voice 2 starts at beat 2
        a = _chord(100, 1.0, _head("y/1", "s1", "up", "up", 1.0, [100, 300, 140, 130]))
        b = _chord(400, 1.0, _head("y/2", "s2", "down", "down", 1.0, [400, 300, 140, 130]))
        placed = E._place_columns([(a, 0), (b, 1)], 16, D)
        self.assertEqual([(e["kind"], E._event_units(e, D)) for e in placed[1]], [(E.FORWARD_KIND, 8), ("chord", 8)])

    # B
    def test_B_tile_2_same_direction_is_written_as_flag_off(self):
        self.assertEqual(self.verdict(tile_2()), "same_direction")

    def test_B_a_real_all_down_eighth_run_is_not_split(self):
        self.assertEqual(self.verdict(eighth_run_all_down()), "same_direction")

    def test_B_control_the_run_was_split_before(self):
        self.assertIsNotNone(E._stem_pair_streams(eighth_run_all_down()))

    def test_B_tile_4_lone_down_stem_is_player_2_and_the_bar_adds_up(self):
        evs = tile_4()
        self.assertIsNone(self.verdict(evs))
        st = E._stem_pair_streams(evs)
        self.assertEqual([[h["glyph"][-4:] for e in s for h in e["noteheads"]] for s in st], [["0/24"], ["/0/8", "/0/3"]])

    # C
    def test_C_a_head_on_an_f_declines_the_bar(self):
        self.assertEqual(self.verdict(f_curl_bar(), _Rec(F_ROWS)), "head_on_a_dynamic_letter")

    def test_C_control_without_the_letter_the_bar_is_written(self):
        self.assertIsNone(self.verdict(f_curl_bar(), _Rec(F_ROWS[:1])))

    def test_C_a_head_on_a_whole_rest_box_declines(self):
        rows = [dict(F_ROWS[0], value=["restWhole"])]
        self.assertEqual(self.verdict(f_curl_bar(), _Rec(rows)), "head_on_a_whole_rest_box")

    def test_flag_off_writes_nothing_new(self):
        with mock.patch.dict(os.environ, {one_chord.STEMS_APART_ENV: "0"}):
            self.assertIsNone(self.verdict(tile_2()))


if __name__ == "__main__":
    unittest.main()
