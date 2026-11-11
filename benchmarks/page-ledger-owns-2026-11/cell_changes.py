"""2.284 probe (read only): what the page ledger's one settle changed, page-wide and in named cells (stroke-owner verdicts re-run OFF and ON on
the same GATHER rows).  usage: cell_changes.py RECORD PAGE [P/S/ST/CELL ...]"""
import collections
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.omr.staged import claim_readout as CR  # noqa: E402

src = CR.cut_record(pathlib.Path(sys.argv[1]))
pg = int(sys.argv[2])
want = [tuple(int(t) for t in w.split("/")) for w in sys.argv[3:]]
rows = CR.read_rows(src, [pg])
on = CR.owner_verdicts(rows, {"OMR_PAGE_LEDGER_OWNS": "1"})
off = CR.owner_verdicts(rows, {"OMR_PAGE_LEDGER_OWNS": "0"})
tot = collections.Counter()
pc = None
for ck, d in on.items():
    pl = d.get("page_ledger") or {}
    pc = pl.get("page") or pc
    for k, v in (pl.get("changed") or {}).items():
        tot[k] += v
print("page census:", pc)
print("stroke changes (cell strokes):", tot.most_common(15))
for w in want:
    d, o = on.get(w) or {}, off.get(w) or {}
    print(w, d.get("page_ledger"))
    so, sn = o.get("strokes", {}), d.get("strokes", {})
    for k in sorted(set(so) | set(sn), key=int):
        a, b = so.get(k, ["unclaimed", None, []]), sn.get(k, ["unclaimed", None, []])
        if a[:2] != b[:2]:
            print("   stroke", k, a[:3], "->", b[:3], [c[:6] for c in b[4]] if len(b) > 4 else "")
    print("   boxes off", o.get("boxes"))
    print("   boxes on ", d.get("boxes"))
