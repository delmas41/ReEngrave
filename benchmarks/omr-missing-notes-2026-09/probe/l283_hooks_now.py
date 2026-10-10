"""l283_hooks_now: what the CURRENT 2.69 hook counter (`gather.stem_tip_hooks`) says at the true tip of every matched truth
FLAGGED stem on Sean's page (the 21 with a CV stem), and the reason when it cannot count. If the counter cannot count a
single printed eighth flag, a reader that only says "a flag is there" would hand `flag_ink_unread` (8th | 16th) a narrowing
and not a decision, and the fix has to reach the counter too. ROADMAP 2.83 probe.
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from l283_common import cell_space  # noqa: E402
from l283_dataset import build  # noqa: E402
from l283_features import head_edges_canonical  # noqa: E402


def main():
    from tools.omr.staged import gather as G
    T, cells, rows = build(sys.argv[1])
    out = collections.defaultdict(collections.Counter)
    detail = []
    for r in rows:
        if r["cv"] is None or r["label"] not in ("flag", "bare"):
            continue
        c = r["cv"]["cell"]
        s = cell_space(c)
        x, y, w, h = r["cv"]["stem"]
        tip_y, sign = (y, 1.0) if r["tip_end"] == "top" else (y + h, -1.0)
        img = (~c["img"]).astype("uint8") * 255
        heads = [(a, b, c_ - a, d - b) for a, b, c_, d in head_edges_canonical(T, c)]
        edge, here = G._head_edge_for_end(heads, x, x + w, tip_y, sign, s)
        if here:
            out[r["label"]]["head_at_this_end"] += 1
            continue
        m = G.stem_tip_hooks(img, x, x + w, tip_y, sign, s, head_edge=edge)
        key = "None" if m is None else (f"hooks={m['hooks']}" if m["hooks"] else f"uncounted[{m['hooks_min']}..{m['hooks_max']}] {m['hooks_reason']}")
        out[r["label"]][key] += 1
        if r["label"] == "flag":
            detail.append((r["stem"], key, m["hooks_support"] if m else None))
    for lab, cnt in out.items():
        print(lab, dict(cnt))
    for d in detail:
        print("  ", d)


if __name__ == "__main__":
    main()
