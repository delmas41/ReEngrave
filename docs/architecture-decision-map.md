# The architectural decision map

**What every decision in the OMR pipeline knows, what it is allowed to use,
what it produces, who reads that, what it depends on, and what it must not be
allowed to hear from.**

Commissioned by Sean, 2026-09-07:

> *"It feels to me like we need a map of every recognition point, every time
> there is a decision and a list of what information that decision needs as well
> as a tracking of how each piece of information is used once it is gathered and
> where it should be used. … **We need the architectural blueprints.**"*

and, the same day:

> *"An important part of that map would be dependencies with a best order — or
> what should be done in parallel — and interreferential."*

**Read one section before building one thing.** This is not a cover-to-cover
document. §2 tells you where in the pipeline your thing sits; §3 tells you what
must already be true before it can work; §4 tells you whether you are standing
in a cycle; §5 is the decision itself; §6 tells you whether the information you
are about to gather already exists and is being thrown away.

⚠️ **No pipeline behaviour was changed to write this.** It is documentation
plus one read-only probe (`benchmarks/omr-decision-map-2026-09/verify.py`).

⚠️ **ADVERSARIALLY VERIFIED 2026-09-07**, at Sean's instruction, because a wrong
entry here will be believed and built on:
[`benchmarks/omr-decision-map-verify-2026-09/FINDINGS.md`](../benchmarks/omr-decision-map-verify-2026-09/FINDINGS.md).
≈93 entries checked; the mechanical half held (all 27 §8 rows re-derived from
code, 24 exactly, 3 narrowed), and **11 errors were found and corrected in
place** — every one of them a *negative* about consumers, plus three whole
stages §5 had dropped. Corrections are marked inline. **The measured half —
every quoted figure in §5 and §7 — was NOT re-run and is unverified.**

---

## 0. How to read a row, and what the labels mean

⚠️ **History worth keeping: this was the INTENT and not the state until
2026-09-07.** Six of the then-twelve §5 tables carried no `CONSUMED BY` column —
8a, 8b, 8c, 9, 10 and 11, i.e. the whole identity-and-export half, which is
where every one of §9.5's shortlist items lives. Nothing caught it, because
prose cannot check its own shape. **`verify.py`'s `V8` now does**, and it fails
if any §5 table loses either of the two columns that matter.

Every decision point in §5 carries the same ten fields. Three of them are the
reason this document exists.

| field | what it is for |
|---|---|
| **DECIDES** | one sentence |
| **CONSUMES** | the inputs actually read, verified in code |
| ⚠️ **BLIND TO** | what is in scope at that moment and is **not** read. **The most valuable column.** |
| **PRODUCES** | the field it writes |
| ⚠️ **CONSUMED BY** | who reads that — `NOBODY` where that is the truth |
| **SHAPE** | the A–E class below, plus gate / additive / vote / abstention |
| **DEPENDS ON** | what must already be settled for this to run at all |
| **PROVENANCE** | which evidence tier it produces or consumes |
| **CONSTANT** | the magic number and whether it sits on a measured gap |
| **FLAG** | the env var that changes it |

### 0.1 The five-class taxonomy — reused, not reinvented

From [`docs/handoff-probability-gates-2026-09-05.md`](handoff-probability-gates-2026-09-05.md).
Do not invent a rival vocabulary.

| | fault | repair |
|---|---|---|
| **A** | the probability is **never formed** — a boolean veto with no score behind it | compute and record the score; the gate may stay |
| **B** | formed, then **quantised** to a label before anyone uses it | carry the float to its consumer |
| **C** | formed, kept, **consumed by nobody** | give it a consumer, or say why it has none |
| **D** | used only as an **exclusive tier or a raw argmax** | a tie-break or a term under the tier |
| **E** | an **all-or-nothing structural refusal** | usually correct — see the constraint/opinion test |

⚠️ **A class is not a verdict.** The criterion for whether a site *should*
change is in
[`benchmarks/omr-additive-vs-gated-2026-09/FINDINGS.md`](../benchmarks/omr-additive-vs-gated-2026-09/FINDINGS.md)
§1, and it is one line:

> **A gate is a "stain" only when it encodes one fallible reader's OPINION.
> When it encodes a CONSTRAINT of the domain it is not a stain, it is
> information — and the strongest kind, because it is the only kind that
> cannot be wrong.**

A monotone alignment cannot reorder staves; a player cannot sound a pitch
outside the instrument's range; two equal-cost mappings that disagree carry
literally zero information. Those are constraints. A symmetry score, an NCC
template match, a detector confidence, an OCR string, a distance to a staff
band — those are opinions.

### 0.2 The provenance tiers, and why the field is load-bearing

`instrument_source` is the field that carries this, and it is already
load-bearing — it was the discriminator that stopped the label-contradiction
check reporting our own landed fixes as defects.

| tier | means | may it feed a clef decision? |
|---|---|---|
| `label` | read off this page's margin | yes |
| `score_order_ambiguity` | a label the layout prior disambiguated | yes (admitted deliberately, `contextual.py:1377`) |
| `roster` | the work's roster, matched to this staff | **held out by default** (`OMR_ROSTER_CLEF=0`) |
| `score_order` | deduced from position alone | **never** — `contextual.py:1380` |
| `catalog` | IMSLP work/edition page, independent of any encoding | measurement paths may use it |
| `encoding` | derived from a MusicXML | a measurement path may **not** use it |
| `page` | read off a raster — i.e. an OMR output | a measurement path may **not** use it |

⚠️ **The last three are the score-library tiers** (`source_kind`), not the
identity tiers, and they govern what a *benchmark* may read rather than what a
*decision* may read. Both are in this table because both are called
"provenance" in the codebase and confusing them is easy.

---

## 1. The pattern this document exists to kill

Not detection failure. **Information correctly gathered and then silently
unused.** The evidence is already written down and this map's job is to make it
visible by construction:

- **Nine "detected, then dropped on the way out" export gaps**, each found by
  forensics, none by a test — numbered in `tools/omr/export_coverage.py`.
- `grep -c '\bconfidence\b' tools/omr/export.py` **returns 1, and that one
  occurrence is a comment** — reproduced here as check `[V1]`. The exporter
  treats a notehead detected at 0.26 and one at 0.98 as equally true, and on a
  scan **29.7% of detections are under 0.40**.
- **Four of the five internal-consistency checks reach no consumer at all**
  (`[V2]`). On the two standing benchmark families, **140 scan / 21 engraved
  signals are computed and inert**.
- **~20 sites compute a real number and discard it at the moment they refuse** —
  the additive-vs-gated survey's list, reproduced in §7.
- And the worked example from 2026-09-07: an identity replay that is
  **clef-blind** resolves an ambiguous `Tp.` to Trumpet and overturns a correct
  label document-wide; handed the real bass clef it declines and the label
  stands. **The clef channel is worth 51 records on that work where the label
  channel is worth 0**, and 58 of the identity harness's 59 arms silently drop
  it ([`benchmarks/omr-readpass-monotonicity-2026-09/FINDINGS.md`](../benchmarks/omr-readpass-monotonicity-2026-09/FINDINGS.md)).

---

## 2. The spine — what happens to a page, in the order it happens

Stage numbers match `docs/progress-dashboard.html`'s flow graph so the two can
be read together. Line numbers are `tools/omr/transcribe.py` at `e1107b5b`.

| # | stage | the call | line | scope |
|---|---|---|--:|---|
| 1 | Render + staff detection | `render_page` → `detect_staves` | 4170–4171 | page |
| 2 | System grouping | inside `detect_staves` → `system_grouping` | — | page |
| 3 | Measure + barline extraction | `detect_barlines` → `extract_measures` → `resegment_fused_measures` | 4173–4194 | page |
| 3b | Staff-line removal (for the CV consumers only) | `remove_staff_lines(cells)` | 4198 | cell |
| 8a′ | **Header clef, for the key-signature slot table only** | `locate_clef` / `_read_staff_header` | 4286–4309 | staff |
| 8b | Header key signature | `_header_key_signatures` | 4323 | staff |
| 4 | Symbol detection (YOLO, per cell) | `_detections_for_cell` | 4490 | cell |
| 5 | Stems + beams (classical CV) | inside `_detections_for_cell` → `line_detection` | — | cell |
| 6 | Pitch resolution | inside the cell loop → `pitch_resolver` | — | cell |
| 7 | Rhythm / durations | inside the cell loop → `rhythm.resolve_rhythms_for_cell` | — | cell |
| 4b | Tie pairing across barlines | `_pair_ties_in_staff` | 4615 | staff |
| 4c | **Ownership: unladdered noteheads dropped** | `_drop_unladdered_noteheads` | 4682 | page |
| 4d | **Ownership: cross-staff duplicates resolved** | `_dedupe_cross_staff_detections` | 4689 | page |
| 3c | System furniture read as a measure, dropped | `_drop_furniture_measures` | 4704 | page |
| 8c | Time signature: dossier override, then vote/backfill | `apply_meter` → `backfill_page_time_signatures` | 4719–4724 | page |
| 7b | **Meter → rhythm feedback** | `_reconcile_page_to_meter` | 4752 | page |
| ✚ | Rhythm-sum check | `_annotate_column_rhythm_warnings` | 4769 | page |
| ✚ | Four cross-staff consistency checks | `_flag_*` ×4 | 4788–4791 | system |
| ✚ | Dossier checks (when supplied) | `dossier.*` | ~4795 | page / run |
| 9′ | Direction text (OCR over subtracted ink) | `read_directions` | 4939 | page |
| 9,10 | **Margin labels → instrument → slot → identity** | `apply_contextual_analysis` | **4970** | **document** |
| 4e | Roster-fed range veto (off by default) | `_apply_roster_range_veto` | 4995 | document |
| 11 | Export | `tools/omr/export.py`, separate entry point | — | document |

⚠️ **Every row here has a §5 table.** That was not true of the first
edition: tie pairing (4b), direction text (9′) and the arc pairing inside
export were named in this spine and catalogued nowhere. §11.0 records
what closed and §11.0b what is still counted-but-not-catalogued.

⚠️ **Rows marked ✚ produce nothing the pipeline consumes.** They are the
consistency checks. They are in the spine because they *run*, not because
anything downstream is different for their having run.

⚠️ **Read the stage numbers as identity, not as order.** Stage 8a happens
*twice* and the two are different decisions: a header clef is read at 4286
solely to choose the key-signature slot table and **is not written to the
output** (`transcribe.py:4243-4246`), while the clef that reaches the output is
read again inside the measure pass. Stage 9/10 (identity) runs **last**, after
every pitch is already resolved. That is §3.2's central finding.

---

## 3. The dependency axis

### 3.1 Hard dependencies — what genuinely cannot be reordered

These are physical or arithmetic, not historical.

```
render ──▶ staff detection ──▶ system grouping ──▶ barlines ──▶ measure cells
                    │                                              │
                    │                                              ▼
                    │                                    canonical cell rescale
                    │                                              │
                    ▼                                              ▼
            staff.line_ys  ─────────────────────────────▶  YOLO detection
                    │                                              │
                    ▼                                              ▼
              header window ──▶ CLEF ──▶ key-signature slot table  │
                                  │                        │       │
                                  └────────┬───────────────┘       │
                                           ▼                       ▼
                                     PITCH  ◀──────────────  notehead y
                                           │
                                           ▼
                        beams/flags/dots ──▶ DURATION ──▶ meter vote
                                           │                  │
                                           │   ┌──────────────┘
                                           ▼   ▼
                                 meter → rhythm reconciliation
                                           │
                                           ▼
                                      identity (contextual)
                                           │
                                           ▼
                                        export
```

Named, because each has bitten someone:

| dependency | why it is hard | evidence |
|---|---|---|
| staff detection → **everything** | a cell is defined by `staff.line_ys`; nothing has coordinates without it | — |
| system grouping → barline vote | "every staff in a system shares its barlines" is the whole vote | `_flag_measure_count_inconsistency` |
| **clef → key signature** | the slot table is *chosen* by the clef; fitting against a guessed clef read three flats as **two sharps** | `transcribe.py:4243-4246`, in the code comment |
| **clef → pitch** | a clef transposes every note on its staff | `clef_correction.apply_proposal` restates them |
| pitch → register checks | a range veto needs resolved MIDI | `_staff_written_ranges` |
| duration → meter vote | the meter is voted out of resolved lengths | `backfill_page_time_signatures` |
| **meter → duration repair** | `_reconcile_measure_to_meter` needs the meter it is repairing against | 4752, deliberately after 4724 |
| detections → direction text | it works by **subtracting** every detection from the page's ink | `direction_text._blank_detections` |
| identity → range veto | named staves are the whole input | 4995, "strictly after the contextual pass" |
| slots → export part names | a part is the same staff on every system | `export._stitch_slots` |

### 3.2 ⚠️ Sequenced by accident, not by necessity — where the leverage is

**This is the section to read if you are choosing what to build.**

#### (a) Identity runs last, and roughly half of it need not

`apply_contextual_analysis` is at line **4970** — the last substantive call —
and its own comment says why:

> *"It is a POST-PASS over the built page dicts: a clef hypothesis is arithmetic
> on already-resolved pitches, so nothing about detection, rhythm or
> segmentation changes … **It runs last for that reason.**"*

The reason is real **for the register half** and false for the rest. Identity's
evidence splits cleanly:

| evidence | needs pitches? | could run at stage 1–3 |
|---|---|---|
| margin labels (text layer / Surya / Vision) | **no** | ✅ |
| bracket structure, staff counts | **no** | ✅ |
| score order / position prior | **no** | ✅ |
| work roster (`work_roster.py`) | **no** | ✅ |
| register fit against an instrument's range | **yes** | ❌ stays late |
| clef-vs-instrument correction | **yes** (it restates pitches) | ❌ stays late |

**The cost of the current order is measured.** `clef_correction`'s FILL tier
fires only where no clef was read, which is 34 of 396 staves (8.6%); replayed
over the standing corpora it produced **5 proposals on 193 scan staves and
applied 0** — the tier reached **nothing, in either family**
(additive-vs-gated §4.5). Meanwhile the documented pipeline ceiling is clefs
read **wrong**, a population the fill tier cannot see by construction.

This is `docs/scope-identity-upstream-2026-09-06.md` §3's phase (a), and this
map is evidence for it: **the pitch-free half of identity has no dependency
holding it at line 4970.**

#### (b) The header clef is read twice and the first read is thrown away

At 4286 a clef is read from the header crop *solely* to pick the
key-signature slot table, and the comment says plainly: *"it is not written to
the output, and the measure pass below still reads the clef its own way."*
Two independent readings of one fact exist at runtime and **they are never
compared.** That comparison is free and is exactly the shape
`contextual._fill_defaulted_clefs` already uses across systems.
⚠️ **UNMEASURED** — nobody has counted how often they disagree.

#### (c) The consistency checks run at the end of a page and could run anywhere

All four `_flag_*` calls (4788–4791) are pure functions over the finished page
dict. They are last because that is where they were added, not because anything
needs them there. Since **nothing consumes them**, their position is currently
irrelevant — but if any becomes an evidence term, it will need to run before its
consumer, and the only real constraint is *after* the pass whose output it
reads.

#### (d) Export is a separate entry point and therefore a separate era

`export.py` runs from a stored JSON. That is why nine signals could be read
correctly and dropped on the way out without a single test noticing: **the two
halves are never exercised together except by a benchmark.** It is also why the
export gaps were cheap to fix once found.

### 3.3 What can run in parallel

| these are independent | why | note |
|---|---|---|
| **pages** | every page is rendered, detected and assembled independently until 4970 | the ONLY document-scope consumers are `apply_contextual_analysis`, the run-level dossier check, and `_apply_roster_range_veto` |
| the three **margin-label readers** | cheapest-first cascade, not a fusion | ⚠️ they are *deliberately* serial: `contextual._labels_for_page` only pays for the next rung when the free one returns empty. Parallelising them would spend money the cascade exists to save |
| **direction text** and **identity** | direction text reads ink minus detections; identity reads labels and pitches | both are post-passes at 4939 / 4970, neither reads the other |
| **key signature** and **time signature** readers | different header sub-windows, different templates | both depend on the clef read at 4286 only for the key half |
| the four **consistency checks** | pure, no shared state | |
| the **CV rungs** (stems, beams, hairpins) and **YOLO** | they read *different images* — CV takes the staff-line-erased cell, YOLO the original | ⚠️ **do not "unify" this**: erasing staff lines before YOLO was measured at −7 to −13 reading points and up to a third of the noteheads |

⚠️ **Nothing here is currently parallelised in code.** The pipeline is a single
serial loop; this table says what *could* be, not what is. The measured cost
centre is elsewhere: on a whole-work run **direction text is ~75% of wall
clock**.

---

## 4. Interreferential — the genuine cycles

⚠️ **These are not ordering problems with a right answer.** Presenting them as
"just do X first" is how the loop gets closed on its own mistake. Each is a real
cycle; what follows is what the codebase already does about it, which in three
cases is a hard-won refusal.

### 4.1 The governing rule

From `docs/scope-identity-upstream-2026-09-06.md` §7, and it is the single most
important sentence in this document:

> **The safety constraint is PROVENANCE, not topology.** It is not enough that
> the control flow has no cycle; the **evidence** must have no cycle. A message
> may be consumed only by a process whose own output did not contribute to it,
> and **two signals sharing an ancestor are ONE signal**, not corroboration.

With §8b's amendment, which supersedes it wherever they conflict: a dissenting
process **lowers a total, it does not veto** — but correlated evidence is
**counted once**, which is the additive expression of the same fact.

### 4.2 The cycles, and the state of each

#### Cycle 1 — identity ⇄ clef

```
   instrument name ──▶ "violas read alto" ──▶ clef ──▶ pitch
          ▲                                            │
          └──────── register fit ◀─────────────────────┘
```

**Refused, three times independently, and the three refusals are the best prior
art in this area.** Verified at `e1107b5b` by check `[V5]`:

| where | line | the edge it refuses | verbatim |
|---|--:|---|---|
| `tools/omr/clef_correction.py` | **396** | deduced identity → clef | *"Both act only on identity a reader actually READ off the page (**never score-order deductions — measured to close the loop on its own mistake, Beethoven 5 p.15**)"* |
| `tools/omr/dossier.py` | **434** | clef → part↔staff join | *"**The evidence is the margin labels, deliberately, and never the clefs.** Clefs are what this join exists to supply, and scoring the join on them would be circular exactly where it matters."* |
| `tools/omr/score_layouts.py` | **682** | clef → layout pin | *"**a clef — never.** Supplying clefs is what the join exists to do, and pinning on them would be circular exactly where it matters."* |

⚠️ Note the two directions are **not** symmetrical, and the codebase gets this
right: `dossier` and `score_layouts` refuse *clef → identity*;
`clef_correction` refuses *deduced identity → clef*. **Read identity → clef is
permitted**, and so is clef → identity where the clef is a reader's and the
identity is a different observation — `contextual` sets
`clef_source = "slot_continuity"`, taking a staff's clef from the same part's
reading on another system, measured 48/52 → 49/52. Two independent looks at one
fact.

#### Cycle 2 — the same cycle, resolved the RIGHT way, with a number

2026-09-07, Beethoven 5 / Litolff, whole work. `Tp.` is Timpani **or** Trumpet.
The tie is broken by asking `fit_layouts` what sits at that position — and
`fit_layouts` takes `clefs=clef_by_slot` (`contextual.py:1076`).

| the fit is handed | it proposes at ordinal 8 | the ambiguous alias resolves to | identity |
|---|---|---|--:|
| **no clefs** (a replay) | `Trumpet` | `Trumpet` — the label is overturned **document-wide** | 0.9368 |
| **the real run's clefs** | `Trombone` | `None` — not a candidate, so the label stands | **1.0000** |

**+51 records from the clef channel; 0 from 11 extra labels.** The circularity
control is explicit and passes: `_read_clefs_by_slot` admits a staff only if it
carries `clef_source`, and `clef_correction` never writes that field — the
admitted rows are `detector` 1220, `detector_header` 96, `cv_locator` 52
(readers) plus **one** `slot_continuity`, and dropping that one changes nothing.

**So "identity needs clefs" is a measured dependency, not a theoretical cycle** —
and the safe form is the one used here: clefs *a reader read*, never clefs an
identity produced.

#### Cycle 3 — pitch ⇄ clef ⇄ register

```
   clef ──▶ pitch ──▶ register ──▶ "that clef cannot be right" ──▶ clef
```

⚠️ **Both arrows are measured weak. Do not build on this.**

- `range → instrument`: a family's range is the UNION of its members', so
  percussion spans 0–127; across the scan corpus only **5 detected pitches of
  9,219** fall outside their family union.
- `range → clef` via `clef_register_warning`: **reach 7 of 193 scan staves, and
  precision 0 of 11.** Every firing is a *family boundary* — bassoon above horn,
  timpani above violin — because an orchestral score is ordered by family, not
  by register. `docs/scope-identity-upstream-2026-09-06.md` §9 nominated it and
  then refuted it the same day. **Do not resurrect the ADJACENT-PAIR form.**

What survives: the check is Class C (computed, unconsumed) and that is still a
defect of the same family. What does not survive is that consuming *this* form
would help.

⚠️ **Scope of the refutation, narrowed 2026-09-07 under
`docs/backlog-2026-09-07-open-items.md` §A00** (*a worse score does not condemn
the mechanism*). What was measured is **one form** — the adjacent-staff register
comparison — on **n = 11 firings**, and the source itself says "in every form
tried so far". §9.4 of this document names two untried variants (restricted to
one bracket group; a staff against **its own** reading on other systems) and
requires a reach measurement first. The earlier flat "do not resurrect it"
contradicted §9.4; this wording is the one to carry.

#### Cycle 4 — meter ⇄ duration

```
   durations ──▶ meter vote ──▶ meter ──▶ re-read a beam level ──▶ durations
```

**Resolved, and the resolution is the model for the others: bound the edge so
narrowly that it cannot launder a guess.** `_reconcile_measure_to_meter` may
re-read a beam level by **±1 only**, the corrected bar must land **exactly** on
the meter, the answer must be **unique**, single-voice measures only, and every
change is recorded as `rhythm_reconciliation`. It never adds, deletes or
re-pitches a note.

Note the parallel with the identity cycle: the dangerous version is *the meter
inferred from these very durations then repairing them*, and the guard is that
a dossier meter (external truth) is applied **first** (4719) so inference is
left with nothing to guess at.

#### Cycle 5 — ownership ⇄ identity

`_dedupe_cross_staff_detections` (4689) awards a contested glyph, and its
strongest available tier — the instrument's written range — needs identity,
which runs 281 lines later at 4970. The code resolves this by **deferring**: a
contested pair that distance alone decided is parked and re-examined by
`_apply_roster_range_veto` at 4995, *after* identity. ⚠️ That deferred pass is
`OMR_ROSTER_RANGE_VETO`, **off by default** — measured 52 swaps for +24 edits.
So today the cycle is cut by simply not using the identity tier at all.

#### Cycle 6 — the shared-server hazard (process, not evidence)

Not an information cycle but it costs whole runs: the Surya keep-alive server is
**one per machine**, `--serve` detaches to ppid 1 by design, and
`pkill -f llama-server` has destroyed a sibling agent's multi-hour
transcription. Use `--stop`, or `OMR_SURYA_KEEP_ALIVE=0` for an unattended run.
**Never blanket-kill by name.**

### 4.3 The standing hazard nobody has designed for

A per-**system** refusal guarding a document-**wide** write.
`_resolve_ambiguous_labels` refuses an overturn on a system that names the
proposed instrument under another alias — a per-system test — but the overturn
it performs writes `instrument_by_slot[slot]` *and* the reference itself, for
the whole document. On Beethoven 5: **80 `Tp.` labels, 73 blocked, 7 not** —
and those 7 systems carried the name across all 88 pages, with 51 judgeable
records inheriting it. Latent today only because with clefs the overturn never
fires.

---

## 5. The decision catalogue

**Depth is uniform by design.** Each row gives the decision, what it is blind
to, what it produces and who reads that, its A–E shape and its dependency.
Where a row needs more, it names the file:line — the code is the authority and
this is an index into it, not a replacement for it.

⚠️ **Read the ⚠️ column first.** It is the one the commission exists for.

Legend for the consumer column: **`NOBODY`** = nothing reads it anywhere;
**`probe`** = only a benchmark or test; **`app`** = it crosses into
`backend/`/`frontend/`. ⚠️ **Use `probe`, not `NOBODY`, the moment a benchmark
reads the field** — the difference decides whether a signal can be priced from
disk, which is what §9.5 item 1 turns on. Three cells got this wrong and were
corrected 2026-09-07.

⚠️ **At the END of the pipeline the consumer column asks a different
question, and says so.** Stage 11 has no downstream module, so *"what consumes
this"* becomes *"**who can SEE this element**"* — musicdiff's detail bits,
`export_coverage.VISIBLE`, and whether LilyPond receives it at all. That is the
same question asked of a terminal stage, and `V8` accepts either wording.

⚠️⚠️ **A `NOBODY` is the fragile kind of claim in this document, and the two
ways it goes wrong are both indirection.** (1) **A `@property`**: a direct grep
for `Staff.nominal_line_spacing_px` finds only the write, while the value
flows out through `Staff.line_spacing_px`, which has **15 production readers**
including `system_grouping`'s crossing band. (2) **A function-local import**:
`grep -n 'instruments\.' tools/omr/transcribe.py` returns one hit and it is a
comment, while `instruments.lookup` is imported *inside* two functions
(`:2484`, `:2872`) and decides glyph ownership. **Check for both before writing
a `NOBODY`** — every error the 2026-09-07 adversarial verification found in
this document was a negative about consumers, and one of them was load-bearing.

**Coverage of §5 — declared, not implied.** ⚠️ §11's old claim that scope was
"cut uniformly in depth" was false; an independent enumeration found five areas
where §5 had two rows against 185 decision points. What is true now:

| area | independent count | rows here | state |
|---|--:|--:|---|
| `direction_text.py` | 72 | **14** | **catalogued** (Stage 9′) — the 14 that decide something |
| slur / arc pairing + numbering | 46 | **13** | **catalogued** (Stage 11) |
| tie pairing | 25 | **12** | **catalogued** (Stage 4b) |
| `pitch_resolver.py` | 25 | 5 | depth cut, declared |
| `condensed_parts.py` | 17 | 1 | ⚠️ **declared gap** — and the reason is in the row: nothing in production calls it, so the knob is inert |

⚠️ **A "depth cut" here means the rows chosen are the ones that CHOOSE
something a reader could change.** The residue is arithmetic and bookkeeping.
That is a judgement, not a measurement, and it is stated so a reader can
disagree with it rather than mistake silence for coverage.

---

### Stage 1 · Render, binarise, deskew — `preprocessing.py`

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| `render_page` channel dispatch `:40` | how to read the pixmap | `pix.colorspace`, `page.rotation`, `page.get_text()`, and ⚠️ **`input_domain.py` sits in the same package unconsulted** | RGB → internal | D |
| `binarize` Sauvola `:90` | ink or paper, per pixel | ⚠️ **the DPI.** `window_size=25` is a fixed PIXEL window, so at 600 dpi it spans a third of the staff spaces it spans at 300 — and `OMR_DPI` legitimately varies 300/600 | `PageImage.binary` → everything | A (the threshold *map* is computed and discarded) |
| `deskew` Hough accept `:112` | is there a near-horizontal line at all | per-line `rho` (positions computed and dropped), vote strength, page height | `lines` → internal | E, abstains to 0.0 |
| `deskew` angle `:127` | the page rotation | ⚠️ the **spread** of the angles — a bimodal set rotates by its midpoint with no complaint | `skew_correction_deg` → `staff_labels.py:175`, else JSON only | B (dead-banded at 0.1°) |

**Constants:** none of stage 1's four (`window_size=25`, `k=0.2`, the 0.1°
dead band, `max_correction_deg=5.0`) is documented against a measurement. This
is the shallowest-evidence stage in the pipeline.

---

### Stage 1b/2 · Staff detection and system grouping — `staff_detector.py`, `system_grouping.py`

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| `_candidate_staff_rows:210` | which rows are staff-line candidates | ⚠️ `find_peaks`' **properties dict is discarded** (`peaks, _ =`) — per-peak prominence and width, computed by scipy, never read; and the gate is *total row ink*, not a long RUN (§8-D14) | peaks → in-file | A |
| `_group_into_staves:243` | are these five peaks one staff | ink strength of each peak (`profile` is not even passed in); the next window's fit — greedy, no backtracking | groups | B (`max_dev` → bool, discarded) |
| `_reject_spacing_outliers:286` | drop a phantom staff | the group's ink, x-extent, whether its rows individually look like lines | groups | A |
| `_comb_match_staves:326` | recover a broken staff | ⚠️ the fit deviation orders candidates and is **never thresholded** — an arbitrarily bad comb fit is accepted if nothing overlaps it; and `page_width` is a parameter this function's body never references | accepted groups | D |
| `_single_line_staff_rows:501-532` | is a lone rule a percussion staff | six stacked vetoes; `_has_the_rest_of_a_staff` probes ±1 and ±2 spacings only, never ±3/±4 | 1-line `Staff` | A/E |
| `_staff_x_extent:588` | the staff's left/right edge | ⚠️ the per-column vote COUNT (3, 4 or 5 of five lines) is thresholded and thrown away — the extent cannot tell a 5/5 column from a 3/5 one; line thickness is measured *later* and would size the band better | `Staff.x_start/x_end` → very wide | vote → A → D |
| `_staff_x_extent:600` fallback | a staff with no voting column | ⚠️ **claims the whole page width, silently** — no flag, no `None`; downstream medians it as if it were a measurement | `(0, w-1)` | E |
| `_refit_misaligned_group:939` | did this window lock onto a beam | ⚠️ **`measure_line_geometry` returns thickness AND WANDER on this very call and the wander is discarded** (`measured[0]`), twice | `shift` ∈ {−1,0,1} | B/D |
| `_line_ink_runs_per_space` gate `:1043` | staff or paragraph of text | the `Staff` already carries `line_thickness_px` and `line_wander_px` and neither is read — a text baseline and a printed rule differ in both | the staff list + `staff_index` renumbering → **everything** | B (score computed, thresholded, never stored) |
| `gap_crossing_runs:298` | does ink cross this inter-staff gap | run **widths** (kept for the sum, then binarised); each staff's own x-extent (medianed away by design) | crossing runs | B |
| **`assign_systems:676`** | is this a system break | ⚠️ **the bridging MAGNITUDE.** The module documents a trimodal 0 / 4–18 / 35–95 structure and the boundary decision reads only `== 0` | `Staff.system_index` → **everything** | C→A |
| `assign_systems:677` | is connectivity usable at all | partial evidence — 1 bridged gap of 20 proceeds; there is no "mostly blind" tier | `used_bridging` | E |
| cue B `:708` / cue A `:722` | choir-barred merges and splits | the count magnitudes (both compared to 1); ⚠️ cue A still anchors on the page-MEDIAN `x_start` **with no bimodality check**, the exact poisoning the module documents at length | breaks | B→A |
| `_assign_groups:613` | where a bracket group ends | run widths (dropped: `for c, _w in runs`); ⚠️ **the pixel path has no `MIN_EVIDENCE` floor** — with `OMR_BRACKET_COLUMNS=0` uniformly-low counts still manufacture groups, the failure the constant exists to prevent | `Staff.group_index` → `slots.py`, cue C, `contextual` | B + abstention |

**On a measured empty gap:** `STAFF_COMB_POOL_FRAC 0.30` (plateau 0.20–0.35) ·
`SINGLE_LINE_CLUSTER_WIDTH_FRAC 0.9` (0.999 vs 0.76/0.02/0.05) ·
`MAX_LINE_INK_RUNS_PER_SPACE 1.7` (music ≤1.39, text ≥2.02) ·
`STAFF_LINE_BAND_SPACES 0.35` · `MISFIT_THICKNESS_RATIO 2.5` (1.0–1.8 vs
3.6/4.0) · `MISFIT_COVERAGE_FRAC 0.35` (0.041–0.112 vs 0.682) ·
`BRACKET_COLUMN_MIN_EVIDENCE 3` (engraved ≤2, scanned ≥5) ·
`CHOIR_MERGE_MIN_CROSS 1` (0 or 6–22) · `BRIDGE_GAP_TOLERANCE_SPACINGS 0.6`.
**Bare:** the three `_candidate_staff_rows` constants ·
`GROUP_LINE_SPACING_TOLERANCE 0.30` · `STAFF_SPACING_OUTLIER_FACTOR 1.6` ·
`STAFF_COMB_TOLERANCE 0.25` · `MAX_SYSTEM_GAP_FACTOR 6.0` ·
`LEFT_BAND_GATE_FRAC 0.7` (self-described as "inactive on the validation
corpus… insurance").

---

### Stage 3 · Barlines, measures, cells — `measure_extractor.py`, `staff_line_removal.py`

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| `_detect_barlines_in_window:165` | is this component a barline | ⚠️ `stats[i]` yields `x, y, w, h, area` — **`y` and `area` are unpacked and never read**; a component's vertical position is never checked against the staff. `Staff.line_thickness_px` unread | x centres | A |
| `_dedup_barline_candidates:210` | which of a 60 px cluster survives | ⚠️ in the default `leftmost` mode the component **height is carried the whole way and then discarded** — its own docstring says so | thinned xs | D |
| `detect_barlines:521` | how many staves must vote | ⚠️ everything about the staves: `group_index` (a barline may legitimately stop at a bracket edge), ink, thickness. A step function of `n` alone — 12 staves need 8 votes, 13 need 7 | `min_votes` | D |
| `detect_barlines:568` | is this an open score | the connectivity *distribution* — bucketed at 0.4 here and re-bucketed at 0.4/0.7 per cluster later | `barlines_cross_gaps` | vote → E |
| cue C `:615` | grouped + window-blind ⇒ never open score | how many gaps are blind, which one, the connectivity that produced the flip | override | A. ⚠️ **Depends on `group_index`, which the gap-heuristic fallback never sets — so cue C is unreachable on any page where connectivity abstained** |
| `:623` / `:650` acceptance | which barlines are real | ⚠️ `_spans_system` — the stricter test — is **never used on 3+-staff systems**; and `n_votes = len(cluster)` counts raw observations, so one staff firing twice inside 12 px counts as two votes | `Barline` list | D + A/B |
| `_drop_close_outliers:709` | drop an implausibly close barline | ⚠️ **every piece of per-barline evidence is already gone** — the function receives only integers, so "which of the pair is spurious" is decided with no vote count, connectivity, span or height | final xs | B + E |
| `_measure_x_boundaries:756` | the system's left/right edge | the SPREAD of `x_start` (medianed silently); ⚠️ and the right edge uses `max`, the extreme its own comment argues against (§8-D16) | `x_lo`, `x_hi` → `_build_measure_cell`, the barline edge filter — **CONSUMED** | D |
| `_measure_x_boundaries:774` edge filter | is this barline the system's OPENING RULE rather than a measure boundary | ⚠️ **how near it was.** `edge_margin = max(10, round(2.0 * spacing))` and the test is `x > x_lo + edge_margin` — a boolean, off an `x_lo` that was **silently medianed** one line earlier. Measured on a live page by the one-line-staves workstream: a cut at **506 against a threshold of 516** decides it, so a barline is kept or discarded on **nine pixels** with no score formed and no record of the near miss. ⚠️ End-to-end cost is currently **zero** — `_drop_furniture_measures` absorbs the sliver downstream — so this is a decision made without a probability, in the spine, now measured but **not** a live defect | the surviving barline set | **A** |
| `_build_measure_cell:1046` | pad 4 spaces or 6 | `line_thickness_px`/`line_wander_px` (the clearance is a flat 0.5 space); the actual ink above/below in this cell's x-range | the `MeasureCell` → **19 importers**, and the ones that matter are not the obvious ones: `transcribe`, `yolo_detector`, `export`, `system_grouping`, `staff_line_removal`, `visualize`, **`staff_header.py:369`/`:427` (which call `_build_measure_cell` directly)** and ⚠️ **the whole labeling pipeline** — `annotate/select_cells.py`, `select_cells_orchestral.py`, `select_timesig_cells.py`, `recut_cells.py`, `annotate/server.py` | E ("four, or six, and nothing between") |
| `_build_measure_cell:1060` | drop a cell narrower than 10 px | ⚠️ `line_spacing_px` — a **bare pixel constant in a file that scales everything else by spacing**; 10 px is 0.4 spaces at 600 dpi and 1.2 at 200 | `None` — the cell vanishes, and the staff's measure count then differs from its siblings, which `_flag_measure_count_inconsistency` later reports | A |
| `_cell_line_offset:1005` | slide the cell's 5-row grid onto the ink | `line_thickness_px` (the band is a fixed 3 rows); ⚠️ **the neighbouring cells' answers** — each cell decides alone, with no smoothness constraint along the staff | `staff_line_ys_canonical` → pitch; provenance → `annotate/recut_cells.py` only | D + 3 abstentions |
| `remove_staff_lines_from_cell:127` | is this run the LINE or a crossing symbol | ⚠️ **`cell.staff_line_thickness_canonical` — the page-measured thickness carried onto this exact object — is not read**; the thickness is re-derived from the cell instead | `image_no_staff` → every CV rung | B |
| `resegment` `:1278`/`:1319` | split a fused measure | ⚠️ **`x_by_staff` is NOT passed to `_intersystem_connectivity` here**, so the leaning-barline Theil–Sen fit the global pass relies on is silently OFF for resegmentation and it drops a vertical column | extra boundaries | vote + B |
| `:1503` split acceptance | accept or reject the whole split | which piece failed; a partial split (explicitly refused) | boundaries | E |

⚠️⚠️ **A CELL'S PADDING IS A LABELING CONTRACT, NOT A CROP SETTING — and the
first edition of this table hid that behind the word "everything".** Every
box a human ever drew is stored in the cell's CANONICAL frame, so a cell
re-cut at a different padding is not a slightly different picture: it is the
same music at a different scale, with every box in the batch landing
somewhere else, and nothing downstream would say so. That is CLAUDE.md's
loudest warning in this area, it is reachable ONLY through the five
`annotate/` consumers named above, and §11 puts the labeling pipeline out of
scope — so a cell reading *"consumed by everything"* actively routed a
reader away from it. **A technically-correct-but-unactionable consumer cell
is an error in this document, not a matter of style.** The safe repair path
is `annotate/recut_cells.py`, which never rewrites `cells.json` and never
deletes; the cutters (`select_cells*.py`, `rank_and_trim.py`) choose cells
and will renumber a labeled batch.

⚠️ **`if len(s.line_ys) >= 5` at `:464`, `:1148`, `:1471`** excludes one-line
percussion staves from the barline vote, from cell extraction and from
resegmentation. They are detected only to preserve slot numbering. This is
backlog item C3. ⚠️ **There is a FOURTH guard the item's "three locations" does
not name**, `measure_extractor.py:849` (`len(other.line_ys) < 5`).

⚠️⚠️ **CORRECTED 2026-09-07 — this paragraph used to say
`Staff.nominal_line_spacing_px` "exists specifically so such a staff could size
its windows, and no production site reads it". THAT WAS FALSE, and it was the
entry the one-line-staves workstream would have read first.** It is read at
`types.py:102`, inside the `Staff.line_spacing_px` **property**:

```python
    if len(self.line_ys) < 2:
        return float(self.nominal_line_spacing_px or 0.0)
```

and `line_spacing_px` has **15 production readers** — among them
`system_grouping.py:237` and `:299`
(`max(upper.line_spacing_px, lower.line_spacing_px)`, the crossing band's own
scale), `:255`, `:357`, `:370`, `:601`, `staff_detector.py:671`/`:755`,
`measure_extractor.py:152`/`:772`/`:973`, `direction_text.py:270`. **A one-line
staff bordering an inter-staff gap already contributes its nominal spacing to
system grouping.** The field is live, not dormant, and "wiring it up" would
change grouping geometry while believing itself inert.

**Why this map got it wrong, and the lesson for every other negative in it:** a
direct grep for the field name finds only the write site and the property. The
consumption is **transitive through a property**. An import graph is not a
consumption graph, and neither is a name grep.
(`benchmarks/omr-decision-map-verify-2026-09/FINDINGS.md` E1.)

---

### Stage 4/5 · Symbol detection and the CV line rungs

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| `yolo_detector.detect:345` | every detection that exists | ⚠️ **`OMR_CONF_THRESHOLD = 0.25` is ONE global number for 208 classes.** There is no per-class floor in code — the shipped weights bake per-class floors into the head BIASES because there was nowhere else to put them | `SymbolDetection.confidence` | A→D |
| `imgsz_for_cell:252` | how many pixels of a staff space the model sees | the page DPI, and ⚠️ **the weight-routing verdict** — already computed at document level, and the two checkpoints were fine-tuned at different imgsz | an int passed to `predict`; ⚠️ **never recorded in the result** | A |
| `_class_name_to_category:178` | the `category` every downstream filter keys on | `conf` and the bbox (both in hand in the caller loop); the class **id**, so the fine/coarse block boundary that would say which vocabulary it came from is discarded | `category`, `smufl_name` | D |
| `_drop_clipped_notehead_fragments:558` | is this a neighbour's ink the crop sliced | ⚠️ `confidence` — a 0.95 detection is deleted on geometry alone, while its sibling rule `_drop_unladdered_noteheads` is built entirely on confidence; also `width_canonical` (a fragment's aspect is as much a giveaway as its height) | a count → **`probe`** (`omr-ned-2026-08/probe_edge_fragments.py:76`, `probe_gate_reach.py:81`) | E |
| `_drop_unladdered_noteheads:3098` | delete an unsupported outside-staff note | ⚠️ `det["pitch"]` (already resolved — an `Ab1` on a flute staff is exactly the impossible the range veto exists for), `det["class"]` (the documented fakes are whole-note-shaped), and the detection's own height in staff spaces | a count → **`probe`** (`probe_gate_reach.py:80`) | **B → hard gate**, the pipeline's one confidence threshold |
| **`_dedupe_cross_staff_detections:2645`** | **which staff owns a contested glyph** | ⚠️ **both confidences are in hand and NEITHER is read** — proven in the same function: they are fetched at `:2801-2802` into the `OMR_CONTEST_DUMP` blob, which the docstring certifies is verdict-neutral. Also unread: the IoU value, the band distances, the ladder rung counts | removals; `deferred` | D — ladder(2) → range/hairpin(1) → **distance(0)** |
| `_apply_roster_range_veto:2919` | reverse a distance-only verdict | both confidences again (the parked records carry the full dicts) | `n_swapped`, `swaps` → **reported, not acted on** | E |
| `_drop_furniture_measures:3032` | drop leading/trailing empty columns | column **width** — ⚠️ checked and **rejected on the record**, the rare case where the unused signal is unused on purpose | a count → **NOBODY** (verified: `n_measures_dropped_as_furniture` has zero readers anywhere) | E |
| `line_detection.detect_stems:302` | what is a stem | ⚠️ **the YOLO detections for the same cell.** `detect_lines(cell)` is passed only the cell; `dets` exist at that moment and are not handed in | `LineDetection(confidence=1.0)` | **A — no probability is ever formed**, and the dataclass says so |
| `_drop_paired_strokes:200` | is this pair a sharp's two strokes | ⚠️ **the YOLO `accidental` detections.** The sibling rule `_filter_stems_overlapping_tremolo` does exactly this shape for ornaments; the identical evidence exists for accidentals one call away | filtered stems | A, symmetric deletion |
| `detect_beams:527` | what is a beam | the YOLO `beam`/`slur`/`tie` detections (both sources exist — `rhythm.py:1523` merges them later); noteheads; the component's slope | `n_bars` beam objects | A / quorum vote |
| `_stacked_bar_count:370` | how many bars are stacked | the spread — a component whose columns read 1/3 is indistinguishable from one that agrees 2/2/2 | `n_bars` | A / median vote |
| `_route_weights:3910` | which checkpoint runs | ⚠️ the classification's whole evidence dict is recorded at `:3907` and **only the categorical verdict is branched on**; no per-page routing on a mixed PDF | `weight_routing` → ⚠️ **tests only** | D + abstention |

⚠️ **The ownership decision is the largest overlapping population in the
pipeline and is decided by a coin flip.** Measured over the 20-row scan gate:
**4,521 contested pairs — 94.1% by DISTANCE, 5.9% by ladder, 0% by range**
(the range tier needs a dossier and the gate runs dossier-free by protocol).
**82% are in categories no tier above distance can reach at all.** Confidence
tested against the ladder as an internal gold standard agrees **0.617
[0.558, 0.674], n=264** — real evidence, and weak.

---

### Stage 6 · Pitch resolution

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| `clef_geometry.resolve_clef:283` | which line the clef names | `detection.confidence`; and the `residual` is thresholded and **never returned as a graded quantity** | `ClefRead` | E + D |
| `transcribe.py:1604` clef argmax | the cell's active clef | ⚠️ the LOSING clef readings are discarded with **no record** — no `clef_candidates` list, unlike `pitch_candidates`; and `ClefRead.residual`/`.source` are in hand and not compared, so a geometry read at 0.30 loses to a class-label read at 0.31 | `clef`, `clef_source` | **D — raw argmax, no floor at all** (`best_clef_conf = -1.0`) |
| `transcribe.py:1656` locator gate | may the CV C-clef locator speak | the detector's own clef confidence — the gate is PRESENCE, so a detector clef at 0.11 permanently silences the locator | `clef_source="cv_locator"` | E |
| `_octave_shift_for_base_clef:394` | ±1/±2 octaves for the whole staff | the marker's `confidence`; vertical distance is used only for its SIGN, so a `clef8` one pixel above the centre is accepted with full force | clef suffix | D |
| ⚑ `pitch_resolver.pitch_for_notehead:182` | **the staff position of every note** | ⚠️ **the fractional residual `pos_float − pos` is computed and thrown away** — no "this note sat exactly between two positions" signal exists anywhere; `confidence` unread; the five measured line positions collapse to a mean and only `lines[0]` anchors | `pitch` → **everything** | **B** |
| `pitch_candidates_for_notehead:246` | the alternates and their weights | as above | `pitch_candidates` → ⚠️ `tools/maestro_bridge/re-rank.ts` **only**; `clef_correction.py:312` merely DELETES them | **C** |
| ⚑ accidental ladder `transcribe.py:1890` | the alteration | the accidental's `confidence`; ⚠️ the three tiers are mutually exclusive, so **agreement between an inline reading and the key signature is never recorded** | `pitch`, `accidental` | D |
| `_pair_accidentals_to_noteheads:963` | which note an accidental alters | ⚠️ the y tolerance is a fraction of **the accidental's own detected height** — detector noise; the staff spacing is in scope and unused. Precisely the fault `rhythm._pair_dots_to_targets` documents and fixed by switching to staff spacing. Also: one accidental can overwrite another's claim with no conflict report | `inline_map` | D, no floor on the winning score |
| `_detect_key_sig_from_cell:845` | the staff's key signature | ⚠️ marker `confidence` (5 low-confidence flats beat 4 high-confidence sharps); and **`read.n_matched` — the quantity the cross-page vote weights by — is computed and discarded**, only `.fifths` is read | `key_signature` | D + B |
| `_correct_notehead_class_by_fill:478` | black / half / whole | ⚠️ **the docstring's three-band table has two branches in code** — the 0.35 boundary is unreachable (§8-D12); and no provenance flag records that a class was rewritten | `smufl_name` → duration | B |

---

### Stage 7 · Rhythm and durations

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| ⚑ `rhythm.py:1553-1596` | beams > flags > notehead class | ⚠️ **the flag is consulted only when the beam count is exactly 0** — a note with 1 beam level and a `flag16thDown` beside it never has the contradiction noticed, let alone recorded | `duration_beats/_type/dots` | D |
| `rhythm.py:1569` fallback | stem-anchored or direct beam counting | ⚠️ the fallback fires on a count of ZERO, indistinguishable from "correctly found no beams" — so every unbeamed note also runs the loose method whose over-counting the module documents (183 noteheads at 5–8 levels) | `n_beam_levels` | D |
| `_beams_attached_to_stem:971` | how many beams are stacked | ⚠️ the CLUSTER GAP SLACK — a 0.34-vs-0.36 decision is indistinguishable in the output from an unambiguous one, and this is the number `_reconcile_measure_to_meter` exists to arbitrate | `beam_levels` | B |
| `_deduplicate_beams:750` | which overlapping beam survives | the DETECTOR OF ORIGIN — a lower-confidence CV stroke loses to a higher-confidence YOLO box, though the rule two functions away establishes CV is the better level-measurer. ⚠️ **This is a fifth confidence decision site the documented count of four omits** (§8-D23) | beams | D |
| `_pair_dots_to_targets:1132` | which note a dot multiplies | `confidence` on both sides; no plausibility ceiling (a triple dot is accepted silently) | `dots` | D |
| ⚑ `_tuplet_groups:1336` | is this group a triplet | ⚠️ the digit's `confidence` — a `fingering3` at 0.2 is admitted identically to a `tuplet3` at 0.9; and the group's written length | `tuplet` → export | E + D |
| `infer_time_signature_from_lengths:419` | the meter, from durations | the runner-up meter and the losing votes | ⚠️ `confidence`/`votes`/`voters` → **NOBODY** (`grep 'get("votes")'` → 0) | E; **C** for the emitted score |
| `_dominant_detected_meter:574` | the meter, from digits | ⚠️ **every reading after a staff's FIRST is discarded unexamined** (`break`) | same, plus `symbol` → `export.py:874` | D + C |
| `backfill_page_time_signatures:692` | which meter estimate wins | ⚠️ **the two independent estimators never corroborate each other** — if propagation succeeds, inference is not run, so neither agreement nor contradiction is ever observed | `time_signature` + `source` | D |
| ⚑ `_reconcile_measure_to_meter:3272` | re-read a beam level ±1 | ⚠️ **when two candidate repairs exist the pipeline knows exactly which two and records neither**; and it refuses multi-voice measures wholesale with no record | `rhythm_reconciliation` → ⚠️ the RECORD reaches **NOBODY**; only the integer counter is read | E; **C** for the record |
| `voicing.group_chords_in_measure:204` | which notes are one chord, and its duration | ⚠️ `confidence` is on every notehead and unread, so a 1–1 duration tie breaks on `Counter` insertion order; `beam_levels` — the REASON two members disagree — is not consulted; **and the disagreement itself is resolved and never recorded** | events → export | D (unweighted mode vote) |
| `voicing.split_events_into_voices:314` | one voice or two | ⚠️ **its own docstring's rule is not implemented** — it says "at a different x position" and the code never compares x (§8-D11) | voices | E. ⚠️ On a page with no CV stems every measure is single-voice, which silently ENABLES the reconciliation above on all of them |

---

### The five internal-consistency checks — computed, and four reach nobody

Run at `transcribe.py:4769` and `:4788-4791`. `[V2]` reproduces the consumer
column.

| check | fires (scan / engraved, 193 / 224 staves) | grades itself | consumed by | ⚠️ blind to |
|---|--:|---|---|---|
| `rhythm_sum_warning` | 111 / 12 | `severity` high/low — ⚠️ **no `confidence` field at all**, the only check without one | `backend/modules/local_omr.py:360`, as a **boolean presence count** for a UI percentage. `severity`/`kind`/`column`/`fused_suspected` → NOBODY | the deviation MAGNITUDE is written and never graded; how many staves of the column mis-sum |
| `measure_count_warning` | **0 / 0** | `confidence` + `confidence_label` + corroboration flags | **NOBODY** | the barline detections and their confidences; measure widths (only the already-binarised `phase1_warning`); ⚠️ `restHBar`/`restHNr` are in `detections` and it re-derives "multi-measure rest" from note-emptiness instead |
| `key_signature_warning` | 0 / 3 | `confidence` + `circle_distance` | **NOBODY** | ⚠️ `key_signature_source`, `key_signature_read` and `key_signature_unread_reason` are on the same staff dict and none is read — **an unread staff (silently 0) is treated exactly like a staff printing no key signature**; and `instrument` would give the real transposition instead of a five-member guess set |
| `clef_register_warning` | 7 / 4 | `confidence_label` hardcoded `"advisory"` | **NOBODY** — `grep -c clef_register_warning tools/omr/clef_correction.py` → **0** | only ADJACENT pairs; `clef_source`, so a CARRIED clef is trusted as much as a read one; `clef_diatonic_shift`, which would say which clef fixes it |
| `time_signature_disagreement` | 17 / 1 | `confidence` (min 0.500, max 0.933) | **NOBODY** | ⚠️ `_READING_SOURCES = {"header_reader"}` exists in `rhythm.py:507` and is honoured by `_dominant_detected_meter` — **this check does not use it**, so a header-reader meter is excluded from its own vote; and `ts["symbol"]`, where a printed C is far stronger evidence than a digit pair |

⚠️ **`clef_register_warning` is Class C and consuming it would still not help.**
Measured: reach 7 of 193 scan staves, **precision as a clef-error detector
0 of 11.** Every firing is a family boundary — bassoon above horn, timpani
above violin — because an orchestral score is ordered by family, not by
register. **Do not resurrect the ADJACENT-PAIR form**; §4.2 Cycle 3 carries the
scope of that refutation (one form, n = 11) and §9.4 names the two variants it
does not cover.

⚠️ **`phase1_warning` is the counter-example worth knowing.** The one
STRUCTURAL warning IS consumed — `rhythm.py:451`, `transcribe.py:3383`/`:3505`
and the backend all read it. The semantic warnings are the ones that reach
nobody.

---

### Stage 8a · Clef — the canonical Class-A chain

`clef_locator.locate_clef` runs a chain of vetoes. **Every one of them computes a
real measurement and destroys it in the same expression.**

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| `cluster_components` y-gap `header_ink.py:314` | do two components merge into one glyph | ⚠️ `dy` is computed at `:300` and destroyed at `:314`; component `area` is carried through the tuple as ballast and never read | clusters → `clef_locator`, `key_signature_locator`, `time_signature_locator` — **CONSUMED**, in-module only | **A** |
| `require_cluster_on_staff` `clef_locator.py:771` | skip a cluster left of the staff's printed lines | how far left (`staff_left − (x+w)` never formed); the cluster's symmetry — it is skipped *before* being scored | a `continue` → nothing recorded → **NOBODY** | **A** |
| `staff_left_max_spaces` `:480` | disbelieve the staff-left measurement | how many long horizontals were found (`len(lefts)` discarded — one fragment and five staff lines are the same evidence); their y against the KNOWN line rows | an abstention → **NOBODY** | **E** |
| width/height gates `:795`, `:804`, `:821` | too narrow / too big / too short | aspect ratio (never formed); how far outside the bound — a 4.6-space and a 12-space width stop identically | a rejection → **NOBODY** | **A** |
| **`_has_f_clef_dots` `:584-628`** | is this an F clef's dot pair | ⚠️ **seven continuous quantities — `bw`, `bh`, `aspect`, `cx/w`, `dx`, `dy`, `dw` — each consumed by a comparison operator in the line that computes it.** `dw` is computed unconditionally although its bound is `None` in the shipped config. And `symmetry`, computed 10 lines earlier at `:840`, is **thrown away at the refusal** rather than combined | a bool → **NOBODY** | **A**, the exemplar |
| `min_symmetry` `:843` | is this a C clef at all | the second-best axis, the sharpness of the peak, the ink fraction (computed at `:783`, never combined) | `LocatedClef.symmetry` → ⚠️ **`probe`** — four benchmark scripts read it and no production site does; production reads `located.read.name` only (`transcribe.py:1684`, `:4288`) | **B** on refusal, **C** on success |
| `ambiguous_snap` `:865` | did geometry name a line | ⚠️ `read.residual` — a real number on the returned object — is not inspected here or anywhere | `LocatedClef.read` → `transcribe.py:1684`, `:4288` — **CONSUMED** (`.name` only) | **A** |
| the `trace` recorder `:700+` | *nothing* — it records | — | the `trace` dict → ⚠️ **`probe`**: the only `trace=` caller in the tree is `test_clef_locator.py:344`. **Neither pipeline call site passes one** (`transcribe.py:1677`, `:4286`) | **C**, with the home already built |
| `clef_geometry.resolve_clef:283` | which line the clef names | `detection.confidence`; the `residual` is thresholded and **never returned as a graded quantity** | `ClefRead.name` → `transcribe.py:1616`, `:1684`, `:4288` — **CONSUMED**. `ClefRead.residual` and `.line` → **`probe`**; `.family` → **NOBODY** | **E + D** |
| **the 5-reader precedence ladder** `transcribe.py:1656 / :1708 / :1769 / :1789` | which reader's clef stands | ⚠️ **every reader's own score.** It arbitrates purely on `clef_source is None`; `best_clef_conf` is computed at `:1607` and discarded at `:1613`, so a locator hit at symmetry 0.701 beats a specialist detection at 0.99 and **nothing records that a contest happened** | `clef`, `clef_source` → **CONSUMED, widely**: `pitch_resolver`, `export.py`, `clef_correction`, `contextual._read_clefs_by_slot` (`contextual.py:1076` — the +51-record channel of §4.2 Cycle 2), `dossier` | **D** |
| `_octave_shift_for_base_clef:394` | ±1/±2 octaves for the whole staff | the marker's `confidence`; vertical distance is used only for its SIGN, so a `clef8` one pixel above the centre is accepted at full force | the clef suffix → **CONSUMED** by `pitch_resolver` and both exporters | **D** |
| mid-staff clef change `transcribe.py:4646` | did the clef change within the staff | — | `clef_final` → ⚠️ **its only reader is its own keeper** — `clef_correction.py:551` reads it solely to keep it consistent after a veto. **Nothing downstream reads it**: not `export.py`, not the backend, not the frontend | bookkeeping |

⚠️ **`clef_diatonic_shift` (`pitch_resolver.py:117`) is the one header-stage
quantity that is genuinely well-consumed** — `clef_correction.py:238`, `:374`,
`:531` — and it is what makes `apply_proposal` able to restate every pitch on a
staff. It is the working half of the identity→clef→pitch edge §4.2 describes.

---

### Stage 8b · Key signature — and the clef dependency

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| `locate_key_signature:310` | refuse without a clef | the clef's PROVENANCE — it cannot tell a measured clef from a defaulted one; the caller must, and does | an abstention → **NOBODY** | **E** |
| clef anchor `:354` | where the key signature may start | ⚠️ **the clef the caller already supplied** — it re-derives the clef's right edge from ink and never checks the two agree | an x → in-module | **A** |
| glyph filter `:361-370` | which clusters are accidental-shaped | ⚠️ `occupied_boxes` is a documented parameter and is **`None` in every production call** (`transcribe.py:1375`), so the detector's notehead boxes never veto a key-signature glyph | filtered clusters | **E**, dead path |
| sharps vs flats `:402-414` | which accidental the run is | the MARGIN between the two residuals — 0.001 apart and 0.4 apart decide identically, with no abstention on a near-tie | `LocatedKeySignature.accidental`, `.boxes` and `.decided_by` (`"pattern"` / `"shape"` / `"tail"`) → ⚠️ **NOBODY, anywhere** — not production, not tests, not benchmarks; `transcribe.py:1375` reads `.read` only. Checked for a property escape hatch: the class has none | **D**; `decided_by` is **C** |
| `_fit_exact` `key_signature_geometry.py:298-311` | which prefix of the slot table | ⚠️ the run's horizontal SPACING — its strongest remaining signal, never used; and the second-best assignment, so "two fit equally" is invisible | the fitted count | **B** |
| **`key_signature_template`** (called `transcribe.py:1394`, `:1409`) | slide the Bravura flat/sharp templates along the header window | ⚠️ **per-match NCC score at the refusal**; and the reading it produces enters the vote at `DEFAULTED_CLEF_WEIGHT` where the clef is a positional default, so its own strength never varies | a reading → the vote — **CONSUMED**. ⚠️ It is the reader behind **D20** and the map's Stage 8b previously had no row for it, though CLAUDE.md records it reading **11 of 12** staves where the locator reads 2 | **D** |
| `key_signature_vote._trustworthy:247` | may this reading depart from the system | how FAR it departs (+3 and +1 are equally legal); the reader kind; the residual | a bool → **CONSUMED** (`key_signature_vote.py:292`, `:395`). ⚠️ The prose `reason` is **string-matched**: `transcribe.py:4586` tests its `"rejected"` prefix to set `key_signature_read`, so a REFUSAL REASON IS PARSED AS CONTROL FLOW — while the serialised `key_signature_reason` (`:4607`) itself reaches only a probe | **A** |
| `_consolidate_across_systems:299` | the part's signature across systems | ⚠️ agreement across three systems is worth **exactly what one system is worth** — `max(w for _, w in seen)`, not a sum; the runner-up is dropped with no record | the consolidated reading → `key_signature`, `key_signature_source` — **CONSUMED** (`dossier.py:165`) | **D** |
| `can_carry` `:156` | may a reading travel to another system | ⚠️ it records **nothing numeric** — a one-bit label derived from `source.startswith("template")`, and the `source` string it came from is then never read again | a bool | **A** |
| the unread-staff record `transcribe.py:4590` | mark a staff whose key was never read | — | `key_signature_read` → **CONSUMED**, `clef_correction.py:338`, `:347`, `transcribe.py:5272`. `key_signature_unread_reason` → **`probe`** | **C** for the reason |
| mid-staff key change `transcribe.py:4648` | did the key change within the staff | — | `key_signature_final` → ⚠️ **NOBODY** | **C** |

⚠️ **The clef→key dependency has a structural hole nobody has named.**
`key_signature_geometry.slot_positions` has tables for `treble`, `bass`,
`alto`, `tenor` **only** — so soprano, mezzosoprano, baritone, french,
varbaritone and subbass **cannot have a key signature fitted at all**, and
those are precisely the C clefs the locator is best at. Acknowledged in the
module docstring; not in any status document.

---

### Stage 8c · Time signature

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| `locate_time_signature:439-448` | which meter this staff prints | ⚠️ the runner-up's score — a 0.51 winner over a 0.50 runner-up is indistinguishable from 0.79 over 0.31; and the 21 losing meters entirely | `LocatedTimeSignature` → the system vote — **CONSUMED**; `.symbol` is a **@property** (`:231`) consumed at `:518`, so a field-name grep finds nothing — the 8c twin of the `nominal_line_spacing_px` trap. `.as_dict` → **`probe`**: the vote rebuilds the same dict by hand at `:507` | **D** then **A** |
| `_looks_cut:381` | is a matched `C` really `¢` | the fill fraction once thresholded — a clean 1.00 and a marginal 0.75 are identical, though the docstring publishes the 0.48↔1.00 gap | `symbol` (`"common"`/`"cut"`) → **CONSUMED**, `export.py:874` writes `<time symbol=…>`, worth a flat 3 edits/staff | **B** |
| **`vote_system_time_signature:499`** | do the staves agree | ⚠️ **every reading's `score`, deliberately** — ranking by median score was measured and REFUSED ("identical verdict table, one documented principle weakened"). Also unused *by the vote*: `x_canonical` agreement, since a real meter is at the same x on every staff — though the value itself is **CONSUMED** at `key_signature_template.py:171` as the right bound of the accidental window | the voted meter → **CONSUMED**. `median_score`, `votes`, `voters` → ⚠️ **`probe`** — two benchmark sweeps and the unit tests; **no production reader** | **A** on the floor; **C** for the scores |
| meter precedence `transcribe.py:1777` | specialist digit vs header vote | ⚠️ **neither `median_score` nor `votes`.** And the precedence is ASYMMETRIC: the clef specialist is gap-fill only (`:1774`, `if spec_clef is not None and clef_source is None`) while the meter specialist **overwrites unconditionally** — a 27-of-27 unanimous header vote is replaced by one detected digit in the music | `time_signature` | **D** |
| carry onto a meterless page `transcribe.py:4739` | does last page's meter apply here | — | ⚠️ `inferred_time_signature` → **`probe`, NOT consumed by the exporter.** `export._ensure_inferred_time_signatures` (`:50`, called at `:663`/`:3401`) calls `backfill_page_time_signatures`, which **WRITES** this key (`rhythm.py:704`) and never reads it — what actually reaches the export is the back-filled `time_signature` on each staff and measure | E |
| mid-staff meter change `transcribe.py:4650` | did the meter change within the staff | — | `time_signature_final` → ⚠️ **NOBODY** | **C** |

**`min_staff_fraction = 0.70`, verified at `time_signature_locator.py:192`** —
matching the documented figure. The effective floor is
`int(round(0.70 × total))`, so an 11-staff system needs 8 (0.727).

---

### Stage 9 · Margin labels → instrument

⚠️ **The cascade is not in `_labels_for_page`.** That function
(`contextual.py:549`) runs the work-roster pass; the reader ladder is
`_read_labels_for_page` (`:605-878`). CLAUDE.md, the module docstring and the
original commission brief all name the wrapper.

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| `staff_labels.read_staff_labels:189` | which staff a text span belongs to | span **x** (captured, used only to sort), font size/weight, `group_index`, and **`system_index`** — a two-system page's margins are pooled by y alone | a `{staff_index: str}` map → `contextual._read_labels_for_page` — **CONSUMED** (free rung 1) | **D** + **E** |
| **`staff_labels_surya.read_staff_labels_surya`** (`contextual.py:685`) | the same map, by local OCR, on a page with no text layer | the PDF's own text layer where one exists (rung 1 already ran); the crop's ink density; ⚠️ **any per-block OCR score — Surya's confidences are not carried out of `_surya_worker`** | the map → **CONSUMED** (free rung 2, **on by default**). Self-disables where `.venv-surya` is absent | **D** at the ladder; **A** internally |
| ↳ `_surya_worker._assign:89` block-height gate | drop a block that swallows the crop | ⚠️ the block's **width** and its text; the gate is height-only. It is scale-invariant by construction (a ratio to the system's own tick span) which is why it survives across editions | the surviving blocks. ⚠️ Measured: the two runaway blocks sit at **1.04×** the span, Boléro's 17 correctly-split blocks at **1.5–4.7%** — a ~22× gap. `_RUNAWAY_HEIGHT_FRACTION = 0.5` sits in the middle of it | **E** on a measured empty gap |
| **`staff_labels_vision.read_staff_labels_vision`** (`contextual.py:809-813`) | the same map, from Claude | ⚠️ what the free rungs already read — it is not shown their answer, so it cannot repair, only replace | the map → **CONSUMED** when it runs. ⚠️ **Off by default** and budgeted per system (~1¢); gated on the free rungs returning too few USABLE labels | **E** (a cost gate) |
| `staff_labels_tesseract._words:103` | which OCR words survive | ⚠️ the per-word confidence is **discarded after the threshold** — a 31 and a 95 produce identical evidence | words → the union merge — **CONSUMED** | **B** |
| `staff_labels_human._questions:64` | which staves a human is asked about | ⚠️ `label.confidence` — a `low` label is `matched`, so **the human is never asked about exactly the labels every consumer will silently drop** | questions → ⚠️ **unreachable from `transcribe`**: `_contextual_call_kwargs` (`transcribe.py:4006`) only ever builds `Assist("vision"\|"none")`, and `Assist.switch` is called only from inside this module and only ever switches AWAY from human | **E** |
| `_read_labels_for_page` ladder `:676-878` | which reader's answer stands | ⚠️ **per-label agreement BETWEEN rungs.** Readers are compared by integer counts of USABLE labels only; two rungs agreeing on a staff is worth nothing, and a set-union merge is attempted for Tesseract alone | the page's label map → `slots`, `score_layouts`, `work_roster`, `dossier` — **CONSUMED** | **D**, with one additive rung |
| `_merge_key:476` | quality then reach | whether the two reads DISAGREE on any staff — the key can see how many labels there are, never whether one is wrong | the ordering | **D** |
| ⚑ **`instruments.lookup:873`** | which instrument a string names | ⚠️ **everything except the string.** A pure function with zero context — every contextual repair downstream exists to patch this deliberate blindness | `Match` → ⚠️ **12 production importers across four stages**: all five label readers, `contextual`, `score_layouts`, `work_roster`, `clef_correction`, `dossier.py:457`, **`transcribe.py:2484` and `:2872`**, and `tools/library/instrumentation.py` **outside `tools/omr` entirely** | **D** + **E** |
| **`Match.confidence:77-81`** | high / medium / low | ⚠️ **the coverage float past the 0.6 comparison.** 0.61 and 1.00 become indistinguishable. The `0.6` is a bare literal with no name, no sweep and no benchmark reference | `Match.confidence` → `slots.MIN_LABEL_CONFIDENCE`, `roster.py:219`, `contextual`, `absent_instrument` — **CONSUMED**. `Match.coverage` (the float) → one direct reader, `work_roster.py:518`, which merely rebuilds a `Match`; ⚠️ **nothing past the bucket ever compares it**. `Match.is_ambiguous` → **`probe`**, though the `alternatives` it wraps is read at `work_roster.py:512` | **B** — the pipeline's cleanest Class-B site |
| `work_roster.decide:485-524` | what a label resolves TO | which staff it is on, the other labels on that system, the roster's ORDERING (used as a set) | a `Decision` → `contextual` — **CONSUMED** under `OMR_ROSTER_LABELS`, ⚠️ whose production reach is **NIL** (needs `OMR_WORK_ID`, which nothing sets). `Decision.names_a_staff` → **`probe`** | **D** + **E** |
| `roster.acquire_roster:292` | which system IS the roster | ⚠️ `Roster.coverage` is computed, serialised, and **compared to nothing** — there is no minimum-coverage gate, only an absolute floor of 2 names | the roster → `contextual` — **CONSUMED** (`OMR_ROSTER`, **on**). `Roster.coverage` → **serialised only** — `roster.py:168` puts it in `evidence()` and no behaviour branches on it | **D** + **E** |

⚠️⚠️ **A LEXICON CHANGE RIPPLES INTO GLYPH OWNERSHIP, TWO STAGES UPSTREAM OF
WHERE THIS TABLE FILES IT — and no grep of `transcribe.py` will show you.**
Both ownership call sites import the lexicon **lazily, inside the function**
(`from .instruments import lookup as lookup_instrument`, `transcribe.py:2484`
in `_staff_written_ranges` and `:2872` in `_apply_roster_range_veto`), so
`grep -n 'instruments\.' tools/omr/transcribe.py` returns **one hit and it is a
comment.** This is the same indirection class as the property that hid
`nominal_line_spacing_px` (§8-E1) in a second costume: **a function-local
import.** Check for both before writing a `NOBODY`.

---

### Stage 10 · Slot alignment and part identity

**This stage contains the pipeline's two ADDITIVE-EVIDENCE MODELS**, which is
what makes it the right target for §8b's principle: `slots._pair_score` and
`score_layouts.fit_layouts` sum signed terms with no vetoes.

`slots._pair_score` (`slots.py:472`) — every term:

| constant | line | value | evidence it weights |
|---|--:|--:|---|
| `SCORE_LABEL_MATCH` | 51 | **+6.0** | the names agree |
| `SCORE_LABEL_CONFLICT` | 52 | **−8.0** | two different named instruments — "the only hard negative" |
| `SCORE_GROUP_MATCH` | 53 | +1.5 | the slot's bracket group is reachable from the staff's |
| `SCORE_GROUP_CONFLICT` | 54 | −1.5 | it is not |
| `SCORE_POSITION_WEIGHT` | 55 | 1.0 × (1 − \|Δpos\|) | relative position down the system |
| `GAP_PENALTY` | 56 | −1.0 | skipping a reference slot (part tacet) |

⚠️ **−8.0 dominates every other term combined** (max non-label positive is
1.5 + 1.0 = 2.5), so the label conflict is a hard gate wearing an additive
coat. ⚠️ And **`SCORE_LABEL_MATCH` is the far end of the `Match.coverage`
quantisation in Stage 9**: a label matching at 0.61 coverage and one at 1.00
arrive here identical, and a 0.59 does not arrive at all. **A builder adding a
term to this table is looking at the wrong end of that pipe** — §7.2 item 12 is
the same signal, and the two are one decision, not two.

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| `reference_candidates:214` | the canonical part list | page ORDER (a system's position is not evidence here); clefs; bracket structure as a candidacy test | the reference → `align`, `fit_layouts` — **CONSUMED** | **D** + **E** |
| `map_groups:363` | may bracket groups be compared at all | labels, clefs, positions, bracket nesting depth — the reading is reduced to an ordinal before it arrives | the group map → `_pair_score` — **CONSUMED**. `best_cost` → **NOBODY** | **E** (a tie of different meanings abstains — correct, §0.1) |
| **`align:492`** | the staff→slot assignment | ⚠️ **no score is ever returned.** `align` returns `list[int]`; `dp` is read only to fill `back[i][j]`, and the traceback at `:534-542` reads `back`, never `dp`, so **no caller can know how confident an alignment was** — `_compose` re-derives evidence by counting contradictions afterwards because the score is unavailable | `slot_index` → **CONSUMED** by `export._stitch_slots_by_slot`, `contextual`, the whole identity block. The **score** → **NOBODY, because it does not exist** | **A** |
| `fit_layouts:530` | what each slot is, from position + clef + labels | ⚠️ **bracket groups** — `fit_layouts` has no group parameter at all, so `slots`' strongest structural signal never reaches the layout vote; also register, indent, key signatures | ⚠️ there is no `.slots` — the field is `assignment`, reached through `instrument_for()` (`contextual.py:1141`) and `support_for()` — **CONSUMED**. `.agreement`, `.considered`, `.score_per_staff` → ⚠️ **NOBODY**: `agreement` is cut to a name-or-None *inside* `fit_layouts:583` and only the post-cut assignment escapes, and `contextual.py:833` discards it deliberately — it reads 1.000 for 70% of the WRONG answers | **B** |
| `_read_clefs_by_slot:1076` | which clefs the layout vote may see | ⚠️ nothing — this is the well-built one. It admits a staff only if it carries `clef_source`, so `clef_correction`'s output cannot re-enter | `clef_by_slot` → `fit_layouts` — **CONSUMED**, and worth **+51 identity records on Beethoven 5** where the label channel is worth 0 (§4.2 Cycle 2) | evidence gate on **provenance**, the model form |
| `score_layouts.resolve_ambiguous_label:597` | the narrow 2-way question | the MAGNITUDE of support — only `> 0.0` is tested, so 0.64 and 0.01 are identical | `instrument_by_slot[slot]` **and a document-wide write into `reference`** — **CONSUMED**. The count → `ambiguous_labels_resolved` → **`probe`** (write at `contextual.py:1491`; only `test_score_layouts.py:295` reads it) | **B→D**. ⚠️ §4.3's per-system-refusal/document-wide-write hazard lives here |
| `instrument_source` assignment `:1136-1148` | the provenance tier | ⚠️ **which page actually carried the label.** The tier is per-SLOT, so a staff twenty pages from the only page that named its slot is stamped `label` | `instrument_source` → **CONSUMED, and load-bearing**: `contextual.py:1385` (the clef gate), `absent_instrument`, `label_contradiction`, `offroster_name` | **D** |
| roster precedence `:1058` | page read beats roster | ⚠️ **a roster that CONTRADICTS the page read is silently discarded with no record.** There is no `roster_disagreements` field | `instrument` | **D** |
| **`movement_reference.lineup_spans`** (`slots.py:565`, `:587`; `OMR_MOVEMENT_REFERENCE`, **default ON**) | where the document's lineup GREW — boundary pages are those setting a new running maximum system size (`_peaks:455`) | ⚠️ **movement boundaries**: it finds one boundary in Beethoven 5's four movements, and says so. A lineup that SHRINKS is invisible by design. No window, no smoothing, no tolerance — and **no probability is formed anywhere**; `_align_by_span` returns `False` rather than guessing | page-index spans → `slots._span_views` → `_align_by_span:660` — **CONSUMED**. ⚠️ This is the flag that shipped default-ON on one work and made a second **four times worse**, and it is **not in CLAUDE.md's env table** (§8-D24) | **E** — the subsequence axiom: a system may OMIT a part, never INVENT one |
| `absent_instrument.find_vetoes:293` | strip a name no nearby page attests | clefs, register, bracket group, and — by design — misread labels; ⚠️ `distance_pages` is computed and used only through a hard interval test at window 0 | `instrument_veto` → ⚠️ **SERIALISED-ONLY** (written `contextual.py:1341`; `label_contradiction` reads the *summary* blob `absent_instrument_veto`, not this field). The removal itself → **CONSUMED** | **E** |
| `label_contradiction.find_contradictions:122` | **nothing** | it is evidence-only by design, and says so | `label_contradiction` → ⚠️ **NOBODY, deliberately.** 158 firings, 0.873 of them the export being wrong, 0 both-right; what it should DO is undecided | **C** |
| `propose_clef` `clef_correction.py:214-279` | which clef the register prefers | ⚠️ the detector's clef confidence — **measured at this site and REFUSED**: misread trebles score 0.34 and 0.72 while a correct one scores 0.61 | `staff["clef_proposal"]` → ⚠️ **NOBODY** (write at `clef_correction.py:640`, no reader). `.confidence_label` → **NOBODY** — `do_apply` at `:612` is decided by `clef_was_read` plus the treble override, never by confidence. `.applied` → **CONSUMED** as a summary count (`contextual.py:1494`). The applied clef itself → **CONSUMED** via `apply_proposal` | **B** + **D** + **E** |

⚠️ **`propose_clef` has FIVE `return` statements, not six** (`:232`, `:245`,
`:262`, `:266`, `:274`) — four refusals and one proposal. Every one of them
discards the whole `fits` dict — ⚠️ and `fits` is a **local** at `:235`, collapsed to the scalar `fit` at `:277`, so the per-clef ballot never becomes a field anyone could read.

⚠️⚠️ **The clef gate everybody has been discussing is the wrong one.**
`sources.get(slot) == "label"` sits at `clef_correction.py:616`, inside the
**OVERRIDE** branch. The **FILL** tier is `do_apply = apply and not detected`
(`:610`) — **no source gate at all inside the function**. What blocks the fill
tier is caller-side: `contextual.py:1380` builds `read_instruments` by dropping
`score_order` (and `roster`, unless `OMR_ROSTER_CLEF`), so those slots never
reach `propose_clef` on either tier. Consequence:
**`score_order_ambiguity` reaches FILL and is blocked from OVERRIDE.**

⚠️ **`bracket_reader.py` (390 lines) would belong in this table and has no call
site.** A complete, tested, benchmarked classical-CV bracket reader whose own
docstring says *"Nothing in the pipeline consumes this module"*; its only
importer anywhere is `test_bracket_reader.py:21`. It forms a full verdict —
`blocks`, `boundaries`, **`interior`** (the gaps a bracket asserts are *not*
boundaries) and `verdict` — and `interior` is evidence
`system_grouping.gap_bridging_counts` **structurally cannot supply**, while
`fit_layouts` above is blind to bracket groups and `_assign_groups` infers them
from ink columns. Class **C**, at 390 lines. See §7.4 before starting any
bracket workstream.

---

### Stage 4b · Tie pairing — `transcribe._pair_ties_in_cell` / `_pair_ties_in_staff`

Named in §2's spine and, until this revision, absent from §5 entirely.
**~25 decision points; the 12 that matter.**

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| `_pair_ties_in_cell:2242` | which detections are ties | the detection's `confidence`; and slur-classed arcs that are geometrically ties. A tie and a slur are the **same glyph** (`docs/position-grammar-confusables-2026-09-04.md` §2); the corrective (`export._arc_reclass_enabled:1867`) is default-OFF and lives in a different file, **after** transcribe has committed | `ties_to_next`/`ties_from_prev` → `tied_to_next`/`tied_from_prev` — **CONSUMED** by `voicing`, both exporters | **D** — raw class argmax |
| `:2247-2251` | the vertical window | ⚠️ **`line_spacing_px`.** `y_tolerance = max(avg_nh_h * 3, 30)` — a **raw 30-pixel floor** in a pipeline whose stated doctrine (`direction_text.py:74-78`) is that every geometric rule is in staff spaces. It means a different thing at every DPI and on every publisher | candidates | **B** |
| `:2270`, `:2275` | the horizontal window | the barline — cell-local, so a tie whose partner is in the next cell finds nothing here | candidates | **B** |
| `:2266-2277` | which two heads a tie joins | ⚠️ **everything but x-distance** — no pitch, no duration, no beat, no stem, and **no adjacency**: nothing requires the two heads be consecutive, so a nearer head with three heads between it and the other end wins | one (left, right) pair | **D** — argmax, no score formed |
| ⚑ `:2236-2239` + `:2279` | the pitch check that does not exist | ⚠️⚠️ **PITCH — structurally, not by choice.** A tie is *defined* as joining two notes of one pitch. The docstring says *"not checked (and not available)"*; the fact exists 300 lines away in `pitch_by_id` and is simply not passed in (§8-D19). The only refusal is `best_left is not best_right` | — | **A**, then **E** |
| `_pair_ties_in_staff:2038` (called `:4615`) | the cross-cell mirror, in page pixels | ⚠️ **its own return value.** `n_new_pairs` is computed at `:2112-2121`, with a `was_already_paired` guard so it means something, and **discarded at the call site** — `_pair_ties_in_staff(staff_dict)` with no assignment. No `tie_pairs` field, no log line | an `int` → **NOBODY** | **C** |
| `:2091` | the same two constants again | ⚠️ **the frame change.** `max(avg_nh_h * 3, 30)` is applied here in PAGE px where `:2247` applied it in CANONICAL px, and the cell is upscaled — two different physical distances, and nothing records which fired | — | **B** |
| `:2136`, `:2141` | window `w * 3` here vs `w * 2` in the cell pass | ⚠️ **any measurement.** Unlike `_SLUR_BOUNDARY_SPACES` or `_ARTIC_MAX_DX_NOTEHEAD_WIDTHS` there is no sweep, no plateau and no FINDINGS reference for either 2 or 3 | — | **B** |
| `:2065-2073` | which noteheads are candidates | ⚠️ **pitch and duration.** Contrast `export._measure_noteheads:2271`, which filters `pitch is not None and duration_beats is not None` *precisely because* an unpitched detection never becomes an event — so a tie here can anchor to a head that never becomes a note, and evaporate downstream | — | **E**, a missing refusal |
| `:2112-2120` | union semantics between the two passes | ⚠️ **disagreement.** Flags are only ever set `True`, never cleared, and the two passes can pick different partners for one glyph: a head can end up `tied_to_next` toward a head that is not `tied_from_prev` from it. The relation is never checked for consistency | — | **E**, no refusal where two answers conflict |
| `voicing.py:215-216` | the chord's tie flag | which member was tied — `any(...)` over the group | event-level flag | **B** |
| ⚑ `export.py:3002-3003` | which notehead wears the tie | ⚠️ combined with the row above: a four-note chord whose **top** note is tied exports `<tie>`+`<tied>` on notehead **index 0**. Scored under musicdiff's `Ties`, so the tie lands on the wrong pitch and is charged | `<tie>`/`<tied>` | **B** |

---

### Stage 9′ · Direction text — `direction_text.py`

**~72 decision points; the 14 that matter.** In §2's spine, ~75% of whole-work
wall clock, and absent from §5 until this revision.

| decision (file:line) | decides | ⚠️ blind to | produces → consumed by | shape |
|---|---|---|---|---|
| ⚑ **the `Reader` type `:614`** | the shape of every OCR answer | ⚠️⚠️ **`Reader = Callable[[list[np.ndarray]], list[str]]` — there is NO CONFIDENCE ANYWHERE IN THE INTERFACE.** Not per crop, not per character, not per rung. Surya returns a score internally and Tesseract has `image_to_data` confidences; **neither can cross this boundary.** Every downstream choice is therefore *forced* to be positional or lexical | the reader contract | **A — structural**, and the purest example in the pipeline: a probability that cannot be formed because the type will not carry it |
| ⚑ `read_directions:801` | which rung wins | ⚠️ **which rung was more likely right on this crop.** `winner_name, hit = accepted[0]` — `accepted` is built in `readers` **list order**, so the winner is Surya-if-present, unconditionally. Not a tie-break, not a vote, not a score: position in a list. `default_readers:689-692` is candid — *"this rule has never yet been load-bearing"* | the winning `DirectionText` | **D** |
| ⚑ `:802-809` | records the disagreement | — | ⚠️ `info["conflicts"]` → **the report dict only.** It is **not** a field on `DirectionText`, not among `to_json()`'s eight keys, and never reaches the measure, the artifact or the exporter. **A two-rung-agreed reading and a two-rung-disagreed reading are the same object downstream** | **C** |
| ⚑ **the lexicon gate `:795`** | is this string a musical direction | ⚠️ **any real marking not in `_TEMPO`/`_EXPRESSION`** — an unknown Italian or German term is indistinguishable from noise; and the OCR's own confidence, which is *why* a lexicon is the only gate available. It tests, in order: charset (`direction_lexicon.py:149` — any digit or bracket rejects, which kills bar numbers and rehearsal letters), phrase length, an **adjacent-repeat veto** (`:166` — the Surya `arco. arco. arco.` failure mode), every token known, and at least one real term | an accepted reading. ⚠️ **"Load-bearing, do not loosen"**, and the arithmetic is at `direction_lexicon.py:11-16`: OMR-NED charges an invented direction exactly what it charges a missed one, so precision and recall trade **1:1** and only a gated reader is safe | **E** — a CONSTRAINT under §0.1, not an opinion |
| ⚑ `_blank_detections:301` | which ink is not a letter | ⚠️ **three ways.** (1) It erases the BOX, not the glyph: a slur box at 24.2 × 4.0 spaces once erased all nine components of `sempre`, so `max_blank_width_spaces = 4.0` was added — a hard cut, and a 7.7-space pedal bracket survives it. (2) **Detector RECALL**: a glyph the detector missed stays in the mask and competes as letter ink, so this method's recall is the detector's precision inverted. (3) It was blind to its own dependence on detector output until a `dynamicP` at 0.87 inside `espr.` was correctly detected, correctly blanked, and took `espr. e legato` off two Brahms staves — **56 edits**. The repair (`_is_inside_a_word:282`) is excused for `category == "dynamic"` only, deliberately | the ink mask → `find_candidates` | **E** with a **B** inside it |
| `_letter_components:353` | letter or curve | ⚠️ a curve that is THICK (a beam fragment, a heavy tie at low DPI) and a letter that is THIN (an italic `l`, a hairline serif). ⚠️ And unlike its neighbours it has **no sweep and no probe script cited** beside it | components | **B**, `min_fill_ratio = 0.16` |
| `page_is_engraved:617` | drop the Tesseract rung | a born-digital edition whose font defeats Surya — the docstring says so. The claim rests on **three** LilyPond fixtures; asymmetric by design, any doubt → `False` | the rung list | **E** |
| `find_candidates:552` | is this above-staff text a heading or a direction | ⚠️ **a second above-staff direction later in the system.** `above_first_measure_only` is the *only* thing separating a movement heading from `Allegro con brio`: `above_spaces = 8.0` cannot, because Mahler's title sits closer to its staff than Beethoven's direction does | candidates | **E** |
| `_bands_for_page:456` | who owns the inter-staff gap | which staff the engraver meant — chosen geometrically (upper staff takes the whole gap within a system; split at the midpoint across one) so no word is ever offered twice | bands | **E** |
| `_measure_at:483` | which measure a word belongs to | ⚠️ a word in the margin BETWEEN systems is **clamped** into the first or last measure rather than dropped — out-of-range never abstains | the measure index | **E**, an absent refusal |
| `_cluster_into_words:397` | what counts as a word | a two-glyph marking (`fp` is excluded on purpose, but so is every real one); and a word whose letters were partly eaten by `_blank_detections` — `CROP_PAD_X_SPACES` exists because *"`legato` read as `egato` is a lexicon miss, not a near miss"* | words | **B** |
| `crop_for:606` | the upscale factor | whether the upscale helped — nothing measures per-crop legibility | a crop | **B** |
| `:784-787` | a rung that crashed | — | `info["failed_readers"]` → ⚠️ the report only. Note the asymmetry with the conflicts row: a rung CRASH and a rung DISAGREEMENT are both recorded in the report, and **neither reaches the artifact** | **C** |
| `attach_to_page:825` | landing a direction on a measure | ⚠️ the difference between "no directions on this page" and "**eight directions that could not be landed**" — an unmatched staff or measure index is dropped silently and only the `placed` count survives | `measure["direction_texts"]` — **CONSUMED** (2 of its 8 keys, below) | **E** |

⚠️ **`direction_texts` carries eight keys and `export.py` reads two.**
`to_json()` (`:254-266`) writes `staff_index`, `measure_index`, `x_page`,
`text`, `category`, `placement`, `terms`, `reader`.
`measure_direction_words:1362-1373` touches **`text`** and **`x_page`**.
The other six are **SERIALISED-ONLY** — including **`placement`**, which the
reader computes per candidate (`above`/`below`, from `_bands_for_page`) and
which `_mxl_direction` overwrites with the literal `placement="below"` at
`:1403` and `:1412`.

⚠️⚠️ **And that hardcode costs exactly zero, provably, which is the point.**
`placement` is a MusicXML *print-style* attribute, so it falls under
musicdiff's `Style` bit — **excluded from `AllObjects`**. No benchmark in this
repo can see it. The only consumer that could is a human reading the file, or
LilyPond, which never receives a `<words>` at all.

---

### Stage 11 · Export

⚠️ **The exporter reads no confidence, and its dead-signal list is the longest
in the pipeline.** At the end of the pipeline, *"consumed by"* means **which
element it writes and which harness can SEE that element** — so this table's
consumer column names musicdiff's detail bits, `export_coverage.VISIBLE`, and
whether LilyPond gets it at all.

**`export_coverage.VISIBLE` — all 19 entries** (`export_coverage.py:181-200`):
`accidental · articulations · accent · barline · bar-style · beam · dot ·
dynamics · fermata · lyric · metronome · notations · slur · stem · tied ·
time-modification · tuplet · wedge · words`.

⚠️ **Two structural limits on that check, both load-bearing.** It is
**categorical only** — `compare():270-285` reports an element *only* when ours
is **zero** and truth is non-zero, so a regression from 118 wedges to 3 is
invisible. And it is **pooled over 11 works**, so a total gap in one work is
masked if any other work emits the element.

⚠️⚠️ **What `AllObjects` EXCLUDES is the more useful half**
(`.venv-omrned/…/musicdiff/detaillevel.py:23-112`): `Style` (stem direction,
placement, colour), `Metadata`, **`Voicing`** (*"we ignore which voice and
chord each note is in"*) and `NoteStaffPosition`. **The metric cannot see
voices** — which matters below, because two of the exporter's most destructive
refusals are enforced *against a fact the metric cannot score.*

| decision (file:line) | decides | ⚠️ blind to | produces → who can SEE it | shape |
|---|---|---|---|---|
| `_parse_pitch:213` | is this pitch renderable | ⚠️ **`pitch_candidates`** — `grep -c pitch_candidates export.py` is **0**. An unparsable primary pitch becomes a `<rest/>` rather than falling to candidate #2, and is then charged twice (delete note + insert rest) | `<pitch>` / `<rest/>` → musicdiff **YES** (`NotesAndRests`). ⚠️ VISIBLE: **NO** — neither `pitch` nor `rest` is in the set, so a total pitch-parser failure is invisible to the coverage check. LilyPond: yes, via a **separate** parser (`_pitch_to_lily:262`) | **A** |
| `_compute_divisions:785` | the score-global `<divisions>` | `tuplet` — the ratio that CAUSES the thirds is on the dict, and the denominator is rediscovered from the float instead | `<divisions>` → musicdiff **indirectly** (a wrong LCM becomes wrong durations becomes `wrong note`). VISIBLE: **no**. LilyPond: **no concept** | **D** |
| `<duration>` rounding `:917`, `:2982` | the integer duration | ⚠️ `duration_type`+`dots` (the same fact by another route, never cross-checked) and **`rhythm_sum_warning`** — the pipeline's own statement that this bar does not sum, unread at the exact moment `<duration>` is written | musicdiff **indirectly, and it is the whole rhythm score**. ⚠️ It compounds: `total_dur` is a sum of ROUNDED units and is what `<backup>` rewinds by, so drift shifts voice 2. VISIBLE: **no**, named at `:180` as failing the membership test. LilyPond: **no** | **B** |
| `measure_dynamics:1313` | is this run one word | `bbox[3]`; **`bbox_page`, so a dynamic straddling a barline cut is unjoinable by construction**; both letters' confidence | `<dynamics>` → musicdiff **YES** (`Directions`); VISIBLE **yes**; ⚠️ LilyPond **NO — it emits no `\f`/`\p` at all**, on any measure | **A** |
| ⚑ **`measure_dynamics:1341`/`:1345`** | a run spelling no dynamic is DROPPED | ⚠️ the run's own letters (no partial recovery) and their confidences. **Measured: 45 of 45 scan and 8 of 8 engraved refused runs are edit distance 1 from a legal dynamic; refused letters p25 0.398 vs kept 0.699** | nothing — a silent drop | **E** — the clearest conversion candidate in the pipeline |
| `measure_direction_words:1349` | where an OCR'd word sits | ⚠️ **six of the eight keys** the reader writes (above) | `<words>` → musicdiff **YES**; VISIBLE **yes**, and it is `FLAG_DEPENDENT`'s only member. LilyPond: **NO** | **C** |
| `annotate_fermatas:997` | which event wears a fermata | ⚠️ `confidence` — **the docstring quotes it as 0.90-0.95 and is the file's single `confidence` occurrence**; and **y entirely**, so a fermata on the wrong staff of a system cannot be detected | `<fermata/>` → musicdiff **YES** (`Ornaments`); VISIBLE **yes**; LilyPond **yes** | **D**, and the fallback has no distance ceiling |
| `_pick_beam_box:1119` | which beam box a notehead joins | notehead **y** (`centre()` computes it and it is never read); `stem_direction`; every notehead past `heads[0]` | `<beam>` → musicdiff **YES** (`Beams` — and its own enum note, *"if not requested, beams are treated exactly like flags"*, is the 430-of-449 `editbeam` bucket); VISIBLE **yes**; LilyPond **NO** (it auto-beams) | **D** |
| `_arbitrate_arcs_in_system:1753` | which staff owns a slur/tie | distance to the staff LINES (**explicitly refused** — "the trap it was for notes"); the arc's confidence; `staff["instrument"]` and its range, read by the notehead arbiter and not here | moves a `<slur>`/`<tied>` between parts → musicdiff **YES**; ⚠️ VISIBLE **can never see it** (it moves, never zeroes). ⚠️ In the DEFAULT `move` mode a rival-owned arc is **deleted outright** (`:1789-1791`) and `moved` is returned to `to_musicxml:3402` and **discarded** | **C** + **E** |
| `_wedge_anchors:2678` | which note a hairpin opens on | head **y** — though a hairpin is always BELOW its staff, 8 of 8 in the page truth | `<wedge>` → musicdiff **YES** (`Directions`, scored by the anchor pair's offset). VISIBLE **yes**. LilyPond **yes, but drops more**: one hairpin at a time, dropped across a lane flip, dropped across a system break by construction | **D** |
| `_wedge_anchors:2694` | where it stops | ⚠️ **`duration_beats` of the note still sounding** — which answers "is it still sounding at the ink's end" DIRECTLY, and is answered by geometry instead | as above | **D** + **E** |
| ⚑ **`_stitch_slots:3231`** | may the systems be joined into parts | ⚠️ **the largest unread set in the file.** `staff["instrument"]` — the exact fact that would join a tacet-suppressed system, read four functions later for NAMING and never for joining; `staff["slot_index"]` (the whole `_stitch_slots_by_slot` that uses it is behind `OMR_SLOT_STITCH`); `staff_geometry`; `clef`; `key_signature`; measure counts | `<part>` boundaries → musicdiff **YES, and expensively** — an unpaired truth PART costs more than that part's unpaired MEASURES. ⚠️ VISIBLE: **NO** — `part` is not in the set, so **the single largest structural lever in the exporter is invisible to the coverage check**. LilyPond: **no stitching at all**, one `\new Staff` per (page, system, staff) | **E**, the canonical one |
| `_condensed_count:3303` | how many parts one condensed staff emits | ⚠️ the TIER that produced the count — `condensed_parts.players_for_label` has four evidence tiers and only the integer would travel. ⚠️ **And nothing writes the field**: no production module calls `players_for_label` and the only writer of `condensed_parts` is a benchmark script, so `_condensed_count` always sees `{1}` and **the knob is inert whatever it is set to** | part count → musicdiff **YES**; VISIBLE **no** | **E** + **A** |
| piano grouping `:3428`, `:3490` | emit a brace | ⚠️ **`staff["instrument"]`** (a 2-staff orchestral extract becomes a piano) and **the bracket block**, which `transcribe.py:4436` emits specifically because it had never reached the dict, and which export still does not read | `<part-group>` → musicdiff **YES** (`StaffDetails` → `AnnStaffGroup`, ~4 symbols; our brace has a symbol so the all-parts skip does not apply). ⚠️ VISIBLE: **NO**. LilyPond: a `\new PianoStaff`, per system, with no number and no barline property | **A** |

#### Slur and arc pairing inside export — ~46 decisions, the 13 that matter

| decision (file:line) | decides | ⚠️ blind to | produces → who can SEE it | shape |
|---|---|---|---|---|
| ⚑ **`_number_spans:2517-2520`** | which simultaneous spans get a MusicXML number | ⚠️⚠️ **THE 7TH SIMULTANEOUS SPAN IS DROPPED SILENTLY.** `number = next((n for n in range(1, max_number + 1) if n not in open_spans), None); if number is None: continue`, with `max_number = 6` for both slurs (`_MAX_SLUR_NUMBER:1592`) and wedges (`_MAX_WEDGE_NUMBER:2565`). **No counter, no warning, no field** — `export.py` imports no `logging` and defines no logger; `_pair_slurs_in_run` returns only `n_marked`, so a run that drops three and marks four is indistinguishable from one that had four; `annotate_slurs_in_slot`'s return is summed and then discarded at every call site. ⚠️ And VISIBLE cannot see it either: `slur` is in the set and is satisfied by the other six | nothing — a silent drop | **E**, unrecorded — §7.1's exact target |
| `:2505` | which span loses the number | ⚠️ the drop is **start-order-biased**: spans are sorted by start and numbers handed out first-come, so the span dropped is always the last to OPEN — never the shortest, never the least confident, because **there is no confidence to rank by** | — | **D** |
| `:2513` | when a number is released | it deliberately inflates simultaneity — a stop-then-start on one note holds two numbers at once, bringing the 7-span ceiling one span closer | — | **B** |
| `_merge_arcs_across_barlines:2226` | was this arc clipped by the cell edge | ⚠️ whether it was clipped **at all** — the detection carries no clipped flag; the boundary is inferred from `bbox_page_px` | segment chains | **B**, `0.5` spaces on a measured 0.10↔1.58 gap |
| `:2246-2260` | are these two halves one slur | ⚠️ **arc CURVATURE and direction.** Two slurs crossing a barline 1.5 spaces apart are joined to the wrong partners by nearest-y, with nothing to break the tie | one merged slur | **D**, `2.0` spaces (plateau 1.0–6.0) |
| `:2247-2253` | continuation across a SYSTEM break | a slur that legitimately crosses from above the staff to below it across the break — the sign test forbids it | — | **E** |
| `_resumes_after_system_break:2161` | is this the resuming half | ⚠️ a system whose first cell has **no noteheads** — it returns `False`, the chain breaks, and both halves become one-sided | a bool | **E** |
| `:2264` | may a slur skip a junction | a slur spanning a whole empty measure (three segments, middle absent) | — | **E** |
| `_noteheads_under:2284` | which heads an arc covers | ⚠️ **the arc's HEIGHT — there is no y term whatsoever.** A slur box over staff 1 admits any head of that measure at any pitch; and the box is a rectangle around a curve, so its corners are paper | the covered list | **B**, pad `0.25` head widths |
| `_measure_noteheads:2271` | which heads are eligible at all | ⚠️ **nothing — this is the CORRECT refusal**, and it is exactly the one tie pairing lacks (Stage 4b, `:2065`). Worth recording as the contrast case | — | **E** |
| ⚑ `_paired_spans:2472` | a slur over fewer than 2 recovered heads is DROPPED | ⚠️ **detector recall.** And an undocumented asymmetry: `_wedge_anchors:2647-2660` was changed on 2026-09-05 to stop doing exactly this — *"ONE ANCHOR IS ENOUGH — Sean's rule"*, worth 116 → 118 wedges. **Slurs still require two** | a silent drop | **E** |
| ⚑ `_paired_spans:2478` | the one-voice rule | ⚠️ **which voice is RIGHT** — the FIRST covered head decides, by position, not by how much of the slur each voice holds (this is §8-D28: the comment promises the *longest* run). ⚠️⚠️ And the voice assignment comes from `split_events_into_voices` (stem direction), **a fact musicdiff cannot score** because `Voicing` is excluded from `AllObjects` — **so a slur is silently truncated or destroyed on the strength of an unscoreable fact** | a silent drop | **E** |
| `annotate_slurs_in_slot:2374` | the idempotency sweep | ⚠️ ORDER. The same staff dict is reachable from both the stitched path and `_staff_measures_xml`; this sweep is the only thing keeping a double export from stacking marks, and **nothing asserts it ran** | — | **E** |

⚠️ **LilyPond gets strictly less, and it is not in `KNOWN_GAPS`.**
`annotate_beams`, `measure_directions` and `measure_dynamics` are called
**only** from the MusicXML path — seven of the twelve rows above are
MusicXML-only. Beams and dynamics are computed by the pipeline and dropped
from every `.ly` file on every measure; `export_coverage` cannot see it
because it compares MusicXML.

**`KNOWN_GAPS` today — six entries, all open**
(`export_coverage.py:208-246`): `barline`, `bar-style`, `lyric`, `metronome`,
`words` (the one conditional entry; `FLAG_DEPENDENT` has exactly this member),
`stem`. The **nine numbered closed gaps** live in the module docstring at
`:18-26` with their closing commits; `wedge` and the accent entry left the list
when they closed, which is what
`test_the_inventory_has_no_stale_entries` enforces.

---

## 6. The information ledger — every signal, and who reads it

The other axis Sean asked for: **track each PIECE of information.** Verdicts:
`CONSUMED` (a production path reads it) · `TEST-ONLY` (only tests/benchmarks) ·
`SERIALISED-ONLY` (reaches the JSON, nothing loads it back) · `NOBODY`.

Reproduce the whole table with
`python3 benchmarks/omr-decision-map-2026-09/verify.py --json` (checks `V2`,
`V6`) and the census script printed in §10.

### 6.1 The result JSON, by verdict

| verdict | keys |
|---|---|
| **CONSUMED** | `pages` · `page_index` · `systems` · `system_index` · `staves` · `staff_index` · `measures` · `measure_index` · `detections` · `bbox_page` · `bbox` · `class` · `category` · `pitch` · `duration_beats` · `duration_type` · `dots` · `beam_levels` · `tuplet` · `tuplet_group` · `articulations` · `accidental` · `stem_direction` (LilyPond only) · `tied_to_next`/`_from_prev` · `clef` · `clef_source` · `key_signature` · `key_signature_read` · `time_signature` · `staff_geometry.line_ys_page`/`line_spacing_px` · `bbox_page_px` · `upscale_factor` · `direction_texts` · `slot_index` · `instrument` · **`instrument_source`** · `phase1_warning` · **`rhythm_sum_warning`** · `confidence` · the seven `n_*_total` counters the backend reads |
| **TEST-ONLY** | `measure_count_warning` · `key_signature_warning` · `clef_register_warning` · `time_signature_disagreement` · `staff_geometry.line_thickness_px` · `staff_geometry.line_wander_px` · `staff_geometry.x_start`/`x_end` · `ambiguous_labels_resolved` and most of the `contextual` summary |
| **SERIALISED-ONLY** | ⚠️ `clef_final` (its only reader, `clef_correction.py:551`, is its own keeper — nothing downstream) · ⚠️ `inferred_time_signature` (`export._ensure_inferred_time_signatures` **writes** it via `backfill_page_time_signatures` and never reads it) · `weight_routing` · `clef_proposal` · `label_contradiction` · `group_index` · `pitch_candidates` · `contested_notehead_pairs` · `roster_range_veto` · `n_clipped_notehead_fragments_dropped` · `n_cross_staff_duplicates_removed` · `n_unladdered_noteheads_dropped` · `key_signature_reason` · `key_signature_unread_reason` · `instrument_label` · `instrument_family` · `instrument_veto` · `page_size_px` · `skew_corrected_deg` · `weights` · `imgsz` · `iou_threshold` · `agnostic_nms` |
| **NOBODY** | `n_measures_dropped_as_furniture` · `clef_overridden_by_dossier` · `key_signature_final` · `time_signature_final` · `rhythm_reconciliation` (the per-measure RECORD — only the integer counter is read) · `contextual.clef_fills` · `contextual.dossier_clefs` |

⚠️ **`confidence_label`: nine write sites, and NO DECISION reads it.** Every
warning block computes a high/medium/low label that nothing consults. That is
the purest dead field in the schema. ⚠️ Narrowed 2026-09-07 from "zero readers
anywhere in the tree", which was too strong: `clef_correction.py:627` reads
`proposal.confidence_label` to serialise it, 13 test assertions read it back,
and two benchmark probes harvest it. Nothing *acts* on it.

### 6.2 The application boundary — ten fields of a 67k-detection JSON

`backend/modules/local_omr.py` reads exactly: `n_measures_total`,
`n_pages_processed`, `n_detections_total`, `runtime.total_s`,
`n_noteheads_total`, `n_noteheads_pitched_total`,
`n_noteheads_with_duration_total`, `phase1_warning` (presence),
`rhythm_sum_warning` (presence), `detections[].confidence` (mean).
`backend/main.py` re-opens the file for the same per-page mean. **That is the
whole boundary.**

⚠️ **CORRECTED 2026-09-07.** This paragraph used to add *"`musicxml_builder.py`
reads `clef`, `key_signature`, `time_signature`, `pitch`, `dots`,
`articulations`"* — **which is a different engine's boundary, not this one's.**
`musicxml_builder` is imported by `backend/modules/claude_vision_omr.py:29` and
by nothing else; it serialises the **Claude Vision** OMR's JSON, whose shape
`transcribe` never emits (`data["staves"]` at top level, `staff_id`,
`instrument_name`, `measures[].staves[].voices[].elements[]` —
`musicxml_builder.py:581-626`). The local pipeline's `clef` / `pitch` /
`key_signature` do **not** reach the application through it. This strengthens
the conclusion below rather than weakening it.

**The frontend reads ZERO OMR-result keys.** The only OMR-derived numbers a
user ever sees are the per-page mean confidence (surfaced as
`FlaggedDifference.audiveris_confidence`) and a synthesised 0-1
`confidence_score`.

So: the entire identity layer, every warning, every provenance field, the
weight-routing verdict, the clef proposals and the label contradictions
**never cross into the application at all.**

### 6.3 Signals with a home already built and no run that fills it

| signal | where it would go | why it is empty |
|---|---|---|
| `clef_locator` symmetry / ink fraction / rejecting branch | `locate_clef(trace=...)` | neither pipeline call site passes a `trace` |
| `key_signature_locator` `boxes` / `accidental` / `decided_by` | the returned `LocatedKeySignature` | `transcribe.py:1375` reads `.read` only |
| `_dedupe` per-pair band distances and ladder rung counts | `OMR_CONTEST_DUMP` | the dump records confidences and the deciding tier — **not the distances**, the quantity documented as a coin flip |
| `absent_instrument` full evidence blob | `report` mode | consumed only by offline sweeps |

---

## 7. Gathered and never used — the list

**Ranked by what it would cost to consume, cheapest first.** Every row is a
number the pipeline already computes.

### 7.1 Free — the number exists and needs only a home

1. **Detection confidence at the export boundary.** `[V1]`: 1 occurrence, a
   comment. On a scan **29.7% of detections are under 0.40** and the median
   notehead is 0.733 (engraved: 4.9%, 0.884). Roughly a third of a scanned
   page's exported symbols are marginal detections the exporter treats as
   certainly true.
2. **`confidence_label`** — 9 writes, 0 reads.
3. **The four inert consistency checks** — 140 scan / 21 engraved firings,
   every one dead `[V2]`.
4. **`clef_locator`'s trace** — the recorder exists; no call site passes it.
5. **`propose_clef`'s `fits` dict** at all five exits. The additive-vs-gated
   survey had to *reimplement the function* to learn that ~50% of both
   populations exit at `already_in_effect`.
6. **`align`'s DP score** — a whole-pipeline identity decision returns
   `list[int]` and no margin.
7. **`_reconcile_measure_to_meter`'s second candidate** when two exist —
   known exactly, recorded nowhere.
7b. ⚠️ **The 7th simultaneous slur or hairpin.** `export._number_spans:2517-2520`
   runs out of MusicXML numbers at 6 and `continue`s — **no counter, no
   warning, no field**, and `export.py` defines no logger at all. The
   drop is start-order-biased (last to open, never least confident,
   because there is no confidence to rank by), and `export_coverage`
   cannot see it because the other six satisfy `slur`.
8. **`voicing`'s chord duration-vote disagreement** — resolved silently.
9. **`infer_time_signature`'s and `_dominant_detected_meter`'s
   `votes`/`voters`/`confidence`** — `grep 'get("votes")'` → 0.
10. **`key_signature_vote`'s `majority` share** — one `<=`, then discarded,
    never emitted.
11. **`pitch_resolver`'s fractional residual** — "this note sat exactly between
    two positions" is computed at `:180` and rounded away at `:182`.

### 7.2 Quantised — the float exists and is bucketed before its consumer

12. **`instruments.Match.coverage`** → high/medium/low → dropped at `low` →
    flat `SCORE_LABEL_MATCH = 6.0`. **Binarised twice on the way into a model
    that is already additive.** ⚠️ Measured reach: **1 label of 193 scan
    staves, 0 of 224 engraved** — it is the cleanest Class-B site and it moves
    essentially nothing today.
13. **Tesseract per-word confidence** — thresholded at 30 and destroyed.
14. **`_looks_cut`'s centre-column fill**, `_accidental_shape`'s bottom-heavy
    ratio, `header_ink`'s shift gain — all real ratios, all bucketed.

### 7.3 Kept and unconsumed

15. **`pitch_candidates`** — the only key that is written and then explicitly
    `pop`ped without ever being read (`clef_correction.py:312`). Its one
    reader is `tools/maestro_bridge/re-rank.ts`, out of band and off by
    default.
16. **`label_contradiction`** — 158 firings, 0.873 of them the export being
    wrong, 0 both-right. Live, unconditional, and deliberately without a
    consumer until someone decides what it should DO.
17. **`clef_proposal`** — recorded with `applied: False` and read by nobody.
18. **`weight_routing`** — the full classification evidence is recorded and only
    the categorical verdict is branched on.
19. **The bracket block** on the staff dict, emitted specifically because it had
    never reached the dict, with a comment saying "nothing reads it yet" — and
    export still decides piano grouping by `len(staves) == 2`.
20. **`Roster.coverage`** — computed, serialised, compared to nothing.
21. **`LayoutFit.agreement` / `.considered` / `.score_per_staff`** — ⚠️ and
    `agreement` is the repo's cautionary case: **1.000 for 70% of the WRONG
    answers.** It is discarded at `contextual.py:833` at no cost, and that is
    the right call.

### 7.4 Dead code — computed by nothing, so not even gathered

- **`hairpin_detection.py` (344 lines) is imported by nothing but its own
  tests.** Its docstring reports shipped results — *"59 of 99 hairpins against
  the detector's 1"* — for a module with no call site.
- ⚠️ **`bracket_reader.py` (390 lines) is imported by nothing but its own tests
  and one benchmark's probes** — the same shape as `hairpin_detection.py` and
  the LARGER of the two. Added 2026-09-07; the map missed it entirely. Its own
  docstring is honest about it (*"Nothing in the pipeline consumes this
  module"*), which makes it a smaller hazard than the hairpin reader's — but
  §7.4 is where an agent asks *"is this already written?"*, and a
  bracket-structure workstream reading the earlier version of this list would
  not have learned that 390 lines of measured classical CV exist. Record:
  `benchmarks/omr-bracket-reading-2026-09/`.
- ⚠️ **`condensed_parts.py` (127 lines) likewise** — `players_for_label` is
  called only by tests and by `benchmarks/omr-condensed-parts-2026-09/`. See
  the Stage 11 `_condensed_count` row for the consequence: the field it would
  fill is never written in production, so `OMR_CONDENSED_PARTS` is inert even
  when set.
- **`template_matcher.py`** survives in the live pipeline only as the home of
  the `SymbolDetection` dataclass; `detect_symbols` is called by tests and
  **two** annotate tools (`build_template.py:34`, `port_verdicts.py:39`). Two
  live env flags (`OMR_PHASE26_FIXES`, `OMR_PHASE28_FIX_TEXT_GATE`) gate dead
  code.
- **`voicing.group_chords_in_transcribe_result`** — hardcodes one voice per
  staff, ignoring `split_events_into_voices` 40 lines above; `grep` finds one
  occurrence, its own definition.
- **`slots.groups_are_comparable`** — zero callers, superseded by `map_groups`,
  and its docstring carries the measurement that motivated the replacement.
- **`transcribe._key_sig_richer`** — defined, documented, never called; the
  fuller-reading rule it implements was priced and refused.
- **`class_aliases.unaccounted()`** — documented as making a new class "a loud
  failure rather than a silent drop", and **never called at load time**; the
  test checks the committed JSON, not the loaded checkpoint.
- **`Decision.names_a_staff`**, **`Match.is_ambiguous`**,
  **`LocatedTimeSignature.as_dict`**, **`staff_header.extract_header_cell`** —
  zero **production** callers each. ⚠️ Corrected 2026-09-07 from "zero callers":
  all four have 2-4 test callers (`test_work_roster.py:136,226`;
  `test_instruments.py:641,643,647,736`;
  `test_time_signature_locator.py:191,194,197`; `test_staff_header.py:180,187`),
  so deleting one on this list's word would break the suite. The map has the
  vocabulary for this — `probe` — and this bullet did not use it.

⚠️ **This list is complete for `tools/omr/*.py` as of 2026-09-07, and the way it
was completed is worth reusing**:
`benchmarks/omr-decision-map-verify-2026-09/probe_orphan_modules.py`. Note the
probe's own caveat, which is this section's hazard in miniature — **a module
invoked as a subprocess, as a `python3 -m` entry point, or inside another venv
has no importer and is not an orphan**; four such false positives are named in
the probe's docstring.

---

## 8. Where the code and the prose disagree

**The tree outranks the ledger.** Every row below was found by reading the code
against a claim, and every one is a finding in its own right. They are grouped
by how much they could mislead someone building on them.

### 8.1 A named thing that does not exist

| # | claim | the tree |
|---|---|---|
| **D1** | CLAUDE.md: *"FIXED 2026-09-04 (**`_mxl_directions_only`**, called from both)"* and *"a source-level anti-drift test asserting BOTH MusicXML emitters call it"* | `grep -rn '_mxl_directions_only' tools/` → **one hit, a comment in `test_export.py:393` explaining the supersession.** The function is `_mxl_empty_measure` (`export.py:1512`), called from `:3155` and `:3573`. CLAUDE.md names it correctly 26 lines earlier and incorrectly here. |
| **D2** | `docs/scope-identity-upstream-2026-09-06.md` §2: *"`key_consistency_warning` and `meter_consistency_warning` have **zero consumers** outside their producer"* | **Those two keys have no PRODUCER.** They appear nowhere in `tools/`, `backend/` or `frontend/` `[V3]`. The five real keys are the ones CLAUDE.md lists. ⚠️ And `benchmarks/omr-additive-vs-gated-2026-09/probe/probe_gate_reach.py:32` harvests both names, so it reports 0 for them **silently** — the "85 warnings fire" figure is computed by a probe whose key list contains two nonexistent keys plus `clef_continuity_warning`, which was explicitly dropped. |
| **D3** | `export.py:1386-1389`: *"See `KNOWN_GAPS["wedge"]` for what that costs"* | `KNOWN_GAPS` has **no `wedge` key** — it was removed when gap #9 closed. That subscript would `KeyError`. A dangling cross-reference in a live docstring. |

### 8.2 A gate whose location is wrong in two documents at once

| # | claim | the tree |
|---|---|---|
| **D4** | CLAUDE.md and `scope-identity-upstream` §3 both say the clef **FILL** tier is blocked by `sources.get(slot) == "label"` | That conjunct is at **`clef_correction.py:616`, inside the OVERRIDE branch.** The FILL tier is `do_apply = apply and not detected` (`:610`) with **no source gate in the function at all**. The real fill blocker is caller-side, `contextual.py:1380`. The additive-vs-gated survey caught this and cited it at **`contextual.py:1202`** — which has since drifted to **1380** `[V7]`. |
| **D5** | `clef_correction.py:33-43` module docstring: *"Three conditions, all required: … 2. **The instrument label is high confidence.**"* | Condition 2 is **not implemented anywhere.** `correct_clefs_from_instruments` never reads a label confidence; the only filter is `slots.MIN_LABEL_CONFIDENCE` (high **or medium**) five layers upstream. |
| **D6** | Prose (several places) says `propose_clef` has **six exits** | It has **five `return` statements** (`:232`, `:245`, `:262`, `:266`, `:274`) — four refusals and one proposal — plus a non-exit `continue` at `:240`. |

### 8.3 Defaults documented backwards

Each of these is a live behaviour flag whose own file says the opposite of what
it does.

| # | flag | docstring says | code says |
|---|---|---|---|
| **D7** | `OMR_CHOIR_GROUPING` | `system_grouping.py:165` *"default OFF"*, and `assign_systems` docstring `:646` *"off"* | `:208-217` → **ON** (and `_choir_grouping_enabled`'s own docstring says "ON by default since 2026-09-05") |
| **D8** | `OMR_LEFT_EDGE_SPLIT` | `assign_systems` docstring `:639` *"off"* | `:159` default `"1"` → **ON** |
| **D9** | `OMR_BRACKET_COLUMNS` | `assign_systems` docstring `:657` *"default OFF"* | `:523` → **ON** |
| **D10** | `OMR_ABSENT_INSTRUMENT_VETO` | `absent_instrument.py:52` *"Off by default"*, echoed at `contextual.py:1153` | `:111` `DEFAULT_MODE = "on"`, with a 24-line justification headed "DEFAULT ON since 2026-09-06" |

### 8.4 A documented rule the code does not implement

| # | claim | the tree |
|---|---|---|
| **D11** | `voicing.split_events_into_voices` docstring `:291-293`: *"stem-up AND another stem-down **at a different x position** ⇒ two voices"* | `:305-314` **never compares x.** `x_position` is on every event and is used only for sorting. |
| **D12** | `transcribe._correct_notehead_class_by_fill` docstring `:449-451` describes **three** fill bands, including *"fill < 0.35: clearly empty → noteheadWhole"* | `:478-484` has **two branches**. The 0.35 boundary is unreachable: a fill of 0.10 with a stem becomes `noteheadHalf`. |
| **D13** | `export.py:1188-1189`: beam boxes merge *"within 3 notehead widths in y"* | `_collapse_beam_stacks:1076-1083` tests **x only**, and its own docstring 130 lines earlier says *"deliberately with NO y term"*. Two docstrings, one function, opposite claims. |
| **D14** | `staff_detector.py:206-212`: *"long horizontal black runs … so a row contains at least one long line"* | `find_peaks(profile, height=min_run)` gates on **total row ink**, with no contiguity requirement. A row of justified text clears it — which is exactly why `MAX_LINE_INK_RUNS_PER_SPACE` had to be added later. |
| **D15** | `system_grouping.py:34-46`: the crossing band runs *"from the top line of the upper staff to the bottom line of the lower"*, and *"extending the band through both staves discriminates"* | `:294-296` (and identically at `:363`, `:241`): `top = upper.bottom_y + 2`, `bot = lower.top_y - 2`. **The band is the gap only.** The discriminating property the docstring names is not implemented anywhere in the file. |
| **D16** | `measure_extractor.py:748-755`: *"the system's edges are a CONSENSUS across its staves, not the extreme"* | `:756-757`: `x_lo = median(...)` but **`x_hi = max(...)`** — the right edge is the extreme the comment argues against. |
| **D17** | `class_aliases.py:69-71`: *"`unaccounted()` fails on anything absent from both tables, so a new weights file is a **loud failure** rather than a silent drop"* | `yolo_detector._ensure_loaded` calls `canonicalize_names(raw)` and **never `unaccounted()`**. The test checks the committed JSON, not the loaded checkpoint. A checkpoint with a new class falls through to `category="unknown"` in silence. |
| **D18** | `transcribe.py:5044`: `--clef-reader-conf` *"Min confidence for a clef-specialist detection to **override** the main clef"* | `:1769` is gap-fill only, and the adjacent comment at `:1755` says so: *"GAP-FILL ONLY … never overwrites one that did."* |
| **D19** | `transcribe._pair_ties_in_cell` docstring `:2238-2240`: *"Pitch match: not checked (**and not available**)"* | `pitch_by_id` is complete at `:1905`; the call is at `:1948`, same scope. "Not available" describes an attribute, not the information. |
| **D28** | `export._paired_spans`, comment at `:2477-2478`: *"**Prefer the longest run the curve covers WITHIN one voice** over dropping it."* | The code takes the voice of the **first** covered head and discards the rest: `voice = voice_of.get(id(covered[0][2]), 0)` (`:2479`). No run length is computed. An arc covering one head of voice 1 and three of voice 2 keeps **one**, fails the `len(in_voice) < 2` test two lines down, and the slur is dropped — where the documented rule would have kept it. Found 2026-09-07 by independent enumeration, not by this map's own pass. |
| **D20** | `key_signature_locator.py:84-86`: *"`transcribe` only reads a key signature for a staff whose clef is actually known — **never** for one on the positional default"* | `transcribe.py:1407-1411` **does** read against `_default_clef_for_position`, at a halved, capped weight. The guard moved from the staff to the vote; CLAUDE.md has the corrected version, the module docstring does not. |

### 8.5 Prose about a module that is not wired in

| # | claim | the tree |
|---|---|---|
| **D21** | `hairpin_detection.py:39-41` reports a shipped result — *"59 of 99 hairpins against the detector's 1, and zero false positives on five of the six pages that carry none"* | **The module is imported by nothing but its own tests.** `grep -rn 'hairpin_detection\|import hairpin' --include='*.py' .` → six hits, all in `tools/omr/tests/test_hairpin_detection.py`. `docs/scope-cv-hairpin-detection-2026-09-04.md` correctly calls detection UNCLAIMED; the file's own docstring is the outlier. |
| **D22** | `offroster_name.py:68-72`: *"**Until that module lands** the caller abstains and this is a complete no-op"* | `work_roster.py` has landed (524 lines) and `contextual.py:1223` imports it. The prose describes a world two branches ago. |
| **D23** | CLAUDE.md / the probability-gates handoff: *"detection confidence reaches a decision at **four** places — three argmax and one threshold"* | All four verified present (drifted +7, +7, +7, +205), **and there is a fifth**: `rhythm.py:750-753` sorts beams by `-confidence` and greedily keeps the highest — a load-bearing argmax that decides beam depth, hence duration. It is arguably excusable (CV beams are pinned at 1.0 by fiat) but the count as written is false. |

### 8.6 Documented but undiscoverable

| # | finding |
|---|---|
| **D24** | ⚠️ **CLAUDE.md's env table is not the tree's env surface.** `[V4]`, re-derived 2026-09-07 after the checker itself was fixed: **41 `OMR_*` variables are read in the tree; 19 are mentioned nowhere in CLAUDE.md**, and several are DEFAULT-ON behaviour flags — `OMR_ABSENT_INSTRUMENT_VETO`, `OMR_LABEL_MERGE_QUALITY`, `OMR_MOVEMENT_REFERENCE` — plus `OMR_ROSTER_CLEF`, `OMR_INSTRUMENT_CLEF_DEFAULT`, `OMR_SLOT_GROUP_MAP`, `OMR_REFERENCE_MOST_LABELLED`, `OMR_TAIL_RULE`, `OMR_ROSTER_RANGE_VETO`, `OMR_ROSTER_SCORE_ORDER_VETO`, `OMR_CONTEST_DUMP`, `OMR_DIRECTION_READERS`, `OMR_EVAL_INDENT_MM`, `OMR_LINEUP_SWAP_SPLIT`, `OMR_PHASE26_FIXES`, `OMR_PHASE28_FIX_TEXT_GATE` and the `OMR_SURYA_*` trio. ⚠️⚠️ **THE PROBE THAT KEEPS THIS ROW CURRENT WAS ITSELF DEFEATED BY THE INDIRECTION THIS MAP WARNS ABOUT, and that is the more useful half of the entry.** Until 2026-09-07 `V4` matched only the literal `os.environ.get("OMR_…")` in `tools/omr/*.py`, so it missed four flags whose NAME lives in a module constant (`ENV_VAR = "OMR_ABSENT_INSTRUMENT_VETO"`, `ENV_CELL_LINE_TRACE`, …) — including a default-ON flag this very row names as important, **which survived only because a human wrote the list**. It now scans `tools/` and `backend/` recursively and catches all three read forms (inline, constant-held, injected-env), and reports which flags are reachable only via a constant. ⚠️ Note the two claims differ: this row is about the env **TABLE**, `V4` about CLAUDE.md **anywhere** — `OMR_SPAN_REFERENCE_FIT` is in the file's prose and not in the table, so it is undocumented by this row's standard and documented by `V4`'s. `V4` is the loose bound on purpose. |
| **D25** | `OMR_TAIL_RULE` is bound at **import time** (`dossier.py:521`) and read directly at both decision sites (`:550`, `:552`), so it has **no per-call escape**. ⚠️ Narrowed 2026-09-07: the original wording, "unlike every other flag", is false — `staff_labels_surya.py:77` and `:91` bind `OMR_SURYA_TIMEOUT_S` and `OMR_SURYA_KEEP_ALIVE` at import too. What is unique to `OMR_TAIL_RULE` is the missing escape: the Surya pair are consumed as `X if arg is None else arg` defaults (`:242`, `:248`, `:307`, `:314`) and a caller can override them. |
| **D26** | `_WEDGE_START_RULE` (`export.py:2587`) is presented with a measured comparison table as a selectable rule and is a module literal with no runtime override — no env read, no CLI flag, no reassignment in `tools/`, so the `"before"` branch at `:2669` is dead on every production and test path. ⚠️ Narrowed 2026-09-07: it is **not unreachable**. `benchmarks/omr-hairpins-2026-09/probe_stop_rule.py:101` monkeypatches the module global, and that probe is where the 1-of-8 vs 4-of-8 figures in the constant's own comment came from. It is a retained A/B arm reachable only by that probe. |
| **D27** | `_DYNAMIC_WORDS` and `_DYNAMIC_ELEMENTS` (`export.py:1303-1310`) are two literals with identical membership, and the comment at `:1302` describes a distinction between them that no longer exists. A live drift hazard: one gates acceptance, the other gates element choice. |

---

## 9. Actionable ordering — what to build, and in what order

Sean's stated purpose is a checkpoint for an agent about to build one thing.
This section is that checkpoint.

### 9.1 What is safe to build on today

| foundation | why it is safe |
|---|---|
| the **page dicts** after `_drop_furniture_measures` (`:4704`) | every ownership and meter decision is settled; this is the shape identity and export both read |
| **`instrument_source`** | the tier vocabulary is stable, load-bearing and enforced by four separate consumers |
| **`slots._pair_score` and `score_layouts.fit_layouts`** | already additive with signed terms and no vetoes — the right shape for new evidence, and both have room for terms that need no new data |
| the **A–E taxonomy** and the **constraint/opinion test** | settled vocabulary; §0.1 |
| **flag-off byte-identity** as an acceptance test | the project's standard discipline, already asserted for arcs, reclass, condensed parts and slot stitch |

### 9.2 What must land first

| you want to build | what must land first | why |
|---|---|---|
| anything scored on **identity accuracy** | ⚠️ **the phase-0 identity harness** | **Part names do not reach musicdiff at all.** The whole identity layer is invisible to OMR-NED, to the 20-row scan gate and to `orchestral_eval`. That is why spans making Brahms four times worse sat under a green benchmark. |
| a **calibrated probability** anywhere | ⚠️ **the corpus, not the estimator** | P(name) ECE 0.1277 / P(set) 0.1301, n=197, top bin promising 0.989 and delivering 0.692. The diagnosis was that the `derived` tier is EMPTY. Accumulate in evidence units with a threshold — as `slots.py` already does — and do not call the sum a probability. |
| a consumer for **any refused number** | **record the refusal first** | This is shortlist item 1 and it is byte-identical to the output. It is exactly why `measure_dynamics` and `absent_instrument` could be priced from disk while `_dedupe` needed a re-run and `propose_clef` needed a reimplementation. |
| **`OMR_ROSTER_LABELS`** | ⚠️ **wiring `OMR_WORK_ID`** | Its production reach is currently **NIL** — nothing sets `OMR_WORK_ID`. More measurement is not the prerequisite; wiring is. |
| a second work for **any n=1 flag** | a third document for `OMR_ROSTER_SCORE_ORDER_VETO` | Beethoven 5 has no plain `score_order` slot. The precedent these items respect: `OMR_MOVEMENT_REFERENCE` shipped default-ON on one work and a second work measured it four times worse. |

### 9.3 What can be built in parallel without colliding

| lane | files it touches | independent of |
|---|---|---|
| **record-the-refusals sweep** | `clef_locator` (pass a trace), `clef_correction` (record `fits`), `key_signature_vote` (the weight), `time_signature_locator` (the NCC scores), `_dedupe` (band distances) | everything — no consumer, output byte-identical |
| **`measure_dynamics` nearest-legal-word** | `export.py` only | every other lane; measured by `probe_dynamic_band.py`, no harness needed |
| **the identity harness** | `benchmarks/` only | all of it |
| **stage-1/2/3 constants** | `preprocessing`, `staff_detector`, `measure_extractor` | identity and export entirely |
| **the dead-code sweep** (§7.4) | `hairpin_detection`, `template_matcher`, `voicing`, `slots`, `transcribe` | ⚠️ **not** parallel with the CV-hairpin workstream — see 9.5 |
| **the code-vs-prose corrections** (§8) | docstrings and CLAUDE.md | everything |

⚠️ **`tools/omr/slots.py` is contended.** At the time of writing, five agents
are active on `page_normalise`, the lineup swap, one-line staves and score
language. Check before touching stage 10.

### 9.4 Dependencies that are currently UNSATISFIABLE

An agent needs to know the difference between "not done" and "cannot be done".

| dependency | why it cannot be satisfied | what would change it |
|---|---|---|
| **`clef_correction`'s OVERRIDE gate needing a `label` source on an unresolved non-treble staff** | measured over the 20-row scan corpus: **29 of 29** such staves have **no label printed at all** — not a lexicon refusal, not an OCR miss. The families labelled on continuation systems are winds and brass, which default to treble and are already right | an edition that labels its strings on every system, or a different admissible source |
| **the `_dedupe` written-range tier on a scan** | `_staff_written_ranges` returns `{}` with no dossier, and the scan gate runs **dossier-free by protocol** (dossiers are built from the MusicXML it scores against). All **4,256** duplicates resolve on ladder or distance | a roster-fed identity tier — which exists (`OMR_ROSTER_RANGE_VETO`) and is off at 52 swaps for +24 edits. ⚠️ **Under standing rule A00, that +24 does not condemn the mechanism**: it is an OMR-NED delta and **it was never attributed** — nobody has opened the op list to say whether the swaps were wrong or merely charged. `OMR_SLOT_STITCH` sits one section away as the precedent for a metric artefact mistaken for a regression. Read matched-note recall before believing it |
| **`OMR_ROSTER_LABELS` in production** | needs `OMR_WORK_ID`; nothing sets it | wiring the work-id lookup into the pipeline entry point |
| **a key signature on a soprano / mezzo / baritone / french / varbaritone / subbass clef** | `key_signature_geometry.slot_positions` has tables for treble, bass, alto, tenor **only** | six more slot tables |
| **`_is_grouped_system` (cue C) on a page where connectivity abstained** | `group_index` is only set on the connectivity path; the gap-heuristic fallback leaves it at the dataclass default 0 | setting `group_index` on the fallback path too |
| **`staff_labels_human`** from `transcribe` | `_contextual_call_kwargs` synthesises `Assist("vision" or "none")` — the human rung is unreachable from the pipeline | plumbing an assist mode through `transcribe()` |
| **the register→clef arrow** | ⚠️ **measured dead in both forms.** `range → instrument`: 5 of 9,219 pitches fall outside their family union. `range → clef` via `clef_register_warning`: reach 7/193, precision **0 of 11** | a variant restricted to one bracket group, or a staff against ITS OWN reading on other systems — a different check, needing its own reach measurement first |

### 9.5 The ranked shortlist, unchanged and re-endorsed

This map does not invent a rival ranking. The additive-vs-gated survey's
shortlist stands, and everything above is consistent with it:

1. **Record the refusals** — free, byte-identical, and the prerequisite for
   deciding 2-5, *including the decision not to convert*.
2. **`export.measure_dynamics` → nearest legal word, confidence-weighted** —
   45/45 and 8/8 refused runs at edit distance 1; on scans dynamics are
   *under*-emitted (376 against a truth of 491), so this pushes the right way.
3. **`clef_correction`: the override tier with the allowlist replaced by an
   additive margin term** — highest per-error cost in the pipeline; ⚠️ coupled
   to the held `OMR_INSTRUMENT_CLEF_DEFAULT` decision, do not move unilaterally.
4. **`_dedupe` rank-0 thresholded confidence** at |Δconf| > 0.30 — 143 pairs, a
   bet the size of the range veto's 52. ⚠️ Price on **note recall**, not
   OMR-NED; `wrong note` is 29.6% of that pool.
5. **`contextual.py:1380`'s provenance exclusion, FILL tier only** — 3 staves on
   one row, and honest about it.
6. **The identity harness**, which everything upstream is blocked on.

⚠️ **And one addition this map makes: the CV hairpin reader is written,
measured, documented — and not wired in.** That is neither a gate nor a
gathered-and-unused signal; it is a whole reader whose docstring reports
shipped results for code with no call site. Before anyone builds hairpin
detection, read `hairpin_detection.py` and `git log --all -S` for its call
site. **`git log --all --oneline -S "<the thing>" -- tools/omr/` before
building anything** — this project has already built a duplicate of a landed
export fix once.

---

## 10. Verification — how to re-derive this document

Prose rots; the mechanical half of this document does not have to.

```bash
python3 benchmarks/omr-decision-map-2026-09/verify.py           # all checks
python3 benchmarks/omr-decision-map-2026-09/verify.py --only V2 # one
python3 benchmarks/omr-decision-map-2026-09/verify.py --json    # machine
python3 benchmarks/omr-decision-map-2026-09/verify.py --check   # is the graph stale?
python3 benchmarks/omr-decision-map-2026-09/verify.py --write-doc
```

| check | what it proves | current answer |
|---|---|---|
| **V1** | `export.py` never reads a detection confidence | 1 hit, 0 of them code — **holds** |
| **V2** | how many of the five consistency checks reach a consumer | **4 of 6 tracked keys have zero consumers.** `rhythm_sum_warning`'s only consumer is `backend/modules/local_omr.py:360` (a boolean presence count; the grep also hits that file's docstring, hence 2). `clef_proposal` has none |
| **V3** | two warning keys named in prose do not exist | **holds** — 0 hits each |
| **V4** | the `OMR_*` surface the tree READS vs what CLAUDE.md mentions | **41 in tree, 19 unmentioned.** ⚠️ **Rewritten 2026-09-07: it undercounted the surface it exists to police.** It matched only the literal `os.environ.get("OMR_…")`, so a flag whose NAME lives in a module constant — `ENV_VAR = "OMR_ABSENT_INSTRUMENT_VETO"`, a **default-ON** flag D24 names as important — dropped out silently on a re-run while the hand-written list still carried it. It now catches all three read forms and reports which flags are reachable only via a constant |
| **V5** | the three circularity refusals still stand | **holds** — `clef_correction.py:396`, `dossier.py:434`, `score_layouts.py:682` |
| **V6** | consumer counts for the tracked result-JSON keys | 10 of 11 never leave `tools/omr/` |
| **V7** | line numbers quoted in prose against the tree | **3 of 6 have drifted** |
| **V8** | every §5 decision table carries the `CONSUMED BY` column | **15 of 15 — holds.** ⚠️ Added 2026-09-07 because six of twelve tables had lost it and nothing noticed: prose cannot check its own shape. It accepts either wording, since a terminal stage's consumer question is "who can SEE this element" |

⚠️ **The exit code is always 0.** This reports; it does not gate. A CI gate on
these numbers would freeze the very facts the map exists to keep current — and
`V4` and `V7` are *supposed* to change as the tree moves.

### 10.1 What is UNMEASURED here, and said so

- **How often the two independent clef readings disagree** (§3.2b). Both are
  computed on every run; nobody has counted.
- **Whether `clef_correction` would get the 29 label-less staves right** if it
  were handed them. Separate question from whether it can reach them.
- **Whether the 60 already-resolved non-treble labels reach `clef_correction`.**
- **Whether page-level parallelism would help.** Direction text is ~75% of wall
  clock on a whole-work run; nothing here is parallelised.
- **Every constant marked "bare" in §5.** They are undocumented, not measured
  and refused — a different thing, and the difference matters.

### 10.2 The consumer census

`verify.py --json` covers the tracked keys. The exhaustive per-key census
(every result-JSON key × every zone) is reproducible with a standalone script;
its method is: enumerate keys from `transcribe.py`'s dict literals plus 28
committed transcriptions, then for each key count WRITE sites
(`"k":` or `["k"] =`) and READ sites (`.get("k")`, `"k" in`, `["k"]` not
followed by `=`, `.pop("k")`) per zone, classifying `tools/omr/**` (excluding
tests), `backend/**`, `frontend/src/**` as production and everything else as
test-or-benchmark.

⚠️ **One regex trap, found the hard way:** a naive read pattern `\["k"\][^=]`
false-positives on `st["k"] = {` because `[^=]` swallows the space before `=`.
Use `(?!\s*=[^=])`. Without it, `measure_count_warning` reports phantom
consumers.

---

## 11. What this map does NOT cover

The intent was to cut uniformly in depth rather than by dropping stages.
⚠️⚠️ **THE INTENT WAS NOT MET IN THE FIRST EDITION**, and an enumeration made
from the code alone, without reading this document, found **185 decision points
in five scopes where §5 had rows for two.** §11.0 is what closed and §11.0b is
what did not — **stated as counts, because silence reads as coverage.**

### 11.0 Closed 2026-09-07 — three stages §2 named and §5 did not catalogue

| area | independent count | §5 rows now | where |
|---|--:|--:|---|
| `direction_text.py` | 72 | **14** | Stage 9′ |
| slur / arc pairing + numbering | 46 | **13** | Stage 11, second table |
| tie pairing (`_pair_ties_in_staff` / `_in_cell`) | 25 | **12** | Stage 4b |

Plus five modules that were **named nowhere in the first edition** and now have
rows: **`staff_labels_surya`** and `_surya_worker._assign`'s block-height gate
(the free DEFAULT rung — §5 previously catalogued the *unreachable* human rung
and skipped this one), **`staff_labels_vision`**, **`key_signature_template`**
(the reader behind D20, credited with 11 of 12 staves where the locator reads
2), **`movement_reference`** (default ON, and the flag that made a second work
four times worse), and **`bracket_reader`** as an orphan.

Three of the recovered decisions are this document's own thesis pattern, and
each is now a row: `read_directions:801`'s `accepted[0]` (the winning OCR rung
chosen by **list position**); the `Reader` type at `:614`, which **cannot carry
a confidence at all**; and `export._number_spans:2517-2520`, where **a 7th
simultaneous slur is dropped with no counter, no warning and no field.**

⚠️ **The rows kept are the ones that CHOOSE something a reader could change**;
the residue is arithmetic and bookkeeping. That is a judgement, not a
measurement, and it is stated so it can be disagreed with.

### 11.0b ⚠️ Still a declared gap — counted, not catalogued

| area | independent count | §5 rows | why it is left |
|---|--:|--:|---|
| `pitch_resolver.py` | 25 | 5 | depth cut; the 5 are the ones that decide a pitch or a candidate list, the rest is arithmetic |
| `condensed_parts.py` | 17 | 1 | ⚠️ **nothing in production calls `players_for_label`** and no production module writes the `condensed_parts` field, so `_condensed_count` always sees `{1}` — the whole module is unreachable and `OMR_CONDENSED_PARTS` is **inert whatever it is set to**. Cataloguing 17 decisions inside a module with no caller would be misleading, so it gets one row saying that |
| `page_normalise.py` | not counted | 0 | ⚠️ **out of scope by §11.1 (benchmark internals) — and it is one of the live workstreams.** Its consumers are `benchmarks/omr-scan-e2e-2026-09/scan_eval.py`, `tools/omr/tests/test_scan_eval_structural.py` and two probes in `benchmarks/omr-staves-map-completion-2026-09/`. **An agent working there cannot use this map at all**, and that is a scope statement, not a defect — but it should be known rather than discovered |
| `tools/omr/annotate/**`, `tools/omr/training/**` | not counted | 0 | §11.1; ⚠️ but see the Stage 3 warning — five `annotate/` consumers of `MeasureCell` are named there because the padding contract reaches them |

Record: `benchmarks/omr-decision-map-verify-2026-09/FINDINGS.md` §4.

### 11.1 What was cut deliberately, so those holes are in known places:

- **Per-constant provenance.** §5 says whether a constant sits on a measured
  gap, a plateau, or nothing. It does not reproduce the measurement. Follow the
  file.
- **The backend, frontend, payments, Gradus and comparison flows.** §6.2 covers
  the OMR boundary; the web app above it is CLAUDE.md's territory.
- **The training and labeling pipeline** (`tools/omr/annotate`,
  `tools/omr/training`). It has its own decisions — the admission tiers, the
  snap grid, the catalog membership record — and its own documents.
- **The Maestro theory layer.** Off by default, host-side only, and it consumes
  the result JSON rather than making pipeline decisions.
- **Benchmark internals.** §5's stage-11 rows say what each measurement module
  can and cannot see; the harnesses' own decisions are out of scope.
- **The score library and its `source_kind` tiers**, beyond §0.2's warning that
  the two provenance vocabularies are easy to confuse.

⚠️ **And one deliberate non-goal.** This document does not recommend a
conversion at any site the additive-vs-gated survey measured and refused. Where
it disagrees with that survey it says so explicitly; where it is silent, that
survey stands.

---

## 12. The picture

**Generated, not drawn** — the stage nodes and edges are declared in
`verify.py`, and the red terminal nodes are red because `V2`/`V6` measured them
unconsumed, not because anyone coloured them. Regenerate with
`--write-doc`, check with `--check`.

Read it beside `docs/progress-dashboard.html`'s flow graph, which answers the
different question of how well each stage works.

| shape | means |
|---|---|
| **dark rectangle** | a pipeline stage, with its technology |
| **solid arrow** | information that actually flows, labelled with what |
| **dashed ⛔ arrow** | an edge the codebase **refuses**, with the file:line of the refusal |
| 🔴 **red rounded node** | a signal computed and reaching **nobody** — measured by `V2`/`V6`, not asserted |
| ⬜ **grey parallelogram** | a whole module that is written and wired to nothing |
| 🟠 **amber hexagon** | a dependency **nobody can satisfy today** — different from one not yet done (§9.4) |

<!-- BEGIN GENERATED: decision-map-graph -->

```mermaid
flowchart TD
  %% GENERATED by benchmarks/omr-decision-map-2026-09/verify.py --mermaid -- do not hand-edit
  s1["<b>1 · Render + staff detection</b><br/><i>classical CV</i>"]
  s2["<b>2 · System grouping</b><br/><i>classical CV</i>"]
  s3["<b>3 · Measure + barlines</b><br/><i>classical CV</i>"]
  s8a["<b>8a · Header clef</b><br/><i>geometry + CV</i>"]
  s8b["<b>8b · Header key signature</b><br/><i>template + fit</i>"]
  s4["<b>4 · Symbol detection</b><br/><i>YOLOv8l 208cls</i>"]
  s5["<b>5 · Stems + beams</b><br/><i>classical CV</i>"]
  s6["<b>6 · Pitch resolution</b><br/><i>geometry</i>"]
  s7["<b>7 · Rhythm / durations</b><br/><i>derived</i>"]
  sown["<b>4d · Glyph OWNERSHIP</b><br/><i>ladder/range/dist</i>"]
  s8c["<b>8c · Time signature</b><br/><i>template + vote</i>"]
  s9["<b>9 · Margin labels</b><br/><i>text/Surya/Vision</i>"]
  s9d["<b>9′ · Direction text</b><br/><i>ink minus dets + OCR</i>"]
  s10["<b>10 · Slot align + identity</b><br/><i>monotone DP</i>"]
  s11["<b>11 · Export</b><br/><i>serialisation</i>"]
  s1 -->|"line_ys, gaps"| s2
  s2 -->|"systems"| s3
  s3 -->|"measure cells"| s4
  s3 -->|"header window"| s8a
  s8a -->|"the SLOT TABLE"| s8b
  s4 -->|"detections"| s5
  s4 -->|"detections"| sown
  s4 -->|"every detection, SUBTRACTED"| s9d
  s9d -->|"2 of its 8 keys"| s11
  s5 -->|"beam levels"| s7
  s4 -->|"notehead y"| s6
  s8a -->|"clef"| s6
  s8b -->|"fifths"| s6
  s6 -->|"pitch"| s7
  s7 -->|"durations"| s8c
  s8c -->|"meter — bounded ±1"| s7
  sown -->|"one glyph, one staff"| s6
  s9 -->|"instrument names"| s10
  s6 -->|"register fit"| s10
  s8a -->|"clefs → fit_layouts · +51 records"| s10
  s10 -->|"part names, slots"| s11
  s7 -->|"events"| s11
  s6 -->|"pitches"| s11
  s10 -.->|"⛔ DEDUCED identity → clef · clef_correction.py:396"| s8a
  s8a -.->|"⛔ clef → the part↔staff PIN · dossier.py:434, score_layouts.py:682"| s10
  d_conf(["detection confidence<br/><i>export.py reads it 0 times [V1]</i>"])
  s4 --> d_conf
  d_pc(["pitch_candidates<br/><i>written, then pop()ed unread</i>"])
  s6 --> d_pc
  d_rhy(["rhythm_sum_warning<br/><i>1 consumer: a UI percentage</i>"])
  s7 --> d_rhy
  d_mc(["measure_count_warning<br/><i>NOBODY [V2]</i>"])
  s3 --> d_mc
  d_key(["key_signature_warning<br/><i>NOBODY [V2]</i>"])
  s8b --> d_key
  d_reg(["clef_register_warning<br/><i>NOBODY — and reach 7/193, precision 0/11</i>"])
  s6 --> d_reg
  d_ts(["time_signature_disagreement<br/><i>NOBODY [V2]</i>"])
  s8c --> d_ts
  d_sym(["clef symmetry + the whole trace<br/><i>no call site passes trace=</i>"])
  s8a --> d_sym
  d_prop(["clef_proposal (applied:False)<br/><i>NOBODY [V2]</i>"])
  s10 --> d_prop
  d_lc(["label_contradiction<br/><i>158 firings, 0.873 right — undecided</i>"])
  s10 --> d_lc
  d_7th(["the 7th simultaneous slur/hairpin<br/><i>dropped: no counter, no field</i>"])
  s11 --> d_7th
  d_conf2(["OCR rung disagreement<br/><i>computed; reaches the report, never the artefact</i>"])
  s9d --> d_conf2
  d_tie(["tie-pair count<br/><i>computed at :2112, discarded at the call site</i>"])
  s4 --> d_tie
  d_place(["direction placement / category / terms / reader<br/><i>6 of 8 keys unread; placement hardcoded — and Style is outside AllObjects, so it costs 0 and no harness can see it</i>"])
  s9d --> d_place
  d_align(["the slot alignment DP score<br/><i>never returned — no margin exists</i>"])
  s10 --> d_align
  o_hair[/"hairpin_detection.py<br/><i>imported only by its own tests</i>"/]
  o_brack[/"bracket_reader.py (390 lines)<br/><i>tests + one benchmark's probes only</i>"/]
  o_cond[/"condensed_parts.py<br/><i>no producer — so OMR_CONDENSED_PARTS is inert</i>"/]
  o_tmpl[/"template_matcher.py<br/><i>dead detector; 2 live env flags on it</i>"/]
  u_clef{{"clef OVERRIDE needs source is 'label'<br/><i>29 of 29 unresolved non-treble scan staves print NO label</i>"}}
  u_range{{"_dedupe range tier needs a dossier<br/><i>scan gate is dossier-free BY PROTOCOL — 0 of 4,256 firings</i>"}}
  s10 -.-> u_clef
  sown -.-> u_range
  classDef dead fill:#7f1d1d,stroke:#ef4444,color:#fee2e2,stroke-width:2px;
  classDef orphan fill:#3f3f46,stroke:#a1a1aa,color:#e4e4e7,stroke-dasharray:4 3;
  classDef unsat fill:#78350f,stroke:#f59e0b,color:#fef3c7;
  classDef stage fill:#1e293b,stroke:#64748b,color:#e2e8f0;
  class d_conf,d_pc,d_rhy,d_mc,d_key,d_reg,d_ts,d_sym,d_prop,d_lc,d_7th,d_conf2,d_tie,d_place,d_align dead;
  class o_hair,o_brack,o_cond,o_tmpl orphan;
  class u_clef,u_range unsat;
  class s1,s2,s3,s8a,s8b,s4,s5,s6,s7,sown,s8c,s9,s9d,s10,s11 stage;
  %% measured: 4 of 6 checks have no consumer; 10 of 11 tracked result keys never leave tools/omr/
```

<!-- END GENERATED: decision-map-graph -->

⚠️ **The graph is one layer, deliberately.** It shows the spine, the refused
edges and the dead ends. It does not show the ~120 individual decision points —
that is §5, and a 120-node graph would be less legible than the table. If a
second view is ever wanted, the natural split is one graph per stage rather
than one bigger graph.
