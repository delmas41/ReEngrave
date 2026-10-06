"""lane-local-staff-lines: do Sean's confirmed-right tiles keep their answers (position and owner) when the local
lines are fitted in windows? A tile whose head the audit did not touch has identical lines both ways (unchanged).
  python3 local_lines_confirmed.py <flips.json> <audit_lito.json> <audit_brah.json>"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slur_not_ledger_sean_tiles as T

flips = json.load(open(sys.argv[1]))
rows = {}
for p in sys.argv[2:]:
    for r in json.load(open(p))["rows"]:
        rows[r["subject"]] = r
lst = [(t[2], t[0], t[1]) for t in T.tiles()] + [("evs%d" % f["n"], f["which"], f["subject"]) for f in flips]
bad = 0
for name, which, s in lst:
    r = rows.get(s)
    if r is None:
        print("%-8s %-8s %-18s not a far head in the audit (unchanged)" % (name, which, s)); continue
    if "old" not in r:
        print("%-8s %-8s %-18s lines identical both ways: unchanged" % (name, which, s)); continue
    o, n = r["old"], r["new"]
    same = (o["pos"] == n["pos"]) and ((o["owner"], o["word"]) == (n["owner"], n["word"]))
    bad += (not same)
    print("%-8s %-8s %-18s pos %s -> %s | owner %s/%s -> %s/%s  %s" % (name, which, s, o["pos"], n["pos"], o["owner"], o["word"], n["owner"], n["word"], "SAME" if same else "CHANGED"))
print("confirmed-right tiles", len(lst), "changed", bad)
