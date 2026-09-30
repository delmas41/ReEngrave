"""Fast unit tests for the pure logic in `tools.omr.acceptance_quick` that
does not need a gather, a shared record, or the score library — the
manifest-parsing helper the manager review of ff8afcb8 (2026-09-30) added,
and ROADMAP 1.6b's GATHER+ADJUDICATE `stage_summary` aggregator.

CLAUDE.md §6c: a test file's text must not contain certain path fragments
(the score store's directory name, the weights directory name, a venv, or
a quoted document-extension path) or the whole file goes slow silently —
none of those fragments are spelled out literally anywhere in this file,
including this docstring, so it stays in the fast tier.

The `stage_summary` fixture is built the way `test_staged_readout.py` builds
its own (a real `record.Log`, round-tripped through JSON the way the CLI
writes a record) — no gather, no PDF, no weights.
"""
import json
import unittest

from tools.omr.acceptance_quick import (
    QuickError, first_movement_page, render_stage_table, stage_summary,
)
from tools.omr.staged import readout as RD
from tools.omr.staged.record import (Candidate, Log, Outcome, Q, READERS,
                                     Verdict, ABSTAIN)
from tools.omr.staged import record as R


class TestFirstMovementPage(unittest.TestCase):
    """The bug this guards: gathering ONLY the count page loses the meter/
    key CARRY from earlier pages (manager review, 2026-09-30) — the fix
    is gathering from the movement's first page through the count page,
    and that first page must be READ from the manifest, never guessed."""

    def test_reads_structural_whole_movement_field(self):
        doc = {"id": "x", "whole_movement": {"pages": "1-16"}}
        self.assertEqual(first_movement_page(doc), 1)

    def test_reads_zero_indexed_structural_field(self):
        doc = {"id": "x", "whole_movement": {"pages": "0-26"}}
        self.assertEqual(first_movement_page(doc), 0)

    def test_falls_back_to_prose_in_caveats(self):
        doc = {"id": "x", "caveats": [
            "Whole movement, pdf pages 0-26 (27 pages). The movement "
            "boundary was VERIFIED against the plate, not assumed."]}
        self.assertEqual(first_movement_page(doc), 0)

    def test_structural_field_wins_over_caveats(self):
        doc = {"id": "x", "whole_movement": {"pages": "1-16"},
              "caveats": ["Whole movement, pdf pages 9-99 (fake, should not win)."]}
        self.assertEqual(first_movement_page(doc), 1)

    def test_refuses_when_neither_is_present(self):
        doc = {"id": "x"}
        with self.assertRaises(QuickError):
            first_movement_page(doc)


# ─────────────────────────────────────────────────────────────────────────
# ROADMAP 1.6b -- the GATHER+ADJUDICATE stage summary
# ─────────────────────────────────────────────────────────────────────────

def _v(log, subject, quantity, outcome, value, decider, reason,
      candidates=()) -> Verdict:
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=subject, quantity=quantity,
        outcome=outcome, value=value, decider=decider, reason=reason,
        candidates=tuple(candidates)))


def _notehead(log, g, page_box, *, staff_ys):
    x0, y0, x1, y1 = page_box
    log.observe(g, Q.GLYPH_BOX,
               ["noteheadBlackOnLine", x0 - 40, y0 - 60, x1 - x0, y1 - y0],
               reader=READERS.DETECTOR, frame=f"cell:{g.cell}", score=0.9,
               bbox_page_px=list(page_box))
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine",
               reader=READERS.DETECTOR, frame=f"cell:{g.cell}", score=0.9)
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION,
               ((y0 + y1) / 2.0 - staff_ys[0]) / 5.0,
               reader=READERS.GEOMETRY, frame=f"cell:{g.cell}")


def _rest(log, g, page_box):
    x0, y0, x1, y1 = page_box
    log.observe(g, Q.GLYPH_BOX,
               ["restQuarter", x0 - 40, y0 - 60, x1 - x0, y1 - y0],
               reader=READERS.DETECTOR, frame=f"cell:{g.cell}", score=0.8,
               bbox_page_px=list(page_box))


QUARTER = {"beats": 1.0, "written": 1.0, "dots": 0, "beam_levels": 0}
HALF = {"beats": 2.0, "written": 2.0, "dots": 0, "beam_levels": 0}


def _build_fixture_run() -> RD.Run:
    """One page, one system, two staves, one bar each:

    staff 0: clef DECIDED treble; a KEPT note (owner decided, duration
    decided), a NARROWED note (duration narrowed), a note whose position is
    ABSTAINED (`no_staff_geometry`), and a REFUSED rest (not a rest).
    staff 1: clef ABSTAINED; a note GIVEN AWAY to it from staff 0.
    system meter: DECIDED 4/4.
    """
    log = Log()
    ys0 = [100.0, 110.0, 120.0, 130.0, 140.0]
    ys1 = [200.0, 210.0, 220.0, 230.0, 240.0]
    st0, st1 = R.staff(0, 0, 0), R.staff(0, 0, 1)
    for st, ys in ((st0, ys0), (st1, ys1)):
        log.observe(st, Q.STAFF_LINES, ys, reader=READERS.GEOMETRY, frame="page")
    _v(log, st0, Q.CLEF, Outcome.DECIDED, "treble", "adjudicate_clef", "scored")
    _v(log, st1, Q.CLEF, Outcome.ABSTAINED, None, "adjudicate_clef", "no_clusters")

    sysk = R.system(0, 0)
    _v(log, sysk, Q.METER, Outcome.DECIDED, {"beats": 4, "beat_type": 4},
      "adjudicate_meter", "meter_printed")

    g_kept = R.glyph(0, 0, 0, 0, 0)
    g_narrow = R.glyph(0, 0, 0, 0, 1)
    g_pos_abstained = R.glyph(0, 0, 0, 0, 2)
    g_rest = R.glyph(0, 0, 0, 0, 3)
    g_away = R.glyph(0, 0, 1, 0, 0)

    _notehead(log, g_kept, (100, 105, 110, 115), staff_ys=ys0)
    _notehead(log, g_narrow, (150, 115, 160, 125), staff_ys=ys0)
    _rest(log, g_rest, (200, 108, 208, 132))
    # a note whose position GATHER declined (a real detector head, but no
    # NOTEHEAD_STAFF_POSITION observation -- an abstention in its place).
    log.observe(g_pos_abstained, Q.GLYPH_BOX,
               ["noteheadBlackOnLine", 210, 15, 10, 10],
               reader=READERS.DETECTOR, frame="cell:0", score=0.7,
               bbox_page_px=[250, 175, 260, 185])
    log.abstain(g_pos_abstained, Q.NOTEHEAD_STAFF_POSITION,
               reader=READERS.GEOMETRY, frame="cell:0",
               reason=ABSTAIN.NO_STAFF_GEOMETRY)
    _notehead(log, g_away, (250, 275, 260, 285), staff_ys=ys1)

    for g in (g_kept, g_narrow, g_pos_abstained, g_away):
        _v(log, g, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.DECIDED, False,
          "adjudicate_notehead_is_not_a_notehead", "notehead")
    _v(log, g_kept, Q.GLYPH_OWNER, Outcome.DECIDED, st0.to_key(),
      "adjudicate_glyph_owner", "distance")
    _v(log, g_away, Q.GLYPH_OWNER, Outcome.DECIDED, st0.to_key(),
      "adjudicate_glyph_owner", "distance")
    _v(log, g_kept, Q.DURATION, Outcome.DECIDED, QUARTER,
      "adjudicate_duration", "head_and_marks")
    _v(log, g_narrow, Q.DURATION, Outcome.NARROWED, None,
      "adjudicate_duration", "beams_ambiguous",
      candidates=(Candidate(HALF, 2.0), Candidate(QUARTER, 1.0)))
    _v(log, g_away, Q.DURATION, Outcome.DECIDED, QUARTER,
      "adjudicate_duration", "head_and_marks")
    _v(log, g_rest, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, True,
      "adjudicate_rest_is_not_a_rest", "rest_has_a_stem")

    result = json.loads(json.dumps({
        "record": log.to_json(), "stopped_after": "adjudicate",
        "weight_routing": {"weights": "/some/where/prod-w.pt"},
        "provenance": {"commit": "c0ffee", "dirty": False, "settings": {
            "env_overrides": {},
            "args": {"pdf": "score-a", "pages": "0", "dpi": 600,
                     "weights": "auto", "through": "adjudicate",
                     "conf": 0.25}}},
    }, default=str))
    return RD.run_from_result(result)


class TestStageSummary(unittest.TestCase):
    def setUp(self):
        self.run = _build_fixture_run()
        self.summary = stage_summary(self.run, page_index=0)

    def test_gathered_counts_by_family(self):
        self.assertEqual(self.summary["gathered_total"], 5)
        self.assertEqual(self.summary["families"]["note"]["gathered"], 4)
        self.assertEqual(self.summary["families"]["rest"]["gathered"], 1)

    def test_note_status_partition(self):
        """`g_kept` KEPT (owner+duration decided); `g_narrow` NARROWED
        (duration narrowed); `g_away` GIVEN AWAY (owner decided elsewhere,
        checked before duration); `g_pos_abstained` carries no DURATION
        verdict at all, so `adjudicate_status` reports it ABSTAINED --
        its GATHER-stage position abstention is a SEPARATE fact, reported
        under `staff_position` below, never folded into this partition."""
        st = self.summary["families"]["note"]["status"]
        self.assertEqual(st.get(RD.KEPT, 0), 1)
        self.assertEqual(st.get(RD.NARROWED, 0), 1)
        self.assertEqual(st.get(RD.GIVEN_AWAY, 0), 1)
        self.assertEqual(st.get(RD.ABSTAINED, 0), 1)
        self.assertEqual(sum(st.values()), 4)

    def test_rest_refused_with_reason(self):
        rest = self.summary["families"]["rest"]
        self.assertEqual(rest["status"].get(RD.REFUSED), 1)
        self.assertTrue(any("rest" in k for k in rest["reasons"]))

    def test_owner_decided_count(self):
        owner = self.summary["families"]["note"]["owner"]["by_outcome"]
        self.assertEqual(owner.get("decided", 0), 2)  # g_kept, g_away
        self.assertEqual(owner.get("no_verdict", 0), 2)  # g_narrow, g_pos_abstained

    def test_duration_narrowed_reason(self):
        dur = self.summary["families"]["note"]["duration"]
        self.assertEqual(dur["by_outcome"].get("narrowed", 0), 1)
        self.assertIn("beams_ambiguous", dur["reasons"])

    def test_staff_position_observed_and_abstained(self):
        pos = self.summary["families"]["note"]["staff_position"]["by_outcome"]
        self.assertEqual(pos.get("observed", 0), 3)
        self.assertEqual(pos.get("abstained", 0), 1)

    def test_clef_by_staff(self):
        clefs = self.summary["clef_by_staff"]
        self.assertEqual(clefs["staff/0/0/0"]["outcome"], "decided")
        self.assertEqual(clefs["staff/0/0/0"]["value"], "treble")
        self.assertEqual(clefs["staff/0/0/1"]["outcome"], "abstained")

    def test_meter_by_system_decided(self):
        meters = self.summary["meter_by_system"]
        self.assertEqual(meters["system/0/0"]["outcome"], "decided")

    def test_render_stage_table_runs_and_mentions_every_family(self):
        text = render_stage_table("fixture-doc", self.summary)
        self.assertIn("note", text)
        self.assertIn("rest", text)
        self.assertIn("clef by staff", text)
        self.assertIn("meter by system", text)

    @staticmethod
    def _count_verdicts(run, family, quantity, outcome="decided"):
        """An INDEPENDENT count of (family, quantity, outcome) verdicts, off
        `readout.readout_rows` rather than `stage_summary`'s own
        `run.standing` calls -- the cross-check `stage_summary`'s table must
        agree with (CLAUDE.md rule 7)."""
        n = 0
        for r in RD.readout_rows(run, family=family, through="adjudicate"):
            if r["quantity"] != quantity:
                continue
            for e in r["entries"]:
                if e["row"] == "verdict" and e.get("outcome") == outcome:
                    n += 1
        return n

    def test_control_owner_decided_matches_readout_rows(self):
        self.assertEqual(
            self._count_verdicts(self.run, "note", Q.GLYPH_OWNER, "decided"),
            self.summary["families"]["note"]["owner"]["by_outcome"]
            .get("decided", 0))

    def test_control_rest_refusal_matches_readout_rows_and_can_fail(self):
        """Positive half of the control: build a SECOND record with the
        rest's own refusal verdict removed and require BOTH the
        independent `readout_rows` count and `stage_summary`'s REFUSED
        bucket to drop to zero together -- if either stayed frozen at 1
        the cross-check would not be measuring anything."""
        self.assertEqual(
            self._count_verdicts(self.run, "rest", Q.REST_IS_NOT_A_REST,
                                 "decided"), 1)
        self.assertEqual(self.summary["families"]["rest"]["status"]
                         .get(RD.REFUSED, 0), 1)

        log = Log()
        g_rest = R.glyph(0, 0, 0, 0, 0)
        _rest(log, g_rest, (200, 108, 208, 132))
        result = json.loads(json.dumps({
            "record": log.to_json(), "stopped_after": "adjudicate",
            "weight_routing": {"weights": "/some/where/prod-w.pt"},
            "provenance": {"commit": "c0ffee", "dirty": False, "settings": {
                "env_overrides": {}, "args": {
                    "pdf": "score-a", "pages": "0", "dpi": 600,
                    "weights": "auto", "through": "adjudicate",
                    "conf": 0.25}}},
        }, default=str))
        run = RD.run_from_result(result)
        summary = stage_summary(run, page_index=0)
        self.assertEqual(
            self._count_verdicts(run, "rest", Q.REST_IS_NOT_A_REST,
                                 "decided"), 0)
        self.assertEqual(summary["families"]["rest"]["status"]
                         .get(RD.REFUSED, 0), 0)
        self.assertEqual(summary["families"]["rest"]["status"]
                         .get(RD.UNDECIDED, 0), 1)


if __name__ == "__main__":
    unittest.main()
