"""The EXPORT half alone: one record, exported twice. Minutes, not an hour.

⚠️ IT PRICES ONLY THE NOTES, AND SAYS SO. The dynamics half of this repair is
in `adjudicate_dynamic`, whose verdicts are already baked into the saved
record — so this arm is STRUCTURALLY BLIND to it and its `<dynamics>` figures
are identical by construction, not by measurement. `ab_arm.py` re-runs
ADJUDICATE and is the instrument for that half.

It exists because it is cheap and because it CROSS-CHECKS the expensive arm:
the note figures must agree between the two, and if they do not, one of them is
measuring itself.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import adjudicate as A                 # noqa: E402
from tools.omr.staged import export as sx                    # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ab_arm import chord_stats, counts, dynamics_histogram    # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    result = json.load(open(args.record))
    print(f"record provenance: {result.get('provenance')}")

    real = A.is_relocated_copy
    stub = lambda *a, **k: False                              # noqa: E731
    A.is_relocated_copy = stub
    sx.A.is_relocated_copy = stub
    try:
        base_xml, base_rep = sx.to_musicxml(result)
    finally:
        A.is_relocated_copy = real
        sx.A.is_relocated_copy = real
    fix_xml, fix_rep = sx.to_musicxml(result)

    b, f = chord_stats(base_xml), chord_stats(fix_xml)
    print(f"\n{'':<36} {'base':>10} {'fix':>10}")
    for label, i in (("chord events (2+ on one stem)", 0),
                     ("... with a REPEATED pitch", 1),
                     ("excess <note> in those chords", 2)):
        print(f"{label:<36} {b[i]:>10} {f[i]:>10}")

    bc, fc = counts(base_xml), counts(fix_xml)
    print()
    for k in bc:
        flag = "" if bc[k] == fc[k] else "   <-- moved"
        print(f"  {k:<22} {bc[k]:>8} {fc[k]:>8}{flag}")

    print("\n⚠️ <dynamics> are identical BY CONSTRUCTION here — the verdicts "
          "are baked into the record. See ab_arm.py.")
    bh, fh = dynamics_histogram(base_xml), dynamics_histogram(fix_xml)
    print(f"  base {dict(bh)}")
    print(f"  fix  {dict(fh)}")

    for name, rep in (("base", base_rep), ("fix", fix_rep)):
        bal = rep["balance"]
        print(f"\n{name}: balanced={bal['balanced']} "
              f"in_log={bal['events_in_log']} written={bal['events_written']} "
              f"not_written={bal['events_not_written']}")
        print(f"  notes_not_written: {rep['notes_not_written']}")
        cen = rep.get("status_census") or {}
        print(f"  status_census.unaccounted: {cen.get('unaccounted')}")

    (out / "export-only-summary.json").write_text(json.dumps({
        "chords": {"base": list(b), "fix": list(f)},
        "counts": {"base": bc, "fix": fc},
        "notes_not_written": {"base": base_rep["notes_not_written"],
                              "fix": fix_rep["notes_not_written"]},
        "balance": {"base": base_rep["balance"], "fix": fix_rep["balance"]},
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
