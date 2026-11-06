"""Pick curves from a ledger by bucket for crops (measure only): python3 pick.py LEDGER.json PLATE SEED N_PER_BUCKET OUT_SPEC.json [bucket ...]
Buckets: slur_fewer, tie_not_in_file, tie_pair, slur_bound_missing, staff_line, written, wrong_note, two_arcs, k_abstain"""
import json
import random
import sys

led = json.load(open(sys.argv[1]))
plate, seed, n, out = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
want = sys.argv[6:]
rows = led["rows"]
B = {
    "slur_fewer": lambda r: r["fate"] == "dropped" and (r.get("lost_rule") or "").startswith("export:arc_binds"),
    "tie_not_in_file": lambda r: (r.get("lost_rule") or "").startswith("export:tie_not_in_file"),
    "tie_end_twin": lambda r: (r.get("lost_rule") or "").startswith("export:tie_not_in_file:start_head_not_written") or (r.get("lost_rule") or "").startswith("export:tie_not_in_file:stop_head_not_written"),
    "not_adjacent": lambda r: (r.get("lost_rule") or "") == "tie_pair:not_adjacent",
    "no_pair_pos": lambda r: (r.get("lost_rule") or "") == "tie_pair:no_pair_at_one_position",
    "cross_system": lambda r: "enters_from_previous_system" in (r.get("lost_rule") or "") or "runs_off_the_system" in (r.get("lost_rule") or ""),
    "no_head": lambda r: (r.get("lost_rule") or "").startswith("tie_pair:no_") and "head" in (r.get("lost_rule") or ""),
    "overjoined": lambda r: bool(r.get("overjoined")),
    "tie_pair": lambda r: (r.get("lost_rule") or "").startswith("tie_pair"),
    "slur_bound_missing": lambda r: (r.get("lost_rule") or "").startswith("export:slur_bound_not_in_file"),
    "staff_line": lambda r: r["fate"] == "not_an_arc",
    "written": lambda r: r["fate"] == "written",
    "wrong_note": lambda r: r["fate"] == "wrong_note",
    "two_arcs": lambda r: r["fate"] == "two_arcs",
    "k_abstain": lambda r: r.get("lost_at") == "K",
}
rng = random.Random(seed)
spec = []
i = 1
for b in want:
    pool = [r for r in rows if B[b](r)]
    rng.shuffle(pool)
    for r in pool[:n]:
        box = list(r["box"])
        if r.get("x_left") is not None:
            box[0], box[2] = min(box[0], r["x_left"]), max(box[2], r["x_right"])
        spec.append(dict(n=i, plate=plate, page=r["page"], box=box, sp=r["sp"], bucket=b, curve=r["curve"], pieces=r["pieces"], fate=r["fate"],
                         lost=[r.get("lost_at"), r.get("lost_rule")], pair=r.get("pair"), classes=r["classes"], why=(r.get("binding") or {}).get("why")))
        i += 1
json.dump(spec, open(out, "w"), indent=1)
print(len(spec), "picked")
for s in spec:
    print(s["n"], s["bucket"], s["curve"], s["classes"], s["lost"], s["why"])
