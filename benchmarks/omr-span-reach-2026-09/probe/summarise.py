"""One table of every profiled edition: pages, spans, boundary pages, peaks.

⚠️ The peak reported per span is `movement_reference._peaks`' OWN peak, not the
raw largest system. `_peaks` drops any system more than `MERGE_CAP_RATIO` times
the document median as a probable concatenation, and the raw maximum therefore
says nothing about the level the boundary rule saw: Dvořák 9's raw peak is 30
on a document whose lineup is 15, and reporting that would make the table look
like it disagreed with the spans it describes.
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.omr import movement_reference  # noqa: E402

D = ROOT / "benchmarks/omr-span-reach-2026-09/out/profiles"

rows = []
for f in sorted(D.glob("*.json")):
    r = json.load(open(f))
    profile = [(int(k), v) for k, v in r["profile"].items()]
    peaks = movement_reference._peaks(profile)
    spans = r["spans"]
    rows.append({
        "edition": f.stem,
        "pages": len(r["pages"]),
        "n_spans": r["n_spans"],
        "ranges": r["span_ranges"],
        "boundaries": [s[0] for s in spans[1:]],
        "span_peaks": [max([peaks[p] for p in s if p in peaks] or [0])
                       for s in spans],
        "raw_peak": max((max(v) if v else 0) for v in r["profile"].values()),
        # The level the rule actually reasons about: a size seen on ONE page
        # is a wobble and never raises the running maximum (`counts[v] < 2`).
        "span_levels": [
            max([v for v, n in collections.Counter(
                [peaks[p] for p in s if p in peaks]).items() if n >= 2] or [0])
            for s in spans],
        "seconds": r.get("seconds"),
    })

rows.sort(key=lambda r: (-r["n_spans"], r["edition"]))
print(f"{'edition':70s} {'pg':>4s} {'spans':>5s}  boundaries / span peaks")
for r in rows:
    print(f"{r['edition'][:70]:70s} {r['pages']:4d} {r['n_spans']:5d}  "
          f"{r['boundaries']} levels={r['span_levels']} peaks={r['span_peaks']}")
multi = [r for r in rows if r["n_spans"] > 1]
print(f"\n{len(multi)} of {len(rows)} profiled editions take more than one "
      f"lineup span")
json.dump(rows, open(D.parent / "summary.json", "w"), indent=1, sort_keys=True)
