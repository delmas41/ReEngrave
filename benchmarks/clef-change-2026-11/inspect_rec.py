"""2.251: the page-wide clef rows of a record, and which head / rest verdicts cite them."""
import json, sys
rec = json.load(open(sys.argv[1]))["record"]
obs = rec["observations"]
ab = rec.get("abstentions", [])
rows = [o for o in obs if o["quantity"] == "claimed_area" and (o.get("detail") or {}).get("source") == "clef_pagewide"]
ids = {o["id"]: o for o in rows}
for o in rows:
    d = o["detail"]
    print("CLAIM", o["subject"], d.get("cell"), [round(v) for v in o["value"]], "change" if d.get("change") else "header", d.get("family"),
          d.get("kind"), d.get("witnesses"), "boxes_inside", len(d.get("boxes_inside") or {}))
near = [a for a in ab if a.get("quantity") == "claimed_area" and (a.get("detail") or {}).get("source") == "clef_pagewide"]
for a in near:
    d = a["detail"]
    print("NEAR", a["subject"], d.get("why"), d.get("family"), d.get("x_page"), d.get("detector_box"))
n = 0
for v in rec["verdicts"]:
    used = set(v.get("basis") or ()) | set(v.get("considered") or ())
    hit = used & set(ids)
    if hit:
        n += 1
        if v["quantity"] != "pitch":
            print("CITES", v["quantity"], v["subject"], v["outcome"], v.get("reason"), v.get("value"))
print("verdicts citing a page-wide clef:", n)
