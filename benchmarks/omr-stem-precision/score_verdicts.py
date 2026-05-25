#!/usr/bin/env python3
"""Score the human-filled verdicts JSON from `run_precision_benchmark.py`.

Computes per-class precision/recall/F1 and writes a markdown report.

  precision = TP / (TP + FP)
              = correct_detections / total_detections
  recall    = TP / (TP + FN)
              = correct_detections / (correct + missed)
  F1        = 2PR / (P+R)

Usage:
    python3 score_verdicts.py path/to/verdicts.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def score(verdicts: dict) -> dict:
    cells = verdicts["cells"]

    def aggregate(kind: str) -> dict:
        """kind is 'stems' or 'beams'."""
        TP, FP, FN = 0, 0, 0
        unverdicted = 0
        per_cell = []
        for c in cells:
            tp = sum(1 for v in c[f"{kind}_verdicts"] if v["judgment"] == "correct")
            fp = sum(1 for v in c[f"{kind}_verdicts"] if v["judgment"] == "wrong")
            unv = sum(1 for v in c[f"{kind}_verdicts"] if v["judgment"] not in ("correct", "wrong"))
            missed_raw = c.get(f"{kind}_missed", "?")
            try:
                missed = int(missed_raw)
            except (TypeError, ValueError):
                missed = 0
                if missed_raw != 0 and missed_raw != "0":
                    unv += 1   # mark missed as ungraded too
            TP += tp; FP += fp; FN += missed
            unverdicted += unv
            per_cell.append({
                "cell_id": c["cell_id"],
                "TP": tp, "FP": fp, "FN": missed,
                "ungraded": unv,
            })
        precision = TP / (TP + FP) if (TP + FP) > 0 else None
        recall = TP / (TP + FN) if (TP + FN) > 0 else None
        if precision is not None and recall is not None and (precision + recall) > 0:
            f1 = 2 * precision * recall / (precision + recall)
        else:
            f1 = None
        return {
            "TP": TP, "FP": FP, "FN": FN, "ungraded": unverdicted,
            "precision": precision, "recall": recall, "f1": f1,
            "per_cell": per_cell,
        }

    return {
        "stems": aggregate("stems"),
        "beams": aggregate("beams"),
    }


def render_report(scores: dict, out_md: Path) -> None:
    lines = []
    lines.append("# Stem & Beam Precision Benchmark — Verdict Results\n")
    for kind in ("stems", "beams"):
        s = scores[kind]
        lines.append(f"## {kind.capitalize()}\n")
        p = s["precision"]; r = s["recall"]; f1 = s["f1"]
        p_str = f"{p*100:.1f}%" if p is not None else "—"
        r_str = f"{r*100:.1f}%" if r is not None else "—"
        f1_str = f"{f1*100:.1f}%" if f1 is not None else "—"
        lines.append(f"- **Precision:** {p_str} ({s['TP']} correct / {s['TP'] + s['FP']} total CV detections)")
        lines.append(f"- **Recall:** {r_str} ({s['TP']} correct / {s['TP'] + s['FN']} real)")
        lines.append(f"- **F1:** {f1_str}")
        lines.append(f"- TP={s['TP']}, FP={s['FP']}, FN={s['FN']}, ungraded={s['ungraded']}")
        lines.append("")
        lines.append("Per-cell:")
        lines.append("")
        lines.append("| Cell | TP | FP | FN | Ungraded |")
        lines.append("|---|---:|---:|---:|---:|")
        for pc in s["per_cell"]:
            lines.append(f"| `{pc['cell_id']}` | {pc['TP']} | {pc['FP']} | {pc['FN']} | {pc['ungraded']} |")
        lines.append("")
    out_md.write_text("\n".join(lines))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("verdicts", help="Path to filled-in verdicts.json")
    ap.add_argument("--out", default=None, help="Markdown report path (default: <verdicts>.report.md)")
    args = ap.parse_args(argv[1:])

    verdicts_path = Path(args.verdicts)
    verdicts = json.loads(verdicts_path.read_text())

    scores = score(verdicts)
    out_md = Path(args.out) if args.out else verdicts_path.with_suffix(".report.md")
    render_report(scores, out_md)

    # Also print summary
    for kind in ("stems", "beams"):
        s = scores[kind]
        p = s["precision"]; r = s["recall"]; f1 = s["f1"]
        p_str = f"{p*100:.1f}%" if p is not None else "—"
        r_str = f"{r*100:.1f}%" if r is not None else "—"
        f1_str = f"{f1*100:.1f}%" if f1 is not None else "—"
        print(f"{kind:6}  P={p_str}  R={r_str}  F1={f1_str}  "
              f"(TP={s['TP']} FP={s['FP']} FN={s['FN']} ungraded={s['ungraded']})")
    print(f"\nReport: {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
