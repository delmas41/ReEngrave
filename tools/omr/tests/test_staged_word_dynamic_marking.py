"""ROADMAP 2.68 -- a word and the dynamic beside it are ONE marking.

`consequences.pair_word_and_dynamic` (EVALUATE): Sean 2026-10-08, "same line,
close": same staff and bar, same line, nothing printed between them, at most
about 1.5 staff spaces apart; a dynamic that two words could claim stays
unpaired. Each rule beside the case it must leave alone.

RED against the unrepaired tree: `Q.MARKING` and the rule did not exist.
"""
from __future__ import annotations

from tools.omr.staged import consequences
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict

CELL = R.cell(0, 0, 1, 3)
SP = 20.0                      # one staff space, px


def _word(log, i, text, box, dynamics=(), includes=(), category="expression"):
    return log.observe(R.glyph(0, 0, 1, 3, 900 + i), Q.DIRECTION_WORD, text,
                       reader=READERS.TESSERACT, frame="page",
                       bbox_page_px=list(box), dynamics=list(dynamics),
                       includes_dynamic_glyphs=list(includes), category=category)


def _letter(log, i, letter, box):
    return log.observe(R.glyph(0, 0, 1, 3, i), Q.DYNAMIC_LETTER,
                       "dynamic" + letter.upper(), reader=READERS.DETECTOR,
                       frame="page", score=0.9, bbox_page_px=list(box),
                       staff_spacing_px=SP)


def _decide(log, runs, words):
    """The two ADJUDICATE verdicts the rule reads: `Q.DYNAMIC` with its runs,
    `Q.DIRECTION` with the bar's words."""
    log.record(Verdict(
        id=log._next_id("vrd"), subject=CELL, quantity=Q.DYNAMIC,
        outcome=Outcome.DECIDED, value=[t for t, _ids in runs],
        decider="test", reason="spelled",
        detail={"words": [{"text": t, "spelled": True, "letters": ids}
                          for t, ids in runs]}))
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=CELL, quantity=Q.DIRECTION,
        outcome=Outcome.DECIDED, value=[w.value for w in words],
        decider="test", reason="in_lexicon"))


def _marking(log, direction):
    out = consequences.pair_word_and_dynamic(log, CELL, direction)
    assert len(out) == 1 and out[0].quantity == Q.MARKING
    return out[0]


def test_a_word_and_the_dynamic_beside_it_are_one_marking():
    """Brahms p3 staff 12: `più` read alone, the `f` a few px to its right."""
    log = Log()
    w = _word(log, 0, "più", (100, 50, 175, 90))
    f = _letter(log, 1, "f", (185, 40, 230, 95))
    m = _marking(log, _decide(log, [("f", [f.id])], [w]))
    assert m.value == ["più f"]
    assert m.detail["markings"][0]["word_first"] is True


def test_a_dynamic_before_the_word_reads_first():
    log = Log()
    p = _letter(log, 1, "p", (60, 50, 90, 90))
    w = _word(log, 0, "dolce", (100, 50, 200, 90))
    assert _marking(log, _decide(log, [("p", [p.id])], [w])).value == ["p dolce"]


def test_a_dynamic_too_far_away_is_not_paired():
    log = Log()
    w = _word(log, 0, "cresc.", (100, 50, 200, 90))
    f = _letter(log, 1, "f", (200 + 2 * SP, 50, 240 + 2 * SP, 90))   # 2 spaces off
    m = _marking(log, _decide(log, [("f", [f.id])], [w]))
    assert m.value == [] and m.detail["unpaired"][0]["why"] == "no_dynamic_beside"


def test_a_dynamic_on_another_line_is_not_paired():
    log = Log()
    w = _word(log, 0, "dolce", (100, 50, 200, 90))
    p = _letter(log, 1, "p", (205, 120, 235, 160))                    # a line lower
    assert _marking(log, _decide(log, [("p", [p.id])], [w])).value == []


def test_a_dynamic_between_two_words_pairs_with_neither():
    """`dolce f espr.`: the `f` could be either word's -- EVALUATE never picks."""
    log = Log()
    w1 = _word(log, 0, "dolce", (100, 50, 200, 90))
    f = _letter(log, 1, "f", (205, 50, 235, 90))
    w2 = _word(log, 2, "espr.", (240, 50, 320, 90))
    m = _marking(log, _decide(log, [("f", [f.id])], [w1, w2]))
    assert m.value == []
    assert {u["why"] for u in m.detail["unpaired"]} == {"ambiguous"}


def test_something_printed_between_them_blocks_the_pair():
    """`dolce p f`: the `p` stands between `dolce` and the `f`, so only the
    `p` can be the word's -- the `f` is blocked, not offered."""
    log = Log()
    w = _word(log, 0, "dolce", (100, 50, 200, 90))
    p = _letter(log, 1, "p", (204, 50, 214, 90))
    f = _letter(log, 2, "f", (216, 50, 228, 90))
    m = _marking(log, _decide(log, [("p", [p.id]), ("f", [f.id])], [w]))
    assert m.value == ["dolce p"]


def test_a_dynamic_on_each_side_of_the_word_is_ambiguous():
    log = Log()
    p = _letter(log, 1, "p", (70, 50, 95, 90))
    w = _word(log, 0, "dolce", (100, 50, 200, 90))
    f = _letter(log, 2, "f", (205, 50, 235, 90))
    m = _marking(log, _decide(log, [("p", [p.id]), ("f", [f.id])], [w]))
    assert m.value == [] and m.detail["unpaired"][0]["why"] == "ambiguous"


def test_a_marking_read_whole_is_listed_and_its_dynamic_not_offered_again():
    log = Log()
    f = _letter(log, 1, "f", (185, 40, 230, 95))
    w = _word(log, 0, "più f", (100, 40, 230, 95), dynamics=["f"],
              includes=[f.subject.to_key()])
    m = _marking(log, _decide(log, [("f", [f.id])], [w]))
    assert m.value == ["più f"]
    assert m.detail["markings"][0]["reason"] == "read_together"
    assert len(m.detail["markings"]) == 1


def test_a_bar_with_no_words_writes_nothing():
    log = Log()
    f = _letter(log, 1, "f", (185, 40, 230, 95))
    direction = _decide(log, [("f", [f.id])], [])
    assert consequences.pair_word_and_dynamic(log, CELL, direction) == []


def test_the_rule_is_registered_downhill_of_the_music():
    from tools.omr.staged import evaluate as E
    E._ensure_rules()
    order = [r.consequence for r in E.execution_order()]
    assert order[-1] is E.Consequence.PAIR_WORD_AND_DYNAMIC


# ── EXPORT: the marking is written as ONE direction ───────────────────────

class _Rec:
    """The one accessor `_place_markings` uses: the verdict, as the record
    file serialises it."""

    def __init__(self, verdicts):
        self._v = verdicts

    def verdict(self, quantity, sub):
        return self._v.get((quantity, sub))


def _run_with(directions, markings):
    from tools.omr.staged import export as SX
    run = SX.StaffRun(key="s", page=0, system=0, staff=1, n_measures=4)
    cell = SX.Cell(0, 0, 1, 3)
    cell.directions = list(directions)
    run.cells = {3: cell}
    rec = _Rec({(Q.MARKING, "cell/0/0/1/3"): {"detail": {"markings": markings}}})
    SX._place_markings(rec, {"s": run})
    return SX, cell


def test_export_writes_a_paired_word_and_dynamic_as_one_direction():
    SX, cell = _run_with(
        [(100.0, "words", "più"), (185.0, "dynamics", "f")],
        [{"word": "più", "dynamics": ["f"], "word_first": True,
          "absorbs_dynamics": ["f"], "reason": "same_line_adjacent"}])
    assert [k for _x, k, _t in cell.directions] == ["marking"]
    xml = SX._direction_xml(*cell.directions[0][1:], "")
    assert xml.count("<direction ") == 1
    assert xml.index("<words>più</words>") < xml.index("<dynamics><f/></dynamics>")
    counters = {"dynamics": 0, "direction_words": 0}
    SX._count_directions(counters, cell.directions)
    assert counters == {"dynamics": 1, "direction_words": 1}


def test_export_writes_the_dynamic_first_when_it_is_printed_first():
    SX, cell = _run_with(
        [(60.0, "dynamics", "p"), (100.0, "words", "dolce")],
        [{"word": "dolce", "dynamics": ["p"], "word_first": False,
          "absorbs_dynamics": ["p"], "reason": "same_line_adjacent"}])
    xml = SX._direction_xml(*cell.directions[0][1:], "")
    assert xml.index("<dynamics><p/></dynamics>") < xml.index("<words>dolce</words>")


def test_export_leaves_a_bar_without_markings_as_it_was():
    before = [(100.0, "words", "dolce"), (300.0, "dynamics", "f")]
    _SX, cell = _run_with(before, [])
    assert cell.directions == before


def test_export_writes_a_marking_read_whole_once():
    """`più f` read in one crop: the reader's text holds both; the bar's own
    spelled `f` (the same glyph) is absorbed, not written a second time."""
    SX, cell = _run_with(
        [(100.0, "words", "più f"), (185.0, "dynamics", "f")],
        [{"text": "più f", "word": "più", "dynamics": ["f"], "word_first": True,
          "absorbs_dynamics": ["f"], "reason": "read_together"}])
    assert [k for _x, k, _t in cell.directions] == ["marking"]
    xml = SX._direction_xml(*cell.directions[0][1:], "")
    assert "<words>più</words>" in xml and xml.count("<f/>") == 1


def test_a_letter_of_the_word_boxed_as_a_dynamic_is_not_a_second_dynamic():
    """Brahms p3 staff 13: the detector boxes the `p` of `più` as `dynamicP`;
    it lies inside the word's own box and is one of its letters -- the `f`
    beside the word is still the word's one dynamic."""
    log = Log()
    w = _word(log, 0, "più", (4782, 3759, 4908, 3810))
    p = _letter(log, 1, "p", (4781, 3759, 4830, 3808))
    f = _letter(log, 2, "f", (4903, 3741, 4967, 3817))
    m = _marking(log, _decide(log, [("p", [p.id]), ("f", [f.id])], [w]))
    assert m.value == ["più f"]


# ── ADJUDICATE: a dynamic letter inside a read word is the word's letter ──

def test_a_dynamic_letter_inside_a_read_word_is_the_words_letter():
    """Brahms p3 staff 12: `dynamicP` on the `p` of `più` and `dynamicM` on its
    `ù` spelled `pmf` beside the real `f`; both lie inside the OCR'd word."""
    from tools.omr.staged.adjudicators import text as T
    log = Log()
    words = [(4777.0, 3528.0, 4901.0, 3588.0)]
    p = _letter(log, 1, "p", (4775, 3538, 4826, 3588))
    m = _letter(log, 2, "m", (4858, 3526, 4900, 3574))
    f = _letter(log, 3, "f", (4897, 3522, 4964, 3593))
    assert T._inside_a_read_word(p, words) and T._inside_a_read_word(m, words)
    assert not T._inside_a_read_word(f, words)          # the real dynamic stays
    assert not T._inside_a_read_word(p, [])             # no word read: nothing changes


def test_a_part_name_never_takes_a_dynamic():
    """Litolff, re-gather 2026-10-09: `Basso p` was paired. A part name says
    who plays; the `p` beside it is the music's dynamic."""
    log = Log()
    w = _word(log, 0, "Basso", (100, 50, 200, 90), category="part")
    p = _letter(log, 1, "p", (205, 50, 235, 90))
    assert _marking(log, _decide(log, [("p", [p.id])], [w])).value == []


# ── the deductive rule: among letters AND a known word (Sean 2026-10-09) ──

def test_a_letter_has_a_neighbour_only_when_letter_ink_touches_it_on_its_line():
    import numpy as np
    from tools.omr.staged.gather import letter_ink_beside
    sp = 20.0
    mask = np.zeros((200, 400), np.uint8)
    mask[100:120, 100:114] = 255                 # the `p` itself (taken out below)
    mask[102:120, 118:126] = 255                 # an `i` 4 px to its right
    mask[100:120, 100:114] = 0                   # (the detector's box is blanked)
    s = letter_ink_beside(mask, (100, 100, 114, 120), sp)
    assert s["right"] and not s["left"]
    mask[:, :] = 0
    mask[100:120, 140:154] = 255                 # the next mark 1.3 spaces away
    s = letter_ink_beside(mask, (100, 100, 114, 120), sp)
    assert not s["right"] and not s["left"]       # a p by itself


def test_alone_inside_a_word_box_is_still_a_dynamic():
    from tools.omr.staged.adjudicators import text as T
    assert T._is_a_letter_of_a_known_word({"left": False, "right": True})
    assert not T._is_a_letter_of_a_known_word({"left": False, "right": False})
    assert not T._is_a_letter_of_a_known_word(None)
