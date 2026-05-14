"""Port verdicts from a baseline verdict-set to a new matcher run.

For each cell in `--cells` (e.g. just the 3 pre-filled WTC cells), this:
  1. Reloads the cell from the manifest.
  2. Runs detect_symbols() with the current matcher code.
  3. Writes a new detections JSON.
  4. For each new detection, looks up the closest detection in the original
     verdict markdown (by category + proximity in canonical px). If a match
     is found, copies the human verdict (TP / FP / WRONG_PITCH / unsure).
     Detections with no near-neighbor in the baseline are written with
     `verdict: __` (pending) so the scorer skips them.
  5. Writes a new verdict markdown file.

Output is then directly scorable by `score.py`.

Used for Phase 2.6 to re-measure precision after fixes WITHOUT requiring a
human to re-annotate every cell.

CLI:
    python3 -m tools.omr.annotate.port_verdicts \
        --baseline-verdicts benchmarks/omr-phase2.5/verdicts \
        --manifest benchmarks/omr-phase2.5/cells.json \
        --cells wtc-p5-sys0-s0-m0 wtc-p5-sys0-s0-m1 wtc-p5-sys0-s0-m2 \
        --out-dir benchmarks/omr-phase2.5/verdicts-fix1 \
        --detections-out benchmarks/omr-phase2.5/detections-fix1
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import cv2

from ..pitch_resolver import pitch_for_notehead
from ..symbol_library.loader import SymbolLibrary
from ..template_matcher import SymbolDetection, detect_symbols
from .build_template import (
    _load_cell_from_manifest,
    _detections_to_dict,
)
from .score import _DET_RX, _VERDICT_RX


# Minimum proximity (in canonical px) for a new detection to be considered
# the "same" as a baseline detection. We use a generous radius because
# small matcher tweaks can shift the peak NCC location by a few pixels.
PROXIMITY_PX = 25


def parse_baseline(md_text: str) -> list[dict]:
    """Pull (smufl, category, x, y, verdict) tuples out of a baseline
    verdict markdown."""
    lines = md_text.splitlines()
    out: list[dict] = []
    cur: dict | None = None
    for ln in lines:
        m = _DET_RX.search(ln)
        if m:
            if cur is not None:
                out.append(cur)
            did, smufl, cat, x, y, pitch, conf = m.groups()
            cur = {
                "id": did,
                "smufl_name": smufl,
                "category": cat,
                "x": int(x),
                "y": int(y),
                "verdict_raw": "",
            }
            vm = _VERDICT_RX.search(ln)
            if vm:
                cur["verdict_raw"] = vm.group(1).strip()
            continue
        if cur is not None and not cur["verdict_raw"]:
            vm = _VERDICT_RX.search(ln)
            if vm:
                cur["verdict_raw"] = vm.group(1).strip()
    if cur is not None:
        out.append(cur)
    return out


def find_match(det: SymbolDetection, baseline: list[dict]) -> dict | None:
    """Return the closest baseline det within radius.

    Strategy: prefer a same-category match (no surprise). If none exists,
    fall back to a same-LOCATION match of any category — Phase 2.6 fixes
    often re-classify the same connected component (e.g. a stem that used
    to be barlineHeavy is now restHalf). In that case the original FP
    verdict still applies: the matcher is still firing at the wrong spot.
    """
    # First pass: same category.
    best = None
    best_d = float("inf")
    for b in baseline:
        if b["category"] != det.category:
            continue
        dx = b["x"] - det.x_center
        dy = b["y"] - det.y_center
        d = (dx * dx + dy * dy) ** 0.5
        if d < best_d and d <= PROXIMITY_PX:
            best_d = d
            best = b
    if best is not None:
        return best
    # Fallback: any category, tighter radius (re-classified CC). We only
    # honor the FP verdict in this case, because a baseline TP at this
    # location was specifically a TP FOR ITS CATEGORY; a category swap
    # makes that TP claim no longer apply.
    for b in baseline:
        dx = b["x"] - det.x_center
        dy = b["y"] - det.y_center
        d = (dx * dx + dy * dy) ** 0.5
        if d <= PROXIMITY_PX / 2:
            verdict = (b.get("verdict_raw") or "").lower().split(" ", 1)[0]
            if verdict in {"fp", "false", "wrong"}:
                return b
    return None


def render_verdict_md(
    cell_id: str,
    entry: dict,
    detections: list[SymbolDetection],
    overlay_rel: str,
    ported: list[tuple[SymbolDetection, dict | None]],
) -> str:
    """Render verdict markdown with verdicts ported from baseline where
    a near-neighbor exists."""
    clef = entry.get("clef", "treble")
    staff_ys = ", ".join(str(y) for y in entry["staff_line_ys_canonical"])
    lines: list[str] = []
    lines.append("<!-- auto-ported from baseline verdicts; new detections are pending -->")
    lines.append(f"# Cell {cell_id} — verdicts\n")
    lines.append(f"**Image:** ![overlay]({overlay_rel})\n")
    lines.append(f"**Clef assumed:** {clef}\n")
    lines.append(f"**Staff lines (canonical y):** {staff_ys}\n")
    lines.append(f"**Source:** {entry.get('source_tag', '?')}  ·  "
                 f"page {entry['page']}  ·  sys {entry['system_index']}  "
                 f"staff {entry['staff_index']}  measure {entry['measure_index']}\n")
    lines.append("")
    lines.append("## Detections\n")

    for i, (d, baseline_match) in enumerate(ported):
        pitch_str = f" → {d.pitch}" if d.pitch else ""
        if baseline_match and baseline_match.get("verdict_raw"):
            verdict = baseline_match["verdict_raw"]
            note = f"  <!-- ported from baseline {baseline_match['id']} -->"
        else:
            verdict = "__________"
            note = "  <!-- new detection, no baseline match -->"
        lines.append(
            f"- [x] D{i}  {d.smufl_name} ({d.category}) at "
            f"(x={d.x_center}, y={d.y_center}){pitch_str}  conf={d.confidence:.2f}\n"
            f"       verdict: {verdict}{note}"
        )
    lines.append("")
    lines.append("## Missed noteheads (FN)\n")
    lines.append("(carried over from baseline — none in pre-filled cells)\n")
    lines.append("## Wrong-pitch corrections\n")
    return "\n".join(lines)


def port(
    baseline_dir: Path,
    manifest_path: Path,
    cell_ids: list[str],
    out_dir: Path,
    detections_out: Path,
    library: SymbolLibrary | None = None,
) -> dict:
    if library is None:
        library = SymbolLibrary.load()

    out_dir.mkdir(parents=True, exist_ok=True)
    detections_out.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text())
    root = Path.cwd()
    by_id = {e["cell_id"]: e for e in manifest}

    summary = {}

    for cid in cell_ids:
        entry = by_id.get(cid)
        if entry is None:
            print(f"  WARN: cell {cid} not in manifest")
            continue
        baseline_md = (baseline_dir / f"{cid}.md")
        if not baseline_md.exists():
            print(f"  WARN: no baseline verdict at {baseline_md}")
            continue

        baseline = parse_baseline(baseline_md.read_text())

        cell = _load_cell_from_manifest(entry, root)
        clef = entry.get("clef", "treble")
        detections = detect_symbols(cell, library)
        for d in detections:
            if d.category == "notehead":
                d.pitch = pitch_for_notehead(d, clef=clef)

        ordered = sorted(detections, key=lambda d: d.x_center)
        ported = [(d, find_match(d, baseline)) for d in ordered]

        # Write detections JSON.
        det_path = detections_out / f"{cid}.json"
        det_path.write_text(json.dumps(_detections_to_dict(cid, detections), indent=2))

        # Write verdict markdown.
        overlay_rel = f"../overlays/{cid}.png"
        md = render_verdict_md(cid, entry, ordered, overlay_rel, ported)
        (out_dir / f"{cid}.md").write_text(md)

        n_total = len(ordered)
        n_ported = sum(1 for (_, b) in ported if b is not None)
        n_new = n_total - n_ported
        n_baseline = len(baseline)
        n_disappeared = sum(
            1 for b in baseline
            if not any(
                (b["category"] == d.category and abs(b["x"] - d.x_center) <= PROXIMITY_PX
                 and abs(b["y"] - d.y_center) <= PROXIMITY_PX)
                for d in ordered
            )
        )
        summary[cid] = {
            "baseline_count": n_baseline,
            "new_count": n_total,
            "ported": n_ported,
            "new_unknown": n_new,
            "disappeared": n_disappeared,
        }
        print(
            f"  {cid}: baseline={n_baseline} → new={n_total} "
            f"(ported={n_ported}, new={n_new}, disappeared={n_disappeared})"
        )
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-verdicts", required=True)
    ap.add_argument("--manifest", default="benchmarks/omr-phase2.5/cells.json")
    ap.add_argument("--cells", nargs="+", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--detections-out", required=True)
    args = ap.parse_args()
    port(
        baseline_dir=Path(args.baseline_verdicts),
        manifest_path=Path(args.manifest),
        cell_ids=args.cells,
        out_dir=Path(args.out_dir),
        detections_out=Path(args.detections_out),
    )


if __name__ == "__main__":
    main()
