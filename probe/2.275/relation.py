"""2.275: the chain from the overnight's `notes_not_written` (4,440 / 11,044) to distinct ink not in the file (1,439 / 5,035).
usage: relation.py PLATE SUMMARY.json PART.rows.jsonl INK.json"""
import collections
import json
import sys

plate, summ, rows_p, ink_p = sys.argv[1:5]
s = json.load(open(summ))
rows = [json.loads(l) for l in open(rows_p)]
ink = json.load(open(ink_p))
nnw = s["notes_not_written"]
tot = sum(nnw.values())
fate_nw = collections.Counter(r["fate"] for r in rows if r["fate"] not in ("written", "written_relocated"))
box_nw = sum(fate_nw.values())
# dict keys that are not notehead-box fates: rests refused, etc.
extra = {k: v for k, v in nnw.items() if k not in fate_nw or fate_nw[k] != v}
print(plate)
print(" notes_not_written total (report dict)           ", tot)
print(" of which notehead-classed boxes not written      ", box_nw)
print(" dict entries that are not box fates (rest/other) ", tot - box_nw, extra if len(extra) < 12 else len(extra))
partial = sum(1 for r in rows if r["fate"] in ("written", "written_relocated") and r["partial_cell"] and not r["held_cell"])
print(" notehead boxes written but in a bar with a red gap", partial, "(counted as written, as in 2.167)")
print(" boxes total", len(rows), "ink clusters", ink["clusters"], "ink in file", ink["ink_in_file"],
      "extra copies riding with written ink", ink["boxes_in_written_clusters"] - ink["ink_in_file"])
in_written_cluster_nw = box_nw - sum(ink["boxes_of_ink_not_in_file"].values())
print(" not-written boxes whose ink IS in the file (copies)", in_written_cluster_nw)
print(" not-written boxes whose ink is NOT in the file      ", sum(ink["boxes_of_ink_not_in_file"].values()),
      "= distinct ink", sum(ink["ink_not_in_file"].values()), "(+", ink["gap_rows_unlocatable"], "heads in red gaps)")
