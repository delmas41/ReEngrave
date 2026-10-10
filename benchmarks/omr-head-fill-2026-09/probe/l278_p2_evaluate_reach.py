"""ROADMAP 2.78 -- REACH of EVALUATE's `share_stem_value`, printed before anything is claimed about it.

PATH: STAGED. A saved record's GATHER rows are replayed (`review.rerun.rebuild_gather`), ADJUDICATE and
then EVALUATE are run with the CURRENT tree. This is a REACH print (CLAUDE.md rule 5: an arm prints its
population first and declares itself DEAD at zero), not an accuracy measurement: CLAUDE.md §6b makes every
test GATHER+ADJUDICATE only until further notice, and nothing here is scored against a reference.

    python3 benchmarks/omr-head-fill-2026-09/probe/l278_p2_evaluate_reach.py LABEL RECORD.json [--dead-ok]

Prints, for the record: how many heads carry a DECIDED stem value, how many `share_stem_value` firings
there were, split into (a) a DECIDED duration restated to a different DECIDED stem value and (b) a NARROWED
duration settled to the stem's value, and the (written, dots, beam_levels) transitions. Exits 3 -- DEAD --
when the rule fired zero times, unless `--dead-ok` (the engraved control, where near-zero is the EXPECTED
reading and the exit code is not the point).
"""
from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.getcwd())


def _w(v):
    val = v.get("value") if isinstance(v, dict) else v.value
    if not isinstance(val, dict):
        return None
    return (val.get("written"), val.get("dots"), val.get("beam_levels"))


def main(argv):
    label, path = argv[1], argv[2]
    dead_ok = "--dead-ok" in argv
    from tools.omr.staged import adjudicate, adjudicators, consequences, evaluate  # noqa: F401
    from tools.omr.staged.record import Outcome, Q
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun

    rec = load_record(path)["record"]
    log, _ = rerun.rebuild_gather(rec)
    adjudicate.run(log)

    subjects = sorted({v.subject for v in log.all_verdicts() if v.quantity == Q.DURATION},
                      key=str)
    before = {str(s): log.verdict(Q.DURATION, s) for s in subjects}

    sv_decided = sv_narrowed = sv_other = 0
    for v in log.all_verdicts():
        if v.quantity == Q.STEM_VALUE:
            if v.outcome is Outcome.DECIDED:
                sv_decided += 1
            elif v.outcome is Outcome.NARROWED:
                sv_narrowed += 1
            else:
                sv_other += 1

    def stem_table():
        """Stems with >= 2 joined heads, classed by their heads' STANDING durations."""
        members = collections.defaultdict(list)
        excluded = 0
        for s in subjects:
            j = log.verdict(Q.HEAD_STEM, s)
            if j is not None and j.outcome is Outcome.DECIDED and isinstance(j.value, str):
                sv = log.verdict(Q.STEM_VALUE, s)
                # ⚠️ A refused box (or another staff's copy) is JOINED to the stem but is not a MEMBER:
                # the stem decision files `not_a_member` for it, EXPORT never writes it, and it must
                # not be counted as a head that disagrees.
                if sv is not None and sv.reason == "not_a_member":
                    excluded += 1
                    continue
                members[j.value].append(s)
        out = collections.Counter()
        out["(joined heads excluded as not_a_member)"] = excluded
        left = []
        for stem, subs in members.items():
            if len(subs) < 2:
                continue
            vs = [log.verdict(Q.DURATION, s) for s in subs]
            if any(v is None or v.outcome is not Outcome.DECIDED for v in vs):
                out["unsettled (a head narrowed/abstained)"] += 1
                continue
            if len({_w(v) for v in vs}) == 1:
                out["agree (all decided, one value)"] += 1
            else:
                out["DISAGREE (decided heads differ)"] += 1
                left.append((stem, sorted(_w(v) for v in vs)))
        return out, left

    tbl_before, _ = stem_table()
    rep = evaluate.run(log)
    fired = [f for f in rep.fired if f[0] == "share_stem_value"]
    tbl_after, left = stem_table()

    after = {str(s): log.verdict(Q.DURATION, s) for s in subjects}

    kinds = collections.Counter()
    transitions = collections.Counter()
    for sub, a in after.items():
        if getattr(a, "decider", None) != "share_stem_value":
            continue
        b = before.get(sub)
        was = b.outcome.value if b is not None else "none"
        kinds["decided_restated" if was == "decided" else f"{was}_settled"] += 1
        if was == "decided":
            transitions[(_w(b), _w(a))] += 1
        else:
            transitions[(f"{was}", _w(a))] += 1

    print(f"== {label}: {path.split('/')[-1]}")
    print(f"   stem values: decided {sv_decided}, narrowed {sv_narrowed}, other {sv_other}")
    print(f"   share_stem_value firings: {len(fired)}   by kind: {dict(kinds)}")
    for (a, b), n in transitions.most_common(12):
        print(f"      {n:4d}  {a} -> {b}")
    print(f"   stems with >=2 joined heads, by their heads' STANDING durations")
    print(f"      after ADJUDICATE : {dict(tbl_before)}")
    print(f"      after EVALUATE   : {dict(tbl_after)}")
    for stem, vals in left:
        print(f"      still disagreeing: {stem}  {vals}")
    if not fired and not dead_ok:
        print("   DEAD: the rule fired zero times on a record that holds multi-head stems", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
