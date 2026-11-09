import json, sys, collections
G = json.load(open(sys.argv[1]))
cnt = collections.Counter(); heads = collections.Counter()
for g in G:
    H = g["heads"]
    stems = {h.get("stem_id") for h in H}
    dirs = {h.get("stem_direction") for h in H}
    vals = {(h["duration_beats"], h["duration_type"], h["dots"]) for h in H}
    types = {h["duration_type"] for h in H}; dots = {h["dots"] for h in H}
    beams = {h["beam_levels"] for h in H}
    if None in stems or "" in stems: s = "some_head_has_no_stem"
    elif len(stems) == 1: s = "ONE_stem_values_differ"
    else: s = "%d_stems" % len(stems)
    if len(types) > 1 and len(dots) == 1: d = "type_differs"
    elif len(types) == 1 and len(dots) > 1: d = "dots_differ"
    else: d = "type_and_dots"
    key = (s, d, "dirs=%d" % len(dirs))
    cnt[key] += 1; heads[key] += len(H)
for k, v in cnt.most_common(): print(k, v, "groups", heads[k], "heads")
print()
for g in G[:40]:
    print(g["cell"], [(h["stem_id"], h["stem_direction"], h["duration_type"], h["dots"], h["beam_levels"], h["guess"]) for h in g["heads"]])
