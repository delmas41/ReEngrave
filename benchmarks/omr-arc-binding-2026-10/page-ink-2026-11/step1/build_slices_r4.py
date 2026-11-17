"""2.274 r4: cut the saved 20261104-night record to the dev + hold-out pages (+ spares), into OUT/<plate>/ (a directory tag for lane_report.slice_dir).

    python3 build_slices_r3.py OUT        (one plate at a time is streamed; ~2 GB read each)
"""
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as L  # noqa: E402
from tools.omr.staged.judged import iter_array  # noqa: E402

PAGES = {"brahms": [0, 4, 5, 7, 9, 12, 14, 19, 22, 25, 11, 20, 8, 10, 15, 17, 18, 21], "litolff": [3, 4, 6, 8, 9, 10, 12, 16, 5, 13, 7, 11, 14, 15, 17]}
TAG = "20261104-night"


def main():
    out = pathlib.Path(sys.argv[1])
    for plate, pages in PAGES.items():
        d = out / plate
        d.mkdir(parents=True, exist_ok=True)
        rp = L.record_path(plate, TAG)
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


if __name__ == "__main__":
    main()
