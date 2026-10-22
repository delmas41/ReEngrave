"""What each arm names the staves of ONE system, top to bottom.

The impossible grade is a lower bound and cannot say whether the names that
survive are right. For a system whose printed lineup has been read by eye, the
whole column can be checked — which is the only correct/wrong evidence this
session produced, and it is 2 systems, not a corpus.

    dump_system.py OFF.json ON.json PAGE SYSTEM
"""
import json
import sys


def load(path):
    b = json.load(open(path))["contextual"]["absent_instrument_veto"]
    name = {s["slot"]: s["instrument"] for s in b["slot_instruments"]}
    vet = {(v["page_index"], v["system_index"], v["staff_index"])
           for v in b["vetoes"]}
    return ({(s["page_index"], s["system_index"], s["staff_index"]):
             s["slot"] for s in b["staff_slots"]}, name, vet)


off, on = sys.argv[1], sys.argv[2]
page, system = int(sys.argv[3]), int(sys.argv[4])
so, no_, vo = load(off)
sn, nn, vn = load(on)
keys = sorted(k for k in so if k[0] == page and k[1] == system)
print(f"page {page} system {system}: {len(keys)} staves")
print(f"{'staff':>5s}  {'spans-off':>12s} {'veto?':>6s}   "
      f"{'spans-on':>12s} {'veto?':>6s}")
for k in keys:
    a = no_.get(so[k]) if so[k] >= 0 else None
    b = nn.get(sn[k]) if sn[k] >= 0 else None
    print(f"{k[2]:5d}  {str(a):>12s} {'VETO' if k in vo else '':>6s}   "
          f"{str(b):>12s} {'VETO' if k in vn else '':>6s}")
