"""Per-row and pooled delta between a control arm and a range-veto arm.

    python3 benchmarks/omr-range-veto-2026-09/compare_arms.py \
        --control /tmp/control-contest.json --arm /tmp/arm-label.json --name label

⚠️ THE 20-ROW GATE'S NOISE FLOOR IS >= +/-6 EDITS. The byte-determinism this
gate's older findings claim held on the FIVE-row era and does not hold at 20
rows, so a per-row or pooled move under 6 edits is not evidence of anything.
`0.8444` is likewise not a baseline for this tree — the control arm here is
measured on the same merge base as the treatment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

NOISE = 6


def rows_of(doc: dict) -> dict[str, dict]:
    """row_id -> row, with the ARM'S TAG STRIPPED off the id.

    ⚠️ `scan_eval --tag` bakes the tag into `row_id` (`…-p1..contest`,
    `…-p1.veto-label`), so joining two arms on the raw id intersects to NOTHING
    and every delta reads as zero. That is a silent-empty failure, which is why
    `main` asserts the join is non-empty rather than printing a clean table of
    no rows.
    """
    out = {}
    for r in doc.get("rows", []):
        if not r.get("omr_ned"):
            continue
        out[r["row_id"].split(".")[0]] = r
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", type=Path, required=True)
    ap.add_argument("--arm", type=Path, required=True)
    ap.add_argument("--name", default="arm")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    ctrl = json.loads(args.control.read_text())
    arm = json.loads(args.arm.read_text())
    c_rows, a_rows = rows_of(ctrl), rows_of(arm)
    shared = set(c_rows) & set(a_rows)
    # PROVE THE COMPARISON LOOKED AT SOMETHING. A join that silently intersects
    # to nothing prints a table of no rows and a delta of zero, which is
    # indistinguishable from a real null result.
    if not shared:
        raise SystemExit(
            f"join is EMPTY: {len(c_rows)} control rows, {len(a_rows)} arm rows, "
            f"0 shared. control ids: {sorted(c_rows)[:3]} "
            f"arm ids: {sorted(a_rows)[:3]}")
    print(f"joined {len(shared)} rows "
          f"(control {len(c_rows)}, arm {len(a_rows)})\n")

    print(f"{'row':<40} {'control':>9} {args.name:>9} {'d_edits':>8} note")
    per_row = []
    for row_id in sorted(shared):
        c = c_rows[row_id]["omr_ned"]
        a = a_rows[row_id]["omr_ned"]
        d = a["omr_ed"] - c["omr_ed"]
        flag = ""
        if d <= -NOISE:
            flag = "IMPROVED"
        elif d >= NOISE:
            flag = "REGRESSED"
        elif d:
            flag = "(within noise)"
        print(f"{row_id:<40} {c['omr_ed']:>9} {a['omr_ed']:>9} {d:>+8} {flag}")
        per_row.append({"row_id": row_id, "control_edits": c["omr_ed"],
                        "arm_edits": a["omr_ed"], "delta": d,
                        "control_omr_ned": c["omr_ned"],
                        "arm_omr_ned": a["omr_ned"]})

    cp, apooled = ctrl.get("pooled"), arm.get("pooled")
    out = {"arm": args.name, "per_row": per_row, "noise_floor_edits": NOISE}
    if cp and apooled:
        d = apooled["omr_ed"] - cp["omr_ed"]
        print(f"\nPOOLED  control {cp['omr_ed']} edits ({cp['omr_ned']:.4f})"
              f"  ->  {args.name} {apooled['omr_ed']} ({apooled['omr_ned']:.4f})"
              f"  delta {d:+d} edits")
        print(f"  {'BEYOND' if abs(d) >= NOISE else 'WITHIN'} the "
              f"+/-{NOISE}-edit noise floor")
        worst = max(per_row, key=lambda r: r["delta"]) if per_row else None
        if worst:
            print(f"  worst single row: {worst['row_id']} {worst['delta']:+d}")
        out["pooled"] = {"control_edits": cp["omr_ed"], "arm_edits": apooled["omr_ed"],
                         "delta": d, "control_omr_ned": cp["omr_ned"],
                         "arm_omr_ned": apooled["omr_ned"]}
        # Categories that actually moved — a range veto should show up in
        # `wrong note`, and anywhere else is worth explaining.
        cc, ac = cp.get("categories", {}), apooled.get("categories", {})
        print("\n  categories that moved:")
        for k in sorted(set(cc) | set(ac)):
            dk = ac.get(k, 0) - cc.get(k, 0)
            if dk:
                print(f"    {k:<34} {cc.get(k,0):>7} -> {ac.get(k,0):>7}  {dk:+d}")
        out["categories"] = {k: {"control": cc.get(k, 0), "arm": ac.get(k, 0)}
                             for k in sorted(set(cc) | set(ac))
                             if ac.get(k, 0) != cc.get(k, 0)}
    if args.out:
        args.out.write_text(json.dumps(out, indent=1) + "\n")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
