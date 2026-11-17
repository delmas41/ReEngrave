"""OFF arm, bucket 5: where does the OLD path lose each printed arc?  For its detector boxes -> `system_arc` curve (join_traces) -> anchors (the notes the curve was bound to) / tie_pair.
Reports the curve's verdict (`value`: why it is or is not anchored), whether the anchors sit at the printed ends, and the export's refusal if the anchors were right."""
import json
import collections
from load import *  # noqa

C = json.load(open("buckets.json"))
rec = record("off")
gb = {o["subject"]: ((o["detail"]["bbox_page_px"][0] + o["detail"]["bbox_page_px"][2]) / 2) for o in rec["observations"] if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/0/")}
sysarc = {o["subject"]: o for o in rec["observations"] if o["quantity"] == "system_arc" and o["subject"].startswith("glyph/0/")}
tp = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "tie_pair" and v["subject"].startswith("glyph/0/")}
cnt = collections.Counter()
for c in C:
    if c["bucket_off"] != "5":
        continue
    seen = []
    for sub, val in c["curves"]:
        o = sysarc.get(sub)
        if not o:
            continue
        d = o["detail"]
        al, ar = d.get("anchor_left"), d.get("anchor_right")
        okl = al in gb and abs(gb[al] - c["x0"]) / SP <= REACH
        okr = ar in gb and abs(gb[ar] - c["x1"]) / SP <= REACH
        seen.append((val, "L" if okl else "-", "R" if okr else "-", d.get("pieces") and len(d["pieces"])))
    t = [tp[b]["value"] for b in c["boxes_kept"] if b in tp and tp[b]["value"]]
    why = collections.Counter(s[0] for s in seen)
    anchored_ok = any(s[1] == "L" and s[2] == "R" for s in seen)
    k = "curve anchors both right (lost later)" if anchored_ok else ("no curve (box unjoined)" if not seen else "curve anchored wrong/none: " + "/".join(sorted(why)))
    cnt[k] += 1
    print("P%-3d %-5s %-4s boxes kept %d  curves %s  tie_pair %s -> %s" % (c["n"], c["staff"], c["kind"], len(c["boxes_kept"]), seen[:3], t[:1], k))
for k, v in cnt.most_common():
    print(v, k)
