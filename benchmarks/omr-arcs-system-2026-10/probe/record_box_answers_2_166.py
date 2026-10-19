"""ROADMAP 2.166 -- record Sean's answers to the 12 BOX tiles (2026-10-17; shown in the order of our tiles 3, 4, 5, 8, 9,
13, 15, 17, 20, 21, 22, 24) into out/print/2.166-review/answers.json (beside the 13 arc answers), name them in
manifest.json, and score each against both arms of the page A/B (out/2.166/ab_<doc>_p<page>.{off,on}.record.json):
is it a note (notehead_is_not_a_notehead) and what duration, base vs erase arm.
usage: record_box_answers_2_166.py"""
import collections
import json

VERBATIM = ("1. A large box that has 2 half notes in it. 2. Barline 3. Dot 4 4. Tio of a dot 4 - box is too small "
            "5. Dot 4 6. 2 7. Dot 4 8.Tip of a half note - box is too small 9. Tie 10. Barline 11.2 12.8")
ORDER = [3, 4, 5, 8, 9, 13, 15, 17, 20, 21, 22, 24]
SAID = ["A large box that has 2 half notes in it.", "Barline", "Dot 4", "Tio of a dot 4 - box is too small", "Dot 4",
        "2", "Dot 4", "Tip of a half note - box is too small", "Tie", "Barline", "2", "8"]
# (is a note, value in quarter beats or None, box-size problem for the detector / re-centre stage)
TRUTH = [(True, None, True), (False, None, False), (True, 1.5, False), (True, 1.5, True), (True, 1.5, False),
         (True, 2.0, False), (True, 1.5, False), (True, 2.0, True), (False, None, False), (False, None, False),
         (True, 2.0, False), (True, 0.5, False)]

key = {t["n"]: t for t in json.load(open("out/2.166/tiles-key.json"))["tiles"]}


def live(path, subjects):
    out = collections.defaultdict(list)
    for v in json.load(open(path))["record"]["verdicts"]:
        if v["subject"] in subjects and v["quantity"] in ("notehead_is_not_a_notehead", "duration"):
            out[(v["subject"], v["quantity"])].append(v)
    res = {}
    for k, ch in out.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        v = ([x for x in ch if x["id"] not in sup] or ch)[-1]
        res[k] = v
    return res


def brief(vs, g):
    nn = vs.get((g, "notehead_is_not_a_notehead"))
    du = vs.get((g, "duration"))
    refused = bool(nn and nn["outcome"] == "decided" and nn.get("value") is True)
    beats = (du.get("value") or {}).get("beats") if du and du["outcome"] == "decided" and isinstance(
        du.get("value"), dict) else None
    return dict(found=nn is not None or du is not None, refused=refused, refusal_reason=nn and nn.get("reason"),
                duration=du and du["outcome"], beats=beats, reason=du and du.get("reason"))


rows = []
for n, said, (is_note, beats, boxprob) in zip(ORDER, SAID, TRUTH):
    k = key[n]
    pre = "out/2.166/ab_%s_p%d" % (k["doc"], k["page"])
    arms = {}
    for arm in ("off", "on"):
        try:
            arms[arm] = brief(live("%s.%s.record.json" % (pre, arm), {k["subject"]}), k["subject"])
        except OSError:
            arms[arm] = None
    def judge(a):
        if not a or not a["found"]:
            return "not_found"
        if not is_note:
            return "right" if a["refused"] else "wrong"
        if a["refused"]:
            return "wrong"
        if beats is None or a["beats"] is None:
            return "kept" if a["beats"] is None else "kept_value_unscored"
        return "right" if abs(a["beats"] - beats) < 1e-6 else "wrong_value"
    rows.append(dict(n=n, doc=k["doc"], glyph=k["subject"], role=k["role"], sean=said, sean_is_note=is_note,
                     sean_beats=beats, box_size_problem=boxprob, erased_inside=k.get("erased_inside"),
                     stroke_only=k.get("stroke_only"), off=arms["off"], on=arms["on"],
                     off_score=judge(arms["off"]), on_score=judge(arms["on"])))

ans = json.load(open("out/print/2.166-review/answers.json"))
have = {t["n"] for t in ans["tiles"]}
ans["tiles"] += [dict(n=r["n"], answer=r["sean"], doc=r["doc"], glyph=r["glyph"]) for r in rows if r["n"] not in have]
ans["tiles"].sort(key=lambda t: t["n"])
ans["verbatim_boxes"] = VERBATIM
ans["via_boxes"] = "shown in the order of our tiles " + ", ".join(str(n) for n in ORDER)
ans.pop("pending", None)
json.dump(ans, open("out/print/2.166-review/answers.json", "w"), indent=1)
man = json.load(open("out/print/2.166-review/manifest.json"))
for m in man["tiles"]:
    if m["n"] in ORDER:
        k = key[m["n"]]
        m.update(doc=k["doc"], glyph=k["subject"], control=k["role"].startswith("control"), kind="head")
json.dump(man, open("out/print/2.166-review/manifest.json", "w"), indent=1)
json.dump(rows, open("out/2.166/box_answers_scored.json", "w"), indent=1)
for r in rows:
    o, a = r["off"] or {}, r["on"] or {}
    print(r["n"], r["doc"], r["glyph"], "| Sean", r["sean"], "| OFF", r["off_score"], o.get("refused"), o.get("beats"),
          "| ON", r["on_score"], a.get("refused"), a.get("beats"), "| stroke-only", r["stroke_only"])
