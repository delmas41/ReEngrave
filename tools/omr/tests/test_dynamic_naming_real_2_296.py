"""ROADMAP 2.296 (A), SLOW: the readout tools name a claim by the READER THAT FILED IT (`claim_readout.named_owner`), on the REAL saved Litolff slice of main
and Sean's REAL answered tiles. His five dynamic tiles on page 2 (2.284b r1 #2, #7; r2 #2, #5; 2.276 r2 #10) must stop reading as a WORD's ink; his
'cr of cresc.' (2.288 r1 #10) stays a word (the lexicon's category `dynamic` is not the reader); a plain word stays a word. Names `library/`: slow by rule."""
import unittest

import pytest

from tools.omr.staged import claim_readout as CR
from tools.omr.staged import judged_claims as JC

pytestmark = pytest.mark.slow
SLICE = CR.RECORDS / "claim-readout-slices-litolff.main"
FIVE = ("2.284b r1 #2", "2.284b r1 #7", "2.284b r2 #2", "2.284b r2 #5", "2.276 r2 #10")


class TestNamedOwner(unittest.TestCase):
    def test_pure_the_reader_names_it_not_the_category(self):
        self.assertEqual(CR.named_owner({"owner": "word", "source": "dynamic_letters", "category": "dynamic"}), "dynamic")
        self.assertEqual(CR.named_owner({"owner": "word", "source": "direction_word", "category": "dynamic"}), "word")      # `cresc.`
        self.assertEqual(CR.named_owner({"owner": "word", "source": "direction_word"}), "word")
        self.assertEqual(CR.named_owner({"owner": "tremolo", "source": "dynamic_letters"}), "tremolo")
        self.assertEqual(CR.fine_of(CR.named_owner({"owner": "word", "source": "dynamic_letters"})), "dynamic")


@unittest.skipUnless((SLICE / "observations.jsonl").exists(), "the claim-readout slices are machine-local")
class TestRealLitolff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rs = {r["id"]: r for r in JC.replay(str(SLICE), doc="litolff", pages=[2], log=lambda *_: None)["results"]["base"]}

    def test_the_five_dynamic_tiles_are_not_read_as_a_words_ink(self):
        for tid in FIVE:
            r = self.rs[tid]
            self.assertIn(r["verdict"], ("agrees", "contradicts"), tid)
            self.assertGreaterEqual(r["read_kinds"].get("dynamic", 0), 0.4, tid)
            self.assertNotIn("word", r["read_kinds"], tid)
        # the fifth (r2 #2, `sf`) is CLAIMED TWICE: a beam and a stem stand on its ink too
        self.assertEqual(sum(self.rs[t]["verdict"] == "agrees" for t in FIVE), 4)

    def test_CONTROL_cr_of_cresc_stays_a_word(self):
        r = self.rs["2.288 r1 #10"]
        self.assertNotIn("dynamic", r["read_kinds"])
