"""Verdicts compared by (quantity, subject) -- ids, basis and timing ignored -- so a row-count shift upstream (an OCR
word filed in one arm only) does not cascade into every later row (ROADMAP 2.249; reads only).

usage: by_subject_diff.py A.record.json B.record.json [--no-ids]
Prints per quantity how many (quantity, subject) verdicts differ in outcome/value/reason, and every differing one
for quantities with few differences.
"""
import json, sys
from collections import defaultdict
import re
import ijson

NO_IDS = "--no-ids" in sys.argv
sys.argv = [x for x in sys.argv if x != "--no-ids"]
ID = re.compile(r'"(obs|abs|vrd):\d+"')


def load(path):
    out = {}
    with open(path, "rb") as fh:
        for v in ijson.items(fh, "record.verdicts.item", use_float=True):
            val = json.dumps(v["value"], sort_keys=True, default=str)
            if NO_IDS:     # a row id in a value names a row, not a reading: an id shift upstream renumbers it
                val = ID.sub("<id>", val)
            out[(v["quantity"], v["subject"])] = (v["outcome"], val, v.get("reason"))
    return out


a, b = load(sys.argv[1]), load(sys.argv[2])
by_q = defaultdict(list)
for k in set(a) | set(b):
    if a.get(k) != b.get(k):
        by_q[k[0]].append((k[1], a.get(k), b.get(k)))
print(f"verdicts A {len(a)}  B {len(b)}  differing (quantity, subject): {sum(len(v) for v in by_q.values())}")
for q, rows in sorted(by_q.items(), key=lambda kv: -len(kv[1])):
    print(f"{q}: {len(rows)}")
    for s, x, y in sorted(rows)[:12]:
        print(f"    {s}: {x} -> {y}"[:400])
