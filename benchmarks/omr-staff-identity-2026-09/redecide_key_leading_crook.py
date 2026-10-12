"""ROADMAP 2.94 -- does reading a LEADING crook (`(C) Hr.` -> 0, was the
horn default 1) move any key verdict? Base vs arm on ONE tree: the base arm
forces `instruments.parse_leading_crook` to None (the old behaviour).

GATHER+ADJUDICATE only, through `key_signature` in `adjudicate.ORDER`.

    python3 redecide_key_leading_crook.py RECORD
"""
from __future__ import annotations

import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr import instruments as I                           # noqa: E402
from tools.omr.staged import adjudicate, adjudicators            # noqa: E402,F401
from tools.omr.staged.record import Log, Q, Subject             # noqa: E402
from tools.omr.staged.record_io import load_record               # noqa: E402

THROUGH = "key_signature"
KEYS = (Q.SYSTEM_KEY, Q.PART_KEY, Q.KEY_SIGNATURE, Q.INSTRUMENT)


def rebuild(rec):
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
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


def run(rec):
    log = rebuild(rec)
    order = adjudicate.ORDER[:adjudicate.ORDER.index(THROUGH) + 1]
    adjudicate.run(log, order=order)
    out = {}
    for v in log.all_verdicts():
        if v.quantity in KEYS:
            out[(v.quantity, str(v.subject))] = (v.outcome.value,
                                                 repr(v.value), v.reason)
    return out


def main(path):
    rec = load_record(path)["record"]
    real = I.parse_leading_crook
    I.parse_leading_crook = lambda text: None
    base = run(rec)
    I.parse_leading_crook = real
    arm = run(rec)
    print("verdicts compared:", len(base), len(arm))
    by_q = collections.Counter(k[0] for k in base)
    print("by quantity:", dict(by_q))
    changed = [(k, base.get(k), arm.get(k)) for k in set(base) | set(arm)
               if base.get(k) != arm.get(k)]
    print("changed:", len(changed))
    for k, b, a in sorted(changed, key=str)[:60]:
        print("  ", k, b, "->", a)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
