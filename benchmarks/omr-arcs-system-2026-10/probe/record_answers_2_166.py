"""ROADMAP 2.166 -- record Sean's answers to the 13 ARC tiles (2026-10-17; he saw them redrawn by the manager,
numbered 1-13 in the order of our tiles 1, 2, 6, 7, 10, 11, 12, 14, 16, 18, 19, 23, 25) into
out/print/2.166-review/answers.json, name each ANSWERED tile's subject in manifest.json (the 12 box tiles stay blind),
and score each against what we read: the ends' shape (a tie's shape = two heads at one position, adjacent), the
anchors, and whether the curve was joined across a barline.
usage: record_answers_2_166.py"""
import json

VERBATIM = ("1. Tie 2. Slur 3.tie 4. Tie 5. Slur 6. Tie on one side of the barline and a slur on the other. "
            "The blue line swaps arcs. 7. Tie 8. Tie 9. Tie 10. Tie 11 slur 12. Tie 13. Tie")
ORDER = [1, 2, 6, 7, 10, 11, 12, 14, 16, 18, 19, 23, 25]
SAID = ["Tie", "Slur", "tie", "Tie", "Slur",
        "Tie on one side of the barline and a slur on the other. The blue line swaps arcs.",
        "Tie", "Tie", "Tie", "Tie", "slur", "Tie", "Tie"]
CALL = {"two_heads_one_position_adjacent": "tie", "two_positions": "slur", "one_position_heads_between": "slur"}

key = {t["n"]: t for t in json.load(open("out/2.166/tiles-key.json"))["tiles"]}
man = json.load(open("out/print/2.166-review/manifest.json"))
for m in man["tiles"]:
    if m["n"] in ORDER:
        k = key[m["n"]]
        m.update(doc=k["doc"], glyph=k["subject"], control=k["role"].startswith("control"), kind="arc",
                 question_kind="arc_kind")
json.dump(man, open("out/print/2.166-review/manifest.json", "w"), indent=1)

rows = []
for redraw, (n, said) in enumerate(zip(ORDER, SAID), 1):
    k = key[n]
    sean = "tie" if said.lower() == "tie" else "slur" if said.lower() == "slur" else "tie|slur (swapped at barline)"
    ours = CALL.get(k["shape"])
    rows.append(dict(n=n, redraw_n=redraw, doc=k["doc"], glyph=k["subject"], role=k["role"], sean=said,
                     sean_kind=sean, our_shape=k["shape"], our_call=ours, anchors=k["anchors"],
                     joined_across_barline=len(k["cells"]) > 1, pieces=len(k["pieces"]), cells=k["cells"],
                     ran_through_stroke_only_box=bool(k["stroke_only"]),
                     score=("unanchored" if ours is None else "right" if ours == sean else
                            "wrong" if sean in ("tie", "slur") else "wrong_curve")))
out = {"answered": "2026-10-17", "verbatim": VERBATIM,
       "via": "manager redraw out/print/2.166-arcs-clear (start-here-go-cbd2bc), numbered 1-13 = our tiles " +
              ", ".join(str(n) for n in ORDER),
       "question": "Is the blue line one tie, one slur, or something else? Which two notes does it join?",
       "pending": "the 12 box tiles (3, 4, 5, 8, 9, 13, 15, 17, 20, 21, 22, 24) are not yet answered",
       "tiles": [dict(n=r["n"], answer=r["sean"], doc=r["doc"], glyph=r["glyph"]) for r in rows]}
json.dump(out, open("out/print/2.166-review/answers.json", "w"), indent=1)
json.dump(rows, open("out/2.166/arc_answers_scored.json", "w"), indent=1)
for r in rows:
    print(r["n"], r["sean_kind"], "| ours", r["our_shape"], "->", r["our_call"], "| joined", r["joined_across_barline"],
          "| stroke-only box", r["ran_through_stroke_only_box"], "|", r["score"])
import collections  # noqa: E402
print(collections.Counter(r["score"] for r in rows))
