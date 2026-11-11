"""2.300: cut the REAL gather rows of named bars out of the saved night slice into a small committed fixture.
    python3 benchmarks/one-chord-one-event-2026-11/cut_fixture.py PLATE OUT.json page/system/staff/cell [...]
Keeps every row whose subject is the bar's cell, any glyph of it, its staff, its system, its page, or the document (rows
of other staves are dropped). Rows are GATHER rows exactly as saved; nothing is edited.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as LR  # noqa: E402
from tools.omr.staged import conservation as C  # noqa: E402

plate, out = sys.argv[1], sys.argv[2]
bars = [tuple(int(x) for x in a.split("/")) for a in sys.argv[3:]]
d = LR.slice_dir(plate, C.DEFAULT_TAG)
#: rows that name rows of OTHER places (a replay cannot re-point them); the cell-level decisions do not read them
DROP_QUANTITIES = {"claimed_area"}


def keep(subject):
    p = subject.split("/")
    if p[0] in ("document", "doc", "work") or len(p) == 1:
        return True
    try:
        nums = tuple(int(x) for x in p[1:])
    except ValueError:
        return True
    for pg, sy, st, ce in bars:
        if p[0] in ("glyph", "cell") and nums[:4] == (pg, sy, st, ce):
            return True
        if p[0] == "staff" and nums[:3] == (pg, sy, st):
            return True
        if p[0] == "system" and nums[:2] == (pg, sy):
            return True
        if p[0] == "page" and nums[:1] == (pg,):
            return True
    return False


res = {"verdicts": [], "plate": plate, "bars": [list(b) for b in bars]}
for kind in ("observations", "abstentions"):
    rows = []
    with open(d / (kind + ".jsonl")) as fh:
        for line in fh:
            it = json.loads(line)
            if keep(it["subject"]) and it["quantity"] not in DROP_QUANTITIES:
                rows.append(it)
    res[kind] = rows
json.dump(res, open(out, "w"), separators=(",", ":"))
print(out, {k: len(v) for k, v in res.items() if isinstance(v, list)})
