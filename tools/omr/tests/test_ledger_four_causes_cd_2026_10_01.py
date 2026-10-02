"""lane-ledger-r8 (2026-10-01): causes C and D of DECISIONS 2026-10-01's
"four causes behind the 8 far heads neither reader gets right"
(`out/print/ledgers/neither_right_sheet.png`, Litolff, tiles 4-8).

  * Cause D (tiles 6-8): one ledger found correctly, the head just beyond
    it ("slightly low but should read as underneath that ledger line")
    -- the OLD code (`derive_far_head_step`'s `TOUCH_TOL_SPACES`/
    `HALF_LEDGER_TOL_SPACES` distance trichotomy) guessed "on the next
    ledger, hidden under the head" from the raw gap SIZE alone and put
    the head one ledger too far out. Replaced with a direct EVIDENCE
    test (`head_middle_rung_evidence`): a head is ON a ledger only if a
    thin, flat line shows stubs on BOTH sides of the head at its own
    MIDDLE row; otherwise it is in the space beyond the last rung found.

  * Cause C (tiles 4-5): accidental (or broken half-note) ink just left
    of a head on a ledger gets read as two "rungs" at the head's own
    top/bottom edges, while the real line through the head's middle is
    missed. Fix: accidental/other-notehead ink is excluded from the
    stub evidence (`exclude_boxes`), and two candidates that are each
    merely the head's own box edges are dropped and replaced by the one
    real middle rung, if the ink (with the same exclusions) shows it
    there (`collapse_head_edge_rungs_to_middle`).

These tests are pure/synthetic -- no re-gather, no record read. See
`derive_far_head_step`'s own round-2 test file (updated alongside this
one) for the end-to-end, through-`derive_far_head_step` version of the
cause-D fix.
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    head_middle_rung_evidence,
    collapse_head_edge_rungs_to_middle,
    derive_far_head_step,
)

SPACING = 100.0


# ─────────────────────────────────────────────────────────────────────────
# cause D: `head_middle_rung_evidence` -- the evidence primitive
# ─────────────────────────────────────────────────────────────────────────


def _blank(h: int = 400, w: int = 300) -> "np.ndarray":
    return np.full((h, w), 255, dtype=np.uint8)


@pytest.mark.omr_annotate
def test_evidence_true_for_a_real_through_head_ledger_both_sides() -> None:
    """Control: a genuine thin, flat band crossing the head's own middle
    row, reaching well past both stub points -> evidence found."""
    img = _blank()
    head_box = (120.0, 139.0, 180.0, 161.0)  # middle row = 150
    img[148:153, 60:241] = 0  # 5px band, both stubs (95, 205) comfortably inside
    assert head_middle_rung_evidence(img, head_box, SPACING) is True


@pytest.mark.omr_annotate
def test_evidence_false_for_a_head_in_a_space_no_line_at_all() -> None:
    """Control: a head sitting in the space BEYOND one ledger and BEFORE
    the next (both exist, neither at this head's own middle row) -- no
    ink crosses its middle at all -> no evidence, never guessed."""
    img = _blank()
    head_box = (120.0, 139.0, 180.0, 161.0)
    # Ledgers exist elsewhere (above and below this head's own middle),
    # never at row 150 itself.
    img[95:100, 60:241] = 0
    img[200:205, 60:241] = 0
    assert head_middle_rung_evidence(img, head_box, SPACING) is False


@pytest.mark.omr_annotate
def test_accidental_ink_is_never_counted_as_a_stub() -> None:
    """RED before this round: a tall accidental sign's own ink, touching
    the real (short) ledger stub and extending it, can fake a jut past
    the RIGHT stub that is not really there on its own. The real ledger
    alone (x=117..175, inside the box, reaching past NEITHER stub at
    x=95/x=205) must show no evidence; excluding the accidental's box
    (which bridges it out to 210, just past the right stub) must drop
    that false confirmation -- the backup to connectivity, for the rare
    case an accidental's ink does touch the head's own."""
    img = _blank()
    head_box = (120.0, 139.0, 180.0, 161.0)  # stubs at x=95 and x=205
    img[148:153, 117:175] = 0  # the real (short) ledger -- clears neither stub
    img[148:153, 175:210] = 0  # the accidental's own ink, touching it, no gap
    assert head_middle_rung_evidence(img, head_box, SPACING) is True, (
        "setup sanity: without exclusion the merged band must look like "
        "evidence, or this test proves nothing"
    )
    accidental_box = (170.0, 145.0, 215.0, 155.0)
    out = head_middle_rung_evidence(
        img, head_box, SPACING, exclude_boxes=[accidental_box]
    )
    assert out is False


@pytest.mark.omr_annotate
def test_a_line_touching_the_head_is_through() -> None:
    """Sean's connectivity test: ink reaching from inside the head's own
    box (containing the probe column) straight out past the right
    stub, with NO white gap anywhere along the way -- through."""
    img = _blank()
    head_box = (120.0, 139.0, 180.0, 161.0)
    img[148:153, 140:230] = 0  # continuous from inside the box out past 205
    assert head_middle_rung_evidence(img, head_box, SPACING) is True


@pytest.mark.omr_annotate
def test_the_same_line_with_a_2px_gap_is_not_through() -> None:
    """The SAME two pieces of ink -- ink inside the head's own box, and
    a long band reaching past the right stub -- but separated by a 2px
    white gap at the box's own edge. Sean: his accidental crops "never
    had any ink touching the note head", so a gap breaks the
    connection: the run containing the head's own column stops at the
    box edge and never reaches the stub on its own, and the detached
    band outside does not count no matter how far it reaches."""
    img = _blank()
    head_box = (120.0, 139.0, 180.0, 161.0)
    img[148:153, 140:180] = 0   # inside the box, stops exactly at its edge
    img[148:153, 182:230] = 0   # a 2px gap (180..182), then reaches past 205
    assert head_middle_rung_evidence(img, head_box, SPACING) is False


@pytest.mark.omr_annotate
def test_no_image_or_box_is_never_evidence() -> None:
    """No evidence is possible without the page -- `False`, never a
    guess (CLAUDE.md rule 8)."""
    assert head_middle_rung_evidence(None, (0, 0, 1, 1), SPACING) is False
    img = _blank()
    assert head_middle_rung_evidence(img, None, SPACING) is False


# ─────────────────────────────────────────────────────────────────────────
# cause C: `collapse_head_edge_rungs_to_middle`
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_two_edge_rungs_collapse_to_the_real_middle_line() -> None:
    """RED before this round: a candidate near the head's own top edge
    and another near its own bottom edge (the box's own outline, not
    ledgers) must be dropped and replaced by the one real line at the
    head's own middle, when the ink shows it there."""
    img = _blank()
    head_box = (120.0, 139.0, 180.0, 161.0)
    img[148:153, 60:241] = 0  # the one real ledger, through the middle
    # Nearest-edge-first order for sign=-1 ("above"): larger y first.
    fake_edges = [160.0, 140.0]  # at the box's own y1 and y0
    out = collapse_head_edge_rungs_to_middle(
        fake_edges, sign=-1.0, head_box=head_box, img_gray=img, spacing=SPACING,
    )
    assert out == pytest.approx([150.0], abs=1.0)


@pytest.mark.omr_annotate
def test_two_edge_rungs_with_no_real_middle_are_just_dropped() -> None:
    """Without real evidence at the middle, the two edge rows are still
    dropped (they are the box's own outline, never a ledger) -- but
    nothing is invented to replace them."""
    img = _blank()
    head_box = (120.0, 139.0, 180.0, 161.0)
    fake_edges = [160.0, 140.0]
    out = collapse_head_edge_rungs_to_middle(
        fake_edges, sign=-1.0, head_box=head_box, img_gray=img, spacing=SPACING,
    )
    assert out == []


@pytest.mark.omr_annotate
def test_real_ledgers_away_from_the_box_edges_are_untouched_control() -> None:
    """Control: two GENUINE ledgers a normal staff spacing apart, neither
    anywhere near this head's own box edges -- must survive unchanged."""
    img = _blank()
    head_box = (120.0, 139.0, 180.0, 161.0)
    real_rungs = [250.0, 350.0]  # far from (140, 161)
    out = collapse_head_edge_rungs_to_middle(
        real_rungs, sign=-1.0, head_box=head_box, img_gray=img, spacing=SPACING,
    )
    assert out == real_rungs


@pytest.mark.omr_annotate
def test_non_adjacent_edge_candidates_are_untouched_control() -> None:
    """Control: a genuine rung sits BETWEEN the two edge-ish candidates
    in the ladder -- they are not adjacent, so nothing is collapsed (a
    real rung between them means they cannot both be this head's own
    outline)."""
    img = _blank()
    head_box = (120.0, 139.0, 180.0, 161.0)
    rungs = [160.0, 150.0, 140.0]  # a real one wedged between the "edges"
    out = collapse_head_edge_rungs_to_middle(
        rungs, sign=-1.0, head_box=head_box, img_gray=img, spacing=SPACING,
    )
    assert out == rungs


# ─────────────────────────────────────────────────────────────────────────
# `derive_far_head_step`'s own THROUGH decision must be governed by the
# same evidence (coordinator, DECISIONS 2026-10-0x) -- a rung sitting at
# or past the head's near edge is a CANDIDATE, never accepted as through
# on distance alone.
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.omr_annotate
def test_rung_through_the_top_edge_with_no_stubs_is_not_through() -> None:
    """A rung sits right at the head's own near edge (classic "through,
    by distance" shape) but there is NO ink at all at the head's own
    middle row -- no stubs on either side. It must NOT be accepted as
    through; with nothing else found before the head, this abstains
    rather than guessing."""
    img = _blank()
    head_box = (120.0, 139.0, 180.0, 161.0)  # near edge (bottom) = 161
    # The candidate rung sits well past the near edge (gap -0.26 sp,
    # the "through" zone) but the image carries no ink anywhere near
    # the head's own middle (150).
    out = derive_far_head_step(
        [135.0], edge_y=300.0, sign=-1.0, head_near_y=161.0, spacing=SPACING,
        img_gray=img, head_box=head_box,
    )
    assert out["kind"] is None
    assert out["offset"] is None


@pytest.mark.omr_annotate
def test_real_through_ledger_with_both_stubs_is_through() -> None:
    """Control: the SAME shape, but the page shows a genuine band AT
    THE CANDIDATE'S OWN row (135, where the walk actually found it --
    never the head box's unrelated geometric centre) reaching well past
    both stubs -- confirmed through."""
    img = _blank()
    head_box = (120.0, 139.0, 180.0, 161.0)
    img[133:138, 60:241] = 0  # the real ledger, at the candidate's own row
    out = derive_far_head_step(
        [135.0], edge_y=300.0, sign=-1.0, head_near_y=161.0, spacing=SPACING,
        img_gray=img, head_box=head_box,
    )
    assert out["kind"] == "line"
    assert out["offset"] == 2
