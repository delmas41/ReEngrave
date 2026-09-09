# ReEngrave — Version Memory

A running log of changes made to this project, newest first. Updated after
every commit alongside CLAUDE.md and PROJECT_BRIEF.md.

⚠️ **ORDER IS CAUSAL, AND THE DATED HEADINGS DISAGREE WITH THE COMMIT DATES
ACROSS SESSIONS — this is not a sorting error.** Parallel sessions dated their
own blocks by their own reckoning, and one dated its work a day ahead of the
commits that carry it. The 09-09 GATHER-coverage entry stands ABOVE the two
09-10 entries because it *builds on* them: it generalises the chord gap the
`Q.EVENT` block found. Headings are left exactly as each session wrote them —
rewriting another session's dated claim to tidy a sort would be the ledger
overwriting the tree.

---

## 2026-09-09 — four parallel sessions merged, and the merge is where two findings changed

Four sessions that had been running concurrently were landed onto one branch.
Three of the four merges needed a real decision rather than a text resolution,
and **two claims were only falsifiable once the trees were together** — the
literal case for this repo's standing rule that a change is measured on the
MERGED tree.

**What landed** (in merge order):

1. `reengraved-meter-carry-0c9da4` — the staged pipeline gets an **EXPORTER**
   (`staged/export.py` — the handoff's *"⚠️ there is NO EXPORTER"* is closed),
   a **derived inventory** (`staged/inventory.py`), a **health report**
   (`staged/health.py`), the GATHER pass for five families read by nothing, the
   meter carry, and `Q.EVENT` (chord grouping happening after the stage that
   needed it).
   ⚠️ **This session pushed one more commit WHILE the merge was in progress**
   (`d0da5f00`), and it SUPERSEDES the meter-carry conclusion the first four
   commits landed. The carry is no longer a gate that had to ship OFF for want
   of a movement-boundary detector: it arrives as a CANDIDATE and the bars it
   claims to govern confirm or refuse it, so **the boundary problem dissolved
   with no detector anywhere** — all three systems of Beethoven 5 p.17 (the
   *Andante*, a new movement in 3/8) refuse the carried 2/4. It is merged, and
   the flag is still `0` **on n — one document, two pages — not on the
   hazard.** Checked before believing it was finished: that worktree is clean
   and the commit is on `origin`.
   ⚠️ It **subsumes `reengraved-staged-pipeline-068163` entirely** — that
   branch's tip is an ancestor — so that branch was NOT merged separately.
2. `brave-diffie-f56a0c` — the staves-map WRITER carries the arity fields, and
   the arity question is asked BEFORE the write.
3. `gracious-kare-2cddc3` — dynamics enter the staged pipeline; `OMR_CV_HAIRPINS`
   re-priced (its stale-pricing prediction REFUTED, the answer changed anyway).
4. `gather-stage-coverage-qp6j01` — `staged/gather_coverage.py`, the derived
   answer to "what does the reader actually write down".

**⚠️ THE THREE SEMANTIC CONFLICTS, and why concatenating would have shipped
bugs:**

- **Two sessions gathered the SAME two quantities from the SAME reader.**
  `gather_glyph_families` (session 1) and `gather_dynamic_letters` /
  `gather_wedge_boxes` (session 3) both observed `Q.DYNAMIC_LETTER` and
  `Q.WEDGE_BOX` as `READERS.DETECTOR`. Keeping both would put **two rows from
  one reader on one glyph** — the "two rows from one reader are ONE signal"
  fault, arrived at by accident, and named in session 3's own comment.
  Resolved by OWNERSHIP: the dynamics rungs own both (they carry the band
  offset a per-cell frame cannot express, and the CV rung); `glyph_families`
  keeps rests, arcs and articulations.
- **`subjects_from` vs the wider `reasons` tuple** in `adjudicate_dynamic`.
  Both kept, and the composition was **checked rather than assumed**:
  `subjects_for` reads `log.all_rows()` and an abstention IS a row, so session
  3's deliberate row-for-every-cell still yields a subject for a bar with no
  letter of its own. The comment claiming otherwise was corrected, not shipped.
- **Four tests then failed, every one at a seam, every one asserting a truth
  the merge changed.** They were updated to the merged truth and re-run RED.

**⚠️⚠️ FINDING 1 — `Q.DYNAMIC` GRADUATED, so it must LEAVE the stub roster.**
`test_the_five_previously_unnamed_stubs_are_named_now` failed because
`adjudicate_dynamic` is implemented. A roster that keeps a graduated entry
describes history rather than the pipeline — the same fault
`export_coverage`'s `test_the_inventory_has_no_stale_entries` exists to
prevent — so the entry was removed AND its graduation pinned by a new test.

**⚠️⚠️ FINDING 2 — "ALL SIX STUBS ARE STARVED AT GATHER" IS NO LONGER TRUE OF
THE MERGED TREE, AND THE FINDING IS CORROBORATED RATHER THAN OVERTURNED.**
Session 4 measured, on its own branch, that all six declared stubs wanted a
measurement no gatherer emitted — *"a stub is two repairs, not one"* — and
named four of them **NAMING gaps, cheap, the ink is already in the log**.
Sessions 1 and 3 then landed **exactly those four gatherers**, without having
read that finding. Measured on the merged tree:

| stub | starved on its own branch | starved MERGED | closed by |
|---|---|---|---|
| `arc_kind`, `arc_owner` | `ARC_BOX` | **fed** | `gather_glyph_families` |
| `articulation_owner` | `ARTICULATION_MARK` | **fed** | `gather_glyph_families` |
| `dynamic` | `DYNAMIC_LETTER` | **fed, and NOT A STUB** | `gather_dynamic_letters` + `adjudicate_dynamic` |
| `wedge_anchor` | `WEDGE_BOX` | **fed** | `gather_wedge_boxes` |
| `direction` | `DIRECTION_WORD` | **still starved** | — |

- `dynamic` is the only one of the six that got BOTH repairs, and the only one
  that now decides anything — the finding holding exactly as stated.
- The four that got only the gatherer are still stubs abstaining honestly,
  which is what a half-repair was predicted to produce.
- **The work plan changes**: four of the five remaining stubs are now ONE
  repair each (write the adjudicator, the evidence is waiting); `direction`
  alone is still two, and it is the one already named as the sole READING gap.
- ⚠️ **Found by a TEST, not by re-reading prose** — it failed with `5 != 6`
  exactly as its own docstring promised, and now pins both halves.

**Documentation kept coherent**: the superseded claim was stated in **four
places** (CLAUDE.md ×2, this file ×2, `FINDINGS.md`) — the exact
restated-figure-goes-stale hazard CLAUDE.md warns about. CLAUDE.md and
FINDINGS.md were corrected in place; the two dated entries in this file were
**left standing with a pointer**, because a dated measurement is a frozen fact
and is never rewritten.

⚠️ The committed `out/gather-coverage.json` is likewise left as session 4
measured it, and is now a BRANCH measurement rather than the tree's state; run
`python3 -m tools.omr.staged.gather_coverage` for the current answer.

---

## 2026-09-09 — GATHER-stage coverage: the chord gap generalises (derived, no arm run)

- **Sean found that chords — notes aligning in a bar — are not tracked.** The
  finding generalises, and the answer is a derived tool rather than a written
  list: `python3 -m tools.omr.staged.gather_coverage`. New:
  `tools/omr/staged/gather_coverage.py`,
  `tools/omr/tests/test_staged_gather_coverage.py` (8 tests),
  [benchmarks/omr-gather-coverage-2026-09/FINDINGS.md](benchmarks/omr-gather-coverage-2026-09/FINDINGS.md)
  and its committed output.
- **Measured: `record.Q` declares 63 quantities and a gatherer OBSERVES 31.**
  Two more are declared and only ever abstained on (`DIRECTION_WORD` —
  `gather_direction_text` is itself a stub — and `SYSTEMIC_COLUMN`).
- **⚠️ THE TWO FAULTS ARE DIFFERENT AND THE TOOL KEEPS THEM APART.** *Not
  gathered*: no row carries it at all (`fermata` — detected, exported, 36-for-36
  on Beethoven 5, and no `Q`). *Wrong place*: the ink IS in the log as an
  anonymous `Q.GLYPH_BOX` and no consumer can ask for it, because `Evidence`
  refuses a quantity the decision did not declare.
- **⚠️ THE STRUCTURAL FINDING: all six declared stubs are ALSO starved at the
  gather stage.** The handoff reads them as six adjudicators left to write;
  every one wants a measurement no gatherer emits, so a stub is **two** repairs,
  not one. Four of the five missing quantities are NAMING gaps (the ink is
  already there: 2 arc classes, 10 artic, 12 dynamic, 2 hairpin); only
  `DIRECTION_WORD` is a reading gap. **The 15 non-stub decisions are all fed.**
  ⚠️ *(merge note, 2026-09-09 — the claim above is TRUE OF THIS SESSION'S
  BRANCH and superseded in the merged tree: four of the four naming gaps were
  filed by sibling sessions and `dynamic` stopped being a stub. The finding is
  corroborated, not overturned. See the merge entry at the head of this file
  and FINDINGS.md §2b-addendum. The dated claim is left standing because it is
  what was measured.)*
- **11 legacy event keys have no name in the record** — `events`, `kind`,
  `x_position` (onset), `voices`/`voice_index`, `stem_direction`,
  `tied_to_next`/`tied_from_prev`, `fermata`, `ornaments`. Chord grouping in
  `voicing.group_chords_in_measure` is a full adjudication — a 0.6-notehead-width
  tolerance, a divisi veto on stem direction, a mode-vote over durations — with
  no subject, no input and no verdict in the record.
- **16 of 35 detector families have no quantity naming them**, led by **`rest`
  (11 classes)** and **`accidental` (8)**. A rest is half of every duration
  decision.
- **⚠️ The tool nearly manufactured its own finding.** `Q.STEM` is observed
  through a loop variable, so the first version reported it ungathered and
  accused `adjudicate_duration` of starving. The AST walker now resolves
  loop-bound quantities; the guard was run RED to prove it load-bearing. A
  second self-inflicted miss: reading the class space from `_CATEGORY_MAP`'s
  KEYS (an allow-list resolved by substring fallback) reported hairpins as
  having no detector class — the same allow-list fault `export_coverage.compare`
  was just repaired for.
- **Anti-drift, because a list of this shape rots**: `unaccounted()` fails on a
  legacy event key in neither table, `class_space_coverage()["unmapped"]` on an
  unmapped detector family, and `test_no_vocabulary_entries_still_have_no_vocabulary`
  fails the day a gap is FILLED — a closed entry must leave the table.
- **⚠️ No arm was run and no page was read.** Every figure is a property of the
  tree, so it says nothing about how often a missing quantity would fire.
  Measure REACH before accuracy.

- **Companion exploration, reasoned from the PAGE rather than the code**:
  [docs/exploration-what-is-on-the-page-2026-09-09.md](docs/exploration-what-is-on-the-page-2026-09-09.md)
  — present / left out / implied. ⚠️ Exploratory and mostly UNPRICED, and it
  says so; it ranks candidates and prices nothing.
- **⚠️ THE HEADLINE IDEA: vertical alignment ACROSS staves is simultaneity, and
  nothing reads it.** The chord finding one scope up. Verified — the only
  cross-staff reasoning in the tree is `_dedupe_cross_staff_detections`, an
  OWNERSHIP question. It is the only large source of **redundant** evidence on
  a page (a 21-staff system is 21 independent readings of one stretch of time),
  which is what lets a record say WHICH decision went wrong. The coarse form is
  saturated (`measure_count_warning`: 0 firings over 29 transcriptions) while
  `rhythm_sum_warning` fires 78 on one document and is inert — so the
  constraint is unexploited exactly where the errors are.
- **⚠️ `export._mxl_empty_measure` cannot tell SILENT from UNREAD.** A bar with
  no detected events exports as a whole-measure rest either way — the
  ABSENT/DECLINED collapse `record.py` exists to prevent, in the musical
  content rather than the metadata. Ink coverage (already computed by
  `direction_text._blank_detections`) separates them.
- **An accidental is SCOPE, not a glyph** — it holds to the barline;
  `transcribe.py:2210` implements it and staged has nowhere to keep the state.
  Same shape as `ottavaBracket`, where a miss costs every note in the span an
  octave.
- **⚠️ Corrected in place: the exploration's own first draft named `breath` and
  `glissando` as detector families from musical memory.** Neither is in the
  class space; `volta` is not either, and the `repeat` family is `repeatDot`
  ONLY — the dots, not the sign, which is why the repeat-export TODO has stayed
  open. Checked against the committed class list rather than recalled.

**Files touched:** `tools/omr/staged/gather_coverage.py` (new),
`tools/omr/tests/test_staged_gather_coverage.py` (new),
`benchmarks/omr-gather-coverage-2026-09/` (new), CLAUDE.md, PROJECT_BRIEF.md,
version_memory.md. Second commit adds
`docs/exploration-what-is-on-the-page-2026-09-09.md` and links it from CLAUDE.md.

---

## 2026-09-10 (later still) — the meter carry is WEIGHED, not gated

Sean: *"I want to make sure we don't get stuck in binary on or off ... If the
measure is what we think it is - does the math of the notes make sense. If not
then the meter should decrease in probability."*

- **The carry is now a CANDIDATE the bars judge.** `carried_from_read_meter`
  **+1.0**, each bar that FITS **+1.0**, each that does not **−1.0**, against
  `METER_CARRY_FLOOR` 2.0 and `METER_CARRY_MIN_BARS` 2.
- ⚠️ **THE MOVEMENT-BOUNDARY PROBLEM DISSOLVED — no detector needed.** Measured
  on Beethoven 5 / Litolff `984073`: page 2's two systems (continuation, truth
  2/4) carry at **+7.0** and **+8.0**; **all three systems of page 17 — the
  *Andante*, a NEW MOVEMENT in 3/8 — REFUSE the carried 2/4** (−3.0, −1.0, and
  one on too-few-bars). The new movement's bars simply contradict the old
  movement's meter.
- File effect, pages 0-2: whole rests at 4.0 ql inside a 2.0 ql bar
  **194 → 70**, `written.notes` 648 → 665 against `duration_narrowed`
  163 → 146, `empty_bars_padded_without_meter: 47` gone,
  `reconcile_duration` **13 → 47**. Control: `no_pitch` 54 → 54.
- ⚠️ **The ordering is STRUCTURAL, not tuned**: two net contradicting bars
  outweigh ANY carry, no carry outweighs the bars — asserted on the constants
  so a sweep breaking it fails even when every behavioural test passes. The
  weights themselves are symmetric and **declared unmeasured** (both
  asymmetries are arguable; n=2 separates under every ratio).
- ⚠️ **Not a probability**, and the ban is narrower than it reads:
  `adjudicate` forbids them because calibrated IDENTITY probabilities measured
  ECE 0.1277, failing worst at the top of the range — but that was diagnosed
  as the CORPUS, and a bar sum is `Checkable.CHECKABLE`, provable with no truth
  file. **So this family could be genuinely calibrated from the score library
  alone.** Nothing does that yet; it is the open route.
- ⚠️ **A LEAK FOUND AND CLOSED.** At first one *Andante* system carried at
  support exactly +2.0 — a single bar summing to 2.0, landing on the floor.
  Fixed with a SEPARATE `METER_CARRY_MIN_BARS` rather than a higher floor,
  because `A-CLEF-6` records that one constant carrying two jobs makes a sweep
  move both behaviours at once.
- ⚠️ **A LONE WHOLE REST IS NEVER READ** — it stands for the bar whatever the
  meter and its 4.0 is our own default (left in, 13 of 17 agreeing bars vote
  4.0 on the Andante); it is also what `size_measure_rest` supersedes, so
  touching it makes the record report a real fixpoint.
- **`rule(single_pass=True)` / `Verdict.single_pass_revision`** — the
  pipeline's ONE sanctioned loop, declared PER RULE. Corroboration makes the
  meter depend on the durations `reconcile_duration` rewrites, and
  `UphillConsequence` refused it. Unrolled it is a straight line — "vote once,
  repair once" — and the BOUND is what makes it safe. Sean's call; the guard
  escalated exactly as its own message instructs, and its text now names the
  exemption. A-DUR-3.
- ⚠️⚠️ **AN OPERATIONAL TRAP THAT INVALIDATED A MUTATION RUN.** macOS system
  Python caches bytecode OUTSIDE the tree, in
  `~/Library/Caches/com.apple.python/<abs path>/`; `find . -name __pycache__`
  never sees it. A reverted mutation stayed live — `grep` showed `-1.0` while
  `import` returned `-0.0` on a file whose md5 matched `inspect.getsource`.
  **Clear that path between mutation arms.** Same family as the cached
  `scan_eval` A/B.
- Suite **3,286 passed / 9 skipped / 0 failed**; `inventory --check` and
  `health --check` exit 0. Still default `0` — on **n** (one document), not on
  the hazard.

---

## 2026-09-10 (later) — the chord was grouped after the stage that needed it

Sean: *"determining when notes and voices and chords line up should be very
early in the process."* Right, and the record said so three ways.

- **The defect.** `grep -rn chord tools/omr/staged/` outside `export.py`
  returned NOTHING and the record held no chord/event/onset/voicing quantity
  at all; `group_chords_in_measure` was called only from `export._events`, at
  serialisation time. So every stage before EXPORT counted each chord member
  as a separate time-advancing event — including
  `consequences.reconcile_duration`, the pipeline's own bar-sum check.
  ⚠️ **It failed SILENTLY**: an inflated total simply never equals the meter,
  so the rule did nothing and said nothing.
- **Measured** on Beethoven 5 / Litolff: page 17 is **38.2% chord bars**, and
  ungrouped the bars landing exactly on the printed meter fall **18 → 13** —
  28% of the evidence destroyed before any consumer sees it. The inflation is
  not a constant to subtract: 13 distinct values, 0.125 to 6.0 ql.
- **`Q.EVENT`** — a CELL-scoped decision, which glyphs of a bar sound
  together. ⚠️ A VERDICT, not a measurement: `GLYPH_BOX` already carried every
  glyph's x (the ingredient was on the record and nothing read it), but
  "these are simultaneous" is an interpretation under a tolerance. A rest is
  its own event. `EVENT_X_TOLERANCE_WIDTHS = 0.6` is not a new constant — it
  is the legacy default, adaptive to the bar's own notehead width.
- **`reconcile_duration` sums EVENTS**, taking the MODE where a chord's
  members disagree. ⚠️ No event verdict means **no repair**, not a fall back
  to the old sum: a bar whose grouping is unknown is a bar whose sum is
  unknown. Effect: page 1 fires **13 → 16**; page 17 is 0 → 0 because with the
  carry off it has no meter at all.
- ⚠️ **The two groupings do NOT agree and I could not make them.** 24 chord
  members here against the exporter's 16 (172 against 102 on p17); most is a
  POPULATION difference (every notehead READ vs only those WRITABLE), and two
  explanations for the 1-and-7 residual were tested and **refuted** — the
  tolerance base (identical numbers) and narrowed durations (overshoots, 24
  and 115). The exporter's population sits BETWEEN, so the boundary is its own
  filter chain, not the clustering. **RULE parity is pinned instead.** This
  argues for the exporter consuming the verdict — the next step, now evidenced
  as necessary rather than tidy.
- ⚠️⚠️ **A field that claimed a check that never ran.** The first draft wrote
  `divisi_guard: "ran"` wherever `Q.STEM` rows merely EXISTED; the guard is not
  built. Caught by reading the field's own output on a real page. Now
  `divisi_guard: "not_implemented"` with `stem_evidence` reporting the input's
  state — and `stem_evidence: read` on some cells means the guard is buildable.
- The architecture caught one of my errors: `implicates` omitted `Q.EVENT` and
  `test_a_failed_check_implicates_the_decision_ITSELF` failed. A bar that does
  not sum may hold two notes I wrongly merged.
- 12 tests, each run RED under three mutations. Suite **3,280 passed / 9
  skipped / 0 failed**; `inventory --check` and `health --check` exit 0.
  `benchmarks/omr-staged-event-grouping-2026-09/FINDINGS.md`.

---

## 2026-09-10 — the meter carry: measured on both sides, shipped OFF

- **`OMR_METER_CARRY`** (staged pipeline, default `0`). A meter is a fact of
  the MOVEMENT, printed at its start and nowhere else, so the staged pipeline
  had no meter from a movement's second page onward while the answer sat in
  the same log one page earlier. A system whose own meter decision ABSTAINED
  now takes the last meter that was READ. ⚠️ **Never chains onto a carry** —
  only a `voted` verdict is a source, so `pages_since_read` is the true
  distance back to ink.
- **BENEFIT**, Beethoven 5 / Litolff `984073` `--pages 0-2`: page 1 decides
  `2/4` from 12 of 12 staves, both page-2 systems take it. **123 whole rests
  stop being 4.0 quarters of silence in a 2.0-quarter bar**; 22 notes with NO
  duration at all get one; `written.notes` 646 → 664 against
  `not_written.duration_narrowed` 165 → 147 — the same 18, agreeing to the
  unit; `written.empty_bars_padded_without_meter: 47` disappears as a field.
  Exactly two quantities move, `meter` (2) and `duration` (111), all on page 2.
- **CONTROLS.** Flag-off reproduces all 4,498 pre-change verdicts exactly
  (which also proves the run deterministic, so the delta is attributable);
  `no_pitch` 54 → 54 and `detected_and_unrepresented` 659 → 659 both unchanged,
  because a meter says nothing about pitch and reads no new ink.
- ⚠️ **A −1 was chased rather than rounded off**: rests 433 → 432. Not a lost
  rest — P4 m44 had been PADDED because its only note had no duration, and the
  note is now written. One of the 18 recoveries, arriving in the rest column.
- ⚠️⚠️ **WHY IT IS OFF — the hazard is on the same document.** Page 17 is the
  *Andante con moto*, a NEW MOVEMENT printing `3/8` on every staff, and all
  three of its systems abstain `no_evidence`: the template reader RAN on all 20
  staves and declined `below_threshold`, because Litolff sets `3` over `8` as
  heavy nearly-touching digits. `3/8` IS in `DEFAULT_METERS`, so it is a
  reading failure, not a missing template. A carry therefore does not merely
  RISK crossing a movement boundary here — it **does**, and holds `2/4` for the
  rest of the movement.
- ⚠️ **Four guards measured, all four refused.** *"A movement start reads SOME
  meter"* is **INVERTED** (continuations p14-16 read 1-4 spurious `C`/`4/4`;
  the movement start reads 0). Key signatures are too noisy on a scan (p14/s1
  reads {−5, −3, −1, 2}; the Andante's true −4 appears nowhere on p17). The
  printed TEMPO HEADING is the right signal but `direction` yields **0 decided
  verdicts**. A DISTANCE BOUND is arithmetically impossible: movement 1
  occupies 16 pages, so any bound under 16 truncates a legitimate carry and any
  bound of 16 or more reaches the Andante. **The blocking input is a
  MOVEMENT-START signal, not a threshold.**
- `Evidence.subjects(kind)` — structural subject enumeration, no quantity and
  no declaration check, because "what pages are there" is layout and not
  evidence. Reading a value off one is still checked.
- Tests: `TestTheMeterCarry` (6) + `TestEvidenceSubjectsIsStructural`, each run
  RED under two mutations before being believed — the no-chain rule is pinned
  by a test that fails when the `voted`-only line is removed. `A-DUR-2` in
  `tools/omr/staged/ASSUMPTIONS.md`;
  `benchmarks/omr-staged-meter-carry-2026-09/FINDINGS.md`.

---

## 2026-09-09 (evening) — the clef's neighbour, the meter's missing half, and three wrong inferences

- **`Q.CLEF_POSITION`** — where each clef glyph stands on THIS staff, in
  half-spaces from the top line. Five of six abstaining staves were an exact
  `{treble: 3.0, bass: 3.0}` tie caused by a NEIGHBOURING staff's clef landing
  in the cell's four spaces of padding. Clef decided 20→21 of 22 and 23→27 of
  27; pitches 835→881 and 1,329→1,470; `no_pitch` 67→54 and 75→**0**.
  ⚠️ Two controls: 19/19 decided staves unchanged (0 would flip), and the
  REGISTER of the newly-decided staves matches the established bass staves.
- ⚠️ **The structural finding is bigger than the fix**: every `CLEF_GLYPH` row
  on a staff shares reader+frame+quantity, so `tally` counts them as ONE
  correlated group and takes the strongest term. **No refinement of the
  detector's own evidence can break a clef contest** — a tie-breaker must come
  from another reader, which is why the position is a GEOMETRY row.
- **`METER_COVERAGE_FLOOR`** — the half of the legacy meter rule the staged
  vote had dropped. Agreement was divided by the staves that SPOKE, so 3 of 11
  shipped a 4/4 at share 1.0 on a page that prints no time signature (truth
  2/4, 18 parts). Coverage and agreement now report apart, with their own
  reasons. ⚠️ It bore on `size_measure_rest` from the same day: with a WRONG
  meter that consequence fired and laundered the error into a `measure="yes"`
  claim; now the system abstains and `measure_rests_read` goes 19 → 0.
- ⚠️ **A second meter fault filed, not fixed**: Brahms p2 reads `9/4` where the
  truth is `9/8` — the denominator digit, at NCC 0.42–0.53, with `9/8` a
  candidate and not even the runner-up. Never tune this family on one edition.
- **`probe_beam_mix.py`** — CV, YOLO and the bar sum together. The bar sum can
  settle only 13 and 6 of 142 and 296 narrowed notes, because half the bars
  have no meter.

⚠️⚠️ **THREE OF MY OWN INFERENCES WERE WRONG, each one step from being
reported.** (1) The written-range test as the fix for an abstaining clef — it
needs the instrument, which abstains on 22/22 and 27/27 staves. (2) "The
staff-line erasure is destroying the beam rung" — 98 strokes against 609, and
rendering ONE CELL killed it: 557 of the 609 (91%) sit on a staff line. (3)
"Durations are systematically doubled" — the bar sum counted every chord member
separately; 83 of the 94 4.0-bars are a lone whole rest. **A number large
enough to be convincing is not evidence about its own cause.**

---

## 2026-09-09 (later) — GATHER: the five families detected and read by nothing, and rests end to end

The lever the morning's tools identified, taken. Five notation families reached
`GLYPH_BOX` and no typed row, so four stubs could not have been filled where
they stood and rests had nowhere to go at all.

- **`gather.gather_glyph_families`** — one typed row per glyph for rests, arcs,
  wedges, dynamic letters and articulation marks. `Q.REST` is new; the other
  four quantities existed and were observed by nothing. ⚠️ Routed by CLASS,
  never by the detector's `category`: `dynamicDiminuendoHairpin` is a WEDGE
  wearing the `dynamic` category and prefix, and all ten `artic*` classes carry
  category `ornament`.
- **The stubs abstain on their own population now.** `arc_owner` ran on every
  subject at its scope — 2,728 abstentions on one page around 199 real
  subjects. With `subjects_from` it is 199, and `wedge_anchor` writes NOTHING
  on a page that prints no hairpin.
- **Rests reach the file.** `adjudicate_duration`'s domain is the tuple
  `(notehead_class, rest)` — one question for two kinds of ink. Values from
  `rhythm._REST_DURATIONS`, imported; `restHBar` abstains `unreadable_rest`.
- **The bar convention is a CONSEQUENCE**, `size_measure_rest` (meter →
  duration, CELL). All six priced cases hold, including firing in 4/4 where the
  number does not move and refusing a lone quarter rest.
- ⚠️ **It exposed a real hazard in `reconcile_duration`**: a lone 4.0 whole rest
  in a 2/4 bar would land exactly at 2.0 and be UNIQUE — the right number by
  the wrong reasoning, exported as a HALF rest with a `<type>`. Rests excluded.
  ⚠️ And a second latent bug came with the second writer: reconcile summed
  every verdict ROW, so a superseded duration would double-count.
- ⚠️ **The derived unclaimed-class check found a DETECTOR fault nobody was
  looking for**: `arpeggiato` 98 + 86 over two pages, median 56×388 and 40×243
  boxes at confidence 0.39 and 0.35 — a stem or a barline, not an arpeggio
  sign. Not excused into `NOT_NOTATION`, because that would hide it.
- **Three checks fired on this work**: ten now-stale `KNOWN_GAPS` entries were
  evicted; a latent `NameError` in `_problems` surfaced the moment a domain was
  not directly gathered; and `test_an_unsatisfiable_want_is_reported` followed
  its own written instruction and became a test of the DISTINCTION.

Rests written 209+19 and 338+11 of 228 and 350; bars padded because we read
nothing 148 → 48 and 60 → 4; detected-and-unrepresented 761 → 533 and
1,270 → 920. Both balance, both parse under music21.

---

## 2026-09-09 — the staged pipeline gets an inventory, an EXPORTER and a health report; and the record turns out not to hold rests

The three ranked tasks of `docs/handoff-2026-09-09-staged-accounting.md`, done
in order, plus the open defect its §6 filed. **No benchmark was run as a goal**
— the metric is retired (Sean, 2026-09-08) and the runs here are controls, not
scores.

- **`tools/omr/staged/inventory.py`** — the 21 decisions, DERIVED from
  `adjudicate.REGISTRY`, `ORDER`, `evaluate.RULES`, `groups`' redundancies,
  `legacy.EXTRACTED_QUANTITIES` and the AST of `gather.py`. Nothing typed.
  `--check` is non-zero on a broken invariant; `--run` folds in what each
  decision actually did on a page.
- **`tools/omr/staged/export.py`** — the staged path **can produce a file**,
  and the CLI wires it as `--musicxml`. Four real conductor's pages export and
  all four parse under music21. Not a port: it takes `tools/omr/export.py`'s
  POSITIONS and reuses its pure renderers, and restates every rule that has to
  be re-derived on a different input, each with a test.
- **`tools/omr/staged/health.py`** — per decision: is there a test saying it
  DECIDES, one saying it ABSTAINS, one saying it RECORDS. Sean's bar, applied
  literally.

**⚠️ WHAT DOING THEM FOUND**

- **2,541 detected glyphs the record cannot carry**, pooled over four pages —
  and **838 of them are RESTS, which have no quantity at all**: no `Q.REST`,
  no adjudicator, no stub, no `wants`, so unlike the stubs nothing declares the
  absence. Detected-then-dropped, inside the architecture built to stop it,
  third instance after `Ruling.detail` and the starved stubs.
- **Five of the six stubs are starved one stage earlier** — `arc_box`,
  `articulation_mark`, `wedge_box`, `dynamic_letter` are observed by nothing,
  so writing those adjudicators would still produce nothing. The next work is
  in GATHER, the thinnest stage by tests (27 against RECORD's 261).
  ⚠️ *(merge note, 2026-09-09 — all four ARE observed in the merged tree, by
  this session's own `gather_glyph_families` plus the dynamics session's two
  rungs. Only `direction` is still starved. Left standing as measured.)*
- **`tuplet_ratio`'s missing row is THE PAGE**, with a positive control on the
  same tree and weights (Beethoven 5 / Litolff `984073` `--pages 2`: 1 marker,
  1 ratio). ⚠️ The SILENCE is a real hole and is not tuplet-specific: an empty
  `subjects_from` domain writes nothing at all, which is not an abstention.
- **The redundancy layer's `checked_nothing` was the fixture** — but the
  handoff's control page was off by one. ⚠️ And **Brahms p2 is two systems and
  still checks nothing**: `_slot_fact` keys on the system's staff count, so the
  redundancy layer inherits the ordinal join's refusal exactly.
- **The exporter's accounting control RAISES** rather than returning a flag
  (`symbol_ledger.coverage_check` tried the flag and was read by nobody). It
  balances on all four pages and reveals **595 notes held in the record and
  absent from the file**, 441 of them a NARROWED duration the exporter
  deliberately refuses to collapse.
- **A `wants` entry a decision never reads is INERT**, found by a test that
  asserted the opposite and failed. Ten decisions have one; `glyph_owner`
  declares `glyph_conf` and never reads it — the standing
  `_dedupe_cross_staff_detections` observation, reproduced.
- ⚠️ **Two of the new checks were wrong when first written and both reported a
  clean ZERO**: a literal-argument AST matcher missed
  `for quantity, kind in ((Q.STEM, …), …)`, and the inert-`wants` check saw the
  decorator (where `wants` lives) as the body. Both are recorded in the code.
- ⚠️ **The health report said "EMPTY CELLS: none" once by accident** — one
  over-broad attribution clause made every decision look covered. A check that
  cannot fail is worse than no check; removed and pinned.
- **The §6 defect is fixed**: `build_cache.research_proposal` sorted `parts`
  under a comment justifying it by a rule removed the SAME DAY, whose own last
  sentence said the opposite. The unsorted proposal reproduces `works.json`
  exactly on all five folded entries across three rows; the sorted one
  disagreed on the three that came back named Piccolo. Four tests, all run RED
  with the fix reverted.
- **Handoff counts corrected**: "153 tests" is **226**.

---

## 2026-09-09 — dynamics: the block is HAIRPINS, not letters (scoping, no arm run)

- **Cloud-session capability established by inventory, not memory**:
  [docs/cloud-session-capabilities-2026-09-09.md](docs/cloud-session-capabilities-2026-09-09.md).
  A web container clones the repo and nothing else — `omr-weights/` and
  `library/` are both gitignored, so no transcription, no `scan_eval`, no
  `orchestral_eval`. **The line is exact: a change acting on an already-made
  transcription can be measured there; a change acting on the PAGE cannot.**
- **⚠️ musicdiff runs NATIVELY in a cloud container and the four-symlink
  workaround does not apply.** CLAUDE.md's OMR-NED section exists because the
  desktop host is Python 3.9; a cloud box is **3.11**, so `pip install music21
  musicdiff` is the whole setup. Verified end-to-end on a committed pair
  (beet5-p1-shift09 vs truth: **0.7152 / 1286 edits**). ⚠️ Run
  `_omrned_worker.py` from ANY directory but the repo root — `tools/omr/types.py`
  shadows the stdlib `types` and fails circularly inside `weakref`, which is
  precisely why that worker is documented as never importing from `tools.*`.
- **⚠️ THREE SCAN-GATE ROWS ARE FULLY REPRODUCIBLE FROM COMMITTED FILES.**
  Brahms 1 / Breitkopf p1-p3: the transcription (`…hollow2…/transcription.json`,
  3 pages, 83 staves, 10,523 detections), its truth (`reference.mxl`) and the
  hand-verified windows (`works.json`) are all in git, so
  **transcription → export → musicdiff → OMR-NED closes without weights.**
  ⚠️ `cells/` is still gitignored — coordinates yes, rasters no. ⚠️ One row is
  not the gate (and the gate's own noise floor is ±6 edits).
- **The dynamics finding was REPRODUCED rather than quoted**: that committed
  transcription carries **265 dynamic-letter detections and ZERO of either
  hairpin class**, and its export emits **159 `<dynamics>` and 0 `<wedge>`**. So
  the ledger's `hairpin matched_exact = 0` is not an instrument artefact — the
  detector sees the letters and is blind to the wedges, confirmed end to end
  with no weights present.
- ⚠️ Checked and NOT a finding: `mahler_p11_finetuned.omr.json` carries
  `dynamicLetterP` (the coarse 136-207 block), but `class_aliases.ALIASES` maps
  all six `dynamicLetter*` → `dynamic*`, so that artefact is pre-fix raw model
  output rather than a live gap.

- **Follow-up (Sean: "not sure our primary issue is the hairpins or the letters
  or both — we will need both read and able to interact in the adjudication
  stage"). Answer: BOTH, and they are the same size.** On the assessable rows
  the absolute miss counts are within 10% of each other — letters **127
  missing**, hairpins **140 missing** — while the recalls (0.714 vs 0.000) give
  the opposite answer. ⚠️ Quoting either figure alone inverts the conclusion,
  which is why the question had no stable answer. Different KINDS: letters are a
  precision/placement problem (186 spurious, 73 wrong-text), hairpins a pure
  recall one (0 spurious — we are silent, not wrong).
- **⚠️⚠️ The obvious adjudication check was measured and is REACH-LIMITED, and
  the sweep is the result rather than any single rate.** New probe
  `benchmarks/omr-dynamics-coupling-2026-09/probe_letter_wedge_coupling.py`,
  on the one committed reference encoding (Brahms 1, 21 parts, 1173
  `<dynamics>`, 683 hairpins): "a crescendo runs quiet → loud" is **exact at
  ±1 measure (34/34)** and **wrong 31.8% of the time at ±4**, reach 5.0% →
  19.3%. So the coupling is real and strictly LOCAL — keep it at ±1 and
  ABSTAIN beyond, additive evidence only, never a veto (`groups.py`: a wrong
  `reading` manufactures disagreement out of correct engraving).
  ⚠️ An earlier pass of this probe quoted "wrong three times in ten" from a
  single ASYMMETRIC window; that is a point on the curve, not a property of the
  rule, and the docstring now says so.
- **⚠️ The interaction that IS strong runs the direction you would not guess.**
  `hairpin_detection.BAND_TOP/BOTTOM_SPACES` (0.3–6.0 below the bottom line) is
  the SAME band the letters occupy (+0.0..+5.6, per the band study) — but the
  hairpin reader works in **page pixels per staff**, so attribution is right by
  construction, while the letters go through per-measure cells and lose **24% to
  the staff above**. **The hairpin reader's band discipline is the fix for the
  letters' placement problem**, not the reverse. Structural, so it does not
  decay with distance the way the direction check does.
- Corollary for the staged pipeline: gather both observations in ONE band frame
  and they meet at `Q.GLYPH_OWNER` — already a real adjudicator, not a stub. The
  two readers are genuinely independent (YOLO letters, classical-CV wedges), so
  the ancestor-closure rule admits them as corroboration rather than collapsing
  them to `SINGLE`.

- **Scoped, nothing measured new**:
  [docs/scope-dynamics-reading-2026-09-09.md](docs/scope-dynamics-reading-2026-09-09.md).
  Every figure is read off a committed artefact; no benchmark arm was run.
- **The two halves separate cleanly in the symbol ledger** (20-row scan gate):
  `hairpin` **matched_exact = 0** with 0 spurious beside it — on every row whose
  parts join we emit no wedge at all — while `dynamic` (letters) reads 244
  matched_exact + 73 attribute-error against 127 missing, ≈71% truth-side
  recall. ⚠️ **They had been filed as one problem, which is why neither moved.**
- **"They're just alphabet letters, use a text tool" is half right.** They are
  SMuFL music-font glyphs (`dynamicForte` U+E522), not text-font letters, and
  `direction_text.py` already runs Surya + Tesseract by default and
  *deliberately refuses* them — its own gate is a 181-word musical lexicon, and
  a single character has no lexicon to be gated by. The tool genuinely missing
  is the third one: **`symbol_library/` holds 38 Bravura templates and not one
  dynamic glyph**, while `glyphnames.json` carries all 42 including the
  COMPOSITES (`dynamicFF`, `dynamicSforzando`) — which would dissolve the
  letter-assembly problem rather than improve it.
- **⚠️ The `OMR_CV_HAIRPINS` pricing is STALE BY ONE DAY, in the direction that
  matters.** The flag is off because it costs OMR-NED, but its own docstring
  attributes half the cost (+37 of +76 edits) to Brahms 1 p2 — a row where
  `_stitch_slots` REFUSED, so no hairpin could pair whatever the anchor picked.
  That arm ran **2026-09-07**; `OMR_SLOT_STITCH` went default ON **2026-09-08**
  and Brahms p2 is *the* row it repairs (27 fragments → 14 parts, 0% → 100%
  correspondence). **The top action is a re-run, not new code** — and it is
  ranked first precisely because the prediction could be wrong.
- **Staged pipeline**: `Q.DYNAMIC`, `Q.DIRECTION` and `Q.WEDGE_ANCHOR` are all
  three declared stubs, and ⚠️ **nothing is behind them** — `Q.DYNAMIC_LETTER`
  and `Q.WEDGE_BOX` are declared in `record.py` and emitted by no gatherer. The
  declared composition is already right, and `Q.GLYPH_OWNER` is the one piece
  that is NOT a stub — so gathering the letters hands the placement fix to a
  real ownership adjudicator instead of bolting the band rule into
  `_dedupe_cross_staff_detections` by hand.
- Four refusals recorded so they are not re-tried: confidence as a filter (233
  of 911 good letters lost to remove half of 35 bad), a band GATE (under-emits
  on both arms), a cross-staff column vote (deletes the soloist-against-section
  `p`), and OCR on single letters.

---

## 2026-09-08 — `OMR_CV_HAIRPINS` re-priced, and dynamics enter the staged pipeline

**The hairpin re-run (Task 1).** Two fresh `scan_eval` arms over the 20-row gate
on the current default tree. ⚠️ **The prediction that motivated it was WRONG.**
`docs/scope-dynamics-reading-2026-09-09.md` §4 argued the 2026-09-07 pricing was
stale because Brahms 1 p2 supplied +37 of the +76 and `_stitch_slots` REFUSED on
it; `OMR_SLOT_STITCH` went default ON the next day. The stitch flag DID repair
that row — `stitch` verdict now `joined`, OFF-arm edits 6547 → 6335 — and **the
hairpin cost on it is unchanged at +37**. Summed +82 against +76, same
11 worse / 8 unchanged / 1 better. Neither arm cached (36m31s, 30m57s; validity
20/20 rows differ only in CV hairpins).

**The bucket split** the flag's docstring asked for refutes its own explanation:
+28 of Brahms p2's +37 is `entire measure insert/delete` **on a row whose parts
join**, so the structural half was never the refusal — it is amplification.
`beethoven-984073-p4` is the pure case: truth carries no hairpin, one invented,
+7 edits, zero wedge-bucket movement. Over the 12 moved rows: wedge +35,
structural +69, other −22.

⚠️⚠️ **And the symbol ledger says the opposite of OMR-NED.** Same two arms,
accounting control passing on both: `hairpin` **matched_exact 0 → 97**, missing
**323 → 187**, spurious 4 → 57, with 13 of 15 other families identical to the
row. 136 truth hairpins recovered on a family whose recall was 0.000 with ZERO
spurious. **Recommendation: default it ON — left OFF pending Sean's call**,
since every default flip here is his and this one buys recall with 53 spurious
wedges. `mahler-p4` (27 truth hairpins, 7 read, 0 paired) is where an anchor
investigation starts, not Brahms p2.

**Dynamics into the staged pipeline (Task 2).** `Q.DYNAMIC_LETTER` and
`Q.WEDGE_BOX` were declared and emitted by no gatherer. Both are now gathered,
**in page pixels against the staff's own bottom line** — the frame
`hairpin_detection` already uses, and the reason the two families become
comparable at all. `READERS.CV_HAIRPINS` is a new reader rather than a mode of
`CV_LINES`. `adjudicate_dynamic` is implemented and **the fix is the ownership
query, not the spelling**: a letter belongs to the cell whose STAFF
`Q.GLYPH_OWNER` names, whatever cell it was cut from. An unspellable run
`narrow`s rather than abstaining. Guarded by `test_staged_dynamics.py`, every
central assertion run RED under a mutation first.

**Partial letter runs (Task 3).** `OMR_PARTIAL_DYNAMICS`, default `off`,
byte-identical to main. ⚠️ **Corrects a standing note**: the dropped population
is "dominated by a lone `s`" on the 11-page band corpus and NOT on Brahms 1 /
Breitkopf, where 15 of 20 dropped runs are a prefix of nothing and look like
`ppmsf`. Priced over the 20-row gate with `probe/reexport_arm.py`: `complete`
+15 edits, `other` +30, **not one row better**. Refused, and re-priceable on the
staged path where ownership is decided before the word is spelled.

---

## 2026-09-08 — works.json: mahler p2's four one-line percussion staves, and the row that closed cause D into cause B

- **`test_works_json_staff_lineup.py` had two tests failing on `main`, and it
  was a DATA defect, not a code one.** `1cf44dbc` added mahler p2's
  hand-confirmed 21-entry `staves` map — closing cause D, the scan gate 20/20
  mapped — but the map lists PRINTED staves and the page prints four one-line
  percussion rules, so `expand_lineup` read 21 five-line slots against our 17
  parts and the arity gate refused. **The row moved from cause D straight into
  cause B; the bucket total never moved, only its label.**
- **Fixed with four `lines: 1` fields** on `Becken`, `Grosse Trommel`,
  `Kleine Trommel`, `Tamtam`. ⚠️ **`Pauken` is a five-line staff and is not
  flagged** — the one entry a name-matching rule would get wrong. Neither the
  identity nor the count was inferred from names: `page.n_staves_note` names
  the rules in prose and `condensation.staves_as_printed` carries `lines` for
  all 21 entries independently, and after the fix every one of the 21 agrees.
  ⚠️ The prose says FIVE rules and four entries are flagged — the fifth is the
  combined-player staff the reference has no part for, so it is not a lineup
  entry (21 − 4 = 17 = `page.n_staves`).
- **Controlled A/B, same tree, only `works.json` differing** (record:
  `benchmarks/omr-part-join-2026-09/mahler-p2-oneline-ab.json`): joined rows
  **16 → 17 of 20**, pooled `part_unresolved` **7,985 → 7,266 (−719)**, p2's
  `uncorresponded` **771 → 52**. **Exactly one row changes**, the other 19
  identical outcome for outcome, and pooled musicdiff is identical between
  arms — a live control, since `works.json` cannot reach it.
- ⚠️ **The row gains no new symbols.** The same 527 truth / 244 predicted enter
  both arms and `coverage.balanced` is `True` in both; 194 predicted symbols
  stop owning a row of their own and become a truth row's PARTNER. The 771 → 52
  fall is that pairing, not new evidence.
- ⚠️ **The 52 that remain are the right 52**: 13 rows each on truth parts 23-26
  (`Becken.`, `Grosse Trommel.`, `Kleine Trommel.`, `Tamtam.`) — a clef, a key,
  a time signature and 10 rests apiece. A five-line staff detector cannot find
  a single printed rule, so that music is genuinely unread and the field says
  so instead of joining it to something.
- ⚠️⚠️ **AND IT WILL RECUR — the writer cannot carry the field.**
  `merge_additions.shape_problems` refuses any key beyond `name`/`parts`, and
  the confirmation UI proposes none (p2's additions row is `{name, parts,
  proposed, verdict}`), while `build_cache.py:496` computes `"lines":
  spec.get("lines", 5)` and it is dropped on the way out — the
  computed-and-unread pattern again. **Not fixed here**: it changes a writer's
  contract and the additions schema, and no unmapped row remains to exercise
  it. The next row mapped through that path with one-line percussion lands
  unflagged and its whole page unassessable, with the test as the only alarm —
  after the human pass is spent.
- **⚠️ THE GENERATOR GAP IS CLOSED TOO (same day).** The deferral in the
  bullet above was reversed: *"no unmapped row remains to exercise it"* argues
  for a cheap fix, not against one, because the failure costs a HUMAN
  CONFIRMATION PASS rather than compute. Four projections between
  `build_cache` (which computes `lines`) and `works.json` each dropped it —
  the UI's row seed, the UI's `staves_for_works_json`, `check_row`'s fallback,
  and `shape_problems`' refusal of any key but `name`/`parts`. Now: the two
  arity fields are allowed and **validated** (`lines` must be 1 or 5,
  `printed_staves` a positive int, no entry both a one-line rule and several
  printed staves, unknown keys still refuse); the projection is written ONCE as
  `merge_additions._entry_for_works_json` and **imported by the UI** so the two
  cannot drift.
- **The guard now runs at the WRITER.** `arity_problems(row, staves)` asks of
  the map about to be written exactly what `test_works_json_staff_lineup.py`
  asks of the file, calling `run_ledger.expand_lineup` rather than recomputing
  it, and abstaining on non-uniform pages as the test does. ⚠️ The point is
  WHEN it fires: a data test fires after a 21-staff human pass is spent.
- **⚠️ Retrospective control:** dry-run against today's additions file, the
  guard refuses **all five** rows whose entries predate the field (mahler
  p2-p5 and bach) — the whole population that had the defect, not just the row
  that was noticed. Behaviour changes for none of them (all already refuse on
  *"already carries a map"*), and a stale `staves_for_works_json` from the old
  UI now fails loudly instead of writing an unflagged map.
- **Five mutants, each red on exactly the intended test**, and the decisive
  test is not synthetic — it feeds `arity_problems` mahler p2's map *as
  `1cf44dbc` merged it*. `TestAOneLineRuleSurvivesTheWholeWritePath` proves the
  chain rather than the links, against a control removing only that field.
- ⚠️ **One existing test was left alone rather than loosened**:
  `test_the_confirmation_ui_asks_it_too` asserts a literal import string that a
  tidy parenthesised import broke, so the import was written back out as single
  lines. A guard is not relaxed to suit a later edit.
- **Files touched:** `benchmarks/omr-scan-e2e-2026-09/works.json` (4 fields),
  `benchmarks/omr-part-join-2026-09/FINDINGS.md` (§7),
  `benchmarks/omr-part-join-2026-09/mahler-p2-oneline-ab.json` (new),
  `benchmarks/omr-staves-map-2026-09/merge_additions.py`,
  `benchmarks/omr-staves-map-2026-09/server.py`,
  `tools/omr/tests/test_staves_map_validation.py`,
  `CLAUDE.md`, `PROJECT_BRIEF.md`, `version_memory.md`.

---

## 2026-09-08 (late) — causes A/B/C closed, `OMR_SLOT_STITCH` default ON, and the meter's own garbage filter wired to its keeper

- **`OMR_SLOT_STITCH` is DEFAULT ON** (Sean's call). Never scored worse
  (−240 raw / −2,278 page-normalised); flipped once the separated `entire
  staff` bucket showed its 3 rows own **46.3% of the unassessable symbol
  mass**, so the cost of `off` is a blocked measurement rather than a foregone
  score, and once the blast radius was shown confined to rows the ordinal join
  has ALREADY refused (**10 of 11 exports byte-identical**; Brahms p2's 27
  fragments → 14 continuous parts, 0% → 100% ledger correspondence).
  ⚠️ The flag site's docstring still carried the refuted *"it still costs more
  OMR-NED"* claim a day after CLAUDE.md was corrected.
- **⚠️ The canary recommended for that flip could not reach it.**
  `label_contradiction` is computed in the contextual pass; the flag is read in
  `export.py`, strictly downstream — identical on and off **by construction**.
  Recommended before checking; the check was one grep. Its QUESTION does reach
  the join: `slot_stitch_canary.py` asks whether the staves a stitched part is
  built from carry margin labels that AGREE — **30 parts with evidence, 0
  disagreements**, `no_evidence` reported apart, positive control printed.
- **Causes B and C closed by DATA, not code**: `one_line: true` (nine
  percussion entries) and `printed_staves: 2` (bach's cembalo) are now fields
  in `works.json`, each asserted against the derivable count and pinned by
  `test_works_json_staff_lineup.py` (run RED against two mutants).
  Rows with a resolved part join over the 11 committed pairs: **7 → 9 → 10**;
  on the 20-row gate pooled `part_unresolved` **14,992 → 7,985**. Only cause D
  (mahler p2's missing lineup) remains.
- **`rhythm._drop_implausible_meters`** — unconditional. `_is_propagatable_meter`
  names `1/4` as garbage in its own docstring and was consulted only for
  VOTING eligibility, never for whether a staff may KEEP a reading: **4 of 227
  staves and 45 of 2,538 measures**, all `1/4`, across three publishers.
  ⚠️ **Its payoff arrived through a channel not being measured** — 0 rests,
  4 notes re-read `16th` → `eighth`, `rhythm_sum_warnings` 48 → 39 — via the
  meter→rhythm loop. The 37 wrongly-sized rests belong to two parked guards
  (a lone dissenter, 7; three corroborating dissenters, 30).
- **The pattern of the day, recorded as such**: four of five findings were *the
  value existed and nothing read it*, two of them inside the measuring
  instruments. Big-picture handoff:
  [docs/handoff-2026-09-08-big-picture.md](docs/handoff-2026-09-08-big-picture.md).

---

## 2026-09-08 (evening) — Step 4 separated the `entire staff` bucket; Step 3's measure-rest convention fixed

- **STEP 4: `entire staff` is FOUR problems, not three, and only one is the
  reader's.** A derived classifier over three hand-verified `works.json` facts
  accounts for the bucket to the symbol — 14,992 vs 14,992 pooled
  `part_unresolved`, 0 rows `unexplained`: **A** `_stitch_slots` refusing (3
  rows, 6,937 symbol rows, 46.3%, the reader); **B** the lineup naming one-line
  percussion staves (3 rows, 32.1%, the ledger's arity gate, and the arithmetic
  is exact to the staff on all three); **C** one lineup entry covering two
  printed staves (bach's cembalo, 16.5%); **D** no lineup at all (mahler p2,
  5.1%) — which the handoff had silently inside the bucket and which is not a
  reading fault. Cause A's three rows are exactly `OMR_SLOT_STITCH`'s measured
  reach; its **n** objection is unchanged.
  `benchmarks/omr-part-join-2026-09/FINDINGS.md`.
- **The symbol ledger was losing 1,771 truth symbols, and its own control said
  so to nobody.** `coverage_check()` reported `balanced=False` on 9 of 20 rows,
  was written into the summary JSON and read by nothing — Class C inside the
  instrument built to make the metric legible. Its rest rule was **98.5%
  wrong**: it dropped every rest of a condensed staff, where 1,050 of 1,066 are
  the all-parts-rest case an engraver prints. Fixed with a new
  `absorbed_by_condensation` outcome; controlled A/B: unbalanced 9 → 0,
  `rest.type` 471 → 963, `rest.duration_ql` 471 → 942, **every non-rest figure
  identical to the unit**.
- **STEP 3: a whole-rest glyph is not four quarters of silence.** The previous
  diagnosis (`_measure_rest_beats` fed `None`) was wrong — that function is
  never CALLED for these bars, and the measure carries its meter. The fault is
  the convention. `export._is_lone_measure_rest` routes a lone whole rest
  through the measure-rest path; 558 of 618 wrong rest durations (90.3%) are
  such a bar. ⚠️ Restricted to the **whole**-rest glyph after the first cut
  inflated single detected QUARTER rests into full bars and cost 34 edits on
  `brahms-sym4-mvt1`.
- **⚠️ OMR-NED cannot see it, on either family** — engraved 0.12138/2532 in both
  arms in all 23 categories, scan gate 34,963 edits in both arms on all 11 rows
  — while the ledger records `rest.type` 933 → 10 and `rest.duration_ql` 328 → 4
  on the engraved eleven with every non-rest family identical. The positive
  control: six works' rest `<duration>` values MOVED (Beethoven 3's whole rests
  4.0 → 3.0 in 3/4, matching truth).
- **⚠️ The "residual is a METER problem" conclusion was itself an artefact, and
  was corrected the same hour.** Per row, every movement-OPENING page reads its
  meter on 100% of staves and every CONTINUATION page reads almost none —
  correct, because a meter is printed at a movement's start and `transcribe`
  carries it forward, but **the gate transcribes ONE PAGE PER ROW so the carry
  has no previous page**. Pages 1-2 in one call: page 2 goes 0 → 20 of 22
  staves with a meter, parts 12 → 34 of 34, and **218 of 255 lone whole rests
  come out at the printed 2/4 length**. So the rest fix is worth MORE in
  production than the benchmark can show. ⚠️ **The standing hazard: the gate's
  one-page cut silently disables every page-spanning mechanism.** What remains
  is 4 staves of 34 reading 4/4 on a 2/4 movement — a vote/override question,
  37 rests. `benchmarks/omr-rests-2026-09/FINDINGS.md` §7-§13.

---

## 2026-09-08 (night) — Steps 1 and 2 CLOSED; Step 4 promoted ahead of Step 3

Handoff: [docs/handoff-2026-09-08-night-step4-then-step3.md](docs/handoff-2026-09-08-night-step4-then-step3.md).

- **The Viola question is ANSWERED**: `detail.n_accidentals` is **1** — a
  detection shortfall, not the alto slot table, corroborated from inside the
  same run (two staves that found 3 boxes read −3; the Clarinet found 1 and is
  correctly −1). Underneath it, **`staged/gather.py` imports
  `locate_key_signature` and nothing else** — `key_signature_template`, measured
  11 of 12 on that exact page against the locator's 2 of 12, is referenced
  nowhere under `tools/omr/staged/`. Parked **D20**.
  `benchmarks/omr-staged-shadow-2026-09/FINDINGS.md`.

- **Step 2 CLOSED** — `benchmarks/omr-staged-shadow-2026-09/STEP2_2026-09-08.md`.
  The divergence table **was blind to 99.3% of what staged decides** (12 of 20
  quantities, 18,177 of 18,302 verdicts) because `divergence()` iterates
  `legacy.items()`; now `staged_only` + `coverage`. **4 of 16 "disagreements"
  were NARROWED verdicts** read as DIFFER with legacy's answer inside the
  candidate set; now `NEW_NARROWING`. The list is ranked by staves touched with
  each row's `basis` closure translated to quantities.

- **GROUPS exercised for the first time, and "run a multi-system page" was
  NECESSARY AND NOT SUFFICIENT.** `_slot_fact` puts the system's staff count in
  the fact key deliberately, so a 14+13 page corroborates nothing BY
  CONSTRUCTION. The 11+11 control works: `clef_across_systems` 8 unanimous +
  **1 split**, `staff_group` 11 unanimous, `checked_nothing` 4 of 6 → 2 of 6.
  **Its first catch, adjudicated by Sean against the print**: the Fagotti staff
  opens in bass, goes to a C clef, returns to bass two bars later — yielding a
  `clef_locator` **false positive** (it fired `tenor` on cell 0, which prints a
  bass clef, unopposed because the detector read nothing) and **a mid-staff clef
  change neither pipeline can express** (`Q.CLEF` is staff-scoped; no arm reads
  past cell 0).

- ⚠️ **THE STAGED PIPELINE CANNOT BE SCORED — IT HAS NO EXPORTER.** Both
  instruments take MusicXML on both sides; staged produces none and has no
  `pages` key. `git log --all -S` finds no bridge on any branch and nothing
  outside `tools/omr/staged/` and its tests imports it. "Never scored" is a
  missing component, not an oversight.

- ⚠️ **Step 3 opened and is BLOCKED BY STEP 4, measured**: only **416 of 4,239
  rest rows are assessable (9.8%)**, from 2 of 11 rows, because the part join
  fails on the other nine. Still, the first look found the mechanism: **139 of
  173 rest duration errors are one thing** — a whole-measure rest emitted as a
  literal whole note (4.0 ql) regardless of meter, so a 4/8 bar comes out twice
  over-full. **The sizing code is correct and simply not fed**; the exporter
  writes `<time>4/8</time>` into a part and then a 4.0-quarter rest into its
  2.0-quarter bars. NOT FIXED — priced on the wrong corpus.
  `benchmarks/omr-rests-2026-09/FINDINGS.md`.

- **`tools/omr/key_consensus.py`** (new, wired into nothing, parked **D21**):
  concert key by consensus over concert-pitch staves, written key per staff by
  deduction through `fifths_offset`. Flags the Viola from 3 witnesses without
  being told. False positives on already-correct data **15.1% → 5.9%** over 152
  orchestral encodings, the whole gap being one defect (`unpitched` honoured
  only half — a drum has no key). Found four transposing instruments the
  lexicon calls concert pitch: **Alto Flute (in G), Oboe d'amore (in A), Bass
  Sarrusophone (in B♭)** — recorded, NOT fixed, because a lexicon change is
  global. `benchmarks/omr-string-key-agreement-2026-09/FINDINGS.md`.

- **`claude/rescue-midstaff-key-lilypond`** — mid-staff KEY changes reaching the
  LilyPond exporter, rescued from **uncommitted** working-tree changes in a
  stale worktree; it exists nowhere else in history. ⚠️ Not merge-ready (its
  `export_coverage.py` hunk targets the `VISIBLE` list `74aa7272` deleted).

---

## 2026-09-08 (evening) — Step 2 opened: the first shadow run on real ink

- **The staged pipeline ran against the existing one on a real scanned page**
  for the first time (Beethoven 5 / Litolff, `pdf_page_index` 1, 12 staves).
  **agree 50, differ 4, new_abstention 20, new_decision 0, legacy_only 0** over
  74 rows. **JOIN CONTROL: `staff_ordinal` 12 of 12** — the subject keys line
  up, which is what makes the rest readable.
- **`4e089e00` — the CLI gathered TWICE.** `--against` re-ran
  prepare/gather/adjudicate and built the divergence table from a SECOND log,
  so `result["adjudication"]` and `result["divergence"]` described different
  passes of a detector with documented run-to-run jitter — contradicting
  `pipeline.py`'s own docstring, where "one gather, jitter cancels exactly" is
  given as the reason shadow mode exists. Also doubled every `--against` run.
  ⚠️ The table is now built **immediately after ADJUDICATE, before GROUPS and
  EVALUATE**: a consequence may restate a value, and building it later would
  compare legacy against post-consequence values while calling them decisions.
- ⚠️ **`be76d961` — the two paths stated the same fact in different shapes and
  `==` never noticed.** `key_signature`: legacy writes
  `{'sharps':0,'flats':2,…}`, staged returns `int(fifths)`; a dict never equals
  an int, so **every decided key-signature row was DIFFER by construction —
  including perfect agreement.** `instrument` had the same defect **latently**
  (`{"name":…}` vs name+family+more), found by asking what each adjudicator
  returns rather than by reading a table. `NOT_COMPARABLE` is now a counted
  first-class outcome — the symbol ledger's principle, that `uncorresponded`
  and `not_assessable` are counted and never absorbed.
  ⚠️ **The guard points the other way**: an adapter may only re-express a unit,
  never make two different readings look equal. A false DIFFER gets
  investigated; a false AGREE does not.
- **The result, stated honestly.** All four `differ` rows are key signatures.
  Against the dossier's written keys joined through `works.json`: staged right
  on 3, legacy on 0. ⚠️ **But that is not "3/4 vs 0/4"** — staged decided only
  **4 of 12** staves and declined 8, while legacy decided all 12 and is wrong
  on every one checkable. **`NEW_ABSTENTION` is a feature that scores as a
  loss**, exactly as designed.
- ⚠️ **OPEN: the Viola.** Hypothesis (Sean) that the alto clef fired a wrong
  signal is **FALSIFIED — the clef read `alto` correctly** — and his correction
  is the right one: an alto clef changes *where* accidentals are drawn, not
  *how many*; a non-transposing viola in C minor is −3 like everyone else.
  Correct clef, correct slot table, still −1. `detail.n_accidentals` splits it:
  **1** = only one flat found (detection shortfall, the fit may not infer);
  **3** = all found and mis-fitted (a real alto slot-table bug). Different
  fixes. First job on the next session.
- ⚠️ **A coordinator-written probe produced a false finding.** It indexed
  record rows on `'row_id'` when the serialised key is `'id'`, so the index was
  empty, every lookup missed, and the basis walk returned `Counter()`
  regardless of content — briefly "showing" that a key-signature verdict rested
  on nothing. *A zero is a suspect.* The corrected probe prints `len(by)` and
  `len(basis)` as positive controls.
- **Branch audit — nothing needed merging.** `agitated-bassi` and
  `dynamics-letters-clef-approach` are **0 ahead of main**; `compassionate-kilby`
  and `slot-group-mapping` **do not exist on origin at all** and may hold
  review-ready work only on the Mac. ⚠️ The first pass read "634 ahead, no merge
  base" — **artefacts of a shallow clone**, corrected with `--unshallow`.
- **`49247b6f` — CLAUDE.md contradicted itself** about whether the `Tp.` fix is
  in main. It is. `fixed-then-kept-open-in-prose`, second recorded instance, and
  worse than a stale sentence because naming a branch as the place to get
  something is a work order.
- **Still not measured anywhere on this branch**: no `orchestral_eval`, no
  `scan_eval`, no OMR-NED. Handoff:
  [docs/handoff-2026-09-08-evening-to-local-session.md](docs/handoff-2026-09-08-evening-to-local-session.md).

---

## 2026-09-08 — The tenth export gap, and the hole in the check built to catch them

- **`<ornaments>` was never emitted.** `grep -c ornaments tools/omr/export.py`
  was 0 while the detector fires `ornamentTrill`/`Turn`/`TurnInverted`/`Mordent`
  freely. Same shape as the nine forensic "detected then dropped" bugs.
  `transcribe._attach_ornaments_in_cell` (beside `_attach_articulations_in_cell`)
  → `voicing` → `export._mxl_ornament_elements`. `<ornaments>` sits between
  `<tuplet>` and `<articulations>` in one `<notations>`; music21 10.5 round-trips
  both `Trill` and `Tremolo`.
- ⚠️ **THE HANDOFF TABLE DOUBLE-COUNTED, AND CONFIRMING IT INVERTED THE JOB.**
  It listed `<ornaments>` (truth 12 engraved) and `tremolo` (truth 12) as two
  gaps. They are one: `beethoven-sym3-mvt1` is the ONLY one of the eleven
  benchmark truths carrying ornaments, and its 12 `<ornaments>` contain 12
  `<tremolo type="single">1</tremolo>` and nothing else. Pinned by
  `test_the_engraved_ornaments_are_ALL_tremolo`.
- ⚠️ **SO THE ENGRAVED GAP DOES NOT CLOSE, AND IT IS NOW A DETECTION PROBLEM.**
  Census over the committed transcriptions: **ZERO `tremolo1`–`5` detections**
  against a positive control of 34,115 detections walked across 11 files, and
  none of the ornament detections is on a benchmark work. The export half is
  closed and the engraved count will stay at 0 until the detector fires. Filed
  in `KNOWN_GAPS` with the evidence, so
  `test_the_inventory_has_no_stale_entries` evicts it the day a detection lands.
- ⚠️ **The class IS taught, it just does not fire.** Independently checked while
  verifying the above: `tremolo2` and friends appear as **hand-labeled** boxes in
  `benchmarks/omr-labeling-*/verdicts/*.verdict.json` (46 occurrences over 8
  files) with `human_category: ornament`. So this is not an absent class in the
  label corpus — it is a class the corpus carries and the checkpoint does not
  produce. That is a narrower and more actionable statement than "no detections".
- **LilyPond gets the four ornament marks and NOT tremolo, deliberately.**
  LilyPond's `c4:32` is a *duration subdivision*, so a wrong mapping writes a
  different RHYTHM rather than a different mark. Hairpin precedent; reason
  recorded rather than the construct approximated.
- **`export_coverage`'s element set is now DERIVED from the truth files.** The
  hand-written 19-name `VISIBLE` dict is deleted — an element in neither
  `VISIBLE` nor `KNOWN_GAPS` failed nothing, which is precisely the blindness the
  module exists to remove. Scope is now: inside `<measure>` (structural — the
  header lives outside it) → categorical → **rollup to the shallowest missing
  ancestor** → a 3-name `NOT_NOTATION` deny-list. That answers the docstring's
  own objection to deriving ("55 elements, ignored, then deleted"): on the
  committed 11-work fixture copy, 88 in-measure elements → 40 categorical → 19
  heads → **16 reported**, the rollup doing 21 of the 24 reductions and the
  deny-list only 3.
- **The decisive RED:** reinstating the pre-2026-09-08 allow-list makes
  `test_ornaments_IS_one_of_them` fail — the old check does not report
  `<ornaments>` on the real committed truth pool. It reported 5 elements and was
  blind to 15.
- **14 new `KNOWN_GAPS` entries**, every one a gap that had been reported by
  nothing. Largest after `<stem>` is **`<transpose>` at 92**.
- ⚠️ **Two self-inflicted faults caught by the discipline, both worth keeping.**
  A reach probe read `bbox_page` as `[x0,y0,x1,y1]` when it is `[x,y,w,h]`, so
  every median notehead width was negative and nothing said so — the probe now
  asserts that quantity is positive before using it. And
  `test_the_rollup_walks_more_than_one_level` PASSED under the mutation it was
  written to catch (chained immediate-parent rollup gives the same answer);
  rewritten to the one distinguishing case and re-run red.
- **`stale_entries` had to be redefined.** `expected − missing` meant three
  different things; `grace`/`unpitched` are gaps on scan truths and absent from
  engraved ones, so without this the suite would go red on a machine with
  fixtures for a non-defect. It now asks our own output.
- ⚠️ **`TestTheRepositoryItself` skips wherever fixtures are absent — the one
  test that would have looked never ran.** New `TestTheCommittedFixtureCopy`
  runs on a clean clone, asserting on the tables only, never on the exporter.
- **Measured with the symbol ledger, not OMR-NED** (handoff §2: musicdiff
  attribution is void — amplification differs 6×–2× by error kind and one changed
  `<type>` scores ZERO on 10 of 20 files). On the committed Breitkopf Brahms 1
  transcription: `<ornaments>` 0 → 4, ledger `ornament` rows none →
  `{'trill-mark': 4}`, **non-ornament rows 6,086 → 6,086 identical** (additive).
  Reach 4 of 8 trills find a notehead; confidence does not separate the two
  groups.
- **Parked, observation kept:** `arpeggiato` at 856 detections (99 on three
  Brahms pages) — a different element (`<arpeggiate/>`, not inside `<ornaments>`)
  and the rate looks like over-detection.
- `_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS = 1.0` is **declared UNMEASURED** — unlike
  the articulation constant beside it, there is no corpus to sweep it on.
- ⚠️ **NOT MEASURED, and no number is claimed:** this container has no weights,
  no fixtures and no venvs, so no `orchestral_eval`, no `scan_eval`, no OMR-NED.
  `test_score_language.py` is **unverified here** (corpus-wide, does not finish);
  it passed on the clean-`HEAD` baseline and this change touches neither it nor
  its subjects. Full suite on the final tree: 2,948 passed, 64 skipped, 2 failed
  — the two being the documented `.venv-surya` `TestReaderSelection` pair,
  failing on clean `HEAD` too.
- **Files:** `transcribe.py`, `voicing.py`, `export.py`, `export_coverage.py`,
  `class_aliases.py`, `score_translation.py`, 4 test files;
  `benchmarks/omr-export-gaps-2026-09/FINDINGS-2026-09-08-ornaments-and-the-derived-check.md`
  and `probe-ornaments-2026-09-08/`.

---

## 2026-09-06 — The prior may not overturn a label the system contradicts

- **`Tp.` exported as a second trumpet on Beethoven 5 / Litolff, with a CORRECT
  lexicon.** `lookup('Tp.')` returns Timpani at `high`; the alias is declared
  ambiguous (Timpani in the German/Italian tradition, Trumpet in the English),
  so the slot goes to `score_layouts.resolve_ambiguous_label`; the canonical
  layout puts the timpani AFTER the trombones while this edition prints it
  BETWEEN the trumpets and the trombones; the aligner is monotone, so staff 8
  took the second trumpet slot. Being ambiguous had also withdrawn the PIN that
  would have taught the aligner the print's order.
- **Third instance of the ambiguous-alias family** (after `c0a80ae7` and
  `fa8258c1`) and **the first whose fault is in the prior rather than in a
  consumer of it** — so, unlike the other two, no lexicon change was involved.
- **The fix uses evidence already on the page**: `Tr.` stands four staves up on
  the same system, and an engraver does not name one section with two different
  abbreviations on one system. The positional prior may not move a staff onto an
  instrument a different alias on the same system already names.
- ⚠️ **Asymmetric on purpose** — it refuses only an OVERTURN and never removes
  the lexicon's own answer. `Tr. Bas.` forces this: both its candidates are
  separately named on its system, so excluding every clashing candidate would
  leave nothing and break a reading that is already right.
- **Measured** over the 1422-label margin corpus
  (`probe_ambiguous_cooccurrence.py`, committed): 86 of 158 ambiguous-alias
  occurrences clash; hand-adjudicated, the rule keeps or restores the right
  answer in **86 of 86** and blocks a correct overturn in **0**.
- ⚠️ **The control is `basso`, and it passes because every clash is Handel's.**
  `c0a80ae7`'s Contrabass overturn is untouched — no orchestral page in the
  corpus names Contrabass twice. The probe FAILS if an orchestral source ever
  joins that list. Handel's *Messiah* prints `BASSO` (the bass voice) and
  `Bassi` (the string basses) on one page and needs both first answers as they
  stand.
- **Same-tree A/B on `--pages 23,44`**, against the hand-read lineup: 24/29 →
  **26/29**, the 17-staff finale system **16/17 → 17/17 exact**, `Timpani ->
  Trumpet` ×2 gone, no other confusion moved. Exactly 3 staff records change,
  all slot 8, all `Trumpet(score_order_ambiguity)` → `Timpani(label)`.
- ⚠️⚠️ **REACH, measured on all three regimes: the bug lives in exactly one, and
  it is NOT the web app's.** `--pages 0-4` (what `local_omr.py:233` actually
  transcribes, default 5) is **byte-identical, 0 records** — movements 1-3 give
  an 11-slot reference with no trombones and the timpani at slot 6, so nothing
  overturns. `--pages 23,44` (a window SPANNING the movement boundary) is where
  it fires. 88 pages is a no-op again. **So this is not a fix to the default
  web-app path** and must not be sold as one; its reach is the CLI and any run
  with `OMR_MAX_PAGES` raised — the whole-work case the project is for. It ships
  because it is correct and **proven inert in the other two regimes**.
- ⚠️ **Three cells, not two:** narrow-at-the-front ≠ narrow-anywhere. They differ
  in whether the window crosses a movement boundary, which is what exposes this
  class of bug. Scored only on pages 0-4 and only on the whole work, this fix
  measures zero — twice.
- ⚠️⚠️ **SCOPE: that figure is about NARROW page sets.** The committed 88-page
  artefact (`out/whole-report2.extract.json`) already has slot 8 = Timpani and
  `ambiguous_labels_resolved = 1`, so the guard is a **no-op** there — with a
  whole work voting, the layout fit proposes Timpani or abstains. Third time
  page-set size has changed an identity result; score identity work on BOTH a
  narrow set and the 88-page extract.
- ⚠️ **The 7 residual errors on that 88-page run are MIS-SLOTTING, not
  mis-naming** (800/807; `Violin -> Trombone` ×4, `Viola -> Trombone` ×2,
  `Timpani -> Trombone` ×1; 17-staff systems 663/663). All carry
  `instrument_source: label`: the strings land on slots 9/10/11 — the finale's
  trombone slots — and inherit a name stamped per SLOT. Cello 15 / Contrabass 16
  are right, so it is an off-by-three in the monotone DP over a reduced system.
  `slots.align` / `assign_slots`, not the movement reference and not the veto.
  **Owned by the `sad-austin-7e16e7` session as of 2026-09-06.**
- **Files:** `tools/omr/contextual.py`,
  `tools/omr/tests/test_contextual_ambiguity_uniqueness.py` (every test run RED
  with the guard removed),
  `benchmarks/omr-absent-instrument-veto-2026-09/probe/probe_ambiguous_cooccurrence.py`.

---

## 2026-09-05 — Scan: where the pipeline decides without a probability

- The clef session found a lot being lost because a staff's clef was either
  SELECTED or DISCARDED, with nothing between. This scans the rest of
  `tools/omr/` (57 modules, 31,346 lines) for the same shape and answers by
  taxonomy: [docs/handoff-probability-gates-2026-09-05.md](docs/handoff-probability-gates-2026-09-05.md).
  Sibling of the 2026-09-04 "detector was right, output was wrong" taxonomy —
  that one asks where a signal was read and lost, this one where a degree of
  belief was formed and thrown away.
- **Five classes**: (A) never formed — a boolean veto with no score behind it;
  (B) formed then quantised; (C) formed, kept, consumed by nobody; (D) used only
  as an exclusive evidence tier or a raw argmax; (E) all-or-nothing structural
  refusals.
- **Two headline Class-C findings.** `export.py` mentions `confidence` exactly
  once and that occurrence is a COMMENT — every detection confidence is
  discarded at the export boundary, and across the pipeline confidence reaches a
  decision at only four places. And the five internal-consistency checks compute
  a graded confidence nothing reads: only `rhythm_sum_warning` is consumed at
  all, as a boolean presence count for a UI percentage in
  `backend/modules/local_omr.py`.
- **Measured, not assumed** — probed 29 stored transcription JSONs for real
  firing rates. On one real scanned document (Breitkopf Brahms 1, 3 pages, 83
  staves) **85 warnings fire and all are inert**: 78 `rhythm_sum`, 4
  `time_signature_disagreement`, 2 `clef_register`, 1 `key_signature`.
  ⚠️ Volume is uneven and the doc says so: `measure_count_warning` fired ZERO
  times across all 29 files (corroborating majority-steering's 0-of-27-systems),
  while the high-volume check is the one carrying no confidence field at all.
- **Handed to the clef session**: `clef_correction` decides on range fit alone
  behind two hard `return None` cutoffs and never reads `clef_register_warning`
  (grep count 0), which fires on the same page dict from an independent
  direction and — crucially — needs no instrument label, the evidence that
  survives where 29 of 29 unresolved non-treble scan staves have no label
  printed at all.
- Ranked 7-item shortlist with blast radius per item, naming which harness can
  price each one and whether that harness can SEE it. Negatives recorded too, so
  the next pass does not re-walk them (the abstain-on-near-even-split rule, the
  pairwise dedupe structure, and `CV_CONFIDENCE = 0.99`, which looks like a fake
  probability and is a deliberate sentinel).
- ⚠️ **No arm was run** — the OMR weights are gitignored and absent from the
  container. Nothing in the document is a benchmark result, and it says so.

- ⚠️ **RECONCILED THE SAME DAY, and the scan was partly wrong.** Sean asked that
  nothing be built without consulting the other sessions first. Cross-session
  messaging turned out to be unavailable (no reachable peers across the
  cloud/bridge boundary; a test send failed), so the consultation was done by
  reading committed work — and `claude/staff-identity-layer-2026-09-05` had
  already run the experiment the scan's recommendations assume is worth running.
  It came back NEGATIVE: neither P(name) nor P(set) calibrates (ECE 0.1277 /
  0.1301, n=197), failing worst where a consumer would set its bar. Its
  pre-registered standard — an uncalibrated probability is worse than none —
  is adopted by the scan.
- The scan's `coverage`-into-`slots` item is **demoted** (same evidence family,
  same corpus) and its clef item **re-framed**: KC-3 showed `clef_correction`'s
  FILL path reaches 34 of 396 staves because it fires only where no clef was
  read, so the reachable question is the OVERRIDE gate, whose
  `sources.get(slot) == "label"` conjunct is unsatisfiable on scans. ⚠️ The
  "just swap the conjunct" framing was WITHDRAWN the same day on merging with
  Sean's own handoff, which carries held-out evidence that the label gate earns
  its keep; what survives is that `clef_register_warning` names no instrument
  and so does not carry that hazard — and that its REACH must be measured
  before its accuracy.
- Written at a path another agent can be pointed at:
  [docs/handoff-probability-gates-2026-09-05.md](docs/handoff-probability-gates-2026-09-05.md).

**Files touched:** `docs/handoff-probability-gates-2026-09-05.md` (new),
`docs/handoff-probability-gates-2026-09-05.md` (new),
`CLAUDE.md`, `PROJECT_BRIEF.md`, `version_memory.md`.

---

## 2026-09-05 — The last margin-label gap closed: a whole system's margin as one label

- The lexicon sweep's last open item — Beethoven 5's 17-staff margin resolving to
  *Piccolo*, Mahler 5's 19-staff margin to *Trombone* — was a reader/assignment
  fault, confirmed by re-reading the exact pages with the raw per-block Surya
  output surfaced for the first time. Both pages: Surya returns **exactly one
  OCR block for the whole crop**, every instrument name on the page glommed into
  one block, where a healthy read splits one block per staff.
- `_assign` was never wrong about WHICH staff the block's centroid landed
  nearest — the input it was handed was already garbage, and nothing recorded a
  block's own SIZE to say so. `_surya_worker._lines_with_boxes` now keeps each
  block's height (already had the polygon, wasn't reading its y-extent),
  threaded to `_assign`, which drops a block taller than half the SYSTEM's own
  tick span before the nearest-tick test rather than forcing it onto whichever
  staff it lands nearest. Scale-invariant on purpose: the ratio is to the crop's
  own span, not a pixel count.
- **Measured, not guessed**: both bad blocks sit at 1.04× the span (crop padding
  pushes them slightly past 1.0); all 17 blocks Surya correctly split on
  Boléro's own dense page — 16 of 19 staves correctly named, the SAME kind of
  system a runaway block would target — sit at 1.5–4.7%. A ~22× gap with the
  0.5 threshold in the middle of it.
- ⚠️ **The first regression test attempt passed whether the fix worked or not.**
  It asserted no returned label exceeded some LENGTH, but the real defect
  concatenates many instrument names into one long STRING specifically because
  the block spans many staves' worth of *text*, not just height — a single huge
  GLYPH is one character, tall without being long. Constructed a synthetic
  crop instead, asserted on staff ASSIGNMENT directly, and ran it red (gate
  disabled: `{0: 'Ob.', 2: 'X'}`) before green (gate on: `{0: 'Ob.'}`) to prove
  it exercises the mechanism.
- Full suite 2058 → **2059 passed, 0 failed**. Both known-bad pages now report
  no label (honest abstention) rather than a confident wrong instrument; the
  known-good Boléro page is byte-identical.
  [benchmarks/omr-margin-labels-blob-2026-09/FINDINGS.md](benchmarks/omr-margin-labels-blob-2026-09/FINDINGS.md).

---

## 2026-09-04 — acting on the split: hairpins and a fermata reach the file, and the arc verdict

Worked the three items the reading/translation split identified.

**1a. HAIRPINS — the ninth export gap, closed on the export side.** `score_translation` priced
what `KNOWN_GAPS` said could not be priced: 9 read across three works, every one discarded,
against 17 `<wedge>` of truth. `export.measure_wedges` emits each as the SPAN it is (opening +
`stop`, with a `number` so overlapping spans stay pairable), through `measure_directions` — the
ONE place both emitters ask what a measure carries; slurs live at four call sites and this does
not add a fifth. **0 → 18 wedges against 17 of truth; Tchaikovsky 6 exact at 6/6.** Control: only
the three works with hairpins change, the other eight are BYTE-IDENTICAL, and the diff is purely
additive. ⚠️ **Costs +11 OMR-NED edits and ships anyway**, but unlike the articulations precedent
the cause is diagnosed: Tchaikovsky (exact detection) IMPROVES −3, and Mahler pays +12 for two
known mechanisms — a hairpin crossing a barline exported as two, and one landing on the staff
below its own.

**1b. THE LOST FERMATA — found by arithmetic, not by reading code.** Beethoven 5 detected 36,
truth 36, exported 35; `export_coverage` cannot see that (it fires only on truth-some/ours-zero).
One query localised it: every part has a fermata at m2 and m5 except P7. Its `restWhole` does not
become an event, so that bar takes the eventless branch — the SAME branch as the directions, one
layer down, and `annotate_fermatas` already documents that an orchestral fermata is usually over
a whole-bar REST. Now **36 of 36**, and it **IMPROVES** the metric: 0.0595 → 0.0556, −5 edits.

**2. ARCS — the verdict, and a lever I nearly rebuilt.** ⚠️ `00b68e24` on
`claude/export-accents-arcs` already built the tie/slur position-grammar veto, measured it on
BOTH families and shipped it default-off (engraved neutral, scan REFUSED). Found by
`git log --all -S` before starting. The reading score adds why it could not have paid: a family
whose F1 climbs with the centre tolerance is FOUND AND LOOSELY PLACED, not missed. **Ties
0.260 → 0.504** at 2 spaces (mostly there); **slurs 0.518 → 0.631**, barely moving — real
absences, 16 of 40 with no arc within TWO spaces while the 24 found sit at a median 0.09. So
slurs are a DETECTION gap, ties a LOCALISATION gap, and neither is a labelling gap. ⚠️ Also
corrected: yesterday's "24 slur arcs lost to `beam`" was a large CV beam box whose CENTRE fell
within tolerance, not a class confusion.

**3. DYNAMICS RE-ATTRIBUTION — hold stands, case stronger.** With hairpins now exported their
placement is measurable, and it is the same mechanism: **three of Mahler's four hairpins are
filed under staff 18 and stand in staff 17's band**, which is half the +12 above. A second symbol
family the rule would fix. ⚠️ It does not change the verdict — the blocker was never the engraved
case (already positive, 52 → 83 staves exact) but that the scan arm cannot see attribution at
all: 7 of 11 pages abstain on the staff→part join, and resolving them needs hand-verified
`staves[].parts` rows. Human input, not another measurement.

---

## 2026-09-04 — reading and reproduction, measured apart (an exact page truth, for free)

Sean asked whether we test the ability to READ a page or to REPRODUCE one, and whether there is
a way to know exactly what is on a page. There is, for pages we render, and it costs nothing:
Verovio draws MusicXML directly and with `svgBoundingBoxes` emits a `<rect>` per notation object
in the same frame as the glyph, plus every glyph's SMuFL codepoint. Image and inventory from one
act, no labeling. `tools/omr/page_truth.py` + `score_reading.py` + `score_translation.py`,
harness and findings in `benchmarks/omr-reading-vs-reproduction-2026-09/`.

- ⚠️ **A PAGE TRUTH IS NOT AN ENCODING TRUTH, and the gap is the point.** Brahms fixture against
  the file it was rendered from: dynamics 19 glyphs vs 19 `<dynamics>` (agree), G clefs **28**
  vs **14** `<sign>G</sign>`, slurs **82 arcs** vs **164 `<slur>` tags**. A clef is printed at
  every system and declared once; MusicXML writes a slur at each end.
- **STAGE 1 — reading F1 0.919** over 11 engraved works / 3220 scoreable symbols, beside OMR-NED
  0.1306 on the same works. The decomposition is the value: **noteheads 0.999 (856 of 856)**,
  rests 0.993, time-sig digits 0.997, flags 0.992, clefs 0.969. **So the engraved residual is
  NOT a failure to see notes.** It is ties **0.260**, slurs **0.518** (24 arcs lost to `beam`,
  the only real class confusion), and dynamic letters **0.552** at precision 0.421 — the same
  over-emission `omr-dynamics-band-2026-09` measured from the other end.
- ⚠️⚠️ **A NEAR-MISS, CAUGHT BY AN EXISTING NUMBER RATHER THAN BY THE NEW TOOL.** `accidental`
  scored recall 0.257 and was about to be written up as the largest reading gap. It is not a
  pipeline result: **Verovio draws one accidental per `<alter>`, not per `<accidental>`** —
  Brahms 1 has 54 `<accidental>` and 149 `<alter>` and it drew 149; Beethoven 5 has ZERO
  `<accidental>` and 13 `<alter>` and it drew 13. `<alter>` is the SOUNDING alteration, which a
  key signature already supplies, so the render carries accidentals no engraver would print. The
  tell was a contradiction with OMR-NED's `wrong pitch`, which is ZERO on these works and cannot
  be if a reader is missing three quarters of the accidentals. `page_truth.render_fidelity` now
  measures the disagreement per work and declares the family unreliable; `score_reading` marks it
  `(RENDER)` and excludes it. Including it gave 0.898; excluding it, **0.919**.
- **STAGE 2 — the funnel prices the open ninth export gap.** `wedge` sat in `KNOWN_GAPS` as
  un-priceable from that inventory. It is now: **9 hairpins read across three works and every one
  discarded** (Mahler 5 4-of-6, Tchaikovsky 6 3-of-6, Brahms 4 2-of-5) — half reading, half
  export, and the export half is free. Plus a **NEW** one nothing else can see: Beethoven 5
  detects 36 fermatas, truth has 36, **35** reach the file. `export_coverage` fires only on the
  categorical case (truth some, ours zero), so 35-of-36 was invisible.
- ⚠️ **The stages read different images on purpose** — stage 1 a Verovio render whose ink is
  known, stage 2 the LilyPond fixtures the headline uses — so their per-family counts are NOT
  comparable to each other. ⚠️ **Neither says anything about scans**; no public symbol-level
  ground truth for real printed scans exists to borrow (DeepScoresV2 rendered, MUSCIMA++
  handwritten).
- **Controls**: matched on CENTRES not IoU (learned boxes vs exact ones would measure box style),
  and pooled F1 moves only 0.846→0.876 across 0.25–1.5 spaces of tolerance; re-rendered at
  600 dpi (45 px/space vs 22) Brahms 1 goes 0.854→0.868 and Tchaikovsky 4 0.787→0.789, so the
  figure is not a resolution artefact.
- ⚠️ **TWO FRAME ERRORS IT FOUND IN ITSELF, both caught the same way — the symbol COUNTS agreed
  almost exactly while NOTHING matched positionally, which is the signature of a coordinate error
  and never of a recognition result.** (1) Verovio wraps the page in `<g class="page-margin"
  transform="translate(500,500)">`; missing it put the whole truth 62.5 px off against a 22.5 px
  staff space — noteheads 259 vs 259, matched ZERO at every tolerance. (2) A glyph's anchor is
  not its centre — SMuFL puts a flat's origin at the staff position it alters — so a synthesised
  square box scored a correctly read key signature at **F1 0.078**; calibrating each glyph's box
  from Verovio's own single-glyph rects took it to **0.990**. A third was avoided by checking:
  reading extents off the `<defs>` outlines is wrong because those paths use RELATIVE curve
  commands, which put noteheads 0.66 spaces right of Verovio's own rect for the same glyph.
- Coordinate chain verified end to end rather than assumed: librsvg maps CSS px to PDF pt at
  72/96 and a pt rasterises at dpi/72, so image px = css px x dpi/96 — exact at both 300 and 600.

---

## 2026-09-04 — a bar we found nothing in now keeps its marks (the predicted bug, fixed)

`export.py`'s whole-measure-rest branch never calls `_mxl_voice_events` — the only other
`<direction>` emitter — so `measure_directions()` was computed, assigned to `_dyn`, and never
used. BOTH MusicXML measure emitters had it, identically. Fixed with `_mxl_directions_only`,
called from both: marks go in x order at the head of the bar, ahead of the rest, because a
`<direction>` carries no duration and applies where it sits.

- ⚠️ **This is the bug CLAUDE.md has been carrying as a PREDICTION** — that the 11-work engraved
  benchmark provably cannot see it (0 triggering bars, measured both ways) and that a SCANNED
  work would be where it finally triggers, because a staff genuinely rests through a marked bar
  and the detector finds nothing in it. It does: **14 dynamics on scans, 0 on the engraved
  eleven**, and the attribution was exact before the fix (`words formed − words in an eventless
  measure == words exported`, all 11 pages, to the mark) and is exact after it (376 formed → 376
  exported).
- **CONTROL: the eleven engraved works export BYTE-IDENTICALLY.** Which is the same fact as the
  benchmark not seeing the bug — so it cannot guard the repair either.
  `TestEventlessMeasureKeepsItsMarks` does (8 tests), including a **source-level anti-drift test
  asserting BOTH MusicXML emitters call it**, verified to fail when either call site is removed.
  The LilyPond branch is deliberately excluded from that guard.
- ⚠️ **IT MAKES SCAN OMR-NED SLIGHTLY WORSE AND SHIPPED ANYWAY.** Mahler p2 0.7122 → 0.7148
  (+5 edits), Beethoven 984073-p1 0.6925 → 0.6949 (+5), Mahler p3 0.8921 → **0.8916** (+3),
  Beethoven 984073-p2 0.8859 → 0.8860 (+3). The marks are not wrong — a spot check shows a
  recovered `f` on a bar that is otherwise a whole-measure rest, the predicted shape exactly.
  These pages score 0.69–0.89, i.e. their bars barely pair, so a correct symbol added to a bar
  already charged delete-whole-plus-insert-whole raises a charge being levied whole. **Same call
  as the articulations fix** (−122 across works that segment, +219 on boulanger alone, shipped
  with the counter-argument beside it).
- ⚠️ Found on the way, NOT fixed: the **LilyPond** exporter never calls `measure_directions` at
  all, so it drops dynamics on *every* measure. A wider gap, and invisible to `export_coverage`,
  which compares MusicXML.
- Landed on an isolated branch while another session had uncommitted `export.py` work in flight
  (cross-staff ARC attribution, hunks at 567/1337/2435) — different concern, non-overlapping
  regions; checked across all 84 worktrees before touching the file.

---

## 2026-09-04 — dynamics letters: a placement band exists, and re-attribution works on engravings only

Sean asked whether dynamics letters should be read the way clefs are. Measured, not reasoned
about: `benchmarks/omr-dynamics-band-2026-09/`.

**Half of the clef approach transfers, and not the famous half.** Geometry-instead-of-
classification does NOT apply — alto and tenor are one glyph on two lines, but a `p` is a `p` at
any height, and the horizontal assembly it does need (`f`+`f` → `ff`) already exists in
`export.measure_dynamics`. The clef LOCATOR does not apply either: it exists because the model
is blind to clefs on scans, and the detector is not blind to dynamics — 1246 letters over 18
pages. What transfers is **POSITION BEFORE SHAPE**, and `measure_dynamics` uses no vertical
information at all.

- **The band is real and holds across 9 publishers** (Breitkopf, Durand, Eulenburg, Jurgenson,
  Litolff, Novello, Peters, Simrock, Universal): 73% of letters stand in their own staff's band,
  24% in the band of the staff **immediately above — distance exactly 1, no exceptions**, which
  is the cell padding confirming itself. Pooled widest empty interval **−3.04 .. −0.52 spaces**,
  and the lower edge is a **plateau** (−1.5 .. +0.25 changes nothing on either scored arm).
- ⚠️ **A GATE IS THE WRONG FIX**; an out-of-band letter is usually not junk but the neighbour's
  ink through this cell's padding, and deleting it loses the mark. **83% of re-attributed letters
  are the target staff's SOLE evidence** — because `_dedupe_cross_staff_detections` already
  removed the twin BY DISTANCE and kept the lower staff's copy, the same failure the ledger-ladder
  work found for noteheads. So the fix belongs in that function as another evidence tier, not in
  a filter after it.
- **Engraved (canonical 11): re-attribution is a clear win** — over-emission 1.19 → 1.04, staves
  exact by word **52 → 83 of 107**, no work worse.
- ⚠️⚠️ **SCANS: IT DOES NOTHING — 16 → 16 staves exact by word** (11 pages, 5 publishers,
  hand-verified windows). The engraved result does not carry, and the table says why: on real
  scans we **under**-emit (376 words against 491, 0.77), so the dominant dynamics error there is
  a mark never found, not a mark on the wrong staff. Measured, **NOT shipped** — the next step is
  why scans under-emit, not a wider band sweep.
- ⚠️ **THEN ANSWERED, same day (`--funnel`): "reads them but doesn't write them" is REAL and is
  the MINORITY.** Of the 129-mark scan shortfall: **14 are computed and thrown away** by the
  eventless-measure branch — `measure_directions()` is called, assigned to `_dyn`, and never
  used, in BOTH of `export.py`'s measure emitters. This is the bug CLAUDE.md records the 11-work
  engraved benchmark cannot see, and which it predicted a SCANNED work would finally trigger:
  **it does — 14 on scans against 0 on the engraved eleven**, and the attribution is exact
  (`words formed − words in an eventless measure == words exported` on all 11 pages, to the
  mark). A further ≤31 are the same family one step earlier: 49 detected letters in runs that
  spell no dynamic, discarded whole, 15 of them a lone `s` (an `sf` whose `f` was missed). The
  rest were never read — and **137 of the shortfall is the two Beethoven 5 p.2 scans alone**;
  across the other nine pages we emit 191 against a truth of 183, over-emitting slightly exactly
  like the engraved arm. ⚠️ So "scans under-emit" was too broad a claim and is corrected here.
  NOT fixed — the eventless-measure branch is a two-site change in `export.py` and is left for
  the session working that file.
- ⚠️ Refuted: **confidence** as a filter. Priced as the trade rather than by comparing medians —
  removing half the unattributable letters costs **233 of 911** good ones.
- ⚠️ The probe restates `measure_dynamics`'s joining rule in page pixels (re-attribution moves a
  letter into a staff whose cell it was never cut into) and **cross-checks itself against the
  real function on every page**. That check earned its keep: the first version compared box
  CENTRES where the exporter compares LEFT and TOP edges and disagreed on 4 of 11 scanned pages.
  A second self-caught flaw: the dedupe keyed on distance could merge the two letters of one
  `ff`, which a word COUNT cannot see — fixed by keying on the source cell, and a word-CONTENT
  check added, which cut the engraved claim from 92/107 to a truthful 83/107.

---

## 2026-09-04 — the class space spells 32 glyphs twice, and consumers read one spelling

Asked whether dynamics letters should be read the way clefs are. Looking for the dynamics
consumers turned up a separate, live fault first: the 208-class vocabulary is **two annotation
sets concatenated** — fine at ids 0-135 (`dynamicF`, `articStaccatoAbove`, `tupletBracket`),
coarse at 136-207 (`dynamicLetterF`, `articulationStaccato`, `tupleBracket`). Forty classes
carry the SAME name at both ids so a name lookup sees both; **thirty-two do not**, and every
consumer in this pipeline was written against the fine spelling.

- A detection at id 192 was a forte `export._DYNAMIC_LETTER` could not spell — the letter never
  joined a word and the mark was dropped with no warning anywhere. The same fault as
  `fingering3`/`tuplet3`. Confirmed **mechanically**, by asking each class-name consumer what it
  returns for both spellings, not by reading: 6 dynamic letters, 5 articulations, `tuple`/
  `tupleBracket`, `arpeggio`/`legerLine`.
- ⚠️ **It cost nothing when found** — the coarse block fires **zero** times across 3 engraved
  fixtures and 29 scanned pages of 9 publishers. What makes it live is the LABELING side: 26 of
  the hollow campaign's hand-drawn boxes are classed `dynamicLetterF`/`P`/`S` and
  `data/user-labeled/catalog.yaml` carries the coarse spelling at ids 190-195, so the next
  fine-tune trains ids the exporter cannot read.
- Renamed at the ONE place the model's own `names` are read (`yolo_detector._ensure_loaded`), so
  every consumer downstream sees a single spelling and no call site knows.
- ⚠️ **Only 11 EXACT TWINS are renamed, and the abstentions are asserted rather than merely
  documented.** A coarser name is not a synonym: `numeral4` is NOT `timeSig4` (one numeral class
  covers meters, tuplet digits, fingerings and measure numbers — and CLAUDE.md records five
  spurious `timeSig4` on barline fragments shipping a 2/4 page as common time, 390 bar-check
  failures against 164 for no meter at all); `articulationStaccato` states no SIDE, which
  `_attach_articulations_in_cell` requires geometry to agree with; `tuple` no NUMBER; `clefC` no
  LINE, and already resolves to alto by documented design with `resolve_clef` measuring the line
  anyway. Those 21 sit in `COARSER_THAN_CANONICAL` with what closing each would take, and
  `unaccounted()` fails the suite on any name in neither table — so a checkpoint with a wider
  class space is a loud failure, not a silent drop.
- One consumer spelling fix beside it: `noteheadFullSmall` (`full` is the coarse spelling of
  `black`) reached `rhythm._NOTEHEAD_INTRINSIC` with a category and NO duration. Fixed as a
  prefix, not a rename — it states no staff position and does not need one, since pitch comes
  from the note's y against the grid.
- **CONTROL**: re-transcribing the same scanned page across the change leaves every musical field
  identical — same detections, classes, boxes, structure; the only differing leaves in the whole
  JSON are the four wall-clock timings. Suite 2010 passed / 4 skipped.
## 2026-09-05 — Choir-grouping cues SHIPPED default-ON; Bach re-admitted to the pool

Sean's coupled call. `OMR_CHOIR_GROUPING` defaults ON
(`system_grouping._choir_grouping_enabled`, opt-out 0/false/no/off): cue B
(pair-local left-edge merge) + cue C (grouped-system open-score guard),
diagnosed and priced on `claude/bach-choir-grouping` — Bach 6→2 systems
[12,12], 122→11 cells vs true 10, row 0.9241→0.8152; byte-identical on the
10 pooled scan rows, the 11-work engraved benchmark, and the boulanger
canary; 969-page probe hand-adjudicated 10/10 changed pages toward truth, 0
false merges. The Bach row's `pooled` flag flips back to true in the same
event — a BENCHMARK BOUNDARY: the pool is 11 rows under the composed
default config (tilt ON × choir ON) from the re-stamp onward, and no pooled
figure crosses the boundary. The re-stamp run (one fresh default-config
pass, all 11 rows, graft weights) stamps the new canonical figure; recorded
in the addendum beside WIDENED_BASELINE_2026-09-04.md when it lands.

## 2026-09-04 — Cell-grid localization SHIPPED default-ON (the tilt fix)

Sean's call, same day the widened gate priced it: `OMR_CELL_LINE_TRACE` now
defaults ON (`measure_extractor._cell_line_trace_enabled`, opt-out via
`0/false/no/off`). Deployed default-config scan baseline moves to the
flag-on arm's figures: **pooled 0.8345 / 28849 over the 10-row pool** (was
0.8387 / 29082 flag-off; same graft weights — the flag is the only
variable, and the harness is byte-deterministic). Engraved figures
unchanged (no-op by construction, byte-identical A/B). Flag tests updated
to pin the new default; the flag-OFF contract every labeled batch depends
on (grid = `staff.line_ys - y0`) is still pinned via explicit `0`. Blast
radius recorded in the knobs table (key-sig slot-fit interaction, net −15;
+2..+7 noise on three low-exposure rows). Evidence:
`benchmarks/omr-cell-grid-tilt-2026-09/WIDENED_PRICING_2026-09-04.md`.

## 2026-09-04 — The widened scan gate prices the tilt fix: −233 edits, on the exposure

The measured-but-unshipped `OMR_CELL_LINE_TRACE` (cell-grid localization, the
rigid comb) was A/B'd on the widened 11-row scan gate — the first tree holding
both the gate and the flag (`claude/tilt-pricing-widened` = `0487be1f` merged
with `claude/tilt-crosscheck`). The old benchmark's null was the corpus: the
widened pool carries **8.6%** of cells past the parity-flip line (was 0.4%),
and the flag is worth **pooled 0.8387 → 0.8345, −233 edits**, −217 of them on
exactly the three tilted rows, zero-exposure row unchanged to the edit,
engraved control byte-identical, exact-pitch recall +4.8pts on the most
exposed edition. Verdict + tables:
`benchmarks/omr-cell-grid-tilt-2026-09/WIDENED_PRICING_2026-09-04.md` —
recommendation is default-ON with no domain gating; the flag stays OFF until
Sean decides. The named ship prerequisite also landed (`be884ff8`):
`recut_cells.frame_mismatch` compares the frame's own (unlocalized) grid,
accepts either dialect a manifest can speak, and `_nostaff.png` — which IS
grid-derived — is re-erased on the manifest's authority, all pinned by three
tests on a page that provably localizes.

---

## 2026-09-04 — Scan gate: widened 5 → 11 rows; Bach excluded from the pool

Six Sean-verified rows promoted (commit `84a5ccac`; drafting on branch
`claude/scan-gate-rows`, stories in scan-e2e VERIFICATION.md), the first
widened baselines measured for both checkpoints (merge `04eb8050`,
WIDENED_BASELINE_2026-09-04.md — the ship decision HOLDS on the deeper
gate), and then, at Sean's decision, the Bach stress row was excluded from
the default pooled figure via a new `"pooled": false` row flag in works.json
+ scan_eval.py support (stress rows run and report per-row, never pool).
Rationale: its OMR-NED measures page-structure parsing (122 detected
measures vs 10) and whole-measure amplification there charges recognition
improvements as regressions — the Boulanger call, repeated. **Canonical
scan-gate baselines: prior-prod (hollow-ft) 0.8457 / 29081; production
(hollow-graft-shift09) 0.8387 / 29082, over 10 pooled rows.** All pre-widening
figures (0.7517 / 0.7493) are 5-row history; no comparison crosses either
boundary. Validation: the pool-exclusion logic re-scored the committed
widened-graft fixtures and reproduced the recorded 10-row figures.

## 2026-09-04 — Design note: position grammar over the mark alphabet

Sean's observation (ties/slurs, then accents/hairpins and tenuto/ledger
lines) generalized into a written principle:
[docs/position-grammar-confusables-2026-09-04.md](docs/position-grammar-confusables-2026-09-04.md).
Engraved music reuses a tiny mark alphabet — dot, stroke, wedge, arc, bowl,
digit — and identity is position grammar over the staff lattice, not shape;
the detector proposes ink events with a class PRIOR, a downstream layer
assigns or vetoes identity. Nine shipped precedents cited with their numbers;
six design rules (class space stays 208 / families closed under
confusability / veto-impossible-first / anchors before grammar /
matches-nothing-is-an-output / never tune positionally on one edition); an
inventory of the confusable families with measured discriminators; and the
next six opportunities each tied to an existing measured hook. First
consumer: the round-6 specialist/labeling campaign via family closures and
adjudication-batch shape.

## 2026-09-04 — Scan weights: the round-5 head-graft candidate SHIPPED

**Why:** rounds 3–5 of the scan-weights campaign established that fine-tuning
on the ~750-cell scan-label corpus deletes whole classes — tie/slur/beam/
augmentationDot/accidentalFlat/restWhole/ledgerLine go to exactly zero — under
every method tried (eleven arms: the ship's own recipe, no-warmup, low LR,
freeze, plain controls, teacher rehearsal/distillation at two confidences).
The fix that survived is surgery, not training: keep only the hollow
fine-tune's seven notehead-class head rows (`model.22.cv3.{0,1,2}.2` is the
only per-class place in a YOLOv8 head), graft them onto production, and bake a
per-class confidence floor into those rows' biases (`--bias-shift 0.9` ≈
raising only those classes' threshold 0.25 → 0.45, since the pipeline has one
global threshold).

**What:** `transcribe.DEFAULT_WEIGHTS` — the scan side of weight routing —
now points at `deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`
(byte-identical to `omr-weights/round5-merged/d25e0_graftprod_shift0.9.pt`,
sha256 `2cb6eb3e…3126`; copies in both `omr-weights/` and
`tools/omr/training/data/weights/`). The engraved side (`ENGRAVED_WEIGHTS`)
is untouched. First checkpoint in three rounds to beat the 09-03 production
on every measure of all three gate axes: half-noteheads 27 → 31,
pitch+duration recall 0.4354 → 0.5102, exact 0.5646 → 0.5782, dense notehead
recall 0.941 → 1.000, scan-e2e pooled OMR-NED 0.7517 → 0.7493 with 4 of 5
rows improving, 28 classes held with 0 collapsed; element counts move toward
truth on ties (60 → 97 of 271) and rests (577 → 589 of 972). The ship was
gated on a fresh determinism probe: the scan-e2e harness is byte-deterministic
(identical outputs across runs, worktrees and days — noise floor exactly
0.0000), so the delta is a real property of the weights. Sean approved the
ship 2026-09-04.

**Records:** `benchmarks/omr-labeling-survey-2026-09/ROUND5_METHOD_2026-09-04.md`
(lands with branch `claude/scan-weights-round4-continue-074940`) and
`benchmarks/omr-scan-e2e-2026-09/DETERMINISM_2026-09-04.md` (branch
`claude/scan-e2e-determinism`). The prior scan production
(`deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt`) stays on disk under its own
name — in-flight benchmark branches that pin "production" by explicit path
are unaffected, and their recorded 0.7517 baseline still names that file. The
web-app container picks the repoint up on its next
`docker compose build backend`.

---
## 2026-09-04 — round 5: the fine-tune deletes CLASSES, and the fix is head surgery

- **"Every fine-tune degrades the base" turned out to mean whole class families going to
  exactly zero.** Not suppression and not a threshold artifact — every fine-tune's MEDIAN
  CONFIDENCE IS HIGHER than production's (0.669-0.698 vs 0.604) while raw detections fall
  3204 → 806-1365. tie 249→0, slur 184→0, beam 188→0, augmentationDot 150→0,
  accidentalFlat 80→0, restWhole 396→0, ledgerLine 288→14, with noteheads holding at
  80-100%. The corpus is the mechanism: 3871 human boxes contain **0 `beam` and 5
  `ledgerLine`**, and only 164 of 591 cells ever saw a rich palette.
- ⚠️ **`beam` and `ledgerLine` are CONSUMED by the pipeline**, against what the labeling
  policy assumed. `rhythm.resolve_rhythms_for_cell` keeps a YOLO beam wherever no CV beam
  overlaps (worth 0.1917 → 0.1861) and the ledger-ladder arbitration reads `ledgerLine`
  detections directly (0.1506 → 0.1431). Both rules were dead on every round-3/4/5
  candidate, silently, because neither has a test that fails when its input vanishes.
  That is now gate axis 3.
- ⚠️ **`restWhole` was nearly exempted from that gate on prose.** 396 over five pages
  reads as absurd and the round-2 audit names it a slur-arc false-positive mode. Counted:
  those pages carry **801 resting bars** and production reads 108/88/11/96/93 — under the
  printed count on every page. The exemption is gone.
- **ELEVEN METHOD ARMS, ALL DEAD.** The 896 ship's recipe on the new labels (the control
  round 4 never ran), warmup off, warmup off + lr 1e-5, low LR, a frozen backbone, a
  matched no-teacher control, and teacher rehearsal in both scopes at conf 0.50 and 0.25.
  The pre-hollow BASE loses nothing, so it is caused by the fine-tune, not inherited.
  **More labeling will not fix it** — round 4 tested that by hand (3%) and round 5 tested
  the perfect version with 3417 teacher boxes (nothing).
- **The fix is surgery.** A YOLOv8 head is per-class in exactly one place —
  `model.22.cv3.{0,1,2}.2`, one weight row and one bias per class — so
  `merge_class_head.py` restores the base's rows for classes the corpus does not teach,
  and `--bias-shift` bakes a per-class confidence floor into the rows that stay. Seconds
  on a Mac, no GPU.
- **`d25e0_graftprod_shift0.9.pt` beats production on every measure of ALL THREE AXES** —
  half-noteheads 27 → 31, pitch+duration recall 0.4354 → 0.5102, exact 0.5646 → 0.5782,
  step 0.6463 → 0.6939, dense notehead recall 0.941 → 1.000, pooled scan-e2e OMR-NED
  0.7517 → **0.7493**, class space 28 with 0 collapsed. First candidate in three rounds
  to clear all three. **Not shipped — the live repoint is Sean's call.**
- ⚠️ **Shift 1.5 has the best axis-2 number (0.7420) and is the worst checkpoint in the
  table** — 17 half-noteheads against production's 27, exact recall below production's.
  The floor went past the false positives into the true ones. Read alone, axis 2 would
  have shipped it.
- Rig faults worth not repeating: **v2/v3/v4 store cell images as SYMLINKS** (a `cp -R`
  into a cloud tarball ships 101 of 136 dense cells as dangling links, skipped as
  "corrupt image/label"); never overwrite a running bash script; the 208-class space has
  **40 duplicated names**; 2× dense oversampling is now 43/57 hollow-MAJORITY and the
  ship's 69/31 ratio needs **6×**.
- GPU spend **$0.37**, box destroyed. Full account:
  `benchmarks/omr-labeling-survey-2026-09/ROUND5_METHOD_2026-09-04.md`; handoff
  `docs/handoff-2026-09-04-round5-class-collapse.md`.
---

## 2026-09-03 — a third audit check: edge fragments live in the training corpus, no image needed

Two `notehead*` labels found live in **v3-2026-06-09-mahler5** and **v4-2026-06-10-la-mer** —
both in `catalog-versions.txt`, both in the round-4 training run at the time — at 0.52sp and
0.54sp tall, inside the measured clipped-fragment band (0.29–0.56sp, from
`transcribe._drop_clipped_notehead_fragments`) and under the genuine-notehead floor (0.60+).
That discriminator was measured once, on the DETECTOR's output, and had never been applied to
hand-drawn labels — which see the identical ambiguous ink.

- ⚠️ **Height alone reads "rest"; WHERE in the cell is the fact that settles it.** A first pass
  measured height only and concluded both were rests. Rendered crops (both sessions,
  independently) show the labeled box capturing only a thin sliver at the cell's own TOP edge,
  of a much larger shape that belongs to the staff ABOVE — not a symbol in this measure at all.
  Likely correction: delete, not relabel. Sean's call — the cells are the reference corpus.
- **Shipped as the auditor's third check**, needing no image at all (manifest geometry only:
  `cell_canonical_h`, staff lines, the label's own bbox) — the first of the three that reaches
  the four `hollow2-2026-09` batches whose `cells/` was never re-cut on this machine.
  ⚠️ **The edge tolerance is NOT the original 1px** (that only holds for a model's box, which is
  pixel-flush with the crop cut) — a hand-drawn box leaves 0.07–0.28sp of margin around the
  visible sliver, so the check uses `CELL_EDGE_TOLERANCE_SPACES = 0.5`.
- **Validated exactly like the other two**: finds the 2 known cases and nothing else on their
  batches; run over the full campaign (1666 labels, 15 batches, 8 never part of this tool's
  development) it finds the SAME two and adds **zero** false positives, including the corrected
  Brahms batch.
- Credit: scanned-weights session, for finding the two live cells and for the missing
  WHERE-in-the-cell field that corrected their own first (height-only) read.

## 2026-09-03 — the ledger-zone auditor's raw flag rate is an UPPER BOUND, not the defect rate

The scanned-weights session ran the auditor on Simrock/Dvořák 9 (110 cells, labeled entirely
after the tool existed — a genuine out-of-sample test) and reported it flagged 7 of 102
ledger-zone labels (6.9%, matching Brahms). Adjudicated by hand: 6 false positives, 1 real —
**true rate ~0.9%, an order of magnitude below the raw flag**. The one real error was worth
having; nobody would have looked for it otherwise.

- **The false-positive mechanism, independently reproduced on the actual pixels**: a printed
  ledger line survives staff-line removal and print-merges into the SAME connected component
  as the notehead beside it, pulling `blob_centre`'s centroid toward the rung by up to a full
  half-step — enough to flip the reported parity. Confirmed by rendering cells with the exact
  known step positions overlaid (no algorithm, just pixels against arithmetic) — the same
  standard the 6 Brahms corrections were already held to.
- **Five candidate fixes were tried against BOTH the Brahms corrections and the Simrock false
  positives; none generalises.** The literal fix as proposed (filter rows by local ink-run vs.
  a multiple of box width) resolves Simrock 4/4 and breaks Brahms 0/6 — traced to WHY: it only
  has room to detect the rung's excess where the human's box carries generous padding around
  the head, and that convention differs by batch/labeler with no record of which is which.
  A width-based reject flag looks clean on the 4 known Simrock false positives but also flags
  40 of Brahms's 76 ledger-zone labels, all independently uncontested — width alone does not
  discriminate. Numbers for all five in `LEDGER_ZONE_LABEL_AUDIT_2026-09-03.md`.
- **Shipped: `blob_centre` now returns the winning component's height/width in staff spaces**,
  printed alongside every parity suspect — context for a human, explicitly NOT a filter or a
  reweighting (no decision logic changed; the corrected Brahms batch still reports 0 suspects).
- **Standing recommendation, now on two independent adjudications**: every candidate needs a
  human looking at the actual ink against the known staff/ledger positions. Read a raw flag
  rate as an upper bound on the true rate, not the rate itself, when the campaign-wide 19
  parity candidates are eventually adjudicated.

## 2026-09-03 — auditing the labels: ledger-zone parity and shape-vs-class

Sean's 49-cell completion pass was audited before it went to training; 7 labels were corrected
(committed with the labels in `4003743`). The two checks that found them are now a tool,
`benchmarks/omr-snap-ledger-2026-09/audit_ledger_zone_labels.py`, because neither is covered by
the inside-staff parity auditor and both generalise.

- **Ledger-zone parity — measure the INK, never the BOX.** Out-of-staff noteheads are where the
  click-to-box snap extrapolates the grid past the staff. Brahms: **6 suspect of 76 ledger-zone
  labels (~8%)** against **0** inside-staff parity errors. ⚠️ A click-placed box inherits the
  slot the snap chose, so its centre is biased toward the grid that placed it — the
  scanned-weights session checked three of these at box centres, read the opposite parity on
  two, and was wrong on both; rendering the cells with the grid drawn showed a printed line
  through each head. Ink inside the HUMAN's box says the human is always right, ink inside the
  PRE-FILL's box says the pre-fill is always right; only the blob on `*_nostaff.png` is
  evidence. (Same trap already recorded from the snap-ledger work — and walked into anyway.)
- **Shape vs class — a parity audit is blind to a wrong KIND.** The whole rest labeled
  `noteheadBlackInSpace` measured **2.13 × 0.72 spaces, aspect 2.97:1** against a median black
  notehead of **1.19 × 1.00, 1.19:1** (n=189), and sits INSIDE the staff, so no parity auditor
  could reach it. Discriminator credit: the scanned-weights session.
- **Validated both ways**: run on the pre-correction verdicts the tool reproduces exactly the 7
  hand-made corrections (6 parity + 1 shape); on the corrected ones, 0.
- **Campaign-wide (1666 human labels, 275 ledger-zone): 19 parity + 3 shape CANDIDATES**, i.e.
  **6.9% of ledger-zone labels** — corroborating the Brahms 8% on eight batches the method was
  never tuned on. ⚠️ Candidates for a human, not corrections: the tool writes nothing, and
  `box_is_Npx_from_ink` is the row-level sanity check (a large value means the blob found may
  not be the labeled glyph — `beet5-p6-sys0-s8-m13` at 106px is the weakest row).
- ⚠️ **Run it from the MAIN checkout.** `cells/*.png` are gitignored, so from a worktree every
  cell abstains — the same trap that makes `verdicts_to_yolo_labels` silently report 0 classes.

## 2026-09-03 — Phase C ANSWERED: pre-filled boxes are a queue, not labels

Sean labeled **49 cells completely and blind** in one sitting — the 25 pre-registered plus 24
more. The pre-registered analysis is the committed one and it is negative.

- **Pre-registered 25: exact 0.838, `labels` tier 0.849** over 74 boxes. Other 24 (also
  out-of-sample, not pre-registered): 1.000 over 67. **Pooled out-of-sample 0.915 over 141.**
  In-sample six, where the tiers were fitted: 0.961 / labels 1.000. The bar was set in advance
  at ≳0.97; every honest reading is under it, so **the queue reading stands — now on
  out-of-sample evidence rather than caution.** The in-sample 1.000 was six dense cells
  describing themselves.
- ⚠️ **The Phase A admission tiers were fitted to those six cells' error MODES, and a random
  sample fails differently** — every policy lands 0.815–0.859 because the signals never fire:
  `near` 0 on all 12 errors, `parity_ok` 1 on 10, `small` 0 on 11. Nothing for a confidence
  band to separate. This is what pre-registration is for.
- **The 12 errors:** 6 line/space flips where the box centre sits 23–51 px (¼–½ staff space)
  off the hand-drawn box — both detector and reference name the position from a MISPLACED box
  while the human labels the ink; **4 rest VALUE disagreements** (`restQuarter` vs the human's
  `rest8th` at IoU 0.65–0.82 — same glyph, reference duration vs printed); 1 whole-rest read as
  a notehead; 1 unmatched grace-sized box. **Rests are the weak class and were invisible
  before**: out-of-sample noteheads **0.943**, rests **0.722** (0.500 on the registered set's
  ten). The six dense cells print almost no rests.
- ⚠️ **Phase A's reference-variant rule is a NO-OP under `hollow-ft`** — 0 overrides across all
  141 boxes, because the detector's variant already agrees with the reference. It earned its
  keep on the older weights (2 of 3 flips) and costs nothing, but it is not holding the number
  up and cannot fix a flip caused by a misplaced box.
- **Two alternative explanations ruled out before reporting:** the blind server's access log
  shows all 49 cells saved through it (no hint contamination), and for every error there is NO
  human box of the pre-fill's class overlapping the pre-fill box (so the greedy IoU-0.3 matcher
  is not stealing a neighbour). The 0.838-vs-1.000 split between the two halves is real and
  unexplained by box geometry (110×101 vs 112×112 px) or labeling order (fully interleaved,
  16:06–17:05 vs 16:09–17:06).
- **The 49 completely-labeled cells are this session's real yield** — blind, complete, and
  exactly the rests-and-accidentals completeness `NEXT_ITERATION.md` step 1 asks for on this
  batch. Re-conversion into a training version belongs to the labeling/training session
  (`data/user-labeled/` is theirs).

## 2026-09-03 — Phase C started, and the training session's finding corrects a Phase B claim

- ⚠️ **CORRECTION to Phase B, from the training session's independent work.** "What it lost was
  junk" was true of NOTEHEADS and over-general about everything else. `NEXT_ITERATION.md`
  establishes that the hollow-family weights suppress **rests and accidentals**, and that the
  cause is a LABELING gap: the completion pass over these cells labeled only black noteheads
  and augmentation dots, so rests and accidentals trained as background. The same signature is
  in the Phase B arm's own numbers, reported but not read — **rests fall 1380 → 951**. And the
  missing-hint control is close to BLIND for rests, because `prefill_cell` drops rests from the
  alignment on condensed staves and a conductor's page is full of them. The notehead half of
  Phase B stands unchanged; the generalisation does not.
- ⚠️ **A palette trap was caught before it could do damage, and it was the difference between
  helping the next training run and harming it.** The batch's ACTIVE `batch_config.json` was a
  stale 9-slot completion palette with **no `accidentalNatural`, slur, tie or hairpin** — while
  the six already-complete cells contain 5 naturals, 8 slurs, 6 ties and 5 hairpins. Labeling
  Phase C under it would have left all of those as background: precisely the mechanism
  `NEXT_ITERATION.md` blames for the completeness regression. Swapped to the canonical 14-slot
  `batch_config.completion.json` (the stale one backed up as `batch_config.stale-9slot.bak`).
- ⚠️ **Even 14 slots is not the whole class space.** The six complete cells also hold `keyFlat`
  ×3, `clefG`, `timeSig8`/`9`, `ornamentTrill`, `accidentalNaturalSmall` and two grace-sized
  black heads — labeled through the FULL PICKER, which is what "complete" means. The protocol
  now says so explicitly.
- **The cells are dual-purpose**: Phase C's out-of-sample measurement AND step 1 of
  `NEXT_ITERATION.md` for this batch (the rests/accidentals completion the next cloud run
  needs). Serving blind on :5053 from a worktree that has `--blind`; ⚠️ a 5.5-hour-old server
  on **:5051 is still serving this batch NON-blind with the stale palette in memory** (config
  is read at startup) — it must not be used for this pass.

---

## 2026-09-03 — `Hr.` / `Trpt.`: the largest gap the lexicon sweep found, closed

- The lexicon sweep two entries below left `Hr.` and `Trpt.` open on purpose —
  "that is a third lexicon change and it deserves the same multi-edition
  measurement rather than a ride on this one." Measured separately, same day:
  `hr` (German/English *Hörner*) and `trpt` (a distinct 4-letter shorthand from
  the `tpt` already in the table, not a typo of it) are **0/409** collisions
  against every existing alias and **0/1271** touches on the reference
  part-name corpus.
- Against the same 1422-label margin dump: **24 labels, 13 distinct strings,
  all Brahms 1 / Breitkopf horn and trumpet staves** — the true count; the "18"
  first reported was a `.most_common(12)` display truncation, not the real one.
  Every committed reader benchmark (`results*.json`, `score_readers.py`) is
  byte-identical to before.
- ⚠️ **The instrument NAME is right in all 13 strings; the transposition
  offset is exact only where the printed key TRAILS the abbreviation**
  (`Hr. (E)` → fifths_offset -4, correct). `(C) Hr.` — key BEFORE the noun —
  falls back to Horn's positional default, because `_parse_bare_key` has only
  ever read the token AFTER a match. **Not a new gap**: `A-Klar.` has resolved
  to Clarinet with its default transposition rather than a parsed one since
  2026-08-31, for every key-taking instrument in the table. The dossier join
  pins on the unambiguous NAME, not the offset, so this doesn't cost a pin.
- `benchmarks/omr-lexicon-2026-09/FINDINGS.md` and `CLAUDE.md`'s "Instrument
  identity" section both updated in place rather than restated.

---

## 2026-09-03 — three margin labels the lexicon dropped, and three different faults

- `scan_eval.py` over the five verified scan rows produced three strings
  `instruments.lookup` could not match. Each turned out to be a different kind of fault, and
  only one was a lexicon bug. Full reading:
  [benchmarks/omr-lexicon-2026-09/FINDINGS.md](benchmarks/omr-lexicon-2026-09/FINDINGS.md).
- **`Contrafagott` was one hole in a family of ~25.** A contrabassoon is printed as a BASSOON
  name with a contra- qualifier, and both halves vary independently (four languages of noun ×
  four of qualifier × the abbreviations a crowded margin uses), so the spellings are a CROSS
  PRODUCT and the hand-list held six. ⚠️ The missing ones did not ABSTAIN — the bassoon noun
  inside them matched on its own, so `Contra-Fagott` read as **Bassoon** and `C. Fagotto` as
  Bassoon at HIGH confidence, enough to pin a staff to the wrong part. `_CONTRA_ALIASES` is now
  DERIVED from the bassoon's own aliases (the `VOICE_QUALIFIERS` move); `contraf` stays listed
  apart as a truncation. Matching is not loosened — every generated string still has to appear
  word-bounded and exact.
- **The live cost was on the scan benchmark's own Brahms edition, not on Mahler.** Breitkopf
  abbreviates Kontrafagott `K. Fag.`, and ten of those staves were reading as Bassoon on a page
  that also prints two real bassoon staves. The reported `Contrafagott` was the cousin that
  happened to abstain and therefore got noticed.
- **`Yiolino II.` was already fixed and unmerged** on `claude/zen-panini-fdc5ae` (`6bfed41`,
  2026-09-02) — merged rather than rebuilt. Its decision: the OCR fold belongs in the lexicon,
  admitted on RARITY not plausibility (`y` occurs only in `tympani`/`xylophone`, both of which
  resolve on the exact pass), and common-letter pairs (a/u, b/h, c/e, n/m) are refused by name
  at a priced cost of two real corpus reads.
- **`in C \frac{1}{2}` was not a lexicon fault.** Surya writes a STACKED part number as a LaTeX
  fraction; the digits are part numbers `normalize_label` already drops, the control word is not
  and it dilutes `coverage`. Folded at the READER (`staff_labels_surya._plain_text`), because
  LaTeX is Surya's output format and `_surya_worker` already unwraps that worker's HTML at the
  same boundary. ⚠️ Measured over 1422 labels it changes **zero** resolutions — the two Brahms
  strings are the HORN staves, and the page prints `Hörner` once braced across them, so
  abstaining is correct and no lexicon can recover them.
- **Validation, three corpora** (`benchmarks/omr-lexicon-2026-09/`): 1 of 1271 reference part
  names changes; every committed reader benchmark is unchanged to the count; **12 of 1422 real
  margin labels across 13 editions change, all in the intended direction**. New harness:
  `read_margin_labels.py` (dump what the readers emit), `resolve_labels.py` (replay a dump
  through two revisions' lexicons), `reference_part_names.py`.
- **Found and NOT fixed, each its own bug:** `Hr.` and `Trpt.` resolve to nothing on 18 Brahms
  labels; a whole system margin can arrive as ONE label and resolve to Piccolo.

---

## 2026-09-03 — snap-ledger audit: three hollow labels corrected, all Eulenburg Scheherazade / v8

- The old click-to-box snap extrapolated the parity grid beyond the staff at the staff
  spacing, and real ledger pitch is a fact about the engraving (the snap-ledger work,
  `benchmarks/omr-snap-ledger-2026-09/FINDINGS.md`, branch `claude/peaceful-shamir-d12e52`) —
  so some accepted suggestions carried the wrong OnLine/InSpace variant. Every out-of-staff
  labeled notehead where the rung-anchored snap disagrees with the stored class was
  re-adjudicated: 26 candidate rows (7 BROKE + 19 STILL WRONG) across the 10 hollow batches,
  each examined on a rendered crop, the ambiguous ones settled by ink measurement.
- **Three labels were wrong — all silent acceptances of the old grid's suggestion, all on the
  Eulenburg Scheherazade batch:** `schehe-p3-sys0-s3-m3` OnLine→InSpace (the head hangs in
  the space below its single ledger), `schehe-p4-sys0-s2-m0` InSpace→OnLine (the counter is
  split into two white lobes by the 2nd ledger running through the head), and
  `schehe-p3-sys0-s3-m0` OnLine→InSpace — FINDINGS §4's "unresolved" row, settled by
  measurement: one connected counter, the single ledger tangent below the head at 1.25×
  staff spacing (the wide Eulenburg first gap), and no ink where a second ledger would print.
- **The other 23 candidates stand**, including every one of Sean's explicit `c`-press
  overrides. Several were confirmed by ink profile rather than eye alone — e.g.
  `mahler1-p3-sys0-s11-m5`, where the ledger band runs through the head with 37–55 px wings
  but both grids read in_space because the cell's manifest staff lines sit ~40 px off the
  ink at that x (the §6 warped-manifest family).
- Corrected in BOTH verdict copies — the batch's `verdicts/` and the survey's
  `v8-merged-verdicts/` that `build_v8.py` derived from them — as class strings only, boxes
  untouched. Then v8 re-exported with the original converter arguments: the diff is exactly
  three class ids (32↔34) on unchanged coordinates, plus the metadata timestamp.
  `build_v8.py` was deliberately NOT re-run (it would silently pull the later Brahms
  completion-sweep boxes into v8's membership), and the catalog was deliberately NOT rebuilt
  from the worktree (its committed lists carry main-checkout absolute paths; training reads
  `labels/*.txt` directly, so the correction is live for the next training run as-is).
- Eval after the correction (shamir tooling over current verdicts): ink transitions
  18 recovered / 7 broke → **21 / 4**; the 4 remaining breaks are FINDINGS §4's adjudicated
  displaced-centre artifacts and the one tangent-merge reader miss, all with correct labels.

## 2026-09-03 — Phase C registered: a blind, pre-registered sample to decide admission

The measurement half is Sean's; everything around it is prepared, and two ways the number
could have come out wrong are now closed by construction.

- **`annotate.server --blind`** withholds the pre-fill from the UI entirely — no ghost hints,
  no `prefill_status`, no queue order. ⚠️ **A human shown the hints cannot measure them**: the
  score would report agreement with what the human was told. The existing `h` toggle is not a
  substitute — hints render by DEFAULT and `Tab` to the next cell is a full page load, so the
  toggle resets on every cell. The queue order is suppressed too, because "most left for me
  first" leaks the same information one step removed. Verdict state is untouched; blind is
  about what the human SEES. 1 new test asserts both payloads and that the cell set and order
  are unchanged.
- **`select_phase_c_cells.py` pre-registers the sample** (`PHASE_C_CELLS.json`): seeded
  (20260903) so it cannot be re-rolled until it flatters something, excluding the six
  already-complete cells, and recording each cell's pre-fill status, box count and admission
  tier **before** any labeling — 25 cells, 74 boxes, 73 of them labels-tier. The list is
  ORDERED and stopping early stays valid (a shuffle's prefix is a uniform sample), which is
  why 25 are registered when 12–15 is the ask: 15 cells ≈ 50 boxes, 25 ≈ 74.
  ⚠️ A random sample of orchestral cells is mostly SPARSE bars (1–6 boxes) against ~8 in the
  six dense ones — that difference IS the bias being corrected. Four cells the pre-fill
  abstains on are kept in: dropping them would quietly reintroduce the old bias.
- ⚠️ **Caught before it could produce a damning wrong number: every registered cell already
  has a verdict file** from the hollow sweep, so an unreached cell is not empty — it holds
  hollow boxes and nothing else, and scoring every class against it charges each correctly
  pre-filled black head as a false positive. `probe_admission.py` gained `--inspected-for`
  (the guard `mxl_verdicts` already had), so both tools score exactly the cells that are
  finished, at any point mid-labeling. It also gained `--transcription`, because which boxes
  exist to be scored moves with the weights (Phase B) — score against the reading the sample
  was registered against.
- Protocol, including how to read the answer either way:
  `benchmarks/omr-prefill-admission-2026-09/PHASE_C_PROTOCOL.md`.

## 2026-09-03 — Round 3: completing the training cells (540 → 1322 boxes)

- **The next-iteration plan's diagnosis was a minority of the problem, and measuring first
  caught it.** `NEXT_ITERATION.md` said the 30-epoch cloud regression came from rests and
  accidentals left unboxed. Running the production detector over the 198 cells that emit a
  YOLO label and bucketing every detection by whether ANY pass had covered its class:
  **41.2% (377 of 916) sat in never-boxed classes** — dynamics 165, slurs 99, ties 26,
  clefs 29 — against 73 for rests+accidentals. **Dynamics + slurs are 3.6× the named gap.**
  Labeling only what the plan named would have spent the GPU and hit the same wall.
- **Work split by which labeler is good at which family**, not one method for everything:
  Sean hand-labeled rests, accidentals and clefs (the round-2 audit measured the model
  FP-prone exactly there); an audited model completion did dynamics, slurs and ties
  (spot-checked 8/8 real per class) and later a black-notehead top-up. **760 human boxes
  over 493 cells**, audited crop-by-crop with **zero label errors found**.
- **Closing measurement, same 280 cells and same detector as the opening one:
  uncovered ink 68.1% → 35.9%.** It also named the next gap rather than just scoring —
  41% of the residue was black noteheads, unevenly covered (80 boxed on Litolff, ONE across
  25 cells of v7), which is the dominant class training as background. Topped up.
- **v13–v21 supersede v7/v8 in `catalog-versions.txt`.** 209 cells / 540 boxes → **280 /
  1322 (+145%)**. The old versions come OUT rather than sitting alongside: they label the
  same images less completely, and training on both teaches that the symbols the incomplete
  copy omits are background — the regression being fixed.

### Three bugs, each caught by diffing rather than by a clean-looking run

- ⚠️ **The converter silently dropped all 445 model boxes.** `verdicts_to_yolo_labels` reads
  a schema-v2 detection as `model_predicted_class` + `model_bbox`; the merge wrote
  `smufl_name` + `bbox`, the shape the completion CANDIDATES use. The file parsed, the cells
  counted, 911 of 1157 boxes were emitted, and the retrained mix would have carried LESS
  completion than v8 while the round looked like progress. Fixed; now verified per version
  as merged == emitted.
- ⚠️ **A config is not a coverage record.** Brahms 1 was left to the session holding it,
  whose palette lists rests and accidentals. Its VERDICTS showed 55 cells stamped
  `hollow noteheads` and **zero stamped for any completion pass** — so its 11 cells in v8
  would have re-imported the exact background bug through the one batch nobody swept.
  What a pass covered is in `inspected_passes`; a palette only says what someone COULD box.
- ⚠️ **A guard that abstains silently is indistinguishable from a guard that passed.** A new
  size guard read `cell.staff_line_ys`; the field is `staff_line_ys_canonical`. getattr
  returned None, every cell registered as "no geometry", the guard abstained on all 169
  candidates and let through the 394×170 slur arc it was written to catch. Nothing errored;
  the only tell was `dropped_size: 0` where a small positive number belonged. The abstention
  path now COUNTS instead of returning True.

### Also

- **Sweeping cells that cannot become training data.** A cell only trains if it carries a
  box (`_is_filled` is false for an inspected-empty cell, which emits no label and is not
  used as background either). Pooling only box-carrying cells cut the remaining sweep from
  328 cells to 152 with identical signal.
- ⚠️ **Scan degradation has TWO directions and a naive probe sees one.** Asked whether a
  batch was a bad scan, ink density, fragmentation and staff-line continuity all said
  mid-pack — they only detect decay by BREAKING. This corpus decays by BLOOMING, and **a
  bloomed staff line is perfectly CONTINUOUS, so it scores WELL on continuity while being
  unreadable.** Every batch here is bloomed (lines at 0.20–0.27 of a staff space against a
  clean 0.08–0.12).
- **The three works asked for cannot be benchmark rows.** Mahler 1, Elgar 1 and La mer have
  edition PDFs and ZERO reference encodings. Of the 27 works pairing a PDF with truth, every
  one is German-published except Holst/Goodwin & Tabb, Tchaikovsky 4/Jurgenson and
  Tchaikovsky 4/Heugel — drafted in `works-draft-nongerman.json`, held out of `works.json`
  because scan_eval refuses a pooled figure while any row is `first_pass`. ⚠️ **The training
  set covers Universal, Novello and Durand and this benchmark cannot validate them.**

---

## 2026-09-03 — Phase B: the pre-fill's precision follows the detector (0.88 → 0.96)

- **"Pre-fill precision is downstream of recognition" is now TESTED, and true** — the measured
  handoff's structural finding, and the reason Sean kept the approach open. A change of
  WEIGHTS alone, with no pre-fill code touched, takes the six-cell figure **exact 0.880 →
  0.961, kind 0.940 → 1.000**, the `labels` tier from 22 boxes to **44 of ~50** (still
  precision 1.000), batch CONFLICTs 4 → **0**, TP/WRONG_CATEGORY 174/16 → **191/5**, extra
  hints 200 → **58** and missing hints 20 → **15**.
- **The arm is not the imgsz-2048 re-ship** — that checkpoint is not blessed yet (the cloud
  run's directories hold per-epoch files and in-flight gate logs). It is the same shape of
  change and was already available: the batch's committed `transcription.json` was made with
  the PRE-hollow `imgsz2048-ft-30ep`, while scan-domain production is now `hollow-ft`.
  `benchmarks/omr-prefill-admission-2026-09/rerun_on_weights.sh` runs one arm per checkpoint
  against a symlinked scratch bench (nothing written inside the batch); add the re-ship column
  when it lands.
- ⚠️ **The objection is that hollow-ft simply detects less** (noteheads 4260 → 2419 on the same
  three pages). The control that settles it asks the opposite question — the MISSING-hint
  count, reference notes the reading never found — and it falls too (20 → 15; 4 → 3 on the six
  cells), while page segmentation is byte-identical (706 measures, 83 staves). The pipeline's
  own filters corroborate: unladdered noteheads dropped 1063 → 304, clipped fragments 259 →
  104. Every channel moves the same way at once, which is what separates a recognition gain
  from a threshold trade.
- Both Phase A predictions confirmed: `s2-m2`'s conflict (called "a duplicate detection the
  re-ship should clean up") is gone, and the labels tier's coverage climbed with the detector.
- ⚠️ **A batch's hints AGE with the weights.** This batch's committed `prefill/` is a
  checkpoint stale — the hints being labeled against are the 0.880 set. Refreshing is a
  re-transcribe plus `mxl_verdicts --write-hints`, which writes `prefill/` only and leaves
  `verdicts/` and `detections/` untouched (no human work, no detection id disturbed). Left to
  the batch's owner: it is served live by another session.

## 2026-09-03 — Phase A of the admission plan lands in the pre-fill

Sean approved the widening plan; its pre-fill half shipped, measured on the six-cell A/B
before and after, 206 tests green across the eight related suites.

- **The on-line/in-space variant follows the reference on exact pairs**
  (`expected_head_class(..., variant=)`, wired in `_decide`): the alignment key IS the
  reference's staff position, so on an exactly-paired note the reference knows the variant at
  the confidence of the pairing itself. Near pairs keep the detector's variant — measured, all
  six near matches were exact-correct and the truth's parity is wrong there by construction.
  Fixes 2 of 3 flips (six-cell exact **0.84 → 0.88**, kind unchanged), and it repairs the
  misread-clef case's variant along the way (both cello heads sit in bass-staff SPACES; the
  treble misreading had implied OnLine). Two test fixtures carried musically impossible
  variant/pitch pairs (E5 "OnLine", D5 "InSpace" in treble) that the new rule exposed —
  fixed to what the pitches actually print.
- **Within-measure tie chains collapse by the reading** (`measure_align.collapse_tie_chains`,
  run before the tremolo collapse): tied fragments become one head of the summed value only
  where the reading placed ≤ 1 head at the position; a chain may enter tied from the previous
  bar and leave tied onward; a total with no single written value (2.5 beats) is left as
  written because the page prints it as tied heads. On the batch: conflicts 5 → 4 and missing
  hints 22 → 20 — `s3-m6` resolved (its two hints pointed at blank paper); `s2-m2` STAYS
  because the reading shows TWO heads at the position (a duplicate detection) and the gate
  believes the reading — Phase B's re-ship is the expected resolver. The two accidental-glyph
  conflicts remain deliberately.
- **Every decision now carries an admission tier** — `admission: labels|queue` +
  `admission_reasons` (near match / variant corrected / grace-sized head < 0.85× the cell's
  median in both dims / cell-level: any flip demotes its whole cell) — and `--score` prints a
  per-tier table. Six-cell result: **labels tier 22/22 = 1.000 exact** at 0.44 coverage,
  queue 28 at 0.786. Stricter than the probe's 0.74-coverage composite because pre-fill time
  has no human-calibrated parity. ⚠️ Metadata only: verdict-writing is unchanged and nothing
  is auto-admitted until the random completion pass prices the tiers out-of-sample.

## 2026-09-03 — the 9 inside-staff snap disagreements diagnosed: ideal staff lines vs tilted scans

- **8 of the 9 flagged inside-staff labels sit in cells whose stored `staff_line_ys_canonical`
  is 0.25–0.55 staff spaces off the printed lines**, and rebuilding the grid from the printed
  ink reproduces Sean's class on all 8 (the 9th, beet5hr, is a tangent-note click ambiguity —
  grid fine). The 3 hand-drawn beet5-p4-s14 disagreements from the 2026-08 batch are the same
  defect. Record + scripts: `benchmarks/omr-cell-grid-tilt-2026-09/FINDINGS.md`.
- Cause is **phase-1's staff MODEL, not the cutter**: `Staff.line_ys` is five ideal horizontal
  rows for the whole staff; the flagged scans' staves tilt/bow 8–17 page px across their
  width; every measure cell inherits the same constants, so end-of-staff measures carry the
  full residual. Reproduces byte-for-byte on today's code (modulo the two cutters' deliberate
  pad difference). `line_wander_px` (7–10 px on every flagged staff) already measures the
  departure but never reaches cells.json.
- Campaign audit (all 225 inside-staff added labels vs ink-measured grids): 15 past the
  0.25 sp flip line; box centres bounded ≤0.25 sp (a near-half-space grid error aliases the
  box onto the other slot's true position — the CLASS flips, the position stays plausible).
  **Two silent wrong labels found**: `brahms1-p2-sys1-s20-m6` HalfInSpace→HalfOnLine (in v8;
  **fixed same day**, `3baadcd` — batch verdict + survey `v8-merged-verdicts` + v8 label line
  30→28) and `lamer-p5-sys0-s2-m0` WholeOnLine→WholeInSpace (exported in v11 since `780cbf6`,
  v9–v12 held out of the catalog; fix 32→34 in flight — three copies: batch verdicts, survey
  `phase2-merged/lamer/verdicts` (v11's export source, a third edit-both trap), v11 labels).
- **`pitch_resolver` eats the same defect**: on warped scans, end-of-staff measures resolve
  pitches against a grid up to half a space off — step-off-by-one for whole bars. Engraved
  benchmark blind (LilyPond pages are straight). Follow-up measurement (landing on
  `claude/sad-austin-7e16e7`): per-line tracing REFUTED as the fix — it aliases 0.87 sp the
  wrong way on the worst cell; a rigid 5-comb slide (< 1 spacing) reproduces all 7 flagged
  cells within 0.04 sp (`OMR_CELL_LINE_TRACE`, default off). Scan e2e cost is 4 edits of 7894
  because only 0.4% of its cells sit past the flip line vs 8–16% on deeper pages — **that
  benchmark cannot price the defect**. The recut-compatibility concern DISSOLVED under
  measurement: flag on/off leaves cell images, bbox and upscale byte-identical (360/360 on the
  worst page), only the stored grid moves — one frame, two grids; fix = `recut_cells.frame_mismatch`
  comparing the unlocalized grid. In-staff snap stays frozen (`test_ledger_snap.py`).

## 2026-09-03 — the five CONFLICTs reviewed: ties and accidentals, not tremolos

- **The measured handoff's hypothesis ("Breitkopf tremolo abbreviations") is refuted for all
  five conflicts**, corrected in place in that handoff and recorded with the evidence in
  `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/CONFLICT_REVIEW.md`. Three
  conflicts (2 on `s2-m2`, 1 on `s3-m6`) are the REFERENCE's tie-splits — one printed
  dotted-half encoded as tied eighth+quarter+quarter, `<tie>` on every fragment, no
  `<tremolo>` — so the hollow heads Sean had already boxed are right and the aligner was
  fighting fragments (its two "missing" hints on `s3-m6` point at blank paper). Two
  (`s26-m0`, `s15-m7`) are a flat's loop and a natural sign the base transcription misread as
  hollow noteheads, over already-empty (correct) human verdicts. **Nothing needs re-clicking.**
- Actionable residue: **tie chains need the reconcile-by-the-reading collapse tremolo already
  gets** (collapse to one summed-value head only where the reading placed one head) — that
  turns the three tie conflicts into confirmations. The two accidental fakes are the same
  family as the admission probe's phantom TPs.
- The optional `tremolo1`–`5` labeling pass gets **no support from this sample** — zero strokes
  in the four cells; parked until a batch shows strokes the detector mishandles.
- batch_config on Sean's Mac: the ACTIVE file is a STALE 9-class completion palette
  (pre-`fd28a76`, missing slur/tie/hairpins); continuing completion work needs
  `cp batch_config.completion.json batch_config.json` + server restart, not the hollow restore.

## 2026-09-03 — PR #5 landed; pre-fill admission signals measured

- **PR #5 (the pre-fill / labeling-system branch) is merged into main** — the branch had gone
  CONFLICTING against main after the weight-routing commits; the one conflict was
  `version_memory.md` (both sides' 2026-09-03 entries, resolved as a union, weight routing
  first), 196 tests green on the merged tree, merged as `711d3ff`. The main checkout on Sean's
  Mac still sits on the branch (now behind); `git pull` there when the cloud training session
  is done with it.
- **The pre-fill's 8 errors were separated by signals already in the records**
  (`benchmarks/omr-prefill-admission-2026-09/`): the aligner's own confidence is the WRONG
  admission axis — all six `near` matches are exact-correct (filtering them lowers precision
  0.840 → 0.818) and `strength_exact` ranks the cleanest cell below every error cell. What
  works: per-cell parity consistency (the one inconsistent cell holds 4 of 8 errors), a
  < 0.85×-median size veto (2/2 grace heads deferred for 1 good box), and re-deriving the
  on-line/in-space variant from the matched reference note rather than the detector (fixes
  2 of 3 flips, zero regressions — the alignment key already trusts that position). Composite:
  **37/37 exact at 0.74 coverage, in-sample** — a ceiling demonstration on the same biased
  six cells, not a claim; the out-of-sample test is a random completion pass scored by
  `probe_admission.py`, which reproduces the recorded 50/42/47 before it prices any policy.

---

## 2026-09-03 — The labeling survey widens: inventory, grace selector, click-first passes

**Why:** Sean's direction — extend the proven single-symbol × publisher
campaign toward every score element, with click-to-box as the standard.

**What:** (1) `benchmarks/omr-labeling-survey-2026-09/symbol_inventory.py`
generates `INVENTORY.md` — all 208 catalog classes + classless elements, each
with an owner (detector / CV / template-reader / specialist-slot / parked),
labeled-box counts, and publisher coverage; 106 detector-owned classes have
zero boxes, and the `numeral*` family surfaced as genuinely unassessed.
(2) `grace_score.py` — survey Row 2's selector (small solid head near a full
head, all thresholds in staff spaces, PROVISIONAL until first real labels) —
plus the honest first measurement in `GRACE_SELECTOR_2026-09-03.md`: the
280-cell hollow pool cannot validate it (top-ranked candidates are fragments
and dots), because cells selected FOR sparse sustained bars anti-correlate
with ornamentation; next step is a cut from grace-rich movements.
(3) The single-symbol pass UI now opens every cell **already in draw mode** —
click the symbols directly, no per-cell "add missed" step (`cell.js`; Esc
steps out; verdict hotkeys unaffected; 52 annotate tests green).
(4) NOTES.md gained the 🅿️ PARKED item Sean asked not to lose: re-try the
template-read elements (time signatures first) under the new labeling system,
detector as an added voter, harness ready-made.

## 2026-09-03 — Labeling UI: the click-to-box snap reads ledger rungs off the page

**Why:** Sean reported the hollow-campaign defect that the single-symbol
click-to-box sometimes suggested on-line for an in-space note — on ledger
lines only, never inside the staff. Probing the 357 committed hollow-campaign
labels confirmed it exactly: wrong-suggestion rate 4.6% inside the staff,
3.3% at the 1st ledger, **38.1% / 39.3% at the 2nd and beyond**. Mechanism:
inside the staff the snap grid anchors on the cell's own measured line
positions, but beyond it extrapolated at the staff spacing — and measured
ledger pitch is publisher-dependent in BOTH directions (Litolff ~1.10× the
staff spacing, Peters/Breitkopf/Simrock ~0.975×), so no corrected constant
can fix it (swept and refused: best variant recovers 3 of 29 wrongs).

**What:** new `tools/omr/annotate/ledger_grid.py` measures the ledger rungs
printed at the clicked x (thin bands of long ink spans; white gaps up to 0.9
spaces bridged because a whole note's counter splits the one rung printed
THROUGH it; the band's peak-span rows are what must be rung-thin), and
`snap_to_staff` gained an optional `ledger_rungs=` that anchors the outside
grid on them — line slots on the rungs, spaces on their midpoints, the old
extrapolation past an incomplete ladder's reach and wherever no rungs were
read. In-staff behaviour is byte-identical (0 changes across all 214
in-staff labels) and every failure of the reader is an abstention back to
the old grid. Measured on the labels: 2nd-ledger agreement 57.4% → 70.2%,
16 rows recovered vs 7 "broken" — of which visual adjudication showed 2 are
**wrong labels the old snap itself planted** (Sean accepted a wrong
suggestion unnoticed; v8 data-quality follow-up), 3 are artifacts of judging
at stored box centres that sit ON the old grid, 1 real miss, 1 unresolved.
The unbiased hand-positioned subset: baseline 7/13 → ink 10/13. 3.4 ms per
click. Guarded by `tools/omr/tests/test_ledger_snap.py` (8 tests: in-staff
frozen, defect case flips, incomplete ladder abstains, reader reads through
a hollow head, endpoint end-to-end). Probe + eval + refused alternatives:
`benchmarks/omr-snap-ledger-2026-09/FINDINGS.md`.

---

## 2026-09-03 — Scan vs engraved weight routing (on by default)

**Why:** the hollow fine-tune ship left the two domains preferring different
checkpoints — scans want the hollow weights (half-notes 8→27 on beet5-p1),
digitally engraved input the prior production weights (11-work OMR-NED 0.1399
vs 0.1421) — and one weights slot forced one side to pay the other's cost.

**What:** when no weights are pinned (`--weights` / `OMR_WEIGHTS_PATH` /
`weights=` all absent), `transcribe()` now classifies its input by where the
ink comes from — a scanned page is one full-page raster image (total coverage
≥ 0.95 on every scan measured), an engraved page is vector drawings (428–2058
paths vs 0–4, gap empty over 147 probed pages) — and routes: scanned →
hollow-ft, engraved → prior production, ambiguous/blank → default. Any scan
page wins the document verdict (an IMSLP scan behind a digital cover is a
scan); a missing engraved file falls back soft; explicit choice always skips
classification. Verdict + evidence recorded in the result JSON as
`weight_routing`. New: `tools/omr/input_domain.py`,
`transcribe._route_weights`, env `OMR_WEIGHT_ROUTING` / `OMR_ENGRAVED_WEIGHTS`,
35 tests. Costs ≤ 77 ms per document. Side effect: default engraved runs use
the same weights the recorded accuracy headline was measured with, so the
record describes shipped behavior again. Measurements + A/B verification:
`benchmarks/omr-weight-routing-2026-09/FINDINGS.md`. The strategy decision —
why exactly ONE fork, why publisher/era weights are deferred and what
measured triggers reopen them, and the checklist future specialist weights
must pass — is recorded in
[docs/weight-routing-and-specialization-2026-09-03.md](docs/weight-routing-and-specialization-2026-09-03.md).

## 2026-09-03 — pre-fill / labeling-system work

- **the pre-fill has a number: precision 0.84 exact / 0.94 kind** — Sean labeled six Brahms
  cells COMPLETELY by hand (every symbol, not just hollow heads) and `--score --score-classes
  all` scored 50 pre-filled boxes against 94 human ones, 42 exactly right. Recall (0.447) is
  meaningless and always will be: the pre-fill proposes only noteheads. Diagnosed box by box,
  the 8 errors are **concentrated, not diffuse** — 2 grace notes (IoU 0.73-0.80, right place,
  wrong size), 3 on-line/in-space flips (IoU 0.31-0.41, box half a notehead off) and 3
  unmatched, with six of the eight inside two of the six cells; excluding grace, 44/50 = 0.88.
  ⚠️ The sample is BIASED by my own cell choice — ranked by how much the pre-fill decided, so
  the densest bars, where alignment slips most; n=50 gives ~0.71-0.93 at 95%. **Verdict: a
  queue, not labels, today** — and the structural finding is that **six of eight errors are the
  DETECTION's placement**, which the pre-fill inherits, so its precision is downstream of
  recognition and should rise with the imgsz-2048 re-ship untouched.
- **grace notes are a ceiling, not a bug, and two plausible fixes were refuted by measurement**
  — the transcription holds **0 `Small` detections on any page** and the reference **0 grace
  notes in 28,579**, so neither source knows. First guess (the pre-fill overwrote a `Small` the
  detector gave) is false: `expected_head_class` already preserves size. Second guess
  (`include_grace=True` so `<grace/>` supplies it) was implemented, **changed nothing**, and was
  **reverted** rather than kept — it alters alignment for every cell and bought nothing
  measurable. ⚠️ Recorded because `truth_tokens` justifies the skip on the grounds that "the
  detector labels them `*Small`", which is FALSE on a scan and makes the skip harmful on the
  first reference that does carry grace notes. Untried route: geometry — a grace head is
  smaller than its neighbours (41×38 against 51-83 in the same cell).
  Full writeup, the checklist state and six ideas for widening this:
  `docs/handoff-2026-09-03-prefill-measured.md`.
- **`--score` can now be widened past the batch's own pass, and refuses to be widened
  misleadingly** — chasing the open checklist item "can pre-filled TPs be admitted without a
  glance". Running `--score` on the Brahms batch answers **precision 0.60, recall 0.333 — over
  5 pre-filled boxes against 9 human ones, in the four hollow-notehead classes only**, because
  scoring was hard-filtered to the batch's `batch_config` pass. That batch is a single-symbol
  hollow sweep, so the black heads and rests that make up the bulk of the 179 confirmations are
  not in the comparison and no way of running it could put them there. `--score-classes
  pass|all|<list>` widens it; ⚠️ **and widening is refused** unless `--cells` or
  `--score-inspected-for PASS` restricts it to cells a human actually swept for those classes.
  The trap is silent and would have looked like a verdict on the pre-fill: a hollow-only pass
  drew no black noteheads, so scoring every class against it charges each correctly pre-filled
  black head as a false positive, and the precision that comes out measures which pass the
  human ran. `inspected_passes` is the evidence used, since it is stamped on the way out of a
  cell and so means "looked and moved on" even where nothing was drawn. The default is
  byte-identical to before (pinned by a test comparing it to the explicit `pass` spec), and the
  report line now always names the classes and cell selection the number covers. 8 new tests,
  191 green across the pre-fill, annotate and training suites.
  **So the deciding number still needs Sean:** a handful of cells labeled COMPLETELY, then
  `--score --score-classes all --score-inspected-for <that pass>`.
- **a checked-out batch shows no music, and now there is a tool for it** —
  `tools/omr/annotate/recut_cells.py`. Sean opened the Brahms batch and got a blank canvas.
  `benchmarks/*/cells/` is gitignored (`.gitignore:77`) and **no batch has ever had a PNG
  committed**, so a checkout that did not CUT a batch has its manifest, detections and
  verdicts and not one image; the server answers 404 for every `/api/cell/{id}/image` and
  the canvas draws nothing, with the sidebar, hotkeys and hints all working. It affects all
  six hollow batches, not just Brahms. The tool re-renders only the ids `cells.json` already
  holds, and **never writes `cells.json` or deletes anything** — the obvious repair, re-running
  the cutter, is the dangerous one: `rank_and_trim.py` rewrites the manifest and deletes the
  PNGs it did not keep, so it can renumber the cell set and orphan every verdict in a labeled
  batch. ⚠️ **The frame is checked, not assumed.** Boxes are stored in the cell's CANONICAL
  frame, so an image re-cut at a different padding puts every box in the batch somewhere else
  on it and nothing downstream would say so. The two cutters disagree on padding on purpose
  and the manifest does not record which was used — but it records `cell_canonical_w`/`_h` and
  `staff_line_ys_canonical`, so the mode is DERIVED by cutting under each and keeping the one
  the manifest agrees with; no match, no write (`--allow-partial` to write the rest anyway).
  33 tests: the decisions with the cut injected, plus an end-to-end suite that cuts a
  synthesized page, deletes the images and re-cuts them **byte-identically** under both modes.
  ⚠️ That fixture crowds its staves to ~5 staff spaces on purpose — `measure_extractor` grows
  the pad where the neighbour is over 6 spaces off, so the first draft (33 spaces apart) had
  both modes returning the same height and could not have tested the detection at all.
  Verified against the real Brahms batch here: it refuses with exit 1 and names the one
  unfound PDF, because the score library is machine-local. Suite: 1752 passed, 4 pre-existing
  failures (identical with the branch stashed), 2 collection errors from no music21.
- **merged main's training gate; Brahms hints refreshed** — `origin/main` brought Sean's gate
  run (`ef51612`, `benchmarks/omr-labeling-survey-2026-09/GATE_RESULTS.md`): hollow scan labels
  PASS (half-note detection 8 → 25 on Beethoven, 9 → 23 on held-out Mahler, `with_duration`
  recall 0.388 → 0.456); the dense-page narrowing belongs to the imgsz-640 fine-tune recipe,
  not the labels, so **v8 stays out of the catalog** until an imgsz-matched fine-tune re-gates.
  Zero conflicts with the branch. Then `prefill/` on the Brahms 1 / Breitkopf batch was
  re-written with `--write-hints` so the committed hints carry the tremolo / tremolando
  collapse and the red `CONFLICT` hints (it had been written from `73f9970`, before either):
  all 57 files changed, totals identical to the handoff (179 TP, 10 relabels, 189 added, 22
  missing, 200 extra, 5 conflicts — on **4 cells**, one carrying two), 5 abstentions unchanged.
  ⚠️ The handoff's re-run command passed `--work-id brahms-sym1-mvt1` and the CLI refused it
  with "no usable window rows": the window rows carry the LIBRARY id `brahms--symphony-1`,
  not the dossier id. The runbook's form (no `--work-id`, one work per file) is right; the
  handoff is corrected. 124 tests green across the pre-fill, drafter and annotate suites.
- **session handoff written** — `docs/handoff-2026-09-03-prefill-session.md`: what the branch
  built, the seven rules the pre-fill decides by, what is measured (Brahms 1: 51 of 56, 5
  conflicts) and what is not (black heads and rests), Sean's checklist, and the environment
  notes for a fresh cloud session. CLAUDE.md and PROJECT_BRIEF.md point at it. This session
  ran out of context and closes here; the next one starts from that file.
- **pre-fill: tremolando — two pitches alternating collapse to two heads** — Sean: "Tremolo
  and tremolando". A reference run `A B A B …` (≥4 equal values, two pitches) is the page's
  two-pitch tremolando: two heads, each written with the FIGURE's full value (a bar of
  alternating sixteenths prints two whole notes joined by beams, not two halves). `tremolo_runs`
  now reports a run's kind (`single` / `pair`); `collapse_tremolo_runs` emits one synthetic
  note for a single-pitch run and two for a pair, each `duration_ql = total/2` with the type of
  the full total, and only where the reading placed ≤1 head at each of the run's positions —
  a page that printed the alternation out is left as written. Same conflict rule as the
  single-pitch case. Brahms 1 dry run unchanged (51 of 56, 5 conflicts); 56 tests green.
- **pre-fill: the READING decides whether a run is abbreviated; a hollow-vs-black conflict goes
  to the human** — Sean's proposal: keep labeling a tremolo head as the hollow head it is (the
  class space already has `tremolo1-5`/`tremoloMark` for the strokes) and let the MXL side
  reconcile. Now a run of ≥3 repeated notes (any value: three eighths as much as six) is
  collapsed to one note of its total value only where the reading placed ≤1 head at that
  staff position, and left as written where the page printed them out. A black head read where
  the collapsed reference says hollow is relabelled (the scan's usual miss); a HOLLOW head read
  where the reference says black is neither trusted nor overruled — the detection stays pending
  with `CONFLICT` in its note and a red hint. Brahms 1: 51 of 56, 5 conflicts for Sean's eyes.
- **pre-fill: tremolo abbreviations, and the first score against Sean's boxes** — Sean had
  labeled all four remaining hollow batches on main (55 Brahms verdict files, 14 hollow boxes).
  Scored: of the pre-fill's hollow boxes 3 agreed, and where it disagreed the reference spells
  a tremolo out as six repeated eighths where the page prints one hollow head with slashes —
  the pre-fill had even relabelled two correctly detected hollow heads to black. A run of ≥3
  repeated notes adding to a half or more is now ONE unit: a hollow head read over it keeps
  its class (note says why), the run counts once for recall, and a missed run becomes one
  hint typed as the abbreviation (`6× eighth → half.`). Brahms 1: 52 of 56 pre-filled.
- **pre-fill run on the Brahms 1 batch from this session** (inputs pushed by Sean): 51 of 56
  cells pre-filled, 179 TP, 15 relabels, 22 missing-note hints, 5 abstentions all on the right
  bar. Three fixes on the way: a weighted LCS that tolerates a half-space of rounding but needs
  at least one EXACT match before near ones count (a wrong bar's notes often sit a step away);
  recall over the reference's NOTES, not its rests; a rests-only bar pre-fills with hints instead
  of abstaining. `prefill/` (hints only) committed into the batch so labeling can start.
- **pre-fill: the gate is recall of the reference, and neighbours' heads stay out of the
  alignment** — a flute bar of 4 reference notes read 21 heads, 17 of them the oboe's and
  piccolo's from the cell's padding (positions 7 spaces off the staff); only heads within the
  reference's own vertical range align, and a bar passes when ≥ 50% of its reference notes
  (and at least 2) are found. Also fixed: `bbox_page_px` is `[x0, y0, x1, y1]`, not
  `[x, y, w, h]` — the x-scale into the batch frame and the width check were wrong.
- **pre-fill: diagnostics for the abstentions** — `--debug-cell` prints both token sequences
  and the geometry for a cell; every cell records a width ratio that says whether the batch
  cell and the transcription measure are the same bar (the batch was cut by a separate
  segmentation run). A reference part with no clef (percussion) falls back to step keys on
  BOTH sides. Second Brahms run: 29 of 56 pre-filled.
- **training: pre-fill aligns on STAFF POSITION, not pitch** — the reference's written clef
  (now parsed by `musicxml_truth`, per note) places each truth note; a detection's position
  comes from its box. Sean's first Brahms 1 run: 26 of 56 cells pre-filled, 30 abstained with
  `0 of N matched` — the misread-clef signature. `--match step|exact` kept as options; the
  summary now lists abstained cells with their match ratio.

## 2026-09-02 — pre-fill / labeling-system work (this branch)

- **training: draft fills an unnamed staff by ORDER** — on a shorter system, a staff the reader
  could not name takes the only unused base entry between its paired neighbours (Sean's page 1
  bottom system: the Kontrafagott between the Fagotte and the Hörner); two candidates → still
  empty for the human. Brahms 1 batch draft now needs no hand edits.
- **training: page-global staff numbering** — `transcribe` numbers `staff_index` across the
  page; the draft summed bars per index across systems (page 1 of the Brahms batch came out
  as 7 bars instead of 15) and the pre-fill joined a staff to the row by index. Both now go by
  position within the system; a full-lineup system pairs by position with the reader's word as
  a cross-check only. Found on Sean's first real draft of the Brahms 1 batch.
- **training: `draft_windows.py` + `--write-hints`** — window rows are drafted from the
  transcription and a base benchmark row (measure window chained page by page, staves paired
  to parts by instrument name, everything marked `draft` with a `check` list); hints-only
  mode writes `prefill/` without touching `verdicts/`. Runbook for the first real-batch
  measurement (Brahms 1 / Breitkopf): `docs/runbook-prefill-brahms1.md`. Finding: the Mahler
  batch cannot be scored — the library has no Adagietto reference.
- **training: MXL-guided verdict pre-fill** — `tools/omr/training/mxl_verdicts.py`
  (+ `measure_align.py`, `musicxml_truth.py`): the detector's boxes are confirmed or
  relabelled by the reference encoding through per-measure sequence alignment; unmatched
  detections stay pending, unmatched reference notes become ghost hints. Annotate server
  serves `<bench>/prefill/`; the cell list gains a queue order and the cell page a hints
  layer (`h`). `--score` measures the pre-fill against human verdicts. 43 new tests, full
  annotate + training suites green. Not yet run on a real batch — that measurement is
  Sean's next step on the Mahler 5 / Peters hollow batch.
- **docs: status brief, project brief, version memory** — consolidated where
  the labeling campaign, the movement-start data, the score-library ingest and
  the MXL-guided auto-label training system stand; created `PROJECT_BRIEF.md`
  and this file. No code change.
- `6a17de7` docs: export-gap ordinal moves out of prose into the numbered list.
- `b5b7db3` / `0a6382c` / `d282371` **eleven-work benchmark landed** — headline
  3 → 11 works; `0.1306 / 2745` default (reader on), `0.1399 / 2915` reader off,
  both on `44a1745`; boundary stamped and checked by `accuracy_record`.
- `52e9945` labeling: Mahler 5 Adagietto (Peters) hollow batch — 49 boxes, 55/56 cells.
- `2a8bf79` labeling survey: symbol × publisher-family plan; scope decision
  PROVE-IT-FIRST (finish the 280 cut cells, one gated training run, extend only if it holds).
- `54d19da` labeling: `batch_config.json` (single-symbol hollow pass) on all five round-2 batches.
- `44a1745` scan-e2e: `works.json` pinned the direction reader off while claiming defaults; now pins `null`.
- `fb4c500` … `59c1eca` labeling: hollow-notehead round 2 cut — five 56-cell batches
  (Peters, Eulenburg, Litolff 4×, Breitkopf, Simrock); enclosed-counter ranker replaces
  meter shortfall (did not transfer).
- `fa9853a` labeling: round-1 hollow batch landed as `data/user-labeled/v7-2026-09-02-hollow`
  (24 cells / 28 boxes); 116 of 117 model pre-labels were false.
- `2b900c4` annotate: `inspected_passes` stamp — a swept-empty cell is provably distinct from a never-opened one.
- `eb3530c` / `9b3cec4` / `6cad993` / `9998390` annotate UI: single-symbol pass mode —
  click places a measured, staff-snapped box; tests 18 → 52.
- `96df4fb` / `a907e41` / `f238ce9` export: a bar with no detected notes still carries its
  `<direction>` and dynamics (eighth detected-then-dropped gap). Neutral on engraved pages by construction.
- `4952005` direction text ON by default (−144 edits, stable across seven mains).
- `de09383` / `fc073f2` finding: same scan page transcribed twice differs; isolated to
  `contextual._labels_for_page`; geometry bit-identical with contextual off.
- `d3d5ec5` export_coverage surveys all eleven works.
- `bc4214d` gitignore: alternate `--work-dir` fixtures are scratch.

## 2026-09-01 — pre-fill / labeling-system work (this branch)

- Overnight generalization session: engraved corpus widened 3 → 10 (opened at ~2× the
  incumbents' error), first five-row scan benchmark (pooled 0.7960), cut-common meter
  bug fixed (3 wrong → 0), two key-signature vote bugs fixed, fermata render completed
  in the Beethoven fixture (0.1519 → 0.0727). See `docs/overnight-2026-09-01-summary.md`.
- Evening queue: edge fragments, dot height, YOLO beam stack, stem cap, beam-bar mask,
  ledger evidence (Beethoven 81/81), viola double stops, slurs paired per staff,
  Tesseract union rung, accuracy figure made single-sourced.

---

## 2026-09-03 — Diagnosed and addressed the failing `Deploy ReEngrave` GitHub Actions workflow

**Why it was asked:** every one of 123 runs of `.github/workflows/deploy.yml`
had failed since it was added on 2026-09-01.

**Root causes found (two independent failures, one per job):**

- [x] **Backend job (Docker build) — wrong build context.** The workflow ran
  `docker build .` from inside `working-directory: backend`, so the build
  context was `backend/`. But `backend/Dockerfile` (and `docker-compose.yml`,
  which builds it correctly) both assume the context is the **repo root** —
  `COPY backend/requirements.txt .` and `COPY tools/ ./tools/` need `tools/`
  and a nested `backend/` folder to exist in the context, neither of which
  exists inside `backend/` itself. Every run failed at `COPY tools/
  ./tools/` with `"/tools": not found`.
  **Fixed:** build from the repo root with `-f backend/Dockerfile .`
  instead of `cd`-ing into `backend/` first.
- [x] **Frontend job (Vercel) — missing repo secrets.** Failed immediately
  with `Error: Input required and not supplied: vercel-token` — the
  `VERCEL_TOKEN` GitHub Actions secret (and likely `VERCEL_ORG_ID` /
  `VERCEL_PROJECT_ID`) was never configured for this repo. Same is true of
  `RAILWAY_TOKEN` for the backend job, just masked by the Docker build
  failing first.

**Decision (asked Sean, he chose):** this workflow targets Vercel + Railway,
but ReEngrave's actual production path is the self-hosted VPS
(`scripts/deploy.sh` + `docker-compose.prod.yml` + Traefik) — Vercel/Railway
were never the real deploy target. Rather than wire up the missing secrets,
**disabled the workflow's automatic trigger** (`on: push` → `on:
workflow_dispatch`, manual-only) so it stops failing loudly on every push,
while fixing the Docker context bug anyway so it isn't left broken if it's
ever triggered by hand or revisited later.

**Files touched:** `.github/workflows/deploy.yml`.

**Follow-up, not done here:** if Vercel/Railway deploys are ever wanted for
real, the four secrets above still need to be added under repo Settings →
Secrets and variables → Actions before a manual run would get past both
jobs.

---

## 2026-09-03 — Added standing docs: `PROJECT_BRIEF.md` and this file

Created per standing preference: CLAUDE.md, `PROJECT_BRIEF.md`, and
`version_memory.md` should all exist and be kept current after every commit.
`PROJECT_BRIEF.md` is the short "what is this project" overview;
CLAUDE.md remains the full technical/working reference; this file is the
running changelog.

---

*Earlier project history (OMR pipeline phases, benchmark results, the
theory layer, etc.) predates this file and is not backfilled here — see
[PROJECT_STATUS.md](PROJECT_STATUS.md) for the narrative history and
`git log` for the full commit record.*
