"""ROADMAP 2.285 round 2 -- the own-ink accidental REACHES the written note (B), and the reader consults what was already read (A).

Every control can fail (each has a `CONTROL_` twin that turns it red): a sharp the page reader read travels the SAME row a boxed one does, so
`adjudicate_accidental_owner` names its head by position, EVALUATE carries it to the bar's later notes, and EXPORT writes `<accidental>` + `<alter>` --
plain only on the family reader's READ bar (a natural at its stagger margin), blue (GUESSED, with its candidates) on a flat or a sharp, and nothing on a
mark the family reader could not name.
"""
from types import SimpleNamespace

import numpy as np

from tools.omr.staged import accidental_family as AF
from tools.omr.staged import adjudicate, evaluate, export as E
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import consequences  # noqa: F401
from tools.omr.staged import gather as G
from tools.omr.staged import page_accidental_ink as PAI
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

SPACE = 20.0
HALF = SPACE / 2.0
CELL = R.cell(0, 0, 0, 0)
STAFF = R.staff(0, 0, 0)


class _Cell:
    """A cell whose canonical frame is the page's, shifted by (1000, 500) page px at 1:1 (so a page -> canonical shift can fail)."""
    staff_index = 0
    page_index = 0
    measure_index = 0
    bbox_page_px = (1000.0, 500.0, 1600.0, 700.0)
    upscale_factor = 1.0
    staff_line_ys_canonical = [0.0, SPACE, 2 * SPACE, 3 * SPACE, 4 * SPACE]
    staff_line_spacing_canonical = SPACE
    image_no_staff = None


def _cluster(kind, margin, page_box=(1100.0, 520.0, 1115.0, 578.0)):
    return {"members": [0, 1, 2, 3], "box": list(page_box), "type": kind, "why": "t", "margin": margin, "standing": "GUESSED", "head": [1140.0, 540.0, 1166.0, 560.0],
            "head_conf": 0.8, "head_key": CELL.to_key(), "candidates": [kind], "features": {}, "w_sp": 0.75, "h_sp": 2.9}


def _gather_head(log, gi, x, position):
    g = R.glyph(0, 0, 0, 0, gi)
    y = position * HALF - SPACE / 2.0
    log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", x, y, 26.0, SPACE), reader=READERS.DETECTOR, frame="cell:0", score=0.9, category="notehead")
    log.observe(g, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine", reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, float(position), reader=READERS.GEOMETRY, frame="cell:0", residual=0.0, rounded=int(round(position)))
    log.record(R.Verdict(id=log._next_id("vrd"), subject=g, quantity=Q.DURATION, outcome=R.Outcome.DECIDED,
                         value={"beats": 1.0, "written": 1.0, "dots": 0}, decider="t", reason="fixture"))
    return g


def _written(kind, margin, *, filed=True):
    """GATHER (the page reader's row + a head at the sharp's height 1.5 spaces right) -> ADJUDICATE -> EVALUATE -> EXPORT. Returns (xml, report)."""
    log = Log()
    log.observe(CELL, Q.CELL_STAFF_SPACE, SPACE, reader=READERS.GEOMETRY, frame="cell:0", half_step=HALF, lines=5)
    c = _cluster(kind, margin)
    # the cluster's centre height 549 page px = canonical 49 -> position ~4.9; the head is put on position 5 (the 4th line + a half), x 1.5 spaces to the right
    if filed:
        keys = PAI.file_own_accidentals(log, [c], [_Cell()], {0: (0, 0)})
        assert keys == [R.glyph(0, 0, 0, 0, PAI.GLYPH_BASE).to_key()]
    _gather_head(log, 1, 140.0, 5.0)
    log.freeze()
    adjudicate.run(log, order=(Q.ACCIDENTAL_OWNER,))
    for q, v, who in ((Q.CLEF, "treble", STAFF), (Q.KEY_SIGNATURE, 0, STAFF), (Q.MEASURE_PARTITION, 1, STAFF), (Q.SYSTEM_STAFF_COUNT, 1, R.system(0, 0))):
        log.record(R.Verdict(id=log._next_id("vrd"), subject=who, quantity=q, outcome=R.Outcome.DECIDED, value=v, decider="t", reason="fixture"))
    log.record(R.Verdict(id=log._next_id("vrd"), subject=R.DOCUMENT, quantity=Q.PART_PARTITION, outcome=R.Outcome.DECIDED,
                         value={"join": "ordinal", "staves_per_system": 1}, decider="t", reason="ordinal"))
    evaluate.run(log)
    return log, E.to_musicxml({"record": log.to_json(), "summary": log.summary()})


def test_the_row_is_the_boxed_accidentals_row():
    log = Log()
    keys = PAI.file_own_accidentals(log, [_cluster("sharp", 0.9)], [_Cell()], {0: (0, 0)})
    rows = log.rows(Q.ACCIDENTAL_STAFF_POSITION, CELL, scope=R.Scope.SELF_AND_DESCENDANTS)
    assert len(rows) == 1 and rows[0].subject.to_key() == keys[0]
    d = rows[0].detail
    assert d["alteration"] == "#" and d["family"]["type"] == "sharp" and d["family"]["detector_class"] == PAI.NO_DETECTOR
    # canonical frame = page minus the cell's origin (1000, 500): x 100..115, y 20..78; a sharp anchors at half its height: (49 - 0) / 10
    assert (d["x0"], d["x1"], d["y0"], d["y1"]) == (100.0, 115.0, 20.0, 78.0)
    assert abs(rows[0].value - (20.0 + 58.0 * AF.anchor_fraction("sharp")) / HALF) < 1e-6


def test_a_sharp_reaches_the_written_note_and_is_blue():
    log, (xml, report) = _written("sharp", 0.9)
    assert "<accidental>sharp</accidental>" in xml and "<alter>1</alter>" in xml
    assert 'color="%s"' % E.GUESS_COLOR in xml                       # nothing is READ on a sharp (accidental_family.reads): GUESSED, blue


def test_a_natural_at_its_read_margin_is_written_plain_and_a_weak_one_is_blue():
    _log, (xml, _r) = _written("natural", 0.9)
    assert "<accidental>natural</accidental>" in xml and 'color="%s"' % E.GUESS_COLOR not in xml
    _log, (xml, _r) = _written("natural", 0.1)                        # below NATURAL_READ_MARGIN: GUESSED
    assert "<accidental>natural</accidental>" in xml and 'color="%s"' % E.GUESS_COLOR in xml


def test_CONTROL_without_the_row_nothing_is_written():
    """The same head with no row filed: the note is written at the key's pitch, with no accidental -- the reading existed and nothing carried it (round 1)."""
    _log, (xml, _r) = _written("sharp", 0.9, filed=False)
    assert "<accidental>" not in xml and "<alter>1</alter>" not in xml


def test_CONTROL_a_cell_with_no_page_frame_files_no_row():
    class _NoFrame(_Cell):
        bbox_page_px = None
    log = Log()
    assert PAI.file_own_accidentals(log, [_cluster("sharp", 0.9)], [_NoFrame()], {0: (0, 0)}) == [None]
    assert log.rows(Q.ACCIDENTAL_STAFF_POSITION, CELL, scope=R.Scope.SELF_AND_DESCENDANTS) == ()


def test_the_glyph_ordinal_is_outside_every_other_readers_range():
    assert 350_000 < PAI.GLYPH_BASE < 375_000
