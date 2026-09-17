"""A NAMED class's geometry in the store is a MIXTURE, unless you split it.

⚠️⚠️ **AN INK ROW'S `memberships` PUT THE MERGED BLOB'S GEOMETRY INTO THE
NAMED CLASS'S DISTRIBUTION.** `Q.INK` carries `ink_explained_by`, the classes
whose detections overlap a blob, and `entries_from_record` turns those into
`memberships` exactly as it does a detection's own class. So a blob five to
seven staff spaces tall, explained by `noteheadBlackOnLine`, lands in the
notehead HEIGHT distribution beside real 1.3-space noteheads.

Found 2026-09-17 by a cross-publisher query whose `mean_h` column read 3.646
for Litolff noteheads against 1.199 for Breitkopf's -- and a notehead is one
staff space tall, so the larger number is not a fact about a plate.

**What it is NOT.** Not a bug in `height_spaces`: split on `source_quantity`
the two publishers AGREE to about a tenth of a space, which is also the
positive control that the two records are comparable at all. Not a schema
gap either -- `source_quantity` is on every entry. It is a QUERY DISCIPLINE,
and `positional_store --ask` does not apply it, so the first conditioning
query anyone runs is the misleading one.

⚠️ **It is the MERGE the ink findings already record** (*"Litolff MERGES …
the median Litolff cell's largest component holds 46% of its ink"*, with
`ink_n_components` / `ink_share_of_cell` carried as a MERGE WARNING) --
arriving in a consumer, which is where it costs something.

⚠️ **And it CONFOUNDS the cross-publisher comparison this store exists for**:
today Litolff has ink rows and Breitkopf has none, so a pooled per-name
`mean_h` between them measures WHICH RECORD WAS GATHERED WITH INK rather than
the two plates. That is `A-INK-4`'s rule -- a measurement retires a concept
only within the factor set it was taken in -- with `source_quantity` as the
factor nobody was holding.

    python3 benchmarks/omr-positional-store-2026-09/probe/source_quantity_mixing.py \
        benchmarks/omr-positional-store-2026-09/out/store-two-publishers.jsonl
"""

import collections
import json
import statistics as st
import sys

NAMES = ("noteheadBlackOnLine", "noteheadBlackInSpace", "ledgerLine",
         "tie", "beam")


def load(path):
    rows = collections.defaultdict(list)
    counts = collections.Counter()
    for line in open(path):
        d = json.loads(line)
        if d.get("_meta"):
            continue
        pub, q = d.get("publisher"), d.get("source_quantity")
        counts[(pub, q)] += 1
        h = d.get("height_spaces")
        if h is None:
            continue
        for m in (d.get("memberships") or []):
            name = m.get("name") if isinstance(m, dict) else m
            rows[(pub, q, name)].append(h)
    return rows, counts


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    rows, counts = load(argv[1])
    print("entries by publisher / source_quantity:")
    for k, v in sorted(counts.items()):
        print(f"    {k[0]:11s} {k[1]:10s} {v:6d}")
    # ⚠️ REACH FIRST, and DECLARE DEAD at zero: a store with no `ink` rows
    # cannot exhibit the mixing, and would print a clean table meaning
    # nothing -- the shape every arm in this repo owes.
    ink = sum(v for k, v in counts.items() if k[1] == "ink")
    print(f"\nink entries in this store: {ink}")
    if not ink:
        print("DEAD: no `ink` rows here, so the mixing cannot appear. "
              "Accumulate a record gathered with OMR_INK on.")
        return 3
    keys = sorted({(p, q) for p, q, _n in rows})
    print(f"\n{'name':22s} {'publisher':11s} {'source':10s} "
          f"{'n':>5s} {'median':>7s} {'mean':>7s} {'p95':>7s}")
    worst = 0.0
    for name in NAMES:
        for pub, q in keys:
            v = rows.get((pub, q, name))
            if not v:
                continue
            s = sorted(v)
            med, mean = st.median(v), st.mean(v)
            p95 = s[int(0.95 * len(s))]
            print(f"  {name:20s} {pub:11s} {q:10s} {len(v):5d} "
                  f"{med:7.3f} {mean:7.3f} {p95:7.3f}")
            if q == "ink":
                worst = max(worst, med)
        print()
    print(f"worst `ink`-row median height over these names: {worst:.3f} staff "
          f"spaces — against ~1.0 for a notehead and ~0.3 for a ledger line.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
