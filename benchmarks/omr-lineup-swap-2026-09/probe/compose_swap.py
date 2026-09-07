"""`compose.py`, with the ONE call-site change the swap split needs, so the
identity effect can be measured before that change is asked for.

`movement_reference.lineup_spans` now takes optional margin evidence, but its
only caller — `slots._span_views` — does not pass it, and `slots.py` is owned by
another session today. So the probe installs the five-line version here:

    page_labels = [(page_index,
                    [[v.labels.get(s.staff_index) for s in v.staves]
                     for v in views])
                   for pws, views in zip(pages, all_views)]
    ... movement_reference.lineup_spans(page_systems, page_labels)

`SystemView.labels` is already `{staff_index: instrument name}` filtered to
`MIN_LABEL_CONFIDENCE`, so no new evidence is read and no new cost is paid —
the swap split sees exactly what the aligner sees.

Everything else is `compose.py` unchanged, including its one-read-pass control.

    compose_swap.py PDF --out-dir DIR --pages 0-98 --cache DIR --tag swapon
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "benchmarks" / "omr-spans-veto-composition-2026-09"
                       / "probe"))

from tools.omr import movement_reference                    # noqa: E402
from tools.omr import slots as slots_mod                    # noqa: E402


def _span_views_with_labels(pages, all_views):
    page_systems = [
        (pws.page.page_index, [v.size for v in views])
        for pws, views in zip(pages, all_views)
    ]
    page_labels = [
        (pws.page.page_index,
         [[v.labels.get(s.staff_index) for s in v.staves] for v in views])
        for pws, views in zip(pages, all_views)
    ]
    by_page = {pws.page.page_index: views
               for pws, views in zip(pages, all_views)}
    return [[v for p in span for v in by_page.get(p, [])]
            for span in movement_reference.lineup_spans(
                page_systems, page_labels)]


slots_mod._span_views = _span_views_with_labels

import compose  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(compose.main())
