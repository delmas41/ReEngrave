"""Score the key-signature layer against hand-read ground truth.

Every figure quoted in `RESULTS.md`, in `tools/omr/README.md` and in the commit
messages for this layer comes from this script. Run it to reproduce them, or to
find out that a change has moved them.

    # both modes, every page whose PDF is present
    python3 benchmarks/omr-key-signature/eval_key_signatures.py

    # one page, one mode
    python3 benchmarks/omr-key-signature/eval_key_signatures.py \
        --page wtc-p17 --mode pipeline

Two modes, because the layer has two halves that fail differently:

  component  Phase 1, then the CV LOCATOR ALONE on each staff's measured
             header window, with the TRUE clef supplied from ground truth. It
             isolates the locator and the vote from clef detection — a real
             ceiling on the end-to-end result that would otherwise hide what
             the reader itself can do. No YOLO, so it runs in seconds.

             Note it forces the locator on every staff, which is NOT what the
             pipeline does: there the detector is preferred and the locator is
             the fallback where the detector is silent. On a clean engraving
             that ordering is the whole game — WTC p.17 scores 0 correct / 5
             wrong here, forcing the locator onto a page the detector reads
             perfectly well, and 10/10 in pipeline mode. Read component mode as
             "what the locator can do on prints the detector can't read", not
             as a score for the layer.

  pipeline   The whole of `transcribe`, scored on what actually lands in the
             output. This is the honest end-to-end number and it is LOWER,
             because a staff whose clef is only a positional default is skipped
             by design (a signature fitted against a guessed clef is a guess
             squared — see tools/omr/key_signature_geometry.py).

A page whose PDF isn't on this machine is skipped, not failed: the orchestral
PDFs live in the gitignored IMSLP corpus and the WTC path is machine-specific.
Override either with --pdf.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

GROUND_TRUTH = Path(__file__).resolve().parent / "ground_truth.json"
DEFAULT_WEIGHTS = REPO / "omr-weights" / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"


def _resolve(pdf: str) -> Path:
    """Ground-truth PDF paths are repo-relative where they can be, absolute
    where the file lives outside the repo."""
    p = Path(pdf)
    return p if p.is_absolute() else REPO / p


def _tally(rows: list[tuple[int, int | None]]) -> dict[str, int]:
    """Score (truth, read) pairs.

    The four outcomes are kept apart on purpose. An abstention on a staff that
    HAS a signature (`missed`) and a wrong signature (`wrong`) are not the same
    failure: the first leaves the staff where it already was, the second
    re-pitches every note on it. A layer that abstains is behaving correctly
    even when its recall is poor, and a summary that merged the two would hide
    exactly the property this layer is designed around.
    """
    out = {"correct": 0, "wrong": 0, "missed": 0, "abstained_correctly": 0}
    for truth, read in rows:
        if read is None or read == 0:
            if truth == 0:
                out["abstained_correctly"] += 1
            else:
                out["missed"] += 1
        elif read == truth:
            out["correct"] += 1
        else:
            out["wrong"] += 1
    return out


def _fmt(name: str, t: dict[str, int]) -> str:
    return (f"  {name:<22} correct={t['correct']:<3} wrong={t['wrong']:<3} "
            f"missed={t['missed']:<3} correct-abstentions={t['abstained_correctly']}")


# ─── component mode: the locator + the vote, clefs supplied ─────────────────

def run_component(page: dict, pdf: Path) -> None:
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr.measure_extractor import detect_barlines
    from tools.omr.staff_header import header_cells_for_page
    from tools.omr.key_signature_locator import locate_key_signature
    from tools.omr.key_signature_vote import StaffCandidate, reconcile

    truth = {s["ordinal"]: s for s in page["staves"]}
    rendered = render_page(pdf, page["page_index"], dpi=page["dpi"])
    pws = detect_barlines(detect_staves(rendered))
    cells = header_cells_for_page(pws)

    candidates: list[StaffCandidate] = []
    for system_index in sorted({st.system_index for st in pws.staves}):
        staves = sorted((st for st in pws.staves if st.system_index == system_index),
                        key=lambda st: st.top_y)
        for ordinal, staff in enumerate(staves):
            cell = cells.get(staff.staff_index)
            gt = truth.get(ordinal)
            located = (locate_key_signature(cell, gt["clef"])
                       if cell is not None and gt else None)
            candidates.append(StaffCandidate(
                staff_index=staff.staff_index, system_index=system_index,
                ordinal=ordinal,
                fifths=located.read.fifths if located else None,
                weight=float(len(located.read.matched_slots)) if located else 0.0,
                source="cv_locator",
            ))

    scored = [c for c in candidates if c.ordinal in truth]
    before = _tally([(truth[c.ordinal]["fifths"], c.fifths) for c in scored])
    voted = reconcile(candidates)
    after = _tally([(truth[c.ordinal]["fifths"], voted.fifths_for(c.staff_index))
                    for c in scored])
    print(_fmt("locator, per-staff", before))
    print(_fmt("locator, after vote", after))


# ─── pipeline mode: what actually lands in the output ───────────────────────

def run_pipeline(page: dict, pdf: Path, weights: Path,
                 imgsz: int | None) -> None:
    from tools.omr.transcribe import transcribe

    truth = {s["ordinal"]: s for s in page["staves"]}
    started = time.time()
    result = transcribe(pdf_path=pdf, pages=[page["page_index"]], weights=str(weights),
                        dpi=page["dpi"], progress=False,
                        **({} if imgsz is None else {"imgsz": imgsz}))
    rows, voted_staves = [], 0
    for out_page in result["pages"]:
        for system in out_page["systems"]:
            for ordinal, staff in enumerate(system["staves"]):
                if ordinal not in truth:
                    continue
                ks = staff["key_signature"]
                rows.append((truth[ordinal]["fifths"], ks["sharps"] - ks["flats"]))
                voted_staves += bool(staff.get("key_signature_source"))
    print(_fmt("end to end", _tally(rows)))
    print(f"  {'':22} staves the vote spoke for: {voted_staves}/{len(rows)}"
          f"   ({time.time() - started:.0f}s, "f"imgsz={imgsz if imgsz else 'per-cell'})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--page", default=None, help="only this ground-truth page id")
    ap.add_argument("--mode", choices=["component", "pipeline", "both"], default="both")
    ap.add_argument("--pdf", default=None, help="override the PDF path (one page only)")
    ap.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    # None = whatever transcribe defaults to, so this harness tracks the
    # pipeline instead of silently pinning a value the pipeline stopped using.
    # It was pinned at 1280 while the CLI default was 2048 and then 512.
    ap.add_argument("--imgsz", type=int, default=None, help="pipeline mode only")
    args = ap.parse_args()

    truth = json.loads(GROUND_TRUTH.read_text())
    pages = [p for p in truth["pages"] if args.page in (None, p["id"])]
    if not pages:
        print(f"no ground-truth page with id {args.page!r}", file=sys.stderr)
        return 2

    for page in pages:
        pdf = Path(args.pdf) if args.pdf else _resolve(page["pdf"])
        print(f"\n=== {page['id']} — {page['work']}")
        if not pdf.exists():
            print(f"  SKIPPED: PDF not on this machine ({pdf})")
            continue
        if args.mode in ("component", "both"):
            run_component(page, pdf)
        if args.mode in ("pipeline", "both"):
            weights = Path(args.weights)
            if not weights.exists():
                print(f"  pipeline mode SKIPPED: weights not found ({weights})")
            else:
                run_pipeline(page, pdf, weights, args.imgsz)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
