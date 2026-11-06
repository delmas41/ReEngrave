"""For a tie / bound-slur end that is not a written note: is its whole BAR (cell) unwritten, or only the head? (measure only)
python3 missing_heads2.py LEDGER.json MUSICXML"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import written as W

led = json.load(open(sys.argv[1]))
wr = W.parse(pathlib.Path(sys.argv[2]).read_text())
notes = wr["notes"]
cells_written = collections.Counter("/".join(k.split("/")[:5]) for k in notes)
c = collections.Counter()
for r in led["rows"]:
    if r.get("lost_rule") not in ("export:tie_not_in_file", "export:slur_bound_not_in_file"):
        continue
    for end, k in zip(("start", "stop"), r["pair"]):
        if k in notes:
            continue
        cell = "/".join(k.split("/")[:5])
        c[(r["lost_rule"][7:], "bar_has_no_written_note" if cells_written[cell] == 0 else "bar_written_head_missing")] += 1
for k, v in c.most_common():
    print(v, k)
