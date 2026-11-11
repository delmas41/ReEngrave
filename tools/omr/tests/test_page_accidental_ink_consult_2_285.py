"""ROADMAP 2.285 round 2, cause A -- the own-ink accidental reader consults what was already read (`staged/page_accidental_ink.py`).

Round 1's three false claims on Brahms p14: two correct QUARTER RESTS read as flats (a quarter rest is a stem and a curl to its right, which is `accidental_family.read_type`'s
flat) and the `(` of the horn's crook label `(C)` read as a sharp. Each refusal below has the same ink claimed in its CONTROL twin, so none passes by luck.
"""
from types import SimpleNamespace

from tools.omr.staged import page_accidental_ink as PAI
from tools.omr.staged import record as R

SP = 20.0
CELL = R.cell(0, 0, 0, 0)


class _Cell:
    staff_index = 0
    page_index = 0
    measure_index = 0
    bbox_page_px = (1000.0, 500.0, 1600.0, 700.0)
    upscale_factor = 1.0


class _Row:
    def __init__(self, value, **detail):
        self.value, self.detail = value, detail


class _Log:
    def __init__(self, rows):
        self._rows = rows

    def rows(self, *_a, **_k):
        return self._rows


class _D:
    def __init__(self, name, x, y, w, h, conf=0.7):
        self.smufl_name, self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical, self.confidence = name, x, y, w, h, conf


def stroke(kind, x, y, w, h, touches=(), fill=0.9):
    return SimpleNamespace(kind=kind, box=(x, y, w, h), length_sp=max(w, h) / SP, touches=[(int(o), 0.3) for o in touches], parts=[], staff_space_local=SP,
                           fill=fill, area_sp2=fill * w * h / (SP * SP))


def flat(x=100, y=100):
    """A flat's strokes: a stem 2.5 sp tall and a curl low at its right -- also what a quarter rest's strokes look like to the family reader."""
    return [stroke("vertical", x, y, 3, 50, touches=(1,)), stroke("curve", x + 3, y + 28, 12, 22, touches=(0,), fill=0.5)]


def sharp(x=100, y=100):
    return [stroke("vertical", x, y, 3, 58, touches=(2, 3)), stroke("vertical", x + 12, y, 3, 58, touches=(2, 3)),
            stroke("horizontal", x, y + 18, 15, 3, touches=(0, 1)), stroke("horizontal", x, y + 36, 15, 3, touches=(0, 1))]


def head_right(x0=130, y0=125):
    return PAI.Head((x0, y0, x0 + 26, y0 + 20), 0.8, CELL.to_key())


def test_CONTROL_a_flat_shaped_ink_is_claimed_without_the_rest_box_and_refused_with_it():
    found, _why = PAI.read_page(flat(), SP, [head_right()], [], [])
    assert len(found) == 1 and found[0]["type"] == "flat"                  # the control: this ink IS claimed when no rest stands on it
    found, why = PAI.read_page(flat(), SP, [head_right()], [], [], rests=[(95.0, 95.0, 125.0, 160.0)])
    assert found == [] and why.get("rest_box") == 1 and why["claimed"] == 0


def test_a_rest_box_elsewhere_does_not_refuse_it():
    found, _why = PAI.read_page(flat(), SP, [head_right()], [], [], rests=[(400.0, 95.0, 430.0, 160.0)])
    assert len(found) == 1


def test_the_detector_rest_boxes_are_read_apart_from_the_other_earlier_reads():
    dets = {CELL.to_key(): [_D("restQuarter", 100, 20, 30, 60), _D("restWhole", 300, 20, 30, 10), _D("dynamicForte", 500, 20, 30, 30),
                            _D("noteheadBlackInSpace", 700, 20, 26, 20, 0.9), _D("accidentalSharp", 900, 20, 15, 58)]}
    heads, boxed, reads, rests = PAI._detector_reads([_Cell()], {0: (0, 0)}, dets)
    assert len(rests) == 2 and len(reads) == 1 and len(heads) == 1 and len(boxed) == 1
    assert rests[0][0] == 1100.0 and rests[0][1] == 520.0                   # canonical + the cell's page origin (1000, 500)


def test_CONTROL_a_read_word_claims_its_ink_through_the_ledger_rows():
    """A READ word area claim on the log holds the strokes whose centre stands in it (`earlier_claims`); the reader never takes them. A word that is only GUESSED holds nothing."""
    rows = [_Row([90.0, 90.0, 130.0, 170.0], unit="area", standing="READ", owner="word", source="margin_label")]
    rects, ids = PAI.earlier_claims(_Log(rows), None)
    found, _ = PAI.read_page(flat(), SP, [head_right()], [], rects, [], ids)
    assert found == []
    rows = [_Row([90.0, 90.0, 130.0, 170.0], unit="area", standing="GUESSED", owner="word", source="margin_label")]
    rects, ids = PAI.earlier_claims(_Log(rows), None)
    found, _ = PAI.read_page(flat(), SP, [head_right()], [], rects, [], ids)
    assert len(found) == 1                 # the control: the same ink, a word that is not READ, is claimed


def test_the_margin_ink_left_of_the_first_clef_is_refused_and_the_same_ink_right_of_it_is_not():
    """Brahms p14 (536, 1722): the `(` of the horn's crook `(C)`, left of the leading column's claim (x 588) and the clef's (690), read as a sharp. The header claims are the
    page ledger's rows; a clef LEFT of the ink refuses nothing, nor does a claim at other rows."""
    head = head_right(132, 119)
    found, why = PAI.read_page(sharp(), SP, [head], [], [], header=[(300.0, 60.0, 400.0, 200.0)])
    assert found == [] and why.get("left_of_the_clef") == 1
    found, _ = PAI.read_page(sharp(), SP, [head], [], [], header=[(20.0, 60.0, 80.0, 200.0)])           # the clef is LEFT of the ink: a real accidental
    assert len(found) == 1
    found, _ = PAI.read_page(sharp(), SP, [head], [], [], header=[(300.0, 400.0, 400.0, 600.0)])        # another staff's rows: no refusal
    assert len(found) == 1


def test_header_claims_are_the_ledgers_system_start_clef_and_leading_column_rows_only():
    rows = [_Row([588.0, 1584.0, 690.0, 1923.0], unit="area", standing="READ", owner="leading_column", cell=0),
            _Row([690.0, 1663.0, 766.0, 1854.0], unit="area", standing="READ", owner="clef", cell=0),
            _Row([3890.0, 6489.0, 3975.0, 6617.0], unit="area", standing="READ", owner="clef", cell=5, source="clef_pagewide"),     # a clef change: accidentals stand before it
            _Row([1143.0, 6495.0, 1217.0, 6650.0], unit="area", standing="NARROWED", owner="clef", cell=0),
            _Row([766.0, 1669.0, 782.0, 1838.0], unit="area", standing="READ", owner="key_signature", cell=0),
            _Row([1.0, 2.0, 3.0, 4.0], unit="ink", standing="READ", owner="clef", cell=0)]
    assert PAI.header_claims(_Log(rows), None) == [(588.0, 1584.0, 690.0, 1923.0), (690.0, 1663.0, 766.0, 1854.0)]
