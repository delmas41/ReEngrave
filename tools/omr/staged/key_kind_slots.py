"""The key signature's KIND (flats / sharps) and COUNT read from where its signs sit -- ROADMAP 2.299 (STAGED ADJUDICATE; GATHER rows only read).

Flag `OMR_KEY_KIND_FROM_SLOTS` (default OFF; "1"/"true"/"yes"/"on" turns it on).

CAUSE (benchmarks/key-kind-from-slots-2026-11/FINDINGS.md; 2.292): `adjudicators/header.py:_marker_run` takes the COUNT and the KIND of a key signature
from the detector's key boxes. Litolff crushes the flats together, so boxes go missing or are classed natural / sharp, the staff abstains, and INFER
(`fill_part_key`) supplies the key from the other systems as a GUESS -- almost always the right key (Sean: 11 of 11), so right notes written blue.
But GATHER (2.187) had ALREADY measured the signs: `Q.CLAIMED_AREA` `key_object.read_pieces` holds, per slot the staff printed, the sign's centre
STEP against the staff's own lines at that x (`key_object.measure_tail_box`). Nothing asked what those steps say.

THE RULE (page-facts §2, Sean 2026-10-12 / 2026-10-22: "If there are flats they only show up as Bb, Eb, Ab, Db"): the k-th sign of a key signature
stands at ONE staff step for a clef -- the k-th flat of B E A D G C F, or the k-th sharp of F C G D A E B -- and the two orders stand at different
steps. So the slots read FLATS 3 when every slot k (k = 1..3) stands within `KIND_TOL_STEPS` of the k-th FLAT step of the staff's READ clef (a whole
flat's ink centre stands `ANCHOR_OFFSET_STEPS["flat"]` above its pitch: `key_object.glyph_offset_steps`, MEASURED) AND the sharp order does not fit.
It is READ only when ONE order fits every slot, in order, one slot apart (no gap), for a READ clef, and the rival order misses by at least
`MIN_MARGIN_STEPS` more. Anything else abstains and the existing reading stands UNCHANGED (rule 8: no fallback converts "cannot tell" into an
answer; this never reads, promotes or consults the INFER fill).

OUT OF SCOPE, ABSTAINED: a run holding a NATURAL (a cancelling key change; CONVENTION: page-facts §2) -- a slot whose shape reader says natural and
whose step is not the order's; a run past the system's count (`more_than_system`: a place to look again); no clef or a clef without a slot table;
a slot with no measured step.

TWO WITNESSES OFF ONE RASTER: the key object and the detector's boxes are the same raster and fall silent together. This reading is therefore not
a second witness to the detector's; the SECOND witness is the system ("a key is printed on every staff at one bar; a majority of the system's
staves is enough"), which `header._system_checked` / `_part_checked` still apply to this reading exactly as to any staff reading. A transposing
staff is read from ITS OWN slots (a horn that prints none reads no slots and is not touched here).

CONVENTION ASSUMED: the fixed order and the staff steps of the clef (Sean-confirmed); the tolerance, the flat anchor offset and the margin are
MEASUREMENTS on two plates, so they may only NARROW until another publisher confirms them. WHAT WOULD FALSIFY IT: a staff whose printed signature
is a different count / kind from the slots' fit (Sean's staff-start tiles). NOT CONFIRMED: sharps on a real case (no saved page of either plate
prints a sharp key signature -- see the FINDINGS).
"""
import os
from typing import Any, Dict, Optional, Sequence

ENV = "OMR_KEY_KIND_FROM_SLOTS"
READER = "cv_key_object"
SOURCE = "system_key_object"

#: how far a slot's measured centre may stand from its fixed step: `header.ORDER_TOL_STEPS` (the fitter's `max_residual` after the anchor offset)
KIND_TOL_STEPS = 0.6
#: the rival order must miss by this many steps MORE than the fitting one at its worst slot (the margin the reading reports)
MIN_MARGIN_STEPS = 1.0
#: one slot apart, centre to centre (`key_object.RUN_GAP_SPACES`; Litolff crushes to ~0.6)
MIN_GAP_SPACES = 0.45
MAX_GAP_SPACES = 2.0
MAX_SLOTS = 7


def enabled() -> bool:
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def key_object_row(rows: Sequence[Any]) -> Optional[Dict[str, Any]]:
    """`{"ko": key_object detail, "space": page-px staff space}` from the staff's `cv_key_object` claim rows, or None."""
    for r in rows:
        if getattr(r, "reader", None) != READER:
            continue
        d = r.detail or {}
        if d.get("source") != SOURCE:
            continue
        ko = d.get("key_object")
        if isinstance(ko, dict):
            return {"ko": ko, "space": d.get("space_page_px")}
    return None


def _fit(pieces: Sequence[Dict[str, Any]], clef: str, acc: str) -> Optional[Dict[str, Any]]:
    """How far each slot k stands from the k-th `acc` ("b" | "#") step of `clef`; None where the clef has no table."""
    from . import key_object as KO
    devs = []
    for k, p in enumerate(pieces, start=1):
        e = KO.expected_step(clef, acc, k)
        if e is None:
            return None
        off = KO.glyph_offset_steps(acc, p.get("h") or 0.0)
        devs.append(abs(float(p["step"]) - (e - off)))
    return {"devs": [round(d, 2) for d in devs], "worst": round(max(devs), 2)}


def read(row: Optional[Dict[str, Any]], clef: Optional[str]) -> Dict[str, Any]:
    """`{"kind": "flat"|"sharp"|None, "count": n, "standing": "READ"|None, "margin": steps, "why": str, ...}` for ONE staff (PURE).

    `row`: `key_object_row`. `clef`: the staff's READ clef value (suffix-stripped by the slot table). READ only as the module docstring says;
    otherwise `standing` is None and `why` names the refusal so a reader of the record can count them."""
    if not clef:
        return {"kind": None, "count": 0, "standing": None, "margin": None, "why": "no_clef"}
    if not row or not row.get("ko"):
        return {"kind": None, "count": 0, "standing": None, "margin": None, "why": "no_key_object"}
    ko, sp = row["ko"], row.get("space")
    pieces = [p for p in (ko.get("read_pieces") or []) if isinstance(p, dict)]
    n = len(pieces)
    base = {"kind": None, "count": n, "standing": None, "margin": None}
    if n == 0:
        return dict(base, why="no_slots")
    if ko.get("more_than_system") or n > MAX_SLOTS:
        return dict(base, why="more_than_system")
    pieces = sorted(pieces, key=lambda p: float(p.get("cx") or 0.0))
    if any(p.get("step") is None or p.get("cx") is None for p in pieces):
        return dict(base, why="slot_not_measured")
    if not sp:
        return dict(base, why="no_staff_space")
    sp = float(sp)
    for a, b in zip(pieces, pieces[1:]):
        g = (float(b["cx"]) - float(a["cx"])) / sp
        if g < MIN_GAP_SPACES or g > MAX_GAP_SPACES:
            return dict(base, why="slots_not_one_apart", gap_spaces=round(g, 2))
    fb, fs = _fit(pieces, clef, "b"), _fit(pieces, clef, "#")
    if fb is None or fs is None:
        return dict(base, why="clef_without_slot_table")
    fits_b, fits_s = fb["worst"] <= KIND_TOL_STEPS, fs["worst"] <= KIND_TOL_STEPS
    info = dict(base, flat_worst=fb["worst"], sharp_worst=fs["worst"], flat_devs=fb["devs"], sharp_devs=fs["devs"])
    if fits_b == fits_s:
        return dict(info, why="both_orders_fit" if fits_b else "slots_fit_neither_order")
    kind, own, rival = ("flat", fb, fs) if fits_b else ("sharp", fs, fb)
    margin = round(rival["worst"] - own["worst"], 2)
    if margin < MIN_MARGIN_STEPS:
        return dict(info, why="margin_below_floor", margin=margin, would_be=kind)
    shapes = [str(p.get("shape")) for p in pieces]
    if "natural" in shapes:
        # CONVENTION (page-facts §2): cancelling naturals are part of a CHANGED key's run and stand at the OLD key's steps; a natural-shaped slot
        # means this may be a cancel run, out of scope. The shape reader calls crushed flats natural / sharp (2.256: 8 of 90), so this only abstains.
        return dict(info, why="natural_shaped_slot", would_be=kind, margin=margin)
    return dict(info, kind=kind, standing="READ", margin=margin, why="slots_fit_one_order")


def fifths_of(res: Dict[str, Any]) -> Optional[int]:
    """The signed fifths of a READ result (flats negative), else None."""
    if res.get("standing") != "READ":
        return None
    return -int(res["count"]) if res["kind"] == "flat" else int(res["count"])
