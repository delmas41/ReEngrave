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
