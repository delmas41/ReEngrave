"""2.306 r14: on Sean's swept Brahms p0 heads (r14_flag_tally.py rows), how many have their value read from a FLAG on their own stem (duration
detail: a flag attached, no beam joined to the stem, no certain beam level) -- by what he labelled (flag / beam) and how they are written now.
A rule "a note whose stem carries a flag is never beamed" may only move rows whose flag he labelled. Usage: r14_flag_rule_check.py REC.json TALLY.json"""
import collections
import json
import sys

from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1])["record"]
rows = [r for r in json.load(open(sys.argv[2])) if r.get("rg")]
dur = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "duration"}


def flagged(d):
    return bool(d.get("flags_attached")) and not d.get("beams_by_stem") and not d.get("levels_certain")


c = collections.Counter()
for r in rows:
    v = dur.get(r["rg"])
    d = (v or {}).get("detail") or {}
    c[(r["kind"], r["what"], r["why"].split(" (")[0][:40], "FLAG-READ" if flagged(d) else "not")] += 1
for k, n in sorted(c.items()):
    print(n, k)
