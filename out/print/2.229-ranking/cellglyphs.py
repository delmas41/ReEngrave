"""2.229: list the glyph rows, verdicts and abstentions the slice holds for one cell. usage: cellglyphs.py SLICEDIR PLATE page/system/staff/cell"""
import json, sys
sl, plate, k = sys.argv[1:4]
pre = "glyph/%s/" % k
for kind in ("observations", "verdicts", "abstentions"):
    for l in open("%s/%s/%s.jsonl" % (sl, plate, kind)):
        if pre in l or ('"subject": "cell/%s"' % k) in l:
            o = json.loads(l)
            if not (o.get("subject") or "").startswith((pre, "cell/" + k)):
                continue
            if kind == "observations" and o["quantity"] not in ("glyph_box", "ink", "cell_ink_pieces", "cell_box", "unboxed_ink"):
                continue
            print(kind[:3], o["subject"], o["quantity"], str(o.get("value"))[:80], o.get("outcome", ""), o.get("reason", ""))
