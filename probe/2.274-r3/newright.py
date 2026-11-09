import json
C = json.load(open("census3.json"))
for c in C:
    if c["strict_on"] != "right" and c["aud_on"] == "right":
        print("P%-3d %-5s %-4s x%d %.1fsp openL=%s openR=%s dup=%s" % (c["n"], c["staff"], c["kind"], c["x0"], c["width_sp"], c["open_L"], c["open_R"], c["dup_of"]))
print("lost by audit:", [c["n"] for c in C if c["strict_on"] == "right" and c["aud_on"] != "right"])
