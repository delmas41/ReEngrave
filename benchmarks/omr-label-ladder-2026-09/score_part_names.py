"""Score the exported <part-name>s against the truth file's.

OMR-NED does not score part names, so the one channel this flag reaches the
export through is invisible to both benchmark pools. That is a reason to measure
it separately, NOT a reason to assume the changes are improvements -- a rename
is only good if it moves toward the truth, and `Oboe -> Flute` could be either.

Matching is by INSTRUMENT FAMILY on a normalised name, positionally by part
order, because our part list and the truth's need not be the same length; a work
whose lengths differ is reported and not scored, rather than aligned by guess.
"""
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def part_names(p: Path) -> list[str]:
    if not p.is_file():
        return []
    root = ET.parse(p).getroot()
    return [(e.findtext("part-name") or "").strip()
            for e in root.iter("score-part")]


def norm(s: str) -> str:
    s = re.sub(r"\s*\d+\s*$", "", s.strip()).lower()
    s = re.sub(r"[^a-z ]", "", s)
    return s.strip()


PLACEHOLDER = re.compile(r"^staff p\d+-s\d+-\d+$", re.I)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--truth-suffix", default=".musicxml")
    args = ap.parse_args()

    A, B = Path(args.off), Path(args.on)
    tot = {"off": [0, 0], "on": [0, 0]}      # [correct, placeholder]
    for a in sorted(A.glob("*.omr.musicxml")):
        b = B / a.name
        work = a.name[: -len(".omr.musicxml")]
        truth = A / f"{work}{args.truth_suffix}"
        if not (b.is_file() and truth.is_file()):
            continue
        t = [norm(x) for x in part_names(truth)]
        na, nb = part_names(a), part_names(b)
        if na == nb:
            for names, key in ((na, "off"), (nb, "on")):
                tot[key][0] += sum(1 for i, x in enumerate(names)
                                   if i < len(t) and norm(x) == t[i])
                tot[key][1] += sum(1 for x in names if PLACEHOLDER.match(x))
            continue
        print(f"=== {work}  (truth has {len(t)} parts, we emit {len(na)}) ===")
        for i, (x, y) in enumerate(zip(na, nb)):
            if x == y:
                continue
            want = t[i] if i < len(t) else "?"
            verdict = ("BETTER" if norm(y) == want and norm(x) != want else
                       "WORSE" if norm(x) == want and norm(y) != want else
                       "neither (truth says %r)" % want)
            print(f"  part {i:>2}: {x!r} -> {y!r}   {verdict}")
        for names, key in ((na, "off"), (nb, "on")):
            tot[key][0] += sum(1 for i, x in enumerate(names)
                               if i < len(t) and norm(x) == t[i])
            tot[key][1] += sum(1 for x in names if PLACEHOLDER.match(x))
    print()
    print(f"part names matching truth positionally:  "
          f"off {tot['off'][0]}   on {tot['on'][0]}")
    print(f"unnamed placeholder parts (Staff p0-s0-N): "
          f"off {tot['off'][1]}   on {tot['on'][1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
