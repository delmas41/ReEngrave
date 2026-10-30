"""ROADMAP 2.223: page-wide binding of a claimed curve's two ends (pure parts of `arc_claim`). Each guard has a twin that fails without it."""
from tools.omr.staged import arc_claim as AC

SP = 10.0


def _h(key, cx, cy, w=12.0, h=10.0):
    return {"key": key, "cx": cx, "cy": cy, "w": w, "h": h, "cell": 0}


def _curve(xl, yl, xr, yr, sag=-15.0):
    """A cap (sag < 0, drawn above its notes) or a cup (sag > 0) between two ends, as GATHER's `[x, y_top, y_bottom]` trace rows."""
    tr = []
    for x in range(int(xl), int(xr) + 1, 2):
        f = (x - xl) / float(xr - xl)
        y = yl + f * (yr - yl) + sag * 4 * f * (1 - f)
        tr.append([x, int(y) - 1, int(y) + 1])
    return {"x_left_page": xl, "y_left_page": yl, "x_right_page": xr, "y_right_page": yr, "trace": tr}


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(AC.ENV_BIND, raising=False)
    assert not AC.bind_enabled()
    monkeypatch.setenv(AC.ENV_BIND, "1")
    assert AC.bind_enabled()
    monkeypatch.setenv(AC.ENV_BIND, "0")
    assert not AC.bind_enabled()


def test_side_of_a_cap_and_a_cup():
    assert AC.curve_side(_curve(0, 100, 100, 100, -15)["trace"], SP) == "above"
    assert AC.curve_side(_curve(0, 100, 100, 100, +15)["trace"], SP) == "below"
    assert AC.curve_side(_curve(0, 100, 100, 100, 0)["trace"], SP) is None


def test_both_ends_bind_to_the_head_beside_each_end():
    heads = [_h("a", -5, 108), _h("b", 105, 108), _h("far", 300, 108)]
    b = AC.bind_curve(_curve(0, 100, 100, 100), heads, SP)
    assert b["left"]["head"] == "a" and b["right"]["head"] == "b"


def test_a_refused_head_is_no_candidate():
    heads = [_h("a", -5, 108), _h("b", 105, 108)]
    b = AC.bind_curve(_curve(0, 100, 100, 100), heads, SP, usable=lambda k: k != "b")
    assert b["right"].get("head") is None and b["right"].get("edge")      # nothing usable beyond: the system's edge
    assert AC.bind_curve(_curve(0, 100, 100, 100), heads, SP)["right"]["head"] == "b"      # the twin


def test_an_end_short_of_a_head_further_on_is_unbound_never_an_edge():
    heads = [_h("a", -5, 108), _h("later", 160, 108)]
    r = AC.bind_curve(_curve(0, 100, 100, 100), heads, SP)["right"]
    assert r.get("unbound") == "no_head_at_end" and r["candidates"] == ["later"] and r["margin_spaces"] > 0


def test_a_chord_end_takes_the_top_note_for_an_arc_above_and_the_bottom_below():
    heads = [_h("lo_top", -5, 108), _h("lo_bot", -5, 125), _h("hi_top", 105, 108), _h("hi_bot", 105, 125)]
    above = AC.bind_curve(_curve(0, 100, 100, 100, -15), heads, SP)
    assert (above["left"]["head"], above["right"]["head"]) == ("lo_top", "hi_top")
    below = AC.bind_curve(_curve(0, 130, 100, 130, +15), heads, SP)
    assert (below["left"]["head"], below["right"]["head"]) == ("lo_bot", "hi_bot")
    flat = AC.bind_curve(_curve(0, 115, 100, 115, 0), heads, SP)
    assert flat["left"].get("unbound") == "chord_end_side_unread"     # no side, a chord: abstain, never pick


def test_two_columns_at_one_end_abstain_with_both_and_the_margin():
    heads = [_h("x1", -6, 108), _h("x2", 6, 108), _h("b", 105, 108)]
    left = AC.bind_curve(_curve(0, 100, 100, 100), heads, SP)["left"]
    assert left.get("unbound") == "two_columns_at_end" and len(left["candidates"]) == 2 and left["margin_spaces"] < 0


def test_one_head_at_both_ends_is_not_a_binding():
    heads = [_h("a", 50, 108)]
    b = AC.bind_curve(_curve(45, 100, 55, 100), heads, SP)
    assert b["left"].get("unbound") == "one_head_both_ends" == b["right"].get("unbound")


def test_heads_between_skip_the_end_chords():
    a, b = _h("a", 0, 100), _h("b", 100, 100)
    chord = _h("a2", 3, 120)
    mid = _h("m", 50, 100)
    assert AC.heads_between(a, b, [a, b, chord]) == []
    assert AC.heads_between(a, b, [a, b, chord, mid]) == ["m"]
    assert AC.heads_between(a, b, [a, b, mid], usable=lambda k: k != "m") == []


def test_an_arc_drawn_to_a_stem_tip_binds_the_head_at_that_end():
    # the right head sits 4 spaces below the curve's end; its up-stem's free end is where the slur stops (arc-recovery FINDINGS s6)
    heads = [_h("a", -5, 108), _h("b", 106, 145)]
    stem = (110, 102, 112, 145)
    assert AC.bind_curve(_curve(0, 100, 100, 100), heads, SP)["right"].get("head") is None          # the twin: the head alone is out of reach
    tips = AC.stem_tips(heads, [stem])
    assert tips and tips[0]["key"] == "b" and tips[0]["cy"] == 102
    r = AC.bind_curve(_curve(0, 100, 100, 100), heads + tips, SP)["right"]
    assert r["head"] == "b" and r.get("via_stem_tip")


def test_a_stem_tip_stands_for_the_extreme_head_on_its_side():
    chord = [_h("top", 100, 120), _h("bot", 100, 135)]
    up = AC.stem_tips(chord, [(104, 90, 106, 136)])
    assert up[0]["key"] == "top" and up[0]["cy"] == 90
    down = AC.stem_tips(chord, [(94, 119, 96, 170)])
    assert down[0]["key"] == "bot" and down[0]["cy"] == 170
    assert AC.stem_tips(chord, [(300, 90, 302, 136)]) == []
