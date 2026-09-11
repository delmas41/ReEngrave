"""The contract every decision owes, asserted where nothing asserted it.

⚠️ These were written to close EMPTY CELLS that
`python3 -m tools.omr.staged.health` found in the existing 226 staged tests,
and every one was confirmed with a `grep` before being believed. The contract
is `adjudicate.Ruling`'s own: a decision DECIDES what it can, ABSTAINS when it
cannot, and RECORDS both. Sean's bar is "are our tools and stages working",
not better-or-worse, so nothing here scores anything.

What the health report found, and this closes:

* `system_membership` — **decision #0, and NO staged test named it at all.**
  `grep -rn SYSTEM_MEMBERSHIP tools/omr/tests/test_staged_*.py` returned two
  hits and both were a docstring.
* `part_partition` — named ONLY by `test_staged_export.py`, which SUPPLIES the
  join as a fixture. Coverage from a downstream stage is not coverage.
* `measure_partition` — no test asserted it decides.
* `group_symbol`, `key_signature`, `tuplet_ratio` — nothing asserted what they
  RECORD, which is the half that makes a staged decision different from a
  field on a dict.
* `arc_owner`, `articulation_owner`, `wedge_anchor`, `dynamic`, `direction` —
  **five declared stubs no test named at all.** `stub=True` PROMISES an
  abstention that says `not_implemented`; nothing checked the promise.
"""

import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Outcome, Q, READERS


def _spec(quantity):
    adjudicate._ensure_decisions()
    return adjudicate.REGISTRY[quantity]


def _decide(log, quantity, subject):
    """Run ONE decision on ONE subject, the way the harness does."""
    log.freeze()
    return adjudicate.adjudicate_one(log, _spec(quantity), subject)


class TestSystemMembership(unittest.TestCase):
    """⚠️ Decision #0 — "structure first, everything else is addressed in
    terms of it" — and the suite did not name it."""

    def test_it_DECIDES_from_the_staff_count_it_was_given(self):
        log = Log()
        log.observe(R.system(0, 0), Q.SYSTEM_STAFF_COUNT, 11,
                    reader=READERS.GEOMETRY, frame="page")
        v = _decide(log, Q.SYSTEM_MEMBERSHIP, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, 11)
        self.assertEqual(v.reason, "counted")

    def test_it_ABSTAINS_with_a_reason_when_nothing_counted(self):
        log = Log()
        v = _decide(log, Q.SYSTEM_MEMBERSHIP, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_evidence")

    def test_it_RECORDS_the_row_it_used(self):
        """The half a field on a dict cannot carry: which row this answer
        rests on, computed by the HARNESS rather than claimed by the
        decision."""
        log = Log()
        obs = log.observe(R.system(0, 0), Q.SYSTEM_STAFF_COUNT, 4,
                          reader=READERS.GEOMETRY, frame="page")
        v = _decide(log, Q.SYSTEM_MEMBERSHIP, R.system(0, 0))
        self.assertIn(obs.id, v.used)
        self.assertIn(obs.id, v.considered)
        self.assertIn(obs.id, v.basis)

    def test_MISSING_records_what_was_ASKED_FOR_and_absent_not_what_was_declared(self):
        """⚠️ A SEMANTIC THIS TEST LEARNED BY BEING WRONG FIRST. It asserted
        `gap_bridging` — declared in `wants` — would appear in `missing`, and
        it does not: `Evidence._note` records a quantity as missing only when
        the decision actually QUERIED it and the log had nothing.

        That is the right semantic (a decision cannot be charged for evidence
        it did not want on this subject) and it has a consequence worth
        keeping: **a `wants` entry the decision never reads is inert.** It
        declares nothing, records nothing, and cannot be told from one that is
        read and always present. `adjudicate_system_membership` declares
        `gap_bridging` and never reads it; `inventory` reports that as
        `declared_and_never_read`."""
        log = Log()
        log.observe(R.system(0, 0), Q.SYSTEM_STAFF_COUNT, 4,
                    reader=READERS.GEOMETRY, frame="page")
        v = _decide(log, Q.SYSTEM_MEMBERSHIP, R.system(0, 0))
        self.assertNotIn(Q.GAP_BRIDGING, v.missing)
        self.assertIn(Q.GAP_BRIDGING, _spec(Q.SYSTEM_MEMBERSHIP).wants)


class TestMeasurePartition(unittest.TestCase):
    def test_it_DECIDES_the_bar_count_it_read(self):
        log = Log()
        log.observe(R.staff(0, 0, 0), Q.BARLINE_COLUMN, 16,
                    reader=READERS.GEOMETRY, frame="page")
        v = _decide(log, Q.MEASURE_PARTITION, R.staff(0, 0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, 16)
        self.assertEqual(v.reason, "read")

    def test_no_barline_ABSTAINS_and_names_that_reason_specifically(self):
        """⚠️ `no_barline` rather than a generic failure: a staff with no
        barline read is a different page from one with no staff."""
        log = Log()
        v = _decide(log, Q.MEASURE_PARTITION, R.staff(0, 0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_barline")


class TestPartPartition(unittest.TestCase):
    """⚠️ Covered only by the EXPORTER's tests until now, and those hand the
    join in. A decision exercised solely by its consumer is untested."""

    def _page(self, counts):
        log = Log()
        for sysi, n in enumerate(counts):
            log.observe(R.system(0, sysi), Q.SYSTEM_STAFF_COUNT, n,
                        reader=READERS.GEOMETRY, frame="page")
            v = adjudicate.Verdict(
                id=log._next_id("vrd"), subject=R.system(0, sysi),
                quantity=Q.SYSTEM_STAFF_COUNT, outcome=Outcome.DECIDED,
                value=n, decider="t", reason="counted")
            log.record(v)
        return log

    def test_equal_counts_DECIDE_the_ordinal_join(self):
        log = self._page([11, 11])
        v = _decide(log, Q.PART_PARTITION, R.DOCUMENT)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["join"], "ordinal")
        self.assertEqual(v.reason, "ordinal")

    def test_unequal_counts_with_no_usable_slot_fall_to_deduced_anchor(self):
        """⚠️ The ordinal join REFUSES on unequal lineups because joining by
        position would graft one instrument's music onto another. With no slot
        to fall back on it says so by REASON rather than by returning
        nothing."""
        log = self._page([13, 14])
        v = _decide(log, Q.PART_PARTITION, R.DOCUMENT)
        self.assertEqual(v.reason, "deduced_anchor")
        self.assertEqual(v.value["reason"], "slots_unusable")

    def test_it_RECORDS_which_counts_it_read(self):
        log = self._page([11, 11])
        v = _decide(log, Q.PART_PARTITION, R.DOCUMENT)
        self.assertTrue(v.used)
        self.assertTrue(v.basis)
        self.assertEqual(v.value["staves_per_system"], 11)

    def test_no_evidence_at_all_ABSTAINS(self):
        log = Log()
        v = _decide(log, Q.PART_PARTITION, R.DOCUMENT)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_evidence")


class TestWhatTheHeaderDecisionsRECORD(unittest.TestCase):
    """The `records` column, empty for three decisions."""

    def _keyed_staff(self):
        log = Log()
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=R.staff(0, 0, 0), quantity=Q.CLEF,
            outcome=Outcome.DECIDED, value="treble", decider="t",
            reason="scored"))
        log.observe(R.staff(0, 0, 0), Q.KEYSIG_CLEF_FIT, "treble",
                    reader=READERS.CV_HEADER, frame="header_window",
                    fifths=-3, n_accidentals=3, accidental="b",
                    decided_by="tail")
        return log

    def test_the_key_signature_records_the_evidence_it_fitted(self):
        v = _decide(self._keyed_staff(), Q.KEY_SIGNATURE, R.staff(0, 0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value, -3)
        self.assertTrue(v.considered, "it read rows and recorded none")
        self.assertTrue(v.basis)
        self.assertEqual(v.detail["n_accidentals"], 3)
        self.assertEqual(v.detail["decided_by"], "tail")

    def test_an_abstaining_key_signature_records_what_it_ASKED_FOR(self):
        """⚠️ `missing` is filled by the HARNESS at hand-in time, not by the
        decision — which is what makes "nobody read it" survive into the
        record even when the decision had nothing to say. Here the clef IS
        settled, so the decision goes on to ask for the fit and records its
        absence."""
        log = Log()
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=R.staff(0, 0, 0), quantity=Q.CLEF,
            outcome=Outcome.DECIDED, value="treble", decider="t",
            reason="scored"))
        v = _decide(log, Q.KEY_SIGNATURE, R.staff(0, 0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertIn(Q.KEYSIG_CLEF_FIT, v.missing)

    def test_no_clef_means_no_key_and_the_reason_SAYS_no_clef(self):
        """⚠️ The guard MOVED, it was not removed: fitting three flats against
        a guessed clef once returned TWO SHARPS. Here it is a dependency
        rather than a boolean inside a reader."""
        v = _decide(Log(), Q.KEY_SIGNATURE, R.staff(0, 0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "needs_clef")

    def test_the_tuplet_records_the_marker_that_decided_it(self):
        log = Log()
        for i in range(3):
            g = R.glyph(0, 0, 0, 0, i)
            log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine",
                        reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(R.glyph(0, 0, 0, 0, 9), Q.TUPLET_MARKER, "tuplet3",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                    is_bracket=False)
        v = _decide(log, Q.TUPLET_RATIO, R.cell(0, 0, 0, 0))
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["actual"], 3)
        self.assertEqual(v.detail.get("marker"), "tuplet3")
        self.assertTrue(v.used)

    def test_the_group_symbol_records_the_groups_it_read(self):
        """⚠️ With a group but NO identity it abstains `no_identity` rather
        than reading a block of two as a grand staff — Brahms 1 p.1 reads
        blocks `[2,2,2,2,2,7,1,3]` and five of those pairs are wind sections,
        not pianos. The record has to show it saw the group and still
        declined."""
        log = Log()
        log.record(adjudicate.Verdict(
            id=log._next_id("vrd"), subject=R.staff(0, 0, 0),
            quantity=Q.STAFF_GROUP, outcome=Outcome.DECIDED, value=0,
            decider="t", reason="bracket_block"))
        v = _decide(log, Q.GROUP_SYMBOL, R.system(0, 0))
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_identity")
        self.assertTrue(v.considered, "it read the group and recorded nothing")

    def test_with_no_group_at_all_it_says_no_group(self):
        v = _decide(Log(), Q.GROUP_SYMBOL, R.system(0, 0))
        self.assertEqual(v.reason, "no_group")


class TestEveryDeclaredStubKeepsItsPromise(unittest.TestCase):
    """⚠️ FIVE STUBS WERE NAMED BY NO TEST. `stub=True` is a PROMISE — it
    always abstains with `not_implemented` and is listed by `stubs()` — and
    nothing checked it. A stub that quietly returned a value, or abstained for
    some other reason, would read as ordinary evidence downstream."""

    def test_each_stub_abstains_with_not_implemented_and_records_it(self):
        for quantity in adjudicate.stubs():
            with self.subTest(quantity=quantity):
                spec = _spec(quantity)
                log = Log()
                subject = _subject_at(spec.scope)
                v = adjudicate.adjudicate_one(log, spec, subject)
                self.assertIs(v.outcome, Outcome.ABSTAINED)
                self.assertEqual(v.reason, ABSTAIN.NOT_IMPLEMENTED)
                self.assertEqual(v.quantity, quantity)
                self.assertIsNone(v.value)
                # ⚠️ AND WHAT IT RECORDS IS THE HALF THAT MATTERS. A stub
                # abstains BEFORE reading anything, so its `considered`,
                # `used` and `basis` must be EMPTY — a stub with evidence in
                # its basis would mean it looked at the page and still said
                # `not_implemented`, which is a different and much worse
                # thing than "not written yet".
                self.assertEqual(v.considered, ())
                self.assertEqual(v.used, ())
                self.assertEqual(v.basis, ())
                self.assertEqual(v.missing, ())
                self.assertEqual(v.declined, ())
                self.assertEqual(v.detail, {})

    def test_a_stub_is_still_reached_by_the_ORDER(self):
        """A stub that abstains is accounted for; one absent from `ORDER`
        writes nothing at all, which is a different and invisible state."""
        for quantity in adjudicate.stubs():
            self.assertIn(quantity, adjudicate.ORDER)

    def test_the_previously_unnamed_stubs_are_named_now(self):
        """The regression this file exists to prevent: a stub landing with no
        test that names it.

        ⚠️ `Q.DYNAMIC` WAS ON THIS LIST AND HAS LEFT IT, because it is no
        longer a stub -- `adjudicate_dynamic` is implemented. A roster of
        stubs that keeps an entry after it graduates stops describing the
        pipeline and starts describing its history, the same fault
        `export_coverage.KNOWN_GAPS` has `test_the_inventory_has_no_stale
        _entries` to prevent. Its graduation is pinned below rather than
        merely un-asserted.
        """
        for quantity in (Q.WEDGE_ANCHOR, Q.DIRECTION):
            self.assertIn(quantity, adjudicate.stubs())

    def test_dynamic_and_the_ARCS_have_GRADUATED_from_the_stub_roster(self):
        """The other half of the line above: assert the implementation, so a
        silent regression to a stub fails here rather than passing quietly.

        ⚠️ `Q.ARC_KIND` and `Q.ARC_OWNER` joined `Q.DYNAMIC` here on
        2026-09-09 and `Q.ARTICULATION_OWNER` on 2026-09-10. Four of the six
        original stubs are now filled and TWO REMAIN — `wedge_anchor` and
        `direction`, the latter still the only input-starved one."""
        for quantity in (Q.DYNAMIC, Q.ARC_KIND, Q.ARC_OWNER,
                         Q.ARTICULATION_OWNER):
            self.assertNotIn(quantity, adjudicate.stubs())
        spec = adjudicate.REGISTRY[Q.DYNAMIC]
        self.assertFalse(spec.stub)
        self.assertEqual(spec.fn.__name__, "adjudicate_dynamic")


def _subject_at(kind):
    from tools.omr.staged.record import Kind
    return {
        Kind.DOCUMENT: R.DOCUMENT,
        Kind.PAGE: R.page(0),
        Kind.SYSTEM: R.system(0, 0),
        Kind.STAFF: R.staff(0, 0, 0),
        Kind.CELL: R.cell(0, 0, 0, 0),
        Kind.GLYPH: R.glyph(0, 0, 0, 0, 0),
    }[kind]


if __name__ == "__main__":
    unittest.main()
