"""ROADMAP 2.313 -- heads refused in arm A (no page 1) and not refused in arm B (page 1 loaded): their fate in B and A's own reason (reads only).

    python3 benchmarks/landing-check-2026-11/newly_refused.py PAGES A.facts.json A.record.json B.facts.json B.record.json [SEED N]

A seeded sample of N (default 15) of those heads: glyph key, fate in B, the reason A's duration verdict gives, and whether A's bar is a red bar there.
"""
import collections
import json
import random
import sys

from tools.omr.staged.record_io import load_record

REF = ("duration_narrowed", "chord_value_undecided")
pages = {int(x) for x in sys.argv[1].split(",")}
fa, fb = json.load(open(sys.argv[2])), json.load(open(sys.argv[4]))
seed = int(sys.argv[6]) if len(sys.argv) > 6 else 2313
n = int(sys.argv[7]) if len(sys.argv) > 7 else 15


def refused(f):
    return {k for k, g in f["glyphs"].items() if len(k.split("/")) == 6 and g.get("head") and g.get("fate") in REF and int(k.split("/")[1]) in pages}


ra, rb = refused(fa), refused(fb)
new = sorted(ra - rb)
print("refused in A %d, in B %d, in A only %d, in B only %d" % (len(ra), len(rb), len(new), len(rb - ra)))
dur = {}
for v in load_record(sys.argv[3])["record"]["verdicts"]:
    if v["quantity"] == "duration":
        dur[v["subject"]] = v
print("fate of those heads in B:", collections.Counter(fb["glyphs"][k].get("fate") for k in new).most_common())
print("A's duration reason:", collections.Counter((dur[k].get("reason"), dur[k].get("outcome")) for k in new if k in dur).most_common())
random.Random(seed).shuffle(new)
for k in new[:n]:
    d = dur.get(k) or {}
    print(k, "| B:", fb["glyphs"][k].get("fate"), "| A reason:", d.get("reason"), "| cands", [c.get("value") for c in (d.get("candidates") or [])][:3])
