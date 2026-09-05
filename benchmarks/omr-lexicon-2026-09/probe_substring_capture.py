#!/usr/bin/env python3
"""Which instruments does a SHORTER alias capture, and which merely abstain?

The lexicon's dangerous failure is not the instrument it does not hold. It is
the instrument it does not hold whose NAME CONTAINS a word-bounded alias of a
different instrument — `Basset horn` resolving to Horn [brass] on the bare
`horn` inside it, at medium confidence, when a basset horn is an alto clarinet
and a WOODWIND. An absent instrument that abstains costs a label; an absent
instrument that is captured costs a wrong staff, and a cross-family one at
that.

Two questions, reported apart because only the second has ever been a bug:

  internal   for every alias in the table, which OTHER instrument's alias fires
             word-bounded inside it — and does the owner hold an alias at least
             as long, so that `_ALIAS_INDEX`'s longest-first order rescues it?
             (Measured 2026-09-05: 131 containment pairs, 0 unrescued. The
             table cannot capture itself.)

  external   a list of real instrument names, run through `lookup`, split into
             CAPTURED (resolves to something else) and ABSTAINS (safe gap).
             This is where every fault in this batch lived.

    python3 benchmarks/omr-lexicon-2026-09/probe_substring_capture.py
    python3 .../probe_substring_capture.py --base origin/main   # before/after

⚠️ The external list is hand-collected repertoire plus the IMSLP
instrumentation residual, not a corpus — it can only show that a name IS
captured, never that no other name is. It is a screen for the next batch of
entries, not a coverage claim.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import types
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

#: Real instruments, with the family they actually belong to. Anything the
#: lexicon holds is skipped automatically, so entries may stay here after they
#: are added — that is what turns this into a regression screen.
REPERTOIRE: tuple[tuple[str, str], ...] = (
    ("Basset horn", "woodwind"), ("Bassetthorn", "woodwind"),
    ("Corno di bassetto", "woodwind"), ("Basset clarinet", "woodwind"),
    ("Contrabass clarinet", "woodwind"), ("Contrabass trombone", "brass"),
    ("Contrabass tuba", "brass"), ("Alto flute", "woodwind"),
    ("Bass flute", "woodwind"), ("Bass oboe", "woodwind"),
    ("Oboe d'amore", "woodwind"), ("Oboe da caccia", "woodwind"),
    ("Heckelphone", "woodwind"), ("Recorder", "woodwind"),
    ("Sopranino clarinet", "woodwind"), ("Alto saxophone", "woodwind"),
    ("Cornet", "brass"), ("2 cornets", "brass"), ("Kornett", "brass"),
    ("Flugelhorn", "brass"), ("Flügel Horn", "brass"), ("Flicorno", "brass"),
    ("Bass trumpet", "brass"), ("Alto trombone", "brass"),
    ("Wagner tuba", "brass"), ("Ophicleide", "brass"), ("Serpent", "brass"),
    ("Euphonium", "brass"), ("Cimbasso", "brass"), ("Bugle", "brass"),
    ("Alto horn", "brass"), ("Tenor horn", "brass"), ("Post horn", "brass"),
    ("Bells", "percussion"), ("Cowbells", "percussion"), ("Gong", "percussion"),
    ("Slapstick", "percussion"), ("Wind machine", "percussion"),
    ("Crotales", "percussion"), ("Marimba", "percussion"),
    ("Vibraphone", "percussion"), ("Tenor drum", "percussion"),
    ("Guiro", "percussion"), ("Ratchet", "percussion"),
    ("Mandolin", "keyboard"), ("Guitar", "keyboard"), ("Harmonium", "keyboard"),
    ("Viola d'amore", "string"), ("Viola da gamba", "string"),
    ("Altos", "string"), ("Bass viol", "string"),
    # plurals — a word-bounded alias cannot fire inside its own plural, so
    # these exercise the derived-plural layer
    ("English horns", "woodwind"), ("cors anglais", "woodwind"),
    ("bass clarinets", "woodwind"), ("oboes", "woodwind"),
    ("cellos", "string"), ("double basses", "string"), ("harps", "keyboard"),
)


def load(rev: str | None) -> types.ModuleType:
    """`tools/omr/instruments.py` at `rev`, or the working tree if None."""
    if rev is None:
        from tools.omr import instruments                       # noqa: PLC0415
        return instruments
    src = subprocess.run(["git", "show", f"{rev}:tools/omr/instruments.py"],
                         cwd=ROOT, capture_output=True, text=True,
                         check=True).stdout
    mod = types.ModuleType("instruments_base")
    mod.__dict__["__file__"] = "<base>"
    sys.modules["instruments_base"] = mod
    exec(compile(src, f"<{rev}:instruments.py>", "exec"), mod.__dict__)
    return mod


def internal_survey(mod) -> list[tuple]:
    """Alias containment WITHIN the table, and whether longest-first rescues."""
    aliases_of = getattr(mod, "aliases_of", lambda i: i.aliases)
    index = [(a, inst) for inst in mod.INSTRUMENTS for a in aliases_of(inst)]
    rows = []
    for inst in mod.INSTRUMENTS:
        for target in (inst.name.lower(),) + tuple(aliases_of(inst)):
            for alias, other in index:
                if other.name == inst.name:
                    continue
                if not re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", target):
                    continue
                rescued = any(
                    len(a) >= len(alias)
                    and re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", target)
                    for a in aliases_of(inst)
                )
                rows.append((target, inst.name, alias, other.name,
                             other.family != inst.family, rescued))
    return rows


def external_survey(mod) -> list[tuple]:
    out = []
    for label, true_family in REPERTOIRE:
        m = mod.lookup(label)
        if m is None:
            out.append((label, true_family, None, None, "abstains"))
            continue
        verdict = ("ok" if m.instrument.family == true_family
                   else "CAPTURED cross-family")
        out.append((label, true_family, m.instrument.name,
                    m.instrument.family, verdict))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=None,
                    help="also resolve at this git revision, for a before/after")
    args = ap.parse_args(argv)

    arms = [("HEAD (working tree)", None)]
    if args.base:
        arms.append((f"BASE {args.base}", args.base))
    for name, rev in arms:
        mod = load(rev)
        print(f"\n===== {name} =====")

        rows = internal_survey(mod)
        unrescued = [r for r in rows if not r[5]]
        print(f"internal: {len(rows)} containment pairs, "
              f"{len(unrescued)} NOT rescued by longest-first")
        for r in unrescued:
            print(f"    {r[0]!r} (owner {r[1]}) stolen by {r[3]} via {r[2]!r}"
                  + ("  CROSS-FAMILY" if r[4] else ""))

        ext = external_survey(mod)
        captured = [r for r in ext if r[4] == "CAPTURED cross-family"]
        abstains = [r for r in ext if r[4] == "abstains"]
        print(f"external: {len(ext)} names — {len(captured)} captured "
              f"cross-family, {len(abstains)} abstain (safe gap), "
              f"{len(ext) - len(captured) - len(abstains)} correct")
        for r in captured:
            print(f"    ⚠️  {r[0]:<24} is {r[1]:<11} -> read as "
                  f"{r[2]} [{r[3]}]")
        if abstains:
            print("    abstains: " + ", ".join(r[0] for r in abstains))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
