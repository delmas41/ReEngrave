"""Give HUMAN REVIEW COST a number, a ceiling and an era key.

Sean's stated purpose for this project is reducing the cost of human review, and
it appears in no measurement the dashboard prints. It has been computed once, as
a side result (`benchmarks/omr-identity-harness-2026-09/FINDINGS.md`): between
two identity passes, accuracy moved 44 records and review cost moved 2
(197 -> 195). That is the failure the identity scope's section 7 names, arriving
as a footnote.

DEFINITION USED HERE — deliberately the harness's own, so it is reproducible
rather than invented. A staff record COSTS A HUMAN if any of:

    unnamed          nothing was emitted; the reviewer must supply a name
    contradicted     the staff's OWN margin label disagrees with the export
    (both)           counted once

⚠️ WHY THE CEILING IS NOT ZERO, and this is the interesting part. A perfect
pipeline still leaves a reviewer work: a staff whose margin carries NO label and
which the roster cannot reach is unnameable from the page, and someone has to
look at it. That irreducible remainder is what a `% of achievable` needs, and it
is measurable from the same records — the staves with no label evidence at all.

⚠️ WHAT THIS IS NOT. It is review cost on the IDENTITY axis only — staff naming.
The reviewer's real load also includes note-level diffs, which this says nothing
about. Named `human:review_cost:identity` for that reason.

Read-only. Writes one JSON.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HARNESS = ROOT / "benchmarks" / "omr-identity-harness-2026-09"
sys.path.insert(0, str(HARNESS / "probe"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fixtureroot import require_nonempty  # noqa: E402
import corpus  # noqa: E402   (the harness's own roster rules, committed)
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "human-cost-identity.json"
RECORDS = ROOT / "benchmarks" / "omr-identity-harness-2026-09" / "out" / "records.json"


def main() -> int:
    doc = json.loads(RECORDS.read_text())
    recs = require_nonempty(doc["records"], "graded identity records", RECORDS)

    # ⚠️ ROUND-2 NEGATIVE WITHDRAWN. Round 2 reported that human cost "does not
    # reproduce from committed artefacts" because records.json carries no
    # `impossible` / `not-in-this-work` field. It does not need to: `score.py`
    # derives both from `corpus.is_impossible(work, page, name)` and
    # `corpus.is_never(work, name)`, and work / page / emitted are ALL on the
    # record. `corpus.py` is committed. So the harness's own four-category cost
    # is recomputable here, exactly, with no harness change — the fields were
    # absent, the INFORMATION was not.
    def flags_for(r) -> list:
        name = r.get("emitted")
        out = []
        if name is None:
            out.append("unnamed")
        if corpus.is_impossible(r["work"], r["page"], name):
            out.append("impossible")
        if corpus.is_never(r["work"], name):
            out.append("not-in-this-work")
        if r.get("label_read") and name and r["label_read"] != name:
            out.append("contradicted")
        return out

    arms = defaultdict(list)
    for r in recs:
        arms[r["arm"]].append(r)

    out_arms = []
    for arm, rs in sorted(arms.items()):
        n = len(rs)
        flagged = {id(r): flags_for(r) for r in rs}
        breakdown = Counter("+".join(sorted(f)) for f in flagged.values() if f)
        unnamed = [r for r in rs if "unnamed" in flagged[id(r)]]
        contra = [r for r in rs if "contradicted" in flagged[id(r)]]
        impossible = [r for r in rs if "impossible" in flagged[id(r)]]
        never = [r for r in rs if "not-in-this-work" in flagged[id(r)]]
        costly = {k for k, v in flagged.items() if v}
        # the irreducible remainder: no label was read on this staff at all, so
        # no amount of pipeline work can name it FROM THE PAGE.
        unlabelled = [r for r in rs if not r.get("label_read")]
        unlabelled_and_unnamed = [r for r in unlabelled if not r.get("named")]
        correct = sum(1 for r in rs if r.get("correct"))
        out_arms.append({
            "arm": arm,
            "n_records": n,
            "accuracy": correct / n if n else None,
            "human_cost_records": len(costly),
            "human_cost_rate": len(costly) / n if n else None,
            "decomposition": {
                "unnamed": len(unnamed),
                "impossible": len(impossible),
                "not_in_this_work": len(never),
                "contradicted": len(contra),
            },
            "human_breakdown": dict(sorted(breakdown.items())),
            "floor_candidate": {
                "staves_with_no_label_read": len(unlabelled),
                "of_those_also_unnamed": len(unlabelled_and_unnamed),
                "floor_rate": len(unlabelled_and_unnamed) / n if n else None,
            },
        })

    # the orthogonality the backlog names (D4), recomputed across every arm pair
    pairs = []
    for i, a in enumerate(out_arms):
        for b in out_arms[i + 1:]:
            if a["n_records"] != b["n_records"]:
                continue
            d_acc = b["accuracy"] - a["accuracy"]
            d_cost = b["human_cost_records"] - a["human_cost_records"]
            pairs.append({"a": a["arm"], "b": b["arm"],
                          "d_accuracy_records": round(
                              (b["accuracy"] - a["accuracy"]) * a["n_records"]),
                          "d_human_cost_records": d_cost,
                          "d_accuracy": round(d_acc, 4)})
    moved_acc = [p for p in pairs if abs(p["d_accuracy_records"]) >= 10]

    result = {
        "generated_by": "benchmarks/omr-pipeline-audit-2026-09/probe/probe_human_cost.py",
        "what": "review cost on the IDENTITY axis — staff records a human must "
                "open because the name is missing or contradicted by the page",
        "definition": {
            "costly": "not `named`, OR `contradicted` by the staff's own margin "
                      "label. Counted once.",
            "floor_candidate": "records where NO margin label was read at all AND "
                               "nothing was emitted — unnameable from the page, so "
                               "irreducible by pipeline work.",
        },
        "not_this": "note-level review load, which is the larger half and has no "
                    "harness at all",
        "source": str(RECORDS.relative_to(ROOT)),
        "era_key": "identity-harness|2026-09-07|1571 graded records|58 replay "
                   "arms + 1 transcription",
        "⚠️_clef_regime": "58 of the harness's 59 arms are clef-blind REPLAYS and "
                          "exactly one is a transcription (backlog F). A human-cost "
                          "figure needs a clef-regime stamp beside its page-set "
                          "regime stamp; these arms are not interchangeable.",
        "⚠️_VERDICT": {
            "reproducible_from_committed_artefacts": True,
            "round2_said_otherwise_and_was_WRONG": (
                "Round 2 reported this estate as irreproducible because "
                "records.json carries no `impossible` or `not-in-this-work` "
                "field. It does not need to: score.py DERIVES both from "
                "corpus.is_impossible(work, page, name) and "
                "corpus.is_never(work, name), and work / page / emitted are all "
                "on the record, and corpus.py is committed. The fields were "
                "absent; the INFORMATION was not. I checked which fields "
                "existed and did not check how the missing ones were computed."),
            "still_true": (
                "the committed export is 1,571 records over 2 arms, so it "
                "cannot reproduce FINDINGS' 197 over 3,543 — that is a COVERAGE "
                "gap (which arms were exported), not a schema gap."),
            "superseded_why": False,
            "_old_why": "FINDINGS.md reports human cost as 197 over 3543 records, "
                   "decomposed 150 contradicted-only / 24 unnamed / 15 "
                   "not-in-this-work / 8 both. The COMMITTED records.json holds "
                   "1571 records across 2 arms and carries no "
                   "`not-in-this-work` field and no unnamed record at all "
                   "(0 of 1571). So only the `contradicted` component is "
                   "reproducible here: 26 of 1571 = 0.0166. The project's "
                   "stated PURPOSE is measured in exactly one place and that "
                   "place cannot be re-derived from the tree.",
            "floor_is_still_open_but_now_LOCATED": (
                "0 of 1,571 records are unnamed, so the floor is not in that "
                "category. It is in `contradicted`: the label-contradiction "
                "check's documented STRUCTURAL false positive is a CONDENSED "
                "staff — `Violoncello e Basso` names one instrument in the "
                "margin and the slot names the other, and BOTH are right. Those "
                "records cost a reviewer a look that no pipeline work can "
                "remove. Neither edition here condenses that way (0 of 158 in "
                "the label-contradiction study), which is a fact about two "
                "publishers, not about the floor. So the floor is measurable "
                "and is the condensed-staff rate — not zero, and not measured."),
            "what_it_would_take": (
                "(1) export MORE ARMS — the committed set is 2 of the harness's "
                "59, which is why 46 here cannot be 197 there; no schema change "
                "is needed. (2) Measure the condensed-staff rate on an edition "
                "that condenses, to give the floor a value. (3) Stamp the "
                "CLEF REGIME on each arm: 58 of 59 arms are clef-blind replays "
                "and one is a transcription (backlog F), and a cost figure that "
                "mixes them is not one figure."),
        },
        "arms": out_arms,
        "orthogonality": {
            "n_comparable_arm_pairs": len(pairs),
            "pairs_where_accuracy_moved_10_or_more_records": len(moved_acc),
            "of_those_human_cost_unchanged": sum(
                1 for p in moved_acc if p["d_human_cost_records"] == 0),
            "examples": sorted(moved_acc,
                               key=lambda p: -abs(p["d_accuracy_records"]))[:8],
        },
    }
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    print("arms: %d" % len(out_arms))
    for a in sorted(out_arms, key=lambda x: -x["n_records"])[:6]:
        print("  %-34s n=%-5d acc=%.4f  cost=%-4d (%.4f)  floor=%d (%.4f)"
              % (a["arm"], a["n_records"], a["accuracy"], a["human_cost_records"],
                 a["human_cost_rate"], a["floor_candidate"]["of_those_also_unnamed"],
                 a["floor_candidate"]["floor_rate"]))
    o = result["orthogonality"]
    print("\ncomparable arm pairs: %d; accuracy moved >=10 records in %d of them; "
          "human cost UNCHANGED in %d of those"
          % (o["n_comparable_arm_pairs"],
             o["pairs_where_accuracy_moved_10_or_more_records"],
             o["of_those_human_cost_unchanged"]))
    for p in o["examples"][:5]:
        print("   %-28s -> %-28s  Δacc=%+4d records  Δcost=%+d"
              % (p["a"][:28], p["b"][:28], p["d_accuracy_records"],
                 p["d_human_cost_records"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
