"""ROADMAP 2.301: which KIND does the ledger give each ink pixel of a region, on this tree's page claims (`replay_claims.replay`) plus the saved page's cell settle?

    python3 benchmarks/dynamics-not-words-2026-11/ledger_probe.py --plate brahms --slice SLICE --page 0 --box X0 Y0 X1 Y1 [--box ...] [--env NAME=V ...]

Prints, per box, the dark pixels of the box by the fine kind(s) standing on them (`claim_readout.FINE_BIT`) and by `state`. Reads rows and the master cell map; writes nothing.
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


def canvas_of(plate, slice_dir, page, env=None):
    import replay_claims as RC
    from tools.omr.staged import cell_map as CM
    from tools.omr.staged import claim_readout as CR
    from tools.omr.staged import lane_report as LR
    got = RC.replay(plate, slice_dir, page, env)
    canvas, _v, _pws, _cells = CR.build_page(got["rows"], LR.LIB / LR.PLATES[plate]["pdf"], page, CM.ROOT_DEFAULT, ledger=True)
    canvas.finish()
    return canvas, got


def kinds_in(canvas, box):
    from tools.omr.staged import claim_readout as CR
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    fam = np.asarray(canvas.fam_eff)[y0:y1, x0:x1]
    st = np.asarray(canvas.state)[y0:y1, x0:x1]
    ink = np.asarray(canvas.ink)[y0:y1, x0:x1]
    out = collections.Counter()
    for k, bit in CR.FINE_BIT.items():
        n = int((ink & ((fam & int(bit)) != 0) & (st != CR.ST_WEAK) & (st != CR.ST_NONE)).sum())
        if n:
            out[k] = n
    return int(ink.sum()), dict(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plate", required=True)
    ap.add_argument("--slice", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--box", nargs=4, type=float, action="append", required=True)
    ap.add_argument("--env", nargs="*", default=[])
    a = ap.parse_args()
    canvas, got = canvas_of(a.plate, a.slice, a.page, dict(e.split("=", 1) for e in a.env))
    for b in a.box:
        print(b, kinds_in(canvas, b))


if __name__ == "__main__":
    main()
