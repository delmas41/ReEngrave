"""2.274 step 2 r2: detector slur/tie BOX counts per page of the saved night record (counts only; no reader runs) -- how the two never-used hold-out pages are chosen.

    python3 boxcount.py PLATE PAGE[,PAGE...] [--tag 20261104-night]
"""
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as L  # noqa: E402
from tools.omr.staged.judged import iter_array  # noqa: E402


def main():
    argv = sys.argv[1:]
    tag = "20261104-night"
    if "--tag" in argv:
        i = argv.index("--tag")
        tag = argv[i + 1]
        del argv[i:i + 2]
    plate, pages = argv[0], set(int(x) for x in argv[1].split(","))
    c = collections.Counter()
    for it in iter_array(L.record_path(plate, tag), "observations"):
        if it.get("quantity") != "glyph_box":
            continue
        v = it.get("value")
        if not v or str(v[0]) not in ("slur", "tie"):
            continue
        pg = L.page_of(it.get("subject"))
        if pg in pages:
            c[pg] += 1
    print(plate, dict(sorted(c.items())))


if __name__ == "__main__":
    main()
