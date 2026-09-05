#!/usr/bin/env python3
"""Reproduce the runaway-block margin-label failure on two real pages, and
score the same systems against a known-good comparison page.

Surfaced 2026-09-04 by the lexicon sweep in `benchmarks/omr-lexicon-2026-09/`:
a whole system's margin — every instrument name on the page — sometimes
arrives as ONE Surya OCR block instead of one block per staff, and gets forced
onto whichever staff its centroid lands nearest. `tools/omr/_surya_worker.py`'s
`_assign` now rejects a block whose own height swallows most of the system's
tick span rather than assigning it. This script is what measured the two
populations the threshold sits between.

    python3 benchmarks/omr-margin-labels-blob-2026-09/reproduce_blob.py

Needs `.venv-surya` (`python3 -m tools.omr.staff_labels_surya --bootstrap`)
and the score library (`library_root()`) — read-only, no library writes.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.library.score_library import library_root          # noqa: E402
from tools.omr.preprocessing import render_page                # noqa: E402
from tools.omr.staff_detector import detect_staves              # noqa: E402
from tools.omr.staff_labels_vision import build_margin_crop     # noqa: E402
from tools.omr import staff_labels_surya as sls                 # noqa: E402

#: (label, edition-relative path, pdf page index, a staff_index known to sit
#: in the affected system). The last two entries are known-good comparisons —
#: real pages where Surya DID split the margin into one block per staff.
CASES = [
    ("mahler5-BAD (p163, 19 staves -> one block, resolved Trombone)",
     "editions/mahler/symphony-5/mahler--symphony-5--unidentified-scan-2016--local.pdf",
     163, 10),
    ("beethoven5-BAD (imslp-575951 p58, 17 staves -> one block, resolved Piccolo)",
     "editions/beethoven/symphony-5-op67/"
     "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp575951.pdf",
     58, 8),
    ("bolero-GOOD (imslp421137 p1, first qualifying system, split correctly)",
     "editions/ravel/bolero-m-81/ravel--bolero-m-81--2016--imslp421137.pdf",
     1, None),
]


def main() -> int:
    lib = library_root()
    systems, meta = [], []
    for name, rel, page_idx, target_staff in CASES:
        pdf = lib / rel
        if not pdf.is_file():
            print(f"  MISSING: {pdf}", file=sys.stderr)
            continue
        page = render_page(pdf, page_idx, dpi=600)
        pws = detect_staves(page)
        by_system: dict[int, list] = {}
        for s in sorted(pws.staves, key=lambda s: s.top_y):
            by_system.setdefault(s.system_index, []).append(s)
        for sysidx, staves in sorted(by_system.items()):
            idxs = [st.staff_index for st in staves]
            if target_staff is not None and target_staff not in idxs:
                continue
            if len(staves) < 2:
                continue
            crop = build_margin_crop(pws, staves)
            if crop is None:
                continue
            systems.append({
                "png_b64": base64.standard_b64encode(crop.png).decode("ascii"),
                "staff_indices": list(crop.staff_indices),
                "tick_ys": list(crop.tick_ys),
                "gutter_px": crop.gutter_px,
            })
            meta.append((name, page_idx, sysidx, len(staves)))
            if target_staff is None:
                break  # one system is enough for the comparison case

    if not systems:
        print("nothing to read — is the score library present?", file=sys.stderr)
        return 1

    python = sls.interpreter()
    proc = subprocess.run([str(python), str(sls._WORKER)],
                          input=json.dumps({"systems": systems}),
                          capture_output=True, text=True, timeout=600)
    if proc.returncode != 0 and not proc.stdout.strip():
        print("worker failed:", proc.stderr[-2000:], file=sys.stderr)
        return 1
    payload = json.loads(proc.stdout)

    for (name, page_idx, sysidx, n_staves), sys_job, entry in zip(
            meta, systems, payload["systems"]):
        tick_ys = sys_job["tick_ys"]
        span = max(tick_ys) - min(tick_ys) if len(tick_ys) > 1 else 0.0
        print(f"=== {name}  p{page_idx} sys{sysidx}  "
              f"{n_staves} staves  span={span:.0f}px ===")
        if entry.get("error"):
            print("  ERROR:", entry["error"])
            continue
        for rl in sorted(entry.get("raw_lines", []),
                         key=lambda r: r["height"], reverse=True):
            frac = rl["height"] / span if span else float("nan")
            print(f"    h={rl['height']:7.1f}  frac={frac:.3f}  "
                  f"{rl['text'][:55]!r}")
        print(f"  -> assigned labels: {entry.get('labels')}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
