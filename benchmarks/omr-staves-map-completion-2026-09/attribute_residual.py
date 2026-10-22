"""After normalisation, WHICH staves still carry `entire staff` edits?

The arithmetic says the residual must be the one-line percussion staves —
`n_output_parts - n_predicted_parts` equals the map's one-line entry count on
all four Mahler rows. Arithmetic is not attribution, so this opens the op list
and NAMES the parts musicdiff left unpaired.

A part-level op (`inspart`/`delpart`) is located the way `dump_ops.py` locates
a note-level one: through a music21 object it holds, here the first bar of the
AnnPart, looked up in an index built from the parsed score.

Runs inside the musicdiff venv (no `tools.*` imports):

    .venv-omrned/bin/python attribute_residual.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from music21 import converter
from musicdiff import AnnScore, Comparison, DetailLevel

HERE = Path(__file__).resolve().parent
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
REC = (MAIN / ".claude/worktrees/reconciliation/benchmarks"
       "/omr-scan-e2e-2026-09/fixtures")
DERIVED = HERE / "derived-truth"

ROWS = ["mahler-sym5-mvt1-local-p2", "mahler-sym5-mvt1-local-p3",
        "mahler-sym5-mvt1-local-p4", "mahler-sym5-mvt1-local-p5",
        "bach-brandenburg3-mvt1-468678-p1"]


def index_measures(score):
    out = {}
    for i, part in enumerate(score.parts):
        name = (part.partName or f"part{i}").strip()
        for m in part.getElementsByClass("Measure"):
            out[m.id] = (i, name)
    return out


def locate(annpart, index):
    for bar in getattr(annpart, "bar_list", []) or []:
        m = getattr(bar, "measure", None)
        if m is not None and m in index:
            return index[m]
    return (-1, "?")


def main() -> int:
    doc = {}
    for rid in ROWS:
        pred = REC / f"{rid}.reconciliation.omr.musicxml"
        norm = DERIVED / f"{rid}.page-normalised.musicxml"
        p_sc = converter.parse(str(pred))
        t_sc = converter.parse(str(norm))
        ops, cost = Comparison.annotated_scores_diff(
            AnnScore(p_sc, DetailLevel.AllObjects),
            AnnScore(t_sc, DetailLevel.AllObjects))
        p_ix, t_ix = index_measures(p_sc), index_measures(t_sc)
        rec = {"n_pred_parts": len(p_sc.parts),
               "n_norm_truth_parts": len(t_sc.parts),
               "total_cost": cost, "part_ops": []}
        counts = Counter()
        for op in ops:
            name, o1, o2, op_cost = op[0], op[1], op[2], op[3]
            counts[name] += 1
            if name not in ("inspart", "delpart"):
                continue
            if o2 is not None:            # truth-side: a part we MISSED
                i, nm = locate(o2, t_ix)
                side = "truth (missed)"
            else:                         # pred-side: a part we INVENTED
                i, nm = locate(o1, p_ix)
                side = "pred (invented)"
            rec["part_ops"].append({"op": name, "side": side, "index": i,
                                    "name": nm, "cost": op_cost})
        rec["op_counts"] = dict(counts)
        rec["part_op_cost"] = sum(o["cost"] for o in rec["part_ops"])
        doc[rid] = rec
        print(f"{rid}: pred {rec['n_pred_parts']} parts vs normalised truth "
              f"{rec['n_norm_truth_parts']} parts; part-level ops "
              f"{len(rec['part_ops'])} costing {rec['part_op_cost']}")
        for o in rec["part_ops"]:
            print(f"    {o['op']:8s} {o['side']:16s} idx {o['index']:>3} "
                  f"{o['name']:<40s} cost {o['cost']}")
    (HERE / "residual-attribution.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print("wrote", HERE / "residual-attribution.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
