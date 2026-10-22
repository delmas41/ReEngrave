"""What is wrong with our rests, per symbol, from the ledger's own rows.

Step 3. Every duration analysis in this repo before this one is note-level, so
the larger half of the duration mass has never been looked at.

⚠️ READ `side` BEFORE READING `attrs`. The ledger emits a row per symbol on
BOTH sides, so on a `truth`-side row `attrs` is the TRUTH and `partner_attrs`
is OURS. The first cut of this probe assumed `attrs` was always ours and
produced the confusion table backwards -- concluding we omitted `<type>` when
in fact we emit `<type>whole</type>` and truth omits it. Nothing in the column
names says which way round they are; the raw XML is what caught it.

⚠️ AND READ THE ASSESSABLE COUNT FIRST. On the scan gate only ~10% of rest
rows can be compared at all -- the rest are `uncorresponded` because the PART
JOIN failed, which is Step 4's problem sitting upstream of this one. A rest
figure quoted without that share is a figure about two pages.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ledger_dir", help="directory of symbol_ledger --json output")
    ap.add_argument("--family", default="rest")
    a = ap.parse_args()

    conf = collections.Counter()
    outcomes = collections.Counter()
    attrs_wrong = collections.Counter()
    n_rows = n_assessable = 0

    for f in sorted(glob.glob(os.path.join(a.ledger_dir, "*.json"))):
        d = json.load(open(f))
        rows = d["rows"] if isinstance(d, dict) and "rows" in d else d
        for r in rows:
            if r.get("family") != a.family:
                continue
            n_rows += 1
            outcomes[r["outcome"]] += 1
            if r["outcome"] != "uncorresponded":
                n_assessable += 1
            if r["outcome"] != "matched_attribute_error":
                continue
            for k in r.get("attrs_wrong", []):
                attrs_wrong[k] += 1
            if "duration_ql" not in r.get("attrs_wrong", []):
                continue
            own, par = r.get("attrs", {}), r.get("partner_attrs", {})
            # ⚠️ orient by side -- see the module docstring
            truth, ours = (own, par) if r["side"] == "truth" else (par, own)
            conf[((ours.get("type"), ours.get("duration_ql")),
                  (truth.get("type"), truth.get("duration_ql")))] += 1

    print(f"{a.family} rows {n_rows}, ASSESSABLE {n_assessable} "
          f"({n_assessable / n_rows:.1%})" if n_rows else "no rows")
    print("  outcomes:", dict(outcomes))
    print("  attributes wrong:", dict(attrs_wrong))
    print(f"\n  {'OURS (type, ql)':<26}{'TRUTH (type, ql)':<26}n")
    for (o, t), n in conf.most_common(15):
        print(f"  {str(o):<26}{str(t):<26}{n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
