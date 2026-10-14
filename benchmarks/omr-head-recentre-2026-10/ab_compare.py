"""2.115 A/B control: OFF vs ON records of one page. (1) every glyph (key, class, box, score) identical; (2) every observation of every quantity other than
`notehead_ink` identical (subject, quantity, value) -- so positions/ownership/beams/ties cannot have moved; (3) the heads whose `notehead_ink` was re-centred
(`detail.part_boxed.accepted`), with the duration verdict OFF vs ON and the staff-position value OFF vs ON (step changes); (4) every standing verdict outside those heads identical.
usage: ab_compare.py off.json on.json OUT.json"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from tools.omr.staged import readout as RO
a, b = RO.load_run(sys.argv[1]), RO.load_run(sys.argv[2])
ga = {k: (g.cls, g.box_canon, g.score) for k, g in a.glyphs.items()}; gb = {k: (g.cls, g.box_canon, g.score) for k, g in b.glyphs.items()}
def obs(r, skip):
    return sorted((o["subject"], o["quantity"], json.dumps(o.get("value"), sort_keys=True, default=str)) for o in r.observations if o["quantity"] not in skip)
oa, ob = obs(a, {"notehead_ink"}), obs(b, {"notehead_ink"})
moved = sorted(o["subject"] for o in b.observations if o["quantity"] == "notehead_ink" and ((o.get("detail") or {}).get("part_boxed") or {}).get("accepted"))
pos = lambda r: {o["subject"]: o["value"] for o in r.observations if o["quantity"] == "notehead_staff_position"}
pa, pb = pos(a), pos(b)
def dur(r, k):
    v = r.standing(k, "duration", "ADJUDICATE")
    return None if v is None else (v["outcome"], json.dumps(v.get("value"), sort_keys=True, default=str), json.dumps(v.get("candidates"), sort_keys=True, default=str))
changed = []
for k in moved:
    da, db = dur(a, k), dur(b, k)
    changed.append(dict(key=k, cls=ga.get(k, [None])[0], pos_off=pa.get(k), pos_on=pb.get(k), step_changed=pa.get(k) != pb.get(k), duration_off=da, duration_on=db, verdict_changed=da != db))
rest_diff = []
for k in set(a.glyphs) | set(b.glyphs):
    if k in moved: continue
    if dur(a, k) != dur(b, k): rest_diff.append(k)
res = dict(glyphs_identical=ga == gb, n_glyphs=len(ga), non_ink_observations_identical=oa == ob, n_obs=len(oa), moved=len(moved),
           step_changes=sum(c["step_changed"] for c in changed), verdict_changes_on_moved=sum(c["verdict_changed"] for c in changed),
           duration_verdict_differences_off_moved_heads=len(rest_diff), rest_diff_keys=rest_diff[:10], changed=changed)
Path(sys.argv[3]).write_text(json.dumps(res, indent=1))
print({k: v for k, v in res.items() if k != "changed"})
