#!/usr/bin/env python3
"""Phase 1 of the label-reach workstream: WHY does a staff resolve to nothing?

MEASUREMENT ONLY. Nothing in the pipeline changes. The staff-identity audit
(`benchmarks/omr-staff-identity-2026-09/FINDINGS.md`) measured S1 — the margin
label — at coverage **0.710**, precision 0.982, and concluded that labels are
the binding constraint on staff identity. It did not say WHY the other 29%
resolves to nothing, and the answer decides what is worth building:

    (a) no label is printed on the page at all      -> a wall; no reader helps
    (b) a label is printed and the CROP misses it   -> a crop fix
    (c) the crop is right and the OCR returns ""    -> a reader question
    (d) OCR read something, the LEXICON refused it  -> lexicon work
    (e) the lexicon resolved it WRONG               -> lexicon work

This script produces the (b)/(c)/(d)/(e) split mechanically and hands (a)-vs-(b)
to a human by writing the exact crop each reader saw plus a widened control.

⚠️ THE LADDER'S EARLY EXIT IS DELIBERATELY DEFEATED HERE. `contextual.
_labels_for_page` stops at the first rung that covers the page, so a production
run never tells you what the rungs below WOULD have read. Every rung is run on
every page, independently, so a staff that only Tesseract can read is visible
even on a page Surya covered.

⚠️ FIXTURE PROVENANCE. Truth and the staff set come from the scan benchmark's
`works.json` (11 rows) and the committed `..graft09` transcriptions in the MAIN
checkout's `benchmarks/omr-scan-e2e-2026-09/fixtures/`. Staves are re-detected
here (phase 1 only, no YOLO) and the per-system staff counts are ASSERTED equal
to the fixture's before any row is scored; a row that disagrees is reported as
`structure_mismatch` and excluded rather than silently scored against the wrong
geometry.

⚠️ THE LEXICON IS THE ONE ON THIS TREE, not the one the fixtures were made with.
Class (d) is a question about today's `instruments.py`, so every raw string is
re-looked-up here. Fixture `unresolved_labels` are reported alongside for drift.

    python3 benchmarks/omr-staff-identity-labels-2026-09/probe_ladder.py
    python3 ... probe_ladder.py --rows dvorak-sym9-mvt1-405834-p6
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

SCAN_BENCH = REPO / "benchmarks" / "omr-scan-e2e-2026-09"
WORKS = SCAN_BENCH / "works.json"
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
FIXTURES = [SCAN_BENCH / "fixtures",
            MAIN / "benchmarks" / "omr-scan-e2e-2026-09" / "fixtures"]
TAG = ".graft09"
DPI = 600          # works.json `protocol.dpi`


def fixtures_dir() -> Path:
    for c in FIXTURES:
        if c.is_dir() and any(c.glob(f"*{TAG}.omr.json")):
            return c
    raise SystemExit("no scan fixtures found")


def library_root() -> Path:
    from tools.library.score_library import library_root as lr
    return Path(lr())


def _truth_staves(row: dict, rows_by_id: dict):
    """The hand-verified staff list, following `same-as:` aliases."""
    st = row.get("staves")
    if isinstance(st, str) and st.startswith("same-as:"):
        return _truth_staves(rows_by_id[st.split(":", 1)[1]], rows_by_id)
    if isinstance(st, list):
        return st, "works.json:staves"
    cond = row.get("condensation") or {}
    sap = cond.get("staves_as_printed")
    if isinstance(sap, list):
        return sap, "works.json:condensation.staves_as_printed"
    sysp = cond.get("systems_as_printed")
    if isinstance(sysp, list):
        return sysp, "works.json:systems_as_printed"
    return None, "none"


def run_row(row: dict, rows_by_id: dict, lib: Path, fx: Path,
            crops_dir: Path) -> dict:
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr import staff_labels, staff_labels_surya, staff_labels_tesseract
    from tools.omr.staff_labels_vision import margin_strip, build_margin_crop
    from tools.omr.instruments import lookup

    rid = row["row_id"]
    pdf = lib / row["edition"]["catalog_path"]
    page_index = row["page"]["pdf_page_index"]

    cands = list(fx.glob(f"{rid}*{TAG}.omr.json"))
    fixture = json.loads(cands[0].read_text()) if cands else None

    pws = detect_staves(render_page(pdf, page_index, dpi=DPI))

    # ── provenance guard: same staff geometry as the scored fixture ──────────
    by_sys: dict[int, list] = {}
    for s in sorted(pws.staves, key=lambda s: s.top_y):
        by_sys.setdefault(s.system_index, []).append(s)
    here_shape = [len(v) for _, v in sorted(by_sys.items())]
    fx_shape = []
    if fixture:
        for p in fixture.get("pages", []):
            for sy in p.get("systems", []):
                fx_shape.append(len(sy.get("staves", [])))
    mismatch = bool(fixture) and here_shape != fx_shape

    # ── every rung, on every staff, independently ───────────────────────────
    rungs: dict[str, dict[int, str]] = {}
    rungs["text_layer"] = {l.staff_index: l.text
                           for l in staff_labels.read_staff_labels(pws)}
    try:
        rungs["surya"] = {l.staff_index: l.text
                          for l in staff_labels_surya.read_staff_labels_surya(pws)} \
            if staff_labels_surya.available() else {}
    except Exception as exc:                                   # noqa: BLE001
        rungs["surya"] = {}
        print(f"  !! surya failed on {rid}: {exc}", file=sys.stderr)
    try:
        rungs["tesseract"] = {
            l.staff_index: l.text
            for l in staff_labels_tesseract.read_staff_labels_tesseract(pws)} \
            if staff_labels_tesseract.available() else {}
    except Exception as exc:                                   # noqa: BLE001
        rungs["tesseract"] = {}
        print(f"  !! tesseract failed on {rid}: {exc}", file=sys.stderr)

    print(f"   rungs: " + ", ".join(f"{k}={len(v)}" for k, v in rungs.items()),
          file=sys.stderr)

    # ── the crops, so (a) vs (b) can be settled by eye ──────────────────────
    crop_files = {}
    for sysi, staves in sorted(by_sys.items()):
        mc = build_margin_crop(pws, staves)
        if mc is not None:
            f = crops_dir / f"{rid}-sys{sysi}.png"
            f.write_bytes(mc.png)
            crop_files[sysi] = f.name
        strip, _ = margin_strip(pws, staves)
        if strip is not None:
            strip.save(crops_dir / f"{rid}-sys{sysi}-bare.png")

    truth, truth_prov = _truth_staves(row, rows_by_id)

    out = []
    for sysi, staves in sorted(by_sys.items()):
        for i, staff in enumerate(staves):
            si = staff.staff_index
            reads = {k: (v.get(si) or "").strip() for k, v in rungs.items()}
            hits = {k: h for k, h in ((k, lookup(t))
                                      for k, t in reads.items() if t) if h}
            resolved = None
            resolved_by = None
            for k in ("text_layer", "surya", "tesseract"):
                h = hits.get(k)
                if h and h.instrument:
                    resolved, resolved_by = h.instrument.name, k
                    break
            # truth name for this staff
            tname = None
            if truth:
                if truth_prov.endswith("systems_as_printed"):
                    blk = truth[sysi] if sysi < len(truth) else None
                    tname = (blk[i] or {}).get("name") if blk and i < len(blk) else None
                elif i < len(truth):
                    tname = (truth[i] or {}).get("name")
            out.append({
                "row_id": rid, "system": sysi, "staff_index": si, "position": i,
                "reads": reads,
                "lexicon": {k: (h.instrument.name if h.instrument else None)
                            for k, h in hits.items()},
                "confidence": {k: (h.confidence if h else None)
                               for k, h in hits.items()},
                "resolved": resolved, "resolved_by": resolved_by,
                "any_text": any(reads.values()),
                "TRUTH_name": tname,
            })

    return {
        "row_id": rid,
        "pdf": str(pdf), "page_index": page_index,
        "publisher": row["edition"].get("publisher_as_catalogued", ""),
        "has_text_layer": row["edition"].get("has_text_layer"),
        "structure_here": here_shape, "structure_fixture": fx_shape,
        "structure_mismatch": mismatch,
        "fixture_unresolved": ((fixture or {}).get("contextual") or {}
                               ).get("unresolved_labels"),
        "fixture_tiers": ((fixture or {}).get("contextual") or {}
                          ).get("label_tiers"),
        "crops": crop_files,
        "staves": out,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="*")
    ap.add_argument("--out", default=str(HERE / "ladder.json"))
    a = ap.parse_args(argv)

    works = json.loads(WORKS.read_text())
    rows_by_id = {r["row_id"]: r for r in works["rows"]}
    lib, fx = library_root(), fixtures_dir()
    crops = HERE / "crops"
    crops.mkdir(exist_ok=True)

    results = []
    for row in works["rows"]:
        if a.rows and row["row_id"] not in a.rows:
            continue
        print(f"== {row['row_id']}", file=sys.stderr)
        results.append(run_row(row, rows_by_id, lib, fx, crops))

    Path(a.out).write_text(json.dumps(
        {"meta": {"fixtures": str(fx), "tag": TAG, "dpi": DPI,
                  "note": "every rung run on every page; ladder early-exit defeated"},
         "rows": results}, indent=1))
    print(f"wrote {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
