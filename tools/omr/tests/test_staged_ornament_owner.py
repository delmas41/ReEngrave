"""`ornament_owner`: a trill is played ON A NOTE, and a tremolo has no side.

⚠️ IT SHARES `fermata_owner`'s SHAPE AND DIFFERS IN TWO PLACES, and both are
the engraving's rather than a modelling preference:

  * a fermata hangs over whatever SOUNDS, most often a whole-bar rest; an
    ornament names a NOTEHEAD and never a rest. `_mxl_note` says the same from
    the other side — it refuses `<ornaments>` on a rest and emits `<fermata>`
    regardless;
  * a fermata is HOISTED to a chord's first `<note>` (one pause, one chord);
    an ornament is PER HEAD, because a chord can carry a trill on any subset of
    its members.

⚠️ CLOSING THIS QUANTITY CLOSES NO DETECTION GAP. `export_coverage.KNOWN_GAPS`
records the eleven-work truth's only ornaments as twelve `<tremolo>` against a
detector producing ZERO tremolo detections over 34,115. The RECORD can now name
the family; the PAGE still supplies none of it.
"""

from __future__ import annotations

import unittest

from tools.omr import transcribe as _legacy
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS


def _head(log, gi, x, y=40.0, w=20.0):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", x, y, w, 20.0),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    return g


def _rest(log, gi, x, y=40.0):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, ("restWhole", x, y, 20.0, 20.0),
                reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="rest")
    return g


def _mark(log, gi, x, cls="ornamentTrill", y=0.0, w=14.0):
    g = R.glyph(0, 0, 0, 0, gi)
    kind = gather._ornament_kind(cls)
    k, strokes, above = kind
    g_ = g
    log.observe(g_, Q.ORNAMENT_MARK, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=0.8,
                x0=x, x1=x + w, y0=y, y1=y + 10.0,
                x_center=x + w / 2.0, y_center=y + 5.0,
                kind=k, strokes=strokes,
                side=("above" if above is True
                      else "below" if above is False else None))
    return g_


def _decide(log, gi=0):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.ORNAMENT_OWNER, R.glyph(0, 0, 0, 0, gi))


class TestItIsWiredAtAllThreeLegs(unittest.TestCase):
    def test_the_registry_says_it_decides(self):
        self.assertFalse(adjudicate.REGISTRY[Q.ORNAMENT_OWNER].stub)

    def test_the_exporter_reads_the_verdict(self):
        import inspect
        from tools.omr.staged import export
        self.assertIn("Q.ORNAMENT_OWNER",
                      inspect.getsource(export._place_ornaments))

    def test_the_families_table_names_a_counter(self):
        from tools.omr.staged.export import FAMILIES
        quantity, _classes, counters = FAMILIES["ornament"]
        self.assertEqual(quantity, Q.ORNAMENT_OWNER)
        self.assertEqual(counters, ("ornaments",))

    def test_the_constant_is_imported_not_restated(self):
        """⚠️ AND IT IS DECLARED UNMEASURED BY ITS OWN AUTHOR. Importing it
        keeps ONE unmeasured number in the tree instead of two that can drift;
        it does not make it measured."""
        import inspect
        from tools.omr.staged.adjudicators import ownership
        src = inspect.getsource(ownership.adjudicate_ornament_owner)
        self.assertIn("_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS", src)
        self.assertNotIn("1.0 *", src)


class TestTheGatherAsksTheTABLE(unittest.TestCase):
    """⚠️ NOT A PREFIX, and the tremolos are why: `tremolo1`-`5` are ornaments
    whose class names do not begin `ornament`."""

    def test_a_tremolo_is_an_ornament(self):
        self.assertEqual(gather._ornament_kind("tremolo3"),
                         ("tremolo", 3, None))

    def test_a_trill_is_an_ornament_printed_above(self):
        self.assertEqual(gather._ornament_kind("ornamentTrill"),
                         ("trill", None, True))

    def test_a_notehead_is_not(self):
        self.assertIsNone(gather._ornament_kind("noteheadBlack"))

    def test_the_table_is_the_LEGACY_one(self):
        """⚠️ AGREEMENT ON EVERY CLASS IT KNOWS, plus an AST check that the
        gather CALLS it. Agreement alone is not enough — a copied table would
        also agree, on the day it was copied."""
        import inspect
        for cls in ("ornamentTrill", "ornamentTurn", "ornamentTurnInverted",
                    "ornamentMordent", "tremolo1", "tremolo5",
                    "noteheadBlack", "restWhole", "articStaccatoAbove"):
            self.assertEqual(gather._ornament_kind(cls),
                             _legacy.ornament_kind(cls), cls)
        self.assertIn("ornament_kind",
                      inspect.getsource(gather._ornament_kind))
        self.assertNotIn("_ORNAMENT_KINDS = ",
                         inspect.getsource(gather))


class TestWhatItNames(unittest.TestCase):

    def test_a_trill_takes_the_note_below_it(self):
        log = Log()
        _mark(log, 0, 100.0)                 # above: smaller y
        head = _head(log, 1, 97.0)
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.reason, "nearest_on_declared_side")
        self.assertEqual(v.detail["ornament"], "trill")
        self.assertIsNone(v.detail["strokes"])

    def test_a_tremolo_has_NO_side_and_the_test_is_SKIPPED(self):
        """⚠️ It rides the STEM and sits on whichever side that is, which the
        legacy rule states explicitly. Here the mark sits BELOW the head — a
        position a side test would refuse."""
        log = Log()
        _mark(log, 0, 100.0, cls="tremolo3", y=200.0)
        head = _head(log, 1, 97.0)
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, head.to_key())
        self.assertEqual(v.reason, "nearest_either_side")
        self.assertEqual(v.detail["strokes"], 3)

    def test_the_two_branches_are_reported_APART(self):
        """A single reason would hide whether a placement satisfied a side
        constraint or merely had none to satisfy."""
        reasons = adjudicate.REGISTRY[Q.ORNAMENT_OWNER].reasons
        self.assertIn("nearest_on_declared_side", reasons)
        self.assertIn("nearest_either_side", reasons)

    def test_the_NEAREST_in_x_wins(self):
        log = Log()
        _mark(log, 0, 100.0)                 # centre 107
        _head(log, 1, 60.0)                  # centre  70
        near = _head(log, 2, 98.0)           # centre 108
        self.assertEqual(_decide(log).value, near.to_key())


class TestTheRefusals(unittest.TestCase):

    def test_a_REST_is_never_an_ornaments_carrier(self):
        """⚠️ THE ONE PLACE THIS DIFFERS FROM `fermata_owner`. A trill is
        played on a note; `_mxl_note` refuses `<ornaments>` on a rest."""
        log = Log()
        _mark(log, 0, 100.0)
        _rest(log, 1, 97.0)
        v = _decide(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_notehead")

        log2 = Log()                          # positive control
        _mark(log2, 0, 100.0)
        _head(log2, 1, 97.0)
        self.assertIs(_decide(log2).outcome, Outcome.DECIDED)

    def test_a_mark_on_the_WRONG_side_abstains(self):
        log = Log()
        _mark(log, 0, 100.0, y=200.0)        # says above, sits BELOW
        _head(log, 1, 97.0)
        self.assertEqual(_decide(log).reason, "no_notehead")

        log2 = Log()                          # positive control
        _mark(log2, 0, 100.0, y=0.0)
        _head(log2, 1, 97.0)
        self.assertIs(_decide(log2).outcome, Outcome.DECIDED)

    def test_a_mark_too_far_in_x_abstains(self):
        log = Log()
        _mark(log, 0, 100.0)
        _head(log, 1, 200.0)                 # far past 1.0 notehead widths
        v = _decide(log)
        self.assertEqual(v.reason, "no_notehead")
        self.assertIn("limit_canonical_px", v.detail)

    def test_a_cell_with_no_notehead_abstains(self):
        log = Log()
        _mark(log, 0, 100.0)
        self.assertEqual(_decide(log).reason, "no_notehead")


if __name__ == "__main__":
    unittest.main()
