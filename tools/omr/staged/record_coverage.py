"""Does anything a reader would SEE come out the far end?

⚠️ THIS EXISTS BECAUSE THE FAMILY IT CHECKS FOR OCCURRED INSIDE THE
ARCHITECTURE BUILT TO STOP IT, THREE DAYS OLD. Three decisions filled
`Ruling.detail`, the harness dropped it, and every number they computed --
the clef's per-candidate scores, the meter's agreement share, ownership's
`would_win_on_distance` -- was thrown away. It took a test asserting on a
field that did not exist to notice.

The project has paid for that shape NINE times in the exporter, each found
late by forensics after a metric bucket grew, and `export_coverage.py` is the
standing answer there. This is the same answer for the record layer.

⚠️ THE QUESTION THAT WORKS IS NOT "IS THIS FIELD REFERENCED SOMEWHERE."
That is a name-grep, and it calls a field consumed because something ASSIGNS
it -- which is exactly how `Ruling.detail` looked fine. The version that found
the exporter's seventh gap compares WHAT GOES IN against WHAT COMES OUT, so
that is what this does:

  1. `serialisation_gaps` -- a field populated on a real row that does not
     appear in that row's `to_json()`. Runs over an actual log.
  2. `ruling_gaps` -- a `Ruling` field carrying a distinctive sentinel that
     does not appear anywhere in the resulting `Verdict`. Runs the real
     harness; nothing is inspected by name.

`KNOWN_DROPS` is an INVENTORY, not a suppression list: every field we
knowingly drop, with its reason. ⚠️ An entry that is CLOSED must LEAVE it, or
the list stops describing the code and starts describing its history --
`test_staged_record_coverage.py` fails on a stale entry.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any, Dict, List, Optional, Tuple

from . import record as R
from .record import Abstention, Log, Observation, Q, READERS, Verdict

#: Fields we knowingly do not carry, with the reason. Empty is the goal.
#:
#: format: (carrier, field) -> why
KNOWN_DROPS: Dict[Tuple[str, str], str] = {
    ("Verdict", "supersedes"):
        "structural: it names another row and is only meaningful inside the "
        "log's own ordering. `Log.verdict` resolves it; a reader never needs "
        "the id. ⚠️ It IS serialised -- this entry exists only to say that a "
        "null on a first verdict is correct rather than a drop.",
}


def _fields(cls) -> Tuple[str, ...]:
    return tuple(f.name for f in dataclasses.fields(cls))


def _is_default(cls, name: str, value: Any) -> bool:
    for f in dataclasses.fields(cls):
        if f.name != name:
            continue
        if f.default is not dataclasses.MISSING:
            return value == f.default
        if f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
            return value == f.default_factory()           # type: ignore[misc]
    return False


def serialisation_gaps(log: Log) -> List[Tuple[str, str, str]]:
    """Fields POPULATED on a real row and absent from that row's JSON.

    Populated means "set to something other than its default on at least one
    row", so a field nobody ever fills is not reported -- it has nothing to
    lose yet.
    """
    gaps: List[Tuple[str, str, str]] = []
    for cls in (Observation, Abstention, Verdict):
        rows = [r for r in log.all_rows() if isinstance(r, cls)]
        if not rows:
            continue
        emitted = set()
        for r in rows:
            emitted |= set(r.to_json())
        for name in _fields(cls):
            if name in emitted:
                continue
            if all(_is_default(cls, name, getattr(r, name)) for r in rows):
                continue
            gaps.append((cls.__name__, name,
                         "populated on a real row, absent from to_json()"))
    return gaps


#: Values chosen so they cannot occur naturally and cannot be confused for
#: each other in a JSON dump.
_SENTINEL = {
    "value": "__SENTINEL_VALUE__",
    "margin": 424242.5,
    "used": ("__SENTINEL_USED__",),
    "detail": {"__SENTINEL_DETAIL_KEY__": "__SENTINEL_DETAIL_VALUE__"},
}


def ruling_gaps() -> List[Tuple[str, str, str]]:
    """`Ruling` fields that do not survive into the `Verdict`.

    ⚠️ Runs the REAL harness on a probe decision and looks for the sentinel in
    the serialised verdict. Nothing is matched by field name, so a field that
    is carried under a different name still passes -- which is correct: the
    question is whether the information comes out, not whether the label does.
    """
    from . import adjudicate as A

    quantity = Q.ARC_KIND          # a stub in production; safe to displace
    prior = A.REGISTRY.pop(quantity, None)
    try:
        @A.decision(quantity=quantity, scope=R.Kind.GLYPH,
                    wants=(Q.ARC_BOX,), reasons=("probe",),
                    composed_from=(Q.ARC_BOX,))
        def _probe(ev):
            return A.Ruling(value=_SENTINEL["value"], reason="probe",
                            margin=_SENTINEL["margin"],
                            used=_SENTINEL["used"],
                            detail=dict(_SENTINEL["detail"]))

        log = Log()
        sub = R.glyph(0, 0, 0, 0, 0)
        log.observe(sub, Q.ARC_BOX, (0, 0, 1, 1), reader=READERS.DETECTOR,
                    frame="cell:0")
        log.freeze()
        verdict = A.adjudicate_one(log, A.REGISTRY[quantity], sub)
        dumped = json.dumps(verdict.to_json(), default=str)

        gaps: List[Tuple[str, str, str]] = []
        for name, sentinel in _SENTINEL.items():
            probe = (sentinel[0] if isinstance(sentinel, tuple)
                     else next(iter(sentinel.values()))
                     if isinstance(sentinel, dict) else sentinel)
            if str(probe) not in dumped:
                gaps.append(("Ruling", name,
                             "filled by the decision, absent from the Verdict"))
        return gaps
    finally:
        A.REGISTRY.pop(quantity, None)
        if prior is not None:
            A.REGISTRY[quantity] = prior


def report(log: Log) -> Dict[str, Any]:
    found = [g for g in serialisation_gaps(log) + ruling_gaps()
             if (g[0], g[1]) not in KNOWN_DROPS]
    return {"gaps": [list(g) for g in found],
            "known_drops": {f"{k[0]}.{k[1]}": v
                            for k, v in sorted(KNOWN_DROPS.items())},
            "clean": not found}
