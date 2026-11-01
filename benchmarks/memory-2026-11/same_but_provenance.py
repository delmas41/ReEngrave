"""Are two staged record FILES byte-identical apart from their top-level `provenance` value? (ROADMAP 2.249; reads only)

usage: same_but_provenance.py A.record.json B.record.json

Never loads a record: `provenance` is the envelope's LAST key-group (written after `record`), so each file is split at
its last `,"provenance":` -- the prefix and the suffix after the provenance object are compared by SHA-256 in 64 MB
chunks, and the two provenance objects are decoded and their differing keys printed. Exit 0 = identical apart from
provenance, 1 = they differ elsewhere (the first differing byte offset is printed).
"""
import hashlib, json, os, sys

KEY = b',"provenance":'


def split(path):
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        tail_n = min(size, 64 << 20)
        fh.seek(size - tail_n)
        tail = fh.read()
    i = tail.rfind(KEY)
    if i < 0:
        raise SystemExit(f"{path}: no provenance key in the last 64 MB")
    start = size - tail_n + i + len(KEY)
    obj, end = json.JSONDecoder().raw_decode(tail[i + len(KEY):].decode("utf-8"))
    return start, start + end, obj, size     # the writer is ensure_ascii, so a char offset is a byte offset


def digest(path, a, b):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        fh.seek(a)
        left = b - a
        while left > 0:
            chunk = fh.read(min(left, 64 << 20))
            if not chunk:
                break
            h.update(chunk); left -= len(chunk)
    return h.hexdigest()


def first_diff(pa, pb, limit):
    with open(pa, "rb") as fa, open(pb, "rb") as fb:
        off = 0
        while off < limit:
            x, y = fa.read(1 << 20), fb.read(1 << 20)
            if x != y:
                for k in range(min(len(x), len(y))):
                    if x[k] != y[k]:
                        return off + k, x[max(0, k - 200):k + 200], y[max(0, k - 200):k + 200]
                return off + min(len(x), len(y)), b"", b""
            if not x:
                break
            off += len(x)
    return None


pa, pb = sys.argv[1:3]
sa, ea, prov_a, size_a = split(pa)
sb, eb, prov_b, size_b = split(pb)
pre = (sa == sb) and digest(pa, 0, sa) == digest(pb, 0, sb)
post = digest(pa, ea, size_a) == digest(pb, eb, size_b)
diff_keys = sorted(k for k in set(prov_a) | set(prov_b) if prov_a.get(k) != prov_b.get(k))
print(f"A {size_a} bytes, B {size_b} bytes; before provenance identical: {pre}; after provenance identical: {post}")
print("provenance keys that differ:", diff_keys)
for k in diff_keys:
    if k != "run":
        print(f"  {k}: {json.dumps(prov_a.get(k))[:300]} -> {json.dumps(prov_b.get(k))[:300]}")
if not (pre and post):
    fd = first_diff(pa, pb, min(sa, sb))
    if fd:
        print("first differing byte at", fd[0]); print(" A:", fd[1]); print(" B:", fd[2])
    sys.exit(1)
