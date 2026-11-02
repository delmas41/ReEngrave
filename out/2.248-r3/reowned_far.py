"""Of the heads move_glyph re-pitched through `reowned` (band-distance geometry on the new staff), how many sit FAR in the new staff
(position < -1 or > 9), and for those, was a ledger reading toward that staff on the record (and did it agree)?"""
import collections
import json

for plate in ("litolff", "brahms"):
    r = json.load(open("out/2.248-r3/far2/work/%s.on.gathered.record.json" % plate))
    r = r.get("record", r)
    band = collections.defaultdict(list)
    led = collections.defaultdict(dict)
    for o in r["observations"]:
        d = o.get("detail") or {}
        if o["quantity"] == "glyph_band_distance":
            band[o["subject"]].append(d)
        if o["quantity"] == "far_head_owner_ledger":
            led[o["subject"]][d.get("candidate")] = o["value"]
    c = collections.Counter()
    for v in r["verdicts"]:
        if v["quantity"] == "pitch" and v["reason"] == "reowned":
            s = v["subject"]
            own = [x for x in (v.get("basis") or [])]
            ow = next((x for x in r["verdicts"] if x["id"] in own and x["quantity"] == "glyph_owner"), None)
            cand = ow["value"] if ow else None
            b = [d for d in band[s] if d.get("candidate") == cand]
            pos = b[0].get("position_in_candidate") if b else None
            if pos is None:
                c["no band pos"] += 1
                continue
            far = pos < -1 or pos > 9
            if not far:
                c["in-staff on the new staff"] += 1
            else:
                lp = led[s].get(cand)
                c["FAR on the new staff, ledger reading toward it: %s" % ("none" if lp is None else ("agrees" if int(lp) == int(round(pos)) else "DISAGREES"))] += 1
    print(plate, dict(c))
