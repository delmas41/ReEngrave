"""2.167e probe 17b: a seeded sample of heads the record reads as a shared head (unison_two_voices or two_stems_left_and_right): 12 per plate, for my look.
usage: e17b_unison_sample.py OUT_A.json OUT_B.json"""
import json
import random
import sys

random.seed(2167)
items = []
for pl in ("lit", "bra"):
    rows = json.load(open("probe/2.167e/data/%s_unison2.json" % pl))
    sel = [r for r in rows if r["kind"] in ("unison_two_voices", "two_stems_left_and_right")]
    for r in random.sample(sel, 16):
        items.append([pl, r["sub"], "%s %s" % (pl, r["kind"][:14])])
json.dump(items[:16], open(sys.argv[1], "w"))
json.dump(items[16:], open(sys.argv[2], "w"))
print(len(items))
