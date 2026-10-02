"""RED-first synthetic tests for head TEMPLATE matching (ROADMAP lane
`lane-ledger-template`, 2026-10-02 -- DECISIONS task brief: "try
head-template matching for far heads" after the oval shape trace
(`ledger_shape_trace.py`) was measured NET NEGATIVE and held back).

Every image here is hand-built (no detector, no page, no weights,
no library) -- fast and fully synthetic, verifying the BUILD/MATCH/
DECIDE primitives in isolation before any real-data re-score. Run:
`pytest tools/omr/tests/test_head_template_2026_10_02.py -k ledger`.
"""
from __future__ import annotations

import numpy as np
import pytest

from tools.omr.annotate import head_template as ht

SPACING = 20.0  # px per staff space
RX = 14.0       # STANDARD_HEAD_WIDTH_SPACES/2 * SPACING
RY = 11.0       # STANDARD_HEAD_HEIGHT_SPACES/2 * SPACING


def _blank(h: int, w: int) -> np.ndarray:
    return np.full((h, w), 255, dtype=np.uint8)


def _draw_oval(img: np.ndarray, cx: float, cy: float, rx: float = RX,
                ry: float = RY, open_top: bool = False) -> None:
    h, w = img.shape
    y0, y1 = max(0, int(cy - ry) - 1), min(h, int(cy + ry) + 2)
    x0, x1 = max(0, int(cx - rx) - 1), min(w, int(cx + rx) + 2)
    for y in range(y0, y1):
        if open_top and y <= cy - ry * 0.85:
            continue
        dy = (y - cy) / ry
        if abs(dy) > 1.0:
            continue
        dx = rx * (1.0 - dy * dy) ** 0.5
        lx, rxx = int(round(cx - dx)), int(round(cx + dx))
        img[y, max(0, lx):min(w, rxx + 1)] = 0


def _draw_hline(img: np.ndarray, y: float, x0: float, x1: float,
                 thickness: float = 2.0) -> None:
    h, w = img.shape
    t0, t1 = int(round(y - thickness / 2)), int(round(y + thickness / 2)) + 1
    t0, t1 = max(0, t0), min(h, t1)
    xi0, xi1 = max(0, int(round(x0))), min(w, int(round(x1)) + 1)
    img[t0:t1, xi0:xi1] = 0


def _head_box(cx, cy, rx=RX, ry=RY):
    return (cx - rx, cy - ry, cx + rx, cy + ry)


def _build_clean_exemplars_canvas(h=400, w=1400):
    """A canvas of CLEAN, isolated, one-per-cell exemplars: 4 filled
    on-line, 4 filled in-space, 3 hollow on-line (open ovals), 3 hollow
    in-space -- spaced far apart so no window overlaps another, each with
    its own real context ink (a line through it, or lines bounding the
    space above/below), same as a real clean on-staff head would show."""
    img = _blank(h, w)
    exemplars = []
    x = 80
    i = 0

    def _place(cx, cy, kind, variant, open_top=False):
        nonlocal i
        _draw_oval(img, cx, cy, open_top=open_top)
        if variant == "on_line":
            _draw_hline(img, cy, cx - 30, cx + 30)
        else:
            # Real engraving distance: adjacent ledgers/staff lines are
            # exactly ONE staff space apart.
            _draw_hline(img, cy - SPACING, cx - 30, cx + 30)
            _draw_hline(img, cy + SPACING, cx - 30, cx + 30)
        class_name = (
            ("noteheadBlackOnLine" if kind == "filled" else "noteheadHalfOnLine")
            if variant == "on_line" else
            ("noteheadBlackInSpace" if kind == "filled" else "noteheadHalfInSpace")
        )
        exemplars.append(dict(
            box=_head_box(cx, cy), spacing=SPACING, class_name=class_name,
            position=(2 if variant == "on_line" else 3), cell_key=f"cell/{i}",
            isolated=True,
        ))
        i += 1

    for _ in range(4):
        _place(x, 120, "filled", "on_line")
        x += 90
    for _ in range(4):
        _place(x, 120, "filled", "in_space")
        x += 90
    for _ in range(3):
        _place(x, 120, "hollow", "on_line", open_top=True)
        x += 90
    for _ in range(3):
        _place(x, 120, "hollow", "in_space", open_top=True)
        x += 90

    return img, exemplars


# ---------------------------------------------------------------------------
# build_templates
# ---------------------------------------------------------------------------

def test_build_templates_reports_counts_and_excludes_chords():
    img, exemplars = _build_clean_exemplars_canvas()
    # Add a chord pair sharing one cell -- must be EXCLUDED entirely, not
    # just one of the pair.
    exemplars.append(dict(
        box=_head_box(1300, 120), spacing=SPACING,
        class_name="noteheadBlackOnLine", position=2, cell_key="chord/0",
        isolated=True,
    ))
    exemplars.append(dict(
        box=_head_box(1300, 160), spacing=SPACING,
        class_name="noteheadBlackOnLine", position=2, cell_key="chord/0",
        isolated=True,
    ))
    templates, counts = ht.build_templates(img, exemplars)
    assert counts["filled_on_line"] == 4
    assert counts["filled_in_space"] == 4
    assert counts["hollow_on_line"] == 3
    assert counts["hollow_in_space"] == 3
    assert ("filled", "on_line") in templates
    assert ("hollow", "on_line") in templates
    for tmpl in templates.values():
        assert tmpl.img.shape == (ht.CANONICAL_H, ht.CANONICAL_W)


def test_build_templates_drops_non_isolated_and_below_minimum():
    img, exemplars = _build_clean_exemplars_canvas()
    for e in exemplars:
        if e["class_name"] == "noteheadHalfInSpace":
            e["isolated"] = False  # pretend a neighbour box overlaps each
    templates, counts = ht.build_templates(img, exemplars)
    assert counts.get("hollow_in_space", 0) == 0
    assert ("hollow", "in_space") not in templates


# ---------------------------------------------------------------------------
# match / decide
# ---------------------------------------------------------------------------

@pytest.fixture()
def templates():
    img, exemplars = _build_clean_exemplars_canvas()
    tmpls, counts = ht.build_templates(img, exemplars)
    assert counts["filled_on_line"] >= ht.MIN_TEMPLATE_EXEMPLARS
    assert counts["filled_in_space"] >= ht.MIN_TEMPLATE_EXEMPLARS
    assert counts["hollow_on_line"] >= ht.MIN_TEMPLATE_EXEMPLARS
    assert counts["hollow_in_space"] >= ht.MIN_TEMPLATE_EXEMPLARS
    return tmpls


def test_head_on_a_ledger_line_reads_on(templates):
    """A far head with a line through its own middle -- on-line wins."""
    img = _blank(200, 200)
    cx, cy = 100.0, 100.0
    _draw_oval(img, cx, cy)
    _draw_hline(img, cy, cx - 30, cx + 30)
    box = _head_box(cx, cy)
    result = ht.decide_head_position_from_template(
        img, box, SPACING, templates, kind="filled")
    assert result["decision"] == "on", result
    assert ht.template_middle_rung_evidence(
        img, box, SPACING, templates=templates, kind="filled") is True


def test_head_in_a_space_with_ledger_touching_top_reads_space(templates):
    """A far head in a space, with a ledger touching only its top (the
    ledger BEFORE it, bounding the space, ONE staff space from the head's
    own centre -- the real engraving distance between adjacent ledgers)
    -- in-space wins, never on."""
    img = _blank(200, 200)
    cx, cy = 100.0, 100.0
    _draw_oval(img, cx, cy)
    _draw_hline(img, cy - SPACING, cx - 30, cx + 30)
    box = _head_box(cx, cy)
    result = ht.decide_head_position_from_template(
        img, box, SPACING, templates, kind="filled")
    assert result["decision"] == "space", result
    assert ht.template_middle_rung_evidence(
        img, box, SPACING, templates=templates, kind="filled") is False


def test_head_fused_to_chord_partner_a_third_away_centres_on_right_head(templates):
    """Two heads a third apart (a stacked-chord pair outside the staff,
    CLAUDE.md sec10) -- the RIGHT head has a real ledger through its own
    middle; the match for that head's own box must centre on IT, not get
    pulled toward its neighbour a third away."""
    img = _blank(220, 260)
    cx1, cy1 = 100.0, 100.0   # the subject head, ON a ledger
    cx2, cy2 = 100.0, 100.0 - 1.5 * SPACING  # partner a third (1.5 sp) above
    _draw_oval(img, cx1, cy1)
    _draw_hline(img, cy1, cx1 - 30, cx1 + 30)
    _draw_oval(img, cx2, cy2)
    box = _head_box(cx1, cy1)
    result = ht.decide_head_position_from_template(
        img, box, SPACING, templates, kind="filled")
    assert result["decision"] == "on", result
    match = result["match"]
    assert abs(match["center_y"] - cy1) <= 3.0, match
    assert abs(match["center_y"] - cy2) > 10.0, match


def test_hollow_head_with_open_end_still_matched(templates):
    """An OPEN half-note oval (one end not closed) on a ledger -- must
    still match kind='hollow' and read ON."""
    img = _blank(200, 200)
    cx, cy = 100.0, 100.0
    _draw_oval(img, cx, cy, open_top=True)
    _draw_hline(img, cy, cx - 30, cx + 30)
    box = _head_box(cx, cy)
    result = ht.decide_head_position_from_template(
        img, box, SPACING, templates, kind="hollow")
    assert result["decision"] == "on", result


def test_no_image_or_templates_never_guesses():
    """CLAUDE.md rule 8: no evidence possible -> `False`/`None`, never a
    guessed answer."""
    assert ht.template_middle_rung_evidence(None, (0, 0, 10, 10), SPACING) is False
    assert ht.match_head_template(None, (0, 0, 10, 10), SPACING, {}) is None
    img = _blank(100, 100)
    assert ht.template_middle_rung_evidence(
        img, (10, 10, 30, 30), SPACING, templates=None) is False


def test_ambiguous_evidence_is_undecided_never_a_guess(templates):
    """Neither a clean through-line nor a clean bounded space -- a faint,
    off-centre scrap of ink that favours neither template clearly must
    read UNDECIDED, never force an answer (CLAUDE.md rule 8, task brief's
    own stated-margin requirement)."""
    img = _blank(200, 200)
    cx, cy = 100.0, 100.0
    _draw_oval(img, cx, cy)
    # A short, faint smudge barely past the oval on one side only, at
    # neither the middle nor a window edge -- not a clean example of
    # either template.
    _draw_hline(img, cy - 5, cx - RX - 3, cx - RX + 2, thickness=1.0)
    box = _head_box(cx, cy)
    result = ht.decide_head_position_from_template(
        img, box, SPACING, templates, kind="filled")
    assert result["decision"] is None, result
    assert ht.template_middle_rung_evidence(
        img, box, SPACING, templates=templates, kind="filled") is False


def test_stem_column_excluded_from_match():
    """A stem fused to the head's own side must not register as part of
    the head/line evidence -- masked exactly like `ledger_shape_trace`
    already masks it."""
    img, exemplars = _build_clean_exemplars_canvas()
    templates, _ = ht.build_templates(img, exemplars)
    far_img = _blank(220, 200)
    cx, cy = 100.0, 120.0
    _draw_oval(far_img, cx, cy)
    _draw_hline(far_img, cy, cx - 30, cx + 30)
    # A tall, narrow stem running up from the head's right edge.
    far_img[int(cy - 90):int(cy - RY), int(cx + RX - 2):int(cx + RX + 1)] = 0
    box = _head_box(cx, cy)
    result = ht.decide_head_position_from_template(
        far_img, box, SPACING, templates, kind="filled")
    assert result["decision"] == "on", result
