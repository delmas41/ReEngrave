"""python3 direction_cap_compare.py <old_dir> <new_dir>: time, found, lost/gained words per page (data_*.json from direction_cap_heldout.py)."""
import json, glob, os, sys
old, new = sys.argv[1:3]
t0 = t1 = n0 = n1 = 0
for f in sorted(glob.glob(os.path.join(new, "data_*.json"))):
    d = json.load(open(f)); b = json.load(open(os.path.join(old, os.path.basename(f))))
    k = lambda x: {tuple(w[:4]) for w in x["on_words"]}
    lost = sorted(k(b) - k(d)); gain = sorted(k(d) - k(b))
    t0 += b["on_s"]; t1 += d["on_s"]; n0 += len(b["on_words"]); n1 += len(d["on_words"])
    print(os.path.basename(f)[5:-5], "time %.1f -> %.1f" % (b["on_s"], d["on_s"]), "found", len(b["on_words"]), "->", len(d["on_words"]),
          "lost", lost, "gain", gain, "| vs cap-off lost", d["lost_on_vs_off"], d.get("error", "")[:100])
print("total s", round(t0), round(t1), "found", n0, n1)
