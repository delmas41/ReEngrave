"""ROADMAP 2.85: repeat barlines and 1st/2nd endings, per SYSTEM.

How a human reads it off the page: a 1st/2nd-ending bracket is a hooked line
over the bars of each ending with its numeral ("1.", "2.") inside the left
hook; the 1st ending closes with a backward repeat (`:||`, dots in spaces 2
and 3 of every staff). The 2nd ending follows directly. Engraving convention
for the BAR NUMBERS (Sean, 2026-10-11, confirmed on the print: Breitkopf
317803 prints 188, 194, 205 -- DECISIONS 2026-10-10): the 2nd ending REUSES
the 1st ending's bar numbers. That numbering is EXPORT's; this module only
decides which bars each ending covers.

Both decisions read GATHER rows only (`Q.VOLTA_BRACKET`, `Q.VOLTA_NUMERAL`,
`Q.REPEAT_DOTS`, `Q.CELL_BOX`, `Q.SYSTEM_STAFF_COUNT`) and abstain with a
named reason wherever a bracket's numeral or span is not read -- never
guessing which ending a bracket is (CLAUDE.md rules 6, 8).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from ..adjudicate import Checkable, Evidence, Mode, Ruling, decision
from ..record import Kind, Q, Scope

#: A volta hook is at least this long (staff spaces). The SAME floor the CV
#: reader admits candidates on -- read from it, never restated.
from ...volta_bracket import MIN_HOOK_SPACES as _MIN_HOOK

#: A bracket's end stands at a barline: within this many staff spaces of a
#: cell edge. Measured on Brahms p10: 7 px and 6 px off (0.25 spaces); the
#: open 2nd ending ended exactly on its barline.
SPAN_TOL_SPACES = 0.75

#: An ending numeral: one digit, optionally followed by a period. Surya
#: sometimes returns the hook's own stroke as a leading `|` -- stripped as
#: punctuation, never read as a digit.
_NUMERAL = re.compile(r"^[|\s]*([1-9])\s*\.?\s*$")


def _ending_number(text: Any) -> Optional[int]:
    m = _NUMERAL.match(str(text or ""))
    return int(m.group(1)) if m else None


#: A repeat sign is printed on every staff of the system; a dot pair on a
#: few staves is a column of dotted notes. Decided where at least this
#: fraction of the system's staves carry the pair at the same barline
#: (Brahms p10: 11 of 14 staves; every other barline of the page: 0).
MIN_STAFF_FRACTION = 0.5
MIN_STAVES = 2


@decision(
    quantity=Q.REPEAT_BARLINE,
    checkable=Checkable.UNCHECKABLE,
    composed_from=(Q.REPEAT_DOTS, Q.SYSTEM_STAFF_COUNT),
    scope=Kind.SYSTEM,
    wants=(Q.REPEAT_DOTS, Q.SYSTEM_STAFF_COUNT),
    reasons=("read", "no_reading", "no_staff_count", "too_few_staves"),
    mode=Mode.ADDITIVE,
)
def adjudicate_repeat_barlines(ev: Evidence) -> Ruling:
    """Which barlines of this system are repeats, and which way.

    ⚠️ A VOTE ACROSS THE STAVES, NOT A MAJORITY OVER COMPETING ANSWERS: each
    staff's dot pair is its own crop and its own signal, and the question at
    each barline is only whether enough of them saw dots there. A barline
    below the floor is not decided either way (`too_few_staves`, with the
    counts) -- a dotted-note column on two staves must not become a repeat.
    """
    rows = ev.rows(Q.REPEAT_DOTS)
    if not rows:
        return Ruling.abstain("no_reading",
                              n_refusals=len(ev.refusals(Q.REPEAT_DOTS)))
    counts = ev.rows(Q.SYSTEM_STAFF_COUNT)
    if not counts:
        return Ruling.abstain("no_staff_count")
    n_staves = int(counts[0].value)
    floor = max(MIN_STAVES, MIN_STAFF_FRACTION * n_staves)
    by_edge: Dict[Tuple[int, str], Dict[int, str]] = {}
    xs: Dict[Tuple[int, str], List[float]] = {}
    for r in rows:
        det = r.detail or {}
        key = (int(det["cell"]), str(r.value))
        by_edge.setdefault(key, {})[int(det["staff"])] = r.id
        if det.get("barline_x") is not None:
            xs.setdefault(key, []).append(float(det["barline_x"]))
    repeats: List[Dict[str, Any]] = []
    used: List[str] = []
    below: List[Dict[str, Any]] = []
    for (cell, edge), staves in sorted(by_edge.items()):
        if len(staves) >= floor:
            bx = sorted(xs.get((cell, edge), ()))
            repeats.append({
                "cell": cell, "edge": edge,
                "direction": "backward" if edge == "end" else "forward",
                "staves": len(staves),
                # where on the page (median barline x) -- for a crop or a
                # trace, never for the numbering
                "x_page": bx[len(bx) // 2] if bx else None})
            used.extend(staves.values())
        else:
            below.append({"cell": cell, "edge": edge,
                          "staves": len(staves)})
    if not repeats:
        return Ruling.abstain("too_few_staves", n_staves=n_staves,
                              floor=floor, edges=below)
    return Ruling(value=repeats, reason="read", used=tuple(used),
                  detail={"n_staves": n_staves, "below_floor": below})


@decision(
    quantity=Q.ENDINGS,
    checkable=Checkable.UNCHECKABLE,
    composed_from=(Q.VOLTA_BRACKET, Q.VOLTA_NUMERAL, Q.CELL_BOX),
    scope=Kind.SYSTEM,
    wants=(Q.VOLTA_BRACKET, Q.VOLTA_NUMERAL, Q.CELL_BOX),
    reasons=("read", "no_bracket", "no_cell_boxes", "span_not_at_barlines",
             "numeral_unread", "numeral_readers_disagree",
             "no_first_and_second_ending", "endings_not_adjacent"),
    mode=Mode.ADDITIVE,
)
def adjudicate_endings(ev: Evidence) -> Ruling:
    """Which bars of this system are the 1st ending, and which the 2nd.

    A bracket counts as an ending when it has a left hook, both its ends
    stand at barlines of the system's top staff, and its numeral reads as
    one digit. Decided only when a "1." bracket is followed IMMEDIATELY (the
    next bar) by a "2." bracket -- the pair whose bar numbers the print
    reuses.

    ⚠️ ONE SYSTEM ONLY. An ending broken across a system or page break shows
    a bracket with no left hook (or no 2nd ending) on this system and abstains
    (`no_first_and_second_ending`); joining it to its neighbour would be a
    cross-system decision this item does not build. The bar numbers then stay
    counted straight through, out loud.
    """
    brackets = ev.rows(Q.VOLTA_BRACKET)
    if not brackets:
        return Ruling.abstain("no_bracket",
                              n_refusals=len(ev.refusals(Q.VOLTA_BRACKET)))
    boxes = [r for r in ev.rows(Q.CELL_BOX, scope=Scope.SELF_AND_DESCENDANTS)
             if r.subject.kind == Kind.CELL and r.subject.staff == 0]
    if not boxes:
        return Ruling.abstain("no_cell_boxes")
    cells = sorted((int(r.subject.cell), float(r.value[0]), float(r.value[2]),
                    r.id) for r in boxes)

    numerals: Dict[int, List[Tuple[Optional[int], str, str]]] = {}
    for r in ev.rows(Q.VOLTA_NUMERAL):
        k = int((r.detail or {}).get("bracket", -1))
        numerals.setdefault(k, []).append(
            (_ending_number(r.value), str(r.value), r.id))

    endings: List[Dict[str, Any]] = []
    refused: List[Dict[str, Any]] = []
    for b in brackets:
        v = b.value or {}
        det = b.detail or {}
        k = int(det.get("bracket", -1))
        space = float(det.get("space") or 0.0)
        if float(v.get("left_hook") or 0.0) < _MIN_HOOK or space <= 0:
            refused.append({"bracket": k, "why": "no_left_hook"})
            continue
        tol = SPAN_TOL_SPACES * space
        first = next((c for c, x0, _x1, _id in cells
                      if abs(x0 - float(v["x0"])) <= tol), None)
        last = next((c for c, _x0, x1, _id in cells
                     if abs(x1 - float(v["x1"])) <= tol), None)
        if first is None or last is None or last < first:
            refused.append({"bracket": k, "why": "span_not_at_barlines",
                            "x0": v.get("x0"), "x1": v.get("x1")})
            continue
        reads = numerals.get(k, [])
        values = {n for n, _t, _id in reads if n is not None}
        if not values:
            refused.append({"bracket": k, "why": "numeral_unread",
                            "texts": [t for _n, t, _id in reads]})
            continue
        if len(values) > 1:
            refused.append({"bracket": k, "why": "numeral_readers_disagree",
                            "texts": [t for _n, t, _id in reads]})
            continue
        cell_ids = [cid for c, _x0, _x1, cid in cells if first <= c <= last]
        endings.append({
            "number": values.pop(), "first_cell": first, "last_cell": last,
            "closed": float(v.get("right_hook") or 0.0) >= _MIN_HOOK,
            "used": [b.id] + [i for n, _t, i in reads if n is not None]
                    + cell_ids[:1] + cell_ids[-1:]})

    one = [e for e in endings if e["number"] == 1]
    two = [e for e in endings if e["number"] == 2]
    if len(one) != 1 or len(two) != 1:
        found = [{x: e[x] for x in e if x != "used"} for e in endings]
        # ⚠️ ONE LITERAL REASON PER EXIT (`brakes` judges the vocabulary
        # statically): where EVERY bracket was refused, the first refusal
        # names why; otherwise the pair itself is missing.
        whys = {r["why"] for r in refused}
        if not endings and whys == {"span_not_at_barlines"}:
            return Ruling.abstain("span_not_at_barlines", refused=refused)
        if not endings and whys == {"numeral_unread"}:
            return Ruling.abstain("numeral_unread", refused=refused)
        if not endings and whys == {"numeral_readers_disagree"}:
            return Ruling.abstain("numeral_readers_disagree",
                                  refused=refused)
        return Ruling.abstain("no_first_and_second_ending", endings=found,
                              refused=refused)
    e1, e2 = one[0], two[0]
    if e2["first_cell"] != e1["last_cell"] + 1:
        return Ruling.abstain("endings_not_adjacent",
                              first=[e1["first_cell"], e1["last_cell"]],
                              second=[e2["first_cell"], e2["last_cell"]])
    used = tuple(e1["used"]) + tuple(e2["used"])
    value = [{x: e[x] for x in e if x != "used"} for e in (e1, e2)]
    return Ruling(value=value, reason="read", used=used,
                  detail={"refused": refused})
