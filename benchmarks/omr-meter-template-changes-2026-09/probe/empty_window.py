#!/usr/bin/env python3
"""THE NUMBER THAT DECIDES THIS JOB: what does the template reader say when it
is handed a mid-staff crop that prints NO meter?

⚠️⚠️ THIS PROJECT HAS ALREADY PAID FOR THIS ONCE, IN THE KEY-SIGNATURE FAMILY.
CLAUDE.md, in terms: *"the locator found no run and abstained; the template
found a clean window and answered a confident `fifths: 0` — a key signature
fabricated out of a crop containing none. The reader that can say 'zero' is the
one that must never be given an empty window."* `locate_time_signature`'s
`min_score` was calibrated on HEADER windows, where a meter is usually present.
A mid-staff bar head is an empty window almost everywhere.

So this probe hands it 1,600+ such windows off REAL SCANNED PAGES that print no
meter change anywhere, and counts how often it answers. It then asks the second
question, which is the one the design turns on: **do two staves of one system
ever agree on the same false meter at the same bar?**

WHAT IT RUNS ON, and why that is not a choice. A cloud container has no
`omr-weights/` and no `library/`, so no page can be transcribed. What it DOES
have is real scanned page rasters committed under `benchmarks/` for other
investigations — Brahms 1 / Breitkopf and Beethoven 5 / Litolff, two publishers
— and the whole pipeline up to the measure cell needs no weights at all:
`detect_staves` -> `detect_barlines` -> `extract_measures` -> `remove_staff_lines`.
That is the same code path a real run takes to build the crop this reader is
handed, so the crops are not a simulation of the input, they ARE the input.

⚠️ EVERY WINDOW HERE IS AN EMPTY ONE. These are continuation pages of movements
already under way; none prints a mid-staff meter change, so every answer above
the floor is a FALSE POSITIVE and no answer is a miss. That makes this a
one-sided measurement, and the POSITIVE CONTROL is what keeps it from being a
measurement of a dead instrument: a real Bravura meter is stamped into a sample
of the very same windows, at the staff's own scale, and the reader must find it.

    python3 .../probe/empty_window.py                 # the table
    python3 .../probe/empty_window.py --check         # non-zero if DEAD
    python3 .../probe/empty_window.py --spaces 4 6 8  # the width sweep

`--check` fails when the probe assessed nothing, or when the positive control
does not answer — never on a threshold.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import statistics
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import cv2                                                     # noqa: E402
import numpy as np                                             # noqa: E402

from tools.omr.header_ink import staff_metrics                 # noqa: E402
from tools.omr.measure_extractor import (detect_barlines,      # noqa: E402
                                         extract_measures)
from tools.omr.staff_detector import detect_staves             # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines    # noqa: E402
from tools.omr.time_signature_locator import (                 # noqa: E402
    DEFAULT_LOCATOR_CONFIG, _meter_templates, locate_time_signature)
from tools.omr.types import PageImage                          # noqa: E402

#: Real scanned pages committed for other investigations. Each is a
#: CONTINUATION page — the movement is already under way and no meter change is
#: printed on it — which is what makes every reading here a false positive.
PAGES = [
    ("brahms1-p006", "benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/page006_full.png"),
    ("brahms1-p022", "benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/page022_full.png"),
    ("brahms1-p042", "benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/page042_full.png"),
    ("brahms1-p043", "benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/page043_full.png"),
    ("brahms1-p044", "benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/page044_full.png"),
    ("brahms1-p045", "benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/page045_full.png"),
    ("beet5lit-p056", "benchmarks/omr-veto-refusal-pricing-2026-09/out/page056_full.png"),
    ("beet5lit-p057", "benchmarks/omr-veto-refusal-pricing-2026-09/out/page057_full.png"),
    ("beet5lit-p063", "benchmarks/omr-veto-refusal-pricing-2026-09/out/page063_full.png"),
    ("beet5lit-p086", "benchmarks/omr-veto-refusal-pricing-2026-09/out/page086_full.png"),
]

#: Stamp the positive control into every Nth window, so it costs a tenth of the
#: run rather than doubling it.
POSITIVE_CONTROL_EVERY = 7


def _page(path: pathlib.Path) -> PageImage:
    grey = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    binary = cv2.adaptiveThreshold(grey, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 10)
    return PageImage(pdf_path=path, page_index=0, dpi=300,
                     rgb=cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR), binary=binary)


def _cells(path: pathlib.Path):
    pws = detect_barlines(detect_staves(_page(path)))
    cells = extract_measures(pws)
    remove_staff_lines(cells)
    return pws, cells


def head_slice(cell, spaces: float):
    """The first `spaces` staff spaces of a measure cell — ⚠️ THE SAME SLICE
    `gather._bar_head_window` takes, deliberately restated here rather than
    imported, because this probe must be able to run against a tree where the
    gatherer does not exist yet. The two are pinned together by
    `test_meter_template_at_bar.TestTheProbeAndTheGathererAgree`."""
    metrics = staff_metrics(cell)
    if metrics is None:
        return None
    width = int(round(spaces * metrics[0]))
    if width < 8:
        return None
    width = min(int(cell.image.shape[1]), width)
    return dataclasses.replace(
        cell, image=cell.image[:, :width],
        image_no_staff=(cell.image_no_staff[:, :width]
                        if cell.image_no_staff is not None else None))


def stamp_meter(cell, raw: str = "3/4"):
    """Paste a real Bravura meter into this window at the staff's own scale.

    ⚠️ THE POSITIVE CONTROL, and it is deliberately OPTIMISTIC: clean template
    ink on a real scanned surround. A printed, scanned meter would score LOWER,
    so the scores it produces are an UPPER bound on what a true reading looks
    like and must never be quoted as the true-positive distribution.
    """
    metrics = staff_metrics(cell)
    if metrics is None:
        return None
    spacing, top, _bottom = metrics
    glyph = None
    for (_n, _d, r), tpl in _meter_templates(
            DEFAULT_LOCATOR_CONFIG.template_em_px,
            tuple(DEFAULT_LOCATOR_CONFIG.meters)):
        if r == raw:
            glyph = tpl
            break
    if glyph is None:
        return None
    height = int(round(4 * spacing))
    width = max(2, int(round(glyph.shape[1] * height / glyph.shape[0])))
    resized = cv2.resize(glyph, (width, height), interpolation=cv2.INTER_AREA)
    ink = resized > 127
    out = cell.image.copy()
    nostaff = (cell.image_no_staff.copy()
               if cell.image_no_staff is not None else None)
    y0 = int(round(top - 0.5 * spacing))
    x0 = int(round(0.4 * spacing))
    for canvas in (out, nostaff):
        if canvas is None:
            continue
        sub = canvas[y0:y0 + height, x0:x0 + width]
        if sub.shape[0] != height or sub.shape[1] != width:
            return None
        sub[ink] = 0
    return dataclasses.replace(cell, image=out, image_no_staff=nostaff)


def run(spaces_list, out_json=None) -> dict:
    rows: list[dict] = []
    positive = {"tried": 0, "answered": 0, "right_meter": 0, "scores": []}
    per_page: dict = {}

    for label, rel in PAGES:
        path = ROOT / rel
        if not path.is_file():
            print(f"{label}: MISSING {rel}")
            continue
        pws, cells = _cells(path)
        system_of = {s.staff_index: s.system_index for s in pws.staves}
        counts = {sp: 0 for sp in spaces_list}
        seen = 0
        for cell in cells:
            if cell.measure_index == 0:
                continue                 # cell 0 is the header's business
            for spaces in spaces_list:
                window = head_slice(cell, spaces)
                if window is None:
                    continue
                counts[spaces] += 1
                # min_score=0.0 so the near-misses are on the record too: the
                # refusals are what say how much headroom the floor has.
                found = locate_time_signature(window, min_score=0.0)
                if found is None:
                    continue
                rows.append({
                    "page": label, "spaces": spaces,
                    "system": system_of.get(cell.staff_index),
                    "staff": cell.staff_index, "cell": cell.measure_index,
                    "raw": found.raw, "score": round(found.score, 4),
                    "margin": (round(found.score_margin, 4)
                               if found.score_margin is not None else None),
                })
            seen += 1
            if seen % POSITIVE_CONTROL_EVERY == 0:
                base = head_slice(cell, min(spaces_list))
                stamped = stamp_meter(base, "3/4") if base is not None else None
                if stamped is not None:
                    positive["tried"] += 1
                    got = locate_time_signature(stamped)
                    if got is not None:
                        positive["answered"] += 1
                        positive["scores"].append(round(got.score, 3))
                        if got.raw == "3/4":
                            positive["right_meter"] += 1
        per_page[label] = counts
        print(f"{label}: windows {counts}")

    floor = DEFAULT_LOCATOR_CONFIG.min_score
    print(f"\nthe reader's own floor (`min_score`): {floor}")
    print(f"{'spaces':>7} {'windows':>8} {'answered':>9} {'rate':>8} "
          f"{'cols>=2 agree':>14} {'cols>=3':>8}")
    table = {}
    for spaces in spaces_list:
        n = sum(c[spaces] for c in per_page.values())
        answered = [r for r in rows
                    if r["spaces"] == spaces and r["score"] >= floor]
        cols: dict = defaultdict(lambda: defaultdict(set))
        for r in answered:
            cols[(r["page"], r["system"], r["cell"])][r["raw"]].add(r["staff"])
        agree2 = sum(1 for c in cols.values()
                     for sts in c.values() if len(sts) >= 2)
        agree3 = sum(1 for c in cols.values()
                     for sts in c.values() if len(sts) >= 3)
        table[spaces] = {"windows": n, "answered": len(answered),
                         "columns_2_agreeing": agree2,
                         "columns_3_agreeing": agree3}
        rate = len(answered) / n if n else 0.0
        print(f"{spaces:>7} {n:>8} {len(answered):>9} {rate:>8.4f} "
              f"{agree2:>14} {agree3:>8}")

    narrow = min(spaces_list)
    scored = sorted((r["score"] for r in rows if r["spaces"] == narrow),
                    reverse=True)
    if scored:
        print(f"\nempty-window score distribution at {narrow} spaces "
              f"(n={len(scored)}): max {scored[0]:.4f} "
              f"p99 {scored[int(0.01 * len(scored))]:.4f} "
              f"median {statistics.median(scored):.4f}")
    print("\ntop empty-window answers:")
    for r in sorted((r for r in rows if r["spaces"] == narrow),
                    key=lambda r: -r["score"])[:10]:
        print(f"   {r['score']:.4f} {r['raw']:>4}  "
              f"{r['page']} sys{r['system']} st{r['staff']} cell{r['cell']}")

    pos_scores = sorted(positive["scores"])
    print(f"\nPOSITIVE CONTROL (a real Bravura 3/4 stamped into the SAME "
          f"windows): tried {positive['tried']}, answered "
          f"{positive['answered']}, right meter {positive['right_meter']}"
          + (f", scores {pos_scores[0]:.3f}..{pos_scores[-1]:.3f}"
             if pos_scores else ""))

    result = {"floor": floor, "table": table, "per_page": per_page,
              "positive_control": positive, "answers": rows}
    if out_json:
        pathlib.Path(out_json).write_text(json.dumps(result, indent=1))
        print(f"wrote {out_json}")
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spaces", type=float, nargs="+", default=[4.0, 6.0, 8.0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)
    result = run(args.spaces, args.json)
    if args.check:
        total = sum(sum(c.values()) for c in result["per_page"].values())
        if total == 0:
            print("\nDEAD: no window was assessed.", file=sys.stderr)
            return 2
        pc = result["positive_control"]
        if pc["tried"] == 0 or pc["answered"] == 0:
            print("\nDEAD: the positive control did not answer — a zero from "
                  "this probe would say nothing.", file=sys.stderr)
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
