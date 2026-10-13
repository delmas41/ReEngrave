"""2.93/2.94/2.95 reach: how each staff got its name, base vs arm, per record pair.
    python3 naming.py DOC BASE_REC ARM_REC"""
import sys
from collections import Counter

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

doc, bp, ap = sys.argv[1:4]
for tag, p in (("base", bp), ("arm", ap)):
    R = load_record(p)["record"]
    last = {}
    for v in R["verdicts"]:
        if v["quantity"] == "instrument":
            last[v["subject"]] = v
    c = Counter()
    unnamed = []
    for s, v in last.items():
        c[(str(v["outcome"]), str(v["decider"]), str(v["reason"]))] += 1
        if str(v["outcome"]) != "decided":
            unnamed.append((s, (v.get("detail") or {}).get("reader_text")))
    print(doc, tag, "staves", len(last))
    for k, n in c.most_common():
        print("   ", n, k)
    print("   unnamed sample:", unnamed[:8])
    shared = sum(1 for o in R["observations"] if o["quantity"] == "margin_label"
                 and (o.get("detail") or {}).get("shared_word"))
    clef_over = sum(1 for v in R["verdicts"] if "clef_glyph_overruled_by_locator" in (v.get("detail") or {}))
    cond = sum(1 for v in R["verdicts"] if v["quantity"] == "slot_index" and "condens" in str(v.get("reason")))
    print("   margin labels with shared_word:", shared, "| clef_glyph_overruled verdicts:", clef_over,
          "| slot_index condensed-like:", cond)
