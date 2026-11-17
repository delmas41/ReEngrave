"""ROADMAP 2.313 -- the shared file-change counting between two arms of one plate (lane_report's own diff, nothing rebuilt).

    PYTHONPATH=. python3 benchmarks/landing-check-2026-11/compare.py WORKROOT litolff BASE_ARM OTHER_ARM [...]

Each arm's files are WORKROOT/<arm>/litolff.<arm>.symbols.json + .mini-record.json (written by `lane_report arm`). Prints the same
`file:` line, red bars and Sean's judged moves (`lane_report.diff_arms`, `format_counts`, `judged_moves`) for BASE_ARM -> each OTHER_ARM.
"""
import json
import pathlib
import sys

from tools.omr.staged import lane_report as LR

root, plate, base = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]


def load(arm):
    d = root / arm
    return json.loads((d / ("%s.%s.symbols.json" % (plate, arm))).read_text()), d / ("%s.%s.mini-record.json" % (plate, arm))


b, bm = load(base)
for arm in sys.argv[4:]:
    o, om = load(arm)
    d = LR.diff_arms(b, o, tol=0.5 * LR.PLATES[plate]["unit"])
    jm = LR.judged_moves(bm, om, plate, b["hosts"], o["hosts"])
    print("%s -> %s" % (base, arm))
    print("  file:   " + LR.format_counts(d["counts"]))
    print("  notes+rests %d -> %d (%d paired) | red bars %s -> %s | notes not written %s -> %s" % (
        d["hosts"][0], d["hosts"][1], d["paired"], b["red_bars"], o["red_bars"], b["notes_not_written"], o["notes_not_written"]))
    print("  judged:", json.dumps(jm, default=str)[:600])
