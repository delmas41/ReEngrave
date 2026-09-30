"""ROADMAP 2.36: measure the REACH of "a chord's members share one stem and
one duration" against a committed acceptance record, BEFORE building it
(CLAUDE.md rule 5: reach before accuracy).

For every NARROWED `Q.DURATION` verdict (notes only), asks: is there another
glyph in the SAME cell whose duration verdict is DECIDED and whose `used`
tuple names the exact SAME `Q.STEM` observation id? (`used`, never
`considered`/`basis` -- `adjudicate_duration` fills those with EVERY stem in
the cell, and only `used` narrows to the ones this glyph's own head box
actually overlapped -- see `rhythm._stem_joined`.)

Read-only, one JSON parse, no re-gather.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path


def cell_key(subject: str) -> str:
    parts = subject.split("/")
    return "/".join(parts[:5])   # glyph/p/s/st/c -> drop the glyph index


def measure(path: str, label: str) -> dict:
    t0 = time.time()
    data = json.loads(Path(path).read_text())
    rec = data["record"]
    t_parsed = time.time()

    stem_ids = {o["id"] for o in rec["observations"] if o["quantity"] == "stem"}
    t_stems = time.time()

    duration_verdicts = [v for v in rec["verdicts"] if v["quantity"] == "duration"]
    by_cell = collections.defaultdict(list)
    for v in duration_verdicts:
        by_cell[cell_key(v["subject"])].append(v)
    t_grouped = time.time()

    def is_rest(v):
        if isinstance(v.get("value"), dict):
            return bool(v["value"].get("is_rest"))
        return any(isinstance(c.get("value"), dict) and c["value"].get("is_rest")
                   for c in (v.get("candidates") or ()))

    def stems_of(v):
        return {rid for rid in v.get("used") or () if rid in stem_ids}

    n_narrowed_notes = 0
    n_with_own_stem = 0
    n_with_decided_mate = 0
    n_with_unique_decided_mate = 0
    n_mate_level_admitted = 0
    reasons_resolved = collections.Counter()
    examples = []

    for cell, verdicts in by_cell.items():
        narrowed = [v for v in verdicts
                    if v["outcome"] == "narrowed" and not is_rest(v)]
        decided = [v for v in verdicts
                   if v["outcome"] == "decided" and not is_rest(v)]
        if not narrowed:
            continue
        decided_stems = [(v, stems_of(v)) for v in decided]
        decided_stems = [(v, s) for v, s in decided_stems if s]
        for n in narrowed:
            n_narrowed_notes += 1
            n_stems = stems_of(n)
            if not n_stems:
                continue
            n_with_own_stem += 1
            mates = [v for v, s in decided_stems if s & n_stems]
            if not mates:
                continue
            n_with_decided_mate += 1
            if len(mates) != 1:
                continue
            n_with_unique_decided_mate += 1
            mate = mates[0]
            mate_level = (mate.get("value") or {}).get("beam_levels")
            admitted = [c for c in (n.get("candidates") or [])
                        if isinstance(c.get("value"), dict)
                        and c["value"].get("beam_levels") == mate_level]
            if len(admitted) == 1:
                n_mate_level_admitted += 1
                reasons_resolved[n["reason"]] += 1
                if len(examples) < 5:
                    examples.append({
                        "narrowed_subject": n["subject"],
                        "narrowed_reason": n["reason"],
                        "mate_subject": mate["subject"],
                        "mate_beam_levels": mate_level,
                    })

    return {
        "label": label,
        "n_narrowed_notes": n_narrowed_notes,
        "n_with_own_stem_in_used": n_with_own_stem,
        "n_with_a_decided_stem_mate": n_with_decided_mate,
        "n_with_a_UNIQUE_decided_stem_mate": n_with_unique_decided_mate,
        "n_where_mate_level_is_one_of_its_own_candidates (WOULD BE DECIDED)":
            n_mate_level_admitted,
        "by_reason_resolved": reasons_resolved.most_common(),
        "examples": examples,
        "timing_s": {
            "json_parse": round(t_parsed - t0, 1),
            "collect_stem_ids": round(t_stems - t_parsed, 1),
            "group_by_cell": round(t_grouped - t_stems, 1),
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", required=True)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    report = measure(args.record, args.label)
    text = json.dumps(report, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text)
        print(f"wrote {args.out}", file=sys.stderr)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
