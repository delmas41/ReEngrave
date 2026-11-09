import json
import collections
from load import *  # noqa

r = record("on")
v = [x for x in r["verdicts"] if x["quantity"] == "page_arc_binding"][0]
runs = v["detail"]["runs"]
print(len(runs), collections.Counter(x["status"] for x in runs))
print(collections.Counter(x.get("why") for x in runs if x["status"] == "abstained"))
for x in runs[:40]:
    if x["status"] == "written":
        print({k: (val if len(str(val)) < 300 else str(val)[:300]) for k, val in x.items()})
        break
for x in runs:
    if x["status"] == "abstained":
        print({k: (val if len(str(val)) < 300 else str(val)[:300]) for k, val in x.items()})
        break
row = [o for o in r["observations"] if o["quantity"] == "page_arc" and o["value"] == "run"][0]
print(type(row["detail"]["points"]), row["detail"]["points"][:2])
br = [o for o in r["observations"] if o["quantity"] == "page_arc" and o["value"] == "box_without_run"][0]
print(br["subject"], {k: str(v)[:100] for k, v in br["detail"].items()})
sd = [o for o in r["observations"] if o["quantity"] == "page_arc" and o["value"] in ("seeded", "census")]
for o in sd:
    print(o["value"], str(o["detail"])[:300])
