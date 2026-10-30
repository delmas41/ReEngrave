"""Scratch: standing verdicts for the three right->wrong subjects in one record."""
import sys, json, pathlib
sys.path.insert(0, '.')
from tools.omr.staged import judged as J
subs = ['glyph/3/1/2/15/0', 'glyph/3/0/4/3/12', 'glyph/4/0/7/7/10']
rec = pathlib.Path(sys.argv[1])
S = J.standing_for(rec, subs)
for k, v in S.items():
    print(k, json.dumps(v)[:1500])
print(J.page_boxes(rec, subs))
