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
