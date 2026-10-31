"""ROADMAP 2.223: a hairpin's two tips bound page-wide to places in the bars of the staff ABOVE it (`OMR_HAIRPIN_BIND_PAGEWIDE`).
Each guard sits beside a twin that is accepted, so a battery that refuses everything fails here.

Page geometry of every fixture: staff 0 lines y 0..40 (space 10), staff 1 lines y 100..140; bars of staff 0 x 0-200 (cell 0) and
200-400 (cell 1). A hairpin under staff 0 sits at y 55-63, BETWEEN the two staves."""
from __future__ import annotations

import pytest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import hairpin_bind as HB
from tools.omr.staged import record as R
from tools.omr.staged.gather import FRAME_PAGE
from tools.omr.staged.record import Log, Q, READERS

SP = 10.0


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv(HB.ENV_BIND, "1")


def _page(log, *, staves=(0, 1)):
    for st in staves:
        top = 100.0 * st
        log.observe(R.staff(0, 0, st), Q.STAFF_LINES, [top + 10 * i for i in range(5)], reader=READERS.GEOMETRY, frame="page")
        for c, (x0, x1) in enumerate(((0.0, 200.0), (200.0, 400.0))):
            log.observe(R.cell(0, 0, st, c), Q.CELL_BOX, [x0, top - 30, x1, top + 70], reader=READERS.GEOMETRY, frame="cell:%d" % c)


def _head(log, staff, cell, gi, cx, cy=15.0, w=12.0, h=10.0):
    g = R.glyph(0, 0, staff, cell, gi)
    x0, y0 = cx - w / 2, cy - h / 2
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", x0, y0, w, h), reader=READERS.DETECTOR, frame="cell:%d" % cell, score=0.9,
                category="notehead", bbox_page_px=[x0, y0, x0 + w, y0 + h])
    return g


def _hairpin(log, staff, cell, x0, x1, y0=55.0, y1=63.0, kind="crescendo", gi=100000):
    g = R.glyph(0, 0, staff, cell, gi)
    log.observe(g, Q.WEDGE_BOX, kind, reader=READERS.CV_HAIRPINS, frame=FRAME_PAGE, score=None,
                bbox_page_px=[x0, y0, x1, y1], x_center_page=(x0 + x1) / 2)
    return g


def _decide(log, w):
    log.freeze()
    adjudicate.run(log)
    return log.verdict(Q.WEDGE_ANCHOR, w)


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(HB.ENV_BIND, raising=False)
    assert not HB.bind_enabled()
    monkeypatch.setenv(HB.ENV_BIND, "yes")
    assert HB.bind_enabled()


def test_off_keeps_the_old_rule(monkeypatch):
    monkeypatch.setenv(HB.ENV_BIND, "0")
    log = Log()
    _page(log)
    _head(log, 0, 0, 0, 40.0)
    _head(log, 0, 0, 1, 150.0)
    v = _decide(log, _hairpin(log, 0, 0, 38.0, 148.0))
    assert v.reason == "nearest_either_side"


def test_both_tips_at_notes():
    log = Log()
    _page(log)
    a = _head(log, 0, 0, 0, 40.0)
    _head(log, 0, 0, 1, 90.0)
    b = _head(log, 0, 0, 2, 150.0)
    v = _decide(log, _hairpin(log, 0, 0, 38.0, 148.0))
    assert v.reason == "bound_page_wide" and v.value == [a.to_key(), b.to_key()]
    assert v.detail["start_how"] == "at" == v.detail["stop_how"]


def test_a_tip_in_open_space_is_under_the_note_sounding_there():
    """A diminuendo drawn under one held note: both tips bind to it (Sean 2026-09-05, one anchor is enough)."""
    log = Log()
    _page(log)
    a = _head(log, 0, 0, 0, 20.0)
    v = _decide(log, _hairpin(log, 0, 0, 60.0, 180.0, kind="diminuendo"))
    assert v.value == [a.to_key(), a.to_key()]
    assert v.detail["start_how"] == "under" and v.detail["stop_how"] == "under" and v.detail["kind"] == "diminuendo"


def test_a_stop_aimed_at_the_next_downbeat():
    log = Log()
    _page(log)
    a = _head(log, 0, 0, 0, 40.0)
    b = _head(log, 0, 1, 0, 210.0)
    v = _decide(log, _hairpin(log, 0, 0, 38.0, 199.0))
    assert v.value == [a.to_key(), b.to_key()] and v.detail["stop_cell"] == 1


def test_a_tip_in_a_bar_with_no_note_abstains_never_the_nearest_of_another_bar():
    """The OFF rule takes the nearest head of any bar in reach of its window; ON, a start in a bar of rests is UNBOUND."""
    log = Log()
    _page(log)
    _head(log, 0, 0, 0, 40.0)
    w = _hairpin(log, 0, 1, 250.0, 380.0)
    v = _decide(log, w)
    assert v.outcome.value == "abstained" and v.reason == "tip_unbound"
    assert v.detail["start"]["unbound"] == "no_note_in_bar"


def test_twin_a_note_in_that_bar_binds_it():
    log = Log()
    _page(log)
    _head(log, 0, 0, 0, 40.0)
    c = _head(log, 0, 1, 0, 252.0)
    v = _decide(log, _hairpin(log, 0, 1, 250.0, 380.0))
    assert v.reason == "bound_page_wide" and v.value[0] == c.to_key()


def test_a_tip_before_the_bars_first_note_and_out_of_reach_abstains():
    log = Log()
    _page(log)
    _head(log, 0, 0, 0, 120.0)
    v = _decide(log, _hairpin(log, 0, 0, 20.0, 110.0))
    assert v.reason == "tip_unbound" and v.detail["start"]["unbound"] == "no_note_at_tip"
    assert v.detail["start"]["margin_spaces"] > 0


def test_a_hairpin_between_two_staves_binds_to_the_staff_ABOVE_never_the_notes_below_it():
    """Sean 2026-10-31: notes above a hairpin belong to the staff above, below it to the staff below. The staff below's heads stand
    right at the tips (nearer in x than the staff above's); they are never candidates."""
    log = Log()
    _page(log)
    a = _head(log, 0, 0, 0, 40.0)
    b = _head(log, 0, 0, 1, 150.0)
    _head(log, 1, 0, 0, 37.0, cy=105.0)
    _head(log, 1, 0, 1, 148.0, cy=105.0)
    v = _decide(log, _hairpin(log, 0, 0, 36.0, 147.0))
    assert v.value == [a.to_key(), b.to_key()]


def test_a_head_of_the_staff_lying_below_the_hairpin_is_not_a_candidate():
    """A head this staff owns but drawn BELOW the hairpin is the staff below's by Sean's rule: excluded and counted."""
    log = Log()
    _page(log)
    a = _head(log, 0, 0, 0, 40.0)
    _head(log, 0, 0, 1, 150.0, cy=80.0)
    v = _decide(log, _hairpin(log, 0, 0, 38.0, 148.0))
    assert v.detail["heads_below_the_hairpin"] == 1
    assert v.value == [a.to_key(), a.to_key()] and v.detail["stop_how"] == "under"


def test_a_box_reaching_into_the_staff_below_is_not_between_staves():
    log = Log()
    _page(log)
    _head(log, 0, 0, 0, 40.0)
    v = _decide(log, _hairpin(log, 0, 0, 38.0, 148.0, y0=90.0, y1=104.0))
    assert v.reason == "not_between_staves" and v.detail["why"] == "reaches_into_the_staff_below"


def test_a_refused_head_is_no_candidate():
    """`usable` (the adjudicator) leaves a head refused as a notehead out of `heads`; the pure rule then binds the stop UNDER the
    note before it, and with the head present binds AT it."""
    a, b = R.glyph(0, 0, 0, 0, 0), R.glyph(0, 0, 0, 0, 1)
    heads = [{"key": a.to_key(), "cx": 40.0, "cy": 15.0, "w": 12.0, "h": 10.0, "cell": 0}]
    r = HB.bind_hairpin([38.0, 55.0, 148.0, 63.0], heads, [(0, 0.0, 200.0), (1, 200.0, 400.0)], SP)
    assert r["stop"]["head"] == a.to_key() and r["stop"]["how"] == "under"
    heads.append({"key": b.to_key(), "cx": 150.0, "cy": 15.0, "w": 12.0, "h": 10.0, "cell": 0})
    r = HB.bind_hairpin([38.0, 55.0, 148.0, 63.0], heads, [(0, 0.0, 200.0), (1, 200.0, 400.0)], SP)
    assert r["stop"]["head"] == b.to_key() and r["stop"]["how"] == "at"


def test_two_columns_in_reach_of_a_tip_abstain_with_both():
    heads = [{"key": "x1", "cx": 95.0, "cy": 15.0, "w": 12.0, "h": 10.0, "cell": 0},
             {"key": "x2", "cx": 105.0, "cy": 15.0, "w": 12.0, "h": 10.0, "cell": 0},
             {"key": "a", "cx": 20.0, "cy": 15.0, "w": 12.0, "h": 10.0, "cell": 0}]
    r = HB.bind_hairpin([18.0, 55.0, 100.0, 63.0], heads, [(0, 0.0, 200.0)], SP)
    assert r["stop"]["unbound"] == "two_columns_at_tip" and len(r["stop"]["candidates"]) == 2
    heads[1]["cx"] = 125.0          # twin: the second column out of reach
    r = HB.bind_hairpin([18.0, 55.0, 100.0, 63.0], heads, [(0, 0.0, 200.0)], SP)
    assert r["stop"]["head"] == "x1"


def test_the_stop_stays_in_the_starts_voice():
    heads = [{"key": "a", "cx": 20.0, "cy": 15.0, "w": 12.0, "h": 10.0, "cell": 0},
             {"key": "v2", "cx": 100.0, "cy": 15.0, "w": 12.0, "h": 10.0, "cell": 0}]
    voice = {"a": 1, "v2": 2}
    r = HB.bind_hairpin([18.0, 55.0, 100.0, 63.0], heads, [(0, 0.0, 200.0)], SP, lambda k: voice[k])
    assert r["stop"]["head"] == "a" and r["stop"]["how"] == "under"
    voice["v2"] = 1
    r = HB.bind_hairpin([18.0, 55.0, 100.0, 63.0], heads, [(0, 0.0, 200.0)], SP, lambda k: voice[k])
    assert r["stop"]["head"] == "v2"


def test_a_hairpin_inside_a_claimed_word_is_the_words_ink():
    """The page-wide pass claims words before dynamics; a 'c' of cresc. read as a crescendo stays the word's (8 of 8 small CV
    'hairpins' on the 2026-10-31 sample were letters)."""
    log = Log()
    _page(log)
    _head(log, 0, 0, 0, 40.0)
    _head(log, 0, 0, 1, 150.0)
    log.observe(R.system(0, 0), Q.CLAIMED_AREA, [30.0, 50.0, 90.0, 70.0], reader="cv_page_claims", frame="page",
                owner="word", unit="area", standing="READ")
    v = _decide(log, _hairpin(log, 0, 0, 38.0, 48.0))
    assert v.reason == "inside_a_word" and v.detail["share"] == 1.0


def test_twin_a_word_beside_the_hairpin_takes_nothing():
    log = Log()
    _page(log)
    _head(log, 0, 0, 0, 40.0)
    _head(log, 0, 0, 1, 150.0)
    log.observe(R.system(0, 0), Q.CLAIMED_AREA, [160.0, 50.0, 190.0, 70.0], reader="cv_page_claims", frame="page",
                owner="word", unit="area", standing="READ")
    assert _decide(log, _hairpin(log, 0, 0, 38.0, 148.0)).reason == "bound_page_wide"


def test_an_unusable_head_at_the_tip_blocks_the_under_guess():
    """Brahms p25 (2026-10-31 crop): the head at the start tip was not usable, so the first build bound the start UNDER the note
    before it -- a guess. A GATHER head box in reach of the tip now makes the tip abstain; without it the tip is under the earlier note."""
    heads = [{"key": "early", "cx": 20.0, "cy": 15.0, "w": 12.0, "h": 10.0, "cell": 0},
             {"key": "end", "cx": 150.0, "cy": 15.0, "w": 12.0, "h": 10.0, "cell": 0}]
    bad = [{"key": "refused", "cx": 62.0, "cy": 15.0, "w": 12.0, "h": 10.0, "cell": 0}]
    r = HB.bind_hairpin([60.0, 55.0, 148.0, 63.0], heads, [(0, 0.0, 200.0)], SP, unusable=bad)
    assert r["start"]["unbound"] == "head_at_tip_not_usable" and r["start"]["candidates"] == ["refused"]
    r = HB.bind_hairpin([60.0, 55.0, 148.0, 63.0], heads, [(0, 0.0, 200.0)], SP)
    assert r["start"]["head"] == "early" and r["start"]["how"] == "under"
