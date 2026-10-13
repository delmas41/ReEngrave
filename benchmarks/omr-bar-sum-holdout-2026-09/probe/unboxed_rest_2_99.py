"""ROADMAP 2.99 -- what `Q.UNBOXED_REST_SHAPE` rows look like, by who covers them.

PATH: STAGED, GATHER + ADJUDICATE (a small re-gather record, `--through
adjudicate`). Prints the CONTROL TABLE the decision's windows were read off:
the clusters a standing REST box covers (positive control), a standing
ACCIDENTAL box covers (negative control), and the unboxed ones the decision
reads. Reads a record only through `record_io.load_record`.

    python3 unboxed_rest_2_99.py rec.json [--json out.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import record_io  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def load(path):
    doc = record_io.load_record(path)
    return doc["record"] if "record" in doc else doc


def rows(rec):
    ver = {}
    for v in rec["verdicts"]:
        if v["quantity"] == Q.UNBOXED_INK_IS_A_REST:
            ver[v["subject"]] = v          # last wins (supersession order)
    out = []
    for o in rec["observations"]:
        if o["quantity"] != Q.UNBOXED_REST_SHAPE or o.get("state") == "declined":
            continue
        d = o.get("detail") or {}
        if "width_spaces" not in d:
            continue
        v = ver.get(o["subject"])
        out.append({"subject": o["subject"], **d,
                    "outcome": v and v["outcome"],
                    "value": v and v.get("value"),
                    "reason": v and v.get("reason")})
    return out


def klass(r):
    by = [b.lower() for b in (r.get("covered_by") or [])]
    if (r.get("coverage") or 0) < 0.5:
        return "unboxed"
    for pre, name in (("rest", "rest"), ("accidental", "accidental"),
                      ("notehead", "notehead"), ("flag", "flag"),
                      ("clef", "clef"), ("gclef", "clef"), ("fclef", "clef"),
                      ("keysig", "key"), ("timesig", "meter"),
                      ("fermata", "fermata")):
        if any(b.startswith(pre) for b in by):
            return name
    return "covered:" + "+".join(sorted(by))[:30]


def stats(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return "-"
    q = lambda p: vals[min(len(vals) - 1, int(p * len(vals)))]
    return f"n={len(vals)} min={vals[0]:.2f} p10={q(.1):.2f} med={statistics.median(vals):.2f} p90={q(.9):.2f} max={vals[-1]:.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json")
    a = ap.parse_args()
    rs = rows(load(a.record))
    by = collections.defaultdict(list)
    for r in rs:
        r["klass"] = klass(r)
        by[r["klass"]].append(r)
    print(f"{len(rs)} clusters")
    for k, lst in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print(f"\n== {k}  ({len(lst)})")
        for f in ("width_spaces", "height_spaces", "staff_step",
                  "max_column_share", "mass_y", "mass_x", "fill"):
            print(f"  {f:17s} {stats([r.get(f) for r in lst])}")
        print("  covered_by:", collections.Counter(
            tuple(r.get("covered_by") or ()) for r in lst).most_common(4))
        if k == "unboxed":
            print("  verdicts:", collections.Counter(
                (r["outcome"], str(r["value"]), r["reason"]) for r in lst))
    if a.json:
        json.dump(rs, open(a.json, "w"))


if __name__ == "__main__":
    main()
