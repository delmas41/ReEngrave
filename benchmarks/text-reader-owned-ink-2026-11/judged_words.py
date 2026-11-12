"""ROADMAP 2.304 controls: the words Sean judged RIGHT (2.296 r1, 2.301 r1, 2.303 r1 blind tiles) and whether each is READ, with the same text, in the OFF and ON arms' probes.

    python3 benchmarks/text-reader-owned-ink-2026-11/judged_words.py OFF.probe.json ON.probe.json [OFF2.probe.json ON2.probe.json ...]   (pairs; each pair one plate)
A judged word is matched to a READ word of the probe by page and x overlap of its box with the READ candidate's box (the probe's `found` rows carry staff and measure only, so the match
goes through the candidate whose lexicon reading it was).
"""
import json
import pathlib
import sys
from collections import defaultdict

ANS = pathlib.Path(__file__).resolve().parents[1] / "dynamics-not-words-2026-11" / "answers"


def judged():
    out = []
    for name in ("answers-2.296-r1.json", "answers-2.301-r1.json", "answers-2.303-r1.json"):
        d = json.load(open(ANS / name))
        for t in d["tiles"]:
            k = t.get("key", t)
            kind = t.get("kind") or k.get("kind")
            right = t.get("kind_right", t.get("ours_right"))
            box = t.get("box") or (k.get("boxes") or [None])[0]
            if kind == "word" and right and box and t.get("plate", k.get("plate")):
                out.append((name, t["tile"], t.get("plate", k.get("plate")), t.get("page", k.get("page")), box, t.get("text") or k.get("text")))
    return out


def read_words(path):
    out = []
    for pg in json.load(open(path)):
        by = defaultdict(list)
        for r in pg["readings"]:
            by[r["candidate"]].append(r)
        for cd in pg["candidates"]:
            acc = sorted({r["accepted"] for r in by.get(cd["i"], []) if r["accepted"]})
            if acc:
                out.append((pg["page"], cd["box"], acc))
    return out


def ovl(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return 0.0 if w <= 0 or h <= 0 else (w * h) / min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))


J = judged()
print("judged-right word tiles:", len(J))
for off, on in zip(sys.argv[1::2], sys.argv[2::2]):
    a, b = read_words(off), read_words(on)
    for name, tile, plate, page, box, text in J:
        if plate not in off:
            continue
        fa = [w for p, bx, w in a if p == page and ovl(bx, box) > 0.5]
        fb = [w for p, bx, w in b if p == page and ovl(bx, box) > 0.5]
        print("%s tile %s %s p%s %s judged text %r | OFF READ %s | ON READ %s" % (name[8:-5], tile, plate, page, [int(v) for v in box], text, fa, fb))
