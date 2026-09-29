"""ROADMAP 2.6c (second half) — base vs arm, subject by subject, on ONE saved
record: two `readjudicate_owner_2_6c.py --dump` files, one run from the
base tree (8100c9ff, extracted with `git archive`) and one from this branch,
over the SAME record (CLAUDE.md §6b: base vs arm on one record, every change
attributed).

    python3 benchmarks/omr-owner-domain-2026-09/diff_base_arm_2_6c.py \
        <base-dump.json> <arm-dump.json>
"""
from __future__ import annotations

import json
import sys
from collections import Counter


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    base = json.load(open(argv[0]))
    arm = json.load(open(argv[1]))
    out = {}
    for q in ("glyph_owner", "notehead_is_not_a_notehead"):
        b, a = base[q], arm[q]
        keys = sorted(set(b) | set(a))
        same = sum(1 for k in keys if b.get(k) == a.get(k))
        trans = Counter()
        value_changed = Counter()
        for k in keys:
            if b.get(k) == a.get(k):
                continue
            bo, ao = b.get(k) or [None] * 3, a.get(k) or [None] * 3
            trans[f"{bo[2]}->{ao[2]}"] += 1
            if bo[1] != ao[1]:
                value_changed[f"{bo[2]}->{ao[2]}"] += 1
        out[q] = {"subjects": len(keys), "identical": same,
                  "changed": len(keys) - same,
                  "value_changed": sum(value_changed.values()),
                  "value_changed_by_reason": dict(value_changed.most_common()),
                  "transitions": dict(trans.most_common())}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
