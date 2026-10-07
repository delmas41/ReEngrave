"""lane-brahms-1007-worse-and-slow, step 1: ONE load_record of a record -> the 10-07 extraction (night_1006_extract.from_result)
PLUS every standing verdict, compact: `allv` {"quantity|subject": [outcome, value (<=120 chars), reason]}.  READ ONLY on the record.

  python3 brahms_1007_worse_extract.py <record.json> <out.json>
"""
from __future__ import annotations
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import night_1006_extract as E6
from tools.omr.staged.record_io import load_record


def main(src, dst):
    res = load_record(src)
    out = E6.from_result(res, src)
    rec = res["record"]
    sup = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    allv = {}
    for v in rec["verdicts"]:
        if v["id"] in sup:
            continue
        val = v.get("value")
        allv[f'{v["quantity"]}|{v["subject"]}'] = [v["outcome"], json.dumps(val, default=str)[:120], v.get("reason")]
    out["allv"] = allv
    Path(dst).write_text(json.dumps(out))
    print(dst, "glyphs", len(out["glyphs"]), "allv", len(allv), flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])
