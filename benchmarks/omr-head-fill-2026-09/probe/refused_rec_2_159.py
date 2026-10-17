"""ROADMAP 2.159 -- the slices hold only duration verdicts; this streams the WHOLE night record's verdicts (judged.iter_array)
for every head-level refusal of the changed glyphs (2.143 tile rule: a head refused as not-a-notehead or as a rest is not a
note). usage: refused_rec_2_159.py RECORD OUTDIR DOC"""
import json
import os
import pathlib
import sys

sys.path.insert(0, ".")
from tools.omr.staged.judged import iter_array  # noqa: E402

REC, OUT, DOC = sys.argv[1:4]
R = json.load(open(os.path.join(OUT, "replay_%s.json" % DOC)))
want = set(R["changed"])
H = json.load(open(os.path.join(OUT, "heads_%s.json" % DOC)))
want |= {s for s, h in H.items() if "hf" in h}           # and every head_fill_from_ink head, for the reach split
res = {g: {} for g in want}
for v in iter_array(pathlib.Path(REC), "verdicts"):
    if v.get("subject") in want and v.get("quantity") != "duration":
        res[v["subject"]][v["quantity"]] = (v["outcome"], v.get("value"), v.get("reason"))
NOT_A_NOTE = ("notehead_is_not_a_notehead", "head_ink_is_a_rest", "notehead_is_a_whole_rest",
              "notehead_is_an_eighth_rest")
refused = {g for g, r in res.items() if any(r.get(q, (None, None))[0] == "decided" and r[q][1] is True
                                            for q in NOT_A_NOTE)}
ch = sorted(set(R["changed"]))
print(DOC, "changed", len(ch), "refused as not a note / a rest:", len([g for g in ch if g in refused]),
      "| hf heads", len(want) - len(set(ch) - {s for s, h in H.items() if "hf" in h}),
      "hf refused:", len([s for s, h in H.items() if "hf" in h and s in refused]))
for g in ch:
    print("  ", g, "REFUSED" if g in refused else "note", {q: res[g].get(q) for q in NOT_A_NOTE if q in res[g]})
json.dump({"refused": sorted(refused), "rows": res}, open(os.path.join(OUT, "refused_%s.json" % DOC), "w"), indent=0)
