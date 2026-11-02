"""A notehead's EXTENT and CENTRE from its own ink, the detector box only the seed -- ROADMAP 2.248 (STAGED GATHER).

Flag `OMR_HEAD_INK_EXTENT` (default OFF; allow-list until Sean's tiles: "1"/"true"/"yes"/"on" turns it on).

CAUSE (benchmarks/ink-extent-2026-10/FINDINGS.md): Sean's "box too small" heads on the 2.240/2.241 tiles are all (9 of 9) CELL-EDGE
TWINS -- the detector reads one staff's cell at a time, a head of the next staff pokes over the cell's edge, and the cut-off piece is
boxed as a head; the same head is boxed whole in its own staff's cell, and the reading refuses the piece (`clipped_fragment`). The tile
tool drew the piece's detector box. That alone is not a reading change. What IS read from the detector box is the head's STAFF
POSITION (`gather_notehead_positions`: the box's centre, rounded), and an only box cut short of its head moves its centre a step.

What this does (with the flag): the head's ink is read by 2.220's `head_ink.trim_head` (page raster, nothing erased; the box rows widened
by `ROW_SLACK_SPACES`, head-tall columns, bare line pixels out; it never takes a stem, a ledger -- a run longer than a head -- or a foreign
mark's ink). Where that ink is ONE head (`not_one_head` None), no taller than `MAX_INK_HEIGHT_SPACES`, holds the box's own centre row,
and runs into no other notehead box of the same cell (a chord-mate), the position is read from the INK's centre -- but only where the
rounded position differs from the box centre's (otherwise nothing moves). The detector's own position is kept on the row.

CONVENTION ASSUMED: a printed notehead is one oval about one staff space tall (SMuFL noteheadBlack 1.18 x 1.0 sp; Litolff 1.0-1.3,
Brahms 1.0-1.2 measured, 2.39); its staff position is its oval's centre. WHAT WOULD FALSIFY IT: Sean's tiles where the ink-centred
pitch is wrong and the box-centred one right (a head merged with a tie or slur end that the head-tall column test keeps).
NOT CONFIRMED: the height cap is read off our two plates and only narrows which heads may move.
"""
import os
from typing import Any, Dict, Optional, Sequence

ENV = "OMR_HEAD_INK_EXTENT"
#: A head's own ink at most this tall to move its position (SMuFL 1.0 sp; Litolff tilted heads to ~1.3; two stacked heads a second
#: apart measure ~1.5). A cut-off from two plates: it only NARROWS which heads may move.
MAX_INK_HEIGHT_SPACES = 1.35
#: Another notehead box of the cell overlapping the ink rows by more than this (sp) is a chord-mate the ink ran into.
MATE_OVERLAP_SPACES = 0.15
#: How many times the trimmed extent is fed back as the seed (each pass reaches 0.45 sp past the last).
MAX_PASSES = 4
#: r2: a line row reaches past both sides of the head's middle rows and is at least this much wider than the widest of them.
LINE_OVERHANG_SPACES = 0.15
#: r2 (Sean, page-facts "ledger lines name the position", DECISIONS 2026-10-27): a head outside the staff is placed ONLY by counting
#: its own ledger lines; the ink centre moves only heads from the first space above the staff (-1) to the first space below (9).
STAFF_POSITIONS = (-1.0, 9.0)
#: r2 (Sean's tile 7, -2.50 -> -2.51): an ink centre this close (in steps) to the half-way point between two positions decides
#: nothing -- never flip on a coin toss.
BOUNDARY_STEPS = 0.15
#: r2: line rows are looked for in this share of the extent's height at each end (a stem or tail may run past the ledger), and
#: stripping must leave at least `MIN_KEPT_SPACES` of head.
EDGE_BAND_SHARE = 0.3
MIN_KEPT_SPACES = 0.6
#: r2: the head's own columns are read over this middle share of the extent's rows.
MIDDLE_SHARE = 0.4


def enabled() -> bool:
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def ink_extent(page_binary: Any, box: Sequence[float], space_px: float,
               foreign_boxes: Sequence[Sequence[float]] = (),
               other_heads: Sequence[Sequence[float]] = ()) -> Dict[str, Any]:
    """The head's own ink extent grown from the detector page box `box` (x0, y0, x1, y1). Returns `extent` [x0, y0, x1, y1] (page px)
    or None, and `why` (None = usable as the head's extent for its centre): 'no_raster', 'no_head_ink', 'not_one_head:<why>',
    'too_tall', 'box_centre_outside', 'runs_into_another_head'."""
    from . import head_ink
    out: Dict[str, Any] = {"extent": None, "why": None, "height_sp": None, "passes": 0}
    if page_binary is None or not space_px:
        out["why"] = "no_raster"
        return out
    # GROWN FROM THE SEED: 2.220's trim reads the box's rows widened by `ROW_SLACK_SPACES` (0.45 sp) a side, so a box holding
    # half a head reaches only part of the rest. The trimmed extent is fed back as the next seed until it stops growing (a head
    # is at most ~1.3 sp, so `MAX_PASSES` passes reach any head from any piece of it); ink still growing past a head's height
    # is not one head (too_tall below).
    seed = tuple(float(v) for v in box)
    t = None
    first_cols = None
    for _ in range(MAX_PASSES):
        t2 = head_ink.trim_head(page_binary, seed, space_px, foreign_boxes)
        if t2 is None or t2.get("trimmed") is None:
            break
        t = t2
        out["passes"] += 1
        if out["passes"] == 1:
            first_cols = (float(t2["trimmed"][0]), float(t2["trimmed"][2]))
        nxt = tuple(float(v) for v in t["trimmed"])
        if nxt == seed or (nxt[1] >= seed[1] and nxt[3] <= seed[3] and out["passes"] > 1):
            break
        if (nxt[3] - nxt[1]) > MAX_INK_HEIGHT_SPACES * float(space_px):
            break
        seed = nxt
    if t is None:
        out["why"] = "no_raster" if out["passes"] == 0 and head_ink.trim_head(page_binary, box, space_px) is None else "no_head_ink"
        return out
    x0, y0, x1, y1 = (float(v) for v in t["trimmed"])
    # r2 (Sean's tile 2): a LEDGER stub touching the head's top or bottom is not the head. Convention: a ledger line sticks out on
    # BOTH sides of its head; a head's own ink never does. Edge rows whose ink run through the head's centre column passes both
    # side edges of the head's columns (the first pass's, read in the box's own rows) are stripped, whatever their length.
    if first_cols is not None:
        y0, y1, stripped, cols = strip_line_rows(page_binary, (x0, y0, x1, y1), (float(box[0]), float(box[2])), float(space_px))
        if cols is not None:                 # the ledger's overhang columns are not the head's either
            x0, x1 = max(x0, cols[0]), min(x1, cols[1] + 1.0)
        out["line_rows_stripped"] = stripped
    out["extent"] = [x0, y0, x1, y1]
    out["height_sp"] = round((y1 - y0) / float(space_px), 3)
    if t.get("not_one_head"):
        out["why"] = "not_one_head:%s" % t["not_one_head"]
        return out
    if (y1 - y0) > MAX_INK_HEIGHT_SPACES * float(space_px):
        out["why"] = "too_tall"
        return out
    cy = (float(box[1]) + float(box[3])) / 2.0
    if not (y0 <= cy <= y1):
        out["why"] = "box_centre_outside"
        return out
    for b in other_heads:
        if b[1] >= float(box[1]) - 1 and b[3] <= float(box[3]) + 1 and b[0] >= float(box[0]) - 1 and b[2] <= float(box[2]) + 1:
            continue                       # a box inside this one (a twin or a piece of the same head)
        ix = min(x1, b[2]) - max(x0, b[0])
        iy = min(y1, b[3]) - max(y0, b[1])
        if ix > 0 and iy > MATE_OVERLAP_SPACES * float(space_px):
            out["why"] = "runs_into_another_head"
            return out
    return out


def strip_line_rows(page_binary: Any, extent: Sequence[float], head_cols: Sequence[float], space_px: float):
    """(y0, y1, n_stripped, head columns or None): `extent`'s rows with the line rows at its top and bottom edges stripped. A line row: the ink run
    through the head's centre column reaches past BOTH `head_cols` edges by `LINE_OVERHANG_SPACES` (a ledger or staff line)."""
    H, W = page_binary.shape
    cx = int(round((float(head_cols[0]) + float(head_cols[1])) / 2.0))
    tol = max(2.0, LINE_OVERHANG_SPACES * space_px)   # how much wider than the head's widest middle row

    def run(y: int):
        if y < 0 or y >= H or cx < 0 or cx >= W or page_binary[y, cx] != 0:
            return None
        a = cx
        while a > 0 and page_binary[y, a - 1] == 0:
            a -= 1
        b = cx
        while b < W - 1 and page_binary[y, b + 1] == 0:
            b += 1
        return a, b

    # the head's own columns: the widest run through its centre column over the extent's middle rows (a ledger stub at an
    # edge is not there; a ledger THROUGH the middle widens these too, so it is never stripped)
    ey0, ey1 = int(round(extent[1])), int(round(extent[3]))
    q = (ey1 - ey0) * (1.0 - MIDDLE_SHARE) / 2.0
    mids = [r for r in (run(y) for y in range(int(ey0 + q), int(ey1 - q) + 1)) if r is not None]
    if not mids:
        return float(ey0), float(ey1), 0, None
    hx0, hx1 = min(r[0] for r in mids), max(r[1] for r in mids)
    wmax = max(r[1] - r[0] for r in mids)

    def is_line(y: int) -> bool:
        r = run(y)
        return (r is not None and r[0] < hx0 and r[1] > hx1 and (r[1] - r[0]) >= wmax + tol)

    y0, y1 = int(round(extent[1])), int(round(extent[3]))
    h = y1 - y0
    band = int(EDGE_BAND_SHARE * h)
    rows = [y for y in range(y0, y1 + 1) if is_line(y)]
    n = 0
    low = [y for y in rows if y >= y1 - band]            # a line in the bottom band: the head ends above its first row
    if low and (min(low) - 1 - y0) >= MIN_KEPT_SPACES * space_px:
        n += y1 - min(low) + 1
        y1 = min(low) - 1
    high = [y for y in rows if y <= y0 + band]
    if high and (y1 - max(high) - 1) >= MIN_KEPT_SPACES * space_px:
        n += max(high) - y0 + 1
        y0 = max(high) + 1
    return float(y0), float(y1), n, ((float(hx0), float(hx1)) if n else None)


def ink_position(pos_box: float, box: Sequence[float], extent: Sequence[float], half_step_page: float) -> Optional[float]:
    """The staff position of the ink's centre, from the box centre's position `pos_box` and the page-px offset between the centres
    (positions grow downward, one per half staff space). None where the rounded position does not change (nothing moves)."""
    if not half_step_page or half_step_page <= 0:
        return None
    d = ((float(extent[1]) + float(extent[3])) / 2.0 - (float(box[1]) + float(box[3])) / 2.0) / float(half_step_page)
    p = float(pos_box) + d
    lo, hi = STAFF_POSITIONS
    if not (lo - 0.5 < p < hi + 0.5 and lo - 0.5 < float(pos_box) < hi + 0.5):
        return None                         # a far head: its ledger lines are the only witness
    if abs(abs(p - int(p)) - 0.5) < BOUNDARY_STEPS:
        return None                         # on the boundary: the ink does not decide
    return p if int(round(p)) != int(round(float(pos_box))) else None


# ─────────────────────────────────────────────────────────────────────────────
# r3: a far head whose ledger count ABSTAINED is written GUESSED (blue), the box centre and the ink centre both carried
# ─────────────────────────────────────────────────────────────────────────────

#: Flag `OMR_FARHEAD_UNREAD_GUESSED` (default OFF; allow-list "1"/"true"/"yes"/"on"). Its own flag, not `OMR_HEAD_INK_EXTENT`'s, because it
#: is a different change with a different measure (r2 moves in-staff heads; this moves no head, it only MARKS far ones) and can land alone.
#: CLAUDE.md section 5 / page-facts (Sean 2026-10-28, ROADMAP 2.216 option B): a head outside the staff is placed by its ledger lines only,
#: and "no rungs either way is OUR failure: abstain and count it". Today the abstention falls back PLAIN to the box centre
#: (`consequences.restate_pitch`) -- an uncertain pitch written unmarked (section 4, rule 8). With the flag the pitch is still the box
#: centre's (nothing moves; r1's mistake was moving far heads by an ink centre) but is written GUESSED, carrying both steps.
FAR_GUESS_ENV = "OMR_FARHEAD_UNREAD_GUESSED"
FAR_GUESS_REASON = "far_head_ledger_unread"
FAR_GUESS_PITCH_REASON = "position_and_clef_ledger_unread"
#: the order of a far-unread verdict's `candidates` (and of `detail.candidate_sources`)
FAR_GUESS_SOURCES = ("box_centre", "ink_centre")


def far_guess_enabled() -> bool:
    return os.environ.get(FAR_GUESS_ENV, "").strip().lower() in ("1", "true", "yes", "on")


def ink_centre_position(pos_box: float, box: Sequence[float], extent: Sequence[float], half_step_page: float) -> Optional[float]:
    """The staff position of the ink's centre, UNRESTRICTED (a far head too) -- a CANDIDATE only, never a placement: a far head is placed by
    its ledger lines (see `FAR_GUESS_ENV`). None where there is no unit."""
    if not half_step_page or half_step_page <= 0:
        return None
    d = ((float(extent[1]) + float(extent[3])) / 2.0 - (float(box[1]) + float(box[3])) / 2.0) / float(half_step_page)
    return float(pos_box) + d
