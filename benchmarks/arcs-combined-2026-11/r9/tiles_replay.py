"""2.305 r9 -- Sean's answered ARC tiles (r1, r2, r4, r6, r7b; truth transcribed in r6's score_tiles.py and answers-2.305-r7b.json) replayed on the
written files of two arms, on the pages those arms hold: right / wrong / unwritten per tile, A -> B. An arc is matched by its two NOTES (either
order; a chord member counts as its chord, as MusicXML writes it); a different arc from the same start note counts WRONG.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 tiles_replay.py A.facts.json B.facts.json PLATE PAGE
"""
import collections
import json
import sys

import judge as J

# (set, tile, plate, start, stop, truth) -- copied from the r6 scratchpad score_tiles.py TRUTH (Sean's words there), plus r7b
TRUTH = [
    ("r1", 4, "brahms", "glyph/0/0/9/6/6", "glyph/0/0/9/6/8", "slur"),
    ("r1", 6, "brahms", "glyph/0/0/12/2/1", "glyph/0/0/12/3/3", "slur"),
    ("r1", 12, "litolff", "glyph/13/0/8/1/6", "glyph/13/0/8/2/6", "tie"),
    ("r2", 1, "litolff", "glyph/13/1/1/11/5", "glyph/13/1/1/12/8", "tie"),
    ("r2", 6, "brahms", "glyph/0/0/10/3/4", "glyph/0/0/10/4/4", "tie"),
    ("r6", 1, "litolff", "glyph/13/0/10/10/7", "glyph/13/0/10/12/6", "none"),
    ("r6", 2, "litolff", "glyph/13/0/3/13/5", "glyph/13/0/3/14/7", "tie"),
    ("r6", 3, "litolff", "glyph/13/1/0/8/3", "glyph/13/1/0/10/9", "none"),
    ("r6", 4, "litolff", "glyph/13/1/1/9/11", "glyph/13/1/1/10/12", "tie"),
    ("r6", 8, "brahms", "glyph/0/0/11/3/12", "glyph/0/0/11/3/6", "none"),
    ("r6", 9, "brahms", "glyph/0/0/5/2/16", "glyph/0/0/5/3/14", "tie"),
    ("r6", 12, "brahms", "glyph/0/0/5/4/15", "glyph/0/0/5/5/12", "tie"),
    ("r7b", 1, "litolff", "glyph/13/1/0/8/6", "glyph/13/1/0/10/9", "none"),       # "the first tick is a couple of 8 notes in front"
    ("r7b", 3, "litolff", "glyph/13/0/0/13/8", "glyph/13/0/0/14/3", "arc"),       # "correct notes, half notes" (kind not said)
    ("r7b", 4, "brahms", "glyph/0/0/9/0/7", "glyph/0/0/9/1/9", "slur"),
    ("r7b", 5, "brahms", "glyph/0/0/11/0/4", "glyph/0/0/11/1/6", "none"),         # "missing one note on the end"
    ("r7b", 6, "brahms", "glyph/0/0/11/0/4", "glyph/0/0/11/1/13", "slur"),
]


def written(facts):
    chord_of, head = {}, None
    for h in facts["written"]:
        if h.get("kind") != "note":
            continue
        if not h.get("chord"):
            head = h["rg"]
        chord_of[h["rg"]] = head if h.get("chord") else h["rg"]
    ck = lambda rg: chord_of.get(rg, rg)   # noqa: E731
    out = collections.defaultdict(set)
    for k, a, b, _ba, _bb in J.xml_arcs(facts["xml"], lambda r: None):
        if a and b:
            out[frozenset((ck(a), ck(b)))].add(k)
    return out, ck


def score(facts, plate, page):
    W, ck = written(facts)
    res = {}
    for st, t, pl, a, b, truth in TRUTH:
        if pl != plate or int(a.split("/")[1]) != page:
            continue
        got = W.get(frozenset((ck(a), ck(b))), set())
        other = any(ck(a) in key for key in W) and not got
        if truth == "none":
            v = "wrong" if got else "right"
        elif got:
            v = "right" if truth == "arc" or truth in got else "wrong"
        else:
            v = "wrong" if other else "unwritten"
        res[(st, t)] = (v, sorted(got))
    return res


def main():
    A, B = (json.load(open(p)) for p in sys.argv[1:3])
    plate, page = sys.argv[3], int(sys.argv[4])
    ra, rb = score(A, plate, page), score(B, plate, page)
    moves = collections.Counter()
    for k in ra:
        moves["%s->%s" % (ra[k][0], rb[k][0])] += 1
        print("%-4s %2d  %-9s %-14s -> %-9s %s" % (k[0], k[1], ra[k][0], ra[k][1], rb[k][0], rb[k][1]))
    print(plate, page, dict(moves))


if __name__ == "__main__":
    main()
