"""2.284 ARC FALSIFIER (read only): head boxes whose ink an ARC claim holds (`claim_final` held, by arc_trace / arc), OFF vs ON.

The stroke owner is re-run on each arm's own GATHER rows with its own flag (OFF record + flag 0, ON record + flag 1: the arc claim is a GATHER row).
A head box held >= 0.5 by the arc in the ON arm means the slur's traced pixels still run through the head outline (the falsifier of the 2.283 audit).

    usage: arc_held_probe.py OFF_RECORD ON_RECORD PAGE [PAGE ...]
"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.omr.staged import claim_readout as CR  # noqa: E402


def held(rec, pages, flag):
    src = CR.cut_record(pathlib.Path(rec))
    out = {}
    for pg in pages:
        rows = CR.read_rows(src, [pg])
        for ck, d in CR.owner_verdicts(rows, {"OMR_PAGE_LEDGER_OWNS": flag}).items():
            for key, e in ((d.get("claim_final") or {}).get("held") or {}).items():
                if e.get("by") in ("arc_trace", "arc") and "/" in key:
                    out[key] = e["share"]
    return out


off_rec, on_rec = sys.argv[1], sys.argv[2]
pages = [int(p) for p in sys.argv[3:]]
off, on = held(off_rec, pages, "0"), held(on_rec, pages, "1")
heads = lambda m: {k: v for k, v in m.items()}
res = {"off_held_ge_0.5": sorted(k for k, v in off.items() if v >= 0.5), "on_held_ge_0.5": sorted(k for k, v in on.items() if v >= 0.5),
       "off_held_near": len(off), "on_held_near": len(on),
       "still_held_ge_0.5": sorted(k for k in off if off[k] >= 0.5 and on.get(k, 0) >= 0.5),
       "shares": {k: [off.get(k), on.get(k)] for k in sorted(set(off) | set(on))}}
print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in res.items() if k != "shares"}))
print("still held >= 0.5 ON:", res["still_held_ge_0.5"])
json.dump(res, open(pathlib.Path(__file__).parent / "out" / "r4" / "arc_held.json", "w"), indent=1)
