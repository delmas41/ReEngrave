"""Every NUMBER the registry states about itself, checked against its entries.

`--check` covers the numbers a machine can join to an entry — the Counts
tables, the Contents list, the Conservation ledger, the FAILED table. This
probe covers the rest: the figures the document states in PROSE, which no
parser was ever going to reach and which are therefore the most likely
place for a stale number to survive.

⚠️ REACH FIRST: it prints how many claims it could locate at all, and
exits **2** if it located none — a probe that matches no prose reports a
document with no wrong numbers in it.

    python3 benchmarks/omr-convention-registry-2026-09/probe/prose_claims.py
    python3 .../prose_claims.py --check   # non-zero if a claim does not reproduce
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr import conventions as C  # noqa: E402


def claims(reg: C.Registry, text: str):
    """(claim, what the document says, what the entries give, note)."""
    src = [t for e in reg for t in e.sources]
    merged = [e for e in reg
              if any(t[0] == "C" for t in e.sources)
              and any(t[0] == "L" for t in e.sources)]
    repo_only = [e for e in reg if all(t[0] == "C" for t in e.sources)]
    lit_only = [e for e in reg if all(t[0] == "L" for t in e.sources)]
    absorbed = sum(sum(1 for t in e.sources if t[0] == "L") for e in merged)
    multi = [e for e in merged
             if sum(1 for t in e.sources if t[0] == "L") > 1]
    excess = sum(sum(1 for t in e.sources if t[0] == "L") - 1 for e in multi)
    pd_rows = [e for e in reg if e.is_publisher_dependent]

    out = []

    def find(pattern, label, got, note=""):
        """A claim whose number is CAPTURED from the document."""
        m = re.search(pattern, text)
        out.append((label, int(m.group(1)) if m else None, got, note))

    WORDS = {"three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10, "eleven": 11}

    def find_word(pattern, label, got, note=""):
        """A claim the document spells as a WORD ('Five entries are ...').

        ⚠️ These are the ones a naive digit scan cannot see at all, which
        is why they are read here rather than assumed absent.
        """
        m = re.search(pattern, text, re.I)
        said = WORDS.get(m.group(1).lower()) if m else None
        out.append((label, said, got, note))

    find(r"\*\*(\d+) registry entries\*\*", "registry entries", len(reg))
    find(r"from (\d+) source entries", "source entries", len(set(src)))
    find(r"\|\s*\[`docs/conventions/from-this-repo\.md`\][^|]*\|[^|]*\|\s*"
         r"\*\*(\d+)\*\*", "repo-side source entries",
         len([t for t in src if t[0] == "C"]))
    find(r"\|\s*\[`docs/conventions/from-the-literature\.md`\][^|]*\|[^|]*\|\s*"
         r"\*\*(\d+)\*\*", "literature source entries",
         len([t for t in src if t[0] == "L"]))
    find(r"(\d+)\s+repo entries that ABSORBED", "repo entries that absorbed",
         len(merged))
    find(r"\+\s*(\d+)\s+literature entries absorbed", "literature absorbed",
         absorbed)
    find(r"\+\s*(\d+)\s+repo entries kept standalone", "repo standalone",
         len(repo_only))
    find(r"\+\s*(\d+)\s+literature entries kept standalone",
         "literature standalone", len(lit_only))
    find_word(r"\*\*(\w+) entries are REFUTED outright", "refuted outright",
              len(reg.refuted()), "the document spells this one as a word")
    find_word(r"\*\*And (\w+) surviving entries carry a refutation INSIDE",
              "entries with an internal refutation",
              len([e for e in reg
                   if e.refutation is C.Refutation.INTERNAL_CAVEAT]),
              "the document spells this one as a word")

    # ── the two that do NOT reproduce ─────────────────────────────────────
    find_word(r"\*\*The (\w+) repo entries that absorbed more than one",
              "entries absorbing >1 literature entry", len(multi),
              f"the document NAMES {len(multi)} of them; the number it "
              f"states is the count of EXCESS absorptions ({excess}), "
              f"which is a different quantity and is CORRECT as arithmetic")

    find(r"leading word:\*\*\s+\*\*(\d+)\*\*\s+of\s+the\s+87\s+repo-side",
         "repo-side entries leading 'publisher-dependent'",
         len([e for e in pd_rows if any(t[0] == "C" for t in e.sources)]),
         "the doc marks this 'the repo file's own count' — inherited from "
         "the SOURCE file and not recomputed after the merge")
    find(r"repo-side entries[^)]*\)\s+and\s+\*\*(\d+)\*\*\s+of\s+the\s+27\s+literature-only",
         "literature-only entries leading 'publisher-dependent'",
         len([e for e in pd_rows if all(t[0] == "L" for t in e.sources)]),
         "the six it names (L6 L7 L8 L14 L15 L71) all lead 'Variable', "
         "which is a different vocabulary word")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    reg = C.load()
    text = reg.path.read_text(encoding="utf-8")
    rows = claims(reg, text)

    located = [r for r in rows if r[1] is not None]
    print(f"REACH: {len(located)} of {len(rows)} prose claims located "
          f"in the document")
    if not located:
        print("DEAD: no prose claim was located; this probe says nothing.",
              file=sys.stderr)
        return 2

    print()
    print(f"  {'claim':<50} {'doc':>5} {'entries':>8}")
    bad = []
    for label, said, got, note in rows:
        if said is None:
            print(f"  {label:<50} {'?':>5} {got:>8}   <- NOT LOCATED")
            continue
        ok = said == got
        if not ok:
            bad.append((label, said, got, note))
        print(f"  {label:<50} {said:>5} {got:>8}   {'ok' if ok else 'DIFFERS'}")
        if note:
            print(f"      note: {note}")

    print()
    if bad:
        print(f"{len(bad)} claim(s) do not reproduce:")
        for label, said, got, note in bad:
            print(f"  - {label}: document says {said}, entries give {got}")
            if note:
                print(f"    {note}")
    else:
        print("every located prose claim reproduces from the entries.")

    if args.check:
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
