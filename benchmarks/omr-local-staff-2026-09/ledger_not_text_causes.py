"""lane-ledger-not-text: of the decisions the rule changed, which test refused the rung (text box / continuity), and did the
decision it removed agree with geometry? Read only, from `ledger_not_text_oos_*.json`.  python3 ledger_not_text_causes.py"""
import collections, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
for which in ("litolff", "brahms"):
    B = {r["subject"]: r for r in json.loads((HERE / f"farhead_note_first_oos_{which}.json").read_text())}
    A = json.loads((HERE / f"ledger_not_text_oos_{which}.json").read_text())
    c = collections.Counter()
    nref = collections.Counter()
    for a in A:
        for x in (a["new"].get("refused") or []):
            nref[x["why"]] += 1
        b = B[a["subject"]]
        if b["new"]["pos"] == a["new"]["pos"]:
            continue
        why = sorted({x["why"] for x in (a["new"].get("refused") or [])}) or ["relaxed-gap search refused it"]
        agree = b["new"]["pos"] == b["geometry"] if b["new"]["pos"] is not None else None
        c[(tuple(why), "removed decision agreed with geometry" if agree else "disagreed/none")] += 1
    print(which, "rungs refused in all decisions:", dict(nref))
    for k, v in c.most_common():
        print("  ", v, k)
