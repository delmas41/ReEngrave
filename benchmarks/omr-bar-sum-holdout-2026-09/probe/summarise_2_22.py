"""ROADMAP 2.22 -- the ranked table FINDINGS §17 prints, from a partition.

    python3 .../summarise_2_22.py <partition.json> [top]
"""
import json
import sys


def main():
    p = json.load(open(sys.argv[1]))
    top = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    chosen = sorted(p["chosen"].items(), key=lambda kv: -kv[1])
    shown = chosen[:top]
    rest = sum(v for _k, v in chosen[top:])
    print(f"| minimal set (ties -> most specific) | bars |")
    print("|---|--:|")
    for k, v in shown:
        print(f"| `{k}` | {v} |")
    print(f"| {len(chosen) - top} other combinations | {rest} |")
    print(f"| **total held** | **{p['held']}** |")
    print()
    print("single fix releases outright:",
          ", ".join(f"`{k}` {v}" for k, v in
                    sorted(p["single"].items(), key=lambda kv: -kv[1])))
    print("necessary (in every minimal set):",
          ", ".join(f"`{k}` {v}" for k, v in
                    sorted(p["necessary"].items(), key=lambda kv: -kv[1])))
    assert sum(p["chosen"].values()) == p["held"], "partition does not close"


if __name__ == "__main__":
    main()
