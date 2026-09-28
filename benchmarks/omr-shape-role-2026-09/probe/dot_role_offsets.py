"""ROADMAP 2.12c — measure the (dx, dy) offset of every `augmentationDot` and
`articStaccato*` box relative to its nearest notehead, in staff spaces, BEFORE
choosing any cut.

CLAUDE.md Sec.10 states the convention: an augmentation dot sits to the RIGHT
of its notehead and level with it (in the space above, on a line note); a
staccato sits directly ABOVE or BELOW the head, centred on its x, on the
opposite side from the stem. This probe measures both populations against
that convention so the cut in `rhythm.py` is taken in an observed gap, not
assumed.

⚠️ READ-ONLY. Changes no code, decides nothing. Every number comes from
`tools.omr.staged.record_io.load_record` (CLAUDE.md Sec.4b) -- never a naive
`json.load`, which would iterate the pooled id-list strings as if they were
rows.

Run:

    python3 benchmarks/omr-shape-role-2026-09/probe/dot_role_offsets.py --all
    python3 benchmarks/omr-shape-role-2026-09/probe/dot_role_offsets.py \
        --record <path> --label <id> --out <json>
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO))
_PROBE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROBE_DIR))

from role_disagreement import Rec, _box_value, _cell_of, _resolve  # noqa: E402

_NOTEHEAD_PREFIX = "notehead"
_DOT_CLASS = "augmentationDot"
#: The staccato spellings gather.py's `_ARTIC_PREFIX` test admits today --
#: the two fine, side-bearing classes and the coarse, side-blind one
#: (`class_aliases.COARSER_THAN_CANONICAL["articulationStaccato"]`: "no SIDE").
_STACCATO_CLASSES = ("articStaccatoAbove", "articStaccatoBelow",
                     "articulationStaccato")


def _nearest_head(heads_by_cell, cell, x, y):
    """The nearest notehead CENTRE in this cell, by euclidean distance."""
    best = None
    for hx, hy in heads_by_cell.get(cell, ()):
        d = (hx - x) ** 2 + (hy - y) ** 2
        if best is None or d < best[0]:
            best = (d, hx, hy)
    return best


def _offsets(r: Rec) -> dict:
    heads_by_cell = collections.defaultdict(list)
    for subj, o in r.box.items():
        b = _box_value(o["value"])
        if b and b[0].startswith(_NOTEHEAD_PREFIX):
            _n, x, y, w, h = b
            heads_by_cell[_cell_of(subj)].append((x + w / 2.0, y + h / 2.0))

    rows = []
    no_space = no_head = 0
    for subj, o in r.box.items():
        b = _box_value(o["value"])
        if b is None:
            continue
        name = b[0]
        if name != _DOT_CLASS and name not in _STACCATO_CLASSES:
            continue
        _n, x, y, w, h = b
        cx, cy = x + w / 2.0, y + h / 2.0
        cell = _cell_of(subj)
        sp = r.cell_space_px(subj)
        if sp is None:
            no_space += 1
            continue
        near = _nearest_head(heads_by_cell, cell, cx, cy)
        if near is None:
            no_head += 1
            continue
        _d, hx, hy = near
        rows.append({
            "class": name,
            "detector_role": "dot" if name == _DOT_CLASS else "staccato",
            # positive: this box's centre sits to the RIGHT of the head's.
            "dx": round((cx - hx) / sp, 4),
            # positive: this box's centre sits ABOVE the head's (smaller y).
            "dy": round((hy - cy) / sp, 4),
        })
    return {"rows": rows, "no_cell_staff_space": no_space,
            "no_notehead_in_cell": no_head}


def _percentiles(values, pcts=(5, 25, 50, 75, 95)):
    if not values:
        return {}
    v = sorted(values)
    out = {}
    for p in pcts:
        idx = min(len(v) - 1, max(0, int(round(p / 100.0 * (len(v) - 1)))))
        out["p%d" % p] = v[idx]
    return out


def _summarize(rows):
    by_role = collections.defaultdict(lambda: {"dx": [], "dy": []})
    for row in rows:
        by_role[row["detector_role"]]["dx"].append(row["dx"])
        by_role[row["detector_role"]]["dy"].append(row["dy"])
    out = {}
    for role, d in by_role.items():
        out[role] = {
            "n": len(d["dx"]),
            "dx": _percentiles(d["dx"]),
            "dy": _percentiles(d["dy"]),
        }
    return out


def run(path: Path, label: str) -> dict:
    r = Rec(path)
    off = _offsets(r)
    return {
        "label": label,
        "record": str(path),
        "provenance": {"commit": r.provenance.get("commit"),
                       "dirty": r.provenance.get("dirty")},
        "no_cell_staff_space": off["no_cell_staff_space"],
        "no_notehead_in_cell": off["no_notehead_in_cell"],
        "summary": _summarize(off["rows"]),
        "rows": off["rows"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record")
    ap.add_argument("--label", default="?")
    ap.add_argument("--out")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    if a.all:
        man = json.loads(
            (_REPO / "benchmarks/acceptance/manifest.json").read_text())
        results = []
        outdir = _REPO / "benchmarks/omr-shape-role-2026-09/out"
        outdir.mkdir(parents=True, exist_ok=True)
        for doc in man["documents"]:
            p = _resolve(doc)
            dst = outdir / ("dot-role-offsets--%s.json" % doc["id"])
            print("=== %s  %s" % (doc["id"], p), flush=True)
            if not p.exists():
                print("   MISSING", flush=True)
                continue
            rc = subprocess.call(
                [sys.executable, __file__, "--record", str(p),
                 "--label", doc["id"], "--out", str(dst)],
                env={**os.environ, "PYTHONPATH": str(_REPO)})
            if rc != 0:
                print("   FAILED rc=%d" % rc, flush=True)
                continue
            results.append(json.loads(dst.read_text()))
        (outdir / "dot-role-offsets--all.json").write_text(
            json.dumps([{k: v for k, v in r.items() if k != "rows"}
                       for r in results], indent=1))
        for r in results:
            print()
            print("===", r["label"], "===")
            print(json.dumps(r["summary"], indent=1))
            print("no_cell_staff_space:", r["no_cell_staff_space"],
                 " no_notehead_in_cell:", r["no_notehead_in_cell"])
        return 0

    if not a.record:
        ap.error("--record or --all")
    res = run(Path(a.record), a.label)
    text = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).write_text(text)
        print("wrote", a.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
