"""ROADMAP 2.310 rule 3 / 2.305 r6: the yes-and-never pair for the page fact "An arc ends at the notes standing where its ink ends"
(`docs/page-facts.md`).

THE RULE (Sean, 2026-11-15): "An arc ends at the notes standing where its ink ends, on the staff it sits over. It often stops a little short of
them; then it belongs to the closest of those notes. It never reaches past a nearer note to a farther one, and never to a note on another
staff. Where two notes are about equally close, we don't choose."

STAGED path. The function exercised is `arc_claim.bind_curve` (-> `bind_end`), the pure binder `ownership._page_binding` calls (2.223 page-wide
binding), fed the way `_page_binding` feeds it: the heads of the arc's OWNER staff only (the caller, not the binder, keeps another staff's notes
out -- `test_never_another_staff_...` below), `usable` = ADJUDICATE's `notehead_is_not_a_notehead` verdict, `by_height` = `end_pitch_enabled()`,
the stroke ends as `alt_ends` when `page_claims_enabled()`, and (2.305 r6) the staff's UNREAD head ink (`arc_claim.unread_head_ink` over the
page's own strokes, boxes and claims, as `ownership._unread_head_ink` reads them). Flag state: `OMR_ARC_BIND_PAGEWIDE`, `OMR_BIND_END_PITCH`,
`OMR_PAGE_CLAIMS` at their defaults (ON) and `OMR_PAGE_ARC_WRITE` ON (2.305 r6: the rule replaces the reach window only with the lane's flag on;
`test_with_the_lane_flag_off_the_old_window_stands` shows the OFF reader unchanged).

2.305 r6 (the rule, not a reach window): `ANCHOR_OUT_SPACES` (1.6 sp) no longer decides; the end binds the closest note of its staff, and the failure
the window guarded against -- a note nobody boxed, where the arc would take the next note along -- is guarded directly: head-shaped ink no reader has
read standing at least about as near the end as the closest note -> "cannot tell" (`unread_ink_at_end`).

FIXTURE: `data/rule_arc_ends_2_310.json`, rows copied unchanged from the saved 2.305 Brahms gather (the `system_arc` rows' traced ends, the
`glyph_box` notehead boxes with their page positions, the `notehead_is_not_a_notehead` verdicts; 2.305 r6 added the staff's blob and vertical page
strokes, every box over the staff with its class, the claimed areas and the page strokes any claim names). CLAUDE rule 7: the marks Sean named,
never a drawing. The twins (`*_twin`) change one row of the real case and show the control can fail.

  YES   Brahms p11 staff 2, the tie `glyph/11/0/2/8/11`: Sean, 2.305 r2 tile 4 "tie, yes" (and arcs-combined r2 tile 3 "a tie"), notes
        `glyph/11/0/2/8/2` -> `glyph/11/0/2/9/7`.
  YES   Brahms p11 staff 12, the arc "going from the second note into the next measure" (Sean, 2.305 r1 tile 5; r2 tile 3 "slur, yes" from
        `glyph/11/0/12/3/2`): its ink stops 2.4 spaces short of that note; it belongs to it.
  NEVER Brahms p11 staff 12 cell 3: Sean, 2.305 r1 tile 5, "no, there's no arc between those two notes. There is one arc going from the second
        note into the next measure" (`glyph/11/0/12/3/0` and `glyph/11/0/12/3/2`).
  NEVER (another staff) Litolff p15 run 4: Sean, arcs-combined r2 tile 9, "the box holds a slur from the lower staff and one from the upper staff"
        (`data_arc_binding_2_305.json`, the 2.305 r1 fixture).
"""
import copy
import json
import os
import pathlib

import pytest

from tools.omr.staged import arc_claim as AC
from tools.omr.staged import page_arc_bind as PB

_FX = os.path.join(os.path.dirname(__file__), "data", "rule_arc_ends_2_310.json")
with open(_FX) as _f:
    FX = json.load(_f)
TILE9 = json.loads((pathlib.Path(__file__).parent / "data_arc_binding_2_305.json").read_text())["litolff_p15_run4_sean_tile9"]

SEAN_YES = ("glyph/11/0/2/8/2", "glyph/11/0/2/9/7")
SEAN_NO = ("glyph/11/0/12/3/0", "glyph/11/0/12/3/2")          # the pair Sean said has no arc between it
SECOND_NOTE = "glyph/11/0/12/3/2"
FIRST_NOTE = "glyph/11/0/12/3/0"
DOT = "glyph/11/0/12/3/23"                                   # a 15 px box ADJUDICATE refused ("too_narrow"): an augmentation dot, not a note


@pytest.fixture(autouse=True)
def _flags(monkeypatch):
    for name in (AC.ENV_BIND, AC.ENV_END_PITCH, AC.ENV_PAGE_CLAIMS):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(PB.ENV_WRITE, "1")


def _unread(case, never_boxed=()):
    """`ownership._unread_head_ink` on the fixture's real rows. `never_boxed`: heads whose box (and so the page head's claim on its ink) the twin
    takes away -- a note the detector never boxed; its INK stays on the page."""
    gone = [b["bbox_page_px"] for b in case["page_boxes_over_staff"] if b["key"] in never_boxed]
    boxes = [b["bbox_page_px"] for b in case["page_boxes_over_staff"] if b["key"] not in never_boxed and AC.reads_ink(b.get("cls"))]

    def inside(s, g):
        x0, y0, x1, y1 = s["bbox_page_px"]
        return g[0] <= (x0 + x1) / 2.0 <= g[2] and g[1] <= (y0 + y1) / 2.0 <= g[3]
    by = {s["ordinal"]: s for s in case["staff_strokes"]}
    claimed = [o for o in case["claimed_strokes"] if not (o in by and any(inside(by[o], g) for g in gone))]
    return AC.unread_head_ink(case["staff_strokes"], boxes, 27.5, claimed)


def _bind(arc, heads, refused=(), unread=None):
    """`ownership._page_binding`'s call, minus the Evidence plumbing."""
    d = arc["detail"]
    alt = None
    if AC.page_claims_enabled() and d.get("stroke_left_page") and d.get("stroke_right_page"):
        alt = {"left": d["stroke_left_page"], "right": d["stroke_right_page"]}
    return AC.bind_curve(d, heads, d["space_page_px"], lambda k: k not in refused, by_height=AC.end_pitch_enabled(), alt_ends=alt, unread=unread)


def _binds_the_rejected_pair(bound):
    return (bound["left"].get("head"), bound["right"].get("head")) == SEAN_NO


def _leaving():
    n = FX["never"]
    return next(a for a in n["arcs_on_staff"] if a["subject"] == n["arc_from_second_note"])


def test_the_flags_stand_at_their_defaults():
    assert AC.bind_enabled() and AC.end_pitch_enabled() and AC.page_claims_enabled()
    assert AC.rule_enabled()                                         # the lane's flag, set by the fixture


def test_with_the_lane_flag_off_the_old_window_stands(monkeypatch):
    """`OMR_PAGE_ARC_WRITE` OFF: the reader is what it was -- the arc leaving the second note stops 2.4 spaces short, past the old 1.6-space window,
    and abstains naming that note (the 2.310 finding). The rule is the lane's, behind its flag."""
    monkeypatch.delenv(PB.ENV_WRITE, raising=False)
    n = FX["never"]
    got = _bind(_leaving(), n["heads"], n["refused"])
    assert got["left"].get("unbound") == "no_head_at_end" and got["left"]["candidates"] == [SECOND_NOTE]


# ── YES ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_yes_an_arc_that_stops_short_belongs_to_the_closest_note_on_its_staff():
    """An arc ends at the notes standing where its ink ends, on the staff it sits over. It often stops a little short of them; then it belongs
    to the closest of those notes. It never reaches past a nearer note to a farther one, and never to a note on another staff. Where two notes
    are about equally close, we don't choose.

    Brahms p11 staff 2, tie 8/11: Sean judged its notes right. Its right end stands 11 px (0.4 space) short of the stop note's centre and its
    left end 16 px past the start note's: each belongs to the closest note of the staff, which are exactly Sean's two."""
    y = FX["yes"]
    assert (y["sean"]["start"], y["sean"]["stop"]) == SEAN_YES
    got = _bind(y["arc"], y["heads"], y["refused"], _unread(y))
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


def test_yes_the_arc_leaving_the_second_note_binds_the_second_note():
    """Sean, 2.305 r1 tile 5: "There is one arc going from the second note into the next measure" (r2 tile 3, "slur, yes", from the second note).
    Its ink stops 2.4 spaces short of that note (66 px, sp 27.5) -- past the old 1.6-space window; by the rule it belongs to the closest note."""
    n = FX["never"]
    leaving = _leaving()
    d = leaving["detail"]
    heads = {h["key"]: h for h in n["heads"]}
    assert 2.0 < (d["stroke_left_page"][0] - heads[SECOND_NOTE]["cx"]) / d["space_page_px"] < 2.5
    got = _bind(leaving, n["heads"], n["refused"], _unread(n))
    assert got["left"].get("head") == SECOND_NOTE


def test_yes_twin_the_nearer_note_never_boxed_the_end_does_not_reach_to_a_farther_one():
    """Control that can fail: the START note was never boxed (its box and the page head's claim on its ink taken away; its ink stays). The end must
    not reach past that ink to another note: it says "cannot tell", naming the ink. The twin's twin -- the ink taken away too -- binds the farther
    note: the guard on the ink is what refuses, not an accident of the fixture."""
    y = FX["yes"]
    without = [h for h in y["heads"] if h["key"] != SEAN_YES[0]]
    got = _bind(y["arc"], without, y["refused"], _unread(y, never_boxed=(SEAN_YES[0],)))
    assert got["left"].get("head") is None
    assert got["left"].get("unbound") == AC.UNREAD_INK_AT_END
    assert got["left"]["margin_spaces"] < 0                          # the ink stands nearer than the farther note, by more than "about equally"
    assert got["right"].get("head") == SEAN_YES[1]                   # the right end, untouched, still binds its own note
    no_ink = _bind(y["arc"], without, y["refused"], _unread(y))
    assert no_ink["left"].get("head") not in (None, SEAN_YES[0])


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
    unread = _unread(n)
    for arc in n["arcs_on_staff"]:
        got = _bind(arc, n["heads"], n["refused"], unread)
        assert not _binds_the_rejected_pair(got), arc["subject"]
    got = _bind(_leaving(), n["heads"], n["refused"], unread)
    assert got["left"].get("head") == SECOND_NOTE
    assert FIRST_NOTE not in (got["left"].get("head"), got["right"].get("head"))


def test_never_twin_the_same_check_flags_ink_that_really_ends_at_those_two_notes():
    """Control that can fail: move the real arc's two ends onto the first and the second note. The binder then does bind the pair, and the
    never-check above (`_binds_the_rejected_pair`) says so -- it is not vacuous."""
    n = FX["never"]
    arc = copy.deepcopy(_leaving())
    heads = {h["key"]: h for h in n["heads"]}
    d = arc["detail"]
    d["x_left_page"], d["y_left_page"] = heads[FIRST_NOTE]["cx"], heads[FIRST_NOTE]["cy"] - 40
    d["x_right_page"], d["y_right_page"] = heads[SECOND_NOTE]["cx"], heads[SECOND_NOTE]["cy"] - 40
    d["stroke_left_page"], d["stroke_right_page"] = [d["x_left_page"], d["y_left_page"]], [d["x_right_page"], d["y_right_page"]]
    assert _binds_the_rejected_pair(_bind(arc, n["heads"], n["refused"], _unread(n)))


def test_never_twin_the_second_note_never_boxed_the_end_never_reaches_past_its_ink():
    """Control that can fail: the SECOND note was never boxed (box and the page head's claim taken away; its ink stays). The arc leaving it must
    not reach on to another note (the first note lies farther back, the next one 8 spaces on): it says "cannot tell", naming that ink. With the ink
    taken away too, the end binds a farther note -- the guard on the ink is what refuses."""
    n = FX["never"]
    without = [h for h in n["heads"] if h["key"] != SECOND_NOTE]
    got = _bind(_leaving(), without, n["refused"], _unread(n, never_boxed=(SECOND_NOTE,)))
    assert got["left"].get("unbound") == AC.UNREAD_INK_AT_END
    assert FIRST_NOTE not in (got["left"].get("head"), got["right"].get("head"))
    no_ink = _bind(_leaving(), without, n["refused"], _unread(n))
    assert no_ink["left"].get("head") is not None


# ── NEVER another staff: the caller's guarantee ────────────────────────────────────────────────────────────────────────────────────────

def _tile9_heads(staves):
    out = []
    for h in TILE9["heads"]:
        if "/".join(h["key"].split("/")[1:4]) in staves:
            x0, y0, x1, y1 = h["box"]
            out.append({"key": h["key"], "cx": (x0 + x1) / 2.0, "cy": (y0 + y1) / 2.0, "w": x1 - x0, "h": y1 - y0, "cell": h["cell"]})
    return out


def test_never_another_staff_the_lower_slurs_ink_does_not_take_the_upper_staffs_notes():
    """Litolff p15 run 4, Sean (arcs-combined r2 tile 9): "the box holds a slur from the lower staff and one from the upper staff". The traced ink
    is the lower slur (a cap, `above`, over the lower staff's notes). Handed the UPPER staff (the witnessing box's owner), the rule never binds both
    of its ends there: the upper staff's note stands on the arc's far side (`head_on_the_arcs_far_side`).

    WHO keeps another staff's notes out: the CALLER -- `ownership._page_binding` hands the binder the heads of ONE staff (`home`: the witnessing
    boxes' owner, else the run's own staff row) and `adjudicate_page_arc_binding` rebinds on the staff the arc's side names when both ends stand on
    the far side. The twin shows it: the same ink handed BOTH staves' notes names the other staff's notes as candidates -- the binder alone does not
    know a staff."""
    sp = float(TILE9["run"]["space_page_px"])
    d = PB.curve_detail(TILE9["run"], sp)
    up = PB.closest_binder({"left": [], "right": []})(_tile9_heads(["15/1/2"]), sp, None, True, None, d)
    assert up.get("by_rule")
    assert not (up["left"].get("head") and up["right"].get("head"))
    assert "head_on_the_arcs_far_side" in (up["left"].get("unbound"), up["right"].get("unbound"))
    both = PB.closest_binder({"left": [], "right": []})(_tile9_heads(["15/1/2", "15/1/3"]), sp, None, True, None, d)
    named = [k for s in ("left", "right") for k in [both[s].get("head")] + list(both[s].get("candidates") or []) if k]
    assert any(k.startswith("glyph/15/1/3/") for k in named) and any(k.startswith("glyph/15/1/2/") for k in named)
