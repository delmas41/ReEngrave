"""ROADMAP 2.6b — CLAUDE.md rule 7: 'a control must be able to fail.' Runs
`crop_losers_2_6b._frame_ok` on the same 24 crops' FILED-staff lines, once at
the record's true geometry and once with those lines shifted half a staff
space, against the same 600 dpi render. If both pass, the control is
vacuous; FINDINGS.md §12 reports the result (24/24 pass true, 0/24 pass
shifted).

    python3 benchmarks/omr-owner-domain-2026-09/check_frame_control_can_fail_2_6b.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from crop_losers_2_6b import _frame_ok, PDF, DPI  # noqa: E402


def main() -> int:
    import fitz
    import numpy as np

    cache = json.loads((HERE / "out" / "o26b-cache.json").read_text())
    manifest = json.loads((HERE / "out" / "print" / "o26b-manifest.json")
                          .read_text())
    lines_of, spacing_of = cache["lines_of"], cache["spacing_of"]

    doc = fitz.open(str(PDF))
    pages = {}
    n_checked = n_true = n_shifted = 0
    for c in manifest["crops"]:
        own = c["filed_staff"]
        if own not in lines_of:
            continue
        p = int(c["subject"].split("/")[1])
        if p not in pages:
            pm = doc[p].get_pixmap(dpi=DPI)
            arr = (np.frombuffer(pm.samples, dtype=np.uint8)
                   .reshape(pm.height, pm.width, pm.n)[:, :, :3]
                   .mean(axis=2).astype(float))
            pages[p] = arr
        arr = pages[p]
        sp = spacing_of.get(own, 40.0)
        ok_true, _ = _frame_ok(arr, lines_of[own], sp)
        shifted = [y + sp / 2.0 for y in lines_of[own]]
        ok_shift, _ = _frame_ok(arr, shifted, sp)
        n_checked += 1
        n_true += int(ok_true)
        n_shifted += int(ok_shift)

    print(f"checked {n_checked}: pass at true lines {n_true}/{n_checked}, "
          f"pass at lines shifted half a space {n_shifted}/{n_checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
