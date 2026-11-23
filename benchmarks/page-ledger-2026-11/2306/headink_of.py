"""2306 r12: the head-ink reading (Q.HEAD_INK, GATHER, before the page stems) of given glyphs -- value or the abstention reason and its detail
(not_one_head's own why, foreign share). Usage: headink_of.py REC glyph[:label] ..."""
import sys, json
rec = sys.argv[1]
want = dict((a.split(":", 1) + [""])[:2] for a in sys.argv[2:])
R = json.load(open(rec))["record"]
got = {}
for o in R["observations"]:
    if o["quantity"] == "head_ink" and o["subject"] in want:
        got[o["subject"]] = ("read", o["value"], {k: o["detail"].get(k) for k in ("not_one_head", "foreign_share", "extent_sp")})
for a in R["abstentions"]:
    if a["quantity"] == "head_ink" and a["subject"] in want:
        d = a.get("detail") or {}
        got[a["subject"]] = ("abstain", a.get("reason"), {k: d.get(k) for k in ("not_one_head", "foreign_share", "extent_sp", "stack_clipped")})
for g, lab in want.items():
    print("%-22s %-28s %s" % (g, lab, got.get(g, "no head_ink row")))
