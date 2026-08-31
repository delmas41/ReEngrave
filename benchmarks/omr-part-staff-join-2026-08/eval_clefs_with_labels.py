"""What are the clefs on Beethoven 5 p.48 worth, once the labels arrive?

`eval_pipeline_clefs.py` scores this page at **8 of 17**, and the reason is not
the join: this edition (IMSLP984073) has **no text layer at all** — zero
characters on every page — so `read_staff_labels` returns nothing, the
part-staff join never sees a label, nothing pins, and the dossier abstains. That
is a failure of label ACQUISITION, which is its own thread
(`benchmarks/omr-margin-labels-2026-08/VISION_CEILING_2026-08-30.md`) and has a
Claude Vision fallback this benchmark does not spend credits on.

So this harness hands the join the labels the page actually PRINTS, from the
hand-read ground truth beside it, and measures the clefs that come out. Only the
printed ones: the five string staves stay unlabelled exactly as the engraving
leaves them, so the answer is a real ceiling and not an oracle in disguise.

It separates three things that the single 8/17 conflates:

    python3 benchmarks/omr-part-staff-join-2026-08/eval_clefs_with_labels.py
    python3 ... eval_clefs_with_labels.py --vision       # the REAL end-to-end number
    python3 ... eval_clefs_with_labels.py --no-pins      # what pinning is worth
    python3 ... eval_clefs_with_labels.py --no-dossier   # what the dossier is worth

`--vision` replays one cached margin read (`evidence/p48-vision-labels.json`,
model claude-opus-5, one call for the page's single system). That read is the
production path, so `--vision` is what the pipeline would actually score once
the fallback is reachable; the default arm is the ceiling if every printed label
arrived perfectly. On this page they are the same, which is the point.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

GROUND_TRUTH = Path(__file__).resolve().parent / "ground-truth-beet5-p48.json"
# One margin read by `staff_labels_vision`, cached so this is reproducible
# without spending credits. The crop it was given is beside it.
VISION_LABELS = (Path(__file__).resolve().parent / "evidence"
                 / "p48-vision-labels.json")
WEIGHTS = REPO / "omr-weights" / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pins", action="store_true",
                    help="disable label pinning, holding everything else fixed")
    ap.add_argument("--no-dossier", action="store_true",
                    help="do not let the work supply clefs at all")
    ap.add_argument("--vision", action="store_true",
                    help="use the labels the MARGIN READER actually returned "
                         "(evidence/p48-vision-labels.json) instead of the "
                         "printed ones — this is the real end-to-end number")
    ap.add_argument("--weights", type=Path, default=WEIGHTS)
    args = ap.parse_args()
    if not args.weights.exists():
        print(f"no weights at {args.weights}", file=sys.stderr)
        return 1

    import tools.omr.contextual as ctx
    from tools.omr.dossier import resolve_dossier
    from tools.omr.instruments import lookup
    from tools.omr.staff_labels import StaffLabel
    from tools.omr.transcribe import transcribe

    if args.no_pins:
        import tools.omr.score_layouts as score_layouts
        score_layouts.label_pins = lambda *a, **k: []

    truth = json.loads(GROUND_TRUTH.read_text())
    if args.vision:
        cached = json.loads(VISION_LABELS.read_text())["labels_by_staff_ordinal"]
        printed = {int(k): v for k, v in cached.items()}
    else:
        printed = {s["slot"]: s["label"] for s in truth["slots"] if s["label"]}

    def supplied(pws, pdf_path, page_index, **kw):
        """The labels this page prints, on the staves that print them."""
        out = []
        for ordinal, staff in enumerate(sorted(pws.staves, key=lambda s: s.top_y)):
            text = printed.get(ordinal)
            match = lookup(text) if text else None
            if match is None:
                continue
            out.append(StaffLabel(
                staff_index=staff.staff_index, text=text,
                instrument=match.instrument, fifths_offset=match.fifths_offset,
                y_center_px=(staff.top_y + staff.bottom_y) / 2,
                confidence="high", alias=match.alias))
        return out

    ctx._labels_for_page = supplied
    # ...and do not take the "no text layer anywhere, so do not bother" branch,
    # which is correct in production and is the very thing being stood in for.
    ctx.has_text_layer = lambda *a, **k: True

    pdf = Path(truth["pdf"])
    if not pdf.exists():
        print(f"missing {pdf}", file=sys.stderr)
        return 1
    result = transcribe(pdf_path=pdf, pages=[truth["page_index"]],
                        weights=str(args.weights), dpi=truth["dpi"])
    dossier = None if args.no_dossier else resolve_dossier(truth["work_id"])
    summary = ctx.apply_contextual_analysis(
        result, pdf_path=pdf, dpi=truth["dpi"], apply_clefs=True, dossier=dossier)

    want = [s["clef"] for s in truth["slots"]]
    rows = []
    for page in result["pages"]:
        for system in page["systems"]:
            for ordinal, staff in enumerate(system["staves"]):
                rows.append((ordinal, want[ordinal], staff.get("clef"),
                             staff.get("clef_source") or "default"))
    arm = ("vision labels" if args.vision else "printed labels") + \
          (", pins OFF" if args.no_pins else ", pins on") + \
          (", NO dossier" if args.no_dossier else ", dossier")
    ok = sum(1 for _, w, g, _ in rows if w == g)
    print(f"\ncontextual — {summary.get('labelled_staves')} labels, "
          f"{summary.get('clefs_from_dossier')} clefs from the dossier")
    print(f"beet5-p48 [{arm}]: {ok}/{len(rows)} correct")
    for ordinal, w, g, src in rows:
        print(f"   {'ok ' if w == g else 'XX '}slot {ordinal:>2} "
              f"{truth['slots'][ordinal]['instrument']:<15} "
              f"want={w:<7} got={str(g):<7} ({src})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
