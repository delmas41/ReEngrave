"""ROADMAP 2.303 control: Sean's answered tiles of 2.296 r1 and 2.301 r1 (`answers/`, 24 tiles with a page box) replayed with `judged_claims.replay` on the OFF and the ON record of a plate, side by side.

    python3 benchmarks/dynamics-not-words-2026-11/replay_judged_303.py PLATE OFF_REC ON_REC PAGES

The registry (`data/judged-claims/registry.json`) does not hold these two lanes' answers, so an ad-hoc registry is built here from the answers files (box, page, plate, Sean's words, kind from
`judged_claims.normalise`; a tile whose words it leaves `unmapped` takes the kind below, from Sean's own words). A tile that AGREES OFF and no longer agrees ON is a right->wrong (must be 0).
Reads records; writes nothing.
"""
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
ANS = pathlib.Path(__file__).resolve().parent / "answers"
#: Sean's words the closed vocabulary does not map by itself, set by hand from his words: tile -> kind
OVERRIDE = {("2.301 r1", 4): "word", ("2.301 r1", 9): "word", ("2.301 r1", 6): "word", ("2.301 r1", 10): "word", ("2.301 r1", 8): "dynamic"}


def registry():
    from tools.omr.staged import judged_claims as JC
    tiles = []
    for lane, f in (("2.296 r1", "answers-2.296-r1.json"), ("2.301 r1", "answers-2.301-r1.json")):
        for t in json.loads((ANS / f).read_text())["tiles"]:
            norm = JC.normalise(t["sean"])
            kind = norm["kind"]
            if kind == "unmapped" or (lane, t["tile"]) in OVERRIDE:
                kind = OVERRIDE.get((lane, t["tile"]), kind)
            tiles.append({"id": "%s #%d" % (lane, t["tile"]), "lane": lane, "tile": t["tile"], "plate": t["plate"], "page": t["page"], "box": t["box"], "words": t["sean"],
                          "kind": kind, "value": None, "whole": True, "why_unmapped": None, "extra": {}})
    return {"tiles": tiles}


def main():
    from tools.omr.staged import judged_claims as JC
    plate, off, on, pages = sys.argv[1], sys.argv[2], sys.argv[3], [int(x) for x in sys.argv[4].split(",")]
    reg = registry()
    res = {}
    for arm, rec in (("off", off), ("on", on)):
        rep = JC.replay(rec, doc=plate, pages=pages, registry=reg, log=lambda *_: None)
        res[arm] = {r["id"]: r for r in rep["results"]["base"]}
    bad = 0
    for tid in sorted(res["off"]):
        a, b = res["off"][tid], res["on"][tid]
        if a["verdict"] == "cannot_tell" and b["verdict"] == "cannot_tell":
            continue
        flip = a["verdict"] == "agrees" and b["verdict"] != "agrees"
        bad += flip
        print("%-12s %-10s page %s  Sean: %-48.48s  OFF %-11s ON %-11s %s" % (tid, a["kind"], a["page"], a["words"], a["verdict"], b["verdict"], "RIGHT->WRONG" if flip else ""))
    print("%s: right->wrong %d" % (plate, bad))
    sys.exit(1 if bad else 0)


main()
