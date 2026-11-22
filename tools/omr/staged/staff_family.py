"""WHICH FAMILY PLAYS A STAFF -- strings, woodwind, brass, percussion, other, or unknown (ROADMAP 2.306 / 2.78, flag `OMR_STRING_STOPS_OWN_VALUE`,
default OFF). PATH: STAGED (read by ADJUDICATE `stem_value.adjudicate_stem_value` and by EXPORT `export._place_notes`).

WHY IT EXISTS (Sean, 2026-11-21, page-facts: "On a WOODWIND or BRASS staff every note on one stem shares one written value; on a STRING staff it
need not"): the reader must KNOW a staff is strings before it writes notes of different lengths on one stem. The record already holds the
staff's identity (`Q.INSTRUMENT`, named from its own margin label or the roster) and which part it continues on other systems (`Q.SLOT_INDEX`,
decided by `identity.adjudicate_slot_index`: position in a full-lineup system, the instrument name in a short one). A staff whose own system
prints no margin label (later Litolff pages name only winds, trumpets and timpani) has no `Q.INSTRUMENT`, but its slot is decided and other
staves of that slot are named. Nothing connected the two for a staff's family: `<part-name>` takes the part's name from any of its staves
(`export.build`'s join), but `_place_notes`, which runs before the join, and ADJUDICATE saw only the staff's own name.

THE RULE, as a musician says it: a staff takes its family from its own name; a staff with no name of its own takes it from the part it continues
-- the staves the record already filed as the same part (the same decided slot) -- only where every named staff of that part is of one family
AND its clef is the clef those named staves read. NEVER from position alone: a slot the record did not decide (a short system that drops
resting staves and names nothing) gives no family; two named staves of a slot that disagree give no family; a clef that differs (or is not
read) gives no family. This connects a decision already on the record (rule 6); it guesses nothing.

FAMILIES: `instruments.Instrument.family` string -> STRINGS; woodwind; brass; percussion; keyboard and voice -> OTHER (timpani, harp and keyboard
were not asked about mixed lengths: page-facts 2026-11-21); no name -> UNKNOWN.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ENV = "OMR_STRING_STOPS_OWN_VALUE"

STRINGS = "strings"
WOODWIND = "woodwind"
BRASS = "brass"
PERCUSSION = "percussion"
OTHER = "other"
UNKNOWN = "unknown"

#: where a family came from: the staff's own `Q.INSTRUMENT`, or the part it continues (same decided `Q.SLOT_INDEX`, same clef).
SOURCE_OWN_NAME = "own_name"
SOURCE_SAME_PART = "same_part_named_elsewhere"


def enabled() -> bool:
    """`OMR_STRING_STOPS_OWN_VALUE`, default OFF (1/true/yes/on turns it on)."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def family_of_name(name: Optional[str]) -> str:
    """The family of a canonical instrument name (`Instrument.name`, as `Q.INSTRUMENT.value["name"]` carries it); UNKNOWN for no name or a
    name the table does not hold."""
    from tools.omr import instruments as _I
    inst = _I.instrument_named(name) if isinstance(name, str) else None
    if inst is None:
        return UNKNOWN
    return {"string": STRINGS, "woodwind": WOODWIND, "brass": BRASS, "percussion": PERCUSSION}.get(inst.family, OTHER)


def decide(own_name: Optional[str], own_clef: Optional[str], own_slot: Optional[int],
           named_in_slot: Sequence[Tuple[str, Optional[str], Optional[str]]]) -> Dict[str, Any]:
    """`{"family", "source", "why", "via"}` for one staff.

    `named_in_slot`: `(staff key, instrument name, clef)` of every OTHER staff whose decided slot equals `own_slot` and whose `Q.INSTRUMENT`
    is decided. Pure: the two callers (ADJUDICATE through its Evidence, EXPORT through the record) gather these and ask here, so the two
    stages cannot disagree about a staff."""
    if own_name:
        return {"family": family_of_name(own_name), "source": SOURCE_OWN_NAME, "why": None, "via": [own_name]}
    if own_slot is None:
        return {"family": UNKNOWN, "source": None, "why": "no_name_and_no_decided_slot", "via": []}
    if not named_in_slot:
        return {"family": UNKNOWN, "source": None, "why": "no_named_staff_in_its_part", "via": []}
    fams = {family_of_name(n) for _k, n, _c in named_in_slot}
    if len(fams) != 1:
        return {"family": UNKNOWN, "source": None, "why": "named_staves_of_its_part_disagree", "via": sorted(fams)}
    if not own_clef:
        return {"family": UNKNOWN, "source": None, "why": "own_clef_not_read", "via": []}
    clefs = {c for _k, _n, c in named_in_slot if c}
    if clefs != {own_clef}:
        return {"family": UNKNOWN, "source": None, "why": "clef_differs_from_its_part", "via": sorted(clefs)}
    fam = next(iter(fams))
    return {"family": fam, "source": SOURCE_SAME_PART, "why": None,
            "via": sorted({k for k, _n, _c in named_in_slot})[:4]}


def _decided(v: Any) -> Tuple[bool, Any]:
    """`(decided?, value)` of a verdict given as a record dict or a `Verdict`."""
    if v is None:
        return False, None
    if isinstance(v, dict):
        return v.get("outcome") == "decided", v.get("value")
    out = getattr(v, "outcome", None)
    return getattr(out, "value", out) == "decided", getattr(v, "value", None)


def _name_of(v: Any) -> Optional[str]:
    ok, val = _decided(v)
    if not ok:
        return None
    if isinstance(val, dict):
        n = val.get("name")
        return n if isinstance(n, str) and n else None
    return val if isinstance(val, str) and val else None


def _str_value(v: Any) -> Optional[str]:
    ok, val = _decided(v)
    return val if ok and isinstance(val, str) and val else None


def _int_value(v: Any) -> Optional[int]:
    ok, val = _decided(v)
    return val if ok and isinstance(val, int) and not isinstance(val, bool) else None


def families_from_rows(instrument: Dict[str, Any], slot: Dict[str, Any], clef: Dict[str, Any],
                       staves: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """Every staff key in `staves` -> its `decide` answer. `instrument`/`slot`/`clef`: staff key -> the standing verdict (dict or Verdict)."""
    by_slot: Dict[int, List[Tuple[str, Optional[str], Optional[str]]]] = {}
    for k, v in slot.items():
        s = _int_value(v)
        n = _name_of(instrument.get(k))
        if s is not None and n:
            by_slot.setdefault(s, []).append((k, n, _str_value(clef.get(k))))
    out: Dict[str, Dict[str, Any]] = {}
    for k in staves:
        s = _int_value(slot.get(k))
        mates = [m for m in by_slot.get(s, ()) if m[0] != k] if s is not None else []
        out[k] = decide(_name_of(instrument.get(k)), _str_value(clef.get(k)), s, mates)
    return out


def families_of_record(rec: Any, staves: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """EXPORT's reading, from the finished record (`export.Record`)."""
    from .record import Q

    def standing(q):            # the standing verdict per staff (`Record.verdict` resolves supersession)
        return {s: rec.verdict(q, s) for s in {v["subject"] for v in rec.verdicts_of(q)}}
    return families_from_rows(standing(Q.INSTRUMENT), standing(Q.SLOT_INDEX), standing(Q.CLEF), staves)
