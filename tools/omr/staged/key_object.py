"""The printed key signature as ONE system object -- ROADMAP 2.187 (STAGED GATHER measurement; decides nothing).

PURE: a page raster (0 == ink, staff lines in), each staff's five line rows, staff space, and the page-px x where its key could start
(the right edge of its clef) and stop (the left edge of its meter, or a fixed reach) in; slot columns out. No log, no cell, no quantity
named -- `gather.gather_key_object` is its stage; `claimed_by.consult` reads the rows it files.

CONVENTION ASSUMED (page-facts §2, Sean 2026-10-12 / 2026-10-20): a key signature is printed on EVERY staff of a system, hard against the
clef, its accidentals one slot apart, and the slots stand at the SAME x on every staff that prints them (the header is typeset as columns,
as the meter is -- 2.177). A staff that transposes prints fewer (or none): its columns are blank, which this reader reports and never
fills. WHAT WOULD FALSIFY IT: a plate whose clef widths push one staff's slots off the others' x (then no column reaches the share and
nothing is claimed -- a refusal to guess, not a wrong claim). NOT CONFIRMED beyond the two plates measured in
`benchmarks/omr-key-signature-claim-2026-10/FINDINGS.md` §2.187.

The shape of `meter_object.find_column`, with the key's own piece test: each staff is read ALONE (`staff_run`: the accidental-sized ink
pieces that chain out of the clef's right edge), then the pieces of all staves are clustered by x into COLUMNS and a column is real only
where a share of the system's staves put a piece in it (`find_object`). The count and extent of the run come from that agreement, never
from one staff. A staff whose own chain is shorter than the system's is reported (`fewer_than_system`), not overruled; a staff with MORE
slots than the system is a place to look again, reported and never claimed past the system's last column.
"""
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import meter_object as MO

#: the flag (ROADMAP 2.187), default ON (Sean 2026-10-23; explicit 0/false/no/off disables); it files through the 2.183 key claim, so `claims.key_active()` must also hold
ENV = "OMR_KEY_PER_SYSTEM"


def enabled() -> bool:
    return os.environ.get(ENV, "").strip().lower() not in ("0", "false", "no", "off")


# --- one accidental piece, in staff spaces (a printed flat is ~1.0 wide and ~2.7 tall; a sharp ~1.2 x 3.2; a natural ~0.8 x 2.8) ---
ACC_H_SPACES = (1.6, 4.4)
ACC_W_SPACES = (0.45, 1.9)
#: ink pixels / box pixels (flats ~0.45, sharps ~0.35; a stemmed note is a thin stem plus a head, ~0.2): keeps the first note of a
#: system with no key signature from being read as one
ACC_FILL_MIN = 0.28
#: the first accidental starts within this many spaces of the clef's right edge (`key_slots.MAX_START_AFTER_CLEF_SPACES`)
MAX_START_AFTER_CLEF_SPACES = 2.0
#: successive accidentals of one run: centre to centre (`key_slots.RUN_GAP_SPACES`)
RUN_GAP_SPACES = 2.0
MAX_SLOTS = 7
#: how far past the clef the window reaches where the staff's meter is unknown (7 slots x 1.15 + a start gap)
WINDOW_REACH_SPACES = 11.0
#: a piece's centre must lie within this many spaces of the staff's five lines (a neighbour staff's ink stands farther)
LEVEL_SPACES = 1.6
#: the band read above / below the staff
BAND_SPACES = 2.2
#: the run's count N is the largest k that at least this many staves of the system read IN FULL on their own (two independent printings of
#: the same signature; measured: the signature is NOT at one x on every staff -- it is typeset against each staff's own clef, so the
#: staves' agreement is on the COUNT and the slot pitch, not on a column)
COUNT_MIN_STAVES = 2
#: the slot pitch used to place a slot a staff did not read: the median centre-to-centre of consecutive pieces over the system, within these
PITCH_SPACES = (0.8, 1.7)


def staff_run(binary: Any, line_ys: Sequence[float], spacing: float, x_start: float, x_hi: float,
              boxes: Sequence[Sequence[float]] = ()) -> Dict[str, Any]:
    """The accidental-sized pieces that chain out of `x_start` (the clef's right edge) on ONE staff, in page px.

    Returns `{"pieces": [{"x0","y0","x1","y1","cx","fill"}...], "reason": None | "no_raster" | "no_staff_geometry" | "no_piece" |
    "starts_too_far" | "too_many_slots"}`. Never a guess: no chain is `pieces == []` and a reason.

    `boxes`: page-px boxes the DETECTOR named as key or accidental ink on this staff (`key*`, `accidental*`) -- a second witness of WHERE a
    slot stands (a different reader from the raster pieces, the same printed ink: each is one candidate, and two on one x are one slot).
    A box is taken as a piece whatever its ink's shape (a crowded print merges a flat with the clef or its neighbour so the raster piece
    fails the size test; the box is the detector's word that a flat stands there). Boxes alone never make a run: the system's columns do."""
    if binary is None or getattr(binary, "ndim", 0) != 2:
        return {"pieces": [], "reason": "no_raster"}
    if len(line_ys) < 5 or not spacing or spacing <= 0:
        return {"pieces": [], "reason": "no_staff_geometry"}
    H, W = binary.shape
    sp = float(spacing)
    ly = [float(v) for v in line_ys]
    x0 = max(0, int(round(x_start - 0.3 * sp)))
    x1 = min(W, int(round(x_hi)))
    y0 = max(0, int(round(ly[0] - BAND_SPACES * sp)))
    y1 = min(H, int(round(ly[-1] + BAND_SPACES * sp)))
    if x1 - x0 < 4 or y1 - y0 < 8:
        return {"pieces": [], "reason": "no_raster"}
    thick = min(MO._line_thickness(binary, ly, x0, x1), 0.5 * sp)
    ink = MO._ink_without_bare_lines(binary, ly, y0, y1, x0, x1, thick)
    cand = []
    for b in boxes:
        if b[2] <= x0 or b[0] >= x1 or not (1.0 <= (b[3] - b[1]) / sp <= ACC_H_SPACES[1]):
            continue
        cy = (b[1] + b[3]) / 2.0
        if cy < ly[0] - LEVEL_SPACES * sp or cy > ly[-1] + LEVEL_SPACES * sp:
            continue
        cand.append({"x0": b[0], "y0": b[1], "x1": b[2], "y1": b[3], "cx": (b[0] + b[2]) / 2.0, "fill": None, "src": "detector"})
    for (px0, py0, px1, py1, area) in MO._pieces(ink):
        w, h = (px1 - px0) / sp, (py1 - py0) / sp
        if not (ACC_W_SPACES[0] <= w <= ACC_W_SPACES[1] and ACC_H_SPACES[0] <= h <= ACC_H_SPACES[1]):
            continue
        fill = area / float(max(1, (px1 - px0) * (py1 - py0)))
        if fill < ACC_FILL_MIN:
            continue
        cy = (py0 + py1) / 2.0 + y0
        if cy < ly[0] - LEVEL_SPACES * sp or cy > ly[-1] + LEVEL_SPACES * sp:
            continue
        cand.append({"x0": px0 + x0, "y0": py0 + y0, "x1": px1 + x0, "y1": py1 + y0, "cx": (px0 + px1) / 2.0 + x0,
                     "fill": round(fill, 3), "src": "raster"})
    for p in cand:
        p["rel"] = round((p["cx"] - x_start) / sp, 3)
        p["rel0"] = round((p["x0"] - x_start) / sp, 3)
        p["rel1"] = round((p["x1"] - x_start) / sp, 3)
    cand.sort(key=lambda p: p["x0"])
    if not cand:
        return {"pieces": [], "reason": "no_piece"}
    first = cand[0]
    if first["x0"] - x_start > MAX_START_AFTER_CLEF_SPACES * sp:
        return {"pieces": [], "reason": "starts_too_far", "first_gap_spaces": round((first["x0"] - x_start) / sp, 2)}
    chain = [first]
    for p in cand[1:]:
        last = chain[-1]
        ov = min(p["x1"], last["x1"]) - max(p["x0"], last["x0"])
        if ov > 0.5 * min(p["x1"] - p["x0"], last["x1"] - last["x0"]):
            continue
        if p["cx"] - last["cx"] > RUN_GAP_SPACES * sp:
            break
        chain.append(p)
    if len(chain) > MAX_SLOTS:
        return {"pieces": [], "reason": "too_many_slots", "n": len(chain)}
    return {"pieces": chain, "reason": None}


def find_object(binary: Any, staves: Sequence[Dict[str, Any]], *, allowed_counts: Optional[Sequence[int]] = None) -> Dict[str, Any]:
    """The key signature of ONE system as ONE count and pitch, from the staves' agreement (and, where admitted, the dossier).

    `staves`: `[{"key", "lines": [5 page y], "spacing": px, "x_start", "x_hi", "boxes": [detector key/accidental boxes]}]` in page px. Each
    staff is read alone (`staff_run`). The run's count `N` is the largest k that at least `COUNT_MIN_STAVES` staves read in full on their
    own; the pitch is the median slot-to-slot distance over the system. `allowed_counts`: the counts the dossier's parts print (a DIFFERENT
    source: the work's own encoding): an `N` outside it is `status: "dossier_disagrees"` and claims nothing; `None` means the dossier is
    silent (`dossier: "silent"`), never "agrees".

    Returns `{"n_staves", "N", "pitch_spaces", "by_staff", "status", "dossier", "counts", "basis"}` with `status` in `found` | `no_count` |
    `dossier_disagrees`; `by_staff[key]` carries `own_slots`, `pieces`, `fewer_than_system`, `more_than_system`. Decides nothing."""
    runs = {st["key"]: staff_run(binary, st["lines"], st["spacing"], st["x_start"], st["x_hi"], st.get("boxes") or ()) for st in staves}
    counts = {k: len(r["pieces"]) for k, r in runs.items()}
    N = 0
    for k in range(MAX_SLOTS, 0, -1):
        if sum(1 for c in counts.values() if c >= k) >= COUNT_MIN_STAVES:
            N = k
            break
    basis = "two_staves"
    if allowed_counts is not None:
        # the dossier (the work's own encoding, a different source) bounds the count: the largest count it prints that AT LEAST ONE staff read
        # in full (a pair reading 4 where the work prints 3 and 1 read a clef's fragment as a slot: 3). It stands in for the second staff when only
        # one read that many. Without the dossier the count stays the pair's -- one staff alone is never the system.
        top = max(counts.values()) if counts else 0
        ks = [k for k in set(allowed_counts) if 1 <= k <= MAX_SLOTS and k <= top]
        # a pair reading a count the work does not print may be one stray piece too many (a clef's fragment, a barline): the dossier's next
        # count down is taken only if it is ONE slot below the pair's; a larger gap is a disagreement, not a correction
        ok = [k for k in ks if k >= N or k == N - 1] if N not in set(allowed_counts) else [k for k in ks if k >= N]
        if ok:
            k = max(ok)
            if k != N:
                N, basis = k, ("two_staves" if sum(1 for c in counts.values() if c >= k) >= COUNT_MIN_STAVES else "one_staff_and_dossier")
    gaps = []
    for st in staves:
        pc = runs[st["key"]]["pieces"]
        gaps += [(b["cx"] - a["cx"]) / st["spacing"] for a, b in zip(pc, pc[1:])]
    gaps.sort()
    pitch = gaps[len(gaps) // 2] if gaps else 1.15
    pitch = min(max(pitch, PITCH_SPACES[0]), PITCH_SPACES[1])
    status = "found" if N else "no_count"
    dossier = "silent"
    if allowed_counts is not None:
        dossier = "agrees" if N in set(allowed_counts) else "disagrees"
        if N and dossier == "disagrees":
            status = "dossier_disagrees"
    by_staff = {}
    for st in staves:
        r = runs[st["key"]]
        n = len(r["pieces"])
        by_staff[st["key"]] = {"own_slots": n, "pieces": r["pieces"], "reason": r["reason"], "x_start": st["x_start"], "x_hi": st["x_hi"],
                               "fewer_than_system": 0 < n < N, "more_than_system": N > 0 and n > N}
    return {"n_staves": len(staves), "N": N, "pitch_spaces": round(pitch, 3), "by_staff": by_staff, "status": status, "dossier": dossier,
            "counts": counts, "basis": basis if N else None}


#: the area reaches this far past the last slot's right edge (`key_slots.EDGE_MARGIN_SPACES`)
EDGE_MARGIN_SPACES = 0.3
#: ... and this far above and below the staff's own pieces (`key_slots.LEVEL_MARGIN_SPACES`)
LEVEL_MARGIN_SPACES = 1.0
#: a slot's own width in spaces where it is placed, not read
SLOT_WIDTH_SPACES = 1.0


def claim_for_staff(obj: Dict[str, Any], key: Any, lines: Sequence[float], spacing: float, *, written_count: Optional[int] = None
                    ) -> Optional[Dict[str, Any]]:
    """What ONE staff claims of the system's run of `N` slots, as one or two PARTS, or None (status not `found`).

    * the slots the staff READ itself (its own pieces, up to N): area from its clef edge to its last read slot, `standing: READ`;
    * the slots it did NOT read, placed one pitch apart from its last (the 'fewer slots' case): a part `standing: NARROWED` -- a box there
      is written blue, never refused -- UNLESS `written_count` (the staff's own instrument's written accidental count, from the roster /
      dossier transposition) is known and is at least N, when that part is READ. Where the instrument's written key cannot be determined
      (`None`, which is every GATHER call today: the part-to-staff join is an ADJUDICATE product) a staff can NEVER claim, beyond the
      slots it read, more than a blue mark -- a B-flat clarinet reading its 1 flat cannot claim 3 (coordinator, 2026-10-22; Sean's
      convention answer pending: CONVENTION ASSUMED);
    * a staff that read none: one NARROWED part over the N slots the system implies (a transposing staff, or a missed one).
    A staff that read MORE than N claims only its first N (a place to look again, reported, never overruled).
    Returns `{"parts": [{"area", "standing", "kind"}], "slots", "own", "placed"}`; `y` is the staff's own pieces' extent (else its five lines')
    unioned with the five lines, padded by `LEVEL_MARGIN_SPACES`."""
    me = obj["by_staff"].get(key)
    N = obj["N"]
    if me is None or obj["status"] != "found" or not N or len(lines) < 5 or not spacing:
        return None
    sp = float(spacing)
    xs = float(me["x_start"])
    pcs = me["pieces"][:N]
    if pcs:
        top, bot = min(p["y0"] for p in pcs), max(p["y1"] for p in pcs)
    else:
        top, bot = float(lines[0]), float(lines[-1])
    # a placed slot's level is not read: take every level a signature's accidental stands at (the staff's five lines, a space beyond)
    top, bot = min(top, float(lines[0])), max(bot, float(lines[-1]))
    y0, y1 = round(top - LEVEL_MARGIN_SPACES * sp, 1), round(bot + LEVEL_MARGIN_SPACES * sp, 1)
    parts: List[Dict[str, Any]] = []
    if pcs:
        read_x1 = pcs[-1]["x1"] + EDGE_MARGIN_SPACES * sp
        parts.append({"area": [round(xs, 1), y0, round(read_x1, 1), y1], "standing": "READ", "kind": "read"})
        if len(pcs) < N:
            pitch = ((pcs[-1]["cx"] - pcs[0]["cx"]) / (len(pcs) - 1) / sp) if len(pcs) >= 2 else obj["pitch_spaces"]
            pitch = min(max(pitch, PITCH_SPACES[0]), PITCH_SPACES[1])
            last_cx = pcs[-1]["cx"] + (N - len(pcs)) * pitch * sp
            x1 = max(last_cx + SLOT_WIDTH_SPACES * sp / 2.0 + EDGE_MARGIN_SPACES * sp, read_x1)
            # slots PLACED, not read: their x is uncertain by the pitch error and a crowded print's drift (Litolff p5: the third flat stands 1.2
            # spaces past where two read slots put it): reach as far as N slots from the clef edge can (first <= 1.8 spaces, pitch <=
            # `PITCH_SPACES[1]`), never past the staff's own meter / window bound
            x1 = max(x1, min(float(me["x_hi"]) - EDGE_MARGIN_SPACES * sp,
                             xs + (1.8 + (N - 1) * PITCH_SPACES[1] + SLOT_WIDTH_SPACES + EDGE_MARGIN_SPACES) * sp))
            known = written_count is not None and int(written_count) >= N
            parts.append({"area": [round(read_x1, 1), y0, round(x1, 1), y1], "standing": "READ" if known else "NARROWED", "kind": "placed"})
    else:
        x1 = xs + (0.9 + (N - 1) * obj["pitch_spaces"] + SLOT_WIDTH_SPACES) * sp + EDGE_MARGIN_SPACES * sp
        parts.append({"area": [round(xs, 1), y0, round(x1, 1), y1], "standing": "NARROWED", "kind": "none_read"})
    return {"parts": parts, "slots": N, "own": len(pcs), "placed": N - len(pcs)}


def allowed_counts(dossier: Any) -> Optional[List[int]]:
    """The accidental counts the dossier's parts print at the work's start (`abs(written_fifths)` over `parts`), or None where the dossier is
    absent or carries no part's fifths (silent, never 'agrees'). Written fifths need no transposition (a part is one instrument)."""
    parts = dossier.get("parts") if isinstance(dossier, dict) else None
    vals = sorted({abs(int(p["written_fifths"])) for p in (parts or []) if isinstance(p, dict) and p.get("written_fifths") is not None})
    return vals or None


# ======================================================================================================================================
# 2.187b -- THE TAIL, JUDGED BY WHAT THE STAFF MAY PRINT (Sean 2026-10-22, three rulings via the coordinator)
#
# The slots a staff did not read itself (the "tail") cost 7 of 9 changes on Sean's tiles: real notes just after a short signature, written blue.
# A box in the tail is now NARROWED only when it could be the staff's own next accidental:
#   (a) SHAPE: its ink is the run's accidental type -- flat / sharp (`accidental_shape.classify`, the 2.190 stem-strength reader: a flat is a
#       stem on the left with nothing top right, a sharp has both, a natural neither); natural too where the key CHANGES (the cancelling
#       naturals come BEFORE the new accidentals, page-facts §2, Sean 2026-10-20); a clear contradiction rejects, an unreadable crush is neutral (a crushed print reads 5 of 15 known flats, so the shape can only reject);
#   (b) POSITION: slot k of the run holds ONLY the k-th accidental of the fixed order (flats B E A D G C F, sharps F C G D A E B -- Sean
#       2026-10-22: "If there are flats they only show up as Bb, Eb, Ab, Db"), and that sits at a FIXED staff step for the clef
#       (`key_signature_geometry.slot_positions`), measured against the staff LOCALLY at the box's x (page-facts §3, `local_line_shift`),
#       within `POS_TOL_STEPS` (the fitter's `max_residual`, half a step) after the glyph-anchor offset (a flat's ink centre stands about a
#       step above its pitch: `ANCHOR_OFFSET_STEPS`, measured);
#   (c) X: it stands at slot k's x (`slot_cx`, the staff's own pitch) within `SLOT_TOL_SPACES` (key_slots.SLOT_TOLERANCE_SPACES) plus a drift
#       allowance per placed slot (Litolff p5 drifts 1.2 spaces by the third);
# and its slot k is within the staff's WRITTEN count (a horn: 0, no tail; a B-flat clarinet in three flats: 1) where that is known.
# Where the written key is not known the type is open (flat, sharp or natural all pass (a)) and the reach is the system's count (today's).
# CONVENTION: the fixed order is Sean's (2026-10-22, confirmed); the offsets / tolerances / drift are MEASUREMENTS on two plates, so they
# may only NARROW. A box that fails any test is LEFT ALONE (no change): it is neither refused nor blue.
# ======================================================================================================================================
POS_TOL_STEPS = 0.5          # key_signature_geometry.KeySignatureFitConfig.max_residual
SLOT_TOL_SPACES = 0.6        # key_slots.SLOT_TOLERANCE_SPACES (0.5) + 0.1: the box's ink centre, not a glyph edge
SLOT_DRIFT_SPACES = 0.2      # per placed slot beyond the first (MEASURED, see FINDINGS 2.187b)
#: a flat's ink centre stands this many steps above its pitch's line / space; a sharp's and a natural's about on it (MEASURED)
ANCHOR_OFFSET_STEPS = {"flat": 1.25, "sharp": 0.0, "natural": 0.0}


def local_line_shift(binary: Any, lines: Sequence[float], spacing: float, x0: float, x1: float) -> float:
    """How far (px) the staff's five lines stand from `lines` at columns x0..x1 (page-facts §3: measure against the staff LOCALLY). The median over
    the lines of the row-profile centroid next to each; 0.0 where a line cannot be found there."""
    import numpy as np
    H, W = binary.shape
    a, b = max(0, int(x0 - 1.5 * spacing)), min(W, int(x1 + 1.5 * spacing))
    if b - a < 4:
        return 0.0
    shifts = []
    for ly in lines:
        r0, r1 = max(0, int(round(ly - 0.45 * spacing))), min(H, int(round(ly + 0.45 * spacing)) + 1)
        if r1 - r0 < 3:
            continue
        prof = (binary[r0:r1, a:b] == 0).sum(axis=1).astype(float)
        if prof.max() < 0.5 * (b - a):
            continue                      # no line here (a glyph's ink or a gap): not measured
        w = np.where(prof >= 0.5 * prof.max(), prof, 0.0)
        shifts.append(float((np.arange(r0, r1) * w).sum() / w.sum()) - float(ly))
    return float(np.median(shifts)) if shifts else 0.0


def measure_tail_box(binary: Any, lines: Sequence[float], spacing: float, box: Sequence[float]) -> Optional[Dict[str, Any]]:
    """What ONE detector box in the tail IS, measured off the page's own ink (PURE; page px in): `{cx, step, h, basis, shape, bl, tr, margin}`.

    The detector's box is NOT the glyph: a crushed Litolff flat is boxed as a rest over its bowl alone (measured: 10 of 15 known key flats have no
    accidental-sized raster piece at their box). So two reads: the INK inside the box (`cx`, and `step`/`h` when no whole glyph is found), and the
    accidental-sized raster PIECE (the `staff_run` size/fill/level tests) that overlaps the box most, the whole glyph where the print kept it
    whole. `shape` is the 2.190 stem-strength reader on that PIECE (flat | natural | sharp | unclear), `unread` when no piece stands there --
    never read off a crop, which calls a flat's bowl a sharp. `step`: the centre's distance below the staff's top line in STEPS (half spaces)
    against the lines AT THIS x (`local_line_shift`); `basis`: `piece` or `box`. None where there is no ink."""
    import numpy as np
    from . import accidental_shape as AS
    if binary is None or getattr(binary, "ndim", 0) != 2 or len(lines) < 5 or not spacing:
        return None
    sp = float(spacing)
    H, W = binary.shape
    bx0, by0, bx1, by1 = (float(v) for v in box)
    x0, x1 = max(0, int(bx0 - 0.6 * sp)), min(W, int(round(bx1 + 0.6 * sp)))
    y0, y1 = max(0, int(lines[0] - BAND_SPACES * sp)), min(H, int(round(lines[-1] + BAND_SPACES * sp)))
    if x1 - x0 < 4 or y1 - y0 < 8:
        return None
    thick = min(MO._line_thickness(binary, lines, max(0, x0 - int(3 * sp)), min(W, x1 + int(3 * sp))), 0.5 * sp)
    ink = MO._ink_without_bare_lines(binary, lines, y0, y1, x0, x1, thick)
    # the ink inside the detector's own box
    ib = np.zeros_like(ink)
    ib[max(0, int(by0) - y0):max(0, int(round(by1)) - y0), max(0, int(bx0) - x0):max(0, int(round(bx1)) - x0)] = True
    ys, xs = np.nonzero(ink & ib)
    if len(ys) < 6:
        return None
    bcx = x0 + (int(xs.min()) + int(xs.max()) + 1) / 2.0
    bcy = y0 + (int(ys.min()) + int(ys.max()) + 1) / 2.0
    bh = (int(ys.max()) + 1 - int(ys.min())) / sp
    # the accidental-sized piece overlapping the box most
    best = None
    for (px0, py0, px1, py1, area) in MO._pieces(ink):
        w, h = (px1 - px0) / sp, (py1 - py0) / sp
        if not (ACC_W_SPACES[0] <= w <= ACC_W_SPACES[1] and ACC_H_SPACES[0] <= h <= ACC_H_SPACES[1]):
            continue
        if area / float(max(1, (px1 - px0) * (py1 - py0))) < ACC_FILL_MIN:
            continue
        cy = (py0 + py1) / 2.0 + y0
        if cy < lines[0] - LEVEL_SPACES * sp or cy > lines[-1] + LEVEL_SPACES * sp:
            continue
        ov = min(px1 + x0, bx1) - max(px0 + x0, bx0)
        if ov > 0 and (best is None or ov > best[0]):
            best = (ov, px0, py0, px1, py1)
    shape, bl, tr, margin = "unread", None, None, None
    cy, h, basis = bcy, bh, "box"
    if best is not None:
        _o, px0, py0, px1, py1 = best
        img = np.where(ink[py0:py1, px0:px1], 0, 255).astype("uint8")
        m = AS.measure(img, (0, 0, img.shape[1], img.shape[0]))
        cl = AS.classify(m)
        shape, bl, tr, margin = cl["shape"], (m or {}).get("bl"), (m or {}).get("tr"), cl["margin"]
        cy, h, basis = (py0 + py1) / 2.0 + y0, (py1 - py0) / sp, "piece"
    shift = local_line_shift(binary, lines, sp, bcx - 0.5 * sp, bcx + 0.5 * sp)
    step = (cy - (float(lines[0]) + shift)) / (sp / 2.0)
    return {"cx": round(bcx, 1), "step": round(step, 2), "h": round(h, 2), "basis": basis, "shape": shape, "bl": bl, "tr": tr, "margin": margin}


def clef_of_box(clef_box: Any, lines: Sequence[float]) -> Optional[str]:
    """The base clef the detector's clef BOX names on one staff, a MEASUREMENT for the key tail's cheap look (the CLEF verdict is ADJUDICATE's):
    gClef / clefG -> treble, fClef / clefF -> bass, cClef / clefC -> alto (the detector's names are `clefG` / `clefF` / `clefC`) where the box's centre stands on the middle line, tenor on the second line from the top, else
    None. `clef_box`: `(smufl name, page-px box)`. An 8va/8vb/15ma suffix changes what sounds, never where the key is printed."""
    if not clef_box or len(lines) < 5:
        return None
    nm, pb = str(clef_box[0]), clef_box[1]
    if nm.startswith(("gClef", "clefG")):
        return "treble"
    if nm.startswith(("fClef", "clefF")):
        return "bass"
    if nm.startswith(("cClef", "clefC")):
        cy = (float(pb[1]) + float(pb[3])) / 2.0
        near = min(range(5), key=lambda i: abs(float(lines[i]) - cy))
        if abs(float(lines[near]) - cy) > 0.35 * (float(lines[1]) - float(lines[0])):
            return None
        return {2: "alto", 1: "tenor"}.get(near)
    return None


def slot_centres(obj: Dict[str, Any], key: Any, spacing: float, upto: int = MAX_SLOTS) -> Dict[int, float]:
    """The page x of the CENTRE of each slot this staff did NOT read (k = own+1 .. upto), placed one pitch apart from its last read piece (or,
    where it read none, from its clef edge as `claim_for_staff` places the none-read area)."""
    me = obj["by_staff"].get(key)
    if me is None:
        return {}
    sp = float(spacing)
    pcs = me["pieces"]
    if pcs:
        pitch = ((pcs[-1]["cx"] - pcs[0]["cx"]) / (len(pcs) - 1) / sp) if len(pcs) >= 2 else obj["pitch_spaces"]
        pitch = min(max(pitch, PITCH_SPACES[0]), PITCH_SPACES[1])
        return {k: pcs[-1]["cx"] + (k - len(pcs)) * pitch * sp for k in range(len(pcs) + 1, upto + 1)}
    pitch = obj["pitch_spaces"]
    return {k: float(me["x_start"]) + (0.9 + (k - 1) * pitch + SLOT_WIDTH_SPACES / 2.0) * sp for k in range(1, upto + 1)}


def expected_step(clef: Optional[str], accidental: str, j: int) -> Optional[float]:
    """The staff step (below the top line) of the j-th (1-based) accidental of the fixed order for `clef`, `accidental` "b" | "#"; None where the
    clef has no table or j is out of 1..7. `key_signature_geometry.slot_positions` (the same table the fitter and the resolver read)."""
    from ..key_signature_geometry import slot_positions
    t = slot_positions(clef, accidental)
    return float(t[j - 1]) if t and 1 <= j <= len(t) else None


def glyph_offset_steps(acc: str, h_spaces: float) -> float:
    """How far the measured ink centre stands ABOVE its pitch's line/space, in steps: a whole flat (about 2.7 spaces: a stem up from a bowl on
    the pitch) stands `ANCHOR_OFFSET_STEPS["flat"]` above it, a crushed bowl alone (about 1.2 spaces, the detector's rest box) stands on it;
    sharps and naturals are centred on it. Interpolated by the ink's height (MEASURED, FINDINGS 2.187b)."""
    if acc != "b":
        return 0.0
    return ANCHOR_OFFSET_STEPS["flat"] * min(1.0, max(0.0, (float(h_spaces) - 1.2) / 1.5))


def judge_tail_box(tb: Optional[Dict[str, Any]], slot_cx: Dict[Any, float], spacing: float, *, own: int, system_n: int,
                   written: Optional[int] = None, previous: Optional[int] = None, clef: Optional[str] = None,
                   loose: bool = False) -> Dict[str, Any]:
    """Is this tail box the staff's own next key accidental? `{"narrow": bool, "why": str, ...}` (PURE; ADJUDICATE calls it with what it knows).

    `tb`: `measure_tail_box`. `slot_cx`: `slot_centres` (keys may be str after a JSON round trip). `own`: the slots the staff read. `system_n`:
    the system's count. `written`: this staff's WRITTEN fifths (negative = flats; None = not known); `previous`: its written fifths on the system
    before (None = unknown); `clef`: base clef name or None.

    The run is, in order: |previous| cancelling naturals at the OLD key's order positions (only where `previous` is known and differs from
    `written`: a key change), then |written| accidentals of the written type at the fixed order's positions; where `written` is None the run is
    the system's N slots of either type (plus naturals) -- today's reach. A box is narrowed when some slot k > own, at its x, could hold it:
      (a) SHAPE: a CLEAR flat/sharp/natural that is not the type slot k holds rejects; unclear / no whole glyph read is neutral (a crushed
          print reads 5 of 15 known flats);
      (b) POSITION: its centre stands at slot k's fixed staff step for the clef (`POS_TOL_STEPS`), after the glyph-anchor offset;
      (c) X: within `SLOT_TOL_SPACES` of slot k's x plus the drift allowance.
    Otherwise the box is LEFT ALONE (`narrow` False). No clef: (b) is unchecked and says so.
    `loose`: the PRE-GATE (a superset of every written key): either type, any slot to `MAX_SLOTS`, any order index 1..k (a key change shifts the
    index by its cancels), naturals allowed -- a box it rejects no written key could narrow, so the heavy reads are skipped for it."""
    if not tb:
        return {"narrow": False, "why": "no_measure"}
    shape = tb.get("shape")
    sp = float(spacing)
    change = previous is not None and written is not None and int(previous) != int(written)
    cancel = abs(int(previous)) if change else 0
    # slot k -> the candidates it could hold: (type "b"|"#", order index j, kind "acc"|"cancel")
    def holds(k):
        if loose:
            return [(t, j, kind) for t in ("b", "#") for j in range(1, k + 1) for kind in ("acc", "cancel")]
        if written is None:
            return [("b", k, "acc"), ("#", k, "acc")] + ([("b", k, "cancel"), ("#", k, "cancel")] if previous is None else [])
        if k <= cancel:
            return [("b" if int(previous) < 0 else "#", k, "cancel")]
        if k - cancel <= abs(int(written)) and written != 0:
            return [("b" if int(written) < 0 else "#", k - cancel, "acc")]
        return []
    reach = int(system_n) if written is None else cancel + abs(int(written))
    if reach <= own:
        return {"narrow": False, "why": "beyond_the_written_count", "reach": reach, "own": own}
    why_not = "not_at_a_slot_x"
    tried = []
    for k in range(own + 1, min(reach, MAX_SLOTS) + 1):
        c = slot_cx.get(k, slot_cx.get(str(k)))
        if c is None:
            continue
        dx = abs(float(tb["cx"]) - float(c))
        if dx > (SLOT_TOL_SPACES + SLOT_DRIFT_SPACES * (k - own - 1)) * sp:
            continue
        tried.append((dx, k))
    for dx, k in sorted(tried):
        cands = holds(k)
        if shape == "flat":
            cands = [c for c in cands if c[0] == "b" and c[2] == "acc"]
        elif shape == "sharp":
            cands = [c for c in cands if c[0] == "#" and c[2] == "acc"]
        elif shape == "natural":
            cands = [c for c in cands if c[2] == "cancel"]
        if not cands:
            why_not = "natural_without_a_key_change" if shape == "natural" else "wrong_accidental_type"
            continue
        if not clef:
            return {"narrow": True, "why": "tail_accidental", "slot": k, "shape": shape, "position": "unchecked_no_clef"}
        best = None
        for (t, j, kind) in cands:
            e = expected_step(clef, t, j)
            if e is None:
                continue
            d = abs(float(tb["step"]) - (e - (0.0 if kind == "cancel" else glyph_offset_steps(t, tb.get("h") or 0.0))))
            best = d if best is None or d < best else best
        if best is None:
            return {"narrow": True, "why": "tail_accidental", "slot": k, "shape": shape, "position": "unchecked_no_table"}
        if best <= POS_TOL_STEPS:
            return {"narrow": True, "why": "tail_accidental", "slot": k, "shape": shape, "position": "matches", "off_by_steps": round(best, 2)}
        why_not = "wrong_staff_step_for_the_slot"
    return {"narrow": False, "why": why_not}
