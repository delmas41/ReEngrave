import json
import sys
C = json.load(open("census3.json"))
arm = sys.argv[1] if len(sys.argv) > 1 else "on"
for c in C:
    a = c["aud_" + arm]
    if a == "right":
        continue
    e = c["bind"][0] if c["bind"] else None
    heads_missing = [s for s, h in c["heads"].items() if h.get("hand_head") and not h.get("written_" + arm)]
    past = max([r["past_sp"] for r in c["runs"]] or [0])
    print("P%-3d %-5s %-4s %5dpx %5.1fsp aud=%-10s strict=%-10s boxcov=%.2f kept=%.2f run=%.2f past=%4.1f %s %s%s%s dup=%s" % (
        c["n"], c["staff"], c["kind"], c["x0"], c["width_sp"], a, c["strict_" + arm], c["box_cov"], c["box_cov_kept"], c["run_cov"], past,
        (e["status"] + ":" + str(e["why"] or e["rule"] or "")) if e else "no-entry", ("HEADMISS" + str(heads_missing)) if heads_missing else "", " openL" if c["open_L"] else "", " openR" if c["open_R"] else "", c["dup_of"]))
