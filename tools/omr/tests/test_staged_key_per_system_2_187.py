"""ROADMAP 2.187: the KEY SIGNATURE read ONCE PER SYSTEM -- flag `OMR_KEY_PER_SYSTEM` (default OFF; files into the 2.183 key claim).

CAUSE (2.183): a staff's key window was drawn from that staff's own detector key boxes, so a flat the detector boxed as a rest, past the last
drawn slot, stood in no window. The page prints one signature per system; its COUNT is read from the staves' agreement. Each CONTROL passes
with the reader absent or present, so a reader that claims everything cannot pass; the failing case (flag OFF) is asserted beside it.
Synthetic rasters: staff space 20 px, a flat is a 20 x 50 px block, slots 24 px apart.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import key_object as KO
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q, READERS

SP = 20.0
ON = {"OMR_KEY_SIGNATURE_CLAIM": "1", "OMR_CLAIMED_REGISTER": "1", "OMR_KEY_PER_SYSTEM": "1"}
OFF = dict(ON, OMR_KEY_PER_SYSTEM="0")
CLEF_X0, CLEF_X1 = 30, 90                       # the clef block
FLAT0, PITCH = 100, 24                         # first flat's left edge, slot pitch
W, H = 700, 1400


def lines_of(i):
    top = 100 + 300 * i
    return [top + SP * j for j in range(5)]


def raster(flats_per_staff, *, extra=(), n=3):
    img = np.full((H, W), 255, np.uint8)
    for i in range(n):
        for y in lines_of(i):
            img[int(y):int(y) + 2, 20:W - 20] = 0
        img[int(lines_of(i)[0]) - 8:int(lines_of(i)[4]) + 8, CLEF_X0:CLEF_X1] = 0           # a clef block (too wide to be an accidental)
        for s in range(flats_per_staff[i]):
            x = FLAT0 + PITCH * s
            top = int(lines_of(i)[1]) - 10 + (s % 2) * 6
            img[top:top + 50, x:x + 18] = 0
    for (x0, y0, x1, y1) in extra:
        img[y0:y1, x0:x1] = 0
    return img


class _Det:
    def __init__(self, name, x, y, w, h):
        self.smufl_name, self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = name, x, y, w, h
        self.confidence, self.category = 0.9, ""


class _Cell:
    def __init__(self, k, staff, bbox=(0.0, 0.0, float(W), float(H))):
        self.staff_index, self.measure_index, self.page_index, self.bbox_page_px, self.upscale_factor = staff, k, 1, bbox, 1.0


class _Staff:
    def __init__(self, i):
        self.staff_index, self.system_index, self.line_ys = i, 0, lines_of(i)


class _PWS:
    class page:
        page_index = 1
    staves: list


def clef_box(i):
    t = lines_of(i)[0] - 8
    return ("clefG", CLEF_X0, t, CLEF_X1 - CLEF_X0, 96)


def flat_box(i, s, cls="keyFlat"):
    top = lines_of(i)[1] - 10 + (s % 2) * 6
    return (cls, FLAT0 + PITCH * s, top, 18, 50)


def rest_on_slot(i, s):
    f = flat_box(i, s)
    return ("rest8th", f[1] + 6, f[2] + 10, 18, 22)             # 0.3 space off the slot: past the 2.100 next-slot rule's 0.2


def gather(flats, boxes_by_staff, *, env=ON, dossier=None, extra=(), n=3):
    log = Log()
    pws = _PWS()
    pws.page.binary = raster(flats, extra=extra, n=n)
    pws.staves = [_Staff(i) for i in range(n)]
    cells, dets, gids = [], {}, {}
    for i in range(n):
        log.observe(R.cell(1, 0, i, 0), Q.CELL_STAFF_SPACE, SP, reader=READERS.GEOMETRY, frame="cell:0")
        cells.append(_Cell(0, i))
        ds = []
        for gi, box in enumerate(boxes_by_staff[i]):
            g = R.glyph(1, 0, i, 0, gi)
            log.observe(g, Q.GLYPH_BOX, tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.5, category="x",
                        bbox_page_px=[box[1], box[2], box[1] + box[3], box[2] + box[4]])
            if box[0].startswith("rest"):
                log.observe(g, Q.REST, box[0], reader=READERS.DETECTOR, frame="cell:0", score=0.5, category="rest")
            log.observe(g, Q.GLYPH_CONF, 0.9, reader=READERS.DETECTOR, frame="cell:0")
            gids[(i, gi)] = g
            ds.append(_Det(*box))
        dets[R.cell(1, 0, i, 0).to_key()] = ds
    with mock.patch.dict(os.environ, env):
        G.gather_key_signature_claim(log, pws, cells, {k: (0, k) for k in range(n)}, dets)
        G.gather_key_object(log, pws, cells, {k: (0, k) for k in range(n)}, dets, dossier=dossier)
    return log, gids


def rows(log, i, source="system_key_object"):
    return [r for r in log.rows(Q.CLAIMED_AREA, R.staff(1, 0, i)) if (r.detail or {}).get("source") == source]


def decide(log, env, q):
    log.freeze()
    adjudicate._ensure_decisions()
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log, order=(q,))


# The detector read three flats on staves 0 and 1, but on staff 2 it boxed two as flats and the third as a REST (the 2.183 cause).
def _full(flats=(3, 3, 2)):
    out = [[clef_box(i)] + [flat_box(i, s) for s in range(flats[i])] for i in range(3)]
    if flats[2] == 2:
        out[2].append(rest_on_slot(2, 2))
    return out


class TestFlag(unittest.TestCase):
    def test_default_off_and_files_through_the_claim(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OMR_KEY_PER_SYSTEM", None)
            self.assertFalse(KO.enabled())
        log, _ = gather([3, 3, 3], _full((3, 3, 3)), env=OFF)
        self.assertEqual([rows(log, i) for i in range(3)], [[], [], []])
        log, _ = gather([3, 3, 3], _full((3, 3, 3)), env=dict(ON, OMR_KEY_SIGNATURE_CLAIM="0"))
        self.assertEqual([rows(log, i) for i in range(3)], [[], [], []])          # the 2.183 claim is the register's door


class TestCountFromTheSystem(unittest.TestCase):
    def test_three_staves_agree_on_three_slots(self):
        log, _ = gather([3, 3, 3], _full((3, 3, 3)))
        for i in range(3):
            d = rows(log, i)[0].detail
            self.assertEqual((d["system_count"], d["standing"], d["slots"]), (3, "READ", 3))
            self.assertEqual(d["dossier"], "silent")

    def test_a_staff_that_read_fewer_slots_claims_the_systems_count(self):
        log, _ = gather([3, 3, 2], _full((3, 3, 2)))
        d = rows(log, 2)[0].detail
        self.assertEqual((d["own_slots"], d["placed_slots"], d["slots"]), (2, 1, 3))
        a = rows(log, 2)[0].value
        self.assertGreater(a[2], FLAT0 + PITCH * 2 + 18)                          # the area reaches the third slot's right edge

    def test_a_staff_that_read_none_is_narrowed_never_read(self):
        log, _ = gather([3, 3, 0], [_full()[0], _full()[1], [clef_box(2)]])
        d = rows(log, 2)[0].detail
        self.assertEqual((d["own_slots"], d["standing"]), (0, "NARROWED"))

    def test_one_staff_alone_with_the_dossier_silent_is_not_the_system(self):
        log, _ = gather([3, 2, 2], [_full()[0], [clef_box(1), flat_box(1, 0), flat_box(1, 1)], _full()[2][:3]])
        self.assertEqual(rows(log, 0)[0].detail["system_count"], 2)                # the pair's count, not the lone staff's

    def test_one_staff_and_the_dossier_make_three(self):
        log, _ = gather([3, 2, 2], [_full()[0], [clef_box(1), flat_box(1, 0), flat_box(1, 1)], _full()[2][:3]], dossier={"parts": [{"written_fifths": -3}, {"written_fifths": -1}]})
        d = rows(log, 1)[0].detail
        self.assertEqual((d["system_count"], d["count_basis"], d["dossier"]), (3, "one_staff_and_dossier", "agrees"))

    def test_the_dossier_disagreeing_abstains_the_system_and_counts_it(self):
        log, _ = gather([3, 3, 3], _full((3, 3, 3)), dossier={"parts": [{"written_fifths": -1}, {"written_fifths": 0}]})
        self.assertEqual([rows(log, i) for i in range(3)], [[], [], []])
        ab = [a for a in log._abs.values() if a.reason == ABSTAIN.NO_COLUMN_EVIDENCE and a.detail.get("why") == "dossier_disagrees"]
        self.assertEqual(len(ab), 3)

    def test_a_transposing_staff_with_one_flat_is_not_given_the_concert_key_as_a_reading(self):
        # staff 2 prints ONE flat (a clarinet): the system's 3 is placed as an area for refusing boxes, never as a key written to the staff
        log, _ = gather([3, 3, 1], [_full()[0], _full()[1], [clef_box(2), flat_box(2, 0)]])
        d = rows(log, 2)[0].detail
        self.assertEqual((d["own_slots"], d["placed_slots"]), (1, 2))
        self.assertEqual(len([r for r in log.rows(Q.KEY_SIGNATURE, R.staff(1, 0, 2))]), 0)

    def test_CONTROL_a_c_major_system_claims_nothing(self):
        log, _ = gather([0, 0, 0], [[clef_box(i)] for i in range(3)])
        self.assertEqual([rows(log, i) for i in range(3)], [[], [], []])

    def test_CONTROL_a_first_piece_far_from_the_clef_is_a_note_not_a_slot(self):
        far = [(CLEF_X1 + 70, int(lines_of(i)[1]), CLEF_X1 + 88, int(lines_of(i)[1]) + 50) for i in range(3)]
        log, _ = gather([0, 0, 0], [[clef_box(i)] for i in range(3)], extra=far)
        self.assertEqual([rows(log, i) for i in range(3)], [[], [], []])

    def test_a_bar_head_key_change_is_found_the_same_way(self):
        # constructed mid-system change: x_start is the barline's right edge, no clef; the object reader is bar-agnostic
        img = np.full((H, W), 255, np.uint8)
        stv = []
        for i in range(3):
            for y in lines_of(i):
                img[int(y):int(y) + 2, 20:W - 20] = 0
            for s in range(2):
                img[int(lines_of(i)[1]) - 10:int(lines_of(i)[1]) + 40, 300 + PITCH * s:318 + PITCH * s] = 0
            stv.append({"key": i, "lines": lines_of(i), "spacing": SP, "x_start": 296.0, "x_hi": 296.0 + 11 * SP})
        obj = KO.find_object(img, stv)
        self.assertEqual((obj["status"], obj["N"]), ("found", 2))


class TestTheConsult(unittest.TestCase):
    """The cause, reproduced: the rest on the third flat of staff 2 is written as a rest unless the system's count reaches it."""

    def _rest(self, env, boxes=None, flats=(3, 3, 2)):
        log, g = gather(list(flats), boxes or _full(), env=env)
        decide(log, env, Q.REST_IS_NOT_A_REST)
        return log.verdict(Q.REST_IS_NOT_A_REST, g[(2, 3)])

    def test_the_rest_on_the_third_flat_is_refused_only_with_the_system_reader(self):
        # the raster has only 2 flats on staff 2 (the third is the bowl the detector boxed as a rest, drawn here as ink too)
        boxes = _full()
        off = self._rest(OFF, boxes)
        on = self._rest(ON, boxes)
        self.assertEqual(on.reason, "claimed_by:key_signature")
        self.assertGreater(on.margin, 0)
        self.assertNotEqual(off.reason, "claimed_by:key_signature")

    def test_CONTROL_a_real_rest_after_the_signature_is_kept_both_ways(self):
        boxes = _full()
        boxes[2] = boxes[2][:3] + [("rest8th", FLAT0 + PITCH * 3 + 90, lines_of(2)[1], 18, 22)]
        for env in (OFF, ON):
            log, g = gather([3, 3, 2], boxes, env=env)
            decide(log, env, Q.REST_IS_NOT_A_REST)
            v = log.verdict(Q.REST_IS_NOT_A_REST, g[(2, 3)])
            self.assertEqual((v.value, v.reason), (False, "rest"), env)

    def test_a_box_in_a_narrowed_area_is_narrowed_not_refused(self):
        boxes = [_full()[0], _full()[1], [clef_box(2), rest_on_slot(2, 1)]]
        log, g = gather([3, 3, 0], boxes)
        decide(log, ON, Q.REST_IS_NOT_A_REST)
        v = log.verdict(Q.REST_IS_NOT_A_REST, g[(2, 1)])
        self.assertEqual((v.outcome, v.reason), ("narrowed", "claim_narrowed:key_signature"))


if __name__ == "__main__":
    unittest.main()
