"""ROADMAP 2.7 step 5 — one REAL base-vs-arm gather of Litolff pdf-index 3.

Base: `python3 -m tools.omr.staged ... --pages 3 --no-surya --no-ocr` run from
an `origin/main` (`0e0f25da`) export of `tools/`. Arm: the same command on
this branch. Same weights, same env (`OMR_DIRECTION_TEXT_SCAN_GATE=1`,
`OMR_SURYA_KEEP_ALIVE=0`). Reports:

  * GATHER parity outside the new quantity (row counts by quantity, and
    whether every `glyph_box` is identical — detector jitter would show here);
  * verdict parity outside the accidental quantities;
  * the export of each (MusicXML re-rendered from the saved record by the
    ARM tree's exporter, so the only difference is the record);
  * the count-page window figures the gate names.

    python3 benchmarks/omr-accidental-2026-09/probe/real_gather_ab.py \\
        --base <base-p3.record.json> --arm <arm-p3.record.json> --out <json>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

ACC_Q = {"accidental_owner", "accidental", "accidental_staff_position"}


def _standing(rec):
    sup = {v.get("supersedes") for v in rec["verdicts"] if v.get("supersedes")}
    return {f'{v["subject"]}|{v["quantity"]}': json.dumps(
        [v["outcome"], v.get("value"), v.get("reason"), v.get("decider")],
        sort_keys=True, default=str)
        for v in rec["verdicts"] if v["id"] not in sup}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    B, A = load_record(a.base), load_record(a.arm)
    rb, ra = B["record"], A["record"]
    qb = collections.Counter(o["quantity"] for o in rb["observations"])
    qa = collections.Counter(o["quantity"] for o in ra["observations"])
    gather_diff = {q: [qb.get(q, 0), qa.get(q, 0)]
                   for q in set(qb) | set(qa) if qb.get(q) != qa.get(q)}
    gb = {o["subject"]: o["value"] for o in rb["observations"]
          if o["quantity"] == "glyph_box"}
    ga = {o["subject"]: o["value"] for o in ra["observations"]
          if o["quantity"] == "glyph_box"}
    vb, va = _standing(rb), _standing(ra)
    vdiff = collections.Counter(
        k.split("|", 1)[1] for k in set(vb) | set(va) if vb.get(k) != va.get(k))
    xb, repb = E.to_musicxml(B)
    xa, repa = E.to_musicxml(A)

    win = [v for v in ra["verdicts"] if v["quantity"] == "accidental_owner"
           and v["subject"].split("/")[2] == "0"
           and int(v["subject"].split("/")[3]) in (7, 8, 9, 10)
           and int(v["subject"].split("/")[4]) <= 7]
    out = {
        "base": a.base, "arm": a.arm,
        "provenance": [B.get("provenance"), A.get("provenance")],
        "gather_row_count_differences": gather_diff,
        "glyph_boxes_identical": gb == ga, "glyph_boxes": [len(gb), len(ga)],
        "standing_verdicts": [len(vb), len(va)],
        "verdict_differences_by_quantity": dict(vdiff),
        "verdict_differences_outside_accidental": {
            q: n for q, n in vdiff.items() if q not in ACC_Q},
        "notes_in_file": [xb.count("<note"), xa.count("<note")],
        "accidental_elements_page": [xb.count("<accidental"),
                                     xa.count("<accidental")],
        "alter_elements": [xb.count("<alter>"), xa.count("<alter>")],
        "accidental_reading_arm": repa.get("accidental_reading"),
        "status_census_balanced": [repb["status_census"]["balanced"],
                                   repa["status_census"]["balanced"]],
        "count_window_strings_bars_49_56": {
            "owner_verdicts": len(win),
            "decided": sum(v["outcome"] == "decided" for v in win),
            "abstained_by_reason": dict(collections.Counter(
                v["reason"] for v in win if v["outcome"] != "decided")),
        },
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
