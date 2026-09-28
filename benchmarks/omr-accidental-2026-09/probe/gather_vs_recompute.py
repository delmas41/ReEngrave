"""ROADMAP 2.7 step 5 — does `regather_accidentals.recompute_rows` reproduce
what a REAL gather files?

Input: a record gathered on the merged tree, which carries
`Q.ACCIDENTAL_STAFF_POSITION` rows from `gather.gather_accidental_positions`
itself. The recompute ignores those rows (it reads only `glyph_box`,
`cell_staff_space`, `notehead_staff_position`, `cell_box`, `staff_lines`) and
the two are joined by glyph subject.

⚠️ A CONTROL THAT CAN FAIL: `--perturb-half-step` scales every cell's
half_step by 1.01 before recomputing, and the agreement must break.

    python3 benchmarks/omr-accidental-2026-09/probe/gather_vs_recompute.py \\
        --record <arm-p3.record.json> --out <json>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "regather", HERE / "regather_accidentals.py")
regather = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(regather)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--perturb-half-step", action="store_true")
    a = ap.parse_args()
    rec = load_record(a.record)["record"]
    real = {o["subject"]: o for o in rec["observations"]
            if o["quantity"] == "accidental_staff_position"}
    if a.perturb_half_step:
        for o in rec["observations"]:
            if o["quantity"] == "cell_staff_space" and "half_step" in (
                    o.get("detail") or {}):
                o["detail"] = {**o["detail"],
                               "half_step": o["detail"]["half_step"] * 1.01}
    rows, ctl = regather.recompute_rows(rec, G)
    mine = {k: (p, d) for k, p, d in rows}
    both = sorted(set(real) & set(mine))
    diffs = [abs(real[k]["value"] - mine[k][0]) for k in both]
    detail_mismatch = [
        k for k in both
        if any(real[k]["detail"].get(f) != mine[k][1].get(f)
               for f in ("alteration", "detector_class", "rounded"))]
    by_route = {}
    for k in both:
        r = mine[k][1]["top_from"]
        d = abs(real[k]["value"] - mine[k][0])
        e = by_route.setdefault(r, {"n": 0, "exact_1e-9": 0, "max_abs": 0.0})
        e["n"] += 1
        e["exact_1e-9"] += d < 1e-9
        e["max_abs"] = max(e["max_abs"], d)
    out = {
        "record": a.record, "perturbed": a.perturb_half_step,
        "real_rows": len(real), "recomputed_rows": len(mine),
        "only_in_real": sorted(set(real) - set(mine))[:20],
        "only_in_recompute": sorted(set(mine) - set(real))[:20],
        "joined": len(both),
        "exact_within_1e-9": sum(d < 1e-9 for d in diffs),
        "max_abs_position_diff": max(diffs) if diffs else None,
        "rounded_or_class_mismatch": len(detail_mismatch),
        "by_top_route": by_route,
        "recompute_controls": ctl,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
