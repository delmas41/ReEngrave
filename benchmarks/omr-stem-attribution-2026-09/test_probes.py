"""Tests for the stem-attribution probes — because the MEASUREMENT is the product.

⚠️ THIS LANE SHIPPED NO CHANGE UNDER `tools/`. What it delivers is a set of
numbers and a refusal, so what has to be mutation-tested is the instrument
that produced them. Every assertion below is on a claim a conclusion rests on.

⚠️⚠️ THE FIRST TEST IS THE LOAD-BEARING ONE. Every reach and distribution
figure in FINDINGS.md claims to reproduce what `_stems_on` does. That is only
true while this probe's overlap predicate agrees with the SHIPPED
`rhythm._boxes_overlap` exactly -- including at the touching boundary, which
the shipped one counts and a strict predicate does not. It is asserted against
the real function, not against a restatement of it.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / "probe"))
sys.path.insert(0, str(ROOT))

import reach  # noqa: E402
import chord_shadow  # noqa: E402


class TestTheOverlapPredicateIsTheShippedOne(unittest.TestCase):
    """The probe must ask exactly the question `_stems_on` asks."""

    def setUp(self):
        from tools.omr.staged.adjudicators.rhythm import _boxes_overlap
        self.shipped = _boxes_overlap

    def test_agrees_on_a_grid_of_boxes_including_the_touching_case(self):
        a = (10.0, 10.0, 10.0, 10.0)
        cases = []
        for x in range(0, 40, 3):
            for y in range(0, 40, 3):
                for w in (1, 5, 10):
                    cases.append((float(x), float(y), float(w), 7.0))
        self.assertTrue(cases)
        for b in cases:
            self.assertEqual(reach.overlap(a, b), self.shipped(a, b),
                             msg=f"disagree on {b}")

    def test_the_touching_boundary_is_INCLUDED_by_both(self):
        # ⚠️ A strict predicate would drop this pair, and the record's own
        # population would then be one pair smaller than `_stems_on` sees.
        a = (0.0, 0.0, 10.0, 10.0)
        b = (10.0, 0.0, 5.0, 10.0)          # touching at x == 10
        self.assertTrue(self.shipped(a, b))
        self.assertTrue(reach.overlap(a, b))

    def test_a_clearly_separated_pair_is_rejected_by_both(self):
        a = (0.0, 0.0, 10.0, 10.0)
        b = (30.0, 0.0, 5.0, 10.0)          # separated in X only
        self.assertFalse(self.shipped(a, b))
        self.assertFalse(reach.overlap(a, b))

    def test_a_pair_separated_in_Y_ONLY_is_rejected_by_both(self):
        # ⚠️ ADDED BY THE MUTATION BATTERY. An arm that made the Y test
        # unconditionally true SURVIVED its named test, because every
        # separation case here was separated in X and the X test still
        # rejected them. The battery had found a real gap: nothing exercised
        # the Y dimension on its own.
        a = (0.0, 0.0, 10.0, 10.0)
        b = (0.0, 30.0, 10.0, 5.0)
        self.assertFalse(self.shipped(a, b))
        self.assertFalse(reach.overlap(a, b))


class TestCellOf(unittest.TestCase):
    def test_a_glyph_subject_maps_to_its_cell(self):
        self.assertEqual(reach.cell_of("glyph/3/1/10/2/16"), "cell/3/1/10/2")

    def test_a_cell_subject_is_its_own_cell(self):
        self.assertEqual(reach.cell_of("cell/3/1/10/2"), "cell/3/1/10/2")

    def test_a_staff_subject_has_no_cell_and_says_so(self):
        # ⚠️ Returning '' rather than a guess: a staff row must not be filed
        # under some cell, or stems would be counted in the wrong bar.
        self.assertEqual(reach.cell_of("staff/3/1/10"), "")


class TestTheEndGapStatistic(unittest.TestCase):
    """distance from the head CENTRE to the NEARER end, in head heights.

    ⚠️ CALLS `reach.end_gap` — the one definition every probe imports. The
    first draft of this class carried its own copy of the formula, which tests
    a copy and would have stayed green while all four probes drifted.
    """

    @staticmethod
    def gap(head, stroke):
        return reach.end_gap(head, stroke)

    def test_a_head_at_the_top_of_a_down_stem_scores_about_a_half(self):
        head = (0.0, 100.0, 20.0, 20.0)          # centre 110
        stroke = (18.0, 110.0, 4.0, 120.0)       # starts at the head's centre
        self.assertAlmostEqual(self.gap(head, stroke), 0.0, places=6)

    def test_a_head_at_the_head_EDGE_scores_a_half(self):
        head = (0.0, 100.0, 20.0, 20.0)          # centre 110, top 100
        stroke = (18.0, 100.0, 4.0, 120.0)       # starts at the head's TOP
        self.assertAlmostEqual(self.gap(head, stroke), 0.5, places=6)

    def test_a_head_halfway_along_a_long_stroke_scores_large(self):
        head = (0.0, 100.0, 20.0, 20.0)          # centre 110
        stroke = (18.0, 40.0, 4.0, 140.0)        # 40..180, midpoint 110
        self.assertAlmostEqual(self.gap(head, stroke), 70.0 / 20.0, places=6)

    def test_it_is_SCALE_FREE_in_the_stroke_length(self):
        # ⚠️ THE WHOLE REASON THIS REPLACED `frac`. A head at an end scores
        # the same whether the stroke is short or long; `frac` does not.
        head = (0.0, 100.0, 20.0, 20.0)
        short = (18.0, 100.0, 4.0, 30.0)
        long_ = (18.0, 100.0, 4.0, 300.0)
        self.assertAlmostEqual(self.gap(head, short),
                               self.gap(head, long_), places=6)

    def test_frac_is_NOT_scale_free_which_is_the_defect_it_replaced(self):
        head = (0.0, 100.0, 20.0, 20.0)          # centre 110
        short = (18.0, 100.0, 4.0, 30.0)
        long_ = (18.0, 100.0, 4.0, 300.0)

        def frac(h, s):
            return ((h[1] + h[3] / 2.0) - s[1]) / s[3]
        self.assertGreater(frac(head, short), 0.25)   # reads as "mid stroke"
        self.assertLess(frac(head, long_), 0.05)      # reads as "at an end"


class TestChordShadow(unittest.TestCase):
    """A stroke carrying one head may still be a CHORD's stroke.

    ⚠️ These call `solo_pairs_with_shadows` -- the function the probe runs --
    rather than re-deriving its loop. The first draft re-derived it, which
    tests a COPY, and its fixture put BOTH heads on the stroke so the pair was
    never solo and the named case was never reached. It went red.
    """

    HEAD_ON_STROKE = (100.0, 200.0, 20.0, 20.0)      # centre (110, 210)
    STROKE = (118.0, 165.0, 4.0, 120.0)              # x 118-122, y 165-285

    def test_a_partner_at_the_same_x_inside_the_span_is_found(self):
        # ⚠️ THE PARTNER MUST NOT OVERLAP THE STROKE, or the pair is not solo
        # and this tests nothing. x 96-116 clears the stroke's 118-122.
        heads = {"cell/0/0/0/0": [
            ("glyph/0/0/0/0/1", "o1", self.HEAD_ON_STROKE),
            ("glyph/0/0/0/0/2", "o2", (96.0, 170.0, 20.0, 20.0)),
        ]}
        stems = {"cell/0/0/0/0": [("s1", self.STROKE)]}
        rows = chord_shadow.solo_pairs_with_shadows(stems, heads)
        self.assertEqual(len(rows), 1, "the pair must be SOLO for this case")
        self.assertEqual(rows[0]["subject"], "glyph/0/0/0/0/1")
        self.assertEqual(rows[0]["n_chord_shadows"], 1)

    def test_a_head_far_away_in_x_is_NOT_a_shadow(self):
        heads = {"cell/0/0/0/0": [
            ("glyph/0/0/0/0/1", "o1", self.HEAD_ON_STROKE),
            ("glyph/0/0/0/0/2", "o2", (400.0, 170.0, 20.0, 20.0)),
        ]}
        stems = {"cell/0/0/0/0": [("s1", self.STROKE)]}
        rows = chord_shadow.solo_pairs_with_shadows(stems, heads)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["n_chord_shadows"], 0)

    def test_a_head_outside_the_strokes_y_span_is_NOT_a_shadow(self):
        heads = {"cell/0/0/0/0": [
            ("glyph/0/0/0/0/1", "o1", self.HEAD_ON_STROKE),
            ("glyph/0/0/0/0/2", "o2", (96.0, 900.0, 20.0, 20.0)),
        ]}
        stems = {"cell/0/0/0/0": [("s1", self.STROKE)]}
        rows = chord_shadow.solo_pairs_with_shadows(stems, heads)
        self.assertEqual(rows[0]["n_chord_shadows"], 0)

    def test_a_stroke_carrying_TWO_heads_is_not_reported_at_all(self):
        # It is a chord by the overlap test's own reckoning, and out of the
        # rule's scope by construction.
        heads = {"cell/0/0/0/0": [
            ("glyph/0/0/0/0/1", "o1", self.HEAD_ON_STROKE),
            ("glyph/0/0/0/0/2", "o2", (100.0, 160.0, 20.0, 20.0)),
        ]}
        stems = {"cell/0/0/0/0": [("s1", self.STROKE)]}
        self.assertEqual(chord_shadow.solo_pairs_with_shadows(stems, heads), [])


class TestTheArmsRebuildIsTheCanonicalOne(unittest.TestCase):
    """`stem_arm.rebuild` must stay identical to `readjudicate.rebuild`.

    ⚠️ THIS IS WHAT LICENSES THE §10 CLAIM. `stem_arm.py`'s CONTROL 1 fails on
    today's tree (2,760 of 2,993 duration verdicts reproduced), and the whole
    argument that this is the TREE rather than the harness rests on the rebuild
    being the canonical instrument's, verbatim. If somebody edits either one,
    that argument breaks SILENTLY — so it is asserted rather than remembered.
    """

    def test_identical(self):
        import ast

        def src(path, name):
            tree = ast.parse(Path(path).read_text())
            for n in ast.walk(tree):
                if isinstance(n, ast.FunctionDef) and n.name == name:
                    return ast.unparse(n)
            return None

        canon = src(ROOT / "benchmarks" / "omr-staged-duration-beams-2026-09"
                    / "readjudicate.py", "rebuild")
        mine = src(HERE / "stem_arm.py", "rebuild")
        self.assertIsNotNone(canon, "the canonical rebuild() was not found")
        self.assertIsNotNone(mine, "stem_arm's rebuild() was not found")
        self.assertEqual(canon, mine)


class TestTheCommittedNumbersAreReproducible(unittest.TestCase):
    """The artefacts must still say what FINDINGS.md quotes.

    ⚠️ A findings file whose own outputs have drifted is the `stale artefact`
    this repo already records; these read the committed JSON rather than
    restating a number in prose.
    """

    OUT = HERE / "out"

    def _load(self, name):
        p = self.OUT / name
        if not p.exists():
            self.skipTest(f"{name} not present (artefacts not generated)")
        return json.loads(p.read_text())

    def test_no_print_adjudicated_head_has_a_shipped_stem(self):
        d = self._load("truth-reach-breitkopf.json")
        for name, pop in d["populations"].items():
            self.assertEqual(pop["with_a_stem"], 0,
                             msg=f"{name} now has heads with a stem")
            self.assertGreater(pop["in_record"], 0,
                               msg=f"{name} is empty — a vacuous zero")

    def test_the_far_population_is_small_on_both_publishers(self):
        for f in ("endgap-breitkopf.json", "endgap-litolff.json"):
            d = self._load(f)
            solo = d["SOLO_gap_head_heights"]["n"]
            far = d["solo_beyond"]["0.8"]
            self.assertGreater(solo, 500)
            self.assertLess(far / solo, 0.05, msg=f"{f}: FAR share grew")

    def test_solo_is_not_a_chord_guarantee(self):
        for f in ("chordshadow-brahms1-breitkopf-p0-p3.json",
                  "chordshadow-beethoven5-p1-p4.json"):
            d = self._load(f)
            self.assertGreater(d["solo_pairs_with_a_chord_shadow"], 0,
                               msg=f"{f}: the refutation of the safety claim "
                                   f"has vanished")


if __name__ == "__main__":
    unittest.main()
