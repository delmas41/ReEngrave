"""ROADMAP 2.68 (Sean's DEDUCTIVE rule, 2026-10-09): a dynamic-classed box is a
letter of a word only when it has letter ink beside it AND lies in a token of a
word the OCR read and the lexicon accepted.

The 10-bar judgement (`out/print/2.68-dynamics-back/`, Sean blind) showed the
rule giving a `p` back where it was real and making five bars worse. Measured on
Brahms p0 `f espr. e legato` (read `f p f`): the `p` of `espr.` had NO letter
neighbour because `gather._ink_without_detections` blanked every detection
under a quarter of the page width -- the slur box over the bar (30 spaces wide),
a `restWhole` box on the `r`, and the detector's own dynamic boxes on the other
letters -- so the word's letters were erased before the neighbour test looked.

One rule decides which boxes may hide a word's letters
(`direction_text.letter_hiding_kind`), read at both sites. Each test sits beside
the case it must leave alone: a real `p dolce`, a real `fp` / `ff`, a lone `p`.

RED against the tree before the commit: the neighbour tests (the slur and
dynamic boxes blanked the word), `letter_hiding_kind` (did not exist) and the
text half (`_letter_of_a_known_word` did not exist; `ff legato` and `f espr.`
were decided by the neighbour test alone).
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from tools.omr import direction_text as DT
from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import text as T
from tools.omr.staged.record import Log, Q, READERS, Scope

SP = 20.0               # one staff space, px
PAGE_W, PAGE_H = 3000, 900
TEXT_Y = 520            # the text line, under a staff whose lines are y 400..480


# ── the ONE rule ────────────────────────────────────────────────────────────

def test_one_rule_says_which_boxes_may_hide_a_words_letters():
    k = DT.letter_hiding_kind
    assert k("slur", 30 * SP, SP) == "span"          # wider than 4 spaces
    assert k("beam", 37 * SP, SP) == "span"
    assert k("clef", 3 * SP, SP) == "letterlike"
    assert k("rest", 2 * SP, SP) == "letterlike"
    assert k("time_sig_digit", 1.5 * SP, SP) == "letterlike"
    assert k("ornament", 2 * SP, SP) == "letterlike"
    assert k("dynamic", 2 * SP, SP) == "dynamic"
    # control: notation stays blanked, or a note beside a word joins the word
    assert k("note", 1.3 * SP, SP) is None
    assert k("accidental", 1.2 * SP, SP) is None
    assert k("flag", 1.8 * SP, SP) is None


# ── GATHER: the neighbour test sees the word's own letters ──────────────────

class _Det:
    def __init__(self, name, category, x, y, w, h):
        self.smufl_name, self.category = name, category
        self.x_canonical, self.y_canonical = x, y - 300.0       # cell origin y = 300
        self.width_canonical, self.height_canonical = w, h
        self.confidence = 0.8
        self.x_center, self.y_center = x + w / 2, y + h / 2


def _page(ink):
    """A white page with black `ink` rectangles (x, y, w, h)."""
    rgb = np.full((PAGE_H, PAGE_W, 3), 255, np.uint8)
    for x, y, w, h in ink:
        rgb[y:y + h, x:x + w] = 0
    return rgb


def _neighbours(ink, dets, which):
    """`Q.DYNAMIC_LETTER_NEIGHBOURS` of the `which`-th dynamic-letter detection,
    through the real gatherer."""
    staff = SimpleNamespace(staff_index=0, system_index=0, line_ys=[400, 420, 440, 460, 480],
                            top_y=400, x_start=0, x_end=PAGE_W, line_thickness_px=None,
                            line_wander_px=None)
    pws = SimpleNamespace(page=SimpleNamespace(page_index=0, binary=None, rgb=_page(ink)),
                          staves=[staff])
    cell = SimpleNamespace(staff_index=0, page_index=0, measure_index=0,
                           bbox_page_px=[0.0, 300.0, float(PAGE_W), 700.0],
                           upscale_factor=1.0, image_no_staff=None)
    log = Log()
    G.gather_dynamic_letters(log, pws, [cell], {0: (0, 0)}, {R.cell(0, 0, 0, 0).to_key(): dets})
    rows = [r for r in log.rows(Q.DYNAMIC_LETTER_NEIGHBOURS, R.cell(0, 0, 0, 0),
                                scope=Scope.SELF_AND_DESCENDANTS)]
    rows.sort(key=lambda r: r.subject.to_key())
    return rows[which].value


def _espr(x0=1000):
    """`e s p r` at 4 px apart, 12 px wide, x-height 26 px; the `p` is #2."""
    return [(x0 + i * 16, TEXT_Y, 12, 26) for i in range(4)]


def test_the_p_of_espr_has_a_neighbour_though_a_slur_box_lies_over_the_text():
    """Brahms p0: a 30-space slur box and the detector's other boxes on the
    word's letters erased `s` and `r` before the `p` looked. RED before."""
    ink = _espr()
    dets = [_Det("dynamicP", "dynamic", 1032, TEXT_Y, 12, 26),
            _Det("slur", "slur", 700, TEXT_Y - 6, 600, 40),          # over the bar
            _Det("restWhole", "rest", 1044, TEXT_Y + 8, 16, 10)]     # on the `r`
    s = _neighbours(ink, dets, 0)
    assert s["left"] and s["right"], s


def test_letters_of_a_word_the_detector_boxed_as_dynamics_are_each_others_neighbours():
    ink = _espr()
    dets = [_Det("dynamicS", "dynamic", 1016, TEXT_Y, 12, 26),
            _Det("dynamicP", "dynamic", 1032, TEXT_Y, 12, 26),
            _Det("dynamicR", "dynamic", 1048, TEXT_Y, 12, 26)]
    assert _neighbours(ink, dets, 1)["left"] and _neighbours(ink, dets, 1)["right"]


def test_CONTROL_a_p_standing_alone_has_no_neighbour_under_the_same_slur_box():
    """The positive control: the slur box over the bar no longer erases
    anything, and it also invents nothing -- a `p` by itself stays by itself."""
    ink = [(1032, TEXT_Y, 12, 26)]
    dets = [_Det("dynamicP", "dynamic", 1032, TEXT_Y, 12, 26),
            _Det("slur", "slur", 700, TEXT_Y - 6, 600, 40)]
    s = _neighbours(ink, dets, 0)
    assert not s["left"] and not s["right"], s


def test_CONTROL_a_dynamic_standing_clear_of_a_word_is_not_its_neighbour():
    """`p dolce`: the word starts 1.2 spaces after the `p`."""
    ink = [(1000, TEXT_Y, 12, 26)] + [(1036 + i * 16, TEXT_Y, 12, 26) for i in range(5)]
    dets = [_Det("dynamicP", "dynamic", 1000, TEXT_Y, 12, 26)]
    s = _neighbours(ink, dets, 0)
    assert not s["right"] and s["right_spaces"] is not None and s["right_spaces"] > 0.5


def test_CONTROL_a_note_beside_a_dynamic_is_still_not_a_letter():
    """Notation stays blanked: a notehead 0.2 spaces from the `p` is no letter."""
    ink = [(1000, TEXT_Y, 12, 26), (1016, TEXT_Y + 6, 26, 18)]
    dets = [_Det("dynamicP", "dynamic", 1000, TEXT_Y, 12, 26),
            _Det("noteheadBlack", "note", 1016, TEXT_Y + 6, 26, 18)]
    assert not _neighbours(ink, dets, 0)["right"]


def test_one_printed_p_boxed_twice_is_not_its_own_neighbour():
    """Brahms p1 `fp p`: the detector boxed ONE ink as `dynamicP` and `dynamicF`."""
    ink = [(1000, TEXT_Y, 12, 26)]
    dets = [_Det("dynamicP", "dynamic", 1000, TEXT_Y, 12, 26),
            _Det("dynamicF", "dynamic", 1001, TEXT_Y, 11, 26)]
    s0, s1 = _neighbours(ink, dets, 0), _neighbours(ink, dets, 1)
    assert not (s0["left"] or s0["right"] or s1["left"] or s1["right"])


def test_a_barline_through_a_word_does_not_hide_the_letter_beside_it():
    """Brahms p0 `legato` across a barline: the `t` touches the line, the `o`
    stands just past it. The line's component is staves tall, so the `t` was no
    neighbour of the `o` (tiles 6 and 8: a `p` in a bar with no dynamic)."""
    ink = [(1000, TEXT_Y, 12, 26), (1020, TEXT_Y, 12, 26),      # `a`, `t`
           (1032, 380, 4, 200),                                  # the barline, touching the `t`
           (1038, TEXT_Y, 12, 26)]                               # the `o`
    dets = [_Det("dynamicP", "dynamic", 1038, TEXT_Y, 12, 26)]
    s = _neighbours(ink, dets, 0)
    assert s["left"], s


def test_CONTROL_a_barline_alone_is_not_a_neighbour():
    ink = [(1032, 380, 4, 200), (1038, TEXT_Y, 12, 26)]
    dets = [_Det("dynamicP", "dynamic", 1038, TEXT_Y, 12, 26)]
    s = _neighbours(ink, dets, 0)
    assert not s["left"] and not s["right"], s


# ── ADJUDICATE: the word's TEXT says which letter is the dynamic ────────────

def _decide(letters, words, neighbours=None):
    """`Q.DYNAMIC` of one bar. `letters` = [(letter, x0, x1)], `words` =
    [(text, x0, x1)]; every letter has a letter beside it unless `neighbours`
    says otherwise ({index: (left, right)})."""
    log = Log()
    cell = R.cell(0, 0, 0, 0)
    for i, (letter, x0, x1) in enumerate(letters):
        g = R.glyph(0, 0, 0, 0, i)
        log.observe(g, Q.DYNAMIC_LETTER, "dynamic" + letter.upper(),
                    reader=READERS.DETECTOR, frame=G.FRAME_PAGE, score=0.8,
                    letter=letter, cell_frame="cell:0",
                    bbox_page_px=[x0, 100.0, x1, 150.0], x_center_page=(x0 + x1) / 2,
                    y_center_page=125.0, staff_bottom_line_page=90.0,
                    staff_spacing_px=SP, band_offset_spaces=1.7, in_hairpin_band=True)
        left, right = (neighbours or {}).get(i, (True, True))
        log.observe(g, Q.DYNAMIC_LETTER_NEIGHBOURS,
                    {"left": left, "right": right, "left_spaces": None, "right_spaces": None},
                    reader=READERS.CV_LETTER_NEIGHBOURS, frame=G.FRAME_PAGE)
    for j, (text, x0, x1) in enumerate(words):
        log.observe(R.glyph(0, 0, 0, 0, 900 + j), Q.DIRECTION_WORD, text,
                    reader=READERS.TESSERACT, frame="page",
                    bbox_page_px=[x0, 95.0, x1, 155.0], category="expression")
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.DYNAMIC, cell).value


def test_no_dynamic_in_the_text_means_every_dynamic_box_inside_it_is_a_letter():
    """`espr. e legato` (Brahms p0): the `p` of `espr.` and the `g` boxed as a
    dynamic are the word's. RED before the text half was wired."""
    assert _decide([("p", 1771, 1818), ("f", 2000, 2041)],
                   [("espr. e legato", 1712, 2153)]) == []


def test_a_leading_dynamic_token_is_the_dynamic_and_the_rest_is_the_word():
    """`f espr. e legato`: the `f` at the left is piano-forte's; the `p` inside
    `espr.` is the word's."""
    assert _decide([("f", 1624, 1692), ("p", 1767, 1815), ("f", 1995, 2038)],
                   [("f espr. e legato", 1622, 2146)]) == ["f"]


def test_CONTROL_a_dynamic_and_a_word_read_as_one_text_keep_the_dynamic():
    """`P dolce`, `p cresc. f`, `f legato`: the dynamic token is at an end."""
    assert _decide([("p", 2398, 2429)], [("P dolce", 2398, 2540)],
                   neighbours={0: (False, False)}) == ["p"]
    assert _decide([("p", 637, 671), ("f", 782, 818)], [("p cresc. f", 622, 823)],
                   neighbours={0: (False, True), 1: (True, False)}) == ["p", "f"]


def test_CONTROL_a_real_run_of_dynamics_in_a_joined_reading_stays_a_dynamic():
    """`ff legato` / `fp espr.`: the two letters touch (each is the other's
    neighbour) -- the TEXT keeps them, where the ink alone would take both."""
    assert _decide([("f", 1000, 1040), ("f", 1042, 1082)], [("ff legato", 1000, 1400)],
                   neighbours={0: (False, True), 1: (True, False)}) == ["ff"]
    assert _decide([("f", 1000, 1040), ("p", 1042, 1082)], [("fp espr.", 1000, 1400)],
                   neighbours={0: (False, True), 1: (True, False)}) == ["fp"]


def test_CONTROL_a_letter_with_nothing_beside_it_stays_a_dynamic_inside_a_word_box():
    """Sean: *a `p` by itself is piano*. The OCR's tight box covers `p dolce`
    but its text lost the `p`: the ink has clear space beside the `p`."""
    assert _decide([("p", 2398, 2429)], [("dolce", 2398, 2540)],
                   neighbours={0: (False, False)}) == ["p"]


def test_CONTROL_no_word_read_nothing_changes():
    assert _decide([("p", 1771, 1818)], []) == ["p"]


def test_conflicting_words_over_the_same_ink_decide_nothing():
    """A joined reading (`f espr.`) and a tight sibling window (`espr.`) over
    one `f`: the readings disagree about that spot, so it stays the detector's."""
    assert _decide([("f", 1624, 1692)],
                   [("f espr.", 1622, 2000), ("espr.", 1600, 2000)]) == ["f"]


def test_the_token_helper_ends_only():
    box = (1622.0, 100.0, 2146.0, 150.0)
    assert not T._token_is_a_word((1624, 100, 1692, 150), box, "f espr. e legato")
    assert T._token_is_a_word((1767, 100, 1815, 150), box, "f espr. e legato")
    assert T._token_is_a_word((1767, 100, 1815, 150), box, "espr. e legato")
    assert not T._token_is_a_word((2100, 100, 2146, 150), box, "dolce f")
    assert not T._token_is_a_word((1624, 100, 1692, 150), box, "p")   # the text IS a dynamic
