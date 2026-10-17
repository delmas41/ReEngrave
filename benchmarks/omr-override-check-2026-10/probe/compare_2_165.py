"""ROADMAP 2.165 -- compare the base and on arms of `replay_2_165.py` (STAGED ADJUDICATE..INFER, whole records).

Prints, per doc: near misses by guard row (and by reason); the READ / GUESSED / UNREAD transitions of every note;
bars newly holding an unread note vs newly holding a guessed one; the stem-value rule's reach; the meter changes.
Writes OUTDIR/<doc>.changed.json: every glyph whose standing duration changed, attributed to the cause the record
names (a guard row, the shared-stem rule, or `downstream` -- 2.162's helper or a consequence of another change).
usage: compare_2_165.py OUTDIR [DOC ...]"""
import collections
import json
import os
import sys

OUT = sys.argv[1]
DOCS = sys.argv[2:] or ["litolff", "brahms"]


def k(b):
    return None if b is None else (b["outcome"], b["written"], b["dots"], b["levels"], b["cls"])


def bar(g):
    return "/".join(g.split("/")[1:5])


for doc in DOCS:
    try:
        B = json.load(open(os.path.join(OUT, "%s.base.json" % doc)))
        O = json.load(open(os.path.join(OUT, "%s.on.json" % doc)))
    except FileNotFoundError:
        continue
    print("=" * 20, doc)
    print("near misses by row:", dict(collections.Counter(m["row"] for m in O["near_misses"]).most_common()))
    print("near misses by row/why:", dict(collections.Counter((m["row"], m["why"]) for m in O["near_misses"]).most_common()))
    miss_by_sub = collections.defaultdict(list)
    for m in O["near_misses"]:
        miss_by_sub[m["subject"]].append(m["row"])
    trans = collections.Counter()
    cause = collections.Counter()
    changed = {}
    bars_unread, bars_guessed = set(), set()
    notes_unread = notes_guessed = notes_read = 0
    for g, b in B["glyphs"].items():
        o = O["glyphs"].get(g)
        if k(b) == k(o):
            continue
        trans[(b["cls"] if b else None, o["cls"] if o else None)] += 1
        st = O["stems"].get(g)
        if g in miss_by_sub:
            c = "row:" + miss_by_sub[g][0]
        elif st and st[1] in ("stem_heads_disagree", "stem_heads_one_dissent"):
            c = "stem:" + st[1]
        else:
            c = "downstream"
        cause[(c, b["cls"] if b else None, o["cls"] if o else None)] += 1
        changed[g] = dict(base=b, on=o, cause=c, stem_on=st, stem_base=B["stems"].get(g))
        if o and o["cls"] == "UNREAD" and (not b or b["cls"] != "UNREAD"):
            bars_unread.add(bar(g))
            notes_unread += 1
        elif o and o["cls"] == "GUESSED" and (not b or b["cls"] != "GUESSED"):
            bars_guessed.add(bar(g))
            notes_guessed += 1
        elif o and o["cls"] == "READ" and b and b["cls"] != "READ":
            notes_read += 1
    print("notes changed", len(changed), "| class transitions", dict(trans.most_common()))
    print("newly UNREAD notes", notes_unread, "in", len(bars_unread), "bars | newly GUESSED notes", notes_guessed, "in",
          len(bars_guessed), "bars | newly READ", notes_read)
    print("by cause:")
    for kk, n in cause.most_common():
        print("  ", n, kk)
    sb = collections.Counter(tuple(v) for v in B["stems"].values())
    so = collections.Counter(tuple(v) for v in O["stems"].values())
    print("stem values: one_dissent", so.get(("decided", "stem_heads_one_dissent"), 0), "| disagree",
          so.get(("narrowed", "stem_heads_disagree"), 0), "| base hollow-over-filled decided (stem_value_from_evidence)",
          sb.get(("decided", "stem_value_from_evidence"), 0), "->", so.get(("decided", "stem_value_from_evidence"), 0))
    mch = {s: (B["meters"].get(s), O["meters"][s]) for s in O["meters"]
           if (B["meters"].get(s) or {}) != O["meters"][s]}
    print("meters changed", len(mch))
    for s, (a, b) in sorted(mch.items()):
        print("  ", s, a and (a["outcome"], a["reason"], a["num"], a["den"]), "->", (b["outcome"], b["reason"], b["num"], b["den"]))
    json.dump(changed, open(os.path.join(OUT, "%s.changed.json" % doc), "w"), indent=0)
