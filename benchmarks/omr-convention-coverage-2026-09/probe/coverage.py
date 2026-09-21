"""Which registry conventions reach a DECISION, and which reach none.

⚠️⚠️ THE JOIN IS A READING, NOT A MEASUREMENT, AND THIS TOOL CANNOT MAKE IT
ONE. `out/join.json` is a hand pairing of the 32 `checked_by` statements to
the 114 registry conventions, made by reading both, with a confidence I
assigned per pairing. This script only does the arithmetic OVER that reading
-- it parses the registry for the authoritative entry list so the DENOMINATOR
is derived, and subtracts what the join claims. A different reader would pair
some of these differently and the uncovered list would move.

⚠️ The two halves are therefore reported apart, always: the ENTRY LIST is
derived from `docs/engraving-conventions.md` and can be checked by anyone;
the CLAIMS are mine.

Positive controls (`--check`): the derived entry list must be non-empty and
must match the registry's OWN published per-category table, and the join must
claim at least one entry -- a join claiming nothing would report every
convention uncovered, which reads like a finding and is a broken parse.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

_ROOT = Path(__file__).resolve().parents[3]
_REGISTRY = _ROOT / "docs" / "engraving-conventions.md"
_JOIN = Path(__file__).resolve().parents[1] / "out" / "join.json"

#: The category `##` headings that hold entries. Everything else in the file
#: (Counts, Contents, the disagreement essays, Conservation, How to use) is
#: prose ABOUT the registry and holds no conventions.
CATEGORIES = (
    "Staff & pitch geometry", "Stems & beams", "Rests & bar filling",
    "Accidentals & key signatures", "Time signatures & meter",
    "Slurs, ties & phrasing", "Dynamics & hairpins",
    "Articulations & ornaments", "Score layout & systems",
    "Text & margin labels", "Barlines & repeats",
)

#: The registry's own published per-category counts (its "Counts" table). Used
#: ONLY as a control on the parse -- if the parse disagrees with the document's
#: own arithmetic, the parse is what is wrong.
PUBLISHED = {
    "Staff & pitch geometry": 14, "Stems & beams": 18,
    "Rests & bar filling": 8, "Accidentals & key signatures": 8,
    "Time signatures & meter": 8, "Slurs, ties & phrasing": 12,
    "Dynamics & hairpins": 7, "Articulations & ornaments": 9,
    "Score layout & systems": 18, "Text & margin labels": 8,
    "Barlines & repeats": 4,
}


def entries() -> List[Tuple[str, str, str, str]]:
    """`(id, category, title, status)` per registry entry, DERIVED."""
    lines = _REGISTRY.read_text().split("\n")
    out: List[Tuple[str, str, str, str]] = []
    cat = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and not line.startswith("###"):
            name = line[3:].strip()
            cat = name if name in CATEGORIES else None
            continue
        if not (line.startswith("### ") and cat):
            continue
        ident, status = "", ""
        for j in range(i + 1, min(i + 4, len(lines))):
            if lines[j].strip():
                m = re.match(r"^`\[(.+?)\]`", lines[j].strip())
                ident = m.group(1).replace(" ", "") if m else ""
                break
        for j in range(i + 1, min(i + 40, len(lines))):
            if lines[j].startswith("- **Status:**"):
                status = lines[j][len("- **Status:**"):].strip()
                break
            if lines[j].startswith("### "):
                break
        out.append((ident, cat, line[4:].strip(), status))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = entries()
    by_cat: Dict[str, int] = {}
    for _i, c, _t, _s in rows:
        by_cat[c] = by_cat.get(c, 0) + 1

    join = json.loads(_JOIN.read_text())
    claimed: Dict[str, List[str]] = {}
    for st in join["statements"]:
        for ident in st["registry"]:
            claimed.setdefault(ident, []).append(st["id"])

    known = {i for i, _c, _t, _s in rows}
    unknown_ids = sorted(set(claimed) - known)
    uncovered = [(i, c, t, s) for i, c, t, s in rows if i not in claimed]
    no_entry = [st for st in join["statements"] if not st["registry"]]

    if args.json:
        print(json.dumps({
            "n_entries": len(rows),
            "per_category": by_cat,
            "claimed": {k: v for k, v in sorted(claimed.items())},
            "uncovered": [{"id": i, "category": c, "title": t, "status": s}
                          for i, c, t, s in uncovered],
            "statements_matching_no_entry": [st["id"] for st in no_entry],
            "claimed_ids_not_in_registry": unknown_ids,
        }, indent=2))
    else:
        print(f"registry entries (DERIVED): {len(rows)}")
        for c in CATEGORIES:
            mark = "" if by_cat.get(c) == PUBLISHED[c] else "  ⚠️ DISAGREES WITH THE DOC'S OWN TABLE"
            print(f"    {by_cat.get(c, 0):3d}  {c}{mark}")
        print(f"\nconventions CLAIMED by at least one decision: {len(claimed)}"
              f"   (of {len(rows)})")
        for k, v in sorted(claimed.items()):
            print(f"    [{k}]  <- {', '.join(v)}")
        print(f"\n⚠️ conventions reaching NO decision: {len(uncovered)}")
        for i, c, t, s in uncovered:
            print(f"    [{i:22s}] {c:28s} {t}")
        print(f"\n⚠️ checked_by statements matching NO registry entry: "
              f"{len(no_entry)}")
        for st in no_entry:
            print(f"    {st['id']} ({st['decision']}): {st['text'][:70]}")
        if unknown_ids:
            print(f"\nREFUSED-WORTHY: join names ids the registry does not "
                  f"hold: {unknown_ids}")

    if args.check:
        # ⚠️ THE DATA FILES MUST COVER EXACTLY THE DERIVED STATEMENTS, and the
        # roster is taken from the REGISTRY rather than from either file --
        # otherwise a statement added to a decision tomorrow would silently
        # be absent from both the join and the verdicts, and this tool would
        # go on reporting a tidy 32.
        import tools.omr.staged.adjudicators  # noqa: F401
        from tools.omr.staged import adjudicate
        derived = sum(len(d.checked_by) for d in adjudicate.REGISTRY.values())
        ids_join = {st["id"] for st in join["statements"]}
        vpath = _JOIN.parent / "verdicts.json"
        ids_verd = {v["id"] for v in
                    json.loads(vpath.read_text())["verdicts"]}
        if not (derived == len(ids_join) == len(ids_verd)):
            print(f"REFUSED: the tree declares {derived} checked_by "
                  f"statements; join.json holds {len(ids_join)} and "
                  f"verdicts.json {len(ids_verd)}. The reading has drifted "
                  f"from the code it is about.", file=sys.stderr)
            return 2
        if ids_join != ids_verd:
            print(f"REFUSED: join.json and verdicts.json disagree about "
                  f"which statements exist: {ids_join ^ ids_verd}",
                  file=sys.stderr)
            return 2
        if not rows:
            print("REFUSED: the registry parse found NO entries.",
                  file=sys.stderr)
            return 2
        if by_cat != PUBLISHED:
            print(f"REFUSED: the parse disagrees with the registry's own "
                  f"Counts table. parsed={by_cat} published={PUBLISHED}",
                  file=sys.stderr)
            return 2
        if not claimed:
            print("REFUSED: the join claims NO convention -- every entry "
                  "would read as uncovered, which is a broken parse wearing "
                  "the shape of a finding.", file=sys.stderr)
            return 2
        if unknown_ids:
            print(f"REFUSED: the join names ids absent from the registry: "
                  f"{unknown_ids}", file=sys.stderr)
            return 2
        print(f"\npositive controls: OK (parse matches the registry's own "
              f"per-category table; the join claims {len(claimed)} entries; "
              f"every claimed id exists)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
