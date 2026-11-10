"""ROADMAP 2.282 (flag `OMR_CLAIM_ORDER`, default OFF): the claim order of heads vs accidentals. Pure tests on `stroke_owner.own_strokes`; the flag OFF is today's
behaviour exactly (a stroke both families fit, with no one clear, is CONTESTED)."""
from tools.omr.staged import stroke_owner as SO


def _blob(ordinal=0, w=0.9, h=0.9, sp=20.0, area=0.8):
    return SO.Ink(ordinal, "blob", (100.0, 100.0, w * sp, h * sp), max(w, h), 0.4, area, sp)     # median run 0.4 sp: not a head's body (2.242's 0.55)


def _claims():
    return [SO.Claim("glyph/h", "head", "noteheadBlackInSpace", (0,)), SO.Claim("glyph/a", "accidental", "accidentalDoubleSharp", (0,))]    # a double sharp is head-sized (1.0 sp)


def test_flag_off_is_contested_with_both_clear(monkeypatch):
    monkeypatch.delenv(SO.ENV_ORDER, raising=False)
    assert SO.claim_order_mode() == ""
    # a head-sized blob that is also an accidental-sized blob: both `clear`
    own = SO.own_strokes([_blob()], _claims())
    assert own[0].state == "contested"


def test_heads_first_gives_the_stroke_to_the_head(monkeypatch):
    monkeypatch.setenv(SO.ENV_ORDER, "heads_first")
    tiers = SO.tiers_for_order(SO.TIERS, SO.claim_order_mode())
    assert tiers == tuple(tuple(t) for t in SO.TIERS)
    own = SO.own_strokes([_blob()], _claims(), tiers=tiers, resolve=True)
    assert (own[0].state, own[0].family) == ("decided", "head")


def test_accidentals_first_gives_the_stroke_to_the_accidental(monkeypatch):
    monkeypatch.setenv(SO.ENV_ORDER, "accidentals_first")
    tiers = SO.tiers_for_order(SO.TIERS, SO.claim_order_mode())
    flat = [f for t in tiers for f in t]
    assert flat.index("accidental") < flat.index("head")
    own = SO.own_strokes([_blob()], _claims(), tiers=tiers, resolve=True)
    assert (own[0].state, own[0].family) == ("decided", "accidental")


def test_one_family_fits_is_unchanged_by_the_order(monkeypatch):
    # a long vertical: an accidental's stem fits, a head never does -- the order cannot move it
    v = SO.Ink(0, "vertical", (100.0, 100.0, 4.0, 40.0), 2.0, 0.2, 0.3, 20.0)
    for mode in ("", "heads_first", "accidentals_first"):
        monkeypatch.setenv(SO.ENV_ORDER, mode)
        m = SO.claim_order_mode()
        tiers = SO.tiers_for_order(SO.TIERS, m)
        own = SO.own_strokes([v], _claims(), tiers=tiers, resolve=bool(m))
        assert (own[0].state, own[0].family) == ("decided", "accidental"), mode
