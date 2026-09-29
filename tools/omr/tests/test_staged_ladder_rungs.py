"""`Q.GLYPH_LADDER` NAMES its rungs, so a refused ledger box can leave the
ladder `glyph_owner` weighs — ROADMAP 2.14.

⚠️ RUN RED FIRST, against the unrepaired tree (before `gather._ledger_index`
carried a glyph key and before `adjudicators.ownership._ladder_complete`
existed): every test below either fails to import (`AttributeError:
_ladder_complete` is not a thing `ownership` exports) or — for
`TestAnOldRecordIsUnchanged`, which needs no repair to pass — is the one
fixture already GREEN on `origin/main`, kept here as the shape-preservation
control. See `benchmarks/omr-family-refusals-2026-09/FINDINGS.md` §2.14 for
the captured RED run.

⚠️ THE POSITIVE CONTROL, per CLAUDE.md §6b and the discipline
`test_staged_family_refusals.py` states: a refusal test that only ever
refuses cannot tell a real discount from a `glyph_owner` that has stopped
reading the ladder tier at all. `TestARefusedRungIsDiscounted`'s second test
is that control — two rungs, NEITHER refused, and the ladder still wins.

The fixture is `test_staged_ownership.py`'s own shape (two staves, one
contested glyph, `Q.GLYPH_BAND_DISTANCE` rows for each candidate) with one
addition: `Q.GLYPH_LADDER`'s `rungs` detail, which is exactly what
`gather._observe_ladder` now files (`test_staged_family_refusals.
TestTheLedgerJoinsTheLadder.test_gather_s_own_ladder_row_NOW_NAMES_ITS_
RUNG_GLYPH` pins the GATHER half; this file pins the ADJUDICATE half that
reads it).
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

UPPER = R.staff(0, 0, 0)      # nearer the glyph, wins on DISTANCE alone
LOWER = R.staff(0, 0, 1)      # further, wins only if its ladder is COMPLETE
GLYPH = R.glyph(0, 0, 0, 0, 0)        # the contested note

#: Two rung subjects, filed under LOWER's own cell — their KIND and STAFF are
#: irrelevant to `adjudicate_ledger_is_not_a_ledger`, which decides on a
#: glyph's own `Q.GLYPH_BOX` row and nothing about who owns it.
RUNG_REFUSED = R.glyph(0, 0, 1, 0, 90)
RUNG_KEPT = R.glyph(0, 0, 1, 0, 91)

EXPECTED = 2       # LOWER's ladder needs two rungs to be COMPLETE

ORDER = (Q.LEDGER_IS_NOT_A_LEDGER, Q.GLYPH_OWNER)


def _band_distances(log: Log) -> None:
    """The contest: nearer UPPER, but LOWER wins it if the ladder is whole."""
    log.observe(GLYPH, Q.GLYPH_BAND_DISTANCE, 1.0, reader=READERS.GEOMETRY,
                frame="page", candidate=UPPER.to_key(), own=True,
                position_in_candidate=20.0)
    log.observe(GLYPH, Q.GLYPH_BAND_DISTANCE, 3.0, reader=READERS.GEOMETRY,
                frame="page", candidate=LOWER.to_key(), own=False,
                position_in_candidate=4.0)


def _named_ladder(log: Log, rung_keys) -> None:
    """Exactly gather._observe_ladder's NEW shape: `found == len(rung_keys)`,
    `rungs` naming each one, in counting order."""
    rung_keys = list(rung_keys)
    log.observe(GLYPH, Q.GLYPH_LADDER, len(rung_keys) == EXPECTED,
                reader=READERS.DETECTOR, frame="page",
                candidate=LOWER.to_key(), expected=EXPECTED,
                found=len(rung_keys), rungs=rung_keys)


def _bare_ledger_box(log: Log, rung: R.Subject) -> None:
    """The minimum that makes `adjudicate_ledger_is_not_a_ledger` run on this
    subject: a `Q.GLYPH_BOX` row classed `ledgerLine`. No `bbox_page_px` and
    no `Q.CELL_STAFF_SPACE` are filed, so `_ledger_geometry` returns
    `(None, [])`, `tall` stays `False`, and the decision reaches
    `Ruling.abstain(ABSTAIN.NO_STAFF_GEOMETRY)` — a real ABSTAINED verdict,
    not merely the absence of one."""
    log.observe(rung, Q.GLYPH_BOX, ("ledgerLine", 10.0, 10.0, 6.0, 4.0),
                reader=READERS.DETECTOR, frame="cell:0", score=0.6,
                category="ledgerLine")


def _refused_ledger_box(log: Log, rung: R.Subject) -> None:
    """The same bare box, PLUS a human `not_a_symbol` verdict.
    `_refused_by_a_human` reads this FIRST, before any geometry, so the
    verdict is a clean DECIDED `True` whatever the box's own shape is."""
    _bare_ledger_box(log, rung)
    log.observe(rung, Q.HUMAN_BOX_VERDICT, "not_a_symbol",
                reader=READERS.SEAN, frame="review:box", sidecar="t.json",
                action="act-0001")


def _run(log: Log) -> Log:
    adjudicate.run(log, order=ORDER)
    return log


class TestARefusedRungIsDiscounted(unittest.TestCase):
    """A REFUSED named rung no longer counts toward `found`."""

    def test_found_drops_and_the_ladder_term_is_withdrawn(self):
        log = Log()
        _band_distances(log)
        _named_ladder(log, [RUNG_REFUSED.to_key(), RUNG_KEPT.to_key()])
        _refused_ledger_box(log, RUNG_REFUSED)
        # ⚠️ ROADMAP 2.6c. UPPER is 1.0 space from its own band, which a real
        # gather would expect ONE rung for (`int(1.0 + LEDGER_ROUND_UP) ==
        # 1`) -- so its ladder must be recorded as genuinely BROKEN here,
        # not left absent. An absent row now reads as "no crossing was ever
        # needed" (`_ledger_direction_winner`), which UPPER's own distance
        # does not support; without this it would be mistaken for the
        # ledger-direction case rather than the two-broken-ladders case this
        # test is actually about.
        log.observe(GLYPH, Q.GLYPH_LADDER, False, reader=READERS.DETECTOR,
                    frame="page", candidate=UPPER.to_key(),
                    expected=1, found=0, rungs=[])
        # RUNG_KEPT carries no row at all: the ledger decision never runs on
        # it, `ev.verdict` returns None, and nothing refused it -- kept.
        _run(log)

        ledger_v = log.verdict(Q.LEDGER_IS_NOT_A_LEDGER, RUNG_REFUSED)
        self.assertEqual(ledger_v.outcome, Outcome.DECIDED)
        self.assertTrue(ledger_v.value)

        v = log.verdict(Q.GLYPH_OWNER, GLYPH)
        # One rung discounted, one kept: 1 of 2 EXPECTED -- incomplete, so it
        # contributes nothing and the nearer staff wins on distance alone.
        self.assertEqual(v.value, UPPER.to_key())
        self.assertEqual(v.reason, "distance")
        self.assertEqual(
            tuple(v.detail.get("ladder_discounted_rungs", {})
                  .get(LOWER.to_key(), ())),
            (RUNG_REFUSED.to_key(),))

    def test_POSITIVE_CONTROL_two_kept_rungs_still_win_it_on_the_ladder(self):
        """Without this, the test above would pass on a `glyph_owner` that
        has simply stopped reading the ladder tier, refusal or not."""
        log = Log()
        _band_distances(log)
        _named_ladder(log, [RUNG_REFUSED.to_key(), RUNG_KEPT.to_key()])
        # Neither rung carries any evidence at all: both are kept.
        _run(log)

        v = log.verdict(Q.GLYPH_OWNER, GLYPH)
        self.assertEqual(v.value, LOWER.to_key())
        self.assertEqual(v.reason, "ladder")
        self.assertNotIn("ladder_discounted_rungs", v.detail)


class TestAnAbstainedRungKeepsItsPlace(unittest.TestCase):
    """CLAUDE.md §2 rule 8: *cannot tell* may never become *not a rung* —
    the control in the same class as the refusal above."""

    def test_an_abstained_ledger_verdict_does_not_discount(self):
        log = Log()
        _band_distances(log)
        _named_ladder(log, [RUNG_REFUSED.to_key(), RUNG_KEPT.to_key()])
        _bare_ledger_box(log, RUNG_REFUSED)      # geometry-abstains, no human row
        _run(log)

        ledger_v = log.verdict(Q.LEDGER_IS_NOT_A_LEDGER, RUNG_REFUSED)
        self.assertEqual(ledger_v.outcome, Outcome.ABSTAINED)

        v = log.verdict(Q.GLYPH_OWNER, GLYPH)
        self.assertEqual(v.value, LOWER.to_key())      # UNCHANGED
        self.assertEqual(v.reason, "ladder")
        self.assertNotIn("ladder_discounted_rungs", v.detail)


class TestAnOldRecordIsUnchanged(unittest.TestCase):
    """No `rungs` named (the pre-2.14 GATHER shape): nothing to discount, so
    the row's own `value` decides exactly as it did before this lane."""

    def test_old_shape_ladder_row_behaves_exactly_as_before(self):
        log = Log()
        _band_distances(log)
        log.observe(GLYPH, Q.GLYPH_LADDER, True, reader=READERS.DETECTOR,
                    frame="page", candidate=LOWER.to_key(),
                    expected=EXPECTED, found=EXPECTED)     # no `rungs` key
        _run(log)

        v = log.verdict(Q.GLYPH_OWNER, GLYPH)
        self.assertEqual(v.value, LOWER.to_key())
        self.assertEqual(v.reason, "ladder")
        self.assertNotIn("ladder_discounted_rungs", v.detail)

    def test_an_EMPTY_named_ladder_takes_the_same_path_as_old_shape(self):
        """`found == 0`, genuinely named (`rungs=[]`) rather than absent, has
        nothing to discount either — it must not be mistaken for the
        old-shape fallback and it must not crash looking up zero rungs."""
        log = Log()
        _band_distances(log)
        log.observe(GLYPH, Q.GLYPH_LADDER, False, reader=READERS.DETECTOR,
                    frame="page", candidate=LOWER.to_key(),
                    expected=EXPECTED, found=0, rungs=[])
        # ⚠️ ROADMAP 2.6c, same reasoning as `TestARefusedRungIsDiscounted`
        # above: UPPER's own real (non-vacuous) broken ladder must be
        # recorded so this stays the "both broken" case rather than reading
        # as ledger-direction's "one clean, one broken".
        log.observe(GLYPH, Q.GLYPH_LADDER, False, reader=READERS.DETECTOR,
                    frame="page", candidate=UPPER.to_key(),
                    expected=1, found=0, rungs=[])
        _run(log)

        v = log.verdict(Q.GLYPH_OWNER, GLYPH)
        self.assertEqual(v.value, UPPER.to_key())      # broken ladder: no tier
        self.assertEqual(v.reason, "distance")
        self.assertNotIn("ladder_discounted_rungs", v.detail)


if __name__ == "__main__":
    unittest.main()
