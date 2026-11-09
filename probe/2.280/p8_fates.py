"""2.280 probe 8 (STAGED ADJUDICATE + EXPORT, CURRENT tree, read-only): re-adjudicate the 20261104-night slices of the frozen sample pages
(lane_report mode `adjudicate`: rebuild_gather + run_stages, then the shipped export with `_place_notes` instrumented) and write, per notehead-classed
glyph box: the export fate, and the HEAD_STEM / DURATION / NOTEHEAD_IS_A_WHOLE_REST / HEAD_INK_IS_A_REST verdicts.
Control: fate counts printed; notes_not_written_total printed (a slice export counts the sample pages only).
usage: python3 probe/2.280/p8_fates.py litolff|brahms OUT.jsonl"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import export as EXPORT              # noqa: E402
from tools.omr.staged import lane_report as LR             # noqa: E402
from tools.omr.staged.review import rerun as RR            # noqa: E402
from tools.omr.staged.record import Q                      # noqa: E402

plate, outp = sys.argv[1:3]
CAP = {}
orig_place = EXPORT._place_notes


def place(rec, runs, **kw):
    CAP["rec"] = rec
    CAP["fates"] = kw.get("fates")
    return orig_place(rec, runs, **kw)


EXPORT._place_notes = place
rec = LR.load_slices(LR.slice_dir(plate, "20261104-night"))
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
result = {"record": log.to_json(), "summary": log.summary()}
del log
xml, report = EXPORT.to_musicxml(result)
r, fates = CAP["rec"], CAP["fates"]
print("notes_not_written_total", report["notes_not_written_total"], "written", report["written"].get("notes"))


def vd(q, sub):
    v = r.verdict(q, sub)
    if v is None:
        return None
    val = v.get("value")
    if isinstance(val, (list, dict)):
        val = "..."
    return [v["outcome"], v.get("reason"), val]


rows = []
for o in r.obs_of(Q.GLYPH_BOX):
    sub = o["subject"]
    if not r.obs(Q.NOTEHEAD_CLASS, sub):
        continue
    rows.append({"sub": sub, "cls": o["value"][0], "fate": fates.get(sub, "NO_FATE"),
                 "head_stem": vd(Q.HEAD_STEM, sub), "duration": vd(Q.DURATION, sub),
                 "not_a_head": vd(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub),
                 "whole_rest": vd(Q.NOTEHEAD_IS_A_WHOLE_REST, sub), "head_ink_rest": vd(Q.HEAD_INK_IS_A_REST, sub),
                 "pitch": vd(Q.PITCH, sub)})
with open(outp, "w") as f:
    for x in rows:
        f.write(json.dumps(x) + "\n")
print(len(rows), "rows;", dict(collections.Counter(x["fate"] for x in rows).most_common(12)))
