import json, sys, numpy as np
sys.argv_saved = sys.argv
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from probe_geometry_near_boundary import measure
tag = sys.argv[1]
rows = json.load(open(f"{tag}-geom.json")); B = np.load(f"{tag}-page.npy")
for r in rows:
    r["measured"] = measure(B, r["px"], r["py"], r["measured"]["staff"], r["sp"], r["side"])
json.dump(rows, open(f"{tag}-geom2.json", "w"), indent=1, default=str)
