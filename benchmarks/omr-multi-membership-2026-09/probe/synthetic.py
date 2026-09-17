"""Does `bridge_join` work AT ALL? Synthetic ink, geometry I control.

⚠️⚠️ THIS EXISTS BECAUSE A CONTROL LIED. `positive_control.py`'s first run
printed *"POSITIVE CONTROL: the bridge is alive"* under a table showing **0
bridges**, on an image that had just been shattered 1,244 -> 4,513 components.
The sentence was written before the number and survived it — the *control that
computes the wrong thing* family, arriving inside the control built to prevent
exactly that.

So the machinery is tested on ink whose every dimension is chosen here, where
the right answer is known by construction and cannot be argued:

  * a vertical stroke crossed by a horizontal line -> naive erasure of the line
    breaks it into two; the bridge MUST re-join them;
  * two strokes side by side on one line -> the bridge must NOT join them
    horizontally (the degenerate re-merge this design exists to prevent);
  * two marks stacked with PAPER between -> the bridge must refuse and naive
    dilation must accept. That is the pair that makes the two arms different.

Usage:  python3 probe/synthetic.py
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from bridge import bridge_join, components, groups_of        # noqa: E402

H, W = 60, 40
LINE_Y, LINE_T = 30, 4          # a 4-px line at row 30


def _case(draw):
    """-> (n_erased_components, n_groups_bridge, n_groups_dilate)"""
    intact = np.zeros((H, W), bool)
    draw(intact)
    erased = intact.copy()
    erased[LINE_Y:LINE_Y + LINE_T, :] = False        # NAIVE: erase the row
    removed = intact & ~erased
    n, lab, stats = components(erased)
    pb, _eb = bridge_join(lab, removed, bound=LINE_T, require_removed=True)
    pd, _ed = bridge_join(lab, removed, bound=LINE_T, require_removed=False)
    return n - 1, len(groups_of(pb, stats)), len(groups_of(pd, stats))


def stroke(a):                      # one vertical stroke through the line
    a[10:50, 18:23] = True


def two_strokes(a):                 # two strokes, both through the line
    a[10:50, 6:11] = True
    a[10:50, 29:34] = True


def stacked_with_paper(a):          # two marks, a PAPER gap, no line between
    a[8:20, 16:24] = True
    a[23:34, 16:24] = True


def line_only(a):                   # the bare line: nothing should survive
    a[LINE_Y:LINE_Y + LINE_T, :] = True


def main() -> int:
    ok = True

    n, b, d = _case(stroke)
    print(f"stroke through a line      erased={n}  bridge={b}  dilate={d}"
          f"   want erased=2 bridge=1")
    ok &= (n == 2 and b == 1)

    n, b, d = _case(two_strokes)
    print(f"two strokes on one line    erased={n}  bridge={b}  dilate={d}"
          f"   want erased=4 bridge=2  (never 1: no horizontal bridge)")
    ok &= (n == 4 and b == 2)

    n, b, d = _case(stacked_with_paper)
    print(f"stacked, PAPER between     erased={n}  bridge={b}  dilate={d}"
          f"   want erased=2 bridge=2 dilate=1  <- the arms MUST differ")
    ok &= (n == 2 and b == 2 and d == 1)

    n, b, d = _case(line_only)
    print(f"bare line, nothing else    erased={n}  bridge={b}  dilate={d}"
          f"   want erased=0")
    ok &= (n == 0)

    print("\nPASS" if ok else "\nFAIL — the machinery does not do what the "
          "method claims; every zero it reports is uninterpretable")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
