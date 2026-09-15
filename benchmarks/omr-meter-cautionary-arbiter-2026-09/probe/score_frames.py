#!/usr/bin/env python3
"""THE NUMBER THIS JOB TURNS ON: is the template reader's own `score` a
currency two meter readings can be compared in?

The brief substitutes the reader's correlation score for the measure math as
the arbiter of Sean's decision table, because the bars are SILENT on exactly
the case that needs them (`caut_bars_fit=0 / caut_bars_contradict=1` on the one
DISAGREE pair, and `0 / 0` on the OPENING-UNKNOWN one). The substitution is
worth testing precisely because a shape match fails for different reasons than
arithmetic built from the same damaged ink.

⚠️ IT IS ONLY A CURRENCY IF BOTH SIDES ARE PRICED THE SAME WAY, and they are
not. `locate_time_signature` is `cv2.matchTemplate(strip, template,
TM_CCOEFF_NORMED)` followed by `minMaxLoc` — **a MAXIMUM over every x position
in the strip**, with no normalisation for how many positions there were. So the
score is monotone non-decreasing in window width BY CONSTRUCTION, and the two
sides of the proposed contest are read in windows of different width:

    the OPENING    `gather_meter`         -> `header_cells_for_page`  16.0 spaces
    the CAUTIONARY `gather_meter_at_bars` -> `_bar_head_window`        4.0 spaces

This probe measures four FALSE populations on the same ten real scanned pages,
so the four are comparable to each other:

    header      the 16-space header window        <- where the opening is read TODAY
    head0       cell 0 sliced to 4 spaces         <- a SAME-FRAME opening, if anyone built one
    head_last   the LAST cell, 4 spaces           <- where a CAUTIONARY lives
    head_mid    cells 1..N-1, 4 spaces            <- the base branch's measured population

⚠️ EVERY WINDOW IS EMPTY, so every answer is a false positive and no answer is
a miss — the same one-sidedness the base branch's empty-window study has, for
the same reason (no weights and no `library/` in a cloud container, and these
ten pages are committed rasters of movements already under way).

⚠️ THE PREMISE IS CHECKED, NOT ASSERTED. A page that STARTS a movement prints a
meter in every header, and would silently turn this into a measurement of true
positives. `--check` fails if any page's header population looks like a real
unanimous meter (>= MOVEMENT_START_STAVES staves of one system agreeing on one
`raw` at or above the floor).

    python3 .../probe/score_frames.py                # the table
    python3 .../probe/score_frames.py --check        # non-zero if DEAD or if a
                                                    #   page prints a meter
    python3 .../probe/score_frames.py --pages 2      # a fast smoke run

`--check` fails when the probe assessed nothing, when the POSITIVE CONTROL does
not answer, or when the all-false premise is violated — never on a threshold.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import statistics
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import cv2                                                     # noqa: E402
import numpy as np                                             # noqa: E402

from tools.omr.header_ink import staff_metrics                 # noqa: E402
from tools.omr.measure_extractor import (detect_barlines,      # noqa: E402
                                         extract_measures)
from tools.omr.staff_detector import detect_staves             # noqa: E402
from tools.omr.staff_header import header_cells_for_page       # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines    # noqa: E402
from tools.omr.time_signature_locator import (                 # noqa: E402
    DEFAULT_LOCATOR_CONFIG, _meter_templates, locate_time_signature)
from tools.omr.types import PageImage                          # noqa: E402

#: ⚠️ IMPORTED, NEVER RESTATED. The window this probe slices must be the window
#: the gatherer slices, or the measurement is of a different reader.
from tools.omr.staged.gather import (                          # noqa: E402
    METER_TEMPLATE_AT_BAR_WINDOW_SPACES, _bar_head_window)

#: The same ten committed rasters the base branch's empty-window study used —
#: two publishers, every one a CONTINUATION page.
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

#: How many staves of one system must agree on one meter, at or above the
#: floor, before this probe declares its own premise broken.
MOVEMENT_START_STAVES = 3

#: Stamp the positive control into every Nth window of each population.
POSITIVE_CONTROL_EVERY = 7


def _page(path: pathlib.Path) -> PageImage:
    grey = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if grey is None:
        raise SystemExit(f"cannot read {path}")
    binary = cv2.adaptiveThreshold(grey, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 10)
    return PageImage(pdf_path=path, page_index=0, dpi=300,
                     rgb=cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR), binary=binary)


def _read(cell):
    """Best score and spelling, WITH THE FLOOR AT ZERO so a near miss is
    visible. Production must not do this; a distribution needs its left tail."""
    trace = {}
    try:
        locate_time_signature(cell, min_score=0.0, trace=trace)
    except Exception:                                          # noqa: BLE001
        return None
    ranked = trace.get("scores") or []
    if not ranked:
        return None
    return float(ranked[0]["score"]), str(ranked[0]["raw"])


def _stamp(cell):
    """A real Bravura `3/4` painted into this crop at the staff's own scale —
    the POSITIVE CONTROL, without which a population of zeros cannot be told
    from a dead reader. ⚠️ DELIBERATELY OPTIMISTIC: clean template ink on a real
    scanned surround, so its scores are an UPPER bound on a true reading and
    must never be quoted as a true-positive distribution."""
    metrics = staff_metrics(cell)
    if metrics is None:
        return None
    spacing, top_y, _bottom = metrics
    template = None
    for (_num, _den, raw), tmpl in _meter_templates(
            DEFAULT_LOCATOR_CONFIG.template_em_px,
            tuple(DEFAULT_LOCATOR_CONFIG.meters)):
        if raw == "3/4":
            template = tmpl
            break
    if template is None:
        return None
    scale = spacing / (DEFAULT_LOCATOR_CONFIG.template_em_px / 4.0)
    glyph = cv2.resize(template, None, fx=scale, fy=scale,
                       interpolation=cv2.INTER_AREA)
    h, w = glyph.shape[:2]
    image = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    if image is None or h >= image.shape[0] or w >= image.shape[1]:
        return None
    y0 = int(round(top_y))
    if y0 + h > image.shape[0]:
        y0 = max(0, image.shape[0] - h)
    def _paint(arr):
        if arr is None:
            return None
        out = arr.copy()
        block = out[y0:y0 + h, 0:w]
        ink = 255 - glyph
        if block.ndim == 3:
            ink = np.repeat(ink[:, :, None], block.shape[2], axis=2)
        out[y0:y0 + h, 0:w] = np.minimum(block, ink)
        return out

    return dataclasses.replace(cell, image=_paint(cell.image),
                               image_no_staff=_paint(cell.image_no_staff))


def run(pages, spaces):
    rows = []
    control = {"tried": 0, "answered": 0, "right": 0, "scores": []}
    for name, rel in pages:
        path = ROOT / rel
        pws = detect_barlines(detect_staves(_page(path)))
        cells = extract_measures(pws)
        remove_staff_lines(cells)
        headers = header_cells_for_page(pws)
        sysof = {s.staff_index: s.system_index for s in pws.staves}

        by_staff = defaultdict(list)
        for c in cells:
            by_staff[c.staff_index].append(c)

        todo = []
        for staff_index, crop in sorted(headers.items()):
            todo.append(("header", staff_index, crop))
        for staff_index, cs in sorted(by_staff.items()):
            cs = sorted(cs, key=lambda c: c.measure_index)
            if not cs:
                continue
            last = cs[-1].measure_index
            for c in cs:
                window = _bar_head_window(c, spaces)
                if window is None:
                    continue
                if c.measure_index == 0:
                    pop = "head0"
                elif c.measure_index == last:
                    pop = "head_last"
                else:
                    pop = "head_mid"
                todo.append((pop, staff_index, window))

        for i, (pop, staff_index, crop) in enumerate(todo):
            got = _read(crop)
            if got is None:
                continue
            score, raw = got
            rows.append({"page": name, "population": pop,
                         "system": sysof.get(staff_index, -1),
                         "staff": staff_index,
                         "cell": int(getattr(crop, "measure_index", -1)),
                         "score": round(score, 4), "raw": raw})
            if i % POSITIVE_CONTROL_EVERY == 0:
                stamped = _stamp(crop)
                if stamped is None:
                    continue
                control["tried"] += 1
                pos = _read(stamped)
                if pos is None:
                    continue
                if pos[0] >= DEFAULT_LOCATOR_CONFIG.min_score:
                    control["answered"] += 1
                    control["scores"].append(round(pos[0], 4))
                    if pos[1] == "3/4":
                        control["right"] += 1
    return rows, control


def summarise(rows, floor):
    out = {}
    for pop in ("header", "head0", "head_last", "head_mid"):
        sel = [r for r in rows if r["population"] == pop]
        if not sel:
            out[pop] = {"windows": 0}
            continue
        scores = sorted(r["score"] for r in sel)
        over = [r for r in sel if r["score"] >= floor]
        out[pop] = {
            "windows": len(sel),
            "answered": len(over),
            "rate": round(len(over) / len(sel), 4),
            "median": round(statistics.median(scores), 4),
            "p90": round(scores[int(0.90 * (len(scores) - 1))], 4),
            "p99": round(scores[int(0.99 * (len(scores) - 1))], 4),
            "max": round(scores[-1], 4),
            "top_spellings": Counter(r["raw"] for r in over).most_common(4),
        }
    return out


def movement_starts(rows, floor):
    """Systems whose HEADER population produces a VOTED meter — the probe's own
    premise check, and the reason it uses the SHIPPED vote rather than a
    threshold of its own: the question is not *"do some staves agree"* but
    *"would this pipeline declare a meter here"*, and only
    `vote_system_time_signature` answers that. Empty when the premise holds."""
    from tools.omr.time_signature_locator import (LocatedTimeSignature,
                                                  vote_system_time_signature)
    bad = []
    per = defaultdict(list)
    for r in rows:
        if r["population"] == "header":
            per[(r["page"], r["system"])].append(r)
    for key, group in sorted(per.items()):
        reads = []
        for r in group:
            if r["score"] < floor:
                reads.append(None)
                continue
            num, _, den = r["raw"].partition("/")
            try:
                reads.append(LocatedTimeSignature(
                    numerator=int(num or 4), denominator=int(den or 4),
                    score=r["score"], x_canonical=0, raw=r["raw"]))
            except ValueError:            # "C" / "C|": a letter, not digits
                reads.append(LocatedTimeSignature(
                    numerator=4, denominator=4, score=r["score"],
                    x_canonical=0, raw=r["raw"]))
        voted = vote_system_time_signature(reads, n_staves=len(reads))
        if voted:
            bad.append({"page": key[0], "system": key[1], "voted": voted,
                        "n_staves": len(reads)})
    return bad


def loose_consensus(rows, floor, n_needed=MOVEMENT_START_STAVES):
    """How often `n_needed` staves of ONE system agree on ONE false meter, per
    population. NOT the premise check — this is the base branch's own
    *"columns_3_agreeing"* question asked of every frame, and it is the number
    that says whether a cross-staff quorum is safe in that frame."""
    out = {}
    for pop in ("header", "head0", "head_last", "head_mid"):
        per = defaultdict(Counter)
        groups = set()
        for r in rows:
            if r["population"] != pop:
                continue
            key = (r["page"], r["system"], r["cell"])
            groups.add(key)
            if r["score"] >= floor:
                per[key][r["raw"]] += 1
        hits = [{"page": k[0], "system": k[1], "cell": k[2],
                 "raw": c.most_common(1)[0][0], "staves": c.most_common(1)[0][1]}
                for k, c in sorted(per.items())
                if c.most_common(1)[0][1] >= n_needed]
        out[pop] = {"columns": len(groups), "columns_n_agreeing": len(hits),
                    "hits": hits}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--pages", type=int, default=0,
                    help="use only the first N pages (a smoke run)")
    ap.add_argument("--only", nargs="*", default=None,
                    help="run only these page names (a fast, targeted arm)")
    ap.add_argument("--spaces", type=float,
                    default=METER_TEMPLATE_AT_BAR_WINDOW_SPACES)
    ap.add_argument("--out", default=str(
        ROOT / "benchmarks/omr-meter-cautionary-arbiter-2026-09"
               "/out/score-frames.json"))
    args = ap.parse_args()

    if args.only:
        pages = [p for p in PAGES if p[0] in set(args.only)]
        if not pages:
            print(f"DEAD: --only named no known page; known: "
                  f"{[p[0] for p in PAGES]}")
            return 2
    else:
        pages = PAGES[:args.pages] if args.pages else PAGES
    floor = DEFAULT_LOCATOR_CONFIG.min_score
    rows, control = run(pages, args.spaces)

    # ⚠️ REACH FIRST, BEFORE ANY RESULT.
    print(f"REACH  pages={len(pages)}  windows={len(rows)}  "
          f"bar-head width={args.spaces} spaces  floor={floor}")
    table = summarise(rows, floor)
    for pop, s in table.items():
        if not s.get("windows"):
            print(f"  {pop:<10} DEAD (no windows)")
            continue
        print(f"  {pop:<10} n={s['windows']:>5}  >=floor {s['answered']:>3} "
              f"({s['rate']:.2%})  median {s['median']:.4f}  p90 {s['p90']:.4f}"
              f"  p99 {s['p99']:.4f}  max {s['max']:.4f}   {s['top_spellings']}")
    print(f"POSITIVE CONTROL  tried={control['tried']} answered="
          f"{control['answered']} right={control['right']}"
          + (f"  min={min(control['scores']):.4f}" if control["scores"] else ""))

    loose = loose_consensus(rows, floor)
    print(f"FALSE CONSENSUS ({MOVEMENT_START_STAVES}+ staves of one system "
          f"agreeing on one meter at one column):")
    for pop, s in loose.items():
        print(f"  {pop:<10} {s['columns_n_agreeing']:>3} of {s['columns']:>5} "
              f"columns" + (f"   {s['hits'][:4]}" if s["hits"] else ""))

    bad = movement_starts(rows, floor)
    print("PREMISE CHECK (would the SHIPPED vote declare a meter here?): "
          + ("OK — no system votes one" if not bad else str(bad)))

    payload = {"floor": floor, "spaces": args.spaces, "table": table,
               "positive_control": control, "premise_violations": bad,
               "false_consensus": loose, "rows": rows}
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=1))
    print(f"wrote {args.out}")

    if args.check:
        if not rows:
            print("DEAD: assessed nothing")
            return 2
        if control["answered"] == 0:
            print("DEAD: the positive control never answered")
            return 2
        if bad:
            print("PREMISE BROKEN: a page prints a meter")
            return 2
        print("CHECK OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
