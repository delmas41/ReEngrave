#!/usr/bin/env python3
"""Resolve a margin-label dump with TWO lexicons and report every change.

The lexicon's own no-regression rule (LEXICON_TR_ALT_2026-08-31.md) is that a
change must be scored on the strings the READERS emit, not on MusicXML part
names — engraving software writes "Contrabassoon" and a printed margin says
"C. Fag.". So this replays `read_margin_labels.py`'s dump through the working
tree's `instruments` and through any git revision's, in one process, and prints
the diff.

    python3 benchmarks/omr-lexicon-2026-09/resolve_labels.py labels.json --base origin/main

`--base` is exec'd standalone out of `git show`, so nothing in the tree has to
move to measure against it.
"""
from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
import types
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))


def load_base(rev: str) -> types.ModuleType:
    """`tools/omr/instruments.py` at `rev`, as a standalone module."""
    src = subprocess.run(["git", "show", f"{rev}:tools/omr/instruments.py"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    mod = types.ModuleType("instruments_base")
    mod.__dict__["__file__"] = "<base>"
    # `@dataclass` resolves annotations through `sys.modules[cls.__module__]`,
    # so an exec'd module that is not registered raises rather than defining
    # `Instrument`. Registered under its own name, never shadowing the real one.
    sys.modules["instruments_base"] = mod
    exec(compile(src, f"<{rev}:instruments.py>", "exec"), mod.__dict__)
    return mod


def resolve(mod, text: str):
    m = mod.lookup(text)
    return None if m is None else (m.instrument.name, m.alias, m.confidence)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("labels", type=Path)
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--detail", action="store_true", help="list every changed string")
    ap.add_argument("--fold-reader-markup", action="store_true",
                    help="apply the HEAD reader's `staff_labels_surya._plain_text` "
                         "to the raw string on the HEAD side only. A dump is "
                         "captured with whatever reader made it, so this is how "
                         "a change at the READER boundary gets priced against "
                         "the same strings — the arms then read "
                         "(base lexicon, raw) vs (head lexicon, folded), which "
                         "is what production does before and after.")
    args = ap.parse_args(argv)

    from tools.omr import instruments as head                       # noqa: PLC0415
    base = load_base(args.base)

    raw = json.loads(args.labels.read_text())
    # Accepts either a `read_margin_labels.py` dump (records with a `text` and a
    # `source`) or a plain list of strings, so the reader corpus and the
    # reference part-name corpus go through one scorer.
    records = ([{"source": args.labels.stem, "text": t} for t in raw]
               if raw and isinstance(raw[0], str) else raw)
    by_source: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"labels": 0, "changed": 0})
    changes: collections.Counter = collections.Counter()
    resolved = {"base": 0, "head": 0}

    fold = (lambda t: t)
    if args.fold_reader_markup:
        from tools.omr.staff_labels_surya import _plain_text                # noqa: PLC0415
        fold = _plain_text

    for rec in records:
        text = rec["text"]
        b, h = resolve(base, text), resolve(head, fold(text))
        row = by_source[rec["source"]]
        row["labels"] += 1
        resolved["base"] += b is not None
        resolved["head"] += h is not None
        if b != h:
            row["changed"] += 1
            changes[(text, b, h)] += 1

    print(f"{'source':32} {'labels':>7} {'changed':>8}")
    total = changed = 0
    for source, row in sorted(by_source.items()):
        print(f"{source:32} {row['labels']:7d} {row['changed']:8d}")
        total += row["labels"]
        changed += row["changed"]
    print(f"{'TOTAL':32} {total:7d} {changed:8d}")
    print(f"\nresolved to some instrument: base {resolved['base']}  "
          f"head {resolved['head']}  (of {total})")

    if changes:
        print(f"\n{len(changes)} distinct changed strings:")
        for (text, b, h), n in changes.most_common():
            bn = b[0] if b else "—"
            hn = h[0] if h else "—"
            print(f"  {n:4d}x  {text!r:36} {bn:>15} -> {hn:<15}"
                  f"  [{(b or ('','',''))[1]!r} -> {(h or ('','',''))[1]!r}]")
    else:
        print("\nno label changes")

    if args.detail:
        print("\nunresolved strings under HEAD:")
        for text, n in collections.Counter(
                r["text"] for r in records
                if resolve(head, fold(r["text"])) is None).most_common():
            print(f"  {n:4d}x  {text!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
