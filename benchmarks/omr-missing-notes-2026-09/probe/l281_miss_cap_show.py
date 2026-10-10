#!/usr/bin/env python3
"""l281_miss_cap_show: print a `l281_miss_rebuild.py` capture, one head per block (the per-stroke story).

    python3 l281_miss_cap_show.py --cap cap.json [KEY ...]
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", required=True)
    ap.add_argument("keys", nargs="*")
    a = ap.parse_args()
    d = json.loads(Path(a.cap).read_text())
    print("control:", {k: (v if k != "differ" else len(v)) for k, v in d["control"].items()})
    for k, h in d["heads"].items():
        if a.keys and k not in a.keys:
            continue
        print("==", k, h["verdict"], {x: v for x, v in h["detail"].items() if v not in (None, 0, False)})
        for sid, s in h["strokes"].items():
            print("   ", sid, s)


if __name__ == "__main__":
    main()
