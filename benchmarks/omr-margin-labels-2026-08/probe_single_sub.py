#!/usr/bin/env python3
"""Intrinsic collision test for a confusion-aware SINGLE-SUBSTITUTION matcher.

The question the task poses: could a fuzzy match gated to one confusable
substitution safely take garbled reads like `Fug.`->fag, `Oh.`->ob?

We answer it from the vocabulary itself, independent of the tiny corpus: for
each alias A (of instrument X), enumerate every string one confusable
substitution away. If any such neighbour is itself an alias of a DIFFERENT
instrument Y, then a CLEAN printed label for Y is a single OCR slip from being
read as X -- a false resolution waiting to happen. Count those, by min length.
"""
from __future__ import annotations
import sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parents[2]))
from tools.omr import instruments as I

# Symmetric confusable pairs seen on printed score margins.
PAIRS = [("v", "y"), ("u", "a"), ("b", "h"), ("o", "0"), ("i", "l"),
         ("i", "1"), ("c", "e"), ("n", "m"), ("f", "t"), ("g", "q"),
         ("m", "rn")]  # rn/m is multi-char; handled separately below

# alias -> set of instrument names owning it (an alias can be shared? no, but
# be safe)
owner = {}
for inst in I.INSTRUMENTS:
    for a in inst.aliases:
        owner.setdefault(a.replace(" ", ""), set()).add(inst.name)
alias_set = set(owner)

def single_sub_neighbours(word, pairs):
    """Every string one single-char confusable substitution away from word."""
    subs = {}
    for x, y in pairs:
        if len(x) == 1 and len(y) == 1:
            subs.setdefault(x, set()).add(y)
            subs.setdefault(y, set()).add(x)
    out = set()
    for i, ch in enumerate(word):
        for repl in subs.get(ch, ()):
            out.add(word[:i] + repl + word[i+1:])
    return out

def report(min_len, pairs, label):
    collisions = []
    for a in sorted(alias_set):
        if len(a) < min_len:
            continue
        for nb in single_sub_neighbours(a, pairs):
            if nb in alias_set and owner[nb] != owner[a]:
                collisions.append((a, sorted(owner[a]), nb, sorted(owner[nb])))
    print(f"\n=== {label}: single-sub collisions among aliases, min_len={min_len} ===")
    print(f"    {len(collisions)} collisions")
    seen = set()
    for a, oa, nb, onb in collisions:
        k = tuple(sorted([a, nb]))
        if k in seen:
            continue
        seen.add(k)
        print(f"      {a!r}({','.join(oa)})  <-1->  {nb!r}({','.join(onb)})")

if __name__ == "__main__":
    for ml in (2, 3, 4, 5):
        report(ml, PAIRS, "all confusables")
    print("\n\n########## V/Y ALONE ##########")
    for ml in (2, 3, 4, 5):
        report(ml, [("v", "y")], "V/Y only")
    print("\n\n########## the benchmark's own pairs a/u, b/h ##########")
    for ml in (2, 3):
        report(ml, [("u", "a"), ("b", "h")], "a/u + b/h")
