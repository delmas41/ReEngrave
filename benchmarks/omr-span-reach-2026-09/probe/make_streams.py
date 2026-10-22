"""Split the remaining editions into N round-robin stream lists.

⚠️ THE POPULATION IS CHOSEN, AND CHOOSING IT IS PART OF THE ANSWER. The library
holds 27,718 edition pages and the phase-1 screen costs ~1-3.5 s of them, so an
exhaustive crawl is 8-24 core-hours. What the reach question needs is not every
page but every KIND of document that could hold a lineup boundary, so the
default population is:

    * one PDF holding several movements — a symphony, a concerto, a suite, a
      mass, an opera: the only documents where a lineup can change at all;
    * at least `--min-pages` pages, because a span needs 4 pages and a
      boundary needs two spans;

and single-movement pieces (overtures, tone poems, single dances) are excluded
by name. They are not immune to the code — a lineup can grow inside one
movement — but they are the population least likely to hold a boundary, and
excluding them is stated here rather than hidden in a page cap.

Round-robin by descending page count so every stream gets a share of the long
documents and they finish together.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "benchmarks/omr-span-reach-2026-09/out"

#: Titles that name a multi-movement container.
MULTI = re.compile(
    r"symphon|concerto|suite|mass|requiem|serenade|sinfoni|quartet|quintet|"
    r"sonata|opera|ballet|nutcracker|swan lake|planets|carmen|dances|"
    r"variations|divertimento|cassation|oratorio|passion|cantata|te deum",
    re.I)

n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
min_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 40
max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 0   # 0 = no cap

cat = json.load(open(ROOT / "data/score-library/catalog.json"))
done = {p.stem for p in (OUT / "profiles").glob("*.json")}

rows = [e for e in cat["entries"]
        if e["kind"] == "edition" and (e.get("pages") or 0) >= min_pages
        and Path(e["path"]).stem not in done
        and MULTI.search(e.get("title") or "")]
rows.sort(key=lambda e: -(e.get("pages") or 0))
if max_pages:
    # A page CAP rather than a total budget, and the difference matters: a cap
    # excludes a known, nameable class of document (the operas, the ballets,
    # Mahler) which can be reported as excluded, where a running budget would
    # silently drop whichever documents happened to sort last.
    rows = [e for e in rows if (e.get("pages") or 0) <= max_pages]

(OUT / "streams").mkdir(parents=True, exist_ok=True)
buckets: list[list[str]] = [[] for _ in range(n)]
load = [0] * n
for e in rows:
    i = load.index(min(load))
    buckets[i].append(e["path"])
    load[i] += e["pages"]
for i, b in enumerate(buckets):
    (OUT / "streams" / f"s{i}.txt").write_text("\n".join(b) + "\n")
    print(f"s{i}: {len(b)} editions, {load[i]} pages")
print(f"({len(done)} already profiled, {len(rows)} selected)")
