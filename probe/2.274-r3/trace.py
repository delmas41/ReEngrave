"""python3 trace.py ORD [ORD...]: the binder's entry for each run ordinal (ON), and every arc in the OFF and ON files that starts or stops on either bound head"""
import sys
import json
from load import *  # noqa

rec = record("on")
bind = [v for v in rec["verdicts"] if v["quantity"] == "page_arc_binding"][0]["detail"]["runs"]
arcs = {a: A.arcs_of_xml((WORK / ("%s.musicxml" % a)).read_text()) for a in ("off", "on")}
gb = {o["subject"]: o["detail"]["bbox_page_px"] for o in rec["observations"] if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/0/")}
x = lambda k: round((gb[k][0] + gb[k][2]) / 2) if k in gb else None
for ordv in [int(a) for a in sys.argv[1:]]:
    for e in bind:
        if e["ordinal"] == ordv:
            print("RUN", ordv, {k: v for k, v in e.items() if k in ("status", "why", "kind", "start", "stop", "piece", "x_range", "rule", "witnesses", "relation")})
            keys = [e.get("start"), e.get("stop")] + [(e.get(s) or {}).get("head") for s in ("left", "right")]
            keys = [k for k in keys if k]
            print("   bound heads x:", [(k.split("/", 2)[2], x(k)) for k in keys])
            for arm in ("off", "on"):
                for a in arcs[arm]:
                    if a["start"] in keys or a["stop"] in keys:
                        print("   %s file arc: %s %s(x%s) -> %s(x%s)" % (arm, a["kind"], a["start"].split("/", 2)[2], x(a["start"]), a["stop"].split("/", 2)[2], x(a["stop"])))
