# A bracket ordinal is not a family identity

The residue on Beethoven 5 / Litolff after movement spans and the absent-instrument
veto was **7 staff records**: `Violin -> Trombone` x4, `Viola -> Trombone` x2 and
`Timpani -> Trombone` x1, on p23 sys1, p31 sys1 and p38 sys0 of
`benchmarks/omr-absent-instrument-veto-2026-09/out/whole-report2.extract.json`
(800/807 correct, size-17 systems a perfect 663/663).

**Every one carries `instrument_source: label`.** Nothing was misnamed — the name is
stamped per SLOT — so these staves were MIS-SLOTTED onto the finale's trombone slots
and then inherited the name those slots legitimately got from p44's own labels.

## It is not a tie broken arbitrarily

`probe/trace_align.py` records every `align` call of a real run. On p23 the DP scores
the WRONG alignment **+8.9489**, decomposed:

| term | chosen | truth | delta |
|---|--:|--:|--:|
| label | 42.0 | 42.0 | **0.0** |
| **group** | 3.0 | −6.0 | **+9.0** |
| position | 11.4659 | 11.5170 | −0.0511 |
| gaps (5 each) | −5.0 | −5.0 | 0.0 |

Both alignments delete five slots, so the gap cost cannot separate them. **This term
was the whole decision and it had the sign backwards.**

## Why

`Staff.group_index` is a **per-system bracket ordinal**. `system_grouping` numbers the
brackets it finds on ONE system, top down; nothing carries a group's meaning to the
next system. `_pair_score` compared it to `Slot.group_index` raw — two vocabularies,
one comparison.

On p23 the reduced twelve-staff system detects **two** brackets (winds and brass
merged, then strings) against the seventeen-slot reference's **three**:

    system     [(0, 7), (1, 5)]
    reference  [(0, 6), (1, 6), (2, 5)]

So its five string staves carry group 1 — which MATCHES the three Trombone slots
(group 1) and CONFLICTS with the real Violin/Viola slots (group 2). The term whose
entire purpose is that "winds do not align to strings" is what put the strings on the
trombones.

## The fix, and the two rules that were found by being wrong first

`map_groups` relates the vocabularies before comparing them: bracket blocks appear in
the same order on both sides, so the correspondence is a monotone assignment, and the
best one is the one whose block SIZES agree.

- **A block of s staves cannot map onto fewer than s slots.** Without it p23 is a TIE
  (`{0}|{2}` and `{1}|{2}` both cost 1) and abstains — costing the fix its own case.
  With it, exactly one assignment gives the seven-staff block room.
- **Untaken reference blocks are FREE.** Requiring full coverage broke
  `test_assign_slots_across_systems_and_pages` — a system with the winds entirely
  tacet, the ordinary case. The existing suite caught it.
- ⚠️ **A tie of different meanings ABSTAINS.** An arbitrary tie-break here is the same
  class of silent wrong answer as the ordinal comparison, only rarer and harder to
  find later.

## Measured

**The system, against hand-read truth** (`--pages 23,44`, twelve staves vs seventeen slots):

| arm | wrong | chosen |
|---|--:|---|
| raw ordinals (old) | 3 | `.., 9, 10, 11, 15, 16` |
| term withheld entirely | 2 | `.., 10, 12, 13, 15, 16` |
| **block mapping (shipped)** | **0** | `.., 12, 13, 14, 15, 16` = truth |

The seventeen-staff finale system is identity in every arm — where the vocabularies
already agree the mapping is 1:1 and nothing moves.

**Whole work, 88 pages, ONE shared read pass** (`probe/run_wholework_ab.sh`; arm 1
read 88 pages, arm 2 took 88 cache hits, so the flag is the only difference):

| | impossible | correct | wrong | slots moved by spans |
|---|--:|--:|--:|--:|
| ordinal, spans off | 89 | 750 | 57 | 208 |
| **map, spans off** | **43** | **756** | **51** | 180 |
| ordinal, spans on | 0 | 756 | 51 | |
| map, spans on | 0 | 756 | 51 | |

**Without spans the fix does about half of what spans do** — impossible 89 → 43, and
the same +6 correct / −6 wrong that spans achieve. **With spans on the two arms are
identical**: on this work they are redundant, and spans get there first.

⚠️ `score_2x2.py`'s baseline guard fires on both arms (89 and 43 against the recorded
91), so **neither arm is comparable to the composition session's figures** — a
different read pass. The two arms here are comparable to EACH OTHER and to nothing
else.

## ⚠️ The null: it does NOT repair the Brahms span regression

The veto-pricing session measured Brahms 1 / Breitkopf at 36 pre-finale impossible
names spans-off and **149 spans-ON**, and traced it to `_align_by_span`'s composition
step — a span's own 14-slot reference placed into the document's 16-slot one through
this same `align`. That made this fix an obvious candidate. It is not the cure:

| arm | spans off | spans on |
|---|--:|--:|
| ordinal | 36 | 149 |
| **map** | **36** | **149** |

Identical on all four cells, `Trombone` x70 + `Tuba` x79 either way
(`probe/run_brahms_ab.sh`, re-using that session's committed read cache, 0 pages read
/ 86 cache hits). Reproducing 36/149 exactly also **validates this harness** against
an independent one.

The reason is visible in the shapes: where the span reference and the document
reference have the SAME bracket structure, `map_groups` is 1:1 and withholds nothing —
the Brahms failure is a deletion choice made among already-comparable groups, a
different fault in the same function. **`OMR_MOVEMENT_REFERENCE`'s default-ON question
is untouched by this work and remains open.**

## Recorded, not fixed

⚠️ **Bracket detection is unstable across pages of one movement** — p31 finds three
groups where p23 and p38 find two, on the same printed lineup. That is a
`system_grouping` fault, and it needs recording precisely because this fix makes it
INVISIBLE: block correspondence is robust to it by design, so nothing downstream will
complain about it again.

## Reproduce

    python3 probe/trace_align.py <beethoven5.pdf> out/trace.json --pages=23,44
    probe/run_wholework_ab.sh          # 88 pages, ~13 min, one read pass
    probe/run_brahms_ab.sh             # re-uses the veto session's read cache

`OMR_SLOT_GROUP_MAP=map` (default) `| ordinal` (the refused arm, kept runnable)
`| off` (withhold the term entirely).
