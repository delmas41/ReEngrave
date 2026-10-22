"""lane-ledger-edge-fix (2026-10-04, Sean: "Start the fix").

Convention (Sean): a head is ON a ledger only if a thin flat line juts out
of it at its middle row, touching; otherwise the head is in the SPACE
beyond the last ledger, and no ledger between the staff and the head is
ever skipped. A white gap, however small, means the ink is not the
head's. An accidental never touches the head but may merge into the
ledger.

Part 1 (`derive_far_head_step(near_edge_ledgers=True)`): a thin flat ledger
printed against the head's NEAR-staff edge is COUNTED (head in the space
beyond it) instead of being dropped as the head's own outline. A rung at
the FAR edge stays dropped.
Part 2 (`measure_ledger_rungs(restore_masked_staff_side_rungs=True)`): a
ledger between the staff and the head that the other-head mask removed is
put back when the masking head is printed ON it.

Synthetic pages, no record read. Spacing 20 px: ledger 4 px thick (0.2
sp), stub minimum 3 px, thin cap 7 px.
"""
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from tools.omr.annotate.ledger_grid import (  # noqa: E402
    derive_far_head_step,
    measure_ledger_rungs,
    near_edge_ledger_evidence,
)

SP = 20.0
# Head ABOVE the staff (sign -1): its near edge (toward the staff) is the
# BOTTOM of the box. The detector box rides 3 px low, as real ones do, so a
# ledger printed against the head's real bottom lies 0.2+ sp inside the box.
BOX = (100.0, 138.0, 126.0, 160.0)
SIGN = -1.0
EDGE_Y = 300.0


def _page(**kw) -> "np.ndarray":
    img = np.full((400, 300), 255, dtype=np.uint8)
    img[138:158, 100:127] = 0                      # the head: rows 138..157
    for (r0, r1, c0, c1) in kw.get("ink", []):
        img[r0:r1, c0:c1] = 0
    return img


def _derive(img, rung_y, *, flag, exclude=None):
    return derive_far_head_step(
        [rung_y], EDGE_Y, SIGN, BOX[3], SP, img_gray=img, head_box=BOX,
        exclude_boxes=exclude, near_edge_ledgers=flag)


# ---------------------------------------------------------------- Part 1
@pytest.mark.omr_annotate
def test_near_edge_ledger_is_counted_and_head_is_in_the_space_beyond() -> None:
    """Ledger rows 154..157 against the head's bottom, jutting 15 px each
    side. Default (today): dropped as the outline -> no rung before the
    head. With the fix: counted, offset 2*1+1 = 3, a space."""
    img = _page(ink=[(154, 158, 85, 142)])
    default = _derive(img, 155.5, flag=False)
    assert default["offset"] is None            # control: the bug state
    fixed = _derive(img, 155.5, flag=True)
    assert fixed["offset"] == 3 and fixed["kind"] == "space"


@pytest.mark.omr_annotate
def test_default_call_is_unchanged_by_the_new_parameter() -> None:
    img = _page(ink=[(154, 158, 85, 142)])
    assert _derive(img, 155.5, flag=False) == derive_far_head_step(
        [155.5], EDGE_Y, SIGN, BOX[3], SP, img_gray=img, head_box=BOX)


@pytest.mark.omr_annotate
def test_far_edge_rung_stays_dropped() -> None:
    """The same thin flat line, but at the head's FAR (top) edge: nothing
    of the head lies beyond it, so it is another head's ledger or the
    outline -- never counted. Same class as the positive case above."""
    img = _page(ink=[(138, 142, 85, 142)])
    fixed = _derive(img, 139.5, flag=True)
    assert fixed["offset"] is None
    ev = near_edge_ledger_evidence(img, 139.5, BOX, SIGN, SP)
    assert ev["ok"] is False and ev["why"] == "no_head_body_beyond_the_rung"


@pytest.mark.omr_annotate
def test_accidental_shaped_blob_touching_the_head_is_not_a_ledger() -> None:
    """A tall narrow blob (a sharp: 44 px tall, 8 wide) fused to the head's
    left at the rung's row. It is tall, not thin/flat. Nothing juts on the
    right. Not a ledger, still dropped."""
    img = _page(ink=[(128, 172, 92, 100)])
    acc = [(92.0, 128.0, 100.0, 172.0)]      # the detector's accidental box
    fixed = _derive(img, 155.5, flag=True, exclude=acc)
    assert fixed["offset"] is None
    ev = near_edge_ledger_evidence(img, 155.5, BOX, SIGN, SP, acc)
    assert ev["ok"] is False
    # and with no box for it, the tall blob alone still supplies no thin jut
    assert near_edge_ledger_evidence(img, 155.5, BOX, SIGN, SP)["ok"] is False


@pytest.mark.omr_annotate
def test_accidental_merged_into_the_ledger_does_not_veto_it() -> None:
    """Sean: an accidental never touches the head but may merge into the
    ledger. The tall blob sits on the ledger's left end; the ledger's
    right jut is thin and flat and still counts."""
    img = _page(ink=[(154, 158, 85, 142), (128, 172, 85, 92)])
    fixed = _derive(img, 155.5, flag=True, exclude=[(85.0, 128.0, 92.0, 172.0)])
    assert fixed["offset"] == 3 and fixed["kind"] == "space"


@pytest.mark.omr_annotate
def test_white_gap_between_ledger_and_head_means_it_is_not_the_heads() -> None:
    """The ledger pieces are separated from the head body by a white
    column on each side (the head is rows 138..157 cols 100..126; the
    line stops at col 98 and restarts at col 128). Not connected to the
    head -> no jut -> dropped."""
    img = _page(ink=[(154, 158, 85, 99), (154, 158, 128, 142)])
    fixed = _derive(img, 155.5, flag=True)
    assert fixed["offset"] is None
    ev = near_edge_ledger_evidence(img, 155.5, BOX, SIGN, SP)
    assert ev["ok"] is False


@pytest.mark.omr_annotate
def test_head_with_body_on_both_sides_is_on_the_line_not_an_edge() -> None:
    """A head ON the ledger has body on both sides of it; that is the
    through-candidate judged at the middle row, never an edge ledger.
    Head rows 138..174 (a tall box), line rows 154..157 near its upper
    part: body on both sides of the line."""
    img = _page(ink=[(154, 158, 85, 142), (138, 175, 100, 127)])
    box = (100.0, 138.0, 126.0, 175.0)
    ev = near_edge_ledger_evidence(img, 155.5, box, SIGN, SP)
    assert ev["ok"] is False
    assert ev["why"] == "head_body_on_both_sides_of_the_rung"


@pytest.mark.omr_annotate
def test_no_image_is_not_evidence() -> None:
    assert near_edge_ledger_evidence(None, 155.5, BOX, SIGN, SP)["ok"] is False
    assert _derive(None, 155.5, flag=True)["offset"] is None


# ---------------------------------------------------------------- Part 2
# Staff: top line y=300. Ledger 1 at y~280 is printed THROUGH the
# neighbour N (rows 270..290); the subject S above it sits ON ledger 2
# (y~260). N's ledger starts INSIDE N's box on the left (col 104), so it
# does not "continue past the box on both sides" and the other-head mask
# blanks it -- the exact way a real ledger was lost.
STAFF_YS = [300.0, 320.0, 340.0, 360.0, 380.0]
S_BOX = (100.0, 250.0, 126.0, 270.0)
N_BOX = (100.0, 270.0, 126.0, 290.0)


def _two_head_page() -> "np.ndarray":
    img = np.full((420, 300), 255, dtype=np.uint8)
    # bodies 21 px wide (< the 1.3 sp = 26 px rung minimum) so only the
    # ledgers form bands, as on a real page
    img[250:270, 103:124] = 0            # S
    img[270:290, 103:124] = 0            # N
    img[258:262, 85:142] = 0             # ledger through S (y~260)
    img[278:282, 104:142] = 0            # ledger through N (y~280), left end inside the box
    return img


def _measure(restore: bool) -> "list[float]":
    kw = dict(restore_masked_staff_side_rungs=True) if restore else {}
    return measure_ledger_rungs(
        _two_head_page(), STAFF_YS, 113.0, head_y=260.0,
        exclude_boxes=[N_BOX], head_box_x=(S_BOX[0], S_BOX[2]),
        collapse_edges_box=S_BOX, **kw).get("above", [])


@pytest.mark.omr_annotate
def test_masked_ledger_through_the_nearer_head_is_restored() -> None:
    default = _measure(False)
    assert not any(abs(y - 280.0) < 3 for y in default)   # control: it was lost
    restored = _measure(True)
    assert any(abs(y - 280.0) < 3 for y in restored)
    # nothing else changed: every rung the default had is still there
    assert all(any(abs(y - r) < 1.0 for r in restored) for y in default)


@pytest.mark.omr_annotate
def test_ledger_beyond_the_head_is_never_restored() -> None:
    """Same two heads, but the subject is the NEARER one (N): the ledger
    through S lies beyond N's far edge, so it is not between the staff and
    N and is never restored."""
    out = measure_ledger_rungs(
        _two_head_page(), STAFF_YS, 113.0, head_y=280.0,
        exclude_boxes=[S_BOX], head_box_x=(N_BOX[0], N_BOX[2]),
        collapse_edges_box=N_BOX,
        restore_masked_staff_side_rungs=True).get("above", [])
    off = measure_ledger_rungs(
        _two_head_page(), STAFF_YS, 113.0, head_y=280.0,
        exclude_boxes=[S_BOX], head_box_x=(N_BOX[0], N_BOX[2]),
        collapse_edges_box=N_BOX).get("above", [])
    assert out == off


@pytest.mark.omr_annotate
def test_restore_needs_a_jut_from_the_masking_head() -> None:
    """The masking head's own widest row must not be restored as a ledger:
    remove N's ledger entirely; the bare walk finds nothing there."""
    img = _two_head_page()
    img[278:282, 104:142] = 255
    img[278:282, 100:127] = 0            # N's own body only, no line past its box
    out = measure_ledger_rungs(
        img, STAFF_YS, 113.0, head_y=260.0, exclude_boxes=[N_BOX],
        head_box_x=(S_BOX[0], S_BOX[2]), collapse_edges_box=S_BOX,
        restore_masked_staff_side_rungs=True).get("above", [])
    assert not any(abs(y - 280.0) < 3 for y in out)


@pytest.mark.omr_annotate
def test_restore_default_is_off() -> None:
    import inspect
    sig = inspect.signature(measure_ledger_rungs)
    assert sig.parameters["restore_masked_staff_side_rungs"].default is False
    sig = inspect.signature(derive_far_head_step)
    assert sig.parameters["near_edge_ledgers"].default is False
