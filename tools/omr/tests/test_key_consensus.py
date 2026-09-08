"""The concert key by consensus, and each staff's written key by deduction.

Every case here is a REAL one that changed the module. Three of the four came
from running it and being wrong; they are pinned so the next change has to
survive what this one did not.
"""

from __future__ import annotations

from tools.omr.key_consensus import (
    AGREES, CONTRADICTS, CONVENTION_NO_SIGNATURE, MAJORITY_SHARE,
    MIN_WITNESSES, StaffKey, analyse,
)


def _beethoven5_p1(reads):
    """The hand-verified lineup of `beethoven-sym5-mvt1-984073-p1`."""
    names = ["Flauti", "Oboi", "Clarinetti in B", "Fagotti", "Corni in Es",
             "Trombe in C", "Timpani in C.G.", "Violino I", "Violino II",
             "Viola", "Violoncello", "Basso"]
    return analyse([StaffKey(i, label=n, read_fifths=reads[i])
                    for i, n in enumerate(names)])


TRUTH = [-3, -3, -1, -3, 0, 0, 0, -3, -3, -3, -3, -3]


class TestTheTruthProducesNoContradiction:
    def test_the_key_is_found_unanimously(self):
        c = _beethoven5_p1(TRUTH)
        assert c.concert_fifths == -3
        assert c.strength == "unanimous"

    def test_nothing_is_flagged(self):
        assert _beethoven5_p1(TRUTH).contradictions == ()

    def test_the_transposing_clarinet_is_DEDUCED_not_skipped(self):
        """⚠️ The bug this test exists for.

        `Clarinetti in B` is the one correctly-deduced transposing staff on the
        page, and the first cut let it escape judgement: it decided whether the
        transposition was KNOWN by comparing the resolved offset against
        `default_fifths_offset`, and those COINCIDE for a B-flat clarinet
        because the default clarinet IS the B-flat one. Ask the label.

        ⚠️ MUTATION-CHECKED, AND THE OBVIOUS MUTANT IS THE WRONG ONE. Stubbing
        `parse_in_key` alone leaves this test GREEN, because `_parse_bare_key`
        fires on the same label independently -- the two paths are redundant
        for `Clarinetti in B` and either suffices. The discriminating control
        is restoring the ORIGINAL comparison against `default_fifths_offset`,
        which fails this test and three others. A mutant that survives is not
        automatically a vacuous test; check what else covers the line first.
        """
        c = _beethoven5_p1(TRUTH)
        cl = c.staves[2]
        assert cl.instrument == "Clarinet"
        assert cl.fifths_offset == 2
        assert cl.expected == -1, "concert -3 plus +2"
        assert cl.outcome == AGREES

    def test_natural_brass_and_timpani_are_explained_not_charged(self):
        c = _beethoven5_p1(TRUTH)
        assert c.staves[5].outcome == CONVENTION_NO_SIGNATURE   # Trombe in C
        assert c.staves[6].outcome == CONVENTION_NO_SIGNATURE   # Timpani
        assert c.staves[5].expected == -3 and c.staves[5].read == 0

    def test_they_do_not_VOTE(self):
        """A trumpet reads 0 whatever the key, so it may not establish one."""
        c = _beethoven5_p1(TRUTH)
        assert c.n_witnesses == 8
        assert not c.staves[5].is_witness and not c.staves[6].is_witness

    def test_the_carve_out_only_ever_explains_a_ZERO(self):
        reads = list(TRUTH)
        reads[5] = 2                      # a trumpet reading two sharps
        c = _beethoven5_p1(reads)
        assert c.staves[5].outcome == CONTRADICTS


class TestItFlagsTheViolaFromTheRealReadings:
    """The case the module was built for. Staged read only 4 of 12 staves."""

    def test_three_witnesses_two_of_them_right_still_find_the_key(self):
        reads = [None] * 12
        reads[2], reads[8], reads[9], reads[10] = -1, -3, -1, -3
        c = _beethoven5_p1(reads)
        assert c.concert_fifths == -3
        assert [s.staff_index for s in c.contradictions] == [9]

    def test_and_it_PREDICTS_the_staves_that_abstained(self):
        reads = [None] * 12
        reads[2], reads[8], reads[9], reads[10] = -1, -3, -1, -3
        c = _beethoven5_p1(reads)
        assert c.staves[0].expected == -3 and c.staves[0].read is None
        assert c.staves[4].expected == 0, "Corni in Es: -3 plus +3"


class TestTheOctaveTrap:
    def test_contrabass_is_a_witness_despite_chromatic_minus_12(self):
        """⚠️ `chromatic % 12 == 0`, never `== 0`.

        Contrabass sounds an octave down and prints the same signature. The
        naive test drops it -- the staff a witness rule most wants, being
        bottom-of-page and often unlabelled.
        """
        c = analyse([StaffKey(0, label="Contrabasso", read_fifths=-3),
                     StaffKey(1, label="Violino", read_fifths=-3),
                     StaffKey(2, label="Viola", read_fifths=-3)])
        assert c.staves[0].instrument == "Contrabass"
        assert c.staves[0].is_witness
        assert c.n_witnesses == 3


class TestHarpMayNotEstablishTheKey:
    def test_harp_is_judged_but_does_not_vote(self):
        c = analyse([StaffKey(0, label="Harp", read_fifths=5),
                     StaffKey(1, label="Violino", read_fifths=-3),
                     StaffKey(2, label="Viola", read_fifths=-3),
                     StaffKey(3, label="Violoncello", read_fifths=-3)])
        assert c.n_witnesses == 3, "the harp did not vote"
        assert c.concert_fifths == -3
        assert not c.staves[0].is_witness
        assert c.staves[0].outcome == CONTRADICTS, "but it IS reported"


class TestAPluralityIsNotAConsensus:
    """⚠️ Measured failure. On Tchaikovsky 6 mvt1 m161 the witnesses split 7
    to 6, a bare strict majority admitted it, THE WINNING SIDE WAS WRONG (the
    second subject is in D major), and six correct staves were flagged."""

    def test_seven_against_six_abstains(self):
        reads = ([StaffKey(i, label="Violino", read_fifths=0) for i in range(7)]
                 + [StaffKey(7 + i, label="Viola", read_fifths=2) for i in range(6)])
        c = analyse(reads)
        assert c.concert_fifths is None
        assert c.strength == "none"
        assert c.contradictions == ()

    def test_a_clear_supermajority_still_stands(self):
        reads = ([StaffKey(i, label="Violino", read_fifths=-3) for i in range(9)]
                 + [StaffKey(9, label="Viola", read_fifths=2)])
        c = analyse(reads)
        assert c.concert_fifths == -3 and c.strength == "majority"

    def test_the_share_is_the_weak_form_of_the_premise(self):
        assert 0.5 < MAJORITY_SHARE < 1.0

    def test_too_few_witnesses_abstains(self):
        c = analyse([StaffKey(0, label="Violino", read_fifths=-3),
                     StaffKey(1, label="Viola", read_fifths=-3)])
        assert c.concert_fifths is None
        assert c.n_witnesses < MIN_WITNESSES


class TestAScoreThatPrintsNoSignatures:
    """⚠️ Measured failure. Holst's `Mercury` is written without signatures
    throughout, so its clarinets read 0 against predictions of +2 and -3 and
    every one was charged. The detector needs no constant: the page
    contradicts ITSELF."""

    def _mercury_ish(self):
        return [
            StaffKey(0, label="Clarinet 1 in B", read_fifths=0),   # expects +2
            StaffKey(1, label="Clarinet 2 in A", read_fifths=0),   # expects -3
            StaffKey(2, label="Flauto", read_fifths=0),
            StaffKey(3, label="Oboe", read_fifths=0),
            StaffKey(4, label="Violino", read_fifths=0),
            StaffKey(5, label="Viola", read_fifths=0),
        ]

    def test_two_keys_of_one_instrument_reading_alike_proves_it(self):
        c = analyse(self._mercury_ish())
        assert c.no_signature_score is True

    def test_and_the_clarinets_are_then_not_charged(self):
        c = analyse(self._mercury_ish())
        assert c.staves[0].outcome == CONVENTION_NO_SIGNATURE
        assert c.staves[1].outcome == CONVENTION_NO_SIGNATURE

    def test_an_ordinary_score_does_not_trip_it(self):
        c = analyse([
            StaffKey(0, label="Clarinet 1 in B", read_fifths=-1),
            StaffKey(1, label="Flauto", read_fifths=-3),
            StaffKey(2, label="Violino", read_fifths=-3),
            StaffKey(3, label="Viola", read_fifths=-3),
        ])
        assert c.no_signature_score is False

    def test_it_still_only_explains_a_ZERO(self):
        rows = self._mercury_ish()
        rows[0] = StaffKey(0, label="Clarinet 1 in B", read_fifths=4)
        c = analyse(rows)
        assert c.staves[0].outcome == CONTRADICTS


class TestItNeverRepairs:
    """⚠️ The governing rule. A contradiction is a QUESTION."""

    def test_the_disagreeing_staff_keeps_its_own_reading(self):
        reads = [None] * 12
        reads[2], reads[8], reads[9], reads[10] = -1, -3, -1, -3
        c = _beethoven5_p1(reads)
        viola = c.staves[9]
        assert viola.read == -1, "unchanged"
        assert viola.expected == -3
        assert viola.outcome == CONTRADICTS


class TestUnitAdapter:
    def test_the_legacy_dict_and_the_staged_int_both_read(self):
        from tools.omr.key_consensus import _fifths_of
        assert _fifths_of({"sharps": 0, "flats": 3}) == -3
        assert _fifths_of({"sharps": 2, "flats": 0}) == 2
        assert _fifths_of(-3) == -3
        assert _fifths_of(None) is None


class TestTheModernScoreWithNoKeySignatures:
    """⚠️ Sean, 2026-09-08: "It is common for modern scores to have no key
    signatures." A whole repertoire, not an edge case -- and the same-instrument
    PROOF cannot see it, because it needs the page to print one instrument in
    two different keys and most scores never do. Without the general test, every
    such score charges each of its transposing staves: a confident contradiction
    against correct engraving, which is this module's worst failure mode."""

    def _modern(self):
        # Nothing prints a signature. The concert-pitch staves read 0, so the
        # consensus is 0, and every transposing staff's deduction is non-zero.
        return [
            StaffKey(0, label="Flauto", read_fifths=0),
            StaffKey(1, label="Oboe", read_fifths=0),
            StaffKey(2, label="Violino", read_fifths=0),
            StaffKey(3, label="Viola", read_fifths=0),
            StaffKey(4, label="Violoncello", read_fifths=0),
            # ⚠️ THREE NAMED WOODWIND transposers, and the choice is not
            # incidental. A bare `Corno inglese` names no key, so its
            # transposition is UNKNOWN and it is excluded; and `Corno in F`
            # is already covered by the natural-brass carve-out. The staves
            # genuinely at risk on a signature-less modern score are the
            # WOODWINDS, which nothing else protects. An earlier version of
            # this fixture used those two and left an expectant set of ONE.
            StaffKey(5, label="Clarinetto in B", read_fifths=0),        # +2
            StaffKey(6, label="Clarinetto basso in B", read_fifths=0),  # +2
            StaffKey(7, label="Corno inglese in F", read_fifths=0),     # +1
        ]

    def test_it_is_detected_without_the_two_key_proof(self):
        c = analyse(self._modern())
        assert c.no_signature_score is True

    def test_and_nothing_is_charged(self):
        assert analyse(self._modern()).contradictions == ()

    def test_a_signature_bearing_score_does_NOT_trip_it(self):
        """The control. A B-flat clarinet in C minor really does print one
        flat, so the expectant staves show what they should."""
        c = analyse([
            StaffKey(0, label="Flauto", read_fifths=-3),
            StaffKey(1, label="Oboe", read_fifths=-3),
            StaffKey(2, label="Violino", read_fifths=-3),
            StaffKey(3, label="Viola", read_fifths=-3),
            StaffKey(4, label="Clarinetto in B", read_fifths=-1),
        ])
        assert c.no_signature_score is False
        assert c.contradictions == ()

    def test_beethoven_5_p1_does_not_trip_it(self):
        """Trombe and Timpani print nothing while ten staves print three flats.

        ⚠️ THIS DOES NOT DISCRIMINATE THE DENOMINATOR, and an earlier version
        of this docstring claimed it did -- asserting that a transposing-only
        denominator would read 2 of 2 here. It would not: Trombe in C and
        Timpani are CONCERT pitch, so that denominator EXCLUDES them rather
        than including them, and both rules answer "no" on this page. The case
        that separates them is below.
        """
        c = _beethoven5_p1(TRUTH)
        assert c.no_signature_score is False
        assert c.staves[5].outcome == CONVENTION_NO_SIGNATURE

    def test_misread_transposers_alone_must_not_declare_a_score_signature_less(self):
        """⚠️ The case that fixes the denominator, and the reason it is wide.

        A tonal score in three flats whose THREE transposing staves were all
        misread as zero, while every concert-pitch staff read correctly. A
        denominator of transposing staves alone answers 3 of 3 = 1.0 and
        declares the page signature-less -- which would silence every real
        contradiction on it, turning three misreads into a blanket amnesty.
        Counting every staff whose DEDUCED signature is non-zero gives 3 of 11.
        """
        rows = [StaffKey(i, label=n, read_fifths=-3) for i, n in enumerate(
            ["Flauto", "Oboe", "Fagotto", "Violino I", "Violino II",
             "Viola", "Violoncello", "Contrabasso"])]
        rows += [
            StaffKey(8, label="Clarinetto in B", read_fifths=0),        # exp -1
            StaffKey(9, label="Clarinetto basso in B", read_fifths=0),  # exp -1
            StaffKey(10, label="Corno inglese in F", read_fifths=0),    # exp -2
        ]
        c = analyse(rows)
        assert c.concert_fifths == -3
        assert c.no_signature_score is False, "three misreads are not a convention"
        assert len(c.contradictions) == 3, "and they are still REPORTED"

    def test_a_two_staff_misread_cannot_trip_it(self):
        c = analyse([
            StaffKey(0, label="Violino", read_fifths=-3),
            StaffKey(1, label="Viola", read_fifths=-3),
            StaffKey(2, label="Violoncello", read_fifths=-3),
            StaffKey(3, label="Corno in F", read_fifths=0),   # exp -2
        ])
        assert c.no_signature_score is False, "one expectant staff is not a sweep"
