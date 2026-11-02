"""What happened to every far head on a 2-page ON gather: read / abstained, and the fate of the abstained ones."""
import collections
import json
import sys

for plate in ("litolff", "brahms"):
    r = json.load(open("out/2.248-r3/far2/work/%s.on.gathered.record.json" % plate))
    r = r.get("record", r)
    ab = {}
    read = set()
    for o in r["observations"]:
        if o["quantity"] == "far_head_ledger_position":
            read.add(o["subject"])
    for a in r["abstentions"]:
        if a["quantity"] == "far_head_ledger_position":
            ab[a["subject"]] = str((a.get("detail") or {}).get("ledger_reason")).split(" ")[0].split(":")[0]
    pitch = collections.defaultdict(list)
    owner = {}
    for v in r["verdicts"]:
        if v["quantity"] == "pitch":
            pitch[v["subject"]].append(v)
        if v["quantity"] == "glyph_owner":
            owner[v["subject"]] = v
    notnote = {v["subject"] for v in r["verdicts"] if v["quantity"] == "notehead_is_not_a_notehead" and v["outcome"] == "decided" and v["value"] is True}
    c = collections.Counter()
    for s, why in ab.items():
        ps = pitch.get(s) or []
        last = ps[-1] if ps else None
        if s in notnote:
            c["refused as not-a-note (no pitch written)"] += 1
        elif last is None:
            c["no pitch verdict"] += 1
        elif last["reason"] == "position_and_clef_ledger_unread":
            c["written BLUE from own-staff box centre"] += 1
        elif last["reason"].startswith("reowned"):
            c["re-owned to another staff (%s)" % last["reason"]] += 1
        else:
            c["other pitch reason: %s" % last["reason"]] += 1
    print(plate, "far read", len(read), "far abstained", len(ab))
    for k, v in sorted(c.items()):
        print("   ", k, v)
