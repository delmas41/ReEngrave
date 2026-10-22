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

#: the flag (ROADMAP 2.187), default OFF; it files through the 2.183 key claim, so `claims.key_active()` must also hold
ENV = "OMR_KEY_PER_SYSTEM"


def enabled() -> bool:
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


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
