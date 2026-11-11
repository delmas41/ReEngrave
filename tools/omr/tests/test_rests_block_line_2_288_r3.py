"""ROADMAP 2.288 round 3 -- a whole / half rest's BLOCK is named when the detector box holds the block but the page stroke is the block PLUS a slab of its staff line
(`page_claim_names.block_rest_strokes`, wired in `gather_page_claim_boxes` under `OMR_PAGE_CLAIM_RESTS`).

Cause (Brahms p14, 26 whole-rest boxes naming no stroke): the stroke map erases a staff line only where nothing but the line crosses it, so where a block meets its line the stroke is
block + line slab, and the box is round the block alone: under half the STROKE is in the box. The ink share is asked of the block (line rows set aside).

Pins, each with a control that can fail: the block is claimed; the same box with too little of the BLOCK in it is not; a note head fused to the line and boxed as a whole rest is
not (shape), a long beam piece boxed as a half rest is not (shape); with no raster the answer is the old by-stroke one (it can only add).
"""
import os
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tools.omr.staged import page_claim_names as PCN
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_page_claim_boxes_and_m4b_2_269 import Cell, det, filed, pagemap
from tools.omr.tests.test_rests_claim_first_2_288 import QUARTER_REST
from tools.omr.tests.test_rests_claim_step_2_288 import contact, pagemap_full


def page(rows_dark, block=None, size=200):
    """A white raster with a full-width staff line on `rows_dark` and a dark block (x0, y0, x1, y1)."""
    raw = np.full((size, size), 255, np.uint8)
    for r in rows_dark:
        raw[r, :] = 0
    if block:
        x0, y0, x1, y1 = block
        raw[y0:y1, x0:x1] = 0
    return SimpleNamespace(page=SimpleNamespace(page_index=0, binary=raw))


def run(dets, pm, pws, log=None):
    log = log or Log()
    contact(log, 0, QUARTER_REST)                                       # the cell raster's own witness: it stands free
    with mock.patch.dict(os.environ, {PCN.ENV_RESTS: "1", PCN.ENV_BOXES: "0", PCN.ENV: "0"}):
        cen = PCN.gather_page_claim_boxes(log, pws, [Cell()], {0: (0, 0)}, {R.cell(0, 0, 0, 0).to_key(): dets}, pm)
    return log, cen


# sp = 20 px: a block 10 px (0.5 sp) under a 4 px line slab = a stroke 14 px (0.7 sp) tall, 30 px (1.5 sp) wide, as on Brahms p14
BLOCK = (80, 50, 110, 64)
LINE = range(50, 54)


def test_the_block_is_claimed_when_the_box_holds_the_block_and_not_the_line_slab():
    pm = pagemap_full([(80, 50, 30, 14)])
    pws = page(LINE, block=BLOCK)
    log, cen = run([det("restWhole", 80, 56, 30, 6)], pm, pws)                   # 6 of the block's 10 rows: 0.6 of the block, 6/14 = 0.43 of the stroke
    rows = filed(log)
    assert len(rows) == 1 and rows[0].value == [0] and rows[0].detail["owner"] == "whole_rest"
    assert cen["rest_read"] == 1 and cen["rest_block_named"] == 1 and cen["rest_weak"] == {}
    # control that can fail: with no raster the answer is the old by-stroke one, which refuses it (names no stroke)
    log, cen = run([det("restWhole", 80, 56, 30, 6)], pm, SimpleNamespace(page=SimpleNamespace(page_index=0)))
    assert filed(log) == [] and cen["rest_weak"] == {"names_no_stroke": 1} and cen["rest_block_named"] == 0


def test_a_box_that_holds_too_little_of_the_block_is_still_refused():
    pm = pagemap_full([(80, 50, 30, 14)])
    pws = page(LINE, block=BLOCK)
    log, cen = run([det("restWhole", 80, 58, 30, 3)], pm, pws)                   # 3 of 10 block rows
    assert filed(log) == [] and cen["rest_weak"] == {"names_no_stroke": 1}


def test_a_half_rest_sitting_on_its_line_is_read_the_same_way():
    pm = pagemap_full([(80, 40, 30, 14)])                                         # block rows 40-49, line slab rows 50-53 below it
    pws = page(LINE, block=(80, 40, 110, 54))
    log, cen = run([det("restHalf", 80, 40, 30, 6)], pm, pws)
    rows = filed(log)
    assert len(rows) == 1 and rows[0].value == [0] and cen["rest_block_named"] == 1


def test_a_head_fused_to_the_line_and_boxed_as_a_whole_rest_stays_refused():
    # a note head on a line: 24 px (1.2 sp) tall, 24 wide; the box is round its lower part
    pm = pagemap_full([(80, 50, 24, 24)])
    pws = page(LINE, block=(80, 50, 104, 74))
    log, cen = run([det("restWhole", 80, 64, 24, 10)], pm, pws)
    assert filed(log) == [] and cen["rest_weak"] == {"names_no_stroke": 1} and cen["rest_block_named"] == 0


def test_a_beam_piece_boxed_as_a_half_rest_stays_refused():
    pm = pagemap_full([(40, 50, 90, 14)])                                         # 4.5 sp long: not a block
    pws = page(LINE, block=(40, 50, 130, 64))
    log, cen = run([det("restHalf", 60, 56, 40, 6)], pm, pws)
    assert filed(log) == [] and cen["rest_weak"] == {"names_no_stroke": 1} and cen["rest_block_named"] == 0


def test_block_share_is_the_old_share_where_there_is_no_line():
    pm = pagemap([(80, 50, 30, 14)])
    pws = page([], block=BLOCK)
    idx = PCN.StrokeIndex(*PCN._boxes_of(pm))
    box = (80, 56, 110, 62)
    assert PCN.block_rest_strokes(pm, box, idx, pws.page.binary, 0.5) == PCN.strokes_by_share(pm, box, idx, 0.5) == []
    box = (80, 52, 110, 62)
    assert PCN.block_rest_strokes(pm, box, idx, pws.page.binary, 0.5) == PCN.strokes_by_share(pm, box, idx, 0.5) == [0]
    assert PCN.block_rest_strokes(pm, box, idx, None, 0.5) == [0]
