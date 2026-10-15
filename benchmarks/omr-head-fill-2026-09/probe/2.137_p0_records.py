"""2.137: Brahms page-0 records for the hand-truth scorer, flag off and on.

    python3 benchmarks/omr-head-fill-2026-09/probe/2.137_p0_records.py NIGHT_RECORD.json OUTDIR

Takes the saved `20261014-night` record, keeps the document-level rows and page 0's rows (the pooled file is
read only through `record_io.load_record`), re-gathers nothing (`rebuild_gather` replays the saved GATHER rows),
re-decides every stage with `OMR_SLASH_AT_STEM_END` unset and then set, and writes `p0-off.record.json` and
`p0-on.record.json`. Score each with
`python3 -m tools.omr.hand_truth.score --page data/hand-truth/pages/imslp317803/0.json --record <file> --derive`.
"""
import json
import os
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

rec_path, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
doc = load_record(rec_path)
rec = doc["record"] if "record" in doc else doc


def on_page0(key):
    parts = key.split("/")
    return len(parts) < 2 or not parts[1].isdigit() or int(parts[1]) == 0


sub = {"observations": [o for o in rec["observations"] if on_page0(o["subject"])],
       "abstentions": [a for a in rec["abstentions"] if on_page0(a["subject"])]}
print("page-0 rows:", len(sub["observations"]), "obs,", len(sub["abstentions"]), "abs")
for flag, name in ((False, "off"), (True, "on")):
    if flag:
        os.environ["OMR_SLASH_AT_STEM_END"] = "1"
    else:
        os.environ.pop("OMR_SLASH_AT_STEM_END", None)
    log, _ = RR.rebuild_gather(sub)
    RR.run_stages(log)
    result = RR._to_result(log, doc, None)
    path = os.path.join(outdir, f"p0-{name}.record.json")
    json.dump(result, open(path, "w"))
    n = sum(1 for v in result["record"]["verdicts"]
            if v["quantity"] == "notehead_is_not_a_notehead" and v["reason"] == "tremolo_slash_crosses_stem")
    print(name, "->", path, "| tremolo-slash refusals:", n)
