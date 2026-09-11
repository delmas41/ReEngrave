"""WHY does identity abstain on 75 of 75? A gatherer gap and a reader gap are
different repairs, and both look like an absent name to the join.

⚠️ This asks the ABSTENTION rows, not the verdicts. `margin_label` has zero
verdicts and 75 abstentions; the reason on those rows says whether the page was
read and found nothing, or was never read at all.
"""

from __future__ import annotations

import collections
import json
import sys


def main(path: str) -> int:
    d = json.load(open(path))
    rec = d["record"]

    print("--- abstention rows, by quantity (top 25)")
    c = collections.Counter(a["quantity"] for a in rec["abstentions"])
    for k, n in c.most_common(25):
        print("   %-28s %5d" % (k, n))

    for name in ("margin_label", "text_layer", "roster_entry"):
        rows = [a for a in rec["abstentions"] if a["quantity"] == name]
        print("\n--- %s: %d abstention rows" % (name, len(rows)))
        print("    reasons", dict(collections.Counter(
            r.get("reason") for r in rows)))
        if rows:
            print("    example:", json.dumps(rows[0])[:600])

    obs = collections.Counter(o["quantity"] for o in rec["observations"])
    print("\n--- observation rows for identity-ish quantities")
    for k in sorted(obs):
        if any(w in k for w in ("label", "text", "roster", "staff", "system")):
            print("   %-28s %5d" % (k, obs[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else "library/_shared-records/beethoven5-p1-p4.record.json"))
