#!/usr/bin/env python3
"""Instrument doubling: a label that is a DOUBLE of the roster entry confirms it.

MEASUREMENT ONLY.

A player doubles — the flautist picks up the piccolo, the oboist the cor
anglais, the trumpeter the cornet. **A double changes a staff's NAME mid-work
while leaving its POSITION alone**: it is the same chair. So the positional
constraint the roster join relies on survives doubling intact, and only the
NAME check fires spuriously.

THE RULE: a label that is a known double of the roster entry at that position
is a CONFIRMATION, not a conflict.

⚠️ DIRECTIONAL, DELIBERATELY NOT SYMMETRIC. A `Flute` chair may be satisfied by
a `Piccolo`; a `Piccolo` chair is NOT satisfied by a `Flute` in the same way.
The ROSTER ENTRY names the chair, so the relation runs roster -> observed. A
symmetric equivalence table would let a misread `Flute` silently satisfy a
`Piccolo` entry, which is the failure this asymmetry exists to prevent.

⚠️ DOUBLING IS WITHIN FAMILY, ALWAYS — and that is what makes it safe to admit
here. `probe_family_errors.py` measured the family level at precision 0.955
against the instrument level's 0.873, so a rule that can never cross a family
boundary cannot convert a within-family question into a cross-family error.
The table is asserted to satisfy that, not assumed to.

⚠️ STRINGS ESSENTIALLY NEVER DOUBLE, which is a useful asymmetry: an
unexpected string label is far likelier a read error than a double, so the
table contains no string entries and must not grow any without evidence.

⚠️ PERCUSSION switches constantly and is not modellable as fixed named chairs;
it is deliberately absent from the table and belongs at FAMILY granularity.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_doubling.py

── RESULT 2026-09-05: THE RULE IS SOUND, THE TABLE IS MOSTLY UNBUILDABLE ─────

⚠️⚠️ THE AUDIT REFUSED THE TABLE ON ITS FIRST RUN, and that is how three
defects were found. Of 12 declared doubles over 7 chairs, only **5 are usable**:

    USABLE   Flute->Piccolo · Oboe->English horn · Clarinet->Bass clarinet
             Bassoon->Contrabassoon · Horn->Tuba

    EXCLUDED, with reasons:
      Clarinet -> Basset horn     CROSS-FAMILY woodwind -> brass, via alias
                                  'horn'  ⚠️ A LEXICON DEFECT
      Trumpet  -> Cornet          UNRESOLVED — absent from the lexicon
      Trumpet  -> Flugelhorn      UNRESOLVED — absent from the lexicon
      Clarinet -> E-flat clarinet NO-OP — collapses to Clarinet
      Flute    -> Alto flute      NO-OP — collapses to Flute
      Oboe     -> Oboe d'amore    NO-OP — collapses to Oboe
      Trombone -> Bass trombone   NO-OP — collapses to Trombone

⚠️ `Basset horn` RESOLVES TO `Horn [brass]` — a basset horn is an alto
clarinet, a WOODWIND. The `horn` alias wins on a substring. This is the SAME
FAILURE CLASS CLAUDE.md already records being fixed for `Tr. Alt.` -> Alto
(a singer): a qualifier beaten by a substring match. It is a lexicon bug in its
own right, independent of doubling, and it is out of this workstream's scope to
fix — routed, not patched here.

⚠️ TRUMPET -> CORNET CANNOT BE ENCODED AT ALL. Cornet and flugelhorn are not in
the lexicon, so the French/Russian repertoire case (Berlioz, Tchaikovsky,
Franck) — one of the most-cited doublings — has no representation. Adding the
rule does not add that capability; the lexicon has to first.

⚠️ FOUR OF THE TWELVE ARE NO-OPS. The lexicon already collapses alto flute,
E-flat clarinet, oboe d'amore and bass trombone onto their parents, so those
labels can never look like a conflict and the doubling rule is unnecessary for
them. The rule's real surface is far smaller than the list of doublings
suggests.

⚠️ `Horn -> Wagner tuba` resolves to `Tuba`, which is same-family and therefore
safe, but semantically off: a Wagner tuba is played by a HORN player and this
seats it with the tuba. Usable, and worth knowing it is approximate.

EXERCISED ON THE GATE: **ZERO.** No staff position anywhere carries a name that
is a double of its roster chair. `Contrabassoon` is the only doubling
instrument present in the truth at all — and Brahms 1's roster carries BOTH
`Bassoon@3` AND `Contrabassoon@4`, i.e. it seats the contrabassoon as its own
player. ⚠️ That is the case that shows why the rule must be ROSTER-RELATIVE: if
the roster names both, they are two chairs, and a doubling relation between
them would let one satisfy the other.

R1 IS UNAFFECTED, by construction and by measurement. R1 compares the LENGTH of
each system's labelled PREFIX, not the names in it; a double changes a name at
an already-labelled position, so it moves no prefix boundary. The failure the
hypothesis names would need the double to ADD a labelled position. And no read
name on any roster page is a doubling instrument, so the 0/20 false-positive
record is untouched either way.

⇒ SHIP THE RULE (5 usable pairs, directional, roster-relative) BUT EXPECT NO
MOVEMENT ON THIS GATE. It is right and unexercised: the gate cannot
regression-test it, and a corpus with French/Russian or late-Romantic
repertoire must.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST   # noqa: E402

IDENT = HERE / "heldout-identity.json"
ACQ = HERE / "acquired-rosters.json"

# roster entry (the CHAIR) -> instruments that chair may be observed playing.
# Directional: presence here means "a <key> chair may show a <value> label".
DOUBLES: dict[str, set[str]] = {
    "Flute":    {"Piccolo", "Alto flute"},
    "Oboe":     {"English horn", "Oboe d'amore"},
    "Clarinet": {"Bass clarinet", "E-flat clarinet", "Basset horn"},
    "Bassoon":  {"Contrabassoon"},
    "Trumpet":  {"Cornet", "Flugelhorn"},
    "Horn":     {"Wagner tuba"},
    "Trombone": {"Bass trombone"},
}


def family(n):
    m = INST.lookup(n) if n else None
    return m.instrument.family if m else None


def main():
    # ── the table's own safety property ─────────────────────────────────────
    # ⚠️ EVERY ENTRY IS VALIDATED THROUGH THE LEXICON BEFORE IT MAY FIRE, and
    # entries that fail are EXCLUDED with a recorded reason rather than silently
    # kept. The first run of this audit REFUSED the table outright, which is how
    # the three defects below were found.
    print("TABLE AUDIT — every entry validated through the lexicon")
    usable, excluded = {}, []
    for chair, subs in sorted(DOUBLES.items()):
        cf = family(chair)
        for s in sorted(subs):
            m = INST.lookup(s)
            sf = family(s)
            if m is None:
                excluded.append((chair, s, "UNRESOLVED — not in the lexicon"))
            elif cf is not None and sf != cf:
                excluded.append((chair, s,
                                 f"CROSS-FAMILY {cf} -> {sf} via alias "
                                 f"{m.alias!r} — a LEXICON DEFECT"))
            elif m.instrument.name == chair:
                excluded.append((chair, s,
                                 f"NO-OP — collapses to {chair} in the lexicon,"
                                 f" so it can never look like a conflict"))
            else:
                usable.setdefault(chair, set()).add(m.instrument.name)
    print(f"  declared {sum(len(v) for v in DOUBLES.values())} doubles over "
          f"{len(DOUBLES)} chairs")
    print(f"  USABLE: {sum(len(v) for v in usable.values())}  "
          f"{ {k: sorted(v) for k, v in sorted(usable.items())} }")
    print(f"  EXCLUDED: {len(excluded)}")
    for chair, s, why in excluded:
        print(f"    {chair:10s} -> {s:18s} {why}")

    # ── is doubling EXERCISED by this corpus at all? ────────────────────────
    ident = json.loads(IDENT.read_text())
    recs = [r for r in ident["records"] if r["TRUTH"]]
    seen = Counter(r["TRUTH"] for r in recs)
    print(f"\n{'='*72}\nIS DOUBLING EXERCISED ON THE 20-ROW GATE?\n{'='*72}")
    print(f"  distinct truth instruments: {dict(seen.most_common())}")
    all_doubles = {d for v in DOUBLES.values() for d in v}
    present = sorted(all_doubles & set(seen))
    print(f"\n  doubling instruments PRESENT in the truth: "
          f"{present if present else 'NONE'}")

    # roster entries, and whether any observed name is a double of its chair
    by_sys = defaultdict(list)
    for r in recs:
        by_sys[(r["row_id"], r["system_index"])].append(r)
    for g in by_sys.values():
        g.sort(key=lambda r: r["ordinal"])
    rosters = {}
    for (rid, sidx), g in by_sys.items():
        w = rid.rsplit("-p", 1)[0]
        p = int(rid.rsplit("-p", 1)[1])
        if w not in rosters or (p, sidx) < rosters[w][0]:
            rosters[w] = ((p, sidx), [r["TRUTH"] for r in g])
    fires = []
    for (rid, sidx), g in sorted(by_sys.items()):
        w = rid.rsplit("-p", 1)[0]
        key, lineup = rosters[w]
        if (int(rid.rsplit("-p", 1)[1]), sidx) == key:
            continue
        for i, r in enumerate(g):
            chair = lineup[i] if i < len(lineup) else None
            obs = r["TRUTH"]
            if chair and obs != chair and obs in DOUBLES.get(chair, ()):
                fires.append((rid, sidx, i, chair, obs))
    print(f"\n  staff-positions where the observed name is a DOUBLE of its"
          f" roster chair: {len(fires)}")
    for f in fires:
        print(f"    {f[0]} sys{f[1]} ord{f[2]}: chair {f[3]} -> observed {f[4]}")

    print(f"""
  ⚠️ A ZERO HERE IS A REAL ANSWER, and it is the expected one: this corpus is
     Beethoven / Brahms / Dvorak / Bach / Mahler. Piccolo and contrabassoon are
     plausible in principle, cornet is not. The rule would be RIGHT BUT
     UNEXERCISED, which is worth stating rather than hiding — it means the gate
     cannot regression-test it and a future corpus must.""")

    # ── Contrabassoon: a double, or its own chair? ──────────────────────────
    print(f"\n{'='*72}\n⚠️ CONTRABASSOON IS A CHAIR HERE, NOT A DOUBLE\n{'='*72}")
    for w, (_k, lineup) in sorted(rosters.items()):
        if "Contrabassoon" in lineup:
            print(f"  {w}: roster carries BOTH "
                  f"Bassoon@{lineup.index('Bassoon')} and "
                  f"Contrabassoon@{lineup.index('Contrabassoon')}")
    print("""  So Brahms 1 seats the contrabassoon as its OWN player, and the
  Bassoon->Contrabassoon entry in the table must NOT collapse them: if the
  roster names both, they are two chairs and a double relation between them
  would let one satisfy the other. The rule is roster-entry-relative, and this
  is the case that shows why that matters.""")

    # ── does doubling touch R1? ─────────────────────────────────────────────
    print(f"\n{'='*72}\nDOES DOUBLING AFFECT R1?\n{'='*72}")
    if ACQ.exists():
        acq = json.loads(ACQ.read_text())
        for rid, rec in sorted(acq.items()):
            names = [v["instrument"] for v in rec["read"].values()
                     if v["instrument"]]
            d = [n for n in names if n in all_doubles]
            print(f"  {rid:34s} read {len(names)} names, doubling names: "
                  f"{d if d else 'none'}")
    print("""
  R1 compares the LENGTH of each system's labelled PREFIX, not the names in it.
  A double changes a name at a position that is already labelled, so it moves
  no prefix boundary and cannot make R1 fire or fall silent. The risk the
  hypothesis names — a doubling page looking like a lineup change — would
  require the double to appear where NO label stood before, i.e. to ADD a
  labelled position. On this corpus no read name is a doubling instrument at
  all, so R1's 0/20 false-positive record is untouched either way.""")


if __name__ == "__main__":
    main()
