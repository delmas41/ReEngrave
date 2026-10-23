"""2.183: OFF vs ON from replay_2_183.py output. usage: compare_2_183.py DOC OUTDIR
Per plate: key-run claims, boxes refused / narrowed by the claim by class, PARITY with the five 2.100 gates, notes in file, blue notes,
red bars, bars that add up, and the key-slot rests still WRITTEN (the cause population, `causes_2_183.py`)."""
import collections
import json
import sys

DOC, OUT = sys.argv[1], sys.argv[2]
off = json.load(open("%s/%s.off.json" % (OUT, DOC)))
on = json.load(open("%s/%s.on.json" % (OUT, DOC)))
OLD_HEAD, OLD_REST = "notehead_in_a_key_signature_slot", "rest_in_a_key_signature_slot"
print("== %s ==" % DOC)
for k in ("notes_in_xml", "blue_in_xml"):
    print(k, "off", off[k], "on", on[k], "delta", on[k] - off[k])
for k in ("bars_written_red", "guessed", "balance"):
    print(k, "off", json.dumps(off["coverage"].get(k), default=str)[:200])
    print(k, "on ", json.dumps(on["coverage"].get(k), default=str)[:200])
print("claims (ON):", dict(collections.Counter((c["owner"], c["standing"]) for c in on["claims"])))
by_cls = collections.Counter()
for tag, off_ref, on_ref in (("head", off["refusals"], on["refusals"]), ("rest", off["rest_refusals"], on["rest_refusals"])):
    old = {g for g, v in off_ref.items() if v[1] in (OLD_HEAD, OLD_REST)}
    new = {g for g, v in on_ref.items() if v[1] == "claimed_by:key_signature"}
    print(tag, "refused by the old key-slot gate (OFF):", len(old), " by claimed_by:key_signature (ON):", len(new),
          " only OFF:", len(old - new), " only ON:", len(new - old))
    for g in sorted(old - new):
        print("   only OFF", g, on_ref.get(g) or ("narrowed" if g in on["narrowed"] else "KEPT"))
    for g in sorted(new - old):
        print("   only ON ", g, "was", off_ref.get(g))
narr = {g: v for g, v in list(on["narrowed"].items()) + list(on["rest_narrowed"].items()) if v[0] == "claim_narrowed:key_signature"}
print("narrowed by the key claim (ON):", len(narr), list(narr)[:10])
# marks (flag / arpeggiato / arc) are not in the judged json; the record's verdict counts are in the replay's `not_a_notehead`
print("report not_a_*:", {k: v for k, v in on["not_a_notehead"].items() if "key" in str(k)}, "OFF", {k: v for k, v in off["not_a_notehead"].items() if "key" in str(k)})
json.dump(dict(only_off=[], narrowed=narr), open("%s/%s.diff183.json" % (OUT, DOC), "w"), default=str)
