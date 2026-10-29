"""ROADMAP 2.221 m2: `OMR_BARLINE_SYSTEM_COLUMNS` -- the system's barline columns read once, through-ink first (STAGED; the extractor is shared)."""
import numpy as np

from tools.omr import measure_extractor as me
from tools.omr.types import Staff

N_STAVES = 4
SPACING = 10
STAFF_H = 4 * SPACING
GAP = 40


def _system():
    """Four staves; barlines at x=300 (through every gap), x=600 (through every gap, but clipped on staff 3), a stem alignment at
    x=450 on staves 0-1 only, and a stem alignment at x=800 on staves 0-2 (a majority) with no ink in any gap."""
    staves, tops = [], []
    for i in range(N_STAVES):
        top = 50 + i * (STAFF_H + GAP)
        tops.append(top)
        staves.append(Staff(page_index=0, staff_index=i, line_ys=[top + k * SPACING for k in range(5)], x_start=100, x_end=1000))
    h = tops[-1] + STAFF_H + 50
    img = np.full((h, 1100), 255, np.uint8)
    for x in (300, 600):
        img[tops[0]:tops[-1] + STAFF_H + 1, x - 1:x + 2] = 0
    img[tops[3] + 5:tops[3] + STAFF_H - 5, 599:602] = 255            # staff 3's own rule is clipped, the gap above still holds it
    img[tops[0]:tops[0] + STAFF_H + 1, 449:452] = 0
    img[tops[0]:tops[0] + STAFF_H + 1, 799:802] = 0
    img[tops[1]:tops[1] + STAFF_H + 1, 799:802] = 0
    img[tops[2]:tops[2] + STAFF_H + 1, 799:802] = 0
    return img, staves


def _clusters(img, staves, xs_by_staff):
    clusters, obs = [], []
    for x in sorted({x for v in xs_by_staff.values() for x in v}):
        clusters.append([x])
        obs.append([(x, si) for si, v in xs_by_staff.items() if x in v])
    return clusters, obs


def test_reinforces_rejects_and_adds_by_through_ink():
    img, staves = _system()
    seen = {0: [300, 450, 600, 800], 1: [300, 600, 800], 2: [300, 600, 800], 3: [300]}
    clusters, obs = _clusters(img, staves, seen)
    counts = {}
    xs_by = lambda ci: {si: clusters[ci][0] for _x, si in obs[ci]}
    old = [300, 450, 800]                                           # the old rule cut the stems and missed the clipped column
    res = me._system_barline_columns(img, staves, clusters, obs, xs_by, old, counts)
    assert res is not None
    assert res[0] == [300, 600]
    assert counts["n_barline_columns_added_missed"] == 1
    assert counts["n_barline_columns_rejected_no_through_ink"] == 2          # 450 minority, 800 majority with no gap ink
    assert counts["n_barline_columns_reinforced_staves"] >= 1


def test_no_through_ink_system_is_left_alone():
    img, staves = _system()
    img[:, 299:302] = 255
    img[:, 599:602] = 255
    img[:, 449:452] = 255
    seen = {0: [450], 1: [450], 2: [450], 3: [450]}
    clusters, obs = _clusters(img, staves, seen)
    assert me._system_barline_columns(img, staves, clusters, obs, lambda ci: {}, [450], {}) is None


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv("OMR_BARLINE_SYSTEM_COLUMNS", raising=False)
    assert not me._system_columns_enabled()
    monkeypatch.setenv("OMR_BARLINE_SYSTEM_COLUMNS", "1")
    assert me._system_columns_enabled()
