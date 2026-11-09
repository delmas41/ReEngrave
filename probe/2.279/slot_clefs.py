"""2.279: for each slot index, the clef verdicts of its staves over the whole record (READ-ONLY): is the slot's clef known elsewhere?

usage: python3 probe/2.279/slot_clefs.py RECORD SLOT [SLOT...]
"""
import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.record_io import load_record      # noqa: E402

d = load_record(sys.argv[1])
want = {int(x) for x in sys.argv[2:]}
from tools.omr.staged.export import Record          # noqa: E402
verds = Record(d).verdicts
slot = {}
clef = {}
for v in verds:
    if v["quantity"] == "slot_index" and v["outcome"] == "decided":
        slot[v["subject"]] = v["value"]
    elif v["quantity"] == "clef":
        clef[v["subject"]] = (v["outcome"], v["value"] if v["outcome"] == "decided" else tuple(sorted(str(c.get("value")) for c in v.get("candidates") or ())))
for s in sorted(want):
    c = collections.Counter(clef.get(sub) for sub, sl in slot.items() if sl == s)
    print("slot", s, c.most_common(8))
