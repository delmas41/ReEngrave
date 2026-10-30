import json
S = "/private/tmp/claude-501/s/slices/%s/litolff/observations.jsonl"
cells = ["cell/3/0/4/3", "cell/3/1/2/15", "cell/4/0/7/7"]
for arm in ("base", "tag"):
    print("=====", arm)
    for l in open(S % arm):
        o = json.loads(l)
        if o["subject"] in cells and o["quantity"] == "stem":
            d = o.get("detail") or {}
            print(o["id"], o["subject"], json.dumps(o["value"])[:90], o.get("reader"), json.dumps({k: v for k, v in d.items() if not isinstance(v, (list, dict))})[:260])
