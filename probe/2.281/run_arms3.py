"""2.281: replay one plate's injected slice (benchmarks/.../step2/build_inject.py) in ONE process under named arms; keep every stage's rows.
    python3 run_arms3.py PLATE SLICES OUTDIR ARM[,ARM...]
ARM: base (OMR_PAGE_ARC_WRITE=0: main's behaviour), write (OMR_PAGE_ARC_WRITE=1), meet (write + OMR_ARC_MEETING_AT_HEAD=1).
Writes OUTDIR/<plate>.<arm>.{record.json,musicxml}. No pipeline code changed here."""
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

plate, slices, out, arms = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]), sys.argv[4].split(",")
out.mkdir(parents=True, exist_ok=True)
for arm in arms:
    os.environ["OMR_PAGE_ARC_WRITE"] = "0" if arm == "base" else "1"
    os.environ["OMR_ARC_MEETING_AT_HEAD"] = "1" if arm == "meet" else "0"
    rec = L.load_slices(L.slice_dir(plate, slices))
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    with L.traced_export():
        xml, report = E.to_musicxml(result)
    (out / ("%s.%s.musicxml" % (plate, arm))).write_text(xml)
    (out / ("%s.%s.record.json" % (plate, arm))).write_text(json.dumps(result["record"], default=str))
    (out / ("%s.%s.report.json" % (plate, arm))).write_text(json.dumps(report, default=str)[:3000000])
    print(plate, arm, len(result["record"]["observations"]), len(result["record"]["verdicts"]), flush=True)
