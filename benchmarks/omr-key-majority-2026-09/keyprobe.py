"""What a staged record says about the key signature, per system per staff.

Run from the repo root:  python3 benchmarks/omr-key-majority-2026-09/keyprobe.py <record.json>

⚠️ Reads the record ONLY through `record_io.load_record` (CLAUDE.md, record
pools): a record file is pooled and `json.loads` alone returns ids, not rows.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr.staged.record_io import load_record  # noqa: E402


def subject_fields(key: str):
    head, *rest = key.split("/")
    nums = [int(x) if x.isdigit() else None for x in rest]
    while len(nums) < 4:
        nums.append(None)
    return head, nums[0], nums[1], nums[2], nums[3]


def main(path: str) -> None:
    r = load_record(path)
    rec = r["record"]
    obs, abst, verds = rec["observations"], rec["abstentions"], rec["verdicts"]
    prov = r["provenance"]
    print(f"== {path}")
    print(f"provenance commit={prov['commit'][:8]} dirty={prov['dirty']}")

    kv = [v for v in verds if v["quantity"] == "key_signature"]
    print(f"key_signature verdicts: {len(kv)}")
    print("  outcomes:", dict(collections.Counter(v["outcome"] for v in kv)))
    print("  reasons :", dict(collections.Counter(v.get("reason") for v in kv)))
    print("  values  :", dict(collections.Counter(str(v.get("value")) for v in kv)))

    dom = [(o["subject"], o["value"]) for o in obs if o["quantity"] == "input_domain"]
    print("input_domain rows:", dom[:4] or "NONE")

    for q in ("keysig_clef_fit", "keysig_template_fit", "keysig_marker",
              "keysig_run_position"):
        rows = [o for o in obs if o["quantity"] == q]
        print(f"{q}: {len(rows)} rows")
        if rows:
            print("   sample:", json.dumps(rows[0], default=str)[:260])

    # markers per staff vs the decided |fifths|
    marks = collections.Counter()
    for o in obs:
        if o["quantity"] == "keysig_marker":
            _, p, s, st, _ = subject_fields(o["subject"])
            marks[(p, s, st)] += 1
    agree = disagree = 0
    for v in kv:
        if v["outcome"] != "decided" or v.get("value") is None:
            continue
        _, p, s, st, _ = subject_fields(v["subject"])
        n = marks.get((p, s, st), 0)
        if n == abs(int(v["value"])):
            agree += 1
        else:
            disagree += 1
    print(f"decided staves whose marker count == |fifths|: {agree}; "
          f"disagreeing: {disagree}")


if __name__ == "__main__":
    main(sys.argv[1])
