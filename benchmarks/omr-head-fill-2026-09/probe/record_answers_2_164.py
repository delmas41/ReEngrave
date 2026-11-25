"""ROADMAP 2.164 -- record Sean's answers to the 20 tiles (2026-10-17) into out/print/2.164-review/answers.json, name each
glyph in manifest.json (from the key out/2.164/tiles-key.json), and score the refusals: "Tie" / "Trem slashes" = not a
note (the refusal is right), a value ("2") = a real note (the refusal is wrong). Controls are scored as kept.
usage: record_answers_2_164.py"""
import json

VERBATIM = "1. Tie 2.2 3.tie 4-7.Tie 8. Trem slashes 9-20. Tie"
LATER_10 = ("That is definitely just a part of a slur. The box only covers from the bar line to the second note. So hopefully "
            "there's actually a box that covers the whole arc, in which case this one would be unnecessary because the size is wrong. "
            "But the actual arc from one half note to the other is a slur.")
ANS = {1: "Tie", 2: "2", 3: "tie", 8: "Trem slashes"}
ANS.update({n: "Tie" for n in range(4, 8)})
ANS.update({n: "Tie" for n in range(9, 21)})
key = json.load(open("out/2.164/tiles-key.json"))
man = {"question": key["question"], "colours": "blue box = the mark we are asking about",
       "rule": "ROADMAP 2.164 OMR_ARC_TAIL_NOT_A_HEAD",
       "tiles": [dict(n=t["n"], file="tile_%02d.png" % t["n"], doc=t["doc"], glyph=t["glyph"],
                      control=t["kind"] == "control", role=t["kind"], page_box=t["page_box"]) for t in key["tiles"]]}
json.dump(man, open("out/print/2.164-review/manifest.json", "w"), indent=1)
out = {"answered": "2026-10-17", "verbatim": VERBATIM, "question": key["question"], "tiles": []}
for t in key["tiles"]:
    a = ANS[t["n"]]
    is_note = a.strip() == "2"
    row = dict(n=t["n"], doc=t["doc"], glyph=t["glyph"], role=t["kind"], sean=a, sean_says_note=is_note,
               refusal_right=(not is_note) if t["kind"] == "refused" else None)
    if a.strip().lower() == "tie":
        # 2026-11-24 (Sean): his "Tie" answered "is the box a note?" -- it says "an arc, not a note", nothing of tie versus slur.
        row["scored_as"] = {"answer_kind": "not_a_note", "value": "arc"}
    if t["n"] == 10:
        row["later_answers"] = [{"date": "2026-11-24", "words": LATER_10}]
    out["tiles"].append(row)
json.dump(out, open("out/print/2.164-review/answers.json", "w"), indent=1)
ref = [t for t in out["tiles"] if t["role"] == "refused"]
print("refused", len(ref), "right", sum(t["refusal_right"] for t in ref), "wrong", sum(not t["refusal_right"] for t in ref))
print("controls", [(t["n"], t["doc"], t["glyph"], t["sean"]) for t in out["tiles"] if t["role"] == "control"])
