"""ROADMAP 2.216 -- OMR_OWNER_LEDGER_WINS (Sean 2026-10-28, option B).

Stem and ledger lines name different staves: flag ON -> the ledger decides,
DECIDED, `ledger_over_stem`, the stem's staff recorded; flag OFF (default) ->
abstains `stem_disagrees` as before. Agreement and no-stem are unchanged.
"""
import os
import unittest
from unittest import mock

from tools.omr.staged.adjudicators import ownership as OWN
from tools.omr.staged.record import Outcome
from tools.omr.tests.test_stem_owner_2026_10_08 import (
    A_KEY, B_KEY, SP, HEAD_CY, _contest)

UP_TO_A = ("up", HEAD_CY - 3.5 * SP)      # stem names A; ledger below names B


class TestLedgerWins(unittest.TestCase):
    def _on(self, **kw):
        with mock.patch.dict(os.environ, {OWN.LEDGER_WINS_ENV: "1"}):
            return _contest(UP_TO_A, **kw)

    def test_default_on(self):
        with mock.patch.dict(os.environ, {}):
            os.environ.pop(OWN.LEDGER_WINS_ENV, None)
            self.assertTrue(OWN.ledger_wins_enabled())

    def test_explicit_off_abstains(self):
        with mock.patch.dict(os.environ, {OWN.LEDGER_WINS_ENV: "0"}):
            self.assertFalse(OWN.ledger_wins_enabled())
            v = _contest(UP_TO_A, note_first=B_KEY)
        self.assertEqual((v.outcome, v.reason), (Outcome.ABSTAINED, "stem_disagrees"))

    def test_on_ledger_decides(self):
        v = self._on(note_first=B_KEY)
        self.assertEqual((v.outcome, v.value, v.reason),
                         (Outcome.DECIDED, B_KEY, "ledger_over_stem"))
        self.assertEqual(v.detail["stem_owner"], A_KEY)

    def test_on_agreement_unchanged(self):
        v = self._on(note_first=A_KEY)
        self.assertEqual((v.value, v.reason), (A_KEY, "ledger_note_first"))

    def test_on_no_stem_unchanged(self):
        with mock.patch.dict(os.environ, {OWN.LEDGER_WINS_ENV: "1"}):
            v = _contest(None, note_first=B_KEY)
        self.assertEqual((v.value, v.reason), (B_KEY, "ledger_note_first"))


if __name__ == "__main__":
    unittest.main()
