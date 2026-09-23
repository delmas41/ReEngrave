"""The STAGE REVIEW — ROADMAP 3.4: a human's corrections as WITNESSES.

⚠️ RUN RED FIRST, and in two stages, because two different things had to be
shown to fail:

  1. Against `origin/main` (03da5523) the whole file dies on
     `ModuleNotFoundError: tools.omr.staged.review` — the package did not
     exist. That proves the fixtures exercise code that is new, and nothing
     more.
  2. The one that matters: with `review/` and the new quantities present but
     `adjudicate_notehead_is_not_a_notehead`'s human test REMOVED, the file
     was run again — **4 failed, 36 passed**. The four are exactly
     `TestADeletedBoxIsRefused`'s four consequences (the verdict reads
     `decided False / notehead`, the export bucket is absent, `<note>` stays
     at 3, no verdict WEIGHED the row) and nothing else moved, so the delete
     tests are testing the CONNECT and not the ingest — the human row is
     filed either way.

⚠️ THE POSITIVE CONTROL IS THE FIRST CLASS IN THE FILE and it is the one that
makes the rest mean anything: an EMPTY sidecar must reproduce the record's
verdicts N/N and write a byte-identical MusicXML. A refusal battery passes by
refusing everything; this one cannot, because the empty arm has to come back
unchanged and the `add_box` arm has to come back with MORE.

⚠️ NO SOURCE-TEXT ASSERTIONS. The "which stages see a human box" table is
asserted against the VERDICTS a real adjudication produced, and the
offset-ordinal bases are read off `gather`'s own module attributes — never off
its text.
"""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.staged.review import feedback as FB
from tools.omr.staged.review import human_evidence as HE
from tools.omr.staged.review import rerun as RR


# ─────────────────────────────────────────────────────────────────────────────
# The fixture: one staff, one cell, three noteheads the detector drew
#
# ⚠️ BUILT BY RUNNING THE REAL STAGES, not by hand-writing verdicts. A
# hand-written verdict cannot be re-decided, and re-deciding is the whole
# subject of this file.
# ─────────────────────────────────────────────────────────────────────────────

SPACING = 100.0            # one staff space, canonical px
STEP = SPACING / 2.0       # one staff step
TOP_Y = 100.0              # canonical y of the staff's top line
UPSCALE = 2.0              # canonical px per page px
CELL_ORIGIN = (500.0, 1000.0)
HEAD_W, HEAD_H = 140.0, 60.0


def _page(x_c: float, y_c: float):
    return (CELL_ORIGIN[0] + x_c / UPSCALE, CELL_ORIGIN[1] + y_c / UPSCALE)


def _head_boxes(x_c: float, pos: float):
    """(canonical 5-tuple, page bbox) for a head at staff position `pos`."""
    y_c = TOP_Y + pos * STEP - HEAD_H / 2.0
    px0, py0 = _page(x_c, y_c)
    px1, py1 = _page(x_c + HEAD_W, y_c + HEAD_H)
    return (x_c, y_c, HEAD_W, HEAD_H), [px0, py0, px1, py1]


def build_log() -> Log:
    log = Log()
    cell, staff, system = R.cell(0, 0, 0, 0), R.staff(0, 0, 0), R.system(0, 0)
    log.observe(cell, Q.CELL_STAFF_SPACE, SPACING, reader=READERS.GEOMETRY,
                frame="cell:0", lines=5)
    log.observe(cell, Q.CELL_BOX,
                [CELL_ORIGIN[0], CELL_ORIGIN[1],
                 CELL_ORIGIN[0] + 400, CELL_ORIGIN[1] + 400],
                reader=READERS.GEOMETRY, frame="cell:0")
    for gi, (x_c, pos) in enumerate([(200.0, 4.0), (400.0, 2.0), (600.0, 6.0)]):
        g = R.glyph(0, 0, 0, 0, gi)
        (bx, by, bw, bh), page = _head_boxes(x_c, pos)
        log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", bx, by, bw, bh),
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                    category="notehead", bbox_page_px=page,
                    x_center_page=(page[0] + page[2]) / 2,
                    y_center_page=(page[1] + page[3]) / 2)
        log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine",
                    reader=READERS.DETECTOR, frame="cell:0", score=0.9)
        log.observe(g, Q.GLYPH_CONF, 0.9, reader=READERS.DETECTOR,
                    frame="cell:0", score=0.9)
        log.observe(g, Q.NOTEHEAD_STAFF_POSITION, pos,
                    reader=READERS.GEOMETRY, frame="cell:0",
                    residual=0.0, rounded=int(pos))
    log.observe(staff, Q.STAFF_LINES, [1050.0, 1075.0, 1100.0, 1125.0, 1150.0],
                reader=READERS.GEOMETRY, frame="page", page_staff_index=0)
    log.observe(staff, Q.CLEF_GLYPH, "gClef", reader=READERS.DETECTOR,
                frame="header:0", score=0.9)
    log.observe(staff, Q.MARGIN_LABEL, "Flauti", reader=READERS.TEXT_LAYER,
                frame="page", score=1.0)
    log.observe(system, Q.METER_GLYPH, "4/4", reader=READERS.DETECTOR,
                frame="header:0", score=0.9)
    log.observe(staff, Q.BARLINE_COLUMN, 1, reader=READERS.GEOMETRY,
                frame="page", note="n_cells cut for this staff")
    return log


def build_record() -> dict:
    log = build_log()
    RR.run_stages(log)
    return {"record": log.to_json(), "summary": log.summary(),
            "provenance": {"commit": "fixture", "dirty": False}}


def _sidecar(*actions, reader=READERS.SESSION_TEST) -> dict:
    return {"record": "fixture", "staff": "staff/0/0/0", "reader": reader,
            "actions": list(actions)}


class _Case(unittest.TestCase):
    """Writes the fixture record to a temp dir and runs `rerun` over it."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.result = build_record()
        self.record_path = self.dir / "fixture.record.json"
        self.record_path.write_text(json.dumps(self.result, default=str))
        self.addCleanup(self.tmp.cleanup)

    def run_review(self, sidecar: dict | None, *, tag="arm"):
        side_path = None
        if sidecar is not None:
            side_path = self.dir / f"{tag}.sidecar.json"
            side_path.write_text(json.dumps(sidecar))
        d, arm, ing = RR.rerun(
            str(self.record_path), str(side_path) if side_path else None,
            str(self.dir / f"{tag}.record.json"), staff="staff/0/0/0",
            musicxml_path=str(self.dir / f"{tag}.musicxml"))
        return d, arm, ing

    def standing(self, record: dict, quantity: str, subject: str):
        idx = RR._verdict_index(record["verdicts"])          # noqa: SLF001
        return idx.get((quantity, subject))


# ─────────────────────────────────────────────────────────────────────────────
# 1. THE POSITIVE CONTROL
# ─────────────────────────────────────────────────────────────────────────────

class TestAnEmptySidecarChangesNothing(_Case):
    def test_every_standing_verdict_reproduces_and_the_file_is_identical(self):
        d, arm, ing = self.run_review(None, tag="control")
        self.assertGreater(d.control_same, 20,
                           "the control did not run: a fixture with no "
                           "verdicts reproduces trivially")
        self.assertEqual(d.control_differ, 0)
        self.assertEqual(d.control_absent, 0)
        self.assertEqual(d.control_extra, 0)
        self.assertTrue(d.musicxml_identical)
        self.assertEqual(d.notes_before, d.notes_after)
        self.assertEqual(ing.controls["rows_filed"], 0)

    def test_an_empty_sidecar_is_legal_and_is_not_an_error(self):
        HE.check_sidecar({"actions": []})

    def test_the_control_CAN_fail(self):
        """⚠️ Rule 7: run it in a state where it fails before trusting it
        where it passes. `--break-control` perturbs one replayed GATHER row."""
        d, _arm, _ing = RR.rerun(
            str(self.record_path), None,
            str(self.dir / "red.record.json"), staff="staff/0/0/0",
            break_control=True)
        self.assertGreater(d.control_differ, 0)
        self.assertFalse(d.musicxml_identical)


# ─────────────────────────────────────────────────────────────────────────────
# 2. A DELETED BOX — the CONNECT
# ─────────────────────────────────────────────────────────────────────────────

DELETE = {"id": "act-del", "t": "2026-09-23T12:00:00", "stage": "gather",
          "kind": "delete_box", "glyph": "glyph/0/0/0/0/1",
          "note": "a barline sliver, not a head"}


class TestADeletedBoxIsRefused(_Case):
    def setUp(self) -> None:
        super().setUp()
        self.d, self.arm, self.ing = self.run_review(_sidecar(DELETE),
                                                     tag="del")

    def test_the_notehead_is_refused_with_the_humans_own_reason(self):
        v = self.standing(self.arm["record"], Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                          "glyph/0/0/0/0/1")
        self.assertIsNotNone(v)
        self.assertEqual(v["outcome"], "decided")
        self.assertIs(v["value"], True)
        self.assertEqual(v["reason"], "human_not_a_symbol")

    def test_the_export_counts_it_under_its_own_bucket(self):
        self.assertEqual(
            self.d.census_after["refused"].get(
                "not_a_notehead:human_not_a_symbol"), 1)
        self.assertNotIn("not_a_notehead:human_not_a_symbol",
                         self.d.census_before["refused"])

    def test_one_fewer_note_is_written(self):
        self.assertEqual(self.d.notes_after, self.d.notes_before - 1)

    def test_the_MACHINES_OWN_BOX_ROW_IS_STILL_THERE(self):
        """⚠️ APPEND-ONLY. A human deleting a box is EVIDENCE ABOUT that box,
        not the absence of it — the same distinction the 2.4a refusal draws
        between refusing to write a glyph and deleting it in GATHER."""
        rows = [o for o in self.arm["record"]["observations"]
                if o["subject"] == "glyph/0/0/0/0/1"
                and o["quantity"] == Q.GLYPH_BOX]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reader"], READERS.DETECTOR)

    def test_the_human_row_sits_beside_it_with_its_own_provenance(self):
        rows = [o for o in self.arm["record"]["observations"]
                if o["subject"] == "glyph/0/0/0/0/1"
                and o["quantity"] == Q.HUMAN_BOX_VERDICT]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["value"], "not_a_symbol")
        self.assertEqual(rows[0]["reader"], READERS.SESSION_TEST)
        self.assertEqual(rows[0]["detail"]["review_action"], "act-del")
        self.assertIn("sidecar_sha256", rows[0]["detail"])
        self.assertIsNone(rows[0]["score"],
                          "a human's reading is not a scored guess")

    def test_the_verdict_says_it_WEIGHED_the_human_row(self):
        hit = [h for h in self.d.basis_names_human
               if h["quantity"] == Q.NOTEHEAD_IS_NOT_A_NOTEHEAD
               and h["subject"] == "glyph/0/0/0/0/1"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["how"], "used")


# ─────────────────────────────────────────────────────────────────────────────
# 3. A DISAGREEMENT — filed, never applied
# ─────────────────────────────────────────────────────────────────────────────

class TestADisagreementNeverChangesTheVerdict(_Case):
    def setUp(self) -> None:
        super().setUp()
        self.clef_before = self.standing(self.result["record"], Q.CLEF,
                                         "staff/0/0/0")
        self.assertIsNotNone(self.clef_before,
                             "the fixture must HAVE a clef verdict, or this "
                             "test passes by disagreeing with nothing")
        action = {"id": "act-dis", "t": "2026-09-23T12:02:00",
                  "stage": "adjudicate", "kind": "disagree",
                  "verdict": self.clef_before["id"],
                  "note": "the printed clef is alto"}
        self.d, self.arm, self.ing = self.run_review(_sidecar(action),
                                                     tag="dis")

    def test_the_verdict_is_unchanged(self):
        after = self.standing(self.arm["record"], Q.CLEF, "staff/0/0/0")
        self.assertEqual(after["outcome"], self.clef_before["outcome"])
        self.assertEqual(after["value"], self.clef_before["value"])
        self.assertEqual(after["reason"], self.clef_before["reason"])
        self.assertEqual(self.d.control_differ, 0,
                         "a stance moved a verdict — the one thing 3.4 forbids")

    def test_the_stance_row_is_on_the_verdicts_own_subject(self):
        rows = [o for o in self.arm["record"]["observations"]
                if o["quantity"] == Q.HUMAN_VERDICT_STANCE]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["subject"], "staff/0/0/0")
        self.assertEqual(rows[0]["value"], "disagree")
        self.assertEqual(rows[0]["detail"]["verdict_id"],
                         self.clef_before["id"])

    def test_the_stance_row_carries_WHAT_HE_WAS_SHOWN(self):
        """⚠️ `factsheet.merge`'s `reader_said`, one layer down: a
        disagreement is uninterpretable without what was disagreed WITH."""
        row = [o for o in self.arm["record"]["observations"]
               if o["quantity"] == Q.HUMAN_VERDICT_STANCE][0]
        self.assertEqual(row["detail"]["verdict_quantity"], Q.CLEF)
        self.assertEqual(row["detail"]["verdict_value"],
                         self.clef_before["value"])
        self.assertEqual(row["detail"]["verdict_reason"],
                         self.clef_before["reason"])
        self.assertEqual(row["detail"]["verdict_decider"],
                         self.clef_before["decider"])

    def test_the_stance_reaches_no_stage_and_that_is_REPORTED(self):
        self.assertEqual(len(self.d.human_rows_unread), 1)
        self.assertEqual(self.d.human_rows_unread[0]["action"], "act-dis")

    def test_the_feedback_file_carries_the_verdicts_OWN_reason(self):
        out = self.dir / "fb.json"
        fb = FB.export_feedback(self.arm["record"], self.ing, self.d, str(out))
        self.assertTrue(out.exists())
        dis = fb["disagreements"]
        self.assertEqual(len(dis), 1)
        self.assertEqual(dis[0]["stance"], "disagree")
        self.assertEqual(dis[0]["verdict"], self.clef_before["id"])
        self.assertEqual(dis[0]["reason"], self.clef_before["reason"])
        self.assertEqual(dis[0]["value"], self.clef_before["value"])
        self.assertFalse(dis[0]["verdict_was_changed_by_this"])
        # ⚠️ RE-RESOLVED against the arm by (quantity, subject), NOT by the
        # verdict id — ids are not stable across a re-decision, and resolving
        # by id returned a different, plausible verdict when this was first
        # written (`group_symbol`/`bracket` where the clef was expected).
        self.assertEqual(dis[0]["verdict_now"]["value"],
                         self.clef_before["value"])
        self.assertEqual(dis[0]["verdict_now"]["reason"],
                         self.clef_before["reason"])
        # ⚠️ self-explaining WITHOUT the record: the rule's own declaration.
        self.assertEqual(dis[0]["declares"]["stage"], "ADJUDICATE")
        self.assertIn("composed_from", dis[0]["declares"])
        self.assertIn(dis[0]["reason"], dis[0]["declares"]["reasons"])

    def test_a_stance_on_a_verdict_the_record_does_not_hold_is_REFUSED(self):
        action = {"id": "act-ghost", "kind": "disagree",
                  "stage": "adjudicate", "verdict": "vrd:999999"}
        _d, arm, ing = self.run_review(_sidecar(action), tag="ghost")
        self.assertEqual(ing.controls["actions_refused"], 1)
        self.assertEqual(
            [o for o in arm["record"]["observations"]
             if o["quantity"] == Q.HUMAN_VERDICT_STANCE], [])


# ─────────────────────────────────────────────────────────────────────────────
# 4. AN ADDED BOX — the subject problem, and the honest table
# ─────────────────────────────────────────────────────────────────────────────

#: A head at staff position 0.0 (ON the top line), at a canonical x beyond the
#: three the detector drew — so it cannot be confused with one of them.
_ADD_BOX, _ADD_PAGE = _head_boxes(800.0, 0.0)
ADD = {"id": "act-add", "t": "2026-09-23T12:01:00", "stage": "gather",
       "kind": "add_box", "cell": "cell/0/0/0/0",
       "bbox_page_px": _ADD_PAGE, "category": "noteheadBlackOnLine",
       "note": "a head the detector missed"}

#: ⚠️ THE ASSERTION THE BRIEF ASKS FOR, AND IT IS EXACT. These are the
#: quantities a human box RECEIVES a verdict on today. A change that starts or
#: stops reading a human box fails HERE, visibly, with the quantity named —
#: which is the point: the honest table must not be able to rot.
STAGES_THAT_SEE_A_HUMAN_BOX = {
    Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Q.STEM_DIRECTION,
    Q.NOTEHEAD_IS_A_WHOLE_REST, Q.DURATION, Q.PITCH,
}


class TestAnAddedBoxBecomesASubject(_Case):
    def setUp(self) -> None:
        super().setUp()
        self.d, self.arm, self.ing = self.run_review(_sidecar(ADD), tag="add")
        self.sub = f"glyph/0/0/0/0/{HE.HUMAN_GLYPH_BASE}"

    def test_the_human_box_is_filed_at_the_human_offset_ordinal(self):
        rows = [o for o in self.arm["record"]["observations"]
                if o["subject"] == self.sub]
        got = {o["quantity"] for o in rows}
        self.assertEqual(got, {Q.GLYPH_BOX, Q.NOTEHEAD_CLASS,
                               Q.NOTEHEAD_STAFF_POSITION})
        self.assertTrue(all(o["reader"] == READERS.SESSION_TEST for o in rows))

    def test_the_offset_base_cannot_collide_with_any_gather_reader(self):
        """⚠️ DERIVED FROM `gather`'s OWN ATTRIBUTES, never from its text. A
        collision would not raise; it would silently merge a human's box and
        another reader's row into one subject."""
        theirs = {name: getattr(G, name) for name in dir(G)
                  if name.endswith("_GLYPH_BASE")}
        self.assertGreaterEqual(len(theirs), 3,
                                "no gather bases found — this test would pass "
                                "by comparing against nothing")
        for name, base in theirs.items():
            self.assertNotEqual(base, HE.HUMAN_GLYPH_BASE, name)
            self.assertLess(base, HE.HUMAN_GLYPH_BASE,
                            f"{name} is at or past the human base")

    def test_the_canonical_box_round_trips_the_page_box_it_was_drawn_from(self):
        row = [o for o in self.arm["record"]["observations"]
               if o["subject"] == self.sub and o["quantity"] == Q.GLYPH_BOX][0]
        _name, x_c, y_c, w_c, h_c = row["value"]
        for got, want in zip((x_c, y_c, w_c, h_c), _ADD_BOX):
            self.assertAlmostEqual(got, want, places=6)
        self.assertEqual(row["detail"]["bbox_page_px"], list(_ADD_PAGE))

    def test_the_staff_position_is_recovered_from_the_cells_own_grid(self):
        row = [o for o in self.arm["record"]["observations"]
               if o["subject"] == self.sub
               and o["quantity"] == Q.NOTEHEAD_STAFF_POSITION][0]
        self.assertAlmostEqual(row["value"], 0.0, places=6)
        self.assertGreaterEqual(row["detail"]["grid_anchors"], 2)
        self.assertEqual(row["basis"][:1],
                         [o["id"] for o in self.arm["record"]["observations"]
                          if o["subject"] == self.sub
                          and o["quantity"] == Q.GLYPH_BOX])

    def test_EXACTLY_these_quantities_decide_about_a_human_box(self):
        got = {v["quantity"] for v in self.arm["record"]["verdicts"]
               if v["subject"] == self.sub}
        self.assertEqual(got, STAGES_THAT_SEE_A_HUMAN_BOX)

    def test_the_pitch_is_restated_in_EVALUATE_from_the_clef(self):
        v = self.standing(self.arm["record"], Q.PITCH, self.sub)
        self.assertEqual(v["outcome"], "decided")
        self.assertEqual(v["value"], "F5")        # position 0.0 in treble
        hit = [h for h in self.d.basis_names_human
               if h["quantity"] == Q.PITCH and h["subject"] == self.sub]
        self.assertEqual([h["stage"] for h in hit], ["EVALUATE"])

    def test_what_a_human_box_CANNOT_have_is_named_rather_than_invented(self):
        got = {o["quantity"] for o in self.arm["record"]["observations"]
               if o["subject"] == self.sub}
        for q in HE.HUMAN_BOX_ABSENT:
            self.assertNotIn(q, got)
        absent = [a for a in self.ing.actions if a.id == "act-add"][0].absent
        for q, why in HE.HUMAN_BOX_ABSENT.items():
            self.assertEqual(absent[q], why)

    def test_a_human_boxs_DURATION_is_read_from_the_HEAD_ALONE(self):
        """⚠️⚠️ NOT "no duration" — an ANSWER, which is worse.

        Nothing gives a human box a beam, a flag or an aug dot (they are read
        off the cell RASTER), so `adjudicate_duration` decides from the
        notehead class alone and still reports reason `head_and_marks` with
        the marks half contributing nothing. Right for a quarter note, wrong
        for every beamed or flagged one, and nothing on the row says which.
        Asserted so the day a GATHER function re-reads the raster around a
        human box, this goes red and somebody re-reads this note.
        """
        v = self.standing(self.arm["record"], Q.DURATION, self.sub)
        self.assertEqual(v["outcome"], "decided")
        self.assertEqual(v["value"]["written"], 1.0)
        self.assertEqual(v["value"]["beam_levels"], 0)
        self.assertEqual(v["reason"], "head_and_marks")
        for q in (Q.BEAM_STROKE, Q.FLAG, Q.AUG_DOT):
            self.assertEqual(
                [o for o in self.arm["record"]["observations"]
                 if o["subject"] == self.sub and o["quantity"] == q], [])

    def test_one_more_note_reaches_the_file(self):
        self.assertEqual(self.d.notes_after, self.d.notes_before + 1)
        pitches = [p.text for p in
                   ET.fromstring((self.dir / "add.musicxml").read_text())
                   .findall(".//note/pitch/step")]
        self.assertIn("F", pitches)

    def test_an_add_box_with_no_resolvable_cell_is_REFUSED_and_named(self):
        """⚠️ Deciding which cell a page-pixel box falls in is the padded-cell
        contest, not a bounding test. The tool refuses rather than guesses."""
        action = dict(ADD, id="act-nocell")
        action.pop("cell")
        _d, arm, ing = self.run_review(_sidecar(action), tag="nocell")
        self.assertEqual(ing.controls["actions_refused"], 1)
        self.assertIn("no cell", ing.actions[0].refused)
        self.assertEqual(
            [o for o in arm["record"]["observations"]
             if o["subject"].endswith(str(HE.HUMAN_GLYPH_BASE))], [])


# ─────────────────────────────────────────────────────────────────────────────
# 4b. A REDRAWN BOX — both halves, and the half that reaches nothing
# ─────────────────────────────────────────────────────────────────────────────

class TestARedrawnBoxFilesBothHalves(_Case):
    def setUp(self) -> None:
        super().setUp()
        action = dict(ADD, id="act-redraw", kind="redraw_box",
                      glyph="glyph/0/0/0/0/2",
                      note="this head is drawn a space too low")
        self.d, self.arm, self.ing = self.run_review(_sidecar(action),
                                                     tag="redraw")
        self.sub = f"glyph/0/0/0/0/{HE.HUMAN_GLYPH_BASE}"

    def test_the_new_box_is_filed_at_the_human_ordinal(self):
        got = {o["quantity"] for o in self.arm["record"]["observations"]
               if o["subject"] == self.sub}
        self.assertIn(Q.GLYPH_BOX, got)
        self.assertIn(Q.NOTEHEAD_STAFF_POSITION, got)

    def test_the_original_is_marked_REDRAWN_and_not_not_a_symbol(self):
        rows = [o for o in self.arm["record"]["observations"]
                if o["subject"] == "glyph/0/0/0/0/2"
                and o["quantity"] == Q.HUMAN_BOX_VERDICT]
        self.assertEqual([r["value"] for r in rows], ["redrawn"])
        self.assertEqual(rows[0]["detail"]["replaced_by"], self.sub)

    def test_REDRAWN_IS_HANDED_TO_A_DECISION_AND_NEVER_WEIGHED(self):
        """⚠️ A redraw says the box is in the wrong PLACE — a different claim
        from *not a symbol*, and what to do with the machine's own box is a
        decision nobody has taken. It must NOT be quietly read as a refusal.

        ⚠️⚠️ AND THE HONEST ANSWER IS NOT "nothing read it". Because
        `notehead_is_not_a_notehead` DECLARES `Q.HUMAN_BOX_VERDICT`, the
        harness hands it every such row on that glyph, so a `redrawn` row
        lands in `considered` and `basis` — and `_human_not_a_symbol` then
        declines it. `used` is the only field that separates *offered* from
        *weighed*, which is exactly why the diff reports the three apart. A
        test asserting `human_rows_unread` would have been WRONG and would
        have looked right.
        """
        v = self.standing(self.arm["record"], Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                          "glyph/0/0/0/0/2")
        self.assertIs(v["value"], False)
        self.assertEqual(v["reason"], "notehead")
        redrawn = {o["id"] for o in self.arm["record"]["observations"]
                   if o["quantity"] == Q.HUMAN_BOX_VERDICT
                   and o["value"] == "redrawn"}
        self.assertEqual(len(redrawn), 1)
        hits = [h for h in self.d.basis_names_human
                if set(h["in_used"]) & redrawn]
        self.assertEqual(hits, [], "a `redrawn` row was WEIGHED by a decision "
                                   "— that is a wiring change, not a test fix")
        offered = [h for h in self.d.basis_names_human
                   if any(r.split("->")[-1] in redrawn
                          for r in h["human_rows"])]
        self.assertTrue(offered, "the row reached no decision at all, so this "
                                 "test proves nothing about `used`")
        self.assertTrue(all(h["how"] != "used" for h in offered))

    def test_the_machines_box_still_stands_and_is_still_written(self):
        rows = [o for o in self.arm["record"]["observations"]
                if o["subject"] == "glyph/0/0/0/0/2"
                and o["quantity"] == Q.GLYPH_BOX]
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.d.notes_after, self.d.notes_before + 1)


# ─────────────────────────────────────────────────────────────────────────────
# 5. THE FRAME RECOVERY, AND ITS OWN CONTROL
# ─────────────────────────────────────────────────────────────────────────────

class TestTheFrameRecoveryCanFail(unittest.TestCase):
    def setUp(self) -> None:
        self.rec = build_record()["record"]
        self.cell = R.cell(0, 0, 0, 0)

    def rows(self):
        return HE._glyph_rows_of_cell(self.rec, self.cell)   # noqa: SLF001

    def test_it_recovers_the_frame_the_fixture_was_built_with(self):
        frame, why = HE.recover_cell_frame(self.rows())
        self.assertIsNone(why)
        self.assertAlmostEqual(frame.upscale, UPSCALE, places=9)
        self.assertAlmostEqual(frame.x0, CELL_ORIGIN[0], places=6)
        self.assertAlmostEqual(frame.y0, CELL_ORIGIN[1], places=6)
        self.assertEqual(frame.anchors, 3)

    def test_anchors_that_disagree_REFUSE_rather_than_average(self):
        rows = copy.deepcopy(self.rows())
        bb = list(rows[0]["detail"]["bbox_page_px"])
        rows[0]["detail"]["bbox_page_px"] = [bb[0] + 40, bb[1] + 40,
                                             bb[2] + 40, bb[3] + 40]
        frame, why = HE.recover_cell_frame(rows)
        self.assertIsNone(frame)
        self.assertIn("disagree", why)

    def test_a_cell_with_no_page_frame_at_all_REFUSES(self):
        rows = copy.deepcopy(self.rows())
        for r in rows:
            r["detail"].pop("bbox_page_px")
        frame, why = HE.recover_cell_frame(rows)
        self.assertIsNone(frame)
        self.assertIn("no anchor", why)

    def test_the_grid_refuses_when_the_cell_has_no_unit(self):
        rec = copy.deepcopy(self.rec)
        rec["observations"] = [o for o in rec["observations"]
                               if o["quantity"] != Q.CELL_STAFF_SPACE]
        grid, why = HE.recover_cell_grid(
            rec, self.cell, HE._glyph_rows_of_cell(rec, self.cell))  # noqa
        self.assertIsNone(grid)
        self.assertIn("no unit", why)


# ─────────────────────────────────────────────────────────────────────────────
# 6. THE SIDECAR CONTRACT, AND THE THINGS THAT MUST NOT HAPPEN
# ─────────────────────────────────────────────────────────────────────────────

class TestTheSidecarContract(unittest.TestCase):
    def setUp(self) -> None:
        self.rec = build_record()["record"]

    def test_a_verb_this_module_was_not_taught_is_REFUSED_not_dropped(self):
        with self.assertRaises(HE.SidecarError):
            HE.check_sidecar({"actions": [{"id": "a", "kind": "move_box"}]})

    def test_two_actions_may_not_share_an_id(self):
        with self.assertRaises(HE.SidecarError):
            HE.check_sidecar({"actions": [
                {"id": "a", "kind": "delete_box", "glyph": "glyph/0/0/0/0/0"},
                {"id": "a", "kind": "delete_box", "glyph": "glyph/0/0/0/0/1"}]})

    def test_a_reader_outside_the_closed_vocabulary_is_REFUSED(self):
        sc = _sidecar(DELETE, reader="somebody-else")
        with self.assertRaises(HE.SidecarError):
            HE.ingest(self.rec, sc)

    def test_ingest_NEVER_mutates_its_input(self):
        before = json.dumps(self.rec, sort_keys=True, default=str)
        HE.ingest(self.rec, _sidecar(DELETE, ADD))
        self.assertEqual(json.dumps(self.rec, sort_keys=True, default=str),
                         before)

    def test_the_amended_record_names_the_parent_and_the_sidecar(self):
        sc = _sidecar(DELETE)
        ing = HE.ingest(self.rec, sc, sidecar_path="/x/side.json",
                        parent_path="/x/parent.json", parent_md5="deadbeef")
        prov = ing.controls["provenance"]
        self.assertEqual(prov["parent"]["md5"], "deadbeef")
        self.assertEqual(prov["parent"]["record"], "/x/parent.json")
        self.assertEqual(prov["sidecar"]["sha256"], HE.sidecar_digest(sc))
        self.assertEqual(prov["sidecar"]["actions"], 1)

    def test_an_unhashed_parent_is_WARNED_not_silently_accepted(self):
        ing = HE.ingest(self.rec, _sidecar(DELETE))
        self.assertIn("warning", ing.controls["provenance"]["parent"])

    def test_one_pixel_changes_the_sidecar_digest(self):
        a = _sidecar(ADD)
        b = json.loads(json.dumps(a))
        b["actions"][0]["bbox_page_px"][0] += 1
        self.assertNotEqual(HE.sidecar_digest(a), HE.sidecar_digest(b))

    def test_key_order_and_whitespace_do_NOT(self):
        a = _sidecar(ADD)
        b = json.loads(json.dumps(a, sort_keys=True, indent=4))
        self.assertEqual(HE.sidecar_digest(a), HE.sidecar_digest(b))


class TestTheAmendedRecordMayNotEatItsParent(_Case):
    def test_writing_over_the_parent_is_refused(self):
        with self.assertRaises(ValueError):
            RR.rerun(str(self.record_path), None, str(self.record_path))


# ─────────────────────────────────────────────────────────────────────────────
# 7. THE DERIVED TABLES — they must not be able to go vacuous
# ─────────────────────────────────────────────────────────────────────────────

class TestTheDerivationsAreNotVacuous(unittest.TestCase):
    def test_the_EVALUATE_decider_set_is_derived_and_non_empty(self):
        """⚠️ The first cut read a `name` attribute `evaluate.Rule` does not
        have, so every consequence reported as ADJUDICATE."""
        self.assertIn("restate_pitch", RR._EVALUATE_DECIDERS)   # noqa: SLF001
        self.assertGreaterEqual(len(RR._EVALUATE_DECIDERS), 5)  # noqa: SLF001

    def test_visibility_names_a_domain_and_an_absence(self):
        vis = HE.visibility()
        self.assertIn("adjudicate_notehead_is_not_a_notehead",
                      vis["adjudicate_domain"])
        self.assertIn(Q.GLYPH_CONF, vis["absent"])
        self.assertTrue(vis["adjudicate_wants"])

    def test_the_convention_join_is_real_and_says_it_is_COARSE(self):
        """⚠️ `conventions.py`'s `code_paths` names FILES, so this join is
        per-MODULE and every decision in `rhythm.py` gets that file's entries.
        Reported as `granularity: "file"` rather than presented as a
        per-decision claim — and a decision with no entry comes back EMPTY,
        which is the gap `staged.check`'s `conventions` part already owns."""
        got = FB._decider_declaration("adjudicate_duration")["conventions"]
        self.assertTrue(got, "the join returned nothing — it would look like "
                             "'this decision claims no convention' for every "
                             "decision in the tree")
        self.assertTrue(all(c["granularity"] == "file" for c in got))
        self.assertTrue(all(c["id"] and c["says"] for c in got))
        self.assertEqual(
            FB._decider_declaration("adjudicate_clef")["conventions"], [],
            "a decision the registry does not name must come back EMPTY, not "
            "with somebody else's convention")

    def test_the_human_quantities_declare_a_claim_kind(self):
        from tools.omr.staged.record import claim_of
        self.assertEqual(claim_of(Q.HUMAN_BOX_VERDICT), "identification")
        self.assertEqual(claim_of(Q.HUMAN_VERDICT_STANCE), "interpretation")


if __name__ == "__main__":
    unittest.main()
