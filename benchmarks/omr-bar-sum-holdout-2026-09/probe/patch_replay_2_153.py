"""one-off: point the 2.153 probes at replay_util_2_153.rebuild (id-faithful slice replay)."""
import os

D = "benchmarks/omr-bar-sum-holdout-2026-09/probe/"
for f in ("attribute_2_153.py", "tag_notes_2_153.py", "diffdetail_2_153.py"):
    s = open(D + f).read()
    if "replay_util_2_153" in s:
        continue
    s = s.replace("RR.rebuild_gather(rec)", "RU.rebuild(rec)")
    s = s.replace("from tools.omr.staged.review import rerun as RR  # noqa: E402\n",
                  "from tools.omr.staged.review import rerun as RR  # noqa: E402\n"
                  "sys.path.insert(0, \"benchmarks/omr-bar-sum-holdout-2026-09/probe\")\n"
                  "import replay_util_2_153 as RU  # noqa: E402\n", 1)
    open(D + f, "w").write(s)
    print(f, s.count("RU."))
