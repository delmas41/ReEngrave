"""ROADMAP 2.162 -- derive every consumer of a BAR'S LENGTH from the code (no hand list).

SEEDS: functions (STAGED, tools/omr/staged/*.py + adjudicators/*.py) whose body reads `Q.DURATION` verdicts AND adds their
`beats` into a total -- i.e. that compute a bar's length from its notes. CONSUMERS: every function that (transitively) calls a
seed, plus every function that takes a seed's output (`bars`, a {cell: [length per staff]} dict) as an argument. Each line
says whether the function reads a NARROWED note's `.candidates` itself.
usage: python3 benchmarks/omr-bar-sum-holdout-2026-09/probe/consumers_2_162.py"""
import ast
import glob
import os

ROOT = "tools/omr/staged"
files = sorted(glob.glob(ROOT + "/*.py") + glob.glob(ROOT + "/adjudicators/*.py") + glob.glob(ROOT + "/review/*.py"))
defs, calls, srcs = {}, {}, {}
for f in files:
    text = open(f).read()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            defs.setdefault(node.name, []).append(f)
            srcs[node.name] = (srcs.get(node.name, "") + (ast.get_source_segment(text, node) or ""))
            cs = calls.setdefault(node.name, set())
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    fn = sub.func
                    cs.add(fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", ""))
            if any(a.arg == "bars" for a in node.args.args):
                calls[node.name].add("<bars>")


def is_seed(src):
    return "Q.DURATION" in src and "beats" in src and any(k in src for k in ("total +=", "total = total", "fixed = fixed +"))


seeds = {n for n, s in srcs.items() if is_seed(s)}
# `_event_totals` is handed `current` (the values) and does the adding for its callers: a seed by the same test minus the read
seeds |= {n for n, s in srcs.items() if "total +=" in s and "beats" in s and "current[" in s}
# 2.162/2.165: THE helper (`staged.bar_length`) and whatever calls it are seeds too, so the list survives the refactor
seeds |= {"length_of_events", "bar_length"} | {n for n, cs in calls.items() if cs & {"length_of_events", "bar_length"}}
consumers = set(seeds) | {"<bars>"}
grew = True
while grew:
    grew = False
    for name, cs in calls.items():
        if name not in consumers and cs & consumers:
            consumers.add(name)
            grew = True
consumers.discard("<bars>")


def row(n):
    s = srcs.get(n, "")
    tag = "reads .candidates" if ".candidates" in s else ""
    return "  %-38s %-28s %s" % (n, ", ".join(os.path.relpath(x, ROOT) for x in defs[n]), tag)


LENGTH_READERS = ("_bar_beats_at", "_bar_quarters", "meter_at")
print("BAR-LENGTH READERS (compare something with the meter's length at a bar):")
for n in sorted(k for k, cs in calls.items() if cs & set(LENGTH_READERS) and k not in LENGTH_READERS):
    print(row(n) + ("  [also sums the bar]" if n in seeds or calls[n] & seeds else ""))
print("SEEDS (sum a bar's durations):")
for n in sorted(seeds):
    print(row(n))
print("CONSUMERS (call a seed transitively, or take its `bars`):")
for n in sorted(consumers - seeds):
    print(row(n))
