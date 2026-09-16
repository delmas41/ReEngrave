"""Every glyph a candidate rule would FIRE on, as a contact sheet.

⚠️ A rule scored only on the rows that happen to be in the hand-adjudicated set
is scored on its easy cases. `shape+slot` fires 21 times on this document and
four of those are in that set; shipping on four would be shipping on four. This
lists all of them so every one can be looked at.

Reuses `sheet.py`'s panel drawing by writing a trace-shaped file it can eat, so
the controls, the scale and the rulers are identical -- a second panel renderer
would be a second convention to keep honest.

    python3 .../fires.py --reach reach.json --out fires-trace.json --rule shape+slot
"""
from __future__ import annotations

import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reach", required=True)
    ap.add_argument("--rule", default="shape+slot")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = json.load(open(a.reach))
    want = a.rule.split("+")
    fires = [r for r in rows if all(bool(r[k]) for k in want)]
    if not fires:
        print("RULE FIRES ON NOTHING -- dead instrument", file=sys.stderr)
        return 2
    out = []
    for r in sorted(fires, key=lambda r: r["subject"]):
        p, s, st, c, g = r["subject"].split("/")[1:]
        out.append({"part": f"p{p}s{s}st{st}", "measure": f"c{c}",
                    "subject": r["subject"], "lone_quarter_in_2_4": True,
                    "truth": r.get("truth"),
                    "height": r["height"], "aspect": r["aspect"],
                    "step": r["step"], "conf": r["conf"],
                    "neighbour": r["neighbour"],
                    "alone_in_bar": r["alone_in_bar"]})
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"{a.rule}: {len(out)} fires -> {a.out}")
    for i, r in enumerate(out):
        print(f"  {i:>3}  {r['subject']:<24} h={r['height']:5.2f} "
              f"asp={r['aspect']:6.2f} step={r['step']:+6.2f} "
              f"conf={r['conf']:.2f} alone={int(r['alone_in_bar'])} "
              f"nb={r['neighbour']} truth={r['truth']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
