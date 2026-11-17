"""ROADMAP 2.313 -- per facts file: red bars and refused note values, on the counted pages (reads only; `redbars.red_bars` is the 2.311 definition).

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/landing-check-2026-11/metrics.py PAGES A.facts.json [B.facts.json ...]

For each file: red bars (every kind), red bars by kind, heads whose value the exporter refused (`duration_narrowed`, `chord_value_undecided`)
-- all of them and those standing in a red bar -- and the export fate `staff_not_identified` (a staff whose name was lost).
"""
import collections
import json
import sys

from redbars import red_bars

REF = ("duration_narrowed", "chord_value_undecided")
pages = {int(x) for x in sys.argv[1].split(",")}
for n in sys.argv[2:]:
    f = json.load(open(n))
    bars = red_bars(f, pages)
    keys = {(b["page"], b["system"], b["staff"], b["cell"]) for b in bars}
    refused = [(k, g) for k, g in f["glyphs"].items() if len(k.split("/")) == 6 and g.get("head") and g.get("fate") in REF and int(k.split("/")[1]) in pages]
    inred = [k for k, g in refused if tuple(int(x) for x in k.split("/")[1:5]) in keys]
    notid = sum(1 for k, g in f["glyphs"].items() if g.get("fate") == "staff_not_identified" and len(k.split("/")) > 1 and k.split("/")[1].isdigit() and int(k.split("/")[1]) in pages)
    print("%-34s red bars %3d %s | refused heads %3d, in red bars %3d | staff_not_identified %d" % (
        n.split("/")[-1], len(bars), dict(collections.Counter(b["kind"] for b in bars)), len(refused), len(inred), notid))
