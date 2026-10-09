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
