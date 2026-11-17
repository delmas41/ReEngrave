"""Lane arcs-r2: cut the combined stack's SAVED REAL GATHERS (`<work>/<plate>.on.gathered.record.json`, GATHER with the page-arc reader on) into lane-report
slice directories, so the binder can be re-adjudicated in minutes (`lane_report --from adjudicate --replay-gathered --tag SLICEDIR`) with no re-gather.

    python3 build_slices_r2.py OUTDIR PLATE:RECORD.json:pages [...]
Keeps every row of the given pages and every document-level row; verdicts only the stored quantities (lane_report.STORED_QUANTITIES). OUTDIR/<plate>/ is the slice.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as L  # noqa: E402
from tools.omr.staged.judged import iter_array  # noqa: E402


def cut(plate, rp, pages, d):
    d.mkdir(parents=True, exist_ok=True)
    keep = set(pages)
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
        print(plate, kind, n, flush=True)
    st = rp.stat()
    (d / "stamp.json").write_text(json.dumps({"pages": sorted(keep), "size": st.st_size, "mtime": int(st.st_mtime), "injected": []}))


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    for spec in sys.argv[2:]:
        plate, rec, pg = spec.split(":")
        cut(plate, pathlib.Path(rec), [int(x) for x in pg.split(",")], out / plate)
