"""2.167 probe 3b: the same partition at the level of INK, not boxes. Boxes that overlap on one page (IoU > 0.3, any staff) are one
piece of ink; if any box of the cluster is WRITTEN in a kept bar the ink is in the file and its other boxes are copies (correctly
refused); otherwise the ink is not in the file and its first cause is that of its most advanced box (rank order below: the
further a box got down the pipeline, the more likely it is the real note). Clusters partition the boxes (sum check raises).

usage: python3 probe/2.167/p3b_ink.py PART.rows.jsonl DOC GAP_ROWS OUT.json
"""
import collections
import json
import sys

rows_path, doc, gap_rows, out_path = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
rows = [json.loads(l) for l in open(rows_path)]
# partial-bar cells: the bar is written, only its red gap (gap_rows rows, unlocatable) is not -> count as written
for r in rows:
    if r["bucket"] == "partial_bar_cell":
        r["bucket"] = "WRITTEN"
RANK = ["held_bar_sum", "refused:chord_value_undecided", "refused:no_pitch", "refused:duration_narrowed",
        "refused:owner_not_read", "refused:mark_group_duplicate", "refused:owned_by_another_staff",
        "refused:ink_is_a_whole_rest", "refused:not_a_notehead:stacked_head_duplicate",
        "refused:not_a_notehead:notehead_is_a_duplicate_box", "refused:not_a_notehead:head_cut_piece",
        "refused:not_a_notehead:clipped_fragment", "refused:not_a_notehead:too_narrow",
        "refused:not_a_notehead:belongs_to_a_nearer_staff", "refused:not_a_notehead:tremolo_slash_crosses_stem",
        "refused:not_a_notehead:on_a_dynamic_letter", "refused:not_a_notehead:is_a_rest_twin",
        "refused:not_a_notehead:is_a_rest_shape", "refused:not_a_notehead:is_a_beam_piece",
        "refused:not_a_notehead:is_a_clef", "refused:not_a_notehead:notehead_in_a_key_signature_slot"]
rank = {k: i for i, k in enumerate(RANK)}
parent = list(range(len(rows)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def iou(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


grid = collections.defaultdict(list)
for i, r in enumerate(rows):
    b = r["bbox"]
    grid[(r["sub"].split("/")[1], int(b[0] // 100), int(b[1] // 100))].append(i)
for i, r in enumerate(rows):
    b = r["bbox"]
    pg = r["sub"].split("/")[1]
    for gx in (int(b[0] // 100) - 1, int(b[0] // 100), int(b[0] // 100) + 1):
        for gy in (int(b[1] // 100) - 1, int(b[1] // 100), int(b[1] // 100) + 1):
            for j in grid.get((pg, gx, gy), ()):
                if j > i and iou(b, rows[j]["bbox"]) > 0.3:
                    parent[find(i)] = find(j)
cl = collections.defaultdict(list)
for i in range(len(rows)):
    cl[find(i)].append(i)
n_boxes = sum(len(v) for v in cl.values())
assert n_boxes == len(rows)
ink_written = 0
boxes_in_written_clusters = 0
lost = collections.Counter()
lost_boxes = collections.Counter()
members = collections.defaultdict(list)
for k, idx in cl.items():
    if any(rows[i]["bucket"] == "WRITTEN" for i in idx):
        ink_written += 1
        boxes_in_written_clusters += len(idx)
        continue
    rep = min(idx, key=lambda i: rank.get(rows[i]["bucket"], 99))
    b = rows[rep]["bucket"]
    lost[b] += 1
    lost_boxes[b] += len(idx)
    members[b].append(rows[rep]["sub"])
total_lost = sum(lost.values())
print("%s: %d boxes -> %d ink clusters; ink IN the file %d (carrying %d boxes, %d of them extra copies)"
      % (doc, len(rows), len(cl), ink_written, boxes_in_written_clusters, boxes_in_written_clusters - ink_written))
print("ink NOT in the file: %d clusters (%d boxes)   [+ up to %d heads in red gaps of partial bars, unlocatable]"
      % (total_lost, sum(lost_boxes.values()), gap_rows))
for b, n in lost.most_common():
    print("  %-56s %5d ink  (%d boxes)" % (b, n, lost_boxes[b]))
json.dump({"doc": doc, "boxes": len(rows), "clusters": len(cl), "ink_in_file": ink_written,
           "boxes_in_written_clusters": boxes_in_written_clusters, "ink_not_in_file": dict(lost),
           "boxes_of_ink_not_in_file": dict(lost_boxes), "gap_rows_unlocatable": gap_rows,
           "members": {b: v for b, v in members.items()}}, open(out_path, "w"), indent=0)
