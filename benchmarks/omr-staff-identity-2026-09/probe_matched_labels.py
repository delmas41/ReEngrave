#!/usr/bin/env python3
"""THE multiplicity question, asked directly.

The condensed-parts session's refusal rests on one fact: `Flauti`, `Oboi`,
`Clarinetti in …`, `Fagotti`, `Corni …`, `Trombe in …` are printed by BOTH the
Litolff Beethoven and the Simrock Dvořák, and the Gradus Beethoven encodes each
as TWO parts while the Gradus Dvořák encodes each as ONE. The label rule is
right about the engraving and wrong about the file, and it costs +2,181 edits.

Sean's bet is that several weak PAGE-SIDE signals could do what the label
cannot. This probe tests that in the sharpest available form: it pairs staves
that carry the SAME printed section label across the two editions and asks
whether ANY page-side signal separates the truth-2 members from the truth-1
members.

If the distributions overlap, no combiner over these signals can succeed —
which is a proof about the signals, not a failure of the search over them.

    python3 benchmarks/omr-staff-identity-2026-09/probe_matched_labels.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from tools.omr import instruments as INST                     # noqa: E402

SIGNALS = [
    ("s7_dyad_bars", "S7 bars carrying a dyad"),
    ("s7_divisi_bars", "S7 bars with stems both ways"),
    ("s7_rest_only_bars", "S7 rest-only bars"),
    ("s7_note_bars", "S7 bars carrying notes"),
    ("s8_group_size", "S8 bracket-block size"),
    ("s8_brace_detections", "S8 brace detections"),
    ("s9_dyn_total", "S9 dynamics filed here"),
    ("s9_dyn_ambiguous", "S9 dynamics in the gap, nearer the neighbour"),
    ("s9_arc_reaches_neighbour_band", "S9 arcs reaching a neighbour's band"),
    ("s4_bimodal_gap", "S4 largest interior pitch gap (two envelopes?)"),
    ("s4_n_notes", "S4 notes read"),
]


def key_of(label: str | None) -> str | None:
    """The canonical instrument the printed label names, ignoring number and
    key qualifiers — so `Flauti` and `2 Flöten` pair, as do `Clarinetti in B`
    and `Clarinetti in A`."""
    if not label:
        return None
    m = INST.lookup(label)
    return m.instrument.name if m else None


def ratio(r, num, den):
    a, b = r.get(num) or 0, r.get(den) or 0
    return round(a / b, 3) if b else None


def main():
    E = json.loads((HERE / "evidence.json").read_text())["evidence"]
    T = [r for r in E if r["TRUTH_n_parts"] and r.get("CEILING_hand_label")]

    by_inst = defaultdict(lambda: defaultdict(list))
    for r in T:
        k = key_of(r["CEILING_hand_label"])
        if k:
            by_inst[k][r["TRUTH_n_parts"]].append(r)

    contested = {k: v for k, v in by_inst.items() if len(v) > 1}
    print(f"instruments printed with the same section label under BOTH a "
          f"1-part and a >1-part encoding: {len(contested)}\n")

    out = {"contested_instruments": {}, "separability": {}}

    for inst in sorted(contested):
        groups = contested[inst]
        print(f"── {inst} " + "─" * (60 - len(inst)))
        for n_parts in sorted(groups):
            for r in groups[n_parts]:
                print(f"   truth={n_parts}  {r['row_id'][:30]:30s} i={r['staff_index']:2d} "
                      f"{str(r['CEILING_hand_label'])[:22]:22s} "
                      f"dyad={r['s7_dyad_bars']}/{r['s7_note_bars']} "
                      f"div={r['s7_divisi_bars']} blk={r.get('s8_group_size')} "
                      f"brace={r['s8_brace_detections']} "
                      f"dyn={r.get('s9_dyn_total', 0)}/amb={r.get('s9_dyn_ambiguous', 0)} "
                      f"arcs={r.get('s9_arc_reaches_neighbour_band', 0)} "
                      f"notes={r['s4_n_notes']}")
        out["contested_instruments"][inst] = {
            str(n): [{"row": r["row_id"], "staff": r["staff_index"],
                      "label": r["CEILING_hand_label"],
                      **{k: r.get(k) for k, _ in SIGNALS}}
                     for r in rs] for n, rs in groups.items()}
        print()

    # ── separability over the contested population only ──────────────────────
    pool = [r for inst in contested for n in contested[inst]
            for r in contested[inst][n]]
    ones = [r for r in pool if r["TRUTH_n_parts"] == 1]
    twos = [r for r in pool if r["TRUTH_n_parts"] > 1]
    print(f"contested pool: {len(ones)} staves encoded as 1 part, "
          f"{len(twos)} as >1, all carrying the same printed section labels\n")
    print(f"{'signal':46s} {'1-part range':>22s} {'>1-part range':>22s} {'separates?':>11s}")
    for k, desc in SIGNALS:
        a = sorted(x for x in (r.get(k) for r in ones) if x is not None)
        b = sorted(x for x in (r.get(k) for r in twos) if x is not None)
        if not a or not b:
            continue
        sep = (min(a) > max(b)) or (min(b) > max(a))
        out["separability"][k] = {
            "one_part": {"n": len(a), "min": a[0], "max": a[-1],
                         "median": a[len(a) // 2]},
            "multi_part": {"n": len(b), "min": b[0], "max": b[-1],
                           "median": b[len(b) // 2]},
            "disjoint": bool(sep)}
        print(f"{desc:46s} {f'{a[0]}..{a[-1]} (med {a[len(a) // 2]})':>22s} "
              f"{f'{b[0]}..{b[-1]} (med {b[len(b) // 2]})':>22s} "
              f"{'YES' if sep else 'no — overlaps':>11s}")

    # a normalised version of the texture signals, since bar counts differ
    print()
    for num, den, desc in [("s7_dyad_bars", "s7_note_bars", "S7 dyad SHARE of note bars"),
                           ("s7_divisi_bars", "s7_note_bars", "S7 divisi SHARE of note bars"),
                           ("s9_dyn_ambiguous", "s9_dyn_total", "S9 ambiguous SHARE of dynamics")]:
        a = sorted(x for x in (ratio(r, num, den) for r in ones) if x is not None)
        b = sorted(x for x in (ratio(r, num, den) for r in twos) if x is not None)
        if not a or not b:
            continue
        sep = (min(a) > max(b)) or (min(b) > max(a))
        out["separability"][f"{num}/{den}"] = {
            "one_part": {"n": len(a), "min": a[0], "max": a[-1]},
            "multi_part": {"n": len(b), "min": b[0], "max": b[-1]},
            "disjoint": bool(sep)}
        print(f"{desc:46s} {f'{a[0]}..{a[-1]}':>22s} {f'{b[0]}..{b[-1]}':>22s} "
              f"{'YES' if sep else 'no — overlaps':>11s}")

    (HERE / "matched-labels.json").write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
