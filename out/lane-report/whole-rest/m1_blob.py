"""m1: record-resident evidence for a hanging whole rest: rest_ink_contact blob_sp / box_height_sp of restWhole boxes by fate."""
import pickle, collections, numpy as np
for pk in ("lit", "brah"):
    d = pickle.load(open("out/lane-report/whole-rest/%s.pkl" % pk, "rb"))
    ric = {o["subject"]: o for o in d["observations"] if o["quantity"] == "rest_ink_contact"}
    gb = {o["subject"]: o for o in d["observations"] if o["quantity"] == "glyph_box"}
    ref = {v["subject"]: v["reason"] for v in d["verdicts"] if v["quantity"] == "rest_is_not_a_rest" and v["value"]}
    allv = {v["subject"] for v in d["verdicts"] if v["quantity"] == "rest_is_not_a_rest"}
    g = collections.defaultdict(list)
    for s, o in ric.items():
        if gb[s]["value"][0] != "restWhole":
            continue
        k = ref.get(s, "KEPT" if s in allv else "noverdict")
        dt = o["detail"]
        g[k].append((dt["blob_sp"], dt["box_height_sp"], dt["thin_run_sp"]))
    print(pk)
    for k, v in g.items():
        a = np.array(v)
        print(" ", k, len(v), "blob p0/50/90/100", np.round(np.percentile(a[:, 0], [0, 50, 90, 100]), 2),
              "boxh", np.round(np.percentile(a[:, 1], [0, 50, 90, 100]), 2))
