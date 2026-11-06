"""Export-side arc counters and ADJUDICATE arc/tie reasons for two arms' gathered records (ROADMAP 2.272: 'the arc reasons that move').

    python3 reasons.py OFF.gathered.record.json ON.gathered.record.json
"""
import collections
import sys

from tools.omr.staged import export as E
from tools.omr.staged.record_io import load_record

NAMES = ("arc_binds_fewer_than_two_notes", "slur_bound_end_not_in_file", "tie_end_not_in_file")


def one(path):
    result = load_record(path)
    if "record" not in result:
        result = {"record": result, "summary": {}}
    r = result["record"]
    ab = collections.Counter()
    for a in r.get("abstentions", []):
        if a.get("quantity") in ("tie_pair", "arc_kind", "arc_owner"):
            ab["%s:%s" % (a["quantity"], a.get("reason"))] += 1
    xml, report = E.to_musicxml(result)

    def walk(d, out, pre=""):
        for k, v in d.items():
            if isinstance(v, dict):
                walk(v, out, pre + k + ".")
            elif k in NAMES or "arc" in k or "slur" in k or "tie" in k:
                if isinstance(v, (int, float)):
                    out[pre + k] = v
    ex = {}
    walk(report, ex)
    return ab, ex


a0, e0 = one(sys.argv[1])
a1, e1 = one(sys.argv[2])
print("EXPORT counters (OFF -> ON), changed only:")
for k in sorted(set(e0) | set(e1)):
    if e0.get(k) != e1.get(k):
        print("  %s: %s -> %s" % (k, e0.get(k), e1.get(k)))
print("EXPORT named reasons:", {k: (e0.get("dropped." + k, 0), e1.get("dropped." + k, 0)) for k in NAMES})
print("ADJUDICATE abstentions (OFF -> ON), changed only:")
for k in sorted(set(a0) | set(a1)):
    if a0.get(k) != a1.get(k):
        print("  %s: %s -> %s" % (k, a0.get(k, 0), a1.get(k, 0)))
