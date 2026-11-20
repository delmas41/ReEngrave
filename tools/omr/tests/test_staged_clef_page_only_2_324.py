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

    @pytest.mark.parametrize("name", ["g_as_f_litolff_p2", "g_treble_litolff_p2"])
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


# ----------------------------------------------------------------------------------------------------------------------------------
# Round 3: the 15 Litolff start-of-staff clefs round 2 did not read, cut from the page binary with BOTH line grids the run had: the
# staff-wide lines gather handed the page-wide pass (`lines_staffwide`) and the header cell's own traced lines (`lines_cell`, what
# `clef_pagewide.cell_lines_page` returns). Cause: at these headers the staff-wide lines stand 0.25-1.1 spaces off the print, further
# than `local_lines` reaches -- the clef was measured against lines that were not there.
# ----------------------------------------------------------------------------------------------------------------------------------
DATA_R3 = pathlib.Path(__file__).with_name("data_clef_page_only_2_324_r3.npz")
G_MISSES = ["g_litolff_p4_s0_st0", "g_litolff_p4_s0_st1", "g_litolff_p4_s0_st5", "g_litolff_p4_s0_st6", "g_litolff_p4_s0_st7",
            "g_litolff_p6_s0_st1", "g_litolff_p6_s0_st2", "g_litolff_p8_s0_st0", "g_litolff_p10_s0_st1", "g_litolff_p16_s0_st0"]
F_MISSES = ["f_litolff_p4_s0_st3", "f_litolff_p6_s0_st3", "f_litolff_p6_s1_st10", "f_litolff_p8_s0_st8"]


def _r3(name, grid="cell"):
    z = np.load(DATA_R3)
    meta = json.loads(str(z["meta"]))[name]
    ink = np.unpackbits(z[name])[: meta["shape"][0] * meta["shape"][1]].reshape(meta["shape"]).astype(bool)
    base = meta["lines_cell"] if grid == "cell" else meta["lines_staffwide"]
    x = meta["box"][0] if meta["box"] is not None else meta["cell_x0"]
    return ink, meta, CP.local_lines(ink, base, meta["sp"], x)


def _r2_header_g(ink, box, lines, sp):
    """Round 2's header G rule, as it stood (a010e9a15): the BOX reaching past the staff, then the ink past it."""
    if not (box[1] <= lines[0] - CP.G_REACH_SPACES * sp and box[3] >= lines[-1] + CP.G_REACH_SPACES * sp):
        return False
    return CP.g_witness(ink, box, lines, sp)["passed"]


def _header_c(ink, meta, ll):
    x0 = int(meta["cell_x0"])
    return [c for c in CP.c_bars(ink, ll, meta["sp"], x0, x0 + int(CP.HEADER_WINDOW_SPACES * meta["sp"])) if c["why"] != "bar_too_thin"]


class TestRound3LinesAtTheHeader:
    def test_cell_lines_page_is_the_cells_own_grid_in_page_px(self):
        import types
        cell = types.SimpleNamespace(staff_line_ys_canonical=[400, 500, 600, 700, 800], bbox_page_px=(10, 300, 200, 520), upscale_factor=4.0)
        assert CP.cell_lines_page(cell) == [400.0, 425.0, 450.0, 475.0, 500.0]
        assert CP.cell_lines_page(types.SimpleNamespace(staff_line_ys_canonical=[1, 2], bbox_page_px=(0, 0, 1, 1), upscale_factor=1.0)) is None

    @pytest.mark.parametrize("name", G_MISSES + F_MISSES + ["c_litolff_p8_s0_st7"])
    def test_the_staff_wide_lines_are_off_the_print_at_the_header(self, name):
        # the measured cause, per clef: the header cell's own lines sit this far from the staff-wide ones (0.25-1.1 spaces)
        _ink, meta, _ll = _r3(name)
        off = abs(meta["lines_cell"][0] - meta["lines_staffwide"][0]) / meta["sp"]
        assert 0.2 <= off <= 1.2


class TestRound3GClef:
    @pytest.mark.parametrize("name", G_MISSES)
    def test_read_by_its_ink_against_the_header_cells_own_lines(self, on, name):
        ink, meta, ll = _r3(name, "cell")
        got = CP.read_header_g("clefG", meta["box"], ink, ll, meta["sp"])
        assert got["passed"] and got["kind"] == "treble"

    @pytest.mark.parametrize("name", G_MISSES)
    def test_round_2s_rule_on_the_staff_wide_lines_refuses_it_the_control_can_fail(self, on, name):
        ink, meta, ll = _r3(name, "staffwide")
        assert not _r2_header_g(ink, meta["box"], ll, meta["sp"])

    @pytest.mark.parametrize("name", ["g_litolff_p4_s0_st5", "g_litolff_p4_s0_st6", "g_litolff_p6_s0_st1", "g_litolff_p6_s0_st2"])
    def test_its_spine_is_still_never_a_c_clef(self, on, name):
        # these G spines pass the C bar test; their own tail and curl refuse them, with the barline window closing on (round 3)
        ink, meta, ll = _r3(name, "cell")
        cands = _header_c(ink, meta, ll)
        assert cands and all(c["why"] == "g_clef_shape" for c in cands)


class TestRound3FClef:
    @pytest.mark.parametrize("name", F_MISSES)
    def test_read_against_the_header_cells_own_lines(self, on, name):
        ink, meta, ll = _r3(name, "cell")
        got = CP.read_box("clefF", meta["box"], ink, ll, meta["sp"], header=True)
        assert got["passed"] and got["kind"] == "bass"

    @pytest.mark.parametrize("name", ["f_litolff_p4_s0_st3", "f_litolff_p6_s0_st3", "f_litolff_p6_s1_st10"])
    def test_on_the_staff_wide_lines_it_is_refused_the_control_can_fail(self, on, name):
        ink, meta, ll = _r3(name, "staffwide")
        assert not CP.read_box("clefF", meta["box"], ink, ll, meta["sp"], header=True)["passed"]

    @pytest.mark.parametrize("name", ["f_litolff_p6_s1_st10", "f_litolff_p8_s0_st8"])
    def test_a_dot_at_one_point_of_its_space_misses_it_the_control_can_fail(self, on, monkeypatch, name):
        # round 2 looked for each dot at ONE point (half a space from the line); here the dots stand high in their spaces
        ink, meta, ll = _r3(name, "cell")
        monkeypatch.setattr(CP, "F_DOT_SPACE_MIDDLE", (0.5, 0.5))
        assert not CP.read_box("clefF", meta["box"], ink, ll, meta["sp"], header=True)["passed"]

    def test_never_an_f_clef_from_a_g_clefs_ink(self, on, monkeypatch):
        # a G clef whose ink fills the dot places (0.84), under a box whose top sits on the top line (an `clefF` box on it)
        ink, meta, ll = _r3("g_litolff_p16_s0_st1", "cell")
        box = [meta["box"][0], ll[0], meta["box"][2], ll[3]]
        assert CP.f_dot_places(ink, box, ll, meta["sp"])["passed"]
        got = CP.read_box("clefF", box, ink, ll, meta["sp"], header=True)
        assert not got["passed"] and got["why"] == "f_box_ink_past_the_staff_like_a_g"
        monkeypatch.setattr(CP, "g_witness", lambda *a, **k: {"passed": False})       # the never is what refuses it
        assert CP.read_box("clefF", box, ink, ll, meta["sp"], header=True)["passed"]

    def test_never_an_f_clef_from_a_c_clefs_bowls(self, on, monkeypatch):
        ink, meta = _case("c_alto_brahms_p0")
        assert CP.f_dot_places(ink, meta["box"], meta["lines"], meta["sp"])["passed"]       # the bowls fill the dot places
        got = CP.read_box("clefF", meta["box"], ink, meta["lines"], meta["sp"], header=True)
        assert not got["passed"] and got["why"] == "f_box_on_a_c_bar"
        monkeypatch.setattr(CP, "c_bars", lambda *a, **k: [])                              # the never is what refuses it
        assert CP.read_box("clefF", meta["box"], ink, meta["lines"], meta["sp"], header=True)["passed"]


class TestRound3RefusedBoxStillNarrows:
    """Brahms p5 s1 staff 3 bar 0 (the round-2 trace): a mid-bar bass clef whose dots are fused with the ink beside them is refused by
    the dot test; its `clefF` box was the register's NARROWED claim, so the head box the detector drew on its dots was narrowed. With the
    register's clef claims stood down (flag ON) nothing claimed that ink and the dots were written as a C4. The page-wide pass now files
    the NARROWED claim for a box it could not read."""

    def _run(self, monkeypatch, flag):
        import types
        from tools.omr.staged import gather as G
        from tools.omr.staged import record as R
        from tools.omr.staged.record import Log, Q
        z = np.load(DATA_R3)
        meta = json.loads(str(z["meta"]))["f_mid_bar_brahms_p5_s1_st3"]
        ink = np.unpackbits(z["f_mid_bar_brahms_p5_s1_st3"])[: meta["shape"][0] * meta["shape"][1]].reshape(meta["shape"]).astype(bool)
        if flag:
            monkeypatch.setenv(CP.ENV_PAGE_ONLY, "1")
        else:
            monkeypatch.delenv(CP.ENV_PAGE_ONLY, raising=False)
        H, W = ink.shape
        lines = meta["lines_cell"]

        class Det:
            def __init__(self, name, bb, cx0):
                self.smufl_name, self.confidence, self.category = name, 0.9, ""
                self.x_canonical, self.y_canonical = bb[0] - cx0, bb[1]
                self.width_canonical, self.height_canonical = bb[2] - bb[0], bb[3] - bb[1]

        def cell(k, x0, x1):
            return types.SimpleNamespace(staff_index=0, measure_index=k, page_index=0, bbox_page_px=(x0, 0, x1, H), upscale_factor=1.0,
                                         staff_line_ys_canonical=list(lines))
        cells = [cell(0, 0, 60), cell(1, 60, W)]
        pws = types.SimpleNamespace(page=types.SimpleNamespace(page_index=0, binary=np.where(ink, 0, 255).astype(np.uint8)),
                                    staves=[types.SimpleNamespace(staff_index=0, system_index=0, line_ys=list(lines),
                                                                  line_spacing_px=meta["sp"])])
        dets = {R.cell(0, 0, 0, 1).to_key(): [Det("clefF", meta["box"], 60), Det("noteheadBlackOnLine", meta["head_box"], 60)]}
        monkeypatch.setattr(G, "_spacing", lambda st: meta["sp"])
        log = Log()
        if flag:
            G.gather_clef_pagewide(log, pws, cells, {0: (0, 0)}, dets)
        else:
            G.gather_claimed_register(log, pws, cells, {0: (0, 0)}, dets)
        return [r for r in log.rows(Q.CLAIMED_AREA, R.staff(0, 0, 0)) if (r.detail or {}).get("owner") == "clef"
                and (r.detail or {}).get("unit") == "area"], R.glyph(0, 0, 0, 1, 1).to_key()

    def test_the_box_is_refused_by_the_dot_test(self, on):
        ink, meta, ll = _r3("f_mid_bar_brahms_p5_s1_st3", "cell")
        got = CP.read_box("clefF", meta["box"], ink, ll, meta["sp"])
        assert not got["passed"] and got["why"] == "f_no_dots"

    def test_flag_on_the_page_wide_pass_files_the_narrowed_claim_over_the_head_on_its_dots(self, monkeypatch):
        rows, head = self._run(monkeypatch, True)
        nar = [r for r in rows if r.detail.get("standing") == "NARROWED"]
        assert len(nar) == 1 and nar[0].detail.get("source") == "detector" and nar[0].detail.get("filed_by") == CP.SOURCE
        assert nar[0].detail["boxes_inside"][head]["ink_share_inside"] >= 0.5
        assert not [r for r in rows if r.detail.get("standing") == "READ"]                    # never read from the box alone

    def test_flag_off_the_register_filed_the_same_narrowed_claim(self, monkeypatch):
        rows, head = self._run(monkeypatch, False)
        assert [r.detail.get("standing") for r in rows] == ["NARROWED"] and head in rows[0].detail["boxes_inside"]


class TestRound3CClef:
    def test_alto_beside_the_system_barline_is_read(self, on):
        ink, meta, ll = _r3("c_litolff_p8_s0_st7", "cell")
        got = [c for c in _header_c(ink, meta, ll) if c["passed"]]
        assert [CP.name_c(c["middle_y"], c.get("lines_local") or ll)[0] for c in got] == ["alto"]
        assert got[0].get("barline_left_x") is not None

    def test_with_the_barlines_ink_counted_as_its_own_it_is_g_shaped_the_control_can_fail(self, on, monkeypatch):
        ink, meta, ll = _r3("c_litolff_p8_s0_st7", "cell")
        monkeypatch.setattr(CP, "barline_left_of", lambda *a, **k: None)
        cands = _header_c(ink, meta, ll)
        assert cands and not any(c["passed"] for c in cands) and cands[0]["why"] == "g_clef_shape"
