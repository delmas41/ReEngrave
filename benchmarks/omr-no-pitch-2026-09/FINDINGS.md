# ROADMAP 2.20 — the Litolff `no_pitch` rise, 369 → 471

STAGED. Diagnosis, no pipeline change (§2 below explains why).

## 1. The two records

| record | commit | `no_pitch` | notes written | bars held out |
|---|---|---|---|---|
| 2026-09-28 | `c19cbca7` | 369 | 3,867 | 1,857 |
| 2026-09-29 | `23f4fa9e` | 471 (+102) | 4,407 (+540) | 1,576 (−281) |

Both records are the acceptance-set Litolff whole-movement gather (pdf pages
1-16), read ONCE each via `record_io.load_record` in
`probe/find_no_pitch.py`, which mirrors the EXACT pre-pitch refusal ladder
`export.to_musicxml` runs (not-a-notehead → whole-rest-ink → the `no_pitch`
check itself, `export.py:796-936`) rather than re-deriving it, so the
population it counts is provably the same one the exporter counts.

`no_pitch` fires when `Q.PITCH` is `None` for a notehead at export time,
which happens when neither EVALUATE consequence that writes it —
`restate_pitch` (own staff's clef) or `move_glyph` (the winning staff's clef,
where `glyph_owner` moved the note) — produced a value: the effective
staff's clef verdict is ABSTAINED, NARROWED, absent, or (rarest) DECIDED to
an anchor `pitch_resolver._pitch_from_position` does not know.

## 2. The +102, classified

`probe/diff_clefs.py` diffs every staff's `Q.CLEF` verdict between the two
records: **exactly 3 of 331 staves changed**, and they are precisely
2026-09-28's own `8dced2e4` (ROADMAP 2.11b, merged onto main between the two
gathers): `adjudicate_clef` now discounts an off-staff detector clef box
(a neighbour's clef bleeding into a padded measure cell) instead of letting
it decide the staff unopposed.

| staff | 09-28 clef | 09-29 clef | no_pitch caused |
|---|---|---|---|
| `staff/11/0/7` | decided `treble` | decided `alto` | 0 (still decided) |
| `staff/14/1/9` | decided `treble` | **abstained** `no_candidates` | **33** |
| `staff/6/1/9` | decided `treble` | **narrowed** `margin_below_floor` (a genuine 3-way tie) | **59** |

**92 of the 102 (90%) is these two staves, and it is 2.11b working exactly
as designed and already measured/tested/gated** (`benchmarks/omr-clef-
geometry-2026-09/FINDINGS.md` §7): a clef that used to be *decided* on
evidence that was really a neighbour's ink is now honestly *unread*. Per
CLAUDE.md rule 8 ("a fallback never converts 'cannot tell' into an
answer") this is the fix in the RIGHT direction — the 09-28 record's 369
`no_pitch` heads included zero WRONG pitches from these two staves because
they had none; the 09-29 record's extra 92 are heads that were previously
silently given the WRONG pitch (`treble`) and now correctly abstain. This is
not a connection fault to repair.

The remaining **10 of 102 (10%)** land on staves that were already
`clef_narrowed` in BOTH records (`staff/10/0/9` +7, `staff/4/0/8` +1,
`staff/4/0/9` +1, `staff/7/0/6` +2, `staff/12/0/10` −1) — consistent with
the task's own hypothesis: `bars_held_out_sum` fell 1,857 → 1,576 (2.19's
held-bar fix, `1eb947c2`), so more heads on already-abstaining/narrowing
staves now reach the pitch-computation stage instead of dying earlier as
`bar_does_not_add_up`. **0 "other."**

(a) shift: ~10. (b) regression from an ADJUDICATE change: ~92, but the
change is correct and already shipped, gated, and measured — not a
connection fault. (c) other: 0.

## 3. Why the existing gap machinery did not recover either staff

2.11b's own commit message names the intended safety net: "the existing
gap machinery (2.10's `clef_from_other_systems`, then INFER's
`fill_clef_gap`) may fill it." On this record it did not, for two distinct
and already-legible reasons (`Q.PART_PARTITION`/`Q.SLOT_INDEX` read via
`export.Record`, no re-adjudication needed):

- **`staff/14/1/9` (abstained `no_candidates`)**: `fill_clef_gap` needs the
  staff PLACED (a part it can find on another system) — `Q.PART_PARTITION`
  is absent here and `Q.SLOT_INDEX` is only `narrowed`
  (`family_block_not_forced`). No placed sibling, no clef to borrow. A
  genuine reading gap, not a bug.
- **`staff/6/1/9` (narrowed `margin_below_floor`, a real 3-way tie)**: this
  staff IS placed (`slot_index` decided 9, `full_lineup`), but
  `inferences.py`'s `_CLEF_GAP_PRIOR = Outcome.ABSTAINED` — the gap census
  targets ABSTAINED priors only, by the module's own comment ("so that a
  future narrowing reader has to come here and decide rather than inherit
  an answer"). `NARROWED` is structurally out of scope for the existing
  rule. Confirmed against the record's own `inference.reevaluation.skipped`
  entries: `["restate_pitch", "staff/6/1/9", "cause_narrowed"]` and
  `["restate_pitch", "staff/14/1/9", "cause_abstained"]` — INFER revisited
  both staves (something else nearby was inferred) and `restate_pitch`
  still had nothing to work with.

Both are named gaps already, not new ones this diagnosis introduces.

## 4. Top `no_pitch` cause overall, and the recommendation

| record | `clef_narrowed` | `clef_abstained:no_candidates` |
|---|---|---|
| 09-28 | 369 (100%) | 0 |
| 09-29 | 438 (93%) | 33 (7%) |

`clef_narrowed` is the dominant cause on BOTH records — confirming 2.10's
own FINDINGS ("residual `no_pitch` was the NARROWED clef") is still exactly
right, now with a concrete third example (`staff/6/1/9`) of the shape it
named. **Recommended next item**: extend `fill_clef_gap`/`clef_gap_census`
to also propose from a NARROWED prior (own candidates only, never a value
outside them — INFER may narrow to one of a rule's OWN candidates, never
invent one, per CLAUDE.md §4a) where the same part's clef is legible on
another system. `inferences.py`'s own comment already marks this as the
intended extension point; it was out of scope for 2.10 and is out of scope
for THIS diagnosis lane (no reading/convention question was asked of Sean
about it), but it is the one concrete, named lever that would recover both
`staff/6/1/9`'s 59 heads and the wider `clef_narrowed` population.

## 5. Reproduction

```
python3 benchmarks/omr-no-pitch-2026-09/probe/find_no_pitch.py <record.json> <out.json>
python3 benchmarks/omr-no-pitch-2026-09/probe/diff_clefs.py <record-28.json> <record-29.json>
```

No pipeline code was touched; `staged.check` is unchanged at 247 and no
test was added, because there is no connection fault here to pin with a
RED→GREEN pair.

## 2. ROADMAP 2.10b — the NARROWED clef gap, built and priced

§4's recommendation (widen `fill_clef_gap` to a NARROWED prior, bounded to
that contest's own candidates) is BUILT on `claude/clef-narrowed-gap-2.10b`,
pushed, not merged.

### 2.1 The change

`inferences.clef_gap_census` (`tools/omr/staged/inferences.py`) widened
`_CLEF_GAP_PRIOR` (now `_CLEF_GAP_PRIORS`) from `(ABSTAINED,)` to
`(ABSTAINED, NARROWED)`. For a NARROWED clef, the SAME two-tier ladder as
2.10 runs (2. the same part's clef DECIDED on other systems, majority, a
split abstains; 3. the instrument's conventional header clef), but the
ladder's answer is checked against that contest's OWN surviving candidates
(`Candidate.value`, read straight off the standing verdict) before it may be
proposed — `declined_not_a_candidate` names the case where it is not.
`infer._admit` would raise `ValueNotAdmitted` if this guard were skipped (it
already enforces rule 4 for every other INFER rule); this rule enforces the
same bound itself, one level up, so the decline reads as a decline rather
than crashing the stage. No new flag — `OMR_CLEF_GAP` (roadmap 2.10) already
gates the whole rule and its semantics ("this rule's evidence ladder, on or
off") cover the widened prior with no change of meaning.

`staff/14/1/9`-type case (§2's own motivating example, an ABSTAINED clef
with no placed part): unaffected structurally. It has no `Q.PART_PARTITION`
and only a `narrowed` `Q.SLOT_INDEX`, so `_part_of` still returns `slot=None`
and the rule still declines `declined_part_not_decided` before candidates
ever enter the question — it does NOT follow, exactly as predicted.

### 2.2 Tests, RED→GREEN

`tools/omr/tests/test_infer_clef_gap.py`: one existing test
(`test_a_narrowed_clef_is_the_clef_readers_problem_not_this_rules`) pinned
the OLD blanket exclusion and is updated in place, not deleted (2.11b's own
precedent) — its fixture now fills, so it moved into a new assertion
(`test_a_narrowed_clef_whose_contest_never_saw_the_answer_stays_narrowed`,
same shape, different candidates, still declines). Six new tests added in
`TestRoadmap210bTheNarrowedClefLadder` covering exactly the three proof
cases asked for (a narrowed {treble, alto} Viola with alto decided on its
other systems → alto; a narrowed staff whose other-system answer is NOT a
candidate → untouched; a split → untouched), plus tier (3) bounded the same
way and the second-EVALUATE-pass ordering proof for a NARROWED fill. RED
confirmed against `origin/main`'s `inferences.py` (swapped in temporarily,
not committed): **7 of 43 failed** for the right reason (`declined_not_a_
candidate` expected, `declined_prior_is_narrowed` — the old blanket
exclusion — returned instead, or the clef stayed NARROWED where it should
have filled). GREEN on the fix: 43/43. Fast tier: **3,748 passed** (main's
3,742 + 6 new), 3 skipped — unchanged from main otherwise. `staged.check`
**247**, unchanged.

### 2.3 Priced in-process on the 09-29 Litolff record — no re-gather

`benchmarks/omr-clef-gap-2026-09/probe/replay.py` (2.10's own base/arm
instrument: rebuild the record's OWN rows — observations, abstentions AND
verdicts, with their original ids — into a fresh `Log`, then re-run INFER +
the bounded second EVALUATE with `OMR_CLEF_GAP` toggled) run unmodified
against the 09-29T104646Z whole-movement record:

- **Control passes**: 135,920 of 135,920 verdicts reproduce exactly, 0
  differ, 0 extra; 189,981 of 189,981 observations replayed. The rebuild IS
  the record.
- **`decided_clefs_changed: []`** — 0, confirmed. Rule 3 held.
- **11 narrowed clefs, 1 abstained clef, total on this document** (the
  `OMR_CLEF_GAP=0` base reading). Of the 11 narrowed: **8 filled, all by
  tier (2), 0 by tier (3)**; **3 correctly declined**
  `declined_not_a_candidate` — real, not synthetic:

  | staff | contest's candidates | other systems' majority | declined? |
  |---|---|---|---|
  | `staff/4/0/9` (Cello) | treble, tenor | bass (21 v 4) | **declined** — bass is not a candidate |
  | `staff/5/0/6` (Violin) | tenor, bass, alto | treble (29/29) | **declined** — treble is not a candidate |
  | `staff/12/0/10` | tenor, treble, alto | bass (21 v 4) | **declined** — bass is not a candidate |

  The single abstained clef, `staff/14/1/9`, **still abstains** — no placed
  part, exactly as predicted in §2.1.
- **`no_pitch`: 471 → 135 (−336, −71%)** on this same record, INFER/EVALUATE
  re-decided in-process, nothing else changed. By system, the shortfall
  clears entirely on `6/1` (staff/6/1/9's own system) and shrinks on `4/0`
  (70→32); `5/0`, `12/0` and `14/1` are untouched — exactly the three
  declined staves plus the one abstained staff that could not follow.
- **`refusal_deltas`**: `no_pitch` −336, `bar_does_not_add_up` +165,
  `duration_narrowed` +22, `owned_by_another_staff` +4, `owner_not_read`
  +17 — heads that used to die early at `no_pitch` now reach further into
  the ladder and a fraction of them are caught by a LATER refusal instead
  (the same reclassification shape §2's own diagnosis named, one stage
  further downstream). `to_musicxml` did not raise `Unbalanced` on either
  arm — the accounting equality holds. `base_arm_is_deterministic` and
  `base_arm_export_equals_the_records_own_export` both `true`.

The full summary is `benchmarks/omr-no-pitch-2026-09/out/210b-arm/litolff-2-
10b-summary.json`; the ARM/BASE records and MusicXML themselves are
regenerable in one command (`replay.py ... --write-arm`, ~1 minute) and are
gitignored (600 MB each, unpooled — see `.gitignore`).

Brahms: **skipped**, per the work order's own escape valve — the acceptance
manifest's Brahms whole-movement record is 1.1 GB and `replay.py`'s rebuild
alone (three full passes: control + base + arm) would multiply the Litolff
rebuild cost several times over on a bigger document; not run.

### 2.4 Crops

Five header crops (clef + first bar), one per distinct instrument among the
8 filled staves plus §2's own motivating subject
(`benchmarks/omr-no-pitch-2026-09/probe/crop_filled_2_10b.py`, adapted from
2.10's `crop_clef.py`, same frame control, same GREEN-staff/RED-bracket
convention): `staff/6/1/9` (unnamed part, alto), `staff/10/0/9` (Viola,
alto), `staff/12/1/2` (Clarinet, treble), `staff/14/0/3` (Bassoon, bass),
`staff/7/0/6` (Timpani, bass) — under `benchmarks/omr-no-pitch-2026-09/
out/print/`, manifest `crop-manifest-litolff-210b.json`,
`VERDICT_none_yet: null` on every row, none refused (frame control passed
on all five).
