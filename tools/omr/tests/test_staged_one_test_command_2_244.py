"""ROADMAP 2.244 -- ONE TEST COMMAND: the default tag, the judged scorer's place key, the changed places nobody judged.
Every positive has a twin that must fail (a control that cannot fail proves nothing)."""
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from tools.omr.staged import judged as J
from tools.omr.staged import lane_report as L

BOX_A = [1000.0, 500.0, 1030.0, 530.0]     # where the half note is
BOX_B = [1400.0, 500.0, 1430.0, 530.0]     # another note in the same cell


def gbox(key, box, cat="notehead"):
    return {"id": "obs:" + key, "subject": key, "quantity": "glyph_box", "value": ["x", 0, 0, 1, 1],
            "detail": {"category": cat, "bbox_page_px": box}}


def dur(key, beats):
    return {"id": "v:" + key, "subject": key, "quantity": "duration", "outcome": "decided",
            "value": {"beats": beats}, "reason": "t", "supersedes": None, "candidates": []}


def write_record(path, boxes, verdicts):
    path.write_text(json.dumps({"observations": boxes, "verdicts": verdicts}))
    return path


def tile(subject="glyph/3/0/1/4/2", box=BOX_A, with_position=True, want=2.0, kind="note"):
    pl = J.key_place(subject)
    r = dict(item="g1", tile="1", doc="litolff", subject=subject, subjects=None, subject_kind="glyph", page_box=box,
             answer="half", question_kind="duration", answer_kind="duration", value=want, followup=False, control=False)
    if with_position:
        r["position"] = dict(page=pl[0], system=pl[1], staff=pl[2], cell=pl[3], page_box=box)
        r["mark_kind"] = kind
    return r


class TestDefaultTag(unittest.TestCase):
    def test_default_tag_is_the_sample_tag(self):
        self.assertEqual(L.DEFAULT_TAG, "20261029-night")
        self.assertEqual(L.load_sample()["record_tag"], L.DEFAULT_TAG)

    def test_a_stale_tag_raises(self):         # the control that can fail
        sample = L.load_sample()
        with self.assertRaises(SystemExit):
            L.check_tag("19990101-night", ["litolff"], sample)

    def test_a_tag_with_a_record_or_slice_passes(self):
        sample = L.load_sample()
        with tempfile.TemporaryDirectory() as d:     # a directory of hand-built slices is taken as it stands
            L.check_tag(d, ["litolff"], sample)


class TestPlaceKey(unittest.TestCase):
    """Gather 1 judged the half note as glyph/3/0/1/4/2. Gather 2 numbered the same page differently: the half note is now
    /9 and /2 is the OTHER note (a quarter). The old key scores the quarter against Sean's 'half'."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.rec2 = write_record(self.tmp / "g2.json",
                                 [gbox("glyph/3/0/1/4/2", BOX_B), gbox("glyph/3/0/1/4/9", BOX_A),
                                  gbox("glyph/3/0/1/5/2", BOX_A)],        # same box, ANOTHER cell: must not match
                                 [dur("glyph/3/0/1/4/2", 1.0), dur("glyph/3/0/1/4/9", 2.0), dur("glyph/3/0/1/5/2", 0.5)])

    def idx(self, **kw):
        return dict(tiles=[tile(**kw)])

    def test_place_finds_the_half_note_at_another_id(self):
        rep = J.score(self.idx(), self.rec2, "litolff")
        self.assertEqual(rep["tiles"][0]["status"], "right")
        self.assertEqual(rep["tiles"][0]["subject"], "glyph/3/0/1/4/9")
        self.assertEqual(rep["tiles"][0]["subject_asked"], "glyph/3/0/1/4/2")
        self.assertEqual(rep["matched"], {"place": 1, "place_moved_id": 1})

    def test_the_old_key_mis_scores_it(self):   # the twin that must fail: by key, the same tile is 'wrong'
        rep = J.score(self.idx(), self.rec2, "litolff", by="key")
        self.assertEqual(rep["tiles"][0]["status"], "wrong")

    def test_a_tile_without_position_keeps_the_key_and_is_counted_apart(self):
        rep = J.score(self.idx(with_position=False), self.rec2, "litolff")
        self.assertEqual(rep["tiles"][0]["status"], "wrong")
        self.assertEqual(rep["matched"], {"key": 1})

    def test_no_mark_at_the_place_is_not_found_never_a_key_fallback(self):
        rec = write_record(self.tmp / "g3.json", [gbox("glyph/3/0/1/4/2", BOX_B)], [dur("glyph/3/0/1/4/2", 1.0)])
        rep = J.score(self.idx(), rec, "litolff")
        self.assertEqual(rep["tiles"][0]["status"], "not_found")
        self.assertEqual(rep["matched"], {"place_no_mark": 1})

    def test_kind_must_agree(self):             # a rest box over the same ink is not the note the tile asked about
        rec = write_record(self.tmp / "g4.json", [gbox("glyph/3/0/1/4/7", BOX_A, "rest")], [dur("glyph/3/0/1/4/7", 4.0)])
        self.assertEqual(J.score(self.idx(), rec, "litolff")["tiles"][0]["status"], "not_found")
        self.assertEqual(J.score(self.idx(kind="rest"), rec, "litolff")["tiles"][0]["note"].startswith("decided"), True)

    def test_the_tiles_own_id_breaks_a_tie(self):
        rec = write_record(self.tmp / "g5.json", [gbox("glyph/3/0/1/4/2", BOX_A), gbox("glyph/3/0/1/4/3", BOX_A)],
                           [dur("glyph/3/0/1/4/2", 2.0), dur("glyph/3/0/1/4/3", 1.0)])
        self.assertEqual(J.score(self.idx(), rec, "litolff")["tiles"][0]["subject"], "glyph/3/0/1/4/2")

    def test_derived_positions_change_nothing_where_ids_are_stable(self):
        rec = write_record(self.tmp / "g6.json", [gbox("glyph/3/0/1/4/2", BOX_A)], [dur("glyph/3/0/1/4/2", 2.0)])
        old = self.idx(with_position=False)
        a = J.score(old, rec, "litolff", by="key")
        b = J.score(J.with_derived_positions(old), rec, "litolff")
        self.assertEqual(J.compare_scores(a, b), [])
        self.assertEqual(b["matched"], {"place": 1})

    def test_the_index_rows_gain_mark_kind_only_with_a_position(self):
        idx = json.loads(J.INDEX_PATH.read_text())
        self.assertFalse([r for r in idx["tiles"] if "mark_kind" in r and "position" not in r])


class TestWrittenAtPlace(unittest.TestCase):
    def test_written_host_found_by_place_not_by_key(self):
        row = tile()
        h_other = dict(rg="glyph/3/0/1/4/2", box=BOX_B, kind="note")      # the id the tile asked for, but elsewhere
        h_here = dict(rg="glyph/3/0/1/4/9", box=BOX_A, kind="note")
        self.assertIs(L.host_for_row([h_other, h_here], row, row["subject"], BOX_A), h_here)
        self.assertIs(L.host_for_row([h_other, h_here], tile(with_position=False), row["subject"], None), h_other)  # old key


class TestUnjudged(unittest.TestCase):
    def change(self, kind="note", box=BOX_A, rg="glyph/3/0/1/4/9", side="gained"):
        return dict(kind=kind, side=side, page=3, cx=1015, cy=515, box=box, rg=rg, value="half")

    def cover(self, **kw):
        return L.judged_cover(dict(tiles=[tile(**kw)]), "litolff", {})

    def test_a_covered_value_change_is_not_listed(self):
        un = L.unjudged_changes([self.change()], self.cover())
        self.assertEqual((len(un["unjudged"]), un["judged"]), (0, 1))

    def test_the_twin_a_change_elsewhere_is_listed(self):
        un = L.unjudged_changes([self.change(box=BOX_B, rg="glyph/3/0/1/4/11")], self.cover())
        self.assertEqual(len(un["unjudged"]), 1)
        self.assertEqual(un["unjudged"][0]["place"], [3, 0, 1, 4])

    def test_a_value_tile_does_not_cover_the_accidental_in_front_of_it(self):
        un = L.unjudged_changes([self.change(kind="accidental")], self.cover())
        self.assertEqual(len(un["unjudged"]), 1)

    def test_same_box_in_another_cell_is_not_covered_for_a_positioned_tile(self):
        un = L.unjudged_changes([self.change(rg="glyph/3/0/1/5/9")], self.cover())
        self.assertEqual(len(un["unjudged"]), 1)

    def test_a_change_with_no_page_box_is_counted_not_listed(self):
        un = L.unjudged_changes([dict(self.change(), box=None)], self.cover())
        self.assertEqual((len(un["unjudged"]), un["no_place"]), (0, 1))

    def test_lines_name_the_place(self):
        un = L.unjudged_changes([self.change(box=BOX_B, rg="glyph/3/0/1/4/11")], self.cover())
        self.assertIn("litolff p3 3/0/1/4  note gained half", L.unjudged_lines("litolff", un["unjudged"])[0])

    def test_tiles_are_cut_from_the_unjudged_only(self):
        un = L.unjudged_changes([self.change(box=BOX_B, rg="glyph/3/0/1/4/11"), self.change()], self.cover())
        items = L.pick_tiles({"litolff": un["unjudged"]}, {}, 1, n_cases=12, n_controls=0)
        self.assertEqual([i["box"] for i in items], [BOX_B])


if __name__ == "__main__":
    unittest.main()
