"""2.181: OFF vs ON from replay_2_181.py output. usage: compare_2_181.py DOC OUTDIR
Prints per plate: boxes refused / narrowed by owner, parity with the subsumed rules, notes in the file, red bars, bars that add up,
the must-keep controls, and writes OUTDIR/DOC.diff.json (every changed glyph, for crops and tiles)."""
import collections
import json
import sys

DOC, OUT = sys.argv[1], sys.argv[2]
off = json.load(open("%s/%s.off.json" % (OUT, DOC)))
on = json.load(open("%s/%s.on.json" % (OUT, DOC)))
SUBSUMED = {"is_a_clef", "on_another_symbols_box", "on_the_staffs_leading_barline", "inside_the_meter"}
#: real heads the old rules were built to keep (2.176 FINDINGS §3 guards, Sean's 2.176 controls)
MUST_KEEP = {"brahms": ["glyph/6/0/3/0/20"], "litolff": ["glyph/9/0/3/11/1", "glyph/16/1/7/2/6"]}


def owner(reason):
    return reason.split(":", 1)[1] if reason and ":" in reason else None


print("== %s ==" % DOC)
print("notes in file: off", off["notes_in_xml"], "on", on["notes_in_xml"], "delta", on["notes_in_xml"] - off["notes_in_xml"])
print("blue notes in file: off", off["blue_in_xml"], "on", on["blue_in_xml"])
for k in ("red_bars", "guessed"):
    print(k, "off", json.dumps(off["coverage"].get(k), default=str)[:300])
    print(k, "on ", json.dumps(on["coverage"].get(k), default=str)[:300])
ref_on = collections.Counter(v[1] for v in on["refusals"].values() if str(v[1]).startswith("claimed_by:"))
rref_on = collections.Counter(v[1] for v in on["rest_refusals"].values() if str(v[1]).startswith("claimed_by:"))
print("heads refused by owner (ON):", dict(ref_on))
print("rests refused by owner (ON):", dict(rref_on))
print("heads narrowed by owner (ON):", dict(collections.Counter(v[0] for v in on["narrowed"].values() if str(v[0]).startswith("claim_"))))
print("rests narrowed by owner (ON):", dict(collections.Counter(v[0] for v in on["rest_narrowed"].values() if str(v[0]).startswith("claim_"))))
print("heads refused: off", len(off["refusals"]), "on", len(on["refusals"]))
new_ref = {g: v for g, v in on["refusals"].items() if g not in off["refusals"]}
gone_ref = {g: v for g, v in off["refusals"].items() if g not in on["refusals"]}
print(" newly refused", len(new_ref), dict(collections.Counter(v[1] for v in new_ref.values())))
print(" no longer refused", len(gone_ref), dict(collections.Counter(v[1] for v in gone_ref.values())))
# parity: every box a subsumed rule refused OFF is refused or narrowed ON
par = collections.Counter()
diffs = []
for g, v in off["refusals"].items():
    if v[1] not in SUBSUMED:
        continue
    if g in on["refusals"]:
        par[(v[1], "refused:" + str(on["refusals"][g][1]))] += 1
    elif g in on["narrowed"]:
        par[(v[1], "narrowed:" + str(on["narrowed"][g][0]))] += 1
        diffs.append((g, v[1], "narrowed", on["narrowed"][g]))
    else:
        par[(v[1], "KEPT AS A HEAD")] += 1
        diffs.append((g, v[1], "kept", None))
for g, v in off["rest_refusals"].items():
    if v[1] in ("inside_the_meter",) or (v[1] == "rest_is_a_barline" and g.split("/")[4] == "0"):
        st = ("refused:" + str(on["rest_refusals"][g][1])) if g in on["rest_refusals"] else (
            "narrowed" if g in on["rest_narrowed"] else "KEPT AS A REST")
        par[("rest:" + v[1] + (":cell0" if v[1] == "rest_is_a_barline" else ""), st)] += 1
print("parity (OFF reason -> ON):")
for k, n in sorted(par.items()):
    print("  ", k, n)
rest_new = {g: v for g, v in on["rest_refusals"].items() if g not in off["rest_refusals"]}
rest_gone = {g: v for g, v in off["rest_refusals"].items() if g not in on["rest_refusals"]}
print("rests: newly refused", len(rest_new), dict(collections.Counter(v[1] for v in rest_new.values())),
      "restored", len(rest_gone), dict(collections.Counter(v[1] for v in rest_gone.values())))
lost = [g for g, v in off["glyphs"].items() if not v["rest"] and v["outcome"] == "decided" and g in new_ref]
print("decided notes (OFF, not refused) newly refused ON:", len(lost))
newly_narrowed = {g: v for g, v in on["narrowed"].items() if g not in off["refusals"]}
print("newly narrowed (were plain heads OFF):", len(newly_narrowed), dict(collections.Counter(v[0] for v in newly_narrowed.values())))
for g in MUST_KEEP.get(DOC, []):
    print(" must-keep", g, "OFF:", off["refusals"].get(g, "kept"), "ON:", on["refusals"].get(g) or on["narrowed"].get(g, "kept"))
for k in ("bars_held_out_sum", "partial_bars"):
    print(k, "off", json.dumps(off["coverage"].get(k), default=str)[:200])
    print(k, "on ", json.dumps(on["coverage"].get(k), default=str)[:200])
cl = collections.Counter((c["owner"], c["standing"], c.get("right_edge") or c.get("source")) for c in on["claims"])
print("claims (ON):", dict(cl))
json.dump(dict(new_refused=new_ref, gone_refused=gone_ref, rests_new=rest_new, rests_restored=rest_gone, lost=lost,
               newly_narrowed=newly_narrowed, narrowed=on["narrowed"], rest_narrowed=on["rest_narrowed"], parity_diffs=diffs,
               claimed=on["claimed"]),
          open("%s/%s.diff.json" % (OUT, DOC), "w"), default=str)
