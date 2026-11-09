import json
import sys
C = json.load(open("census2.json"))
want = sys.argv[1]
for c in C:
    if c["bind_state"].startswith(want) and c["file_on"] != "right":
        e = c["bind"][0] if c["bind"] else None
        print("P%d %s %s x%d-%d (%.1fsp) boxcov %.2f kept %.2f runcov %.2f past %s | OFF %s ON %s" % (c["n"], c["staff"], c["kind"], c["x0"], c["x1"], c["width_sp"], c["box_cov"], c["box_cov_kept"], c["run_cov"], [r["past_sp"] for r in c["runs"]][:2], c["file_off"], c["file_on"]))
        if e:
            print("    bind", e["status"], e["why"], e["kind"], "ordinal", e["ordinal"], "piece", e["piece"], "xr", e["x_range"], "err", c.get("bind_err"), "L", e["left"] and (e["left"]["distance_spaces"], e["left"]["out_by_spaces"], e["left"]["chord"]), "R", e["right"] and (e["right"]["distance_spaces"], e["right"]["out_by_spaces"], e["right"]["chord"]))
        print("    near OFF", c["near_off"], "\n    near ON ", c["near_on"], "\n    heads", c["heads"])
