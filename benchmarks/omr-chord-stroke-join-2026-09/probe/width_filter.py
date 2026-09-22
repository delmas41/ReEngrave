"""Would a NOTEHEAD-WIDTH floor clean the population this rule acts on?

⚠️ THE PRINT SAYS THE RULE'S FAILURE IS NOT ITS CONVENTION BUT ITS POPULATION:
of the 17 candidates the print settles, 13 are not two noteheads at all --
clefs, printed `ff`, a barline, beams, a quarter rest, an augmentation dot.
Two sibling lanes measured a width floor against exactly that contamination
(`omr-stem-crop-pass-2026-09`: width < 1.0 staff spaces catches 39 of 46
non-noteheads at a cost of 0 of 63 real stems; `omr-notehead-width-2026-09`:
it takes 6 of 1,443 and 12 of 1,791 of the heads the pipeline reads
CORRECTLY). This asks what it would do HERE.

⚠️⚠️ THE UNIT IS `Q.CELL_STAFF_SPACE` AND THE ABSENT CASE ABSTAINS. A sibling
lane computed Breitkopf figures under a flat 100 px and was wrong by up to
25%, because only 514 of 817 Breitkopf cells sit at the nominal. That is the
exact trap that quantity's docstring exists to prevent, and a box whose cell
has no measured space is REPORTED as unmeasurable rather than given one.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import cell_of, collect, stream_array  # noqa: E402


def cell_spaces(record):
    """cell key -> the CELL's own staff space, in canonical px."""
    out = {}
    for o in stream_array(record, "observations"):
        if o.get("quantity") != "cell_staff_space":
            continue
        try:
            v = float(o["value"])
        except (TypeError, ValueError, KeyError):
            continue
        c = cell_of(o.get("subject", ""))
        if c:
            out[c] = v
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--reach", required=True)
    ap.add_argument("--adjudication", default="")
    ap.add_argument("--label", default="")
    ap.add_argument("--floor", type=float, default=1.0,
                    help="notehead width floor, in staff spaces "
                         "(the sibling crop pass's, imported as a NUMBER and "
                         "not re-argued)")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    reach = json.loads(Path(a.reach).read_text())
    wanted = {r["head"] for r in reach["rows"]}
    wanted |= {m for r in reach["rows"] for m in r["mates"]}

    spaces = cell_spaces(a.record)
    _stems, heads, _b, _n = collect(a.record)

    width = {}
    for c, hs in heads.items():
        sp = spaces.get(c)
        for h in hs:
            if h.subject in wanted:
                width[h.subject] = (h.value[2] / sp) if sp else None

    rows = []
    for r in reach["rows"]:
        wr = width.get(r["head"])
        wm = width.get(r["mates"][0])
        rows.append({"head": r["head"], "mate": r["mates"][0],
                     "head_width_spaces": round(wr, 3) if wr else None,
                     "mate_width_spaces": round(wm, 3) if wm else None,
                     "thin": None if (wr is None or wm is None)
                             else (wr < a.floor or wm < a.floor)})

    unmeasurable = [r for r in rows if r["thin"] is None]
    thin = [r for r in rows if r["thin"] is True]
    kept = [r for r in rows if r["thin"] is False]

    out = {
        "label": a.label or Path(a.record).name,
        "floor_staff_spaces": a.floor,
        "candidate_pairs": len(rows),
        "cells_with_a_measured_staff_space": len(spaces),
        "pairs_the_floor_REMOVES": len(thin),
        "pairs_the_floor_KEEPS": len(kept),
        "pairs_with_NO_measured_unit_and_so_UNJUDGED": len(unmeasurable),
        "removed": [r["head"] for r in thin],
        "kept": [r["head"] for r in kept],
        "rows": rows,
    }

    if a.adjudication:
        adj = json.loads(Path(a.adjudication).read_text())["verdicts"]
        man_p = Path(a.adjudication).parent / "out" / (
            "manifest-" + Path(a.adjudication).stem.split("-", 1)[1] + ".json")
        man = json.loads(man_p.read_text())
        by_head = defaultdict(list)
        for t in man["tiles"]:
            if t["stratum"] == "CANDIDATE" and t["id"] in adj:
                by_head[(t["subject"], t["mate"])].append(
                    adj[t["id"]]["verdict"])
        cross = {"removed": defaultdict(int), "kept": defaultdict(int),
                 "unjudged": defaultdict(int)}
        for r in rows:
            where = ("unjudged" if r["thin"] is None
                     else "removed" if r["thin"] else "kept")
            for v in by_head.get((r["head"], r["mate"]), []):
                cross[where][v] += 1
        out["against_the_print"] = {k: dict(v) for k, v in cross.items()}

    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
