"""Re-read the SHIPPING evidence for OMR_ROSTER, on its own recorded records.

`benchmarks/omr-roster-wiring-2026-09/roster-identity-pooled.json` is the file
the default-ON decision was made on.  Two things are asked of it here, neither
of which needs a new run:

  1. how many PDF PAGES each row covers -- the roster's premise is
     "acquire once, serve the whole document", so the span of a row is the span
     of the evidence;
  2. which records the two arms actually disagree on, printed in full, so the
     delta can be read rather than trusted.
"""
import json
import collections
import sys
from pathlib import Path

p = Path(sys.argv[1] if len(sys.argv) > 1
         else "benchmarks/omr-roster-wiring-2026-09/roster-identity-pooled.json")
d = json.load(open(p))
recs = d["records"]
rows = collections.OrderedDict()
for r in recs:
    rows.setdefault(r["row_id"], []).append(r)

print(f"INPUT ASSERTION: file={p} records={len(recs)} rows={len(rows)}")
if not recs:
    print("REFUSING: no records")
    raise SystemExit(1)

print()
print("## 1. how many PDF pages does each row span?")
spans = collections.Counter()
for k, v in rows.items():
    pages = sorted({x["page_index"] for x in v})
    spans[len(pages)] += 1
    off = sum(1 for x in v if x["OFF"] == x["TRUTH"])
    on = sum(1 for x in v if x["ON"] == x["TRUTH"])
    print(f"  {k:42s} pages={pages} staves={len(v):3d} "
          f"OFF={off:3d} ON={on:3d} delta={on-off:+d}")
print(f"  rows by page-span: {dict(spans)}")

print()
print("## 2. every record the two arms disagree on")
diff = [r for r in recs if r["OFF"] != r["ON"]]
print(f"  {len(diff)} of {len(recs)} records differ")
tally = collections.Counter()
for r in diff:
    okoff = r["OFF"] == r["TRUTH"]
    okon = r["ON"] == r["TRUTH"]
    verdict = ("ON fixes" if okon and not okoff else
               "ON breaks" if okoff and not okon else
               "both wrong")
    tally[verdict] += 1
    tally[(verdict, r["TRUTH"])] += 1
print("  " + ", ".join(f"{k}={v}" for k, v in tally.items()
                       if isinstance(k, str)))
print()
print("  by truth label:")
for k, v in sorted(((k, v) for k, v in tally.items() if isinstance(k, tuple)),
                   key=lambda t: -t[1]):
    print(f"    {v:4d}  {k[0]:10s} truth={k[1]}")
print()
print("  first 40 differing records:")
for r in diff[:40]:
    print(f"    {r['row_id']:36s} ord{r['ordinal']:3d} printed={str(r['TRUTH_printed'])!r:20s} "
          f"TRUTH={str(r['TRUTH']):12s} OFF={str(r['OFF']):12s} ON={str(r['ON']):12s}")

print()
print("## 3. records whose TRUTH is `Bass voice`")
bv = [r for r in recs if r["TRUTH"] == "Bass voice"]
print(f"  {len(bv)} records. In an orchestral score `Basso` is the DOUBLE BASS;")
print("  the reference encodings' own part lists say Contrabass.")
for r in bv:
    print(f"    {r['row_id']:36s} ord{r['ordinal']:3d} printed={str(r['TRUTH_printed'])!r:12s} "
          f"OFF={str(r['OFF']):12s} ON={str(r['ON']):12s}")
