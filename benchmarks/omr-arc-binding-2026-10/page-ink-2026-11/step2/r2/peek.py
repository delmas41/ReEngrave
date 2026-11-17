"""peek at the row shapes of a slice (development aid)."""
import json
import sys

SL = sys.argv[1]
want = sys.argv[2]
n = 0
with open(SL) as fh:
    for line in fh:
        if ('"%s"' % want) not in line:
            continue
        o = json.loads(line)
        if o["quantity"] != want:
            continue
        d = o.get("detail") or {}
        print(o["subject"], o["value"], o["reader"], {k: (v if not isinstance(v, (list, dict)) or len(str(v)) < 120 else str(v)[:120] + "...") for k, v in d.items()})
        n += 1
        if n >= int(sys.argv[3] if len(sys.argv) > 3 else 3):
            break
