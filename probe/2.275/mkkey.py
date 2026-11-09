"""2.275: merge the two per-plate tile keys into out/print/2.275-pattern/key.json (checked equal to the tile files)."""
import json
import os
import sys

a = json.load(open(sys.argv[1]))
b = json.load(open(sys.argv[2]))
out = sys.argv[3]
k = {**a, **b}
files = [f for f in os.listdir(out) if f.startswith("tile_")]
assert len(k) == len(files) == len(a) + len(b), (len(k), len(files))
json.dump({"note": "bucket = FIRST cause the exporter refused the ink (20261104-night records, main 242289863). "
                   "Never drawn on a tile. Box (blue) = the detector box of the head, padded 0.15 staff space. "
                   "Litolff tiles first, then Brahms; seeded, proportional to bucket size per plate.",
           "tiles": k}, open(os.path.join(out, "key.json"), "w"), indent=1)
print(len(k), "tiles")
