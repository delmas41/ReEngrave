"""IS THE C-CLEF FAULT SYSTEMIC? The other literal-set admission filters.

§12 sketches a derived check nobody has: *does a gatherer's own admission rule
drop members of the family it claims to gather?* `gather.py` holds five more
literal-set filters besides the clef one. This asks the same question of each.

⚠️⚠️ THE QUESTION ONLY MEANS SOMETHING WHERE A SET CLAIMS A WHOLE CATEGORY,
AND THIS PROBE'S FIRST RUN DID NOT KNOW THAT. `_ARC_CLASSES` is `{slur, tie}`
inside detector category `structural`, which also holds barlines, staff lines
and ledger lines -- so "the set drops 19 of its category" is true and
meaningless. Reported per set as a COVERAGE RATIO with the residue named, for
a human to read, rather than as a pass/fail.

⚠️ AND IT MUST APPLY THE ALIASES FIRST, which the first run also did not.
`canonicalize_names` renames every coarse spelling at the one place the
model's `names` are read, so `dynamicLetterF` NEVER reaches a gatherer -- and
a probe comparing raw vocabulary names against a gatherer's set reports six
phantom drops for `_DYNAMIC_LETTER_CLASSES` that cannot occur.

⚠️ REPORT ONLY. Those families belong to other lanes; nothing here is fixed.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.class_aliases import canonical, vocabulary    # noqa: E402
from tools.omr.yolo_detector import _class_name_to_category  # noqa: E402
from tools.omr.staged import gather as g                     # noqa: E402

SETS = [
    ("_CLEF_CLASSES_INCUMBENT (the fault this lane repaired)",
     g._CLEF_CLASSES_INCUMBENT),
    ("_TUPLET_CLASSES", getattr(g, "_TUPLET_CLASSES", None)),
    ("_ARC_CLASSES", getattr(g, "_ARC_CLASSES", None)),
    ("_DYNAMIC_LETTER_CLASSES", getattr(g, "_DYNAMIC_LETTER_CLASSES", None)),
    ("_KEYSIG_CLASSES", getattr(g, "_KEYSIG_CLASSES", None)),
    ("_METER_CLASSES", getattr(g, "_METER_CLASSES", None)),
]


def main() -> int:
    # ⚠️ ALIASED FIRST: this is the spelling a gatherer actually sees.
    arriving = sorted({canonical(n) for n in vocabulary()})
    cat_of = {n: _class_name_to_category(n) for n in arriving}
    by_cat: dict[str, list[str]] = {}
    for n in arriving:
        by_cat.setdefault(cat_of[n], []).append(n)

    print("For each literal-set filter: which detector categories its members "
          "span, how much of each it covers, and what it leaves.\n"
          "A set covering ONE WHOLE category is claiming that family; a set "
          "selecting inside a broad category is not.\n")
    flagged = []
    for label, s in SETS:
        if s is None:
            print(f"{label}: NOT A MODULE-LEVEL SET -- skipped and reported\n")
            continue
        cats = Counter(cat_of.get(n, "NOT IN VOCABULARY") for n in s)
        print(f"=== {label} ===")
        print(f"  set ({len(s)}): {sorted(s)}")
        for c, k in sorted(cats.items()):
            members = by_cat.get(c, [])
            residue = [n for n in members if n not in s]
            whole = "WHOLE CATEGORY CLAIMED" if not residue else \
                    f"{k}/{len(members)} of category '{c}'"
            print(f"    category '{c}': {whole}")
            if residue and len(members) and k / len(members) >= 0.5:
                # a set holding most of a category plausibly claims it
                print(f"      ⚠️ residue ({len(residue)}): {residue}")
                flagged.append((label, c, tuple(residue)))
            elif residue:
                print(f"      (selection inside a broad category — "
                      f"{len(residue)} others, not a claim)")
        print()

    print("FLAGGED — a set holding at least half of a detector category, with "
          "residue:")
    if not flagged:
        print("  none")
    for label, c, residue in flagged:
        print(f"  {label} / '{c}': {list(residue)}")

    # ⚠️ POSITIVE CONTROL: the repaired clef set is in the table on purpose.
    # If it were not flagged, the probe is not reading the sets.
    if not any(l.startswith("_CLEF_CLASSES_INCUMBENT") for l, _c, _r in flagged):
        print("\nPROBE DEAD: the known clef fault is not flagged, so the "
              "probe is not reading the sets.")
        return 2
    print("\npositive control: the known clef fault IS flagged above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
