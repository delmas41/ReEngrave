#!/usr/bin/env python3
"""Prototype + measure a gated confusable single-substitution matcher.

Gate: after normalization, a WHOLE token equals an alias after exactly one
confusable substitution, alias length >= MIN_LEN. This is stricter than the
global substring fold. Measure recall (garbled reads recovered) and precision
(any clean input changing resolution = failure), and a perturbation stress
test for the second failure mode (a non-alias word one slip from an alias).
"""
from __future__ import annotations
import glob, json, sys, itertools
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parents[2]))
from tools.omr import instruments as I

PAIRS = [("v", "y"), ("u", "a"), ("b", "h")]  # the pairs that touch real cases
SUBS = {}
for x, y in PAIRS:
    SUBS.setdefault(x, set()).add(y)
    SUBS.setdefault(y, set()).add(x)

# longest-first alias index of single-token aliases (space-collapsed)
ALIAS_BY_KEY = {}
for inst in I.INSTRUMENTS:
    for a in inst.aliases:
        ALIAS_BY_KEY.setdefault(a.replace(" ", ""), inst)

def neighbours(word):
    for i, ch in enumerate(word):
        for repl in SUBS.get(ch, ()):
            yield word[:i] + repl + word[i+1:]

def gated_lookup(text, min_len):
    """Only fires if exact instruments.lookup fails; whole-token single-sub."""
    if I.lookup(text) is not None:
        return None  # exact/fold path already handles it; don't interfere
    norm = I.normalize_label(text)
    stripped = __import__("re").sub(r"\s+", " ",
                    I._STRIP_TOKENS.sub(" ", norm)).strip()
    for cand in (norm, stripped, norm.replace(" ", ""), stripped.replace(" ", "")):
        key = cand.replace(" ", "")
        if len(key) < min_len:
            continue
        for nb in neighbours(key):
            inst = ALIAS_BY_KEY.get(nb)
            if inst is not None and len(nb) >= min_len:
                return inst.name
    return None

def clean_inputs():
    out = {}
    for inst in I.INSTRUMENTS:
        for a in inst.aliases:
            out[a] = inst.name
    for f in glob.glob(str(_P(__file__).resolve().parent / "results*.json")):
        for entry in json.load(open(f)):
            for v in (entry.get("truth") or {}).values():
                if isinstance(v, dict) and isinstance(v.get("text"), str) and v["text"].strip():
                    out.setdefault(v["text"].strip(), "?")
    return out

def reader_reads():
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

MOTIV = ["Yiolino II.", "Yiola", "Fug.", "Oh."]

for MIN_LEN in (2, 3, 4):
    print(f"\n========== MIN_LEN = {MIN_LEN}, pairs={PAIRS} ==========")
    # precision: clean inputs that gated matcher would (wrongly) fire on
    # (a clean input already resolves via exact lookup, so gated returns None;
    #  a clean input that does NOT resolve and now fires is what we inspect)
    fires_clean = []
    for s, expect in clean_inputs().items():
        g = gated_lookup(s, MIN_LEN)
        if g is not None:  # gated fired on a clean input that exact-lookup missed
            fires_clean.append((s, expect, g))
    print(f"  gated fires on clean inputs exact-lookup missed: {len(fires_clean)}")
    for s, e, g in fires_clean:
        print(f"     clean {s!r} (truth-resolves {e}) -> gated {g}")
    # recall on garbled corpus reads
    recov = [(s, gated_lookup(s, MIN_LEN)) for s in sorted(reader_reads())]
    recov = [(s, g) for s, g in recov if g]
    print(f"  garbled corpus reads recovered: {len(recov)}")
    for s, g in recov:
        print(f"     {s!r} -> {g}")
    print("  motivating cases:")
    for s in MOTIV:
        print(f"     {s!r} -> {gated_lookup(s, MIN_LEN)}")

# Perturbation stress test: take every alias, apply ONE confusable sub to make a
# fake garbled read, and check it still maps back to its OWN instrument (not a
# different one). This probes the second failure mode directly.
print("\n\n========== perturbation stress (min_len=3) ==========")
wrong = []
for key, inst in ALIAS_BY_KEY.items():
    if len(key) < 3:
        continue
    for nb in neighbours(key):
        g = gated_lookup(nb, 3)
        if g is not None and g != inst.name:
            wrong.append((key, inst.name, nb, g))
print(f"  perturbed aliases resolving to a DIFFERENT instrument: {len(wrong)}")
for k, o, nb, g in wrong[:30]:
    print(f"     {k!r}({o}) --slip--> {nb!r} -> {g}")
