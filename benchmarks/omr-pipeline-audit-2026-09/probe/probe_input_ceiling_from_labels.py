"""Can the hand-labeling corpus supply the INPUT ceiling? — asked, not assumed.

The registry's one empty ceiling kind is `input`: how much of a scanned page's
ink is *genuinely* unrecoverable. Every scan detector row is currently scored
against an assumed C = 1.0, i.e. against the claim that a perfect reader could
recover every symbol from a bitonal 600 dpi scan of 1870 type.

THE PROPOSAL. A human labeler drew boxes on those exact scanned cells, looking
at the same ink the detector saw, with no reference to our output. That
satisfies the independence guard in a way a truth MusicXML cannot: **the MXL
says what the MUSIC is; a human's box says what the INK is.**

WHAT THE MEASUREMENT HAS TO BE, and it is not the obvious one. Comparing human
boxes to DETECTOR boxes measures the detector, not the ceiling — it is an
achievement number wearing a ceiling's clothes. The ceiling is the other
comparison:

    of the notes the ENCODING says are printed in this bar,
    how many could a HUMAN find on the scan?

    C_input = (reference notes a human boxed) / (reference notes in those bars)

A C of 1.0 says the ink is all there and every detector shortfall is a detector
problem. A C of 0.85 says 15% of it is gone and `scan:pitch` at 0.834 is really
0.834/0.85 of what was available.

THREE HAZARDS, all of which restrict the answer rather than invalidate it:
 (a) SELECTION — batches are chosen by density/sparseness/symbol, so these cells
     are not a random sample of a page. The answer is conditional on them.
 (b) PASS COMPLETENESS — a single-symbol pass leaves everything else unboxed by
     instruction. Only cells stamped `inspected_passes: [... "completion"]` can
     be used, because only a completion pass boxes every class.
 (c) CLASS SCOPE — a labeler skips staff lines, stems, beams and free text by
     instruction, so this can only ever be a ceiling for the classes swept.
     Noteheads are the one class both the encoding and the labeler carry.

Read-only. Writes one JSON.
"""
from __future__ import annotations

import json
from pathlib import Path

sys_path_added = True
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixtureroot import fixture_root, require_nonempty  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "input-ceiling-from-labels.json"
BENCH = ROOT / "benchmarks"

#: the only batch in the corpus with a COMPLETION pass — every class boxed.
BATCH = BENCH / "omr-labeling-hollow2-2026-09-breitkopf-brahms1"
COMPLETION_PASS = "completion"
NOTEHEAD_PREFIX = "notehead"


def main() -> int:
    verdicts = {}
    vfiles = require_nonempty(sorted((BATCH / "verdicts").glob("*.json")),
                              "verdict files", BATCH / "verdicts", "*.json")
    for f in vfiles:
        d = json.loads(f.read_text())
        if COMPLETION_PASS in (d.get("inspected_passes") or []):
            verdicts[d["cell_id"]] = d

    rows, no_prefill, no_alignment = [], [], []
    for cid, v in verdicts.items():
        pf = BATCH / "prefill" / f"{cid}.json"
        if not pf.is_file():
            no_prefill.append(cid)
            continue
        p = json.loads(pf.read_text())
        al = p.get("alignment") or {}
        if not al.get("n_truth_notes"):
            no_alignment.append({"cell_id": cid, "reason": p.get("reason") or "no alignment"})
            continue
        human_nh = sum(1 for b in (v.get("added_detections") or [])
                       if str(b.get("human_category") or "").startswith(NOTEHEAD_PREFIX)
                       or str(b.get("human_class") or "").startswith("notehead"))
        # a model detection the human CONFIRMED (or relabelled to a notehead)
        for det in (v.get("detections") or []):
            verdict = det.get("verdict")
            cls = det.get("human_class") or det.get("class") or ""
            if verdict in ("TP", "WRONG_CATEGORY") and str(cls).startswith("notehead"):
                human_nh += 1
        rows.append({
            "cell_id": cid,
            "truth_notes": al["n_truth_notes"],
            "human_noteheads": human_nh,
            "detector_matched_truth_notes": al.get("matched_notes"),
            "alignment_strength": al.get("strength"),
        })

    require_nonempty(rows, "usable completion-swept cells", BATCH)
    t = sum(r["truth_notes"] for r in rows)
    h = sum(r["human_noteheads"] for r in rows)
    dm = sum(r["detector_matched_truth_notes"] or 0 for r in rows)

    doc = {
        "generated_by": "benchmarks/omr-pipeline-audit-2026-09/probe/"
                        "probe_input_ceiling_from_labels.py",
        "question": "can the hand-labeling corpus supply an INPUT ceiling?",
        "batch": str(BATCH.relative_to(ROOT)),
        "why_this_batch": "the ONLY batch in the corpus carrying a COMPLETION "
                          "pass. Every other batch is a single-symbol sweep, "
                          "where everything outside the pass is unboxed BY "
                          "INSTRUCTION and a count of human boxes would measure "
                          "the pass, not the ink.",
        "coverage": {
            "cells_stamped_completion": len(verdicts),
            "cells_usable": len(rows),
            "cells_without_a_prefill_record": len(no_prefill),
            "cells_whose_prefill_has_no_alignment": len(no_alignment),
        },
        "counts": {
            "reference_notes_in_those_bars": t,
            "human_noteheads_drawn": h,
            "reference_notes_the_DETECTOR_matched": dm,
        },
        "ratios": {
            "human_boxes_per_reference_note": (h / t) if t else None,
            "detector_recall_vs_reference": (dm / t) if t else None,
            "detector_recall_vs_human": (dm / h) if h else None,
        },
        "rows": rows,
        "no_prefill": no_prefill,
        "no_alignment": no_alignment,
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({k: doc[k] for k in ("coverage", "counts", "ratios")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
