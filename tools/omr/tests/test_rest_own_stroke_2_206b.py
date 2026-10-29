"""ROADMAP 2.206b: a 'stem' that is the rest ink's own stroke is not a stem on it; flags parse."""
from tools.omr.staged.adjudicators import head_rest_shape as H
from tools.omr import time_signature_locator as T

INK = (123, 478, 265, 710)          # Litolff p9 tile 10 on the corrected image (232 px = 2.32 sp)


def test_stem_spanning_the_whole_ink_is_its_own_stroke():
    assert H._is_own_stroke((207, 479, 32, 232), INK, 100.0)


def test_real_stem_leaves_the_head_sticking_out():
    # a stem 0.5 sp shorter than the ink (the head below it) is a stem, and one reaching past is too
    assert not H._is_own_stroke((207, 479, 32, 180), INK, 100.0)
    assert not H._is_own_stroke((207, 400, 32, 150), INK, 100.0)


def test_stem_outside_the_ink_columns_is_not_its_own_stroke():
    assert not H._is_own_stroke((400, 478, 32, 232), INK, 100.0)


def test_no_scale_no_claim():
    assert not H._is_own_stroke((207, 479, 32, 232), INK, 0.0)


def test_flags_default_on(monkeypatch):
    monkeypatch.delenv(H.ENV_OWN_STROKE, raising=False)
    monkeypatch.delenv(T.ENV_METER_SLOT, raising=False)
    assert H.own_stroke_enabled() and T.meter_slot_enabled()      # ON since 2026-10-27 (Sean "Land eraser path")
    monkeypatch.setenv(H.ENV_OWN_STROKE, "0")
    monkeypatch.setenv(T.ENV_METER_SLOT, "off")
    assert not H.own_stroke_enabled() and not T.meter_slot_enabled()
