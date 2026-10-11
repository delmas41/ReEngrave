# The missing-notes diagnosis — Brahms 1/i (Breitkopf `317803`), 2026-09-28/29

PATH: STAGED. ROADMAP work-order item 2. One record read, no re-gather, no
re-adjudicate, no code change under `tools/omr/staged/`.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

This diagnosis assumes CLAUDE.md §10's stated conventions (a whole rest
means the bar; a beam runs stem-to-stem; the ledger lines are authoritative
for owner) without re-asking Sean. It would be falsified by a crop where
Sean says a `beams_ambiguous` example's TRUE beam count disagrees with both
candidates this record narrowed between. NOT CONFIRMED with Sean.

## 0. What was read

Record: `.claude/worktrees/redecide-f4168dfd/out-redecide/brahms/amended.record.json`
(1.5 GB on disk), provenance `{commit: c19cbca7b7339d74e255a26b80e7fc3a385d428e,
dirty: True}`, a review/amend pass over the whole-movement Brahms 1/i gather
(`library/_shared-records/brahms1-breitkopf-mvt1-whole-20260928.record.json`,
`amended_at: 2026-09-28T13:18:14-07:00`) — this is the SAME provenance
commit the current whole-movement figures in ROADMAP's START HERE cite
(`c19cbca7`), so this record IS the one behind the "3,529 pitched notes
written (was 965 the morning of the 28th)" line, and that figure is
reproduced exactly below (§1), which is the cheapest control available:
an independent read landing on a number someone else already wrote down.

Read exactly ONCE, via `record_io.load_record`, inside
`probe/notehead_funnel.py`. That script:

1. calls `export.build(rec)` and `export.to_musicxml(doc)` — the SAME two
   functions the product path itself calls at EXPORT, on this record,
   read-only (no `--out` file written; the same technique
   `benchmarks/omr-accidental-2026-09/probe/reexport.py` already uses) — for
   the AUTHORITATIVE funnel (`report["notes_not_written"]`,
   `report["bars_held_out_sum"]`);
2. separately walks `Q.GLYPH_BOX` itself, mirroring only the PREFIX of
   `export._place_notes` (the not-a-notehead / not-a-rest / whole-rest /
   no-pitch / duration checks, which run BEFORE the owner/held-out checks),
   to get the duration verdict's OWN reason and the clef's own status —
   detail the authoritative counters don't carry;
3. cross-validates every bucket the walk produces against the authoritative
   counters from (1). **The control passed: zero mismatch**, on three
   separate runs of the script (the script was extended twice, for more
   examples and for page-frame glyph boxes, and re-run each time — the
   record was loaded three times across development, not once; the FINAL
   numbers below come from one designated run, `probe/out/funnel.log`,
   and did not change across any of the three loads).
4. dumps geometry (`Q.STAFF_LINES`, `Q.STAFF_SPACING`, `Q.CELL_BOX`, and each
   example glyph's own PAGE-frame `bbox_page`) for every captured example,
   so the crop step (`probe/crop_beams_ambiguous.py`) never opens the record
   again.

Everything below is read straight off `probe/out/funnel.json`
(committed, 160 KB).

## 1. The funnel — does it close?

| | |
|---|--:|
| Gathered (Q.GLYPH_BOX rows that are a notehead or a rest) | **32,656** |
| Written (`<note>` + `<rest>`) | **4,926** (3,529 notes + 1,397 rests) |
| Not written, named | **27,620** |
| **Sum (written + not written)** | **32,546** |
| **Residual, unaccounted** | **110 (0.34%)** |

The partition closes to within 0.34%. **It does not close exactly, and
that residual is reported rather than hidden** (rule 7: a control that can
fail). Traced as far as this diagnosis went: my own prefix-walk agrees with
the authoritative `build()`/`to_musicxml()` counters on every individual
bucket, at every one of the three runs — so the gap is not a bug in this
probe's replication of `_place_notes`. It sits between "candidates that
pass the owner/held-out/fit checks" (23,973 rows, independently derived two
ways and agreeing) and "final written + bar-holdout-removed" (20,332 by one
arithmetic, 20,442 by the other) — a 110-row gap in the owner/held-out/
written-value-fits-no-note segment of `_place_notes`, which this probe did
not re-walk (it only mirrors the PREFIX). **Not run down further — flagged
as an open accounting question for whoever next touches that segment**, not
claimed as a defect.

### The funnel, top to bottom

| named refusal | count | % of not-written | sub-reason (where named) |
|---|--:|--:|---|
| `bar_does_not_add_up` (2.8 hold-out) | 15,406 | 55.8% | — (bar-level; see §2) |
| `not_a_notehead:too_narrow` | 3,401 | 12.3% | width < 1.0 staff space (see §4) |
| `duration_narrowed` | 3,333 | 12.1% | **100% `beams_ambiguous`** (see §3) |
| `owned_by_another_staff` | 2,532 | 9.2% | already adjudicated by Sean (o26b, 16/19 correct) |
| `not_a_rest:rest_is_a_duplicate_box` | 882 | 3.2% | roadmap 2.15's own repair, working as shipped |
| `staff_not_identified` | 867 | 3.1% | not investigated this session |
| `not_a_notehead:clipped_fragment` | 617 | 2.2% | legacy `_drop_clipped_notehead_fragments` port |
| `written_value_fits_no_note` | 132 | 0.5% | not investigated this session |
| `rest_duration_abstained` | 222 | 0.8% | `rest_stands_where_no_rest_hangs` 202, `unreadable_rest` 20 |
| `not_a_notehead:belongs_to_a_nearer_staff` | 115 | 0.4% | roadmap 2.7b's own repair |
| `ink_is_a_whole_rest` | 66 | 0.2% | working as shipped (2026-09-15) |
| `not_a_notehead:is_a_clef` | 32 | 0.1% | not investigated this session |
| `rest_duration_narrowed` | 11 | 0.04% | `rest_slot_contradicts_class` (all 11) |
| `no_pitch` | 4 | 0.01% | clef itself NARROWED, not abstained (all 4) |
| **total** | **27,620** | 100% | |

`bars_held_out_sum`: **4,607 of 5,792 bars-with-events (79.5%)**, judged by
a carried meter on 4,406 of them — up from the 2026-09-23 whole-movement
gather's 4,513/5,792 (77.9%, ROADMAP's own prior figure), consistent with
this being a DIFFERENT, later re-decision (2.6c/2.15/2.12-chain landed
between the two reads) rather than the same number restated. **Not
re-diagnosed at the bar level here** — that partition (`missing_events` /
`meter_wrong` / `extra_events` / `dots` / `duplicate_rest_detection` /
`voices_merged_or_chord_split` / `other`) is `benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md`
§13's job and is already done; this diagnosis works one layer down, at the
NOTEHEAD the bar-holdout bar is made of, which is where the brief pointed
("the ownership drops are mostly correct, so the missing notes come from
elsewhere").

`bar_does_not_add_up` is the largest bucket by 4.5x, but it is a **shell**,
not a root cause: 2.8 holds out a WHOLE bar the moment any one voice in it
fails to sum to the meter, so one bad note anywhere in a bar removes every
correctly-read note beside it. The 15,406 notes in this bucket were mostly
never dropped by THIS diagnosis's own funnel — they are notes that reached
`cell.detections` successfully and were then discarded en masse at render
time because their bar-mate failed a DIFFERENT check. Chasing it further is
chasing §13's own funnel restated; this diagnosis instead asks which
NOTEHEAD-level refusal is worth fixing first, among the ones §13 does not
cover.

## 2. Picking the "top cause" among what is actually unresolved

Of the four largest buckets:

* `not_a_notehead:too_narrow` (3,401) — **already measured, at whole-movement
  scale it is worth re-checking, but the mechanism is not new** (§4).
* `duration_narrowed:beams_ambiguous` (3,333) — the one this brief's own
  context named as "the next refusal in the funnel." **Fresh, mechanism
  traced below (§3), crops cut for it.**
* `owned_by_another_staff` (2,532) — Sean's o26b pass already adjudicated
  this population (mostly correct de-duplications, 16/19) — the reason this
  diagnosis exists at all is that the missing notes come from ELSEWHERE.
  Not re-opened.
* `not_a_rest:rest_is_a_duplicate_box` (882) — roadmap 2.15's own shipped
  repair, firing as designed.

**`duration_narrowed:beams_ambiguous` is this diagnosis's "top cause"** —
the largest bucket that is both fresh (no prior measurement on this
document) and actionable (a decision this record's own stages can reach,
not an already-closed question). The 12 crops (§5) are cut for it.

## 3. Mechanism: `duration_narrowed:beams_ambiguous`

**What the decision sees.** `adjudicate_duration` (`tools/omr/staged/
adjudicators/rhythm.py:735`) composes a note's length from its head class,
the beam strokes over it, its flags, and its dots. Where a beamed note's
stroke count is a RANGE rather than a single number — `_beam_levels`
(`rhythm.py:366`) returns `(certain, possible)` and `possible > certain` —
the verdict is `Ruling.narrow(...)`, reason `beams_ambiguous`, and EXPORT
refuses to write it (CLAUDE.md §4a: EXPORT "refuses to argmax a narrowing").
Every one of the 3,333 `duration_narrowed` refusals on this record carries
this ONE reason — there is no other duration-narrowing reason on this
document.

**Twenty examples pulled** (spread <=3/page across pages 0-6, `probe/out/
funnel.json["examples"]["duration_narrowed:beams_ambiguous"]`), each with
the full `adjudicate_duration` `detail` block:

| | count | of 20 |
|---|--:|--:|
| `stems_attached == 0` | 15 | 75% |
| `beam_evidence == "none_over_this_note"` | 12 | 60% |
| `beam_evidence == "read"` | 8 | 40% |
| candidates offered | always exactly 2 (one case: 3) | |

**The mechanism, traced through `_stem_joined`/`_beam_levels`
(`rhythm.py:165-218`):** a note joins a beam stroke via its OWN STEM, not
its notehead centre (CLAUDE.md §10's own convention, `[C12]` in
`docs/engraving-conventions.md`: *"a beam stroke runs from the FIRST stem
it joins to the LAST, and a stem stands at the SIDE of its notehead"*).
`_stem_joined` first asks which `Q.STEM` rows overlap this note's OWN head
box (`attached`); with none, it returns `([], [])` outright — this is
`stems_attached=0`, 75% of the sample. `_beam_levels` then falls back to a
looser x-proximity test (`x0-pad <= x_center <= x1+pad`), which is why
`possible` is still >0 even with zero stems: a beam stroke belonging to a
NEIGHBOURING note, close enough in x, becomes a "possible" (not "certain")
reading for THIS note too — `beam_evidence="none_over_this_note"` is
exactly this case (no beam directly over the note, but one nearby). Where a
stem IS attached (`beam_evidence="read"`, 40%), the ambiguity survives
anyway when the STROKE COUNT itself is uncertain — a broken/thin beam mark
can register as 1 stroke to `certain` and 2 to `possible`.

**This is NOT a missing adjudication rule — the fix for this EXACT
convention already shipped, measured on the OTHER plate.** `[C12]`'s own
FINDINGS entry (`docs/engraving-conventions.md` line 586) records that the
stem-join code (`_stem_joined`, `_beam_levels`, the same functions read
above) was measured on `beethoven-sym5-mvt4` (Litolff, the MERGING plate)
and took that document's `narrowed` count **147 -> 29** — "the stem tier is
the whole gain." That fix is on `main` today, is the code this record's
3,333 refusals are running through right now, and is doing essentially
nothing for them: 75% of THIS document's ambiguous notes present zero
stems to join in the first place. **The gap is not in ADJUDICATE — it is
in GATHER**, specifically `Q.STEM`'s yield on Breitkopf (the SHATTERING
plate, CLAUDE.md §10): a shattered scan breaks a continuous stem into
fragments the CV line reader (`gather_cv_lines`) either never detects or
detects in pieces too short to overlap a head's box. This also explains the
`beam_evidence="read"`-but-still-ambiguous 40%: the SAME shattering that
breaks stems also breaks beam strokes into an uncertain number of pieces.

**Is EVALUATE or INFER close to reaching it?** `consequences.
reconcile_duration` (EVALUATE) re-reads a NARROWED duration only where
EXACTLY ONE admitted candidate makes its enclosing bar's voice sum land the
meter precisely, and refuses outright the moment more than one reading
would land it (CLAUDE.md §4a: "certain about the GROUP, silent about the
MEMBER"). Several of the 20 examples share a CELL with another
simultaneously-narrowed note (e.g. `glyph/0/0/0/1/6` and `glyph/0/0/0/1/15`,
both cell 1 of `staff/0/0/0`) — exactly the case `reconcile_duration`'s own
docstring says must stay silent, because the search space multiplies and
"it must never condemn the cheapest member." **INFER** carries two rules
built for this shape of ambiguity, `collapse_duration_by_column` and
`collapse_duration_to_barline` (CLAUDE.md §4c) — but both are **default
OFF and "never print-checked"** (roadmap 2.3). Neither is silently reaching
this refusal today; both are the obvious next lever, and both are
explicitly gated off pending print verification — which this diagnosis does
not attempt (that is a fix, not a read).

**Governing convention:** `[C12]`, `docs/engraving-conventions.md` line
586, status MEASURED HERE, code `rhythm.py:165` `_stem_joined`, `:366`
`_beam_levels`. `adjudicate_duration`'s own `checked_by=` declaration
(`rhythm.py:688`) cites only the bar-sum control, by a free-text string —
**it does not cite `[C12]`'s registry id**, so the convention that governs
this exact decision is (like 44 of the registry's 114 entries) invoked in
comments but not wired to the decision's own declared checks.

## 4. Second-largest bucket, re-examined rather than re-diagnosed: `not_a_notehead:too_narrow`

`_too_narrow` (`notehead_precision.py:287`) refuses a `noteheadBlack*` box
under `TOO_NARROW_MIN_SPACES = 1.0` staff space wide. This is **already
measured on BOTH plates**, including Breitkopf specifically:
`benchmarks/omr-notehead-width-2026-09/FINDINGS.md` §3 — "ZERO of 103
confirmed noteheads is flagged, on both plates" (0/29 Litolff, 0/74
Breitkopf), while it correctly catches 41 of 63 confirmed NON-noteheads
(73% on Breitkopf). That measurement was on a 4-page sample per document
(Litolff pp.1-4, Breitkopf pp.0-3); this funnel's 3,401 is whole-movement
(27 pages), roughly 3x the page count at a similar per-page rate — **no
crops were cut for this bucket in this session**, on the reasoning that
cutting new crops to re-confirm a filter already measured at 0/103 false
positives, on the exact document, is not this diagnosis's most valuable
use of Sean's time (rule 5: reach before accuracy, and this reach is
already established). If a future session wants the whole-movement rate
re-confirmed, `probe/out/funnel.json["examples"]["not_a_notehead:too_narrow"]`
already carries 12 example subjects with page-frame boxes, ready to crop
with no new record read.

## 5. Crops — `duration_narrowed:beams_ambiguous`, 12 of 12 cut

`benchmarks/omr-missing-notes-2026-09/out/print/beams_ambiguous-*.png` +
matching `.json` sidecars, `VERDICT_none_yet: null`, plus
`funnel-crop-manifest-beams_ambiguous.json`. Banded style
(`crop_losers_2_6b.py`'s own convention): the FILED staff drawn as a shaded,
labelled blue band with thick lines; the bar's own `Q.CELL_BOX` frame
bracketed thin blue; the SUBJECT glyph corner-bracketed thick red; the two
(or three) candidate readings, the beam/stem evidence, and the stem/YOLO
counts printed above the crop in one line each. Spread across pages 0-6
(pages after 6 were not sampled — the example cap stopped there).

**One caveat found while cutting these, named rather than hidden**:
`beams_ambiguous-1-0-0-0-12.png`'s cell box is unusually tall (399-780 px
against a 27px staff spacing — reaching well past this staff's own last
line), and the flagged glyph sits at the very bottom of that padded cell,
close to the next staff down. CLAUDE.md §10: "the measure cell is padded 4
spaces (6 where the neighbour is far)... on a conductor's page that reaches
the next staff's ink." This crop is filed on the staff its subject key
names, and the band drawn IS that staff — but the ink itself sits near the
boundary a `glyph_owner` contest could equally be asked about. Duration
narrowing and cross-staff ownership are separate, stackable questions on
the same ink; this crop does not resolve which one, if either, is at fault
for THIS note, and none of 2.6c's open ownership work was re-opened here.

## 6. Recommended roadmap item

The next lever is not another ADJUDICATE rule on this document — `[C12]`'s
rule is already shipped and doing everything the geometry gives it. The
open question is upstream, at GATHER: how much of Breitkopf's `Q.STEM`
population is actually there to join. That has to be MEASURED before any
rule change (rule 5: reach before accuracy) — a rule refinement built on a
guess about why stems are missing would be exactly the "guessing lives in
INFER and is labelled" trap (rule 6) if it tried to live in ADJUDICATE
instead.

| item | what | status |
|---|---|---|
| 2.17 | Measure `Q.STEM`'s GATHER yield on Breitkopf's beamed noteheads specifically (rows-per-beamed-cell, Litolff vs. Breitkopf, on the `stems_attached==0` population `duration_narrowed:beams_ambiguous` names — 75% of it on this document, `benchmarks/omr-missing-notes-2026-09/`) before any ADJUDICATE or GATHER change; then, ONLY if the plate difference confirms a GATHER-side (not join-tolerance) shortfall, print-check a handful of the `stems_attached==0` crops to see whether a stem is genuinely printed and undetected, versus genuinely absent (an unstemmed head narrowed for an unrelated reason) | PROPOSED, not built |

Stage: **diagnostic / GATHER-reach**, not ADJUDICATE/EVALUATE/INFER — the
brief's own question ("does the answer follow, or is it merely best") does
not yet apply, because it is not yet known whether the INPUT (`Q.STEM` rows
near these heads) exists at all on this plate. Answering that is what
`gather_coverage`-style reach counting is for. Gate: a two-page re-gather
(NOT the whole movement — Sean, 2026-09-28: no whole-work runs while
reading/deciding is unsettled) on a Breitkopf page inside this sample and
the equivalent Litolff page, comparing `Q.STEM` rows per beamed cell; if
Breitkopf's yield is materially lower, name it as a GATHER gap and stop
there for this item (a GATHER change needs its own priced roadmap item,
CLAUDE.md §6b: "a GATHER change needs two full re-gathers"); if the yield
is comparable, the gap is in `_stem_joined`'s tolerance or `gather_cv_lines`'
placement precision on shattered ink, not its recall, and the next step
is a join-tolerance measurement instead.

This also names the benchmark directory this FINDINGS lives in
(`benchmarks/omr-missing-notes-2026-09/`), per CLAUDE.md rule 9.

## 7. What this session could NOT do / did not do

* Did not re-diagnose `bar_does_not_add_up` at the bar level — already done
  in `omr-bar-sum-holdout-2026-09/FINDINGS.md` §13, on an EARLIER record
  (2026-09-23 gather, before 2.6c/2.15/2.12-chain); the two funnels are not
  directly comparable row-for-row and this session did not attempt to
  reconcile them beyond noting the bars-held-out fraction moved 77.9% ->
  79.5%.
* Did not investigate `staff_not_identified` (867), `written_value_fits_no_note`
  (132), or `not_a_notehead:is_a_clef` (32) — smaller buckets, out of
  budget this session.
* Did not close the 110-row accounting residual (§1) — named, not chased.
* Did not cut crops for `not_a_notehead:too_narrow` (§4) — judged lower
  value than confirming the fresher `beams_ambiguous` cause, given the
  filter's own 0/103 measured cost on this exact document pair.
* Did not touch `tools/omr/staged/` — this is a diagnosis, not a fix.
* Did not re-gather or re-adjudicate anything; did not run a whole-movement
  export (the `to_musicxml` call in `probe/notehead_funnel.py` is a
  read-only re-export of an EXISTING record for census purposes, the same
  technique `reexport.py` already uses — no `.musicxml` file was written
  to disk, and no A/B was run).

## 8. Files

```
probe/notehead_funnel.py           the ONE record read; dumps out/funnel.json
probe/crop_beams_ambiguous.py      cuts the 12 crops from out/funnel.json, no record read
probe/out/funnel.json              every count and example this FINDINGS cites
probe/out/funnel.log               the three run logs (control passing each time)
out/print/beams_ambiguous-*.png    the 12 crops + .json sidecars, VERDICT_none_yet: null
out/print/funnel-crop-manifest-beams_ambiguous.json
```

## 9. ROADMAP 2.17 -- the GATHER-reach measurement, and the priced fix that does not pay for itself (2026-09-28)

PATH: STAGED. Answers roadmap 2.17 exactly as scoped: measure `Q.STEM`'s
GATHER yield on Breitkopf's beamed noteheads specifically, Litolff vs.
Breitkopf, on the `stems_attached==0` population `duration_narrowed:
beams_ambiguous` names, BEFORE any ADJUDICATE or GATHER change; then, only
if the plate difference confirms a GATHER-side shortfall, print-check a
handful of crops.

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

Assumes CLAUDE.md SS10's stated stem/beam conventions (a stem stands at the
side of its head; a beam runs stem-to-stem) without re-asking Sean this
session. Falsified by a crop where Sean says a flagged "stem-gap" example's
own ink shows no stem was ever printed there. NOT CONFIRMED with Sean.

### 9.1 Step 1 -- the FULL-POPULATION measurement (no re-gather)

The prior session's own mechanism section (SS3) sampled 20 examples and
reported "75% of the sample" carry `stems_attached==0` -- true, but a
20-row sample cannot separate "the cell has literally nothing" from "the
cell has stems, just not this note's". This session re-asks the SAME
question over the WHOLE `Q.DURATION` population of both acceptance
records (`library/_shared-records/beethoven5-litolff-mvt1-whole-20260928.
record.json`, `.../brahms1-breitkopf-mvt1-whole-20260928.record.json`,
both provenance `c19cbca7`, the SAME commit -- a fair A/B), read ONCE each
via `record_io.load_record` inside `probe/stem_yield.py`. No re-gather, no
re-adjudicate, no code change under `tools/omr/staged/`.

**Per-CELL yield, every beamed cell (has >=1 `Q.BEAM_STROKE` row from
either reader):**

| | Litolff | Breitkopf |
|---|--:|--:|
| beamed cells | 1,726 | 3,886 |
| beamed cells with ZERO `Q.STEM` rows at all | 139 (8.1%) | 432 (11.1%) |

At the whole-CELL level the two plates are close -- Breitkopf's rate is
higher but not dramatically so. **The cell-level number alone does not
show the shortfall the prior sample suggested.**

**The population roadmap 2.17 actually names** -- every `Q.DURATION`
verdict standing as `narrowed`/`beams_ambiguous` with `detail.
stems_attached==0` -- split three ways, the third of which the prior
session's 20-row sample could not distinguish: does the cell have ZERO
stem rows at all, or does it have stems that simply are not near THIS
head (within one notehead width of its own x-centre -- `_stem_joined`'s
own `_boxes_overlap` test has ZERO tolerance, so "near" here is a
generous stand-in for "a real join-tolerance candidate exists")?

| | Litolff (n=640) | Breitkopf (n=2,102) |
|---|--:|--:|
| cell has ZERO stem rows | 138 (21.6%) | 432 (20.6%) |
| cell has stems, NEAREST within 1 notehead width (join-tolerance candidate) | 354 (55.3%) | 592 (28.2%) |
| cell has stems, NEAREST over 1 notehead width away (no local candidate) | 148 (23.1%) | 1,078 (51.3%) |
| **no local candidate at all (empty + far)** | **286 (44.7%)** | **1,510 (71.8%)** |

**This is the plate difference roadmap 2.17 asks for, and it is real, but
it is not the one the prior sample described.** The "cell is literally
empty" rate barely differs (21.6% vs 20.6% -- Breitkopf is not even
higher). What differs is what happens when the cell is NOT empty: on
Litolff, a non-empty cell's nearest stem is usually right there (354 of
502, 70.5% -- a genuine join-TOLERANCE question, consistent with `[C12]`'s
own fix already working well on this plate, 147 -> 29 narrowed). On
Breitkopf, a non-empty cell's nearest stem is usually nowhere near this
note (1,078 of 1,670, 64.6%) -- this note's own local ink produced no
accepted candidate even though OTHER notes in the same (wide) cell did.
Combined with the truly-empty cells, **71.8% of Breitkopf's
`beams_ambiguous`/`stems_attached==0` population has no local stem
candidate at all, against 44.7% on Litolff.** That gap -- not the raw
"cell empty" rate -- is roadmap 2.17's GATHER-side confirmation: this
IS materially a plate-specific reach shortfall, not (mainly) a
join-tolerance one, and it warrants the print check.

Reproduce: `probe/stem_yield.py --record <path> --label <l> --out
<out.json>` (each record read exactly once; ~4-16s per record, no
re-gather).

### 9.2 Step 1b -- print-check: crops of the "no local candidate" population

`probe/crop_stem_gap.py` cuts crops from the SAME geometry `stem_yield.py`
already pulled off its one record read (no second record read), in the
banded style `crop_beams_ambiguous.py` established. 12 Breitkopf + 12
Litolff crops, spread one/two per page across pages 0-6 (Breitkopf) and
2-7 (Litolff), `benchmarks/omr-missing-notes-2026-09/out/print/
stem_gap-<label>-*.png` + `.json` sidecars, `VERDICT_none_yet: null`.

Read by eye (NOT Sean-adjudicated -- flagged, not claimed):

* **`stem_gap-breitkopf-2-0-0-3-3.png`** (page 2, 8.56 notehead widths to
  the nearest accepted stem): the flagged notehead has a clearly PRINTED
  stem descending from it -- visible, curving slightly at its foot -- that
  the CV opening never accepted; the cell's two accepted stems belong to
  two OTHER notes several notehead-widths to the left. **This is a clean
  positive: ink genuinely printed, genuinely undetected** -- the
  GATHER-reach fault roadmap 2.17 asks about.
* **`stem_gap-breitkopf-1-0-2-0-17.png`** (page 1, a dense fused 16th-note
  passage, `n_cell_stem_rows=8`, `cv_beams=4`): the flagged note sits
  inside a run where stems, beams and noteheads visibly fuse into solid
  black regions -- consistent with `benchmarks/omr-stem-ink-2026-09`'s own
  census ("a component EXISTS and is the wrong SHAPE," the dominant
  Breitkopf failure at 74%), not with ink being absent.
* **`stem_gap-breitkopf-0-0-0-1-6.png` / `-0-0-0-1-15.png`** (page 0, two
  adjacent glyph indices in the SAME cell, stacked canonical boxes
  touching exactly at the join, `yolo_beams=2 cv_beams=0`): zoomed
  (`fitz` render at the recorded `bbox_page_px`, +/-80px pad, 6x), this is
  **NOT a notehead with a missing stem at all** -- the ink is a small
  rounded head with a thin curved hooked tail, the classic shape of an
  OLD-STYLE ENGRAVED EIGHTH REST, sitting on the top line beside a slur
  end and the word "tenuto". The detector's own class for this glyph
  (`noteheadBlackInSpace`, `NOT_a_notehead`/`REST` never fired) is a
  **misclassification, not a stem-detection gap** -- a different fault
  (detector/notehead-precision, `notehead_precision.py`'s domain, which
  this session was told not to touch: another lane owns
  `ownership.py`/`notehead_precision.py`). Flagged rather than fixed:
  **not every "stem gap" example is a stem-gap example** -- some of the
  71.8% "no local candidate" population is this same class-confusion
  fault wearing the `beams_ambiguous` label instead of `duration_narrowed`
  because the class read as a NOTEHEAD in the first place. Not quantified
  this session (would need a hand pass over the 54 gathered crop
  candidates, out of budget); named as an open question for whoever picks
  up `notehead_precision.py` next, not claimed as sized.

**Net read: the print check is MIXED but net POSITIVE for the GATHER-reach
hypothesis** -- at least one clean case of printed-and-undetected ink
(2-0-0-3-3), plausible support from a fused-ink passage (1-0-2-0-17), and
one case that turned out to be an unrelated bug wearing this funnel's
label (0-0-0-1-6/15). The plate-level population number (SS9.1, 71.8% vs
44.7%) stands regardless of how any one crop reads; Sean has not
adjudicated any of these 24 crops and this is not claimed as his
verdict.

### 9.3 Step 2 -- the one candidate repair ALREADY BUILT, priced at the FILE level for the first time

The obvious lever is not new: `OMR_STEM_STROKE` (`line_detection.py`
`_column_stroke_bands`) was built and measured in
`benchmarks/omr-stem-stroke-2026-09/` for exactly this failure mode -- "a
component EXISTS and is the wrong SHAPE," reading a stem from a COLUMN
PROFILE (bands columns that AGREE about where a vertical run starts and
ends) rather than from a connected component, so a stem fused to its own
notehead or to a beam no longer gets measured at the fused blob's width.
That benchmark's own chronicle entry says explicitly: **"no effect on a
FILE has been measured"** -- the flag is default OFF, gated behind no
umbrella (stays OFF per `docs/flags-2026-09.md` SS1, re-decided at roadmap
2.4a), because its effect on the exported CENSUS was never priced, only
its effect on raw stem RECALL.

This session prices it, for the first time, on the EXACT population
roadmap 2.17 names: a base-vs-arm re-gather of Breitkopf pdf page 1 (the
count page), `--no-surya --no-ocr --no-roster` (this question needs
neither), scan weights
(`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`), each arm its
own `--out` dir (`out/stem-stroke-arm/{base,arm}/`), ~85s each:

| | base | arm (`OMR_STEM_STROKE=1`) | delta |
|---|--:|--:|--:|
| `Q.STEM` rows | 792 | 1,242 | **+450 (+56.8%)** |
| `Q.BEAM_STROKE` rows | 924 | 972 | +48 |
| `duration_narrowed:beams_ambiguous` (narrowed count) | 177 | 180 | +3 |
| of those, `stems_attached==0` | 85 | 78 | -7 |
| **notes written** | **226** | **222** | **-4** |
| rests written | 123 | 119 | -4 |
| `notes_not_written[duration_narrowed]` | 104 | 104 | **0 (unchanged)** |
| `notes_not_written[bar_does_not_add_up]` | 529 | 535 | **+6 (worse)** |
| `bars_held_out_sum` | 85 | 86 | +1 (worse) |
| beams (exported) | 169 | 198 | +29 |

**The raw-recall claim reproduces exactly as its own FINDINGS predicted
(+56.8% stem rows, in the same range as the prior Litolff/Breitkopf-scale
gains).** But at the FILE level, on the EXACT page and EXACT population
this roadmap item was opened to fix, the flag is a
**wash-to-slightly-negative**: `duration_narrowed` (the count that
includes `beams_ambiguous`) does not move at all -- every one of the 450
recovered stems either belongs to a note that was already correctly
decided, or attaches without resolving that note's own certain/possible
gap -- and the exported note count goes DOWN by 4 while bar-sum
hold-outs go UP by 6. **This is a control that can fail (CLAUDE.md rule
7), and here it failed**: turning the lever on does not pay for itself on
this page.

Per CLAUDE.md rule 5 ("reach before accuracy, and print before default;
no default flips on agreement with our own reading") and rule 6 ("connect,
never guess"), this result does NOT license flipping `OMR_STEM_STROKE` on,
building a new join-tolerance change, or touching `line_detection.py`'s
filters on the strength of this session's evidence alone -- the ONE
available, already-built candidate repair was connected and measured
honestly, and the honest answer is that it does not close this funnel.
Inventing a NEW filter change (a length floor tweak, a join-tolerance
pad) without further per-example evidence would be exactly the "guessing
lives in INFER and is labelled" trap rule 6 warns against, given the
crops in SS9.2 already show the population is NOT uniform in cause (one
of four read crops was an unrelated detector bug, not a stem gap at all).

Reproduce: `probe/compare_arm.py <label> <rec.json>` reads a record once
via the same `export.Record`/`to_musicxml` path `notehead_funnel.py`
uses; `out/stem-stroke-arm/{base,arm}.compare.json` are the two runs'
numbers above, `{base,arm}.log` the gather logs. The two ~23 MB
single-page records themselves were not committed (CLAUDE.md's own
discipline of committing derived summaries, not records); they are
reproducible in ~85s each from the commands named in `{base,arm}.log`'s
own argv.

### 9.4 Conclusion and roadmap disposition

* The plate difference IS real and DOES confirm a GATHER-side (not
  mainly join-tolerance) shortfall on Breitkopf specifically, at
  population scale (71.8% vs 44.7% "no local stem candidate" among the
  narrowed population) -- roadmap 2.17's own gate for proceeding to a
  print check.
* The print check is genuinely mixed: real printed-and-undetected ink
  confirmed in at least one case, but ALSO an unrelated detector
  class-confusion fault (a rest misread as a notehead) hiding inside the
  same population -- named, not sized, this session.
* The one already-built candidate repair (`OMR_STEM_STROKE`) was priced
  at the file level for the first time (closing that flag's own long-
  standing open question) and does NOT close this funnel -- flat on
  `duration_narrowed`, slightly negative on the exported census.
* **No code under `tools/omr/staged/` or `tools/omr/line_detection.py`
  was changed this session.** No flag default was flipped. This is a
  MEASUREMENT delivering the answer roadmap 2.17 asked for
  ("only if... print-check... versus genuinely absent") plus one
  additional, unscoped-but-free measurement (the file-level pricing of
  the one candidate fix) -- not a BUILT repair, because the repair that
  was tried does not work and inventing another was judged (rule 6) to
  need more per-example evidence than this session's budget allowed.
* Next lever, for whoever picks this up: (a) size the detector
  class-confusion fault SS9.2 flagged inside this same population
  (belongs beside `notehead_precision.py`, out of this session's fence);
  (b) if that is sized and subtracted, re-ask whether the REMAINING
  genuine stem-gap population still shows the 71.8%-vs-44.7% split, since
  right now that number is not yet cleaned of the class-confusion cases.

### 9.5 Files

```
probe/stem_yield.py                     Step 1 -- the full-population, per-cell/per-note
                                         measurement, two records each read ONCE
probe/out/stem_yield_litolff.json       Litolff's numbers + 12 crop-geometry examples
probe/out/stem_yield_breitkopf.json     Breitkopf's numbers + 54 crop-geometry examples
probe/crop_stem_gap.py                  Step 1b -- crops of the "no local candidate" population
out/print/stem_gap-breitkopf-*.png(.json)  12 Breitkopf crops, VERDICT_none_yet: null
out/print/stem_gap-litolff-*.png(.json)    12 Litolff crops, VERDICT_none_yet: null
out/print/stem-gap-crop-manifest-{breitkopf,litolff}.json
probe/compare_arm.py                    Step 2 -- reads a record once, reports the
                                         census both `stem-stroke-arm/*.compare.json` cite
out/stem-stroke-arm/{base,arm}.log      the two one-page gather runs (argv, timing)
out/stem-stroke-arm/{base,arm}.compare.json  the file-level pricing table (SS9.3)
out/stem-stroke-arm/{base,arm}/out.musicxml(.coverage.json)  the two exports compared
```

## 10. ROADMAP 2.18 -- `beams_ambiguous`: the beam column test was blind in Y, and the head's own stem direction existed and was not read (2026-09-29)

PATH: STAGED. Question from the brief: `OMR_STEM_STROKE` added +450
`Q.STEM` rows on Breitkopf p1 and `duration_narrowed` did not move
(104 = 104), and ~half the narrowed heads HAVE a stem attached -- so what
between the stem/beam readers and the duration decision is not connecting?

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

`[C12]` and CLAUDE.md SS10: a beam runs between STEM ENDS, a stem stands at
the side of its head, stems up -> right, down -> left. So a note's beams
stand on the side its stem points to, and a stroke across the head's centre
from its own stem is not one of them. Falsified by a crop where Sean reads a
RED-X (far-side) stroke as the bracketed note's own beam (a kneed or
cross-staff beam with stems pointing both ways would be the shape to look
for). NOT CONFIRMED with Sean -- the eight crops below are for him.

### 10.1 Population and the one re-gather

One re-gather of Breitkopf `317803` pdf p1 on this tree (`6309396a`,
`dirty False`, `--no-surya --no-ocr --no-roster`, scan weights, 84 s):
`duration: beams_ambiguous` **177** narrowed verdicts, identical to the 2.17
base. `probe/beams_mechanism.py` rebuilds the record's GATHER rows
(`review.rerun.rebuild_gather`), re-derives every head's inputs through
`adjudicate_duration`'s own helpers, and its CONTROL -- the re-derived
`(certain, possible)` equals the verdict's own detail -- passes **177 of
177**. It then asks EXPORT (`review.rerun.export_with_subjects`, whose own
control is that the per-subject refusals sum to `notes_not_written`) what
became of each head:

| what EXPORT did with the 177 | n |
|---|--:|
| refused `duration_narrowed` -- the population that costs notes | **104** |
| refused earlier as `not_a_notehead:too_narrow` | 58 |
| refused `not_a_notehead:clipped_fragment` / `belongs_to_a_nearer_staff` | 5 / 1 |
| written (EVALUATE/INFER resolved it) | 9 |

### 10.2 The ranked mechanism table

Each stroke that is POSSIBLE but not CERTAIN for a head is labelled by where
it stands against the head's OWN stem (`Q.STEM_DIRECTION`, decided), and the
head takes the class of its possible-only strokes (first match wins;
`probe/beams_mechanism.py:head_class`):

| class | the 104 | all 177 |
|---|--:|--:|
| **A** every possible-only stroke is on the FAR side of the head from its own read stem | **39** | 45 |
| **E** a stroke on the stem side, within the stem's reach, that the read stem does not touch (edge overshoot / short stem / beamlet) | 25 | 26 |
| **C** no stem attached to the head (2.17's GATHER reach) | 19 | 79 |
| **B** possible-only strokes on the far side OR more than 1 space past the read stem's tip (the next staff's beam, through the cell's 4-space pad) | 16 | 22 |
| **D** stem attached but its direction abstained (`stems_disagree`) | 5 | 5 |
| total | **104** | **177** |

Stroke labels over the 104: `wrong_side` 69, `stem_side_stem_misses_stroke`
30, `beyond_stem_tip` 26, `direction_unread_no_stem` 18,
`direction_unread_stem_attached` 9, `stem_side_no_stem_attached` 5. And **29
of the 104 carry a far-side stroke among their CERTAIN levels too** -- the
same fault, on the side that decides wrongly instead of narrowing.

**Why `OMR_STEM_STROKE` could not move the count** (the brief's puzzle, part
b): class C -- the stemless heads, the only ones more stems could help -- is
79 of the 177 but only **19 of the 104**. Sixty of the stemless narrowed
heads are refused as NOT NOTEHEADS before their duration is asked (consistent
with SS9.2's rest-read-as-a-notehead crop). Part a: the heads that HAVE a
stem are narrowed mostly by strokes that are not theirs (A + B = 55 of 104).

**The mechanism of A (and half of B)**: `_beam_levels` counts a stroke by
its x-range alone -- `x0 <= x_center <= x1` is CERTAIN, within one head
width is POSSIBLE -- wherever it stands vertically. On a two-voice staff the
other voice's beam under a stem-up head counts as this note's; hairpins and
slurs the detector boxes as `beam` do too; through the pad, so does the next
staff's beam. The head's own stem direction was decided three decisions
earlier (`adjudicate_stem_direction`, `stem_projection` off its own stem)
and read by `adjudicate_duration` only inside `_flag_direction`, which by
design changes no duration -- **the value existed and nothing read it**.
Measured on this record over every head with a decided direction, stroke
centre distance from the head centre in staff spaces, positive = the stem
side:

| | n | on the far side (< 0) | in [+2, +4) |
|---|--:|--:|--:|
| strokes the head's own stem JOINS (`_stem_joined`) | 407 | 12 | 294 |
| strokes merely in its column (+/- one head width), not joined | 707 | **270** | 81 |
| the attached stems' own tips | 615 | 0 | 410 in [+3, +4) |

### 10.3 The fix (ADJUDICATE, a connection -- it FOLLOWS, it is not BEST)

`rhythm._own_stem_side` reads `Q.STEM_DIRECTION` where it is DECIDED with
reason `stem_projection` (read off THIS head's stem; a `beam_mate` direction
is borrowed from the very strokes it would be choosing among, so it is not
used), and `rhythm._on_stem_side` drops every stroke whose centre is across
the head's centre from that side -- from BOTH the certain and the possible
count. No own direction -> no side -> every stroke stays, exactly as before
(additive; `cannot tell` stays `cannot tell`). The duration's detail carries
`beam_side` and `beams_far_side`; the direction verdict is in its basis;
`Q.STEM_DIRECTION` joins `composed_from`. Tests: `tools/omr/tests/
test_staged_duration.py::TestABeamLiesOnTheStemSIDEOfItsHead`, run RED
against the unrepaired tree first (6 of 6 failed), with the positive control
-- the SAME stroke moved to the stem side still narrows -- and the no-stem
control that keeps the old reading. Gate: `pytest -m "not slow"` 3,590
passed; `staged.check` TOTAL 249.

Stage: this is forced, given a stem read off the head, so it is ADJUDICATE
and not INFER. Not a GATHER change -- no row is added or moved -- so a
re-decision of the one frozen record is the right instrument.

### 10.4 Priced on p1 (`probe/price_stem_side.py`, same frozen gather)

The OFF arm (`_own_stem_side` forced to `(None, None)`) is the control and
it can fail: it reproduced the record's verdicts N/N and wrote the
byte-identical MusicXML (PASSED).

| | OFF (pre-2.18) | ON (2.18) | delta |
|---|--:|--:|--:|
| duration verdicts changed | -- | 95 | |
| standing `narrowed:beams_ambiguous` | 161 | 123 | -38 |
| `notes_not_written[duration_narrowed]` | **104** | **66** | **-38** |
| `notes_not_written[written_value_fits_no_note]` | 14 | 1 | -13 |
| `notes_not_written[bar_does_not_add_up]` | 528 | 568 | +40 |
| bars held out by the sum | 85 | 85 | **the SAME 85 bars** (none newly held, none released) |
| notes written | 224 | 235 | +11 |
| `<note>` in the file | 444 | 455 | +11 |
| heads with `levels_certain` >= 5 (a 64th or shorter) | 28 | 7 | -21 |

Every one of the 85 held bars is in system 0 (the only system with a meter
in force on this page; `bars_with_events_without_a_meter` 103), so the
notes the rule resolves there land in bars already held out for other
reasons, and the +11 written notes are all in system 1, whose bars nothing
judges. **So the bar sum cannot vouch for these values and the crops have
to.** My eye over the 28 changed durations in written bars (NOT Sean's
verdict): **8 refused -> right, 8 wrong -> right, 4 value unchanged, 1
wrong -> refused, 3 wrong -> still wrong, 4 refused -> wrong, 0 right ->
wrong.** The four new wrong notes are two eighths whose FLAG the detector
never boxed (with the far-side strokes gone nothing marks the stem and the
head falls to its own value, a quarter -- the pre-existing *no mark read ->
head value* path, now reached by these two) and two heads whose stem-side
strokes come from the staff above through the pad (class B: 0.0625, 0.25).
And two of the "refused -> right" (`glyph/1/1/3/1/27`, `/31`) are TWO
detections of ONE printed head, so the second copy now reaches the file
where the narrowing used to hide it -- a duplicate-box fault upstream of
this rule, which the narrowing had been masking.

### 10.5 Crops for Sean

`out/print/beams-2.18-01..08.png`, manifest `beams-2.18-manifest.json`,
every row `VERDICT_none_yet: null`. Class A only, both systems, both stem
directions, cut by `probe/crop_stem_side.py` at 600 dpi: the filed staff is
a shaded labelled band over its own `Q.STAFF_LINES`, the head is bracketed
thick red, GREEN = its own read stem, BLUE = a kept stem-side stroke, RED X
= a dropped far-side stroke, a staff-space ruler down the left; the frame
control passed on all eight. #07 (`glyph/1/1/3/3/2`) and #08
(`glyph/1/1/8/0/9`) are the two flag-not-boxed cases above, included on
purpose. Question on each: *the printed value of the bracketed note, and is
any RED-X stroke this note's beam?*

### 10.6 What is left, and what this could not do

* **B (16) is the next connection**: a `Q.BEAM_STROKE` row has no staff
  owner. `glyph_owner` contests NOTEHEADS across the 4-space pad; nothing
  asks which staff a STROKE belongs to, so the staff above's beam counts on
  the stem side of an up-stem head. A reach bound off the attached stem's
  tip was considered and NOT built: a shattered stem read short would then
  drop the note's real beam and DECIDE it unbeamed (rule 8).
* **E (25)**: a stem-side stroke within reach that the stem does not touch
  -- the outer-note overshoot, a stem fragment, or a beamlet; genuinely a
  range on this evidence, so it stays NARROWED; `reconcile_duration` / INFER
  are where it belongs.
* **C (19 of the 104)** is 2.17's GATHER reach, and most of the stemless
  population (60 of 79) is not noteheads at all.
* **The flag path**: a note whose flag the detector missed and whose stem
  carries no stroke decides at its head value -- converting *no mark read*
  into *no mark printed*. Pre-existing and not this change's rule, but 2.18
  routes two more notes on p1 into it; named, not fixed.
* One page, one plate. Litolff not re-decided; no whole-movement run (Sean,
  2026-09-28). The -38 / +11 are p1 numbers and the value judgement in 10.4
  is mine, not Sean's.

### 10.7 Files

```
probe/beams_mechanism.py            the ranked table (177 heads, control 177/177)
probe/price_stem_side.py            OFF-vs-ON re-decision of one frozen record
probe/crop_stem_side.py             the eight crops
probe/out/beams_mechanism_p1.json   per-head classes, stroke labels, export fate
probe/out/price_stem_side_p1.json   both arms' census + every changed verdict
out/print/beams-2.18-0{1..8}.png, beams-2.18-manifest.json
```
The p1 record itself (~24 MB) is not committed; it reproduces in ~85 s from
the gather command in 10.1 on `6309396a`.

## 11. ROADMAP 2.18b -- class B (strokes past the stem tip), class E (the stem misses a stroke), and the missed-flag path (2026-09-29)

PATH: STAGED, ADJUDICATE. Same frozen Breitkopf p1 record as SS10, re-decided
on the 2.18 tree (`63247979`) and on this one. Nothing re-gathered.

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

CLAUDE.md SS10: a beam is drawn at the stem's END and runs from the first
stem it joins to the last; a flag hangs from the stem's end. So a stroke
that lies past a head's own read stem tip and that no read stem reaches is
not that note's beam; and a flag box a fraction of a space off a stem is
that stem's flag. Falsified by a crop where a RED-X stroke (below) is the
bracketed note's own beam, or where an ORANGE flag hangs from a different
stem. NOT CONFIRMED with Sean.

### 11.1 The population on the 2.18 tree

`probe/beams_2_18b.py --off` (tolerance 0 is the 2.18 tree exactly; the
control -- re-derived `(certain, possible)` equals every narrowed verdict --
passes 123/123) classifies the **66** heads EXPORT counts as
`duration_narrowed`:

| class | n |
|---|--:|
| C no stem attached (2.17) | 23 |
| E a stem-side stroke within reach that the stem does not touch | 20 |
| B every possible-only stroke lies more than 1 space past the stem tip | 14 |
| B+E both | 4 |
| D the stem's direction is not its own (`beam_mate` / abstained) | 5 |

### 11.2 Class B: what the strokes are, and the fix

Every DETECTOR box among the B strokes touches **zero** read stems; they sit
2-5.5 spaces above the head's own top line or 1.5-2.5 below its bottom line.
On the overlays they are the detector's `beam` class on HAIRPINS and SLURS
(`<`/`>` boxes, the slur arc under a group) and, through the pad, the next
staff's strokes. The two CV B strokes that ARE reached by a read stem (one
by 2, one by 6) belong to real groups -- in one the head's own stem was read
as a 0.33-space fragment.

The manager's second suggestion -- a stroke on the neighbouring staff's
stems belongs there, by `Q.GLYPH_OWNER` -- has **zero reach** here: no B
stroke touches a stem whose head ownership awards to another staff (the
heads on those stems are uncontested). Not built.

**Fix** (`rhythm._beyond_own_stem`): a stroke is not this note's when BOTH
it lies past the tip of the head's own read stem by more than
`STEM_JOIN_TOLERANCE_SPACES` (0.8 of the cell's own staff space) AND no read
stem in the cell comes within that distance of it. The second half is the
guard for a shattered stem read short: a real beam is reached by the other
stems of its group. No own stem, no own direction, or no staff-space unit ->
nothing is dropped.

**And a rule-8 guard, added after pricing.** Built without it, the rule
turned 8 notes in written bars into bare QUARTERS (the strokes were the only
thing over the head, and once they went the stem carried nothing): by eye 3
right, 3 wrong -- two of them printed eighths whose flag no reader read,
which the spurious stroke had been standing in for -- and 2 unclear. Half
wrong, against 10 of 69 (~1 in 7) across every stemmed head the page then
wrote at its head value (the by-eye pass in 11.4, made before the guard). So
where dropping would leave the head with no beam, no possible beam and no
flag, the strokes stay and the reading stays what it was
(`beyond_stem_kept_no_other_mark` on the verdict). Removing an unconnected
stroke may make a note less wrong; it may not make it unmarked.

### 11.3 Class E: measured, NOT a connection fault on this evidence -- refused

The stem-to-stroke gap (larger of the x and y box separations, in spaces)
for every head with a read stem and direction:

| strokes on the stem side, within reach, not joined | n | gaps |
|---|--:|---|
| covering the head's centre (so the join decides nothing) | 101 | 0.00-0.80, continuous |
| possible-only (the E population and its peers) | 36 | 27 in 0.00-0.88, then 1.13-2.13 |

There is no empty interval inside the band the E strokes occupy. A 0.8-space
join tolerance was built anyway and priced (`duration_narrowed` 66 -> 52),
and the eye-check refused it: it made narrowed eighths into sixteenths and
one into a 32nd (`glyph/1/1/10/7/2`, `/11/7/5`, `/3/4/1`, `/3/0/3`). The
overlays say why: many E strokes are a SECOND READING of a beam the head
already counts -- two CV components ~0.5 spaces apart under one printed beam
-- so joining them adds a level that is not on the page. E is genuine
ambiguity on this evidence; the join stays at overlap and E stays NARROWED,
for EVALUATE (`reconcile_duration`) / INFER. The duplicate-stroke reading is
a beam-reader question, named, not sized. `TestTheBEAMJoinIsNOTWidened`
guards it.

### 11.4 The missed-flag path

(a) **A connection fault inside it, fixed.** Every detected flag's nearest
read stem on p1: 0.00 (106 -- attached), **0.01-0.32 (13)**, 1.31+ (15);
**nothing between 0.33 and 1.30**. The 13 were written as quarters with the
flag's own box on the record. `_attached_flags` now attaches within
`STEM_JOIN_TOLERANCE_SPACES` -- 0.8 lies in that empty interval, and it is
also the measured maximum of the 11.3 belonging population, which is why one
constant serves both rules. Flag-only arm: 9 durations change, 4 in written
bars, all 4 right by eye (1.0 -> 0.5 on printed flagged eighths).

(b) **The rest has no cheap witness; sized, left.** After 2.18b, **53**
stemmed black heads are decided at their head value with no beam and no flag
read. A by-eye pass over every one: **6 print a flag no reader read**
(`glyph/1/0/9/5/1`, `/1/1/8/0/9`, `/1/1/8/1/11`, `/1/1/8/3/4`,
`/1/1/9/1/23`, `/1/1/9/3/9` -- ~1 in 9), the rest are quarters (plus a few
non-notes: a bass clef, grace heads). The detector boxes sitting at those
stems' tips do not separate the two (`staff`, `tie`, `slur`, `ledgerLine` on
both), and `Q.INK` persists only a per-cell summary on these records
(`ink_rows` off), so no row on the record says *ink hangs off this stem tip*.
A witness would be a GATHER reader (ink to the right of the stem tip) and
needs its own roadmap item and two re-gathers. Rule 8 is honoured by the
guard in 11.2 not ADDING to this population; the population itself is the
pre-existing *no mark read -> head value* fallback and is not changed.

### 11.5 Priced (`probe/price_2_18b.py`, same frozen gather)

The OFF arm (tolerance 0) is the control and it can fail: it must equal the
2.18 arm committed in `probe/out/price_stem_side_p1.json` -- PASSED.

| | 2.18 (OFF) | flag only | 2.18b (ALL) |
|---|--:|--:|--:|
| `notes_not_written[duration_narrowed]` | 66 | 66 | **56** |
| standing `narrowed:beams_ambiguous` | 123 | 123 | 109 |
| decided by a flag | 81 | 90 | 101 |
| notes written | 235 | 235 | 239 |
| `<note>` in the file | 455 | 455 | 459 |
| `bar_does_not_add_up` | 568 | 568 | 574 |
| bars held out by the sum | 85 | 85 | **85, the same bars** |
| durations changed vs OFF | -- | 9 | 81 |

The 85 held bars are all system 0 again (the only system with a meter), so
the bar sum vouches for nothing here. By eye over the 19 changed durations in
written bars (NOT Sean's verdict): **6 wrong -> right, 3 refused -> right,
5 value unchanged, 4 wrong -> still wrong (closer: 32nds/16ths now 16ths/
eighths, the E duplicate-stroke fault above), 1 refused -> wrong, 0 right ->
wrong.** The new wrong one (`glyph/1/1/9/0/13`, now 0.25) is a printed
flagged eighth whose flag the detector boxed twice, once as `flag16th*`; the
tolerance attaches both and `_attached_flags` takes the max -- a detector
class error that now reaches the file.

After 2.18b the 56: C 23, E 20, D 5, B 6, B+E 2 (the B heads left are the
ones the rule-8 guard keeps).

Tests: `TestAFlagHangsFromItsStemWithinAMeasuredTolerance`,
`TestAStrokeBeyondTheStemTipThatJoinsNOStemIsNotThisNotes` (each with a
positive control; the three fix assertions run RED with the tolerance at 0,
i.e. on the 2.18 behaviour), the rule-8 guard and its control, and the E
guard `TestTheBEAMJoinIsNOTWidened`. Gate: `pytest -m "not slow"` 3,600
passed; `staged.check` TOTAL 249.

### 11.6 Crops for Sean

`out/print/beams-2.18b-01..08.png`, manifest `beams-2.18b-manifest.json`,
every row `VERDICT_none_yet: null`, cut by `probe/crop_2_18b.py` in the 2.18
style (filed staff a labelled band, head bracketed, ruler; frame control
passed on all eight). GREEN own stem, BLUE kept stroke, RED X dropped by
2.18b, GREY X far side (2.18), ORANGE flag read. #01-#03 class B fixed, #04
class B still wrong, #05-#06 flags joined, #07 the 16th-flag regression, #08
a head the rule-8 guard kept narrowed. Question on each: *the printed value
of the bracketed note, and is any RED-X stroke this note's beam?*

### 11.7 What this could not do

* E stays open: the duplicate CV reading of one beam needs the beam reader
  (or a stroke de-duplication in ADJUDICATE with its own measurement), not a
  tolerance.
* The missed-flag witness needs a GATHER reader; not built (11.4b).
* `STEM_JOIN_TOLERANCE_SPACES` was measured on one Breitkopf page. It is not
  re-measured on Litolff or the engraved fixture (whose 22 y-separated
  stem/beam pairs at >= 35 px could fall inside 0.8 spaces on small cells --
  though the beam join no longer uses it, so only flags and the beyond-tip
  rule are exposed).
* One page, one plate, no whole-movement run; the value judgements are mine.

### 11.9 Controls asked for before merge: the engraved page and one Litolff page

No re-gather. `probe/redecide_arm.py` re-decides a saved record with the code
tree it sits in; a copy placed in `git archive origin/main` (`63247979`)
runs MAIN's code on the same record, so base = origin/main, not a
reconstruction of it. The CONTROL: the branch with the tolerance at 0 must
equal main verdict for verdict (outcome, reason, beats, written, dots,
levels) plus the census -- **PASSED on both records.**

| | engraved p0 (`omr-staged-engraved-2026-09/out/engraved-p0.record.json`) | Litolff pdf idx 3 (acceptance record, page-3 rows only) |
|---|--:|--:|
| duration verdicts | 174 | 628 |
| `duration_narrowed`, main -> branch | 0 -> 0 | 36 -> 36 |
| notes written, main -> branch | 73 -> 73 | 381 -> 381 |
| `<note>` in the file | 174 -> 174 | 560 -> 560 |
| durations whose value changed | **0** | **1** |
| heads the beyond-the-tip rule acted on | 0 | 3 (no value change) |
| flags attached | 3 -> 3 | 5 -> 8 |

**Engraved: 0 changed durations, so 0 to check against the Verovio page
truth -- nothing is wrong there.** It is not vacuous for lack of input: the
record carries 126 `Q.CELL_STAFF_SPACE`, 136 stems, 34 beam strokes and 3
flags, so the tolerance was live; every engraved flag already overlaps its
stem and no stroke lies past a tip unreached.

**Litolff: the one change is the 16th-flag fault again.**
`glyph/3/0/7/3/5` 0.5 -> 0.25: the detector boxed ONE mark at that stem
twice, `flag8thUp` and `flag16thUp`; main attached only the overlapping
one, the tolerance attaches both, and `_attached_flags` takes the MAX of
their levels. Same mechanism as Breitkopf `glyph/1/1/9/0/13` (11.5). The
printed value is not settled by the crop (my eye leans eighth); in either
case the reading is a disagreement between two detections of one glyph, and
taking the max is an argmax the stage should not make -- the fix is to
NARROW where attached flags disagree on their level (`beams_ambiguous`-style
candidates), not to revert the tolerance. Named here; NOT built in 2.18b.

Reproduce: `git archive origin/main tools benchmarks/omr-missing-notes-2026-09/probe
| tar -x -C <dir>`, copy `redecide_arm.py` in, then `python3
<dir>/.../redecide_arm.py <record> [--page 3] --arm plain`, and on the branch
`--arm off` / `--arm plain`. Outputs: `probe/out/controls_2_18b/{eng,lit}-{main,off,branch}.json`.

### 11.10 Flags that disagree on their level NARROW (manager decision, rule 8)

**Built.** In `adjudicate_duration`, where the flags attached to one stem
name more than one level (a `flag8th*` and a `flag16th*` box on one mark),
the duration NARROWS, reason `flags_disagree`, one candidate per level named,
support = how many attached boxes name it. It used to take the MAX. A box an
existing verdict refuses (`Q.FLAG_IS_NOT_A_FLAG`, incl. a human's) is
skipped by `_attached_flags` and does not vote. Tests
`TestFlagsThatDISAGREEOnTheirLevelNarrow`: the fix assertion ran RED on the
prior branch head; the positive control (two agreeing boxes decide 0.5) and
the refused-box case (the 16th refused -> 0.5 decides) pass on both.

Re-priced with `probe/redecide_arm.py`, base = origin/main's own code
(`63247979`) on each saved record:

| | Breitkopf p1 | Litolff idx 3 | engraved p0 |
|---|--:|--:|--:|
| `duration_narrowed`, main -> branch | 66 -> **59** | 36 -> 37 | 0 -> 0 |
| notes written | 235 -> **238** | 381 -> 380 | 73 -> 73 |
| `<note>` in the file | 455 -> 458 | 560 -> 559 | 174 -> 174 |
| bars held out by the sum | 85 -> 85 | 0 -> 0 (page slice) | 0 -> 0 |
| durations changed vs main | 84 | 1 | **0** |
| of which now `flags_disagree` | 4 | 1 | 0 |

* **Litolff `glyph/3/0/7/3/5`**: 0.5 (main) -> NARROWED `flags_disagree`
  {0.5, 0.25}. The wrong-looking 0.25 of 11.9 no longer reaches the file;
  the note is refused, which is the price of the disagreement.
* **Breitkopf**: `glyph/1/1/9/0/13` (the 11.5 regression, 0.25) is now
  refused as `flags_disagree`, so the 11.5 by-eye tally becomes **9 right,
  4 still wrong, 0 refused -> wrong, 0 right -> wrong**. Three more heads
  that main decided 0.25 through a max over disagreeing flags now narrow:
  `glyph/1/0/10/4/11`, `/1/0/3/3/0`, `/1/1/8/1/3`.
* **Engraved: 0 changed durations -- nothing to check against the truth.**

**The control, restated.** With the tolerance at 0 the branch equals main
verdict for verdict on engraved and Litolff; on Breitkopf it differs in
exactly ONE row, `glyph/1/1/8/1/3`, which reads `flags_disagree` -- two
flags that already OVERLAPPED the stem on main and disagreed, i.e. this
rule acting independently of the tolerance. Every other row reproduces.

Outputs: `probe/out/controls_2_18b/{brk,eng,lit}-{main,off,branch}.json`.
Gate: `pytest -m "not slow"` 3,603 passed; `staged.check` TOTAL 249.

### 11.8 Files

```
probe/redecide_arm.py                 one arm, one record, the tree it sits in (11.9)
probe/beams_2_18b.py                  B/E/missed-flag measurement (--off = the 2.18 tree)
probe/price_2_18b.py                  OFF / flag-only / ALL re-decision of one frozen record
probe/crop_2_18b.py                   the eight crops
probe/out/beams_2_18b_before_p1.json  per-head classes and stroke facts on the 2.18 tree
probe/out/beams_2_18b_after_p1.json   the same on 2.18b, and the 53-head missed-flag list
probe/out/price_2_18b_p1.json         the three arms' census + every changed duration
out/print/beams-2.18b-0{1..8}.png, beams-2.18b-manifest.json
```

## 12. ROADMAP 2.18c -- a second, CV witness for the missed-flag path: `Q.STEM_TIP_INK` (2026-09-29)

PATH: STAGED. GATHER (`gather.stem_tip_ink`, `gather._observe_stem_tip_ink`,
`gather._stem_tip_blockers`) + ADJUDICATE (`rhythm._stem_tip_flag_ink`,
`adjudicate_duration`'s new `flag_ink_unread` branch). Two full re-gathers of
Breitkopf 317803 pdf idx 1 (page 1) on this tree, `--no-surya --no-ocr
--no-roster`, scan weights (`deepscoresv2-yolov8l-hollow-graft-shift09-
2026-09-04.pt`), ~90 s each; 2.18/2.18b are already merged into this tree
(`f3764c9c`, `63247979`), so the population measured here is FRESH, not a
reuse of either lane's frozen record, and its counts do not match 2.18b's
"53" (a different population, on a different gather, after both those
fixes were already active).

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

CLAUDE.md SS10 already states a flag hangs from a stem's end. This item adds
WHERE, relative to the tip, and on WHICH SIDE: Bravura's own flag glyphs run
roughly 1.7-2.4 staff spaces from the stem to their far corner and sit to the
stem's RIGHT whichever way the stem points -- an up-stem's flag hangs DOWN-
right from the top tip, back toward the head; a down-stem's hangs UP-right
from the bottom tip, likewise back toward the head. So the window tested
walks INTO the stem's own body from either end, 1.0 to 2.5 staff spaces,
never past the tip and never to the left (`gather.py`'s own
`STEM_TIP_INK_NEAR_SPACES`/`FAR_SPACES` comment). Falsified by a print-
confirmed flag whose hook sits entirely inside 1.0 space of its tip, reaches
past 2.5, or hangs to the stem's LEFT. NOT CONFIRMED with Sean -- argued from
CLAUDE.md's own convention and Bravura's published metrics, never measured
against a crop before this session; **six real flags were then found and
eye-confirmed inside exactly this window (SS12.5)**, which is evidence FOR
the convention on this plate, not a substitute for asking him.

The density floor (`STEM_TIP_INK_DENSE = 0.30`) and the background guard
(`STEM_TIP_INK_BACKGROUND_MAX = 0.20`) are borrowed reasoning from
`LEDGER_RUNG_INK_DENSE`, not measured for this mark family specifically --
NOT CONFIRMED, and SS12.5 below finds one borderline case (right density
0.2413) that by eye also looks like a real flag, i.e. a plausible
false-negative AT the current floor. Not retuned on one crop (rule 5: no
default flips on agreement with our own reading, and a sweep needs more than
one data point).

### 12.1 GATHER: `Q.STEM_TIP_INK`

One row per (`Q.STEM` row, END), END in `{"top", "bottom"}` -- GATHER does
not know which end is a stem's TRUE tip (that is `Q.STEM_DIRECTION`'s
question, decided later in ADJUDICATE), so both ends are asked and ADJUDICATE
picks the one matching the head's own decided side. `stem_tip_ink` reuses
`ledger_rung_ink`'s shape exactly: a windowed density test off the staff-
ERASED raster (CLAUDE.md SS9) with a background band for contrast -- here,
the mirrored window on the stem's LEFT, since a flag never prints on both
sides of one stem. `value` is `found` (bool); `detail` carries `stem_row_id`
(joins the row back to its exact `Q.STEM` row), `end`, `right`/`left`
densities and the page/canonical window. ABSTAINS -- never defaults --
where the cell carries no `image_no_staff` (`NO_MASK`), no staff-space unit
(`NO_STAFF_GEOMETRY`), or the window falls off the raster, or a BLOCKER
already occupies the window (`OCCUPIED`, SS12.2).

Registered: `record.Q.STEM_TIP_INK` (`CLAIM.MEASUREMENT`), `record.READERS.
CV_STEM_TIP`, `capture.UNSCORED["STEM_TIP_INK"]` (RELATION, same family as
`LEDGER_RUNG_INK`) + `capture.READER_RASTER["CV_STEM_TIP"]`, `Q.DURATION`'s
own `wants`/`composed_from`/`reasons` (adds `flag_ink_unread`).
`python3 -m tools.omr.staged.check`: **TOTAL 249 before and after** -- no
new open finding anywhere (`inventory` 10, `wiring` 67, `gather_coverage`
17, `capture` 18, `reach` 24 all unchanged).

### 12.2 The blocker bug, found and fixed by the FIRST re-gather

Built first with a blocker list of "every `Q.BEAM_STROKE` this cell read
plus every OTHER detection the detector drew here" (a neighbour's head, an
accidental, text, a slur/tie arc -- the brief's own list). Priced on the
first gather: **0 heads narrowed**, against the ~6 the item's brief hoped
for. Of 1,584 window attempts (792 stems x 2 ends), **1,380 abstained
`occupied`** and only 204 were ever measured; of the 173 heads matching the
target population (decided `head_and_marks`, `beam_evidence ==
"none_over_this_note"`), only 8 were measured at all and the highest RIGHT
density among them was 0.033 -- essentially blank. Checking the SIX exact
subjects FINDINGS SS11.4b names as printing an unread flag
(`glyph/1/0/9/5/1`, `/1/1/8/0/9`, `/1/1/8/1/11`, `/1/1/8/3/4`,
`/1/1/9/1/23`, `/1/1/9/3/9`) directly: **all six abstained `occupied` at
BOTH ends**, and the blocker in every case was a single detection box
spanning the WHOLE SYSTEM's width (a `staff` classification box 2,047 px
wide, or a `tie` box 2,043 px wide) that happened to sit at that y -- not a
box that "explains" this window's ink in any local sense.

**Fix**: `_stem_tip_blockers` borrows `_explaining_detections`'s own width
cut (`direction_text.DEFAULT_BAND_CONFIG.max_blank_width_spaces`, 4.0 staff
spaces) -- CLAUDE.md SS10's own reasoning, restated there for the same
reason: "a `staff` box is 26.6 staff spaces wide and a `slur` box is the
rectangle its arc travels through; both are mostly paper." Applied to the
DETECTOR's classification boxes only, never to this reader's own (already
narrow) beam strokes. `test_staged_stem_tip_ink.py`'s
`TestStemTipBlockersWidthCut` (4 tests) checks a page-wide box is NOT a
blocker, a genuinely local one still is, and a beam stroke blocks
regardless of width.

### 12.3 ADJUDICATE: `flag_ink_unread`

`rhythm._stem_tip_flag_ink(ev, cell, own_stems, side)` reads ONLY the
`Q.STEM_TIP_INK` row(s) whose `end` matches this head's OWN decided
`stem_direction` (`side == "up"` -> `end == "top"`) AND whose
`stem_row_id` is one of `own_stems`' ids (`_stems_on`, the same attachment
test `_stem_joined` uses) -- reading the wrong end would ask the question
of the wrong end of a DIFFERENT physical stem, exactly the fault
`_own_stem_side` (2.18) already exists to keep out of the beam join. `None,
()` -- no evidence -- where this head has no own stem, no own direction, or
the matching end was never measured or fully abstained (an older record, or
this window was `OCCUPIED`).

In `adjudicate_duration`, reached ONLY where the fallthrough case would
otherwise decide the head value from silence: `beam_evidence ==
"none_over_this_note"` (the beam reader RAN over this cell and found
nothing over this note -- not merely `"reader_declined"`, the *no reader
ran* case) and no flag was attached (`not flag_levels`). Where `tip_ink` is
`True`: NARROW between exactly two candidates -- the head value (support
1.0) and ONE flag level up (support 2.0, since ink was positively read) --
reason `flag_ink_unread`. Where `tip_ink` is `False`: unchanged, decides the
head value as before. Where `tip_ink` is `None` (no evidence, including
every record gathered before this item existed): unchanged. Never decides
straight to eighth from ink alone -- narrowing between two candidates is the
whole of rule 6's "connect, never guess" applied here: the ink says A hook
exists, not how many.

### 12.4 Priced (`probe/price_flag_2_18c.py`, two full re-gathers, same page)

The control is the OFF arm: `RH._stem_tip_flag_ink` forced to `(None, ())`,
which must decide EVERY duration identically to a record with no
`Q.STEM_TIP_INK` on it at all, and every verdict this rule moves must have
been OFF's own `decided:head_and_marks` -- **PASSED** on both the buggy-
blocker gather and the fixed one.

| | first gather (buggy blocker) | second gather (width-cut fix) |
|---|--:|--:|
| `Q.STEM_TIP_INK` observations / abstentions | 204 / 1,380 | 621 / 963 |
| of which `found=True` | 6 | 27 |
| heads newly NARROWED `flag_ink_unread` | **0** | **6** |
| `duration_narrowed`, off -> on | 59 -> 59 | 59 -> **65** |
| notes in file, off -> on | 1,225 -> 1,225 | 1,225 -> **1,219** |
| `<note>`/rests/beams/bars-held-out-by-sum | unchanged | unchanged (85 bars, same as 2.18b) |

Every `abstained` reason on `Q.STEM_TIP_INK` in the fixed gather is
`occupied` by a LOCAL box under the new cut (963 of 1,584 attempts) -- no
`NO_MASK`/`NO_STAFF_GEOMETRY` on this page, since every cell here carries
an erased raster and a staff-space unit.

### 12.5 Eye-check: 8 crops, `probe/crop_flag_2_18c.py`

Style after `crop_2_18b.py`: the FILED staff a shaded labelled band, the
head bracketed thick red, GREEN the head's own read stem, YELLOW the
EXACT tested window (only the matching end), a staff-space ruler down the
left. Frame control (staff lines darker than a half-space off them)
**PASSED on all 8, none refused**. `out/print/flag-2.18c-0{1..8}.png`,
manifest `flag-2.18c-manifest.json`, every row `VERDICT_none_yet: null`.

**The six narrowed heads (`glyph/1/0/9/5/1`, `/1/1/8/0/9`, `/1/1/8/1/11`,
`/1/1/8/3/4`, `/1/1/9/0/17`, `/1/1/9/3/9` -- five of six are the EXACT
subjects FINDINGS SS11.4b named on the earlier frozen record; the sixth,
`/1/1/9/0/17`, replaces `/1/1/9/1/23`, expected on an independent re-
gather):**

**6 of 6, by my own eye, print a real flag hanging from the stem inside the
yellow window** -- crops #01 (a pizzicato passage), #02-#04, #06 all show
an unmistakable eighth-flag hook curling right off the stem tip; #05 the
same beside an `arco` direction word. Want, per the brief: "the ~6 caught,
few clean quarters narrowed" -- met, with a 6/6 hit rate on this run (n=6,
too small to be a precision figure on its own; see SS12.6).

**2 control crops, heads the reader MEASURED clean (`tip_ink=False`):**
crop #07 (`glyph/1/0/0/0/5`, right density 0.0007) is genuinely a plain
quarter, no flag anywhere near the window -- the mechanism correctly leaves
it decided. Crop #08 (`glyph/1/0/0/2/2`, right density 0.2413, background
0.167) is BORDERLINE: by eye there is a small hook shape beside the stem
tip that could be a flag feeding into the following tie/slur arc -- a
plausible false negative sitting just under `STEM_TIP_INK_DENSE = 0.30`.
Named, not retuned (see the CONVENTION note above).

### 12.6 What this could not do

* n=6 narrowed on one page is not a precision/recall figure; a whole-
  movement or second-plate run would need its own re-gather and its own
  crops, and Sean has asked NOT to burn whole-work runs for a per-change
  check (CLAUDE.md, "build, don't burn runs").
* The borderline crop #08 says the density floor may be slightly high;
  not swept, not retuned -- one data point is not a calibration.
* `STEM_TIP_INK_WIDTH_SPACES`/`NEAR_SPACES`/`FAR_SPACES` are argued from
  Bravura's published metrics and CLAUDE.md's own convention, not measured
  against a ruler on this plate before being built; the eye-check is
  evidence for them, not a replacement for asking Sean.
* Litolff (the MERGING plate) and the engraved fixture are untouched --
  this item's window/threshold is tuned on ZERO Litolff or engraved crops.
* The blocker bug (SS12.2) was found by this session, on this item's own
  first re-gather; it is not known whether an equivalent "wide box hides
  local ink" fault exists in any OTHER reader that filters by detection
  overlap without `_explaining_detections`'s cut. Not audited.

### 12.7 Tests

`test_staged_stem_tip_ink.py` (15): `TestTheMeasurement` (7, `stem_tip_ink`
on synthetic rasters -- a flag found, the POSITIVE CONTROL that a clean tip
is NOT found, the background guard, top/bottom symmetry, off-raster/no-
unit/no-raster all abstain), `TestStemTipBlockersWidthCut` (4, SS12.2's
fix), `TestGatherIntegration` (4, `_observe_stem_tip_ink` files one row per
end, a blocker abstains `occupied`, no mask, no unit). `test_staged_
duration.py`'s new `TestAStemTipWithUnreadFlagInkNarrowsInsteadOfDeciding`
(8): flag ink at the matching end NARROWS; the POSITIVE CONTROL (a clean
tip still DECIDES the head value); an OLDER record with no `Q.STEM_TIP_INK`
row is ALSO unchanged; ink at the WRONG end is not read; a down-stem reads
its BOTTOM tip (symmetry); the guard stands down where a real flag already
decided the note (`beam_evidence == "flag"`); it never decides straight to
eighth (rule 6). **RUN RED FIRST**: with the new branch's condition
short-circuited (`if False and ...`), the 3 tests that exercise the
narrowing itself failed as expected and the 4 unchanged-behaviour/guard
tests still passed (a positive-control discipline: a test that cannot fail
is not a test) -- restored, all 91 pass together with the pre-existing
`test_staged_duration.py` suite (73 -> 76 -> 91 across this session's
edits, per CLAUDE.md SS6c's own concern; no `library/`/`omr-weights/`/venv
path in either file, so neither moves to the slow tier).

Gate: `pytest tools/omr/tests -m "not slow" -q -p no:cacheprovider` --
**3,654 passed, 3 skipped** (main: 3,632 -- +22 net, no drop, so no test
file moved to the slow tier; this item's own two files add 23, +1 of
"stray" is inside that noise and not investigated further);
`python3 -m tools.omr.staged.check` **TOTAL 249** before, during (buggy
blocker) and after (fixed) -- unchanged throughout.

### 12.8 Files

```
tools/omr/staged/gather.py                new: stem_tip_ink, _stem_tip_blockers,
                                           _observe_stem_tip_ink, and the
                                           gather_cv_lines wiring
tools/omr/staged/record.py                Q.STEM_TIP_INK, READERS.CV_STEM_TIP,
                                           CLAIM["STEM_TIP_INK"]
tools/omr/staged/capture.py               UNSCORED + READER_RASTER entries
tools/omr/staged/adjudicators/rhythm.py   _stem_tip_flag_ink, the new
                                           flag_ink_unread branch, wants/
                                           composed_from/reasons on Q.DURATION
tools/omr/tests/test_staged_stem_tip_ink.py         new, 15 tests
tools/omr/tests/test_staged_duration.py             +8 tests
benchmarks/omr-missing-notes-2026-09/probe/price_flag_2_18c.py    the pricing arm
benchmarks/omr-missing-notes-2026-09/probe/crop_flag_2_18c.py     the 8 crops
benchmarks/omr-missing-notes-2026-09/out/print/flag-2.18c-0{1..8}.png,
    flag-2.18c-manifest.json
```

## 13. ROADMAP 2.25 -- strokes that are not this note's beam are not counted
as its beam (2026-09-29)

PATH: STAGED. Branch `claude/beam-strokes-2.25`, off `origin/main` `df61ed08`
(2.18/2.18b already in the tree). Question from `benchmarks/omr-bar-sum-
holdout-2026-09/FINDINGS.md` §17f item 4: at WHOLE-MOVEMENT scale, 2.22's
`G` classes (168 Brahms + 73 Litolff bars, plus much of the unmodelled
remainder, §17c) name ledger lines, hairpins and other staves' beams
entering the beam count -- what is left after 2.18 (far-side strokes
dropped) and 2.18b (strokes past the stem tip with no stem reaching them)?

### CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

CLAUDE.md §10: a beam runs from the first stem it joins to the last, and a
whole rest means the bar whatever the meter. This item adds no new
engraving convention -- it claims only that a beam-shaped stroke standing
exactly where the DETECTOR ALSO boxed a `ledgerLine` glyph is that ledger
line, i.e. two readers named the same ink two different things. Falsified
by a crop where a RED-X stroke this rule drops is genuinely the bracketed
note's own beam and the YELLOW `ledgerLine` box under it is a detector
false positive on real beam ink. NOT CONFIRMED with Sean -- the 8 crops
below are for him.

### §13a. Diagnosis: fresh gathers, one page each plate

Breitkopf `317803` pdf idx 1 (Brahms 1/i) and Litolff `984073` pdf idx 3
(Beethoven 5/i, the count page), both gathered fresh on this tree,
`--no-surya --no-ocr --no-roster`, scan weights
(`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`), ~75-90 s each
(`out/r225/gather-{brahms-p1,litolff-p3}.log`). Not committed -- 46 MB and
12 MB, regenerable from the command in this section.

`probe/beam_stroke_sources_2_25.py` rebuilds each record's GATHER rows
(`record_io.load_record` + `review.rerun.rebuild_gather`) and, for every
`Q.DURATION` verdict whose own `detail.beam_evidence == "read"` (at least
one beam level was actually COUNTED, narrowed or decided), re-derives the
counted strokes through `adjudicate_duration`'s own current helpers
(`_kept_beams`, `_own_stem_side`, `_on_stem_side`, `_beyond_own_stem`, the
rule-8 guard, `_stem_joined`, `_beam_levels`) -- so the population
classified is exactly what 2.18/2.18b already count, not a re-invented one.

**CONTROL, and it failed once before it passed.** `rebuild_gather`'s own
docstring: *"Verdicts are NOT replayed."* The first pass therefore always
saw `Q.STEM_DIRECTION` as unread, `_own_stem_side` always returned `None`,
and the re-derived `certain` disagreed with the verdict's own
`detail.levels_certain` on 89 of 555 Brahms heads (466/555). Fixed by
reading the record's OWN saved `Q.STEM_DIRECTION` verdicts by subject key
instead of through `ev.verdict` on the rebuilt (verdict-less) log --
**555 of 555 (Brahms) and 128 of 128 (Litolff) re-derived exactly, after
the fix.** A control that reproduces for the wrong reason and is caught by
its own arithmetic (CLAUDE.md §2 rule 7) rather than trusted on the first
green number.

For every COUNTED stroke of every such head, does its canonical box
(`_boxes_overlap`) coincide with: a DETECTOR-boxed `ledgerLine` glyph in the
same cell (`Q.GLYPH_BOX`, same frame, no conversion needed); a decided-found
`Q.LEDGER_RUNG_INK` window on THIS head (page pixels, converted to
canonical through an `up` factor solved algebraically from any co-located
detector `Q.GLYPH_BOX` row that carries both frames -- the same arithmetic
`gather._page_box` computes forward, never a guess); a `Q.WEDGE_BOX` (same
conversion, either reader); a `Q.ARC_BOX` (slur/tie ink, already canonical);
or ink sitting more than 2.5 staff spaces outside THIS cell's own
`Q.STAFF_LINES` band (`other_staff_via_pad`, a label only -- a genuinely
elevated note's own ledger-line beam can sit that far out too, so this
label is NOT by itself evidence of a cross-staff mistake).

**Ranked, per HEAD (a head may carry more than one label):**

| label | Brahms p1 (555 heads) | Litolff p3 (128 heads) |
|---|--:|--:|
| `unexplained` (a stroke matching none of the below -- most likely a real beam) | 349 | 113 |
| `other_staff_via_pad` | 150 | 7 |
| `arc_box` | 139 | 0 |
| `wedge_box` | 68 | 0 |
| `ledger_line_box` | 7 | 21 |
| `ledger_rung_ink` | 0 | 0 |

`ledger_rung_ink` reads zero on both pages -- not because no ledger-line
stroke is real, but because a `Q.LEDGER_RUNG_INK` window is a THIN band a
few px either side of the expected rung y, and it is common for the CV/YOLO
beam opening to box a wider run than that window covers, or for the rung to
be ABSTAINED (state, not value) rather than decided-found. Named, not
chased further within this item's budget.

`arc_box` and `wedge_box` are measured by BOUNDING-BOX overlap only. A
slur or a hairpin is drawn as a curve or a pair of converging lines, and
its box can span a whole phrase; a stroke can sit inside that box without
the stroke and the mark's actual ink ever touching. These two numbers are
therefore an UPPER BOUND on how often the stated mechanism (CLAUDE.md §10:
"An arc is drawn OVER its notes, a hairpin BETWEEN them") is the true
cause, not a count of confirmed cases -- eye-checking a sample of both
before building anything against either was out of this item's budget.
Named as the top TWO unbuilt classes below.

### §13b. Built: a stroke over a boxed `ledgerLine` glyph is that ledger
line, not this note's beam

Of the five candidate causes, ONLY the ledger-line connection is built,
for one reason: it is the only one where BOTH sides of the comparison are
already the SAME canonical per-cell frame `Q.GLYPH_BOX` and `Q.BEAM_STROKE`
both use, so no conversion, and no chance of the `Q.ONSET_COLUMN` frame
error (`adjudicate_wedge_anchor`'s own docstring: *"comparing a cell-frame
wedge against a page-frame notehead is the frame error that made
Q.ONSET_COLUMN report 1,062 columns of nothing"*), is needed. `wedge_box`
is the larger number on Brahms (68 heads) but every wedge reading that
matters on a scan comes from `cv_hairpins`, which files PAGE pixels only
(CLAUDE.md §6b precedent, `ownership.py`'s own wedge-anchor rule: *"a row
without them abstains"*) -- building it would need the SAME `up`-factor
conversion my diagnostic script uses, and that is named here (§13c) for the
next lane rather than rushed into `tools/`.

**The fix** (`rhythm._ledger_line_glyph_boxes`, `_not_a_ledger_line`,
`adjudicators/rhythm.py`): right after `_kept_beams` returns the cell's
candidate strokes and BEFORE any stem-side/tolerance filtering, every
stroke that overlaps a DETECTOR-boxed `ledgerLine` glyph in the SAME cell
is dropped. No new `wants`/`composed_from` entry: `Q.GLYPH_BOX` is already
read for the head's own box. ADDITIVE, never subtractive of the record --
a cell where the detector never boxed a `ledgerLine` drops nothing, so a
page without one behaves exactly as before. No rule-8 guard was added:
pricing (§13d) found no case where this step alone left a note with no
other mark, and 2.18b's own guard on `_beyond_own_stem` already covers the
general fallback where dropping a stroke would.

Stage: ADJUDICATE, not INFER. Two readers (the CV/YOLO beam opening and the
DETECTOR's own class head) already named the SAME ink; this is a
CONNECTION between two existing GATHER facts, not a choice between two
readings of one fact -- it FOLLOWS, it does not merely fit better.

**RED -> GREEN.** `tools/omr/tests/test_staged_duration.py::
TestAStrokeOverAABoxedLedgerLineIsThatLedgerLineNotABeam`, 4 tests. Run RED
against the unrepaired tree first (stash-and-restore of `rhythm.py` alone,
tests kept): **4 of 4 failed** -- two on the fix assertion itself (a note
whose only "second beam level" is a boxed ledger line decides at the LOWER
value, `beams_ledger_line == 1`), two on the new `detail.beams_ledger_line`
key not existing yet. The POSITIVE control (`test_the_POSITIVE_control_a_
real_second_level_still_counts`): the SAME two strokes with no ledger line
boxed at that y are two genuine levels and BOTH count. A third test
(`test_a_ledger_line_boxed_ELSEWHERE_in_x...`) checks the overlap is a real
box test, not a per-cell veto: a ledger line under a DIFFERENT note's
column leaves this note alone. A fourth (`test_no_boxed_ledger_line_at_
all_changes_nothing`) is the ADDITIVE control. All 4 pass on the repaired
tree.

### §13c. Priced: base (`git archive origin/main`) vs arm, same records,
re-decided in-process

`probe/price_2_25.py` (`RR.rebuild_gather` + `RR.run_stages` +
`RR.export_with_subjects`, the `redecide_arm.py` §11.9 precedent -- base
runs origin/main's OWN `rhythm.py` on the SAME gather, arm runs this
tree's). Independent control: `benchmarks/omr-bar-sum-holdout-2026-09/
probe/bar_sum_check.py` against the exported FILE, never against the
exporter's own arithmetic.

| | engraved p0-p2 (control) | Litolff p3 (single page, no meter carried in) | Brahms p1 (single page) |
|---|--:|--:|--:|
| heads touched by the rule | 0 | 37 | 66 |
| ...of which the VALUE changed | -- | 18 | 7 |
| `duration_narrowed`, base -> arm | 1 -> 1 | 37 -> 35 | 65 -> 60 |
| notes written, base -> arm | 341 -> 341 | 380 -> 382 | 229 -> 231 |
| `<note>` in file, base -> arm | 658 -> 658 | 559 -> 561 | 445 -> 447 |
| `bars_held_out_sum`, base -> arm | -- | 0 -> 0 | 74 -> 74 (the SAME bars) |
| `bar_sum_check`, base / arm | 432/432 exact / 432/432 exact | **DEAD AT ZERO both arms** (320 unassessable -- a single mid-movement page carries no meter of its own) | 98/98 exact / 98/98 exact |

**The engraved control moves nothing** -- a clean engraving has no
detector-boxed `ledgerLine` glyph sitting under a beam stroke, so the rule
is inert there exactly as it should be. **Litolff's bar-sum control is
DEAD, not passing** -- pdf idx 3 alone, gathered with no prior page to
carry a meter in, corroborates zero bars on EITHER arm; that is a property
of testing one mid-movement page in isolation (CLAUDE.md §6b: "an arm that
moves nothing because it is inert and one that moves nothing because the
page holds nothing to move are the same number" -- named here so it is not
mistaken for a pass). **Brahms's bar-sum control is the real one and it
holds: 98 of 98 exact on both arms**, and `bars_held_out_sum` is the
IDENTICAL 74 bars before and after -- the fix moves accounting inside
already-held or already-written bars, never which bars are held (the same
invariant §17d's `reconcile_duration` fix reports).

**18 of 37 Litolff heads and 7 of 66 Brahms heads change VALUE**, every one
by exactly one beam level (a duplicated reading of the note's own ledger
rung was doubling or quadrupling the apparent subdivision -- e.g.
0.25 -> 0.5, 0.5 -> 1.0 -- or holding a note NARROWED that now decides).
The remaining touched heads keep their prior outcome: the dropped stroke
was a redundant second reading of ink a real beam or stem already
accounted for, so removing it changes nothing written. `owned_by_another_
staff` moves by 1 on Brahms (45 -> 46) and `bar_does_not_add_up` by 2
(540 -> 542) with `bars_held_out_sum` unchanged -- the SAME ripple §17d's
own pricing table names: "a decided duration changes the events a contest
sees."

### §13d. Crops for Sean

`benchmarks/omr-missing-notes-2026-09/out/print/beam-strokes-2.25-{litolff,
brahms}-0{1..5,1..3}.png` (5 Litolff + 3 Brahms = 8), manifests
`beam-strokes-2.25-{litolff,brahms}-manifest.json`, every row
`VERDICT_none_yet: null`, cut by `probe/crop_2_25.py` at 600 dpi in the
2.18b style: the filed staff a shaded labelled band over its own
`Q.STAFF_LINES`, the head bracketed thick red, a staff-space ruler down the
left. GREEN = the head's own read stem, BLUE = a kept stroke, RED X = a
stroke dropped by 2.25, YELLOW = the boxed `ledgerLine` glyph that did the
dropping. Frame control passed on all 8 (none refused). Chosen from the
heads whose VALUE changed (§13c), spanning both plates: Litolff #1
(`glyph/3/0/0/2/4`, 0.5 -> 1.0), #4 (`glyph/3/0/7/3/1`, narrowed ->
decided 0.5); Brahms #2 (`glyph/1/0/9/0/4`, narrowed -> decided 0.125). My
own eye-check on #1 (Litolff) is convincing: a single stemmed head sitting
on ONE ledger line above the staff, the YELLOW box drawn exactly on that
rung, the note reading 1.0 (a plain quarter) after the fix where before it
read as a doubled value from the same rung counted as a second beam level.
Question on each: *the printed value of the bracketed note, and is any
RED-X stroke this note's beam, or is it the ledger rung under a YELLOW
box?*

### §13e. Ranked next

1. **`wedge_box`, 68 Brahms heads** -- the larger of the two unbuilt
   classes. Needs the `up`-factor page->canonical conversion this item's
   diagnostic script already implements for `cv_hairpins` rows, ported
   into `rhythm.py` and eye-checked on a sample first (§13a's bounding-box
   caveat) before it is trusted the way the ledger-line connection was.
2. **`arc_box`, 139 Brahms heads** -- the largest unbuilt class by count,
   and the one with the WEAKEST evidence of the five: a slur/tie bounding
   box is the least reliable proxy for where its ink actually is. Eye-check
   a sample before building anything.
3. **`other_staff_via_pad`, 150 Brahms / 7 Litolff heads** -- NOT the same
   claim 2.18b's own `glyph_owner`-routing suggestion measured and found
   zero reach for (that was about which STAFF a stroke's OWNER contest
   awards; this is a raw geometric distance from the cell's own staff
   band). Confounded with genuinely elevated notes whose own ledger-line
   beam legitimately sits far from the band -- untangling the two needs a
   print check, not a threshold.
4. **`ledger_rung_ink`, measured at zero** -- the CV rung's window may be
   narrower than the stroke it should explain, or the rung is commonly
   ABSTAINED rather than decided-found where it would matter most. Worth a
   look before trusting `ledger_line_box` alone as the whole ledger-line
   story at whole-movement scale.
5. **Whole-movement pricing** -- not run (Sean, 2026-09-28: no whole-work
   runs without asking; this item priced two single pages only). §17b/§17c's
   168/73-bar `G` figures are NOT re-measured against this fix.

### §13f. Gates

`pytest tools/omr/tests -m "not slow" -q -p no:cacheprovider`: **3,797
passed, 3 skipped** (main's own 3,793 + 4 new, 0 failed;
`out/r225/pytest-fast.txt`). No `library/`/`omr-weights/`/venv/PDF path in
`test_staged_duration.py`'s new class. `python3 -m tools.omr.staged.check`:
**TOTAL 247, unchanged** (`out/r225/staged-check.txt`).

### §13g. Files

```
benchmarks/omr-missing-notes-2026-09/probe/beam_stroke_sources_2_25.py
    the diagnosis (§13a): per-head ranked stroke-source census, control
    555/555 + 128/128
benchmarks/omr-missing-notes-2026-09/probe/price_2_25.py
    base-vs-arm pricing over a fixed gather (§13c)
benchmarks/omr-missing-notes-2026-09/probe/crop_2_25.py
    the 8 crops (§13d)
benchmarks/omr-missing-notes-2026-09/out/r225/
    brahms-p1.record.json, litolff-p3.record.json (gathers, not committed,
    46 MB / 12 MB), brahms-p1-strokes.json, litolff-p3-strokes.json (the
    census), {eng,litolff,brahms}-{base,arm}.json/.musicxml (pricing),
    staged-check.txt
tools/omr/staged/adjudicators/rhythm.py
    _ledger_line_glyph_boxes, _not_a_ledger_line, wired into
    adjudicate_duration right after _kept_beams; detail.beams_ledger_line
tools/omr/tests/test_staged_duration.py
    +4 tests, TestAStrokeOverAABoxedLedgerLineIsThatLedgerLineNotABeam
benchmarks/omr-missing-notes-2026-09/out/print/beam-strokes-2.25-{litolff,
    brahms}-0{1..5,1..3}.png, and the two manifests
```

### §13h. ROADMAP 2.25b -- two of the three named classes, as conceptual
wiring, plus rule 8 (2026-09-29)

PATH: STAGED. Branch `claude/beam-strokes-2.25b`, off `origin/main` `ae81a3e5`
(2.25 merged). **Sean, mid-lane: no more pricing runs -- no gathers, no
base-vs-arm re-adjudications, no crop batches.** This section is built and
verified to that instruction: the wiring exists, proved by microscopic
tests, and is NOT priced against a real page. An earlier exploratory pass
DID run real pricing on Brahms p1/Litolff p3 and eye-checked ~10 crops
before that instruction landed -- the finding it surfaced is why class 3
below is NOT shipped: on Brahms, the `wedge_box` connection's `>= 2 stems`
override did not reliably distinguish a real down-stemmed beam sitting
under a hairpin (CLAUDE.md SS10: a hairpin sits UNDER its staff, the same
territory a down-stem's beam occupies) from the hairpin's own ink, and 2
of 2 wedge-tagged crops looked like a real beam wrongly discounted. That
run is not reproduced here; the artefacts were discarded per Sean's
instruction, and this paragraph is what is carried forward from it.

**Built**, all in `tools/omr/staged/adjudicators/rhythm.py`:

- `_cell_frame(ev, cell)` -- `(origin_x, origin_y, up)` solving `page =
  origin + canonical / up`, solved backward from any ONE `Q.GLYPH_BOX` row
  in the cell that already carries both frames (no new quantity; there is
  no persisted `upscale_factor` on a saved record). `_to_page`/
  `_to_canonical` are its exact inverses. Declines (returns `None`, never
  guesses) where no dual-frame row exists.
- `_not_the_neighbours_beam` (class 1, `other_staff_via_pad`): a stroke
  beyond THIS staff's own outer line (`Q.STAFF_LINES`) that overlaps, in
  PAGE pixels, a `Q.STEM` filed on the neighbouring staff's own same-cell
  subject, is that staff's beam -- unless THIS head's own attached stem
  also reaches it (rule 6's override).
- `_not_a_decided_arc` (class 2, `arc_box`): a stroke inside a glyph whose
  `Q.ARC_KIND` verdict is DECIDED (tie/slur; runs before `duration` in
  `adjudicate.ORDER`) is that arc's ink, unless the stroke joins >= 2 of
  this cell's own `Q.STEM` rows (the manager's own positive control: a real
  beam spanning several stems still counts).

**NOT built: class 3, `wedge_box`.** Taken OUT of the wiring before merge
(Sean) for the reason above -- a wrongly dropped beam writes a wrong
value, which is worse than the cases this class would have caught. The
comment above `_flag_levels_table` (where `_not_inside_a_wedge` used to
live) carries the reason forward; `Q.WEDGE_BOX` no longer joins
`Q.DURATION`'s `wants`/`composed_from`. `Q.WEDGE_ANCHOR` could not have
gated it anyway -- it runs AFTER `duration` in `adjudicate.ORDER`, and
there is no per-family refusal for a hairpin the way 3.4g built one for
ledger/arc/etc.

Both surviving classes run right after `_not_a_ledger_line`, before
2.18/2.18b's side/tolerance filtering, additive-safe (drop only).
`Q.ARC_BOX`, `Q.ARC_KIND` joined `Q.DURATION`'s `wants`/`composed_from`;
`Q.STEM` needed no new entry (a second SUBJECT of an already-declared
quantity). `detail.beams_neighbour_staff`/`beams_decided_arc` carry each
class's count.

**2.18b's rule 8, applied to both survivors (Sean, before merge).**
Discounting every candidate stroke a STEMMED head had, as the neighbour's
beam or a decided arc's own ink, may not by itself turn a marked note into
an unmarked one -- the exact shape 2.18b's own `beyond_stem_kept_no_other_
mark` guard already uses for `_beyond_own_stem`, applied to a different
cause. `discount_removed_all_marks` is computed right after the two
connections run (before 2.18/2.18b touch `kept` further): true only where
this head had at least one candidate stroke, has NONE now, and one of
these two connections (not an empty page) is why. Where that holds AND the
head has its own stem AND no flag was found either, `adjudicate_duration`
NARROWS between the head value and ONE beam level (reason
`beam_discounted_uncertain`, same shape as 2.18c's `flag_ink_unread`)
instead of deciding the head value from an absence the discount itself
created -- never straight to a specific level, because the discount says
nothing about HOW MANY levels the ink would have been.

**Tests, RED first.** `TestCellFrameRoundTrips` (2), `TestANeighbourStaffsB
eamThroughThePadIsNotThisNotes` (3: the fix, the OWN-STEM positive control,
the no-neighbour-stem ADDITIVE control), `TestRule8AppliesToTheNeighbourAn
dArcDiscounts` (2: the neighbour case narrows, the positive control -- a
head with ANOTHER real, undiscounted beam still decides normally),
`TestAStrokeInsideADecidedArcIsThatArcNotABeam` (3: the fix -- now
NARROWED under rule 8, since that fixture's head carries a stem -- the
>=2-stems positive control, the no-arc ADDITIVE control) -- **10 tests for
this half of the item** (11 from the first 2.25b pass, minus 3 removed
with the wedge class, plus 2 for rule 8). Run against the unrepaired
(neighbour/arc built, no rule 8) tree via stash-and-restore of `rhythm.py`
alone: the rule-8 case and the now-updated arc test **both failed** (the
arc fixture's head has a stem, so it now exercises rule 8 too -- an
existing assertion changed on purpose, not a new one dodged). All pass on
the repaired tree.

**Not measured, on purpose (Sean's instruction).** No real page was
gathered or re-priced for this section; no `bar_sum_check`; no crops of a
real subject. class 1/2's real-page yield with rule 8 applied is unpriced
and open; class 3 is not shipped at all.

**Gates.** `pytest tools/omr/tests -m "not slow" -q -p no:cacheprovider`:
**3,807 passed, 3 skipped** (main's 3,797 + 10 net new, 0 failed).
`python3 -m tools.omr.staged.check`: **TOTAL 247, unchanged.**
```

---

## 14. ROADMAP 2.69 -- count the hooks at a stem tip (2026-10-09)

Path: STAGED. Sean, 2026-10-09 (DECISIONS): *"Count the hooks and if you can't
count use the fact that there is a hook to help later deduction process ... if
we see a hook but can't tell if it has 1 or 2 hooks then pass that along and a
later deduction where we add up bar math could tell us if we are missing an
eighth note then it could decide."* And, the same day (ROADMAP 2.71): a flag
hook hangs from ONE side of the stem; a tremolo slash crosses both and is never
a hook.

**The mechanism found.** 2.18c's narrowing was `head value | one flag level`
(`flag_ink_unread`, quarter or eighth). Sheet B of 2.65 (tiles 6, 11, 12, 14,
17, and tile 13, a dotted case) were five-six lone flagged eighths the
`Q.STEM_TIP_INK` reader SAW and the narrowing then left half-open towards the
head value. Nothing counted the hooks, and nothing downstream needed to be
told: `consequences.reconcile_duration` already searches a narrowing's OWN
candidates (`_admitted`) and takes the one that makes the bar add up where
exactly one does, and `collapse_duration_*` (INFER) take any narrowed verdict.
So the change is the narrowing's CANDIDATES (levels >= 1 only) and a counted
decision, not a new settling rule. Wired, not duplicated.

**Built.** GATHER: `gather.stem_tip_hooks` (+ `_head_edge_for_end`), called from
`_observe_stem_tip_ink` where the ink is found; the count rides in the
`Q.STEM_TIP_INK` row's detail (`hooks`, `hooks_min`, `hooks_max`,
`hooks_reason`, `hooks_support`) -- NO new quantity, no new reader, no new
flag, `check` TOTAL **192, unchanged**. The reader counts distinct runs of ink
attached to the stem in a band 0.1-0.4 spaces to its right, from the tip to
the first notehead beside the stem (cut so the stem's own head is never a
hook), after healing the staff-erase's stripes. It REFUSES with a reason word:
`crosses_both_sides` (ink attached on the stem's left too -- the slash, a
crossing slur), `head_at_this_end`, `no_room`, `too_little_ink`,
`unresolved` (support below/above its floors, or stacked runs not hook-spaced:
the first within 0.8 spaces of the tip, consecutive ones 0.4-1.1 apart).
ADJUDICATE: `rhythm._stem_tip_hook_count` + the 2.18c block in
`adjudicate_duration`: counted -> DECIDED at that level (`hooks_counted`);
seen-not-counted -> NARROWED over `hooks_min..hooks_max` (>= 1, lowest best
supported, reason still `flag_ink_unread`); never the head value. A row from
before the count existed brackets 1..2.

**Measured (Brahms 1 Breitkopf, pdf pages 0-1, GATHER+ADJUDICATE, small
re-gather at the commit that follows 96c379fd).**
- Calibration set: the 109 flag-bearing heads on page 1 with a stem, counted
  off the dump of the cells the gather itself used: every one is a single hook
  by eye. Counted 1: 83 (71 detector-flagged + 4 `flags_disagree` + 8 of Sean's
  unread); counted 2 or more: **0 after the spacing guard** (before it, 3-4
  slurs/ledger lines attached to a stem read as a second run); refused with a
  reason: the rest. The two detector `flag16th*` boxes on single hooks
  (glyph/1/0/12/5/0, glyph/1/1/3/0/10; tile 21's family) count 1.
- Two-hook calibration is NOT on this plate (it holds none): LilyPond-engraved
  8th/16th/32nd, stems up and down, 300 dpi, staff-erased (scratchpad,
  not committed): 8th -> 1 in 12 of 14 stems (never wrong), 16th -> 2 in 11 of 12, 32nd -> 3 in
  8 of 12 real stems, no miscount, the rest `unresolved`/refused. Unit tests draw 1, 2, 3
  stacked hooks, a slash and a hook+slash (both refused), a slur on one side
  (not a second hook) and the own-head cut (with its uncut control).
- **The 22 tiles** (`out/print/2.65/compare.py`): before 12 right / 2 wrong / 8
  narrowed; after **17 right / 3 wrong (1, 13, 21) / 2 narrowed (4, 15)**. Sheet
  B: tiles 6, 11, 12, 14, 17 decided eighth. Tile 13 (an eighth with NO dot on
  the print) is now decided 0.75: the 2.12c dot reader attached an
  `augmentationDot` box to it (the flag's tail, by the crop), a fault that was
  already in the old narrowing (0.75 / 1.5) and is not this mechanism; deciding
  made it visible. Tiles 15 (`flags_disagree` 8th/16th: the detector boxes
  both on one single hook -- `hooks=1` would settle it, NOT wired: a detector
  flag box outranks the count, per the existing guard), 1 (read quarter, truly
  eighth on a ledger line) and 21 (read sixteenth, truly eighth) are not this
  mechanism and are untouched.
- **Population (all Brahms p0-1 duration verdicts, 1,862 on both records):
  8 changed, all `narrowed flag_ink_unread` -> decided: 7 -> eighth, 1 ->
  dotted eighth.** Nothing else moved; no `flag_ink_unread` narrowing remains
  on the page, so the uncounted->narrowed branch and the bar-math settlement
  are exercised by unit tests only, not by a real head here.
- Print: the two decided heads Sean has not judged
  (`out/print/2.69/head_01.png`, `head_02.png`; manifest beside them): both
  show one hook by eye (a single curl at the stem tip).

**Gates.** RED first: the 26 new/changed tests failed on the unrepaired tree
(controls stayed green). `pytest -m "not slow" tools/omr/tests`: 6,408 passed,
11 skipped, 2 xfailed, 0 failed. `staged.check` TOTAL 192 (= main).

**CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED with Sean:**
hooks are separate strokes leaving the stem's right side, stacked a hook
spacing apart; falsified by a print-confirmed two-hook flag whose strokes touch
across the 0.1-0.4 band, or a single hook whose root is split by a stray
attached ink the guards pass. Thresholds (support .40, glitch .12, coverage .5,
spacing .4-1.1) are set on one plate.

**Not done.** Wiring the count as a witness against a detector flag box
(`flags_disagree`, tile 15; the detector's 16th on a single hook); a real
two-hook head from a scan (none in the gathered pages).

### 14b. Follow-up: a "dot" on the tip of a flag (Sean, 2026-10-09, DECISIONS)

Tile 13 (glyph/1/1/8/3/4, a plain eighth) was DECIDED 0.75 after 14: the
detector's `augmentationDot` box glyph/1/1/8/3/15 sits entirely on the curled
tip of the note's own flag, `adjudicate_dot_role` called it right-of-and-level
and the note was dotted. Sean: *"a dot can not fully or mostly overlap a flag
but it can touch it"* -- overlap, not contact.

**Built.** GATHER `Q.DOT_STROKE_INK` (`gather.dot_stroke_ink`,
`_observe_dot_stroke_ink`, `READERS.CV_DOT_STROKE`; filed on each
`augmentationDot` detection's own glyph subject): the share of the ink inside
the dot box that lies on an elongated stroke -- ink a line three dot-widths
long fits through, opened at 45/90/135 degrees (not 0: erased staff lines leave
horizontal stripes, which first read a real dot as 0.94), the survivors grown
back 0.15 spaces within the ink. A disc, touching a flag or not, has no such
line (0.0); a flag tip or stem does. ADJUDICATE: `adjudicate_dot_role`
abstains `on_a_stroke` at >= `DOT_ON_STROKE_MIN` (0.5); `_attached_dots` already
reads only DECIDED augmentation roles, so the note is not dotted. Nothing is
decided about what the box IS. `check` TOTAL 192 (= main); capture/producer
entries added.

**Measured (Brahms p1, 44 dot boxes holding over 100 ink pixels).** Real dots: 0.0
on every one. Refused: glyph/1/1/8/3/15 (0.93, tile 13's tip) and
glyph/1/0/13/0/24 (1.0, 18 ink pixels, a box on the base of a stem against a
head; crop `out/print/2.69/dot_02.png`: no dot is printed there).
**Durations that moved (full page, 1,862 verdicts): tile 13 0.75 -> 0.5
(decided eighth, right) and glyph/1/0/13/0/8 `beam_certain_not_joined`
[0.375, 0.75] -> [0.25, 0.5] (the dotted candidates, from the second false dot,
gone). Nothing else.** The 22-tile table: 18 right / 2 wrong (1, 21) / 2
narrowed (4, 15); tile 13 right.

**Tests.** `test_staged_dot_on_stroke.py` (17): RED first -- 16 of 17 failed on
the unrepaired tree (the controls fail there on missing vocabulary, so the
behavioural controls are the ones that matter: no stroke row = unchanged, a
staccato above a note stays a staccato, a dot with stroke 0.2/0.49 stays a dot,
a disc touching a flag and a disc on a staff stripe read < 0.5). The existing
2026-10-07 rulings' tests (staccato placed dots, dot on a barline, dot follows
the real note) pass unchanged. `pytest -m "not slow"`: 6,474 passed, 0 failed.

**Beamless cells (asked by the 2.70 lane).** NOT handled on this branch: the
2.18c/2.69 block is gated on `beam_evidence == "none_over_this_note"`, which
needs `Q.BEAM_STROKE` READ in the cell. A cell where the beam reader found no
stroke at all (abstention `no_line_accepted`) reads `reader_declined`, so a note
whose hook the tip reader COUNTED still decides its head value there (checked:
a counted hook, with and without the `no_line_accepted` abstention, decides
the quarter). The sheet-B heads decided because their cells hold other beams.
The same hole existed before 2.69; it is not a regression. The fix is to admit
`reader_declined` where every `Q.BEAM_STROKE` abstention in the cell is
`no_line_accepted`/`no_stems_to_join` (the reader ran and accepted nothing),
never for `reader_unavailable`.

---

## 15. ROADMAP 2.74 -- a beam is thick, straight, and stands on two stems (2026-10-09)

Path: STAGED, GATHER + ADJUDICATE only (Sean, 2026-09-30). Branch
`lane-2.74-beam-two-stems`, off `lane-2.69-flag-hooks` + main. Sean, 2026-10-09
(DECISIONS), on 2.65 tiles 1, 4, 15, 21: *"A beam must not only connect to its note
but also to another note."* / *"A beam never has an arc."* / *"The thickness on a
beam is always more than a hairpin."* and, asked: once ink is shown to be a
hairpin, can it never be a beam?

**CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED beyond Sean's three
lines:** the numbers. A beam is >= 1.75 staff-line thicknesses thick (the staff
lines measured AT the stroke's columns); it bows no more than 0.40 spaces; a second
stem stands within reach (`Q.STEM` within the join tolerance, or a vertical run in the
ink at either end). Falsified by a print-confirmed beam the tests refuse. The crops
below are my eye, not Sean's.

### 15.1 Mechanism per tile (base = the 2.69 tree `2b6f0741`, small re-gather, Brahms p0-1)

| tile | printed | read | mechanism | after 2.74 |
|---|---|---|---|---|
| 21 `glyph/1/1/10/7/4` | 8th | 16th | two CV "beams" over a real beam are a **slur's tapering arcs** (1.5 and 1.6 staff lines thick, bow 0.18 / 0.20 spaces, no stem at either end); both overlap the head's stem box, so 2 certain levels | **eighth** (`too_thin` x2) |
| 1 `glyph/1/0/0/0/5` | 8th | quarter | **no beam was ever read**: the group's beam and a dim. hairpin drawn under it fuse into ONE component 125 px tall against a 115 px ceiling (`line_detection.detect_beams`, `h > max_h`); nothing else stands over the head, so the head value stands | **eighth** (the fused component re-opened with a kernel 1.75 lines tall: the beam survives, the hairpin's line does not) |
| 4 `glyph/1/0/3/3/11` | 8th | 128th..32nd (no eighth) | the cell holds **no CV beam** (the group's real beam is unread) and 12 overlapping detector `beam` boxes, none a beam (1.0-1.2 lines thick: ties, hairpin lines, staff-line residue; they stacked as levels 3-5) | narrowed `beam_discounted_uncertain`, **eighth \| quarter**, eighth first; the real beam is still unread |
| 15 `glyph/1/1/9/0/13` | 8th | narrowed 8th \| 16th | the detector boxes ONE flag as `flag8thUp` and `flag16thUp`; **no hook count exists for this stem**: its `Q.STEM_TIP_INK` window abstains `occupied`, the two flag boxes being the "other detections" that block it | **unchanged**, still `flags_disagree` (15.5) |

The `compare.py` diff shows only tiles 1, 4, 21 moved. The 22 tiles, 2.69 tree -> 2.74:
**18 right / 2 wrong (1, 21) / 2 narrowed (4, 15) -> 20 right / 0 wrong / 2 narrowed (4, 15).**

### 15.2 What was built

GATHER: `Q.BEAM_STROKE_INK` (`gather.beam_stroke_ink`, `gather_beam_stroke_ink`,
`READERS.CV_BEAM_SHAPE`), one row per `Q.BEAM_STROKE` row (CV and detector), off the
UNERASED cell raster (the staff-erase thins a beam where it crosses a line: one read 34 px
there and 49 on the original): `thickness_ratio` (median ink run through the stroke's
columns / the staff lines' thickness at those columns; `None` where no line is
measurable, never a pixel default), `sagitta_spaces` (the bow of the straightest of centre
line, top edge and bottom edge, so a beam with a slur's tail stuck to it is not read as an
arc), `end_stems` (a vertical run leaving the band at each end, found / not found).
`local_line_thickness` reads each line's 25th percentile over the stroke's columns +/- 3
spaces and takes the SECOND-thinnest line: ink only adds to a line, and the first version
(pooled median) read 54-63 px for a true 23-29 where a beam stood on two lines or a bar of
stems merged, which called real beams hairpins.

ADJUDICATE (`rhythm._not_a_beam_by_ink`, in `adjudicate_duration` after the side and
beyond-the-tip tests): a stroke is refused as `too_thin` (< 1.75 lines), `not_straight`
(> 0.40 spaces) or `one_stem` (no second stem by `Q.STEM` within reach or by the ink at
the ends). **A test that cannot be read abstains and the stroke stays** (no ratio, sagitta
unread, an end unread). A one-stem stroke within a space of a stroke that passes is a
**beamlet** (a dotted rhythm's short second level) and stays. Where the refusals take away
levels the head would have had, it **narrows** (`beam_discounted_uncertain`, head value |
one level, as 2.25b does) instead of deciding its head value from an absence the refusal
made; no `own_stems` condition (a chord head's stem is another head's box). Also: a
`flags_disagree` is settled by a COUNTED hook that is one of the voted levels (unit tests;
idle on tile 15, 15.5). `line_detection.detect_beams(rescue_tall=True)`, passed by the
staged gather only (default False: the legacy pipeline reads exactly what it did).

**Thresholds, both plates.** CV strokes with a stem read at BOTH ends (the surest beams):
Brahms p0-1 172 of 174 read >= 2.5 lines, Litolff p1-3 130 of 131 read >= 2.0; the thin
strokes read <= 1.75 on both, with 2 strokes between 1.75 and 2.0. Hairpin lines read
1.0-1.3. 1.75 is the midpoint of the gap. **The bow cut is the looser ruler**: every CV
stroke at or over the thickness cut reads <= 0.23 spaces but one (a real Brahms beam fused
to a slur's tail, 0.30), the slur arcs 0.18-0.26, so bow alone cannot separate them; the
thickness cut does that work. `not_straight` refused **0 strokes on either plate** (unit
tests only): thick strokes bowed past 0.40 are detector boxes over a whole cluster of ink
(0.4-1.4 spaces) that thinness had already taken or that never counted for a head.

**Cross-staff beam:** the end-stem ruler reads the raster, not the stem set, so a beam whose
far stem stands on the neighbour staff is kept (`TestACrossStaffBeamIsKeptByItsInk`);
`_not_the_neighbours_beam` (2.25b/2.27d) is unchanged. Not exercised by a real page here.

### 15.3 Population (every `Q.DURATION` verdict standing at ADJUDICATE; base `2b6f0741`, arm
`0f880dde`, both CLEAN records, same pages, small re-gathers)

Brahms pdf p0-1: 1,862 verdicts, 1,552 same, **310 changed**.

| old -> new | n |
|---|---|
| decided -> narrowed `beam_discounted_uncertain` | 116 |
| narrowed `beam_certain_not_joined` -> decided | 83 |
| narrowed `beams_ambiguous` -> narrowed `beam_discounted_uncertain` | 52 |
| decided -> decided (value changed) | 41 |
| narrowed `beam_certain_not_joined` -> narrowed `beam_discounted_uncertain` | 10 |
| narrowed `beams_ambiguous` -> narrowed `beams_ambiguous` (candidates changed) | 6 |
| decided -> narrowed `beams_ambiguous`; narrowed `beams_ambiguous` -> decided | 1; 1 |

By value. Decided -> decided: 21 sixteenth -> eighth, 8 32nd -> eighth, 8 quarter -> eighth
(the tile-1 group), 4 64th/128th -> sixteenth or eighth. Narrowed -> decided: 32 `32nd|eighth`,
31 `eighth|sixteenth`, 11 `32nd|sixteenth` -> eighth; 10 -> sixteenth. Decided -> narrowed: 61
eighth, 31 sixteenth, 13 dotted eighth, 6 3/16, 5 32nd/64th, 1 quarter; the eighth is a candidate
in the eighth, dotted and quarter cases and was a REFUSED level in the sixteenth, 32nd and 64th ones.
Litolff p1-3: 1,807 verdicts, **42 changed**: 30 decided -> narrowed `beam_discounted_uncertain`
(29 of them eighth -> `eighth|quarter`), 9 narrowed `beams_ambiguous` -> `beam_discounted_uncertain`,
2 decided 32nd -> sixteenth, 1 candidates changed.

Strokes: Brahms 1,168 (1,166 measured, 2 `no_reading`), Litolff 490 (489, 1). Heads with >= 1
stroke refused by the ink: Brahms 439 (`too_thin` 436, `one_stem` 33, `not_straight` 0), Litolff 89
(82, 7, 0) -- most never counted for the head. The CV rescue added **1 stroke on Brahms (tile 1's
beam), 0 on Litolff**.

**What this costs.** The 116 + 30 decided -> narrowed are heads whose decided value rested on a
non-beam stroke. Brahms page 0's are beamed chords whose CV stems were not read (cell `0/0/0/3` reads ONE
stem for the group) and whose only "beam" was a detector box lying on a staff line -- right by luck, now
honestly narrowed with the eighth first. Of Litolff's 29, the 3 I cropped are whole rests and a half note
(a fermata) boxed as black heads and read eighth by the same junk. EVALUATE's bar arithmetic or INFER's column
rule settles a narrowing; this lane did not price that (first two stages only).

### 15.4 Real beams lost? (the control that could fail)

Refused strokes I eye-checked (debug sheets in the scratchpad, not committed): 16 of the 123 detector
strokes refused as `too_thin` with a stem found at BOTH ends and no CV stroke over their x-range (60 Brahms,
63 Litolff) -- all staff-line residue or a tie lying between two barlines; all 18 CV strokes refused as thin
with a stem at an end (12 Brahms, 6 Litolff) -- slurs and hairpin lines beside a group, ledger pieces under
heads. **No real beam among them.** The kind a tighter ruler would lose is a beam fused to thin ink (Brahms
tile 20's left group: bow 0.30 by centre line, thickness 3.0 lines): kept.

### 15.5 Not done

* **Tile 15** (`flags_disagree`): the settle-by-count path is built and unit-tested (a counted hook that is one
  of the voted levels decides; a count no box voted for, or none, leaves it narrowed), but this stem has no count:
  its `Q.STEM_TIP_INK` window is `occupied` by the flag boxes themselves, and the 2.69 count named in the brief
  reads a DIFFERENT stem (`obs:038697`, x 834). A count at a detector-flagged stem is a GATHER change (the
  blockers); a probe of the reader on this stem without the head cut read `crosses_both_sides`. Not made.
* **Tile 4**: narrowed `eighth | quarter`; the group's own beam is unread (its stems are not).

### 15.6 Sean's question: once ink is a hairpin, can it never be a beam? -- MEASURED, NOT BUILT

The exclusion (2.25b class 3, reverted): a stroke inside a hairpin's box is not a beam. To be built only if it
drops zero real beams on both plates. With the four tests in place, over the strokes a duration verdict used
(200 on Brahms, 145 on Litolff):

* by the gathered hairpin boxes (Brahms 42: 41 `cv_hairpins`, 1 detector): **0** strokes with >= 25% of their
  box inside one, 1 with >= 1%, 0 with the centre inside. **Litolff p1-3: 0 hairpin boxes gathered -- that arm is
  DEAD at zero and is not evidence.** And the CV hairpin reader **never read tile 1's dim.** (no `cv_hairpins`
  box on that staff near x 1000-1750): a hairpin fused to a beam is exactly the ink the reader loses, so the
  exclusion is inert where it matters.
* by the proxy a hairpin's line IS by the ink rulers (thin, straight, refused ink over >= 25% of a counted stroke):
  **12 of 200 Brahms, 6 of 145 Litolff** -- by eye almost all REAL beams, with a slur, a hairpin line or a second
  reading of the same beam lying across them (`out/print/2.74/hairpin-excl/`, 5 crops, the stroke in corner brackets).

So ink read as a hairpin, slur or tie does not stop the stroke beside it being a beam; what refuses a stroke is its
own thickness, bow and stems. The exclusion would drop real beams by the proxy and is unreachable by the reader:
**not built.** (For a stroke measured thin the answer is already yes -- refused by the thickness test, not by the label.)

### 15.7 Files / gates

`tools/omr/staged/gather.py` (`beam_stroke_ink`, `local_line_thickness`, `gather_beam_stroke_ink`), `record.py`
(`Q.BEAM_STROKE_INK`, `READERS.CV_BEAM_SHAPE`), `capture.py`, `adjudicators/rhythm.py` (`_not_a_beam_by_ink`, the
guard, `_at_level_value`, the `flags_disagree` settle), `line_detection.py` (`rescue_tall`),
`tests/test_staged_beam_two_stems.py` (37 tests, RED first: 25 of the first 28 failed on the unrepaired tree, the 3
passing being stays-narrowed controls). Crops `out/print/2.74/` (10 changed heads, `manifest.json` with before/after
readings NOT shown to Sean). Gates at `0f880dde`: `pytest -m "not slow" tools/omr/tests`
**6,511 passed, 11 skipped, 2 xfailed, 0 failed** (2.69's 6,408 + 37 here + main's merged tests);
`python3 -m tools.omr.staged.check` TOTAL **192** (= base).

---

## 16. Two leftovers Sean judged EIGHTHS: 2.65 tile 15 and 2.74 review Litolff 1 (2026-10-09)

Path: STAGED, GATHER + ADJUDICATE only. Branch `lane-rhythm-leftovers`, off `0a06e5c2` (main with 2.69 + 2.74
merged). Sean, 2026-10-09, blind: the Brahms tile-15 head is an EIGHTH; the Litolff head of the 2.74 review is an
EIGHTH. Base and arm are both CLEAN small re-gathers (`dirty: False`), same pages, same machine, base `0a06e5c2`,
arm `b6558cf9`; the brief's two hypotheses were checked and one was REFUTED (B, below).

### 16.1 A -- 2.65 tile 15 (`glyph/1/1/9/0/13`): the flag box blocked its own stem's tip

Cause, measured on the base record. The detector draws ONE printed flag twice, `flag8thUp` (1890,422)-(1956,625) and
`flag16thUp` (1890,427)-(1956,625) on the stem (1884-1896, tip y 407, staff space 66.75): two near-identical boxes, so the
flag-class vote ties 1:1 (`flags_disagree`). 2.74's settle-by-count was built and idle because
`gather._stem_tip_blockers` hands every detection of the cell (width under the staff-width cut) to
`_observe_stem_tip_ink` as "ink the record can already name", and the two flag boxes lie entirely over the stem's own tip window
(x 1896-1956, y 474-574) -> `occupied` before the ink was read. Run on that cell's own raster, the reader counts
**one hook** (`stem_tip_ink` found, right 0.38 / left 0.05; `stem_tip_hooks` hooks 1, support [1.0, 0, 0, 0]), with the
head cut at y 604; without the head cut it reads `crosses_both_sides` (the 2.74 probe), which is why the head edge matters.

Fix (the function is `gather._stem_tip_blockers`, new keyword `own_stem=`; the call site in `gather_cv_lines` now
computes blockers PER STEM): a detected FLAG box that hangs off THIS stem's tip (left edge within 0.6 spaces of the
stem's side, near edge within 0.8 spaces of its top or bottom tip: `STEM_TIP_OWN_FLAG_X_SPACES`,
`STEM_TIP_OWN_FLAG_TIP_SPACES`, `_flag_box_hangs_off_stem`) is set aside. Nothing else is: a flag of ANOTHER stem, a flag
box starting mid-stem, a tie, a beam stroke, anything not a flag box still blocks; `own_stem=None` is the pre-change call
byte for byte. A flag box is never evidence of a hook: the window is still READ off the ink (a flag box over a bare stem
files `found False`, no count). The settle itself is 2.74's, unchanged: a counted hook that is one of the voted levels
decides (`hooks_counted`, `flags_disagree_settled_by_hooks`); a count no box voted for, or none, leaves it narrowed. The
detector's class score is never the tie-break.

This did NOT touch `lane-2.73-line-cut-heads`' tip test (its diff reads `_stem_tip_flag_ink`'s rows in `rhythm.py`; `_stem_tip_blockers` and `_observe_stem_tip_ink` are not in it).

### 16.2 B -- 2.74 review Litolff 1 (`glyph/3/0/7/6/2`): not a beamlet; the heads' own row

The brief's hypothesis (a short secondary stroke kept by 2.74's beamlet rule) is REFUTED. The cell holds three CV strokes
(canonical px, space 100): `obs:036861` [595,494,419,63], the real beam (2.36 line thicknesses, two stems found, kept);
`obs:036862` [395,1088,425,37] (1.25, refused `too_thin`); `obs:036863` [476,1188,350,37]. The third is the one that made
the 16th: **the second ledger line through the row of three heads, fused with them** (thickness 108 px = 1.08 spaces,
3.86 lines, straight, a stem found at one end, a second stem within the join tolerance -> it passes all three of 2.74's
tests) -- 0.80 of its box lies inside the three notehead boxes, and the detector boxed no `ledgerLine` there, so 2.25's ledger
rule never saw it. `rhythm._on_stem_side`'s own docstring names the fault: *"a stroke lying THROUGH the head (the CV opening
fuses a row of heads into one horizontal run) ... is a beam reader's false positive"*. The beamlet rule is not involved:
the stroke is 6 spaces from the primary beam, farther than `BEAM_BEAMLET_GAP_SPACES`, and a beamlet is untouched (control test).

Fix (`rhythm._not_a_beam_by_ink`, first tier, new `_notehead_glyph_boxes`, `_covered_fraction`,
`BEAM_THROUGH_HEADS_MIN = 0.5`, `BEAM_HEAD_BOX_MAX_SPACES = 2.2`): a stroke whose box lies at least half (exact union) inside the
cell's HEAD-SIZED notehead boxes is those heads' ink -- refused `through_heads`, whether or not the ink reader measured
it. It reuses 2.74's refusal plumbing, so rule 8 holds: where it was the head's only mark the head is NARROWED
(`beam_discounted_uncertain`, head value | one level), never decided from the absence. Head-sized matters: the first
version of the rule (commit `34972ddc`) refused a REAL stem-down beam on Brahms p1 cell 1/0/0/4 (`obs:033787`, [143,668,237,56])
because the detector drew a `noteheadWholeOnLine` box 3.2 spaces wide over it (213 x 93 px at space 66.75); a box wider than
2.2 spaces is a cluster, not a head, and with no staff-space unit the rule does not run (`b6558cf9`, RED first on both).

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED beyond Sean's three beam lines: a beam is drawn at the far end of
its stems and runs BETWEEN them, never through a notehead (CLAUDE.md §10); the cuts are 0.5 and 2.2. Falsified by a
print-confirmed beam lying half inside head-sized boxes (a very short-stemmed cluster). My eye-check: the 34 refused strokes
that a base duration verdict USED as a level (23 Litolff p1-3, 11 Brahms p0-1; contact sheets in the scratchpad, not
committed) are all a ledger line through or touching a head or a fused head row; none is a beam but the one the size cut now keeps.

### 16.3 Sean's 22 tiles (`out/print/2.65/compare.py`), base -> arm

20 right / 0 wrong / 2 narrowed (4, 15) -> **21 right / 0 wrong / 1 narrowed (4)**. Only tile 15 moved:
`narrowed flags_disagree 8th|16th` -> **decided eighth**. Tile 4 (the group's own beam unread) is unchanged,
`beam_discounted_uncertain` eighth|quarter. The other judged heads (2.69's 2, 2.74's 10, 2.73's 10) are unchanged except
the target: **2.74 Litolff 1 sixteenth -> eighth (right)**; Brahms 2.74 tiles 1-9 and 2.73 tiles 7-8 identical.

### 16.4 Population (every note-family `Q.DURATION` verdict standing at ADJUDICATE)

| plate | verdicts | changed | what |
|---|---|---|---|
| Brahms p0-1 | 1,491 | **8** | 2 `flags_disagree` -> decided eighth (A: tile 15 and one more); 1 `beams_ambiguous` 8th/16th -> eighth; 2 decided 32nd -> 16th; 1 decided eighth -> narrowed eighth\|quarter; 1 decided dotted eighth -> narrowed dotted 8th\|dotted quarter; 1 `beam_certain_not_joined` -> `beam_discounted_uncertain` (same pair) |
| Litolff p1-3 | 1,286 | **45** | 16 decided 16th -> eighth; 8 decided eighth -> narrowed eighth\|quarter; 6 decided 32nd -> 16th; 3 decided 64th -> 32nd; 3 narrowed 8th\|16th -> decided eighth; 1 narrowed 32nd\|16th -> decided 16th; 8 narrowed -> narrowed (candidates changed) |

`Q.STEM_TIP_INK` (A): Brahms rows read 842 -> **1,006**, windows found 27 -> 92, hooks counted 11 -> **47, every one a single
hook** (no two-hook count on this plate); `occupied` abstentions 1,458 -> 1,294 (164 windows now read). Litolff 674 -> 684 rows,
found 30 -> 33, counted 10 -> 13 (`occupied` 1,704 -> 1,694). These rows feed `flags_disagree` only (a flag-boxed head never
reads them otherwise), which is why 164 more windows moved 2 verdicts. Three Brahms and one Litolff `flags_disagree` remain:
their own tip is still `occupied` by something that is not a flag box, or the head is at that end -> they stay narrowed.

**What this costs.** The 8 + 2 decided -> narrowed are heads whose decided value rested on a heads'-row / ledger stroke:
right by luck (their real beam lay beyond the tip, or was unread -- on `glyph/2/1/7/8/0` the real beam [167,794,571,69] lies 0
inside any head and was not what the base counted either), now honestly `eighth | quarter`. EVALUATE's bar arithmetic
or INFER settles a narrowing; not priced here.

### 16.5 Files / gates

`tools/omr/staged/gather.py` (`_stem_tip_blockers`, `_flag_box_hangs_off_stem`, `_is_flag_detection`, the per-stem call in
`gather_cv_lines`), `adjudicators/rhythm.py` (`_not_a_beam_by_ink`, `_notehead_glyph_boxes`, `_covered_fraction`),
`tests/test_staged_rhythm_leftovers.py` (25 tests). RED first, on the unrepaired tree: A 11 of 15 failed (the 4 that
passed: the legacy call, "today the flag boxes make the tip occupied", and the two call-site controls that draw no flag box over the hook or a tie); B 4 of 7
failed (the 3 passing: a real second level, a dotted-8th beamlet, a stroke near but not through the heads); the size cut: 2 of 3
failed on the previous commit's rule (the control that a head-SIZED box still refuses passed). Crops: `out/print/rhythm-leftovers/`
(10 changed heads Sean has not judged, 5 per plate, `manifest.json` with before/after NOT shown). Gates: `pytest -m "not slow"
tools/omr/tests` **6,559 passed, 11 skipped, 2 xfailed, 0 failed**; `python3 -m tools.omr.staged.check` TOTAL **192** (= base).

### 16.6 Sean's review of the 10 crops (`out/print/rhythm-leftovers-review/`): tiles 5, 7, 8, 9 (2026-10-09)

Sean, blind: all ten are EIGHTHS except 1 (16th) and 2 (dotted quarter). On `b6558cf9` tiles 1, 3, 6, 10 were newly right,
2 narrowed with the answer in it, 4 unchanged narrowed, **8 (read 16th) and 9 (read 32nd) still wrong, 5 and 7 lost a right
decision**. Measured per tile on the record (strokes with their ink rows, stems, heads; scratchpad overlays, not committed):

* **Tiles 8 and 9 (Litolff p3 cells 2/0/3/1 and 2/0/0/5): one printed head SHARED BY TWO VOICES.** The head carries an up-stem
  to a beam above AND a down-stem to a beam below (a unison of two eighth voices); `Q.STEM_DIRECTION` says `stems_disagree`, so
  `side` is `None` and `_beam_levels` counted both beams as levels of one stem: 2 (16th), plus a third stroke on tile 9. That
  third stroke (`obs:020007`, 243 x 32 px, 3.0 line thicknesses, **a stem at NEITHER end**) is a bar under the lower beam (the
  foot of a dynamic letter); `_stems_a_stroke_stands_on` counted it as standing on two stems because stems pass within the
  join tolerance of its box. Not a staff line, not a split beam, not a fused ledger (the ledger-through-heads strokes `020448/9` and
  `020005` were already refused). Fix: (a) a head with a stem each way counts each stem's beams against ITS side only
  (`rhythm._voice_stems`, the `voice_levels` block; the head's level is the voices' range: equal -> that level, different ->
  NARROWED, never one voice's value for both -- `detail.beam_voices`); (b) a stroke the ink READ at both ends and found a
  stem at NEITHER is refused `no_stem_at_ends`.
* **Tile 7 (Litolff p3 cell 3/0/7/4): a real beam was refused as a ledger line, and 2.74's through-the-heads rule then
  removed the stroke that had supplied the (lucky) level.** The detector drew a `ledgerLine` box [405,795,1055,826] over the
  stem-down beam [458,794,412,63] (2.36 line thicknesses, straight, a stem at both ends); 2.25's `_not_a_ledger_line` refuses any
  stroke that overlaps such a box. The eighth on `main` came from the ledger line through the heads (`obs:036811`), right by
  luck. Fix: a stroke that passes every beam test the ink can read -- thick, straight, a stem found at BOTH ends, not lying
  through the heads (`_beam_anchor_ids`) -- is exempt from the ledger-box refusal. A thin stroke, or one with a stem at one end,
  under a ledger box is still a ledger line (tests).
* **Tile 5 (Brahms p1 cell 1/0/3/4): NO beam is lost -- there is none.** The head is the lower one of a pair; its eighth is the
  FLAG at the bottom of its down-stem. `main`'s decided eighth came from the head's own blob (`obs:034934`, 123 x 46 px, 0.93 inside the
  head box) read as a one-level "beam", exactly the false stroke the through-the-heads rule refuses. The flag is not read:
  the stem's bottom tip window is `occupied` by a `tie` box [800,632,306,56] hung under it, and on the raster the window
  reads `right` 0.26 (< 0.30). The hook COUNTER on that stem counts one hook (probe), so the cause is the blocker and the density
  floor, not the mark. Left NARROWED `eighth | quarter` (the answer is in it); NOT fixed: letting a tie box through, or lowering the
  density floor, changes every tip window on the plate and needs its own item.

**Measured (clean re-gathers on the merged tree after 2.71/2.76: base = origin/main `3ec53272`, arm = `61d4c88a`; the same 24 / 74 changes and the same table on the earlier base `f2a0efb1`/`0d08e10c`).** Sean's 10: **7 right** (1, 3, 6, 7, 8, 9, 10), 2, 4 and 5 narrowed with the answer in them, **0 wrong**. Sean's 22: **21 right / 0 wrong / 1 narrowed (4)**
(only tile 15 moved). The other judged heads (2.69's 2, 2.73's 10, 2.74's 10) unchanged except Litolff 1 -> eighth.
Population: Brahms p0-1 **24 of 1,491** changed (4 `beam_certain_not_joined` -> decided eighth, 4 -> `beam_discounted_uncertain` same pair, 3 `beams_ambiguous` candidates changed,
3 `flags_disagree` -> eighth, 3 decided 16th -> eighth, 2 32nd -> 16th, 3 decided eighth -> narrowed eighth|quarter, 1 dotted eighth ->
narrowed, 1 ambiguous -> eighth);
Litolff p1-3 **74 of 1,286**: 32 decided 16th -> eighth, **16 decided quarter -> eighth** (real beams the ledger-box rule had dropped; I
eye-checked 8 of the 16 on crops: all beamed eighths), 4 decided eighth -> narrowed, 3 32nd -> eighth, 3 32nd -> 16th, 2 64th -> eighth,
and 14 narrowed -> decided/narrowed. `Q.STEM_TIP_INK`: Brahms found 28 -> 104, counted 11 -> 52 (all single hooks).
Crops of 10 changed heads Sean has not judged: `out/print/rhythm-leftovers-2/` (head 7 is the false notehead box over tile 7's beam:
expect "not a note").
Tests: `test_staged_rhythm_leftovers.py` now 33; RED first on `b6558cf9`: 4 of the 8 new tests failed (tiles 7, 8, 9 on real
measured geometry, and the voices-that-differ range); controls (one stem, thin stroke under a ledger box, one-end stroke, a
row through heads alone) stayed green.

Gates at `61d4c88a`: `pytest -m "not slow" tools/omr/tests` **6,769 passed, 11 skipped, 2 xfailed, 0 failed**; `staged.check` TOTAL **193** (= origin/main's 193). The merge conflict with 2.71 was in `gather_cv_lines` only (per-stem blockers vs the new `slashes=` argument): both kept; 2.73 touched no stem-tip function.

### 16.7 2.77b -- Sean's second review (`out/print/rhythm-leftovers-2/`): crops 9, 8 and 7 (2026-10-10)

Path: STAGED, GATHER + ADJUDICATE (the gate); EVALUATE reported beside it. Branch `lane-2.77b`, off `origin/lane-rhythm-leftovers`
`eae25f3c`, merged with origin/main `655407c2` (2.12f, 2.78) -- the merge was clean. **Base** = that branch tip + main with no 2.77b change
(`25c2c276`), **arm** = `33557d81` (the same + the three changes); both are CLEAN small re-gathers (`dirty: False`) of the two count pages on
one machine, each `--through adjudicate`. Sean's round 2 at the start: 1, 3, 5, 6, 10 newly right; 2 and 4 narrowed with the answer; 8 lost a
right decision; 9 still wrong; 7 is not a notehead (his words: *"a beam that connects 8th notes but is not a notehead"*).

**A -- crop 9 (`glyph/2/0/3/1/4`, Litolff p3, a printed EIGHTH read a 16th).** Verified on the print and the record: the head hangs below staff
2, its stem runs UP 4.45 spaces (`Q.HEAD_STEM_REACH` up, tip y 672) to a beam on staff 2's top line. The detector boxed it twice
(`glyph/2/0/2/1/3` in staff 2's cell, `glyph/2/0/3/1/4` in staff 3's padded cell); `glyph_owner` names staff 2 for both
(`stem_toward_staff`). The staff-3 copy counted two strokes of STAFF 3's own group (a beam below the head, against a stem that runs up):
`stems_attached` 0, `beam_side` None because its direction came from `beam_mate` (`down`, borrowed from those very strokes),
`beams_neighbour_staff` 0 (judged against the FILED staff). The staff-2 copy, the one EXPORT writes, decided a QUARTER: nothing at its stem tip
was ever read. Three changes, ADJUDICATE (`rhythm.py`):
* **The loser abstains** (`owned_by_another_staff`) where the owner staff holds a TWIN of the mark (a `Q.MARK_GROUP` member on the owner's
  staff). A lone copy keeps its duration (a first version without the twin test broke `test_dot_not_a_note`'s "note owned by another staff" and
  would have starved `OMR_RELOCATE_AT_EXPORT`'s own population). EXPORT counts it under the name it always had (`export.py`, 8 lines, so
  `status_census` does not read it as a reading gap). Litolff p0-3: **130 of 1,286** duration verdicts, Brahms p0-1 **84 of 1,491** (values
  nothing writes, which every population count included).
* **A head's beams are the ones its OWN stem reaches, also where the CV found no stem** (`_own_stem_side`): `Q.HEAD_STEM_REACH`'s up/down
  becomes the side where no `stem_projection` was decided, and a beam on the far side is not the head's. MEASURED, not chosen: the ruler agrees
  with the head's own CV-stem direction (`stem_projection`) on **306 of 307** heads at 2.0 spaces of run or more (100% at 2.0-2.5, 100% at
  2.5-3.0, 208 of 209 over 3.0) and on 27 of 29 at 1.5-2.0 and 23 of 30 under 1.5 (a stacked neighbour's ink). `REACH_STEM_MIN_SPACES = 2.0`, also
  the CV stem finder's own floor. The first version had no floor and narrowed Brahms eighths whose stem runs down (a neighbouring head's 1.06-space
  run read `up`); the floor removed 12 of those 20 Brahms changes.
* **RULE 8 for the same heads** (`beam_discounted_uncertain`, the 2.25b/2.74 shape): a head with a RULER stem and no CV stem whose only candidate
  strokes were discounted (the neighbour's beam, a decided arc) or put on the far side is NARROWED, eighth | quarter, never decided a quarter from
  the absence of a mark: its tip was never examined.

Why crop 9's owner is not decided EIGHTH here (the "can the beam be read" question, answered): the CV stem finder finds no stem for it. Two heads
a second apart fuse in the vertical opening into ONE component 127 px wide against a 60 px cap (`RUN_TOO_WIDE`; canonical px, space 100: x 578,
w 127, y 427-1004), and `detect_beams` needs two anchor stems that END at a slab; the slab at the stem tip (x 331-877, y 426-553, ON staff 2's
top line) has one. The existing column-profile reader finds both: with `detect_stems(enable_stroke_reader=True)` the cell returns the stem
(x 667, y 427-985) and the beam (331, 426, 546, 127). `OMR_STEM_STROKE` is default OFF (2.17 priced it at file level on Breitkopf p1: +450 stem
rows, `duration_narrowed` unchanged, notes written 226 -> 222) and I did NOT flip it. **Experiment, Litolff p0-3 only, arm code with
`OMR_STEM_STROKE=1`** (own out-root, scratch): crop 9's owner reads **eighth, decided** (right) and none of the 20 judged heads reads worse; but 81 of
1,286 duration verdicts change and narrowed rises 81 -> 109 (10 quarter -> eighth, 12 narrowed -> eighth, 34 quarter -> narrowed, 7 -> `beam_certain_not_joined`).
Not priced on Brahms, not print-checked beyond the judged heads. **The reading is a GATHER item on the stem finder for stacked heads, not a
duration rule; it needs its own roadmap row.** Population of the ruler-only heads (owner, stem read by the ruler, no CV stem, nothing read at the
tip, decided a quarter): 10 on Litolff p0-3 and 16 on Brahms p0-1; my eye-check of their crops (not Sean's): about a third print a flag or beam
the record never reads, the rest are plain quarters or halves -- which is why they are NOT all narrowed (that would turn about as many right
answers into narrowed as wrong ones), only the ones that had a candidate stroke taken away.

**B -- crop 8 (`glyph/2/1/7/13/1`, an EIGHTH right before 2.77).** Verified: a 4-head chord under a SLOPED beam, `obs:023316`
[211,629,482,139], 2.72 line thicknesses, straight; the ink reader's end window found a stem at NEITHER end although four CV stems END inside its
box (three tips, y 687, 706 and 738, inside 629-768; a fourth 39 px under it). 2.77's `no_stem_at_ends` refused it, and the other stroke
(`obs:023317`, a 114-px band through the row of heads) was refused by `beams_ledger_line` -- CORRECTLY: it is the ledger line through the heads (a
`ledgerLine` box overlaps it), not a beam; the ledger-box rule took nothing it should not have. Fix (`rhythm._stems_ending_in`,
`BEAM_STEMS_ENDING_MIN = 2`): a stroke the ink read with no stem at either end is still refused UNLESS two or more DIFFERENT read stems end inside its
box -- a stem each side of a beam (Sean, 2.74), counted off the CV stem rows. Measured over the 109 strokes the ink read at both ends with a stem at
neither (thick, straight; Litolff p0-3 and Brahms p0-1): **5 have two or more stems ending inside, all 5 are printed beams on the page crops** (4 of 5
detector boxes; the ink end window misses the stem of a sloped beam); the dynamic letter's foot bar 2.77 was built to refuse has none (its stems
end 24-36 px above it) and stays refused; 5 have exactly one and 99 none (not eye-checked; they stay refused, as before). A tolerance of the join's
size (80 px) would have credited the foot bar, so the test is INSIDE the box.

**C -- crop 7 (`glyph/3/0/7/4/13`, Litolff p3).** `noteheadBlackInSpace`, 1.23 x 0.69 spaces, 85% inside the stem-down beam `obs:037765`
(66 px thick, straight, a stem found at BOTH ends). **A flatness floor is measured NOT to be a test** and was not built: print-confirmed heads of the
notehead-width crop pass (a model reading the print, not Sean) include 6 of 102 boxed 0.34-0.69 spaces tall (a head the crop cut, a partial box over
one head of a stack), and Sean's 361 hand-confirmed Brahms p0 boxes (`data/hand-truth/pages/imslp317803/0.json`) include four under 0.8 (one is a
dot, mislabelled; two are partial boxes over heads of stacks; one is a real wide flat head) -- no height separates them from the crop-7 box. The
refusal needs the beam as a second witness (`notehead_precision._beam_piece_refusal`, reason `is_a_beam_piece`, ONE call in
`adjudicate_notehead_is_not_a_notehead`, between the `is_a_dot` return and the 2.49 tremolo call): a REGULAR-head box (`geometry.is_regular_notehead`:
never a `*Small` cue head, never a whole note) at least **0.7** inside a stroke that passes the 2.74/2.77 beam tests (thick, straight, a stem at both
ends or two read stems ending inside) AND no taller than **0.9** spaces. Margins, over every detector notehead box of both re-gathers (Litolff
1,286, Brahms 1,491): the share inside a read beam stroke is **0.21 at most over Sean's 361 hand-confirmed heads** (re-measured on the arm
record); the boxes covered by 0.5 or more fall into two groups by height, 0.69 and 0.75 (crop 7 and one 4.1-spaces-wide box on a beam) and
1.10 and up (head-sized boxes under the bounding box of a SLOPED beam) -- nothing between 0.75 and 1.10, and the cuts sit in those gaps. Population:
**2 boxes** refused, both Litolff p3 and both beams on the print crop: crop 7 (`notehead` -> `is_a_beam_piece`) and `glyph/2/0/8/13/9`, a stem-up
group's beam, which was already refused as `stacked_head_duplicate` (the reason changed, nothing else). Brahms: 0. Expected merge conflict with
any lane touching `adjudicate_notehead_is_not_a_notehead`: the added call, and the `reasons=` / `composed_from` / `wants` tuples of that decorator
(`Q.BEAM_STROKE`, `Q.BEAM_STROKE_INK`).

**Sean's 20 heads (both rounds), one line each** -- ADJUDICATE, the head a file would carry (the surviving box of the print head, the owner's
copy), base -> arm; regenerated from the two record sets by scratch scripts (not committed):

| tile | Sean | base | arm | class |
|---|---|---|---|---|
| R1-1 Brahms | 16th | 16th | 16th | right |
| R1-2 | dotted quarter | narrowed | narrowed | narrowed with the answer |
| R1-3 | eighth | eighth | eighth | right |
| R1-4 | eighth | narrowed | narrowed (eighth / quarter) | narrowed with the answer |
| R1-5 | eighth | narrowed | narrowed (eighth / quarter) | narrowed with the answer |
| R1-6 Litolff | eighth | eighth | eighth | right |
| R1-7 | eighth | eighth | eighth | right |
| R1-8 | eighth | eighth | eighth | right |
| R1-9 | eighth | eighth | eighth | right |
| R1-10 | eighth | eighth | eighth | right |
| R2-1 Brahms | 8th | eighth | eighth | right |
| R2-2 | 8th | narrowed | narrowed (eighth / quarter) | narrowed with the answer |
| R2-3 | 8th | eighth | eighth | right |
| R2-4 | 8th | narrowed | narrowed (eighth / quarter) | narrowed with the answer |
| R2-5 | 8th | eighth | eighth | right |
| R2-6 Litolff | 8th | eighth | eighth | right |
| **R2-7** | not a notehead | decided eighth | **refused, `is_a_beam_piece`** | **right** |
| **R2-8** | 8th | narrowed | **eighth, decided** | **right** |
| **R2-9** | 8th | quarter (the written copy; its twin read a 16th) | narrowed (eighth / quarter); the twin abstains | narrowed with the answer -- **not right** |
| R2-10 | 8th | eighth | eighth | right |

**No judged head ends worse.** Tiles 7 and 8 are right; tile 9 is NOT: the written copy was wrong and is now narrowed with the answer in it, and the
copy that read a 16th no longer reads anything. The 44 heads of Sean's earlier reviews (2.65's 22 tiles, 2.69, 2.73, 2.74) read identically (0 changed
of 44 matched, by box overlap). Through EVALUATE (the log rebuilt from each record with row ids remapped, then `adjudicate.run` and `evaluate.run`,
base and arm each on its own tree): the 20 read the SAME on base and arm; against ADJUDICATE, `share_stem_value` (2.78) settles R1-2 to a dotted
quarter (`stem_value_follows`, right) and `reconcile_chord_duration` (`chord_mate_shares_the_stem`) decides R1-4 a QUARTER (wrong, on base as well:
not this lane's).

**Population (every note-family `Q.DURATION` verdict at ADJUDICATE, base -> arm):**

| plate | verdicts | decided | narrowed | abstained | changed | of which the loser abstaining | written heads changed |
|---|---|---|---|---|---|---|---|
| Litolff p0-3 | 1,286 | 1,190 -> 1,075 | 96 -> 81 | 0 -> 130 | 146 | 130 | **16** |
| Brahms p0-1 | 1,491 | 1,225 -> 1,158 | 266 -> 249 | 0 -> 84 | 91 | 84 | **7** |

The 23 written-head changes, old -> new: decided quarter -> narrowed (eighth | quarter) 9; decided eighth -> narrowed 4; decided dotted quarter ->
narrowed (0.75 | 1.5) 1; narrowed -> decided eighth 3 (crop 8's chord); narrowed -> narrowed (the reason or the candidates) 6. The decided -> narrowed
ones are heads whose answer rested on a far-side or neighbour's stroke, or on the absence of one under a stem nobody examined (my eye on the crops,
not Sean's: about as many print a flag or beam the record never read as print the plain value). `Q.STEM_TIP_INK` is identical on both arms
(Litolff 970 rows / 39 found / 13 counted, Brahms 1,219 / 104 / 52): no GATHER row moved.

Crops of 7 changed heads Sean has not judged: `out/print/rhythm-leftovers-3/` (`manifest.json`, readings hidden). Only 7 exist because only 7 written
heads changed and are unjudged; tiles 2, 4 and 6 are members of crop 8's own chord (one beam), tile 5 is a plain dotted quarter that now narrows.

Tests `tools/omr/tests/test_staged_rhythm_2_77b.py`: 24, RED first on the unrepaired tree (6 failed: the loser, the ruler's side x2, crop 8 and the
two-stem bar, crop 7; the controls -- a thin stroke, a stroke no stem stands on, a half-covered box, a flat box away from any beam, a cue head, a
head-sized box, stems that end above a bar, one stem inside, an owner, an abstained owner, a lone copy -- green throughout). Gates at `33557d81` (code
identical to the final head): `pytest -m "not slow" tools/omr/tests` **6,900 passed, 11 skipped, 2 xfailed, 0 failed**; `staged.check` TOTAL **193**
(= base; every check's count identical). ⚠️ A rebuild of a record into a fresh `Log` (the `readjudicate` pattern) MUST remap row ids: the first
rebuild here reproduced nothing that joins through `beam_row_id` (the crop-7 box read `notehead`, not `is_a_beam_piece`) until the ids in each row's
detail were remapped.

## 17. ROADMAP 2.81 PHASE 1 -- a stem with nothing on it: how often is it a quarter? (2026-10-10)

Path: STAGED, GATHER + ADJUDICATE for the hand-truth score (CLAUDE.md §6b), the overnight record's later stages for (c). Lane
`lane-2.81-bare-stem`, off main `46b35ad5`. **No product code changed**; nothing here builds the rule. Sean, 2026-10-10 (DECISIONS):
a stem with nothing on it *"is most likely going to be a quarter note ... if it is right 95% of the time we keep that rule; if it is
lower ... send it on to the other stages with a high likelihood of being a quarter note and make sure the bar math adds up"*.
Everything below is regenerated by `probe/l281_run_all.sh` (machine-local; outputs in `probe/out/l281/`); the Brahms 5.3 GB overnight
record is STREAMED with `ijson` (CLAUDE.md §5a: `load_record` is ~6.6x the file), and `l281_control.py` checks that reader against
`readout.load_run` on the 208 MB quick record: **identical on all 1,491 heads, and a one-head perturbation is reported different**.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (rule 3; nobody was asked about the derivations, though the BOXES are Sean's):
(1) a head's written value is readable off Sean's boxes: it STANDS ON the stem box that touches it (x within 0.35 spaces, y within 0.35 of
its box: his stem boxes start where the head's ink ends), the beams whose x covers that stem and whose y reaches within 2.6 spaces of its
far end, and the flag boxes at that end, are its levels; a dot belongs to the nearest head in y -- falsified by a head whose crop shows
otherwise (one was found, 17.3); (2) "the stem's tip" is its end farther from the head; (3) the strict tip test's two numbers (a stroke
box within 0.6 spaces of the tip, x within 0.3 of the stem) are mine and unconfirmed.

### 17.1 The population, from the tree

`rhythm.adjudicate_duration` returns the narrowing `beam_discounted_uncertain` iff every stroke that could have been this head's beam was
refused (a neighbour staff's beam, a decided arc's ink, a far-side stroke, or 2.74/2.77's ink tests) AND the head is not hollow AND no
flag is attached AND the cell's beam reader ran (`none_over_this_note`). Its two candidates are always LEVEL 0 (the head's own value, dotted
if dotted: quarter 1.0 or 1.5) and LEVEL 1 (0.5 or 0.75) -- **and it ranks level 1 above level 0 (`support=2.0 if level == 1 else 1.0`)**, the
opposite of Sean's ruling. **P = a head ADJUDICATE KEPT (not refused, not given to another staff) whose standing duration verdict is that one.**
Defined over the overnight records `*-mvt1-whole-20261010-night` (main `26fdb4d0`, dirty False):

| | heads | narrowed | **P** | tip `clean` (window) | ... and NO stroke box at the tip | no decided stem | tip `occupied` | hook seen |
|---|---|---|---|---|---|---|---|---|
| Brahms (Breitkopf) | 24,260 | 3,860 | **3,604** | 1,825 (50.6%) | **1,197** (33.2%) | 1,167 (32.4%) | 562 (15.6%) | 46 |
| Litolff | 11,399 | 793 | **584** | 180 (30.8%) | **133** (22.8%) | 269 (46.1%) | 127 (21.7%) | 3 |

(P is the STANDING population; UNDECIDED.md's 1,976 / 329 are the part that moved kept -> narrowed overnight.) What fed the refusal, per member
(a member can have several): an ink refusal 2,554 / 401 (`too_thin` 2,464 / 319), a decided arc's stroke 1,578 / 95, a neighbour staff's
beam 630 / 117, a far-side stroke 941 / 75. A dot is attached on 1,837 of Brahms' 3,604 (the 6/8 dotted quarters), on 1 of Litolff's 584.

### 17.2 Does a positive "tip seen clean" reading exist?

**Not as such.** `Q.STEM_TIP_INK` (reader `CV_STEM_TIP`; the brief's `Q.CV_STEM_TIP` is the READER, not a quantity) is one row per stem END:
`value True` = flag-shaped ink in a window 0.9 spaces wide to the stem's RIGHT, **1.0 to 2.5 spaces back from the tip** (`gather.
STEM_TIP_INK_NEAR/FAR_SPACES`), dense >= 0.30 with the left band <= 0.20; `False` = the window was READ and held none; an ABSTENTION
(`occupied`) where any `Q.BEAM_STROKE` box or other detection overlaps the window. So (i) a `False` row is a real positive reading of "no flag
ink in that window" -- Brahms 1,825 of P, Litolff 180; (ii) **it cannot see a beam**: a primary beam lies across the tip itself (0 to 0.5 spaces
from it), outside the window; (iii) it is `occupied` for 16% / 22% of P (any `Q.BEAM_STROKE` box in the window abstains it, the refused strokes
included); (iv) 32% / 46% of P have no decided stem at all (`Q.HEAD_STEM` abstained `no_stem` 1,105 / 227, narrowed `two_stems` 62 / 42), so
there is no tip to read; (v) it misses a flag near its cut (a flagged eighth read `right 0.2693` against 0.30, 17.3). "No beam found" is not
"tip seen clean", and here it is worse: the head is IN P because a stroke WAS found and refused. The stricter definition used below -- window
clean AND no `Q.BEAM_STROKE` box (CV or detector, accepted or refused) standing within 0.6 spaces of the stem's tip end -- is built from rows the
record already holds (`l281_population.stroke_at_tip`), is a PROBE definition and not a gather reading, and leaves 1,197 / 133 members.

### 17.3 (a) Sean's hand truth: Brahms 317803 pdf 0

Truth: `data/hand-truth/pages/imslp317803/0.json` (read, never written), 89 fully labelled measure cells, 339 truth heads in them, 321 with a
stem box (the other 18, 15 of them in cells `s0-st3-m5/m6`, have none). Record: the small re-gather of this tree (`acceptance_quick --doc
brahms1-breitkopf`, GATHER+ADJUDICATE, `46b35ad5`, clean, 569 s) and the overnight record -- **identical on every page-0 member** (91). Matched
with the scorer's own `hand_truth.score.match_boxes` (IoU >= 0.3; 74 of the 76 judged at IoU >= 0.99, min 0.78, so the frame is the same). Of
the 91: 11 sit in cells not fully labelled (unscored), **4 have no truth head under the box** (false heads: a quarter there is invented),
**76 are judged**.

| stratum (tip status) | right | wrong | precision | 95% Wilson |
|---|---|---|---|---|
| **all 76 judged** | 54 | 22 | **0.711** | 0.600-0.800 |
| same, by independent stem/beam/flag GROUP (44 groups) | 37 | 7 | 0.841 | 0.706-0.921 |
| tip `clean` (window), any | 31 | 5 | 0.861 | 0.713-0.939 |
| ... and NO stroke box at the tip (the strict reading) | **10** | **0** | 1.000 | 0.722-1.000 |
| ... a stroke box at the tip | 21 | 5 | 0.808 | 0.621-0.915 |
| tip `occupied` | 3 | 1 | 0.750 | 0.301-0.954 |
| no decided stem | 20 | 16 | 0.556 | 0.396-0.705 |

**The 22 wrong are all level 1 on his boxes** (none is a hollow head): **17 beamed eighths** -- a thick slanted beam at the stems' tips,
**THREE beam groups of 5, 6 and 6 heads** (staff 0 bars 3 and 4, staff 1 bar 5), so one refused beam is 5-6 wrong heads -- and **5 flagged
eighths** (4 groups). 16 of the 22 have no decided stem (the reader found no stem under a head whose stem runs through the staff), 5 are
tip-`clean` (4 beamed: the window `right` band reads 0.0 on all four, a detector beam box lies at the tip, refused `too_thin` at ratio 1.1-1.3
or discounted as a decided arc's ink -- and one flagged, read 0.269 against the 0.30 cut), 1 is `occupied`. The ink test's ratios on the
strokes at a tip do not separate wrong from right (wrong 1.0-1.3 and 2.65; right 1.0-1.58): on this plate the staff lines are thick and a
real beam measures 1.3 of one. Crops: `out/print/2.81-hand-truth-check/wrong_cases/` (22, clean, bracket on the head), `bare_heads/` (the 54).

**Sean's page is not complete, and the "right" count rests on it.** Looking at the 54 heads' crops at stem length (my eye, not Sean's):
**one is a head his boxes call bare whose stem carries a printed flag he did not box** (`glyph/0/0/9/2/2`,
`out/print/2.81-hand-truth-check/g0_0_9_2_2_flag_unboxed_*.png`): with it counted wrong, 53/76 = 0.697 (0.587-0.789), no_stem 19/36.
The strata that matter are untouched (the strict stratum's 10 heads were looked at). Also: dots agree on 71 of 76 (3 missed, 1 read where
his page has none, 1 doubled). **Sample cautions:** one page; three beam groups carry 17 of the 22 wrong heads (so the by-group row, 7 wrong
groups of 44, is the honest unit and the per-head interval understates the uncertainty); and 10/10 is a Wilson LOWER bound of 0.722, not
evidence for 0.95 (an error-free sample needs n >= 73).

**A raster reading of the tip is buildable, on this page.** `l281_tipprobe.py` measures the ink hugging each judged head's stem end (0.45
spaces past it to 1.5 back, both sides, staff-line rows and his non-beam/flag boxes left out): wrong heads read 0.08-0.27 (median 0.229),
right heads 0.0-0.238 (median 0.048); at a cut of 0.072 (CHOSEN ON THIS PAGE, using his stem boxes) it keeps 38 of the 54 bare heads and passes
0 of the 22 wrong. It says the reading can be made; it is not a validated one.

### 17.4 (c) What the later stages already do with P

EVALUATE (`reconcile_duration`, `share_stem_value`, `reconcile_chord_duration`) settles some by the bar's arithmetic; **INFER's two duration rules
settle essentially none**: over ALL heads they wrote 9 duration verdicts on Brahms and 3 on Litolff, and 0 / 1 of P (the stage control: INFER ran,
`222 inferred` on Brahms in all, but this population is outside the neighbours-agree rule's reach).

| | P | settled by a later stage | by what | to level 0 | to level 1 | still narrowed |
|---|---|---|---|---|---|---|
| Brahms | 3,604 | 217 (6.0%) | `reconcile_duration` 177, `share_stem_value` 30, `reconcile_chord_duration` 10; INFER 0 | 194 | 23 | 3,387 |
| Litolff | 584 | 113 (19.3%) | `reconcile_duration` 76, `share_stem_value` 21, `reconcile_chord_duration` 15; INFER 1 | 103 | 10 | 471 |

Every settled value is one of the narrowing's own candidates. The bar arithmetic lands on level 0 for ~90% of what it settles, and it settles
2 of the 76 hand-truth members (both level 0, **both right, 2 of 2**): too few to say how right it is. The other ~94% of Brahms' P reaches
EXPORT narrowed (`duration_narrowed`, counted, not written).

### 17.5 (b) The blind tiles: `out/print/2.81-review/`

34 tiles, `manifest.json` (OUR reading and every other hidden field -- not for Sean), `answers.template.json`, `frame_control.txt`. Question on
every tile: *what is the printed value of the note in the red brackets?* Nothing is drawn but a red corner bracket. 600 dpi from the edition PDF
by `render_page` (the gather's raster), normalised to 32 px per staff space (Litolff is ~15 natively); the window holds the head's whole stem
(from its `Q.STEM` row) and 1.6 spaces past its far end.

**Sample: 30, seed 20261010.** Frame = P of both overnight records MINUS Brahms pdf page 0 (it has an answer already). Two strata, each drawn
at random, so the rule's candidate subset is not diluted by the 66% of P it will not apply to: **A (20)** = decided stem, tip window clean, no
stroke box at the tip (Brahms 14 of 1,181, Litolff 6 of 133); **B (10)** = every other member (Brahms 6 of 2,332, Litolff 4 of 451). Both
strata's frame sizes are in the manifest so a population figure can be weighted back. **Plus 4 controls** (`control_1..4`, taken from the
hand-truth page at a seed+1): two heads his boxes show BEAMED (the answer must not be a quarter) and two BARE. If his answers on them disagree
with his boxes, the derivation or the tiles are in doubt and `l281_tilescore.py` says so before it prints anything else.

**Frame control (can fail):** the head's box darkness vs the same box moved 1.6 head-widths either way beats both on 33 of 34 tiles (the one,
`control_4`, is a head of a beam group: its neighbours are dark too); the same measure on the page shifted 1.6 widths passes **0 of 34**. I looked
at all 34 tiles in contact sheets before the commit.

**Scoring Sean's answers:** `python3 benchmarks/omr-missing-notes-2026-09/probe/l281_tilescore.py --dir out/print/2.81-review --answers
answers.json` (his words per tile; right = a quarter or dotted quarter; wrong = anything shorter or longer; a rest / a dot = "not a note", counted
apart): per stratum and per movement with Wilson, the wrong tiles listed with our reading, the dot agreement, and a stratified population estimate.
A pipeline test on made-up answers (not committed) passes. **30 error-free tiles bound the rate only at 0.886; 20 in stratum A at 0.839.**

### 17.6 What this does and does not say (for Sean; not a verdict)

* **No bar-clearing number exists yet.** Page 0's best honest figure for the rule as Sean stated it, on every member with no tip requirement, is
  **0.71** (0.84 by independent group); with the window-clean tip requirement 0.86 (0.71-0.94); with the strict tip reading 10 of 10 (>= 0.72). All
  below 0.95 on any lower bound, from ONE page; the tiles are what can move it, and they can only bound it at 0.886.
* **The existing tip reading is not the witness Sean's rule needs.** It is blind to the beam, the commonest way a "bare" stem is not bare in P
  (17 of the 22 wrong here, in 3 groups); half of Brahms' P (49%) and 69% of Litolff's is outside it altogether (no decided stem, `occupied` by
  the refused strokes, or a hook seen), and two thirds / three quarters is outside the strict reading.
* **The narrowing already ranks the eighth over the quarter** (support 2.0 vs 1.0). On page 0 level 0 is right for 54 of 76. If the result is
  "below 95%, carry a likelihood", that ordering is the first thing that is backwards.
* **2.74's `too_thin` refuses real beams on this plate** (all 17 beamed wrong heads): a finding for that item, not measured further here.

### 17.7 Where the brief and the tree disagree

(1) "INFER may already settle many with bar math": it settles 0 of 3,604 / 1 of 584; EVALUATE settles 6.0% / 19.3%. (2) "Q.CV_STEM_TIP": a reader
id; the rows are `Q.STEM_TIP_INK`. (3) "boxes stems, beams, flags, dots and heads with all the ink": stems are missing on 18 heads and a printed flag
is unboxed (17.3). (4) The 2.81 ROADMAP row's "~1,976 of 1,991" is the overnight DELTA; the standing population is 3,604 / 584. (5) The sample is
stratified (17.5), not a simple random draw: a simple one would put ~8 tiles on the rule's own subset.

### 17.8 Files

`probe/l281_*.py` (extract, control, population, truth, score, later, wrong, tipprobe, tiles, tilescore, sheet/view/show/row/unmatched/montage/peek,
`l281_run_all.sh`), `probe/out/l281/` (population CSVs per record, `hand-truth-score-*.txt`, `later-stages-*.txt`, `tip-ink-probe.txt`,
`tiles-our-reading.txt`), `out/print/2.81-review/` (the tiles), `out/print/2.81-hand-truth-check/` (the crops above). `staged.check` TOTAL **192**
(= main, re-run with the probes in the tree). No test was added or run: no product code changed.

### 17.9 The misses in context (Sean, 2026-10-10: *"Can we look closer at the 1/4 of quarters that are missing - I would like to see if I can identify some patterns"*)

`out/print/2.81-misses/` (`miss_01.png` ... `miss_16.png`, `manifest.json`, `table.txt`): 16 phone-sized images (1000 px wide, panels
stacked): the clean print with a red bracket on the miss, then the same crop with OUR reading drawn on -- the stem we attached or "no stem
decided", every stroke refused as a beam with the test that refused it, any beam kept, the tip window, any flag box. Images 1-8 are Sean's
tiles 04, 09, 27, 22, 02, 11, 29, 07; 9-11 the three beam groups of the hand-truth page (17 heads); 12-15 its flagged eighths (the two heads
sharing a bar in one image); 16 the flag the page does not box. The hand-truth page is the CORRECTED one (1,346 boxes): the same 22 wrong.
`table.txt` is the manager's table of MEASURED FACTS (no conclusion): per head the tip state and the tip window's right/left densities
against the 0.30/0.20 cut, the stem, the distance from the stem tip to the nearest candidate stroke, the counters; per stroke its refusal,
thickness against 2.74's 1.75, bow, stems at its ends, size, slope estimated from the box, over/under the heads, and where it sits against the
LOCAL staff lines (read off the print at the crop: the record's global lines are 0.36-0.62 spaces off at Brahms pdf 20 and 7).

**How the per-stroke refusals were got.** The saved verdicts carry counts, not which stroke each count was. `probe/l281_miss_rebuild.py`
re-runs ADJUDICATE over one page's saved GATHER rows (streamed out of the overnight records with `ijson`; ids remapped as FINDINGS 2.77b
requires) with the stroke filters in `rhythm.adjudicate_duration` wrapped to note what each was given and dropped (results returned
unchanged). **Control, every page:** each saved `adjudicate_duration` verdict on the page is reproduced exactly (Brahms p0 507/507, p2 996,
p7 861, p20 955, p24 1,648, p25 1,165; Litolff p10 888, p13 1,202, p15 1,268), and the break that must fail (every stroke on page 0 made
thick) moves 42 verdicts. Each image's frame control: every bracketed head holds more ink than the same box moved diagonally by 1.6 head
widths (all 16 pass; the stroke-box numbers are recorded, not gated: a detector box is loose around its stroke).

Run it all: `SCRATCH=... probe/l281_miss_run_all.sh` (machine-local).

## 18. ROADMAP 2.83 -- the eighth flag at the stem tip: read where Sean's flags actually are (2026-10-10)

Path: STAGED, GATHER + ADJUDICATE only (CLAUDE.md §6b); EVALUATE, INFER and EXPORT were not run. Lane `lane-2.83-flag-tip`, off the
coordinator's `faf913f4` (the commit that opened 2.83); the arm is `b438cda7` (code) -- `e6aa75ab` is the same code plus committed probe
outputs. Sean, 2026-10-10 (DECISIONS): *"There are 8th note flags that are not being seen. We need to make sure the reader box is big
enough. Sometimes the flag stays closer to the stem at the tip but the flag shape is undeniable."* Everything below is regenerated by
`probe/l283_*.py` (machine-local, outputs in `probe/out/l283/`); cached erased cell rasters (`l283_cells.py`) let the reader be iterated on
the REAL raster in seconds, and every number that decided a cut was then re-measured on a real re-gather.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (rule 3): the BOXES are Sean's, the reading is mine. (1) A flag is ink hanging
from the stem at its tip, on the stem's RIGHT, whose shape is a root at the tip and an arm back toward the head (the two cut sets in 18.3);
(2) the cut values are measured on ONE plate (Brahms 317803) and checked by eye on Brahms pdf 1, 20, 25 and Litolff pdf 3 -- assumed beyond
it; (3) "cannot tell" stays a decline (rule 8) and is never turned into "no flag". Falsified by an eighth Sean confirms that reads `None` or
`False` at its true tip, or a non-flag that reads `True`. NOT CONFIRMED with Sean: tiles in `out/print/2.83-review/` are unjudged.

### 18.1 Where Sean's flags stand against the tip (measured, local staff spaces)

`probe/l283_flag_geometry.py` over his hand-truth page (Brahms pdf 0, `data/hand-truth/pages/imslp317803/0.json`): **34** `flag8th*` boxes
(the brief said ~31), 29 with a stem box of his; space 32.0 px. t = spaces from the stem's true tip toward the head, u = spaces right of the
stem's right edge:

| measure (n=29) | min | p10 | median | p90 | max |
|---|---|---|---|---|---|
| flag box starts at t | -0.19 | -0.09 | **0.07** | 0.30 | 0.43 |
| flag box ends at t | 2.82 | 2.94 | 3.12 | 3.54 | 3.76 |
| flag box right edge, u | 0.84 | 1.00 | 1.13 | 1.22 | 1.97 |
| ink's farthest u | 0.83 | 1.03 | **1.15** | 1.25 | 2.00 |

A flag's ink therefore STARTS AT THE TIP and runs 2.8-3.8 spaces toward the head; its root is a wedge at the tip (0 .. 0.7 out) and its arm a
thin stroke 0.55-1.1 out. The band beside the stem holds 0.02-0.04 ink fraction for t < 0.4 (the root is narrow) and rises to 0.55 at t 1.0-1.1.

### 18.2 What was wrong with the old window

`Q.STEM_TIP_INK` (2.18c) tested ink DENSITY in a box 1.0 to 2.5 spaces back from the tip, 0.9 wide, against 0.30: every number CONVENTION
ASSUMED. That box sits on the thin ARM. On the real erased raster of his page (`old_reader_on_truth_stems.txt`) the 21 of his flags with a CV
stem read 0.134 .. 0.294 and ONE cleared 0.30 (0.34); a stem with nothing on it read up to 0.139 and a beam stem up to 0.303 -- so the cut
was not separating them either way, and the window also began 1.0 space in: it could not see a flag that stays near the stem at the tip.
Sean's "reader box is big enough" is exactly this: the box was not where the flags are.

### 18.3 The fix, and its stage

STAGE (§4a): a MEASUREMENT of one thing the page shows -- GATHER (`gather.stem_tip_ink`, filed as `Q.STEM_TIP_INK` by `_observe_stem_tip_ink`)
-- consulted by ADJUDICATE (`rhythm.adjudicate_duration`, which already consumed it); nothing here is EVALUATE or INFER and nothing guesses.

READ: the ink CONNECTED to the stem near its tip (0.06-space closing; seeds are the stem's own ink in the first 1.0 spaces), right of the
stem's edge, from the tip itself back to the stem's own head (`head_edge`: the head's ink is attached too), staff and ledger lines left out
(`_tip_line_rows`, shared with the hook counter; a run thicker than 0.45 spaces is a bar). Three answers: `True` (a hook), `False` (nothing
hangs: attached ink under 0.02 sq spaces), `None` (ink hangs that is not flag-shaped, or the tip cannot be read: a reason word on an
abstention). A flag is THIN (out >= 0.33, arm >= 0.40, root within 1.2 spaces of the tip) or DEVELOPED (out >= 0.8, arm >= 1.0, root within
1.6); out <= 1.5; ink on the stem's LEFT above 0.08 sq spaces is a different mark. `out` = farthest right, `arm` = length along the stem of ink
more than 0.35 out, `t_first` = where the ink starts. Two more rules, each found by a re-gather:
* a detection box explains the ink it COVERS (`STEM_TIP_COVER_AREA_MIN` 0.05 sq spaces after trimming its edges 0.1 spaces), not any ink it
  overlaps -- the 0.9-1.5-space window made 2.18c's any-overlap rule block a flag beside a flat (Brahms pdf 1 `glyph/1/0/3/3/0`, first arm)
  and a rest's loose box edge covering 0.001 sq spaces blocked another (pdf 25 `glyph/25/0/13/1/3`);
* BROKEN flags: the scan and the staff-line eraser leave a hairline break between a flag's wedge and its arm (Sean's 2.81 tile 04); a component
  within 0.35 spaces of the attached ink, right of the stem, wide enough (>= 0.3 spaces: a neighbour's stem is 0.2), >= 0.25 sq spaces and
  starting within 1.6 spaces of the tip is taken as part of the flag -- UNLESS at least half of it stands under another mark's detection box
  (`STEM_TIP_FRAG_EXPLAINED`; v4 lost a flag beside a `rest8th` to exactly this).

MARGINS on his page, measured, and thin where I say so (`probe/out/l283/shape_probe_on_truth_stems.txt`, `l283_new_reader_truth.py`): his 21
flags with a CV stem measure out 0.50 .. 1.34, arm 0.62 .. 2.5, first ink 0.42 .. 0.81; the nearest non-flags (staff-line remnants beside a
stem) out 0.37-0.38, **arm 0.37**, first ink 1.12-1.18. **ARM_MIN 0.40 sits between the largest non-flag arm seen (0.37) and the smallest flag arm
seen (0.41): 0.03 and 0.01 spaces, a pixel or less at 600 dpi** (the hugging flags the first cuts declined on Brahms pdf 25, 8 of 82 stems,
all flags on the print, measure out 0.36-0.44, arm 0.47-0.58); that is the weakest number in this section and the one most likely falsified. The developed class exists for one Litolff
flag (`glyph/10/0/9/0/2`: out 1.08, arm 1.5, root 1.33 spaces from the tip) -- n=1. Rehearsal on his page's real raster (production code,
`l283_new_reader_truth.py`): his 21 flags: **20 read `True`**, 1 `None` (`crosses_both_sides`, ink on the left 0.155); his 46 bare stems: 30
`False`, 11 `None` not flag-shaped, 5 `None` runs on, **0 `True`**; his 85 beam stems: 60 `None` crosses both sides, 25 `None` runs on, **0
`True`**. (The old reader: 1 / 0 / 1.)

### 18.4 The hook counter read the same wrong place

`stem_tip_hooks` counted in a band 0.1-0.4 spaces from the stem and refused ink on both sides; it now takes the component out to 0.9 spaces
and drops the same line rows (`_tip_line_rows`), so a flag the tip reader finds is counted. Under the arm, on his page 31 heads have a flag
read at the true tip: **28 `hooks=1`**, 3 uncounted `too_little_ink`; on the Brahms count page (pdf 1) 90 heads: 88 `hooks=1`, 2 `unresolved`.
Single flag only, per the brief; the counter is unchanged in what it claims (a count where the ink lets it, a reason where not).

### 18.5 ADJUDICATE: the flag box at the tip, and the order

* `_flags_on_reach_stem`: a head whose stem was only read by `Q.HEAD_STEM_REACH` (the contested-ownership path) got no detector flag box
  attached because the attach looked for a Q.STEM row. It now builds the virtual stem from the reach tip and uses the SAME hang test
  (`gather._flag_box_hangs_off_stem`: 0.6 spaces in x, 0.8 from the tip) and requires the flag class's direction to equal the ruler side. A wiring
  change (a decision connected), not a guess. **Brahms, 16 pages: 49 `head_and_marks{0}` -> `{1}` and 29 `beam_discounted_uncertain` ->
  `head_and_marks{1}`; Litolff 2**; 9 of 9 looked at on the print were eighths. The brief said "even when the stem was only read by reach": the
  tree holds reach rows only for heads whose ownership was contested, which is why the population is Brahms' "a 2" dyads.
* `tip_first`: the tip reading is consulted BEFORE the `beam_discounted_uncertain` narrowing (gated by the discount flags, no flags attached, no
  open-by-class), so a read hook decides level 1 where the narrowing used to say {0,1}. Expected merge conflict with lane 2.82: the
  `if (((discount_removed_all_marks ...` statement in `adjudicate_duration` (the dry-run `git merge-tree` against origin/main `40ab373a` is
  textually clean, and 354 staged duration/beam/tip tests pass on that merged tree; NOT re-measured on it).

### 18.6 Hand truth (Brahms pdf 0), base `faf913f4` vs arm `b438cda7`, GATHER+ADJUDICATE (`hand_truth_base_vs_arm.txt`, `hand_truth_flag_by_flag.txt`)

| his heads | n | base: right / narrowed+ / wrong / abstained | arm |
|---|---|---|---|
| flagged (an EIGHTH) | 40 | 26 / 6 / 7 / 1 | **28 / 4 / 7 / 1** |
| beamed | 135 | 105 / 25 / 4 / 1 | unchanged |
| bare (a QUARTER) | 119 | 63 / 54 / 1 / 1 | unchanged |

Per flag (a stem): right -> right 21; read -> right 1; not_read -> right 1; not_read -> not_read 3; wrong -> wrong 3; 5 have no stem box of his.
Tip row at the true tip end of his 40 flagged heads, base -> arm: none -> **flag 20**, flag -> flag 1, occupied -> flag 1, no_stem -> no_stem 10,
none -> no_room 4 (head too near the tip for a 1.2-space window: cannot tell), occupied -> occupied 2, other 2. **GUARD: of the 254 heads
whose stem carries NO flag (bare + beam) NONE newly reads as a flag** (tip rows: no_stem 88, crosses both sides 71, empty 44, occupied 30, not
flag-shaped 12, runs on 9). The control can fail: the old reader on the same raster reads 1 of 21 flags and 1 beam stem as a flag.

So on his page the reader now SEES 20 of 21 flags, and the duration verdict moves on 2 heads: the other 26 flagged heads were already right
(the detector's flag box was attached on the path that does not need the tip reading). The real misses are not on his page.

### 18.7 The count pages and the 2.81 population P (beam_discounted_uncertain, kept)

Small re-gathers (`acceptance_quick`, `--against` the base record, own `--out-root`), same tree but for the change:

| | heads | changed | P | P decided EIGHTH | P decided QUARTER | P other |
|---|---|---|---|---|---|---|
| Brahms pdf 1 (count page) | 1,491 | 9 | 155 | **7** (6 `hooks_counted`, 1 `head_and_marks{1}`) | 0 | 148 unchanged |
| Litolff pdf 3 (count page) | 1,286 | 10 | 41 | **0** | 0 | 41 unchanged |

(Brahms changed: 6 + 1 `beam_discounted_uncertain` -> decided eighth, 1 `flags_disagree{1,2}` -> `hooks_counted{1}`, 1 `head_and_marks{0}` ->
`hooks_counted{1}`. Litolff changed: 9 of the 10 are 2.70 hollow-head verdicts, see 18.9; 1 is a flag gained.)
Over every page re-gathered -- the count page above against the same-tree base, plus 22 other pages (Sean's judged 2.81 tiles' pages and the
miss images' pages) against the overnight verdicts, which are a valid base because
`gather.py` and `adjudicators/` are byte-identical between the overnight tree `26fdb4d0` and `faf913f4`, and the Brahms page-1 control
reproduces 1,005 of 1,005 verdicts and moves to 1 different when one is perturbed -- `base_control.txt`; **Litolff has no same-page control**):

| | pages | heads | changed | P | P decided EIGHTH | P decided QUARTER | P narrowed {1,2} |
|---|---|---|---|---|---|---|---|
| Brahms | 16 | 14,784 | 199 | 2,103 | **98** (69 `hooks_counted`, 29 `head_and_marks{1}`) + 1 decided sixteenth | 0 | 4 |
| Litolff | 8 | 7,285 | 67 | 408 | **2** | 0 | 0 |

The population is barely touched: **101 of 2,511 (4.0%)** became decided (100 eighths, 1 sixteenth) and none a decided quarter. What is left
of P is stems the reader never read (18.8) and strokes refused as beams (lane 2.82's), not a tip reading.

Sean's 30 judged 2.81 tiles (`sean_2.81_tiles_arm_reading.txt`): of his 6 EIGHTHS **4 are now decided eighths** (tiles 04, 09, 11, 27) and 2
are still undecided (02, 29: no CV stem at all); of his 24 other values (quarter, dotted quarter, half, rest) **24 unchanged, 0 newly wrong**.
Brief vs tree: tile 27's detector flag box belongs to a NEIGHBOURING stem, so it is read by the tip reader, not by a box.

### 18.8 How many misses are really missing stems

Of his 40 flagged heads, **10 have no CV stem** (7 wrong, 3 `narrowed+`): stacked pairs and chords whose heads share an unread stem; the mate has
none either (`hand_truth_stemless_flagged_heads.txt`). Sean's 2.81 tiles 02 and 29 are the same thing. A tip reader has nothing to stand on
there: they are a STEM-finder problem (the stem measurement lane), not a flag problem. Also `no_room`: 5 of his flagged heads sit within 1.2 spaces
of the tip and are declined as cannot-tell.

### 18.9 What got worse, honestly

1. **Flags the old window saw and the arm does not: Litolff 13, Brahms 2** (the merging plate loses, the shattering plate gains).
   Litolff: 6 DECIDED eighths (`hooks_counted{1}` -> `head_and_marks{0}`: pdf 4, 10 x2, 13 x2, 16) plus 7 NARROWED `flag_ink_unread{1,2}`
   (5 -> a decided quarter, 2 -> `head_fill_from_ink{0}`: pdf 10 x2, 11, 13 x3, and the count page). Brahms: 1 narrowed -> quarter (pdf 4) and, under
   v4, 1 decided (a flag beside a `rest8th`, pdf 25), fixed by the fragment rule. The old window counted the flag's arm alone; here the arm TOUCHES a
   neighbour (a rest, a beam, a head) or the tip has a head at both ends, and the tip reads `runs_on` (out 2.0-2.6), `occupied` or `crosses
   both sides`. Cannot tell is the honest reading. My own look at the small crops of the 6 narrowed Litolff ones: about half show a flag at the
   tip (pdf 10 `glyph/10/0/7/1/5`, `glyph/10/1/8/8/10`, pdf 13 `glyph/13/0/1/1/5`); the rest are chord clusters. Gains on Litolff: 5
   `head_and_marks{0}` -> `hooks_counted{1}`, 2 `beam_discounted_uncertain` -> `hooks_counted{1}`, 2 `{0}` -> `{1}` (reach) = 9 against 13, so **on
   Litolff the arm is flat to negative**; on Brahms 190 heads gain flag evidence (70 + 49 + 29 + 18 + 17 + 1 + 4 + 2) against 2. What turns a
   `None` into a decided QUARTER is not this reader: ADJUDICATE falls back to `head_and_marks{0}` whenever the tip says cannot-tell (a rule 8
   concern that pre-exists), and a narrowing {0,1} for "ink hangs, not flag-shaped" would touch thousands of heads (578 `crosses_both_sides` on
   the Brahms count page alone). It is Sean's call and is NOT done here.
2. **2.70 hollow-head churn** (Sean's rule, DECISIONS 2026-10-09: *a hollow note with nothing on the stem is always a half note*). The rule
   needs `tip_looked is False`; this reader reports "nothing hangs from the true tip" in different places than the old one, so it fires on
   different heads. Same-tree, Litolff count page: 9 of its 10 changed verdicts (5 `head_and_marks{0}` -> `hollow_head_bare_stem`, 2 the reverse, 1
   `head_fill_from_ink` -> `hollow_head_bare_stem`, 1 `flag_ink_unread` -> `head_fill_from_ink`); the 8 pages: 45 flips each way (15 + 10 + 10 +
   10); Brahms 7. **NOT CONFIRMED either way.** My own look at the 9 count-page crops (small, not authoritative): 3 changes look right, 5 look wrong --
   **4 newly decided halves sit on black-looking merged blobs** (a chord cluster, a stem with a head box on its tip) and 1 half was lost on a
   hollow-looking head. If Sean says the blobs are black, 2.70's premise (`_ink_reads_decisively_hollow` on the head's box) is the fault and was
   shielded before by the old tip reader abstaining where this one reads the true tip as empty; this lane does not touch it. Tiles 01, 06 and 10
   ask Sean.

### 18.10 Not done

* Hook counting beyond a single flag (a 16th) was not touched: `hooks=2` is reached only where the counter already counted two.
* No `Q.STEM_TIP_INK` consumer other than `adjudicate_duration` was changed; the bare-stem readers (2.18c, 2.70) read the new `False` as before.
* A rule-8 narrowing for "ink hangs but not flag-shaped" (18.9 item 1) and a Litolff same-page control for the overnight base.
* The stem finder was not touched; `no_stem` heads (18.8) stay unread.

### 18.11 Tiles for Sean

`out/print/2.83-review/` (`tile_01.png` ... `tile_10.png` + `control_1.png` ... `control_4.png`, `manifest.json`, `answers.template.json`,
`frame_control.txt`): the question on every tile is *What is the printed value of the note in the red brackets?*; a red corner bracket on the head
and NOTHING of ours drawn; our before/after reading is in `manifest.json` only. 10 sample tiles drawn at random per CLASS of change (the rare
classes are not drowned): 3 tip (the tip reader decided or narrowed it), 2 reach (a flag box attached to a reach-read stem), 2 hollow_new (2.70
newly decides a half), 1 hollow_lost (it stopped), 2 regress (a flag the old window counted that is now read `None`); plus 4 CONTROLS from his hand
truth (2 flagged = an eighth, 2 bare = a quarter) so his answers can be checked against his own boxes. His 30 judged 2.81 tiles are excluded.
Frame control (can fail): the bracketed head holds more ink than the same box shifted 1.6 head widths on 13 of 14 tiles; shifted, 0 of 14.

### 18.12 Files and controls

Product: `tools/omr/staged/gather.py` (`stem_tip_ink`, `stem_tip_hooks`, `_observe_stem_tip_ink`, constants `STEM_TIP_INK_*`, `STEM_TIP_LINE_*`,
`STEM_TIP_FRAG_*`, `STEM_TIP_COVER_AREA_MIN`, `STEM_TIP_BLOCKER_TOLERANCE_SPACES`), `adjudicators/rhythm.py` (`_flags_on_reach_stem`, `tip_first`),
doc comments in `record.py`/`capture.py`. Tests `test_staged_stem_tip_flag_2_83.py` (38), `test_staged_flag_tip_adjudicate_2_83.py` (11), three older
tip test files updated for the new semantics; each new test was run RED against the unrepaired code first (v3 for the v4 cuts: hugging flag,
developed flag, graze box; v4 for the fragment rule), with a positive control in the same class (a quarter with a clean tip stays unflagged, a
hairpin crossing the window is not a flag, a staff-line remnant stub and a thin mark 1.4 spaces in do not read, a blob touching the flag under
a box still makes the tip `occupied`, the same blob with no box still runs on). Fast tier on the final head: **7068 passed, 11 skipped, 2 xfailed,
0 failed** (577 s). `staged.check` TOTAL **192** (= main at branch time; 46 source-text tests, unchanged: none added). Probes: `probe/l283_*.py`,
outputs `probe/out/l283/`. Scratch re-gathers: base `faf913f4` clean; arm `b438cda7` clean on every stream (the Litolff non-count stream was re-run
once: the first pass wrote no record while the disk was at 100%, and its second start was killed because probe outputs were uncommitted and the
stamp read dirty; the third, `e6aa75ab`, is the same code).
