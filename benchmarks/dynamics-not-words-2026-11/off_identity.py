"""ROADMAP 2.296: the flag OFF is main -- two gathered records of the same pages (one gathered on main's code, one on this branch with the flag unset) hold the same rows.

    python3 benchmarks/dynamics-not-words-2026-11/off_identity.py A.record.json B.record.json PAGE[,PAGE...]

Compares, for the named pages, every observation / abstention / verdict row (id, subject, quantity, value, reader, detail) after dropping the per-run timing keys. Prints the
counts and the first differences; exit 1 if any. A control that can fail: `--plant` edits one row of B in memory and the comparison must then report exactly one difference.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.record_io import load_record  # noqa: E402

DROP = {"ms", "seconds", "elapsed", "wall", "time", "ts", "rss", "peak_rss"}


def page_of(sub):
    m = re.match(r"^(?:glyph|cell|staff|system|page)/(\d+)", str(sub))
    return int(m.group(1)) if m else None


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items() if k not in DROP}
    if isinstance(o, list):
        return [clean(v) for v in o]
    return o


def rows(path, pages):
    res = load_record(path)
    rec = res.get("record", res)
    out = {}
    for kind in ("observations", "abstentions", "verdicts"):
        for r in rec.get(kind, []):
            if page_of(r.get("subject")) in pages:
                out[(kind, r.get("id"))] = json.dumps(clean(r), sort_keys=True, default=str)
    return out


def main():
    a, b = sys.argv[1], sys.argv[2]
    pages = {int(x) for x in sys.argv[3].split(",")}
    ra, rb = rows(a, pages), rows(b, pages)
    if "--plant" in sys.argv:
        k = sorted(rb)[len(rb) // 2]
        rb[k] = rb[k] + "x"
    only_a, only_b = sorted(set(ra) - set(rb)), sorted(set(rb) - set(ra))
    diff = [k for k in ra if k in rb and ra[k] != rb[k]]
    print("pages %s: rows A %d, B %d; only in A %d, only in B %d, same id but different %d" % (sorted(pages), len(ra), len(rb), len(only_a), len(only_b), len(diff)))
    for k in (only_a[:3] + only_b[:3] + diff[:5]):
        print("   ", k, (ra.get(k) or "")[:160], "|", (rb.get(k) or "")[:160])
    sys.exit(1 if (only_a or only_b or diff) else 0)


main()
