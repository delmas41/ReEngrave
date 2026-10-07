"""ROADMAP 2.58 -- a head that belongs to another staff is WRITTEN there.

Sean, 2026-10-06: *"All note heads should be found and written on their
staff."* `OMR_RELOCATE_AT_EXPORT` (default OFF) relocates a head whose decided
owner is another staff and which that staff holds no copy of; a head the owner
holds a twin of is still dropped, and a head that lands on one the owner's
cell already has is COUNTED (`relocation_collides`), never written twice.

Every refusal has a positive control in the same class (CLAUDE.md §6b), and the
accounting stays an EQUALITY.
"""

import os
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

from tools.omr.staged import export as SX
from tools.omr.staged.record import Q

QUARTER = {"beats": 1.0, "written": 1.0, "dots": 0}
SPACING = 10.0          # page px per staff space
UP = 2.0                # canonical px per page px


def _obs(i, subject, quantity, value, **detail):
    return {"id": f"obs:{i:06d}", "subject": subject, "quantity": quantity,
            "value": value, "reader": "detector", "frame": "cell:0",
            "score": 0.9, "detail": detail, "basis": []}


def _vrd(i, subject, quantity, value, outcome="decided", reason="x",
         decider="t"):
    return {"id": f"vrd:{i:06d}", "subject": subject, "quantity": quantity,
            "outcome": outcome, "value": value, "decider": decider,
            "reason": reason, "considered": [], "used": [], "missing": [],
            "declined": [], "excluded": [], "correlated": [],
            "candidates": [], "basis": [], "margin": None,
            "supersedes": None, "detail": {}}


def _head(rec, n, sub, page_box, *, pitch, decider="t", owner=None):
    x0, y0, x1, y1 = page_box
    rec["observations"] += [
        _obs(n, sub, Q.GLYPH_BOX,
             ["noteheadBlackOnLine", 10, 10, 20, 20], category="notehead",
             bbox_page_px=list(page_box)),
        _obs(n + 1, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine")]
    rec["verdicts"] += [_vrd(n + 2, sub, Q.PITCH, pitch, decider=decider),
                        _vrd(n + 3, sub, Q.DURATION, QUARTER)]
    if owner:
        rec["verdicts"].append(
            _vrd(n + 4, sub, Q.GLYPH_OWNER, owner, reason="ledger_note_first"))


def _two_staves(*, cell_x=(0.0, 400.0), moved_box=(100, 210, 120, 230),
                owner_pitch="G4", owner_decider="move_glyph",
                owner_head_box=None, owner_twin_box=None):
    """Staff 1 detected a head that staff 0 owns. Staff 0 holds NO copy unless
    `owner_head_box` (a near-but-not-twin head) or `owner_twin_box` is given."""
    rec = {"observations": [], "verdicts": [], "abstentions": [],
           "counts": {}}
    for st in (0, 1):
        sk = f"staff/0/0/{st}"
        rec["verdicts"] += [_vrd(900 + st, sk, Q.MEASURE_PARTITION, 1),
                            _vrd(910 + st, sk, Q.CLEF, "treble")]
        rec["observations"] += [
            _obs(920 + st, sk, Q.STAFF_SPACING, SPACING),
            _obs(930 + st, f"cell/0/0/{st}/0", Q.CELL_BOX,
                 [cell_x[0], 100.0 * st, cell_x[1], 100.0 * st + 200.0]),
            _obs(940 + st, f"cell/0/0/{st}/0", Q.CELL_STAFF_SPACE,
                 SPACING * UP)]
    rec["verdicts"] += [
        _vrd(950, "system/0/0", Q.SYSTEM_STAFF_COUNT, 2),
        _vrd(951, "document", Q.PART_PARTITION,
             {"join": "ordinal", "staves_per_system": 2}, reason="ordinal")]
    _head(rec, 100, "glyph/0/0/1/0/0", moved_box, pitch=owner_pitch,
          decider=owner_decider, owner="staff/0/0/0")
    if owner_head_box is not None:
        _head(rec, 200, "glyph/0/0/0/0/0", owner_head_box, pitch="C4")
    if owner_twin_box is not None:
        _head(rec, 300, "glyph/0/0/0/0/1", owner_twin_box, pitch="C4",
              owner="staff/0/0/0")
    return {"record": rec, "summary": {}}


def _notes_by_part(xml):
    root = ET.fromstring(xml)
    return {p.get("id"): [n.findtext("pitch/step") + n.findtext("pitch/octave")
                          for n in p.iter("note") if n.find("pitch") is not None]
            for p in root.findall("part")}


def _export(page, flag):
    env = {"OMR_RELOCATE_AT_EXPORT": "1"} if flag else {}
    with mock.patch.dict(os.environ, env, clear=False):
        if not flag:
            os.environ.pop("OMR_RELOCATE_AT_EXPORT", None)
        return SX.to_musicxml(page)


class TestRelocationIsOffByDefault(unittest.TestCase):
    def test_the_flag_off_drops_the_head_as_before(self):
        xml, rep = _export(_two_staves(), flag=False)
        self.assertEqual(_notes_by_part(xml), {"P1": [], "P2": []})
        self.assertEqual(rep["notes_not_written"],
                         {"owned_by_another_staff": 1})
        self.assertTrue(rep["balance"]["balanced"])


class TestAHeadIsWrittenOnItsOwner(unittest.TestCase):
    def test_it_lands_on_the_owner_staff_with_the_re_derived_pitch(self):
        xml, rep = _export(_two_staves(), flag=True)
        self.assertEqual(_notes_by_part(xml), {"P1": ["G4"], "P2": []})
        self.assertEqual(rep["notes_not_written_total"], 0)
        self.assertEqual(rep["balance"]["relocated_heads_written"], 1)
        self.assertTrue(rep["balance"]["balanced"])

    def test_it_is_written_once(self):
        xml, _ = _export(_two_staves(), flag=True)
        self.assertEqual(sum(len(v) for v in _notes_by_part(xml).values()), 1)


class TestACollisionIsCountedNotWritten(unittest.TestCase):
    def test_a_head_the_owner_cell_already_has_there_is_one_mark(self):
        # a head 5 px away, box overlap well under 0.3 IoU -> not a twin, but
        # within 0.75 sp (7.5 px) on both axes
        page = _two_staves(owner_head_box=(107, 217, 127, 237))
        xml, rep = _export(page, flag=True)
        self.assertEqual(_notes_by_part(xml)["P1"], ["C4"])   # the owner's own
        self.assertEqual(rep["notes_not_written"],
                         {"relocation_collides": 1})
        self.assertTrue(rep["balance"]["balanced"])

    def test_positive_control_a_head_far_from_the_owners_is_written(self):
        page = _two_staves(owner_head_box=(250, 214, 270, 234))
        xml, rep = _export(page, flag=True)
        self.assertEqual(sorted(_notes_by_part(xml)["P1"]), ["C4", "G4"])
        self.assertEqual(rep["notes_not_written_total"], 0)


class TestTheTwinCaseIsUnchanged(unittest.TestCase):
    def test_an_owner_that_holds_the_ink_still_drops_the_other_copy(self):
        page = _two_staves(owner_twin_box=(101, 211, 121, 231))
        xml, rep = _export(page, flag=True)
        self.assertEqual(_notes_by_part(xml)["P1"], ["C4"])
        self.assertEqual(rep["notes_not_written"],
                         {"owned_by_another_staff": 1})


class TestEveryRefusalIsNamed(unittest.TestCase):
    def test_a_pitch_not_derived_by_move_glyph_is_refused_not_trusted(self):
        """The pitch on the staff the head was CUT from is the 263-edit
        failure; positive control is the first test of the class above."""
        xml, rep = _export(_two_staves(owner_decider="restate_pitch"),
                           flag=True)
        self.assertEqual(_notes_by_part(xml), {"P1": [], "P2": []})
        self.assertEqual(rep["notes_not_written"],
                         {"relocation_not_repitched": 1})
        self.assertTrue(rep["balance"]["balanced"])

    def test_no_owner_cell_at_that_x_is_refused(self):
        xml, rep = _export(_two_staves(cell_x=(300.0, 400.0)), flag=True)
        self.assertEqual(rep["notes_not_written"],
                         {"relocation_no_cell_at_x": 1})
        self.assertTrue(rep["balance"]["balanced"])


class TestNearerStaffClaimIsRelocatedToo(unittest.TestCase):
    """`not_a_notehead:belongs_to_a_nearer_staff` is an OWNERSHIP claim, so
    under the flag it is relocated where the owner holds no copy and still
    dropped (under its own name) where the owner holds one."""

    def _page(self, **kw):
        page = _two_staves(**kw)
        page["record"]["verdicts"].append(
            _vrd(990, "glyph/0/0/1/0/0", Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, True,
                 reason="belongs_to_a_nearer_staff"))
        return page

    def test_off_it_is_dropped_under_its_own_name(self):
        xml, rep = _export(self._page(), flag=False)
        self.assertEqual(rep["notes_not_written"],
                         {"not_a_notehead:belongs_to_a_nearer_staff": 1})

    def test_on_and_no_twin_it_is_written_on_the_owner(self):
        xml, rep = _export(self._page(), flag=True)
        self.assertEqual(_notes_by_part(xml), {"P1": ["G4"], "P2": []})
        self.assertEqual(rep["notes_not_written_total"], 0)

    def test_on_and_a_twin_it_is_still_dropped_under_the_same_name(self):
        xml, rep = _export(self._page(owner_twin_box=(101, 211, 121, 231)),
                           flag=True)
        self.assertEqual(rep["notes_not_written"],
                         {"not_a_notehead:belongs_to_a_nearer_staff": 1})

    def test_a_fragment_box_is_NOT_relocated_it_is_about_the_box(self):
        page = _two_staves()
        page["record"]["verdicts"].append(
            _vrd(990, "glyph/0/0/1/0/0", Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, True,
                 reason="clipped_fragment"))
        xml, rep = _export(page, flag=True)
        self.assertEqual(rep["notes_not_written"],
                         {"not_a_notehead:clipped_fragment": 1})


class TestMoveGlyphReadsTheLedgerReadingWhenThereIsNoBandRow(unittest.TestCase):
    """The head's owner holds no copy, so there is no band-distance row toward
    it; the position the owner verdict itself stands on is the ledger reading."""

    def _log(self, *, band=None, ledger=None):
        from tools.omr.staged import consequences as C
        from tools.omr import staged  # noqa: F401
        from tools.omr.staged.record import Log, Outcome, Verdict, READERS
        from tools.omr.staged import record as R
        log = Log()
        g = R.glyph(0, 0, 1, 0, 0)
        if band is not None:
            log.observe(g, Q.GLYPH_BAND_DISTANCE, 1.0, reader=READERS.GEOMETRY,
                        frame="cell:0", candidate="staff/0/0/0",
                        position_in_candidate=band)
        if ledger is not None:
            log.observe(g, Q.FAR_HEAD_OWNER_LEDGER, ledger,
                        reader=READERS.LEDGER_OWNER_NOTE_FIRST,
                        frame="cell:0", candidate="staff/0/0/0")
        owner = log.record(Verdict(
            id=log._next_id("vrd"), subject=g, quantity=Q.GLYPH_OWNER,
            outcome=Outcome.DECIDED, value="staff/0/0/0", decider="t",
            reason="x"))
        log.record(Verdict(
            id=log._next_id("vrd"), subject=R.staff(0, 0, 0), quantity=Q.CLEF,
            outcome=Outcome.DECIDED, value="treble", decider="t", reason="x"))
        return C.move_glyph(log, g, owner)

    def test_the_ledger_reading_gives_the_pitch_on_the_owner_clef(self):
        out = self._log(ledger=-2)
        self.assertEqual([v.value for v in out], ["A5"])
        self.assertEqual(out[0].decider, "move_glyph")

    def test_the_band_row_still_wins_when_there_is_one(self):
        out = self._log(band=4.0, ledger=-2)
        self.assertEqual([v.value for v in out], ["B4"])

    def test_neither_row_means_no_pitch_never_a_guess(self):
        self.assertEqual(self._log(), [])


if __name__ == "__main__":
    unittest.main()
