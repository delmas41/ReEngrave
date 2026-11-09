"""2.278: where in its bar is each narrowed head? rank by x among the cell's noteheads (first / middle / last), vs all written heads.
usage: barpos.py RECORD DIAG.jsonl [slim]"""
import sys, json, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from tools.omr.staged.record_io import load_record, expand_result
from tools.omr.staged.record import Q
from tools.omr.staged import export as EXPORT

CAP = {}
orig = EXPORT._place_notes
def place(rec, runs, **kw):
    CAP["rec"] = rec; CAP["fates"] = kw.get("fates"); return orig(rec, runs, **kw)
EXPORT._place_notes = place
path, diag = sys.argv[1], sys.argv[2]
if len(sys.argv) > 3 and sys.argv[3] == "slim":
    def _hook(o):
        if "quantity" in o and "outcome" in o:
            o.pop("considered", None); o.pop("correlated", None)
        return o
    d = expand_result(json.loads(Path(path).read_text(), object_hook=_hook))
else:
    d = load_record(path)
EXPORT.to_musicxml(d)
rec, fates = CAP["rec"], CAP["fates"]
cells = collections.defaultdict(list)
for o in rec.obs_of(Q.GLYPH_BOX):
    sub = o["subject"]
    if not rec.obs(Q.NOTEHEAD_CLASS, sub): continue
    if fates.get(sub, "").startswith("not_a_notehead") or fates.get(sub) in ("mark_group_duplicate", "owned_by_another_staff"): continue
    x = (o.get("detail") or {}).get("x_center_page")
    if x is None: continue
    cells[tuple(sub.split("/")[1:5])].append((x, sub))
pos = {}
for k, v in cells.items():
    v.sort()
    n = len(v)
    for i, (x, s) in enumerate(v):
        pos[s] = (i, n, x, v[0][0], v[-1][0])
def cls(s):
    i, n, x, x0, x1 = pos[s]
    if n == 1: return "only"
    return "first" if i == 0 else ("last" if i == n - 1 else "middle")
R = [json.loads(l) for l in open(diag)]
for name, sel in (("narrowed", lambda r: r["fate"] == "duration_narrowed"),
                  ("narrowed beam family", lambda r: r["fate"] == "duration_narrowed" and r["reason"] in ("beams_ambiguous", "beam_discounted_uncertain", "beam_certain_not_joined")),
                  ("narrowed beams_ambiguous disagree", lambda r: r["fate"] == "duration_narrowed" and (r.get("bfs") or {}).get("settled") == "disagree_narrowed")):
    c = collections.Counter(cls(r["sub"]) for r in R if sel(r) and r["sub"] in pos)
    print(name, dict(c))
allc = collections.Counter(cls(s) for s in pos if fates.get(s) == "written")
print("all written heads", dict(allc))
