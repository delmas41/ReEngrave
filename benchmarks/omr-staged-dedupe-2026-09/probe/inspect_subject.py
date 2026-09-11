"""Dump every row the record holds for a named subject. No aggregation."""
from __future__ import annotations

import argparse
import json


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("subjects", nargs="+")
    args = ap.parse_args(argv)
    d = json.load(open(args.record))
    want = set(args.subjects)
    for key in ("observations", "abstentions", "verdicts"):
        for o in d["record"].get(key, []):
            if o.get("subject") in want:
                print(f"[{key}] " + json.dumps(o))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
