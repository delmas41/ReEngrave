"""Which veto direction carries the scan damage? Price each alone.

The A/B prices OMR_ARC_RECLASS as a unit: scan pooled 0.8387 -> 0.8391
(+130). This probe re-exports the same stored transcriptions with ONE
direction of the veto neutered at a time — module patching, no product
knob — and scores both single-direction arms through the same musicdiff
harness, so the refusal (or a partial keep) is attributed rather than
guessed.
"""
from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import export as export_mod  # noqa: E402
from tools.omr import omr_ned  # noqa: E402

SCAN_FIX = ROOT / "benchmarks" / "omr-scan-e2e-2026-09" / "fixtures"
ROWS = [
    "beethoven-sym5-mvt1-984073-p1", "beethoven-sym5-mvt1-984073-p2",
    "beethoven-sym5-mvt1-575951-p1", "beethoven-sym5-mvt1-575951-p2",
    "dvorak-sym9-mvt1-405834-p5", "dvorak-sym9-mvt1-405834-p6",
    "brahms-sym1-mvt1-317803-p1", "brahms-sym1-mvt1-317803-p2",
    "mahler-sym5-mvt1-local-p2", "mahler-sym5-mvt1-local-p3",
]


def _counts(path: Path) -> tuple[int, int]:
    root = ET.parse(path).getroot()
    return (sum(1 for e in root.iter("tie")),
            sum(1 for e in root.iter("slur") if e.get("type") == "start"))


def _arm(name: str, *, no_tie2slur: bool, no_slur2tie: bool) -> dict:
    os.environ["OMR_ARC_RECLASS"] = "1"
    saved_reclass = export_mod._reclass_tie_arcs_in_run
    saved_covers = export_mod._slur_covers_a_tie
    if no_tie2slur:
        export_mod._reclass_tie_arcs_in_run = (
            lambda measures, staff_of, arcs, order: 0)
    if no_slur2tie:
        export_mod._slur_covers_a_tie = lambda covered, order: False
    pairs = []
    ties = slurs = 0
    try:
        for rid in ROWS:
            result = json.loads(
                (SCAN_FIX / f"{rid}.arcoff.omr.json").read_text())
            export_mod.reset_arc_reclass_stats()
            xml = export_mod.to_musicxml(result)
            out = SCAN_FIX / f"{rid}.{name}.omr.musicxml"
            out.write_text(xml)
            t, s = _counts(out)
            ties += t
            slurs += s
            pairs.append((rid, out, SCAN_FIX / f"{rid}.truth.musicxml"))
    finally:
        export_mod._reclass_tie_arcs_in_run = saved_reclass
        export_mod._slur_covers_a_tie = saved_covers
        os.environ["OMR_ARC_RECLASS"] = "0"
    scored = omr_ned.score_batch(pairs)
    ed = sum(p["omr_ed"] for p in scored["pairs"])
    ps = sum(p["pred_symbols"] for p in scored["pairs"])
    ts = sum(p["truth_symbols"] for p in scored["pairs"])
    return {"arm": name, "omr_ed": ed, "omr_ned": ed / (ps + ts),
            "tie_elements": ties, "slur_starts": slurs}


def main() -> int:
    out = [_arm("s2tonly", no_tie2slur=True, no_slur2tie=False),
           _arm("t2sonly", no_tie2slur=False, no_slur2tie=True)]
    for a in out:
        print(f"{a['arm']}: pooled {a['omr_ned']:.4f} / {a['omr_ed']} edits, "
              f"tie elements {a['tie_elements']}, slur starts {a['slur_starts']}")
    (BENCH / "probe_scan_directions.json").write_text(
        json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
