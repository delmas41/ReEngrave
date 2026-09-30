"""ROADMAP 1.5 -- the stage readout: one stage's output read off a record, a
GATHER+ADJUDICATE diff of two records, and the page over the print.

⚠️ The fixtures are built by the REAL `Log` and round-tripped through JSON,
the way the CLI reads a record, so a field `to_json` drops is invisible here
exactly as it is in production (`test_staged_trace`'s rule).

⚠️ Every "reports zero" assertion sits beside a pair that must report
non-zero, and every refusal beside a positive control of the same class.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import numpy as np

from tools.omr.staged import readout as RO
from tools.omr.staged import record as R
from tools.omr.staged.record import (Candidate, Log, Outcome, Q, READERS,
                                     Verdict, ABSTAIN)

STAFF0 = [100.0, 110.0, 120.0, 130.0, 140.0]
STAFF1 = [200.0, 210.0, 220.0, 230.0, 240.0]


def _v(log: Log, subject, quantity, outcome, value, decider, reason,
       candidates=(), supersedes=None) -> Verdict:
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=subject, quantity=quantity,
        outcome=outcome, value=value, decider=decider, reason=reason,
        candidates=tuple(candidates), supersedes=supersedes))


def _glyph(log: Log, g, cls, page_box, *, score=0.9):
    x0, y0, x1, y1 = page_box
    # canonical box: the cell frame, deliberately a different frame from the
    # page one (offset), as GATHER's is.
    log.observe(g, Q.GLYPH_BOX, [cls, x0 - 40, y0 - 60, x1 - x0, y1 - y0],
                reader=READERS.DETECTOR, frame=f"cell:{g.cell}", score=score,
                bbox_page_px=list(page_box))
    if cls.startswith("notehead"):
        log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
                    frame=f"cell:{g.cell}", score=score)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION,
                    ((y0 + y1) / 2.0 - STAFF0[0]) / 5.0,
                    reader=READERS.GEOMETRY, frame=f"cell:{g.cell}")


QUARTER = {"beats": 1.0, "written": 1.0, "dots": 0, "beam_levels": 0}
HALF = {"beats": 2.0, "written": 2.0, "dots": 0, "beam_levels": 0}
EIGHTH = {"beats": 0.5, "written": 0.5, "dots": 0, "beam_levels": 1}


def build_log(*, shift: bool = False, second_duration=QUARTER,
              with_glyphs: bool = True) -> Log:
    """One system, two staves, one bar each.

    staff 0 bar 0: a kept quarter, a head whose length is NARROWED, a quarter
    rest REFUSED as not a rest, and a head GIVEN to staff 1 by ownership.
    `shift=True` inserts an extra head at index 0 (a detector change), so
    every other glyph's INDEX moves up by one while its BOX stays put.
    """
    log = Log()
    st0, st1 = R.staff(0, 0, 0), R.staff(0, 0, 1)
    for st, ys in ((st0, STAFF0), (st1, STAFF1)):
        log.observe(st, Q.STAFF_LINES, ys, reader=READERS.GEOMETRY,
                    frame="page")
        log.observe(st, Q.STAFF_EXTENT, (50, 450), reader=READERS.GEOMETRY,
                    frame="page")
        _v(log, st, Q.CLEF, Outcome.DECIDED, "treble", "adjudicate_clef",
           "scored")
    c0 = R.cell(0, 0, 0, 0)
    log.observe(c0, Q.CELL_BOX, [50.0, 80.0, 450.0, 160.0],
                reader=READERS.GEOMETRY, frame="page")
    if not with_glyphs:
        log.abstain(c0, Q.GLYPH_BOX, reader=READERS.DETECTOR, frame="cell:0",
                    reason=ABSTAIN.READER_UNAVAILABLE)
        return log
    k = 1 if shift else 0
    if shift:
        extra = R.glyph(0, 0, 0, 0, 0)
        _glyph(log, extra, "noteheadBlackOnLine", (300, 108, 310, 118))
        _v(log, extra, Q.DURATION, Outcome.DECIDED, QUARTER,
           "adjudicate_duration", "head_and_marks")
    g_kept = R.glyph(0, 0, 0, 0, 0 + k)
    g_narrow = R.glyph(0, 0, 0, 0, 1 + k)
    g_rest = R.glyph(0, 0, 0, 0, 2 + k)
    g_away = R.glyph(0, 0, 0, 0, 3 + k)
    _glyph(log, g_kept, "noteheadBlackInSpace", (100, 105, 110, 115))
    _glyph(log, g_narrow, "noteheadBlackOnLine", (150, 115, 160, 125))
    _glyph(log, g_rest, "restQuarter", (200, 108, 208, 132))
    _glyph(log, g_away, "noteheadBlackOnLine", (250, 175, 260, 185))
    for g in (g_kept, g_narrow, g_away):
        _v(log, g, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.DECIDED, False,
           "adjudicate_notehead_is_not_a_notehead", "notehead")
    _v(log, g_kept, Q.GLYPH_OWNER, Outcome.DECIDED, st0.to_key(),
       "adjudicate_glyph_owner", "distance")
    _v(log, g_away, Q.GLYPH_OWNER, Outcome.DECIDED, st1.to_key(),
       "adjudicate_glyph_owner", "distance")
    if second_duration is None:
        _v(log, g_kept, Q.DURATION, Outcome.NARROWED, None,
           "adjudicate_duration", "beams_ambiguous",
           candidates=(Candidate(QUARTER, 2.0), Candidate(EIGHTH, 1.0)))
    else:
        _v(log, g_kept, Q.DURATION, Outcome.DECIDED, second_duration,
           "adjudicate_duration", "head_and_marks")
    _v(log, g_narrow, Q.DURATION, Outcome.NARROWED, None,
       "adjudicate_duration", "beams_ambiguous",
       candidates=(Candidate(HALF, 2.0), Candidate(QUARTER, 1.0)))
    _v(log, g_rest, Q.REST_IS_NOT_A_REST, Outcome.DECIDED, True,
       "adjudicate_rest_is_not_a_rest", "rest_has_a_stem")
    _v(log, g_away, Q.DURATION, Outcome.DECIDED, QUARTER,
       "adjudicate_duration", "head_and_marks")
    return log


def result_of(log: Log, *, commit="c0ffee", weights="prod-w.pt",
              pages="0", dpi=600, pdf="score-a") -> dict:
    return json.loads(json.dumps({
        "record": log.to_json(), "stopped_after": "adjudicate",
        "weight_routing": {"weights": f"/some/where/{weights}"},
        "provenance": {"commit": commit, "dirty": False, "settings": {
            "env_overrides": {},
            "args": {"pdf": pdf, "pages": pages, "dpi": dpi,
                     "weights": "auto", "through": "adjudicate",
                     "conf": 0.25}}},
    }, default=str))


def run_of(log: Log, **kw) -> RO.Run:
    return RO.run_from_result(result_of(log, **kw))


class TestNoDetectorIsRefused(unittest.TestCase):
    """The 2026-09-30 overnight run: no `--weights`, the detector never
    fired, every stage had nothing to decide, and it exited 0."""

    def test_a_record_with_no_gathered_glyph_is_REFUSED(self):
        res = result_of(build_log(with_glyphs=False))
        with self.assertRaises(RO.NoGatheredGlyphs) as cm:
            RO.run_from_result(res, path="empty")
        self.assertIn("--weights auto", str(cm.exception))
        self.assertIn("reader_unavailable", str(cm.exception))

    def test_positive_control_the_same_record_WITH_glyphs_loads(self):
        run = RO.run_from_result(result_of(build_log()))
        self.assertEqual(len(run.glyphs), 4)

    def test_the_cli_exits_2_on_it_for_show_and_for_diff(self):
        with tempfile.TemporaryDirectory() as d:
            empty = os.path.join(d, "empty.json")
            full = os.path.join(d, "full.json")
            with open(empty, "w") as fh:
                json.dump(result_of(build_log(with_glyphs=False)), fh)
            with open(full, "w") as fh:
                json.dump(result_of(build_log()), fh)
            self.assertEqual(RO.main(["show", empty]), 2)
            self.assertEqual(RO.main(["diff", empty, full]), 2)
            self.assertEqual(RO.main(["diff", full, empty]), 2)
            out = os.path.join(d, "o.txt")
            self.assertEqual(RO.main(["show", full, "--out", out]), 0)


class TestOneStageInIsolation(unittest.TestCase):

    def setUp(self):
        self.run = run_of(build_log())

    def test_through_gather_holds_no_adjudicate_row(self):
        rows = RO.readout_rows(self.run, through="gather")
        self.assertTrue(rows)
        self.assertEqual({r["stage"] for r in rows}, {"GATHER"})
        self.assertIn(Q.GLYPH_BOX, {r["quantity"] for r in rows})

    def test_through_adjudicate_adds_the_verdicts_and_nothing_later(self):
        rows = RO.readout_rows(self.run, through="adjudicate")
        self.assertEqual({r["stage"] for r in rows}, {"GATHER", "ADJUDICATE"})
        dur = [r for r in rows if r["quantity"] == Q.DURATION
               and r["subject"] == "glyph/0/0/0/0/1"]
        self.assertEqual(dur[0]["entries"][0]["outcome"], "narrowed")
        self.assertEqual(len(dur[0]["entries"][0]["candidates"]), 2)

    def test_an_evaluate_revision_is_its_own_stage_and_names_what_it_revised(self):
        log = build_log()
        g = R.glyph(0, 0, 0, 0, 0)
        first = [v for v in log.all_verdicts()
                 if v.subject == g and v.quantity == Q.DURATION][0]
        _v(log, g, Q.DURATION, Outcome.DECIDED, HALF, "reconcile_duration",
           "meter_reconciliation", supersedes=first.id)
        run = run_of(log)
        rows = RO.readout_rows(run, where=RO.Where(subject=g.to_key()))
        ev = [r for r in rows if r["stage"] == "EVALUATE"]
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["entries"][0]["revises"]["stage"], "ADJUDICATE")
        # and --through adjudicate hides it
        rows = RO.readout_rows(run, where=RO.Where(subject=g.to_key()),
                               through="adjudicate")
        self.assertNotIn("EVALUATE", {r["stage"] for r in rows})

    def test_the_machine_form_is_stable_and_carries_no_row_ids(self):
        import io
        a, b = io.StringIO(), io.StringIO()
        RO.write_jsonl(RO.readout_rows(run_of(build_log())), a)
        RO.write_jsonl(RO.readout_rows(run_of(build_log())), b)
        self.assertEqual(a.getvalue(), b.getvalue())
        self.assertNotIn('"obs:', a.getvalue())
        self.assertNotIn('"vrd:', a.getvalue())

    def test_scope_filters_to_one_staff(self):
        rows = RO.readout_rows(self.run, where=RO.Where(page=0, staff=1))
        self.assertTrue(rows)
        self.assertTrue(all(r["staff"] == 1 for r in rows))

    def test_the_text_table_names_each_status(self):
        text = RO.render_text(self.run)
        for word in ("KEPT", "NARROWED", "REFUSED", "GIVEN AWAY"):
            self.assertIn(word, text)
        gather_only = RO.render_text(self.run, through="gather")
        self.assertNotIn("ADJUDICATE", gather_only.split("\n", 2)[2])


class TestTheStatusWord(unittest.TestCase):

    def test_each_status_from_its_own_verdict(self):
        run = run_of(build_log())
        st = {k: RO.adjudicate_status(run, g)[0] for k, g in run.glyphs.items()}
        self.assertEqual(st["glyph/0/0/0/0/0"], RO.KEPT)
        self.assertEqual(st["glyph/0/0/0/0/1"], RO.NARROWED)
        self.assertEqual(st["glyph/0/0/0/0/2"], RO.REFUSED)
        self.assertEqual(st["glyph/0/0/0/0/3"], RO.GIVEN_AWAY)

    def test_a_refusal_decided_FALSE_is_not_a_refusal(self):
        run = run_of(build_log())
        why = RO.adjudicate_status(run, run.glyphs["glyph/0/0/0/0/2"])[1]
        self.assertIn("not a rest", why[0])
        self.assertEqual(RO.adjudicate_status(
            run, run.glyphs["glyph/0/0/0/0/0"])[0], RO.KEPT)


class TestTheDiff(unittest.TestCase):

    def test_CONTROL_two_identical_records_diff_to_zero(self):
        d = RO.diff_runs(run_of(build_log()), run_of(build_log()))
        self.assertEqual(d["n_differences"], 0)

    def test_and_a_changed_verdict_diffs_to_non_zero_with_its_direction(self):
        d = RO.diff_runs(run_of(build_log()),
                         run_of(build_log(second_duration=None)))
        self.assertEqual(d["n_differences"], 1)
        row = d["families"]["note"]["adjudicate"][Q.DURATION]
        self.assertEqual(row["changed"], 1)
        (direction,) = row["directions"]
        self.assertTrue(direction.startswith("decided:"))
        self.assertIn("-> narrowed:", direction)
        self.assertEqual(d["families"]["note"]["status"]["kept -> narrowed"], 1)

    def test_a_changed_GATHER_reading_is_a_difference_too(self):
        log_b = build_log()
        log_b.observe(R.glyph(0, 0, 0, 0, 0), Q.LEDGER_RUNG_INK, True,
                      reader=READERS.CV_INK, frame="page")
        d = RO.diff_runs(run_of(build_log()), run_of(log_b))
        self.assertEqual(d["n_differences"], 1)
        self.assertEqual(
            d["families"]["note"]["gather"][Q.LEDGER_RUNG_INK]["changed"], 1)

    def test_glyphs_are_matched_by_BOX_OVERLAP_when_their_indexes_shift(self):
        a, b = run_of(build_log()), run_of(build_log(shift=True))
        # the fixture really shifts: the same index names a different box
        self.assertNotEqual(a.glyphs["glyph/0/0/0/0/0"].box_page,
                            b.glyphs["glyph/0/0/0/0/0"].box_page)
        pairs, only_a, only_b = RO.match_glyphs(a, b)
        mapping = {pa: pb for pa, pb, _iou, _how in pairs}
        for i in range(4):
            self.assertEqual(mapping[f"glyph/0/0/0/0/{i}"],
                             f"glyph/0/0/0/0/{i + 1}")
        self.assertEqual(only_a, [])
        self.assertEqual(only_b, ["glyph/0/0/0/0/0"])
        d = RO.diff_runs(a, b)
        self.assertEqual(d["families"]["note"]["only_b"], 1)
        self.assertEqual(d["changed_pairs"], [])
        self.assertEqual(d["n_differences"], 1)

    def test_family_filter(self):
        d = RO.diff_runs(run_of(build_log()), run_of(build_log(shift=True)),
                         family="rest")
        self.assertEqual(list(d["families"]), ["rest"])
        self.assertEqual(d["n_differences"], 0)

    def test_the_cli_exits_1_on_a_difference_and_0_on_none(self):
        with tempfile.TemporaryDirectory() as d:
            pa, pb = os.path.join(d, "a.json"), os.path.join(d, "b.json")
            with open(pa, "w") as fh:
                json.dump(result_of(build_log()), fh)
            with open(pb, "w") as fh:
                json.dump(result_of(build_log(second_duration=None)), fh)
            out = os.path.join(d, "o.txt")
            self.assertEqual(RO.main(["diff", pa, pa, "--out", out]), 0)
            self.assertEqual(RO.main(["diff", pa, pb, "--out", out]), 1)
            with open(out) as fh:
                self.assertIn("decided", fh.read())


class TestProvenance(unittest.TestCase):

    def test_different_pages_are_REFUSED(self):
        with self.assertRaises(RO.ProvenanceRefused):
            RO.check_provenance(run_of(build_log(), pages="0"),
                                run_of(build_log(), pages="1"))

    def test_an_arm_that_is_not_the_only_difference_is_REFUSED(self):
        a = run_of(build_log(), commit="aaa", weights="prod.pt")
        b = run_of(build_log(), commit="bbb", weights="graft.pt")
        with self.assertRaises(RO.ProvenanceRefused):
            RO.check_provenance(a, b, arm=["weights"])
        # positive control: naming both arms passes, and --force passes
        diffs, _ = RO.check_provenance(a, b, arm=["weights", "code"])
        self.assertEqual({d[0] for d in diffs}, {"weights", "code"})
        RO.check_provenance(a, b, arm=["weights"], force=True)

    def test_the_weights_arm_alone_passes_and_is_reported(self):
        a = run_of(build_log(), weights="prod.pt")
        b = run_of(build_log(), weights="graft.pt")
        diffs, warn = RO.check_provenance(a, b, arm=["weights"])
        self.assertEqual(diffs, [("weights", "weights", "prod.pt", "graft.pt")])

    def test_an_unnamed_tree_is_announced(self):
        a = run_of(build_log(), commit=None)
        diffs, warn = RO.check_provenance(a, run_of(build_log()))
        self.assertTrue(any("does not name its tree" in w for w in warn))


def _page_image(ys_shift: float = 0.0):
    img = np.full((300, 500, 3), 255, dtype=np.uint8)
    for y in STAFF0 + STAFF1:
        r = int(round(y + ys_shift))
        img[r:r + 2, 50:450] = 0
    return img


class TestThePage(unittest.TestCase):

    def test_the_frame_control_passes_on_the_print_and_FAILS_off_it(self):
        run = run_of(build_log())
        self.assertGreater(RO.frame_control(_page_image(), run, 0), 0)
        # the same lines, half a space off: the control must go non-positive
        self.assertLessEqual(RO.frame_control(_page_image(5.0), run, 0), 0)

    def test_the_page_draws_each_stage_and_says_what_each_colour_means(self):
        run = run_of(build_log())
        page = RO.build_html(run, lambda p: _page_image(), scale=1.0)
        for words in ("kept", "thrown out", "given to the neighbouring staff",
                      "length still undecided", "What the detector found",
                      "frame check passed"):
            self.assertIn(words, page)
        self.assertEqual(page.count('class="ov-g"'), 4)
        self.assertEqual(page.count('class="ov-a"'), 4)
        self.assertNotIn("stage-diff", page.split("<section>")[1])
        bad = RO.build_html(run, lambda p: _page_image(5.0), scale=1.0)
        self.assertIn("do NOT land on the print", bad)

    def test_diff_mode_marks_what_changed(self):
        a = run_of(build_log())
        b = run_of(build_log(shift=True, second_duration=None))
        page = RO.build_html(b, lambda p: _page_image(), against=a, scale=1.0)
        self.assertIn("What changed", page)
        self.assertEqual(page.count('class="ov-d"'), 5)
        self.assertIn("ONLY IN B", page)
        self.assertIn("FOUND IN BOTH, READ OR DECIDED DIFFERENTLY", page)


if __name__ == "__main__":
    unittest.main()
