"""ROADMAP 2.312 job 2 -- where the real far heads that carry the blue fallback pitch verdict but are NOT in the exported file are dropped (exporter refusal reason per subject).
    python3 drop_tally.py HEADS.json   (HEADS.json.export.json beside it, from far_heads_rerun.py)
"""
import collections
import json
import sys

hs = json.load(open(sys.argv[1]))
ex = json.load(open(sys.argv[1] + ".export.json"))
ref = {}
for sub, why in ex["refusals"]:
    ref.setdefault(sub, []).append(why)
c = collections.Counter()
ex_s = []
for h in hs:
    g = int(round(h["geom"]))
    if not (g <= -2 or g >= 10) or h["ledger_row"] is not None:
        continue
    pv = h["pitch"] or {}
    nan = h["not_a_note"]
    if pv.get("reason") != "position_and_clef_ledger_unread" or (nan and nan[1] is True) or h["written"]:
        continue
    r = ref.get(h["key"])
    c[tuple(r) if r else ("no exporter refusal on this glyph",)] += 1
    if not r:
        ex_s.append(h["key"])
print("blue-verdict real heads not in the file:", sum(c.values()))
for k, v in c.most_common():
    print("  %3d  %s" % (v, k))
print("exporter's own count of notes not written (all pages):", ex["notes_not_written_total"], ex["notes_not_written"])
print("no refusal recorded:", ex_s[:10])
