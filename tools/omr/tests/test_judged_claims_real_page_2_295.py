"""ROADMAP 2.295, SLOW: the judged-claims replay on the REAL saved slices of main (the post-2.284 Brahms p0,p14 gather), with the controls
that must fail where they should. Names the `library/` slices, so it is slow by rule (about 1.5 min)."""
import unittest

import pytest

from tools.omr.staged import claim_readout as CR
from tools.omr.staged import judged_claims as JC

pytestmark = pytest.mark.slow
SLICE = CR.RECORDS / "claim-readout-slices-brahms.main"


@unittest.skipUnless((SLICE / "observations.jsonl").exists(), "the claim-readout slices are machine-local")
class TestRealSlice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rep = JC.replay(str(SLICE), doc="brahms", log=lambda *_: None)

    def test_tiles_are_judged_on_both_pages_and_the_rest_cannot_tell_for_a_named_reason(self):
        rs = self.rep["results"]["base"]
        t = JC.tally(rs)
        self.assertGreater(t["agrees"], 10)
        self.assertEqual(sum(t.values()), len(rs))
        for r in rs:
            if r["verdict"] == "cannot_tell":
                self.assertTrue(r["why"])

    def test_controls_fail_where_they_must(self):
        self.assertEqual(JC.controls(str(SLICE), doc="brahms", log=lambda *_: None), 0)
