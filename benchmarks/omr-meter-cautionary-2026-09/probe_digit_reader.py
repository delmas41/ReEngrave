"""Where can the DETECTOR'S digit reader form a meter at all — and could it
arbitrate an OPENING directly, without a cautionary?

⚠️⚠️ THE CHEAPER HYPOTHESIS FIRST, BECAUSE IF IT HOLDS THE CAUTIONARY IS
UNNECESSARY. A cautionary is rare (three in the whole committed corpus). But
the two readers that produce it and the mis-voted opening are DIFFERENT
readers, and they both look at every cell: `adjudicate_meter` votes the
opening off `Q.METER_TEMPLATE` (sliding a Bravura composite along the header
crop) while a cautionary is built off `Q.METER_GLYPH` (the detector's own
`timeSig*` boxes, stacked by `y_center`). **If the detector can read a stack at
CELL 0, the contest needs no cautionary and has the reach of every system.**
`_meter_changes` skips cell 0 by design — *"cell 0 states the staff's
OPENING"* — so nothing has ever asked.

⚠️ IT DRIVES THE PIPELINE'S OWN `rhythm._meter_from_digits` AND
`_meter_from_letter`, imported, not re-implemented — so what this reports is
what that reader would say, not what a second reader thinks it would say.

⚠️⚠️ THE INPUT IS A *LEGACY* TRANSCRIPTION AND THAT IS A REAL CAVEAT, STATED
BEFORE THE RESULT. A cloud container has no weights and no `library/`, so the
only page-level artefact for this document is the committed
`benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json`
(Breitkopf Brahms 1, **pdf pages 1-3**, same weights, same 600 dpi). It was
made by `transcribe()`, which passes `iou=0.5, agnostic_nms=True`, where
`gather.py` takes the detector's own `0.7 / False` — CLAUDE.md records that
divergence. Class-agnostic NMS suppresses ACROSS classes, so GATHER sees at
least as many boxes as this file does: every count here is a **LOWER BOUND**
on what the staged path would see, and the direction of the bias is stated
rather than assumed away.

⚠️ THE CAUTIONARY ITSELF IS OUT OF REACH: it stands on pdf page 0 and this
artefact starts at page 1. What IS in reach is the very system whose opening
is voted `9/4`.

    python3 benchmarks/omr-meter-cautionary-2026-09/probe_digit_reader.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.adjudicators import rhythm                  # noqa: E402

DEFAULT_TX = (ROOT / "benchmarks" /
              "omr-labeling-hollow2-2026-09-breitkopf-brahms1" /
              "transcription.json")


class _Row:
    """The two fields `_meter_from_digits` reads, and nothing else.

    ⚠️ Deliberately minimal: a shim that carried more would invite the reader
    to grow a dependency this probe has silently satisfied.
    """

    __slots__ = ("value", "detail")

    def __init__(self, smufl: str, y_center: float):
        self.value = smufl
        self.detail = {"y_center": y_center}


def _rows_for(measure) -> list:
    out = []
    for d in measure.get("detections", []):
        cls = d.get("class", "")
        if not cls.startswith("timeSig"):
            continue
        x, y, w, h = d["bbox"]
        # ⚠️ `SymbolDetection.y_center` is `y_canonical + height_canonical//2`
        # (template_matcher.py). Reproduced exactly, integer division and all,
        # because `_meter_from_digits` compares two of these for EQUALITY to
        # decide "all at one height: not a stack" — and a float centre would
        # make that test fire differently.
        out.append(_Row(cls, y + h // 2))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcription", default=str(DEFAULT_TX))
    ap.add_argument("--json-out", default=str(HERE / "out" / "digits.json"))
    a = ap.parse_args()

    tx_path = Path(a.transcription)
    if not tx_path.is_file():
        print(f"DEAD: no transcription at {tx_path}")
        return 2
    tx = json.loads(tx_path.read_text())

    print("═══ PROVENANCE ═══")
    for k in ("source_pdf", "weights", "dpi", "conf_threshold",
              "iou_threshold", "agnostic_nms", "n_detections_total"):
        print(f"  {k:<20} {tx.get(k)}")
    print("  ⚠️ LEGACY arm: agnostic_nms=True where gather.py uses False, so"
          "\n     every count below is a LOWER BOUND on the staged path's.")

    rows = []
    n_staff_cells = n_with_glyph = 0
    for page in tx["pages"]:
        p = page.get("page_index")
        for si, sysd in enumerate(page.get("systems", [])):
            staves = sysd.get("staves", [])
            n_cells = max((len(st.get("measures", [])) for st in staves),
                          default=0)
            for sti, st in enumerate(staves):
                meas = st.get("measures", [])
                last = len(meas) - 1
                for mi, m in enumerate(meas):
                    n_staff_cells += 1
                    rr = _rows_for(m)
                    if not rr:
                        continue
                    n_with_glyph += 1
                    pair = rhythm._meter_from_digits(rr)
                    letter = (None if pair
                              else rhythm._meter_from_letter(rr))
                    rows.append({
                        "page": p, "system": si, "staff": sti, "cell": mi,
                        "is_cell0": mi == 0, "is_last_cell": mi == last,
                        "n_cells": n_cells, "n_glyphs": len(rr),
                        "glyphs": sorted(r.value for r in rr),
                        "digit_pair": (f"{pair[0]}/{pair[1]}" if pair
                                       else None),
                        "letter": (f"{letter[0]}/{letter[1]}" if letter
                                   else None),
                    })

    print("\n═══ REACH ═══")
    print(f"  staff-cells walked ............. {n_staff_cells}")
    print(f"  ...holding any timeSig glyph ... {n_with_glyph}")
    paired = [r for r in rows if r["digit_pair"]]
    lettered = [r for r in rows if r["letter"]]
    print(f"  ...that form a DIGIT STACK ..... {len(paired)}")
    print(f"  ...that form a LETTER meter .... {len(lettered)}")
    if not rows:
        print("DEAD: no timeSig glyph anywhere — the reader cannot be "
              "exercised on this artefact.")
        return 2
    if not paired:
        print("\n⚠️ POSITIVE CONTROL: the digit reader forms NO stack "
              "anywhere on this artefact, so a zero at cell 0 below would be "
              "uninformative — it would mean the reader is dead, not that "
              "the opening is unreadable.")
        return 3
    print("  ✓ positive control: the reader DOES form stacks on this "
          "artefact, so a zero at cell 0 is a fact about cell 0.")

    # ── 1. CELL 0 — could the detector arbitrate an opening directly? ───────
    print("\n═══ 1. CELL 0 — the opening, read by the DETECTOR ═══")
    print("  This is the cell `adjudicate_meter` votes on via the TEMPLATE"
          " reader.\n  If the detector reads a stack here, a contest needs no"
          " cautionary.\n")
    by_sys: dict = {}
    for r in rows:
        if not r["is_cell0"]:
            continue
        by_sys.setdefault((r["page"], r["system"]), []).append(r)
    all_sys = sorted({(p["page_index"], i)
                      for p in tx["pages"]
                      for i in range(len(p.get("systems", [])))})
    n_sys_stack = 0
    for key in all_sys:
        rr = by_sys.get(key, [])
        stacks = [x for x in rr if x["digit_pair"]]
        letters = [x for x in rr if x["letter"]]
        if stacks:
            n_sys_stack += 1
        print(f"  page {key[0]} system {key[1]}: "
              f"{len(rr):>2} staves with a glyph at cell 0, "
              f"{len(stacks):>2} form a stack, {len(letters):>2} a letter"
              + (f"   -> {sorted({x['digit_pair'] for x in stacks})}"
                 if stacks else ""))
        for x in rr:
            print(f"        staff {x['staff']:>2}  {x['glyphs']}"
                  f"  stack={x['digit_pair']}  letter={x['letter']}")
    print(f"\n  systems where the DETECTOR forms an opening stack: "
          f"{n_sys_stack} of {len(all_sys)}")

    # ── 2. LAST CELL — how often is a cautionary even proposable? ──────────
    print("\n═══ 2. LAST CELL — how often does a cautionary get proposed ═══")
    print("  ⚠️ Brahms 1 mvt 1 prints its ONLY meter change at m8, announced "
          "by the\n     cautionary at the end of pdf page 0. Pages 1-3 print "
          "NO cautionary at\n     all, so every last-cell reading here is a "
          "FALSE one — which is what\n     makes this the false-positive "
          "measurement.\n")
    last = [r for r in rows if r["is_last_cell"]]
    last_stack = [r for r in last if r["digit_pair"]]
    last_letter = [r for r in last if r["letter"]]
    print(f"  staff-last-cells holding a glyph ... {len(last)}")
    print(f"  ...forming a stack ................. {len(last_stack)}")
    print(f"  ...forming a letter ................ {len(last_letter)}")
    for r in last_stack + last_letter:
        print(f"      page {r['page']} sys {r['system']} staff {r['staff']} "
              f"cell {r['cell']}/{r['n_cells'] - 1}  {r['glyphs']}  "
              f"-> {r['digit_pair'] or r['letter']}")

    # ── 2b. WHAT the stacks say, and what the page prints there ────────────
    print("\n═══ 2b. WHAT THE STACKS SAY ═══")
    vals: dict = {}
    for r in paired:
        vals[r["digit_pair"]] = vals.get(r["digit_pair"], 0) + 1
    print(f"  {len(paired)} stacks: {dict(sorted(vals.items()))}")
    plausible = {f"{n}/{d}" for (n, d) in rhythm._PLAUSIBLE_METERS}
    refused = {k: v for k, v in vals.items() if k not in plausible}
    print(f"  ...of which `_PLAUSIBLE_METERS` refuses outright: "
          f"{dict(sorted(refused.items()))}")
    # ⚠️ TRUTH ONLY WHERE THE PROJECT ALREADY COMMITS IT. The boundary
    # benchmark's hand-read table covers pdf pages 0-1 of this edition
    # (`brahms1-317803`): page 1 system 0 opens on the `9/8` bar (m8) and
    # changes to `6/8` at its cell 1; system 1 (mm 15-22) prints nothing. It
    # says nothing about pdf pages 2-3, so those are COUNTED and NOT SCORED.
    printed = {(1, 0, 0): "9/8", (1, 0, 1): "6/8"}
    print("\n  where the committed truth says a meter IS printed "
          "(pdf page 1 only):")
    for (pg, sy, ce), want in sorted(printed.items()):
        got = [r for r in rows
               if (r["page"], r["system"], r["cell"]) == (pg, sy, ce)]
        stacks = [r["digit_pair"] for r in got if r["digit_pair"]]
        print(f"      page {pg} sys {sy} cell {ce}  prints {want:>4}  ->  "
              f"{len(got)} staves hold a glyph, {len(stacks)} form a stack "
              f"{sorted(set(stacks))}")
    print("  ⚠️ pdf pages 2-3 carry no committed per-cell truth here and are "
          "NOT scored.")

    # ── 3. the loose digits: how much meter-shaped noise is there ──────────
    print("\n═══ 3. THE NOISE FLOOR ═══")
    loose = [r for r in rows if not r["digit_pair"] and not r["letter"]]
    print(f"  staff-cells with a glyph that names NOTHING ... {len(loose)}")
    cls: dict = {}
    for r in rows:
        for g in r["glyphs"]:
            cls[g] = cls.get(g, 0) + 1
    print(f"  glyph classes seen: {dict(sorted(cls.items()))}")
    mid = [r for r in rows if not r["is_cell0"]]
    print(f"  glyph-bearing cells at cell 0 .... "
          f"{len(rows) - len(mid)}   mid/late ... {len(mid)}")

    Path(a.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json_out).write_text(json.dumps(
        {"provenance": {k: tx.get(k) for k in
                        ("source_pdf", "weights", "dpi", "conf_threshold",
                         "iou_threshold", "agnostic_nms")},
         "n_staff_cells": n_staff_cells, "rows": rows}, indent=1) + "\n")
    print(f"\nwrote {a.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
