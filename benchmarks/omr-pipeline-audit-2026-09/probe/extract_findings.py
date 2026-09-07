#!/usr/bin/env python3
"""Pull the recorded-refusal findings out of a transcription, reproducibly.

    python3 benchmarks/omr-pipeline-audit-2026-09/probe/extract_findings.py \
        OUT.json [OUT2.json ...] > findings.json

A recording sweep whose own findings are unreproducible undercuts its thesis, so
the numbers this branch reports in prose are extracted by THIS script from a
result JSON, and the committed extract names the command and the input that made
it. Four findings, one per recorded site:

  thin_key_majority      the cross-page key vote's share against `min_majority`
  thin_meter_margin      a staff's winning meter template against the runner-up
  midstaff_clef_flips    a LATER cell overturning the staff's inherited clef —
                         the population that was unrecorded before review, and
                         which `contest.disagrees` structurally cannot see
  clef_proposal_exits    where `propose_clef` actually returns

Everything here is read off keys this branch added. Nothing is recomputed, so
the extract cannot disagree with the run.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

#: `key_signature_vote.VoteConfig.min_majority` and
#: `TimeSignatureLocatorConfig.min_score` — quoted, not imported, so the extract
#: records the constants the run was judged against rather than today's.
MIN_MAJORITY = 0.5
MIN_METER_SCORE = 0.5


def staves(result):
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                yield page, staff


def findings(path: Path) -> dict:
    result = json.loads(path.read_text())
    out: dict = {"source": path.name, "thin_key_majority": [],
                 "thin_meter_margin": [], "midstaff_clef_flips": [],
                 "clef_proposal_exits": Counter()}

    seen_systems = set()
    for page, staff in staves(result):
        ks = staff.get("key_signature_evidence") or {}
        key = (page.get("page_index"), ks.get("system_index"))
        if ks.get("system_majority") is not None and key not in seen_systems:
            seen_systems.add(key)
            out["thin_key_majority"].append({
                "page": key[0], "system": key[1],
                "majority": ks["system_majority"],
                "min_majority": MIN_MAJORITY,
                "over_the_gate": round(ks["system_majority"] - MIN_MAJORITY, 4),
                "reference_fifths": ks.get("system_reference"),
                "vote_totals": ks.get("system_vote_totals"),
            })

        proposal = staff.get("clef_proposal_evidence")
        if proposal:
            out["clef_proposal_exits"][proposal.get("exit")] += 1

        for measure in staff.get("measures", []):
            contest = ((measure.get("clef_evidence") or {}).get("contest") or {})
            if not contest.get("overturns_inherited"):
                continue
            # `read_clef_rung_ran` separates the two populations: True is the
            # staff's OPENING cell replacing the positional default, which is
            # the pass working. False is a later cell moving a clef that was
            # already established — the flip.
            if contest.get("read_clef_rung_ran"):
                continue
            out["midstaff_clef_flips"].append({
                "page": page.get("page_index"),
                "staff": staff.get("staff_index"),
                "measure": measure.get("measure_index"),
                "from": contest.get("clef_in_effect_before"),
                "to": contest.get("clef_in_effect_after"),
                "on_confidence": contest.get("winner_confidence"),
                "n_resolved": contest.get("n_resolved"),
                # ⚠️ The reason `disagrees` cannot report this population.
                "has_disagrees_key": "disagrees" in contest,
            })

    for page in result.get("pages", []):
        for system, record in (page.get("header_meter_evidence") or {}).items():
            for staff_index, table in (record.get("staves") or {}).items():
                rows = table.get("scores") or []
                if not table.get("cleared_floor") or len(rows) < 2:
                    continue
                out["thin_meter_margin"].append({
                    "page": page.get("page_index"), "system": int(system),
                    "staff": int(staff_index),
                    "winner": rows[0]["raw"], "winner_score": rows[0]["score"],
                    "runner_up": rows[1]["raw"],
                    "runner_up_score": rows[1]["score"],
                    "margin": round(rows[0]["score"] - rows[1]["score"], 4),
                    "min_score": MIN_METER_SCORE,
                    "over_the_gate": round(rows[0]["score"] - MIN_METER_SCORE, 4),
                })
    out["thin_meter_margin"].sort(key=lambda r: r["margin"])
    out["clef_proposal_exits"] = dict(out["clef_proposal_exits"])
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    print(json.dumps([findings(Path(a)) for a in sys.argv[1:]], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
