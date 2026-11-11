"""Pitch-blue notes on a page subset of one analyze.py JSON.   python3 subset.py X.json PAGE[,PAGE..]"""
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from tally import reasons_for  # noqa

d = json.load(open(sys.argv[1]))
pg = set(sys.argv[2].split(","))
S = [s for s in d["symbols"] if not s["is_rest"] and s["sub"].split("/")[1] in pg]
B = [s for s in S if s["blue"]]
P = [s for s in B if {"key_fill", "clef_fill"} & reasons_for(s)]
K = [s for s in B if "key_fill" in reasons_for(s)]
C = [s for s in B if "clef_fill" in reasons_for(s)]
print(sys.argv[1].split("/")[-1], "pages", sorted(pg), "notes", len(S), "blue", len(B), "pitch-blue", len(P), "(key %d, clef %d)" % (len(K), len(C)),
      "%.1f%% of notes" % (100.0 * len(P) / max(1, len(S))))
