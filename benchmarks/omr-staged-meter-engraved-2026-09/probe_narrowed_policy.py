"""What a NARROWED duration does to a bar sum — three policies, one record.

⚠️ OFFLINE, ON A SAVED STAGED RECORD. No re-transcription, so nothing here is
detector jitter: the same 428 duration verdicts are re-consumed three ways.

⚠️ IT DEMONSTRATES A MECHANISM, IT DOES NOT PROPOSE A FIX. "Take the lowest
candidate" fixes the dense page (0 correct of 1 -> 4 of 4) and makes the mixed
page WORSE (3 of 5 -> 2 of 4). A policy that fixes one page and breaks another
is a fudge that fits. See FINDINGS.md §6: the repair is upstream, in beam
detection, because `beam_evidence: "none_over_this_note"` on a CLEAN ENGRAVING
is a detection failure and a note whose beam is missed reads too long.

    python3 benchmarks/omr-staged-meter-engraved-2026-09/probe_narrowed_policy.py <staged.json>
"""
import json
from collections import Counter

import sys
rec = json.load(open(sys.argv[1] if len(sys.argv) > 1
                    else "/tmp/fixed-e209A-OFF.json"))["record"]
dur = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "duration"}
events = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "event"}
rests = {o["subject"] for o in rec["observations"]
         if o["quantity"] == "rest" and o["value"] == "restWhole"}

def beats(v, policy):
    if v is None: return None
    if v["outcome"] == "decided":
        return (v.get("value") or {}).get("beats")
    c = v.get("candidates") or []
    if not c: return None
    vals = [(x.get("value") or {}).get("beats") for x in c]
    vals = [x for x in vals if x is not None]
    if not vals: return None
    if policy == "top":    return vals[0]
    if policy == "lowest": return min(vals)
    if policy == "drop":   return None
    raise ValueError(policy)

TRUTH = 4.0   # page 2 = excerpt bars 13-16 = original 215-218, all 4/4
for policy in ("top", "lowest", "drop"):
    bars = {}
    for key, ev in events.items():
        if not key.startswith("cell/2/") or ev["outcome"] != "decided": continue
        _, p, sy, st, ce = key.split("/")
        gl = lambda i: f"glyph/{p}/{sy}/{st}/{ce}/{i}"
        evs = (ev.get("value") or {}).get("events") or []
        if any(gl(i) in rests for e in evs for i in (e.get("glyphs") or [])):
            continue
        total = 0.0
        for e in evs:
            bs = [beats(dur.get(gl(i)), policy) for i in (e.get("glyphs") or [])]
            bs = [b for b in bs if b]
            if bs: total += Counter(bs).most_common(1)[0][0]
        if total > 0:
            bars.setdefault(int(ce), []).append(round(total, 4))
    out = []
    for ce in sorted(bars):
        L = bars[ce]
        mode, n = Counter(L).most_common(1)[0]
        ok = len(L) >= 3 and n / len(L) >= 0.5
        if ok: out.append((ce, mode, f"{n}/{len(L)}"))
    right = sum(1 for _, m, _ in out if abs(m - TRUTH) < 1e-6)
    print(f"{policy:7s} -> assessable {len(out)}, correct {right}: {out}")
