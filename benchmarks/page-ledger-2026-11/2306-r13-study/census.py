"""2.306 r13 study: OLD (cell join, OFF arm) x NEW (page stem as gathered) on every real head of ONE gather per plate. Counts are our own output.
Usage: census.py lit|bra"""
import sys, collections
from common import *
plate = sys.argv[1]
D = load(plate)
real = sorted(g for g in D["heads"] if is_real(D, g, "on"))
print(plate, "head boxes", len(D["heads"]), "real heads of their own staff (ON arm, pre-retire)", len(real))
tab = collections.Counter(); how = collections.Counter(); why = collections.Counter(); dirs = collections.Counter(); dwhy = collections.Counter()
nhow = collections.Counter()
for g in real:
    o, n = old_answer(D, g), new_answer(D, g)
    O = "OLD stem" if o["stem"] else "OLD none(%s)" % o["why"]
    N = "NEW stem" if n["read"] else ("NEW two_voices" if n["how"] == "two_voices" else ("NEW no reading" if n["read"] is None else "NEW refuses"))
    tab[(O.split("(")[0], N)] += 1
    if o["stem"] and n["read"] is False and n["how"] != "two_voices":
        how[n["how"]] += 1; why[o["why"]] += 1; dwhy[(o["direction"], o["dir_why"])] += 1
    if o["stem"] and n["read"]:
        dirs[(o["direction"], n["direction"], n["how"])] += 1
    if not o["stem"] and n["read"]:
        nhow[(o["why"], n["how"])] += 1
for k, v in sorted(tab.items()):
    print("  %5d  %s | %s" % (v, k[0], k[1]))
print(" OLD stems, NEW refuses, by NEW's reason word:", how.most_common())
print("   ... by OLD's join reason:", why.most_common())
print("   ... by OLD's direction (reason):", dwhy.most_common())
agree = sum(v for (a, b, h), v in dirs.items() if a == b)
print(" both stem: direction agrees", agree, "of", sum(dirs.values()))
print("   disagreements:", [(k, v) for k, v in dirs.most_common() if k[0] != k[1]])
print(" NEW stems, OLD none, by (OLD why, NEW how):", nhow.most_common())
