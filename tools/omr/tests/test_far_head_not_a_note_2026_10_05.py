"""lane-farhead-not-a-note (Sean, DECISIONS 2026-10-05): of 12 seeded far-head abstentions, 4 were not noteheads at all
(two barlines/brackets, a tremolo slash, the "a 2" numeral) and were boxed as noteheads and sent to the far-head reader.

The reader refuses (abstains, never deletes) a far "notehead" box when the record's OWN evidence says it is something
else: the record's not-a-notehead verdict, a barline cut the record measured, a tremolo slash (2.49's shape and crossing
rows), a text box overlying it, or the floors `notehead_precision` already holds (too narrow, a clipped sliver).

Spacing here is 16 px (staff lines 100..164); a real head is ~1.3 sp = 21 px wide.
"""
import cv2
import numpy as np

from tools.omr.annotate import far_head_reader as FH

SP = 16.0
HEAD = (290.0, 188.0, 311.0, 204.0)               # 21 x 16 px: a real head, ~1.3 sp wide
CELL = (200.0, 60.0, 500.0, 300.0)
CLS = "noteheadBlackInSpace"
LINES = [100.0, 116.0, 132.0, 148.0, 164.0]
SUBJ = "glyph/0/0/0/0/0"


def _why(box=HEAD, cls=CLS, **ev):
    ev.setdefault("cell_box", CELL)
    return FH.not_a_note_reason(box, cls, SP, **ev)


def test_a_real_head_is_not_refused_with_no_evidence_and_with_all_of_it_clear():
    """The positive control, in the same class as every refusal below."""
    assert _why() is None
    assert _why(barline_xs=[200.0, 500.0], text_boxes=[(0.0, 0.0, 50.0, 20.0)],
                cross=dict(angle_deg=3.0, elongation=1.2, fill=0.7, left_share=0.05, right_share=0.9)) is None


def test_a_narrow_box_on_a_barline_cut_is_refused_as_a_barline():
    box = (296.0, 188.0, 308.0, 204.0)              # 12 px = 0.75 sp, centred on the cut at x=302
    r = _why(box=box, barline_xs=[302.0])
    assert r["reason"] == "on_a_barline" and "barline" in r["words"]
    assert r["drawn"] == [("barline", 302.0)]


def test_a_barline_cut_beside_a_head_wide_box_does_not_refuse_it():
    """The first draft refused real heads and dynamic letters that stood near a cut: it must not."""
    assert _why(barline_xs=[289.0]) is None            # just outside a head-wide box
    assert _why(barline_xs=[292.0]) is None            # inside it, but the box is a whole head wide
    assert (_why(box=(296.0, 188.0, 308.0, 204.0), barline_xs=[290.0]) or {}).get("reason") != "on_a_barline"   # narrow, cut outside it


def test_a_slash_across_its_stem_is_refused_and_a_real_head_on_a_stem_is_not():
    slash = dict(angle_deg=23.7, elongation=2.74, fill=0.45, left_share=0.65, right_share=0.35)
    r = _why(cross=slash)
    assert r["reason"] == "tremolo_slash" and "slash" in r["words"]
    head = dict(angle_deg=5.0, elongation=1.2, fill=0.73, left_share=0.05, right_share=0.9)
    assert _why(cross=head) is None
    one_sided = dict(slash, left_share=0.05, right_share=0.95)       # a stroke on ONE side of the stem only
    assert _why(cross=one_sided) is None


def test_a_text_box_over_the_head_refuses_it_and_a_corner_touch_does_not():
    text = (285.0, 184.0, 316.0, 208.0)             # covers the whole head
    r = _why(text_boxes=[text])
    assert r["reason"] == "on_text" and r["drawn"] == [("text", text)]
    corner = (305.0, 200.0, 340.0, 230.0)           # 6x4 of a 21x16 box: well under half
    assert _why(text_boxes=[corner]) is None


def test_the_floors_the_adjudicator_holds_are_the_same_floors_here():
    thin = (296.0, 188.0, 306.0, 204.0)             # 10 px = 0.62 sp, a black-class box
    assert _why(box=thin)["reason"] == "too_narrow"
    assert _why(box=thin, cls="noteheadHalfInSpace") is None        # the floor is for noteheadBlack* only
    sliver = (290.0, 292.0, 311.0, 300.0)           # 8 px = 0.5 sp tall, on the cell's bottom edge
    assert _why(box=sliver)["reason"] == "clipped_fragment"
    assert _why(box=(290.0, 250.0, 311.0, 258.0)) is None           # the same sliver mid-cell is nobody's edge


def test_the_records_own_not_a_notehead_verdict_refuses_whatever_the_reason():
    r = _why(decided="too_narrow")
    assert r["reason"] == "decided_not_a_notehead" and "too_narrow" in r["words"]


def test_switched_off_the_reader_reads_as_it_did():
    FH.READER_KEYWORDS["not_a_note"] = False
    try:
        gray = np.full((320, 600), 255, np.uint8)
        page = FH.FarHeadPage(gray, [], [], {})
        page.not_a_note = {SUBJ: dict(barline_xs=[302.0], cell_box=CELL)}
        assert page.refuse_not_a_note(SUBJ, (296.0, 188.0, 308.0, 204.0), CLS, SP) is None
    finally:
        FH.READER_KEYWORDS["not_a_note"] = True


def test_page_read_abstains_with_the_named_reason_and_never_a_position():
    gray = np.full((320, 600), 255, np.uint8)
    for y in LINES:
        gray[int(y) - 1:int(y) + 2, 20:580] = 0
    cv2.ellipse(gray, (300, 196), (10, 8), 0, 0, 360, 0, -1)
    box = (296.0, 188.0, 308.0, 204.0)           # a narrow box (half-note class: no width floor) with the cut inside
    page = FH.FarHeadPage(gray, [], [], {})
    page.not_a_note = {SUBJ: dict(barline_xs=[302.0], cell_box=CELL)}
    HALF = "noteheadHalfInSpace"
    res = page.read(SUBJ, box, HALF, LINES)
    assert res["pos"] is None and res["reason"] == "not_a_note:on_a_barline"
    assert res["not_a_note"]["reason"] == "on_a_barline"
    # the same page and head with no evidence is NOT refused for that reason
    page.not_a_note = {}
    assert not str(page.read(SUBJ, box, HALF, LINES)["reason"]).startswith("not_a_note")


# --- the GATHER wiring: the gate reads the record's own rows -------------------------------------------------------
def _gather(cross_detail):
    from tools.omr.staged import gather
    from tools.omr.staged.record import Log, Q
    from tools.omr.tests import test_staged_far_head_ledger_2_56 as T
    gray, box = T._page(ledgers=True, head_pos=-4)
    log = Log()
    g = T.R_glyph(0, 0, 0, 0, 0)
    log.observe(g, Q.NOTEHEAD_STAFF_POSITION, -4.0, reader="geometry", frame="cell:0", residual=0.0, rounded=-4)
    if cross_detail is not None:
        log.observe(g, Q.NOTEHEAD_STEM_CROSS_INK, [0.5, 0.5], reader="cv_notehead_stem_cross_ink", frame="cell:0",
                    **cross_detail)
    from unittest import mock
    with mock.patch.object(FH, "FarHeadPage", T._PooledPage):
        gather.gather_far_head_ledger_positions(log, T._Pws(gray), [T._Cell()], {0: (0, 0)},
                                                {T.R_cell(0, 0, 0, 0).to_key(): [T._Det(box)]}, None)
    return log, g, Q


def test_gather_refuses_a_slash_the_record_measured_and_reads_the_same_head_without_it():
    slash = dict(angle_deg=24.0, elongation=2.7, fill=0.45, left_share=0.6, right_share=0.4)
    log, g, Q = _gather(slash)
    assert log.rows(Q.FAR_HEAD_LEDGER_POSITION, g) == ()
    ab = log.refusals(Q.FAR_HEAD_LEDGER_POSITION, g)
    assert len(ab) == 1 and ab[0].detail["ledger_reason"] == "not_a_note:tremolo_slash"
    log, g, Q = _gather(None)                                   # the positive control: no evidence, the head is read
    assert [r.value for r in log.rows(Q.FAR_HEAD_LEDGER_POSITION, g)] == [-4]
