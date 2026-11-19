"""ROADMAP 2.324 -- the clef is read once, on the page, by the page-wide pass (`OMR_CLEF_PAGE_ONLY`), STAGED GATHER.

Every case is cut from the pipeline's own page binary (master cell map) at a mark Sean named or labelled, or a mark read the same before
and after; `data_clef_page_only_2_324.npz` holds the ink, the staff lines and the detector box in crop pixels (`what` says whose word it
is). Each rule is shown to FAIL where it should: the old rule (flag OFF) on the Breitkopf C clefs and the merged Litolff F dots, and the
widened rule on the marks it must still refuse (a barline, a G clef beside a barline, a G or C clef looked at as an F clef).
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from tools.omr.staged import clef_pagewide as CP

DATA = pathlib.Path(__file__).with_name("data_clef_page_only_2_324.npz")


def _case(name):
    z = np.load(DATA)
    meta = json.loads(str(z["meta"]))[name]
    ink = np.unpackbits(z[name])[: meta["shape"][0] * meta["shape"][1]].reshape(meta["shape"]).astype(bool)
    if meta["box"] is not None:          # the reader measures the lines AT the clef (CLAUDE §5), as `gather_clef_pagewide` hands them
        meta["lines"] = CP.local_lines(ink, meta["lines"], meta["sp"], meta["box"][0])
    return ink, meta


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv(CP.ENV_PAGE_ONLY, "1")


@pytest.fixture
def off(monkeypatch):
    monkeypatch.delenv(CP.ENV_PAGE_ONLY, raising=False)


def _passing_c(ink, meta, x0=0, x1=None):
    sp = meta["sp"]
    return [c for c in CP.c_bars(ink, meta["lines"], sp, x0, x1 if x1 is not None else ink.shape[1]) if c["passed"]]


def _c_name(ink, meta, cand):
    return CP.name_c(cand["middle_y"], cand.get("lines_local") or meta["lines"])[0]


class TestCClef:
    @pytest.mark.parametrize("name,kind", [("c_tenor_brahms_p0", "tenor"), ("c_alto_brahms_p0", "alto")])
    def test_breitkopf_header_c_clef_is_read_against_its_own_thin_line(self, on, name, kind):
        ink, meta = _case(name)
        got = CP.read_box("clefC" + kind.capitalize(), meta["box"], ink, meta["lines"], meta["sp"])
        assert got["passed"] and got["kind"] == kind

    @pytest.mark.parametrize("name", ["c_tenor_brahms_p0", "c_alto_brahms_p0"])
    def test_the_old_rule_misses_it_the_control_can_fail(self, off, name):
        ink, meta = _case(name)
        got = CP.read_box("clefCTenor", meta["box"], ink, meta["lines"], meta["sp"])
        assert not got["passed"] and got["why"] == "c_no_bar_and_bowls"

    def test_litolff_header_alto_and_mid_staff_tenor_read_as_before(self, on):
        ink, meta = _case("c_alto_litolff_p9")
        assert [_c_name(ink, meta, c) for c in _passing_c(ink, meta)] == ["alto"]
        ink, meta = _case("c_change_tenor_litolff_p9")
        assert [_c_name(ink, meta, c) for c in _passing_c(ink, meta)] == ["tenor"]

    def test_never_a_c_clef_from_a_barline(self, on):
        ink, meta = _case("barline_litolff_p5")
        assert _passing_c(ink, meta) == []

    def test_a_g_clef_beside_a_barline_is_refused_by_the_thin_line_ratio(self, on, monkeypatch):
        ink, meta = _case("g_beside_barline_litolff_p8")
        assert _passing_c(ink, meta) == []
        monkeypatch.setattr(CP, "C_BAR_THICK_RATIO", 2.0)      # the boundary: at 2.0 its bowls would pass it as an alto clef
        assert [_c_name(ink, meta, c) for c in _passing_c(ink, meta)] == ["alto"]


class TestFClef:
    @pytest.mark.parametrize("name", ["f_bass_litolff_p2", "f_bass_litolff_p9"])
    def test_merged_dots_are_read_as_ink_at_their_two_places(self, on, name):
        ink, meta = _case(name)
        got = CP.read_box("clefF", meta["box"], ink, meta["lines"], meta["sp"], header=True)
        assert got["passed"] and got["kind"] == "bass" and got.get("witness") == "f_dot_places"

    @pytest.mark.parametrize("name", ["f_bass_litolff_p2", "f_bass_litolff_p9"])
    def test_the_dot_pair_test_misses_them_the_control_can_fail(self, on, name):
        ink, meta = _case(name)
        got = CP.read_box("clefF", meta["box"], ink, meta["lines"], meta["sp"])         # not a header read: the pair test only
        assert not got["passed"] and got["why"] == "f_no_dots"

    def test_a_breitkopf_header_bass_clef_is_still_read_by_its_dot_pair(self, on):
        ink, meta = _case("two_staves_brahms_p12")
        got = CP.read_box("clefF", meta["box"], ink, meta["lines"], meta["sp"], header=True)
        assert got["passed"] and got["kind"] == "bass" and got.get("witness") is None

    @pytest.mark.parametrize("name", ["g_as_f_litolff_p2", "c_alto_brahms_p0", "g_treble_litolff_p2"])
    def test_never_an_f_clef_with_no_dot_ink_at_its_places(self, on, name):
        ink, meta = _case(name)
        fp = CP.f_dot_places(ink, meta["box"], meta["lines"], meta["sp"])
        assert not fp["passed"] and min(fp["upper"], fp["lower"]) < CP.F_DOT_MIN_FILL


class TestGClef:
    @pytest.mark.parametrize("name", ["g_treble_litolff_p2", "g_treble_litolff_p6_tile5"])
    def test_header_g_clef_read_by_its_box_and_its_ink_past_the_staff(self, on, name):
        ink, meta = _case(name)
        got = CP.read_header_g("clefG", meta["box"], ink, meta["lines"], meta["sp"])
        assert got["passed"] and got["kind"] == "treble"

    def test_seans_tile_5_g_clef_is_never_a_c_clef(self, on):
        ink, meta = _case("g_treble_litolff_p6_tile5")
        b = meta["box"]
        assert _passing_c(ink, meta, int(b[0] - meta["sp"]), int(b[2])) == []

    def test_no_ink_past_the_staff_is_no_g_clef(self, on):
        ink, meta = _case("g_treble_litolff_p2")
        blank = ink.copy()
        blank[: int(meta["lines"][0])] = False
        blank[int(meta["lines"][-1]) + 1:] = False
        got = CP.read_header_g("clefG", meta["box"], blank, meta["lines"], meta["sp"])
        assert not got["passed"] and got["why"] == "g_no_ink_past_the_staff"


class TestOwnStaff:
    def test_a_clef_belongs_to_the_staff_whose_lines_it_sits_on(self):
        ink, meta = _case("two_staves_brahms_p12")
        sp, box = meta["sp"], meta["box"]
        own = CP.local_lines(ink, meta["lines"], sp, box[0])
        other = CP.local_lines(ink, meta["extra_lines"][0], sp, box[0])
        assert CP.on_this_staff(box, own, sp) and not CP.on_this_staff(box, other, sp)
