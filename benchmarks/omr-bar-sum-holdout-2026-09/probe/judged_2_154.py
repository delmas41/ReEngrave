"""ROADMAP 2.154 -- BEFORE BUILDING: on Sean's judged tiles, what does each bar-sum decider give, right or wrong, and who loses a
right value if it goes confirm-only? STAGED EVALUATE/INFER, read from a stored record (no replay).

For every judged duration tile (`benchmarks/acceptance/judged-tiles.json`, scored by `tools.omr.staged.judged`'s own comparator)
whose standing duration chain contains a bar-sum verdict, score three standings:
  base  -- the record as it is;
  arm a -- every bar verdict that PICKED from a NARROWING is undone (the chain stands at the narrowing it superseded);
  arm b -- arm a, and every bar verdict that MOVED a DECIDED value is undone too.
A static undo: it does not re-run the bar, so a later rule that fed on the undone value is not reproduced (the replay does that).
usage: judged_2_154.py DOC RECORD_KEY OUT.json     (RECORD_KEY in rec.RECORDS)
"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
sys.path.insert(0, ".")
import rec  # noqa: E402
from tools.omr.staged import judged  # noqa: E402

DOC, KEY, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
BAR = ("reconcile_duration", "infer:collapse_bare_stem_by_bar", "infer:collapse_narrowed_by_bar")
path = pathlib.Path(rec.RECORDS[KEY])
index = json.load(open("benchmarks/acceptance/judged-tiles.json"))
rows = [r for r in index["tiles"] if not r["followup"] and r["subject_kind"] == "glyph"
        and r["question_kind"] not in judged._NOT_SCORED_QUESTIONS and r["answer_kind"] == "duration"
        and r["value"] is not None]
# tiles naming no document: resolved onto this record by page box, as `judged.score` does
unknown = [r for r in rows if r["doc"] is None and r["page_box"]]
with rec.lock():
    boxes = judged.page_boxes(path, {s for r in unknown for s in (r["subjects"] or [r["subject"]])})
    mine = [r for r in rows if r["doc"] == DOC or (r["doc"] is None and r["page_box"] and all(
        s in boxes and judged.box_matches(boxes[s], r["page_box"]) for s in (r["subjects"] or [r["subject"]])))]
    subs = {s for r in mine for s in (r["subjects"] or [r["subject"]])}
    allv = collections.defaultdict(list)
    for v in judged.iter_verdicts(path):
        if v.get("subject") in subs and v.get("quantity") in ("duration", "notehead_is_not_a_notehead"):
            allv[(v["subject"], v["quantity"])].append({k: v.get(k) for k in (
                "id", "subject", "quantity", "outcome", "value", "decider", "reason", "margin", "supersedes", "candidates",
                "detail")})


def standing(vs):
    sup = {x["supersedes"] for x in vs if x.get("supersedes")}
    live = [x for x in vs if x["id"] not in sup] or vs
    return live[-1]


S = {"base": {}, "a": {}, "b": {}}
bar_kind = {}
for key, vs in allv.items():
    st = standing(vs)
    for arm in S:
        S[arm][key] = st
    if key[1] != "duration":
        continue
    byid = {x["id"]: x for x in vs}
    cur = st
    while cur is not None:                      # the newest bar verdict in the chain
        if cur.get("decider") in BAR:
            prior = byid.get(cur.get("supersedes"))
            kind = "PICK" if prior and prior["outcome"] == "narrowed" else "MOVE"
            bar_kind[key[0]] = (cur["decider"], kind)
            if prior is not None:
                S["b"][key] = prior
                if kind == "PICK":
                    S["a"][key] = prior
            break
        cur = byid.get(cur.get("supersedes"))

out = []
tally = collections.Counter()
for r in mine:
    sb = r["subjects"] or [r["subject"]]
    hit = [bar_kind[s] for s in sb if s in bar_kind]
    if not hit:
        continue
    res = {arm: judged.score_row(r, S[arm])[:2] for arm in S}
    dec, kind = hit[0]
    tally[(dec, kind, res["base"][0], res["a"][0], res["b"][0])] += 1
    out.append(dict(item=r["item"], tile=r["tile"], subject=r["subject"] or r["subjects"], answer=r["answer"], decider=dec,
                    kind=kind, base=res["base"], arm_a=res["a"], arm_b=res["b"]))
json.dump(dict(doc=DOC, record=KEY, judged_duration_tiles=len(mine), tiles=out), open(OUT, "w"), indent=1)
print(KEY, "judged duration tiles on this record:", len(mine), "touched by a bar verdict:", len(out))
for k, n in sorted(tally.items()):
    print("%4d  %-36s %-4s base=%-9s a=%-9s b=%s" % ((n,) + k))
