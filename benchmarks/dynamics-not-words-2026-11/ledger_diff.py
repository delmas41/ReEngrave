"""ROADMAP 2.301 measure: which ink changes KIND between two arms of the page-claim replay (`replay_claims`), as the ledger canvas (`claim_readout.build_page`) sees it.

    python3 benchmarks/dynamics-not-words-2026-11/ledger_diff.py --plate brahms --slice SLICE --page 0 [--env-a NAME=V ...] --env-b NAME=V ... [--tree-a PATH]

Arm A = this tree with `--env-a`; arm B = this tree with `--env-b`. Prints, per (kind on A -> kind on B), the dark pixels that moved, and the page boxes of the moved regions
(8-connected, at least 6 px). Reads rows and the master cell map; writes nothing.
"""
import argparse
import collections
import os
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def kind_map(canvas):
    from tools.omr.staged import claim_readout as CR
    fam = np.asarray(canvas.fam_eff)
    st = np.asarray(canvas.state)
    ink = np.asarray(canvas.ink)
    names = sorted(CR.FINE_BIT)
    out = np.zeros(fam.shape, np.int16)
    for i, k in enumerate(names, 1):
        out[ink & ((fam & int(CR.FINE_BIT[k])) != 0) & (st != CR.ST_WEAK) & (st != CR.ST_NONE)] = i      # the last kind in name order wins a twin pixel; the diff is by whole map
    return out, names


def diff(plate, slice_dir, page, env_a, env_b):
    import cv2
    import ledger_probe as LP
    ca, _ = LP.canvas_of(plate, slice_dir, page, env_a)
    ma, names = kind_map(ca)
    del ca
    cb, _ = LP.canvas_of(plate, slice_dir, page, env_b)
    mb, _ = kind_map(cb)
    del cb
    moved = ma != mb
    pairs = collections.Counter((names[a - 1] if a else "-", names[b - 1] if b else "-") for a, b in zip(ma[moved].tolist(), mb[moved].tolist()))
    n, lab, st, _c = cv2.connectedComponentsWithStats(moved.astype(np.uint8), connectivity=8)
    boxes = []
    for k in range(1, n):
        x, y, w, h, area = (int(v) for v in st[k])
        if area >= 6:
            sub = lab[y:y + h, x:x + w] == k
            fa = collections.Counter(names[v - 1] if v else "-" for v in ma[y:y + h, x:x + w][sub].tolist())
            fb = collections.Counter(names[v - 1] if v else "-" for v in mb[y:y + h, x:x + w][sub].tolist())
            boxes.append(dict(box=[x, y, x + w, y + h], px=area, a=dict(fa), b=dict(fb)))
    return dict(pairs={"%s->%s" % k: v for k, v in pairs.items()}, regions=sorted(boxes, key=lambda r: -r["px"]), px=int(moved.sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plate", required=True)
    ap.add_argument("--slice", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--env-a", nargs="*", default=[])
    ap.add_argument("--env-b", nargs="*", default=[])
    a = ap.parse_args()
    got = diff(a.plate, a.slice, a.page, dict(e.split("=", 1) for e in a.env_a), dict(e.split("=", 1) for e in a.env_b))
    print("moved px", got["px"], got["pairs"])
    for r in got["regions"]:
        print(r)


if __name__ == "__main__":
    main()
