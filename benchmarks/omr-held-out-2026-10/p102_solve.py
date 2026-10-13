"""ROADMAP 2.102 probe: re-run `solve_bare_stem_bar` over one saved record's cells.

INFER-only replay (no gather, no adjudicate): the record's rows minus every
verdict an `infer:` rule filed, so the rule under test is the only variable.

    python3 benchmarks/omr-held-out-2026-10/p102_solve.py REC [cell/p/s/st/c ...]
No cells = every cell holding a bare-stem member; prints a one-line count.
"""
import collections
import importlib.util
import sys

sys.path.insert(0, ".")
spec = importlib.util.spec_from_file_location(
    "reinfer", "benchmarks/omr-infer-stage-2026-09/reinfer.py")
reinfer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reinfer)

import os  # noqa: E402

from tools.omr.staged import inferences  # noqa: E402

if os.environ.get("P102_BASELINE"):          # the rule as it was before 2.102
    inferences.bar_has_tuplet = lambda log, cell: ()
    inferences._simultaneous_heads = lambda log, cell, events: False
    inferences._tuplet_world_lengths = lambda seq, **kw: {}
from tools.omr.staged.record import Kind, Subject  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402


def load_log(path):
    doc = load_record(path)
    rec = doc["record"] if "record" in doc else doc
    rec = dict(rec)
    inferred_ids = {v["id"] for v in rec["verdicts"]
                    if str(v["decider"]).startswith("infer:")}
    rec["verdicts"] = [v for v in rec["verdicts"] if v["id"] not in inferred_ids]
    return rec, reinfer.rebuild(rec)


def cells_with_members(rec):
    out = set()
    for v in rec["verdicts"]:
        if (v["quantity"] == "duration" and v["outcome"] == "narrowed"
                and v["reason"] == inferences.BARE_STEM_REASON):
            out.add("/".join(v["subject"].split("/")[1:5]))
    return sorted("cell/" + c for c in out)


def settle(log, cell_key):
    cell = Subject.from_key(cell_key)
    return inferences.solve_bare_stem_bar(log, cell)


if __name__ == "__main__":
    rec, log = load_log(sys.argv[1])
    cells = sys.argv[2:] or cells_with_members(rec)
    tally = collections.Counter()
    for c in cells:
        o = settle(log, c)
        n = len(o.proposals or [])
        tally["cells"] += 1
        tally["settled_members"] += n
        if n:
            tally["cells_settling"] += 1
        tally["tuplet_possible"] += o.tuplet_possible
        if o.decline:
            tally["decline:" + str(o.decline)] += 1
        if len(sys.argv) > 2:
            print(c, "members", o.members, "proposals", n, "decline", o.decline)
    print(dict(tally))
