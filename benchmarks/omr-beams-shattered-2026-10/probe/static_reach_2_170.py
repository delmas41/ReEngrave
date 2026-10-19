"""2.170: static estimate of the tightened rule's reach from the record rows (causes C + tip state `runs:0 unread:ink_not_flag_shaped`,
every own stem). Writes the glyph list. usage: static_reach_2_170.py DOC OUT.json"""
import json
import sys

doc, out = sys.argv[1:3]
c = json.load(open(".s170/causes_%s.json" % doc))
t = json.load(open(".s170/tips_%s.json" % doc))
ex = json.load(open(".s170/ex_%s.json" % doc))
g = [s for s, k in c.items() if k == "C_no_beam_at_tip" and ex["narrowed"][s]["reason"] == "beam_discounted_uncertain"
     and (t.get(s) or {}).get("k") == "runs:0 unread:ink_not_flag_shaped"]
print(doc, "static reach", len(g))
json.dump(sorted(g), open(out, "w"))
