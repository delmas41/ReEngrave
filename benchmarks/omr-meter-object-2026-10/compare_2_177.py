"""2.177: OFF vs ON from replay_2_177.py output. usage: compare_2_177.py DOC OUTDIR [DOSSIER_JSON]
Prints per plate: objects found vs expected, numbers read vs dossier, boxes newly refused (by class/reason), rests restored / newly refused,
notes in the file, and writes OUTDIR/DOC.diff.json with every newly refused glyph key and every restored rest."""
import collections
import json
import sys

DOC, OUT = sys.argv[1], sys.argv[2]
off = json.load(open("%s/%s.off.json" % (OUT, DOC)))
on = json.load(open("%s/%s.on.json" % (OUT, DOC)))
print("notes in file: off", off["notes_in_xml"], "on", on["notes_in_xml"], "delta", on["notes_in_xml"] - off["notes_in_xml"])
print("held bars: off", len(off["held_bars"]), "on", len(on["held_bars"]))
new_ref = {g: v for g, v in on["refusals"].items() if g not in off["refusals"]}
gone_ref = {g: v for g, v in off["refusals"].items() if g not in on["refusals"]}
print("heads refused: off", len(off["refusals"]), "on", len(on["refusals"]), "newly refused", len(new_ref), "no longer refused", len(gone_ref))
print(" new reasons:", dict(collections.Counter(v[1] for v in new_ref.values())))
ins = {g: v for g, v in on["refusals"].items() if v[1] == "inside_the_meter"}
print(" inside_the_meter (heads):", len(ins), " of which previously refused for another reason:", sum(1 for g in ins if g in off["refusals"]))
rest_new = {g: v for g, v in on["rest_refusals"].items() if g not in off["rest_refusals"]}
rest_restored = {g: v for g, v in off["rest_refusals"].items() if g not in on["rest_refusals"]}
print("rests refused: off", len(off["rest_refusals"]), "on", len(on["rest_refusals"]), "newly", len(rest_new), "restored", len(rest_restored))
print(" restored reasons (OFF reason):", dict(collections.Counter(v[1] for v in rest_restored.values())))
print(" new rest reasons:", dict(collections.Counter(v[1] for v in rest_new.values())))
# notes lost: a glyph decided (not rest) in OFF and not refused, now refused or no longer decided
lost = []
for g, v in off["glyphs"].items():
    if v["rest"] or v["measure_rest"] or v["outcome"] != "decided":
        continue
    if g in new_ref:
        lost.append(g)
print("decided notes (OFF) newly refused in ON:", len(lost))
# claims
cl = on["claims"]
by_place = collections.defaultdict(list)
for c in cl:
    s = c["subject"].split("/")
    by_place[(int(s[1]), int(s[2]), c["cell"])].append(c)
print("meter objects found:", len(cl), "places:", {k: len(v) for k, v in sorted(by_place.items())})
print("claim abstentions:", len(on["claim_abstentions"]), dict(collections.Counter(a["why"] for a in on["claim_abstentions"])))
for k, v in sorted(by_place.items()):
    nums = collections.Counter()
    for c in v:
        n = c["numbers"] or {}
        nums[(n.get("numerator", {}).get("value"), n.get("denominator", {}).get("value"),
              n.get("numerator", {}).get("state"), n.get("denominator", {}).get("state"))] += 1
    print(" place", k, "n_staves", v[0]["n_staves"], "in_column", v[0]["n_in_column"], "numbers (num, den, states):", dict(nums))
json.dump(dict(new_refused=new_ref, gone_refused=gone_ref, rests_restored=rest_restored, rests_new=rest_new, lost=lost),
          open("%s/%s.diff.json" % (OUT, DOC), "w"), default=str)
