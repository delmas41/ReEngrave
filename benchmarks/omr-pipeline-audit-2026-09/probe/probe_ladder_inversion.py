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

# ── OMR_AUDIT_GUARD ─────────────────────────────────────────────────────────
# ⚠️ A probe that prints a clean all-zero table when it means "I looked in the
# wrong place" is this audit's own recurring failure — it produced the round-2
# N4 retraction. Inputs are resolved from THIS FILE's location (never the CWD),
# `OMR_FIXTURE_ROOT` names the checkout for anything gitignored, and a missing
# or empty input set is a NON-ZERO EXIT, never a result.
import os as _os

FIXTURE_ROOT = Path(_os.environ.get(
    "OMR_FIXTURE_ROOT", "/Users/seanjohnson/Desktop/ReEngrave"))


def _require(paths, what):
    """Abort with exit 2 unless every named input exists and the set is non-empty."""
    missing = [str(p) for p in paths if not Path(p).exists()]
    if not paths or missing:
        print(f"FATAL: {len(missing) or 'all'} {what} missing "
              f"(set OMR_FIXTURE_ROOT if these are gitignored inputs)",
              file=sys.stderr)
        for m in missing[:5]:
            print(f"  {m}", file=sys.stderr)
        raise SystemExit(2)
    return list(paths)
# ────────────────────────────────────────────────────────────────────────────
sys.path.insert(0, str(ROOT))
from tools.omr.transcribe import (  # noqa: E402
    _ledger_ladder, _ledger_rows,
    _LEDGER_RUNG_EXPECTED_SLACK as _SLACK,
    _LEDGER_RUNG_Y_TOL_SPACES as _YTOL,
    _LEDGER_RUNG_MIN_X_OVERLAP as _XOV,
)

FILES = {
    "beet5-p02 (Litolff, hollow-graft-shift09)":
        "benchmarks/omr-reference-selection-2026-09/out/beet5-p02-on.json",
    "brahms1   (Breitkopf, imgsz2048-ft-30ep)":
        "benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json",
}


def matched_rungs(box, band, ledgers):
    """Mirror of `_ledger_ladder`, returning WHICH rungs matched.

    Q3 and Q4 below need the identity of the load-bearing rungs, which
    `_ledger_ladder` does not return. Constants are IMPORTED from the module
    rather than restated, so this cannot drift from the rule it mirrors.
    """
    top, bottom, spacing = band[0], band[1], band[2]
    if spacing <= 0:
        return 0, []
    x0, y0, w, h = box
    yc = y0 + h / 2.0
    if yc < top:
        anchor, sign = top, -1.0
    elif yc > bottom:
        anchor, sign = bottom, 1.0
    else:
        return 0, []
    n_exp = int(abs(yc - anchor) / spacing + _SLACK)
    if n_exp <= 0:
        return 0, []
    tol, min_ov = _YTOL * spacing, _XOV * max(1.0, w)
    hits = []
    for k in range(1, n_exp + 1):
        ry = anchor + sign * k * spacing
        for lx0, lx1, ly, lc in ledgers:
            if abs(ly - ry) > tol:
                continue
            if min(lx1, x0 + w) - max(lx0, x0) < min_ov:
                continue
            hits.append((ly, lc))
            break
    return n_exp, hits


def rungs_with_conf(page, floor=0.0):
    """`_ledger_rows` plus the confidence it drops, and an optional floor."""
    out = []
    for sy in page.get("systems", []):
        for stf in sy.get("staves", []):
            for m in stf.get("measures", []):
                for d in m.get("detections", []):
                    if d.get("class") != "ledgerLine":
                        continue
                    c = d.get("confidence", 1.0)
                    if c < floor:
                        continue
                    b = d.get("bbox_page")
                    if not b or len(b) != 4:
                        continue
                    out.append((b[0], b[0] + b[2], b[1] + b[3] / 2.0, c))
    return out


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
    _require([ROOT / r for r in FILES.values()], "transcriptions")
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

        # ── Q3: do the trusted tier's OWN verdicts rest on impossible rungs?
        # ── Q4: how many survive a confidence floor on the rungs? (the reach
        #        probe that decides whether a floor cleans the tier or silences
        #        it) — and the confidence of the MATCHED rungs, which is the
        #        direct form of the "different populations" argument.
        import statistics as _st
        outside = complete = with_impossible = 0
        matched_conf, impossible_conf = [], []
        for page in doc.get("pages", []):
            bands = bands_of(page)
            if not bands:
                continue
            led = rungs_with_conf(page)
            def _inband(y):
                return any(t < y < b for (t, b, _s) in bands.values())
            for _lx0, _lx1, ly, lc in led:
                if _inband(ly):
                    impossible_conf.append(lc)
            for own, d in noteheads_of(page):
                if own not in bands:
                    continue
                box = d["bbox_page"]
                yc = box[1] + box[3] / 2.0
                t, b, _sp = bands[own]
                if t <= yc <= b:
                    continue
                outside += 1
                if _ledger_ladder(box, bands[own],
                                  [(a, c, e) for a, c, e, _f in led])[0] != 1:
                    continue
                complete += 1
                _n, hits = matched_rungs(box, bands[own], led)
                matched_conf += [c for _y, c in hits]
                if any(_inband(y) for y, _c in hits):
                    with_impossible += 1
        print(f"  [Q3] noteheads outside their band {outside};"
              f" COMPLETE ladders {complete};"
              f" using >=1 impossible rung {with_impossible}")
        def _line(lab, v):
            if not v:
                return
            print(f"       {lab:34s} n={len(v):4d} median {_st.median(v):.3f}"
                  f"  <0.40 {sum(1 for c in v if c < 0.40)/len(v):.3f}")
        _line("all ledgerLine", [c for pg in doc.get("pages", [])
                                 for _a, _b, _y, c in rungs_with_conf(pg)])
        _line("rungs INSIDE a band (impossible)", impossible_conf)
        _line("rungs MATCHED by a complete ladder", matched_conf)
        print(f"  [Q4] complete ladders surviving a rung-confidence floor:")
        base = None
        for floor in (0.0, 0.30, 0.35, 0.40, 0.45, 0.50):
            n_rung = n_comp = 0
            for page in doc.get("pages", []):
                bands = bands_of(page)
                if not bands:
                    continue
                led = [(a, c, e) for a, c, e, _f in rungs_with_conf(page, floor)]
                n_rung += len(led)
                for own, d in noteheads_of(page):
                    if own not in bands:
                        continue
                    box = d["bbox_page"]
                    yc = box[1] + box[3] / 2.0
                    t, b, _sp = bands[own]
                    if t <= yc <= b:
                        continue
                    if _ledger_ladder(box, bands[own], led)[0] == 1:
                        n_comp += 1
            base = base if base is not None else n_comp
            print(f"       floor {floor:.2f}  rungs {n_rung:5d}"
                  f"  complete ladders {n_comp:4d}"
                  f"  share {n_comp/max(1,base):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
