import json
P = ("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-scan-e2e-2026-09/"
     "fixtures/bach-brandenburg3-mvt1-468678-p1..graft09.omr.json")
d = json.load(open(P))
c = d["contextual"]
for k in ("clefs_applied", "noteheads_restated", "clefs_filled_from_slot",
          "clefs_from_dossier", "label_tiers", "assist", "layout_named_slots"):
    print(k, "=", json.dumps(c.get(k))[:300])
print("proposals:")
for p in c.get("proposals", []):
    print("  ", json.dumps(p)[:300])
