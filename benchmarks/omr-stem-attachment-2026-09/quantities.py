"""Which quantities a record actually carries, and how many rows of each.

⚠️ WHY THIS IS HERE AND NOT A GREP OF `record.Q`. The question this directory
has to answer first is not *what does the vocabulary declare* but *what could a
tier in ADJUDICATE actually READ*. `Evidence` exposes `rows()` and
`refusals()` and nothing else -- no raster, no page image; no adjudicator in
the tree imports `cv2`, `numpy`, `fitz` or `PIL`. So the attachment convention,
which is a reading of PIXELS, can only reach a tier through a quantity that is
already on the record.

This lists what is on it. If nothing here carries the side and reach of the ink
beside a notehead, the convention needs a GATHER producer before it can be a
tier at all -- and that is a different job in a different file.
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: quantities.py <record.json>", file=sys.stderr)
        return 2
    path = sys.argv[1]
    obs: collections.Counter = collections.Counter()
    keys: dict[str, set] = collections.defaultdict(set)
    for o in stream_array(path, "observations"):
        q = str(o.get("quantity"))
        obs[q] += 1
        if obs[q] <= 200:
            keys[q] |= set((o.get("detail") or {}).keys())
    if not obs:
        print(f"DEAD: {Path(path).name} holds no observations", file=sys.stderr)
        return 2
    print(f"{Path(path).name}: {sum(obs.values())} observations, "
          f"{len(obs)} quantities\n")
    for q, n in obs.most_common():
        print(f"{n:>8}  {q}")
        if keys[q]:
            print(f"          detail: {sorted(keys[q])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
