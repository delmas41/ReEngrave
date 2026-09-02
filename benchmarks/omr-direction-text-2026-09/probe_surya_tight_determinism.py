"""Is Surya a fixed function of its input? The tight test nobody has run.

`SURYA_BAKEOFF_2026-08-31.md` replayed one image 45 times and found it fixed,
with the recorded caveat that replaying ONE image cannot see a shared prompt
cache — the thing that would make a crop's reading depend on what was read
before it. This runs the case that caveat names:

  A. the same crop LIST twice, in ONE process, same order    (shared cache live)
  B. the same list a third time in the SAME process, shuffled and restored
                                                             (cache, order varied)
  C. the same list again in a SECOND process                 (cache cold)

If A disagrees with itself, Surya is not a function of one crop. If A agrees but
C differs, the state is per-process. If all agree, the reader is fixed and the
non-determinism seen downstream is somewhere else.

RESULT, 2026-09-02, 20 crops from the Litolff Beethoven 5 scan: **0 of 20 differ
in every comparison** — A vs B, A vs C shuffled, and process 1 vs process 2.
Surya is a fixed function of its input, order-independent and cache-independent.
So the 485-line run-to-run difference recorded in `NONDETERMINISM_2026-09-02.md`
is NOT this reader, and the search belongs upstream of it.
"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.omr.staff_labels_surya import read_crops_text   # noqa: E402

#: Crops written by `eval_on_scan.py --crops-dir`. Machine-local; override.
CROPS = Path(os.environ.get("OMR_CROPS_DIR",
                            Path(__file__).parent / "scan-crops"))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
TAG = sys.argv[2] if len(sys.argv) > 2 else "run"

paths = sorted(CROPS.glob("p*.png"))[:N]
images = [cv2.imread(str(p)) for p in paths]
print(f"{len(images)} crops from {CROPS}", flush=True)

a = read_crops_text(images)
print("pass A done", flush=True)
b = read_crops_text(images)
print("pass B done", flush=True)

order = list(range(len(images)))
random.Random(7).shuffle(order)
shuffled = read_crops_text([images[i] for i in order])
c = [None] * len(images)
for slot, i in enumerate(order):
    c[i] = shuffled[slot]
print("pass C (shuffled) done", flush=True)

def diff(x, y, nx, ny):
    bad = [(paths[i].name, x[i], y[i]) for i in range(len(x)) if x[i] != y[i]]
    print(f"\n{nx} vs {ny}: {len(bad)} of {len(x)} differ")
    for name, u, v in bad[:12]:
        print(f"   {name:34s} {u!r}  ->  {v!r}")
    return bad

d1 = diff(a, b, "A", "B (same order, same process)")
d2 = diff(a, c, "A", "C (shuffled, same process)")

out = Path(__file__).parent / f"determinism-{TAG}.json"
out.write_text(json.dumps(
    {"crops": [p.name for p in paths], "A": a, "B": b, "C_unshuffled": c},
    indent=1))
print(f"\nwrote {out}")
print("VERDICT within process:",
      "FIXED" if not d1 and not d2 else "NOT a function of the crop alone")
