"""ROADMAP 2.153 tile picks.
  picks_2_153.py systems DOC N          -> samples N glyphs of the A set (seed 2153) and prints their (page,system) list
  picks_2_153.py replay DOC SLICE.json OUT.json
        -> re-decides the slice with OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM off and on (faithful replay, replay_util_2_153),
           and writes picks: every glyph of the A list whose live DURATION differs between the arms ('changed'), joined
           controls (a joined beam, decided, same in both arms), plain controls (no beam, decided quarter, same in both).
Roles are NEVER drawn; they live in the hidden key only."""
import json
import os
import random
import sys

sys.path.insert(0, ".")
mode, DOC = sys.argv[1], sys.argv[2]
A = json.load(open("out/2.153/a_%s.json" % DOC))
if mode == "systems":
    n = int(sys.argv[3])
    rnd = random.Random(2153)
    pick = rnd.sample(A["a"], n)
    json.dump(pick, open("out/2.153/a_pick_%s.json" % DOC, "w"))
    print(";".join(sorted({"%s,%s" % tuple(r["glyph"].split("/")[1:3]) for r in pick})))
    sys.exit(0)

SL, OUT = sys.argv[3:5]
rec = json.load(open(SL))
from tools.omr.staged.review import rerun as RR  # noqa: E402

sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import replay_util_2_153 as RU  # noqa: E402

FLAG = "OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM"
res = {}
for arm, env in (("off", ""), ("on", "1")):
    os.environ[FLAG] = env
    log, _ = RU.rebuild(rec)
    RR.run_stages(log)
    by = {}
    for v in log.to_json()["verdicts"]:
        if v["quantity"] == "duration":
            by.setdefault(v["subject"], []).append(v)
    out = {}
    for g, ch in by.items():
        L = RU.live(ch)
        val = L["value"] if isinstance(L["value"], dict) else {}
        out[g] = dict(outcome=L["outcome"], written=val.get("written"), reason=L.get("reason"), is_rest=val.get("is_rest"),
                      cands=[c.get("value", {}).get("written") for c in (L.get("candidates") or [])] or None)
    res[arm] = out
boxes = {}
for o in rec["observations"]:
    if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px") and o["detail"].get("category") == "notehead":
        boxes[o["subject"]] = o["detail"]["bbox_page_px"]
sysset = {tuple(int(x) for x in r["glyph"].split("/")[1:3]) for pool in A.values() for r in pool}
present = {tuple(int(x) for x in g.split("/")[1:3]) for g in res["off"]}
changed, joined, plain = [], [], []
for g in res["off"]:
    a, b = res["off"][g], res["on"].get(g)
    if g not in boxes or b is None:
        continue
    same = (a["outcome"], a["written"], a["cands"] and tuple(a["cands"])) == (b["outcome"], b["written"], b["cands"] and tuple(b["cands"]))
    if not same and a["outcome"] == "decided" and not a["is_rest"]:
        changed.append(dict(glyph=g, bbox=boxes[g], base=a, arm=b))
a_set = {r["glyph"]: r for r in A["a"]}
jc = {r["glyph"]: r for r in A["joined"]}
pc = {r["glyph"]: r for r in A["plain"]}
for g, r in jc.items():
    if g in res["off"] and g in boxes and res["off"][g] == res["on"].get(g) and res["off"][g]["outcome"] == "decided":
        joined.append(dict(glyph=g, bbox=boxes[g], base=res["off"][g], arm=res["on"][g], stored=r))
for g, r in pc.items():
    if g in res["off"] and g in boxes and res["off"][g] == res["on"].get(g) and res["off"][g]["outcome"] == "decided":
        plain.append(dict(glyph=g, bbox=boxes[g], base=res["off"][g], arm=res["on"][g], stored=r))
json.dump(dict(changed=changed, joined=joined, plain=plain, changed_in_a_list=sum(1 for c in changed if c["glyph"] in a_set)),
          open(OUT, "w"), default=str)
print("systems in slice", len(present), "| notes the arm changes:", len(changed), "(in the stored A list: %d)" % sum(
    1 for c in changed if c["glyph"] in a_set), "| joined controls", len(joined), "| plain controls", len(plain))
import collections  # noqa: E402

print(collections.Counter((c["base"]["written"], tuple(c["arm"]["cands"] or ()) if c["arm"]["outcome"] == "narrowed" else c["arm"]["written"]) for c in changed).most_common(12))
