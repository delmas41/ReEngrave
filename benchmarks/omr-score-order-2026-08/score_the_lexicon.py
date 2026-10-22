"""Score the instrument lexicon against real engravers' part lists.

`tools/omr/instruments.py` maps a printed label to an instrument, and until now
it was checked against hand-written cases and whatever labels a few scanned
pages happened to yield. The Gradus MusicXML library is a much better ruler:
`<part-list>` is what an engraver actually wrote, in the order they wrote it,
with no OCR in between. 500+ works, of which ~110 are orchestral.

Two numbers come out, and they answer different questions:

  **resolved**   what fraction of real part names the lexicon can read at all.
                 A miss here is a staff with no instrument identity, which
                 costs the clef, transposition and register priors downstream.

  **monotone**   how many works come out in score order — woodwind, brass,
                 percussion, harp and keyboards, then strings. Score order is
                 a convention, so a work that violates it is either a genuinely
                 different layout or a lexicon that has misread a label. It is
                 almost always the second, which makes this a sharper test of
                 the lexicon than "resolved" alone: `Basso` reads fine and
                 reads WRONG, and only the order shows it.

The second number is reported twice — for the lexicon alone, and again allowing
`instruments.AMBIGUOUS_ALIASES` to be settled by position, which is what
`score_layouts.resolve_ambiguous_label` does against a real layout fit. The gap
between them is what the score-order prior is worth.

Baroque works are excluded from the monotone count and reported separately:
their layout genuinely differs (continuo last, soloists first), so counting
them as failures would be measuring the wrong thing.

    python3 benchmarks/omr-score-order-2026-08/score_the_lexicon.py
    python3 benchmarks/omr-score-order-2026-08/score_the_lexicon.py --misses
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.instruments import candidates_for_alias, lookup  # noqa: E402

DEFAULT_LIBRARY = "/Users/seanjohnson/Desktop/gradus-vercel/public/scores"

# Score order by family. Harp, piano, celesta and organ rank with the keyboards
# ABOVE the strings — this is score order, not the family taxonomy, and a harp
# is where the two disagree.
FAMILY_RANK = {"woodwind": 0, "brass": 1, "percussion": 2,
               "keyboard": 3, "voice": 4, "string": 5}


def part_names(path: str) -> list[str] | None:
    """The `part-list`, in order, from a compressed MusicXML file."""
    try:
        with zipfile.ZipFile(path) as z:
            inner = [n for n in z.namelist()
                     if n.endswith(".xml") and not n.startswith("META-INF")]
            if not inner:
                return None
            data = z.read(max(inner, key=lambda n: z.getinfo(n).file_size))
        root = ET.fromstring(data)
    except Exception:
        return None
    out = []
    for sp in root.iter("score-part"):
        nm, ab = sp.find("part-name"), sp.find("part-abbreviation")
        txt = (nm.text if nm is not None and nm.text
               else (ab.text if ab is not None and ab.text else ""))
        out.append(" ".join(txt.split()))
    return out


def usable(parts: list[str]) -> bool:
    """A work whose part names are mostly "Track 7" came from a scan whose
    names did not survive, and says nothing about the lexicon."""
    junk = sum(1 for p in parts if p.lower().startswith("track") or len(p) < 2)
    return junk <= len(parts) // 4


def monotone(parts: list[str], *, position_aware: bool) -> bool:
    seq, prev = [], -1
    for p in parts:
        m = lookup(p)
        if m is None or m.instrument.family not in FAMILY_RANK:
            continue
        pick = m.instrument
        if position_aware:
            alts = candidates_for_alias(m.alias)
            if alts:
                ok = [a for a in alts if FAMILY_RANK.get(a.family, -1) >= prev]
                if ok:
                    pick = ok[0]
        rank = FAMILY_RANK[pick.family]
        seq.append(rank)
        prev = max(prev, rank)
    return all(a <= b for a, b in zip(seq, seq[1:]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--library", default=DEFAULT_LIBRARY)
    ap.add_argument("--min-parts", type=int, default=8,
                    help="a work smaller than this is chamber music, not a score order")
    ap.add_argument("--misses", action="store_true",
                    help="list the part names the lexicon could not read")
    args = ap.parse_args()

    if not os.path.isdir(args.library):
        print(f"no MusicXML library at {args.library}", file=sys.stderr)
        return 1

    works = []
    for path in sorted(glob.glob(os.path.join(args.library, "*.mxl"))):
        parts = part_names(path)
        if parts and len(parts) >= args.min_parts and usable(parts):
            works.append((os.path.basename(path)[:-4], parts))
    if not works:
        print("no usable works found", file=sys.stderr)
        return 1

    resolved = total = 0
    misses: Counter[str] = Counter()
    for _w, parts in works:
        for p in parts:
            total += 1
            if lookup(p) is None:
                misses[p] += 1
            else:
                resolved += 1

    baroque = [w for w in works if w[0].startswith("bach")]
    symphonic = [w for w in works if not w[0].startswith("bach")]
    plain = sum(monotone(p, position_aware=False) for _w, p in symphonic)
    aware = sum(monotone(p, position_aware=True) for _w, p in symphonic)
    bar_mono = sum(monotone(p, position_aware=True) for _w, p in baroque)

    print(f"{len(works)} orchestral works, {total} part names\n")
    print(f"  resolved by the lexicon        {resolved}/{total} ({resolved/total:.0%})")
    print(f"  symphonic works in score order")
    print(f"    lexicon alone                {plain}/{len(symphonic)}")
    print(f"    ambiguity settled by position {aware}/{len(symphonic)}")
    print(f"  baroque works in score order   {bar_mono}/{len(baroque)}"
          f"   (expected to be low — continuo goes last)")
    if args.misses and misses:
        print("\nunread part names:")
        for name, n in misses.most_common(30):
            print(f"   {n:>3}x  {name!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
