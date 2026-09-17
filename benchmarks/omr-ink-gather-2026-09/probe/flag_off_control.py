"""Flag OFF must be byte-identical to a tree that has never heard of `Q.INK`.

⚠️⚠️ THE CONTROL THAT MATTERS IS AGAINST `origin/main`, NOT AGAINST MYSELF.
Comparing my own flag-off arm with my own flag-on arm proves only that the
branch is taken; it cannot see a row this change added OUTSIDE `gather_ink`,
which is exactly the kind of thing that perturbs every byte-identity control
downstream of it. So `origin/main`'s `gather.py` is loaded as a module and run
over the SAME prepared page and the SAME detections, and the three logs are
compared by md5 of their serialised rows.

⚠️ THE DETECTOR IS SHARED AND MEMOISED. A from-scratch rebuild of the hairpin
fix reproduced the categorical result and NOT the edit count -- the same four
boxes' confidences moved between runs on byte-identical code. Two arms that
each call the detector are not a controlled comparison.

⚠️ AND THE POSITIVE CONTROL IS THE POINT: the flag-ON arm MUST differ. Without
it, a comparison that reports "identical" is indistinguishable from one that
compared a file with itself -- the `regather_control.py` lesson.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_DIRECTION_TEXT", "0")

from tools.omr.staged.record import Log                          # noqa: E402

WEIGHTS = str(ROOT / "omr-weights"
              / "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")


class Memo:
    """One detector call per cell, replayed. See the docstring."""

    def __init__(self, inner):
        self.inner = inner
        self.cache = {}

    def detect(self, cell, **kw):
        key = (cell.staff_index, cell.measure_index)
        if key not in self.cache:
            self.cache[key] = self.inner.detect(cell, **kw)
        return self.cache[key]


def load_main_gather():
    """`origin/main`'s `gather.py`, as a module, with this tree's siblings."""
    src = subprocess.run(
        ["git", "-C", str(ROOT), "show", "origin/main:tools/omr/staged/gather.py"],
        capture_output=True, text=True, check=True).stdout
    path = ROOT / "benchmarks" / "omr-ink-gather-2026-09" / "out" / "_main_gather.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(src)
    spec = importlib.util.spec_from_file_location(
        "tools.omr.staged._main_gather", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod, path


def digest(log: Log) -> str:
    rows = []
    for r in log.all_rows():
        rows.append(json.dumps(r.to_json(), sort_keys=True, default=str))
    rows.sort()
    return hashlib.md5("\n".join(rows).encode()).hexdigest(), len(rows)


def run(gather_mod, prepared, detector, *, ink):
    old = os.environ.get("OMR_INK")
    if ink:
        os.environ["OMR_INK"] = "1"
    else:
        os.environ.pop("OMR_INK", None)
    try:
        return gather_mod.gather(prepared, detector=detector,
                                 surya_fallback=False, ocr_fallback=False)
    finally:
        if old is None:
            os.environ.pop("OMR_INK", None)
        else:
            os.environ["OMR_INK"] = old


def main() -> int:
    pdf, page = sys.argv[1], int(sys.argv[2])
    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged import gather as mine
    from tools.omr.yolo_detector import YoloDetector

    prepared = prepare_pages(pdf, [page], dpi=600)
    det = Memo(YoloDetector(WEIGHTS))

    main_mod, tmp = load_main_gather()
    try:
        h_main, n_main = digest(run(main_mod, prepared, det, ink=False))
        h_off, n_off = digest(run(mine, prepared, det, ink=False))
        h_on, n_on = digest(run(mine, prepared, det, ink=True))
    finally:
        tmp.unlink(missing_ok=True)

    print(f"origin/main, flag absent : {h_main}  rows {n_main}")
    print(f"this tree,  OMR_INK off  : {h_off}  rows {n_off}")
    print(f"this tree,  OMR_INK=1    : {h_on}  rows {n_on}")

    ok = True
    if h_off != h_main:
        print("\nFAIL: flag-off is NOT byte-identical to origin/main")
        ok = False
    else:
        print("\nflag-off == origin/main, to the byte")
    if h_on == h_off:
        print("FAIL (positive control): the flag changes nothing, so the "
              "comparison above proves nothing")
        ok = False
    else:
        print(f"positive control: the flag DOES change the log "
              f"(+{n_on - n_off} rows)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
