"""night 2026-10-08 read: pick the heads the STEM witness moved to a different staff, from the two small extracts only.

Pools (NEW = 20261008-night, BASE = 20261007-day, matched by subject, control: same class and box):
  A  stem_toward_staff, BASE decided another staff                (the stem overturned a distance/group answer)
  B  stem_toward_staff, BASE abstained                             (the stem answered a gap)
  C  stem_toward_staff, owner != the staff the head is filed on, BASE agreed on the owner (the stem confirmed a move)
Heads Sean already saw (out/print/stem_owner/key.json, mark_group_no_owner) and their pages are left out.
Seeded pick of 10, A first, then B, then C, at most one per (doc, page, system), spread over both documents.

  python3 night_1008_pick.py <dir holding x/> [--seed 20261008] -> <dir>/pick.json
"""
from __future__ import annotations
import collections, json, random, sys
from pathlib import Path

DOCS = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}
SEEN = {"litolff": {"glyph/14/0/6/1/1", "glyph/4/1/2/4/3", "glyph/12/0/2/6/5", "glyph/4/1/0/12/3", "glyph/16/0/2/15/2"},
        "brahms": {"glyph/15/0/4/2/4", "glyph/4/0/11/9/5", "glyph/11/0/3/0/11", "glyph/24/0/3/8/10", "glyph/19/1/5/6/1"}}
SEEN_PAGES = {"litolff": {14, 4, 12, 16, 3}, "brahms": {15, 4, 11, 24, 19, 1}}
NEW, BASE = "20261008-night", "20261007-day"


def pools(d):
    out = collections.defaultdict(list)
    for tag, doc in DOCS.items():
        N = json.loads((d / "x" / f"{doc}-{NEW}.json").read_text())
        B = json.loads((d / "x" / f"{doc}-{BASE}.json").read_text())
        for s, g in N["glyphs"].items():
            o = g.get("own")
            if not o or o["outcome"] != "decided" or o["reason"] != "stem_toward_staff" or s in SEEN[tag]:
                continue
            b = B["glyphs"].get(s)
            if b is None or b.get("cls") != g.get("cls"):
                continue
            bo = b.get("own")
            filing = "staff/" + "/".join(s.split("/")[1:4])
            if bo and bo["outcome"] == "decided" and bo["value"] != o["value"]:
                pool, other = "A", bo["value"]
            elif not bo or bo["outcome"] != "decided":
                pool, other = "B", filing
            elif o["value"] != filing:
                pool, other = "C", filing
            else:
                continue
            if other == o["value"]:
                continue
            out[(pool, tag)].append(dict(doc=tag, head=s, pool=pool, new=o["value"], other=other, base=bo,
                                         cls=g.get("cls"), box=g["box"]))
    return out


def main(d, seed=20261008):
    d = Path(d)
    P = pools(d)
    print({f"{k[0]}-{k[1]}": len(v) for k, v in sorted(P.items())})
    rng = random.Random(seed)
    chosen, used = [], set()

    def take(pool, prefer_new_pages=True):
        cand = []
        for tag in DOCS:
            for h in P.get((pool, tag), []):
                p = int(h["head"].split("/")[1])
                key = (tag, h["head"].split("/")[1], h["head"].split("/")[2])
                cand.append((p in SEEN_PAGES[tag], h, key))
        rng.shuffle(cand)
        cand.sort(key=lambda t: t[0])           # pages the rules were not written on first
        return cand
    for pool, quota in (("A", 6), ("B", 4), ("C", 10)):
        for strict in ((True, False) if pool != "C" else (True,)):    # A and B: a second head in a system only if short
            for _, h, key in take(pool):
                if len(chosen) >= 10 or sum(1 for c in chosen if c["pool"] == pool) >= quota:
                    break
                nsys = sum(1 for c in chosen if (c["doc"],) + tuple(c["head"].split("/")[1:3]) == (h["doc"],) + key[1:])
                if h in chosen or (strict and key in used) or nsys >= 2:
                    continue
                used.add(key)
                chosen.append(h)
    rng.shuffle(chosen)
    (d / "pick.json").write_text(json.dumps(chosen, indent=1))
    for i, c in enumerate(chosen, 1):
        print(i, c["doc"], c["head"], c["pool"], "new", c["new"], "other", c["other"], c["cls"])


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261008)
