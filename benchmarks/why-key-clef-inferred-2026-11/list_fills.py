"""List every staff whose key or clef was filled by INFER, with the prior abstention and what the staff itself read.
    python3 list_fills.py X.json"""
import json, sys

d = json.load(open(sys.argv[1]))
S = d["staffs"]
for s, v in sorted(S.items(), key=lambda kv: tuple(int(x) for x in kv[0].split("/")[1:])):
    k = v["key"]
    if k and k[0]["decider"].startswith("infer"):
        f = k[0]; p = k[-1]
        pd = p.get("detail") or {}
        inst = (v["instrument"][0]["detail"] or {}).get("reader_text") if v["instrument"] else None
        print("KEY ", s, "|", inst, "| slot", v["slot"][0]["value"] if v["slot"] else None,
              "|fill", f["value"], f["reason"], "off", (f.get("detail") or {}).get("fifths_offset"),
              "|prior", p["reason"],
              {x: pd.get(x) for x in ("written_fifths", "read_by", "keysig_marker_slots", "keysig_run_slots", "header_ink_slots",
                                      "marker_slots", "system_tally", "disagreeing_readers", "concert_fifths") if x in pd})
for s, v in sorted(S.items(), key=lambda kv: tuple(int(x) for x in kv[0].split("/")[1:])):
    c = v["clef"]
    if c and c[0]["decider"].startswith("infer"):
        print("CLEF", s, json.dumps(c)[:1400])
        print("     slot", v["slot"][0]["value"] if v["slot"] else None, v["slot"][0]["decider"] if v["slot"] else None,
              "inst", v["instrument"][0]["value"] if v["instrument"] else None)
