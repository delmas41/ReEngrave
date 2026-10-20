"""2.176: OFF vs ON from replay_2_176.py outputs -> the exported-file numbers and the list of newly refused heads.
usage: compare_2_176.py DOC OUTDIR"""
import collections
import json
import sys

DOC, D = sys.argv[1], sys.argv[2]
a = json.load(open("%s/%s.off.json" % (D, DOC)))
b = json.load(open("%s/%s.on.json" % (D, DOC)))


def nums(x):
    w = x["coverage"]["written"] or {}
    held = (x["coverage"]["bars_held_out_sum"] or {}).get("bars")
    partial = w.get("bars_partial")
    ev = w.get("bars_with_events")
    return dict(notes_in_file=w.get("notes"), notes_in_xml_elements=x["notes_in_xml"], bars_with_events=ev, held_bars=held,
                partial_bars=partial, bars_add_up=(ev - held - partial) if None not in (ev, held, partial) else None,
                notes_held_out=w.get("notes_held_out_sum"), guessed_notes=w.get("guessed_notes"), refused_heads=len(x["refusals"]))


na, nb = nums(a), nums(b)
print(DOC)
for k in na:
    print("  %-24s off %-8s on %-8s delta %s" % (k, na[k], nb[k], (nb[k] - na[k]) if None not in (na[k], nb[k]) else None))
new = {g: r for g, r in b["refusals"].items() if g not in a["refusals"]}
lost = [g for g in a["refusals"] if g not in b["refusals"]]
print("  newly refused", len(new), dict(collections.Counter(r[1] for r in new.values())), "| refusals lost", len(lost))
oc = collections.Counter((a["glyphs"].get(g) or {}).get("outcome") for g in new)
print("  the newly refused were (off arm duration outcome):", dict(oc))
held_a = {tuple(h) for h in a["held_bars"]}
held_b = {tuple(h) for h in b["held_bars"]}
print("  bars released from held:", len(held_a - held_b), "| newly held:", len(held_b - held_a))
json.dump(dict(new=sorted(new), released=sorted(held_a - held_b), newly_held=sorted(held_b - held_a),
               written_off=[g for g, v in a["glyphs"].items() if v["outcome"] == "decided" and g in new]),
          open("%s/%s.cmp.json" % (D, DOC), "w"))
