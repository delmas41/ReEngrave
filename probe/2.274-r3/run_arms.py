"""2.274 r3 diagnosis: replay Brahms p0 (injected slice) OFF and ON of OMR_PAGE_ARC_WRITE in one process; keep EVERY stage's rows for the census.
    python3 run_arms.py SLICES OUTDIR
Writes OUTDIR/{off,on}.record.json (full re-adjudicated record), {off,on}.musicxml (rg-stamped).  Changes no pipeline code."""
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"
from tools.omr.staged import lane_report as L  # noqa: E402
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

slices, out = sys.argv[1], pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for arm in ("off", "on"):
    os.environ["OMR_PAGE_ARC_WRITE"] = "1" if arm == "on" else "0"
    rec = L.load_slices(L.slice_dir("brahms", slices))
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    with L.traced_export():
        xml, report = E.to_musicxml(result)
    (out / ("%s.musicxml" % arm)).write_text(xml)
    (out / ("%s.record.json" % arm)).write_text(json.dumps(result["record"], default=str))
    (out / ("%s.report.json" % arm)).write_text(json.dumps(report, default=str)[:3000000])
    print(arm, len(result["record"]["observations"]), len(result["record"]["verdicts"]), flush=True)
