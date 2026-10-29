"""Pick candidate arcs per fate group (seeded) and cut tiles with lane_report.cut_tiles (one neutral orange box; nothing of ours drawn).
usage: pick.py OUTDIR N_PER_GROUP  [final: pick.py OUTDIR final IDX,IDX,...  reads OUTDIR/pool_key.json]"""
import json, random, sys, pathlib, collections
from tools.omr.staged import lane_report as L

out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
rnd = random.Random(1029)
GROUPS = [  # (label, plate, predicate on cluster fate)
    ("slur_binds_fewer_than_two_notes", "litolff", "refused:slur_binds_fewer_than_two_notes", 4),
    ("slur_binds_fewer_than_two_notes", "brahms", "refused:slur_binds_fewer_than_two_notes", 4),
    ("tie_pair_no_head_near_the_arc", "litolff", "refused:tie_pair_no_head_near_the_arc", 3),
    ("tie_pair_no_head_near_the_arc", "brahms", "refused:tie_pair_no_head_near_the_arc", 3),
    ("tie_pair_narrowed", "brahms", "refused:tie_pair_narrowed", 3),
    ("tie_pair_no_start_head", "litolff", "refused:tie_pair_no_start_head", 2),
    ("tie_pair_no_stop_head", "litolff", "refused:tie_pair_no_stop_head", 2),
    ("tie_pair_no_pair_at_one_position", "litolff", "refused:tie_pair_no_pair_at_one_position", 2),
    ("tie_pair_not_adjacent", "brahms", "refused:tie_pair_not_adjacent", 2),
    ("tie_pair_decided_not_in_file", "brahms", "refused:tie_pair_decided_not_in_file", 2),
    ("tie_spelling_differs", "brahms", "refused:tie_spelling_differs", 2),
    ("tie_pair_enters_from_previous_system", "litolff", "refused:tie_pair_enters_from_previous_system", 2),
    ("CONTROL_written_tie", "brahms", "tie_marked", 2),
    ("CONTROL_written_slur", "litolff", "slur_marked", 2),
]
items = []
for label, plate, fate, n in GROUPS:
    d = json.load(open("/private/tmp/claude-501/arcs/%s.json" % plate))
    u = L.PLATES[plate]["unit"]
    cand = [c for c in d["clusters"] if c["fate"] == fate and c["box"] and c["box"][2] <= 10 * u and c["box"][3] <= 4 * u]
    rnd.shuffle(cand)
    for c in cand[:n]:
        x, y, w, h = c["box"]
        items.append(dict(plate=plate, page=c["page"], box=[x, y, x + w, y + h], role="control" if label.startswith("CONTROL") else "case",
                          group=label, fate=c["fate"], sub=c["subs"][0], n_boxes_in_cluster=c["n_boxes"]))
if len(sys.argv) > 2 and sys.argv[2] == "final":
    idx = [int(i) - 1 for i in sys.argv[3].split(",")]
    items = [items[i] for i in idx]
    rnd.shuffle(items)   # blind order
print(L.cut_tiles(items, out))
