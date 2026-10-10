#!/usr/bin/env python3
"""l281_row: print selected rows of a `l281_score.py --json` file (scored page-0 members).

    python3 l281_row.py --scored scored.json KEY [KEY ...]
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("keys", nargs="+")
    a = ap.parse_args()
    for r in json.loads(Path(a.scored).read_text()):
        if r["key"] in a.keys:
            print({k: v for k, v in r.items() if k not in ("final_stage", "final_outcome")})


if __name__ == "__main__":
    main()
