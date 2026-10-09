"""A notehead whose INK is a detected dynamic letter's stroke is not a note
(Sean 2026-10-09, `out/print/2.73-review` tile 10: *"Not a note - dynamic p"*).
STAGED. GATHER measures (`gather.gather_notehead_letter_ink`, `Q.NOTEHEAD_
LETTER_INK`), ADJUDICATE decides (`notehead_precision._on_a_dynamic_letter_
refusal`, reason `on_a_dynamic_letter`).

SECOND BUILD. The first build decided on BOXES -- a head inside a letter box
refused unless a 3-space CV stem touched it or the box was over 3.6 x 4.6
spaces -- and Sean, judging its blind tiles, said two heads it refused were
*"two small notes just to the right of SF"*: they lie inside the `sf`'s wide
box, the CV stem rows missed one of them, and the letter's box is wider than
its ink. RED, run against that build on the real record (Litolff pdf page 3,
`glyph/2/1/9/6/9`, `head_in_letter` 1.0): `notehead -> on_a_dynamic_letter`, the
wrong refusal. The tests below are RED on that tree for the plain reason that
`Q.NOTEHEAD_LETTER_INK` / `gather_notehead_letter_ink` do not exist there.

THE QUESTION IS ASKED OF THE INK: is the head's ink a stroke (the hook of an `f`)
or the letter's body (the bowl of a `p`), or a filled head of its own?

CONTROLS THAT CAN FAIL, each beside a refusal of the SAME class and geometry:
the two notes beside an `sf` stay; a SMALL (cue-size) filled head with no stem
at all stays (nothing here reads a stem); a head only touching a letter stays.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.record import Log, Outcome, Q, READERS, Scope
from tools.omr.tests.test_staged_notehead_precision import (
    CELL, SPACING, _cell_geometry, _verdict)

SP = 16.0   # page px per staff space on the synthetic rasters


# ── the pure measurement, on rasters whose answer is known ─────────────────

def _disc(img, cx, cy, r):
    yy, xx = np.ogrid[:img.shape[0], :img.shape[1]]
    img[(xx - cx) ** 2 + (yy - cy) ** 2 <= r * r] = 255


def _stroke(img, x0, y0, x1, y1, t=3):
    n = int(max(abs(x1 - x0), abs(y1 - y0)))
    for i in range(n + 1):
        x = int(round(x0 + (x1 - x0) * i / max(1, n)))
        y = int(round(y0 + (y1 - y0) * i / max(1, n)))
        img[y - t // 2:y + t // 2 + 1, x - t // 2:x + t // 2 + 1] = 255


def _sf_page():
    """An `sf`-like wide letter box: a thin slanted stroke on the LEFT (the `f`)
    and a filled head of its own on the RIGHT, inside the same box."""
    img = np.zeros((200, 300), np.uint8)
    _stroke(img, 60, 140, 90, 70, t=5)       # the f's stem, thin
    _stroke(img, 90, 70, 105, 62, t=5)       # its hook
    _stroke(img, 55, 105, 80, 100, t=5)      # its crossbar
    _stroke(img, 52, 125, 75, 118, t=5)      # the `s` before it
    _stroke(img, 52, 125, 55, 105, t=5)
    _disc(img, 150, 100, 10)                 # a head: 1.25 spaces across
    return img, (50.0, 55.0, 170.0, 150.0), (140.0, 90.0, 161.0, 110.0)


def test_a_filled_head_inside_a_wide_box_is_a_head_of_its_own():
    img, letter, head = _sf_page()
    m = G.head_letter_ink(img, head, letter, SP)
    assert m["disc_spaces"] >= 1.15, m
    assert m["letter_ink_share"] < 0.4, m


def test_the_hook_of_an_f_is_a_stroke():
    """Positive control for the refusal: the SAME page, the head box moved onto
    the thin hook. Same raster, same letter box, the answer flips."""
    img, letter, _head = _sf_page()
    m = G.head_letter_ink(img, (88.0, 58.0, 108.0, 74.0), letter, SP)
    assert m["disc_spaces"] < NP.DYNAMIC_LETTER_STROKE_DISC_SPACES, m


def test_the_bowl_of_a_p_is_most_of_the_letter():
    img = np.zeros((200, 200), np.uint8)
    _disc(img, 100, 90, 9)                   # the bowl, as thick as a head
    _stroke(img, 92, 90, 92, 125)            # the descender
    m = G.head_letter_ink(img, (88.0, 78.0, 112.0, 102.0), (84.0, 78.0, 116.0, 128.0), SP)
    assert m["disc_spaces"] >= NP.DYNAMIC_LETTER_STROKE_DISC_SPACES, \
        "the bowl is as filled as a head: the disc alone cannot refuse it"
    assert m["letter_ink_share"] >= NP.DYNAMIC_LETTER_BODY_SHARE, m


def test_a_blank_crop_or_no_spacing_measures_nothing():
    img = np.zeros((50, 50), np.uint8)
    assert G.head_letter_ink(img, (10, 10, 20, 20), (5, 5, 30, 30), 0.0) is None


# ── GATHER: a row only where a head lies on a letter ───────────────────────

PAGE_W, PAGE_H = 400, 700


class _Det:
    def __init__(self, name, category, x, y, w, h):
        self.smufl_name, self.category = name, category
        self.x_canonical, self.y_canonical = x, y - 300.0       # cell origin y = 300
        self.width_canonical, self.height_canonical = w, h
        self.confidence = 0.8
        self.x_center, self.y_center = x + w / 2, y + h / 2


def _gathered(page_ink, dets):
    staff = SimpleNamespace(staff_index=0, system_index=0,
                            line_ys=[400, 416, 432, 448, 464], top_y=400,
                            x_start=0, x_end=PAGE_W, line_thickness_px=None,
                            line_wander_px=None)
    rgb = np.full((PAGE_H, PAGE_W, 3), 255, np.uint8)
    rgb[page_ink > 0] = 0
    pws = SimpleNamespace(page=SimpleNamespace(page_index=0, binary=None, rgb=rgb),
                          staves=[staff])
    cell = SimpleNamespace(staff_index=0, page_index=0, measure_index=0,
                           bbox_page_px=[0.0, 300.0, float(PAGE_W), 700.0],
                           upscale_factor=1.0, image_no_staff=None)
    log = Log()
    G.gather_notehead_letter_ink(log, pws, [cell], {0: (0, 0)},
                                 {R.cell(0, 0, 0, 0).to_key(): dets})
    return log


def test_gather_files_a_row_on_the_head_that_lies_on_a_letter_and_only_there():
    page = np.zeros((PAGE_H, PAGE_W), np.uint8)
    _disc(page, 150, 520, 10)                                   # the head on the letter
    _disc(page, 300, 520, 10)                                   # a head clear of it
    for x0, y0, x1, y1 in ((105, 485, 120, 540), (106, 515, 130, 523), (125, 540, 135, 550),
                           (104, 485, 116, 489), (125, 490, 135, 500)):   # the f's strokes
        page[y0:y1, x0:x1] = 255
    dets = [_Det("dynamicF", "dynamic", 100, 480, 100, 80),
            _Det("noteheadBlackInSpace", "notehead", 140, 510, 21, 21),
            _Det("noteheadBlackInSpace", "notehead", 290, 510, 21, 21)]
    log = _gathered(page, dets)
    rows = log.rows(Q.NOTEHEAD_LETTER_INK, R.cell(0, 0, 0, 0),
                    scope=Scope.SELF_AND_DESCENDANTS)
    assert [r.subject.to_key() for r in rows] == ["glyph/0/0/0/0/1"]
    r = rows[0]
    assert r.value >= 1.15 and r.detail["head_in_letter"] >= 0.9
    assert r.detail["letter"] == "glyph/0/0/0/0/0" and r.detail["letter_class"] == "dynamicF"
    assert r.detail["letter_ink_share"] < 0.4


def test_gather_files_nothing_on_a_page_with_no_letter():
    page = np.zeros((PAGE_H, PAGE_W), np.uint8)
    _disc(page, 150, 520, 10)
    log = _gathered(page, [_Det("noteheadBlackInSpace", "notehead", 140, 510, 21, 21)])
    assert not log.rows(Q.NOTEHEAD_LETTER_INK, R.cell(0, 0, 0, 0),
                        scope=Scope.SELF_AND_DESCENDANTS)


# ── ADJUDICATE: the rows already filed, the verdict they earn ──────────────

def _head(log, gi, *, cls="noteheadBlackInSpace", conf=0.4):
    g = R.glyph(CELL.page, CELL.system, CELL.staff, CELL.cell, gi)
    log.observe(g, Q.GLYPH_BOX, (cls, 200.0, 200.0, 140.0, 100.0),
                reader=READERS.DETECTOR, frame="cell:0", score=conf,
                category="notehead", bbox_page_px=[520.0, 1100.0, 660.0, 1200.0])
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR,
                frame="cell:0", score=conf)
    log.observe(g, Q.GLYPH_CONF, conf, reader=READERS.DETECTOR,
                frame="cell:0", score=conf)
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, 4.0, reader=READERS.GEOMETRY,
                frame="cell:0")
    return g


def _ink_row(log, g, disc, share, *, on=1.0, cls="dynamicF", w=2.5, h=3.0):
    log.observe(g, Q.NOTEHEAD_LETTER_INK, disc,
                reader=READERS.CV_NOTEHEAD_LETTER_INK, frame="page",
                letter_ink_share=share, head_in_letter=on,
                letter="glyph/0/0/1/0/0", letter_class=cls,
                letter_w_spaces=w, letter_h_spaces=h)


def _decide(disc, share, **kw):
    log = Log()
    _cell_geometry(log)
    g = _head(log, 0)
    _ink_row(log, g, disc, share, **kw)
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    return _verdict(log, g)


def test_the_hook_of_an_f_is_refused_as_a_stroke():
    """Litolff `glyph/2/0/1/2/9`: disc 0.74, share 0.08, an `f`'s top."""
    v = _decide(0.74, 0.08)
    assert v.outcome == Outcome.DECIDED and v.value is True
    assert v.reason == "on_a_dynamic_letter"
    assert v.detail["why"] == "stroke_not_a_filled_head"


def test_the_bowl_of_a_p_is_refused_as_the_letters_body():
    """Tile 10, `glyph/2/0/2/1/12`: disc 1.09 (as thick as a head), share 0.60."""
    v = _decide(1.09, 0.60, cls="dynamicP", w=1.85, h=1.97, on=0.576)
    assert v.value is True and v.reason == "on_a_dynamic_letter"
    assert v.detail["why"] == "head_holds_the_letters_body"


def test_the_two_notes_beside_an_sf_are_kept():
    """Tile 9 `glyph/2/1/9/6/9` (disc 1.22, share 0.11) and tile 3 `glyph/2/1/8/
    6/7` (1.27, 0.22): Sean, *two small notes just to the right of SF*. Same
    class, same letter box, same overlap as the refusals above."""
    for disc, share in ((1.22, 0.11), (1.27, 0.22)):
        v = _decide(disc, share, w=4.02, h=3.38)
        assert v.value is False and v.reason == "notehead", (disc, share)
        assert v.detail["dynamic_letter_signal"]["spared"] == "a_filled_head_of_its_own"


def test_a_small_filled_head_with_no_stem_is_kept():
    """A cue/grace-size head is a smaller filled blob (0.95) and may have a
    short stem or none: nothing here reads a stem, so it is kept."""
    v = _decide(0.95, 0.15)
    assert v.value is False and v.reason == "notehead"


def test_a_head_that_only_touches_the_letter_is_kept():
    v = _decide(0.5, 0.9, on=0.25)
    assert v.value is False and v.reason == "notehead"


def test_an_f_box_too_narrow_to_be_an_f_spares_the_head():
    """Brahms `glyph/1/0/7/0/13`: a beam's tail boxed `dynamicF`, 1.49 wide;
    positive control, the same numbers on a `dynamicP` (a `p` is that narrow)."""
    v = _decide(0.99, 0.83, w=1.49, h=3.36)
    assert v.value is False
    assert v.detail["dynamic_letter_signal"]["spared"] == "letter_box_too_narrow_for_an_f"
    v = _decide(0.99, 0.83, cls="dynamicP", w=1.49, h=3.36)
    assert v.value is True and v.reason == "on_a_dynamic_letter"


def test_a_head_with_no_letter_ink_row_is_unchanged():
    log = Log()
    _cell_geometry(log)
    g = _head(log, 0)
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD,))
    v = _verdict(log, g)
    assert v.value is False and v.reason == "notehead"


def test_the_reason_is_declared():
    assert "on_a_dynamic_letter" in adjudicate.REGISTRY[
        Q.NOTEHEAD_IS_NOT_A_NOTEHEAD].reasons
