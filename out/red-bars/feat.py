"""2.230 red bars: per red bar, WHY. Loads a saved record (no re-adjudication), exports it with the exporter's own fates captured,
and writes one JSON row per red bar with everything the record knows about the bar's glyphs, the meter, and the same cell on
the other staves of the system.
usage: feat.py RECORD OUT.json PLATE PAGES"""
import json, sys, collections
from tools.omr.staged import lane_report as L, export as E
from tools.omr.staged.record_io import load_record

rec, outp, plate, pages = sys.argv[1], sys.argv[2], sys.argv[3], {int(x) for x in sys.argv[4].split(",")}
res = load_record(rec)
r = res["record"] if "record" in res else res
if "record" not in res:
    res = {"record": res, "summary": {}}
keep = lambda it: (lambda pg: pg is None or pg in pages)(L.page_of(it.get("subject")))
for k in ("observations", "abstentions", "verdicts"):
    r[k] = [x for x in r[k] if keep(x)]

captured = {}
orig = E._attach_unplaced
def cap(rec_, runs, fates):
    captured.update(fates)
    return orig(rec_, runs, fates)
E._attach_unplaced = cap
xml, report = E.to_musicxml(res)
E._attach_unplaced = orig

box = {}      # glyph -> dict
pos = {}
for o in r["observations"]:
    q, s = o["quantity"], o["subject"]
    if q == "glyph_box":
        d = o.get("detail") or {}
        box[s] = dict(cls=o["value"][0], reader=o.get("reader"), page_box=d.get("bbox_page_px"), xc=d.get("x_center_page"),
                      yc=d.get("y_center_page"), score=o.get("score"), cat=d.get("category"))
    elif q == "notehead_staff_position":
        pos[s] = o["value"]
dur, notnote, own, ev, voices, meter = {}, {}, {}, {}, {}, {}
for v in r["verdicts"]:
    q, s = v["quantity"], v["subject"]
    if q == "duration" and v["outcome"] in ("decided", "narrowed"):
        dur[s] = dict(outcome=v["outcome"], reason=v["reason"], value=v.get("value"))
    elif q == "duration":
        dur.setdefault(s, dict(outcome=v["outcome"], reason=v["reason"], value=None))
    elif q == "notehead_is_not_a_notehead":
        notnote[s] = (v["outcome"], v["reason"])
    elif q == "glyph_owner":
        own[s] = v.get("value")
    elif q == "event":
        ev[s] = v.get("value")
    elif q == "voices":
        voices[s] = (v["outcome"], v["reason"], v.get("value"))
    elif q == "meter":
        meter[s] = dict(reason=v["reason"], outcome=v["outcome"], value=v.get("value"))

staves_in_system = collections.defaultdict(set)
for s in ev:
    p = s.split("/")
    staves_in_system[(int(p[1]), int(p[2]))].add(int(p[3]))

red = report["bars_written_red"]["bars_list"]
pbars = {(b["page"], b["system"], b["staff"], b["cell"]): b for b in report["partial_bars"]["bars"]}
byc = collections.defaultdict(list)
for b in red:
    byc[(b["page"], b["system"], b["cell"])].append(b)
cellg = collections.defaultdict(list)   # glyph fates by cell
for sub, reason in captured.items():
    p = sub.split("/")
    cellg[tuple(int(x) for x in p[1:5])].append((sub, reason))

out = []
for b in red:
    key = (b["page"], b["system"], b["staff"], b["cell"])
    pb = pbars.get(key, {})
    rows = []
    for row in b["rows"]:
        g = row["glyph"]
        bx = box.get(g, {})
        rows.append(dict(kind=row["kind"], beats=row["beats"], pitch=row.get("pitch"), type=row.get("type"), status=row["status"],
                         measure_rest=row.get("measure_rest"), glyph=g, cls=bx.get("cls"), reader=bx.get("reader"), xc=bx.get("xc"),
                         yc=bx.get("yc"), page_box=bx.get("page_box"), staffpos=pos.get(g),
                         dur=dur.get(g), notnote=notnote.get(g), owner=own.get(g)))
    others = [o for o in byc[(b["page"], b["system"], b["cell"])] if o["staff"] != b["staff"]]
    sysm = meter.get("system/%d/%d" % (b["page"], b["system"]))
    cellsub = "cell/%d/%d/%d/%d" % key
    fates = [(s.split("/", 5)[5], box.get(s, {}).get("cls"), rsn) for s, rsn in cellg.get(key, [])]
    out.append(dict(key="%d/%d/%d/%d" % key, page=b["page"], system=b["system"], staff=b["staff"], cell=b["cell"], part=b["part"],
                    want=b["want_quarters"], counted=b["counted_quarters"], two_voice=b["two_voice"], doubled=b["doubled_staff_copy"],
                    why=pb.get("why"), status=pb.get("status"), unread_glyphs=pb.get("unread_glyphs"), rows=rows, fates=fates,
                    meter=sysm, n_staves=len(staves_in_system[(b["page"], b["system"])]),
                    others_red=[dict(staff=o["staff"], counted=o["counted_quarters"], want=o["want_quarters"]) for o in others],
                    voices=voices.get(cellsub), event=ev.get(cellsub)))
json.dump(out, open(outp, "w"), default=str)
print(plate, len(out), "red bars written to", outp)
