"""ROADMAP 2.86 -- a key printed AFTER a system's last barline (a change
announced at the system end) is not a bar, even when the tail's ink is MIXED.

Seen on the print: Brahms 1/i, Breitkopf 317803, pdf p11 system 1 ends with
a double barline and then the new key on every staff (crop
`out/print/bar-drift/brahms_p11_s1_right.png`, branch `crops-bar-drift`).
STAGED kept that strip as a bar (+1 to every later bar number) because
2.47b's vote demotes only a tail whose ink is PURE clef/key/time classes,
and on the plate the detector boxes a key's flats as `accidentalFlat`,
prints naturals cancelling the old key, and a tie or slur end crosses the
strip (FINDINGS `omr-measure-partition-2026-09` §10d: 49 Brahms tails
'mixed', never demoted).

The rule (`structure._mixed_tail_announces_next_key`): a tail whose ink is
KEY-SHAPED on a strict majority of its staves (an accidental run with no
note to alter -- naturals first, then ONE kind of flat/sharp, [C21]; a tie
or slur end is neutral) is demoted ONLY where the NEXT system's decided
`Q.SYSTEM_KEY` differs from this system's -- the change at the boundary is
an already-decided fact the tail announces (connect, never guess). Where
either system's key is not a single corroborated concert key, today's
behaviour stands and the verdict says why.

⚠️ RED against unmodified origin/main (40ab373a): the three mixed-tail
repros, the notehead-duplicating-a-key-box test, and the `why` detail tests
FAIL there (11 bars / no detail); the pure-key control, the real short bar,
the next-key-matches control, the undecided-next-key control, the tie-only
control and the no-next-system control pass there and must still pass.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

PAGE = 0
SYS = 0          # the system whose tail is contested
NEXT = 1         # the system after it
N_STAVES = 4
N_CELLS = 11     # 10 real bars + the contested tail


def _decide(log, quantity, subject):
    return adjudicate.adjudicate_one(log, adjudicate.REGISTRY[quantity],
                                     subject)


def _glyph(log, s, st, c, g, name, x=0.0):
    log.observe(R.glyph(PAGE, s, st, c, g), Q.GLYPH_BOX,
                (name, float(x), 0.0, 1.0, 1.0),
                reader=READERS.DETECTOR, frame="cell:%d" % c, score=0.9,
                category=name)


def _system_key(log, s, corroborated, n=[0]):
    n[0] += 1
    log.record(Verdict(
        id="vrd:sk%d" % n[0], subject=R.system(PAGE, s),
        quantity=Q.SYSTEM_KEY, outcome=Outcome.DECIDED,
        value={"corroborated": list(corroborated),
               "tally": {str(k): N_STAVES for k in corroborated}},
        decider="system_key", reason="read"))


def _system_key_abstained(log, s, n=[0]):
    n[0] += 1
    log.record(Verdict(
        id="vrd:ska%d" % n[0], subject=R.system(PAGE, s),
        quantity=Q.SYSTEM_KEY, outcome=Outcome.ABSTAINED, value=None,
        decider="system_key", reason="one_staff_only"))


def _build(tail, *, this_key=(0,), next_key=(-3,), next_system=True,
           next_abstains=False):
    """`tail` is a list of (name, x) placed in EVERY staff's tail cell, or a
    dict staff -> list. The two systems' `Q.SYSTEM_KEY` verdicts are filed
    after the freeze, as ADJUDICATE would have filed them (ORDER runs
    `system_key` before `measure_partition` since 2.86)."""
    log = Log()
    systems = (SYS, NEXT) if next_system else (SYS,)
    for s in systems:
        for st in range(N_STAVES):
            log.observe(R.staff(PAGE, s, st), Q.BARLINE_COLUMN,
                        N_CELLS if s == SYS else 4,
                        reader=READERS.GEOMETRY, frame="page")
            last = (N_CELLS - 1) if s == SYS else 4
            for c in range(last):
                _glyph(log, s, st, c, 0, "noteheadBlackOnLine")
    for st in range(N_STAVES):
        names = tail[st] if isinstance(tail, dict) else tail
        for gi, (name, x) in enumerate(names):
            _glyph(log, SYS, st, N_CELLS - 1, gi, name, x)
    log.freeze()
    if this_key is not None:
        _system_key(log, SYS, this_key)
    if next_system:
        if next_abstains:
            _system_key_abstained(log, NEXT)
        elif next_key is not None:
            _system_key(log, NEXT, next_key)
    return log


def _partition(log, st=0):
    return _decide(log, Q.MEASURE_PARTITION, R.staff(PAGE, SYS, st))


NAT2_KEYFLAT3 = [("accidentalNatural", 0), ("accidentalNatural", 1),
                 ("keyFlat", 3), ("keyFlat", 4), ("keyFlat", 5)]
ACCFLAT3 = [("accidentalFlat", 0), ("accidentalFlat", 1),
            ("accidentalFlat", 2)]
KEYFLAT3_TIE = [("keyFlat", 1), ("keyFlat", 2), ("keyFlat", 3), ("tie", 0)]


class TestMixedTailAnnouncingTheNextKeyIsNotABar(unittest.TestCase):
    """The three RED repros of the 2026-10-10 bar-drift diagnosis, now with
    the connection the rule needs: the next system's key is decided and
    differs from this one's."""

    def _assert_demoted(self, log):
        for st in range(N_STAVES):
            v = _partition(log, st)
            self.assertEqual(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value, N_CELLS - 1, "staff %d" % st)
            self.assertEqual(v.reason, "cautionary_key_tail_not_a_bar")
            self.assertEqual(v.detail["cautionary_cell"], N_CELLS - 1)
            self.assertEqual(v.detail["key_shaped_vote"], "4/4")
            self.assertEqual(v.detail["this_system_key"], 0)
            self.assertEqual(v.detail["next_system_key"], -3)

    def test_naturals_then_key_flats(self):
        self._assert_demoted(_build(NAT2_KEYFLAT3))

    def test_flats_boxed_as_accidentals(self):
        self._assert_demoted(_build(ACCFLAT3))

    def test_key_flats_with_a_tie_end_crossing_the_tail(self):
        self._assert_demoted(_build(KEYFLAT3_TIE))

    def test_a_minority_of_staves_with_a_real_note_does_not_block(self):
        """MAJORITY, the same shape as 2.47b (DECISIONS 2026-10-01): 3 of 4
        key-shaped staves demote; the 4th staff's stray head is the minority
        misreading, not a real bar."""
        tail = {0: ACCFLAT3, 1: ACCFLAT3, 2: ACCFLAT3,
                3: [("noteheadBlackOnLine", 0)]}
        v = _partition(_build(tail))
        self.assertEqual(v.value, N_CELLS - 1)
        self.assertEqual(v.detail["key_shaped_vote"], "3/4")


class TestControls(unittest.TestCase):

    def test_pure_key_tail_is_demoted_as_today_whatever_the_next_key(self):
        """CONTROL (2.47b, unchanged): `keyNatural`x2 + `keyFlat`x3 is PURE
        signature ink and is demoted by the old vote, with no next-system
        reading at all."""
        tail = [("keyNatural", 0), ("keyNatural", 1), ("keyFlat", 3),
                ("keyFlat", 4), ("keyFlat", 5)]
        v = _partition(_build(tail, this_key=None, next_system=False))
        self.assertEqual(v.value, N_CELLS - 1)
        self.assertEqual(v.reason, "cautionary_tail_not_a_bar")

    def test_a_real_short_final_bar_with_heads_stays_a_bar(self):
        """POSITIVE CONTROL: a flat in front of a NOTEHEAD alters the note;
        it is a real short bar even where the key changes at the next
        system."""
        tail = [("accidentalFlat", 0), ("noteheadBlackOnLine", 1),
                ("noteheadBlackOnLine", 3)]
        v = _partition(_build(tail))
        self.assertEqual(v.value, N_CELLS)
        self.assertEqual(v.reason, "read")

    def test_a_short_final_bar_with_a_rest_and_an_accidental_stays_a_bar(self):
        tail = [("accidentalSharp", 0), ("restQuarter", 2)]
        v = _partition(_build(tail))
        self.assertEqual(v.value, N_CELLS)

    def test_mixed_tail_whose_next_key_is_the_same_stays_as_today(self):
        """The next system's decided key is THIS system's: nothing changes
        at the boundary, so key-shaped ink there is not an announcement we
        can connect -- today's count stands, and the verdict says why."""
        v = _partition(_build(ACCFLAT3, this_key=(-3,), next_key=(-3,)))
        self.assertEqual(v.value, N_CELLS)
        self.assertEqual(v.reason, "read")
        self.assertEqual(v.detail["mixed_tail_kept"], "next_key_unchanged")

    def test_mixed_tail_whose_next_key_is_not_decided_stays_as_today(self):
        v = _partition(_build(ACCFLAT3, next_abstains=True))
        self.assertEqual(v.value, N_CELLS)
        self.assertEqual(v.detail["mixed_tail_kept"], "next_key_not_decided")

    def test_mixed_tail_whose_next_key_is_ambiguous_stays_as_today(self):
        """Two corroborated concert keys on the next system (bitonal or
        half-misread): not ONE decided key, so no connection."""
        v = _partition(_build(ACCFLAT3, next_key=(-3, 0)))
        self.assertEqual(v.value, N_CELLS)
        self.assertEqual(v.detail["mixed_tail_kept"], "next_key_not_decided")

    def test_mixed_tail_whose_own_key_is_not_decided_stays_as_today(self):
        v = _partition(_build(ACCFLAT3, this_key=None))
        self.assertEqual(v.value, N_CELLS)
        self.assertEqual(v.detail["mixed_tail_kept"], "this_key_not_decided")

    def test_mixed_tail_on_the_last_system_stays_as_today(self):
        v = _partition(_build(ACCFLAT3, next_system=False))
        self.assertEqual(v.value, N_CELLS)
        self.assertEqual(v.detail["mixed_tail_kept"], "no_next_system")

    def test_a_tail_holding_only_a_tie_end_stays_a_bar(self):
        """A tie or slur end is NEUTRAL: it votes for neither reading, so a
        tail of nothing else is no evidence (rule 8) -- today's count."""
        v = _partition(_build([("tie", 0)]))
        self.assertEqual(v.value, N_CELLS)
        self.assertEqual(v.reason, "read")
        self.assertNotIn("mixed_tail_kept", v.detail)

    def test_a_natural_after_the_flats_is_not_a_key(self):
        """[C21]: a key change prints its cancelling naturals FIRST. A
        natural standing to the right of the flats is an in-bar accidental
        (a note's), not a signature."""
        tail = [("accidentalFlat", 0), ("accidentalFlat", 1),
                ("accidentalNatural", 3)]
        v = _partition(_build(tail))
        self.assertEqual(v.value, N_CELLS)

    def test_flats_and_sharps_together_are_not_a_key(self):
        tail = [("accidentalFlat", 0), ("accidentalSharp", 1)]
        v = _partition(_build(tail))
        self.assertEqual(v.value, N_CELLS)

    def test_a_double_flat_is_never_key_ink(self):
        tail = [("accidentalDoubleFlat", 0), ("accidentalFlat", 1)]
        v = _partition(_build(tail))
        self.assertEqual(v.value, N_CELLS)

    def test_half_the_staves_key_shaped_is_not_a_majority(self):
        tail = {0: ACCFLAT3, 1: ACCFLAT3,
                2: [("noteheadBlackOnLine", 0)],
                3: [("noteheadBlackOnLine", 0)]}
        v = _partition(_build(tail))
        self.assertEqual(v.value, N_CELLS)


class TestDuplicateInkIsTimeSignatureOnly(unittest.TestCase):
    """The 2.47bc excuse (a notehead-classed box that is the SAME ink as a
    signature box) was written for `timeSig*` boxes only -- `geometry.
    is_timesig_digit_ink`'s contract and `notehead_precision`'s 2.47c rule,
    which says the clef/key pairing is NOT CONFIRMED -- but the vote passed
    it every clef and key box too. A notehead box lying exactly on a
    `keyFlat` box is therefore no longer excused."""

    def test_a_notehead_on_a_key_flat_box_is_not_excused(self):
        tail = [("keyFlat", 0), ("noteheadBlackOnLine", 0)]
        v = _partition(_build(tail, this_key=None, next_system=False))
        self.assertEqual(v.value, N_CELLS)
        self.assertEqual(v.reason, "read")

    def test_a_notehead_on_a_time_signature_box_is_still_excused(self):
        """CONTROL: the measured 2.47bc case is untouched."""
        tail = [("timeSig4", 0), ("noteheadBlackOnLine", 0)]
        v = _partition(_build(tail, this_key=None, next_system=False))
        self.assertEqual(v.value, N_CELLS - 1)
        self.assertEqual(v.reason, "cautionary_tail_not_a_bar")


if __name__ == "__main__":
    unittest.main()
