"""Content diff of two gathered records' GATHER rows (row ids blanked), by quantity -- what differs besides the new quantities."""
import collections, json, re, sys
sys.path.insert(0, ".")
from tools.omr.staged.judged import iter_array

SKIP = {"page_mark", "page_mark_owner", "page_span"}


def rows(path):
    c = collections.Counter()
    for kind in ("observations", "abstentions"):
        for o in iter_array(path, kind):
            if o.get("quantity") in SKIP:
                continue
            o = dict(o)
            o.pop("id", None)
            o.pop("basis", None)
            c[(o.get("quantity"), re.sub(r"(obs|abs|vrd):[0-9]+", "ID", json.dumps(o, sort_keys=True, default=str)))] += 1
    return c


a, b = rows(sys.argv[1]), rows(sys.argv[2])
only = collections.Counter()
for k in set(a) | set(b):
    if a[k] != b[k]:
        only[k[0]] += abs(a[k] - b[k])
print("differing rows by quantity:", dict(only))
for k in list(set(a) - set(b))[:3] + list(set(b) - set(a))[:3]:
    print(k[1][:400])
