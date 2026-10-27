"""ROADMAP 2.211 -- notes are scored by the PLACE they are written at, not by the detector box they came from.
Each positive has a twin that must still fire (a scorer that reports nothing for everything cannot pass)."""
from __future__ import annotations

import unittest

from tools.omr.staged import lane_report as L


def host(rg, cx, cy, onset="0", pitch="G4", typ="half", kind="note", part="P8", measure="8", sub=None, h=10):
    return dict(kind=kind, part=part, measure=measure, rg=rg, page=4, cx=cx, cy=cy, box=[cx - 5, cy - h, cx + 5, cy + h],
                type=typ, pitch=pitch if kind == "note" else None, blue=False, sub=sub or {}, chord=False,
                onset=onset, voice="1")


def arm(hosts):
    return dict(hosts=list(hosts), loose=[])


# the twin: one head boxed twice; OFF wrote it from the head box (/2), ON from the head+stem box (/10), centres 40 px apart
OFF = [host("glyph/4/0/7/7/2", 100, 500)]
ON = [host("glyph/4/0/7/7/10", 100, 460)]


class TestPlace(unittest.TestCase):
    def test_place_of_reads_the_written_event(self):
        self.assertEqual(L.place_of(OFF[0]), (4, 0, 7, 7, "P8", "8", "0"))
        self.assertIsNone(L.place_of(dict(OFF[0], onset=None)))
        self.assertIsNone(L.place_of(dict(OFF[0], rg="glyph/4/0/7/7/x")))

    def test_box_swap_with_the_same_music_reports_nothing(self):
        d = L.diff_arms(arm(OFF), arm(ON), tol=8)
        self.assertEqual(d["counts"], {})
        self.assertEqual(d["paired"], 1)

    def test_the_old_box_keyed_rule_fails_it(self):    # the control that can fail: strip the places and it is a lost note
        d = L.diff_arms(arm([dict(OFF[0], onset=None)]), arm([dict(ON[0], onset=None)]), tol=8)
        self.assertEqual(d["counts"]["note"], {"gained": 1, "lost": 1, "changed": 0})

    def test_swap_with_a_changed_pitch_still_reports(self):
        d = L.diff_arms(arm(OFF), arm([dict(ON[0], pitch="E4")]), tol=8)
        self.assertEqual(d["counts"], {"pitch": {"gained": 0, "lost": 0, "changed": 1}})

    def test_swap_with_a_changed_value_still_reports(self):
        d = L.diff_arms(arm(OFF), arm([dict(ON[0], type="quarter")]), tol=8)
        self.assertEqual(d["counts"], {"value": {"gained": 0, "lost": 0, "changed": 1}})

    def test_a_deleted_note_is_a_lost_note(self):
        d = L.diff_arms(arm(OFF), arm([]), tol=8)
        self.assertEqual(d["counts"]["note"]["lost"], 1)

    def test_other_onset_is_not_the_same_place(self):
        d = L.diff_arms(arm(OFF), arm([dict(ON[0], onset="1/2", cy=900)]), tol=8)
        self.assertEqual(d["counts"]["note"], {"gained": 1, "lost": 1, "changed": 0})

    def test_a_moved_onset_over_the_same_ink_still_pairs_by_position(self):
        d = L.diff_arms(arm([host("glyph/4/0/7/7/21", 100, 500)]), arm([host("glyph/4/0/7/7/22", 102, 501, onset="1/2")]), tol=8)
        self.assertEqual(d["counts"], {})

    def test_two_notes_at_one_place_pair_in_x_order(self):
        o = [host("glyph/4/0/7/7/21", 100, 500, pitch="G4"), host("glyph/4/0/7/7/22", 100, 480, pitch="B4")]
        n = [host("glyph/4/0/7/7/23", 100, 440, pitch="B4"), host("glyph/4/0/7/7/24", 100, 520, pitch="G4")]
        self.assertEqual(L.diff_arms(arm(o), arm(n), tol=8)["counts"], {})

    def test_parse_symbols_gives_onsets_and_chords_share_one(self):
        xml = ('<score-partwise><part id="P1"><measure number="1"><attributes><divisions>2</divisions></attributes>'
               '<note rg="glyph/4/0/7/7/1"><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type></note>'
               '<note rg="glyph/4/0/7/7/2"><chord/><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type></note>'
               '<note rg="glyph/4/0/7/7/3"><pitch><step>G</step><octave>4</octave></pitch><duration>4</duration><type>half</type></note>'
               '</measure></part></score-partwise>')
        boxes = {"glyph/4/0/7/7/%d" % i: dict(page=4, box=[0, 0, 2, 2], cls=None) for i in (1, 2, 3)}
        hs = L.parse_symbols(xml, boxes)["hosts"]
        self.assertEqual([h["onset"] for h in hs], ["0", "0", "1"])


class TestJudgedByPlace(unittest.TestCase):
    ROW = dict(item="i", tile="t", subject="glyph/4/0/7/7/10", answer="2", now="refused as not a note")
    # the twin /10 was never written; /2 was, and its centre lies inside /10's (head + stem) box
    BOX = {"glyph/4/0/7/7/10": [95, 450, 105, 520]}

    def rep(self, key="worse"):
        return dict(worse=[dict(self.ROW)] if key == "worse" else [], lost=[dict(self.ROW)] if key == "lost" else [],
                    better=[], scored=1)

    def test_same_music_leaves_the_regression_list(self):
        r = L.by_place(self.rep(), self.BOX, OFF, [host("glyph/4/0/7/7/9", 100, 440)])
        self.assertEqual((len(r["worse"]), len(r["same_music"]), len(r["not_found"])), (0, 1, 0))

    def test_changed_pitch_stays_a_regression(self):
        r = L.by_place(self.rep(), self.BOX, OFF, [host("glyph/4/0/7/7/9", 100, 440, pitch="E4")])
        self.assertEqual((len(r["worse"]), len(r["same_music"])), (1, 0))

    def test_changed_value_stays_a_regression(self):
        r = L.by_place(self.rep(), self.BOX, OFF, [host("glyph/4/0/7/7/9", 100, 440, typ="quarter")])
        self.assertEqual(len(r["worse"]), 1)

    def test_nothing_written_at_the_place_ON_stays_a_regression(self):
        self.assertEqual(len(L.by_place(self.rep(), self.BOX, OFF, [])["worse"]), 1)

    def test_no_written_event_at_the_place_OFF_is_not_found_not_a_verdict(self):
        r = L.by_place(self.rep(), self.BOX, [], [host("glyph/4/0/7/7/9", 100, 440)])
        self.assertEqual((len(r["worse"]), len(r["same_music"]), len(r["not_found"])), (0, 0, 1))
        self.assertEqual(r["not_found"][0]["was"], "worse")

    def test_lost_rows_are_attached_the_same_way(self):
        r = L.by_place(self.rep("lost"), self.BOX, OFF, [host("glyph/4/0/7/7/9", 100, 440)])
        self.assertEqual((len(r["lost"]), len(r["same_music"])), (0, 1))


if __name__ == "__main__":
    unittest.main()
