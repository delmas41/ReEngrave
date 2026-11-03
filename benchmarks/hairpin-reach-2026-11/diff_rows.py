"""ROADMAP 2.254: GATHER rows that differ OFF vs ON under one page/system/staff (or cell) prefix of the lane report's gathered records.

    python3 benchmarks/hairpin-reach-2026-11/diff_rows.py WORKDIR brahms 25/0/13
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.judged import iter_array  # noqa: E402


def rows(rec, prefix):
    out = collections.Counter()
    for kind in ("observations", "abstentions"):
        for it in iter_array(rec, kind):
            parts = (it.get("subject") or "").split("/")
            if "/".join(parts[1:1 + len(prefix.split("/"))]) == prefix:
                d = dict(it.get("detail") or {})
                out[json.dumps([kind, it["subject"], it["quantity"], it.get("reader"), it.get("value"), d.get("why") or it.get("reason")],
                               default=str, sort_keys=True)] += 1
    return out


def main(work, plate, prefix):
    w = pathlib.Path(work)
    a = rows(w / ("%s.off.gathered.record.json" % plate), prefix)
    b = rows(w / ("%s.on.gathered.record.json" % plate), prefix)
    only_off, only_on = a - b, b - a
    q = collections.Counter()
    for k in list(only_off) + list(only_on):
        q[json.loads(k)[2]] += 1
    print("differing rows by quantity:", dict(q))
    for k in list(only_off)[:15]:
        print("OFF only", k[:300])
    for k in list(only_on)[:15]:
        print("ON  only", k[:300])


if __name__ == "__main__":
    main(*sys.argv[1:4])
