"""Print the per-arm summaries written by replay.py side by side. usage: show.py OUTDIR TAG"""
import json
import sys

out, tag = sys.argv[1], sys.argv[2]
keys = ("xml_sha", "ly_sha", "notes", "rests", "bars_with_events", "bars_held_out_sum", "notes_held_out_sum",
        "held_doubled", "bars_partial", "partial_stay_held", "bars_written_red", "red_rows", "red_read",
        "red_guessed", "red_two_voice", "guessed", "notes_not_written_total", "ly_bars_written_red", "ly_notes_in_red",
        "ly_notes_not_written_total", "secs")
arms = {}
for a in ("off", "on", "off2"):
    try:
        arms[a] = json.load(open("%s/%s.%s.summary.json" % (out, tag, a)))
    except FileNotFoundError:
        pass
for k in keys:
    print("%-28s" % k, "  |  ".join("%s=%s" % (a, str(d.get(k))[:90]) for a, d in arms.items()))
