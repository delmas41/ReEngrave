"""2.274 step 2: cut the saved 20261104-night record to the pages named, and FILE THE STEP-1 `Q.PAGE_ARC` ROWS INTO EACH PAGE'S SLICE (no detector, no OCR).

    python3 build_inject.py PLATE OUTDIR PAGE[,PAGE...] [--tag 20261104-night] [--inject-only]

Why this exists: the saved night records were gathered with `OMR_PAGE_ARCS` OFF, so they hold no `Q.PAGE_ARC` rows, and the lane report's re-adjudication
(`--from adjudicate`) replays the saved GATHER rows. The rows are what `page_arcs.gather_page_arcs` files in GATHER; here that SAME function is run on the page's
rebuilt raster (`pipeline.prepare_pages` + `page_strokes.assemble` + `carve_columns`, exactly what `step1/canvas.py` and the r1-r4 measurements did; the
gather-vs-standalone control of step 1 is `step1/measure.py readback`) over the slice's own `glyph_box` / `claimed_area` rows, and its rows are appended to the slice.
The page stroke names (`page_strokes`) are left empty (no page stroke map here; step 2 does not read them).

OUTDIR/<plate>/{observations,abstentions,verdicts}.jsonl + stamp.json is a lane-report slice directory (`--tag OUTDIR`).
"""
import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.environ["OMR_SURYA_KEEP_ALIVE"] = "0"

from tools.omr.staged import lane_report as L  # noqa: E402
from tools.omr.staged.judged import iter_array  # noqa: E402


def cut(plate, pages, tag, d):
    d.mkdir(parents=True, exist_ok=True)
    rp = L.record_path(plate, tag)
    keep = set(pages)
    t0 = time.time()
    for kind in ("observations", "abstentions", "verdicts"):
        n = 0
        with open(d / ("%s.jsonl" % kind), "w") as fh:
            for it in iter_array(rp, kind):
                if kind == "verdicts" and it.get("quantity") not in L.STORED_QUANTITIES:
                    continue
                pg = L.page_of(it.get("subject"))
                if pg is None or pg in keep:
                    fh.write(json.dumps(it, default=str) + "\n")
                    n += 1
        print(plate, kind, n, "%.0fs" % (time.time() - t0), flush=True)
    st = rp.stat()
    (d / "stamp.json").write_text(json.dumps({"pages": sorted(pages), "size": st.st_size, "mtime": int(st.st_mtime), "injected": []}))


class _Map:
    """The least a page map the reader needs: the canvas and the spacing (no stroke map)."""

    def __init__(self, asm, sp):
        self.assembly = asm
        self.sp = sp
        self.masks = []
        self.strokes = []
        self.scale = 1.0


def inject_page(plate, page, d, quiet=True):
    from tools.omr.staged import pipeline as P, page_strokes as PS, barline_columns as BC, page_arcs as PA, gather as G, record as R
    from tools.omr.staged.record import Log, Subject
    pdf = str(L.LIB / L.PLATES[plate]["pdf"])
    (pws, cells), = P.prepare_pages(pdf, [page])
    asm = PS.assemble(pws, cells)
    sp = PS.page_spacing(pws)
    PS.carve_columns(asm.canvas, BC.fit_columns(pws), sp)
    local = G._system_local(pws.staves)
    obs_path = d / "observations.jsonl"
    keep, mx = [], 0
    with open(obs_path) as fh:
        for line in fh:
            o = json.loads(line)
            mx = max(mx, int(o["id"].split(":")[1]))
            if o["quantity"] in ("glyph_box", "claimed_area") and L.page_of(o.get("subject")) == page:
                keep.append(o)
    log = Log()         # only the two quantities the reader reads, row ids in `detail` left as they were (nothing here follows them)
    for o in sorted(keep, key=lambda t: int(t["id"].split(":")[1])):
        log.observe(Subject.from_key(o["subject"]), o["quantity"], o["value"], reader=o["reader"], frame=o["frame"], score=o.get("score"), **dict(o.get("detail") or {}))
    os.environ["OMR_PAGE_ARCS"] = "1"
    census = PA.gather_page_arcs(log, pws, cells, local, _Map(asm, sp), progress=not quiet)
    rows = [o for o in log.to_json()["observations"] if o["quantity"] == "page_arc"]
    with open(obs_path, "a") as fh:
        for i, o in enumerate(rows):
            o = dict(o)
            o["id"] = "obs:%06d" % (mx + 1 + i)
            fh.write(json.dumps(o, default=str) + "\n")
    print(plate, "p%d" % page, "page_arc rows", len(rows), "runs", (census or {}).get("runs"), flush=True)
    return len(rows)


def main():
    argv = sys.argv[1:]
    tag = "20261104-night"
    inject_only = "--inject-only" in argv
    if "--tag" in argv:
        i = argv.index("--tag")
        tag = argv[i + 1]
        del argv[i:i + 2]
    argv = [a for a in argv if a != "--inject-only"]
    plate, out, pages = argv[0], pathlib.Path(argv[1]), [int(x) for x in argv[2].split(",")]
    d = out / plate
    if not inject_only:
        cut(plate, pages, tag, d)
    stamp = json.loads((d / "stamp.json").read_text())
    want = [int(x) for x in os.environ.get("INJECT", "").split(",") if x] or pages      # INJECT=4,5: a context page is cut but not injected
    todo = [p for p in want if p not in stamp.get("injected", [])]
    for p in todo:
        inject_page(plate, p, d)
        stamp.setdefault("injected", []).append(p)
        (d / "stamp.json").write_text(json.dumps(stamp))


if __name__ == "__main__":
    main()
