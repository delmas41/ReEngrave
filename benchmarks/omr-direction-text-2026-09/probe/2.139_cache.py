"""2.139: stream a staged record once per list, keep only the rows 2.139 needs.
usage: 2.139_cache.py RECORD obs|ver OUT.json   (streaming: ijson, bounded memory)"""
import sys, json, ijson
from decimal import Decimal
path, which, out = sys.argv[1:4]
def fix(o):
    if isinstance(o, Decimal): return float(o)
    if isinstance(o, dict): return {k: fix(v) for k, v in o.items()}
    if isinstance(o, list): return [fix(v) for v in o]
    return o
OBS = {"dynamic_letter", "direction_word", "dynamic", "direction", "dynamic_letter_neighbours", "dynamic_is_not_a_dynamic"}
keep = []
with open(path, "rb") as f:
    if which == "obs":
        for o in ijson.items(f, "record.observations.item"):
            if o.get("quantity") in OBS:
                keep.append(fix(o))
    else:
        for v in ijson.items(f, "record.verdicts.item"):
            if v.get("quantity") in OBS:
                keep.append(fix(v))
json.dump(keep, open(out, "w"))
print(which, len(keep))
