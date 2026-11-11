"""ROADMAP 2.288 -- the rest claim STEP (`page_claim_names.gather_page_claim_boxes` under `OMR_PAGE_CLAIM_RESTS`), on synthetic masks (the harness of the 2.269 step 3 tests).

Pins: only a rest that STANDS READ (an ink-contact row says it stands free) names strokes, and a box with no measurement files nothing and is counted weak (rule 8); the rests flag
alone never names a dynamic; a READ word's AREA claim (the names flag is OFF, so it is a rectangle, not page strokes) keeps its ink from a rest box (Litolff p2, the 'c' 'r' of
"cresc." under a rest-8th box in the first 2.288 gather), and the same box with no word claims it (the control that can fail).
"""
import os
from unittest import mock

from tools.omr.staged import page_claim_names as PCN
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_page_claim_boxes_and_m4b_2_269 import Cell, PWS, det, filed, pagemap
from tools.omr.tests.test_rests_claim_first_2_288 import QUARTER_REST


def pagemap_full(specs):
    """The 2.269 harness's page map with the stroke fields a shape test reads (a real page-map stroke always has them)."""
    pm = pagemap(specs)
    for st in pm.strokes:
        x, y, w, h = st.box
        st.length_sp, st.thickness_sp, st.area_sp2, st.angle_deg, st.staff_space_local = max(w, h) / 20.0, min(w, h) / 20.0, w * h / 400.0, 90.0, 20.0
    return pm


def run_rests(dets, pm, log=None):
    log = log or Log()
    with mock.patch.dict(os.environ, {PCN.ENV_RESTS: "1", PCN.ENV_BOXES: "0", PCN.ENV: "0"}):
        cen = PCN.gather_page_claim_boxes(log, PWS, [Cell()], {0: (0, 0)}, {R.cell(0, 0, 0, 0).to_key(): dets}, pm)
    return log, cen


def contact(log, gi, detail):
    log.observe(R.glyph(0, 0, 0, 0, gi), Q.REST_INK_CONTACT, detail["thin_run_sp"], reader=READERS.CV_REST_INK_CONTACT, frame="cell:0", **detail)


def test_a_READ_rest_claims_its_stroke_and_a_rest_with_no_measurement_claims_nothing():
    pm = pagemap_full([(10, 10, 6, 20)])
    log = Log()
    contact(log, 0, QUARTER_REST)
    log, cen = run_rests([det("restQuarter", 8, 8, 12, 26)], pm, log)
    rows = filed(log)
    assert len(rows) == 1 and rows[0].value == [0] and rows[0].detail["owner"] == "rest" and rows[0].detail["rest_standing"] == "READ"
    assert cen["rest_read"] == 1 and cen["rest_weak"] == {}
    log, cen = run_rests([det("restQuarter", 8, 8, 12, 26)], pm)             # the control that can fail: no contact row -> weak, nothing filed, counted
    assert filed(log) == [] and cen["rest_weak"] == {"no_ink_contact_row": 1} and len(cen["rest_weak_boxes"]) == 1


def test_the_rests_flag_alone_never_names_a_dynamic():
    pm = pagemap_full([(10, 10, 6, 20)])
    log, cen = run_rests([det("dynamicF", 8, 8, 26, 26)], pm)
    assert filed(log) == [] and cen["boxes"] == 0


def test_a_READ_word_over_the_ink_keeps_it_and_the_same_box_without_the_word_claims_it():
    pm = pagemap_full([(10, 10, 6, 20), (20, 10, 6, 20)])
    log = Log()
    contact(log, 0, QUARTER_REST)
    log.observe(R.page(0), Q.CLAIMED_AREA, [5.0, 5.0, 40.0, 40.0], reader=READERS.CV_CLAIMED_REGISTER, frame="page", owner="word", unit="area", standing="READ",
                scope="system", cell=None, source="direction_word")
    log, cen = run_rests([det("rest8th", 8, 8, 24, 26)], pm, log)
    assert filed(log) == [] and cen["contested"] == 2                        # the word holds both strokes
    log2 = Log()
    contact(log2, 0, QUARTER_REST)
    log2, _ = run_rests([det("rest8th", 8, 8, 24, 26)], pm, log2)
    assert len(filed(log2)) == 1 and filed(log2)[0].value == [0, 1]          # control: no word, the rest takes them
