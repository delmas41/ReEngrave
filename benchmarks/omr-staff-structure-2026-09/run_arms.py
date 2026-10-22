"""Score the slot-stitch arm against its own baseline, over the 11 scan rows.

WHY IT RE-EXPORTS RATHER THAN RE-TRANSCRIBING. `OMR_SLOT_STITCH` changes
`export.to_musicxml` and nothing upstream of it, so the transcriptions the scan
benchmark already committed (`fixtures/*.restamp-composed.omr.json`) are the
same bytes both arms would produce. Re-using them makes the A/B exact — the two
arms differ in the exporter and in nothing else — and costs no detector time on
a shared machine.

WHY IT DOES NOT COMPARE TO `results-restamp-composed.json`. That baseline was
exported on a different commit; this tree carries the arc-attribution merge, so
a re-export is NOT byte-identical to it (measured: it differs on every row). The
baseline here is therefore this tree's own flag-off export, scored the same way.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr import omr_ned  # noqa: E402
from tools.omr.export import to_musicxml  # noqa: E402

ROWS = [
    "beethoven-sym5-mvt1-984073-p1", "beethoven-sym5-mvt1-984073-p2",
    "beethoven-sym5-mvt1-575951-p1", "beethoven-sym5-mvt1-575951-p2",
    "dvorak-sym9-mvt1-405834-p5", "dvorak-sym9-mvt1-405834-p6",
    "brahms-sym1-mvt1-317803-p1", "brahms-sym1-mvt1-317803-p2",
    "mahler-sym5-mvt1-local-p2", "mahler-sym5-mvt1-local-p3",
    "bach-brandenburg3-mvt1-468678-p1",
]
ES = "entire staff insert/delete"
EM = "entire measure insert/delete"


def export_arm(fixtures: Path, out: Path, flag: str, tag: str) -> dict[str, Path]:
    os.environ["OMR_SLOT_STITCH"] = flag
    paths = {}
    for row in ROWS:
        src = fixtures / f"{row}.restamp-composed.omr.json"
        dst = out / f"{row}.{tag}.musicxml"
        dst.write_text(to_musicxml(json.loads(src.read_text())))
        paths[row] = dst
    return paths


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=str(
        Path("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-scan-e2e-2026-09/fixtures")))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "out"))
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    fixtures, out = Path(args.fixtures), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    base = export_arm(fixtures, out, "0", "baseline")
    fix = export_arm(fixtures, out, "1", "slotstitch")

    identical = {r for r in ROWS if base[r].read_bytes() == fix[r].read_bytes()}
    print(f"rows byte-identical between arms: {len(identical)}/{len(ROWS)}")
    print(f"rows the flag changes: {sorted(set(ROWS) - identical)}\n")

    results = {}
    for arm, paths in (("baseline", base), ("slotstitch", fix)):
        rows = []
        for r in ROWS:
            # A row the flag does not touch is the same file; score it once.
            if arm == "slotstitch" and r in identical:
                rows.append(dict(results["baseline"]["rows"][ROWS.index(r)], arm=arm))
                continue
            truth = fixtures / f"{r}.truth.musicxml"
            s = omr_ned.score_pair(pred=paths[r], truth=truth, name=r)
            rows.append({"row": r, "omr_ned": s["omr_ned"], "omr_ed": s["omr_ed"],
                         "pred_symbols": s["pred_symbols"],
                         "truth_symbols": s["truth_symbols"],
                         "categories": s.get("categories", {}), "arm": arm})
            print(f"  [{arm}] {r:<34} ned {s['omr_ned']:.4f}  ed {s['omr_ed']}")
        ed = sum(x["omr_ed"] for x in rows)
        den = sum(x["pred_symbols"] + x["truth_symbols"] for x in rows)
        results[arm] = {"rows": rows, "pooled_omr_ed": ed,
                        "pooled_omr_ned": ed / den if den else 0.0,
                        "denominator": den}

    print(f"\n{'row':<34} {'base ed':>8} {'fix ed':>8} {'Δed':>6} "
          f"{'ΔES':>6} {'ΔEM':>6}")
    for i, r in enumerate(ROWS):
        b, f = results["baseline"]["rows"][i], results["slotstitch"]["rows"][i]
        print(f"{r:<34} {b['omr_ed']:>8} {f['omr_ed']:>8} "
              f"{f['omr_ed']-b['omr_ed']:>+6} "
              f"{f['categories'].get(ES,0)-b['categories'].get(ES,0):>+6} "
              f"{f['categories'].get(EM,0)-b['categories'].get(EM,0):>+6}")
    for arm in ("baseline", "slotstitch"):
        rr = results[arm]
        es = sum(x["categories"].get(ES, 0) for x in rr["rows"])
        print(f"\n{arm:<12} pooled OMR-NED {rr['pooled_omr_ned']:.4f} / "
              f"{rr['pooled_omr_ed']} edits   entire-staff {es}")

    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2) + "\n")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
