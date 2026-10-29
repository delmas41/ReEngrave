"""2.222 m0: every note WRITTEN in an arm's exported file (lane_report symbols.json, matched to its box by the host's own glyph
subject), and that box's Q.HEAD_INK reading (2.220) + the detector's own score and reader. FILE level.
usage: m0_census.py SLICES_DIR SYMBOLS_JSON OUT_JSON"""
import collections, json, sys

sl, sym, out = sys.argv[1:4]
hi, gb = {}, {}
for kind in ("observations", "abstentions"):
    for line in open("%s/%s.jsonl" % (sl, kind)):
        if '"head_ink"' not in line and '"glyph_box"' not in line:
            continue
        o = json.loads(line)
        q = o.get("quantity")
        if q == "head_ink":
            d = dict(o.get("detail") or {})
            d["value"], d["reason"] = o.get("value"), o.get("reason")
            hi[o["subject"]] = d
        elif q == "glyph_box" and "value" in o:
            gb[o["subject"]] = {"cls": o["value"][0], "score": o.get("score"), "reader": o.get("reader"),
                                "page_box": (o.get("detail") or {}).get("bbox_page_px")}
S = json.load(open(sym))
rows = []
for h in S["hosts"]:
    if h.get("kind") != "note":
        continue
    s = h.get("rg")
    r = hi.get(s) or {}
    g = gb.get(s) or {}
    rows.append(dict(sub=s, page=h["page"], cx=h["cx"], cy=h["cy"], box=h.get("box"), type=h.get("type"), pitch=h.get("pitch"),
                     blue=h.get("blue"), chord=h.get("chord"), noh=r.get("not_one_head"), hi_reason=r.get("reason"),
                     hi_value=r.get("value"), extent=r.get("extent_sp"), margin=r.get("size_margin_sp"), fs=r.get("foreign_share"),
                     score=g.get("score"), reader=g.get("reader"), cls=g.get("cls"), has_hi=bool(r)))
json.dump(rows, open(out, "w"))
c = collections.Counter((r["noh"] or ("-" if r["has_hi"] else "NO_ROW")) for r in rows)
print(sym, "written notes", len(rows), dict(c))
by = collections.defaultdict(list)
for r in rows:
    if r["noh"]:
        by[r["noh"]].append(r["score"] or 0)
for k, v in by.items():
    v.sort()
    print("  %-26s n=%4d score median %.2f  <0.5: %d" % (k, len(v), v[len(v) // 2], sum(1 for x in v if x < 0.5)))
ok = sorted(r["score"] or 0 for r in rows if r["has_hi"] and not r["noh"])
if ok:
    print("  one head                   n=%4d score median %.2f  <0.5: %d" % (len(ok), ok[len(ok) // 2], sum(1 for x in ok if x < 0.5)))
print("  readers of not_one_head:", dict(collections.Counter(r["reader"] for r in rows if r["noh"])))
