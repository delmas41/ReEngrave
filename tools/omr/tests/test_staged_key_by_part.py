"""Roadmap 2.9b — the key the DOCUMENT reads, and the key each PART reads.

Sean, 2026-09-23, adjudicating 2.9's four system-header crops: *"all 4 of
those crops are pieces with 3 flats and the staffs that have fewer flats are
transposing clefs."*

⚠️ THIS FILE IS RED ON THE TREE IT WAS WRITTEN AGAINST, and that is checkable
with one command rather than asserted here:

    git grep -n -e PART_KEY_SWITCH -e part_key_enabled -e expected_fifths \
        -e admitted_changes -e part_key_census -e 'def fill_part_key' \
        -e disagrees_with_document 7dead94b -- tools/

returns NOTHING. Every symbol this module imports or reaches for was absent at
`7dead94b`, so the file could not import there, let alone pass. It was also
run against that tree with the imports stubbed out, and the two behavioural
families failed in the two different ways the item predicts: the dissenting
staff came back DECIDED at its own wrong value, and the INFER stage had no
rule to fill anything.

⚠️ COHERENCE, NOT ACCURACY. Every fixture here is hand-built, so these say
what the rule DOES and never how often it is right. The accuracy figures are
in `benchmarks/omr-key-majority-2026-09/FINDINGS.md` §2.9b, measured on the
three acceptance records.

⚠️ NO TEST HERE ASSERTS ON MODULE SOURCE TEXT. Every assertion is about a
verdict the machine wrote or a value a pure function returned.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, evaluate, infer, inferences
from tools.omr.staged import adjudicators  # noqa: F401 -- registers ADJUDICATE
from tools.omr.staged import consequences  # noqa: F401 -- registers EVALUATE
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import header as H
from tools.omr.staged.record import (Kind, Log, Outcome, Q, READERS, Subject,
                                     Verdict)

DOC = Subject(Kind.DOCUMENT)

#: One staff space in the CELL's canonical frame, as the engraved fixture
#: measures it — the same constant `test_staged_key_from_markers` uses, so the
#: two files' marker runs mean the same thing.
SPACE = 85.0


def _flats(n, x0=375.0):
    return [("keyFlat", x0 + i * SPACE) for i in range(n)]


def _header(log, page, system, staff, *, markers=(), label=None,
            clef="treble"):
    """One staff's header ink. No verdicts — ADJUDICATE writes those."""
    sub = R.staff(page, system, staff)
    log.observe(sub, Q.CLEF_GLYPH,
                {"treble": "clefG", "bass": "clefF", "alto": "clefC"}[clef],
                reader=READERS.DETECTOR, frame="cell:0", score=0.95)
    log.observe(R.cell(page, system, staff, 0), Q.CELL_STAFF_SPACE, SPACE,
                reader=READERS.GEOMETRY, frame="cell:0")
    if label is not None:
        log.observe(sub, Q.MARGIN_LABEL, label, reader=READERS.TEXT_LAYER,
                    frame="page")
    for kind, x in markers:
        log.observe(sub, Q.KEYSIG_MARKER, kind, reader=READERS.DETECTOR,
                    frame="cell:0", score=0.92, x=x, y_center=500)
    return sub


def _slot(log, sub, slot, instrument=None):
    """A decided `Q.SLOT_INDEX`, as `adjudicate_slot_index` would leave one.

    ⚠️ PRE-RECORDED AND THE DECISION IS THEN EXCLUDED FROM THE ORDER, because
    placing a staff needs a page's worth of structure this fixture does not
    have. What is under test is what the KEY decisions do with a part, not how
    the part was found.
    """
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=Q.SLOT_INDEX,
        outcome=Outcome.DECIDED, value=slot, decider="test",
        reason="paired_by_name",
        detail={"instrument": instrument} if instrument else {}))


_ORDER_WITHOUT_SLOTS = tuple(q for q in adjudicate.ORDER
                             if q != Q.SLOT_INDEX)


def _run(log):
    adjudicate.run(log, order=_ORDER_WITHOUT_SLOTS)
    return log


# ─────────────────────────────────────────────────────────────────────────────
# The pure functions — a change is admitted, or it is not
# ─────────────────────────────────────────────────────────────────────────────


def _seq(*values, page=0):
    return [((page, i), v) for i, v in enumerate(values)]


class TestWhenAKeyChangeIsAdmitted(unittest.TestCase):
    """⚠️ `[C24]`: *a key CHANGE is printed at ONE bar of ONE system, on EVERY
    staff of it* — and its own **Numbers** field is `MIN_WITNESSES = 2`."""

    def test_the_threshold_is_the_registrys_and_not_this_modules(self):
        from tools.omr.key_signature_corroboration import MIN_WITNESSES
        self.assertEqual(H.CHANGE_MIN_WITNESSES, MIN_WITNESSES)
        H._assert_change_threshold_matches_legacy()

    def test_one_part_changing_alone_admits_nothing(self):
        readings = {0: _seq(-3, -3, 0, 0, 0),
                    1: _seq(-3, -3, -3, -3, -3),
                    2: _seq(-3, -3, -3, -3, -3)}
        self.assertEqual(H.admitted_changes(readings), [])

    def test_a_majority_changing_by_ONE_delta_is_admitted(self):
        readings = {i: _seq(-3, -3, 0, 0, 0) for i in range(3)}
        readings[3] = _seq(-3, -3, -3, -3, -3)
        self.assertEqual(H.admitted_changes(readings), [((0, 2), 3)])

    def test_the_DELTA_is_shared_where_the_VALUE_is_not(self):
        """⚠️ A B-flat clarinet prints one flat where the score prints three,
        and at a change both shift by the same amount. `[C24]`: *the BAR is
        the shared fact even where the VALUE differs by transposition*."""
        readings = {0: _seq(-3, -3, 0, 0),      # concert parts
                    1: _seq(-3, -3, 0, 0),
                    2: _seq(-1, -1, 2, 2)}      # the clarinet
        self.assertEqual(H.admitted_changes(readings), [((0, 2), 3)])

    def test_witnesses_disagreeing_about_the_delta_admit_nothing(self):
        readings = {0: _seq(-3, -3, 0, 0), 1: _seq(-3, -3, 0, 0),
                    2: _seq(-3, -3, -1, -1), 3: _seq(-3, -3, -1, -1)}
        self.assertEqual(H.admitted_changes(readings), [])

    def test_a_value_that_does_not_HOLD_is_not_a_change(self):
        """⚠️ The Litolff guard: that plate under-counts in runs, so two parts
        misreading the same amount at one system is not a change."""
        readings = {i: _seq(-3, -3, -2, -3, -3) for i in range(4)}
        self.assertEqual(H.admitted_changes(readings), [])
        # ...and with the persistence rule switched off it IS admitted, which
        # is what makes the guard a measurable choice rather than a belief.
        self.assertEqual(H.admitted_changes(readings, min_run=1),
                         [((0, 2), 1), ((0, 3), -1)])

    def test_two_of_twenty_four_parts_is_not_EVERY_staff_of_the_system(self):
        readings = {i: _seq(-3, -3, -3, -3) for i in range(24)}
        readings[0] = _seq(-3, -3, 0, 0)
        readings[1] = _seq(-3, -3, 0, 0)
        self.assertEqual(H.admitted_changes(readings), [])
        self.assertEqual(H.admitted_changes(readings, min_share=0.0),
                         [((0, 2), 3)])


class TestTheMajorityInsideAStretch(unittest.TestCase):

    def test_a_tie_abstains(self):
        segs = H._segments(_seq(-3, -3, -1, -1), [])
        self.assertEqual(len(segs), 1)
        self.assertIsNone(segs[0]["fifths"])
        self.assertEqual(segs[0]["tally"], {"-3": 2, "-1": 2})

    def test_a_change_cuts_the_stretch_and_each_side_keeps_its_own(self):
        segs = H._segments(_seq(-3, -3, 0, 0, 0), [((0, 2), 3)])
        self.assertEqual([s["fifths"] for s in segs], [-3, 0])
        self.assertEqual(H.segment_fifths(segs, (0, 1)), -3)
        self.assertEqual(H.segment_fifths(segs, (0, 4)), 0)


# ─────────────────────────────────────────────────────────────────────────────
# ADJUDICATE — the check, and it can FAIL
# ─────────────────────────────────────────────────────────────────────────────


class TestTheDocumentCheck(unittest.TestCase):
    """Tier (2): the DOCUMENT-wide majority of decided CONCERT keys."""

    def test_a_staff_disagreeing_with_its_document_is_abstained(self):
        """⚠️ THE CASE 2.9 COULD NOT REACH. Two staves reading alike survive
        the SYSTEM check (they are each other's peer), and the document says
        three flats on nine staves. `test_staged_key_from_markers`'
        `TestTheSystemCheck` asserts the first half still holds with this
        rule off."""
        log = Log()
        names = ["Flauti.", "Obol.", "Violino I.", "Violoncello.",
                 "Contrabasso.", "Fagotti."]
        for system in range(2):
            for i, name in enumerate(names):
                _header(log, 0, system, i, label=name, markers=_flats(3))
        odd = [_header(log, 0, 2, i, label=n, markers=_flats(1))
               for i, n in enumerate(["Violino II.", "Viola."])]
        _run(log)
        for sub in odd:
            v = log.verdict(Q.KEY_SIGNATURE, sub)
            self.assertIs(v.outcome, Outcome.ABSTAINED)
            self.assertEqual(v.reason, "disagrees_with_document")
            self.assertEqual(v.detail["expected_fifths"], -3)
            self.assertEqual(v.detail["written_fifths"], -1)

    def test_a_TRANSPOSING_staff_is_re_transposed_and_stands(self):
        """⚠️ THE POSITIVE CONTROL FOR THE WHOLE RULE. A B-flat clarinet
        printing ONE flat in a document printing three is RIGHT, and a rule
        that flattened it would be reading the page as a spreadsheet."""
        log = Log()
        for i, name in enumerate(["Flauti.", "Obol.", "Violino I.",
                                  "Violoncello."]):
            _header(log, 0, 0, i, label=name, markers=_flats(3))
        clar = _header(log, 0, 0, 4, label="Clarinetti in B.",
                       markers=_flats(1))
        _run(log)
        v = log.verdict(Q.KEY_SIGNATURE, clar)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, -1)
        self.assertEqual(v.detail["agrees_with"], "document_majority")

    def test_a_staff_that_prints_NO_signature_is_not_judged_by_it(self):
        """`[C81]` — a natural trumpet reads 0 whatever the key."""
        log = Log()
        for i, name in enumerate(["Flauti.", "Obol.", "Violino I.",
                                  "Violoncello."]):
            _header(log, 0, 0, i, label=name, markers=_flats(3))
        tp = _header(log, 0, 0, 4, label="Trombe in C.")
        _run(log)
        v = log.verdict(Q.KEY_SIGNATURE, tp)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertNotIn(v.reason,
                         ("disagrees_with_document", "disagrees_with_part"))


class TestThePartCheck(unittest.TestCase):
    """Tier (3): the same PART's WRITTEN key on its other systems — the tier
    that needs no margin label, and therefore the only one most of a scanned
    conductor's page can use at all."""

    def _part(self, values, *, slot=7, settled=(-3, -3, -3)):
        """One unlabelled part reading `values`, beside one that settles.

        ⚠️ THE SECOND PART IS NOT DECORATION. With one part and no margin
        label nothing in the document settles a key at all and `Q.PART_KEY`
        abstains `no_staff_read_a_key` — the honest answer, and one that would
        make the split fixture below pass for the wrong reason.
        """
        log = Log()
        subs = []
        for i, v in enumerate(values):
            sub = _header(log, 0, i, 3,
                          markers=() if v is None else _flats(-v))
            _slot(log, sub, slot, instrument="Violin")
            subs.append(sub)
        for i, v in enumerate(settled):
            other = _header(log, 0, i, 4, markers=_flats(-v))
            _slot(log, other, slot + 1, instrument="Cello")
        return log, subs

    def test_one_system_disagreeing_with_its_own_part_is_abstained(self):
        """The item's own fixture: `-3 -3 -1 -3 -3`."""
        log, subs = self._part([-3, -3, -1, -3, -3])
        _run(log)
        for i, sub in enumerate(subs):
            v = log.verdict(Q.KEY_SIGNATURE, sub)
            if i == 2:
                self.assertIs(v.outcome, Outcome.ABSTAINED)
                self.assertEqual(v.reason, "disagrees_with_part")
                self.assertEqual(v.detail["expected_fifths"], -3)
                self.assertEqual(v.detail["written_fifths"], -1)
            else:
                self.assertIs(v.outcome, Outcome.DECIDED)
                self.assertEqual(v.value, -3)

    def test_a_part_that_splits_EVENLY_touches_nothing(self):
        """⚠️ A TIE ABSTAINS — and abstaining the PART means the check does
        not fire, NOT that every staff is abstained. Abstaining all four would
        leave the `<part>` with no `<key>` anywhere, which MusicXML reads as C
        major: a fallback converting *cannot tell* into an answer, and a worse
        one than the reading it replaced (CLAUDE.md rule 8)."""
        log, subs = self._part([-3, -3, -1, -1])
        _run(log)
        part_key = log.verdict(Q.PART_KEY, DOC)
        segs = part_key.value["parts"]["7"]["segments"]
        self.assertIsNone(segs[0]["fifths"])
        for sub in subs:
            self.assertIs(log.verdict(Q.KEY_SIGNATURE, sub).outcome,
                          Outcome.DECIDED)

    def test_a_real_change_printed_on_every_part_is_KEPT(self):
        """⚠️⚠️ THE POSITIVE CONTROL FOR THE SEGMENTATION. Sixteen systems,
        every part changing at system 8 and holding — the change survives and
        no staff on either side of it is abstained."""
        log = Log()
        subs = []
        for slot in range(4):
            for i in range(16):
                sub = _header(log, 0, i, slot,
                              markers=_flats(3) if i < 8 else _flats(1))
                _slot(log, sub, slot, instrument="Violin")
                subs.append((slot, i, sub))
        _run(log)
        part_key = log.verdict(Q.PART_KEY, DOC)
        self.assertEqual(part_key.value["changes"], [[[0, 8], 2]])
        for _slot_i, i, sub in subs:
            v = log.verdict(Q.KEY_SIGNATURE, sub)
            self.assertIs(v.outcome, Outcome.DECIDED)
            self.assertEqual(v.value, -3 if i < 8 else -1)


class TestThePartsTranspositionTravels(unittest.TestCase):
    """⚠️⚠️ WITHOUT THIS THE DOCUMENT TIER IS NEARLY INERT ON A SCAN. Litolff
    prints its margin labels on the first system and nowhere else — 76 of 331
    staff-systems carry one, and the count page carries none."""

    def _movement(self, *, clarinet_label_on_system_0=True):
        log = Log()
        concert = ["Flauti.", "Obol.", "Violino I.", "Violoncello."]
        for system in range(4):
            for i, name in enumerate(concert):
                _header(log, 0, system, i,
                        label=name if system == 0 else None,
                        markers=_flats(3))
                _slot(log, R.staff(0, system, i), i, instrument="Flute")
            clar = _header(
                log, 0, system, 4,
                label=("Clarinetti in B."
                       if system == 0 and clarinet_label_on_system_0
                       else None),
                markers=_flats(1) if system < 3 else _flats(4))
            _slot(log, clar, 9, instrument="Clarinet")
        return log, R.staff(0, 3, 4)

    def test_a_label_on_system_0_judges_the_same_part_on_system_3(self):
        log, last = self._movement()
        _run(log)
        v = log.verdict(Q.KEY_SIGNATURE, last)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "disagrees_with_document")
        self.assertEqual(v.detail["expected_fifths"], -1)
        _infer(log)
        filled = log.verdict(Q.KEY_SIGNATURE, last)
        self.assertEqual(filled.value, -1)
        self.assertEqual(filled.reason, "key_from_document_majority")

    def test_with_no_label_anywhere_the_PART_tier_judges_it_instead(self):
        """⚠️ And it reaches a different answer for a different reason: the
        part's own WRITTEN majority is one flat, so the staff is still
        repaired — by the tier that needs no identity at all."""
        log, last = self._movement(clarinet_label_on_system_0=False)
        _run(log)
        v = log.verdict(Q.KEY_SIGNATURE, last)
        self.assertEqual(v.reason, "disagrees_with_part")
        self.assertEqual(v.detail["expected_fifths"], -1)

    def test_a_slot_whose_labels_CONTRADICT_lends_nothing(self):
        """⚠️ `adjudicate_part_partition` is known to be wrong on 3 of 27
        staves on the one page it is measured on. A slot carrying two
        instruments' labels may not lend either one's transposition to the
        other's staves.

        ⚠️ The second label has to be one that RESOLVES TO AN OFFSET. A
        grafted `Corni in Es.` says nothing here, because a horn prints no
        signature and `_transposition` returns no offset for it either way —
        so the contradiction this guard catches is between two parts that
        both speak, which is the only kind it could catch."""
        log, _last = self._movement()
        clar_sys1 = R.staff(0, 1, 4)
        log.observe(clar_sys1, Q.MARGIN_LABEL, "Flauti.",
                    reader=READERS.TEXT_LAYER, frame="page")
        _run(log)
        part = log.verdict(Q.PART_KEY, DOC).value["parts"]["9"]
        self.assertIsNone(part["offset"])


class TestTheFlagReturnsTheTreeToTwoNine(unittest.TestCase):

    def test_off_means_no_staff_is_abstained_by_either_tier(self):
        log = Log()
        for system in range(2):
            for i, name in enumerate(["Flauti.", "Obol.", "Violino I.",
                                      "Violoncello.", "Fagotti."]):
                _header(log, 0, system, i, label=name, markers=_flats(3))
        odd = [_header(log, 0, 2, i, label=n, markers=_flats(1))
               for i, n in enumerate(["Violino II.", "Viola."])]
        with mock.patch.dict(os.environ, {"OMR_PART_KEY": "0"}):
            _run(log)
        for sub in odd:
            self.assertIs(log.verdict(Q.KEY_SIGNATURE, sub).outcome,
                          Outcome.DECIDED)


# ─────────────────────────────────────────────────────────────────────────────
# INFER — the fill, labelled, and never over a reading
# ─────────────────────────────────────────────────────────────────────────────


def _infer(log):
    evaluated = evaluate.run(log)
    return infer.run(log, evaluated)


class TestTheInference(unittest.TestCase):

    def test_the_abstained_staff_is_filled_from_its_own_part(self):
        log = Log()
        subs = []
        for i, v in enumerate([-3, -3, -1, -3, -3]):
            sub = _header(log, 0, i, 3, markers=_flats(-v))
            _slot(log, sub, 7, instrument="Violin")
            subs.append(sub)
        _run(log)
        _infer(log)
        v = log.verdict(Q.KEY_SIGNATURE, subs[2])
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, -3)
        self.assertEqual(v.reason, "key_from_other_systems")
        self.assertTrue(infer.is_inferred(v))
        self.assertTrue(v.detail["inferred"])
        self.assertEqual(v.detail["staff_read"], -1)
        # ⚠️ The part's OWN rows are the basis, and the four agreeing staves
        # are the witnesses — not a number this rule computed.
        others = {log.verdict(Q.KEY_SIGNATURE, s).id
                  for i, s in enumerate(subs) if i != 2}
        self.assertTrue(others & set(v.used))
        self.assertIn(log.verdict(Q.PART_KEY, DOC).id, v.basis)

    def test_the_document_tier_re_transposes_for_the_staff_it_fills(self):
        """⚠️ A clarinet whose own header was unreadable takes the document's
        THREE flats as ONE, because the value it should print is the concert
        key shifted by ITS OWN read transposition."""
        log = Log()
        for system in range(2):
            for i, name in enumerate(["Flauti.", "Obol.", "Violino I.",
                                      "Violoncello.", "Contrabasso."]):
                _header(log, 0, system, i, label=name, markers=_flats(3))
        # ⚠️ TWO clarinets misreading TOGETHER, because one alone is caught by
        # the SYSTEM check and never reaches this tier. That is CLAUDE.md §10
        # in the fixture: two readers off one plate fall silent together, and
        # the wider population is what answers them.
        clars = [_header(log, 0, 2, i, label=n, markers=_flats(3))
                 for i, n in enumerate(["Clarinetti in B.", "Clarinetto in B."])]
        _run(log)
        for clar in clars:
            self.assertEqual(log.verdict(Q.KEY_SIGNATURE, clar).reason,
                             "disagrees_with_document")
        _infer(log)
        for clar in clars:
            v = log.verdict(Q.KEY_SIGNATURE, clar)
            self.assertEqual(v.value, -1)
            self.assertEqual(v.reason, "key_from_document_majority")
            self.assertEqual(v.detail["fifths_offset"], 2)

    def test_a_DECIDED_key_is_never_overturned(self):
        log = Log()
        for i, name in enumerate(["Flauti.", "Obol.", "Violino I.",
                                  "Violoncello."]):
            _header(log, 0, 0, i, label=name, markers=_flats(3))
        _run(log)
        _infer(log)
        census = {g.staff.to_key(): g.outcome
                  for g in inferences.part_key_census(log)}
        self.assertTrue(all(o == "declined_prior_is_decided"
                            for o in census.values()), census)

    def test_it_runs_after_the_slot_rule_it_depends_on(self):
        """⚠️ Tier (3) needs a decided `Q.SLOT_INDEX`, and on Litolff 28 of
        them are the family-block rule's. Registered first, this rule would
        find fewer parts and report a clean, false number."""
        infer._ensure_rules()
        names = [r.inference.value for r in infer.RULES]
        self.assertLess(names.index("collapse_slot_index_to_family_block"),
                        names.index("fill_part_key"))

    def test_an_inferred_key_reaches_respell_accidental(self):
        """⚠️⚠️ THE INERT-INFERENCE TRAP. INFER runs AFTER EVALUATE, so a key
        filled here changes no `<alter>` unless something restates the
        spellings beneath it — `evaluate.run_over`, bounded to the
        consequences of what INFER just wrote (roadmap 2.10 built it)."""
        log = Log()
        subs = []
        for i, v in enumerate([-3, -3, -1, -3, -3]):
            sub = _header(log, 0, i, 3, markers=_flats(-v))
            _slot(log, sub, 7, instrument="Violin")
            subs.append(sub)
        # One note on the staff whose key will be inferred. Its pitch is a
        # GATHER-free fixture: what is under test is the RESPELLING.
        note = Subject(Kind.GLYPH, page=0, system=2, staff=3, cell=0, glyph=0)
        _run(log)
        log.record(Verdict(
            id=log._next_id("vrd"), subject=note, quantity=Q.PITCH,
            outcome=Outcome.DECIDED, value="E4", decider="test",
            reason="fixture"))
        evaluated = evaluate.run(log)
        self.assertIsNone(log.verdict(Q.ACCIDENTAL, note))
        infer.run(log, evaluated)
        evaluate.run_over(log, infer.inferred_verdicts(log))
        acc = log.verdict(Q.ACCIDENTAL, note)
        self.assertIsNotNone(acc)
        self.assertEqual(acc.value, "b")
        # ⚠️ And the label PROPAGATES as a query over the basis rather than as
        # a second flag: the re-spelling is a CONSEQUENCE of an inference.
        self.assertTrue(infer.inferred_in_basis(log, acc))


# ─────────────────────────────────────────────────────────────────────────────
# GATHER — the detector's class is TWO claims, and only the SHAPE is its own
# ─────────────────────────────────────────────────────────────────────────────


class _Box:
    """One detection, as `gather_detections` hands them on."""

    def __init__(self, smufl_name, x, conf=0.9, y=500.0):
        self.smufl_name = smufl_name
        self.x_canonical = float(x)
        self.y_center = float(y)
        self.confidence = float(conf)


def _refusal(log, sub):
    rows = log.refusals(Q.KEYSIG_MARKER, sub)
    return rows[-1].reason if rows else None


class TestTheRoleIsGeometryNotAClassName(unittest.TestCase):
    """Sean, 2026-09-23, on a crop: one header's three flats were boxed as one
    `accidentalFlat` and two `keyFlat`, and `gather._KEYSIG_CLASSES` admitted
    only the key-class ones — so a printed flat was dropped at GATHER, before
    any reader saw it, where no derived check can see it (CLAUDE.md §4d).

    ⚠️ THE PRINCIPLE, HIS: the detector's class is TWO claims. The SHAPE
    (flat / sharp / natural) is what it is good at; the ROLE (key member vs
    in-bar accidental) is GEOMETRY and belongs to a later stage. GATHER files
    the shape and the position; the role-half is recorded as one witness's
    opinion and is never the filter.
    """

    def _markers(self, boxes, *, space=SPACE):
        from tools.omr.staged import gather as G
        log = Log()
        sub = R.staff(0, 0, 3)
        cell = R.cell(0, 0, 3, 0)
        if space:
            log.observe(cell, Q.CELL_STAFF_SPACE, float(space),
                        reader=READERS.GEOMETRY, frame="cell:0")
        G._gather_keysig_markers(log, sub, {cell.to_key(): boxes}, 0, (0, 3))
        return log, sub, log.rows(Q.KEYSIG_MARKER, sub)

    def test_a_run_boxed_key_accidental_key_reads_THREE_slots(self):
        boxes = [_Box("keyFlat", 375.0),
                 _Box("accidentalFlat", 375.0 + SPACE),
                 _Box("keyFlat", 375.0 + 2 * SPACE)]
        _log, _sub, rows = self._markers(boxes)
        self.assertEqual(len(rows), 3)
        # ⚠️ THE VALUE IS THE SHAPE. `_marker_run` abstains
        # `mixed_marker_kinds` on two KINDS, so filing the detector's raw
        # class would turn the repair into a refusal.
        self.assertEqual({str(r.value) for r in rows}, {"keyFlat"})
        self.assertEqual([r.detail["detector_role"] for r in rows],
                         ["key", "accidental", "key"])
        fifths, reason, detail = H._marker_run(rows, SPACE)
        self.assertEqual(fifths, -3)
        self.assertEqual(reason, "markers")
        self.assertEqual(detail["keysig_marker_slots"], 3)

    def test_the_detectors_own_class_is_kept_as_its_OPINION(self):
        _log, _sub, rows = self._markers([_Box("accidentalFlat", 375.0)])
        self.assertEqual(rows[0].detail["detector_class"], "accidentalFlat")
        self.assertEqual(rows[0].detail["detector_role"], "accidental")

    def test_an_accidental_past_the_header_window_is_NOT_a_marker(self):
        from tools.omr.staged import gather as G
        far = (G._keysig_header_limit() + 1.0) * SPACE
        _log, _sub, rows = self._markers(
            [_Box("keyFlat", 375.0), _Box("accidentalFlat", far)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].detail["detector_role"], "key")

    def test_a_KEY_class_box_is_admitted_wherever_it_was_drawn(self):
        """⚠️ ONE-SIDED: the window bounds only the newly admitted class, so
        this change cannot remove a row any shipped record holds."""
        from tools.omr.staged import gather as G
        far = (G._keysig_header_limit() + 5.0) * SPACE
        _log, _sub, rows = self._markers([_Box("keyFlat", far)])
        self.assertEqual(len(rows), 1)

    def test_a_natural_inside_bar_1_does_not_JOIN_a_flat_signature(self):
        """⚠️⚠️ THE FIRST DRAFT ADMITTED IT AND IT COST 84 RUNS ON BREITKOPF,
        35 OF THEM ALREADY READING THE RIGHT ANSWER. `_gather_keysig_markers`
        reads the whole first MEASURE, so an accidental printed inside bar 1
        is in this population; admitting a natural turned a clean three-flat
        run into `mixed_marker_kinds` on the shattering plate. `[C21]`: a
        standard signature carries ONE kind, and the detector's own key-class
        boxes say which kind this header is."""
        boxes = [_Box("keyFlat", 375.0),
                 _Box("accidentalFlat", 375.0 + SPACE),
                 _Box("accidentalNatural", 375.0 + 3 * SPACE)]
        _log, _sub, rows = self._markers(boxes)
        self.assertEqual({str(r.value) for r in rows}, {"keyFlat"})
        self.assertEqual(len(rows), 2)
        self.assertEqual(H._marker_run(rows, SPACE)[0], -2)

    def test_with_NO_key_class_box_nothing_says_which_kind(self):
        """⚠️ 53 header cells on Litolff and 81 on Breitkopf carry an
        accidental-class box and no key-class box at all. Nothing there says
        which kind the header is, so both are admitted and `_marker_run`
        abstains if they disagree — which is the honest answer, not a guess."""
        boxes = [_Box("accidentalFlat", 375.0),
                 _Box("accidentalSharp", 375.0 + SPACE)]
        _log, _sub, rows = self._markers(boxes)
        self.assertEqual(len(rows), 2)
        fifths, reason, _d = H._marker_run(rows, SPACE)
        self.assertIsNone(fifths)
        self.assertEqual(reason, "mixed_marker_kinds")

    def test_a_DOUBLE_accidental_is_not_a_signature_member(self):
        """`[C21]`'s ladder has one accidental per slot."""
        log, sub, rows = self._markers([_Box("accidentalDoubleFlat", 375.0)])
        self.assertEqual(len(rows), 0)
        self.assertEqual(_refusal(log, sub), "no_detections")

    def test_with_no_measured_cell_space_the_widening_does_not_happen(self):
        """⚠️ No unit, no window — so the behaviour is exactly the shipped one
        rather than a guess at the scale, which is how three flats become
        five."""
        log, sub, rows = self._markers([_Box("accidentalFlat", 375.0)],
                                       space=None)
        self.assertEqual(len(rows), 0)
        self.assertEqual(_refusal(log, sub), "no_detections")


if __name__ == "__main__":
    unittest.main()
