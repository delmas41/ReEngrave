"""2.185: stream a whole-movement record (ijson, never whole) and keep what the double-box census needs.
usage: extract.py RECORD.json OUT.json
  boxes    : every glyph_box row (id, subject, class, score, reader, source/view/witness/..., bbox_page_px)
  mark_group: subject -> [group id, family] (gather MARK_GROUP, IoU>0.3 components over notehead/rest/accidental)
  verdicts : ADJUDICATE verdicts about whether a box is a thing (`*_is_not_a*`), whole-rest reading, ownership, duration, dot role,
             rest-ink readings -- with `supersedes`, so the STANDING verdict can be found (readout.adjudicate_status's own rule)."""
import json, sys, ijson, time
rec, out = sys.argv[1:3]
t0 = time.time()
KEEPQ = {"notehead_is_a_whole_rest", "glyph_owner", "duration", "dot_role", "head_ink_is_a_rest", "unboxed_ink_is_a_rest",
         "notehead_is_an_eighth_rest", "rest", "aug_dot"}
DKEYS = ("duplicate_of", "duplicate_disagrees_with", "overlaps", "contested_with")
boxes = []
mg = {}
with open(rec, "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        if o.get("quantity") == "mark_group":
            mg[o["subject"]] = [o["value"], (o.get("detail") or {}).get("family")]
            continue
        if o.get("quantity") != "glyph_box":
            continue
        d = o.get("detail") or {}
        v = o.get("value")
        boxes.append(dict(id=o["id"], subject=o["subject"], cls=v[0] if isinstance(v, list) and v else None,
                          score=o.get("score"), reader=o.get("reader"), bbox=d.get("bbox_page_px"), cat=d.get("category"),
                          source=d.get("source"), view=d.get("view"), witness=d.get("witness"), family=d.get("family"),
                          end=d.get("end"), from_record_box=d.get("from_record_box"), read_as=d.get("read_as")))
print("boxes", len(boxes), round(time.time() - t0), "s", flush=True)
verd = []
with open(rec, "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        q = v.get("quantity")
        if "_is_not_a" in q or q in KEEPQ:
            d = v.get("detail") or {}
            val = v.get("value")
            if isinstance(val, (list, dict)) and len(json.dumps(val)) > 400:
                val = "<big>"
            verd.append(dict(id=v["id"], subject=v["subject"], quantity=q, outcome=v.get("outcome"), value=val,
                             reason=v.get("reason"), decider=v.get("decider"), supersedes=v.get("supersedes"),
                             detail={k: d[k] for k in DKEYS if k in d}))
print("verdicts", len(verd), round(time.time() - t0), "s", flush=True)
json.dump(dict(boxes=boxes, verdicts=verd, mark_group=mg), open(out, "w"))
