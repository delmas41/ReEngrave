"""ROADMAP 2.97 -- re-decide a saved record on THIS tree and export. Usage:
   python3 run_2_97.py REC.json OUT_REPORT.json OUT.musicxml [LOG.pickle]
Writes the export report (json; NOT the record -- GBs), the MusicXML and,
if asked, the pickled post-INFER Log (for the probes beside this file).
Arm and base differ only in the environment: OMR_NARROWED_BAR=1 for the arm."""
import json
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged import export as EXPORT  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun  # noqa: E402

t = time.time()
doc = load_record(sys.argv[1])
rec = doc["record"] if "record" in doc else doc
import os  # noqa: E402
if os.environ.get("PAGES_MAX") is not None:
    # SMALL re-decide: keep only the GATHER rows of pages 0..PAGES_MAX (and
    # the document-level ones). A control on Sean's hand-truth page, not a
    # substitute for the whole movement.
    from tools.omr.staged.record import Subject  # noqa: E402
    pmax = int(os.environ["PAGES_MAX"])
    rec = dict(rec)
    for k in ("observations", "abstentions"):
        rec[k] = [r for r in rec.get(k) or ()
                  if Subject.from_key(r["subject"]).page is None
                  or Subject.from_key(r["subject"]).page <= pmax]
log, _ = rerun.rebuild_gather(rec)
rerun.run_stages(log)
if len(sys.argv) > 4:
    import pickle
    pickle.dump(log, open(sys.argv[4], "wb"), protocol=5)
result = {"record": log.to_json(), "summary": log.summary()}
xml, report = EXPORT.to_musicxml(result)
open(sys.argv[3], "w").write(xml)
json.dump(report, open(sys.argv[2], "w"), default=str)
b = report["bars_held_out_sum"]
print("done", round(time.time() - t), "held", b["bars"], "notes",
      report["written"].get("notes"), "narrowed_not_written",
      report["notes_not_written"].get("duration_narrowed"))
