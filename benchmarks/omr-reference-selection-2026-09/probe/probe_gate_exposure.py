#!/usr/bin/env python3
"""Can the 20-row scan gate EXERCISE this change at all?

Every row of `benchmarks/omr-scan-e2e-2026-09/works.json` is a single-PAGE run,
and the bug is about pooling pages — so a flat gate result is expected rather
than reassuring, and "no regression" would overstate it. That is a claim about
coverage, and it can be MEASURED instead of asserted: the flag changes nothing
unless `build_reference` picks a different system, and which system it picks is
decided by the page's own systems' staff counts and label counts.

So this renders each row's page, detects its staves, reads its margins, and asks
both rules for a reference — ~10 s a row, against ~2 minutes to transcribe it.
Rows where the two rules pick the same reference CANNOT move, whatever the
transcription does with them.

    python3 .../probe_gate_exposure.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO))

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
WORKS = REPO / "benchmarks/omr-scan-e2e-2026-09/works.json"

from tools.omr.preprocessing import render_page            # noqa: E402
from tools.omr.staff_detector import detect_staves         # noqa: E402
from tools.omr.slots import SystemView, build_reference    # noqa: E402
from tools.omr import staff_labels_surya as S              # noqa: E402


def main():
    doc = json.loads(WORKS.read_text())
    dpi = doc["protocol"].get("dpi", 600)
    rows = doc["rows"]
    print(f"{len(rows)} rows, dpi {dpi} (the protocol's own)")
    exposed = []
    for r in rows:
        pdf = LIB / r["edition"]["catalog_path"]
        pi = r["page"]["pdf_page_index"]
        pws = detect_staves(render_page(pdf, pi, dpi=dpi))
        labs = {l.staff_index: l.instrument.name for l in
                S.read_staff_labels_surya(pws)
                if l.matched and l.instrument
                and l.confidence in ("high", "medium")}
        by_system = defaultdict(list)
        for st in sorted(pws.staves, key=lambda s: s.top_y):
            by_system[st.system_index].append(st)
        views = [SystemView(staves=sts,
                            labels={s.staff_index: labs[s.staff_index]
                                    for s in sts if s.staff_index in labs})
                 for _i, sts in sorted(by_system.items())]
        old = build_reference(views, most_labelled="off")
        new = build_reference(views, most_labelled="on")
        same = ([(s.index, s.instrument, s.group_index) for s in old]
                == [(s.index, s.instrument, s.group_index) for s in new])
        if not same:
            exposed.append(r["row_id"])
        print(f"  {r['row_id']:36s} systems="
              f"{[v.size for v in views]} labels={[len(v.labels) for v in views]}"
              f"  ref old={len(old)} new={len(new)}  "
              f"{'SAME' if same else '*** DIFFERS ***'}")
    print()
    print(f"rows whose reference CHANGES: {len(exposed)}/{len(rows)}"
          + (f"  {exposed}" if exposed else
             "  — the gate is blind to this flag by construction, and a flat "
             "result there is coverage of nothing"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
