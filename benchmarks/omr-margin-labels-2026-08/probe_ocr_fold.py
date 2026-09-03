#!/usr/bin/env python3
"""Probe candidate OCR-confusion folds for the instrument lexicon.

For each candidate fold set we measure, in one place:
  * COLLISIONS: does any clean input (an alias, or a real text-layer label)
    that resolves to instrument X today resolve to a DIFFERENT instrument once
    the fold is added? That is the precision failure the Tr.Alt bug warns of.
  * RECALL:     which garbled reads the lexicon rejects today now resolve, and
    to what.
The baseline is the shipped fold. A safe fold has zero collisions.
"""
from __future__ import annotations
import glob, json, sys
from pathlib import Path
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parents[2]))

from tools.omr import instruments as I

# Every clean string we trust to resolve correctly today: every alias, plus
# every clean text-layer truth string in the corpora.
def clean_inputs():
    out = {}
    for inst in I.INSTRUMENTS:
        for a in inst.aliases:
            out.setdefault(a, inst.name)
    # corpus truth strings (the text layer is clean)
    for f in glob.glob(str(_P(__file__).resolve().parent / "results*.json")):
        for entry in json.load(open(f)):
            truth = entry.get("truth") or {}
            for v in truth.values():
                if isinstance(v, dict):
                    t = v.get("text")
                    if isinstance(t, str) and t.strip():
                        out.setdefault(t.strip(), "?")
    return out

def reader_reads():
    """Every raw reader string in the corpora (garbled + clean)."""
    out = set()
    for f in glob.glob(str(_P(__file__).resolve().parent / "results*.json")):
        for entry in json.load(open(f)):
            for key in ("labels", "vision", "surya", "reader"):
                d = entry.get(key)
                if isinstance(d, dict):
                    for v in d.values():
                        if isinstance(v, str) and v.strip():
                            out.add(v.strip())
    return out

MOTIVATING = ["Yiolino II.", "Yiola", "Yioloncello", "Yni", "Fug.", "Oh.",
              "Tympani", "Xylophone", "Timp.", "Cor.", "Ob.", "Fag."]

def resolve_name(text):
    hit = I.lookup(text)
    return hit.instrument.name if hit else None

def measure(label, extra_fold):
    """Install an extended fold, report collisions vs baseline and new recalls."""
    base_fold = dict(I._OCR_FOLD)
    # baseline resolutions
    clean = clean_inputs()
    base_clean = {s: resolve_name(s) for s in clean}
    base_reads = {s: resolve_name(s) for s in reader_reads()}
    base_motiv = {s: resolve_name(s) for s in MOTIVATING}

    # install extended fold
    merged = dict(base_fold)
    merged.update({ord(k): ord(v) for k, v in extra_fold.items()})
    I._OCR_FOLD = merged
    try:
        new_clean = {s: resolve_name(s) for s in clean}
        new_reads = {s: resolve_name(s) for s in reader_reads()}
        new_motiv = {s: resolve_name(s) for s in MOTIVATING}
    finally:
        I._OCR_FOLD = base_fold

    collisions = [(s, base_clean[s], new_clean[s]) for s in clean
                  if base_clean[s] != new_clean[s]]
    read_changes = [(s, base_reads[s], new_reads[s]) for s in base_reads
                    if base_reads[s] != new_reads[s]]
    motiv_changes = [(s, base_motiv[s], new_motiv[s]) for s in MOTIVATING
                     if base_motiv[s] != new_motiv[s]]

    print(f"\n=== {label}  fold += {extra_fold} ===")
    print(f"  COLLISIONS on clean inputs (aliases+truth): {len(collisions)}")
    for s, b, n in collisions:
        print(f"     !! {s!r:24} {b} -> {n}")
    print(f"  reader-string resolution changes: {len(read_changes)}")
    for s, b, n in read_changes:
        print(f"      ~ {s!r:24} {b} -> {n}")
    print(f"  motivating-case changes: {len(motiv_changes)}")
    for s, b, n in motiv_changes:
        print(f"      + {s!r:24} {b} -> {n}")
    return len(collisions)


if __name__ == "__main__":
    # Candidate fold sets. Fold maps a confusable char to a canonical rep.
    # Direction chosen so the *rare* char folds onto the common one.
    measure("V/Y only", {"y": "v"})
    measure("V/Y + rn-ish (n/m NOT foldable as 1:1, skip)", {"y": "v"})
    # The dangerous common-letter folds, shown to prove why they are rejected:
    measure("a/u (REJECT expected)", {"u": "a"})
    measure("b/h (REJECT expected)", {"h": "b"})
    measure("e/c (REJECT expected)", {"c": "e"})
    # combined safe candidate
    measure("V/Y + a couple rare swaps", {"y": "v"})
