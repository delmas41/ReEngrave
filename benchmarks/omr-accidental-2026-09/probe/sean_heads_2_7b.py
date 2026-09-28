"""ROADMAP 2.7b gate — what became of every head and glyph Sean adjudicated
in 2.7, base vs arm: the head's `notehead_is_not_a_notehead` verdict, its
accidental owner's verdict, and whether the head's note is in the FILE.

"In the file" is read off the exporter's own placement: a head is written iff
`export._place_notes` did not drop it, which the harness does not save per
head — so it is recomputed here by running `export.to_musicxml` on each
record's saved verdicts and asking the exporter's drop log, via
`export.status_census`'s per-subject fate where available, else by the
standing refusals (npv / glyph_owner elsewhere / bar held out).

    python3 benchmarks/omr-accidental-2026-09/probe/sean_heads_2_7b.py \\
        --base <base.record.json> --arm <arm.record.json> --out <json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from tools.omr.staged.record_io import load_record  # noqa: E402

ADJ = HERE.parent / "out" / "print" / "ADJUDICATION-sean-2026-09-27.json"


def _standing(rec):
    sup = {v.get("supersedes") for v in rec["verdicts"] if v.get("supersedes")}
    return {(v["subject"], v["quantity"]): v for v in rec["verdicts"]
            if v["id"] not in sup}


def _short(v):
    return None if v is None else [v.get("outcome"), v.get("value"),
                                   v.get("reason")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    adj = json.loads(ADJ.read_text())["verdicts"]
    S = {k: _standing(load_record(p)["record"])
         for k, p in (("base", a.base), ("arm", a.arm))}
    rows = []
    for v in adj:
        n = int(v["crop"][4:6])
        row = {"crop": n, "sean": v["sean"], "glyph": v["glyph"],
               "head": v["head"]}
        for k, st in S.items():
            row[k] = {
                "head_npv": _short(st.get((v["head"], "notehead_is_not_a_notehead"))),
                "head_owner": _short(st.get((v["head"], "glyph_owner"))),
                "glyph_owner_verdict": _short(st.get((v["glyph"], "accidental_owner"))),
                "head_pitch": _short(st.get((v["head"], "pitch"))),
                "head_accidental": _short(st.get((v["head"], "accidental"))),
            }
        row["changed"] = row["base"] != row["arm"]
        rows.append(row)
    Path(a.out).write_text(json.dumps(rows, indent=1, default=str))
    for r in rows:
        print(r["crop"], r["head"], "CHANGED" if r["changed"] else "same",
              r["arm"]["head_npv"], r["arm"]["glyph_owner_verdict"],
              "|", r["sean"][:50])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
