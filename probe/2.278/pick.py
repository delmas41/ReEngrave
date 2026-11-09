"""2.278: stratified picks for the 12 blind tiles. usage: pick.py PLATE DIAG.jsonl CHORDS.json SEED OUT.json  (6 per plate)"""
import json, random, sys, ast
PLATE, DIAG, CH, SEED, OUT = sys.argv[1:6]
rng = random.Random(int(SEED))
R = [json.loads(l) for l in open(DIAG)]
N = [r for r in R if r["fate"] == "duration_narrowed" and r.get("bbox")]


def b(r):
    d = r["d"]; bf = (r.get("bfs") or {}).get("settled")
    if r["reason"] == "beams_ambiguous":
        if not d.get("stems_attached"): return "A_no_stem"
        return "C_disagree" if bf == "disagree_narrowed" else "C_other"
    if r["reason"] == "beam_discounted_uncertain":
        return "A_no_stem" if not d.get("stems_attached") else "D_refused"
    if r["reason"] in ("head_fill_from_ink", "open_head_flag_contradiction", "whole_class_filled_on_a_stem"): return "H_fill"
    return "other"


pool = {}
for r in N: pool.setdefault(b(r), []).append(r)
quota = {"C_disagree": 1, "C_other": 1, "D_refused": 1, "A_no_stem": 1, "H_fill": 1}
picks = []
for k, q in quota.items():
    for r in rng.sample(pool[k], q):
        sd = r.get("stem_dir") or [None, None]
        picks.append(dict(plate=PLATE, sub=r["sub"], bbox=r["bbox"], stem_dir=sd[1] if sd[0] == "decided" else None, bucket=k, reason=r["reason"]))
G = json.load(open(CH))
g = rng.choice(G)
h = g["heads"][0]
bb = h["bbox_page"]
if isinstance(bb, str): bb = ast.literal_eval(bb)
picks.append(dict(plate=PLATE, sub=h["glyph"], bbox=[bb[0], bb[1], bb[0] + bb[2], bb[1] + bb[3]], stem_dir=None, bucket="chord_value_undecided",
                  reason="chord", chord_values=[[x["duration_type"], x["dots"]] for x in g["heads"]]))
json.dump(picks, open(OUT, "w"), indent=1, default=str)
print({k: len(v) for k, v in pool.items()})
