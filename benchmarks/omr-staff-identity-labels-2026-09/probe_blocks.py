#!/usr/bin/env python3
"""Where does a margin OCR block sit relative to the staff ticks?

Phase 2 (ii). Phase 1 left 12 reachable staves unresolved for one reason: a
bracketed or braced group is engraved with its instrument name ONCE, and each
member staff carries only its discriminator — `(Es)` under a shared `Hr.`,
`III` under a shared `Violino`. `_surya_worker._assign` gives every block to
the single staff whose tick it lands nearest, so the name reaches one staff and
the others get a key or a numeral the lexicon cannot read.

Before proposing a sharing rule, MEASURE where these blocks actually are.
`raw_lines` carries text and height but not the y-centre, and the y-centre is
the whole question — a name centred BETWEEN two ticks is a different fact from
one centred ON a tick, and only the first can be shared on geometry alone.

Emits, per system, every block with its y-centre expressed in TICK UNITS
(0 = first staff, 1 = second, …) so the number is comparable across pages,
DPI and system size.

    python3 benchmarks/omr-staff-identity-labels-2026-09/probe_blocks.py
    python3 ... probe_blocks.py --rows brahms-sym1-mvt1-317803-p3
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

WORKS = REPO / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"
DPI = 600


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="*")
    ap.add_argument("--out", default=str(HERE / "blocks.json"))
    a = ap.parse_args()

    from tools.library.score_library import library_root
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr.staff_labels_vision import build_margin_crop
    from tools.omr import staff_labels_surya as sls

    lib = Path(library_root())
    works = json.loads(WORKS.read_text())

    systems, meta = [], []
    for row in works["rows"]:
        rid = row["row_id"]
        if a.rows and rid not in a.rows:
            continue
        page = render_page(lib / row["edition"]["catalog_path"],
                           row["page"]["pdf_page_index"], dpi=DPI)
        pws = detect_staves(page)
        by_sys: dict[int, list] = {}
        for s in sorted(pws.staves, key=lambda s: s.top_y):
            by_sys.setdefault(s.system_index, []).append(s)
        for sysi, staves in sorted(by_sys.items()):
            crop = build_margin_crop(pws, staves)
            if crop is None:
                continue
            systems.append({
                "png_b64": base64.standard_b64encode(crop.png).decode("ascii"),
                "staff_indices": list(crop.staff_indices),
                "tick_ys": list(crop.tick_ys),
                "gutter_px": crop.gutter_px,
            })
            meta.append({"row_id": rid, "system": sysi})

    proc = subprocess.run(
        [str(sls.interpreter()), str(HERE / "_block_dump_worker.py")],
        input=json.dumps({"systems": systems}), capture_output=True, text=True,
        timeout=3600)
    if proc.returncode != 0:
        print(proc.stderr[-3000:], file=sys.stderr)
        raise SystemExit("block dump worker failed")
    got = json.loads(proc.stdout)["systems"]

    out = []
    for m, entry in zip(meta, got):
        ticks = entry["tick_ys"] or []
        span = (max(ticks) - min(ticks)) if len(ticks) > 1 else 0.0
        spacing = span / (len(ticks) - 1) if len(ticks) > 1 else float("inf")
        blocks = []
        for b in sorted(entry["blocks"], key=lambda b: b["y"]):
            # y in TICK UNITS: 0.0 = first staff's tick, 1.0 = second, and 0.5
            # is exactly midway between the two — the brace-centred position.
            u = ((b["y"] - ticks[0]) / spacing) if ticks and spacing else None
            d = [abs(b["y"] - t) / spacing for t in ticks] if ticks else []
            near = min(range(len(d)), key=d.__getitem__) if d else None
            blocks.append({
                "text": b["text"], "y": b["y"], "h": b["h"],
                "tick_units": None if u is None else round(u, 3),
                "h_in_spacings": None if spacing in (0, float("inf"))
                else round(b["h"] / spacing, 3),
                "nearest_tick": near,
                "dist_to_nearest": None if not d else round(d[near], 3),
                "dist_to_second": (None if len(d) < 2 else
                                   round(sorted(d)[1], 3)),
            })
        # ⚠️ TICK SPACING IS NOT UNIFORM on a conductor's page — an engraver
        # opens the gap between families — so a distance expressed in the MEAN
        # spacing is not comparable between a wind pair and a wind/brass
        # boundary. The ticks themselves are kept so the analysis can work in
        # the LOCAL gap, which is the only unit in which "centred between these
        # two staves" means one thing everywhere.
        out.append({**m, "n_staves": len(ticks), "tick_ys": ticks,
                    "staff_indices": entry.get("staff_indices"),
                    "spacing_px": round(spacing, 1)
                    if spacing != float("inf") else None, "blocks": blocks})

    Path(a.out).write_text(json.dumps(out, indent=1))
    for e in out:
        print(f"== {e['row_id']} sys{e['system']}  {e['n_staves']} staves")
        for b in e["blocks"]:
            print(f"   u={b['tick_units']:>7}  h={b['h_in_spacings']:>6}sp  "
                  f"near={b['nearest_tick']:>2} d1={b['dist_to_nearest']:>6} "
                  f"d2={b['dist_to_second']:>6}  {b['text']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
