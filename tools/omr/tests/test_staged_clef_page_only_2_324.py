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


DATA_R4 = pathlib.Path(__file__).with_name("data_clef_page_only_2_324_r4.npz")
MID_F_READ = ["mid_f_brahms_p25_s0_st3", "mid_f_brahms_p0_s0_st12", "mid_f_brahms_p8_s0_st9", "mid_f_litolff_p4_s1_st3"]
MID_F_NEVER = ["never_sf_litolff_p10_s0_st0", "never_half_litolff_p11_s0_st7", "never_flag_litolff_p11_s1_st10",
               "never_rest8_litolff_p16_s1_st9", "never_rest4_litolff_p9_s0_st11", "never_flag_brahms_p0_s0_st9",
               "never_half_brahms_p25_s0_st3"]


def _load(data, name):
    z = np.load(data)
    meta = json.loads(str(z["meta"]))[name]
    ink = np.unpackbits(z[name])[: meta["shape"][0] * meta["shape"][1]].reshape(meta["shape"]).astype(bool)
    return ink, meta


def _r4(name, grid="cell"):
    ink, meta = _load(DATA_R4, name)
    base = meta["lines_cell"] if grid == "cell" else meta["lines_staffwide"]
    return ink, meta, CP.local_lines(ink, base, meta["sp"], meta["box"][0])


def _gather_one_staff(monkeypatch, ink, meta, dets_boxes, flag):
    """`gather_clef_pagewide` (flag ON) or `gather_claimed_register` (OFF) on one real crop: a staff whose first bar starts left of the
    crop, so the box stands INSIDE the line; the cell carries the bar's own traced lines."""
    import types
    from tools.omr.staged import gather as G
    from tools.omr.staged import record as R
    from tools.omr.staged.record import Log, Q
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
    x_cut = max(1, int(meta["box"][0]) - 40)
    cells = [cell(0, x_cut - 200, x_cut), cell(1, x_cut, W)]
    pws = types.SimpleNamespace(page=types.SimpleNamespace(page_index=0, binary=np.where(ink, 0, 255).astype(np.uint8)),
                                staves=[types.SimpleNamespace(staff_index=0, system_index=0, line_ys=list(meta["lines_staffwide"]),
                                                              line_spacing_px=meta["sp"])])
    dets = {R.cell(0, 0, 0, 1).to_key(): [Det(n, bb, x_cut) for n, bb in dets_boxes]}
    monkeypatch.setattr(G, "_spacing", lambda st: meta["sp"])
    log = Log()
    if flag:
        G.gather_clef_pagewide(log, pws, cells, {0: (0, 0)}, dets)
    else:
        G.gather_claimed_register(log, pws, cells, {0: (0, 0)}, dets)
    rows = [r for r in log.rows(Q.CLAIMED_AREA, R.staff(0, 0, 0)) if (r.detail or {}).get("owner") == "clef"
            and (r.detail or {}).get("unit") == "area"]
    return log, rows, [R.glyph(0, 0, 0, 1, j).to_key() for j in range(len(dets_boxes))]


class TestRound4MidLineF:
    """ROADMAP 2.324 r4 (Sean 2026-11-20 "Teach it", shown Brahms p25 s0 staff 3): an F clef printed inside the line is READ by its own
    ink against its own bar's lines -- body at the top line, dot ink in both spaces round line 4, never a G's or a C's ink. CAUSE: the
    mid-line reader's witness was the dot PAIR (two separate round dots); on these clefs the dots touch the clef's curve, a stem or the
    ink beside them, so no separate pair exists. Round 2 gave the dot-place witness to the start of the staff only."""

    @pytest.mark.parametrize("name", ["mid_f_brahms_p25_s0_st3", "mid_f_brahms_p0_s0_st12", "mid_f_brahms_p8_s0_st9", "mid_f_litolff_p4_s1_st3"])
    def test_read_plain_by_its_ink(self, on, name):
        ink, meta, ll = _r4(name)
        got = CP.read_mid_f("clefF", meta["box"], ink, ll, meta["sp"])
        assert got["passed"] and got["plain"] and got["kind"] == "bass"

    def test_a_reading_at_its_cut_narrows_never_plain(self, on):
        ink, meta, ll = _r4("mid_f_brahms_p4_s1_st3")
        got = CP.read_mid_f("clefF", meta["box"], ink, ll, meta["sp"])
        assert got["passed"] and not got["plain"] and min(got["dots"]["upper"], got["dots"]["lower"]) < CP.F_DOT_PLAIN_FILL

    @pytest.mark.parametrize("name", ["mid_f_brahms_p25_s0_st3", "mid_f_brahms_p8_s0_st9", "mid_f_brahms_p4_s1_st3"])
    def test_the_old_mid_line_rule_refused_it_the_control_can_fail(self, on, name):
        ink, meta, ll = _r4(name, "staffwide")
        assert not CP.read_box("clefF", meta["box"], ink, ll, meta["sp"])["passed"]

    @pytest.mark.parametrize("name", MID_F_NEVER)
    def test_never_over_a_note_a_rest_or_a_dynamic(self, on, name):
        ink, meta, ll = _r4(name)
        got = CP.read_mid_f("clefF", meta["box"], ink, ll, meta["sp"])
        assert not got["passed"], (name, got.get("why"), got.get("body_top"), got.get("dots"))

    def test_the_quarter_rest_is_refused_by_its_empty_dot_space_and_the_dot_pair_would_have_read_it(self, on):
        # Litolff's quarter rest: on its own bar's lines the dot PAIR test names line 4 (the control can fail); one of its two spaces
        # holds no dot ink. (Round 4 also refused it by its body reaching the bottom line; round 5 dropped that never -- header F clefs'
        # tails reach the bottom line too, it measured where the line clearing cut the tail, not the mark.)
        ink, meta, ll = _r4("never_rest4_litolff_p9_s0_st11")
        assert CP.read_box("clefF", meta["box"], ink, ll, meta["sp"])["passed"]
        got = CP.read_mid_f("clefF", meta["box"], ink, ll, meta["sp"])
        assert not got["passed"] and got["why"] == "f_no_dot_ink_in_both_spaces"

    def test_an_f_body_with_one_dot_not_clear_is_not_read(self, on):
        # Litolff p10 s0 staff 3: the lower dot sits on a thick line 4 and goes with it -- not read (its header clef is bass already)
        ink, meta, ll = _r4("mid_f_litolff_p10_s0_st3")
        got = CP.read_mid_f("clefF", meta["box"], ink, ll, meta["sp"])
        assert not got["passed"] and got["why"] == "f_no_dot_ink_in_both_spaces"

    @pytest.mark.parametrize("name", ["never_sf_litolff_p10_s0_st0", "never_half_brahms_p25_s0_st3"])
    def test_the_body_at_the_top_line_is_the_never_that_refuses_it(self, on, monkeypatch, name):
        ink, meta, ll = _r4(name)
        assert CP.read_mid_f("clefF", meta["box"], ink, ll, meta["sp"])["why"] == "f_body_not_at_the_top_line"

    def test_flag_on_the_p25_clef_is_read_once_as_a_change(self, monkeypatch):
        ink, meta = _load(DATA_R4, "mid_f_brahms_p25_s0_st3")
        log, rows, _keys = _gather_one_staff(monkeypatch, ink, meta, [("clefF", meta["box"])], True)
        read = [r for r in rows if r.detail.get("standing") == "READ"]
        assert len(read) == 1 and read[0].detail.get("kind") == "bass" and read[0].detail.get("change") is True
        assert CP.clef_in_force(meta["box"][2] + 30, CP.changes_of(read), [], header="tenor")[0] == "bass"

    @pytest.mark.parametrize("name", ["never_half_brahms_p25_s0_st3", "never_sf_litolff_p10_s0_st0"])
    def test_flag_on_a_box_whose_ink_is_not_an_f_clef_is_no_carry_stop(self, monkeypatch, name):
        # the touched-pages run: Brahms p25's half note by the barline (bar 1) was a clef-shaped candidate, so the bass clef read in
        # bar 0 stopped there and bars 1-9 went unread; a box refused by an ink never is not a clef and stops nothing
        from tools.omr.staged import record as R
        from tools.omr.staged.record import Q
        ink, meta = _load(DATA_R4, name)
        log, rows, _keys = _gather_one_staff(monkeypatch, ink, meta, [("clefF", meta["box"])], True)
        refusals = log.refusals(Q.CLAIMED_AREA, R.staff(0, 0, 0))
        assert refusals and all(r.detail.get("why") in CP.MID_F_NOT_A_CLEF for r in refusals)
        assert CP.candidates_of(refusals) == []
        assert CP.clef_in_force(meta["box"][2] + 30, [(0.0, "bass", None)], CP.candidates_of(refusals), header="tenor")[0] == "bass"

    def test_flag_on_a_reading_at_its_cut_is_a_strong_candidate(self, monkeypatch):
        from tools.omr.staged import record as R
        from tools.omr.staged.record import Q
        ink, meta = _load(DATA_R4, "mid_f_brahms_p4_s1_st3")
        log, rows, _keys = _gather_one_staff(monkeypatch, ink, meta, [("clefF", meta["box"])], True)
        assert not [r for r in rows if r.detail.get("standing") == "READ"]
        cands = CP.candidates_of(log.refusals(Q.CLAIMED_AREA, R.staff(0, 0, 0)))
        assert len(cands) == 1 and cands[0][2].detail.get("strong")
        assert CP.clef_in_force(meta["box"][2] + 30, [], cands, header="tenor")[0] is None     # unread, never pitched as tenor


class TestRound3RefusedBoxStillNarrows:
    """A clef-sized box the page-wide pass cannot read keeps the NARROWED claim the register filed for it (round 3; Brahms p5's dots were
    written as a C4 in round 2 when nothing claimed them). Shown on a box that is not a clef (Litolff's quarter rest)."""

    def test_flag_on_the_narrowed_claim_is_filed_and_nothing_is_read(self, monkeypatch):
        ink, meta = _load(DATA_R4, "never_rest4_litolff_p9_s0_st11")
        log, rows, _keys = _gather_one_staff(monkeypatch, ink, meta, [("clefF", meta["box"])], True)
        assert [r.detail.get("standing") for r in rows] == ["NARROWED"] and rows[0].detail.get("source") == "detector"

    def test_flag_off_the_register_filed_the_same(self, monkeypatch):
        ink, meta = _load(DATA_R4, "never_rest4_litolff_p9_s0_st11")
        log, rows, _keys = _gather_one_staff(monkeypatch, ink, meta, [("clefF", meta["box"])], False)
        assert [r.detail.get("standing") for r in rows] == ["NARROWED"]

    def test_p5_flag_on_the_head_on_its_dots_is_inside_the_read_clef(self, monkeypatch):
        ink, meta = _load(DATA_R3, "f_mid_bar_brahms_p5_s1_st3")
        log, rows, keys = _gather_one_staff(monkeypatch, ink, meta, [("clefF", meta["box"]), ("noteheadBlackOnLine", meta["head_box"])], True)
        read = [r for r in rows if r.detail.get("standing") == "READ"]
        assert len(read) == 1 and read[0].detail.get("kind") == "bass"
        assert read[0].detail["boxes_inside"][keys[1]]["ink_share_inside"] >= 0.5


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


# ----------------------------------------------------------------------------------------------------------------------------------
# Round 5 (Sean 2026-11-20: "every note on the page is dependent on the clefs being correct"): a clef is recognised by its shape on the
# staff wherever it stands; the detector's box is one more witness, never a requirement. Real pixels: the 7 start-of-staff clefs the
# detector drew no box on (carried from other systems before), read in the system's clef column; the mid-line clefG boxes.
# ----------------------------------------------------------------------------------------------------------------------------------
DATA_R5 = pathlib.Path(__file__).with_name("data_clef_page_only_2_324_r5.npz")
NOBOX = ["nobox_bass_litolff_p2_s1_st3", "nobox_bass_litolff_p4_s1_st6", "nobox_bass_litolff_p4_s1_st10", "nobox_treble_litolff_p6_s1_st0",
         "nobox_bass_litolff_p11_s0_st8", "nobox_bass_litolff_p11_s1_st5", "nobox_bass_brahms_p14_s0_st12"]


def _r5(name):
    ink, meta = _load(DATA_R5, name)
    key = meta.get("place") or meta["box"]
    return ink, meta, CP.local_lines(ink, meta["lines_cell"], meta["sp"], key[0])


class TestRound5ClefFromInk:
    @pytest.mark.parametrize("name", NOBOX)
    def test_a_start_of_staff_clef_with_no_box_is_read_from_its_own_ink(self, on, name):
        ink, meta, ll = _r5(name)
        got = CP.read_header_ink(ink, meta["place"], ll, meta["sp"])
        assert got["passed"] and got.get("plain") and got["kind"] == meta["truth"], got.get("why")

    @pytest.mark.parametrize("name", [n for n in NOBOX if "_bass_" in n])
    def test_never_a_g_clef_from_a_bass_clefs_ink(self, on, name):
        ink, meta, ll = _r5(name)
        assert not CP.read_g(ink, meta["place"], ll, meta["sp"], box_witness=False)["passed"]

    def test_never_an_f_clef_from_the_treble_clefs_ink(self, on):
        ink, meta, ll = _r5("nobox_treble_litolff_p6_s1_st0")
        pc = CP.glyph_piece(ink, meta["place"], ll, meta["sp"])
        assert not CP.read_mid_f("clefF", pc["box"], ink, ll, meta["sp"], dots_beside_core=True)["passed"]

    def test_the_curl_is_the_second_witness_with_no_box_the_control_can_fail(self, on, monkeypatch):
        ink, meta, ll = _r5("nobox_treble_litolff_p6_s1_st0")
        got = CP.read_g(ink, meta["place"], ll, meta["sp"], box_witness=False)
        assert got["passed"] and got["curl"] >= CP.G_CURL_MIN_REGIONS
        monkeypatch.setattr(CP, "curl_round_line2", lambda *a, **k: 0)
        assert not CP.read_g(ink, meta["place"], ll, meta["sp"], box_witness=False)["passed"]

    @staticmethod
    def _midg(name, heads=True):
        ink, meta, ll = _r5(name)
        bb, sp = meta["box"], meta["sp"]
        return CP.read_g(ink, [bb[0], ll[0] - 2.5 * sp, bb[2], ll[4] + 2.5 * sp], ll, sp, box_witness=True,
                         heads=meta["heads"] if heads else ())

    def test_seans_mid_line_treble_clef_is_read_by_its_curl(self, on):
        # Sean r5 tile 5, "treble clef" (Brahms p14 s1 staff 9): ink past the staff and the curl round line 2 (3 regions), no box needed
        ink, meta, ll = _r5("midg_treble_brahms_p14_s1_st9")
        bb, sp = meta["box"], meta["sp"]
        got = CP.read_g(ink, [bb[0], ll[0] - 2.5 * sp, bb[2], ll[4] + 2.5 * sp], ll, sp, box_witness=False)
        assert got["passed"] and got["witness"] == "g_curl" and got["curl"] >= CP.G_CURL_MIN_REGIONS

    def test_the_treble_clef_claims_its_own_ink_not_the_word_over_it(self, on, monkeypatch):
        # round 7b (Sean: the clef claims only its own ink): Brahms p14 s1 staff 9 -- "div." stands over the treble clef, 1.4-2.5 spaces
        # above the top line; the measuring piece joins it, the claim must not take it
        ink, meta, ll = _r5("midg_treble_brahms_p14_s1_st9")
        bb, sp = meta["box"], meta["sp"]
        place = [bb[0], ll[0] - 2.5 * sp, bb[2], ll[4] + 2.5 * sp]
        got = CP.read_g(ink, place, ll, sp, box_witness=False)
        assert got["passed"] and got["box"][1] >= ll[0] - 1.0 * sp
        monkeypatch.setattr(CP, "own_ink_box", lambda ink_, pc, *a, **k: list(pc["box"]))     # the control: the piece's box (round 7)
        assert CP.read_g(ink, place, ll, sp, box_witness=False)["box"][1] < ll[0] - 2.0 * sp

    @pytest.mark.parametrize("name,curl", [("midg_never_litolff_p10_s1_st4", 0), ("midg_never_litolff_p9_s0_st3", 1)])
    def test_seans_stem_and_half_note_chord_are_refused_by_the_curl_alone(self, on, name, curl):
        # Sean r5 tile 1 "just a stem" (no curl), tile 10 "2 half notes in a chord" (one ring, not a curl cut by a stroke): refused with
        # no detector head box and no box witness -- the curl does the refusing by itself
        ink, meta, ll = _r5(name)
        bb, sp = meta["box"], meta["sp"]
        got = CP.read_g(ink, [bb[0], ll[0] - 2.5 * sp, bb[2], ll[4] + 2.5 * sp], ll, sp, box_witness=False)
        assert not got["passed"] and got["why"] == "g_no_curl_round_line_2" and got["curl"] == curl

    @pytest.mark.parametrize("name", ["midg_never_litolff_p10_s1_st4", "midg_never_litolff_p9_s0_st3"])
    def test_with_the_curl_test_switched_off_they_pass_the_control_can_fail(self, on, monkeypatch, name):
        ink, meta, ll = _r5(name)
        bb, sp = meta["box"], meta["sp"]
        monkeypatch.setattr(CP, "G_CURL_MIN_REGIONS", 0)
        assert CP.read_g(ink, [bb[0], ll[0] - 2.5 * sp, bb[2], ll[4] + 2.5 * sp], ll, sp, box_witness=False)["passed"]

    @pytest.mark.parametrize("name", ["midg_never_litolff_p10_s1_st4", "midg_never_litolff_p9_s0_st3"])
    def test_the_head_on_their_ink_is_a_second_witness(self, on, name):
        ink, meta, ll = _r5(name)
        bb, sp = meta["box"], meta["sp"]
        got = CP.read_g(ink, [bb[0], ll[0] - 2.5 * sp, bb[2], ll[4] + 2.5 * sp], ll, sp, box_witness=True, heads=meta["heads"])
        assert not got["passed"] and got["why"] == "g_over_a_notehead" and got["why"] in CP.MID_F_NOT_A_CLEF

    @pytest.mark.parametrize("name", NOBOX)
    def test_the_ink_read_clef_claims_only_what_a_clef_can_reach(self, on, name):
        # Sean r5 tiles 2, 3, 6: the claim ran down the system's barline -- the place starts right of the barline, the area stays inside
        # a clef's reach past the staff
        ink, meta, ll = _r5(name)
        got = CP.read_header_ink(ink, meta["place"], ll, meta["sp"])
        up, down = CP.CLEF_REACH_SPACES["G" if meta["truth"] == "treble" else "F"]
        assert got["box"][1] >= ll[0] - up * meta["sp"] - 1 and got["box"][3] <= ll[4] + down * meta["sp"] + 1

    def test_a_strong_g_candidate_stops_a_non_g_clef_and_nothing_else(self):
        import types
        row = types.SimpleNamespace(detail={"strong": True, "family": "G", "source": CP.SOURCE, "candidate": True, "x_page": 100.0})
        cands = CP.candidates_of([row])
        assert CP.clef_in_force(150.0, [], cands, header="alto")[0] is None
        assert CP.clef_in_force(150.0, [], cands, header="treble") is None
        assert CP.clef_in_force(50.0, [], cands, header="alto") is None
