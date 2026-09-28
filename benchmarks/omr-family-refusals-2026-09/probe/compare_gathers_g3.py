"""BASE vs ARM gather, one tree — the price of the GATHER half of 3.4g-3.

    python3 .../compare_gathers_g3.py <base.record.json> <arm.record.json> --out <json>

Both records must carry the SAME provenance commit and `dirty: False`, or
this exits 3 (an A/B across trees is not an A/B).

Reports: the detector's box set (jitter control: identical box lists means
every difference below is the change's); the ledger tally both sides; every
verdict that moved, by quantity, named; `<note>` count of each file through
`staged.export`; the census; `Q.LEDGER_INK_UNDER` rows filed.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path.cwd()))

from tools.omr.staged import export as SX                  # noqa: E402
from tools.omr.staged.record import Q                      # noqa: E402
from tools.omr.staged.record_io import load_record         # noqa: E402


def word(v):
    if v["outcome"] != "decided":
        return f"ABSTAINED:{v.get('reason')}"
    if v["quantity"] == Q.LEDGER_IS_NOT_A_LEDGER:
        return (f"refused:{v.get('reason')}" if v["value"] is True
                else f"kept:{v.get('reason')}")
    return f"{json.dumps(v.get('value'), default=str)}|{v.get('reason')}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("arm")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    B, A = load_record(a.base), load_record(a.arm)
    pb, pa = B.get("provenance") or {}, A.get("provenance") or {}
    if (pb.get("commit") != pa.get("commit") or pb.get("dirty") is not False
            or pa.get("dirty") is not False):
        print("PROVENANCE REFUSED:", pb, pa)
        return 3
    rb, ra = B["record"], A["record"]

    def boxes(r):
        return sorted((o["subject"], json.dumps(o["value"]))
                      for o in r["observations"]
                      if o["quantity"] == Q.GLYPH_BOX)
    bb, ba = boxes(rb), boxes(ra)
    n_ink = sum(1 for o in ra["observations"]
                if o["quantity"] == Q.LEDGER_INK_UNDER)
    n_ink_abs = sum(1 for o in ra.get("abstentions", [])
                    if o["quantity"] == Q.LEDGER_INK_UNDER)
    n_ink_base = sum(1 for o in rb["observations"]
                     if o["quantity"] == Q.LEDGER_INK_UNDER)

    vb = {(v["quantity"], v["subject"]): v for v in rb["verdicts"]}
    va = {(v["quantity"], v["subject"]): v for v in ra["verdicts"]}
    moved = collections.Counter()
    named = collections.defaultdict(list)
    for k in sorted(set(vb) | set(va)):
        wb = word(vb[k]) if k in vb else "<absent>"
        wa = word(va[k]) if k in va else "<absent>"
        if wb != wa:
            moved[k[0]] += 1
            if len(named[k[0]]) < 20:
                named[k[0]].append({"subject": k[1], "base": wb, "arm": wa})

    def tally(vs):
        c = collections.Counter(word(v) for k, v in vs.items()
                                if k[0] == Q.LEDGER_IS_NOT_A_LEDGER)
        return dict(sorted(c.items()))

    xb, repb = SX.to_musicxml(B)
    xa, repa = SX.to_musicxml(A)
    out = {
        "provenance": {"commit": pa.get("commit"), "dirty": pa.get("dirty")},
        "detector_boxes": {"base": len(bb), "arm": len(ba),
                           "identical": bb == ba},
        "ledger_ink_rows": {"base": n_ink_base, "arm": n_ink,
                            "arm_abstentions": n_ink_abs},
        "ledger_tally": {"base": tally(vb), "arm": tally(va)},
        "verdicts_moved_by_quantity": dict(sorted(moved.items())),
        "verdicts_moved_named": dict(named),
        "notes": {"base": xb.count("<note"), "arm": xa.count("<note")},
        "musicxml_identical": xb == xa,
        "notes_not_written_identical":
            repb.get("notes_not_written") == repa.get("notes_not_written"),
        "family_refusals_ledger": {
            "base": (repb.get("family_refusals") or {}).get(
                Q.LEDGER_IS_NOT_A_LEDGER),
            "arm": (repa.get("family_refusals") or {}).get(
                Q.LEDGER_IS_NOT_A_LEDGER)},
        "census_unaccounted": {
            "base": (repb.get("status_census") or {}).get("unaccounted"),
            "arm": (repa.get("status_census") or {}).get("unaccounted")},
    }
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items()
                      if k != "verdicts_moved_named"}, indent=1, default=str))
    print(json.dumps(out["verdicts_moved_named"], indent=1)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
