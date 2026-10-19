"""2.167 probe 1: one row per notehead-classed glyph box of a record, with the
exporter's own fate (instrumented, not re-decided) and the verdicts that bear on
it. READ-ONLY. Control: our fate counts reproduce export's notes_not_written.

usage: python3 probe/2.167/p1_table.py RECORD OUT_PREFIX
"""
import collections
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import export as EXPORT          # noqa: E402
from tools.omr.staged.record_io import load_record      # noqa: E402
from tools.omr.staged.record import Q                   # noqa: E402

CAP = {}
orig_place = EXPORT._place_notes


def place(rec, runs, **kw):
    CAP["rec"] = rec
    CAP["fates"] = kw.get("fates")
    return orig_place(rec, runs, **kw)


EXPORT._place_notes = place

path, outp = sys.argv[1], sys.argv[2]
t = time.time()
if len(sys.argv) > 3 and sys.argv[3] == "slim":
    # SLIM LOAD (Brahms is 7 GB; full load ~50 GB RSS). Drop the two bulky id-list fields no reader here consults
    # (`considered`, `correlated`); `basis`/`used` are kept. The Litolff control proves the slim run reproduces the full one.
    import json as _json
    from tools.omr.staged.record_io import expand_result

    def _hook(o):
        if "quantity" in o and "outcome" in o:
            o.pop("considered", None)
            o.pop("correlated", None)
        return o

    d = expand_result(_json.loads(Path(path).read_text(), object_hook=_hook))
else:
    d = load_record(path)
print("loaded", round(time.time() - t), "s", flush=True)
xml, report = EXPORT.to_musicxml(d)
rec, fates = CAP["rec"], CAP["fates"]
print("exported", round(time.time() - t), "s; notes_not_written_total",
      report["notes_not_written_total"], flush=True)
nnw = report["notes_not_written"]


def vd(q, sub):
    v = rec.verdict(q, sub)
    if v is None:
        return None
    val = v.get("value")
    if isinstance(val, (list, dict)):
        val = "..."
    return [v["outcome"], v.get("reason"), val]


held = {(b["page"], b["system"], b["staff"], b["cell"])
        for b in report["bars_held_out_sum"]["held"]}
partial = {(b["page"], b["system"], b["staff"], b["cell"]): b
           for b in report["partial_bars"]["bars"] if b["status"] == "partial"}

rows = []
for o in rec.obs_of(Q.GLYPH_BOX):
    sub = o["subject"]
    if not rec.obs(Q.NOTEHEAD_CLASS, sub):
        continue
    p = sub.split("/")   # glyph/page/system/staff/cell/...
    cellk = (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
    fate = fates.get(sub, "NO_FATE")
    r = {"sub": sub, "cls": o["value"][0],
         "is_rest_obs": bool(rec.obs(Q.REST, sub)),
         "fate": fate, "held_cell": cellk in held, "partial_cell": cellk in partial,
         "bbox": (o.get("detail") or {}).get("bbox_page_px"),
         "head_stem": vd(Q.HEAD_STEM, sub), "stem_value": vd(Q.STEM_VALUE, sub),
         "stem_dir": vd(Q.STEM_DIRECTION, sub), "duration": vd(Q.DURATION, sub),
         "position": vd(Q.NOTEHEAD_POSITION, sub), "pitch": vd(Q.PITCH, sub),
         "not_a_head": vd(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub),
         "whole_rest": vd(Q.NOTEHEAD_IS_A_WHOLE_REST, sub),
         "head_ink_rest": vd(Q.HEAD_INK_IS_A_REST, sub),
         "owner": vd(Q.GLYPH_OWNER, sub)}
    rows.append(r)
with open(outp + ".rows.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
fc = collections.Counter(r["fate"] for r in rows)
summ = {"n_rows": len(rows), "fates": dict(fc), "notes_not_written": nnw,
        "notes_written_report": report["written"].get("notes"),
        "bars_held_out_sum_rows": report["bars_held_out_sum"]["noteheads_and_rests"],
        "rows_in_gaps": report["partial_bars"]["rows_in_gaps"],
        "held_cells": len(held), "partial_cells": len(partial)}
Path(outp + ".summary.json").write_text(json.dumps(summ, indent=1))
print(json.dumps(summ)[:3000])
