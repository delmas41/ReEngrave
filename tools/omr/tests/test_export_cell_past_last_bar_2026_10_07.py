"""EXPORT's accounting EQUALITY on whole Brahms (night 10-07): six heads went
nowhere.

`to_musicxml` raised `Unbalanced` on the whole Brahms movement -- 32,389
noteheads, 7,164 written, 25,219 counted, 6 in neither. All six sat in cell 7
of page 0 / system 0 on a staff whose `measure_partition` says SEVEN bars (cells
0-6). `_place_notes` filed each head into `run.cells[7]` and counted it
`written`; the renderer walks `range(run.n_measures)` and never visits cell 7.
So the head was written to a bar the file does not have: no `<note>`, no
refusal. It happens with every flag combination -- flags off included -- because
it is a fact of the partition against the cell the detector cut, not of the
relocation or the mark groups.

Each lost case gets its OWN true reason (never a catch-all), and each has a
positive control in the same class: the same head in a bar the partition does
hold is written. All four flag combinations (`OMR_RELOCATE_AT_EXPORT` x mark
groups) are run: the accounting must balance in every one.
"""

import itertools
import os
import unittest
from unittest import mock

from tools.omr.staged import export as SX
from tools.omr.staged.record import Q
from tools.omr.tests.test_relocate_at_export_2026_10_06 import (
    SPACING, UP, _head, _notes_by_part, _obs, _vrd)

PAST = "cell_past_the_last_bar"
UNDECIDED = "bar_count_not_decided"


def _staves(*, n_bars=(1, 1), n_staves=2):
    rec = {"observations": [], "verdicts": [], "abstentions": [],
           "counts": {}}
    for st in range(n_staves):
        sk = f"staff/0/0/{st}"
        nb = n_bars[st]
        if nb is None:                      # the partition ABSTAINED
            rec["verdicts"].append(_vrd(900 + st, sk, Q.MEASURE_PARTITION,
                                        None, outcome="abstained"))
        else:
            rec["verdicts"].append(_vrd(900 + st, sk, Q.MEASURE_PARTITION, nb))
        rec["verdicts"].append(_vrd(910 + st, sk, Q.CLEF, "treble"))
        rec["observations"].append(_obs(920 + st, sk, Q.STAFF_SPACING, SPACING))
        # the detector cut THREE cells whatever the partition decided
        for c in range(3):
            rec["observations"] += [
                _obs(1000 + 10 * st + c, f"cell/0/0/{st}/{c}", Q.CELL_BOX,
                     [400.0 * c, 100.0 * st, 400.0 * c + 400.0,
                      100.0 * st + 200.0]),
                _obs(1100 + 10 * st + c, f"cell/0/0/{st}/{c}",
                     Q.CELL_STAFF_SPACE, SPACING * UP)]
    rec["verdicts"] += [
        _vrd(950, "system/0/0", Q.SYSTEM_STAFF_COUNT, n_staves),
        _vrd(951, "document", Q.PART_PARTITION,
             {"join": "ordinal", "staves_per_system": n_staves},
             reason="ordinal")]
    return rec


def _own_head(rec, n, staff, cell, glyph, x0, *, conf=0.9, pitch="C4"):
    sub = f"glyph/0/0/{staff}/{cell}/{glyph}"
    _head(rec, n, sub, (x0, 10 + 100 * staff, x0 + 20, 30 + 100 * staff),
          pitch=pitch)
    for o in rec["observations"]:
        if o["subject"] == sub and o["quantity"] == Q.GLYPH_BOX:
            o["score"] = conf
    return sub


def _group(rec, n, gid, subs):
    for k, sub in enumerate(subs):
        rec["observations"].append(
            _obs(n + k, sub, Q.MARK_GROUP, gid, family="notehead"))


FLAGS = list(itertools.product((False, True), repeat=2))   # (groups, relocate)


def _export(rec, *, relocate):
    env = {"OMR_RELOCATE_AT_EXPORT": "1"} if relocate else {}
    with mock.patch.dict(os.environ, env, clear=False):
        if not relocate:
            os.environ.pop("OMR_RELOCATE_AT_EXPORT", None)
        return SX.to_musicxml({"record": rec, "summary": {}})


def _with_group_rows(build, groups):
    """`build(rec)` files the head(s); with `groups` each head is its own
    one-member group, which is what a record gathered with OMR_MARK_GROUPS
    holds for a mark detected once."""
    rec = _staves()
    subs = build(rec)
    if groups:
        for k, s in enumerate(subs):
            _group(rec, 3000 + 10 * k, f"mark:{k}", [s])
    return rec


class TestAHeadInACellPastTheLastBarIsCounted(unittest.TestCase):
    def test_it_is_counted_under_its_own_reason_in_every_flag_combination(self):
        for groups, reloc in FLAGS:
            with self.subTest(groups=groups, relocate=reloc):
                rec = _with_group_rows(
                    lambda r: [_own_head(r, 100, 0, 1, 0, 450)], groups)
                xml, rep = _export(rec, relocate=reloc)
                self.assertEqual(rep["notes_not_written"], {PAST: 1})
                self.assertEqual(_notes_by_part(xml)["P1"], [])
                self.assertTrue(rep["balance"]["balanced"])

    def test_positive_control_the_same_head_in_a_bar_the_partition_holds(self):
        for groups, reloc in FLAGS:
            with self.subTest(groups=groups, relocate=reloc):
                rec = _with_group_rows(
                    lambda r: [_own_head(r, 100, 0, 0, 0, 50)], groups)
                xml, rep = _export(rec, relocate=reloc)
                self.assertEqual(_notes_by_part(xml)["P1"], ["C4"])
                self.assertEqual(rep["notes_not_written_total"], 0)
                self.assertTrue(rep["balance"]["balanced"])


class TestAStaffWhoseBarCountAbstainedNamesThatNotCellsPastTheEnd(
        unittest.TestCase):
    def test_every_flag_combination_balances_and_names_the_partition(self):
        for groups, reloc in FLAGS:
            with self.subTest(groups=groups, relocate=reloc):
                def build(r):
                    return [_own_head(r, 100, 0, 0, 0, 50)]
                rec = _staves(n_bars=(None, 1))
                subs = build(rec)
                if groups:
                    _group(rec, 3000, "mark:0", subs)
                xml, rep = _export(rec, relocate=reloc)
                self.assertEqual(rep["notes_not_written"], {UNDECIDED: 1})
                self.assertTrue(rep["balance"]["balanced"])


class TestARelocatedHeadLandingPastTheOwnersLastBar(unittest.TestCase):
    """The relocation branch picks the owner's cell by page x
    (`_plan_relocation`); that cell can be one the owner's partition does not
    hold. Written on staff 0 would be written nowhere."""

    def _rec(self, *, moved_x):
        rec = _staves()
        sub = "glyph/0/0/1/0/0"
        _head(rec, 100, sub, (moved_x, 210, moved_x + 20, 230),
              pitch="G4", decider="move_glyph", owner="staff/0/0/0")
        return rec, sub

    def test_it_is_counted_not_lost_with_the_flag_on_and_off(self):
        for groups, reloc in FLAGS:
            with self.subTest(groups=groups, relocate=reloc):
                rec, sub = self._rec(moved_x=450)    # owner's cell 1
                if groups:
                    _group(rec, 3000, "mark:0", [sub])
                xml, rep = _export(rec, relocate=reloc)
                self.assertTrue(rep["balance"]["balanced"])
                self.assertEqual(_notes_by_part(xml), {"P1": [], "P2": []})
                if reloc:
                    self.assertEqual(rep["notes_not_written"], {PAST: 1})
                else:
                    self.assertEqual(rep["notes_not_written"],
                                     {"owned_by_another_staff": 1})

    def test_positive_control_a_head_over_the_owners_first_bar_is_written(self):
        rec, sub = self._rec(moved_x=100)
        xml, rep = _export(rec, relocate=True)
        self.assertEqual(_notes_by_part(xml), {"P1": ["G4"], "P2": []})
        self.assertEqual(rep["notes_not_written_total"], 0)
        self.assertTrue(rep["balance"]["balanced"])


class TestAMarkGroupWhoseBestMemberIsPastTheLastBar(unittest.TestCase):
    def test_the_mark_is_written_once_and_the_lost_member_is_counted(self):
        for reloc in (False, True):
            with self.subTest(relocate=reloc):
                rec = _staves()
                best = _own_head(rec, 100, 0, 1, 0, 450, conf=0.95)
                other = _own_head(rec, 200, 1, 0, 0, 50, conf=0.5)
                _group(rec, 3000, "mark:0", [best, other])
                xml, rep = _export(rec, relocate=reloc)
                self.assertTrue(rep["balance"]["balanced"])
                written = sum(len(v) for v in _notes_by_part(xml).values())
                self.assertEqual(written, 1)
                self.assertEqual(rep["notes_not_written"], {PAST: 1})
