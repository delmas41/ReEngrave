#!/usr/bin/env python3
"""lud_partition: the exclusive partition of kept -> narrowed (and narrowed -> kept) notes by the item(s) whose
guard input newly differs. Same tags as lud_rollup.py, summed over every reason word."""
import collections
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lud_rollup import tags  # noqa: E402
import re

out = []
for doc in ("brahms1-breitkopf", "beethoven5-litolff"):
    rows = list(csv.DictReader(open(HERE.parent / "undecided" / f"changed-notes-{doc}.csv")))
    k2n = [r for r in rows if r["kind"] == "kept_to_narrowed"]
    n2k = [r for r in rows if r["kind"] == "narrowed_to_kept"]
    c = collections.Counter(" + ".join(sorted(t.split(" (")[0] for t in tags(r))) or "none differs" for r in k2n)
    out.append(f"{doc}: kept -> narrowed {len(k2n)} (exclusive partition by item whose guard input differs)")
    for k, n in c.most_common():
        out.append(f"   {n:5d}  {100 * n / len(k2n):5.1f}%  {k}")
    c2 = collections.Counter()
    for r in n2k:
        m = re.match(r"^tonight decided by `(\w+)`", r["what_changed"])
        now = m.group(1) if m else r["tonight_reason"]
        t = " + ".join(sorted(x.split(" (")[0] for x in tags(r))) or "none differs"
        c2[(now if now in ("hooks_counted", "hollow_head_bare_stem") else "head_and_marks via " + t)] += 1
    out.append(f"{doc}: narrowed -> kept {len(n2k)}")
    for k, n in c2.most_common():
        out.append(f"   {n:5d}  {100 * n / len(n2k):5.1f}%  {k}")
    out.append("")
txt = "\n".join(out)
(HERE.parent / "undecided" / "partition.txt").write_text(txt + "\n")
print(txt)
