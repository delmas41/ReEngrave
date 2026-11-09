"""2.275 q: what claim rows does a record hold for a head box? usage: inspect_claims.py RECORD SUBJECT"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.record_io import load_record   # noqa: E402
from tools.omr.staged.export import Record            # noqa: E402
from tools.omr.staged.record import Q                 # noqa: E402

rec = Record(load_record(sys.argv[1]))
sub = sys.argv[2]
p = sub.split("/")
sov = rec.verdicts_of(Q.STROKE_OWNER)
print("stroke_owner verdicts", len(sov), "first subject", sov[0]["subject"] if sov else None)
for v in sov:
    sk = v["subject"]
    if sk.endswith("/".join(p[1:5])):
        d = v.get("detail") or {}
        print("cell verdict subject", sk, "keys", list(d))
        print("boxes entry for the glyph:", json.dumps((d.get("boxes") or {}).get(sub))[:600])
        print("box_owns has it:", sub in set(d.get("box_owns") or ()))
        print("vetoes:", json.dumps((d.get("vetoes") or {}).get(sub))[:300])
        st = d.get("strokes") or {}
        print("n strokes", len(st), "sample:", json.dumps(list(st.items())[:3])[:900])
        break
gs = rec.obs(Q.GLYPH_STROKES, sub)
print("GLYPH_STROKES", json.dumps(gs)[:700])
ca = collections.Counter((o.get("detail") or {}).get("owner") for o in rec.obs_of(Q.CLAIMED_AREA))
print("CLAIMED_AREA owners", ca.most_common(25))
for o in rec.obs_of(Q.CLAIMED_AREA)[:2]:
    print("CLAIMED_AREA sample", json.dumps(o)[:600])
ps = rec.obs_of(Q.PAGE_STROKE)
print("PAGE_STROKE rows", len(ps), json.dumps(ps[:1])[:500])
