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


# ═════════════════════════════════════════════════════════════════════════
# 7. ROADMAP 3.4c — THE LABELS. Sean, 2026-09-23, after his first minutes on
#    the page: *"it works now but the UI is awkward — I need to be able to
#    select a box and re-label it"*, and *"and to label boxes as nothing or
#    belongs to another staff etc."*
#
# ⚠️⚠️ RUN RED FIRST, and the RED that matters is NOT "the verb did not
# exist". With the whole ingest in place and ONLY the two CONNECTs neutered —
# `notehead_precision._human_not_a_symbol`'s `is_a`/`duplicate_of` arms
# returning None, and `ownership._human_owner` returning None — this file was
# run again and the failures were exactly the four consequence tests
# (`test_the_head_is_refused_...`, `test_the_refusal_names_WHAT_HE_SAID`,
# `test_a_duplicate_is_refused_...`, `test_the_owner_is_the_HUMANS`), with
# every ingest test still green. So these test the CONNECT, not the filing:
# the rows are filed either way, which is the distinction this whole package
# is built to keep visible.
# ═════════════════════════════════════════════════════════════════════════

def _add_second_cell(log):
    """Cell 1 of the fixture staff: a unit, a box and one anchored notehead.

    ⚠️ EXACTLY WHAT THE FRAME RECOVERY NEEDS AND NOTHING MORE — one
    `Q.CELL_STAFF_SPACE`, one `Q.CELL_BOX` and ONE anchor box carrying both a
    canonical rectangle and `detail.bbox_page_px`. The anchor is deliberately
    NOT a notehead: a fourth head in a cell the exporter's partition does not
    know about raises `export.Unbalanced` (measured — it did), and the
    cell-0 rule this class tests is reached before any grid is recovered, so
    the extra head would have bought nothing.
    """
    cell = R.cell(0, 0, 0, 1)
    log.observe(cell, Q.CELL_STAFF_SPACE, SPACING, reader=READERS.GEOMETRY,
                frame="cell:1", lines=5)
    log.observe(cell, Q.CELL_BOX,
                [CELL_ORIGIN[0] + 400, CELL_ORIGIN[1],
                 CELL_ORIGIN[0] + 800, CELL_ORIGIN[1] + 400],
                reader=READERS.GEOMETRY, frame="cell:1")
    g = R.glyph(0, 0, 0, 1, 0)
    (bx, by, bw, bh), page = _head_boxes(1600.0, 4.0)
    log.observe(g, Q.GLYPH_BOX, ("accidentalSharp", bx, by, bw, bh),
                reader=READERS.DETECTOR, frame="cell:1", score=0.9,
                category="accidental", bbox_page_px=page)
    return log


def _relabel(category, glyph="glyph/0/0/0/0/1", **kw):
    return {"id": "act-rl", "t": "2026-09-23T12:02:00", "stage": "gather",
            "kind": "relabel_box", "glyph": glyph, "category": category, **kw}


class TestARelabelOutsideTheNoteheadFamily(_Case):
    """`noteheadBlackOnLine` -> `clefCAlto`: Sean's own first case, the two
    heads the detector drew on the Viola staff's alto clef."""

    def setUp(self) -> None:
        super().setUp()
        self.d, self.arm, self.ing = self.run_review(
            _sidecar(_relabel("clefCAlto", note="that is the alto clef")),
            tag="relabel-clef")
        self.sub = f"glyph/0/0/0/0/{HE.HUMAN_GLYPH_BASE}"

    def test_the_head_is_refused_with_the_humans_own_reason(self):
        v = self.standing(self.arm["record"], Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                          "glyph/0/0/0/0/1")
        self.assertIs(v["value"], True)
        self.assertEqual(v["reason"], "human_not_a_symbol")

    def test_the_refusal_names_WHAT_HE_SAID_not_merely_THAT_he_refused(self):
        """⚠️ A refusal recording only *a human refused this* cannot be turned
        into a fix. One recording *a human says this is a clefCAlto* can, and
        that is the whole unit of roadmap 3.4."""
        v = self.standing(self.arm["record"], Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                          "glyph/0/0/0/0/1")
        self.assertEqual(v["detail"]["human_says"], "is_a:clefCAlto")
        self.assertEqual(v["detail"]["human_reader"], READERS.SESSION_TEST)

    def test_the_is_a_row_sits_on_the_MACHINES_own_subject(self):
        rows = [o for o in self.arm["record"]["observations"]
                if o["subject"] == "glyph/0/0/0/0/1"
                and o["quantity"] == Q.HUMAN_BOX_VERDICT]
        self.assertEqual([r["value"] for r in rows], ["is_a:clefCAlto"])
        self.assertEqual(rows[0]["detail"]["filed_as"], self.sub)
        self.assertEqual(rows[0]["detail"]["machine_called_it"],
                         "noteheadBlackOnLine")
        # the machine's own box row is untouched, as for every other label
        boxes = [o for o in self.arm["record"]["observations"]
                 if o["subject"] == "glyph/0/0/0/0/1"
                 and o["quantity"] == Q.GLYPH_BOX]
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0]["reader"], READERS.DETECTOR)

    def test_the_new_class_becomes_a_human_BOX_of_its_own(self):
        got = {o["quantity"] for o in self.arm["record"]["observations"]
               if o["subject"] == self.sub}
        self.assertIn(Q.GLYPH_BOX, got)
        self.assertNotIn(Q.NOTEHEAD_CLASS, got)
        row = [o for o in self.arm["record"]["observations"]
               if o["subject"] == self.sub and o["quantity"] == Q.GLYPH_BOX][0]
        self.assertEqual(row["value"][0], "clefCAlto")
        self.assertEqual(row["detail"]["relabel_of"], "glyph/0/0/0/0/1")
        self.assertEqual(row["detail"]["bbox_page_px"],
                         _page_box_of(self.result["record"],
                                      "glyph/0/0/0/0/1"),
                         "the relabel moved the box — he said THIS box is a "
                         "clef, not that a clef is somewhere near here")

    def test_a_human_clefC_box_in_CELL_0_reaches_the_clef_decision(self):
        """⚠️⚠️ THE CONNECT, AND IT IS A CONNECT BECAUSE IT FILES THE SAME TWO
        ROWS `gather_clefs` FILES: `Q.CLEF_GLYPH` on the STAFF and
        `Q.CLEF_POSITION` beside it from the cell's own grid. Nothing is
        invented — the position is the same arithmetic a notehead's is.
        """
        rows = [o for o in self.arm["record"]["observations"]
                if o["subject"] == "staff/0/0/0"
                and o["reader"] == READERS.SESSION_TEST]
        self.assertEqual({o["quantity"] for o in rows},
                         {Q.CLEF_GLYPH, Q.CLEF_POSITION})
        glyph_row = [o for o in rows if o["quantity"] == Q.CLEF_GLYPH][0]
        self.assertEqual(glyph_row["value"], "clefCAlto")
        self.assertIsNone(glyph_row["score"],
                          "a person produced no softmax; a number here would "
                          "be a fallback (CLAUDE.md rule 8)")
        hit = [h for h in self.d.basis_names_human
               if h["quantity"] == Q.CLEF and h["subject"] == "staff/0/0/0"]
        self.assertTrue(hit, "the human's clef row reached no clef verdict at "
                             "all — that is a wiring finding, not a test fix")

    def test_THE_HUMANS_CLEF_ENTERS_AS_THE_WEAKEST_WITNESS_AND_IT_IS_SAID(self):
        """⚠️⚠️ THE HONEST HALF, ASSERTED SO IT CANNOT ROT. `clef.
        _detector_terms` weights by `row.score`, reading None as 0.0 and
        therefore as `W_DETECTOR_LOW` — so a human who read the plate is
        weighted BELOW a 0.9 detection of the same staff. That is wrong, it is
        not repaired here (repairing it is a change to `clef.py`'s weighting
        with its own measurement), and the row says so in its own detail.
        """
        glyph_row = [o for o in self.arm["record"]["observations"]
                     if o["subject"] == "staff/0/0/0"
                     and o["quantity"] == Q.CLEF_GLYPH
                     and o["reader"] == READERS.SESSION_TEST][0]
        self.assertIn("W_DETECTOR_LOW", glyph_row["detail"]["score_is_None"])

    def test_a_clef_class_box_OUTSIDE_cell_0_files_no_clef_row(self):
        """⚠️ `gather_clefs` reads cell 0 only — *a clef is read at the head
        of the staff*. A mid-staff clef change is a reading GATHER does not
        make, and this module may not invent one.

        ⚠️ THE FIXTURE GROWS A SECOND CELL FOR THIS, because a clef-class box
        in a cell with no rows is refused for the FRAME, one step earlier —
        which would have made this test pass while proving nothing about the
        cell-0 rule."""
        log = build_log()
        _add_second_cell(log)
        RR.run_stages(log)
        path = self.dir / "twocell.record.json"
        path.write_text(json.dumps(
            {"record": log.to_json(), "summary": log.summary(),
             "provenance": {"commit": "fixture", "dirty": False}}, default=str))
        _box, page = _head_boxes(1800.0, 0.0)
        action = {"id": "act-midclef", "stage": "gather", "kind": "add_box",
                  "cell": "cell/0/0/0/1", "bbox_page_px": page,
                  "category": "clefCAlto"}
        side = self.dir / "midclef.sidecar.json"
        side.write_text(json.dumps(_sidecar(action)))
        _d, arm, ing = RR.rerun(str(path), str(side),
                                str(self.dir / "midclef.record.json"),
                                staff="staff/0/0/0")
        self.assertIsNone(ing.actions[0].refused,
                          "refused before it reached the cell-0 rule, so this "
                          "test would prove nothing")
        self.assertEqual(
            [o for o in arm["record"]["observations"]
             if o["quantity"] == Q.CLEF_GLYPH
             and o["reader"] == READERS.SESSION_TEST], [])
        self.assertIn("cell 0", ing.actions[0].absent[Q.CLEF_GLYPH])


class TestARelabelINSIDETheNoteheadFamily(_Case):
    """black -> half. ⚠️ NOT a refusal: he disagrees about WHICH head, not
    about whether there is one."""

    def setUp(self) -> None:
        super().setUp()
        self.d, self.arm, self.ing = self.run_review(
            _sidecar(_relabel("noteheadHalfOnLine",
                              note="that is a half, not a quarter")),
            tag="relabel-half")
        self.sub = f"glyph/0/0/0/0/{HE.HUMAN_GLYPH_BASE}"

    def test_the_machines_head_is_NOT_refused(self):
        v = self.standing(self.arm["record"], Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                          "glyph/0/0/0/0/1")
        self.assertIs(v["value"], False)
        self.assertEqual(v["reason"], "notehead")
        self.assertNotIn("human_says", v["detail"])

    def test_EXACTLY_these_stages_see_the_relabelled_box(self):
        """⚠️ THE EXACT SET, as for an added box. A change that starts or
        stops reading a relabelled box fails HERE with the quantity named."""
        got = {v["quantity"] for v in self.arm["record"]["verdicts"]
               if v["subject"] == self.sub}
        self.assertEqual(got, STAGES_THAT_SEE_A_HUMAN_BOX)

    def test_the_consumer_that_sees_the_NEW_class_is_adjudicate_duration(self):
        """⚠️⚠️ AND IT SEES IT ON THE HUMAN BOX'S OWN SUBJECT, NOT ON THE
        MACHINE'S. `rhythm._head_class` is `max(rows, key=score or 0.0)`, so a
        human `Q.NOTEHEAD_CLASS` row filed on the MACHINE's glyph (score None
        -> 0.0) would LOSE to the detector's 0.9 — while still landing in that
        verdict's `used`, because `adjudicate_duration` puts every
        `Q.NOTEHEAD_CLASS` row it can see there. It would read as WEIGHED in
        the feedback file and change nothing. So the relabel does not file
        one; the new class arrives as a box of its own and `duration` decides
        on that subject. Asserted here so the day `_head_class` stops reading
        by score, this goes red and somebody re-reads this note.
        """
        v = self.standing(self.arm["record"], Q.DURATION, self.sub)
        self.assertEqual(v["value"]["written"], 2.0)
        self.assertEqual(
            self.standing(self.arm["record"], Q.DURATION,
                          "glyph/0/0/0/0/1")["value"]["written"], 1.0,
            "the machine's own head was re-decided — nothing here may mutate "
            "a machine row")
        self.assertEqual(
            [o for o in self.arm["record"]["observations"]
             if o["subject"] == "glyph/0/0/0/0/1"
             and o["quantity"] == Q.NOTEHEAD_CLASS
             and o["reader"] == READERS.SESSION_TEST], [])

    def test_AND_THE_PRICE_IS_TWO_NOTES_WHERE_THE_PLATE_HAS_ONE(self):
        """⚠️⚠️ THE FINDING, ASSERTED RATHER THAN BURIED. An in-family relabel
        adds a head and refuses none, so the bar now carries the machine's
        quarter AND the human's half. Closing it needs either a rule that
        `is_a:<other notehead>` supersedes the head class, or one that refuses
        the machine's box — and the second is `redrawn`'s open question, which
        nobody has decided. Out of 3.4c's scope, IN 3.4c's report."""
        self.assertEqual(self.d.notes_after, self.d.notes_before + 1)


class TestADuplicateIsOnePieceOfInk(_Case):
    def setUp(self) -> None:
        super().setUp()
        self.d, self.arm, self.ing = self.run_review(_sidecar(
            {"id": "act-dup", "t": "2026-09-23T12:03:00", "stage": "gather",
             "kind": "dup_box", "glyph": "glyph/0/0/0/0/1",
             "of": "glyph/0/0/0/0/0", "note": "the same head, boxed twice"}),
            tag="dup")

    def test_a_duplicate_is_refused_and_names_its_twin(self):
        v = self.standing(self.arm["record"], Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                          "glyph/0/0/0/0/1")
        self.assertIs(v["value"], True)
        self.assertEqual(v["reason"], "human_not_a_symbol")
        self.assertEqual(v["detail"]["human_says"],
                         "duplicate_of:glyph/0/0/0/0/0")

    def test_the_twin_is_untouched_and_one_fewer_note_is_written(self):
        self.assertIs(
            self.standing(self.arm["record"], Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                          "glyph/0/0/0/0/0")["value"], False)
        self.assertEqual(self.d.notes_after, self.d.notes_before - 1)

    def test_a_duplicate_OF_a_box_the_record_does_not_hold_is_REFUSED(self):
        _d, arm, ing = self.run_review(_sidecar(
            {"id": "act-dup2", "stage": "gather", "kind": "dup_box",
             "glyph": "glyph/0/0/0/0/1", "of": "glyph/9/9/9/9/9"}),
            tag="dup-missing")
        self.assertEqual(ing.controls["actions_refused"], 1)
        self.assertIn("holds no rows", ing.actions[0].refused)


class TestICantTellIsAnABSTENTION(_Case):
    def setUp(self) -> None:
        super().setUp()
        self.d, self.arm, self.ing = self.run_review(_sidecar(
            {"id": "act-unsure", "t": "2026-09-23T12:04:00", "stage": "gather",
             "kind": "unsure_box", "glyph": "glyph/0/0/0/0/1",
             "note": "the plate is broken here; I cannot read it"}),
            tag="unsure")

    def test_it_is_an_abstention_row_with_the_humans_own_reason(self):
        """⚠️ A HUMAN MAY DECLINE, AND THE RECORD MUST BE ABLE TO SAY SO. A
        review tool that could only file his ANSWERS would quietly select for
        the boxes he was sure about, and the places where the PLATE is
        ambiguous would never reach the record at all."""
        rows = [a for a in self.arm["record"]["abstentions"]
                if a["reader"] == READERS.SESSION_TEST]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quantity"], Q.HUMAN_BOX_VERDICT)
        self.assertEqual(rows[0]["reason"], R.ABSTAIN.HUMAN_UNSURE)
        self.assertEqual(rows[0]["subject"], "glyph/0/0/0/0/1")
        self.assertEqual(
            [o for o in self.arm["record"]["observations"]
             if o["reader"] == READERS.SESSION_TEST], [],
            "an abstention was also filed as an observation — that is the "
            "READ/DECLINED collapse the record exists to prevent")

    def test_it_changes_NOTHING_and_that_is_the_design(self):
        self.assertEqual(self.d.notes_after, self.d.notes_before)
        v = self.standing(self.arm["record"], Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                          "glyph/0/0/0/0/1")
        self.assertIs(v["value"], False)

    def test_the_feedback_file_reports_it_as_a_place_the_PRINT_is_ambiguous(self):
        out = FB.export_feedback(
            self.arm["record"], self.ing, self.d,
            str(self.dir / "unsure.feedback.json"))
        self.assertEqual(out["counts"]["actions"], 1)
        entry = out["actions"]["act-unsure"]
        self.assertEqual(entry["action"]["detail"]["row_kind"], "abstention")
        self.assertTrue(entry["human_rows"][0]["reason"]
                        == R.ABSTAIN.HUMAN_UNSURE)


# ─────────────────────────────────────────────────────────────────────────────
# 7b. `belongs to another staff` — the one label that DECIDES rather than
#     refuses, and the only edit 3.4c makes to `ownership.py`.
# ─────────────────────────────────────────────────────────────────────────────

def _contested_record() -> dict:
    """The fixture, plus ONE cross-staff contest on `glyph/0/0/0/0/1`.

    ⚠️ `adjudicate_glyph_owner`'s domain is `subjects_from=
    Q.GLYPH_BAND_DISTANCE` — the CONTESTED population. A glyph nobody disputes
    gets no verdict at all, so a human owner row on one reaches nothing; that
    is asserted in its own test below rather than left as a surprise.
    """
    log = build_log()
    g = R.glyph(0, 0, 0, 0, 1)
    log.observe(g, Q.GLYPH_BAND_DISTANCE, 0.4, reader=READERS.GEOMETRY,
                frame="page", candidate="staff/0/0/1", own=False,
                position_in_candidate=2.0)
    log.observe(g, Q.GLYPH_BAND_DISTANCE, 3.1, reader=READERS.GEOMETRY,
                frame="page", candidate="staff/0/0/0", own=True,
                position_in_candidate=8.0)
    RR.run_stages(log)
    return {"record": log.to_json(), "summary": log.summary(),
            "provenance": {"commit": "fixture", "dirty": False}}


class TestBelongsToAnotherStaff(_Case):
    def setUp(self) -> None:
        super().setUp()
        self.result = _contested_record()
        self.record_path.write_text(json.dumps(self.result, default=str))

    def test_THE_POSITIVE_CONTROL_no_human_row_leaves_the_contest_alone(self):
        """⚠️ RULE 7. Without this, the test below passes for a
        `_human_owner` that fires on every glyph — and a decision that always
        returns the same answer looks exactly like one that works."""
        d, arm, _ing = self.run_review(None, tag="own-control")
        v = self.standing(arm["record"], Q.GLYPH_OWNER, "glyph/0/0/0/0/1")
        self.assertEqual(v["value"], "staff/0/0/1")
        self.assertEqual(v["reason"], "distance")
        self.assertEqual(d.control_differ, 0)

    def test_the_owner_is_the_HUMANS_and_the_reason_names_him(self):
        d, arm, _ing = self.run_review(_sidecar(
            {"id": "act-own", "t": "2026-09-23T12:05:00", "stage": "gather",
             "kind": "own_box", "glyph": "glyph/0/0/0/0/1",
             "staff": "staff/0/0/0", "note": "that is the flute's note"}),
            tag="own")
        v = self.standing(arm["record"], Q.GLYPH_OWNER, "glyph/0/0/0/0/1")
        self.assertEqual(v["value"], "staff/0/0/0")
        self.assertEqual(v["reason"], "human_owner")
        self.assertEqual(v["detail"]["human_reader"], READERS.SESSION_TEST)
        self.assertEqual(v["detail"]["human_says"], "owner:staff/0/0/0")
        hit = [h for h in d.basis_names_human
               if h["quantity"] == Q.GLYPH_OWNER]
        self.assertEqual([h["how"] for h in hit], ["used"],
                         "the owner row was handed to the decision and not "
                         "weighed — that is a wiring finding")

    def test_owning_it_BACK_recovers_the_note_the_contest_had_dropped(self):
        """⚠️ THE FIXTURE'S CONTROL ALREADY LOSES THIS HEAD: distance awards
        it to `staff/0/0/1`, so EXPORT refuses it here under
        `owned_by_another_staff` and 2 of 3 heads are written. The human
        owning it back is the only thing in the tree that puts it in the
        file."""
        d, arm, _ing = self.run_review(_sidecar(
            {"id": "act-own1", "stage": "gather", "kind": "own_box",
             "glyph": "glyph/0/0/0/0/1", "staff": "staff/0/0/0"}), tag="own1")
        self.assertEqual((d.notes_before, d.notes_after), (2, 3))

    def test_it_records_whether_the_named_staff_HOLDS_A_TWIN(self):
        """⚠️⚠️ CLAUDE.md §10: a resolved contest DROPS the loser and NEVER
        relocates it. So awarding a glyph to a staff whose own detector never
        boxed that ink removes a note and adds none. The record says which of
        the two happened, on the human's own row and on the verdict's detail;
        nothing here repairs it.

        ⚠️ AND THE NOTE COUNT CANNOT SHOW THE SECOND CASE ON THIS FIXTURE,
        MEASURED: the contest had already awarded this head away, so owning it
        to a THIRD staff leaves the count at 2 either way. The twin field is
        the only thing that separates *moved somewhere real* from *moved
        nowhere*, which is exactly why it is recorded rather than inferred
        from the count."""
        d, arm, _ing = self.run_review(_sidecar(
            {"id": "act-own2", "stage": "gather", "kind": "own_box",
             "glyph": "glyph/0/0/0/0/1", "staff": "staff/0/0/1"}), tag="own2")
        v = self.standing(arm["record"], Q.GLYPH_OWNER, "glyph/0/0/0/0/1")
        twin = v["detail"]["twin_on_the_named_staff"]
        self.assertIsNotNone(twin,
                             "staff/0/0/1 IS a candidate of this contest, so "
                             "the record does hold the same ink there")
        self.assertIs(twin["is_the_glyphs_own_staff"], False,
                      "⚠️ the commonest own_box pulls a glyph BACK to the "
                      "staff it was cut from, and there the 'twin' is the "
                      "glyph itself — a bare row id would read as a second "
                      "copy that does not exist")
        own = self.run_review(_sidecar(
            {"id": "act-own2b", "stage": "gather", "kind": "own_box",
             "glyph": "glyph/0/0/0/0/1", "staff": "staff/0/0/0"}),
            tag="own2b")[1]
        self.assertIs(
            self.standing(own["record"], Q.GLYPH_OWNER, "glyph/0/0/0/0/1")
            ["detail"]["twin_on_the_named_staff"]["is_the_glyphs_own_staff"],
            True)
        d3, arm3, _i3 = self.run_review(_sidecar(
            {"id": "act-own3", "stage": "gather", "kind": "own_box",
             "glyph": "glyph/0/0/0/0/1", "staff": "staff/0/0/7"}), tag="own3")
        v3 = self.standing(arm3["record"], Q.GLYPH_OWNER, "glyph/0/0/0/0/1")
        self.assertEqual(v3["value"], "staff/0/0/7",
                         "a human naming a staff the contest never offered is "
                         "telling us the candidate set is wrong; swallowing "
                         "it would hide that")
        self.assertIsNone(v3["detail"]["twin_on_the_named_staff"])
        self.assertEqual((d3.notes_before, d3.notes_after), (2, 2))

    def test_an_owner_that_is_not_a_STAFF_subject_is_REFUSED(self):
        _d, _arm, ing = self.run_review(_sidecar(
            {"id": "act-own4", "stage": "gather", "kind": "own_box",
             "glyph": "glyph/0/0/0/0/1", "staff": "Violino II"}), tag="own4")
        self.assertEqual(ing.controls["actions_refused"], 1)
        self.assertIn("not a staff subject", ing.actions[0].refused)

    def test_an_owner_row_on_an_UNCONTESTED_glyph_DECIDES_NOTHING(self):
        """⚠️ NAMED, NOT HIDDEN. `adjudicate_glyph_owner`'s domain is
        `subjects_from=Q.GLYPH_BAND_DISTANCE` — the CONTESTED population — so
        a human owning an uncontested box files a row that decision is never
        asked about. There is no `Q.GLYPH_OWNER` verdict on that glyph at all.

        ⚠️⚠️ AND `reached_nothing` IS THE WRONG ASSERTION HERE, MEASURED. The
        row is NOT unread: `notehead_is_not_a_notehead` DECLARES
        `Q.HUMAN_BOX_VERDICT`, so the harness hands it every such row on that
        glyph and it lands in `basis` — where `_human_not_a_symbol` declines
        it, because `owner:` is not its question. `used` is the only field
        that separates OFFERED from WEIGHED, which is why the diff reports the
        three apart; the identical trap is recorded for `redrawn` one class
        up, and a test asserting `reached_nothing` would have been WRONG and
        would have looked right."""
        d, arm, ing = self.run_review(_sidecar(
            {"id": "act-own5", "stage": "gather", "kind": "own_box",
             "glyph": "glyph/0/0/0/0/2", "staff": "staff/0/0/1"}), tag="own5")
        self.assertIsNone(self.standing(arm["record"], Q.GLYPH_OWNER,
                                        "glyph/0/0/0/0/2"))
        self.assertEqual(
            [(h["quantity"], h["how"]) for h in d.basis_names_human],
            [(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, "basis")])
        self.assertIs(
            self.standing(arm["record"], Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,
                          "glyph/0/0/0/0/2")["value"], False,
            "an `owner:` row was read as a refusal — that is a different "
            "question answered by the wrong decision")
        self.assertEqual(d.notes_after, d.notes_before)


def _page_box_of(record: dict, glyph_key: str):
    for o in record["observations"]:
        if o["subject"] == glyph_key and o["quantity"] == Q.GLYPH_BOX:
            return list((o.get("detail") or {})["bbox_page_px"])
    return None


if __name__ == "__main__":
    unittest.main()
