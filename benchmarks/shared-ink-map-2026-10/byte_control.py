"""ROADMAP 2.195: the record-level control. usage: byte_control.py OFF.gathered.record.json ON.gathered.record.json
Drops every Q.STROKE row (and its glyph subjects) from the ON record, renumbers nothing -- compares the remaining observations / abstentions as a multiset of
(subject, quantity, value, reader, frame, detail) (not in order: Surya's direction words come and go run to run), ids (also inside a detail), timings and basis excluded (a new row shifts every later id). Prints the number of differing
rows per quantity and the first few. Surya-dependent fields vary run to run on UNCHANGED code (benchmarks/gather-speed-2026-10/FINDINGS.md), so the
differences are listed by quantity, not hidden."""
import json, sys, collections
sys.path.insert(0, ".")
from tools.omr.staged import record_io


import re
_ID = re.compile(r"obs:\d+|abs:\d+")
_MS = re.compile(r'"ms": [0-9.]+')


def norm(r):
    d = json.dumps(r.get("detail") or r.get("note") or r.get("reason"), sort_keys=True, default=str)
    d = _MS.sub('"ms": 0', _ID.sub("ID", d))             # ids shift when rows are inserted; timings are not data
    return (r["subject"], r["quantity"], json.dumps(r.get("value"), sort_keys=True), r.get("reader"), r.get("frame"), d)


a = record_io.load_record(sys.argv[1])["record"]
b = record_io.load_record(sys.argv[2])["record"]
out = {}
for part in ("observations", "abstentions"):
    A = collections.Counter(norm(r) for r in a[part])
    B = collections.Counter(norm(r) for r in b[part] if r["quantity"] != "stroke")
    onlyA, onlyB = A - B, B - A
    by = collections.Counter()
    for k, v in onlyA.items():
        by[k[1]] += v
    for k, v in onlyB.items():
        by[k[1]] += v
    out[part] = dict(off=sum(A.values()), on_without_stroke=sum(B.values()), differing=sum(by.values()), by_quantity=dict(by))
    print(part, "OFF", sum(A.values()), "ON-minus-stroke", sum(B.values()), "rows in only one arm", sum(by.values()), dict(by))
    for k in list(onlyA)[:2]:
        print("    OFF only:", k[:2], k[5][:200])
    for k in list(onlyB)[:2]:
        print("    ON only: ", k[:2], k[5][:200])
print("stroke rows in ON:", sum(1 for r in b["observations"] if r["quantity"] == "stroke"),
      "| stroke abstentions:", sum(1 for r in b["abstentions"] if r["quantity"] == "stroke"))
