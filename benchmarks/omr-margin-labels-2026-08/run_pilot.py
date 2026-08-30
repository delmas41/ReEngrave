#!/usr/bin/env python3
"""Can Claude read instrument labels off a score's margin?

Ground truth is **free**: 18 of 65 IMSLP score PDFs carry an OCR text layer, and
`staff_labels.read_staff_labels` already extracts labels from it. So the vision
reader can be scored on pages where the answer is known, before being trusted on
scans where it is not.

Scoring is on the RESOLVED INSTRUMENT, not the raw string — "Fg." and "Fag." are
both Bassoon and both correct. Three outcomes per staff:

    agree      both paths resolve the same instrument
    disagree   both resolve, differently  <- the number that matters
    recovered  vision resolved one where the text layer did not

`recovered` is the point of the exercise. The text layer resolves 79% of labelled
staves; the residue is garbled OCR ("V}a.", ",/\"", "/A") that a human reads at a
glance.

Usage:
    python3 benchmarks/omr-margin-labels-2026-08/run_pilot.py            # default budget
    python3 benchmarks/omr-margin-labels-2026-08/run_pilot.py --budget 2.00 --limit 12
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.staff_labels import has_text_layer, read_staff_labels
from tools.omr.staff_labels_vision import (
    DEFAULT_MODEL,
    build_margin_crop,
    read_system_labels,
)
from tools.omr.instruments import lookup

CORPUS = ("/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp")
PAGES = (40, 59)
# Claude Opus 5, $/MTok (skill "claude-api" model table).
PRICE_IN, PRICE_OUT = 5.00, 25.00


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=1.00, help="hard USD cap")
    ap.add_argument("--limit", type=int, default=10, help="max systems to read")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        # backend/.env is gitignored, so in a worktree it only exists in the
        # main checkout. Try both.
        for env in (Path(__file__).resolve().parents[2] / "backend" / ".env",
                    Path("/Users/seanjohnson/Desktop/ReEngrave/backend/.env")):
            if not env.exists():
                continue
            for line in env.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()
            if os.environ.get("ANTHROPIC_API_KEY"):
                break
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("no ANTHROPIC_API_KEY", file=sys.stderr)
        return 1

    import anthropic
    client = anthropic.Anthropic()

    pdfs = [p for w in sorted(os.listdir(CORPUS))
            for p in sorted(glob.glob(f"{CORPUS}/{w}/pdfs/*/score.pdf"))]

    tally = collections.Counter()
    spend = 0.0
    systems_read = 0
    examples: list[str] = []

    for pdf in pdfs:
        if systems_read >= args.limit or spend >= args.budget:
            break
        for page_index in PAGES:
            if systems_read >= args.limit or spend >= args.budget:
                break
            if not has_text_layer(pdf, page_index):
                continue
            try:
                pws = detect_staves(render_page(pdf, page_index, dpi=args.dpi))
            except Exception as exc:                       # noqa: BLE001
                print(f"skip {pdf} p{page_index}: {exc}", file=sys.stderr)
                continue

            truth = {l.staff_index: l for l in read_staff_labels(pws)}
            by_system: dict[int, list] = {}
            for st in sorted(pws.staves, key=lambda s: s.top_y):
                by_system.setdefault(st.system_index, []).append(st)

            for _sys, staves in sorted(by_system.items()):
                if systems_read >= args.limit or spend >= args.budget:
                    break
                crop = build_margin_crop(pws, staves)
                if crop is None:
                    continue
                try:
                    texts = read_system_labels(crop, client=client, model=args.model)
                except Exception as exc:                   # noqa: BLE001
                    print(f"  API error: {exc}", file=sys.stderr)
                    continue
                systems_read += 1
                # Rough spend: the image plus a short prompt and answer.
                px = 196 * 1568
                spend += (px / 750 + 300) * PRICE_IN / 1e6 + 300 * PRICE_OUT / 1e6

                name = Path(pdf).parents[1].name
                for st in staves:
                    idx = st.staff_index
                    v_text = texts.get(idx)
                    v_hit = lookup(v_text) if v_text else None
                    v_inst = v_hit.instrument.name if v_hit else None
                    t = truth.get(idx)
                    t_inst = t.instrument.name if (t and t.matched) else None

                    if t_inst and v_inst:
                        if t_inst == v_inst:
                            tally["agree"] += 1
                        else:
                            tally["disagree"] += 1
                            if len(examples) < 12:
                                examples.append(
                                    f"  DISAGREE {name} p{page_index} staff {idx}: "
                                    f"text-layer {t.text!r}->{t_inst}  vs  "
                                    f"vision {v_text!r}->{v_inst}")
                    elif v_inst and not t_inst:
                        tally["recovered"] += 1
                        if len(examples) < 12:
                            examples.append(
                                f"  RECOVERED {name} p{page_index} staff {idx}: "
                                f"text-layer {(t.text if t else None)!r} -> "
                                f"vision {v_text!r} -> {v_inst}")
                    elif t_inst and not v_inst:
                        tally["missed_by_vision"] += 1
                        if len(examples) < 12:
                            examples.append(
                                f"  MISSED   {name} p{page_index} staff {idx}: "
                                f"text-layer {t.text!r}->{t_inst}, vision returned "
                                f"{v_text!r}")
                    else:
                        tally["both_silent"] += 1

    print(f"\nmodel {args.model}   systems read: {systems_read}   "
          f"estimated spend: ${spend:.2f} (cap ${args.budget:.2f})")
    total = sum(tally.values())
    print(f"staves compared: {total}")
    for k in ("agree", "disagree", "recovered", "missed_by_vision", "both_silent"):
        print(f"  {k:17s} {tally[k]:4d}")
    resolved = tally["agree"] + tally["disagree"]
    if resolved:
        print(f"\nagreement where both resolved: {tally['agree']}/{resolved} "
              f"({tally['agree'] / resolved:.0%})")
    print(f"staves the text layer could not resolve but vision could: {tally['recovered']}")
    if examples:
        print("\nexamples:")
        for e in examples:
            print(e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
