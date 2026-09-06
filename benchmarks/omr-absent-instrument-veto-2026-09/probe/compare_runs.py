"""Are two transcriptions identical where it matters?

`runtime` and the routing probe's millisecond field move run to run and say
nothing about the music, so they are excluded by name. Everything else — every
page, every staff, and the whole contextual block bar the veto's own report —
is compared verbatim.
"""
from __future__ import annotations

import json
import sys


def norm(path):
    r = json.load(open(path))
    r.pop("runtime", None)
    wr = r.get("weight_routing")
    if isinstance(wr, dict):
        wr.get("classification", {}).pop("ms", None)
    ctx = r.get("contextual")
    if isinstance(ctx, dict):
        ctx.pop("absent_instrument_veto", None)
    return json.dumps(r, sort_keys=True)


if __name__ == "__main__":
    a, b = sys.argv[1], sys.argv[2]
    x, y = norm(a), norm(b)
    print(f"A {a}  {len(x)} chars")
    print(f"B {b}  {len(y)} chars")
    print("IDENTICAL" if x == y else "DIFFER")
    raise SystemExit(0 if x == y else 1)
