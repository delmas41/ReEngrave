# H0 — a structure metric for the 20-row scan gate

Measured 2026-09-05 on branch `claude/structure-rnd-2026-09`.
Instrument: [`score_structure.py`](score_structure.py) → [`structure-score.json`](structure-score.json).

```bash
python3 benchmarks/omr-structure-rnd-2026-09/score_structure.py
```

No detector is run, no dossier is loaded, nothing is tuned. This is an
instrument, not a result.

---

## Why it exists

**OMR-NED cannot referee structure work on this corpus.** Three measurements
already establish that, and this document does not re-derive them:

- `benchmarks/omr-staff-structure-2026-09/FINDINGS.md` §6 — "slot assignment
  and staff segmentation are not costing anything in this bucket on this
  corpus".
- 87% of the `entire staff` bucket is a **condensation floor** tied with
  Audiveris *to the edit* on all seven single-system rows (513/513, 513/513,
  0/0, 1001/1001, 649/649, 1674/1674).
- `benchmarks/omr-structural-parts-2026-09/FINDINGS.md` — the structural
  buckets **invert sign** depending on whether a count source exists (ES +2,864
  without an oracle, −892 with) from the same stitching code.

So a correct structure fix moves pooled OMR-NED by a rounding error, and a
wrong one may *improve* it: the metric is symmetric and rewards
under-prediction, which has fooled this repo twice already (the slur `drop`
variant; fragments-are-cheaper).

⚠️ **This metric emits no edit counts and no combined score.** A structure
score and an edit count answer different questions; merging them is how the
ES/EM repricing fooled two sessions. The three sub-scores below are reported
side by side and are never summed with each other or with OMR-NED. That is
enforced by construction — there is no code path in `score_structure.py` that
produces a single number.

---

## Fixture provenance (verified, not assumed)

| | |
|---|---|
| transcriptions | `/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/**reconciliation**/benchmarks/omr-scan-e2e-2026-09/fixtures/` |
| suffix | `.reconciliation.omr.json` — **20 files** |
| ground truth | `benchmarks/omr-scan-e2e-2026-09/works.json`, 20 rows (identical row count in both trees) |
| read | 396 staves, 26 scored systems, 11 multi-system rows |
| slot coverage | `slot_index` present on 396/396 staves |

⚠️ **The main checkout's `fixtures/` still holds the 11-row `..graft09` set.**
A script pointed there measures the *old* gate and says nothing about this one.
`score_structure.py` asserts `len(fixtures) == 20` and that the fixture stems
equal the `works.json` row ids exactly, and fails loudly with that warning in
the message. The reconciliation tree is opened **read-only**; nothing is
written there.

`works.json` is **scoring only, never an input**. Dossiers are barred entirely
(the row protocol already records `dossier: null`, because `data/dossiers/` is
generated from the same Gradus MusicXML used as truth).

**Assertions that prove the audit looked at something** — an audit that can
return "nothing found" must first prove it looked. `score_structure.py` fails
on: fixture count ≠ 20, row count ≠ 20, fixture/row id mismatch, staves read
≠ 396, multi-system rows ≠ 11, any staff missing `slot_index`, and any of the
three sub-scores scoring zero rows.

**Parsers only** — `json` throughout; no regex touches a structured format.

### The name normalizer is deliberately NOT the pipeline's

Truth names are printed (`Corni III.IV. in C`, `Kontrafagott`, `Bässe`);
predictions are canonical English (`Horn`, `Contrabassoon`, `Contrabass`). The
mapping is a **hand table inside `score_structure.py`**, covering every printed
name that occurs in `works.json` (0 unmapped names across all 324 scored
staves).

It is not `tools/omr/instruments.py` on purpose: that lexicon is *part of the
system under test* — it is what reads `Hörner in Es` as *Trumpet* on the
Breitkopf Brahms and once turned `Tr. Alt.` into a singer. Normalising the
truth with it would hide exactly the errors this metric is built to see. (And
indeed, 13 of the 26 identity errors below are that lexicon.)

---

## 0. Page cardinality — a precondition, not a sub-score

**20/20 rows**: predicted system count and staff count equal `page.n_systems` /
`page.n_staves`. **26/26 scored systems** have the exact staff count.

This is reported first because every naming number below is *conditional on it*
— identity pairs staves positionally, which is only meaningful because the
counts are right. It is also the direct corroboration of the FINDINGS §6 claim
that staff segmentation costs nothing here: on this corpus it is not merely
cheap, it is exact.

⚠️ Consequence: **the `over` / `under` columns in the roster table are
ALIGNMENT residuals, not count errors.** Every one of them is a staff we cut
correctly and named wrongly or not at all.

---

## 1. Roster recovery

*Did we recover the ordered printed lineup of each system?*

Per system, the predicted ordered list of instrument kinds is compared against
the hand-verified printed lineup. Two numbers, both reported:

- **order-preserving alignment accuracy** — longest order-preserving matching
  (LCS on canonical kind) / truth staves. Forgiving of a single insertion that
  shifts everything after it.
- **strict positional accuracy** — position *i* against position *i*. The hard
  number.

Truth comes, in order of preference: an explicit `systems_as_printed` block; a
single `staves` map **only where `n_systems × len(map) == n_staves`** (the page
really is n copies of that lineup); Mahler's `condensation.staves_as_printed`.
Otherwise the row abstains.

**Coverage: 16 of 20 rows, 324 of 396 staves.**

| pooled | |
|---|--:|
| cardinality exact | 16/16 rows, 26/26 systems |
| order-preserving alignment accuracy | **0.8457** (274/324) |
| strict positional accuracy | **0.8302** (269/324) |
| over / under (alignment residuals) | 50 / 50 |

| row | truth source | T | P | over | under | aligned | positional |
|---|---|--:|--:|--:|--:|--:|--:|
| beethoven-sym5-mvt1-984073-p1 | staves_map × systems | 12 | 12 | 0 | 0 | 12 | 12 |
| beethoven-sym5-mvt1-984073-p2 | staves_map × systems | 22 | 22 | 2 | 2 | 20 | 20 |
| beethoven-sym5-mvt1-984073-p3 | systems_as_printed | 19 | 19 | 0 | 0 | 19 | 19 |
| beethoven-sym5-mvt1-984073-p4 | systems_as_printed | 22 | 22 | 4 | 4 | 18 | 16 |
| beethoven-sym5-mvt1-575951-p1 | staves_map × systems | 12 | 12 | 0 | 0 | 12 | 12 |
| beethoven-sym5-mvt1-575951-p2 | staves_map × systems | 22 | 22 | 2 | 2 | 20 | 20 |
| beethoven-sym5-mvt1-575951-p3 | systems_as_printed | 19 | 19 | 0 | 0 | 19 | 19 |
| beethoven-sym5-mvt1-575951-p4 | systems_as_printed | 22 | 22 | 5 | 5 | 17 | 16 |
| dvorak-sym9-mvt1-405834-p5 | staves_map × systems | 15 | 15 | 0 | 0 | 15 | 15 |
| dvorak-sym9-mvt1-405834-p6 | staves_map × systems | 15 | 15 | 7 | 7 | 8 | 8 |
| dvorak-sym9-mvt1-405834-p7 | staves_map × systems | 30 | 30 | 16 | 16 | 14 | 12 |
| brahms-sym1-mvt1-317803-p1 | staves_map × systems | 14 | 14 | 1 | 1 | 13 | 13 |
| brahms-sym1-mvt1-317803-p2 | systems_as_printed | 27 | 27 | 4 | 4 | 23 | 23 |
| brahms-sym1-mvt1-317803-p3 | staves_map × systems | 28 | 28 | 4 | 4 | 24 | 24 |
| brahms-sym1-mvt1-317803-p4 | staves_map × systems | 28 | 28 | 4 | 4 | 24 | 24 |
| mahler-sym5-mvt1-local-p2 | condensation.staves_as_printed | 17 | 17 | 1 | 1 | 16 | 16 |

The two Dvořák rows carry most of the loss and it is **coverage, not error**:
p.5 reads margin labels on all 15 staves (`instrument_source: label`) and
scores 15/15; p.6 and p.7 read none, fall back to `score_order`, and leave 7 of
15 (resp. 8 of 15) staves unnamed. A null is charged as a miss here by design —
an unnamed staff is not a recovered roster entry.

---

## 2. Continuity

*Does the same printed part get the same slot in every system it appears in?*

Scored as **pairwise slot linkage**, which needs no global slot numbering and
therefore imputes nothing where a page's union order is ambiguous:

- *truth link* — two staves in different systems printing the same part;
- *pred link* — two staves in different systems given the same `slot_index`;
- precision = |pred ∩ truth| / |pred|, recall = |pred ∩ truth| / |truth|.

A staff whose part is **re-condensed** in the other system is *unpairable*: it
leaves both sides and is counted, never scored. Beethoven p.4 is the case —
system 1 prints `Violoncello` + `Basso` on two staves, system 2 condenses them
into `Bassi (Violoncello e Basso)`. Detected mechanically (unmatched on both
sides, canonical kind-sets overlap), not hand-listed.

**Coverage: 10 of 11 multi-system rows.**

| pool | rows | truth links | pred links | correct | precision | recall |
|---|--:|--:|--:|--:|--:|--:|
| all | 10 | 112 | 112 | 105 | 0.9375 | 0.9375 |
| tier A — explicit per-system truth | 5 | 47 | 47 | 40 | **0.8511** | **0.8511** |
| tier B — one map × n_systems | 5 | 65 | 65 | 65 | 1.0000 | 1.0000 |
| **informative** — lineups actually differ | 5 | 47 | 47 | 40 | **0.8511** | **0.8511** |

| row | tier | lineups identical? | T | P | ok | precision | recall | unpairable |
|---|---|---|--:|--:|--:|--:|--:|--:|
| beethoven-sym5-mvt1-984073-p2 | B | yes | 11 | 11 | 11 | 1.0000 | 1.0000 | 0 |
| beethoven-sym5-mvt1-984073-p3 | A | no | 8 | 8 | 8 | 1.0000 | 1.0000 | 0 |
| beethoven-sym5-mvt1-984073-p4 | A | no | 9 | 9 | 6 | 0.6667 | 0.6667 | 3 |
| beethoven-sym5-mvt1-575951-p2 | B | yes | 11 | 11 | 11 | 1.0000 | 1.0000 | 0 |
| beethoven-sym5-mvt1-575951-p3 | A | no | 8 | 8 | 8 | 1.0000 | 1.0000 | 0 |
| beethoven-sym5-mvt1-575951-p4 | A | no | 9 | 9 | 6 | 0.6667 | 0.6667 | 3 |
| dvorak-sym9-mvt1-405834-p7 | B | yes | 15 | 15 | 15 | 1.0000 | 1.0000 | 0 |
| brahms-sym1-mvt1-317803-p2 | A | no | 13 | 13 | 12 | 0.9231 | 0.9231 | 0 |
| brahms-sym1-mvt1-317803-p3 | B | yes | 14 | 14 | 14 | 1.0000 | 1.0000 | 0 |
| brahms-sym1-mvt1-317803-p4 | B | yes | 14 | 14 | 14 | 1.0000 | 1.0000 | 0 |

⚠️ **THE `all` ROW IS THE WRONG NUMBER AND IS PRINTED ONLY SO IT CANNOT BE
QUOTED WITHOUT ITS QUALIFIER.** All five tier-B rows print the **identical
lineup in every system**, and the exporter joins staves by ordinal — so those
rows are satisfied *by construction*. They confirm nothing is broken; they
cannot show the continuity logic works. The five informative rows are exactly
the five tier-A rows, and they pool to **0.8511**. Quote that.

The score reproduces both documented failures without being told about them:

- **Beethoven p.4 twins, 6/9.** Both systems count 11 but the lineups differ
  (system 1 has no Timpani and splits Vcl./Basso; system 2 keeps Timpani and
  condenses to `Bassi.`), so ordinal stitching does not refuse — it grafts
  system 1's Violino I onto system 2's Timpani and everything below shifts.
  That is precisely the `_purpose` warning on that row, priced here as 3 wrong
  links out of 9 on each twin.
- **Brahms p.2, 12/13.** System 2 suppresses `2 Trompeten in C`; the pipeline
  instead skips the slot belonging to `4 Hörner in Es 3./4.` — the documented
  "Hörner in Es read as Trumpet" lexicon misread, costing exactly one link.
- **Beethoven p.3 twins, 8/8.** Genuine tacet suppression (11 staves then 8),
  handled correctly on both scans. This is the one place the corpus shows the
  continuity logic *working* on a page that could have broken.

---

## 3. Identity

*Do we name each staff's instrument, and is the name right?*

Coverage and precision are reported **separately, coverage first**. Pairing is
positional within a system and only attempted where the predicted staff count
equals the truth lineup length (26/26 systems qualify).

| pooled | |
|---|--:|
| scoreable staves (16 rows) | 324 |
| named | 295 → **coverage 0.9105** |
| correct | 269 → **precision 0.9119** |
| whole corpus, no truth needed | 365/396 named, coverage 0.9217 |

| row | scoreable | named | correct | coverage | precision |
|---|--:|--:|--:|--:|--:|
| beethoven-sym5-mvt1-984073-p1 | 12 | 12 | 12 | 1.0000 | 1.0000 |
| beethoven-sym5-mvt1-984073-p2 | 22 | 22 | 20 | 1.0000 | 0.9091 |
| beethoven-sym5-mvt1-984073-p3 | 19 | 19 | 19 | 1.0000 | 1.0000 |
| beethoven-sym5-mvt1-984073-p4 | 22 | 20 | 16 | 0.9091 | 0.8000 |
| beethoven-sym5-mvt1-575951-p1 | 12 | 12 | 12 | 1.0000 | 1.0000 |
| beethoven-sym5-mvt1-575951-p2 | 22 | 22 | 20 | 1.0000 | 0.9091 |
| beethoven-sym5-mvt1-575951-p3 | 19 | 19 | 19 | 1.0000 | 1.0000 |
| beethoven-sym5-mvt1-575951-p4 | 22 | 18 | 16 | 0.8182 | 0.8889 |
| dvorak-sym9-mvt1-405834-p5 | 15 | 15 | 15 | 1.0000 | 1.0000 |
| dvorak-sym9-mvt1-405834-p6 | 15 | 8 | 8 | 0.5333 | 1.0000 |
| dvorak-sym9-mvt1-405834-p7 | 30 | 14 | 12 | 0.4667 | 0.8571 |
| brahms-sym1-mvt1-317803-p1 | 14 | 14 | 13 | 1.0000 | 0.9286 |
| brahms-sym1-mvt1-317803-p2 | 27 | 27 | 23 | 1.0000 | 0.8519 |
| brahms-sym1-mvt1-317803-p3 | 28 | 28 | 24 | 1.0000 | 0.8571 |
| brahms-sym1-mvt1-317803-p4 | 28 | 28 | 24 | 1.0000 | 0.8571 |
| mahler-sym5-mvt1-local-p2 | 17 | 17 | 16 | 1.0000 | 0.9412 |

**Dvořák p.6 has precision 1.0000 at coverage 0.5333.** That is the reason
coverage is printed first: a precision figure read alone would rank the row
above every page that actually named its staves.

### The 26 identity errors, by printed name

| n | printed | truth | predicted | source |
|--:|---|---|---|---|
| 7 | `4 Hörner in Es 3./4.` | Horn | Trumpet | score_order |
| 6 | `Kontrafagott` | Contrabassoon | Bassoon | label |
| 5 | `Viola` | Viola | Violin | score_order |
| 2 | `Tromboni I.II.` | Trombone | Trumpet | score_order |
| 1 | `Violino I` | Violin | Trumpet | score_order_ambiguity |
| 1 | `Timpani in C.G.` | Timpani | Trumpet | score_order_ambiguity |
| 1 | `Viola` | Viola | Cello | score_order |
| 1 | `Violino I` | Violin | Timpani | label |
| 1 | `Violino II` | Violin | Viola | score_order |
| 1 | `Contrafagott` | Contrabassoon | Horn | score_order |

**Half the errors are two known lexicon faults on one edition.** The top two
rows (13 of 26) are the two misreads works.json already documents for the
Breitkopf Brahms. The metric found them from the fixtures alone.

---

## Abstentions — every one, with its reason

| row | sub-score | reason |
|---|---|---|
| mahler-sym5-mvt1-local-p2 | roster + identity, **partial** | 5 one-line percussion staves excluded from the truth lineup — a five-line staff detector cannot find them by construction. The 17 five-line staves are scored. |
| mahler-sym5-mvt1-local-p3 | roster, identity | row carries no printed-lineup truth (OMR-NED-only row) |
| mahler-sym5-mvt1-local-p4 | roster, identity | " |
| mahler-sym5-mvt1-local-p5 | roster, identity | " |
| bach-brandenburg3-mvt1-468678-p1 | roster, identity, **continuity** | " — the only multi-system row with no lineup truth |
| beethoven-sym5-mvt1-984073-p4 | continuity, 3 staves | `Violoncello` + `Basso` vs `Bassi (Violoncello e Basso)` — re-condensation, unpairable |
| beethoven-sym5-mvt1-575951-p4 | continuity, 3 staves | " (twin scan of the same plate) |

Counts: **4 rows abstain on roster and identity** (4/20), **1 row abstains on
continuity** (1/11), **6 staves abstain within continuity** as unpairable, and
**5 printed staves abstain within Mahler p.2**. Zero truth names were unmapped
by the hand table, so there are no silent abstentions hiding in the normalizer.

---

## What this metric CANNOT see

This is the part that matters. Read it before quoting any number above.

1. **It cannot distinguish `Violino I` from `Violino II`, `Corni I.II.` from
   `Corni III.IV.`, or the upper from the lower Mahler trumpet staff.** The
   pipeline emits *instrument kinds* (`Violin`, `Horn`), not numbered desks, so
   the truth is folded to that granularity before comparison. A prediction that
   swapped the two horn staves would score **perfect**. This is the single
   largest leniency, and it touches roster, continuity and identity alike.

2. **Condensed staves are scored leniently.** `Violoncello e Basso` counts as
   correct for either `Cello` or `Contrabass`. Naming a condensed staff by only
   one of its sections is invisible here — and that is exactly the condensation
   floor that owns 87% of the `entire staff` OMR-NED bucket. **Neither metric
   can see it.**

3. **Continuity is answered by five rows, and only five.** The other five
   multi-system rows print the same lineup in every system, where joining by
   ordinal cannot fail; one abstains. A change to the continuity logic that
   only affects identical-lineup pages will move nothing here, and a change
   that breaks them will move it by exactly the amount ordinal stitching was
   already getting for free.

4. **Roster and identity are correlated, not independent.** They share the
   positional pairing and the same name table; a systematically mis-named staff
   is charged in both. They are separate *questions* (ordered-set recovery vs
   per-staff naming + coverage), not statistically independent measurements.
   Do not read agreement between them as corroboration.

5. **It cannot see anything below the staff.** Not one note, duration, clef,
   key, meter, measure count or barline is examined. A pipeline that recovered
   the roster perfectly and read no music at all scores 1.0000 on all three.
   This metric is a *complement* to OMR-NED, never a replacement — the reason
   it exists is that OMR-NED cannot referee structure, not that structure is
   the whole job.

6. **Positional identity presumes segmentation.** Page cardinality is 20/20 on
   this corpus, so pairing by position is safe *today*. A future change that
   splits or merges a staff would make identity abstain (systems whose counts
   disagree are skipped whole), and the pooled figure would silently rest on
   fewer staves. The `abstained_systems` field exists to catch that; check it
   before comparing two runs.

7. **`instrument_source` is recorded but never scored.** A staff named
   correctly from a margin label and one named correctly from the score-order
   prior are worth the same here, though only the first is evidence the page
   was read.

8. **Four rows and 72 staves are outside the metric's reach entirely**
   (Mahler p.3/p.4/p.5, Bach p.1). Mahler p.3–p.5 are also the corpus's densest
   Peters pages and Bach is its only Baroque one, so the abstentions are not a
   random 18% — the unmeasured slice is systematically the hardest and the most
   unlike the rest.

### On sub-score 2, plainly

**Continuity is measurable on this corpus, but only just.** Five informative
rows, of which four are two plate-twins of the same two Beethoven pages — so
the effective independent evidence is **three pages** (Beethoven p.3, Beethoven
p.4, Brahms p.2), the twins serving as a resolution control rather than as new
structure. A pooled 0.8511 over 47 links is a real number and it caught a real,
documented graft; it is not a number that will separate two competing
continuity designs. Widening it needs more pages that print *different* lineups
in different systems — tacet suppression and re-condensation — not more pages.

---

## Reproducing

```bash
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a33465d4058896096
python3 benchmarks/omr-structure-rnd-2026-09/score_structure.py
```

Re-run after any structure change and diff `structure-score.json`. The pooled
sub-scores are in `pooled`; per-row detail, the wrong-link list and the identity
error census are in `per_row`; every abstention is in `abstentions`.
