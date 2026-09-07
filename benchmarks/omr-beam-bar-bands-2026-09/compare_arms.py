"""Compare two scan_eval arms per row and per bucket, and check the controls.

The 11 rows with no multi-bar component are the control: they MUST be identical
to the edit. If they are not, something other than this change moved and the
pooled figure is not attributable to it.

Exits non-zero if an arm is missing, if the arms disagree about which rows they
scored, or if either arm withheld its pooled figure.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

# The 9 rows carrying at least one multi-bar component, from probe_bar_placement.
AFFECTED = {
    "dvorak-sym9-mvt1-405834-p5", "dvorak-sym9-mvt1-405834-p6",
    "dvorak-sym9-mvt1-405834-p7", "brahms-sym1-mvt1-317803-p2",
    "brahms-sym1-mvt1-317803-p3", "brahms-sym1-mvt1-317803-p4",
    "mahler-sym5-mvt1-local-p2", "mahler-sym5-mvt1-local-p3",
    "bach-brandenburg3-mvt1-468678-p1",
}
KEY = ["wrong note", "wrong flag/beam", "entire measure insert/delete",
       "entire staff insert/delete", "wrong note head", "wrong direction"]


def load(p: Path, tag: str) -> tuple[dict, dict]:
    if not p.is_file():
        sys.exit(f"FATAL: arm file missing: {p}")
    d = json.loads(p.read_text())
    rows = {r["row_id"].replace(f".{tag}", ""): r for r in d["rows"]}
    return d, rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", type=Path, required=True)
    ap.add_argument("--base", type=Path, required=True)
    a = ap.parse_args()
    df, rf = load(a.fix, "fixarm")
    db, rb = load(a.base, "basectl")

    if rf.keys() != rb.keys():
        sys.exit(f"FATAL: arms scored different rows: "
                 f"fix-only {rf.keys()-rb.keys()}, base-only {rb.keys()-rf.keys()}")
    for name, d in (("fix", df), ("base", db)):
        if d.get("pooled_withheld_because"):
            sys.exit(f"FATAL: {name} arm withheld pooled: {d['pooled_withheld_because']}")

    pf, pb = df["pooled"], db["pooled"]
    print(f"POOLED over {pf['n_rows']} rows")
    print(f"  base  OMR-NED {pb['omr_ned']:.4f}   edits {pb['omr_ed']:6d}   "
          f"pred symbols {pb['pred_symbols']}")
    print(f"  fix   OMR-NED {pf['omr_ned']:.4f}   edits {pf['omr_ed']:6d}   "
          f"pred symbols {pf['pred_symbols']}")
    print(f"  delta         {pf['omr_ned']-pb['omr_ned']:+.4f}   "
          f"{pf['omr_ed']-pb['omr_ed']:+6d}   "
          f"{pf['pred_symbols']-pb['pred_symbols']:+d}")

    print("\nPOOLED BUCKETS (base -> fix)")
    cats = sorted(set(pf["categories"]) | set(pb["categories"]))
    for c in cats:
        vb, vf = pb["categories"].get(c, 0), pf["categories"].get(c, 0)
        star = "  <<<" if c in KEY and vf != vb else ""
        print(f"  {c:32s} {vb:6d} -> {vf:6d}   {vf-vb:+5d}{star}")

    print("\nPER ROW  (A = carries a multi-bar component)")
    print(f"  {'':2s} {'row':36s} {'base':>8s} {'fix':>8s} {'dNED':>9s} "
          f"{'base ed':>8s} {'fix ed':>7s} {'dEd':>6s}")
    moved_unaffected, moved_affected = [], []
    for rid in sorted(rf):
        # ⚠️ row["omr_ned"] is a DICT (name/omr_ned/omr_ed/categories), not a float.
        ob, of = rb[rid]["omr_ned"], rf[rid]["omr_ned"]
        nb, nf = ob["omr_ned"], of["omr_ned"]
        eb, ef = ob["omr_ed"], of["omr_ed"]
        mark = "A" if rid in AFFECTED else " "
        print(f"  {mark:2s} {rid:36s} {nb:8.4f} {nf:8.4f} {nf-nb:+9.4f} "
              f"{eb:8d} {ef:7d} {ef-eb:+6d}")
        if eb != ef or abs(nf - nb) > 1e-12:
            (moved_affected if rid in AFFECTED else moved_unaffected).append(rid)
            for c in sorted(set(ob["categories"]) | set(of["categories"])):
                vb, vf = ob["categories"].get(c, 0), of["categories"].get(c, 0)
                if vb != vf:
                    print(f"        {c:30s} {vb:5d} -> {vf:5d}  {vf-vb:+4d}")

    print(f"\nCONTROL: unaffected rows that moved: {len(moved_unaffected)}")
    for r in moved_unaffected:
        print(f"  ⚠️  {r}")
    if not moved_unaffected:
        print("  none — every row without a multi-bar component is identical")
    print(f"affected rows that moved: {len(moved_affected)} of "
          f"{len(AFFECTED & set(rf))}")


if __name__ == "__main__":
    main()
