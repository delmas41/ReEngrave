"""2.274 step 2 r2: cut an injected slice directory down to fewer pages, so a develop run replays ONLY the develop pages (the lane report replays every page of a slice: a develop run on a
slice that holds hold-out pages computes the hold-out arms too, which step 2 had to confess).

    python3 cutslice.py SRC_SLICES DST_SLICES PLATE PAGE[,PAGE...]
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as L  # noqa: E402


def main():
    src, dst, plate, pages = sys.argv[1:5]
    keep = set(int(x) for x in pages.split(","))
    s, d = pathlib.Path(src) / plate, pathlib.Path(dst) / plate
    d.mkdir(parents=True, exist_ok=True)
    for kind in ("observations", "abstentions", "verdicts"):
        n = 0
        with open(s / ("%s.jsonl" % kind)) as fi, open(d / ("%s.jsonl" % kind), "w") as fo:
            for line in fi:
                # the page is in the subject key; cheap check before parsing
                it = json.loads(line)
                pg = L.page_of(it.get("subject"))
                if pg is None or pg in keep:
                    fo.write(line)
                    n += 1
        print(plate, kind, n, flush=True)
    st = json.loads((s / "stamp.json").read_text())
    st["pages"] = sorted(keep)
    st["injected"] = [p for p in st.get("injected", []) if p in keep]
    (d / "stamp.json").write_text(json.dumps(st))


if __name__ == "__main__":
    main()
