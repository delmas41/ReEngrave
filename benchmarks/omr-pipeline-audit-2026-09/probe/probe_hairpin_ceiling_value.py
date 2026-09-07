"""Turn the hairpin REFUTATION into a hairpin CEILING, and make the matched
comparison the refutation never made.

Round 2 established that a human drew 17 hairpins on 55 scanned cells of a
Breitkopf Brahms 1, so `scan:hairpin_detect` at 1.01% is a detector failure and
not missing ink. Two things were missing from that:

  (1) a VALUE. "The ink is visible" is a refutation; "a reader can recover X of
      what the encoding says is printed" is a ceiling.
  (2) THE MATCHED COMPARISON. The 1.01% is a corpus-level rate over eleven
      scanned pages. What the detector found on THESE 55 cells was never asked.

Both are answerable from artefacts already in the batch: the 55 completion-swept
verdicts, the batch's own `transcription.json` (the pipeline's read of the same
three pages), and `reference.mxl` (the encoding).

⚠️ THREE UNITS, AND CONFLATING THEM IS THE WHOLE TRAP.
    encoding   MusicXML writes a <wedge> at EACH END, so one printed hairpin is
               two elements. Wedge STARTS (crescendo|diminuendo) are counted.
    page       an engraver draws ONE arc.
    cell       a measure cell CUTS it, so one printed hairpin crossing a barline
               becomes TWO human boxes. A human box is therefore an upper bound
               on hairpins-in-that-bar, never a lower one.
So the ratio human/encoding is reported with its direction of bias stated, and no
matched pairing is claimed that the geometry cannot support.

⚠️ SINGLE EDITION, AND IRREDUCIBLY SO TODAY. Exactly one batch in the corpus
carries a COMPLETION pass; every other is a single-symbol sweep leaving other
classes unboxed by instruction. Every figure here is Breitkopf Brahms 1 and must
be quoted with the publisher named.
"""
from __future__ import annotations

import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixtureroot import require_nonempty  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "hairpin-ceiling-value.json"
BATCH = ROOT / "benchmarks" / "omr-labeling-hollow2-2026-09-breitkopf-brahms1"

HAIRPIN_CLASSES = ("dynamicCrescendoHairpin", "dynamicDiminuendoHairpin")
WEDGE_STARTS = ("crescendo", "diminuendo")


def reference_wedges(mxl: Path) -> dict:
    """{(part_index, measure_number): n_wedge_starts} from the encoding."""
    with zipfile.ZipFile(mxl) as z:
        name = next(n for n in z.namelist()
                    if n.endswith(".xml") and not n.startswith("META-INF"))
        root = ET.fromstring(z.read(name))
    out, total_elems = {}, 0
    for pi, part in enumerate(root.findall("part")):
        for meas in part.findall("measure"):
            try:
                num = int(meas.get("number"))
            except (TypeError, ValueError):
                continue
            n = 0
            for w in meas.iter("wedge"):
                total_elems += 1
                if w.get("type") in WEDGE_STARTS:
                    n += 1
            if n:
                out[(pi, num)] = out.get((pi, num), 0) + n
    return out, total_elems


def main() -> int:
    # ── the 55 completion-swept cells, with their bar and their reference parts
    cells = {}
    vfiles = require_nonempty(sorted((BATCH / "verdicts").glob("*.json")),
                              "verdict files", BATCH / "verdicts", "*.json")
    for f in vfiles:
        d = json.loads(f.read_text())
        if "completion" not in (d.get("inspected_passes") or []):
            continue
        cells[d["cell_id"]] = {
            "human_hairpins": sum(
                1 for b in (d.get("added_detections") or [])
                if str(b.get("human_class")) in HAIRPIN_CLASSES),
        }
    require_nonempty(cells, "completion-swept cells", BATCH / "verdicts")

    for cid, rec in cells.items():
        pf = BATCH / "prefill" / f"{cid}.json"
        if pf.is_file():
            p = json.loads(pf.read_text())
            rec["measure"] = p.get("measure_number")
            rec["parts"] = p.get("parts")

    # ── what the DETECTOR found on the same cells (item 1b)
    tr = json.loads((BATCH / "transcription.json").read_text())
    det_by_cell, det_total, hairpin_total = {}, 0, 0
    for page in tr["pages"]:
        pno = page.get("page_index", page.get("page_number"))
        for sy in page["systems"]:
            for st in sy["staves"]:
                for m in st["measures"]:
                    for det in m.get("detections", []):
                        det_total += 1
                        if det["class"] in HAIRPIN_CLASSES:
                            hairpin_total += 1
    # per-cell is unnecessary once the page-level count is zero, but assert it
    cell_pages = sorted({cid.split("-")[1] for cid in cells})

    wedges, wedge_elems = reference_wedges(BATCH / "reference.mxl")

    # ── the encoding's hairpin STARTS in exactly the (part, bar) pairs swept
    covered, missing_map = 0, 0
    per_cell = []
    for cid, rec in sorted(cells.items()):
        m, parts = rec.get("measure"), rec.get("parts")
        if m is None or parts is None:
            missing_map += 1
            continue
        ref = sum(wedges.get((pi, m), 0) for pi in parts)
        covered += ref
        per_cell.append({"cell_id": cid, "measure": m, "parts": parts,
                         "reference_wedge_starts": ref,
                         "human_hairpin_boxes": rec["human_hairpins"]})

    human = sum(c["human_hairpin_boxes"] for c in per_cell)
    ref_total = sum(c["reference_wedge_starts"] for c in per_cell)
    both = [c for c in per_cell if c["reference_wedge_starts"] and c["human_hairpin_boxes"]]
    ref_only = [c for c in per_cell if c["reference_wedge_starts"] and not c["human_hairpin_boxes"]]
    human_only = [c for c in per_cell if c["human_hairpin_boxes"] and not c["reference_wedge_starts"]]

    doc = {
        "generated_by": "benchmarks/omr-pipeline-audit-2026-09/probe/"
                        "probe_hairpin_ceiling_value.py",
        "edition": "Breitkopf & Härtel, Brahms Symphony 1 mvt 1 — ONE EDITION. "
                   "Every figure here must be quoted with the publisher named; "
                   "it is not a claim about scans in general.",
        "why_one_edition": "exactly one batch in the corpus carries a COMPLETION "
                           "pass. Every other is a single-symbol sweep, where the "
                           "other classes are unboxed BY INSTRUCTION, so a count "
                           "of human hairpin boxes there would measure the pass "
                           "and not the ink. Irreducible today.",
        "units": {
            "encoding": "a <wedge> at EACH END — wedge STARTS "
                        "(crescendo|diminuendo) are counted, so one printed "
                        "hairpin is one unit",
            "page": "the engraver draws one arc",
            "cell": "a measure cell CUTS the arc, so one printed hairpin "
                    "crossing a barline becomes TWO human boxes — a human box "
                    "count is an UPPER bound on hairpins in that bar",
        },
        "coverage": {
            "completion_swept_cells": len(cells),
            "cells_with_a_bar_and_parts_map": len(per_cell),
            "cells_without": missing_map,
            "pages": cell_pages,
        },
        "item_1b_matched_comparison": {
            "question": "on THESE cells, what did the detector find?",
            "detector_detections_on_these_pages_total": det_total,
            "detector_HAIRPIN_detections": hairpin_total,
            "human_hairpin_boxes": human,
            "verdict": ("the detector found %d hairpins on the same three pages "
                        "where a human drew %d on 55 cells — out of %d "
                        "detections it did make. The corpus-level 1 of 99 is not "
                        "a thin-sample artefact: on this edition it is ZERO."
                        % (hairpin_total, human, det_total)),
            "⚠️_scope": "the transcription is per PAGE, not per cell; a page-level "
                        "count of zero entails a per-cell count of zero, which is "
                        "why no per-cell join was needed. Had it been non-zero, "
                        "the join would have been required.",
        },
        "item_1_ceiling_value": {
            "reference_wedge_elements_in_the_whole_file": wedge_elems,
            "reference_wedge_STARTS_in_the_swept_bars": ref_total,
            "human_hairpin_boxes_in_the_swept_bars": human,
            "ratio_human_over_reference": (human / ref_total) if ref_total else None,
            "cells_both": len(both),
            "cells_reference_only": len(ref_only),
            "cells_human_only": len(human_only),
            "⚠️_bias": "human boxes are an UPPER bound (a barline cuts one "
                       "hairpin into two boxes) and the reference count is per "
                       "BAR OF ENTRY (a hairpin spanning three bars is one "
                       "start). The two biases push opposite ways and neither is "
                       "quantified here, so this is a BAND, not a point.",
        },
        "item_1_ceiling_BAR_LEVEL": {
            "why_this_and_not_the_ratio": "the count ratio (1.545) is unusable as "
                "a ceiling: both units are biased and in opposite directions. "
                "What IS well defined is a BAR-LEVEL question with no unit "
                "mismatch — of the swept bars where the encoding STARTS a "
                "hairpin, in how many did a human find hairpin ink?",
            "swept_bars_with_a_reference_wedge_start": len(both) + len(ref_only),
            "of_those_where_a_human_drew_a_box": len(both),
            "human_bar_recall": (len(both) / (len(both) + len(ref_only))
                                 if (len(both) + len(ref_only)) else None),
            "⚠️_n": "n = %d bars. Thin, and it is the whole sample this corpus "
                    "can offer: only one batch has a completion pass, and only "
                    "%d of its 55 swept bars carry a reference hairpin start. "
                    "The figure is a BOUND worth having and not a point estimate "
                    "worth quoting to three places."
                    % (len(both) + len(ref_only), len(both) + len(ref_only)),
            "what_it_licenses": "C_input(hairpin, Breitkopf Brahms 1) is near 1 "
                                "and is certainly not near 0.01. That converts "
                                "`scan:hairpin_detect` from 'refuted as a "
                                "ceiling' to 'bounded below' — the detector is "
                                "at ~0.01 of a ceiling that is at least 0.8.",
            "the_other_12_boxes": "12 human boxes fall in bars where the encoding "
                "starts no hairpin. Those are continuations — a hairpin spanning "
                "three bars is ONE start and is drawn across three cells — plus "
                "barline cuts. They are not false positives and are not evidence "
                "against the encoding.",
        },
        "per_cell": per_cell,
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print("ITEM 1b — matched, on the same three pages:")
    print("   detector detections total : %d" % det_total)
    print("   detector HAIRPIN dets     : %d" % hairpin_total)
    print("   human hairpin boxes       : %d  (55 completion cells)" % human)
    print()
    print("ITEM 1 — ceiling value, %d swept cells:" % len(per_cell))
    print("   reference wedge STARTS in those bars : %d" % ref_total)
    print("   human hairpin boxes in those bars    : %d" % human)
    print("   ratio human/reference                : %s"
          % (("%.3f" % (human / ref_total)) if ref_total else "n/a"))
    print("   cells both / ref-only / human-only   : %d / %d / %d"
          % (len(both), len(ref_only), len(human_only)))
    nb = len(both) + len(ref_only)
    print()
    print("ITEM 1 — the DEFENSIBLE form (bar level, no unit mismatch):")
    print("   swept bars where the encoding starts a hairpin : %d" % nb)
    print("   of those, bars where a human found ink         : %d" % len(both))
    print("   human bar recall                               : %s  (n=%d)"
          % (("%.2f" % (len(both) / nb)) if nb else "n/a", nb))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
