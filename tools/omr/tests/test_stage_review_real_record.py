"""ROADMAP 3.4 lane B — the stage review against the REAL Litolff record.

⚠️ SLOW AND MACHINE-LOCAL, by the fast/slow split's own content rule: the
shared record and the edition are gitignored, so a fresh checkout has
neither. Absent, these SKIP — and a skip is reported as a skip, never as a
pass.

What they pin: the viewer's pick-list funnel is
`benchmarks/omr-notehead-funnel-2026-09/FINDINGS.md`'s own table, number for
number, on the staff the whole item was opened for.
"""

import unittest
from pathlib import Path

import pytest

from tools.omr.staged.record import Q
from tools.omr.staged.review import server as R

REAL_RECORD = Path("/Users/seanjohnson/Desktop/ReEngrave/library/"
                   "_shared-records/"
                   "beethoven5-litolff-mvt1-whole-20260923.record.json")


@pytest.mark.slow
class TestAgainstTheRealRecord(unittest.TestCase):
    """⚠️ MACHINE-LOCAL. `library/` is gitignored and a cloud checkout has
    none of it, so this SKIPS rather than fails where the record is absent —
    and a skip is reported as a skip, never as a pass."""

    @classmethod
    def setUpClass(cls):
        if not REAL_RECORD.exists():
            raise unittest.SkipTest(f"{REAL_RECORD} is not on this machine")
        cls.D = R.ReviewData(REAL_RECORD, None)

    def test_the_viola_funnel_matches_the_notehead_funnel_findings(self):
        """`benchmarks/omr-notehead-funnel-2026-09/FINDINGS.md`, Table 1:
        48 notehead boxes, 0 written, 40 `no_pitch`, 3
        `owned_by_another_staff`, 3 `clipped_fragment`, 1 `too_narrow`,
        1 `ink_is_a_whole_rest`."""
        f = self.D.staff_funnel("staff/3/0/9")
        self.assertEqual(f["heads_boxed"], 48)
        self.assertEqual(f["heads_written"], 0)
        self.assertEqual(f["refused"], {
            "ink_is_a_whole_rest": 1,
            "no_pitch": 40,
            "not_a_notehead:clipped_fragment": 3,
            "not_a_notehead:too_narrow": 1,
            "owned_by_another_staff": 3,
        })
        self.assertEqual(sum(f["refused"].values()) + f["heads_written"],
                         f["heads_boxed"])

    def test_the_clef_abstained_with_its_two_occupied_abstentions(self):
        v = R.staff_stage_view(self.D, "staff/3/0/9", "adjudicate")
        head = next(b for b in v["staff_level"]
                    if b["subject"] == "staff/3/0/9")
        clef = next(s for s in head["verdicts"] if s["quantity"] == Q.CLEF)
        self.assertEqual(clef["outcome"], "abstained")
        self.assertEqual(clef["reason"], "no_candidates")
        occupied = [a for a in head["abstentions"]
                    if a["quantity"] == Q.CLEF_LOCATED
                    and a["reason"] == "occupied"]
        self.assertEqual(len(occupied), 2)
        self.assertTrue(all(a["detail"] for a in occupied))

    def test_the_two_notehead_boxes_sit_on_the_alto_clef(self):
        """FINDINGS: `glyph/3/0/9/0/1` conf 0.64 and `glyph/3/0/9/0/6` conf
        0.36, at page px x 388-416, y 1828-1862 — the alto C-clef read as
        noteheads."""
        g = R.gather_view(self.D, "staff/3/0/9", 2)
        byid = {b["glyph"]: b for b in g["boxes"]}
        for key, conf in (("glyph/3/0/9/0/1", 0.64), ("glyph/3/0/9/0/6", 0.36)):
            b = byid[key]
            self.assertEqual(b["family"], "notehead")
            self.assertAlmostEqual(b["conf"], conf, places=2)
            x0, y0, x1, y1 = b["bbox_page_px"]
            self.assertTrue(388 <= x0 <= 389 and 415 <= x1 <= 416)
            self.assertTrue(1828 <= y0 <= 1829 and 1850 <= y1 <= 1862)
            self.assertEqual(b["refused"], ["no_pitch"])

    def test_the_viola_is_first_on_its_own_page(self):
        """⚠️ FIRST ON PAGE 3, and 12th over the WHOLE 16-page record — the
        funnel benchmark measured one page and the pick list measures the
        document, so the ranking is reported as what it is rather than as
        what the brief expected."""
        rows = [r for r in self.D.funnels() if r["page"] == 3]
        self.assertEqual(rows[0]["staff"], "staff/3/0/9")
