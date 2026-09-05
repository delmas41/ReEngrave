"""Two numbers on the same page: how much we SAW, and how much we WROTE.

    stage 1  reading      detections vs `page_truth`'s inventory of the ink
    stage 2  translation  detected -> exported -> truth, per symbol family

Every accuracy figure this project reports is stage 2's far end alone, so a
signal read perfectly and lost in the exporter is indistinguishable from one
never read. Nine fixes have been found by opening that bucket by hand.

    python3 benchmarks/omr-reading-vs-reproduction-2026-09/run.py \\
        --fixtures <dir of *.musicxml truth + *.omr.json + *.omr.musicxml> \\
        --work-dir <scratch> --out results.json

⚠️ **THE TWO STAGES READ DIFFERENT PAGES ON PURPOSE, and the reason is not
laziness.** Stage 1 needs a page whose ink is known exactly, which means one we
RENDER (Verovio, so the truth comes out of the same act as the image). Stage 2
needs the pipeline's own numbers on the pages the headline benchmark uses, which
are LilyPond renders. Mixing them would make stage 1's reading score and stage
2's export counts refer to different images. They are reported side by side and
never differenced.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.page_truth import build                      # noqa: E402
from tools.omr.score_reading import report as reading_report  # noqa: E402
from tools.omr.score_translation import funnel, verdict       # noqa: E402


def stage1(fixtures: Path, work_dir: Path, works: list[str], dpi: int) -> dict:
    out = {}
    for w in works:
        d = work_dir / w
        truth_json = d / f"{w}.pagetruth.json"
        if not truth_json.exists():
            try:
                build(fixtures / f"{w}.musicxml", d, dpi=dpi)
            except Exception as exc:
                out[w] = {"error": f"{type(exc).__name__}: {exc}"}
                continue
        read = d / "read-p1.json"
        if not read.exists():
            r = subprocess.run(
                [sys.executable, "-m", "tools.omr.transcribe", str(d / f"{w}.pdf"),
                 "--pages", "0", "--dpi", str(dpi), "--no-contextual",
                 "--no-direction-text", "--out", str(read)],
                capture_output=True, text=True, cwd=str(REPO))
            if r.returncode != 0:
                out[w] = {"error": r.stderr[-300:]}
                continue
        print(f"\n{'=' * 70}\n{w}\n{'=' * 70}")
        out[w] = reading_report(json.loads(truth_json.read_text()),
                                json.loads(read.read_text()), 0,
                                [0.5, 0.25, 0.75, 1.0, 1.5])
    return out


def stage2(fixtures: Path, works: list[str]) -> dict:
    per_work, agg = {}, defaultdict(
        lambda: {"detected": 0, "exported": 0, "truth": 0,
                 "unit_mismatch": None, "element": ""})
    for w in works:
        omr = fixtures / f"{w}.omr.json"
        truth = fixtures / f"{w}.musicxml"
        ours = fixtures / f"{w}.omr.musicxml"
        if not (omr.exists() and truth.exists()):
            continue
        f = funnel(json.loads(omr.read_text()), truth.read_text(),
                   ours.read_text() if ours.exists() else None)
        per_work[w] = f["rows"]
        for row in f["rows"]:
            a = agg[row["family"]]
            a["detected"] += row["detected"]
            a["exported"] += row["exported"]
            a["truth"] += row["truth"]
            a["unit_mismatch"] = row["unit_mismatch"]
            a["element"] = row["element"]
    return {"per_work": per_work, "pooled": dict(agg)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixtures", type=Path, required=True)
    ap.add_argument("--work-dir", type=Path, required=True)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--works", nargs="*")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--skip-stage1", action="store_true")
    args = ap.parse_args()

    works = args.works or sorted(
        p.name[: -len(".musicxml")] for p in args.fixtures.glob("*.musicxml")
        if not p.name.endswith(".omr.musicxml"))
    print(f"{len(works)} works: {', '.join(works)}")

    result = {"works": works, "dpi": args.dpi}
    if not args.skip_stage1:
        result["stage1_reading"] = stage1(args.fixtures, args.work_dir, works, args.dpi)

    s2 = stage2(args.fixtures, works)
    result["stage2_translation"] = s2
    print(f"\n{'=' * 70}\nSTAGE 2 — pooled over {len(s2['per_work'])} works\n{'=' * 70}")
    print(f"{'family':18s} {'element':16s} {'detect':>7s} {'export':>7s} "
          f"{'truth':>6s}   verdict")
    for fam in sorted(s2["pooled"]):
        a = dict(s2["pooled"][fam], family=fam)
        print(f"{fam:18s} {a['element']:16s} {a['detected']:7d} "
              f"{a['exported']:7d} {a['truth']:6d}   {verdict(a)}")

    flags = [(w, r["family"], verdict(r))
             for w, rows in s2["per_work"].items() for r in rows
             if "READ AND" in verdict(r)]
    print(f"\nper-work read-and-lost flags ({len(flags)}):")
    for w, fam, v in flags:
        print(f"   {w:24s} {fam:16s} {v}")

    if args.out:
        args.out.write_text(json.dumps(result, indent=1, default=str))
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
