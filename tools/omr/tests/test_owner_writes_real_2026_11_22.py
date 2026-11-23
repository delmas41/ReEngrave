"""lane-owner-writes (2026-11-22) -- REAL-RECORD controls for `OMR_RELOCATE_AT_EXPORT`.

THE RULE, as a musician says it: a note belongs to the staff its ledger lines climb from, and it is written there once,
with the chord on its stem. The neighbouring staff's bar may be where we happened to see it; that changes nothing about
where it belongs. Never written on two staves; never a clef part, a slash, a key flat or a letter carried over as a note.

CAUSE: each bar is read from a view that reaches 4 spaces past its own staff (6 where the gap leaves room:
`measure_extractor._build_measure_cell`), so a head 4.5 spaces below its staff (the low dotted head of a Brahms p12 horn
chord) was shown only to the neighbouring staff's bar, which rightly refused it as another staff's.

The rows are cut from the 2026-11-21 frozen-sample Brahms gather (lr-r7-frozen), re-adjudicated on the lane tree
(`data/owner_writes_real_brahms.json`: every row on the two staves in the bar at each control's x, slimmed to the fields
EXPORT reads). The notes are placed by the exporter's own `_place_notes`; nothing here is drawn.
"""

import json
import os
import pathlib
import unittest
from unittest import mock

from tools.omr.staged import export as SX
from tools.omr.staged.record import Q

DATA = pathlib.Path(__file__).parent / "data" / "owner_writes_real_brahms.json"

HORN_P12 = "glyph/12/0/6/6/1"        # the low dotted head of a horn chord, 4.5 spaces below staff 12/0/5
HORN_P12_TWIN = "glyph/12/0/5/6/3"   # the head 3 spaces higher on the same stem, written OFF and ON
HIGH_P19 = "glyph/19/0/8/0/2"        # a dotted head 4 ledger lines above staff 19/0/9
HORN_P14 = "glyph/14/0/6/8/1"        # p14 horn, the same figure
F_CLEF_DOT = "glyph/5/1/3/0/28"      # the bass clef's dot of staff 5/1/4, boxed as a head on the staff above
KEY_FLAT = "glyph/19/0/5/0/18"       # a key flat of staff 19/0/4, boxed as a head
SLASH = "glyph/12/0/10/0/8"          # a tremolo slash; the owner's copy is refused as a slash
P4_HORN = "glyph/4/1/6/8/1"          # p4 horn: its own view read a quarter, its stem mate an eighth (flag): held
TWIN_HELD = "glyph/12/0/6/3/0"       # a head the owner holds a copy of: written once, on the owner


def _runs(rec):
    """`export.build`'s own first step (staff runs from the partition, spacing and cell frames), without the part join."""
    runs = {}
    for v in rec.verdicts_of(Q.MEASURE_PARTITION):
        s = SX._parse_subject(v["subject"])
        run = runs.setdefault(v["subject"], SX.StaffRun(key=v["subject"], page=s["page"] or 0, system=s["system"] or 0,
                                                         staff=s["staff"] or 0))
        run.n_measures = int(v["value"]) if v["outcome"] == "decided" else 0
        run.n_measures_decided = v["outcome"] == "decided"
    for key, run in runs.items():
        run.meter = rec.value(Q.METER, "system/%d/%d" % (run.page, run.system))
        sp = rec.obs(Q.STAFF_SPACING, key)
        run.spacing = float(sp[-1]["value"]) if sp else None
    for o in rec.obs_of(Q.CELL_BOX):
        cs = SX._parse_subject(o["subject"])
        run = runs.get(SX._staff_key(cs["page"] or 0, cs["system"] or 0, cs["staff"] or 0))
        if run is not None and cs["cell"] is not None:
            run.cell_boxes[cs["cell"]] = [float(v) for v in o["value"]]
    return runs


def _place(flag):
    rec = SX.Record({"record": json.loads(DATA.read_text())["record"], "summary": {}})
    runs = _runs(rec)
    fates = {}
    with mock.patch.dict(os.environ, {"OMR_RELOCATE_AT_EXPORT": "1" if flag else "0"}):
        SX._place_notes(rec, runs, fates=fates)
    return runs, fates


def _heads(runs, staff):
    return [d for run in runs.values() if run.key == staff for c in run.cells.values() for d in c.detections
            if d.get("category") == "notehead"]


class TestTheFarHeadIsWrittenOnItsOwner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.off = _place(False)
        cls.on = _place(True)

    def test_flag_off_the_horn_head_is_not_written(self):
        runs, fates = self.off
        self.assertEqual(fates[HORN_P12], "owned_by_another_staff")
        self.assertNotIn(HORN_P12, [d["glyph"] for d in _heads(runs, "staff/12/0/5")])

    def test_on_it_is_written_on_its_owner_in_the_chord_dotted_at_its_ledger_pitch(self):
        runs, fates = self.on
        self.assertEqual(fates[HORN_P12], "written_relocated")
        mine = [d for d in _heads(runs, "staff/12/0/5") if d["glyph"] == HORN_P12]
        twin = [d for d in _heads(runs, "staff/12/0/5") if d["glyph"] == HORN_P12_TWIN]
        self.assertEqual(len(mine), 1)
        self.assertEqual(len(twin), 1)
        self.assertEqual(mine[0]["pitch"], "C3")                   # 4 ledger lines, then the space beyond them
        self.assertEqual(twin[0]["pitch"], "C4")
        self.assertEqual(mine[0]["dots"], 1)
        self.assertEqual((mine[0]["duration_beats"], mine[0]["duration_type"]),
                         (twin[0]["duration_beats"], twin[0]["duration_type"]))
        run = next(r for r in runs.values() if r.key == "staff/12/0/5")
        cell = next(c for c in run.cells.values() if any(d is mine[0] for d in c.detections))
        ev = [e for e in SX._group_chords(cell.detections) if any(h is mine[0] for h in e.get("noteheads") or ())]
        self.assertTrue(ev and any(h is twin[0] for h in ev[0]["noteheads"]), "the far head joins the chord on its stem")
        self.assertNotIn(HORN_P12, [d["glyph"] for d in _heads(runs, "staff/12/0/6")])   # never on the staff that saw it

    def test_two_more_far_heads(self):
        runs, fates = self.on
        self.assertEqual(fates[HIGH_P19], "written_relocated")
        self.assertEqual(fates[HORN_P14], "written_relocated")
        self.assertEqual([d["pitch"] for d in _heads(runs, "staff/19/0/9") if d["glyph"] == HIGH_P19], ["Ab6"])   # the key flats A
        self.assertEqual(self.off[1][HIGH_P19], "owned_by_another_staff")


class TestNeverANonNote(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.on = _place(True)

    def test_a_clef_part_is_not_carried_over(self):
        self.assertEqual(self.on[1][F_CLEF_DOT], "relocation_on_another_mark")

    def test_a_key_flat_is_not_carried_over(self):
        self.assertEqual(self.on[1][KEY_FLAT], "relocation_on_another_mark")

    def test_a_tremolo_slash_is_not_carried_over(self):
        self.assertEqual(self.on[1][SLASH], "owned_by_another_staff")

    def test_a_head_whose_value_its_stem_mate_contradicts_is_held(self):
        self.assertEqual(self.on[1][P4_HORN], "relocation_value_disagrees_with_its_chord")

    def test_a_head_the_owner_holds_is_written_once(self):
        runs, fates = self.on
        self.assertEqual(fates[TWIN_HELD], "owned_by_another_staff")
        here = [d for d in _heads(runs, "staff/12/0/5") if d.get("pitch") == "G3"
                and abs(d["bbox_page"][0] - SX._page_box_of(next(o for o in SX.Record(
                    {"record": json.loads(DATA.read_text())["record"], "summary": {}}).obs(Q.GLYPH_BOX, TWIN_HELD)))[0]) < 30]
        self.assertEqual(len(here), 1)


if __name__ == "__main__":
    unittest.main()
