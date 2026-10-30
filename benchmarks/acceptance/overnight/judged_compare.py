"""Sean's judged tiles on two records, ONE scorer, ONE index (rule 4, rule 7, CLAUDE.md section 6).

Both records are scored here, now, by the tree this runs in -- the BASE is re-scored, never
quoted from its own night's README, because the scorer moves (d51e3967c: written values incl.
blue). Per tile (item, tile) the BASE status is matched to the TAG status:
  right -> wrong   (must be 0)        right -> narrowed / abstained / not_found ("gone")
  wrong -> right                      and the whole status transition table.
Streams the records (tools.omr.staged.judged), so a Brahms record is safe to score.

python3 judged_compare.py BASE.record.json TAG.record.json litolff|brahms [--json OUT]
"""
import argparse
import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3]))
from tools.omr.staged import judged as J            # noqa: E402
from tools.omr.staged import lane_report as L       # noqa: E402

STAT = ("right", "wrong", "narrowed", "abstained", "not_found", "unscored")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("tag")
    ap.add_argument("doc", choices=("litolff", "brahms"))
    ap.add_argument("--json")
    a = ap.parse_args()
    idx = json.loads(J.INDEX_PATH.read_text())
    sa = J.score(idx, pathlib.Path(a.base), a.doc)
    sb = J.score(idx, pathlib.Path(a.tag), a.doc)
    mv = L.compare_judged(sa["tiles"], sb["tiles"])
    by_b = {(t["item"], t["tile"]): t for t in sb["tiles"]}
    trans = collections.Counter()
    for t in sa["tiles"]:
        u = by_b.get((t["item"], t["tile"]))
        if u is not None:
            trans[(t["status"], u["status"])] += 1
    print("judged tiles, %s, today's scorer on BOTH records (index %d tiles)" % (a.doc, idx["n_tiles"]))
    print("  %-8s" % "" + "".join("%11s" % s for s in STAT))
    for name, rep in (("BASE", sa), ("TAG", sb)):
        print("  %-8s" % name + "".join("%11d" % rep["totals"].get(s, 0) for s in STAT))
    print("  right/wrong/narrowed  BASE %d/%d/%d  ->  TAG %d/%d/%d" % (
        sa["totals"].get("right", 0), sa["totals"].get("wrong", 0), sa["totals"].get("narrowed", 0),
        sb["totals"].get("right", 0), sb["totals"].get("wrong", 0), sb["totals"].get("narrowed", 0)))
    print("  moves: right->wrong %d (must be 0) | right->gone %d | wrong->right %d | "
          "unwritten->wrong %d | unwritten->right %d | tiles scored on both %d" % (
              len(mv["worse"]), len(mv["lost"]), len(mv["better"]), len(mv["unwritten_wrong"]),
              len(mv["unwritten_right"]), mv["scored"]))
    print("  status transitions that are not 'same' (BASE -> TAG: n):")
    for (x, y), n in sorted(trans.items(), key=lambda kv: -kv[1]):
        if x != y:
            print("    %-10s -> %-10s %d" % (x, y, n))
    for key, title in (("worse", "RIGHT -> WRONG"), ("lost", "RIGHT -> GONE"), ("better", "WRONG -> RIGHT"),
                       ("unwritten_wrong", "UNWRITTEN -> WRONG")):
        rows = mv[key]
        print("  %s (%d)%s" % (title, len(rows), ":" if rows else ""))
        for r in rows[:40]:
            print("    %-26s tile %-4s %s %s" % (r["item"], r["tile"], r["subject"],
                                                 r.get("now") or r.get("answer") or ""))
        if len(rows) > 40:
            print("    ... %d more (see --json)" % (len(rows) - 40))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(dict(
            doc=a.doc, base=sa["totals"], tag=sb["totals"], moves=mv,
            transitions={"%s->%s" % k: v for k, v in trans.items()}), indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
