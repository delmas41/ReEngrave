"""ROADMAP 2.179 -- re-decide ADJUDICATE..INFER over a through-adjudicate record and EXPORT (MusicXML + LilyPond), red bars on.

usage: python3 benchmarks/omr-unseen-symbols-2026-10/probe/e1_export.py RECORD.json OUTDIR TAG [ENV=VAL ...]
ENV=VAL pairs are set before the stages run (an A/B arm's flag). Writes OUTDIR/TAG.musicxml, .ly, .summary.json,
.red_rows.json (every red bar with its rows and glyph ids) and .judged.record.json (the judged quantities only, for
`python3 -m tools.omr.staged.judged score`). Prints the summary line.
"""
import json
import os
import sys
import time

sys.path.insert(0, ".")
path, outdir, tag = sys.argv[1], sys.argv[2], sys.argv[3]
for kv in sys.argv[4:]:
    k, v = kv.split("=", 1)
    os.environ[k] = v
os.environ.setdefault("OMR_RED_BARS", "1")

from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged import lilypond as LY  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

JUDGED_Q = {"duration", "notehead_is_not_a_notehead", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest", "arc_kind"}
os.makedirs(outdir, exist_ok=True)
t0 = time.time()
result = load_record(path)
rec = result["record"]
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
new = log.to_json()
del log
r2 = dict(result)
r2["record"] = new
xml, rep = E.to_musicxml(r2)
ly, lrep = LY.to_lilypond(r2)
base = os.path.join(outdir, tag)
open(base + ".musicxml", "w").write(xml)
open(base + ".ly", "w").write(ly)
w = rep["written"]
red = rep.get("bars_written_red") or {}
held = rep.get("bars_held_out_sum") or {}
summ = dict(tag=tag, env={kv.split("=")[0]: kv.split("=", 1)[1] for kv in sys.argv[4:]},
            notes=w.get("notes"), rests=w.get("rests"), bars_with_events=w.get("bars_with_events"),
            bars_red=red.get("bars"), red_rows=red.get("noteheads_and_rests"), red_read=red.get("read"),
            red_guessed=red.get("guessed"), bars_held=held.get("bars"),
            unread_empty=(rep.get("unread_empty_bars") or {}).get("bars"),
            notes_not_written=rep.get("notes_not_written_total"),
            ly_red=(lrep.get("written") or {}).get("bars_written_red"),
            secs=round(time.time() - t0))
try:
    from tools.omr import acceptance as A
    summ["bars_add_up_control"] = A.bars_add_up(xml)
except Exception as exc:  # noqa: BLE001
    summ["bars_add_up_control"] = "error %s" % type(exc).__name__
json.dump(summ, open(base + ".summary.json", "w"), indent=1, default=str)
json.dump(red.get("bars_list", []), open(base + ".red_rows.json", "w"))
boxes, seen = [], set()
for o in new["observations"]:
    s = o.get("subject") or ""
    if s.startswith("glyph/") and s not in seen and isinstance((o.get("detail") or {}).get("bbox_page_px"), list):
        seen.add(s)
        boxes.append({k: o.get(k) for k in ("id", "subject", "quantity", "detail")})
json.dump({"observations": boxes, "abstentions": [], "verdicts": [v for v in new["verdicts"] if v["quantity"] in JUDGED_Q]},
          open(base + ".judged.record.json", "w"), default=str)
print(json.dumps(summ, default=str), flush=True)
