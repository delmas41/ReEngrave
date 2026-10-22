"""ROADMAP 2.94 -- re-decide `adjudicate_instrument` over a committed record,
base vs arm on ONE tree.

GATHER+ADJUDICATE only, and only this decision: it reads the
`Q.MARGIN_LABEL` / `Q.ROSTER_ENTRY` / `Q.STAFF_*` rows, so the record is
filtered to those quantities before the rebuild. Base = `recover_worn` forced
to return None; arm = the code as it stands. Same process, same tree.

    python3 benchmarks/omr-staff-identity-2026-09/readjudicate_worn_label.py REC [REC...]

Prints, per record: staves, named before/after, the reasons that abstained
before/after, and every staff whose NAME changed (must be only the
abstained -> named ones; a named -> other change is a defect).
"""
from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr import work_roster as WR                         # noqa: E402
from tools.omr.staged import adjudicate                         # noqa: E402
from tools.omr.staged import adjudicators                       # noqa: E402,F401
from tools.omr.staged.record import Kind, Log, Q, Subject       # noqa: E402
from tools.omr.staged.record_io import load_record              # noqa: E402

KEEP = {Q.MARGIN_LABEL, Q.ROSTER_ENTRY, Q.STAFF_ORDINAL, Q.STAFF_GROUP}


def rebuild(rec: dict) -> Log:
    log = Log()
    rows = [(r, "obs") for r in rec["observations"] if r["quantity"] in KEEP]
    rows += [(r, "abs") for r in rec.get("abstentions", [])
             if r["quantity"] in KEEP]
    rows.sort(key=lambda t: t[0]["id"])
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)
    return log


def decide_all(log: Log) -> dict:
    spec = adjudicate.REGISTRY[Q.INSTRUMENT]
    out = {}
    for sub in adjudicate.subjects_for(log, spec):
        v = adjudicate.adjudicate_one(log, spec, sub)
        out[str(sub)] = (v.outcome.value,
                         (v.value or {}).get("name") if v.value else None,
                         v.reason)
    return out


def main(paths) -> int:
    real = WR.recover_worn
    for p in paths:
        rec = load_record(p)["record"]
        WR.recover_worn = lambda *a, **k: None
        base = decide_all(rebuild(rec))     # a Log refuses a 2nd verdict
        WR.recover_worn = real
        arm = decide_all(rebuild(rec))
        print("==", pathlib.Path(p).name, "staves", len(base))
        for tag, d in (("base", base), ("arm", arm)):
            named = sum(1 for v in d.values() if v[1])
            why = collections.Counter(v[2] for v in d.values() if not v[1])
            print(f"  {tag}: named {named}  abstained {dict(why)}")
        changed = [(k, base[k], arm[k]) for k in base if base[k] != arm[k]]
        print(f"  changed: {len(changed)}")
        for k, b, a in changed:
            print("   ", k, b, "->", a)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
