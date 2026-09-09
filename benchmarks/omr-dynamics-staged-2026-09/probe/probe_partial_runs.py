"""What a DISCARDED dynamic letter run actually is — over stored transcriptions.

`export.measure_dynamics` assembles adjacent `dynamic*` letter glyphs into a
word and then **drops the run whole** if it does not spell one of the 17 entries
in `_DYNAMIC_WORDS`. This counts what is being dropped, and — the part that
decides what a partial run may EXPORT as — whether the dropped string is a
PREFIX of a real dynamic word or something no dynamic begins with.

⚠️ It re-implements nothing: it calls `export.measure_dynamics` for the KEPT
runs and re-runs the module's own assembly loop for the dropped ones, so the
two populations are cut by the same code that ships.

    python3 benchmarks/omr-dynamics-staged-2026-09/probe/probe_partial_runs.py \
        --transcriptions <a.json> [<b.json> ...]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from tools.omr import export as E   # noqa: E402


def runs_of(detections):
    """Every assembled run, kept or not — the module's own loop, verbatim."""
    letters = []
    for det in detections:
        letter = E._DYNAMIC_LETTER.get(det.get("class") or "")
        box = det.get("bbox")
        if letter and box and len(box) == 4:
            letters.append((box[0], box[1], box[2], letter))
    if not letters:
        return []
    letters.sort()
    width = max(w for _x, _y, w, _l in letters) or 1
    out, n = [], 1
    run_x, run_y, word = letters[0][0], letters[0][1], letters[0][3]
    prev_right = letters[0][0] + letters[0][2]
    for x, y, w, letter in letters[1:]:
        if x - prev_right <= width and abs(y - run_y) <= width:
            word += letter
            n += 1
        else:
            out.append((word, n))
            run_x, run_y, word, n = x, y, letter, 1
        prev_right = x + w
    out.append((word, n))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcriptions", nargs="+", type=pathlib.Path,
                    required=True)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    args = ap.parse_args()

    kept = collections.Counter()
    dropped = collections.Counter()
    dropped_letters = 0
    kept_letters = 0
    for path in args.transcriptions:
        doc = json.loads(path.read_text())
        for pg in doc.get("pages", []):
            for sy in pg.get("systems", []):
                for st in sy.get("staves", []):
                    for m in st.get("measures", []):
                        for word, n in runs_of(m.get("detections", [])):
                            if word in E._DYNAMIC_WORDS:
                                kept[word] += 1
                                kept_letters += n
                            else:
                                dropped[word] += 1
                                dropped_letters += n

    # Is the dropped string the START of a real dynamic word?
    prefixes = collections.Counter()
    for word, c in dropped.items():
        hits = sorted(w for w in E._DYNAMIC_WORDS if w.startswith(word))
        prefixes["prefix_of_" + ("|".join(hits) if hits else "NOTHING")] += c

    res = {
        "kept_runs": sum(kept.values()), "kept_letters": kept_letters,
        "dropped_runs": sum(dropped.values()), "dropped_letters": dropped_letters,
        "kept_by_word": dict(kept.most_common()),
        "dropped_by_word": dict(dropped.most_common()),
        "dropped_prefix_classification": dict(prefixes.most_common()),
        "dropped_that_are_a_prefix_of_something":
            sum(c for w, c in dropped.items()
                if any(x.startswith(w) for x in E._DYNAMIC_WORDS)),
    }
    print(json.dumps(res, indent=2))
    if args.out:
        args.out.write_text(json.dumps(res, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
