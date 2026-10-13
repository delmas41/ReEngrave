"""Print base -> arm for two probe_reach.py outputs.
    python3 compare.py BASE.json ARM.json
"""
import json
import sys

b = json.load(open(sys.argv[1]))
a = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else None


def prox(d):
    p = d["proxies"]
    h = p["bars_held_out_sum"]
    ba = p["bars_add_up_control"]
    return {
        "notes_reaching_file": f'{p["notes_reaching_file"]["n"]}/{p["notes_reaching_file"]["of"]}',
        "bars_held_out_sum": f'{h["n"]}/{h["of"]}',
        "held_noteheads_rests": h["noteheads_and_rests"],
        "bars_add_up": f'exact {ba["exact"]} short {ba["short"]} overfull {ba["overfull"]} empty {ba["empty"]} unassessable {ba["unassessable"]}',
        "parts_named": p.get("parts_named"),
        "held_out_staff_not_identified": p["held_out"]["staff_not_identified"],
        "unread_bars": p["unread_bars"],
        "balanced": p.get("balanced"),
    }


pb = prox(b)
pa = prox(a) if a else {}
for k in pb:
    print(f"{k:32s} {pb[k]!s:60s} -> {pa.get(k)!s}")
if a:
    print("\n--- notes_not_written")
    keys = sorted(set(b["notes_not_written"] or {}) | set(a["notes_not_written"] or {}))
    for k in keys:
        x, y = (b["notes_not_written"] or {}).get(k, 0), (a["notes_not_written"] or {}).get(k, 0)
        if x != y:
            print(f"  {k:40s} {x} -> {y}")
    print("\n--- verdict rows that differ (quantity|decider|outcome|reason)")
    keys = sorted(set(b["verdicts"]) | set(a["verdicts"]))
    for k in keys:
        x, y = b["verdicts"].get(k, 0), a["verdicts"].get(k, 0)
        if x != y:
            print(f"  {k:100s} {x} -> {y}")
    print("\n--- observation/abstention rows that differ")
    for sec in ("observations", "abstentions"):
        for k in sorted(set(b[sec]) | set(a[sec])):
            x, y = b[sec].get(k, 0), a[sec].get(k, 0)
            if x != y:
                print(f"  {sec[:3]} {k:90s} {x} -> {y}")
    print("\n--- detail flags")
    for k in sorted(set(b["detail_flags"]) | set(a["detail_flags"])):
        print(f"  {k:70s} {b['detail_flags'].get(k, 0)} -> {a['detail_flags'].get(k, 0)}")
    print("\n--- written counters that differ")
    for k in sorted(set(b["export_counters"]) | set(a["export_counters"])):
        x, y = b["export_counters"].get(k), a["export_counters"].get(k)
        if x != y:
            print(f"  {k:60s} {x} -> {y}")
