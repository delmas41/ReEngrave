"""Tally the print pass -- DERIVED from the manifests and the adjudications.

⚠️ THE STRATUM COMES FROM THE MANIFEST, NEVER FROM THE ADJUDICATION FILE. The
adjudication is written against opaque tile ids with no stratum in it, which is
what makes the pass blind; joining them here is the only place the two meet, and
doing it in code rather than by hand is what stops a control being scored as a
candidate by accident.

⚠️ IT REFUSES A TILE IT CANNOT PLACE (`--check` exits non-zero), because a tile
adjudicated but absent from the manifest, or written but not adjudicated, is a
gap in a CENSUS and a census with a gap is a sample.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

#: A verdict that says the ink is not two noteheads at all. ⚠️ KEPT APART FROM
#: `separate_stems`: one says the rule joined two things that are not a chord,
#: the other says it joined two things that are not NOTES, and the repairs are
#: in different stages.
NOT_A_HEAD = ("red_is_not_a_notehead", "blue_is_not_a_notehead")


def load(bench: Path, label: str):
    man = json.loads((bench / "out" / f"manifest-{label}.json").read_text())
    adj = json.loads((bench / f"ADJUDICATION-{label}.json").read_text())
    return man, adj


def tally(man, adj):
    stratum = {t["id"]: t["stratum"] for t in man["tiles"]}
    v = adj["verdicts"]
    missing = sorted(set(stratum) - set(v))
    extra = sorted(set(v) - set(stratum))
    out = {"CANDIDATE": Counter(), "CONTROL": Counter()}
    for tid, rec in v.items():
        if tid in stratum:
            out[stratum[tid]][rec["verdict"]] += 1
    return out, missing, extra


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--labels", nargs="+", default=["litolff", "breitkopf"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    bench = Path(a.bench)
    report, problems = {}, []
    pooled = {"CANDIDATE": Counter(), "CONTROL": Counter()}
    for label in a.labels:
        man, adj = load(bench, label)
        counts, missing, extra = tally(man, adj)
        if missing:
            problems.append(f"{label}: {len(missing)} written but NOT "
                            f"adjudicated: {missing}")
        if extra:
            problems.append(f"{label}: {len(extra)} adjudicated but NOT in the "
                            f"manifest: {extra}")
        report[label] = {
            "written": man["written"], "refused": len(man["refused"]),
            "refusal_reasons": [r["why"] for r in man["refused"]],
            "CANDIDATE": dict(counts["CANDIDATE"]),
            "CONTROL": dict(counts["CONTROL"]),
        }
        for k in pooled:
            pooled[k] += counts[k]

    cand, ctrl = pooled["CANDIDATE"], pooled["CONTROL"]
    settled = sum(v for k, v in cand.items() if k != "cannot_tell")
    not_head = sum(cand[k] for k in NOT_A_HEAD if k in cand)
    report["POOLED"] = {
        "CANDIDATE": dict(cand), "CONTROL": dict(ctrl),
        "candidates": sum(cand.values()),
        "candidates_the_print_SETTLES": settled,
        "candidates_that_are_a_REAL_CHORD": cand.get("one_shared_stem", 0),
        "candidates_that_are_NOT_TWO_NOTEHEADS": not_head,
        "candidates_that_are_TWO_SEPARATE_NOTES":
            cand.get("separate_stems", 0),
        "share_of_settled_that_is_a_real_chord":
            round(cand.get("one_shared_stem", 0) / settled, 4) if settled else None,
        "controls": sum(ctrl.values()),
        "controls_correct": ctrl.get("one_shared_stem", 0),
        "controls_WRONG": sum(v for k, v in ctrl.items()
                              if k not in ("one_shared_stem", "cannot_tell")),
    }
    print(json.dumps(report, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(report, indent=1))
    for p in problems:
        print(f"⚠️ {p}", file=sys.stderr)
    if a.check:
        if problems:
            return 2
        # ⚠️ A POSITIVE CONTROL ON THE CONTROLS THEMSELVES. If no control was
        # adjudicated `one_shared_stem` the pass did not establish that the
        # question is answerable, and no candidate verdict means anything.
        if report["POOLED"]["controls_correct"] == 0:
            print("⚠️ DEAD: not one control was adjudicated a shared stem",
                  file=sys.stderr)
            return 2
        if report["POOLED"]["controls_WRONG"]:
            print("⚠️ a CONTROL adjudicated against the record -- the marking "
                  "or the question is wrong", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
