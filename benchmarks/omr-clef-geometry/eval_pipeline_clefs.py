"""What clef does the PIPELINE finally put on each staff?

`eval_orchestral_clefs.py` scores the CV locator's precision, and
`probe_clef_rejection.py` scores coverage of the header window. Neither answers
the question everything downstream actually depends on: after the detector, the
locator, the header vote and the positional default have all had their say,
what clef does a staff end up with, and is it right?

That number matters more than the parts, because a staff carries its clef into
every pitch on it, and into which slot table its key signature is fitted. Three
of this project's threads ended by pointing at it (docs/next-steps-omr-2026-08-28.md).

Ground truth is the hand-read clefs already in
`benchmarks/omr-key-signature/ground_truth.json` — one `clef` per staff ordinal
within a system, for pages whose systems all carry the same instrumentation.

    python3 benchmarks/omr-clef-geometry/eval_pipeline_clefs.py

Reports accuracy overall and split by SOURCE, because "wrong" means different
things: a clef the detector read wrongly is a detection error, while a staff
carrying the positional default was never read at all and is only right by
luck — the default is treble, and most staves are treble.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.contextual import apply_contextual_analysis  # noqa: E402
from tools.omr.dossier import resolve_dossier  # noqa: E402
from tools.omr.transcribe import transcribe  # noqa: E402

TRUTH = REPO / "benchmarks" / "omr-key-signature" / "ground_truth.json"
# A fourth page, kept beside the join benchmark rather than folded into the file
# above, and deliberately: several other benchmarks read that file, and moving
# its page count would silently move their denominators too. Its clefs are
# hand-read from the print (see `how_the_clefs_were_read` in it).
EXTRA = (REPO / "benchmarks" / "omr-part-staff-join-2026-08"
         / "ground-truth-beet5-p48.json")
WEIGHTS = REPO / "omr-weights" / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"

# The three pages this benchmark has always carried. Their subtotal is reported
# separately so the historical number stays directly comparable across sessions.
BASE_PAGES = ("beet5-p2", "pastoral-p2", "wtc-p17")

# The work each ground-truth page comes from, for --dossier. Only pages whose
# work has a generated dossier can be scored that way.
WORKS = {"beet5-p2": "beethoven-sym5-mvt1", "pastoral-p2": "beethoven-sym6-mvt1",
         "beet5-p48": "beethoven-sym5-mvt4"}


def extra_pages() -> list[dict]:
    """The join benchmark's page, in this benchmark's own page schema.

    It is the page where the part-staff join has something to prove: 23 parts on
    17 staves, printed out of the part list's order, and three of its staves are
    the alto, tenor and bass trombones that no detector reads.
    """
    if not EXTRA.exists():
        return []
    g = json.loads(EXTRA.read_text())
    if not all("clef" in slot for slot in g["slots"]):
        return []
    return [{
        "id": g["id"],
        "work": g.get("_about", ""),
        "pdf": g["pdf"],
        "page_index": g["page_index"],
        "dpi": g["dpi"],
        "n_systems": 1,
        "staves": [{"ordinal": slot["slot"], "instrument": slot["instrument"],
                    "clef": slot["clef"], "fifths": 0} for slot in g["slots"]],
    }]


def score_page(page: dict, weights: Path, dpi: int | None,
               contextual: bool = False, use_dossier: bool = False,
               vision_labels: bool = False) -> list[dict]:
    pdf = Path(page["pdf"])
    if not pdf.is_absolute():
        pdf = REPO / pdf
    if not pdf.exists():
        print(f"{page['id']:14s} SKIP (missing {pdf.name})")
        return []
    result = transcribe(
        pdf_path=pdf, pages=[page["page_index"]], weights=str(weights),
        dpi=dpi or page["dpi"],
    )
    if contextual:
        # The pass that proposes a clef from the instrument's own convention,
        # vetoed by the staff's register — and only where nothing read a clef.
        dossier = (resolve_dossier(WORKS[page["id"]])
                   if use_dossier and page["id"] in WORKS else None)
        summary = apply_contextual_analysis(
            result, pdf_path=pdf, dpi=dpi or page["dpi"], apply_clefs=True,
            dossier=dossier, vision_fallback=vision_labels)
        print(f"  {page['id']}: contextual — {summary.get('labelled_staves')} labels, "
              f"{summary.get('clefs_applied')} instrument corrections, "
              f"{summary.get('clefs_filled_from_slot')} filled from another system, "
              f"{summary.get('clefs_from_dossier')} from the dossier"
              f"  tiers={summary.get('label_tiers')}")
        # Read off the page and then dropped, because nothing in the lexicon
        # matched. Printed because it is otherwise invisible — the page just
        # behaves as though those staves carry no label.
        if summary.get("unresolved_labels"):
            print(f"  {page['id']}: UNRESOLVED labels (lexicon gaps): "
                  + ", ".join(repr(t) for t in summary["unresolved_labels"]))
    truth = {s["ordinal"]: s["clef"] for s in page["staves"]}
    rows = []
    for page_d in result["pages"]:
        for system in page_d["systems"]:
            staves = system["staves"]
            # Ground truth is by ordinal within the system, which only lines up
            # when the system has the instrumentation the truth describes. A
            # system with a different staff count is a different reading of the
            # page, and scoring it by ordinal would compare unrelated staves.
            if len(staves) != len(truth):
                print(f"  {page['id']}: system {system.get('system_index')} has "
                      f"{len(staves)} staves against {len(truth)} in ground "
                      f"truth — skipped, ordinals would not correspond")
                continue
            for ordinal, staff in enumerate(staves):
                rows.append({
                    "page": page["id"],
                    "system": system.get("system_index"),
                    "ordinal": ordinal,
                    "want": truth[ordinal],
                    "got": staff.get("clef"),
                    "source": staff.get("clef_source") or "default",
                })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, help="override each page's own DPI")
    ap.add_argument("--weights", type=Path, default=WEIGHTS)
    ap.add_argument("--out", type=Path, help="write the per-staff rows as JSON")
    ap.add_argument("--dossier", action="store_true",
                    help="let the work's own parts supply clefs where the join is anchored")
    ap.add_argument("--contextual", action="store_true",
                    help="run contextual analysis (instrument identity -> clef) first")
    ap.add_argument("--vision-labels", action="store_true",
                    help="COSTS API CREDITS. Read the margin with Claude where the "
                         "text layer yields nothing — up to 3 systems per page "
                         "(`vision_system_budget`), about a cent each.")
    args = ap.parse_args()
    if not args.weights.exists():
        print(f"no weights at {args.weights}", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for page in json.loads(TRUTH.read_text())["pages"] + extra_pages():
        rows.extend(score_page(page, args.weights, args.dpi,
                               args.contextual or args.dossier, args.dossier,
                               args.vision_labels))
    if not rows:
        print("no pages scored")
        return 1

    by_source: dict[str, Counter] = {}
    for r in rows:
        c = by_source.setdefault(r["source"], Counter())
        c["n"] += 1
        c["ok"] += 1 if r["got"] == r["want"] else 0

    total = len(rows)
    correct = sum(1 for r in rows if r["got"] == r["want"])
    print(f"\n{total} staves with hand-read clefs")
    print(f"  correct overall: {correct}/{total} = {correct / total:.0%}")

    print(f"\n  {'page':12s} {'staves':>7} {'correct':>8} {'accuracy':>9}")
    for page_id in dict.fromkeys(r["page"] for r in rows):
        pr = [r for r in rows if r["page"] == page_id]
        ok = sum(1 for r in pr if r["got"] == r["want"])
        print(f"  {page_id:12s} {len(pr):7d} {ok:8d} {ok / len(pr):9.0%}")
    base = [r for r in rows if r["page"] in BASE_PAGES]
    if base and len(base) != total:
        ok = sum(1 for r in base if r["got"] == r["want"])
        print(f"  {'(base 3)':12s} {len(base):7d} {ok:8d} {ok / len(base):9.0%}"
              f"   <- the historical number")
    print(f"\n  {'source':12s} {'staves':>7} {'correct':>8} {'accuracy':>9}")
    for source, c in sorted(by_source.items(), key=lambda kv: -kv[1]["n"]):
        print(f"  {source:12s} {c['n']:7d} {c['ok']:8d} {c['ok'] / c['n']:9.0%}")

    wrong = [r for r in rows if r["got"] != r["want"]]
    if wrong:
        print(f"\n  the {len(wrong)} wrong readings, by (want -> got):")
        for (want, got), n in Counter((r["want"], r["got"]) for r in wrong).most_common():
            print(f"    {want:7s} -> {got or 'none':7s}  x{n}")
    if args.out:
        args.out.write_text(json.dumps(rows, indent=2) + "\n")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
