"""The barline evidence and the measure-cell pad reach the result JSON.

⚠️ **WHAT THIS FILE IS FOR, stated so it is not mistaken for a decision
test.** Two builds on 2026-09-06 recorded facts that could not cross the
process boundary: `types.Barline` gained eight evidence fields and barlines
are serialised nowhere at all, and `types.MeasureCell` gained the pad it was
actually cut with while `transcribe`'s measure dict is built from an explicit
key list that never names it. Nothing about either changes a verdict. What
this file pins is REACH — that the numbers are on disk, with their `None`s
intact and their per-item variation preserved.

⚠️ **ANTI-VACUITY IS THE DESIGN CONSTRAINT HERE, not a nicety.** A test that
asserts a key EXISTS passes on an empty dict; a test that asserts a pad equals
4.0 passes against a field wired to the module constant, which is the exact
bug the pad field was added to prevent. So every test below asserts on VALUES
that DIFFER between rows of one page, and the fixture is checked to produce
that variation before anything is concluded from it. Each test names the
mutation it was run red against.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.omr.transcribe import _barline_records
from tools.omr.types import Barline


# ---------------------------------------------------------------------------
# 1. The record itself: a pure function, so the traps are testable cheaply.
# ---------------------------------------------------------------------------

def _bl(**kw) -> Barline:
    base = dict(page_index=0, x=100, y_top=10, y_bottom=200, system_index=0)
    base.update(kw)
    return Barline(**base)


def test_a_never_measured_number_stays_null_and_is_not_coerced_to_zero():
    """⚠️ THE CENTRAL TRAP OF THE WHOLE RECORD.

    `connectivity=None` means the number was never computed (the 1-staff
    small-system path), `connectivity=0.0` means it was computed and came back
    empty — and on the engraved page 0.0 sits under SEVEN unanimous real
    barlines. A serialiser that wrote `float(x or 0)` would erase the
    distinction and every consumer would read "measured and terrible".

    Red against: `round(float(bl.connectivity or 0.0), 6)` in
    `_barline_records`.
    """
    rows = _barline_records([
        _bl(x=1, connectivity=None, span_ink=None),
        _bl(x=2, connectivity=0.0, span_ink=0.0),
    ])
    assert rows[0]["connectivity"] is None
    assert rows[1]["connectivity"] == 0.0
    assert rows[0]["connectivity"] is not rows[1]["connectivity"]
    assert rows[0]["span_ink"] is None
    assert rows[1]["span_ink"] == 0.0


def test_the_regime_verdict_is_carried_on_every_row():
    """`barlines_cross_gaps` is the discriminator the `Barline` docstring says
    must be read BEFORE `connectivity`, because connectivity's sign inverts
    between an open score and a conductor's page. Hoisting it to the system
    dict would make it skippable from a row.

    Red against: deleting `"barlines_cross_gaps"` from the emitted dict.
    """
    rows = _barline_records([
        _bl(x=1, connectivity=0.0, barlines_cross_gaps=False),
        _bl(x=2, connectivity=0.0, barlines_cross_gaps=True),
    ])
    assert [r["barlines_cross_gaps"] for r in rows] == [False, True]
    # Same connectivity, opposite meaning — which is only legible because the
    # regime rides along.
    assert rows[0]["connectivity"] == rows[1]["connectivity"] == 0.0


def test_the_row_carries_its_own_locator():
    """A reviewer caught the docstring promising `system_index` "so a row is
    self-locating" while the emitted dict had neither `system_index` nor
    `page_index` in it. Both are redundant with the parent dicts and are
    emitted anyway — the phrase is precisely what invites lifting a row out of
    its parent, and that is when redundancy stops being redundant.

    Red against: deleting `"system_index"` from the emitted dict.
    """
    rows = _barline_records([_bl(page_index=4, system_index=2, x=7)])
    assert rows[0]["page_index"] == 4
    assert rows[0]["system_index"] == 2


def test_the_row_carries_its_own_denominator():
    """`n_votes` is meaningless without `n_staves_in_system`, and the sibling
    system dict's `n_staves` is a DIFFERENT number (it counts staves that
    produced cells; the vote counts staves with >= 5 lines). A row that
    dropped its own denominator would be silently read against the wrong one
    on any page with percussion.

    Red against: deleting `"n_staves_in_system"` from the emitted dict.
    """
    rows = _barline_records([_bl(n_votes=9, n_staves_in_system=12, min_votes=4)])
    assert rows[0]["n_votes"] == 9
    assert rows[0]["n_staves_in_system"] == 12
    assert rows[0]["min_votes"] == 4


def test_rows_come_out_in_x_order_and_keep_their_own_prongs():
    """Five acceptance prongs exist and a rescued barline is a weaker claim
    than a voted one. If the serialiser collapsed them (or emitted one prong
    for the system) nothing downstream could tell them apart.

    Red against: emitting `barlines[0].accept_prong` for every row.
    """
    rows = _barline_records([
        _bl(x=300, accept_prong="connectivity_rescue"),
        _bl(x=100, accept_prong="vote_and_connectivity"),
        _bl(x=200, accept_prong="vote_open_score"),
    ])
    assert [r["x"] for r in rows] == [100, 200, 300]
    assert [r["accept_prong"] for r in rows] == [
        "vote_and_connectivity", "vote_open_score", "connectivity_rescue"]


def test_an_unannotated_barline_serialises_as_nulls_not_as_absent_keys():
    """The four fixture/test construction sites build a `Barline` with
    coordinates only. Those rows must still carry every key, as null — an
    absent key and a null one read differently to `dict.get`, and a consumer
    sweeping a mixed page would silently skip the unannotated ones.
    """
    row = _barline_records([_bl()])[0]
    for k in ("n_votes", "n_staves_in_system", "min_votes", "connectivity",
              "span_ink", "accept_prong", "barlines_cross_gaps",
              "choir_cue_c_override"):
        assert k in row, k
        assert row[k] is None, k


def test_it_is_json_serialisable_with_no_default_hook():
    """The record goes to disk. A numpy float or an int64 leaking out of
    `measure_extractor` would be written by `json.dumps(..., default=str)` as
    a STRING and nothing would say so — the arm runner passes `default=str`,
    so this is the only place that can catch it.
    """
    rows = _barline_records([_bl(n_votes=3, connectivity=0.75, span_ink=1.0,
                                 accept_prong="vote_and_connectivity",
                                 barlines_cross_gaps=True,
                                 choir_cue_c_override=False)])
    back = json.loads(json.dumps(rows))     # no default= on purpose
    assert back == rows
    assert isinstance(back[0]["connectivity"], float)
    assert isinstance(back[0]["n_votes"], int)


# ---------------------------------------------------------------------------
# 2. The wiring. A pure function nothing calls records nothing — which is the
#    failure this whole branch exists to repair, arriving one level up.
# ---------------------------------------------------------------------------

SRC = Path(__file__).resolve().parents[1] / "transcribe.py"


def test_the_system_dict_is_built_with_the_barline_record():
    """Source-level anti-drift. `_barline_records` is a complete recorder that
    records nothing unless the system dict calls it, and no unit test of the
    function can see that. Verified to go red when the `"barlines":` line is
    removed from the `sys_dict` literal.
    """
    src = SRC.read_text()
    assert '"barlines": _barline_records(' in src, (
        "the system dict no longer builds a barline record — a pure "
        "serialiser nothing calls is exactly the fault this branch repairs"
    )


def test_the_measure_dict_reads_the_pad_off_the_cell_not_off_the_module():
    """⚠️ The pad's failure mode is not absence, it is a plausible wrong
    value. `PAD_ABOVE_STAFF_LINES` is 4.0 and a cell grown to the ceiling was
    cut at 6.0; wiring the key to the module constant would produce a field
    that is right on most cells and silently wrong on exactly the cells the
    growth exists for. Assert the SOURCE of the value, not just the key.

    Red against: `"pad_above_staff_lines": PAD_ABOVE_STAFF_LINES`.
    """
    src = SRC.read_text()
    assert '"pad_above_staff_lines": cell.pad_above_staff_lines,' in src
    assert '"pad_below_staff_lines": cell.pad_below_staff_lines,' in src


# ---------------------------------------------------------------------------
# 3. End to end: the values on disk, on a page whose staves DISAGREE.
#
# ⚠️ The two tests above are source-level, and a source-level assertion is a
# weak instrument — it proves the line is written, not that the line produces
# a right number. This section runs the real `transcribe` on a synthesized
# page and asserts VALUES that vary between rows, which is the only shape of
# assertion that cannot pass against a constant.
#
# The detector is stubbed to return no detections. That is legitimate here and
# is worth saying why: nothing under test is a recognition result. The pad
# comes from `measure_extractor`'s crop and the barline evidence from
# `detect_barlines`, both of which run BEFORE any inference — so the stub
# removes an 88 MB model load and several seconds of CPU from a test whose
# subject is untouched by it. It also means this test runs on a machine with
# no weights at all.
# ---------------------------------------------------------------------------

pytest.importorskip("skimage", reason="pipeline needs scikit-image")
pytest.importorskip("pymupdf", reason="fixture needs PyMuPDF to draw a page")

from tools.omr import measure_extractor as me            # noqa: E402
from tools.omr.transcribe import transcribe              # noqa: E402

# Same crowding as test_measure_cell_pad.py's fixture, and for the same
# reason: ~5 staff spaces apart means an interior staff grows on NEITHER side
# while the top staff grows above and only above. A page of well-spaced staves
# would put 6.0 on every side and the module-constant bug would be invisible.
_STAFF_TOPS = (200, 254, 308, 362)


def _draw_page(path: Path) -> None:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    for y0 in _STAFF_TOPS:
        for i in range(5):
            y = y0 + i * 6
            page.draw_line(pymupdf.Point(60, y), pymupdf.Point(550, y), width=0.6)
        for bx in (60, 220, 380, 550):
            page.draw_line(pymupdf.Point(bx, y0), pymupdf.Point(bx, y0 + 24), width=0.9)
        for nx in (120, 180, 280, 340, 440):
            page.draw_circle(pymupdf.Point(nx, y0 + 12), 2.6, fill=(0, 0, 0))
    doc.save(str(path))
    doc.close()


@pytest.fixture(scope="module")
def transcribed(tmp_path_factory, module_mocker=None):
    """`transcribe` on the synthesized page, detector stubbed to silence."""
    import tools.omr.yolo_detector as yd

    pdf = tmp_path_factory.mktemp("serialise-e2e") / "page.pdf"
    _draw_page(pdf)

    class _Silent:
        def __init__(self, *a, **kw):
            pass

        def detect(self, *a, **kw):
            return []

    real = yd.YoloDetector
    yd.YoloDetector = _Silent
    try:
        return transcribe(
            pdf_path=pdf, pages=[0], weights="stub.pt", dpi=300,
            contextual=False, read_direction_text=False, progress=False,
        )
    finally:
        yd.YoloDetector = real


def _measures(result):
    return [m
            for page in result["pages"]
            for sys_ in page["systems"]
            for staff in sys_["staves"]
            for m in staff["measures"]]


def test_the_fixture_actually_produces_disagreeing_pads(transcribed):
    """⚠️ ANTI-VACUITY GATE. Everything below is a claim about variation, so
    fail HERE if the fixture stopped producing any — a page whose staves all
    grew to the ceiling would let a module-constant field pass every test
    after this one.
    """
    ms = _measures(transcribed)
    assert ms, "the fixture produced no measures — nothing below means anything"
    above = {m["pad_above_staff_lines"] for m in ms}
    assert len(above) > 1, (
        f"every cell recorded the same pad above ({above}) — the staves have "
        "drifted apart and this file can no longer detect a pad wired to the "
        "module constant"
    )
    assert {float(me.PAD_ABOVE_STAFF_LINES), float(me.PAD_MAX_STAFF_LINES)} == above


def test_the_serialised_pad_is_the_cells_own_per_side_value(transcribed):
    """The top staff has open paper above and a crowded neighbour below, so
    its cells must record DIFFERENT numbers on the two sides of one cell —
    which no module constant can produce.

    Red against: `"pad_above_staff_lines": float(PAD_ABOVE_STAFF_LINES)`.
    """
    page = transcribed["pages"][0]
    staves = [st for sys_ in page["systems"] for st in sys_["staves"]]
    top = min(staves, key=lambda s: s["staff_index"])
    assert top["measures"], "top staff has no measures"
    for m in top["measures"]:
        assert m["pad_above_staff_lines"] == float(me.PAD_MAX_STAFF_LINES)
        assert m["pad_below_staff_lines"] == float(me.PAD_BELOW_STAFF_LINES)
        assert m["pad_above_staff_lines"] != m["pad_below_staff_lines"]

    interior = sorted(staves, key=lambda s: s["staff_index"])[1:-1]
    assert interior, "fixture should have an interior staff"
    for st in interior:
        for m in st["measures"]:
            assert m["pad_above_staff_lines"] == float(me.PAD_ABOVE_STAFF_LINES)
            assert m["pad_below_staff_lines"] == float(me.PAD_BELOW_STAFF_LINES)


def test_barlines_reach_disk_with_the_evidence_that_admitted_them(transcribed):
    """Before this change `grep '"barline' tools/omr/transcribe.py` returned
    nothing and a barline reached disk only as the measure boundary it made.

    Asserts on VALUES, not on the key: a `barlines: []` on every system would
    satisfy an existence check and record exactly as much as before.

    Red against: removing the `"barlines":` line from the `sys_dict` literal.
    """
    page = transcribed["pages"][0]
    rows = [r for sys_ in page["systems"] for r in sys_["barlines"]]
    assert rows, "no barline reached the JSON on a page drawn with barlines"
    for r in rows:
        assert r["n_votes"] is not None and r["n_votes"] >= 1
        assert r["n_staves_in_system"] is not None
        assert r["n_votes"] <= r["n_staves_in_system"]
        assert r["accept_prong"] in {
            "vote_small_system", "span_rescue_small_system", "vote_open_score",
            "vote_and_connectivity", "connectivity_rescue"}
        assert r["barlines_cross_gaps"] in (True, False)
    assert [r["x"] for r in rows] == sorted(r["x"] for r in rows)


def test_the_rows_locator_agrees_with_the_dicts_it_hangs_in(transcribed):
    """A locator that disagrees with its parent is worse than none — it would
    be believed. Asserts the redundancy is CONSISTENT rather than merely
    present, on the real page.

    Red against: `"system_index": 0` (a constant) in `_barline_records`, which
    a single-system fixture alone could not catch — so the page_index half is
    checked against the page dict too.
    """
    for page in transcribed["pages"]:
        for sys_ in page["systems"]:
            for r in sys_["barlines"]:
                assert r["system_index"] == sys_["system_index"]
                assert r["page_index"] == page["page_index"]


def test_the_serialised_barlines_are_the_ones_phase_one_accepted(transcribed):
    """Cross-check against `detect_barlines` re-run on the same page, so the
    record is pinned to the pipeline's own answer rather than to itself. A
    serialiser that emitted a filtered or invented set would pass every
    self-consistency test above.
    """
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves

    pdf = Path(transcribed["source_pdf"])
    pws = me.detect_barlines(detect_staves(render_page(pdf, 0, dpi=300)))
    want = sorted((bl.system_index, bl.x, bl.n_votes) for bl in pws.barlines)
    got = sorted((sys_["system_index"], r["x"], r["n_votes"])
                 for sys_ in transcribed["pages"][0]["systems"]
                 for r in sys_["barlines"])
    assert got == want
