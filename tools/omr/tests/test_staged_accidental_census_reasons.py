"""The accidental census is a partition: every reason `accidental_owner` can emit must have a census key (2.192 `on_a_rest` was missing)."""
import unittest

from tools.omr.staged import adjudicate as A
from tools.omr.staged import export as X
from tools.omr.staged.record import Q


class CensusCoversEveryOwnerReason(unittest.TestCase):
    def test_every_declared_reason_has_a_census_key(self):
        reasons = set(A.REGISTRY[Q.ACCIDENTAL_OWNER].reasons) - {"immediately_right_same_position", "not_implemented"}  # DECIDED reason; framework stub reason
        self.assertEqual(reasons, set(X._ACCIDENTAL_CENSUS_BY_REASON), "census and producer vocabularies differ")

    def test_an_unlisted_reason_would_be_caught_and_on_a_rest_is_counted(self):
        class V(dict):
            pass
        class Rec:
            def verdicts_of(self, q):
                if q == Q.ACCIDENTAL_OWNER:
                    return [{"outcome": "abstained", "reason": "on_a_rest"}, {"outcome": "abstained", "reason": "made_up"}]
                return []
            def obs_of(self, q):
                return [1, 2]
        c = X._accidental_census(Rec(), {}, {})
        self.assertEqual(c["on_a_rest"], 1)
        self.assertEqual(c["unaccounted"], 1)  # the made-up reason is NOT silently absorbed


if __name__ == "__main__":
    unittest.main()
