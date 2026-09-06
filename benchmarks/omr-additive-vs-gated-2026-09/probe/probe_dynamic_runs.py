"""`export.measure_dynamics` -- the refused letter runs, with the evidence it
had in hand and did not read.

The function assembles adjacent dynamic-letter detections into a word and drops
the run outright unless the word is in `_DYNAMIC_WORDS`. Per-letter detection
`confidence` is on every `det` at that moment and is never read; nor is the edit
distance to the nearest legal dynamic.

This replays the same assembly over the committed transcriptions of both
benchmark families and reports the refused runs: how many, what they spelled,
their letters' confidences, and their edit distance to the nearest legal word.
Reads only; changes nothing.
"""
from __future__ import annotations

import collections
import glob
import json
import os
import sys

ROOT = os.environ.get("OMR_FIXTURE_ROOT", os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from tools.omr.export import _DYNAMIC_LETTER, _DYNAMIC_WORDS  # noqa: E402

PATTERNS = [
    ("scan", ROOT + "/benchmarks/omr-scan-e2e-2026-09/fixtures/"
             "*.graft09.omr.json"),
    ("engraved", ROOT + "/benchmarks/omr-orchestral-e2e/fixtures/*.omr.json"),
]


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def nearest(word: str) -> tuple[str, int]:
    return min(((w, edit_distance(word, w)) for w in _DYNAMIC_WORDS),
               key=lambda wd: (wd[1], len(wd[0])))


def runs(detections):
    """Exactly `measure_dynamics`' assembly, but yielding EVERY run."""
    letters = []
    for det in detections:
        letter = _DYNAMIC_LETTER.get(det.get("class") or "")
        box = det.get("bbox")
        if letter and box and len(box) == 4:
            letters.append((box[0], box[1], box[2], letter,
                            det.get("confidence")))
    if not letters:
        return []
    letters.sort()
    width = max(w for _x, _y, w, _l, _c in letters) or 1
    out, word, confs = [], letters[0][3], [letters[0][4]]
    run_y = letters[0][1]
    prev_right = letters[0][0] + letters[0][2]
    for x, y, w, letter, c in letters[1:]:
        if x - prev_right <= width and abs(y - run_y) <= width:
            word += letter
            confs.append(c)
        else:
            out.append((word, confs))
            word, confs, run_y = letter, [c], y
        prev_right = x + w
    out.append((word, confs))
    return out


def main():
    for fam, pat in PATTERNS:
        paths = sorted(p for p in glob.glob(pat)
                       if fam == "scan" or ("graft09" not in p
                                            and "restamp" not in p))
        kept = refused = 0
        spelled = collections.Counter()
        by_dist = collections.Counter()
        confs_kept, confs_refused = [], []
        for path in paths:
            for page in json.load(open(path)).get("pages", []):
                for sysm in page.get("systems", []):
                    for st in sysm.get("staves", []):
                        for m in st.get("measures", []):
                            for word, confs in runs(m.get("detections", [])):
                                cs = [c for c in confs
                                      if isinstance(c, (int, float))]
                                if word in _DYNAMIC_WORDS:
                                    kept += 1
                                    confs_kept += cs
                                else:
                                    refused += 1
                                    confs_refused += cs
                                    spelled[word] += 1
                                    by_dist[nearest(word)[1]] += 1
        tot = kept + refused
        print(f"\n{'='*76}\n{fam.upper()}  dynamic letter runs\n{'='*76}")
        print(f"   runs assembled                {tot:5d}")
        print(f"   exported (a legal word)       {kept:5d}  "
              f"{kept/max(1,tot):5.1%}")
        print(f"   REFUSED, dropped entirely     {refused:5d}  "
              f"{refused/max(1,tot):5.1%}")
        print("   edit distance from the refused run to the nearest legal "
              "dynamic:")
        for d, n in sorted(by_dist.items()):
            print(f"      distance {d}: {n:5d}  {n/max(1,refused):5.1%}")
        print("   what the refused runs spelled (top 15):")
        for w, n in spelled.most_common(15):
            print(f"      {w!r:12s} {n:5d}   nearest={nearest(w)}")
        for tag, cs in (("kept", confs_kept), ("refused", confs_refused)):
            if not cs:
                continue
            cs.sort()
            print(f"   letter confidence, {tag}: n={len(cs)} "
                  f"p25={cs[len(cs)//4]:.3f} med={cs[len(cs)//2]:.3f} "
                  f"p75={cs[3*len(cs)//4]:.3f}")


if __name__ == "__main__":
    main()
