"""ROADMAP 2.12f ROUND 2 -- choose the NEW blind tiles: CHANGED owners only, none
Sean already judged. Seeded, one tile per page where it can be, shuffled.

    python3 benchmarks/omr-shape-role-2026-09/select_artic_r2_tiles.py \
        --base-brahms B --r2-brahms R --round1-brahms A \
        --base-litolff B --r2-litolff R --out selection.json [--seed 20261009]

CATEGORIES (recorded in the manifest; Sean never sees them):

  moved_touching   the owner MOVED to the head the mark touches (the x-only pick
                   took a farther one). The rule under test: nearest by gap.
  moved_other      moved, but NOT to the head round 1 recorded as touching.
  stem_side        decided -> abstained `stem_contradicts_class_side`: the stem
                   convention puts the mark on the stem side of a single voice.
  stem_unread      decided -> abstained `stem_direction_unread`: the nearest
                   head's stem is unread (the old pick agreed with it in most).
  narrowed         decided -> NARROWED `heads_about_equally_near` (Brahms, and one
                   from the second plate, Litolff).
  two_voice        decided on the STEM side of a two-voice column.
  control          decided, same head as before, single voice.
"""
from __future__ import annotations

import argparse
import json
import random

JUDGED = {"glyph/18/0/2/0/7", "glyph/23/1/3/4/5", "glyph/11/0/4/3/11",
          "glyph/3/0/0/1/9", "glyph/19/1/10/1/6", "glyph/9/0/10/2/1",
          "glyph/6/0/5/2/4", "glyph/25/1/9/8/7", "glyph/10/0/5/4/1",
          "glyph/24/0/5/7/4", "glyph/2/1/8/0/14", "glyph/5/0/7/6/14"}


def _load(p):
    d = json.load(open(p))
    return d, {r["subject"]: r for r in d["articulations"]}


def _after(o):
    d = o["detail"] or {}
    if o["outcome"] == "decided":
        return ("decided: owner %s (stem %s, notehead side %s, rule %s, gap %.2f "
                "heads)" % (o["value"], d.get("stem_direction"),
                            d.get("notehead_side"), d.get("stem_rule"),
                            d.get("gap_head_heights", float("nan"))))
    if o["outcome"] == "narrowed":
        return "NARROWED: heads_about_equally_near"
    return "abstained: %s (nearest head %s, gap %.2f heads, stem %s)" % (
        o["reason"], d.get("nearest_head"), d.get("gap_head_heights", float("nan")),
        d.get("stem_direction"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    for dname in ("brahms", "litolff"):
        for k in ("base", "r2"):
            ap.add_argument("--%s-%s" % (k, dname), required=True)
    ap.add_argument("--round1-brahms", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261009)
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)

    docs = {}
    for dname in ("brahms", "litolff"):
        bj, b = _load(getattr(a, "base_" + dname))
        rj, r = _load(getattr(a, "r2_" + dname))
        docs[dname] = (rj["pdf"], b, r)
    _, r1 = _load(a.round1_brahms)

    pools = {k: [] for k in ("moved_touching", "moved_other", "stem_side",
                             "stem_unread", "narrowed", "narrowed_litolff",
                             "two_voice", "control")}
    for dname, (pdf, b, r) in docs.items():
        for s, row in r.items():
            if s in JUDGED or not row.get("mark_bbox_page"):
                continue
            bo, ro = b[s]["owner"], row["owner"]
            if bo["outcome"] != "decided":
                continue
            item = {"doc": dname, "pdf": pdf, "page": row["page"], "subject": s,
                    "mark_bbox_page": row["mark_bbox_page"],
                    "before": bo, "after": ro, "round1": r1.get(s) if dname == "brahms" else None}
            if ro["outcome"] == "decided":
                d = ro["detail"]
                if ro["value"] != bo["value"]:
                    touch = ((item["round1"] or {}).get("owner") or {}).get(
                        "detail", {}).get("nearest_declared_side_head")
                    pools["moved_touching" if touch == ro["value"]
                          else "moved_other"].append(item)
                elif d["two_voice"]:
                    pools["two_voice"].append(item)
                elif (d["gap_head_heights"] or 9) <= 0.6:
                    pools["control"].append(item)
                if ro["value"] != bo["value"] and d["two_voice"]:
                    pools["two_voice"].append(item)
            elif ro["outcome"] == "narrowed":
                pools["narrowed_litolff" if dname == "litolff"
                      else "narrowed"].append(item)
            elif ro["reason"] == "stem_contradicts_class_side":
                pools["stem_side"].append(item)
            elif ro["reason"] == "stem_direction_unread":
                pools["stem_unread"].append(item)

    # the rarest categories first, so a page they share with a common one is
    # not taken by it
    want = (("moved_other", 1), ("narrowed_litolff", 1), ("narrowed", 1),
            ("two_voice", 1),
            ("stem_side", 2), ("moved_touching", 3), ("stem_unread", 2),
            ("control", 1))
    used, tiles = set(), []
    for cat, n in want:
        pool = list(pools[cat])
        rng.shuffle(pool)
        got = 0
        for it in pool:
            if got == n:
                break
            key = (it["doc"], it["page"])
            if key in used:
                continue
            used.add(key)
            got += 1
            bo = it["before"]
            before = "decided: owner %s" % bo["value"]
            r1o = ((it["round1"] or {}).get("owner") or {}).get("detail") or {}
            if "gap_head_heights" in r1o:
                before += " (gap %.2f heads)" % r1o["gap_head_heights"]
            tiles.append({"category": cat, "doc": it["doc"], "pdf": it["pdf"],
                          "page": it["page"], "subject": it["subject"],
                          "mark_bbox_page": it["mark_bbox_page"],
                          "read_before": before, "read_after": _after(it["after"])})
    rng.shuffle(tiles)
    for i, t in enumerate(tiles, 1):
        t["n"] = i
    json.dump(tiles, open(a.out, "w"), indent=1)
    print({k: len(v) for k, v in pools.items()})
    for t in tiles:
        print(t["n"], t["category"], t["doc"], t["subject"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
