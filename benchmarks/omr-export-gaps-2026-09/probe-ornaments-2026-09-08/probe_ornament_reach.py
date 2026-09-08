"""Would the ornament attach pass reach the ornaments this repository has read?

⚠️ WHAT THIS IS AND IS NOT. `transcribe._attach_ornaments_in_cell` runs at
TRANSCRIBE time, on `SymbolDetection` objects in a measure cell's CANONICAL
frame. Re-running it needs the detector, the weights and the PDF, none of which
exist in the container this was written in. So this probe re-implements the
same rule in PAGE PIXELS over a stored transcription's detection dicts, which
carry `bbox_page`. The rule is the same three lines (nearest notehead in x, on
the side the class names, within N median notehead widths); the FRAME is not.
It answers "is there a notehead there at all", not "does the shipped code path
place it" — the unit tests answer the second.

The one real transcription in this repository that carries ornament detections
is the Breitkopf Brahms 1 labeling batch: 3 pages, 10,523 detections, 8
`ornamentTrill` and — the finding that chose the whole shape of this work — ZERO
`tremolo1`-`tremolo5`.

    python3 benchmarks/omr-export-gaps-2026-09/probe-ornaments-2026-09-08/probe_ornament_reach.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.transcribe import (  # noqa: E402
    ornament_kind, _ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS)

TRANSCRIPTION = (ROOT / "benchmarks"
                 / "omr-labeling-hollow2-2026-09-breitkopf-brahms1"
                 / "transcription.json")


def _centre(box):
    """⚠️ `bbox_page` is [x, y, WIDTH, HEIGHT], not [x0, y0, x1, y1].

    The first draft of this probe read it as a corner pair and reported
    "0 of 8 marks reach a notehead" — a clean, plausible, WRONG zero, with
    every median notehead width coming out NEGATIVE and nothing saying so.
    `transcribe.py:202` states the format in a comment; the probe did not read
    it. A ZERO IS A SUSPECT, NOT A RESULT.
    """
    x, y, w, h = box
    return x + w / 2.0, y + h / 2.0


def attach_in_page_pixels(dets):
    """The `_attach_ornaments_in_cell` rule, in the frame this JSON stores."""
    heads = [d for d in dets if d.get("category") == "notehead"
             and len(d.get("bbox_page") or ()) == 4]
    marks = [(d, k) for d in dets
             if len(d.get("bbox_page") or ()) == 4
             and (k := ornament_kind(d.get("class") or "")) is not None]
    if not heads or not marks:
        return []
    widths = sorted(b[2] for b in (h["bbox_page"] for h in heads))
    nh_width = widths[len(widths) // 2] or 1.0
    limit = nh_width * _ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS
    placed = []
    for mark, (kind, strokes, above) in marks:
        mx, my = _centre(mark["bbox_page"])
        best = None
        for h in heads:
            hx, hy = _centre(h["bbox_page"])
            if above is True and my >= hy:
                continue
            if above is False and my <= hy:
                continue
            dx = abs(mx - hx)
            if dx > limit:
                continue
            if best is None or dx < best[0]:
                best = (dx, h)
        placed.append((mark, kind, strokes, best))
    return placed


def nh_width_sanity(result) -> float:
    """The median notehead width over the whole document, in page pixels.

    A guard rather than a statistic: the probe's first draft mis-read the bbox
    format and this quantity came out negative, which is what a report of
    "0 of 8" was standing on.
    """
    ws = sorted(d["bbox_page"][2]
                for page in result.get("pages", [])
                for system in page.get("systems", [])
                for staff in system.get("staves", [])
                for meas in staff.get("measures", [])
                for d in meas.get("detections", [])
                if d.get("category") == "notehead"
                and len(d.get("bbox_page") or ()) == 4)
    return ws[len(ws) // 2] if ws else 0.0


def main() -> int:
    result = json.loads(TRANSCRIPTION.read_text())
    classes: Counter = Counter()
    n_dets = n_cells = 0
    reached = []
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                for meas in staff.get("measures", []):
                    dets = meas.get("detections", [])
                    n_cells += 1
                    n_dets += len(dets)
                    classes.update(d.get("class") for d in dets)
                    reached.extend(attach_in_page_pixels(dets))

    print(f"transcription      {TRANSCRIPTION.relative_to(ROOT)}")
    print(f"POSITIVE CONTROLS  {len(result.get('pages', []))} pages, "
          f"{n_cells} measure cells, {n_dets} detections, "
          f"{len(classes)} distinct classes")
    orn = {c: n for c, n in classes.items() if ornament_kind(c or "")}
    print(f"                   noteheadBlackInSpace = "
          f"{classes.get('noteheadBlackInSpace', 0)} (a class we know fires)")
    print(f"ornament classes   {orn or 'NONE'}")
    trem = {c: n for c, n in classes.items()
            if (c or '').lower().startswith('tremolo')}
    print(f"tremolo classes    {trem or 'NONE — the finding'}")
    placed = [r for r in reached if r[3] is not None]
    assert nh_width_sanity(result) > 0, "median notehead width must be positive"
    print(f"\nreach              {len(placed)} of {len(reached)} marks find a "
          f"notehead within {_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS} notehead widths "
          "on the printed side")
    for mark, kind, strokes, best in reached:
        where = ("no notehead on that side within reach" if best is None
                 else f"dx={best[0]:.1f}px -> {best[1].get('class')}")
        print(f"  {mark.get('class'):18s} conf {mark.get('confidence', 0):.2f} "
              f"{kind:6s} {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
