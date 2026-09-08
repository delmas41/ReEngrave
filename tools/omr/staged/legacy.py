"""Extract what the EXISTING pipeline concluded, for the divergence table.

The staged path produces `Verdict`s; the old path produces fields on nested
dicts. This maps the second onto the first's addressing so the two can be
compared without either knowing about the other.

⚠️ ONLY QUANTITIES THE OLD PATH ACTUALLY DECIDES ARE LISTED. A quantity the
old pipeline never concludes has no legacy counterpart, and its staged
verdicts show as `legacy_only` rather than being silently scored as wins.

⚠️ AND ONE FIELD IS DELIBERATELY NOT EXTRACTED: `group_index`. It is written
onto the serialised staff dict (`transcribe.py:4921`) and **no reader in
`export.py` touches it** -- it is DELIVERED AND UNREAD. Comparing against it
would compare our verdict to a number that changes nothing downstream, which
would read as agreement or divergence about a fact the old pipeline does not
actually use. It is available via `group_index_for_reference()` for someone
who wants it, named so the distinction is unmissable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import record as R
from .record import Q, Subject


#: Every quantity `extract` is CAPABLE of emitting.
#:
#: ⚠️ Needed because "the extractor carries no code for this" and "legacy
#: decided nothing here on this page" are different facts that look identical
#: in the output -- both are simply an absent key. On Brahms 1 p2 the coverage
#: report listed `meter` as not extracted, which is false: `extract` puts it,
#: and that page's systems carried `time_signature: None`. A reader would have
#: gone looking for missing code.
EXTRACTED_QUANTITIES: frozenset[str] = frozenset({
    Q.SYSTEM_STAFF_COUNT, Q.SYSTEM_MEMBERSHIP, Q.STAFF_ORDINAL, Q.CLEF,
    Q.KEY_SIGNATURE, Q.INSTRUMENT, Q.SLOT_INDEX, Q.MEASURE_PARTITION, Q.METER,
})


def _system_local(staves: List[dict]) -> Dict[int, int]:
    """Page-wide staff index -> index within its system.

    ⚠️ Mirrors `gather._system_local`. The old result JSON nests staves under
    systems already, so the local index is just enumeration order -- but the
    `staff_index` FIELD on each staff is page-wide, and using it as a subject
    coordinate would misfile every row of every system after the first.
    """
    return {s.get("staff_index", i): i for i, s in enumerate(staves)}


def extract(result: dict) -> Dict[str, Dict[str, Any]]:
    """`{quantity: {subject_key: value}}` from a legacy transcribe result."""
    out: Dict[str, Dict[str, Any]] = {}

    def put(quantity: str, subject: Subject, value: Any) -> None:
        out.setdefault(quantity, {})[subject.to_key()] = value

    for page in result.get("pages", []):
        p = page.get("page_index", 0)
        for sys_i, sys_d in enumerate(page.get("systems", [])):
            s = sys_d.get("system_index", sys_i)
            staves = sys_d.get("staves", [])
            put(Q.SYSTEM_STAFF_COUNT, R.system(p, s), len(staves))
            put(Q.SYSTEM_MEMBERSHIP, R.system(p, s), len(staves))

            for local, staff in enumerate(staves):
                sub = R.staff(p, s, local)
                put(Q.STAFF_ORDINAL, sub, local)

                if staff.get("clef") is not None:
                    put(Q.CLEF, sub, staff["clef"])
                if staff.get("key_signature") is not None:
                    put(Q.KEY_SIGNATURE, sub, staff["key_signature"])
                if staff.get("instrument") is not None:
                    put(Q.INSTRUMENT, sub, {"name": staff["instrument"]})
                if staff.get("slot_index", -1) != -1:
                    put(Q.SLOT_INDEX, sub, staff.get("slot_index"))

                measures = staff.get("measures", [])
                put(Q.MEASURE_PARTITION, sub, len(measures))

            ts = sys_d.get("time_signature")
            if ts is not None:
                put(Q.METER, R.system(p, s), ts)

    return out


def group_index_for_reference(result: dict) -> Dict[str, Any]:
    """⚠️ NOT part of `extract`, and the name says why.

    `group_index` reaches the serialised staff dict and no reader in
    `export.py` consumes it. That is a DIFFERENT failure from a fact that
    never crosses the JSON boundary at all -- delivered-and-unread rather than
    stranded-in-process -- and the two need different fixes. Comparing our
    grouping verdict against it measures agreement about a number that
    changes nothing.
    """
    out: Dict[str, Any] = {}
    for page in result.get("pages", []):
        p = page.get("page_index", 0)
        for sys_i, sys_d in enumerate(page.get("systems", [])):
            s = sys_d.get("system_index", sys_i)
            for local, staff in enumerate(sys_d.get("staves", [])):
                gi = staff.get("group_index")
                if gi is not None:
                    out[R.staff(p, s, local).to_key()] = gi
    return out


def load(path: str) -> Dict[str, Dict[str, Any]]:
    return extract(json.loads(Path(path).read_text()))
