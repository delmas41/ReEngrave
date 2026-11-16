"""2.306 r14: the duration verdict's flag/beam evidence for glyphs named in a tally json (r14_flag_tally.py) by kind/what.
Usage: r14_dur_detail.py REC.json TALLY.json KIND WHAT"""
import json
import sys

from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1])["record"]
rows = [r for r in json.load(open(sys.argv[2])) if r["kind"] == sys.argv[3] and r["what"] == sys.argv[4] and r.get("rg")]
want = {r["rg"]: r for r in rows}
KEYS = ("flags_attached", "flag_levels", "beams_by_stem", "stems_attached", "levels_certain", "levels_possible", "yolo_kept", "beams_neighbour_staff",
        "beams_decided_arc", "beams_not_by_ink")
for v in rec["verdicts"]:
    if v["quantity"] == "duration" and v["subject"] in want:
        d = v.get("detail") or {}
        print(want[v["subject"]]["id"], v["subject"], v["outcome"], v.get("reason"), {k: d.get(k) for k in KEYS})
