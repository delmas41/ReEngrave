"""ROADMAP 2.173 -- replay EXPORT only (MusicXML + LilyPond) over a whole 20261018-night record, flag OFF vs ON.

usage: python3 benchmarks/omr-red-bars-2026-10/replay.py RECORD.json OUTDIR TAG [ARMS]
       ARMS: comma list from off,on,off2 (default off,on,off2). Loads the record ONCE (Brahms is ~7 GB); `off2` is a second
       OFF run after ON in the same process -- it must equal `off` byte for byte (the exporter must not mutate the record).
Writes OUTDIR/TAG.<arm>.musicxml, .ly, .summary.json (+ .red_rows.json for `on`: every red bar's rows with READ/GUESSED
and glyph ids), and prints one JSON line per arm. No PDF here (that is a separate lilypond call on the .ly).
"""
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged import lilypond as LY  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

rec_path, outdir, tag = sys.argv[1], sys.argv[2], sys.argv[3]
arms = (sys.argv[4] if len(sys.argv) > 4 else "off,on,off2").split(",")
os.makedirs(outdir, exist_ok=True)
t0 = time.time()
result = load_record(rec_path)
print(tag, "loaded %.0fs" % (time.time() - t0), flush=True)


def sha(t):
    return hashlib.sha256(t.encode()).hexdigest()[:16]


for arm in arms:
    os.environ["OMR_RED_BARS"] = "1" if arm == "on" else "0"
    t1 = time.time()
    xml, rep = E.to_musicxml(result)
    ly, lrep = LY.to_lilypond(result)
    base = os.path.join(outdir, "%s.%s" % (tag, arm))
    open(base + ".musicxml", "w").write(xml)
    open(base + ".ly", "w").write(ly)
    w = rep["written"]
    pb = rep.get("partial_bars", {})
    red = rep.get("bars_written_red")
    summ = dict(
        tag=tag, arm=arm, xml_sha=sha(xml), ly_sha=sha(ly), xml_bytes=len(xml), ly_bytes=len(ly),
        notes=w.get("notes"), rests=w.get("rests"), measure_rests_read=w.get("measure_rests_read"),
        noteheads_in_log=(rep.get("balance") or {}).get("noteheads_in_log"),
        bars_with_events=w.get("bars_with_events"),
        bars_held_out_sum=(rep.get("bars_held_out_sum") or {}).get("bars"),
        notes_held_out_sum=(rep.get("bars_held_out_sum") or {}).get("noteheads_and_rests"),
        held_doubled=(rep.get("bars_held_out_sum") or {}).get("bars_on_a_doubled_staff"),
        bars_partial=w.get("bars_partial"), partial_stay_held=pb.get("stay_held_by_reason"),
        bars_written_red=(red or {}).get("bars"), red_rows=(red or {}).get("noteheads_and_rests"),
        red_read=(red or {}).get("read"), red_guessed=(red or {}).get("guessed"),
        red_two_voice=(red or {}).get("two_voice"),
        unread_empty=(rep.get("unread_empty_bars") or {}).get("bars"),
        guessed=rep.get("guessed"),
        notes_not_written_total=rep.get("notes_not_written_total"),
        notes_not_written=rep.get("notes_not_written"),
        ly_notes_not_written_total=lrep.get("notes_not_written_total"),
        ly_bars_written_red=(lrep.get("written") or {}).get("bars_written_red"),
        ly_notes_in_red=(lrep.get("written") or {}).get("notes_written_in_red_bars"),
        secs=round(time.time() - t1))
    json.dump(summ, open(base + ".summary.json", "w"), indent=1, default=str)
    if red:
        json.dump(red["bars_list"], open(base + ".red_rows.json", "w"), default=str)
    if arm == "off":
        # the held list, to compare with the red list (same bars, same events)
        json.dump((rep.get("bars_held_out_sum") or {}).get("held"), open(base + ".held.json", "w"), default=str)
        json.dump(pb.get("bars"), open(base + ".partial.json", "w"), default=str)
    print(json.dumps(summ, default=str), flush=True)
