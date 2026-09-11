"""One piece of ink is one element — the contest resolved, not relocated.

⚠️ THE PREMISE THE WHOLE REPAIR RESTS ON, and it is a property of a DOMAIN
rather than of a rule: `adjudicate_glyph_owner` declares
`subjects_from=Q.GLYPH_BAND_DISTANCE`, and `gather_contested_glyphs` files a
band-distance row only where TWO same-class detections on DIFFERENT staves
overlap. So a glyph whose ownership verdict names another staff has a twin on
that staff BY CONSTRUCTION, and relocating it doubles rather than rescues.

Widen that domain and the repair becomes unsafe, so the domain is asserted off
the REGISTRY rather than remembered, and the two-detections premise is asserted
against `gather_contested_glyphs` by running it — not by restating what it is
believed to do.

⚠️ `arc_owner` is the deliberate counter-example and is asserted too: its
domain is every `Q.ARC_BOX`, so it CAN move an arc onto a staff that detected
nothing (CLAUDE.md records six of twelve doing so), and the rule here must
never be applied to it.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.adjudicate import is_relocated_copy
from tools.omr.staged.record import Log, Q, READERS


class TestTheRuleItself(unittest.TestCase):
    def test_a_verdict_naming_another_staff_is_a_relocated_copy(self):
        self.assertTrue(
            is_relocated_copy("glyph/1/0/7/0/1", "staff/1/0/8"))

    def test_a_verdict_naming_its_own_staff_is_not(self):
        self.assertFalse(
            is_relocated_copy("glyph/1/0/7/0/1", "staff/1/0/7"))

    def test_no_verdict_is_not_a_relocation(self):
        """⚠️ ABSENCE IS NOT A DECISION. A glyph with no ownership verdict was
        never contested; treating a missing verdict as a relocation would drop
        every uncontested notehead on the page."""
        self.assertFalse(is_relocated_copy("glyph/1/0/7/0/1", None))
        self.assertFalse(is_relocated_copy("glyph/1/0/7/0/1", ""))
        self.assertFalse(is_relocated_copy("glyph/1/0/7/0/1", []))

    def test_it_accepts_a_Subject_as_well_as_a_key(self):
        self.assertTrue(
            is_relocated_copy(R.glyph(1, 0, 7, 0, 1), "staff/1/0/8"))


class TestTheDomainThatMakesItSafe(unittest.TestCase):
    """⚠️ DERIVED FROM THE REGISTRY, never from a written list."""

    def test_glyph_owner_speaks_only_about_contested_glyphs(self):
        spec = adjudicate.REGISTRY[Q.GLYPH_OWNER]
        self.assertEqual(
            spec.subjects_from, Q.GLYPH_BAND_DISTANCE,
            "`is_relocated_copy` is safe only because a glyph_owner verdict "
            "implies a twin. Widening this domain to every glyph makes "
            "dropping the non-own copy delete real ink.")

    def test_arc_owner_does_NOT_and_the_rule_must_not_reach_it(self):
        spec = adjudicate.REGISTRY[Q.ARC_OWNER]
        self.assertEqual(spec.subjects_from, Q.ARC_BOX)


class TestOneLetterIsNeverContested(unittest.TestCase):
    """⚠️ THE PREMISE, RUN RATHER THAN RESTATED.

    This is the case the rewritten `TestOwnershipResolvesTheContest` fixture
    used to assert the opposite of: a lone glyph produces NO band-distance row,
    so it is never handed to another staff, so the sole-evidence "rescue" the
    dynamics docstring credited is structurally unreachable on this path.
    """

    def _band_rows(self, n_copies):
        """Run the REAL gatherer over a two-staff system holding one glyph in
        `n_copies` of its staves' cells, and return the band-distance rows.

        ⚠️ Boxes are placed away from the origin deliberately: at (0, 0) a
        corner box and a width box agree in every coordinate, so a frame error
        would be invisible — the confusion CLAUDE.md records costing a session.
        """
        log = Log()
        staves = [_Staff(0, [1100.0, 1110.0, 1120.0, 1130.0, 1140.0]),
                  _Staff(1, [1300.0, 1310.0, 1320.0, 1330.0, 1340.0])]
        cells = [_Cell(0, 0), _Cell(1, 0)]
        dets = {}
        for i in range(n_copies):
            dets[R.cell(0, 0, i, 0).to_key()] = [
                _Det("noteheadBlackInSpace", 200.0, 1200.0, 20.0, 18.0)]
        G.gather_ownership_evidence(
            log, _PWS(staves), cells,
            {st.staff_index: (0, st.staff_index) for st in staves}, dets)
        return [r for r in log.all_rows()
                if getattr(r, "quantity", None) == Q.GLYPH_BAND_DISTANCE]

    def test_ONE_copy_yields_no_contest(self):
        self.assertEqual(self._band_rows(1), [])

    def test_TWO_copies_DO_yield_a_contest(self):
        """⚠️ THE POSITIVE CONTROL IN THE SAME CLASS. Without it the test above
        would pass for any reason at all — a broken fixture, a renamed
        quantity, a gatherer that files nothing ever."""
        self.assertTrue(self._band_rows(2))


class _Det:
    def __init__(self, name, x, y, w, h):
        self.smufl_name = name
        self.x_canonical = x
        self.y_canonical = y
        self.width_canonical = w
        self.height_canonical = h
        self.confidence = 0.8


class _Staff:
    def __init__(self, staff_index, line_ys):
        self.staff_index = staff_index
        self.line_ys = line_ys


class _Cell:
    def __init__(self, staff_index, measure_index):
        self.page_index = 0
        self.staff_index = staff_index
        self.measure_index = measure_index
        self.bbox_page_px = [0.0, 0.0, 2000.0, 2000.0]
        self.upscale_factor = 1.0


class _PWS:
    def __init__(self, staves):
        self.staves = staves
        self.page = _P()


class _P:
    page_index = 0


if __name__ == "__main__":
    unittest.main()
