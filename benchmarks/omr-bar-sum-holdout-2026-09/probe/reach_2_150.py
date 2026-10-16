"""ROADMAP 2.150 -- reach of the width floor on a cached record (census_2_150.py output): kept restQuarter boxes
under 0.7 staff spaces, per page, and the evidence beside them. usage: reach_2_150.py CENSUS.json"""
import json, sys, collections

c = json.load(open(sys.argv[1]))
q = [r for r in c if r["cls"] == "restQuarter"]
hit = [r for r in q if r["w"] < 0.7]
print("kept restQuarter", len(q), "under 0.7:", len(hit))
print("  with a standing head at an end:", sum(bool(r["head_end"]) for r in hit),
      " a Q.STEM row in the box:", sum(bool(r["stem_rows"]) for r in hit),
      " a flag box:", sum(bool(r["flags"]) for r in hit),
      " none of these:", sum(not (r["head_end"] or r["stem_rows"] or r["flags"]) for r in hit))
pages = collections.Counter(int(r["glyph"].split("/")[1]) for r in hit)
print("  pages:", dict(sorted(pages.items())))
systems = collections.Counter(tuple(int(x) for x in r["glyph"].split("/")[1:3]) for r in hit)
print("  top systems:", systems.most_common(12))
band = [r for r in q if 0.7 <= r["w"] < 0.9]
print("band 0.7-0.9 (not reached):", len(band), "with head at an end:", sum(bool(r["head_end"]) for r in band))
