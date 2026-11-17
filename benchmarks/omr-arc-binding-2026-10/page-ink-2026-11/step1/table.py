"""2.274 step 1: one line per page, and the pooled line.   python3 table.py WORKDIR"""
import glob
import json
import sys

T = [0, 0, 0, 0, 0]
for f in sorted(glob.glob(sys.argv[1] + "/*.step1.json")):
    s = json.load(open(f))["summary"]
    print(f.split("/")[-1][:11], "runs", s["runs"], "witnessed", s["runs_witnessed"], "NEW", s["runs_new"], "kept curves", s["curves_kept"], "whole", s["whole"],
          "%.0f%%" % (100.0 * s["whole"] / s["curves_kept"]), "after seed", s["whole_after_seed"], "| s", s["seconds"]["runs"], "+", s["seconds"]["seeded"],
          {k: v for k, v in s["rejected"].items() if k in ("straight", "thin")})
    T[0] += s["runs"]
    T[1] += s["runs_new"]
    T[2] += s["curves_kept"]
    T[3] += s["whole"]
    T[4] += s["whole_after_seed"]
print("POOLED runs", T[0], "NEW", T[1], "kept curves", T[2], "whole", T[3], "%.1f%%" % (100.0 * T[3] / T[2]), "after seed", T[4], "%.1f%%" % (100.0 * T[4] / T[2]))
