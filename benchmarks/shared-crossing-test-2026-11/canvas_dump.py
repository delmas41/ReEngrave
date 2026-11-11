"""2.294: build the 2.293 ink canvas of a slice's pages (flag env as given) and save its per-pixel arrays (compressed) for the crossing analysis.
usage: python3 benchmarks/shared-crossing-test-2026-11/canvas_dump.py PLATE PAGES OUTDIR [NAME=V ...]"""
import os, sys, pathlib
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
plate, pages, outdir = sys.argv[1], [int(x) for x in sys.argv[2].split(",")], pathlib.Path(sys.argv[3])
for a in sys.argv[4:]:
    k, v = a.split("=", 1); os.environ[k] = v
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
from tools.omr.staged import claim_readout as CR
outdir.mkdir(parents=True, exist_ok=True)
rep = CR.run_ink("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/claim-readout-slices-%s.main" % plate, pages, keep_canvas=True, log=lambda *_: None)
for pg, c in rep["canvases"].items():
    np.savez_compressed(outdir / ("%s.p%d.npz" % (plate, pg)), ink=c.ink, fam=c.fam_eff, state=c.state, none_class=c.none_class, weak=c.weak, afam=c.afam,
                        rival=c.rival, open=c.open, twin=c.twin, uk=c.uk, incell=c.incell, staff=c.staff, sp=np.float32(c.sp))
    print(plate, pg, c.ink.shape, int(c.ink.sum()))
import json
(outdir / ("%s.tally.json" % plate)).write_text(json.dumps(rep["total"], default=str))
