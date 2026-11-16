"""ROADMAP 2.305 r7: controls from Sean's answers to the r6 arc tiles (benchmarks/arcs-combined-2026-11/answers/answers-2.305-r6.json). STAGED.

THE RULE (Sean, 2026-11-15, page-facts "An arc ends at the notes standing where its ink ends"): "An arc ends at the notes standing where its ink ends, on
the staff it sits over. It often stops a little short of them; then it belongs to the closest of those notes. It never reaches past a nearer note to a
farther one, and never to a note on another staff. Where two notes are about equally close, we don't choose."

Each control is the REAL case (fixture `data/rule_arc_ends_r7_2_305.json`, rows copied unchanged from the saved 2305 gathers by the lane's `fx_r7.py`),
bound the way `ownership._page_binding` binds it with `OMR_PAGE_ARC_WRITE` ON (the arc's own staff's notes; ADJUDICATE's notehead verdicts; the unread-ink
guard over the page's own strokes, boxes, claims and ledger lines; the neighbouring staves' notes as a guard only). Each failed on the r6 tree.

  NEVER tile 1  Litolff p13: "The first two half notes have a tie between them ... nothing between the second and third note" -- the tie's stop note was boxed
                in part and refused `too_narrow`; its ink is unread, so the end cannot tell; never the third note 10 spaces on.
  NEVER tile 3  Litolff p13: "it grabs an eighth note that's not a part of it" -- the half-note chord the tie starts at stands on ledger lines nobody boxed a
                note on: a ledger column with no read note is a note nobody read; never the eighth before it.
  NEVER tile 5  Litolff p15: "a tie coming from a previous bar ... from a previous system" -- the only "note" left of the piece is a box on the key signature the
                key's claim narrowed: a note held in doubt is no note an arc ends at; the piece's left end is the system's edge.
  NEVER tile 8  Brahms p0: "there's no arc. There is a slur above it, but it starts before the bar" -- the page map carves the barline out of the slur, so its
                page stroke ends AT the barline while its ink runs on before the bar; the ink ends at the outermost of the traced end and the stroke end, and
                the left end is never a note of that bar (`0/0/11/3/12`, an empty notehead box beside a stem, upstream).
  YES   tile 12 Brahms p0: "a tie" -- the head's top, cut off by its ledger line, is that head's own ink, not a note nobody read: the tie binds.
  YES   tile 9  Brahms p0: "a tie from dotted halves" (written on r6; must stay).
"""
import json
import os

import pytest

from tools.omr.staged import arc_claim as AC
from tools.omr.staged import page_arc_bind as PB

with open(os.path.join(os.path.dirname(__file__), "data", "rule_arc_ends_r7_2_305.json")) as _f:
    FX = json.load(_f)["cases"]


@pytest.fixture(autouse=True)
def _flags(monkeypatch):
    for name in (AC.ENV_BIND, AC.ENV_END_PITCH, AC.ENV_PAGE_CLAIMS):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(PB.ENV_WRITE, "1")


def _read(h):
    """`ownership._head_read`: ADJUDICATE read the box as a note (not refused, not held in doubt)."""
    v = h.get("verdict")
    if v is None:
        return True
    if v["outcome"] == "decided":
        return v["value"] is not True
    return v["outcome"] != "narrowed"


def _bind(case, drop_ink=()):
    sp = case["sp"]
    home = case["home"]
    heads, others = [], []
    for h in case["heads"]:
        x0, y0, x1, y1 = h["box"]
        d = {"key": h["key"], "cx": (x0 + x1) / 2.0, "cy": (y0 + y1) / 2.0, "w": x1 - x0, "h": y1 - y0, "cell": int(h["key"].split("/")[4])}
        if h.get("ink_centre"):
            d["ink_cx"], d["ink_cy"] = h["ink_centre"]
        if h["staff"] == home:
            heads.append(d)
        elif _read(h) and h["staff"][0] == home[0] and abs(h["staff"][1] - home[1]) == 1:
            others.append(dict(d, other_staff=True))
    if heads:
        mean_h = sum(h["h"] for h in heads) / len(heads)
        for h in heads:
            h["hh"] = mean_h
            h["tall"] = h["h"] > 1.5 * mean_h
    read = {h["key"]: _read(h) for h in case["heads"]}
    boxes = [b["box"] for b in case["boxes"] if AC.reads_ink(b.get("cls")) and not (b.get("category") == "notehead" and not read[b["key"]])]
    head_boxes = [(h["box"], h["staff"]) for h in case["heads"] if read[h["key"]]]
    ledgers = [{"box": b["box"], "key": b["key"], "id": b["key"], "staff": b["staff"]} for b in case["boxes"] if str(b.get("cls") or "").lower() == "ledgerline"]
    strokes = [s for s in case["strokes"] if s["ordinal"] not in drop_ink]
    unread = [u for u in AC.unread_head_ink(strokes, boxes, sp, case["claimed"], head_boxes, ledgers) if list(u.get("staff") or ()) == home] + others
    usable = (lambda k: read.get(k, True))
    arc = case["arc"]
    if arc["source"] == "system_arc":
        d = arc["detail"]
        alt = {"left": d["stroke_left_page"], "right": d["stroke_right_page"]} if d.get("stroke_left_page") and d.get("stroke_right_page") else None
        return AC.bind_curve(d, heads, d["space_page_px"], usable, by_height=True, alt_ends=alt, unread=unread)
    d = PB.curve_detail(arc["detail"], float(arc["detail"]["space_page_px"]))
    return PB.closest_binder({"left": [], "right": []})(heads, float(arc["detail"]["space_page_px"]), usable, True, None, d, unread)


def _pair(b):
    return (b["left"].get("head"), b["right"].get("head"))


def test_never_tile1_the_end_never_reaches_past_the_refused_stop_note_to_the_third_note():
    b = _bind(FX["tile1"])
    assert b["left"].get("head") == FX["tile1"]["sean"]["start"]          # the tie's start, the first half note
    assert b["right"].get("head") is None
    assert b["right"].get("unbound") == AC.UNREAD_INK_AT_END


def test_never_tile3_the_tie_never_starts_at_the_eighth_before_the_unboxed_chord():
    b = _bind(FX["tile3"])
    assert b["left"].get("head") != FX["tile3"]["sean"]["start"]
    assert b["left"].get("unbound") == AC.UNREAD_INK_AT_END and str(b["left"]["candidates"][1]).startswith("page_stroke:ledger:")
    assert b["right"].get("head") == FX["tile3"]["sean"]["stop"]          # the stop chord, which is boxed, still binds


def test_never_tile5_a_box_held_in_doubt_is_no_note_the_piece_from_the_previous_system_starts_at_the_edge():
    b = _bind(FX["tile5"])
    assert "glyph/15/0/0/0/5" not in _pair(b) and "glyph/15/0/0/0/10" not in _pair(b)
    assert b["left"].get("edge") is True


def test_never_tile8_the_slur_over_the_staff_below_takes_none_of_this_staffs_notes():
    b = _bind(FX["tile8"])
    assert _pair(b) != ("glyph/0/0/11/3/12", "glyph/0/0/11/3/6")
    # "it starts before the bar that has the orange box notes" (bar = cell 3): the left end is never a note of that bar
    left = b["left"].get("head")
    assert left is None or int(left.split("/")[4]) < 3


def test_yes_tile12_a_heads_own_ink_cut_off_by_its_ledger_is_not_an_unread_note():
    c = FX["tile12"]
    assert _pair(_bind(c)) == (c["sean"]["start"], c["sean"]["stop"])


def test_yes_tile12_twin_the_ink_of_a_note_nobody_read_still_refuses():
    """Control that can fail: with the head's own box taken out of the fold (the head unboxed), the same cut-off ink is a note nobody read again."""
    c = dict(FX["tile12"])
    c["heads"] = [h for h in c["heads"] if h["key"] != c["sean"]["start"]]
    c["boxes"] = [b for b in c["boxes"] if b["key"] != c["sean"]["start"]]
    b = _bind(c)
    assert b["left"].get("unbound") == AC.UNREAD_INK_AT_END


def test_yes_tile9_the_written_tie_stays():
    c = FX["tile9"]
    assert _pair(_bind(c)) == (c["sean"]["start"], c["sean"]["stop"])
