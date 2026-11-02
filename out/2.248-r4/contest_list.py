"""List the SPACE-CONTESTED far heads (reader: space beyond ledger n; cv_ledger: a ledger at step n+1) with their boxes."""
import json, sys, collections
S = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night/%s/observations.jsonl"
plate = sys.argv[1]
far, rung, box = {}, collections.defaultdict(dict), {}
for line in open(S % plate):
    if '"far_head_ledger_position"' in line or '"ledger_rung_ink"' in line or '"glyph_box"' in line:
        o = json.loads(line)
        q = o["quantity"]
        if q == "far_head_ledger_position":
            far[o["subject"]] = o
        elif q == "ledger_rung_ink":
            rung[(o["subject"], o["detail"]["candidate"])][o["detail"]["step"]] = o["value"]
        else:
            box[o["subject"]] = o["detail"].get("bbox_page_px")
for s, o in sorted(far.items()):
    p = int(o["value"]); dist = -p if p < 0 else (p - 8 if p > 8 else None)
    if dist is None or dist % 2 == 0:
        continue
    st = "staff/" + "/".join(s.split("/")[1:4])
    if rung.get((s, st), {}).get(dist // 2 + 1):
        print(s, p, [round(v) for v in box[s]], o["detail"]["ledger_reason"])
