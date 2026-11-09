"""2.280 probe 16: the TALL refusals. For heads whose first cause is 'run REFUSED: TALL' (p3, full population): the refused run's height / width in staff spaces. usage: p16_tall.py plate"""
import json
import statistics
import sys

plate = sys.argv[1]
R = json.load(open("out/2.280/rerunfull_%s.json" % plate))
B = json.load(open("out/2.280/bucketsfull_%s.json" % plate))
hs, ws = [], []
for s, b in B.items():
    if "TALL" in b["cause"]:
        r = R[s]
        for n in r["refused_near"]:
            if "TALL" in n["outcome"].upper() and n["dx_sp"] <= 0.35 and n["dy_sp"] == 0 and n["h_sp"] >= 1.5:
                hs.append(n["h_sp"])
                ws.append(n["w_sp"])
                break
print(plate, "TALL n=%d" % len(hs), "height sp: min %.1f median %.1f max %.1f" % (min(hs), statistics.median(hs), max(hs)),
      "| width sp: median %.2f max %.2f" % (statistics.median(ws), max(ws)))
q = sorted(hs)
print("  height quartiles", [round(q[int(len(q) * f)], 1) for f in (0.1, 0.25, 0.5, 0.75, 0.9)])
