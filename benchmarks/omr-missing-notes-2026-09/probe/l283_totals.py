#!/usr/bin/env python3
"""l283_totals: the `l283_compare.py` outputs (`probe/out/l283/compare_*.txt`) summed over every page the arm re-gathered: heads, duration
verdicts changed, the transitions, the 2.81 population P and what its members became, per movement. Reads the committed text, re-derives
nothing. ROADMAP 2.83 probe.

    python3 l283_totals.py probe/out/l283
"""
import collections
import re
import sys
from pathlib import Path

GROUPS = {"brahms": ["compare_brahms_count_pages", "compare_brahms-t1", "compare_brahms-t2", "compare_brahms-t3", "compare_brahms-t4"],
          "litolff": ["compare_litolff_count_pages", "compare_litolff-t"]}


def main():
    d = Path(sys.argv[1])
    for mv, files in GROUPS.items():
        heads = changed = 0
        trans = collections.Counter()
        p = collections.Counter()
        p_total = 0
        for f in files:
            txt = (d / (f + ".txt")).read_text()
            m = re.search(r"in both (\d+) ", txt)
            heads += int(m.group(1))
            m = re.search(r"duration verdicts changed \(matched heads\): (\d+) of", txt)
            changed += int(m.group(1))
            for n, a, b in re.findall(r"^\s+(\d+)\s+(\S+)\s+->\s+(\S+)\s*$", txt, flags=re.M):
                trans[(a, b)] += int(n)
            m = re.search(r"population P \(base beam_discounted_uncertain, kept by ADJUDICATE\): (\d+)", txt)
            p_total += int(m.group(1))
            block = txt.split("kept by ADJUDICATE):")[1].split("(status")[0].split("\n", 1)[1]
            for n, what in re.findall(r"^[ \t]+(\d+)[ \t]+(.+)$", block, flags=re.M):
                p[what.strip()] += int(n)
        print(f"== {mv}: heads with a duration verdict {heads}, CHANGED {changed}")
        for (a, b), n in trans.most_common():
            print(f"   {n:4d}  {a}  ->  {b}")
        print(f"   P (base beam_discounted_uncertain, kept) {p_total}:")
        for what, n in p.most_common():
            print(f"      {n:4d}  {what}")


if __name__ == "__main__":
    main()
