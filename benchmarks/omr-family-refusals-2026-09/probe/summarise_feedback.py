"""The committable summary of a 24 MB `feedback.json` — ROADMAP 3.4g.

    python3 .../summarise_feedback.py <out dir>

⚠️ THE SAME SHAPE `benchmarks/omr-stage-review-2026-09/out/sean-viola-p3/
feedback-summary.json` ALREADY HAS, so the before and after are comparable
row for row rather than by eye. `feedback.json` itself is ~24 MB and is
gitignored; this is what §3 of the FINDINGS quotes.

⚠️ IT SUMMARISES AND DOES NOT RECOMPUTE. `weighed_by` is the one field this
has to build rather than lift, because `feedback.json` carries the full
verdict rows and the summary carries their shape; it is built from
`how_the_human_row_reached_it == "used"`, which is the field `rerun.py` and
`feedback.py` both use to separate OFFERED from WEIGHED. Every other number
is copied from the file `rerun.py` wrote — a second derivation beside it is
how a report comes to disagree with the run it reports on.
"""
import collections
import json
import sys
from pathlib import Path


def main() -> int:
    out = Path(sys.argv[1])
    d = json.loads((out / "feedback.json").read_text())
    per_action = {}
    for aid, a in d["actions"].items():
        act = a.get("action") or {}
        weighed = collections.Counter()
        named = collections.Counter()
        for v in a.get("verdicts_that_named_it") or ():
            key = str(v.get("decider", "")).replace("adjudicate_", "")
            named[key] += 1
            if v.get("how_the_human_row_reached_it") == "used":
                weighed[key] += 1
        per_action[aid] = {
            "kind": act.get("kind"),
            "subject": act.get("subject"),
            "category": act.get("category"),
            "staff": act.get("staff"),
            "weighed_by": sorted(weighed.items()),
            "named_by": sorted(named.items()),
            "reached_nothing": a.get("reached_nothing"),
        }
    summary = {
        "counts": d["counts"],
        "per_stage": d["per_stage"],
        "export": d["export"],
        "reached_nothing": d["reached_nothing"],
        "per_action": per_action,
    }
    dest = out / "feedback-summary.json"
    dest.write_text(json.dumps(summary, indent=1, default=str))
    print("wrote", dest, "| reached_nothing", len(d["reached_nothing"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
