#!/usr/bin/env python3
"""Agent I, round 2 — is the `_ledger_ladder` "inside the staff" collapse REACHABLE?

THE FINDING UNDER TEST (round 1, §7 item 1). `_ledger_ladder` returns
`(complete, rungs)` and returns `(0, 0)` for TWO opposite situations:

    * the glyph is INSIDE the staff's five lines — it needs no ladder, the
      strongest ownership evidence there is;
    * the glyph is OUTSIDE and its ladder is BROKEN — the weakest.

`_dedupe_cross_staff_detections` compares only `ladder[0]`
(`transcribe.py:2737`), so a glyph sitting inside staff i's own five lines
LOSES to a staff j that happens to hold a complete rung ladder out to it.

⚠️ The committed `OMR_CONTEST_DUMP` files cannot answer this: `dump_contests.py`
records per-staff `clef`/`instrument` and per-pair classes and confidences, and
**no geometry at all** — no bbox on a contest, no band on a staff. So this probe
asks the question the other way, off committed TRANSCRIPTIONS, which do carry
`staff_geometry.line_ys_page` and `bbox_page` on every detection:

    for every notehead that sits INSIDE its own staff's five-line band,
    does any OTHER staff on the page hold a COMPLETE ledger ladder out to it?

A hit is a live inversion. Zero hits over a page is evidence the inversion is
unreachable THERE, not that it is unreachable.

⚠️ LIMIT, stated because it bounds the conclusion: a committed transcription is
POST-dedupe, so the losing copy of every contested pair is already gone. This
measures the ingredient and the geometry, not the historical firings.

It also reports the ingredient the inversion needs — `ledgerLine` detections
that sit INSIDE some staff's five-line band, which a ledger line by definition
never does, and which `_ledger_rows` (`transcribe.py:2510`) admits with no
filter of any kind.

    python3 benchmarks/omr-pipeline-audit-2026-09/probe/probe_ladder_inversion.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.omr.transcribe import _ledger_ladder, _ledger_rows  # noqa: E402

FILES = {
    "beet5-p02 (Litolff, hollow-graft-shift09)":
        "benchmarks/omr-reference-selection-2026-09/out/beet5-p02-on.json",
    "brahms1   (Breitkopf, imgsz2048-ft-30ep)":
        "benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json",
}


def bands_of(page):
    out = {}
    for sy in page.get("systems", []):
        for st in sy.get("staves", []):
            g = st.get("staff_geometry") or {}
            ys = g.get("line_ys_page") or []
            sp = g.get("line_spacing_px")
            if len(ys) >= 2 and sp:
                out[st.get("staff_index")] = (float(ys[0]), float(ys[-1]), float(sp))
    return out


def noteheads_of(page):
    for sy in page.get("systems", []):
        for st in sy.get("staves", []):
            for m in st.get("measures", []):
                for d in m.get("detections", []):
                    if d.get("category") == "notehead" and d.get("bbox_page"):
                        yield st.get("staff_index"), d


def main() -> int:
    for lab, rel in FILES.items():
        doc = json.load(open(ROOT / rel))
        tot_nh = inside_own = inversions = 0
        rungs_total = rungs_inside_a_band = 0
        examples = []
        for page in doc.get("pages", []):
            bands = bands_of(page)
            if not bands:
                continue
            ledgers = _ledger_rows(page)
            rungs_total += len(ledgers)
            for lx0, lx1, ly in ledgers:
                if any(t < ly < b for (t, b, _s) in bands.values()):
                    rungs_inside_a_band += 1
            for own, d in noteheads_of(page):
                tot_nh += 1
                if own not in bands:
                    continue
                box = d["bbox_page"]
                yc = box[1] + box[3] / 2.0
                t, b, _sp = bands[own]
                if not (t <= yc <= b):
                    continue          # not inside its own staff
                inside_own += 1
                # the collapse: its own ladder reads (0, 0)
                assert _ledger_ladder(box, bands[own], ledgers)[0] == 0
                for other, band_o in bands.items():
                    if other == own:
                        continue
                    if _ledger_ladder(box, band_o, ledgers)[0] == 1:
                        inversions += 1
                        if len(examples) < 5:
                            examples.append(
                                (page.get("page_index"), own, other,
                                 d.get("class"), round(yc, 1)))
                        break
        print(f"\n=== {lab}")
        print(f"  noteheads                                  {tot_nh}")
        print(f"  ... sitting INSIDE their own five lines    {inside_own}")
        print(f"  ... of those, some OTHER staff holds a")
        print(f"      COMPLETE ladder out to them (INVERSION) {inversions}")
        for e in examples:
            print(f"        page {e[0]} staff {e[1]} -> staff {e[2]}  {e[3]} y={e[4]}")
        print(f"  ledgerLine detections                      {rungs_total}")
        print(f"  ... sitting INSIDE some staff's own band"
              f" (impossible for a real ledger line)          {rungs_inside_a_band}"
              f"  = {rungs_inside_a_band/max(1,rungs_total):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
