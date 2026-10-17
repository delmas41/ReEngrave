"""ROADMAP 2.155 step 3 -- PROBE for lane 2.154 (read-only): replay a slice faithfully (`replay_util_2_153.rebuild`) under the env the
caller sets (OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM=1) and dump, for the three bars of 2.153 tiles 4/14/16, every duration verdict of every
glyph in the bar (decider, outcome, reason, value, candidates, detail) and every cell/staff/system-scoped verdict whose quantity
mentions the bar sum. usage: barsum_2_155.py SLICE.json OUT.json"""
import json
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
from replay_util_2_153 import rebuild  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

rec = json.load(open(sys.argv[1]))
log, _ = rebuild(rec)
RR.run_stages(log)
out = log.to_json()
CELLS = ("cell/2/1/7/12", "cell/1/0/8/2", "cell/10/1/6/3")
keep = []
for v in out["verdicts"]:
    s = v["subject"]
    if any(s == c or s.startswith(c.replace("cell", "glyph") + "/") or s == c for c in CELLS):
        keep.append(v)
    elif any(s == "/".join(c.split("/")[:4]).replace("cell", "staff") for c in CELLS) or s.startswith("bar/"):
        keep.append(v)
json.dump(keep, open(sys.argv[2], "w"), default=str, indent=0)
print("kept", len(keep))
