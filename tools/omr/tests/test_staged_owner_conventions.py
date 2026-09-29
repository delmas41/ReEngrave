"""ROADMAP 2.6c — Sean's two ownership conventions (DECISIONS 2026-09-28),
applied where `glyph_owner`'s weakest term, `range_veto`, decides today.

    "there have to be ledger lines in between wherever that note is and the
    staff that it's connected to ... if the note is above the hairpin ... it
    belongs to the staff that's between the hairpin and that staff"

Evidence: 24 crops of `glyph_owner` losers on the Brahms 1/i record
(`benchmarks/omr-owner-domain-2026-09/FINDINGS.md` §2.6b/§2.6b.v). Over a
149-decision `range_veto` population, distance went 8/8 and ladder 7/7 —
`range_veto` went 2 of 3 wrong: crops #19 (`glyph/12/1/6/7/7`) and #20
(`glyph/16/0/5/5/1`), both a Horn note one space above its own staff (no
ledger needed at all) wrongly vetoed by the written-range table and handed to
a distant, unidentified staff whose own three-or-four-rung ladder was never
detected.

⚠️ NEITHER CONVENTION, TAKEN LITERALLY, IS WHAT FIXES #19/#20. Convention 1
as Sean states it ("ledger lines... between it and the staff it belongs to")
describes rungs that are FOUND; in both crops the correct staff needs ZERO
rungs (it is close enough that `gather._observe_ladder` never even asks) and
the wrong, distant staff's rungs are simply ABSENT (found 0 of 3-4). The gap
this lane closes is the corollary: a candidate that never had to leave its
own staff is not "no evidence" against a rival who demonstrably HAD to and
couldn't — the same shape as the 2026-09-23 precedent (a note one space
beyond a neighbour's outer line is that staff's, on its own first ledger
line, while the far staff's three-rung ladder was never detected), one rung
shorter. Convention 2 (the hairpin) never gets a chance to speak on either
crop: neither system has a hairpin at all
(`Q.WEDGE_BOX` — zero rows on page 12 system 1 or page 16 system 0 near
either staff). Both findings are recorded here as fixture tests, not swept
under a synthetic pass.

⚠️ THE FIRST CONTROL PROVED WRONG BY ARITHMETIC, NOT ASSUMED: a genuinely
COMPLETE ladder's own `W_LADDER_COMPLETE` (+4.0) does not outweigh a range
veto's `W_RANGE_IMPOSSIBLE` (-6.0) on its own (`4.0 - 6.0 = -2.0`, still a net
loss against a rival with no veto). So `_ledger_direction_winner` cannot
refuse to fire wherever a candidate's own ladder happens to be genuinely
complete -- it has to be exactly as decisive there as in the vacuous case,
or convention 1 could not do the one thing the brief asks of it (`test_a_-
genuinely_complete_ladder_still_needs_the_convention_to_beat_a_veto` below
pins the arithmetic so a future "simplification" cannot reintroduce the gate
silently).
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate as A
from tools.omr.staged import adjudicators  # noqa: F401  registers decisions
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

SPEC = A.REGISTRY[Q.GLYPH_OWNER]

# A Violin can't read a note this low; a Contrabass can -- the exact shape
# `test_staged_ownership.py`'s own range-veto fixture uses, reused here so the
# baseline ("no rungs, no hairpin") is the ALREADY-COMMITTED, unchanged
# behaviour rather than a fresh assertion about it.
VIOLIN = {"name": "Violin", "family": "strings", "expected_clef": "treble",
          "written_range": [55, 100], "unpitched": False}
CONTRABASS = {"name": "Contrabass", "family": "strings",
              "expected_clef": "bass", "written_range": [28, 67],
              "unpitched": False}
HORN = {"name": "Horn", "family": "brass", "expected_clef": "treble",
        "written_range": [41, 77], "unpitched": False}

UPPER = R.staff(0, 0, 0)      # nearer the glyph; the range veto excludes it
LOWER = R.staff(0, 0, 1)      # farther; the only instrument that fits
GLYPH = R.glyph(0, 0, 0, 0, 0)

#: Under UPPER's treble clef the glyph reads G2 = MIDI 43, below a Violin's
#: written range (55, 100) -- IMPOSSIBLE. Under LOWER's bass clef it reads D3
#: = MIDI 50, inside a Contrabass's (28, 67) -- possible.
POS_IN_UPPER = 20.0
POS_IN_LOWER = 4.0


def _decide_verdict(log: Log, subject: R.Subject, quantity: str,
                    value) -> Verdict:
    # ⚠️ A UNIQUE id per call. `Log._vrd` is keyed by id alone, so two
    # verdicts sharing one hand-typed id silently overwrite each other in
    # that dict while the (quantity, subject) index still points at the
    # id — every lookup then returns whichever verdict was recorded LAST,
    # regardless of which subject or quantity asked.
    return Verdict(id=log._next_id("vrd"), subject=subject, quantity=quantity,
                   outcome=Outcome.DECIDED, value=value,
                   decider="test_fixture", reason="test")


def _base_log() -> Log:
    """The range-veto contest, identity-resolved, no ledger or hairpin
    evidence at all -- `range_veto` gives it to LOWER, unchanged."""
    log = Log()
    log.record(_decide_verdict(log, UPPER, Q.INSTRUMENT, VIOLIN))
    log.record(_decide_verdict(log, UPPER, Q.CLEF, "treble"))
    log.record(_decide_verdict(log, LOWER, Q.INSTRUMENT, CONTRABASS))
    log.record(_decide_verdict(log, LOWER, Q.CLEF, "bass"))
    log.observe(GLYPH, Q.GLYPH_BAND_DISTANCE, 1.0, reader=READERS.GEOMETRY,
                frame="page", candidate=UPPER.to_key(), own=True,
                position_in_candidate=POS_IN_UPPER)
    log.observe(GLYPH, Q.GLYPH_BAND_DISTANCE, 3.0, reader=READERS.GEOMETRY,
                frame="page", candidate=LOWER.to_key(), own=False,
                position_in_candidate=POS_IN_LOWER)
    return log


def _decide(log: Log) -> Verdict:
    log.freeze()
    return A.adjudicate_one(log, SPEC, GLYPH)


class TestBaselineUnchanged(unittest.TestCase):
    """CONTROL: no rungs and no hairpin — today's outcome, unchanged."""

    def test_no_rungs_no_hairpin_range_veto_still_wins(self):
        v = _decide(_base_log())
        self.assertEqual(v.value, LOWER.to_key())
        self.assertEqual(v.reason, "range_veto")


class TestLedgerDirection(unittest.TestCase):
    """Convention 1: rungs toward one staff, none toward the other."""

    def test_rungs_toward_upper_none_toward_lower_flips_the_veto(self):
        """RED under the old code (`range_veto` gives it to LOWER); GREEN
        once the ledger direction is read: a real, complete run of rungs
        toward UPPER against a real, definite absence toward LOWER decides
        ahead of the veto, exactly as the brief asks."""
        log = _base_log()
        log.observe(GLYPH, Q.GLYPH_LADDER, True, reader=READERS.DETECTOR,
                    frame="page", candidate=UPPER.to_key(),
                    expected=2, found=2, rungs=[])
        log.observe(GLYPH, Q.GLYPH_LADDER, False, reader=READERS.DETECTOR,
                    frame="page", candidate=LOWER.to_key(),
                    expected=3, found=0, rungs=[])
        v = _decide(log)
        self.assertEqual(v.value, UPPER.to_key())
        self.assertEqual(v.reason, "ledger_direction")

    def test_a_genuinely_complete_ladder_still_needs_the_convention_to_beat_a_veto(self):
        """⚠️ Pins the arithmetic the module docstring states: `+4.0` alone
        loses to `-6.0`. Without `ledger_direction`'s own term, UPPER's total
        would be `4.0 (ladder) - 6.0 (veto) - 0.5 (distance) = -2.5`, and
        LOWER's plain `-1.5` (distance only) would still win -- so a genuine
        complete ladder is not, by itself, decisive against the range veto."""
        log = _base_log()
        log.observe(GLYPH, Q.GLYPH_LADDER, True, reader=READERS.DETECTOR,
                    frame="page", candidate=UPPER.to_key(),
                    expected=2, found=2, rungs=[])
        log.observe(GLYPH, Q.GLYPH_LADDER, False, reader=READERS.DETECTOR,
                    frame="page", candidate=LOWER.to_key(),
                    expected=3, found=0, rungs=[])
        v = _decide(log)
        self.assertEqual(v.value, UPPER.to_key())
        self.assertEqual(v.reason, "ledger_direction")

    def test_no_directional_signal_when_both_sides_are_broken(self):
        """Two broken (non-vacuous) ladders are not evidence either way —
        `_ledger_direction_winner` requires exactly ONE clean side, and stays
        silent when neither qualifies. This is crop #19's OWN duplicate
        (`glyph/12/1/5/7/8`, staff/12/1/5 vs staff/12/1/6): both need real
        rungs (3 and 1) and both have none, so the contest is left to decide
        on `range_veto` exactly as before — a known, documented residual,
        not a regression this lane introduces."""
        log = _base_log()
        log.observe(GLYPH, Q.GLYPH_LADDER, False, reader=READERS.DETECTOR,
                    frame="page", candidate=UPPER.to_key(),
                    expected=1, found=0, rungs=[])
        log.observe(GLYPH, Q.GLYPH_LADDER, False, reader=READERS.DETECTOR,
                    frame="page", candidate=LOWER.to_key(),
                    expected=3, found=0, rungs=[])
        v = _decide(log)
        self.assertEqual(v.value, LOWER.to_key())
        self.assertEqual(v.reason, "range_veto")


class TestHairpinSeparates(unittest.TestCase):
    """Convention 2: a hairpin sits UNDER its staff."""

    #: UPPER's own staff lines, page pixels; bottom line at 140.
    UPPER_LINES = [100.0, 110.0, 120.0, 130.0, 140.0]

    def _log_with_head_and_lines(self, head_y: float) -> Log:
        log = _base_log()
        log.observe(UPPER, Q.STAFF_LINES, list(self.UPPER_LINES),
                    reader=READERS.GEOMETRY, frame="page")
        log.observe(GLYPH, Q.GLYPH_BOX,
                    ("noteheadBlackInSpace", 0, 0, 10, 10),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.8,
                    bbox_page_px=[500.0, head_y - 5.0, 510.0, head_y + 5.0],
                    x_center_page=505.0, y_center_page=head_y)
        return log

    def test_a_hairpin_below_the_head_flips_the_veto(self):
        """RED under the old code (`range_veto` gives it to LOWER); GREEN
        once the hairpin is read: the head (150) sits between UPPER's bottom
        line (140) and a hairpin filed under UPPER (200), so UPPER owns it —
        even with no ledger evidence at all."""
        log = self._log_with_head_and_lines(head_y=150.0)
        hairpin = R.glyph(UPPER.page, UPPER.system, UPPER.staff, 3, 0)
        log.observe(hairpin, Q.WEDGE_BOX, "diminuendo",
                    reader=READERS.CV_HAIRPINS, frame="page",
                    bbox_page_px=[490.0, 195.0, 560.0, 205.0],
                    x_center_page=525.0, y_center_page=200.0)
        v = _decide(log)
        self.assertEqual(v.value, UPPER.to_key())
        self.assertEqual(v.reason, "hairpin_separates")

    def test_a_hairpin_not_between_the_two_has_no_effect(self):
        """CONTROL: the same staff, the same head, but the hairpin sits
        ABOVE the head (145, between UPPER's bottom line and the head)
        rather than below it — the convention does not apply, and the
        contest falls through to `range_veto`, unchanged."""
        log = self._log_with_head_and_lines(head_y=150.0)
        hairpin = R.glyph(UPPER.page, UPPER.system, UPPER.staff, 3, 0)
        log.observe(hairpin, Q.WEDGE_BOX, "diminuendo",
                    reader=READERS.CV_HAIRPINS, frame="page",
                    bbox_page_px=[490.0, 140.0, 560.0, 150.0],
                    x_center_page=525.0, y_center_page=145.0)
        v = _decide(log)
        self.assertEqual(v.value, LOWER.to_key())
        self.assertEqual(v.reason, "range_veto")

    def test_a_detector_only_wedge_with_no_page_frame_is_declined(self):
        """CONTROL: a `Q.WEDGE_BOX` row from the DETECTOR reader carries a
        cell-frame box and no page coordinate (CLAUDE.md §10: a canonical
        cell frame cannot answer a cross-staff question) — it must be
        declined, never defaulted, and the contest still falls through to
        `range_veto`."""
        log = self._log_with_head_and_lines(head_y=150.0)
        hairpin = R.glyph(UPPER.page, UPPER.system, UPPER.staff, 3, 0)
        log.observe(hairpin, Q.WEDGE_BOX, "diminuendo",
                    reader=READERS.DETECTOR, frame="cell:3",
                    detector_class="dynamicDiminuendoHairpin")
        v = _decide(log)
        self.assertEqual(v.value, LOWER.to_key())
        self.assertEqual(v.reason, "range_veto")


class TestRealCrops(unittest.TestCase):
    """The two RED cases Sean print-adjudicated wrong
    (`out/print/o26b-manifest.json` #19/#20, `VERDICT: wrong_staff_dropped`),
    rebuilt from the exact rows on the committed f4168dfd Brahms record
    (`/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/redecide-f4168dfd/
    out-redecide/brahms/amended.record.json`, read once via
    `record_io.load_record` — see FINDINGS §2.6c for the full dump)."""

    def test_crop_19_glyph_12_1_6_7_7_now_names_the_horn_staff(self):
        """`glyph/12/1/6/7/7`: a Horn note one half-space above its own
        staff (`staff/12/1/6`, no ledger needed — no `Q.GLYPH_LADDER` row at
        all) that the range veto handed to `staff/12/1/5` (unidentified,
        needing a 4-rung ladder that was never detected). RED before this
        lane: `range_veto` -> staff/12/1/5. GREEN after: `ledger_direction`
        -> staff/12/1/6, matching Sean's `wrong_staff_dropped` verdict."""
        OWN = R.staff(12, 1, 6)
        OTH = R.staff(12, 1, 5)      # instrument abstained on the real page
        g = R.glyph(12, 1, 6, 7, 7)
        log = Log()
        log.record(_decide_verdict(log, OWN, Q.INSTRUMENT, HORN))
        log.record(_decide_verdict(log, OWN, Q.CLEF, "treble"))
        log.observe(g, Q.GLYPH_BAND_DISTANCE, 0.540000000000021,
                    reader=READERS.GEOMETRY, frame="page",
                    candidate=OWN.to_key(), own=True,
                    position_in_candidate=-1.080000000000042)
        log.observe(g, Q.GLYPH_BAND_DISTANCE, 3.784324324324303,
                    reader=READERS.GEOMETRY, frame="page",
                    candidate=OTH.to_key(), own=False,
                    position_in_candidate=15.568648648648606)
        log.observe(g, Q.GLYPH_LADDER, False, reader=READERS.DETECTOR,
                    frame="page", candidate=OTH.to_key(),
                    expected=4, found=0, rungs=[])
        log.freeze()
        v = A.adjudicate_one(log, SPEC, g)
        self.assertEqual(v.value, OWN.to_key())
        self.assertEqual(v.reason, "ledger_direction")

    def test_crop_20_glyph_16_0_5_5_1_now_names_the_horn_staff(self):
        """`glyph/16/0/5/5/1`: the same shape — a Horn note one half-space
        above `staff/16/0/5`, handed by the range veto to the Contrabassoon
        staff `staff/16/0/4` (a 3-rung ladder never detected). RED before:
        `range_veto` -> staff/16/0/4. GREEN after: `ledger_direction` ->
        staff/16/0/5, matching Sean's `wrong_staff_dropped` verdict."""
        OWN = R.staff(16, 0, 5)
        OTH = R.staff(16, 0, 4)
        g = R.glyph(16, 0, 5, 5, 1)
        BASSOON = {"name": "Contrabassoon", "family": "woodwind",
                   "expected_clef": "bass", "written_range": [22, 60],
                   "unpitched": False}
        log = Log()
        log.record(_decide_verdict(log, OWN, Q.INSTRUMENT, HORN))
        log.record(_decide_verdict(log, OWN, Q.CLEF, "treble"))
        log.record(_decide_verdict(log, OTH, Q.INSTRUMENT, BASSOON))
        log.record(_decide_verdict(log, OTH, Q.CLEF, "bass"))
        log.observe(g, Q.GLYPH_BAND_DISTANCE, 0.594999999999996,
                    reader=READERS.GEOMETRY, frame="page",
                    candidate=OWN.to_key(), own=True,
                    position_in_candidate=-1.189999999999992)
        log.observe(g, Q.GLYPH_BAND_DISTANCE, 3.119500000000004,
                    reader=READERS.GEOMETRY, frame="page",
                    candidate=OTH.to_key(), own=False,
                    position_in_candidate=14.239000000000008)
        log.observe(g, Q.GLYPH_LADDER, False, reader=READERS.DETECTOR,
                    frame="page", candidate=OTH.to_key(),
                    expected=3, found=0, rungs=[])
        log.freeze()
        v = A.adjudicate_one(log, SPEC, g)
        self.assertEqual(v.value, OWN.to_key())
        self.assertEqual(v.reason, "ledger_direction")

    def test_crop_19s_own_duplicate_stays_wrong_a_documented_residual(self):
        """`glyph/12/1/5/7/8` is crop #19's paired duplicate (the same ink,
        filed under `staff/12/1/5` instead) — and on ITS OWN contest neither
        side is clean: `staff/12/1/5` needs 3 rungs and has none,
        `staff/12/1/6` needs 1 and has none. `_ledger_direction_winner`
        correctly stays silent (two broken ladders are not evidence either
        way), so this one is UNCHANGED by 2.6c: `range_veto` still names
        `staff/12/1/5`, which Sean's crop #19 verdict says is wrong. Recorded
        here so the gap is visible rather than silently inherited."""
        OWN = R.staff(12, 1, 5)
        OTH = R.staff(12, 1, 6)
        g = R.glyph(12, 1, 5, 7, 8)
        log = Log()
        log.record(_decide_verdict(log, OTH, Q.INSTRUMENT, HORN))
        log.record(_decide_verdict(log, OTH, Q.CLEF, "treble"))
        log.observe(g, Q.GLYPH_BAND_DISTANCE, 3.540000000000021,
                    reader=READERS.GEOMETRY, frame="page",
                    candidate=OWN.to_key(), own=True,
                    position_in_candidate=15.080000000000043)
        log.observe(g, Q.GLYPH_LADDER, False, reader=READERS.DETECTOR,
                    frame="page", candidate=OWN.to_key(),
                    expected=3, found=0, rungs=[])
        log.observe(g, Q.GLYPH_BAND_DISTANCE, 0.7843243243243033,
                    reader=READERS.GEOMETRY, frame="page",
                    candidate=OTH.to_key(), own=False,
                    position_in_candidate=-1.5686486486486066)
        log.observe(g, Q.GLYPH_LADDER, False, reader=READERS.DETECTOR,
                    frame="page", candidate=OTH.to_key(),
                    expected=1, found=0, rungs=[])
        log.freeze()
        v = A.adjudicate_one(log, SPEC, g)
        self.assertEqual(v.value, OWN.to_key())
        self.assertEqual(v.reason, "range_veto")


if __name__ == "__main__":
    unittest.main()
