"""2.280 probe 14: the Litolff rest blocks (my label R): what did the CURRENT tree's re-adjudication + export do with each? usage: p14_rests_written.py"""
import json

L = json.load(open("out/2.280/labels_litolff.json"))
fates = {}
for l in open("out/2.280/fates_litolff.jsonl"):
    r = json.loads(l)
    fates[r["sub"]] = r
for s, lab in sorted(L.items()):
    if lab != "R":
        continue
    f = fates[s]
    print(s, f["cls"][:22], "| fate", f["fate"], "| dur", f["duration"], "| whole_rest", f["whole_rest"], "| head_ink_rest", f["head_ink_rest"], "| pitch", (f["pitch"] or [None])[0])
