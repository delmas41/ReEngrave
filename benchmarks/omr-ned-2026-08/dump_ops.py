"""Dump musicdiff's op list for one pair, located to part and measure.

`orchestral_eval --omr-ned` reports CATEGORIES; a category is not a cause. This
opens the individual operations behind one and says where each one is, which is
what turns "wrong note, 733 edits" into a page and a staff to look at.

RUN IT WITH THE musicdiff VENV, not the host Python:

    .venv-omrned/bin/python benchmarks/omr-ned-2026-08/dump_ops.py \\
        benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.omr.musicxml \\
        benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.musicxml

Like `_omrned_worker.py` this file runs inside an interpreter that does NOT have
this project on its path — keep it free of `tools.*` imports.

ARGUMENT ORDER IS PREDICTION FIRST, matching `diff_ml_training(pred, truth)` in
the worker, and it decides how every op name reads:

    *ins*  — present in the TRUTH only .......... we MISSED it
    *del*  — present in the PREDICTION only ..... we INVENTED it

Getting that backwards inverts every conclusion, so it is asserted rather than
remembered: `insbar` carries `None` on the prediction side.

WHAT `wrong note` ACTUALLY IS, since the name invites a wrong reading.
musicdiff maps `noteins`/`notedel` to `wrong note` and `pitchnameedit` to a
SEPARATE `wrong pitch` category. So `wrong note` is about notes being present
or absent, never about a note having the wrong pitch. Two notes that musicdiff
declines to pair appear as one `noteins` plus one `notedel`, which looks like a
substitution in the totals and is not one.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from music21 import converter, stream
from musicdiff import AnnScore, Comparison, DetailLevel

#: musicdiff's own op -> category map lives in Visualization; importing it keeps
#: this report speaking the same language as the CSV the benchmark prints.
from musicdiff.visualization import Visualization  # noqa: E402


def _index(score: stream.Score) -> dict[Any, tuple[int, str, Any]]:
    """music21 object id -> (part index, part name, measure number).

    Both notes and measures are indexed, so an op holding either kind of object
    can be placed. Chord members carry the CHORD's id in musicdiff, which is why
    the chord itself is indexed rather than its pitches.
    """
    out: dict[Any, tuple[int, str, Any]] = {}
    for p_idx, part in enumerate(score.parts):
        name = (part.partName or f"part{p_idx}").strip()
        for measure in part.getElementsByClass("Measure"):
            here = (p_idx, name, measure.number)
            out[measure.id] = here
            for element in measure.recurse().notesAndRests:
                out[element.id] = here
    return out


def _locate(op: tuple, pred_index: dict, truth_index: dict) -> tuple:
    """Best (side, part, name, measure) for an op, preferring the truth side."""
    for obj, index, side in ((op[2], truth_index, "truth"),
                            (op[1], pred_index, "pred")):
        if obj is None:
            continue
        ident = getattr(obj, "general_note", None)
        if ident is None:
            ident = getattr(obj, "measure", None)
        if ident is None:
            continue
        found = index.get(ident)
        if found:
            return (side, *found)
    return ("?", -1, "?", None)


def dump(pred: Path, truth: Path, detail: str = "AllObjects") -> dict[str, Any]:
    pred_score = converter.parse(str(pred))
    truth_score = converter.parse(str(truth))
    level = getattr(DetailLevel, detail)
    ops, cost = Comparison.annotated_scores_diff(
        AnnScore(pred_score, level), AnnScore(truth_score, level))

    pred_index = _index(pred_score)
    truth_index = _index(truth_score)

    categories = Visualization._HEADER_NAME_OF_EDIT_NAME
    by_op: Counter = Counter()
    cost_by_op: Counter = Counter()
    cost_by_category: Counter = Counter()
    by_part: dict[str, Counter] = defaultdict(Counter)
    rows = []
    for op in ops:
        name, o1, o2, op_cost = op[0], op[1], op[2], op[3]
        side, part_idx, part_name, measure = _locate(op, pred_index, truth_index)
        category = categories.get(name, f"?({name})")
        by_op[name] += 1
        cost_by_op[name] += op_cost
        cost_by_category[category] += op_cost
        key = f"{part_idx:02d} {part_name}"
        by_part[key][category] += op_cost
        rows.append({
            "op": name,
            "category": category,
            "cost": op_cost,
            "side": side,
            "part_index": part_idx,
            "part_name": part_name,
            "measure": measure,
            "pred_repr": str(o1)[:200] if o1 is not None else None,
            "truth_repr": str(o2)[:200] if o2 is not None else None,
        })

    # The direction of ins/del is load-bearing for every conclusion drawn from
    # this file, so check it against the data rather than trusting the comment.
    # Only the STRUCTURAL ops carry a None side: an attribute op such as
    # `accidentins` describes a note that exists in both scores and therefore
    # holds an object on each side, which is not evidence of a swap.
    for row in rows:
        if row["op"] in ("noteins", "insbar") and row["pred_repr"] is not None:
            raise AssertionError(
                f"{row['op']} carries a prediction-side object; arguments are "
                "probably swapped (expected pred first, truth second)")
        if row["op"] in ("notedel", "delbar") and row["truth_repr"] is not None:
            raise AssertionError(
                f"{row['op']} carries a truth-side object; arguments are "
                "probably swapped (expected pred first, truth second)")

    return {
        "pred": str(pred),
        "truth": str(truth),
        "total_cost": cost,
        "n_ops": len(ops),
        "ops_by_name": dict(by_op.most_common()),
        "cost_by_name": dict(cost_by_op.most_common()),
        "cost_by_category": dict(cost_by_category.most_common()),
        "cost_by_part": {k: dict(v.most_common())
                         for k, v in sorted(by_part.items())},
        "rows": rows,
    }


def report(result: dict[str, Any], top: int = 12) -> None:
    print(f"\n{Path(result['pred']).name}  ops {result['n_ops']}  "
          f"cost {result['total_cost']}")
    print("\n  cost by category")
    for name, c in list(result["cost_by_category"].items())[:top]:
        print(f"    {name:44s} {c:>6d}")
    print("\n  cost by op")
    for name, c in list(result["cost_by_name"].items())[:top]:
        print(f"    {name:24s} {c:>6d}  ({result['ops_by_name'][name]} ops)")
    print("\n  cost by part (top categories)")
    ranked = sorted(result["cost_by_part"].items(),
                    key=lambda kv: -sum(kv[1].values()))
    for part, cats in ranked[:top]:
        total = sum(cats.values())
        head = "  ".join(f"{k.replace(' OMR-ED', '')}={v}"
                         for k, v in list(cats.items())[:3])
        print(f"    {part[:26]:26s} {total:>6d}   {head}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pred", type=Path)
    ap.add_argument("truth", type=Path)
    ap.add_argument("--detail", default="AllObjects")
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--only", default=None,
                    help="print every row whose op name contains this")
    args = ap.parse_args(argv)

    result = dump(args.pred, args.truth, args.detail)
    report(result)

    if args.only:
        print(f"\n  rows matching {args.only!r}")
        for row in result["rows"]:
            if args.only in row["op"]:
                print(f"    {row['op']:12s} c{row['cost']:<3d} "
                      f"p{row['part_index']:02d} {row['part_name'][:18]:18s} "
                      f"m{row['measure']}  "
                      f"pred={row['pred_repr']}  truth={row['truth_repr']}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2, default=str) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
