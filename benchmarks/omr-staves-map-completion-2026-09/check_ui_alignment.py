"""Does the UI's crop panel line up for each research row?

`server.py`'s `instancesFor` boxes a map entry's printed instance only where the
hand-read lineup and the detected bands agree about how many staves the system
has — otherwise it says so rather than boxing the wrong staff. This asks that
question of the running server, per row, so the slot count quoted in FINDINGS
is the number of slots that actually SHOW a crop.
"""
from __future__ import annotations

import json
import urllib.request

ROWS = ["mahler-sym5-mvt1-local-p2", "mahler-sym5-mvt1-local-p3",
        "mahler-sym5-mvt1-local-p4", "mahler-sym5-mvt1-local-p5",
        "bach-brandenburg3-mvt1-468678-p1"]
BASE = "http://127.0.0.1:5076"


def main() -> int:
    out = []
    for rid in ROWS:
        with urllib.request.urlopen(f"{BASE}/api/row/{rid}") as fh:
            d = json.load(fh)
        seed = d["seed"]
        sap = seed["systems_as_printed"]
        det = seed["detected"]["systems"]
        aligned = [len(a["staves"]) == len(b["staves"])
                   for a, b in zip(sap, det)]
        rec = {"row_id": rid,
               "slots": len(seed["proposal"]["staves"]),
               "lineup_per_system": [len(s["staves"]) for s in sap],
               "detected_per_system": [len(s["staves"]) for s in det],
               "crop_shown": all(aligned) and bool(aligned),
               "n_parts": seed["reference"]["n_parts_music21"],
               "unnamed": d["validation"]["unnamed"]}
        out.append(rec)
        print(json.dumps(rec, ensure_ascii=False))
    print("total slots:", sum(r["slots"] for r in out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
