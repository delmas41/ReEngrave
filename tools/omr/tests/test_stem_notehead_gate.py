"""`OMR_STEM_NOTEHEAD_GATE`: a stroke that meets a notehead is a stem.

Synthetic cells, so these run without LilyPond, a PDF or weights.

The shape under test is the one `benchmarks/omr-stem-pair-rule-2026-09`
measured and never acted on: `_drop_paired_strokes` deletes BOTH members of
any pair of verticals within 0.9 staff spaces, on the premise that
*"successive notes are set further apart than an accidental's own strokes"*.
On a dense low-res orchestral plate that is false — of the 244 strokes it
deletes on Litolff Beethoven 5 pp.1-4, 80 carry a detected notehead and **62
of those 80 (77.5%) were paired with ANOTHER stroke that also carries one**.

⚠️ THE FIRST TEST IS THE ONE THAT MATTERS AND IT IS THE FLAG-OFF IDENTITY,
for exactly the reason `test_line_detection_stroke_reader.py` gives about its
own flag: this file is on the path every stem arm in this repo proves faithful
before reporting a delta (1,920 strokes on Litolff, 2,305 on Breitkopf). If
the default set ever moves, those instruments break and the failure reads as
theirs. Its positive control sits beside it — the gated set must DIFFER on
the same cell, or the identity test passes because the gate does nothing.

⚠️ THE GATE TAKES TWO THINGS: the FLAG and the DATA. Both halves are tested
separately, because either alone silently leaving the rule in place is the
whole safety argument for the legacy path — `detect_lines(cell)` passes no
detections, so `transcribe` is unchanged BY CONSTRUCTION.
"""

from __future__ import annotations

import numpy as np

from tools.omr.line_detection import (
    STEM_NOTEHEAD_GATE_ENV,
    _drop_paired_strokes,
    detect_stems,
    stem_notehead_gate_enabled,
)
from tools.omr.types import MeasureCell


SPACING = 100
LINE_YS = [100, 200, 300, 400, 500]


def _cell(paint, width: int = 900) -> MeasureCell:
    img = np.full((900, width), 255, dtype=np.uint8)
    paint(img)
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, width, 900),
        staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
    )


def _stroke(img, x: int, y0: int, y1: int, w: int = 8) -> None:
    img[y0:y1, x:x + w] = 0


def _two_close_strokes(img) -> None:
    """Two verticals 0.55 staff spaces apart — inside the 0.9 pair window.

    ⚠️ THE GEOMETRY IS THE POINT. This is what an accidental's two strokes
    look like AND what two successive stems look like on a crowded plate;
    `detect_stems` cannot tell them apart by any dimension it can see (best
    single feature 0.823 against a 0.723 majority baseline, no empty interval
    anywhere), which is why the repair is the notehead and not a threshold.
    """
    _stroke(img, 300, 180, 500)
    _stroke(img, 355, 180, 500)


#: A notehead box under the LEFT stroke and under the LEFT stroke ONLY.
#: ⚠️ THE FIRST VERSION WAS 120 px WIDE AND COVERED BOTH STROKES, so the
#: "the partner is still deleted" test failed against a correct gate: the
#: partner met the head too. A fixture that does not isolate the case tests
#: the fixture. The two strokes stand at x 300 and 355; this spans 250-340.
HEAD_LEFT = (250.0, 460.0, 90.0, 100.0)
HEAD_RIGHT = (320.0, 460.0, 90.0, 100.0)


def _boxes(strokes):
    return sorted((s.x_canonical, s.y_canonical,
                   s.width_canonical, s.height_canonical) for s in strokes)


class _Box:
    """A `LineDetection`-shaped stub for `_drop_paired_strokes`."""

    def __init__(self, x, y, w, h):
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h


class TestThePremise:
    """Before anything is claimed, the fixture must reach the rule."""

    def test_the_pair_rule_deletes_both_strokes_of_the_fixture(self):
        cell = _cell(_two_close_strokes)
        assert detect_stems(cell, drop_accidental_pairs=False), \
            "the fixture paints no stroke the range filters accept"
        assert detect_stems(cell) == [], (
            "the pair rule does not fire on this fixture, so nothing below "
            "tests the gate")


class TestFlagOffIsIdentical:
    """The default path must not move. This is the load-bearing test."""

    def test_the_default_is_off(self, monkeypatch):
        monkeypatch.delenv(STEM_NOTEHEAD_GATE_ENV, raising=False)
        assert stem_notehead_gate_enabled() is False

    def test_flag_off_with_noteheads_supplied_is_byte_identical(self):
        cell = _cell(_two_close_strokes)
        heads = [HEAD_LEFT]
        plain = _boxes(detect_stems(cell))
        with_heads_flag_off = _boxes(
            detect_stems(cell, noteheads=heads, enable_notehead_gate=False))
        assert plain == with_heads_flag_off

    def test_the_flag_alone_with_no_noteheads_changes_nothing(self):
        """The legacy path's safety, stated as a test.

        `detect_lines(cell)` passes no detections, so `transcribe` can never
        reach the gate however the flag is set.
        """
        cell = _cell(_two_close_strokes)
        assert _boxes(detect_stems(cell)) == _boxes(
            detect_stems(cell, enable_notehead_gate=True))

    def test_positive_control_the_gate_does_change_this_cell(self):
        """Without this, the three tests above pass because the gate is dead."""
        cell = _cell(_two_close_strokes)
        heads = [HEAD_LEFT]
        assert _boxes(detect_stems(cell)) != _boxes(
            detect_stems(cell, noteheads=heads, enable_notehead_gate=True))


class TestTheGate:
    def test_a_stroke_on_a_notehead_is_kept(self):
        cell = _cell(_two_close_strokes)
        heads = [HEAD_LEFT]        # under the LEFT stroke
        kept = detect_stems(cell, noteheads=heads, enable_notehead_gate=True)
        xs = sorted(s.x_canonical for s in kept)
        assert 300 in xs, "the stroke standing on the notehead was deleted"

    def test_its_partner_is_still_deleted_when_it_meets_no_notehead(self):
        """One-sided, and this is the half that keeps the rule working.

        A stem beside an accidental must still lose the accidental's stroke.
        """
        cell = _cell(_two_close_strokes)
        heads = [HEAD_LEFT]
        kept = detect_stems(cell, noteheads=heads, enable_notehead_gate=True)
        xs = sorted(s.x_canonical for s in kept)
        assert 355 not in xs, (
            "the partner carries no notehead and must still be dropped")

    def test_two_strokes_each_on_a_notehead_are_BOTH_kept(self):
        """The 62 of 80. Two genuine stems must stop eating each other."""
        cell = _cell(_two_close_strokes)
        heads = [HEAD_LEFT, HEAD_RIGHT]
        kept = detect_stems(cell, noteheads=heads, enable_notehead_gate=True)
        assert len(kept) == 2, (
            "both strokes meet a notehead and neither may condemn the other")

    def test_a_pair_meeting_no_notehead_is_still_dropped(self):
        """The accidental case, unchanged. An empty head list is not a licence."""
        cell = _cell(_two_close_strokes)
        assert detect_stems(cell, noteheads=[],
                            enable_notehead_gate=True) == []

    def test_none_and_empty_are_not_the_same_argument(self):
        """`None` is *no gate*; `[]` is *the gate, and nothing to protect*.

        They agree on THIS cell by arithmetic, so the test asserts the
        distinction where it bites: with a head present, `None` must behave
        like the shipped rule and `[...]` must not.
        """
        cell = _cell(_two_close_strokes)
        heads = [HEAD_LEFT]
        assert detect_stems(cell, noteheads=None,
                            enable_notehead_gate=True) == []
        assert detect_stems(cell, noteheads=heads,
                            enable_notehead_gate=True) != []


class TestTheRelationDirectly:
    """`_drop_paired_strokes` on its own, with no image in the way."""

    def test_heads_none_reproduces_the_shipped_relation(self):
        a, b = _Box(300, 180, 8, 320), _Box(355, 180, 8, 320)
        assert _drop_paired_strokes([a, b], SPACING, 0.9, 0.6) == []
        assert _drop_paired_strokes([a, b], SPACING, 0.9, 0.6,
                                    heads=None) == []

    def test_the_gate_is_one_sided(self):
        """It can only ever UN-condemn: nothing it keeps off is kept on."""
        a, b = _Box(300, 180, 8, 320), _Box(355, 180, 8, 320)
        off = _drop_paired_strokes([a, b], SPACING, 0.9, 0.6)
        on = _drop_paired_strokes([a, b], SPACING, 0.9, 0.6,
                                  heads=[HEAD_LEFT])
        assert set(map(id, off)) <= set(map(id, on))

    def test_a_far_apart_pair_was_never_paired_either_way(self):
        """A control: the gate must not be credited with the window's work."""
        a, b = _Box(300, 180, 8, 320), _Box(700, 180, 8, 320)
        assert len(_drop_paired_strokes([a, b], SPACING, 0.9, 0.6)) == 2
        assert len(_drop_paired_strokes([a, b], SPACING, 0.9, 0.6,
                                        heads=[])) == 2


class TestTheGatherWiring:
    """The gate needs the detections, and `gather()` already held them."""

    def test_gather_cv_lines_accepts_a_detection_map(self):
        import inspect
        from tools.omr.staged import gather as g
        sig = inspect.signature(g.gather_cv_lines)
        assert "detections" in sig.parameters, (
            "`gather_cv_lines` must take the detection map; without it the "
            "gate has no data and is inert on the staged path")

    def test_gather_passes_the_detections_to_gather_cv_lines(self):
        """Source-level, because nothing else would catch the forward being
        dropped: a gate with no data is silently the shipped rule."""
        import inspect
        from tools.omr.staged import gather as g
        src = inspect.getsource(g.gather)
        assert "gather_cv_lines(log, cells, local, detections)" in src

    def test_no_detector_means_no_gate_rather_than_an_empty_one(self):
        """`gather_detections(detector=None)` is a supported mode."""
        from tools.omr.staged.gather import _notehead_boxes_for_cell, R
        sub = R.cell(0, 0, 0, 0)
        assert _notehead_boxes_for_cell(None, sub) is None
        assert _notehead_boxes_for_cell({}, sub) == []


class TestTheLegacyPathCannotReachIt:
    """`transcribe` is unchanged BY CONSTRUCTION, asserted rather than said.

    ⚠️ This is the sibling lane's objection 2 — *"the legacy path would
    diverge"* — and the answer is that it CANNOT: `transcribe` reaches the CV
    rung through `detect_lines(cell)` with no detections, so the gate has no
    data however the flag is set. That is a property of a call site, and a
    call site is exactly the thing a later change moves without noticing, so
    it is pinned at source level.
    """

    def test_transcribe_passes_no_noteheads(self):
        """Parsed, not grepped.

        ⚠️ The first version of this test grepped for the string
        `noteheads=` and FAILED on `print(f"  noteheads={...}")` — a label in
        an f-string, not a keyword argument. A substring test cannot tell a
        call from a caption, so this walks the AST and looks at KEYWORDS of
        calls to the two entry points.
        """
        import ast
        import inspect
        from tools.omr import transcribe as t
        tree = ast.parse(inspect.getsource(t))
        calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name in ("detect_lines", "detect_stems"):
                calls.append((name, sorted(k.arg for k in node.keywords)))
        assert calls, (
            "the legacy call site moved; re-check that it still passes no "
            "detections before trusting the byte-identity claim")
        assert all(kw == [] for _n, kw in calls), calls

    def test_only_the_staged_gather_opts_in(self):
        """One producer of the gate's data in the whole of `tools/`."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[3]
        hits = []
        for f in (root / "tools").rglob("*.py"):
            if "/tests/" in str(f):
                continue
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if "noteheads=noteheads" in line or "noteheads=heads" in line:
                    hits.append(f"{f.relative_to(root)}:{i}")
        assert sorted(hits) == [
            "tools/omr/line_detection.py:1199",   # the forward, detect_lines
            "tools/omr/staged/gather.py:1433",    # the one opt-in
        ], hits
