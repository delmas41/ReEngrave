"""The divergence table must compare like with like -- or say it cannot."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged import pipeline as P
from tools.omr.staged.record import Q


class TestKeySignatureUnits:
    def test_agreement_is_reported_as_agreement(self):
        """3 flats vs -3 is the SAME key. Before the adapter this was DIFFER."""
        lc, sc, ok = P._canonical(
            Q.KEY_SIGNATURE, {"sharps": 0, "flats": 3, "alterations": {}}, -3)
        assert ok and lc == sc == -3

    def test_a_real_disagreement_still_disagrees(self):
        lc, sc, ok = P._canonical(
            Q.KEY_SIGNATURE, {"sharps": 0, "flats": 2, "alterations": {}}, -3)
        assert ok and lc != sc

    def test_sharps_side(self):
        lc, sc, ok = P._canonical(
            Q.KEY_SIGNATURE, {"sharps": 4, "flats": 0, "alterations": {}}, 4)
        assert ok and lc == sc == 4


class TestInstrumentShape:
    def test_the_shared_field_decides(self):
        lc, sc, ok = P._canonical(
            Q.INSTRUMENT, {"name": "Timpani"},
            {"name": "Timpani", "family": "percussion", "transpose": 0})
        assert ok and lc == sc == "Timpani"

    def test_different_instruments_still_differ(self):
        lc, sc, ok = P._canonical(
            Q.INSTRUMENT, {"name": "Timpani"}, {"name": "Trumpet", "family": "brass"})
        assert ok and lc != sc


class TestUncomparableIsItsOwnOutcome:
    def test_a_dict_against_a_scalar_is_not_comparable(self):
        _, _, ok = P._canonical("some_unadapted_quantity", {"a": 1}, 3)
        assert not ok, "a dict vs a scalar must not be reported as DIFFER"

    def test_not_comparable_is_counted_separately(self):
        assert P.NOT_COMPARABLE in ("not_comparable",)
        assert P.NOT_COMPARABLE not in (P.DIFFER, P.AGREE)


class TestTheAdapterCannotManufactureAgreement:
    """The failure worse than a false DIFFER: a false AGREE nobody checks."""

    def test_unequal_keys_never_collapse(self):
        for flats, fifths in ((0, -1), (1, -3), (3, 0), (2, 4)):
            lc, sc, ok = P._canonical(
                Q.KEY_SIGNATURE,
                {"sharps": 0, "flats": flats, "alterations": {}}, fifths)
            assert lc != sc, f"flats={flats} wrongly equals fifths={fifths}"

    def test_unadapted_quantities_are_untouched(self):
        lc, sc, ok = P._canonical("staff_ordinal", 3, 3)
        assert ok and lc == 3 and sc == 3


# ─── the two Step-2 gaps: invisibility, and no ranking ──────────────────────

from tools.omr.staged.record import (           # noqa: E402
    Kind, Log, Outcome, Subject, Verdict,
)
from tools.omr.staged import record as R        # noqa: E402


def _log_with(verdicts):
    """A Log carrying exactly these verdicts. `verdicts` is (q, subject, value,
    outcome, basis) tuples."""
    log = Log()
    for i, (q, sub, val, outcome, basis) in enumerate(verdicts):
        log.record(Verdict(
            id=f"vrd:{i:06d}", subject=sub, quantity=q, outcome=outcome,
            value=val, decider="test", reason="test", basis=tuple(basis)))
    return log


class TestAStagedVerdictWithNoLegacyCounterpartIsVISIBLE:
    """⚠️ THE BUG: `divergence()` iterates `legacy.items()`, so a quantity the
    extractor does not carry produced NO ROW AT ALL -- not an agreement, not a
    divergence, not a `legacy_only`. Six of fifteen wired decisions were in
    that state, and a reader could total the table, find it coherent, and never
    learn that 40% of the decisions were missing from it."""

    def _fixture(self):
        s0 = R.staff(0, 0, 0)
        log = _log_with([
            (Q.CLEF, s0, "treble", Outcome.DECIDED, []),
            # nothing in `legacy` will carry these two:
            ("staff_group", s0, 1, Outcome.DECIDED, []),
            # ⚠️ value MUST be None: `Verdict` refuses an abstention that
            # carries one, which is the record enforcing that a decision with
            # an answer has not abstained. The first draft of this fixture
            # passed "x" and the schema rejected it.
            ("glyph_owner", s0, None, Outcome.ABSTAINED, []),
        ])
        legacy = {Q.CLEF: {s0.to_key(): "treble"}}
        return P.divergence(log, legacy)

    def test_they_are_counted(self):
        d = self._fixture()
        assert d["counts"][P.STAGED_ONLY] == 2

    def test_they_are_named_per_quantity_with_their_outcome(self):
        d = self._fixture()
        assert d["staged_only"]["staff_group"]["decided"] == 1
        assert d["staged_only"]["glyph_owner"]["abstained"] == 1

    def test_the_compared_quantity_is_NOT_listed_as_staged_only(self):
        assert "clef" not in self._fixture()["staged_only"]

    def test_coverage_states_both_vocabularies(self):
        c = self._fixture()["coverage"]
        assert c["compared"] == ["clef"]
        assert set(c["staged_not_extracted"]) == {"staff_group", "glyph_owner"}

    def test_summarised_not_emitted_as_rows(self):
        """⚠️ `duration` decides 113 subjects on ONE page and `glyph_owner` 60.
        As rows they would swamp a table whose purpose is to be read, and rank
        above every real disagreement while comparing against nothing."""
        d = self._fixture()
        assert all(r["quantity"] == "clef" for r in d["rows"])


class TestTheListIsRankedByStavesTouched:
    """Step 2's own words: "ranked by how many staves each disagreement
    touches". A wrong clef on one staff is one staff wrong; a wrong staff
    COUNT on a system is wrong about every staff in it."""

    def _fixture(self):
        s0, sysA = R.staff(0, 0, 0), R.system(0, 0)
        log = _log_with([
            (Q.CLEF, s0, "bass", Outcome.DECIDED, []),
            (Q.SYSTEM_STAFF_COUNT, sysA, 27, Outcome.DECIDED, []),
        ])
        legacy = {
            Q.CLEF: {s0.to_key(): "treble"},
            Q.SYSTEM_STAFF_COUNT: {sysA.to_key(): 26},
        }
        return P.divergence(log, legacy)

    def test_both_disagreements_are_present(self):
        assert len(self._fixture()["ranked"]) == 2

    def test_the_system_wide_one_ranks_FIRST(self):
        r = self._fixture()["ranked"]
        assert r[0]["quantity"] == Q.SYSTEM_STAFF_COUNT
        assert r[0]["staves_touched"] == 26
        assert r[1]["staves_touched"] == 1

    def test_the_width_comes_from_LEGACY_not_from_the_staged_side(self):
        """⚠️ On exactly the rows where `system_staff_count` DIFFERS the two
        paths disagree about the answer, so ranking by the staged number would
        let a decision inflate its own importance. Legacy says 26, staged 27."""
        assert self._fixture()["ranked"][0]["staves_touched"] == 26

    def test_an_abstention_is_not_a_disagreement(self):
        s0 = R.staff(0, 0, 0)
        log = _log_with([(Q.CLEF, s0, None, Outcome.ABSTAINED, [])])
        d = P.divergence(log, {Q.CLEF: {s0.to_key(): "treble"}})
        assert d["counts"][P.NEW_ABSTENTION] == 1
        assert d["ranked"] == [], "an abstention is a separate column on purpose"


class TestADivergenceIsTraceableToWhatCausedIt:
    """`Verdict.basis` is the ancestor closure -- the whole point of the
    record. Raw it is opaque ids; translated to the quantities they carry it
    says what the disagreement RESTS ON."""

    def test_the_basis_is_reported_as_quantities(self):
        s0 = R.staff(0, 0, 0)
        log = Log()
        log.record(Verdict(id="vrd:000001", subject=s0, quantity=Q.CLEF,
                           outcome=Outcome.DECIDED, value="treble",
                           decider="d", reason="r"))
        log.record(Verdict(id="vrd:000002", subject=s0, quantity=Q.KEY_SIGNATURE,
                           outcome=Outcome.DECIDED, value=-1, decider="d",
                           reason="fitted", basis=("vrd:000001",)))
        d = P.divergence(log, {Q.KEY_SIGNATURE: {s0.to_key(): {
            "sharps": 0, "flats": 3, "alterations": {}}}})
        row = d["ranked"][0]
        assert row["basis"]["rests_on"] == {Q.CLEF: 1}
        assert row["basis"]["ids"] == ["vrd:000001"]

    def test_no_basis_is_None_not_an_empty_shell(self):
        s0 = R.staff(0, 0, 0)
        log = _log_with([(Q.CLEF, s0, "bass", Outcome.DECIDED, [])])
        d = P.divergence(log, {Q.CLEF: {s0.to_key(): "treble"}})
        assert d["ranked"][0]["basis"] is None
