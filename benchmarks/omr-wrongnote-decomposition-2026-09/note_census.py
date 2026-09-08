"""Per-row note census: pitched notes only, by written TYPE, truth vs pred.

Two questions musicdiff's `wrong note` cannot separate:
  * RECALL — are the notes there at all?
  * the CLAUDE.md contradiction — hollow heads "not detected" (a missing note)
    vs "a half read as something shorter" (present, typed short).
Both are answered by counting, with no alignment and therefore no alignment
assumptions.
⚠️ A <rest> is not a note. `rest measure="yes"` in particular is one element
standing for a whole bar and would swamp any count it entered.
"""
import json, collections, xml.etree.ElementTree as ET

HOLLOW = {"whole", "half", "breve", "long"}

def census(path):
    r = ET.parse(path).getroot()
    types = collections.Counter(); n_pitched = n_rest = n_grace = n_chord = 0
    for n in r.iter("note"):
        if n.find("rest") is not None:
            n_rest += 1; continue
        if n.find("grace") is not None: n_grace += 1
        if n.find("chord") is not None: n_chord += 1
        n_pitched += 1
        t = n.findtext("type")
        types[t if t else "(no type)"] += 1
    return {"pitched": n_pitched, "rests": n_rest, "grace": n_grace,
            "chord_members": n_chord, "types": types,
            "parts": len(r.findall(".//part"))}

pairs = json.load(open('/tmp/scan_pairs.json'))
rows = []
print(f"{'row':34s}{'truth n':>8s}{'pred n':>8s}{'delta':>7s}"
      f"{'t hollow':>9s}{'p hollow':>9s}{'t parts':>8s}{'p parts':>8s}")
T = P = TH = PH = 0
for pr in pairs:
    t, p = census(pr["truth"]), census(pr["pred"])
    th = sum(v for k, v in t["types"].items() if k in HOLLOW)
    ph = sum(v for k, v in p["types"].items() if k in HOLLOW)
    T += t["pitched"]; P += p["pitched"]; TH += th; PH += ph
    rows.append({"row": pr["name"], "truth": t["pitched"], "pred": p["pitched"],
                 "truth_hollow": th, "pred_hollow": ph,
                 "truth_types": dict(t["types"]), "pred_types": dict(p["types"]),
                 "truth_parts": t["parts"], "pred_parts": p["parts"]})
    print(f"{pr['name']:34s}{t['pitched']:8d}{p['pitched']:8d}"
          f"{p['pitched']-t['pitched']:+7d}{th:9d}{ph:9d}"
          f"{t['parts']:8d}{p['parts']:8d}")
print(f"\nPOOLED pitched notes: truth {T}  pred {P}  delta {P-T:+d}"
      f"  ({(P-T)/T:+.1%})")
print(f"POOLED hollow (whole/half/breve/long): truth {TH}  pred {PH}"
      f"  delta {PH-TH:+d}  pred/truth {PH/max(1,TH):.3f}")
json.dump(rows, open('/tmp/note_census.json','w'), indent=1)
