"""ROADMAP 2.324 downstream (`lane-2.324-downstream`; benchmarks/data-flow-audit-2026-11/FINDINGS.md section A). STAGED.

Item 1 -- THE KEY WINDOW STARTS RIGHT OF THE CLEF THE PAGE READ, NEVER RIGHT OF A DETECTOR BOX (CLAUDE.md section 4: "Only a clef
stands before the key accidentals"; section 3: the clef is read once on the page-wide pass and claims first). `key_slots.header_boxes`
drops the detector's `clef*` boxes and puts in the clefs the page-wide pass claimed; a key-shaped box inside a read clef's claim is
that clef's ink. Controls are REAL rows of the 2.324 r7 frozen-sample record (Litolff ON arm), `data_key_window_read_clef_2_324.json`.
Each control is asserted on both sides: the old drawing (every detector box, `boxes_of`) gives the wrong window -- the control fails
with the change taken out -- and the new one gives the window the page's read clef bounds.
"""
from __future__ import annotations

import json
import pathlib
import unittest
from types import SimpleNamespace

from tools.omr.staged import clef_pagewide as CP
from tools.omr.staged.adjudicators import key_slots as KS

DATA = pathlib.Path(__file__).with_name("data_key_window_read_clef_2_324.json")


def _rows():
    return [SimpleNamespace(**r) for r in json.loads(DATA.read_text())["rows"]]


def _cell(staff: str, cell: int):
    rows = _rows()
    glyphs = [r for r in rows if r.quantity == "glyph_box" and r.subject.startswith(f"glyph/{staff}/{cell}/")]
    claims = [r for r in rows if r.quantity == "claimed_area" and r.subject == f"staff/{staff}"]
    space = next(float(r.value) for r in rows if r.quantity == "cell_staff_space" and r.subject == f"cell/{staff}/{cell}")
    return glyphs, claims, space


def _id(rows, subject):
    return next(r.id for r in rows if r.subject == subject)


class TestKeyWindowFromTheReadClef(unittest.TestCase):

    def test_source_name_matches_the_page_wide_reader(self):
        self.assertEqual(KS.CLEF_PAGEWIDE_SOURCE, CP.SOURCE)

    def test_litolff_6_1_3_bar_93_refused_small_clef_box_opens_no_window(self):
        # the audit's case: a small `clefG` box under the staff (glyph/6/1/3/1/8), refused by the page-wide pass
        # (`clef_box_not_clef_sized`); bar 93's natural (1/7) is an in-bar accidental, and the note 1/4 stood in a window drawn off the box
        glyphs, claims, space = _cell("6/1/3", 1)
        old = KS.key_slot_window(KS.boxes_of(glyphs), space)
        self.assertIsNotNone(old)                                       # the old drawing: a window off the refused box
        self.assertEqual(old.clef, _id(glyphs, "glyph/6/1/3/1/8"))
        note = next(b for b in KS.boxes_of(glyphs) if b.row_id == _id(glyphs, "glyph/6/1/3/1/4"))
        self.assertTrue(KS.stands_in_the_window(old, note))
        new = KS.key_slot_window(KS.header_boxes(glyphs, claims, 1), space)
        self.assertIsNone(new)                                          # no clef read in the bar, no key-class box: no window

    def test_litolff_4_1_9_keyflat_box_over_the_alto_clef_is_the_clefs_ink(self):
        # the alto clef is read from its ink with no clef box; the detector boxed the clef's ink as a `keyFlat` (glyph/4/1/9/0/8)
        glyphs, claims, space = _cell("4/1/9", 0)
        clef_ink = _id(glyphs, "glyph/4/1/9/0/8")
        old = KS.key_slot_window(KS.boxes_of(glyphs), space)
        self.assertIsNotNone(old)
        self.assertIsNone(old.clef)
        self.assertEqual(old.members[0], clef_ink)                      # the old run opens ON the clef
        new = KS.key_slot_window(KS.header_boxes(glyphs, claims, 0), space)
        self.assertIsNotNone(new)
        self.assertNotIn(clef_ink, new.members)
        claim = next(c for c in claims if c.detail["cell"] == 0 and not c.detail["change"])
        self.assertEqual(new.clef, claim.id)
        self.assertEqual(new.clef_standing, "READ")
        self.assertFalse(new.uncertain)
        self.assertEqual(new.slots, 3)                                  # the three flats
        self.assertGreater(new.lo, old.lo + 2.0 * space)                # starts right of the clef, not inside it

    def test_litolff_2_0_0_padded_clef_copy_no_longer_bounds_the_run(self):
        # two `clefG` boxes on one treble clef; the page read the clef through glyph/2/0/0/0/2, the wider copy 0/4 bounded the run
        glyphs, claims, space = _cell("2/0/0", 0)
        old = KS.key_slot_window(KS.boxes_of(glyphs), space)
        self.assertEqual(old.clef, _id(glyphs, "glyph/2/0/0/0/4"))
        new = KS.key_slot_window(KS.header_boxes(glyphs, claims, 0), space)
        claim = next(c for c in claims if c.detail["cell"] == 0)
        self.assertEqual(new.clef, claim.id)
        self.assertEqual(new.members, old.members)                      # the same two flats
        self.assertLess(new.lo, old.lo - 0.5 * space)                   # from the read clef's own right edge

    def test_a_possible_clef_bounds_a_window_marked_uncertain(self):
        # the 2/0/0 run, its read clef filed instead as NARROWED (a possible clef): the window is drawn and marked uncertain
        glyphs, claims, space = _cell("2/0/0", 0)
        c = next(c for c in claims if c.detail["cell"] == 0)
        narrowed = SimpleNamespace(id=c.id, subject=c.subject, quantity=c.quantity, value=c.value,
                                   detail={**c.detail, "standing": "NARROWED", "source": "detector"})
        new = KS.key_slot_window(KS.header_boxes(glyphs, [narrowed], 0), space)
        self.assertIsNotNone(new)
        self.assertTrue(new.uncertain)
        self.assertEqual(new.detail()["key_slot_clef_standing"], "NARROWED")

    def test_a_refused_not_a_clef_gives_no_bound(self):
        # nothing filed for the clef (r8: a not-a-clef files no claim) and no detector box consulted: the 2/0/0 run is then bounded
        # only by its own first key-class box, never by either `clefG` box
        glyphs, _claims, space = _cell("2/0/0", 0)
        new = KS.key_slot_window(KS.header_boxes(glyphs, [], 0), space)
        self.assertIsNotNone(new)
        self.assertIsNone(new.clef)


# ─────────────────────────────────────────────────────────────────────────────
# Item 2 -- A CLEF CHANGE READ INSIDE A LINE PITCHES THE NOTES AFTER IT EVEN WHEN THE STAFF'S OPENING CLEF IS UNDECIDED (CLAUDE.md §3:
# the answer FOLLOWS, so EVALUATE writes it). NO STAFF ON THE FROZEN SAMPLE HAS AN UNDECIDED OPENING CLEF (2.324 r7 records: Litolff
# 184 of 184 and Brahms 199 of 199 header clefs DECIDED), so the control is the NEAREST REAL CASE, LABELLED: every row of Litolff p6 s1
# staff 3 as the r7 record filed it (tenor header, a bass clef READ inside bar 0 at x 599.5; 43 heads pitched from the bass clef, 4 from
# the tenor before it), with ONE constructed change -- the header clef verdict replaced by an ABSTAINED one.
# ─────────────────────────────────────────────────────────────────────────────

DATA2 = pathlib.Path(__file__).with_name("data_clef_change_unsettled_header_2_324.json")
STAFF = "staff/6/1/3"


def _staff_log(header: str):
    """The real rows of Litolff p6 s1 staff 3 in a Log; the header clef `decided` (the record's own verdict) or `abstained`
    (CONSTRUCTED). Returns (log, expected pitch by head as the r7 record wrote it, the real pitch verdicts' reasons)."""
    from tools.omr.staged.record import Candidate, Log, Outcome, Subject, Verdict
    raw = json.loads(DATA2.read_text())
    log = Log()
    for r in raw["observations"]:
        log.observe(Subject.from_key(r["subject"]), r["quantity"], r["value"], reader=r["reader"], frame=r["frame"], **r["detail"])
    for r in raw["abstentions"]:
        log.abstain(Subject.from_key(r["subject"]), r["quantity"], reader=r["reader"], frame=r["frame"], reason=r["reason"],
                    **r["detail"])
    log.freeze()
    expected, reasons = {}, {}
    for v in raw["verdicts"]:
        if v["quantity"] == "pitch":
            expected[v["subject"]], reasons[v["subject"]] = v["value"], v["reason"]
            continue
        if v["quantity"] == "clef":
            if header == "abstained":
                log.record(Verdict(id=log._next_id("vrd"), subject=Subject.from_key(STAFF), quantity=v["quantity"],
                                   outcome=Outcome.ABSTAINED, value=None, decider=v["decider"], reason="no_candidates"))
                continue
        log.record(Verdict(id=log._next_id("vrd"), subject=Subject.from_key(v["subject"]), quantity=v["quantity"],
                           outcome=Outcome(v["outcome"]), value=v["value"], decider=v["decider"], reason=v["reason"],
                           candidates=tuple(Candidate(c["value"], c["support"]) for c in (v.get("candidates") or ())),
                           detail=v["detail"]))
    return log, expected, reasons


def _pitches(log):
    from tools.omr.staged.record import Q, Scope, Subject
    return {v.subject.to_key(): v.value for v in log.verdicts(Q.PITCH, Subject.from_key(STAFF), scope=Scope.SELF_AND_DESCENDANTS)
            if v.decider == "restate_pitch"}


def _restate_only(log):
    """EVALUATE's first pass over the `restate_pitch` rule alone (the other rules need facts this staff's rows do not carry)."""
    from tools.omr.staged import evaluate
    evaluate._ensure_rules()
    rules = [r for r in evaluate.RULES if r.consequence is evaluate.Consequence.RESTATE_PITCH]
    report = evaluate.Report(fired=[], skipped=[], stubs=[])
    saved = list(evaluate.RULES)
    try:
        evaluate.RULES[:] = rules
        evaluate._pass(log, report, progress=False)
    finally:
        evaluate.RULES[:] = saved
    return report


class TestClefChangeWithUnsettledHeader(unittest.TestCase):

    def test_the_real_record_as_filed_pitches_every_head(self):
        log, expected, reasons = _staff_log("decided")
        _restate_only(log)
        got = _pitches(log)
        mine = {k: v for k, v in expected.items() if reasons[k] in ("position_and_clef_change", "position_and_clef")}
        self.assertEqual({k: got.get(k) for k in mine}, mine)        # the replay reproduces the r7 record's pitches

    def test_abstained_header_after_the_change_pitched_before_it_unread(self):
        log, expected, reasons = _staff_log("abstained")
        report = _restate_only(log)
        got = _pitches(log)
        after = {k for k, r in reasons.items() if r == "position_and_clef_change"}
        before = {k for k, r in reasons.items() if r != "position_and_clef_change"}
        self.assertEqual(len(after), 43)
        self.assertEqual(len(before), 4)
        self.assertEqual({k: got.get(k) for k in after}, {k: expected[k] for k in after})   # from the READ bass clef, unchanged
        self.assertEqual({k for k in before if k in got}, set())                           # the opening clef is unknown: unread
        self.assertTrue(any(f[0] == "restate_pitch" for f in report.fired))

    def test_the_control_fails_with_the_change_taken_out(self):
        from tools.omr.staged import evaluate
        log, _expected, _reasons = _staff_log("abstained")
        evaluate._ensure_rules()
        rule = next(r for r in evaluate.RULES if r.consequence is evaluate.Consequence.RESTATE_PITCH)
        i = evaluate.RULES.index(rule)
        import dataclasses
        evaluate.RULES[i] = dataclasses.replace(rule, fires_unsettled=False)
        try:
            report = _restate_only(log)
        finally:
            evaluate.RULES[i] = rule
        self.assertEqual(_pitches(log), {})                                                 # the old guard: nothing until INFER
        self.assertIn(("restate_pitch", STAFF, "cause_abstained"), report.skipped)


if __name__ == "__main__":
    unittest.main()
