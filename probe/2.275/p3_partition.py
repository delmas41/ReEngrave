"""2.167 probe 3 (PART 2): partition every notehead-classed box of a record by its FIRST cause, from the rows file p1_table.py
wrote. Buckets are mutually exclusive, so they SUM to the box count (the control, which raises if it does not).

  WRITTEN            reached a kept bar of the file
  refused:<fate>     the exporter's own first refusal (its checks run in a fixed order; `fates` is the exporter's own record)
  held_bar_sum       reached a bar, but the bar is held out because its durations do not sum to the meter
  partial_bar_cell   in a bar rendered with a red unread gap (which heads sit in the gap is not recorded)

Each non-written box then gets a TWIN state (another notehead box on the same ink, IoU > 0.3, any staff):
  twin_kept   the twin is WRITTEN in a kept bar  -> this box is a copy of ink that IS in the file (not a lost note)
  twin_held   the twin sits in a held / partial bar
  twin_lost   the twin is itself refused
  no_twin     nothing overlaps it
and Sean's judged answer on a tile of this very box where one exists (judged-tiles.json): note / rest / not_a_note / other.

usage: python3 probe/2.167/p3_partition.py ROWS.jsonl DOC OUT.json
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
rows_path, doc, out_path = sys.argv[1:4]
rows = [json.loads(l) for l in open(rows_path)]

J = json.load(open(ROOT / "benchmarks/acceptance/judged-tiles.json"))["tiles"]
judged = collections.defaultdict(list)
for t in J:
    if t.get("subject") and t["subject"].startswith("glyph/") and t.get("doc") in (doc, None):
        judged[t["subject"]].append(t)


def judged_class(sub):
    js = judged.get(sub)
    if not js:
        return "none"
    k = js[-1]["answer_kind"]
    return {"duration": "note", "duration_multi": "note", "rest": "rest", "not_a_note": "not_a_note"}.get(k, "other")


def iou(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def bucket(r):
    if r["fate"] in ("written", "written_relocated"):
        return "held_bar_sum" if r["held_cell"] else "partial_bar_cell" if r["partial_cell"] else "WRITTEN"
    return "refused:" + r["fate"]


for r in rows:
    r["bucket"] = bucket(r)
grid = collections.defaultdict(list)
for r in rows:
    b = r["bbox"]
    grid[(r["sub"].split("/")[1], int(b[0] // 100), int(b[1] // 100))].append(r)


def twin_state(r):
    b = r["bbox"]
    pg = r["sub"].split("/")[1]
    best = (0.0, None)
    for gx in (int(b[0] // 100) - 1, int(b[0] // 100), int(b[0] // 100) + 1):
        for gy in (int(b[1] // 100) - 1, int(b[1] // 100), int(b[1] // 100) + 1):
            for w in grid.get((pg, gx, gy), ()):
                if w["sub"] == r["sub"]:
                    continue
                i = iou(b, w["bbox"])
                # prefer a WRITTEN twin over a refused one when several overlap
                rank = (w["bucket"] == "WRITTEN", i)
                if i > 0.3 and (best[1] is None or rank > (best[1]["bucket"] == "WRITTEN", best[0])):
                    best = (i, w)
    w = best[1]
    if w is None:
        return "no_twin"
    if w["bucket"] == "WRITTEN":
        return "twin_kept"
    if w["bucket"] in ("held_bar_sum", "partial_bar_cell"):
        return "twin_held"
    return "twin_lost"


tally = collections.Counter(r["bucket"] for r in rows)
assert sum(tally.values()) == len(rows)
tab = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    if r["bucket"] == "WRITTEN":
        continue
    ts = twin_state(r)
    r["twin"] = ts
    r["judged"] = judged_class(r["sub"])
    tab[r["bucket"]][ts] += 1
    tab[r["bucket"]]["judged_" + r["judged"]] += 1
unwritten = sum(v for k, v in tally.items() if k != "WRITTEN")
chk = sum(sum(c[t] for t in ("twin_kept", "twin_held", "twin_lost", "no_twin")) for c in tab.values())
assert chk == unwritten, (chk, unwritten)
out = {"doc": doc, "n_boxes": len(rows), "written": tally["WRITTEN"], "unwritten": unwritten,
       "tally": dict(tally), "by_bucket": {k: dict(v) for k, v in tab.items()}}
Path(out_path).write_text(json.dumps(out, indent=1))
print("%s boxes %d  written %d  unwritten %d  (sum check ok)" % (doc, len(rows), tally["WRITTEN"], unwritten))
print("%-52s %6s | %9s %9s %9s %9s | judged: note rest not_a_note other" % ("first cause", "n", "twin_kept", "twin_held",
                                                                           "twin_lost", "no_twin"))
for k, n in sorted(tally.items(), key=lambda kv: -kv[1]):
    if k == "WRITTEN":
        continue
    c = tab[k]
    print("%-52s %6d | %9d %9d %9d %9d | %d %d %d %d" % (
        k, n, c["twin_kept"], c["twin_held"], c["twin_lost"], c["no_twin"], c["judged_note"], c["judged_rest"],
        c["judged_not_a_note"], c["judged_other"]))
# save the annotated rows for the crop step
with open(out_path.replace(".json", ".rows.jsonl"), "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
