"""Tests for the chord/stroke-join probes.

⚠️ THEY EXERCISE THE FUNCTIONS THE PROBES CALL, NOT COPIES OF THEM. The
sibling lane records a test that re-derived its loop inline and therefore
tested a copy; every case here imports the shipped function.

Run: `python3 -m pytest benchmarks/omr-chord-stroke-join-2026-09/test_probes.py`
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(_BENCH / "probe"))
sys.path.insert(0, str(_BENCH.parents[1]))

from common import (  # noqa: E402
    _Row, _boxes_overlap, _stems_on, cell_of, x_overlap, y_overlap,
)
import flip  # noqa: E402
import reach  # noqa: E402
import score as scoring  # noqa: E402
from decompose import shadows  # noqa: E402


def H(x, y, w=10.0, h=10.0, subject="glyph/0/0/0/0/0", page=None):
    return _Row((x, y, w, h), f"obs:{subject}", subject, page)


def S(x, y, w=2.0, h=40.0, rid="obs:stem"):
    return _Row((x, y, w, h), rid, "stem")


class TestThePredicatesAreTheShippedOnes(unittest.TestCase):
    """⚠️ Both halves must agree with `_boxes_overlap` AT THE TOUCHING EDGE,
    which the shipped predicate counts and a strict `<` does not."""

    def test_x_overlap_matches_the_shipped_predicate(self):
        for ax in range(0, 40, 3):
            a, b = (ax, 0.0, 10.0, 10.0), (20.0, 0.0, 10.0, 10.0)
            self.assertEqual(x_overlap(a, b), _boxes_overlap(a, b),
                             f"disagree at ax={ax}")

    def test_y_overlap_matches_the_shipped_predicate(self):
        for ay in range(0, 40, 3):
            a, b = (0.0, ay, 10.0, 10.0), (0.0, 20.0, 10.0, 10.0)
            self.assertEqual(y_overlap(a, b), _boxes_overlap(a, b),
                             f"disagree at ay={ay}")

    def test_the_touching_edge_is_INCLUDED(self):
        self.assertTrue(x_overlap((0.0, 0.0, 10.0, 1.0), (10.0, 0.0, 5.0, 1.0)))
        self.assertTrue(y_overlap((0.0, 0.0, 1.0, 10.0), (0.0, 10.0, 1.0, 5.0)))


class TestCellOf(unittest.TestCase):
    def test_a_glyph_key_yields_its_cell(self):
        self.assertEqual(cell_of("glyph/1/0/2/4/1"), "cell/1/0/2/4")

    def test_a_cell_key_is_its_own_cell(self):
        self.assertEqual(cell_of("cell/1/0/2/4"), "cell/1/0/2/4")

    def test_anything_else_abstains(self):
        self.assertEqual(cell_of("staff/1/0/2"), "")


class TestUnjoinedMembers(unittest.TestCase):
    """The population the widened join would ADD."""

    def _chord(self):
        # a stroke at x 20-22 running y 0-40; the joined head touches it,
        # the second head stands at the same x and MISSES it by 3 px.
        stroke = S(20.0, 0.0)
        joined = H(10.0, 0.0, subject="glyph/0/0/0/0/joined")
        stranded = H(7.0, 20.0, subject="glyph/0/0/0/0/stranded")
        return stroke, joined, stranded

    def test_it_finds_a_chord_member_the_overlap_test_dropped(self):
        stroke, joined, stranded = self._chord()
        self.assertTrue(_stems_on(joined.value, [stroke]))
        self.assertFalse(_stems_on(stranded.value, [stroke]))
        rows = reach.unjoined_members([stroke], [joined, stranded])
        self.assertEqual([r["head"] for r in rows], [stranded.subject])
        self.assertEqual(rows[0]["mates"], [joined.subject])

    def test_a_head_that_ALREADY_has_a_stroke_is_never_reached(self):
        """⚠️ THE ONE-SIDEDNESS. The tier may only serve a head that abstains
        `no_stem`; a head with a stem of its own must be untouched, or the
        change could turn a DECIDED verdict into `stems_disagree`."""
        stroke, joined, stranded = self._chord()
        own = S(6.0, 18.0, rid="obs:own")
        self.assertTrue(_stems_on(stranded.value, [own]))
        rows = reach.unjoined_members([stroke, own], [joined, stranded])
        self.assertEqual(rows, [])

    def test_a_head_OUTSIDE_the_strokes_y_span_is_not_reached(self):
        stroke, joined, _ = self._chord()
        far = H(7.0, 200.0, subject="glyph/0/0/0/0/far")
        rows = reach.unjoined_members([stroke], [joined, far])
        self.assertEqual(rows, [])

    def test_a_head_at_a_DIFFERENT_x_is_not_reached(self):
        """The rule's only x ruler is the joined head's own width."""
        stroke, joined, _ = self._chord()
        elsewhere = H(400.0, 20.0, subject="glyph/0/0/0/0/elsewhere")
        rows = reach.unjoined_members([stroke], [joined, elsewhere])
        self.assertEqual(rows, [])

    def test_a_stroke_with_NO_joined_head_recruits_nobody(self):
        """⚠️ Without this the rule would be *any head inside a stroke's
        reach*, which is the successive-note case."""
        stroke = S(200.0, 0.0)
        stranded = H(7.0, 20.0, subject="glyph/0/0/0/0/stranded")
        self.assertEqual(reach.unjoined_members([stroke], [stranded]), [])


class TestTheDecompositionReproducesTheSiblingsWindows(unittest.TestCase):
    """`decompose.shadows` restates two windows on purpose; these pin them."""

    def test_a_solo_pair_with_a_stemless_shadow_is_flagged_as_such(self):
        stroke = S(20.0, 0.0)
        joined = H(10.0, 0.0, subject="glyph/0/0/0/0/a")
        shadow = H(7.0, 20.0, subject="glyph/0/0/0/0/b")
        rows = shadows([stroke], [joined, shadow])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["n_chord_shadows"], 1)
        self.assertTrue(rows[0]["shadows"][0]["shadow_is_stemless"])

    def test_a_shadow_WITH_a_stroke_of_its_own_is_reported_as_not_stemless(self):
        """⚠️ THE COLUMN THE PUBLISHED 73/98 DID NOT HAVE. Two thirds of that
        figure is this case, and it is not a missing join at all."""
        stroke = S(20.0, 0.0)
        joined = H(10.0, 0.0, subject="glyph/0/0/0/0/a")
        shadow = H(7.0, 20.0, subject="glyph/0/0/0/0/b")
        own = S(6.0, 18.0, rid="obs:own")
        rows = shadows([stroke, own], [joined, shadow])
        solo = [r for r in rows if r["stem"] == stroke.id]
        self.assertEqual(len(solo), 1)
        self.assertEqual(solo[0]["n_chord_shadows"], 1)
        self.assertFalse(solo[0]["shadows"][0]["shadow_is_stemless"])

    def test_a_stroke_with_two_joined_heads_is_not_a_solo_pair(self):
        stroke = S(20.0, 0.0)
        a = H(10.0, 0.0, subject="glyph/0/0/0/0/a")
        b = H(10.0, 20.0, subject="glyph/0/0/0/0/b")
        self.assertEqual(shadows([stroke], [a, b]), [])


class TestTheDirectionFlip(unittest.TestCase):
    """Adding the missing member changes what `_stem_direction` sees."""

    def test_a_member_at_the_far_extreme_flips_the_answer(self):
        # stroke spans y 0..40; the only JOINED head sits at its top, so the
        # stroke reads as hanging BELOW it -> "down". A second member at the
        # bottom makes the projection above the group the larger one -> "up".
        stroke = S(20.0, 0.0).value
        top = (10.0, 0.0, 10.0, 10.0)
        bottom = (10.0, 30.0, 10.0, 10.0)
        self.assertEqual(flip._dir(stroke, [top]), "down")
        self.assertEqual(flip._dir(stroke, [bottom]), "up")
        # ⚠️ so which member is missing decides the answer, which is why a
        # widened join is not a no-op for heads that already have one.
        self.assertNotEqual(flip._dir(stroke, [top]),
                            flip._dir(stroke, [bottom]))

    def test_extra_members_agrees_with_unjoined_members(self):
        stroke = S(20.0, 0.0)
        joined = H(10.0, 0.0, subject="glyph/0/0/0/0/a")
        stranded = H(7.0, 20.0, subject="glyph/0/0/0/0/b")
        heads = [joined, stranded]
        extra = flip.extra_members(stroke.value, heads, [stroke], heads)
        self.assertEqual([h.subject for h in extra], [stranded.subject])


class TestTheScorer(unittest.TestCase):
    """⚠️ The stratum comes from the MANIFEST, so a mis-stratified tile is
    impossible by construction and a gap in the census is loud."""

    def _write(self, tmp, tiles, verdicts):
        (tmp / "out").mkdir(parents=True, exist_ok=True)
        (tmp / "out" / "manifest-x.json").write_text(json.dumps(
            {"written": len(tiles), "refused": [], "tiles": tiles}))
        (tmp / "ADJUDICATION-x.json").write_text(json.dumps(
            {"verdicts": {k: {"verdict": v} for k, v in verdicts.items()}}))

    def test_it_places_each_tile_by_the_manifests_stratum(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._write(tmp,
                        [{"id": "a", "stratum": "CANDIDATE"},
                         {"id": "b", "stratum": "CONTROL"}],
                        {"a": "separate_stems", "b": "one_shared_stem"})
            man, adj = scoring.load(tmp, "x")
            counts, missing, extra = scoring.tally(man, adj)
            self.assertEqual(dict(counts["CANDIDATE"]), {"separate_stems": 1})
            self.assertEqual(dict(counts["CONTROL"]), {"one_shared_stem": 1})
            self.assertEqual((missing, extra), ([], []))

    def test_a_written_but_unadjudicated_tile_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._write(tmp, [{"id": "a", "stratum": "CANDIDATE"}], {})
            man, adj = scoring.load(tmp, "x")
            _c, missing, extra = scoring.tally(man, adj)
            self.assertEqual((missing, extra), (["a"], []))

    def test_an_adjudicated_tile_absent_from_the_manifest_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._write(tmp, [], {"z": "one_shared_stem"})
            man, adj = scoring.load(tmp, "x")
            _c, missing, extra = scoring.tally(man, adj)
            self.assertEqual((missing, extra), ([], ["z"]))

    def _run_check(self, tmp):
        return subprocess.run(
            [sys.executable, str(_BENCH / "probe" / "score.py"),
             "--bench", str(tmp), "--labels", "x", "--check"],
            capture_output=True, text=True,
            env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
        ).returncode

    def test_check_REFUSES_when_no_control_was_adjudicated_correct(self):
        """⚠️ A pass whose controls all read `cannot_tell` has not shown the
        question is answerable, so its candidate verdicts mean nothing."""
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._write(tmp,
                        [{"id": "a", "stratum": "CANDIDATE"},
                         {"id": "b", "stratum": "CONTROL"}],
                        {"a": "separate_stems", "b": "cannot_tell"})
            self.assertEqual(self._run_check(tmp), 2)

    def test_check_REFUSES_when_a_control_adjudicates_against_the_record(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._write(tmp,
                        [{"id": "a", "stratum": "CANDIDATE"},
                         {"id": "b", "stratum": "CONTROL"},
                         {"id": "c", "stratum": "CONTROL"}],
                        {"a": "separate_stems", "b": "one_shared_stem",
                         "c": "separate_stems"})
            self.assertEqual(self._run_check(tmp), 2)

    def test_check_PASSES_on_a_healthy_pass(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            self._write(tmp,
                        [{"id": "a", "stratum": "CANDIDATE"},
                         {"id": "b", "stratum": "CONTROL"}],
                        {"a": "separate_stems", "b": "one_shared_stem"})
            self.assertEqual(self._run_check(tmp), 0)


class TestTheCommittedResult(unittest.TestCase):
    """⚠️ The published numbers, re-derived from the committed artefacts. A
    finding this file quotes must not be able to drift from its data."""

    def setUp(self):
        man, adj = scoring.load(_BENCH, "breitkopf")
        self.bk, _m, _e = scoring.tally(man, adj)
        man, adj = scoring.load(_BENCH, "litolff")
        self.li, _m, _e = scoring.tally(man, adj)

    def test_every_control_that_could_be_read_reads_one_shared_stem(self):
        for c in (self.bk["CONTROL"], self.li["CONTROL"]):
            wrong = {k: v for k, v in c.items()
                     if k not in ("one_shared_stem", "cannot_tell")}
            self.assertEqual(wrong, {})
        self.assertEqual(self.bk["CONTROL"]["one_shared_stem"]
                         + self.li["CONTROL"]["one_shared_stem"], 12)

    def test_two_candidates_of_thirty_three_are_a_real_chord(self):
        cand = self.bk["CANDIDATE"] + self.li["CANDIDATE"]
        self.assertEqual(sum(cand.values()), 33)
        self.assertEqual(cand["one_shared_stem"], 2)

    def test_thirteen_candidates_are_not_two_noteheads(self):
        cand = self.bk["CANDIDATE"] + self.li["CANDIDATE"]
        self.assertEqual(sum(cand[k] for k in scoring.NOT_A_HEAD), 13)

    def test_the_reach_figures_are_the_committed_ones(self):
        for label, heads, no_stem in (("litolff", 20, 793),
                                      ("breitkopf", 11, 1529)):
            d = json.loads((_BENCH / "out" / f"reach-{label}.json").read_text())
            self.assertEqual(d["REACH"]["heads_reached"], heads)
            self.assertEqual(d["counts_today"]["no_stem"], no_stem)

    def test_the_published_shadow_figures_are_reproduced(self):
        """73 / 98 -- the sibling lane's `solo_pairs_with_a_chord_shadow`."""
        for label, published, stemless in (("litolff", 73, 24),
                                           ("breitkopf", 98, 33)):
            d = json.loads(
                (_BENCH / "out" / f"decompose-{label}.json").read_text())
            self.assertEqual(d["solo_pairs_with_a_chord_shadow"], published)
            self.assertEqual(
                d["shadow_rows_where_the_shadow_IS_STEMLESS"], stemless)


if __name__ == "__main__":
    unittest.main()
