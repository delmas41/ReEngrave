"""append 2.98 (lone whole rest = the bar) tiles + extra abstained tiles to plan.json"""
import json
import random
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

plan = json.load(open(sys.argv[1]))
R = load_record(plan["docs"]["dvorak"]["record"])["record"]
whole = []
for o in R["observations"]:
    if o["quantity"] == "glyph_box" and str(o["value"][0]).lower().startswith("restwhole"):
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b and o["subject"].split("/")[1] in ("5", "6", "7"):
            whole.append((o["subject"], b))
rng = random.Random(11)
print("dvorak whole-rest boxes", len(whole))
for s, b in rng.sample(whole, 2):
    plan["tiles"].append({"doc": "dvorak", "kind": "mark", "subject": s, "box": b,
                          "purpose": "2.98 lone whole rest: written as the bar (file meter)",
                          "rule": "2.98_whole_rest_bar", "our_reading": {"arm": "whole-bar rest"}})
json.dump(plan, open(sys.argv[1], "w"), indent=1, default=str)
print(len(plan["tiles"]))
