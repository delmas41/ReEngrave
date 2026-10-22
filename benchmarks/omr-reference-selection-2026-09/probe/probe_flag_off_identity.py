#!/usr/bin/env python3
"""Is the flag-OFF path identical to the code it replaced?

The claim is structural — the recurring branch is the same expression, just
hoisted so the label branch can compare against it — and a structural claim is
the kind this repository has been burned by. So it is CHECKED: `build_reference`
as of `origin/main` and this tree's version with `most_labelled="off"` are run
over the same randomly generated system sets and their references compared slot
for slot.

Not a unit test on purpose: it reads a git revision, which is not a thing the
suite should depend on. The suite pins the behaviour directly
(`tools/omr/tests/test_slots.py`).

    python3 .../probe_flag_off_identity.py [--base origin/main] [--trials 3000]

RESULT 2026-09-06, base origin/main, 3000 trials: 0 differences.
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import random
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr import slots as new              # noqa: E402
from tools.omr.types import Staff               # noqa: E402

NAMES = ["Flute", "Oboe", "Horn", "Violin", "Cello", None, None]


def load_base(rev):
    src = subprocess.check_output(
        ["git", "-C", str(REPO), "show", f"{rev}:tools/omr/slots.py"]).decode()
    src = src.replace("from .types import", "from tools.omr.types import")
    p = pathlib.Path(tempfile.mkdtemp()) / "base_slots.py"
    p.write_text(src)
    spec = importlib.util.spec_from_file_location("base_slots", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["base_slots"] = mod
    spec.loader.exec_module(mod)
    return mod


def staff(i, g):
    return Staff(page_index=0, staff_index=i,
                 line_ys=[i * 100 + 12 * k for k in range(5)],
                 x_start=100, x_end=1000, group_index=g)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--trials", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    old = load_base(args.base)
    rnd = random.Random(args.seed)
    bad = 0
    for _ in range(args.trials):
        views = []
        for _ in range(rnd.randint(1, 6)):
            n = rnd.randint(1, 14)
            sts = [staff(i, rnd.randint(0, 2)) for i in range(n)]
            labels = {}
            for i in range(n):
                nm = rnd.choice(NAMES)
                if nm:
                    labels[i] = nm
            views.append((sts, labels))

        def flat(mod, **kw):
            vs = [mod.SystemView(staves=s, labels=l) for s, l in views]
            return [(x.index, x.group_index, x.instrument, round(x.position, 6))
                    for x in mod.build_reference(vs, **kw)]

        a, b = flat(old), flat(new, most_labelled="off")
        if a != b:
            bad += 1
            if bad <= 3:
                print("DIFF\n  base", a, "\n  here", b)
    print(f"base={args.base} trials={args.trials} differences={bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
