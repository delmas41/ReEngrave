"""The free margin reader, and the order the three readers run in.

The subprocess half needs `.venv-surya` and skips without it. The chain and the
crop geometry do not, and those are where the wiring can go wrong silently — a
paid call made on a page the free reader already answered costs money, and a
free reader skipped on a page with no text layer costs the whole point.
"""
from __future__ import annotations

import types

import pytest

from tools.omr import contextual, staff_labels_surya, staff_labels_tesseract
from tools.omr.assist import Assist
from tools.omr.instruments import lookup
from tools.omr.staff_labels import StaffLabel
from tools.omr.staff_labels_vision import GUTTER_PX, MAX_EDGE_PX, build_margin_crop


# ── crop geometry the OCR reader depends on ─────────────────────────────────

class _FakeStaff:
    def __init__(self, index, top, bottom, x_start=400, spacing=10.0):
        self.staff_index = index
        self.top_y, self.bottom_y = top, bottom
        self.x_start = x_start
        self.line_spacing_px = spacing
        self.system_index = 0


def _page(height=600, width=800):
    import numpy as np
    page = types.SimpleNamespace()
    page.binary = np.zeros((height, width), dtype=np.uint8)
    page.rgb = np.full((height, width, 3), 255, dtype=np.uint8)
    return types.SimpleNamespace(page=page, staves=[])


def test_crop_reports_a_tick_for_every_staff():
    pws = _page()
    staves = [_FakeStaff(0, 100, 140), _FakeStaff(1, 200, 240), _FakeStaff(2, 300, 340)]
    crop = build_margin_crop(pws, staves)

    assert crop is not None
    assert crop.staff_indices == [0, 1, 2]
    assert len(crop.tick_ys) == len(crop.staff_indices)
    assert crop.gutter_px == GUTTER_PX
    # Ticks must be ordered like the staves, or the OCR row assignment silently
    # attaches every label to the wrong instrument.
    assert list(crop.tick_ys) == sorted(crop.tick_ys)


def test_tick_positions_scale_with_a_downsized_crop():
    """A crop taller than MAX_EDGE_PX is resized on the way out. The ticks and
    the gutter must be reported in the FINAL image's pixels — this is the bug
    the benchmark hit when it assumed the gutter was always 70 wide."""
    tall = MAX_EDGE_PX * 2
    pws = _page(height=tall)
    staves = [_FakeStaff(0, 100, 140), _FakeStaff(1, tall - 300, tall - 260)]
    crop = build_margin_crop(pws, staves)

    assert crop is not None
    assert crop.gutter_px < GUTTER_PX          # shrunk with the canvas
    assert max(crop.tick_ys) <= MAX_EDGE_PX    # inside the resized image


# ── the fallthrough order ───────────────────────────────────────────────────

def _label(idx, text="Fl."):
    # A MATCHED label: the ladder's gates count labels the lexicon can turn into
    # a part, because an unresolved one reaches the join as nothing at all.
    hit = lookup(text)
    return StaffLabel(staff_index=idx, text=text,
                      instrument=hit.instrument if hit else None,
                      fifths_offset=0, y_center_px=float(idx * 100),
                      confidence=hit.confidence if hit else "none")


@pytest.fixture
def chain(monkeypatch):
    """Record which readers ran, with each one's output controllable."""
    calls: list[str] = []
    state = {"text": [], "surya": [], "tesseract": [], "vision": [],
             "surya_available": True, "tesseract_available": False}

    def fake_text(pws):
        calls.append("text")
        return state["text"]

    def fake_surya(pws, **kw):
        calls.append("surya")
        return state["surya"]

    def fake_vision(pws, **kw):
        calls.append("vision")
        return state["vision"]

    monkeypatch.setattr(contextual, "read_staff_labels", fake_text)
    monkeypatch.setattr(staff_labels_surya, "available",
                        lambda: state["surya_available"])
    monkeypatch.setattr(staff_labels_surya, "read_staff_labels_surya", fake_surya)

    def fake_tesseract(pws, **kw):
        calls.append("tesseract")
        return state["tesseract"]

    # Off unless a test asks for it, so the ladder's other rungs are tested
    # without a real Tesseract on the machine changing the answer.
    monkeypatch.setattr(staff_labels_tesseract, "available",
                        lambda: state["tesseract_available"])
    monkeypatch.setattr(staff_labels_tesseract, "read_staff_labels_tesseract",
                        fake_tesseract)
    import tools.omr.staff_labels_vision as slv
    monkeypatch.setattr(slv, "read_staff_labels_vision", fake_vision)
    return calls, state


def _run(budget=3, vision=True, surya=True):
    pws = types.SimpleNamespace(staves=[_FakeStaff(0, 0, 40)])
    return contextual._labels_for_page(
        pws, __import__("pathlib").Path("x.pdf"), 0,
        assist=Assist("vision" if vision else "none"),
        budget=[budget], surya_fallback=surya)


def test_text_layer_wins_and_nothing_else_runs(chain):
    calls, state = chain
    state["text"] = [_label(0)]
    assert _run() == state["text"]
    assert calls == ["text"]


def test_surya_runs_before_the_paid_reader(chain):
    calls, state = chain
    state["surya"] = [_label(0)]
    state["vision"] = [_label(0, "should not be used")]
    out = _run()
    assert out == state["surya"]
    assert calls == ["text", "surya"]
    assert "vision" not in calls, "the paid reader ran when the free one answered"


def test_paid_reader_runs_only_when_both_free_rungs_are_empty(chain):
    calls, state = chain
    state["vision"] = [_label(0)]
    assert _run() == state["vision"]
    assert calls == ["text", "surya", "vision"]


def test_missing_venv_skips_surya_without_erroring(chain):
    calls, state = chain
    state["surya_available"] = False
    state["vision"] = [_label(0)]
    assert _run() == state["vision"]
    assert calls == ["text", "vision"]


def test_surya_failure_falls_through_to_the_paid_reader(chain, monkeypatch):
    calls, state = chain

    def boom(pws, **kw):
        calls.append("surya")
        raise staff_labels_surya.SuryaLabelError("llama.cpp not installed")

    monkeypatch.setattr(staff_labels_surya, "read_staff_labels_surya", boom)
    state["vision"] = [_label(0)]
    assert _run() == state["vision"]
    assert calls == ["text", "surya", "vision"]


def test_surya_still_runs_when_the_paid_reader_is_off(chain):
    """The free rung must not be gated on the paid one — that is the whole
    point of having it."""
    calls, state = chain
    state["surya"] = [_label(0)]
    assert _run(vision=False) == state["surya"]
    assert calls == ["text", "surya"]


def test_surya_does_not_consume_the_paid_budget(chain):
    calls, state = chain
    state["surya"] = [_label(0)]
    budget = [3]
    pws = types.SimpleNamespace(staves=[_FakeStaff(0, 0, 40)])
    contextual._labels_for_page(pws, __import__("pathlib").Path("x.pdf"), 0,
                                assist=Assist("vision"), budget=budget)
    assert budget == [3], "a free read spent the paid budget"


# ── ranking the rungs on what a CONSUMER can use ────────────────────────────
#
# `OMR_LABEL_MERGE_QUALITY`, default OFF. The fault it repairs, measured on
# `beethoven-sym5-mvt1-575951-p1`: the text layer resolves twelve staves of
# which ELEVEN are consumable (staff 8 prints `Violino II.` and the text layer
# encodes it `Yiolino II.`, which resolves only through the OCR fold and is
# therefore `low`); Surya reads all twelve cleanly. Both score `_usable` 12,
# `_well_covered` returns before Surya is ever asked, and the page reaches the
# join with fewer labels than one of its own rungs would have given alone.

def _low_label(idx):
    """A label that resolves only through the OCR fold, so `confidence` is low.

    Built through `lookup` rather than hand-stamped, so the test fails if the
    lexicon stops folding this the way the measured page does.
    """
    hit = lookup("Yiolino II.")
    assert hit is not None and hit.confidence == "low", (
        "this fixture is only meaningful while the lexicon resolves the "
        "measured text layer's spelling at low confidence")
    return StaffLabel(staff_index=idx, text="Yiolino II.",
                      instrument=hit.instrument, fifths_offset=0,
                      y_center_px=float(idx * 100), confidence=hit.confidence)


def _ladder(chain_state, monkeypatch, flag):
    if flag is None:
        monkeypatch.delenv("OMR_LABEL_MERGE_QUALITY", raising=False)
    else:
        monkeypatch.setenv("OMR_LABEL_MERGE_QUALITY", flag)
    pws = types.SimpleNamespace(staves=[_FakeStaff(0, 0, 40)])
    return contextual._labels_for_page(
        pws, __import__("pathlib").Path("x.pdf"), 0,
        assist=Assist("none"), budget=[0])


def test_a_low_confidence_text_layer_blocks_surya_by_default(chain, monkeypatch):
    """The fault, pinned as it stands — so a default flip is a visible diff."""
    calls, state = chain
    state["text"] = [_low_label(0)]
    state["surya"] = [_label(0, "Violino II.")]
    out = _ladder(state, monkeypatch, None)
    assert [l.text for l in out] == ["Yiolino II."]
    assert "surya" not in calls, "the default ladder asked a rung it should skip"
    assert contextual._consumable(out) == 0
    assert contextual._usable(out) == 1


def test_the_flag_lets_the_stronger_free_rung_win_the_tie(chain, monkeypatch):
    calls, state = chain
    state["text"] = [_low_label(0)]
    state["surya"] = [_label(0, "Violino II.")]
    out = _ladder(state, monkeypatch, "1")
    assert "surya" in calls, "a free rung was still gated on the text layer"
    assert [l.text for l in out] == ["Violino II."]
    assert contextual._consumable(out) == 1


def test_the_flag_does_not_let_a_WORSE_free_rung_win(chain, monkeypatch):
    """Quality first, reach second — and neither is 'whoever ran last'."""
    calls, state = chain
    state["text"] = [_label(0, "Violino II."), _label(1, "Viola.")]
    state["surya"] = [_label(0, "Violino II.")]
    out = _ladder(state, monkeypatch, "1")
    assert "surya" in calls
    assert len(out) == 2, "a shorter read replaced a longer one of equal quality"


def test_an_unresolved_label_no_longer_blocks_tesseract(chain, monkeypatch):
    """The documented live fault: `'(C)'` present-but-unusable blocked a rung
    that could supply `'(C) Hr.'` for the same staff."""
    calls, state = chain
    state["tesseract_available"] = True
    state["text"] = [StaffLabel(staff_index=0, text="(C)", instrument=None,
                                fifths_offset=0, y_center_px=0.0,
                                confidence="none")]
    state["tesseract"] = [_label(0, "Corni in Es.")]

    off = _ladder(state, monkeypatch, None)
    assert [l.text for l in off] == ["(C)"], "the fault is no longer reproducible"

    on = _ladder(state, monkeypatch, "1")
    assert [l.text for l in on] == ["Corni in Es."], \
        "an unresolved label still blocked the rung that could resolve it"
    assert len(on) == 1, "the dead reading was shipped alongside the live one"


def test_tesseract_still_never_overwrites_a_RESOLVED_label(chain, monkeypatch):
    """Deliberately narrower than the Surya rung. Tesseract is the least
    accurate reader here (`Ki.Tr.` -> Trumpet), so a weak-but-real reading from
    a better rung stands."""
    calls, state = chain
    state["tesseract_available"] = True
    state["text"] = [_low_label(0)]
    state["tesseract"] = [_label(0, "Corni in Es.")]
    on = _ladder(state, monkeypatch, "1")
    assert [l.text for l in on] == ["Yiolino II."]


# ── the subprocess, when the venv exists ────────────────────────────────────

needs_venv = pytest.mark.skipif(
    not staff_labels_surya.available(),
    reason="no surya venv; run `python3 -m tools.omr.staff_labels_surya --bootstrap`",
)


@needs_venv
def test_reads_a_real_margin_crop():
    """End to end through the subprocess, on a crop drawn here rather than a
    fixture, so it exercises the geometry the bridge actually sends."""
    from PIL import Image, ImageDraw, ImageFont

    import numpy as np
    height, width = 900, 400
    x_start, spacing = 380, 10.0
    # The crop window is [x_start - MARGIN_SPACINGS*spacing, x_start + spacing],
    # so the words have to be drawn INSIDE it — put them just right of its left
    # edge. Drawing at the page edge instead puts them outside the crop and the
    # reader correctly returns nothing, which looks exactly like a broken pipe.
    text_x = int(x_start - 20 * spacing) + 20
    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf", 34)
    except OSError:                                       # pragma: no cover
        font = ImageFont.load_default()

    image = Image.fromarray(np.full((height, width, 3), 255, dtype=np.uint8))
    draw = ImageDraw.Draw(image)
    for y, word in ((150, "Flauti"), (450, "Oboi"), (750, "Fagotti")):
        draw.text((text_x, y - 20), word, fill=(0, 0, 0), font=font)
    page = types.SimpleNamespace()
    page.binary = np.zeros((height, width), dtype=np.uint8)
    page.rgb = np.asarray(image)
    pws = types.SimpleNamespace(page=page, staves=[])
    staves = [_FakeStaff(0, 130, 170, x_start=x_start),
              _FakeStaff(1, 430, 470, x_start=x_start),
              _FakeStaff(2, 730, 770, x_start=x_start)]

    crop = build_margin_crop(pws, staves)
    assert crop is not None
    read = staff_labels_surya.read_crops_surya([crop])

    assert len(read) == 1
    # Not asserting exact strings — this is a smoke test of the pipe, and the
    # accuracy claim is the bake-off's job, not a unit test's.
    assert read[0], "surya returned nothing for a clean synthetic margin"
    assert set(read[0]) <= {0, 1, 2}


# ── the seam transcribe uses ────────────────────────────────────────────────

def test_apply_contextual_rejects_a_mismatched_staved_list(monkeypatch):
    """`transcribe` hands its OWN detected pages in rather than paying for
    phase 1 twice. If that list ever disagreed with the result's pages, slot
    indices would be attached to the wrong staves — so it fails loudly.

    The guard is pure argument checking, so it must fire before any page is
    opened, and therefore on every machine. It once sat AFTER the margin-reader
    check, which made this test read the host instead of the code: with
    `.venv-surya` present `available()` short-circuited the `and` and the guard
    was reached, and without it `has_text_layer` opened the non-PDF path below
    and raised a PyMuPDF file error first. Both readers are pinned here — the
    venv is declared absent, which is the path that broke, and `has_text_layer`
    fails the test outright if the guard ever falls behind it again.
    """
    import pathlib

    from tools.omr.contextual import apply_contextual_analysis

    monkeypatch.setattr(staff_labels_surya, "available", lambda: False)
    monkeypatch.setattr(
        contextual, "has_text_layer",
        lambda *a, **k: pytest.fail("arguments validated after opening the PDF"))

    result = {"pages": [{"page_index": 0, "systems": []},
                        {"page_index": 1, "systems": []}]}
    with pytest.raises(ValueError, match="staved has 1 pages, result has 2"):
        apply_contextual_analysis(
            result, assist=Assist('none'),
            pdf_path=pathlib.Path(__file__),   # exists, so the early-out is skipped
            staved=[object()],
        )


def test_apply_contextual_reports_a_missing_pdf_rather_than_raising():
    from tools.omr.contextual import apply_contextual_analysis

    summary = apply_contextual_analysis(
        {"pages": [{"page_index": 0, "systems": []}]},
        assist=Assist("none"),
        pdf_path="/nonexistent/score.pdf",
    )
    assert summary["available"] is False
    assert "unavailable" in summary["reason"]


# ── persistent server lifecycle ─────────────────────────────────────────────

class TestResidentServer:
    """Sentinel handling. Pure filesystem and PID logic, so it needs no venv.

    The sentinel outlives a crash — llama.cpp dying does not clean up after
    itself — so a stale file must never be reported as a running server, or
    every later run attaches to a port with nothing behind it.
    """

    @staticmethod
    def _sentinel(monkeypatch, tmp_path, payload):
        path = tmp_path / "llamacpp_server.json"
        if payload is not None:
            path.write_text(__import__("json").dumps(payload))
        monkeypatch.setattr(staff_labels_surya, "SENTINEL", path)
        return path

    def test_no_sentinel_means_no_server(self, monkeypatch, tmp_path):
        self._sentinel(monkeypatch, tmp_path, None)
        assert staff_labels_surya.resident_server() is None

    def test_live_pid_is_reported(self, monkeypatch, tmp_path):
        import os
        self._sentinel(monkeypatch, tmp_path,
                       {"port": 1234, "pid": os.getpid()})
        info = staff_labels_surya.resident_server()
        assert info is not None and info["port"] == 1234

    def test_stale_pid_is_not_a_running_server(self, monkeypatch, tmp_path):
        # PID 2**22 is above any real pid on macOS/Linux defaults.
        self._sentinel(monkeypatch, tmp_path, {"port": 1234, "pid": 2 ** 22})
        assert staff_labels_surya.resident_server() is None

    def test_corrupt_sentinel_is_not_a_crash(self, monkeypatch, tmp_path):
        path = tmp_path / "llamacpp_server.json"
        path.write_text("{ not json")
        monkeypatch.setattr(staff_labels_surya, "SENTINEL", path)
        assert staff_labels_surya.resident_server() is None

    def test_stop_clears_a_stale_sentinel_and_reports_nothing_ran(
            self, monkeypatch, tmp_path):
        path = self._sentinel(monkeypatch, tmp_path,
                              {"port": 1234, "pid": 2 ** 22})
        assert staff_labels_surya.stop_server() is False
        assert not path.exists(), "a stale sentinel must not survive --stop"

    def test_stop_with_no_sentinel_is_not_an_error(self, monkeypatch, tmp_path):
        self._sentinel(monkeypatch, tmp_path, None)
        assert staff_labels_surya.stop_server() is False


def test_keep_alive_is_off_unless_asked(monkeypatch):
    """A 1.7 GB resident process must never appear because a default said so."""
    monkeypatch.delenv("OMR_SURYA_KEEP_ALIVE", raising=False)
    import importlib
    reloaded = importlib.reload(staff_labels_surya)
    try:
        assert reloaded.KEEP_ALIVE is False
    finally:
        importlib.reload(staff_labels_surya)


# ── Surya's LaTeX markup for a stacked part number ──────────────────────────

class TestPlainText:
    """Surya writes a STACKED pair of numerals as a LaTeX fraction, because a
    stack is what the page prints. Breitkopf's Brahms 1 puts the horn part
    numbers "1." over "2." beside "in C" and the reader returns
    `in C \\frac{1}{2}` — surfaced 2026-09-03 by scan_eval.py.

    The digits are part numbers and `instruments.normalize_label` already drops
    those; the CONTROL WORD is not a number and survives into the matched
    string, where it dilutes `coverage` and demotes a correct read.
    """

    def test_a_stacked_part_number_stops_demoting_the_instrument_beside_it(self):
        assert staff_labels_surya._plain_text("Hörner in C  \\frac{1}{2}") \
            == "Hörner in C 1 2"
        for markup, plain in (("Clar. \\frac{1}{2}", "Clar. 1 2"),
                              ("Fag. \\dfrac{1}{2}", "Fag. 1 2"),
                              ("Fl. \\tfrac{3}{4}", "Fl. 3 4")):
            assert staff_labels_surya._plain_text(markup) == plain
            before, after = lookup(markup), lookup(plain)
            assert before.instrument.name == after.instrument.name
            assert before.confidence == "medium" and after.confidence == "high"

    def test_ocr_damage_inside_the_braces_is_folded_too(self):
        """`\\frac{3｜4}` — one brace pair and a fullwidth bar for the rule. The
        markup is removed and the digits kept as plain tokens rather than the
        numerator/denominator split being relied on."""
        assert staff_labels_surya._plain_text("in Es  \\frac{3｜4}") == "in Es 3 4"
        # ...and it still names no instrument, which is the right answer: the
        # noun is printed once, braced across the pair of horn staves.
        assert lookup("in Es 3 4") is None

    def test_a_string_without_markup_is_returned_untouched(self):
        """The braces and bars are stripped only where the control word is,
        because `instruments._OCR_FOLD` reads a `|` as an `i` — a part number
        `II.` comes back as `||.` often enough that deleting bars everywhere
        would cost more than the markup does."""
        for text in ("Tr. Alt.", "Vl. II.", "Cor. || .", "2 Clarinetti in B",
                     "Vcelle. get.", "{Fl.}"):
            assert staff_labels_surya._plain_text(text) == text

    def test_the_fold_is_applied_to_what_the_reader_returns(self, monkeypatch):
        """Folding at the boundary, not at the call site, is what makes the raw
        `StaffLabel.text` a human reads back the label rather than the markup."""
        monkeypatch.setattr(staff_labels_surya, "interpreter", lambda: "/bin/false")

        def fake_run(*_args, **_kwargs):
            return types.SimpleNamespace(
                returncode=0, stderr="",
                stdout='{"systems": [{"labels": {"3": "H\\u00f6rner in C \\\\frac{1}{2}"}}]}')

        monkeypatch.setattr(staff_labels_surya.subprocess, "run", fake_run)
        crop = types.SimpleNamespace(png=b"", staff_indices=[3], tick_ys=(1.0,),
                                     gutter_px=0)
        assert staff_labels_surya.read_crops_surya([crop]) == [{3: "Hörner in C 1 2"}]


@needs_venv
def test_a_block_that_swallows_the_whole_crop_is_rejected_not_assigned():
    """Surya's own layout step occasionally fails to segment a tall, dense
    margin at all and returns the WHOLE crop as one block — surfaced
    2026-09-04 on real orchestral margins (17-19 staves), where a single
    detected block spanning every instrument name on the page got forced
    onto whichever staff its centroid happened to land nearest, reading as
    a confident wrong instrument (Piccolo, Trombone) rather than an honest
    abstention.

    A giant font is the reliable way to construct a block that is
    GEOMETRICALLY too tall for its system without depending on Surya's own
    (undocumented, occasionally nondeterministic) paragraph-grouping
    behavior — the gate rejects on the block's own height, not on why it
    got that tall, so this exercises the same mechanism the real pages hit.
    """
    from PIL import Image, ImageDraw, ImageFont

    import numpy as np
    height, width = 900, 500
    x_start, spacing = 380, 10.0
    text_x = int(x_start - 20 * spacing) + 20
    try:
        small_font = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf", 34)
        giant_font = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf", 420)
    except OSError:                                       # pragma: no cover
        small_font = giant_font = ImageFont.load_default()

    image = Image.fromarray(np.full((height, width, 3), 255, dtype=np.uint8))
    draw = ImageDraw.Draw(image)
    # A normal-sized label near staff 0 — the control: the pipe must still work.
    draw.text((text_x, 100 - 20), "Ob.", fill=(0, 0, 0), font=small_font)
    # One glyph tall enough to swallow most of a 4-staff system's tick span —
    # the shape the real pages hit, constructed deterministically instead of
    # depending on Surya's own paragraph-grouping to reproduce it. Drawn well
    # inside the crop's own y-bounds (the staves' span plus the 2-spacing pad
    # `margin_strip` adds) — measured at 283px tall against a 450px span here
    # (frac 0.63), comfortably past the 0.5 gate with the same margin the real
    # pages showed (frac ~1.0 there) and comfortably clear of Boléro's
    # correctly-split blocks (frac 0.03-0.04, `benchmarks/omr-margin-labels-
    # blob-2026-09/FINDINGS.md`). Drawing it larger or later in the crop risks
    # clipping it against the crop's bottom edge, which produced NO block at
    # all rather than a tall one the one time this was tried.
    draw.text((text_x, 150), "X", fill=(0, 0, 0), font=giant_font)

    page = types.SimpleNamespace()
    page.binary = np.zeros((height, width), dtype=np.uint8)
    page.rgb = np.asarray(image)
    pws = types.SimpleNamespace(page=page, staves=[])
    staves = [_FakeStaff(0, 100, 140, x_start=x_start),
              _FakeStaff(1, 250, 290, x_start=x_start),
              _FakeStaff(2, 400, 440, x_start=x_start),
              _FakeStaff(3, 550, 590, x_start=x_start)]

    crop = build_margin_crop(pws, staves)
    assert crop is not None
    read = staff_labels_surya.read_crops_surya([crop])

    assert len(read) == 1
    labels = read[0]
    # The control survives: a normal label still reaches its staff.
    assert labels.get(0) == "Ob.", labels
    # No staff inherits the giant glyph's text. Checking the TEXT rather than
    # its length matters here — the glyph is one character ("X"), so a block
    # that swallows most of the crop is not a block with a long STRING, and a
    # length check would pass whether or not the gate fired. The real failure
    # mode concatenates many instrument names into one long string precisely
    # because the runaway block spans many staves' worth of TEXT as well as
    # height; this synthetic case isolates the height signal alone, which is
    # what the gate actually reads.
    assert "X" not in labels.values(), labels
    assert labels == {0: "Ob."}, labels
