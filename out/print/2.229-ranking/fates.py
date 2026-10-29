"""2.229: why is a bar 'unread empty'? Export a saved record's own verdicts (as export_saved.py does) while capturing `_place_notes`'
per-glyph `fates` (the exporter's own ledger: written / the refusal reason), then for every unread-empty bar list its glyphs'
classes and fates and sort the bar into a kind.
usage: fates.py RECORD OUTJSON PLATE PAGES"""
import json, sys, collections, pathlib
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
cls = {}
for o in r["observations"]:
    if o.get("quantity") == "glyph_box":
        cls[o["subject"]] = o["value"][0]
captured = {}
orig = E._attach_unplaced
def cap(rec_, runs, fates):
    captured.update(fates)
    return orig(rec_, runs, fates)
E._attach_unplaced = cap
xml, report = E.to_musicxml(res)
E._attach_unplaced = orig
bars = report["unread_empty_bars"]["list"]
bycell = collections.defaultdict(list)
for sub, reason in captured.items():
    p = sub.split("/")                     # glyph/page/system/staff/cell/idx
    bycell[tuple(int(x) for x in p[1:5])].append((sub, cls.get(sub, "?"), reason))
HEAD = ("notehead",)
out = []
for b in bars:
    key = (b["page"], b["system"], b["staff"], b["cell"])
    gl = [g for g in bycell.get(key, []) if g[1].startswith(("notehead", "rest"))]
    reasons = sorted({g[2] for g in gl})
    if not gl:
        kind = "no_head_or_rest_glyph"
    elif any(g[2] == "ink_is_a_whole_rest" for g in gl):
        kind = "whole_rest_ink_refused"
    elif all(g[2].startswith("not_a_") for g in gl) or all(g[2] in ("mark_group_duplicate",) for g in gl):
        kind = "all_glyphs_judged_not_symbols"
    elif any(g[2] == "owned_by_another_staff" for g in gl):
        kind = "heads_owned_by_another_staff"
    elif any(g[2] == "no_pitch" for g in gl):
        kind = "head_has_no_pitch"
    elif any("duration" in g[2] or "rest_duration" in g[2] for g in gl):
        kind = "value_undecided"
    else:
        kind = "other:" + "+".join(reasons)
    out.append(dict(key="%d/%d/%d/%d" % key, kind=kind, glyphs=[(g[0].split("/", 5)[5], g[1], g[2]) for g in gl]))
cnt = collections.Counter(o["kind"] for o in out)
perpage = collections.defaultdict(collections.Counter)
for o, b in zip(out, bars):
    perpage[b["page"]][o["kind"]] += 1
json.dump(dict(counts=cnt, per_page={str(k): v for k, v in perpage.items()}, bars=out), open(outp, "w"), default=str)
print(plate, "unread bars", len(bars), dict(cnt))
for pg in sorted(perpage): print(" page", pg, dict(perpage[pg]))
