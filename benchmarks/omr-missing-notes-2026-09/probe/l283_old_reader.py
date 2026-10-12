"""l283_old_reader: what the CURRENT `gather.stem_tip_ink` (2.18c/2.73) says at the true tip of every matched truth stem,
by Sean's label. The base the new reader is measured against. ROADMAP 2.83 probe.

    python3 l283_old_reader.py CELLS.pkl.gz
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from l283_common import cell_space  # noqa: E402
from l283_dataset import build  # noqa: E402


def tip_of(row):
    x, y, w, h = row["cv"]["stem"]
    if row["tip_end"] == "top":
        return x, x + w, y, 1.0
    return x, x + w, y + h, -1.0


def main():
    from tools.omr.staged import gather as G
    T, cells, rows = build(sys.argv[1])
    res = collections.defaultdict(list)
    for r in rows:
        if r["cv"] is None or r["label"] == "trem":
            continue
        c = r["cv"]["cell"]
        s = cell_space(c)
        x0, x1, tip_y, sign = tip_of(r)
        m = G.stem_tip_ink(c["img"].__invert__().astype("uint8") * 255 if False else (~c["img"]).astype("uint8") * 255,
                           x0, x1, tip_y, sign, s)
        res[r["label"]].append((m, r))
    for lab in ("flag", "bare", "beam"):
        L = res[lab]
        n = len(L)
        none = sum(1 for m, _ in L if m is None)
        found = sum(1 for m, _ in L if m and m["right"] is not None and (m["right"] >= G.STEM_TIP_INK_DENSE and m["left"] <= G.STEM_TIP_INK_BACKGROUND_MAX))
        rv = sorted(round(m["right"], 3) for m, _ in L if m)
        print(f"{lab:5s} n={n} declined={none} reads_flag(old)={found}  right-band: {rv}")


if __name__ == "__main__":
    main()
