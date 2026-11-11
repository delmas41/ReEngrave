"""ROADMAP 2.290 r1 -- READ-ONLY: every head box the export dropped as `mark_group_duplicate` (a MARK_GROUP member, IoU 0.3, whose group-mate was written): does
`Q.PAGE_MARK` (shared ink, ON) agree that it is the SAME mark as that written group-mate? Where it does not, the IoU group may have thrown away a real second head.

    python3 benchmarks/page-heads-ledger-2026-11/mgdup_vs_pagemark.py SLICE_DIR FATES.twin.json PAGES OUT.json
"""
import collections
import json
import sys


def main(slice_dir, fates, pages, out):
    pages = set(int(x) for x in pages.split(","))
    pm = {}
    with open(slice_dir + "/observations.jsonl") as fh:
        for line in fh:
            if '"page_mark"' not in line:
                continue
            o = json.loads(line)
            s = o["subject"]
            if s.startswith("glyph/") and int(s.split("/")[1]) in pages and (o.get("detail") or {}).get("family") == "head":
                pm[s] = (int(s.split("/")[1]), o["value"])
    rows = json.load(open(fates))
    by_group = collections.defaultdict(list)
    for r in rows:
        by_group[r["group"]].append(r)
    c = collections.Counter()
    differ = []
    for r in rows:
        if r["fate"] != "mark_group_duplicate":
            continue
        mates = [q for q in by_group[r["group"]] if q is not r and q["fate"].startswith("written")]
        if not mates:
            c["no_written_mate"] += 1
            continue
        same = any(pm.get(q["sub"]) == pm.get(r["sub"]) and r["sub"] in pm for q in mates)
        c["same_page_mark" if same else "DIFFERENT_page_mark"] += 1
        if not same:
            differ.append(dict(r, mate=mates[0]["sub"], mate_box=mates[0]["box"]))
    print(dict(c))
    json.dump(differ, open(out, "w"))


if __name__ == "__main__":
    main(*sys.argv[1:5])
