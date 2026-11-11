"""2.292 second witness for FILLED KEYS and CLEFS that is NOT the same raster: the work's dossier (data/dossiers, generated from the reference MusicXML).
    python3 dossier.py PLATE X.json [X.json ...]
For each filled staff: the instrument family the record placed on the slot (`Q.SLOT_INDEX` detail) -> the dossier's written_fifths / written_clef for the
parts of that family; agreement = the fill is one of the dossier's values for the family.  An ENCODING (source_kind: encoding): evidence about the fill's
correctness only, never a decider; and a disagreement may be the encoding's convention, not the fill's error (page truth is not an encoding truth).
"""
import collections
import json
import sys

DOSS = {"litolff": "data/dossiers/beethoven-sym5-mvt1.json", "brahms": "data/dossiers/brahms-sym1-mvt1.json"}
FAMILY = {"Flute": "Flute", "Oboe": "Oboe", "Clarinet": "Clarinet", "Bassoon": "Bassoon", "Horn": "Horn", "Trumpet": "Trumpet",
          "Timpani": "Timpani", "Violin": "Violin", "Viola": "Viola", "Violoncello": "Violoncello", "Contrabass": "Contrabass",
          "Contrabassoon": "Contrabassoon"}

plate = sys.argv[1]
dos = json.load(open(DOSS[plate]))
parts = dos["parts"]
tot = collections.Counter()
for path in sys.argv[2:]:
    d = json.load(open(path))
    slot_name = {}
    for v in d["staffs"].values():
        if v["slot"] and (v["slot"][0]["detail"] or {}).get("instrument"):
            slot_name[v["slot"][0]["value"]] = v["slot"][0]["detail"]["instrument"]
    for k, v in sorted(d["staffs"].items(), key=lambda kv: tuple(int(x) for x in kv[0].split("/")[1:])):
        inst = ((v["slot"][0]["detail"] or {}).get("instrument") if v["slot"] else None)
        if inst is None and v["slot"]:
            inst = slot_name.get(v["slot"][0]["value"])
        inst = {"Cello": "Violoncello", "Double Bass": "Contrabass"}.get(inst, inst)
        fam = next((f for f in FAMILY if inst and inst.startswith(f)), None)
        keyfill = v["key"] and v["key"][0]["decider"].startswith("infer")
        clef_fill = v["clef"] and v["clef"][0]["decider"].startswith("infer")
        if not (keyfill or clef_fill):
            continue
        ps = [p for p in parts if fam and fam in p["name"]]
        if keyfill:
            fill = v["key"][0]["value"]
            vals = sorted(set(p["written_fifths"] for p in ps))
            ok = fill in vals
            tot["key agree" if ok else "key DISAGREE"] += 1
            if not ok:
                print("KEY DISAGREE", k, inst, "fill", fill, "dossier", vals, [p["name"] for p in ps])
        if clef_fill:
            fill = v["clef"][0]["value"]
            vals = sorted(set(p["written_clef"] for p in ps))
            ok = fill in vals
            tot["clef agree" if ok else "clef DISAGREE"] += 1
            print("CLEF", k, inst, "fill", fill, "dossier", vals, "agree" if ok else "DISAGREE")
print(plate, dict(tot))
