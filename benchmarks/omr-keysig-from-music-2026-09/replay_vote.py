"""Replay the cross-page vote on RECORDED candidate lists.

`reconcile` is a pure function of its candidates, so the vote's own
contribution can be measured without re-running the model — which matters when
the tree is not pristine, as it was not on 2026-09-01 (another workstream held
uncommitted edits in `transcribe.py`, `export.py` and `voicing.py`, so an
end-to-end number taken then would not have been attributable to this change).

The candidate lists below were captured by `probe_vote_inputs.py` on `8c6452e`,
one field per column of its output. They are the pipeline's real inputs, not a
hypothetical.

    python3 benchmarks/omr-keysig-from-music-2026-09/replay_vote.py
    python3 benchmarks/omr-keysig-from-music-2026-09/replay_vote.py --defaulted-clef-weight-fix
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.key_signature_vote import StaffCandidate, reconcile  # noqa: E402

GT = json.loads((Path(__file__).resolve().parents[1] /
                 "omr-key-signature" / "ground_truth.json").read_text())


# (system, ordinal, fifths, weight, source) — probe_vote_inputs.py output.
# A source of "" means nothing read the staff.
BEET5_P15 = [
    (0, 0, None, 0.00, ""), (0, 1, None, 0.00, ""), (0, 2, None, 0.00, ""),
    (0, 3, None, 0.00, ""), (0, 4, None, 0.00, ""), (0, 5, None, 0.00, ""),
    (0, 6, None, 0.00, ""),
    (0, 7, -2, 0.50, "template_default_clef"),
    (0, 8, -1, 0.50, "template_default_clef"),
    (0, 9, None, 0.00, ""), (0, 10, None, 0.00, ""),
    (1, 0, None, 0.00, ""),
    (1, 1, -3, 0.50, "template_default_clef"),
    (1, 2, None, 0.00, ""), (1, 3, None, 0.00, ""), (1, 4, None, 0.00, ""),
    (1, 5, None, 0.00, ""), (1, 6, None, 0.00, ""),
    (1, 7, -3, 0.50, "template_default_clef"),
    (1, 8, -3, 0.50, "template_default_clef"),
    (1, 9, -1, 1.00, "detector"),
    (1, 10, -1, 1.00, "cv_locator"),
]

# How many accidentals each template_default_clef reading actually matched.
# `transcribe` throws this away — it substitutes a flat DEFAULTED_CLEF_WEIGHT
# of 0.5 regardless — which is the whole of the p.15 defect. Recovered here
# from |fifths|, which is what `len(matched_slots)` equals for a fit that
# inferred nothing.
BOLERO_P10 = [
    (0, 0, 4, 4.00, "detector"), (0, 1, 1, 1.00, "detector"),
    (0, 2, -1, 1.00, "template"), (0, 3, 2, 2.00, "detector"),
    (0, 4, None, 0.0, ""), (0, 5, None, 0.0, ""), (0, 6, None, 0.0, ""),
    (0, 7, -1, 1.00, "template"), (0, 8, -1, 1.00, "template"),
    (0, 9, None, 0.0, ""), (0, 10, None, 0.0, ""), (0, 11, None, 0.0, ""),
    (0, 12, None, 0.0, ""), (0, 13, None, 0.0, ""), (0, 14, None, 0.0, ""),
    (0, 15, None, 0.0, ""), (0, 16, None, 0.0, ""),
    (1, 0, 4, 4.00, "detector"), (1, 1, 1, 1.00, "detector"),
    (1, 2, -1, 1.00, "template"), (1, 3, 2, 2.00, "detector"),
    (1, 4, None, 0.0, ""), (1, 5, None, 0.0, ""), (1, 6, None, 0.0, ""),
    (1, 7, None, 0.0, ""), (1, 8, -1, 1.00, "template"),
    (1, 9, None, 0.0, ""), (1, 10, None, 0.0, ""), (1, 11, None, 0.0, ""),
    (1, 12, None, 0.0, ""), (1, 13, None, 0.0, ""), (1, 14, None, 0.0, ""),
    (1, 15, None, 0.0, ""), (1, 16, None, 0.0, ""),
]

# Boléro is not a ground-truth page in benchmarks/omr-key-signature; its truth
# is read off the engraving in crops/bolero_p10_sys0_headers.png. Staves not
# listed print no signature.
BOLERO_TRUTH = {0: 4, 1: 1, 2: 0, 3: 2, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0,
                9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0, 16: 0}

DEFAULTED_CLEF_WEIGHT = 0.5


def build(rows, weight_fix: bool) -> list[StaffCandidate]:
    out = []
    for system, ordinal, fifths, weight, source in rows:
        if weight_fix and source == "template_default_clef" and fifths:
            # The proposed one-line change in transcribe.py: DISCOUNT the
            # accidental count for a guessed clef instead of REPLACING it.
            weight = abs(fifths) * DEFAULTED_CLEF_WEIGHT
        out.append(StaffCandidate(
            staff_index=system * 100 + ordinal, system_index=system,
            ordinal=ordinal, fifths=fifths, weight=weight, source=source,
            can_carry=not source.startswith("template"),
        ))
    return out


def tally(rows):
    """The scoring in benchmarks/omr-key-signature/eval_key_signatures.py."""
    out = {"correct": 0, "wrong": 0, "missed": 0, "abstained_correctly": 0}
    for truth, read in rows:
        if read is None or read == 0:
            out["abstained_correctly" if truth == 0 else "missed"] += 1
        elif read == truth:
            out["correct"] += 1
        else:
            out["wrong"] += 1
    return out


def score(name, rows, truth_by_ordinal, weight_fix: bool):
    cands = build(rows, weight_fix)
    result = reconcile(cands)
    scored = [(truth_by_ordinal[c.ordinal], result.fifths_for(c.staff_index))
              for c in cands if c.ordinal in truth_by_ordinal]
    t = tally(scored)
    ref = {k: v for k, v in result.reference_written_by_system.items()}
    print(f"  {name:<28} correct={t['correct']:<3} wrong={t['wrong']:<3} "
          f"missed={t['missed']:<3} correct-abstentions={t['abstained_correctly']:<3} "
          f"reference={ref}")
    return t, result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    p15 = {s["ordinal"]: s["fifths"]
           for pg in GT["pages"] if pg["id"] == "beet5-p15"
           for s in pg["staves"]}

    for label, rows, truth in (("beet5-p15", BEET5_P15, p15),
                               ("bolero-p10", BOLERO_P10, BOLERO_TRUTH)):
        print(f"\n=== {label} — vote replayed on recorded candidates ===")
        _, r_off = score("vote only", rows, truth, weight_fix=False)
        _, r_on = score("+ defaulted-clef weight fix", rows, truth, weight_fix=True)
        if args.verbose:
            for c in build(rows, False):
                if c.fifths is None:
                    continue
                a, b = r_off.verdicts[c.staff_index], r_on.verdicts[c.staff_index]
                print(f"      sys{c.system_index}/ord{c.ordinal:<2} read={c.fifths:+d} "
                      f"w={c.weight:.2f} {c.source[:22]:<22} "
                      f"| {a.action:<8} -> {b.action:<8} | {b.reason[:52]}")


if __name__ == "__main__":
    main()
