"""lane-slur-not-ledger: which rung did the slur rule refuse on each truth-set head it changes, and what shape did it have."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import jut_from_ink_eval as J
import truth_set_2_44c as ts
import farhead_owner_by_ledgers as OW

CASES = (("beethoven5-litolff", 3, ["glyph/3/0/0/7/1", "glyph/3/0/7/7/0"]), ("brahms1-breitkopf", 1, ["glyph/1/1/0/4/5"]))
for doc, page, subs in CASES:
    ts.DOCS[doc]["record"] = OW.TRUTHSET / ("beethoven5-litolff-p3.record.json" if "litolff" in doc else "brahms1-breitkopf-p1.record.json")
    L, fp, far = J.prepare(doc, page)
    for s in subs:
        h = [h for h in far if h["subject"] == s][0]
        sk = "staff/" + "/".join(s.split("/")[1:4])
        r = fp.read(s, h["box"], h["cls"], L["staff_lines"][sk])
        nf = r["detail"]["note_first"]
        print(s, r["pos"], "between", nf["between"], "line", nf["line_y"])
        for x in nf["refused_rungs"]:
            sh = x.get("shape") or {}
            print("    refused", round(x["y"], 1), x["why"], {k: (round(v, 2) if isinstance(v, float) else v) for k, v in sh.items()})
