"""The key signature's KIND (flats / sharps) and COUNT read from where its signs sit -- ROADMAP 2.299 (STAGED ADJUDICATE; GATHER rows only read).

Flag `OMR_KEY_KIND_FROM_SLOTS` (default OFF; "1"/"true"/"yes"/"on" turns it on).

CAUSE (benchmarks/key-kind-from-slots-2026-11/FINDINGS.md; 2.292): `adjudicators/header.py:_marker_run` takes the COUNT and the KIND of a key signature
from the detector's key boxes. Litolff crushes the flats together, so boxes go missing or are classed natural / sharp, the staff abstains, and INFER
(`fill_part_key`) supplies the key from the other systems as a GUESS -- almost always the right key (Sean: 11 of 11), so right notes written blue.
But GATHER (2.187) had ALREADY measured the signs: `Q.CLAIMED_AREA` `key_object.read_pieces` holds, per slot the staff printed, the sign's centre
STEP against the staff's own lines at that x (`key_object.measure_tail_box`). Nothing asked what those steps say.

THE RULE (page-facts §2, Sean 2026-10-12 / 2026-10-22: "If there are flats they only show up as Bb, Eb, Ab, Db"): the k-th sign of a key signature
stands at ONE staff step for a clef -- the k-th flat of B E A D G C F, or the k-th sharp of F C G D A E B -- and the two orders stand at different
steps. A measured slot is the centre of the ink the key object found there. A flat's whole glyph (stem and bowl) has its centre
`ANCHOR_OFFSET_STEPS["flat"]` above its pitch and a crushed bowl alone has it ON its pitch (`key_object.glyph_offset_steps`, MEASURED), and a crushed
Litolff piece covers an unknown part of the glyph -- so a flat slot's feasible centres are the INTERVAL from one anchor to the other; a sharp's is
the step itself. Per slot k: the distance of the measured centre from each order's feasible centres. The slots READ the order they all stand
nearest, when: every slot stands within `KIND_TOL_STEPS` of it, no slot stands nearer the rival, and on average the rival misses by at least
`MIN_MARGIN_STEPS` more (the margin the reading reports). THE COUNT is the number of slots the staff read, accepted only when it EQUALS the
system's agreed count (`key_object` N: two staves read that many in full) -- a staff that read fewer (a crush, or a transposing instrument) is not
read here, and the existing reading stands. Anything else abstains and the existing reading stands UNCHANGED (rule 8: no fallback converts
"cannot tell" into an answer; this never reads, promotes or consults the INFER fill).

OUT OF SCOPE, ABSTAINED: a run holding a NATURAL (a cancelling key change; page-facts §2) -- a slot whose shape reader says natural; a staff with
more pieces than the system's count (`more_than_system`: the extra piece is not on the record, a place to look again); no READ clef or a clef without
a slot table; a slot with no measured step; two slots less than `MIN_GAP_SPACES` apart (one blob counted twice).

TWO WITNESSES OFF ONE RASTER: the key object and the detector's boxes are the same raster and fall silent together. This reading is therefore not
a second witness to the detector's; the SECOND witness is the system ("a key is printed on every staff at one bar; a majority of the system's
staves is enough"), which `header._system_checked` / `_part_checked` still apply to this reading exactly as to any staff reading. A transposing
staff is read from ITS OWN slots; one that prints fewer than the system (a B-flat clarinet in three flats) or none is not touched here.

CONVENTION ASSUMED: the fixed order and the staff steps of the clef (Sean-confirmed); the tolerance, the flat anchors and the margin are
MEASUREMENTS on two plates, so they may only NARROW until another publisher confirms them. WHAT WOULD FALSIFY IT: a staff whose printed signature
is a different count / kind from the slots' fit (Sean's staff-start tiles). NOT CONFIRMED: sharps on a real case (no saved page of either plate
prints a sharp key signature -- see the FINDINGS).
"""
import os
from typing import Any, Dict, Optional, Sequence

ENV = "OMR_KEY_KIND_FROM_SLOTS"
READER = "cv_key_object"
SOURCE = "system_key_object"

#: how far a slot's measured centre may stand from its feasible centres (the interval between the glyph anchors): a MEASUREMENT on Litolff's scan
#: (the 2.187b tail judge uses 0.5 on a point; the interval absorbs the anchor ambiguity, this absorbs the scan's wander)
KIND_TOL_STEPS = 1.0
#: on average over the slots, the rival order must miss by this many steps MORE than the fitting one (the margin the reading reports)
MIN_MARGIN_STEPS = 1.0
#: one slot apart, centre to centre (`key_object.RUN_GAP_SPACES`; Litolff crushes to ~0.6); closer than this is one blob counted twice
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


def _feasible(acc: str, e: float):
    """The centres a slot's ink can measure at when the k-th sign of `acc` stands at step `e`: a flat's from its whole glyph (`e` less the
    anchor offset) to the bowl alone (`e`); a sharp's the step itself."""
    from . import key_object as KO
    return (e - KO.ANCHOR_OFFSET_STEPS["flat"], e) if acc == "b" else (e, e)


def _fit(pieces: Sequence[Dict[str, Any]], clef: str, acc: str) -> Optional[Dict[str, Any]]:
    """How far each slot k stands from the k-th `acc` ("b" | "#") step of `clef` (0 inside its feasible interval); None where the clef has no table."""
    from . import key_object as KO
    devs = []
    for k, p in enumerate(pieces, start=1):
        e = KO.expected_step(clef, acc, k)
        if e is None:
            return None
        lo, hi = _feasible(acc, e)
        st = float(p["step"])
        devs.append(0.0 if lo <= st <= hi else min(abs(st - lo), abs(st - hi)))
    return {"devs": [round(d, 2) for d in devs], "worst": round(max(devs), 2), "sum": round(sum(devs), 2)}


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
    system_n = ko.get("system_count")
    if not isinstance(system_n, int) or system_n < 1:
        return dict(base, why="no_system_count")
    if n != system_n:
        return dict(base, why="fewer_than_system", system_count=system_n)
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
    info = dict(base, flat_devs=fb["devs"], sharp_devs=fs["devs"])
    kind, own, rival = ("flat", fb, fs) if fb["sum"] <= fs["sum"] else ("sharp", fs, fb)
    if own["worst"] > KIND_TOL_STEPS:
        return dict(info, why="slots_fit_neither_order", would_be=kind)
    if any(o > r for o, r in zip(own["devs"], rival["devs"])):
        return dict(info, why="a_slot_stands_nearer_the_other_order", would_be=kind)
    margin = round((rival["sum"] - own["sum"]) / n, 2)
    if margin < MIN_MARGIN_STEPS:
        return dict(info, why="margin_below_floor", margin=margin, would_be=kind)
    if "natural" in [str(p.get("shape")) for p in pieces]:
        # page-facts §2: cancelling naturals are part of a CHANGED key's run; a natural-shaped slot means this may be a cancel run, out of scope.
        # The shape reader calls crushed flats natural / sharp (2.256: 8 of 90), so this only ever abstains.
        return dict(info, why="natural_shaped_slot", would_be=kind, margin=margin)
    return dict(info, kind=kind, standing="READ", margin=margin, why="slots_fit_one_order")


def fifths_of(res: Dict[str, Any]) -> Optional[int]:
    """The signed fifths of a READ result (flats negative), else None."""
    if res.get("standing") != "READ":
        return None
    return -int(res["count"]) if res["kind"] == "flat" else int(res["count"])
