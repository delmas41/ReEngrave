"""What a record says about how it was made, WITHOUT loading it (8.8 GB Brahms records are read by mmap, from the tail).

Reads the top-level `provenance` (commit, dirty, env overrides, args), `weight_routing` (mode, verdict) and the row `counts`
(observations / abstentions / verdicts) and prints them for each record, then a SETTINGS/ENV diff between the first and the
last record: anything that is not identical is an apples-to-oranges difference and is printed first.
What a record does NOT carry (so it is not estimated anywhere): per-stage wall time, detector calls, OCR calls.
python3 prov_peek.py A.record.json B.record.json
"""
import json
import mmap
import os
import re
import sys

DEC = json.JSONDecoder()


def tail_key(m, key: bytes, must_have=None):
    """The last top-level-looking `"key": {...}` that parses (and holds `must_have`, since e.g. `counts` also names the
    EVALUATE fired/skipped rows)."""
    end = len(m)
    while True:
        i = m.rfind(b'"' + key + b'"', 0, end)
        if i < 0:
            return None
        end = i
        j = m.find(b":", i) + 1
        raw = m[j:j + (1 << 22)].decode("utf-8", errors="ignore").lstrip()
        try:
            v = DEC.raw_decode(raw)[0]
        except ValueError:
            continue
        if must_have is None or (isinstance(v, dict) and must_have in v):
            return v


def peek(path):
    with open(path, "rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as m:
        prov = tail_key(m, b"provenance") or {}
        wr = tail_key(m, b"weight_routing") or {}
        counts = tail_key(m, b"counts", "observations") or {}
    return dict(path=path, mb=round(os.path.getsize(path) / 1e6), prov=prov, mode=wr.get("mode"), verdict=wr.get("verdict"),
                counts=counts)


def flat(d, pre=""):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            out.update(flat(v, pre + k + "."))
        else:
            out[pre + k] = v
    return out


def main():
    ps = [peek(p) for p in sys.argv[1:]]
    for p in ps:
        pv = p["prov"]
        print("%s\n  %d MB  commit %s dirty=%s  weight routing %s/%s" % (os.path.basename(p["path"]), p["mb"], pv.get("commit"),
                                                                       pv.get("dirty"), p["mode"], p["verdict"]))
        print("  rows %s" % p["counts"])
        print("  settings %s" % json.dumps(pv.get("settings"), sort_keys=True, default=str)[:700])
    if len(ps) >= 2:
        a, b = flat(ps[0]["prov"].get("settings")), flat(ps[-1]["prov"].get("settings"))
        keys = sorted(set(a) | set(b))
        diff = [(k, a.get(k, "<absent>"), b.get(k, "<absent>")) for k in keys if a.get(k, "<absent>") != b.get(k, "<absent>")]
        # the output path is named after the tag: not a setting
        diff = [d for d in diff if d[0] != "args.out"]
        print("SETTINGS/ENV difference first -> last record (%s): %s" % ("IDENTICAL" if not diff else "DIFFERS", "" if not diff else diff))


if __name__ == "__main__":
    main()
