"""Score the score-order prior against hand-read instrumentation.

    python3 benchmarks/omr-score-order/eval_score_order.py

Three evidence settings, because the prior's whole question is how much
POSITION alone is worth:

  position    staff count and order only — the unlabelled case it exists for.
  read clefs  plus whatever clefs the pipeline actually read on the page. This
              is what a real run has, and it is bounded by clef reading: on
              Beethoven 5 p.15 two string staves are misread as treble.
  true clefs  plus the clef each part is really printed in. The ceiling — what
              the prior could do if clef reading were solved.

  pipeline    `--pipeline`, and it needs the weights. The clefs a real
              `transcribe` run reads — which is what production actually hands
              `fit_layouts`, and is NOT the "read clefs" arm above.

THE "READ CLEFS" ARM IS NOT PRODUCTION, and quoting it as though it were sent a
session chasing the wrong number. It uses `locate_clef` alone, deliberately, so
this benchmark runs with no weights — but the CV locator supplies 3 staves of
166 on the ten-page clef corpus, where the detector supplies 97 at 98%. Measured
2026-09-01 on the two hand-read pages: locator clefs score precision 0.50, the
pipeline's own evidence 0.82, position alone 0.92.

Precision is the number that matters: a wrong instrument carries a wrong clef
and a wrong transposition with it, so naming nothing beats naming wrongly.

`--wide` adds two more truth sources that already existed in the repo, taking
the corpus from 2 pages of 1 edition to 9 pages of 4:

  the margin-label manifest   36 staves whose instrument the PDF text layer
                              names, over 12 systems of Beethoven 5 and 6
                              (`benchmarks/omr-margin-labels-2026-08`)
  the part-staff join page    Beethoven 5 p.48, 17 slots read by hand
                              (`benchmarks/omr-part-staff-join-2026-08`)

Their truth is PARTIAL per system — only the staves a reader could name — so a
page scores on the staves it has truth for and the rest are not counted either
way.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.instruments import lookup  # noqa: E402
from tools.omr.measure_extractor import detect_barlines  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.score_layouts import fit_layouts  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402
from tools.omr.clef_locator import locate_clef  # noqa: E402

TRUTH = Path(__file__).resolve().parent / "ground_truth.json"
MANIFEST = (REPO / "benchmarks" / "omr-margin-labels-2026-08"
            / "crops-w20" / "manifest.json")
JOIN = (REPO / "benchmarks" / "omr-part-staff-join-2026-08"
        / "ground-truth-beet5-p48.json")
IMSLP = REPO / "tools" / "omr" / "training" / "data" / "imslp"
WEIGHTS = (REPO / "omr-weights"
           / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt")


def canonical(name: str | None) -> str:
    """Both sides of the comparison through the lexicon, so `Bb Clarinet` from a
    layout and `Clarinetti` from a margin are the same instrument."""
    match = lookup(name or "")
    return match.instrument.name if match else (name or "")


def manifest_pages() -> list[dict]:
    """The margin-label corpus, as pages with PARTIAL truth.

    `truth` there is keyed by page staff index and only covers staves the PDF's
    own text layer named, so it becomes `parts_by_ordinal` — the aligner still
    fits the whole system, and only the truthed staves are scored.
    """
    if not MANIFEST.exists():
        return []
    out = []
    for entry in json.loads(MANIFEST.read_text()):
        work, _, edition = entry["work"].rpartition("_")
        pdf = IMSLP / work / "pdfs" / edition / "score.pdf"
        if not pdf.exists():
            continue
        order = list(entry["staff_indices"])
        by_ordinal = {}
        for staff_index, fact in entry["truth"].items():
            # Re-resolve the PRINTED TEXT through today's lexicon rather than
            # trusting the stored instrument. That file was written on
            # 2026-08-31 and froze a lexicon bug fixed hours later the same day:
            # Beethoven 5 p.59's three trombones are stored as `Tr. Alt.` ->
            # Alto, `Tr. Ten` -> Tenor and `Tr. Bas` -> Trumpet, two singers and
            # a trumpet where the page prints trombones. A stored resolution is
            # a measurement of the lexicon, and only the text is ground truth.
            hit = lookup(fact.get("text") or "")
            if hit is None:
                continue                       # read but unresolved: not truth
            if int(staff_index) in order:
                by_ordinal[order.index(int(staff_index))] = hit.instrument.name
        if not by_ordinal:
            continue
        out.append({
            "id": f"{edition}-p{entry['page_index']}s{entry['system_index']}",
            "pdf": str(pdf), "page_index": entry["page_index"], "dpi": 300,
            "system_index": entry["system_index"],
            "n_staves": len(order), "parts_by_ordinal": by_ordinal,
        })
    return out


def join_page() -> list[dict]:
    """Beethoven 5 p.48 — 17 slots read by hand, one system, no text layer."""
    if not JOIN.exists():
        return []
    g = json.loads(JOIN.read_text())
    pdf = Path(g["pdf"]).expanduser()
    if not pdf.exists():
        return []
    return [{
        "id": g["id"], "pdf": str(pdf), "page_index": g["page_index"],
        "dpi": g["dpi"], "system_index": 0,
        "parts": [slot["instrument"] for slot in g["slots"]],
    }]


def pipeline_clefs(page: dict) -> dict[int, str]:
    """The clefs a real run reads, by ordinal within the system.

    This is `contextual._read_clefs_by_slot`'s input — every reader the pipeline
    has, not the CV locator alone — restricted to the system the truth covers.
    """
    from tools.omr.transcribe import transcribe          # noqa: PLC0415

    result = transcribe(pdf_path=Path(page["pdf"]), pages=[page["page_index"]],
                        weights=str(WEIGHTS), dpi=page["dpi"])
    out: dict[int, str] = {}
    for rendered in result["pages"]:
        for system in rendered.get("systems", []):
            if system.get("system_index") != page["system_index"]:
                continue
            for ordinal, staff in enumerate(system.get("staves", [])):
                if staff.get("clef_source") and staff.get("clef"):
                    out[ordinal] = staff["clef"]
    return out


def read_clefs(pws) -> dict[int, str]:
    """The clefs the CV locator reads on this page, by ordinal in the system.

    Deliberately the locator alone rather than a full `transcribe` run: it needs
    no weights, so this benchmark runs anywhere, and it is the same reader the
    pipeline falls back on where the detector is silent.
    """
    cells = header_cells_for_page(pws)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    out: dict[int, str] = {}
    for ordinal, staff in enumerate(staves):
        cell = cells.get(staff.staff_index)
        if cell is None:
            continue
        found = locate_clef(cell)
        if found is not None:
            out[ordinal] = found.read.name
    return out


def true_clefs(parts: list[str]) -> dict[int, str]:
    out = {}
    for i, name in enumerate(parts):
        match = lookup(name)
        if match:
            out[i] = match.instrument.default_clef
    return out


def production_names(page: dict) -> dict[int, tuple[str | None, str | None]]:
    """`{staff_index: (instrument, source)}` from the real contextual pass.

    The arms above fit ONE SYSTEM at a time, and production does not: it fits
    `len(reference)` — the page's slot set, built by `assign_slots` across every
    system — and one fit then reaches every system through the slots. A
    per-system number is therefore no more a description of production than the
    locator-only "read clefs" arm is, and this session found both the same way.

    Label readers are switched off so that what is measured is the PRIOR, which
    is this benchmark's whole question; a page whose margin can be read does not
    need it.
    """
    from tools.omr import contextual                      # noqa: PLC0415
    from tools.omr.assist import Assist                   # noqa: PLC0415
    from tools.omr.transcribe import transcribe           # noqa: PLC0415

    result = transcribe(pdf_path=Path(page["pdf"]), pages=[page["page_index"]],
                        weights=str(WEIGHTS), dpi=page["dpi"])
    real = contextual.read_staff_labels
    contextual.read_staff_labels = lambda pws: []
    try:
        contextual.apply_contextual_analysis(
            result, pdf_path=Path(page["pdf"]), dpi=page["dpi"],
            apply_clefs=False, assist=Assist("none"),
            surya_fallback=False, ocr_fallback=False)
    finally:
        contextual.read_staff_labels = real

    out: dict[int, tuple[str | None, str | None]] = {}
    for rendered in result["pages"]:
        for system in rendered.get("systems", []):
            if system.get("system_index") != page["system_index"]:
                continue
            for ordinal, staff in enumerate(system.get("staves", [])):
                out[ordinal] = (staff.get("instrument"),
                                staff.get("instrument_source"))
    return out


def score_names(page: dict, names: dict[int, tuple]) -> tuple[int, int]:
    """`(named, correct)` for the production arm, over truthed staves only."""
    truth = ({int(k): v for k, v in page["parts_by_ordinal"].items()}
             if "parts_by_ordinal" in page
             else dict(enumerate(page["parts"])))
    named = [(i, n) for i, (n, _src) in names.items() if n]
    scored = [(i, n) for i, n in named if i in truth]
    ok = sum(1 for i, n in scored if canonical(n) == canonical(truth[i]))
    return len(scored), ok


def score(page: dict, fit) -> tuple[int, int]:
    """`(named, correct)` over the staves this page has truth for.

    A page with `parts` is truthed throughout; one with `parts_by_ordinal` is
    truthed in places, and a name the aligner gives an untruthed staff is not
    evidence either way — counting it as wrong would punish coverage the corpus
    simply cannot check.
    """
    named = [(i, a) for i, a in enumerate(fit.assignment) if a is not None]
    if "parts_by_ordinal" in page:
        truth = {int(k): v for k, v in page["parts_by_ordinal"].items()}
        scored = [(i, a) for i, a in named if i in truth]
        ok = sum(1 for i, a in scored if canonical(a) == canonical(truth[i]))
        return len(scored), ok
    truth = page["parts"]
    ok = sum(1 for i, a in named
             if i < len(truth) and canonical(a) == canonical(truth[i]))
    return len(named), ok


def truth_size(page: dict) -> int:
    return (len(page["parts_by_ordinal"]) if "parts_by_ordinal" in page
            else len(page["parts"]))


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--wide", action="store_true",
                    help="add the margin-label manifest and the join page — "
                         "9 pages of 4 editions instead of 2 of 1")
    ap.add_argument("--pipeline", action="store_true",
                    help="also score the clefs a real transcribe run reads, "
                         "which is what production hands the prior. Needs the "
                         "weights; the other arms do not.")
    ap.add_argument("--production", action="store_true",
                    help="score the prior through the real contextual pass — "
                         "page-level fit, label readers off. The only arm that "
                         "describes what a run actually does. Needs the weights.")
    args = ap.parse_args()

    pages = json.loads(TRUTH.read_text())["pages"]
    if args.wide:
        pages = pages + join_page() + manifest_pages()
    print(f"{'page':22s} {'evidence':14s} {'layout':22s} {'named':>7} "
          f"{'correct':>8} {'precision':>10} {'coverage':>9}")
    totals: dict[str, list[int]] = {}
    for page in pages:
        pdf = Path(page["pdf"])
        if not pdf.exists():
            print(f"{page['id']:22s} SKIP (missing {pdf.name})")
            continue
        pws = detect_barlines(detect_staves(
            render_page(pdf, page["page_index"], dpi=page["dpi"])))
        staves = sorted(
            (s for s in pws.staves if s.system_index == page["system_index"]),
            key=lambda s: s.top_y)
        if not staves:
            print(f"{page['id']:22s} SKIP (no system {page['system_index']})")
            continue
        # A page whose layout this run reads differently from the one the truth
        # was recorded against cannot be scored by ordinal.
        if page.get("n_staves") and len(staves) != page["n_staves"]:
            print(f"{page['id']:22s} SKIP ({len(staves)} staves against "
                  f"{page['n_staves']} in truth — ordinals would not correspond)")
            continue
        settings = {
            "position": None,
            "read clefs": read_clefs(pws),
        }
        if args.pipeline:
            settings["PIPELINE clefs"] = pipeline_clefs(page)
        if "parts" in page:
            settings["true clefs"] = true_clefs(page["parts"])
        for label, clefs in settings.items():
            fit = fit_layouts(len(staves), None, clefs)
            if fit is None:
                print(f"{page['id']:22s} {label:14s} ABSTAINED")
                continue
            n_named, ok = score(page, fit)
            precision = ok / n_named if n_named else 0.0
            coverage = n_named / max(1, truth_size(page))
            print(f"{page['id']:22s} {label:14s} {fit.layout.name:22s} "
                  f"{n_named:3d}/{truth_size(page):<3d} {ok:8d} "
                  f"{precision:10.2f} {coverage:9.2f}")
            acc = totals.setdefault(label, [0, 0])
            acc[0] += n_named
            acc[1] += ok
        if args.production:
            names = production_names(page)
            n_named, ok = score_names(page, names)
            deduced = sum(1 for _i, (n, src) in names.items()
                          if n and src == "score_order")
            print(f"{page['id']:22s} {'PRODUCTION':14s} "
                  f"{'(page-level fit)':22s} {n_named:3d}/{truth_size(page):<3d} "
                  f"{ok:8d} {ok / n_named if n_named else 0:10.2f} "
                  f"{n_named / max(1, truth_size(page)):9.2f}"
                  f"   {deduced} deduced")
            acc = totals.setdefault("PRODUCTION", [0, 0])
            acc[0] += n_named
            acc[1] += ok
    print()
    for label, (named, ok) in totals.items():
        print(f"  total {label:14s} named {named:3d}  correct {ok:3d}  "
              f"precision {ok / named if named else 0:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
