"""STREAM a record's verdicts (never loaded whole) -> {glyph: [outcome, beats, beam_levels, reason, decider, n_cand, detail-subset]}
for the LAST duration verdict per subject (the standing one, emission order). python3 stream_durations_2_140.py RECORD OUT.json"""
import json, sys, pathlib
sys.path.insert(0, ".")
from tools.omr.staged import judged as J
m = {}
for v in J.iter_verdicts(pathlib.Path(sys.argv[1])):
    if v["quantity"] != "duration":
        continue
    val = v.get("value") if isinstance(v.get("value"), dict) else {}
    d = v.get("detail") or {}
    m[v["subject"]] = [v["outcome"], val.get("beats"), val.get("beam_levels"), v["reason"], v["decider"], len(v.get("candidates") or ()),
                       {k: d.get(k) for k in ("levels_certain", "levels_possible", "cv_beams", "yolo_kept", "beam_evidence") if d.get(k) is not None}]
json.dump(m, open(sys.argv[2], "w"))
print(len(m), "duration verdicts ->", sys.argv[2])
