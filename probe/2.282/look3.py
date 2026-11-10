import collections
import json
import sys

r = json.load(open(sys.argv[1]))
for x in r:
    if x["sub"] in sys.argv[2:]:
        print({k: x[k] for k in ("sub", "type", "why", "margin", "n_stems", "n_members", "head_to_right", "acc_box_over")})
sharp = [x for x in r if x["type"] == "sharp" and not x["acc_box_over"]]
print(collections.Counter((x["why"], x["n_members"], x["n_stems"]) for x in sharp).most_common(8))
for x in sharp[:6]:
    print(x["sub"], x["n_stems"], x["n_members"], bool(x["head_to_right"]), x["ink_box_cell"])
