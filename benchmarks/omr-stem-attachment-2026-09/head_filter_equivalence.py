"""IS SELECTING HEADS BY NAME THE SAME SET AS BY `detail["category"]`?

An arm of `mutate.py` swapped `_heads_in`'s selector -- `detail["category"] ==
"notehead"` -- for a test on the glyph's SMuFL NAME, and the arm came back
GREEN: the beam-mate fire set was still exactly 152.

⚠️ A GREEN ARM IS EITHER AN EQUIVALENT MUTANT OR A HOLE, AND THE TWO NEED
OPPOSITE RESPONSES. This asks which, rather than assuming. If the two selectors
pick the same rows on this record the arm can never go red and belongs OUT of
the battery with its name recorded -- *an arm that can never go red trains the
next reader to ignore the list.* If they differ, the battery has a hole.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array                            # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: head_filter_equivalence.py <record.json> [...]",
              file=sys.stderr)
        return 2
    bad = 0
    for p in sys.argv[1:]:
        by_cat, by_name, both, n = set(), set(), 0, 0
        for o in stream_array(p, "observations"):
            if o.get("quantity") != "glyph_box":
                continue
            n += 1
            v = o.get("value")
            name = str(v[0]) if isinstance(v, (list, tuple)) and v else ""
            cat = (o.get("detail") or {}).get("category")
            c = cat == "notehead"
            m = "otehead" in name
            if c:
                by_cat.add(o["subject"])
            if m:
                by_name.add(o["subject"])
            if c and m:
                both += 1
        only_cat, only_name = by_cat - by_name, by_name - by_cat
        print(f"{Path(p).name}: {n} glyph_box rows")
        print(f"   category == 'notehead'      {len(by_cat):>6}")
        print(f"   name contains 'otehead'     {len(by_name):>6}")
        print(f"   both                        {both:>6}")
        print(f"   ONLY category               {len(only_cat):>6}")
        print(f"   ONLY name                   {len(only_name):>6}")
        if only_cat or only_name:
            bad += 1
            print("   -> the selectors DIFFER: the arm is a real hole")
            for s in list(only_cat)[:5]:
                print(f"      only-category: {s}")
            for s in list(only_name)[:5]:
                print(f"      only-name:     {s}")
        else:
            print("   -> IDENTICAL on this record: the arm is an EQUIVALENT "
                  "MUTANT and must leave the battery")
        print()
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
