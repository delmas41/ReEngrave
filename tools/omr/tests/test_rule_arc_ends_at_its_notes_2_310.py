"""ROADMAP 2.310 rule 3: the yes-and-never pair for the page fact "An arc ends at the notes standing where its ink ends"
(`docs/page-facts.md`).

THE RULE (Sean, 2026-11-15): "An arc ends at the notes standing where its ink ends, on the staff it sits over. It often stops a little short of
them; then it belongs to the closest of those notes. It never reaches past a nearer note to a farther one, and never to a note on another
staff. Where two notes are about equally close, we don't choose."

STAGED path. The function exercised is `arc_claim.bind_curve` (-> `bind_end`), the pure binder `ownership._page_binding` calls (2.223 page-wide
binding), fed the way `_page_binding` feeds it: the heads of the arc's OWNER staff only (the caller, not the binder, keeps another staff's notes
out), `usable` = ADJUDICATE's `notehead_is_not_a_notehead` verdict, `by_height` = `end_pitch_enabled()` and the stroke ends as `alt_ends` when
`page_claims_enabled()`. Flag state: `OMR_ARC_BIND_PAGEWIDE`, `OMR_BIND_END_PITCH`, `OMR_PAGE_CLAIMS` all at their defaults, which are ON
(`test_the_flags_stand_at_their_defaults`).

FIXTURE: `data/rule_arc_ends_2_310.json`, rows copied unchanged from the saved 2.305 Brahms gather (the `system_arc` rows' traced ends, the
`glyph_box` notehead boxes with their page positions, the `notehead_is_not_a_notehead` verdicts). CLAUDE rule 7: the marks Sean named, never a
drawing. The twins (`*_twin`) change one row of the real case and show the control can fail.

  YES   Brahms p11 staff 2, the tie `glyph/11/0/2/8/11`: Sean, 2.305 r2 tile 4 "tie, yes" (and arcs-combined r2 tile 3 "a tie"), notes
        `glyph/11/0/2/8/2` -> `glyph/11/0/2/9/7`.
  NEVER Brahms p11 staff 12 cell 3: Sean, 2.305 r1 tile 5, "no, there's no arc between those two notes. There is one arc going from the second
        note into the next measure" (`glyph/11/0/12/3/0` and `glyph/11/0/12/3/2`).
"""
import copy
import json
import os

import pytest

from tools.omr.staged import arc_claim as AC

_FX = os.path.join(os.path.dirname(__file__), "data", "rule_arc_ends_2_310.json")
with open(_FX) as _f:
    FX = json.load(_f)

SEAN_YES = ("glyph/11/0/2/8/2", "glyph/11/0/2/9/7")
SEAN_NO = ("glyph/11/0/12/3/0", "glyph/11/0/12/3/2")          # the pair Sean said has no arc between it
SECOND_NOTE = "glyph/11/0/12/3/2"
FIRST_NOTE = "glyph/11/0/12/3/0"
DOT = "glyph/11/0/12/3/23"                                   # a 15 px box ADJUDICATE refused ("too_narrow"): an augmentation dot, not a note


@pytest.fixture(autouse=True)
def _default_flags(monkeypatch):
    for name in (AC.ENV_BIND, AC.ENV_END_PITCH, AC.ENV_PAGE_CLAIMS):
        monkeypatch.delenv(name, raising=False)


def _bind(arc, heads, refused=()):
    """`ownership._page_binding`'s call, minus the Evidence plumbing."""
    d = arc["detail"]
    alt = None
    if AC.page_claims_enabled() and d.get("stroke_left_page") and d.get("stroke_right_page"):
        alt = {"left": d["stroke_left_page"], "right": d["stroke_right_page"]}
    return AC.bind_curve(d, heads, d["space_page_px"], lambda k: k not in refused, by_height=AC.end_pitch_enabled(), alt_ends=alt)


def _binds_the_rejected_pair(bound):
    return (bound["left"].get("head"), bound["right"].get("head")) == SEAN_NO


def test_the_flags_stand_at_their_defaults():
    assert AC.bind_enabled() and AC.end_pitch_enabled() and AC.page_claims_enabled()


# ── YES ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_yes_an_arc_that_stops_short_belongs_to_the_closest_note_on_its_staff():
    """An arc ends at the notes standing where its ink ends, on the staff it sits over. It often stops a little short of them; then it belongs
    to the closest of those notes. It never reaches past a nearer note to a farther one, and never to a note on another staff. Where two notes
    are about equally close, we don't choose.

    Brahms p11 staff 2, tie 8/11: Sean judged its notes right. Its right end stands 11 px (0.4 space) short of the stop note's centre and its
    left end 16 px past the start note's: each belongs to the closest note of the staff, which are exactly Sean's two."""
    y = FX["yes"]
    assert (y["sean"]["start"], y["sean"]["stop"]) == SEAN_YES
    got = _bind(y["arc"], y["heads"], y["refused"])
    assert (got["left"].get("head"), got["right"].get("head")) == SEAN_YES
    heads = {h["key"]: h for h in y["heads"]}
    d = y["arc"]["detail"]
    sp = d["space_page_px"]
    # the ink does NOT end on the note's centre (it stops short / starts inside), by less than one staff space
    assert 0 < abs(d["x_right_page"] - heads[SEAN_YES[1]]["cx"]) < sp
    assert 0 < abs(d["x_left_page"] - heads[SEAN_YES[0]]["cx"]) < sp
    # and each is the closest note of its column in x: no other column of the staff stands nearer the ink's end
    for end, x in (("left", d["x_left_page"]), ("right", d["x_right_page"])):
        bound = heads[got[end]["head"]]
        nearer = [k for k, h in heads.items() if abs(h["cx"] - x) < abs(bound["cx"] - x) - 0.6 * bound["w"]]
        assert nearer == [], (end, nearer)


def test_yes_twin_the_nearer_note_removed_the_end_does_not_reach_to_a_farther_one():
    """Control that can fail: take the START note out of the staff. If the binder reached past the missing nearer note, the left end would bind
    another head of the staff; the rule says it must not (it abstains, naming what it saw)."""
    y = FX["yes"]
    without = [h for h in y["heads"] if h["key"] != SEAN_YES[0]]
    got = _bind(y["arc"], without, y["refused"])
    assert got["left"].get("head") != SEAN_YES[0]                    # the answer changed: the control reads the row it is about
    assert got["left"].get("head") is None                          # ... and it did not become a farther head
    assert got["left"].get("unbound") == "no_head_at_end"
    # the right end, untouched, still binds its own note
    assert got["right"].get("head") == SEAN_YES[1]


# ── NEVER ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_never_no_arc_of_the_staff_binds_the_pair_sean_said_has_no_arc_between_it():
    """An arc ends at the notes standing where its ink ends, on the staff it sits over. It often stops a little short of them; then it belongs
    to the closest of those notes. It never reaches past a nearer note to a farther one, and never to a note on another staff. Where two notes
    are about equally close, we don't choose.

    Brahms p11 staff 12, 2.305 r1 tile 5: Sean, "no, there's no arc between those two notes. There is one arc going from the second note into
    the next measure". Every real curve the page pass traced on that staff is bound; none gets the pair, and the arc that does leave the
    second note never takes the FIRST note (a farther one, past the nearer second note)."""
    n = FX["never"]
    assert (n["sean"]["start"], n["sean"]["stop"]) == SEAN_NO
    assert len(n["arcs_on_staff"]) >= 8
    assert n["refused"] == {DOT: n["refused"][DOT]} and n["refused"][DOT]["reason"] == "too_narrow"
    for arc in n["arcs_on_staff"]:
        got = _bind(arc, n["heads"], n["refused"])
        assert not _binds_the_rejected_pair(got), arc["subject"]
    leaving = next(a for a in n["arcs_on_staff"] if a["subject"] == n["arc_from_second_note"])
    got = _bind(leaving, n["heads"], n["refused"])
    assert got["left"].get("head") in (None, SECOND_NOTE)
    assert FIRST_NOTE not in (got["left"].get("head"), got["right"].get("head"))
    if got["left"].get("head") is None:                              # an abstention names the CLOSEST note, never the farther one
        assert got["left"]["candidates"] == [SECOND_NOTE]


def test_never_twin_the_same_check_flags_ink_that_really_ends_at_those_two_notes():
    """Control that can fail: move the real arc's two ends onto the first and the second note. The binder then does bind the pair, and the
    never-check above (`_binds_the_rejected_pair`) says so -- it is not vacuous."""
    n = FX["never"]
    arc = copy.deepcopy(next(a for a in n["arcs_on_staff"] if a["subject"] == n["arc_from_second_note"]))
    heads = {h["key"]: h for h in n["heads"]}
    d = arc["detail"]
    d["x_left_page"], d["y_left_page"] = heads[FIRST_NOTE]["cx"], heads[FIRST_NOTE]["cy"] - 40
    d["x_right_page"], d["y_right_page"] = heads[SECOND_NOTE]["cx"], heads[SECOND_NOTE]["cy"] - 40
    d["stroke_left_page"], d["stroke_right_page"] = [d["x_left_page"], d["y_left_page"]], [d["x_right_page"], d["y_right_page"]]
    assert _binds_the_rejected_pair(_bind(arc, n["heads"], n["refused"]))


def test_never_twin_the_nearer_note_removed_the_candidate_changes_to_the_farther_note():
    """Control that can fail: the abstention above names the second note. Take the second note out of the staff and the named candidate is
    the first note -- so the assertion `candidates == [second note]` is reading the nearer note, not passing by accident."""
    n = FX["never"]
    leaving = next(a for a in n["arcs_on_staff"] if a["subject"] == n["arc_from_second_note"])
    without = [h for h in n["heads"] if h["key"] != SECOND_NOTE]
    got = _bind(leaving, without, n["refused"])
    assert got["left"]["candidates"] == [FIRST_NOTE]


# ── a documented gap, NOT one of the two controls ──────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.xfail(strict=True, reason=(
    "ROADMAP 2.305 / 2.310 rule 3 FINDING: the rule says an arc that stops short belongs to the closest note. Sean's r1 tile 5 names the arc "
    "that 'goes from the second note into the next measure'; its traced stroke ends 2.4 spaces short of that note (66 px, sp 27.5), past "
    "ANCHOR_OUT_SPACES = 1.6, so `bind_end` abstains (`no_head_at_end`, candidate = the second note, margin +2.03) where the rule's yes-clause "
    "says bind it. The reader follows the old measured reach window, not the reworded rule. Unchanged here: lane work, not this lane."))
def test_the_arc_leaving_the_second_note_binds_the_second_note():
    n = FX["never"]
    leaving = next(a for a in n["arcs_on_staff"] if a["subject"] == n["arc_from_second_note"])
    got = _bind(leaving, n["heads"], n["refused"])
    assert got["left"].get("head") == SECOND_NOTE
