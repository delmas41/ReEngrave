import json, sys, collections
R = [json.loads(l) for l in open(sys.argv[1])]
c = collections.Counter()
for r in R:
    if r["fate"] != "duration_narrowed" or r["reason"] != "beam_discounted_uncertain": continue
    d = r["d"]
    if not d.get("stems_attached"): c["no own stem"] += 1; continue
    c[("tip_window_clean=%s" % d.get("bare_stem_tip_window_clean"), "refused_stroke_at_tip=%s" % d.get("bare_stem_refused_stroke_at_tip"))] += 1
for k, v in c.most_common(): print(v, k)
