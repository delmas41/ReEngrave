"""2.136: print every duration/event/meter verdict history of one cell (record as written).

    python3 hist_2_136.py RECORD page/system/staff/cell [...]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.omr.staged.record_io import load_record  # noqa: E402

rec_path, *cells = sys.argv[1:]
want = {tuple(int(x) for x in c.split("/")) for c in cells}
doc = load_record(rec_path)
rec = doc["record"] if "record" in doc else doc
for v in rec["verdicts"]:
    s = v["subject"].split("/")
    if s[0] in ("cell", "glyph") and tuple(int(x) for x in s[1:5]) in want \
            and v["quantity"] in ("duration", "event", "head_stem", "stem_value"):
        val = v.get("value")
        if v["quantity"] == "event":
            val = [e.get("glyphs") for e in (val or {}).get("events", [])]
        print(v["id"], v["subject"], v["quantity"], v["outcome"], v["decider"],
              v["reason"], "ss", v.get("supersedes"),
              json.dumps(val)[:140] if val is not None else "",
              [(c["value"].get("beats"), c["value"].get("beam_levels"))
               for c in v.get("candidates") or [] if isinstance(c["value"], dict)])
for v in rec["verdicts"]:
    s = v["subject"].split("/")
    if v["quantity"] == "meter" and s[0] == "system" \
            and any((int(s[1]), int(s[2])) == (c[0], c[1]) for c in want):
        print("METER", v["id"], v["subject"], v["outcome"], v["decider"],
              v["reason"], v.get("supersedes"))
