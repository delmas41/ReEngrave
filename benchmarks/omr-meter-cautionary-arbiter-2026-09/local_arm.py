#!/usr/bin/env python3
"""THE ARM THAT WOULD SETTLE THIS — one gather, and both sides of the contest
priced in the SAME unit for the first time.

⚠️⚠️ THIS CANNOT RUN IN A CLOUD CONTAINER AND IS NOT MEANT TO. It needs
`omr-weights/` and a PDF from `library/`, both gitignored. Everything else in
this benchmark directory ran without weights and measures the READER; this
measures the PIPELINE on the one document the whole meter thread is blocked on.

WHAT IS MISSING TODAY, and why only a gather can supply it. The cautionary
session established that a cautionary and the opening it announces carry NO
COMMON CURRENCY: the cautionary states `support`, the opening states `share`,
and the one quantity both state — how many staves read it — prefers the WRONG
reading on the only contested pair (9 against 10). Its §2d named the one
genuinely new lever: `Q.METER_TEMPLATE.score` is on the record and read by
nothing. ⚠️ But the template reader has only ever looked at the HEADER window,
so **the cautionary had no score to be compared with** — there was no contest
to hold. The base branch (`OMR_METER_TEMPLATE_AT_BAR`) is what changes that: it
asks the same reader at every candidate mid-staff bar head, and a cautionary
stands at a system's LAST cell.

⚠️⚠️ AND THE TWO SCORES ARE STILL NOT ON ONE SCALE — WHICH IS WHY THIS ARM
PRINTS THE WINDOW WIDTH BESIDE EVERY SCORE. `locate_time_signature` is
`matchTemplate` + `minMaxLoc`: a MAXIMUM over every x position in the strip,
with no normalisation for how many positions there were. So the score is
monotone non-decreasing in window width BY CONSTRUCTION (measured on 1,612
real windows: 968 rose from 4 to 8 spaces, **0 fell**), and the opening's
window is **16.0 staff spaces** against the bar head's **4.0**. A naive
`caut_score > open_score` comparison is therefore biased toward the OPENING —
the same direction the staff count already fails in.

So this arm reports THREE readings per system, and the third is the only fair
one:

    A  the OPENING, header frame       16.0 spaces   (what ships today)
    B  the CAUTIONARY, bar-head frame   4.0 spaces   (the base branch's new rows)
    C  the OPENING at its OWN bar head  4.0 spaces   (C vs B is the fair contest)

C is computed by this arm directly — re-running the pipeline's own
`detect_staves -> detect_barlines -> extract_measures -> remove_staff_lines`
and slicing cell 0 with the gatherer's OWN `_bar_head_window` — so **no file
under `tools/` has to change to measure it**. If C ever ships it is a
one-predicate scope change in `_meter_candidate_columns`, which today skips
cell 0.

    python3 benchmarks/omr-meter-cautionary-arbiter-2026-09/local_arm.py \\
        --pdf "$HOME/Desktop/ReEngrave/library/editions/brahms/symphony-1/brahms--symphony-1--breitkopf--imslp317803.pdf" \\
        --weights "$HOME/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt" \\
        --pages 0-3 --out-dir /tmp/meter-arbiter

⚠️ BREITKOPF BRAHMS 1 p0-3 IS THE FIXTURE, for the reason CLAUDE.md gives: on
that scan `9/8` is voted `9/4`, the real change at m8 is missed, and five
spurious `4/4` changes clear the floor — and the document's own answer, a
cautionary reading `9/8` on nine staves at the end of page 0, is consumed by
nothing. Page 0 is REQUIRED: the cautionary is on it.

⚠️ WHAT TO LOOK FOR, in order:
  1. **REACH.** Systems carrying a LAST-cell template row at all. Zero means
     the arm is dead and nothing below it counts — it exits non-zero.
  2. **B on the page-0 cautionary.** Does the bar-head reader answer `9/8`
     there, and on how many staves?
  3. **C vs B.** The fair contest. Does the cautionary out-score the opening
     when both are read in a 4-space window?
  4. **A vs C on the same opening.** The width effect on a real opening,
     measured rather than argued.
  5. **The five spurious `4/4`.** They must not gain staves.

⚠️ RUN THE GATHER WITHOUT `--musicxml`: CLAUDE.md records that
`staged/__main__.py` imports the EXPORTER after the gather, so an edit made
during a long run kills a finished one. This arm exports nothing.

⚠️ NOTHING HERE ADJUDICATES. It prints the two sides and the truth is a human's
to supply — this benchmark has no print and says so.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ENV_FLAG = "OMR_METER_TEMPLATE_AT_BAR"


def _gather(pdf, weights, pages, out):
    env = dict(os.environ)
    env[ENV_FLAG] = "1"
    cmd = [sys.executable, "-m", "tools.omr.staged", str(pdf),
           "--pages", pages, "--weights", str(weights), "--out", str(out)]
    print(f"\n$ {ENV_FLAG}=1 " + " ".join(cmd), flush=True)
    t0 = time.time()
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)
    return time.time() - t0


def _record(path: pathlib.Path) -> dict:
    """⚠️ REFUSES rather than defaulting to an empty record: a parser that
    returns `{}` for an unrecognised file reports *nothing moved* for a run
    that never happened."""
    doc = json.loads(path.read_text())
    rec = doc.get("record")
    if not isinstance(rec, dict) or "verdicts" not in rec:
        raise SystemExit(f"{path} is not a staged record (no record.verdicts)")
    return rec


def _rows(rec, quantity):
    return [r for r in (rec.get("observations") or [])
            if r.get("quantity") == quantity]


def _system_of(subject: str):
    """`staff/1/0/3` -> `system/1/0`."""
    parts = subject.split("/")
    if len(parts) >= 3:
        return f"system/{parts[1]}/{parts[2]}"
    return subject


def same_frame_openings(pdf, pages, spaces):
    """READING C — cell 0's own bar head, at the bar-head width.

    Re-runs only the weightless half of the pipeline, so this costs CV time and
    no inference. ⚠️ It slices with the GATHERER's `_bar_head_window`, imported,
    because a restated slice would be a different reader.
    """
    import cv2

    from tools.omr.measure_extractor import detect_barlines, extract_measures
    from tools.omr.preprocessing import render_pdf_pages
    from tools.omr.staff_detector import detect_staves
    from tools.omr.staff_line_removal import remove_staff_lines
    from tools.omr.staged.gather import _bar_head_window
    from tools.omr.time_signature_locator import locate_time_signature

    del cv2  # imported for the side effect of failing early if absent
    out = collections.defaultdict(list)
    for page in render_pdf_pages(pathlib.Path(pdf), pages=pages):
        pws = detect_barlines(detect_staves(page))
        cells = extract_measures(pws)
        remove_staff_lines(cells)
        sysof = {s.staff_index: s.system_index for s in pws.staves}
        for c in cells:
            if c.measure_index != 0:
                continue
            window = _bar_head_window(c, spaces)
            if window is None:
                continue
            trace = {}
            found = locate_time_signature(window, trace=trace)
            ranked = trace.get("scores") or []
            best = ranked[0] if ranked else None
            key = f"system/{page.page_index}/{sysof.get(c.staff_index, -1)}"
            out[key].append({
                "staff": c.staff_index,
                "score": None if best is None else best["score"],
                "raw": None if best is None else best["raw"],
                "cleared_floor": bool(found is not None),
            })
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--pages", default="0-3")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--skip-same-frame", action="store_true",
                    help="skip READING C (saves a CV pass per page)")
    ap.add_argument("--reuse", action="store_true",
                    help="reuse an existing record instead of gathering")
    args = ap.parse_args(argv)

    from tools.omr.staged.gather import METER_TEMPLATE_AT_BAR_WINDOW_SPACES
    spaces = METER_TEMPLATE_AT_BAR_WINDOW_SPACES

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    record_path = out_dir / "arbiter.json"
    if record_path.exists() and not args.reuse:
        raise SystemExit(f"{record_path} exists — refusing to overwrite. "
                         f"Pass --reuse to read it, or choose a new --out-dir.")
    if not args.reuse:
        took = _gather(args.pdf, args.weights, args.pages, record_path)
        print(f"gather took {took:.1f}s")

    rec = _record(record_path)
    header = _rows(rec, "meter_template")
    at_bar = _rows(rec, "meter_template_at_bar")
    meters = {v["subject"]: v for v in rec["verdicts"]
              if v.get("quantity") == "meter"}

    # ── REACH FIRST ──────────────────────────────────────────────────────────
    by_sys_cell = collections.defaultdict(list)
    for r in at_bar:
        by_sys_cell[(_system_of(r["subject"]),
                     (r.get("detail") or {}).get("cell"))].append(r)
    last_cell = {}
    for (sysk, cell), rows in by_sys_cell.items():
        if cell is None:
            continue
        if sysk not in last_cell or cell > last_cell[sysk]:
            last_cell[sysk] = cell
    print("\nREACH")
    print(f"  systems with a meter verdict ................. {len(meters)}")
    print(f"  header-frame template rows (READING A) ....... {len(header)}")
    print(f"  bar-head template rows (READING B) ........... {len(at_bar)}")
    print(f"  systems with ANY last-cell bar-head row ...... {len(last_cell)}")
    if not at_bar:
        print("DEAD: the bar-head reader answered nowhere. Was "
              f"{ENV_FLAG}=1 set, and does this document print any "
              "meter-shaped ink off the header?")
        return 2

    # ── READING C ────────────────────────────────────────────────────────────
    same = {}
    if not args.skip_same_frame:
        same = same_frame_openings(args.pdf, args.pages, spaces)
        print(f"  same-frame opening readings (READING C) ...... "
              f"{sum(len(v) for v in same.values())} over {len(same)} systems")

    # ── THE TABLE ────────────────────────────────────────────────────────────
    print("\nPER SYSTEM — ⚠️ THE WIDTHS DIFFER; A AND B ARE NOT COMPARABLE")
    print(f"   A = header window 16.0 spaces | "
          f"B = last-cell bar head {spaces} spaces | "
          f"C = cell-0 bar head {spaces} spaces")
    report = {}
    for sysk in sorted(meters, key=lambda s: tuple(int(x) for x in s.split("/")[1:])):
        v = meters[sysk]
        val = v.get("value") or {}
        caut = val.get("cautionary")
        a = [r for r in header if _system_of(r["subject"]) == sysk]
        lc = last_cell.get(sysk)
        b = by_sys_cell.get((sysk, lc), []) if lc is not None else []
        c = same.get(sysk, [])

        def _fmt(rows, key="score"):
            vals = sorted(x for x in ((r.get("detail") or r).get(key)
                                      for r in rows) if x is not None)
            if not vals:
                return "none"
            return (f"n={len(vals)} med={vals[len(vals)//2]:.4f} "
                    f"max={vals[-1]:.4f}")

        def _spellings(rows):
            return collections.Counter(
                (r.get("detail") or r).get("raw") for r in rows).most_common(3)

        print(f"\n  {sysk}  verdict={val.get('raw')} reason={v.get('reason')}")
        print(f"     A opening/header   {_fmt(a)}   {_spellings(a)}")
        print(f"     B last cell {str(lc):>3}    {_fmt(b)}   {_spellings(b)}")
        print(f"     C opening/bar head {_fmt(c)}   {_spellings(c)}")
        if caut:
            print(f"     ⚠️ RECORDED CAUTIONARY  raw={caut.get('raw')} "
                  f"support={caut.get('support')} "
                  f"staves={len(caut.get('staves_reading_it') or [])} "
                  f"from_cell={caut.get('from_cell')}")
        report[sysk] = {"verdict": val.get("raw"), "reason": v.get("reason"),
                        "cautionary": caut, "last_cell": lc,
                        "A": [r.get("detail") for r in a],
                        "B": [r.get("detail") for r in b], "C": c}

    payload = {"pages": args.pages, "window_spaces": spaces, "systems": report}
    (out_dir / "arbiter-table.json").write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {out_dir / 'arbiter-table.json'}")
    print("\n⚠️ NOTHING ABOVE IS ADJUDICATED. Compare B against C — never "
          "against A — and read the result against the print.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
