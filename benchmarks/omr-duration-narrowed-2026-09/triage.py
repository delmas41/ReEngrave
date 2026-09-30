"""ROADMAP 2.36: triage every NARROWED `Q.DURATION` verdict in a committed
acceptance record.

Read-only. Loads the record file directly (the same JSON `Log.to_json`
writes, per `tools.omr.staged.record_io`) and tabulates, per verdict:

  (a) the candidate SET -- the distinct written durations a narrowing offers,
      named by ear (quarter/eighth/...) where the value matches a plain note
      length, else reported as a raw beat count;
  (b) the `reason` (which branch of `adjudicate_duration` / `_rest_ruling`
      produced it);
  (c) which reader rows disagree -- read from the verdict's own `detail`
      (`beam_evidence`, `flag_level_votes`, `levels_certain`/`levels_possible`,
      `head_fill`, `slot_says`/`slot_prefers`, ...), the same fields
      `adjudicate_duration`'s docstring calls out as the fragile inputs.

Does NOT call `record_io.expand_id_lists` / `load_record`: `reason`,
`candidates` and `detail` are never pooled (only `considered`/`basis`/
`correlated` are, per `record_io.py`'s own docstring), so this tabulation
needs no pool expansion -- one fewer full walk over every verdict in a
465 MB / 3.1 GB file.

No re-gather, no re-adjudication: `json.loads` of the committed file, once.

    python3 benchmarks/omr-duration-narrowed-2026-09/triage.py <record.json> --label litolff
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

NOTE_NAMES = {
    4.0: "whole", 2.0: "half", 1.0: "quarter", 0.5: "eighth",
    0.25: "16th", 0.125: "32nd", 0.0625: "64th",
    6.0: "dotted-whole", 3.0: "dotted-half", 1.5: "dotted-quarter",
    0.75: "dotted-eighth", 0.375: "dotted-16th",
}


def _name(written) -> str:
    try:
        w = float(written)
    except (TypeError, ValueError):
        return str(written)
    return NOTE_NAMES.get(round(w, 6), f"beats={w:g}")


def _candidate_set(v) -> str:
    names = []
    for c in v.get("candidates") or ():
        val = c.get("value") or {}
        names.append(_name(val.get("written")))
    # first-listed is the reader's own top candidate (Candidate ordering is
    # the whole claim, per every comment above `Ruling.narrow` in rhythm.py)
    return "{" + ", ".join(names) + "}"


def _disagreement_key(v) -> str:
    """One short string naming WHICH witnesses disagree, from the verdict's
    own `detail` -- never re-derived from raster."""
    reason = v.get("reason")
    d = v.get("detail") or {}
    if reason == "flags_disagree":
        votes = d.get("flag_level_votes") or {}
        return f"flag_boxes_disagree(levels={sorted(votes.keys())})"
    if reason == "beams_ambiguous":
        return (f"beam_count_certain={d.get('levels_certain')}_"
                f"possible={d.get('levels_possible')}")
    if reason == "beam_discounted_uncertain":
        return "beam_discounted_by_2.25b(neighbour_or_arc)"
    if reason == "flag_ink_unread":
        return "stem_tip_ink_says_flag_but_no_box"
    if reason == "head_fill_from_ink":
        return f"notehead_ink_vs_detector_class(fill={d.get('notehead_ink')})"
    if reason == "rest_slot_contradicts_class":
        return f"rest_slot_vs_detector_class(slot_prefers={d.get('slot_prefers')})"
    return f"other:{reason}"


def triage(path: str, label: str) -> dict:
    t0 = time.time()
    data = json.loads(Path(path).read_text())
    rec = data["record"]
    t_parsed = time.time()
    duration_verdicts = [v for v in rec["verdicts"] if v["quantity"] == "duration"]
    t_filtered = time.time()

    narrowed = [v for v in duration_verdicts if v["outcome"] == "narrowed"]
    decided = [v for v in duration_verdicts if v["outcome"] == "decided"]

    by_reason = collections.Counter(v["reason"] for v in narrowed)
    by_candset = collections.Counter(_candidate_set(v) for v in narrowed)
    by_disagreement = collections.Counter(_disagreement_key(v) for v in narrowed)
    # cross: reason x is-rest
    rests = sum(1 for v in narrowed
                if (v.get("candidates") or [{}])[0].get("value", {}).get("is_rest"))
    notes = len(narrowed) - rests

    top_examples = collections.defaultdict(list)
    for v in narrowed:
        key = v["reason"]
        if len(top_examples[key]) < 3:
            top_examples[key].append(
                {"subject": v["subject"], "candidates": _candidate_set(v),
                 "disagreement": _disagreement_key(v)})

    report = {
        "label": label,
        "path": path,
        "n_duration_verdicts": len(duration_verdicts),
        "n_decided": len(decided),
        "n_narrowed": len(narrowed),
        "n_narrowed_notes": notes,
        "n_narrowed_rests": rests,
        "by_reason": by_reason.most_common(),
        "by_candidate_set": by_candset.most_common(20),
        "by_disagreement_class": by_disagreement.most_common(20),
        "examples_by_reason": dict(top_examples),
        "timing_s": {
            "json_parse": round(t_parsed - t0, 1),
            "filter_duration_rows": round(t_filtered - t_parsed, 1),
        },
    }
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record", help="path to a committed acceptance record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", help="write JSON report here")
    args = ap.parse_args(argv)

    report = triage(args.record, args.label)
    text = json.dumps(report, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text)
        print(f"wrote {args.out}", file=sys.stderr)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
