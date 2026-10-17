"""ROADMAP 2.158 -- why a named bar is or is not guessed: replay a slice (flag ON) through EVALUATE, stopping before INFER,
then print `lone_event_decline` and the solver's own `solve_bare_stem_bar(any_reason=True)` decline for each CELL.
usage: why_2_158.py SLICE.json cell/p/s/st/c [cell/...]"""
import json
import os
import sys

sys.path.insert(0, ".")
os.environ["OMR_LONE_EVENT_FILLS_BAR"] = "1"
from tools.omr.staged import inferences, pipeline  # noqa: E402
from tools.omr.staged.record import Subject  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

raw = json.load(open(sys.argv[1]))
rec = raw.get("record", raw)
log, _ = RR.rebuild_gather(rec)
seen = {}
orig = inferences.collapse_narrowed_by_bar.__wrapped__ if hasattr(inferences.collapse_narrowed_by_bar, "__wrapped__") else None
want = set(sys.argv[2:])
_solve = inferences.solve_bare_stem_bar


def spy(lg, cell, **kw):
    out = _solve(lg, cell, **kw)
    k = cell.to_key()
    if k in want and kw.get("any_reason"):
        seen[k] = dict(lone=inferences.lone_event_decline(lg, cell), solver=out.decline, landings=out.landings,
                       forced=out.forced, ambiguous=out.ambiguous, lengthening_unwitnessed=out.lengthening_unwitnessed,
                       proposals=[(p.subject.to_key(), p.value.get("beats")) for p in out.proposals or []])
    return out


inferences.solve_bare_stem_bar = spy
pipeline.decide(log)
for k in sys.argv[2:]:
    print(k, seen.get(k, "solver never asked (EVALUATE settled it, or no narrowing reached INFER)"))
