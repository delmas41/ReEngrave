"""List whole-work edition candidates with their reference encodings."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
cat = json.load(open(ROOT / "data/score-library/catalog.json"))
want = {"beethoven--symphony-5", "dvorak--symphony-9",
        "mozart--symphony-41", "brahms--symphony-1", "brahms--symphony-2"}

for e in cat["entries"]:
    if e["kind"] == "edition" and e["work_id"] in want and e.get("pages", 0) >= 40:
        p = ROOT / "library" / e["path"]
        print(f"{e['work_id']:26s} pages={e.get('pages'):4d} imslp={e['imslp_id']:8s} "
              f"exists={p.exists()} {e['path']}")
print("--- references ---")
for e in cat["entries"]:
    if e["kind"] != "edition" and e["work_id"] in want:
        print(f"{e['work_id']:26s} {e['path']}")
