"""2.266b: for the notes whose blue flag goes away (lane_report OFF blue -> ON plain, from the work dir's symbols.json), stream the record the lane report replayed and
keep the decided accidental_owner verdict (family reading, one-ink detail, detector class), what the head's accidental verdict writes, and the accidental's page box.
Writes WORK/PLATE.c266b.json ({head: {...}}) for tiles_2_266b.py. Measurement only.
usage (repo root): python3 benchmarks/omr-one-ink-one-mark-2026-10/extract_2_266b.py WORK_DIR PLATE RECORD"""
import json, pathlib, sys

sys.path.insert(0, ".")
from tools.omr.staged import judged as J

W, plate, rec = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
off = json.load(open(W / (plate + ".off.symbols.json")))["hosts"]
on = json.load(open(W / (plate + ".on.symbols.json")))["hosts"]
onb = {h["rg"]: h["blue"] for h in on if h["kind"] == "note"}
lost = {h["rg"] for h in off if h["kind"] == "note" and h["blue"] and onb.get(h["rg"]) is False}
owners, written, accs = {}, {}, {}
for v in J.iter_array(rec, "verdicts"):
    q = v.get("quantity")
    if q == "accidental_owner" and v.get("outcome") == "decided" and v.get("value") in lost:
        d = v.get("detail") or {}
        owners[v["value"]] = dict(acc=v["subject"], family=d.get("family"), one_ink=d.get("one_ink"), detector_class=d.get("detector_class"),
                                  alteration=d.get("alteration"))
    elif q == "accidental" and v.get("outcome") == "decided" and v["subject"] in lost:
        written[v["subject"]] = v.get("value")
want = {o["acc"] for o in owners.values()}
for o in J.iter_array(rec, "observations"):
    if o.get("quantity") == "glyph_box" and o["subject"] in want:
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b:
            accs[o["subject"]] = [float(x) for x in b]
out = {}
for head, o in owners.items():
    if o["acc"] in accs:
        out[head] = dict(o, box=accs[o["acc"]], written=written.get(head))
json.dump(out, open(W / (plate + ".c266b.json"), "w"))
print(plate, "lost-blue notes", len(lost), "owner found", len(owners), "with box", len(out))
