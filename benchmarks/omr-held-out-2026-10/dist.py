import json, sys
from collections import Counter
c = json.load(open(sys.argv[1]))
for doc, cases in c.items():
    cnt = Counter()
    for x in cases:
        if x["rule"] == sys.argv[2]:
            v = (x["arm"] or {}).get("value")
            b = (x["base"] or {})
            cnt[(json.dumps(v, sort_keys=True) if not isinstance(v, dict) else f'beats={v.get("beats")} dots={v.get("dots")} bl={v.get("beam_levels")}', b.get("outcome"), b.get("reason"))] += 1
    print(doc); [print("  ", k, n) for k, n in cnt.most_common()]
