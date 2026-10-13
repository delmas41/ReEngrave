import json
import sys

P = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/held-out-2101/probe/"
for d in sys.argv[1:]:
    b = json.load(open(P + d + "-base.json"))["held_list"]
    a = json.load(open(P + d + "-arm.json"))["held_list"]
    key = lambda h: json.dumps(h if isinstance(h, list) else [h.get(k) for k in sorted(h) if k in ("part", "bar", "measure", "page", "system", "cell", "staff")], sort_keys=True)  # noqa: E731
    kb, ka = {key(h): h for h in b}, {key(h): h for h in a}
    new, gone = [kb_ for kb_ in ka if kb_ not in kb], [x for x in kb if x not in ka]
    print(d, "base", len(b), "arm", len(a), "newly held", len(new), "released", len(gone))
    for k in new[:3]:
        print("   new", json.dumps(ka[k])[:260])
