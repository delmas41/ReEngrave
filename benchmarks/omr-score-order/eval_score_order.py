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

Precision is the number that matters: a wrong instrument carries a wrong clef
and a wrong transposition with it, so naming nothing beats naming wrongly.
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


def main() -> int:
    pages = json.loads(TRUTH.read_text())["pages"]
    print(f"{'page':18s} {'evidence':12s} {'layout':22s} {'named':>7} "
          f"{'correct':>8} {'precision':>10} {'coverage':>9}")
    totals: dict[str, list[int]] = {}
    for page in pages:
        pdf = Path(page["pdf"])
        if not pdf.exists():
            print(f"{page['id']:18s} SKIP (missing {pdf.name})")
            continue
        pws = detect_barlines(detect_staves(
            render_page(pdf, page["page_index"], dpi=page["dpi"])))
        staves = sorted(
            (s for s in pws.staves if s.system_index == page["system_index"]),
            key=lambda s: s.top_y)
        truth = page["parts"]
        settings = {
            "position": None,
            "read clefs": read_clefs(pws),
            "true clefs": true_clefs(truth),
        }
        for label, clefs in settings.items():
            fit = fit_layouts(len(staves), None, clefs)
            if fit is None:
                print(f"{page['id']:18s} {label:12s} ABSTAINED")
                continue
            named = [(i, a) for i, a in enumerate(fit.assignment) if a is not None]
            ok = sum(1 for i, a in named if i < len(truth) and a == truth[i])
            precision = ok / len(named) if named else 0.0
            coverage = len(named) / max(1, len(truth))
            print(f"{page['id']:18s} {label:12s} {fit.layout.name:22s} "
                  f"{len(named):3d}/{len(truth):<3d} {ok:8d} {precision:10.2f} "
                  f"{coverage:9.2f}")
            acc = totals.setdefault(label, [0, 0])
            acc[0] += len(named)
            acc[1] += ok
    print()
    for label, (named, ok) in totals.items():
        print(f"  total {label:12s} named {named:3d}  correct {ok:3d}  "
              f"precision {ok / named if named else 0:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
