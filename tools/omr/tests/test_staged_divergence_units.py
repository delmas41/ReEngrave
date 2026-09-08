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
