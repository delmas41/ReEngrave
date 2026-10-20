"""ROADMAP 2.173 (second half, Sean "Do both"): `OMR_WHOLE_NEEDS_HOLLOW_NO_STEM` -- RE-DECIDE ADJUDICATE..INFER over a whole record
(GATHER rows rebuilt, review.rerun) and export, with OMR_RED_BARS=1, whole-flag OFF vs ON.
usage: rerun_whole.py RECORD.json OUTDIR TAG ARMS(off,on)
Per arm: OUTDIR/TAG.w<arm>.musicxml, .summary.json (notes, whole notes in the file, red bars), .wholes.json (every written whole note
with its glyph/bar when in a red bar), .record.json (mini record of the judged quantities for `judged score`)."""
import collections
import json
import os
import re
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

path, outdir, tag, arms = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
os.makedirs(outdir, exist_ok=True)
JUDGED_Q = {"duration", "notehead_is_not_a_notehead", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest", "arc_kind"}
t0 = time.time()
result = load_record(path)
rec = result["record"]
print(tag, "loaded %.0fs" % (time.time() - t0), flush=True)
boxes, seen = [], set()
for o in rec["observations"]:
    s = o.get("subject") or ""
    if s.startswith("glyph/") and s not in seen and isinstance((o.get("detail") or {}).get("bbox_page_px"), list):
        seen.add(s)
        boxes.append({k: o.get(k) for k in ("id", "subject", "quantity", "detail")})
for arm in arms:
    os.environ["OMR_RED_BARS"] = "1"
    os.environ["OMR_WHOLE_NEEDS_HOLLOW_NO_STEM"] = "1" if arm == "on" else "0"
    t1 = time.time()
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    new = log.to_json()
    del log
    r2 = dict(result)
    r2["record"] = new
    xml, rep = E.to_musicxml(r2)
    base = os.path.join(outdir, "%s.w%s" % (tag, arm))
    open(base + ".musicxml", "w").write(xml)
    whole_all = len(re.findall(r"<note[^>]*>(?:(?!</note>).)*?<type>whole</type>", xml, flags=re.S)) - len(
        re.findall(r"<note[^>]*>(?:(?!</note>).)*?<rest[^>]*/?>(?:(?!</note>).)*?<type>whole</type>", xml, flags=re.S))
    red = rep.get("bars_written_red") or {}
    wholes = [dict(glyph=r.get("glyph"), bar=b["bar_key"], part=b["part"], status=r["status"], bar_words=b["words"])
              for b in red.get("bars_list", []) for r in b["rows"] if r["kind"] == "note" and r.get("type") == "whole"]
    summ = dict(tag=tag, arm=arm, notes=rep["written"]["notes"], rests=rep["written"]["rests"],
                whole_notes_in_file=whole_all, whole_notes_in_red_bars=len(wholes),
                bars_red=red.get("bars"), bars_held=(rep.get("bars_held_out_sum") or {}).get("bars"),
                notes_not_written=rep.get("notes_not_written_total"),
                abstained_whole=sum(1 for v in new["verdicts"] if v.get("reason") == "whole_class_filled_or_stemmed"),
                secs=round(time.time() - t1))
    json.dump(summ, open(base + ".summary.json", "w"), indent=1)
    json.dump(wholes, open(base + ".wholes.json", "w"))
    json.dump({"observations": boxes, "abstentions": [], "verdicts": [v for v in new["verdicts"] if v["quantity"] in JUDGED_Q]},
              open(base + ".record.json", "w"), default=str)
    print(json.dumps(summ), flush=True)
    del new, r2
