"""Turn the sweep's JSONL into per-publisher counts and a ranked candidate queue.

Ranking only.  Nothing here reads ground truth; nothing here is a claim about
what a page prints.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def publisher_of(rec: dict[str, Any]) -> str:
    p = rec.get("publisher") or ""
    return (p.split(",")[0].strip() or "UNKNOWN")


def load(path: Path) -> list[dict[str, Any]]:
    recs = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    assert recs, f"{path} is empty -- the sweep measured nothing"
    return recs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--queue-limit", type=int, default=200)
    args = ap.parse_args()

    recs = load(Path(args.jsonl))
    n = len(recs)
    editions = {r["path"] for r in recs}
    assert editions, "no editions in the sweep output"

    tiers = Counter(r.get("tier") for r in recs)
    # the denominator that matters: pages that were actually SCREENABLE
    screenable = [r for r in recs
                  if r.get("tier") in ("A", "D", "none", "doubtful")]
    assert screenable, "ZERO screenable pages -- refusing to report a rate"

    a = [r for r in screenable if r["tier"] == "A"]
    d = [r for r in screenable if r["tier"] == "D"]
    doubtful = [r for r in screenable if r["tier"] == "doubtful"]

    abstain_reasons = Counter(
        (r.get("abstain") or "").split("--")[-1].strip()
        for r in recs if r.get("tier") == "abstain")

    per_pub: dict[str, Counter] = defaultdict(Counter)
    for r in recs:
        per_pub[publisher_of(r)][r.get("tier")] += 1
        per_pub[publisher_of(r)]["pages"] += 1

    per_edition: dict[str, Counter] = defaultdict(Counter)
    for r in recs:
        per_edition[r["path"]][r.get("tier")] += 1
        per_edition[r["path"]]["pages"] += 1

    # ---- ranked queue.  Tier A first, ordered by how large the count change is
    # relative to the widest system (a 14->13 suppression is a smaller, more
    # plausible tacet than a 15->4 phase-1 collapse).
    def spread(r):
        c = r["staff_counts"]
        return (max(c) - min(c)) / max(c)

    queue = []
    for r in sorted(a, key=spread):
        queue.append({
            "tier": "A",
            "screens": r["screens"],
            "path": r["path"],
            "page_index": r["page_index"],
            "page_1based": r["page_index"] + 1,
            "publisher": publisher_of(r),
            "work_id": r.get("work_id"),
            "title": r.get("title"),
            "staff_counts": r["staff_counts"],
            "block_shapes": r.get("block_shapes"),
            "spread": round(spread(r), 3),
        })
    for r in d:
        queue.append({
            "tier": "D",
            "screens": r["screens"],
            "path": r["path"],
            "page_index": r["page_index"],
            "page_1based": r["page_index"] + 1,
            "publisher": publisher_of(r),
            "work_id": r.get("work_id"),
            "title": r.get("title"),
            "staff_counts": r["staff_counts"],
            "block_shapes": r.get("block_shapes"),
        })

    payload = {
        "n_pages_measured": n,
        "n_editions_touched": len(editions),
        "tiers": dict(tiers),
        "n_screenable": len(screenable),
        "n_tier_A": len(a),
        "n_tier_D": len(d),
        "n_doubtful": len(doubtful),
        "tier_A_rate_of_screenable": round(len(a) / len(screenable), 4),
        "abstain_reasons": dict(abstain_reasons),
        "per_publisher": {k: dict(v) for k, v in sorted(
            per_pub.items(), key=lambda kv: -kv[1]["pages"])},
        "per_edition_tier_A": {k: v["A"] for k, v in sorted(
            per_edition.items(), key=lambda kv: -kv[1]["A"]) if v["A"]},
        "queue": queue[: args.queue_limit],
        "queue_full_length": len(queue),
    }
    Path(args.out).write_text(json.dumps(payload, indent=1))

    print(f"pages measured        {n}")
    print(f"editions touched      {len(editions)}")
    print(f"tiers                 {dict(tiers)}")
    print(f"screenable pages      {len(screenable)}")
    print(f"tier A (counts differ){len(a):>6}  "
          f"({len(a) / len(screenable):.1%} of screenable)")
    print(f"tier D (blocks only)  {len(d):>6}")
    print(f"structurally doubtful {len(doubtful):>6}")
    print()
    print(f"{'publisher':<42} {'pages':>6} {'A':>5} {'D':>5} {'doubt':>6} {'abst':>6}")
    for k, v in sorted(per_pub.items(), key=lambda kv: -kv[1]["A"])[:15]:
        print(f"{k[:42]:<42} {v['pages']:>6} {v['A']:>5} {v['D']:>5} "
              f"{v['doubtful']:>6} {v['abstain']:>6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
