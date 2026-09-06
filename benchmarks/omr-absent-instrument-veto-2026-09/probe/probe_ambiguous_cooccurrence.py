"""How often does an ambiguous alias share a page with a DIFFERENT alias that
names one of its own candidates?

This is the control for the per-system uniqueness constraint in
`contextual._resolve_ambiguous_labels`: the positional prior may not move a
staff onto an instrument another label on the same system already names.

⚠️ **PAGE, NOT SYSTEM, AND DELIBERATELY SO.** The 1422-label corpus records
`page_index` and `staff_index` but no system index, and a page is a SUPERSET of
a system — so every hit here is a hit-or-more for the real rule. That makes this
an upper bound on reach, which is the safe direction for a control: the rule
cannot fire anywhere this does not, and the hit list is small enough to
adjudicate by hand.

Read the output as three questions:

  1. REACH   — how many occurrences the rule could speak to at all.
  2. SAFETY  — of those, how many would have the LEXICON's answer refused. The
               constraint is asymmetric and never does this; the column exists
               so that a future change which makes it symmetric shows up here
               instead of in a benchmark six weeks later.
  3. CONTROL — which sources produce `basso`/`bassi` clashes. `c0a80ae7` fixed
               `Basso.` at the foot of an orchestral score by letting POSITION
               overturn the lexicon's `Bass voice` to Contrabass. If an
               orchestral source ever appears in that list, this constraint has
               started blocking that fix and the two are in conflict.

Measured 2026-09-06 on `benchmarks/omr-lexicon-2026-09/labels.json`:
158 ambiguous-alias occurrences, 86 clashing — 52 `cor`, 18 `tp`, 9 `tr bas`,
7 `basso`/`bassi` — over 6 sources. Adjudicated by hand, the rule keeps or
restores the right answer in 86 of 86 and blocks a correct overturn in 0. Every
`bass*` clash is Handel's `Messiah`, which prints `BASSO` (the bass VOICE) and
`Bassi` (the string basses) on ONE page and needs both first answers exactly as
they stand; no orchestral page in the corpus names Contrabass twice, so the
`c0a80ae7` overturn passes through untouched.

Usage:  python3 benchmarks/.../probe_ambiguous_cooccurrence.py [labels.json]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.instruments import candidates_for_alias, lookup  # noqa: E402

DEFAULT_LABELS = ROOT / "benchmarks" / "omr-lexicon-2026-09" / "labels.json"

# Sources whose pages are orchestral scores. The `basso` control is only
# meaningful against these: a clash on a VOCAL work is the ambiguity being real,
# which is the case the lexicon's two first answers already handle correctly.
VOCAL_SOURCES = {"handel-messiah-leadsheet"}


def main(path: Path) -> int:
    rows = json.loads(path.read_text())

    by_page = collections.defaultdict(list)
    for r in rows:
        by_page[(r["source"], r["reader"], r["page_index"])].append(r)

    n_ambiguous = 0
    hits = []
    for key, page_rows in sorted(by_page.items()):
        resolved = [(r, lookup(r["text"])) for r in page_rows]
        for r, m in resolved:
            if m is None:
                continue
            candidates = candidates_for_alias(m.alias)
            if len(candidates) < 2:
                continue
            n_ambiguous += 1
            others: dict[str, list] = {}
            for r2, m2 in resolved:
                if m2 is None or r2 is r or m2.alias == m.alias:
                    continue
                others.setdefault(m2.instrument.name, []).append(
                    (r2["staff_index"], r2["text"], m2.alias))
            clash = [c.name for c in candidates if c.name in others]
            if clash:
                hits.append(dict(
                    key=key, staff=r["staff_index"], text=r["text"],
                    alias=m.alias, lexicon=m.instrument.name,
                    candidates=[c.name for c in candidates],
                    clash={c: others[c] for c in clash}))

    print(f"labels                                  {len(rows)}")
    print(f"ambiguous-alias occurrences             {n_ambiguous}")
    print(f"  ... a candidate named by another alias  {len(hits)}   <- REACH")

    # SAFETY. The constraint refuses only an OVERTURN, so a hit whose LEXICON
    # answer is among the clashing names must still keep that answer.
    would_refuse_lexicon = [h for h in hits if h["lexicon"] in h["clash"]]
    print(f"  ... of those, the lexicon's OWN answer  {len(would_refuse_lexicon)}"
          f"    <- must never be refused")
    print()

    print("by alias:")
    for alias, n in collections.Counter(h["alias"] for h in hits).most_common():
        print(f"  {alias!r:12} {n}")
    print()

    print("CONTROL — sources with a `bass*` clash (an orchestral one would mean")
    print("this constraint has started blocking c0a80ae7's Contrabass overturn):")
    bass = {h["key"][0] for h in hits if h["alias"].startswith("bass")}
    for src in sorted(bass):
        kind = "vocal — expected" if src in VOCAL_SOURCES else "ORCHESTRAL — CONFLICT"
        print(f"  {src:36} {kind}")
    if not bass:
        print("  (none)")
    print()

    for h in hits:
        src, reader, pg = h["key"]
        print(f"{src} [{reader}] p{pg} staff {h['staff']}: "
              f"{h['text']!r} alias={h['alias']!r}")
        print(f"    lexicon says {h['lexicon']}   candidates {h['candidates']}")
        for name, occ in h["clash"].items():
            where = "; ".join(f"staff {s} {t!r} (alias {a!r})" for s, t, a in occ)
            mark = "  [the lexicon's own answer — never refused]" if name == h["lexicon"] else ""
            print(f"    CLASH {name} also named by: {where}{mark}")
        print()

    conflicts = bass - VOCAL_SOURCES
    if conflicts:
        print(f"FAIL: orchestral `bass*` clash in {sorted(conflicts)}")
        return 1
    return 0


if __name__ == "__main__":
    arg = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LABELS
    raise SystemExit(main(arg))
