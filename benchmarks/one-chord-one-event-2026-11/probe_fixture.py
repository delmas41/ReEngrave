"""probe: replay a cut fixture through ADJUDICATE..EXPORT; print the events and the bar's report row."""
import json
import os
import sys

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
sys.path.insert(0, ".")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

rec = json.load(open(sys.argv[1]))
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
xml, report = E.to_musicxml({"record": log.to_json(), "summary": log.summary()})
print(len(xml), report["bars_written_red"]["count"] if "count" in report["bars_written_red"] else report["bars_written_red"].keys())
print([ (b["bar_key"], b["want_quarters"], b["counted_quarters"]) for b in report["bars_written_red"]["bars_list"]])
print(report["partial_bars"]["bars"][:3])
