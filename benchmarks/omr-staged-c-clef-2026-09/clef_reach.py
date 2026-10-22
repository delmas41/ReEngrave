"""REACH: how many clef detections does the staged gatherer admit, and how many
does it drop in silence -- and, the number that decides the lane, how many
STAVES lose their clef entirely because of it.

⚠️ WHY STAVES AND NOT DETECTIONS. `gather_clef` abstains
`Q.CLEF_GLYPH / NO_DETECTIONS` on a staff whose cell-0 holds no ADMITTED clef.
A staff whose clef abstains gets no pitches at all on the staged path
(`consequences.restate_pitch`), so one dropped C clef is a whole staff of
missing music -- while a dropped C clef on a staff that ALSO detected a
`clefG` costs only a contest the adjudicator never saw.

⚠️ THE ADMITTED SET IS IMPORTED, NEVER RESTATED. Restating it here would let
the probe and the pipeline drift, which is the whole failure this lane is
about.

⚠️ CELL 0 ONLY, because that is `gather_clef`'s own domain (`if sub.cell != 0:
continue`). Clef detections in later cells are counted and reported APART: a
mid-staff clef change is a different question and this lane does not touch it.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))

from recordstream import stream_array                       # noqa: E402
from tools.omr.staged.gather import (                       # noqa: E402
    _CLEF_CLASSES_INCUMBENT, _is_clef_class)
from tools.omr.clef_geometry import clef_family             # noqa: E402


def admit_incumbent(name: str, category: str) -> bool:
    """The rule as it stood before this lane -- a literal set, no category."""
    return name in _CLEF_CLASSES_INCUMBENT


def admit_repaired(name: str, category: str) -> bool:
    """The shipped rule, IMPORTED so the probe cannot drift from it."""
    return _is_clef_class(name, category)


def _is_clef_row(o: dict) -> bool:
    """A clef by the DETECTOR'S OWN category, not by a name prefix.

    ⚠️ Category, because the question is 'what did the detector call a clef',
    and a name test would bake this lane's own answer into its measurement.
    """
    return (o.get("detail") or {}).get("category") == "clef"


def measure(path: str, admit=admit_incumbent) -> dict:
    admitted = Counter()
    dropped = Counter()
    later_cell = Counter()
    staves: dict[tuple, dict] = defaultdict(lambda: {"admitted": 0, "dropped": Counter()})
    seen_staves: set[tuple] = set()

    for o in stream_array(path, "observations"):
        if o.get("quantity") != "glyph_box":
            continue
        if not _is_clef_row(o):
            continue
        val = o.get("value") or []
        if not val:
            continue
        name = str(val[0])
        parts = str(o.get("subject", "")).split("/")
        # glyph/page/system/staff/cell/idx
        if len(parts) != 6 or parts[0] != "glyph":
            continue
        page, system, staff, cell = parts[1], parts[2], parts[3], parts[4]
        if cell != "0":
            later_cell[name] += 1
            continue
        key = (page, system, staff)
        seen_staves.add(key)
        if admit(name, (o.get("detail") or {}).get("category")):
            admitted[name] += 1
            staves[key]["admitted"] += 1
        else:
            dropped[name] += 1
            staves[key]["dropped"][name] += 1

    starved = {k: v for k, v in staves.items()
               if v["admitted"] == 0 and sum(v["dropped"].values()) > 0}
    rescuable = {k: v for k, v in starved.items()
                 if any(clef_family(n) is not None for n in v["dropped"])}
    return {
        "admitted": admitted, "dropped": dropped, "later_cell": later_cell,
        "staves_with_a_clef_detection": len(seen_staves),
        "starved": starved, "rescuable": rescuable,
    }


def main() -> int:
    docs = {
        "Litolff Beethoven 5 p1-p4": "library/_shared-records/beethoven5-p1-p4.record.json",
        "Breitkopf Brahms 1 p0-p3": "library/_shared-records/brahms1-breitkopf-p0-p3.record.json",
    }
    print(f"incumbent admitted set: {sorted(_CLEF_CLASSES_INCUMBENT)}\n")
    total_admitted = 0
    for label, rel in docs.items():
        p = ROOT / rel
        if not p.exists():
            print(f"{label}: RECORD ABSENT at {rel} -- reported, not skipped")
            continue
        print(f"=== {label} ===")
        for arm, fn in (("INCUMBENT", admit_incumbent), ("REPAIRED", admit_repaired)):
            r = measure(str(p), fn)
            na, nd = sum(r["admitted"].values()), sum(r["dropped"].values())
            if arm == "INCUMBENT":
                total_admitted += na
            print(f"  -- {arm} --")
            print(f"     cell-0 clef detections : {na + nd}")
            print(f"     ADMITTED               : {na}   {dict(r['admitted'])}")
            print(f"     DROPPED                : {nd}   {dict(r['dropped'])}")
            print(f"     staves with any clef detection in cell 0: "
                  f"{r['staves_with_a_clef_detection']}")
            print(f"     STAVES STARVED (0 admitted, >=1 dropped) : "
                  f"{len(r['starved'])}")
            print(f"     ... a PITCHED clef would rescue           : "
                  f"{len(r['rescuable'])}")
            for k, v in sorted(r["rescuable"].items()):
                print(f"         staff p{k[0]}/s{k[1]}/st{k[2]}  "
                      f"dropped={dict(v['dropped'])}")
            if arm == "INCUMBENT":
                print(f"     (later cells, reported apart, NOT this lane): "
                      f"{sum(r['later_cell'].values())} {dict(r['later_cell'])}")
        print()

    # ⚠️ POSITIVE CONTROL. A probe that reads nothing and a record that holds
    # nothing look identical. If not one clef row was ADMITTED anywhere, this
    # probe is not reading the record and every zero below it is void.
    if not total_admitted:
        print("PROBE DEAD: zero clef rows admitted across every record read.")
        return 2
    print(f"positive control: {total_admitted} clef rows admitted -- probe is live.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
