"""Re-owned far heads (move_glyph, EVALUATE): the step written from the band geometry on the NEW staff vs the ledger reading toward that
staff (far_head_owner_ledger), on the whole-movement night slices.  usage: reowned.py PLATE"""
import collections
import json
import sys

S = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night/%s/" % sys.argv[1]
band, led, owner, pitch, nan = {}, collections.defaultdict(dict), {}, {}, set()
for line in open(S + "observations.jsonl"):
    if '"glyph_band_distance"' in line or '"far_head_owner_ledger"' in line:
        o = json.loads(line)
        d = o["detail"]
        if o["quantity"] == "glyph_band_distance":
            band[(o["subject"], d["candidate"])] = d.get("position_in_candidate")
        elif isinstance(o["value"], (int, float)):
            led[o["subject"]][d["candidate"]] = (o["value"], d.get("ledger_reason"))
for line in open(S + "verdicts.jsonl"):
    if '"glyph_owner"' not in line and '"move_glyph"' not in line and '"notehead_is_not_a_notehead"' not in line:
        continue
    v = json.loads(line)
    if v["quantity"] == "glyph_owner" and v["outcome"] == "decided":
        owner[v["subject"]] = (v["value"], v["reason"])
    elif v["quantity"] == "pitch" and v.get("decider") == "move_glyph":
        pitch[v["subject"]] = (v["value"], v["reason"])
    elif v["quantity"] == "notehead_is_not_a_notehead" and v["outcome"] == "decided" and v["value"] is True:
        nan.add(v["subject"])
c = collections.Counter()
ex = []
for s, (ow, owhy) in owner.items():
    if not isinstance(ow, str) or ow == "staff/" + "/".join(s.split("/")[1:4]) or s in nan:
        continue
    pv = owhy
    if (s, ow) not in band:
        c["reowned by ledger reading (no band row)"] += 1
        continue
    geo = band.get((s, ow))
    g = int(round(geo)) if geo is not None else None
    far = g is not None and (g < -1 or g > 9)
    lp = led.get(s, {}).get(ow)
    if not far:
        c["reowned, in staff / first space"] += 1
    elif lp is None:
        c["reowned FAR, no ledger reading toward owner"] += 1
    elif int(lp[0]) == g:
        c["reowned FAR, ledger agrees"] += 1
    else:
        c["reowned FAR, ledger DISAGREES (written from geometry)"] += 1
        ex.append((s, ow, round(geo, 2), lp[0], lp[1], pv))
print(sys.argv[1], dict(c))
for e in ex[:40]:
    print("   ", e)
