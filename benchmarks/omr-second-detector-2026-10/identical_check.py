"""Control: every glyph that is NOT the second detector's is identical OFF vs ON (key, class, box, score) -- so beams/ledgers/ties cannot have moved.
usage: identical_check.py off.json on.json"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from tools.omr.staged import readout as RO
a, b = RO.load_run(sys.argv[1]), RO.load_run(sys.argv[2])
sec = {o["subject"] for o in b.observations if o["quantity"] == "second_hollow" and (o.get("detail") or {}).get("relation") == "second_only"}
f = lambda r, skip: {k: (g.cls, g.box_canon, g.score) for k, g in r.glyphs.items() if k not in skip}
fa, fb = f(a, set()), f(b, sec)
print(f"OFF glyphs {len(fa)}; ON glyphs {len(b.glyphs)} of which second-only {len(sec)}; identical set: {fa == fb}; differing keys: {[k for k in set(fa)|set(fb) if fa.get(k)!=fb.get(k)][:5]}")
sys.exit(0 if fa == fb else 1)
