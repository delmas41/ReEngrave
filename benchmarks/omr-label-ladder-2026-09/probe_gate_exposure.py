"""Can the 20-row scan gate price `OMR_LABEL_MERGE_QUALITY` at all?

The flag only ever acts where the PDF TEXT LAYER produced labels -- with no
text layer `_well_covered([])` is already False, the free rungs already run, and
the merge key has nothing to rank. The scan gate is mostly text-layer-free, so a
flat gate result would be coverage of nothing rather than reassurance.

That is a claim about coverage and it can be MEASURED. This renders each row's
page, reads its margins through the real ladder both ways, and reports which
rows can move -- ~15 s a row against ~2 minutes to transcribe one.

    python3 -m benchmarks.omr-label-ladder-2026-09.probe_gate_exposure
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
REPO = Path(__file__).resolve().parents[2]
WORKS = REPO / "benchmarks/omr-scan-e2e-2026-09/works.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args()

    from tools.omr import contextual
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr.staff_labels import read_staff_labels

    class _NoAssist:
        mode = "none"

    doc = json.loads(WORKS.read_text())
    dpi = doc["protocol"].get("dpi", 600)
    rows = doc["rows"]
    print(f"{len(rows)} scan-gate rows, dpi {dpi} (the protocol's own)")

    results, exposed = [], []
    for r in rows:
        pdf = LIB / r["edition"]["catalog_path"]
        pi = r["page"]["pdf_page_index"]
        pws = detect_staves(render_page(pdf, pi, dpi=dpi))
        text = read_staff_labels(pws)

        arms = {}
        for flag in ("0", "1"):
            os.environ["OMR_LABEL_MERGE_QUALITY"] = flag
            labs = contextual._labels_for_page(
                pws, pdf, pi, assist=_NoAssist(), budget=[0])
            arms[flag] = {str(l.staff_index): [
                l.text, l.instrument.name if l.instrument else None,
                l.confidence] for l in labs}
        os.environ.pop("OMR_LABEL_MERGE_QUALITY", None)

        off, on = arms["0"], arms["1"]
        changed = sorted((set(off) | set(on)) - {k for k in set(off) & set(on)
                                                 if off[k] == on[k]}, key=int)
        row = {"row_id": r["row_id"], "n_staves": len(pws.staves),
               "text_layer_labels": len(text), "off": off, "on": on,
               "staves_changed": changed}
        results.append(row)
        if changed:
            exposed.append(r["row_id"])
        print(f"  {r['row_id']:38s} staves={len(pws.staves):>3} "
              f"text-layer labels={len(text):>3}  changed={len(changed):>3}  "
              f"{'*** EXPOSED ***' if changed else 'blind'}")

    print()
    print(f"rows this flag can move: {len(exposed)}/{len(rows)}"
          + (f"  {exposed}" if exposed else
             "  — the gate is blind to this flag by construction, and a flat "
             "result there is coverage of nothing"))
    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
