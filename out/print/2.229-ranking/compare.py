"""2.229: compare symbols.json files by place (lane_report.diff_arms) and count kinds per page.
usage: compare.py PLATE A.json B.json"""
import json, sys, collections
from tools.omr.staged import lane_report as L
plate, a, b = sys.argv[1:4]
A, B = json.load(open(a)), json.load(open(b))
d = L.diff_arms(A, B, tol=0.5 * L.PLATES[plate]["unit"])
print(plate, "A=", a.split("/")[-3:], "B=", b.split("/")[-3:])
print(L.format_counts(d["counts"]))
print("paired", d["paired"], "hosts", d["hosts"], "red", A["red_bars"], B["red_bars"], "blue", A["blue_marks"], B["blue_marks"], "not written", A["notes_not_written"], B["notes_not_written"])
