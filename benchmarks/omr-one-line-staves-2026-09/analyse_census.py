"""Summarise the census: how often does a sub-five-line staff appear, and where?

The census can only report GEOMETRY. This turns it into the two numbers the
commission asks for — how much the `>= 5` filter drops, and how concentrated it
is — and lists the hits so `cut_crops.py` can put ink in front of a human.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", default="census.json")
    args = ap.parse_args(argv)
    doc = json.loads((HERE / args.census).read_text())
    rows = doc["rows"]
    ok = [r for r in rows if "n_one" in r]
    err = [r for r in rows if "error" in r]
    hits = [r for r in ok if r.get("n_one")]
    n_one = sum(r["n_one"] for r in ok)
    n_staves = sum(r["n_staves"] for r in ok)

    print(f"pages read              {len(ok)}")
    print(f"pages that errored      {len(err)}")
    print(f"editions covered        {len({r['path'] for r in ok})}")
    print(f"staves detected         {n_staves}")
    print(f"ONE-LINE staves         {n_one}"
          f"   ({100.0 * n_one / max(1, n_staves):.3f}% of all staves)")
    print(f"pages carrying one      {len(hits)}"
          f"   ({100.0 * len(hits) / max(1, len(ok)):.2f}% of pages)")
    if err:
        print("\nerrors:")
        for r in err[:10]:
            print(f"  {r['path']} p{r['page']}: {r['error'][:90]}")

    print("\nby work (pages : one-line staves):")
    byw: Counter = Counter()
    stw: Counter = Counter()
    for r in hits:
        byw[r["work_id"]] += 1
        stw[r["work_id"]] += r["n_one"]
    for w, v in byw.most_common():
        print(f"  {w:44} {v:3d} pages  {stw[w]:3d} staves")

    print("\nthe hits, for adjudication:")
    for r in sorted(hits, key=lambda r: (r["path"], r["page"])):
        ys = ", ".join(f"s{e['staff_index']}@y{e['y']}" for e in r["one_line"])
        print(f"  {r['path'][:78]}")
        print(f"      p{r['page']}  {r['n_five']} five-line + "
              f"{r['n_one']} one-line   [{ys}]")

    out = {
        "pages_read": len(ok), "pages_errored": len(err),
        "editions": len({r["path"] for r in ok}),
        "staves_detected": n_staves, "one_line_staves": n_one,
        "pages_with_one_line": len(hits),
        "share_of_staves": n_one / max(1, n_staves),
        "share_of_pages": len(hits) / max(1, len(ok)),
        "by_work_pages": dict(byw), "by_work_staves": dict(stw),
    }
    (HERE / "census-summary.json").write_text(json.dumps(out, indent=1) + "\n")
    print("\nwrote", HERE / "census-summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
