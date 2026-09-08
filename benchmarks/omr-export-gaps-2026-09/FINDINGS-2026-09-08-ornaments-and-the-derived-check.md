# The tenth export gap, and the hole in the check built to catch them

**Date:** 2026-09-08 · **Branch:** `claude/ornaments-export-gap-pcfwfm`
(merge base `a526745a`) · **Charter:** `docs/handoff-2026-09-08-next-steps.md`
§3 Step 1 — close the `<ornaments>` gap AND fix the check that failed to
report it.

**Duplication check first, per the standing rule.** `git log --all -S
"ornaments" -- tools/omr/` and `-S "tremolo"` return only the symbol-ledger and
unrelated commits; `grep -c ornaments tools/omr/export.py` was **0** and
`grep -n -i tremolo tools/omr/export.py` was empty. Nothing existed to reuse.

---

## 0. ⚠️ WHERE THIS WAS WRITTEN, AND WHAT THAT MEANS FOR EVERY NUMBER BELOW

This is a **remote container, not Sean's machine**. There is no
`benchmarks/omr-orchestral-e2e/fixtures/`, no `omr-weights/`, no
`.venv-omrned`, no `.venv-surya`, no `library/`. **`orchestral_eval`,
`scan_eval`, OMR-NED and the detector could not be run and were not.** The
four-symlink recipe in handoff §5 points at paths on Sean's machine and does
not apply.

What *was* available, and what every figure here rests on:

| asset | used for |
|---|---|
| `benchmarks/omr-margin-window-truncation-2026-09/out/fixtures-control/` | **a COMMITTED copy of all 11 benchmark works' truth + that run's export.** The coverage funnel, and the prediction of what will fire on Sean's machine |
| `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json` | the one real transcription in the repo carrying ornament detections (3 pages, 10,523 detections). The end-to-end A/B |
| `tools/omr/symbol_ledger.py` | the scoring instrument. Pure stdlib, runs here |
| the unit suite | 2,910 pass on clean `HEAD`; 2,948 pass on the final tree with one slow file excluded — see §6 |
| 7,090 committed JSON artifacts | the detection census |

**Measured here** — §1's arithmetic, §2's detection census, §4's A/B, §5's
funnel, every RED-then-green in §6. **NOT measurable here and needing a run on
Sean's machine** — §7, with the exact commands.

---

## 1. THE ARITHMETIC: `<ornaments>` and `tremolo` are ONE finding, not two

The handoff's table reads:

| element | truth (engraved / scan) | ours |
|---|--:|--:|
| `<ornaments>` | 12 / 131 | 0 |
| `tremolo` | 12 / 123 | 0 |

**Confirmed: on the engraved side they are the same twelve elements.**
`beethoven-sym3-mvt1.musicxml` is the only one of the eleven benchmark truths
carrying ornaments, and it holds **twelve `<ornaments>` blocks containing
twelve `<tremolo type="single">1</tremolo>` and nothing else** — verified by
element census, by grouping each block's child tags (one distinct child set,
`("tremolo",)`), and independently by `symbol_ledger.extract_symbols`, which
reports `{'tremolo': 12}` ornament rows out of 417 total rows.

The scan side's 131 vs 123 leaves 8 non-tremolo ornaments; the committed
scan-derived truth `mahler-sym5-mvt1-local-p5.normalised.musicxml` shows the
shape — **17 `<ornaments>` = 15 tremolo-only blocks + 2 `<wavy-line>` blocks**
(4 `<wavy-line>` elements, start and stop), the trill's continuation line.

**So on the ENGRAVED benchmark, "close the ornaments gap" means emit
`<tremolo>`. Wiring trills alone would move it by exactly zero.** Pinned by
`test_the_engraved_ornaments_are_ALL_tremolo`, against the committed file, so
the arithmetic cannot be re-derived wrongly.

Stroke counts in the truths are **1 and 2** — not a constant. That is what
makes the count load-bearing and the coarse `tremoloMark` spelling unusable
(§3).

---

## 2. ⚠️ THE DETECTION CENSUS, and it inverts what to expect from this fix

Over **all 7,090 committed JSON artifacts** (detections, transcriptions,
verdicts, class inventories):

| class | detections found |
|---|--:|
| `arpeggiato` | 769 |
| `ornamentTrill` | 21 (+26 in the class-inventory files) |
| `ornamentTurn` | 6 |
| `ornamentTurnInverted` | 3 |
| `ornamentMordent` | 3 |
| **`tremolo1` … `tremolo5`** | **ZERO** |

Positive control: the same census returns 8,255 `noteheadBlackInSpace`, 2,785
`beam`, 455 `tie` — the walker sees classes, and it found 802 ornament-category
detections. **The zero is a property of the corpus, not of the probe.**

And **none of the 33 ornament detections is on a benchmark work**: they are
Breitkopf Brahms 1 (8), Simrock Dvořák 9 p15 (1), Peters Mahler 5 p180 (1) and
Bach WTC (the rest) — all scans or non-benchmark pages.

**Consequence, stated plainly rather than buried:** this is the **hairpin
situation, and the halves are swapped**. Hairpins were an export gap that a
same-day detection fix could partly fill. Here the export half is now built and
**the engraved `<ornaments>` gap will very likely stay open**, because its
whole population is tremolo and we detect no tremolos. The trills we *do* read
are on scans, where they now reach the file.

---

## 3. WHAT WAS WIRED, AND WHAT WAS DELIBERATELY NOT

### Wired

| | MusicXML | LilyPond |
|---|---|---|
| `ornamentTrill` | `<trill-mark/>` | `\trill` |
| `ornamentTurn` | `<turn/>` | `\turn` |
| `ornamentTurnInverted` | `<inverted-turn/>` | `\reverseturn` |
| `ornamentMordent` | `<mordent/>` | `\mordent` |
| `tremolo1`–`tremolo5` | `<tremolo type="single">N</tremolo>` | **no** |

`transcribe._attach_ornaments_in_cell` (a separate pass beside
`_attach_articulations_in_cell`), `voicing` ride-up to the chord's first note,
`export._mxl_ornament_elements` + `_mxl_note(ornaments=…)`, `_lily_event`.

`<ornaments>` is emitted **between `<tuplet>` and `<articulations>`** inside one
`<notations>`. MusicXML's `<notations>` content model is an unbounded *choice*,
so no order is schema-enforced; this follows the order the schema **lists** them
in, the same convention `_mxl_note`'s existing `<tuplet>` comment states.
Verified by round-tripping through **music21 10.5**, which reads back `Trill`
and `Tremolo` expressions on the right notes.

### Not wired, each with its reason

- **LilyPond tremolo.** LilyPond spells a single-note tremolo `c4:32` — a
  **duration subdivision**, so the number depends on the note's own written
  value and the same three strokes are `:32` on a quarter and `:64` on an
  eighth. A wrong mapping writes a different **rhythm**, not a different mark.
  Nothing in the repository detects a tremolo, so there is no measurement to
  price it against. **The hairpin precedent applied**: MusicXML gets what can be
  said safely, LilyPond gets less, and the reason is recorded.
  (`test_lilypond_does_NOT_carry_a_tremolo`.)
- **Bowed (two-note) tremolo**, `type="start"`/`"stop"`. Nothing pairs two
  noteheads to one tremolo mark. Both truth files print only `type="single"`.
- **`tremoloMark` (class id 161)**, the coarse vocabulary's spelling. It carries
  **no stroke count**, and the count is the whole of what `<tremolo>` says.
  `ornament_kind` abstains on it and the exporter drops a countless tremolo
  rather than guessing.
  ⚠️ **This expires an existing claim in `class_aliases.py`**, whose entry read
  *"Nothing downstream reads a tremolo's count today … so there is nothing to
  lose yet"*. Something reads it now. The **conclusion** survives on a stronger
  argument (a guessed count writes a different rhythm) and the entry has been
  rewritten to say so; `test_a_countless_tremolo_is_not_given_a_count` pins the
  pair.
- **`arpeggiato` (769 detections).** `<arpeggiate/>` is a `<notations>` child,
  **not** an `<ornaments>` child, so it is a different element and a different
  gap. **PARKED** under the standing scope rule — it does not corrupt this
  work. ⚠️ Worth someone's attention: 769 detections on scans, of which 99 are
  on three Brahms pages, is a rate that looks like over-detection rather than
  music. Observation kept, fix parked.
- **`<wavy-line>`.** The trill's continuation. Needs a span (start and stop
  notes); the detector gives a point. Not attempted.

### One thing left duplicated on purpose

`_attach_ornaments_in_cell` repeats ~20 lines of `_attach_articulations_in_cell`
rather than sharing a helper. The side rule genuinely differs (a trill is above
its note, a tremolo rides the stem and has **no** side), and — the deciding
reason — **the articulation constant sits on a measured plateau and the ornament
one does not**. Sharing a body would put a measured number and an unmeasured
one behind one call. The measured, shipped path was not touched.

### ⚠️ One constant, declared UNMEASURED

`_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS = 1.0`, against the articulations'
swept-plateau `0.75`. **There is no corpus to sweep it on**: zero tremolo
detections, and the 33 ornament detections have no per-mark truth to score a
placement against. It is 1.0 rather than 0.75 for a stated reason — a tremolo
stands on the **stem**, at the notehead's edge, so a constant tuned for a mark
centred on the notehead is the wrong prior — and it should be swept the day a
measurement is possible.

---

## 4. THE A/B, SCORED WITH THE SYMBOL LEDGER (not OMR-NED)

Handoff §2: musicdiff amplification differs 6×–2× by error kind, one changed
`<type>` scores **zero** on 10 of 20 files, and attribution through it is void.
`symbol_ledger.py` already emits an `ornament` family keyed on the mark's
element name, is pure stdlib, and runs here.

`probe-ornaments-2026-09-08/probe_export_ab.py`, on the real Breitkopf Brahms 1
transcription:

```
POSITIVE CONTROLS    ledger rows BEFORE 6086, AFTER 6090
                     <ornaments> in BEFORE xml: 0, AFTER: 4
marks attached       4

ledger `ornament` rows
  BEFORE             NONE — the gap
  AFTER              {'trill-mark': 4}
  synthetic tremolo  {'tremolo': 1}

non-ornament rows    BEFORE 6086  AFTER 6086  identical
```

**The change is additive**: 6,086 non-ornament ledger rows before and after,
identical. Nothing else moved, so the delta is not priced against a mixture.

**Reach**, `probe_ornament_reach.py`: **4 of the 8 `ornamentTrill` detections
find a notehead** within 1.0 notehead widths on the printed-above side (dx
4–13.5 px against a median notehead width of ~30–40 px). The other 4 have no
notehead above them within reach and are left unattached rather than given to
the nearest thing available — the rule that keeps the articulation pass's
precision at 0.980. Confidence does not separate the two groups (placed: 0.70,
0.34, 0.74, 0.36; unplaced: 0.31, 0.49, 0.56, 0.41), consistent with the
standing refusal to use it as a discriminator.

⚠️ **What that A/B is and is not.** `_attach_ornaments_in_cell` runs at
transcribe time in a canonical **cell** frame that cannot be reconstructed
without the detector, so the probe re-implements the same rule in **page
pixels** over the stored detection dicts. **The substitution is the frame, not
the rule**, and it is named rather than blurred: the probe prices the export
half on real detections, and the unit tests price the attach half.

⚠️ **A ZERO CAUGHT IN THE ACT.** The first draft of `probe_ornament_reach.py`
reported **"0 of 8 marks reach a notehead"** — clean, plausible, and wrong. It
read `bbox_page` as `[x0, y0, x1, y1]`; it is `[x, y, WIDTH, HEIGHT]`
(`transcribe.py:202` says so in a comment). Every median notehead width came out
**negative** and nothing said so. The probe now asserts that quantity is
positive before printing a reach figure. **A zero is a suspect, not a result** —
and the tell here was not the zero, it was checking why.

---

## 5. THE CHECK: why it missed this, and what replaces it

`export_coverage.compare()` iterated a **hand-written 19-name `VISIBLE` dict**,
so an element in neither `VISIBLE` nor `KNOWN_GAPS` **failed nothing** — and
nobody had to write anything down for that to be true. `<ornaments>` was in
neither. *A check built to remove a blind spot had one, in the same shape.*

### The design, and how it answers the docstring's own objection

The docstring's objection is real and survives the rewrite: *"a MusicXML file is
mostly not notation … a check that reported it would list 55 elements, be
ignored, and then be deleted."* Deriving from the truth brings all 55 back.
Three structural rules and one short deny-list cut it down. Measured on the
committed 11-work pool (`probe_derived_coverage.py`):

```
  every element inside <measure>                    88
  ... minus the ones we DO emit (categorical)        40   <- the "55"
  ... minus every element whose PARENT is missing    19
  ... minus NOT_NOTATION (print, sound, staff-details)  16
```

1. **Scope: inside `<measure>`.** Not an opinion — MusicXML puts `<work>`,
   `<identification>`, `<defaults>` and `<part-list>` (with every MIDI block)
   *outside* it, and every note, rest, clef, direction and barline *inside* it.
   ⚠️ **Named residual:** `<part-name>` and `<work-title>` are ink and are
   outside a measure, so this check does not watch them.
   `label_contradiction.py` watches part naming from a stronger direction;
   nothing watches `<work-title>`.
2. **Categorical only** — truth has some, ours has zero. Unchanged.
3. **Rollup to the shallowest missing ancestor.** ⚠️ **This is the ornaments
   arithmetic made structural.** `<tremolo>` lives inside `<ornaments>`; if we
   emit no `<ornaments>`, `<tremolo>` is not a second gap. The handoff table's
   two rows become one row by construction. Rollup does 21 of the 24 elements
   of noise removal; the deny-list does 3.
4. **`NOT_NOTATION`** — `print`, `sound`, `staff-details`. Three entries.

⚠️ **`NOT_NOTATION` IS NOT `VISIBLE` WEARING A DIFFERENT HAT**, and the
difference is the property rather than a defence of it. `VISIBLE` was an
**allow**-list: the default for an unmet element was *silently unchecked*.
`NOT_NOTATION` is a **deny**-list: the default is *fails until someone writes
down why*. **The failure direction is inverted.** That, not the list's length,
is what makes the tenth gap unrepeatable. Both tables carry a staleness test.

### What the old list was actually seeing

On the same committed 11-work pool:

| | count | which |
|---|--:|---|
| the old allow-list reported | **5** | `bar-style`, `barline`, `lyric`, `metronome`, `stem` — and `bar-style` was `barline` counted twice, which the rollup now folds |
| it was **blind** to | **15** | `ornaments`, `transpose`, `staff`, `staves`, `spiccato`, `detached-legato`, `display-step`, `display-octave`, `offset`, `normal-type`, `tuplet-actual`, `tuplet-normal`, and the three bookkeeping (`print`, `sound`, `staff-details`) |

⚠️ Two more, `grace` (24) and `unpitched` (14), are gaps on the **scan**-derived
truth and are absent from the engraved pool — which is what forced the
`stale_entries` redefinition below.

### The fourteen new `KNOWN_GAPS` entries are the backlog, not a suppression list

Every one was **already** a gap and was reported by nothing. Writing them down
with a reason and a size is the whole product of deriving the set. The largest
after `<stem>` is **`<transpose>` at 92** — the written-to-sounding interval,
a fact the pipeline already holds in `instruments.py` and never writes.

### Two definitions had to change with it

- **`stale_entries` was `expected − missing`, and was only ever right by luck.**
  That calls an entry stale in three situations and means it in one: (a) we emit
  it now — the real case; (b) the truth does not print it at all — impossible
  under a curated `VISIBLE` where every entry named something all three
  canonical truths printed, and live now (`grace`, `unpitched`); (c) it is
  rolled up under a missing parent — reported, not closed. It now asks our own
  output directly: an entry is spent when **the exporter writes the element**.
  Without this the suite would have gone red on Sean's machine for a reason that
  is not a defect.
- **`bar-style` left `KNOWN_GAPS`.** It can never be reported again (always
  rolled under `barline`), so its reason would be dead text. Folded into
  `barline`'s entry, which is what it said anyway.

### The skip that let this last

⚠️ `TestTheRepositoryItself` **skips** wherever
`benchmarks/omr-orchestral-e2e/fixtures/` is absent — every fresh checkout,
every worktree, this container. *The one test that would have looked never ran.*
`TestTheCommittedFixtureCopy` is new and runs on a clean clone, against the
committed 11-work truth + export copy. ⚠️ It asserts on the **tables** only,
never on the exporter: those `.omr.musicxml` files are from an older tree, and
reading a leftover export is precisely the false-green defect this module was
rewritten to remove.

---

## 6. EVERY TEST RUN RED BEFORE GREEN

**Baseline first, before a line was changed.** The full suite on a clean
`git archive` of `HEAD` (`a526745a`): **2,910 passed, 64 skipped, 7 failed in
609 s**. ⚠️ Two of those seven are the documented `.venv-surya` absence
(`test_direction_text.py::TestReaderSelection`); the other five are
`test_label_contradiction.py` and are an artefact of the ARCHIVE COPY — that
file's tests read gitignored artefacts, and **all 24 pass in the working
checkout**. So the pre-existing failure set here is **exactly two**, and
neither is mine.

**After, on the final tree:** `pytest tools/omr/tests/` with
`--ignore=tools/omr/tests/test_score_language.py` gives **2,948 passed, 64
skipped, 2 failed in 216 s** — and the two are exactly that
`TestReaderSelection` pair. **No new failure.** The six most relevant files run
green on their own too (`test_export.py`, `test_export_coverage.py`,
`test_transcribe_helpers.py`, `test_class_aliases.py`, `test_voicing.py`,
`test_symbol_ledger.py`: **656 passed, 4 skipped**).

⚠️ **`test_score_language.py` was excluded from that run and is therefore NOT
verified here.** It is a corpus-wide test over all 1,422 margin labels and does
not complete inside this container's CPU budget; it passed on the clean-`HEAD`
baseline, and nothing in this change touches `score_language.py`,
`instruments.py` or that test. **Run it once on a normal machine** —
`python3 -m pytest tools/omr/tests/ -q` with nothing ignored — and expect the
same 2 failures and nothing else.

⚠️ Earlier readings of this same run that looked like a stall were **self-
inflicted**: several overlapping background pytest invocations were competing
for one throttled core, and the run that finished in 216 s uncontended had
looked frozen at 66% for forty minutes. Recorded because it is exactly the
shape of a wrong conclusion: *the tell was the process table, not the numbers.*

| # | mutation | test that went RED |
|--:|---|---|
| 1 | drop `tremolo1`–`5` from `_ORNAMENT_KINDS` | 4 tests, incl. `test_the_stroke_count_reaches_the_entry` |
| 2 | make the ornament side rule unconditionally "above" | `test_a_tremolo_attaches_from_EITHER_side` |
| 3 | admit `tremoloMark` with a guessed count of 3 | `test_the_coarse_tremolo_spelling_is_REFUSED` |
| 4 | drop the ornament classes from the CV stem-rejection veto | `test_the_stem_rejection_veto_still_sees_these_classes` (+4) |
| 5 | unwire `_mxl_note`'s emission | 10 of 15 `TestOrnaments` |
| 6 | unwire the call site `event → _mxl_note` | 10 of 15 |
| 7 | guess a stroke count instead of dropping | `test_a_tremolo_with_NO_count_is_dropped_not_guessed` |
| 8 | move `<ornaments>` after `<articulations>` | `test_ornaments_precede_articulations_inside_notations` |
| 9 | add `tremolo` to `_LILY_ORNAMENT` | `test_lilypond_does_NOT_carry_a_tremolo` |
| 10 | drop the `voicing` ride-up | 11 of 15, incl. the music21 round-trip |
| 11 | alias `tremoloMark → tremolo3` in `class_aliases` | `test_a_countless_tremolo_is_not_given_a_count` (+ the disjointness test) |
| 12 | reinstate a curated allow-list in `compare()` | 6 tests, incl. `test_the_old_allow_list_is_gone` |
| 13 | remove the rollup | 3 tests |
| 14 | roll up on the **immediate parent** only | `test_the_rollup_tests_EVERY_ancestor_not_just_the_parent` — **see below** |
| 15 | widen the scope past `<measure>` | 3 tests |
| 16 | revert `stale_entries` to `expected − missing` | `test_an_entry_the_TRUTH_never_prints_is_not_stale` |
| 17 | let `NOT_NOTATION` also excuse an unexplained element | `test_bookkeeping_is_a_DENY_list_not_an_allow_list` |
| 18 | stop stripping the XML prolog when pooling | `test_several_truths_pool_without_a_parse_error` |
| 19 | remove `<ornaments>` from `KNOWN_GAPS` | `test_every_gap_head_is_accounted_for_by_one_of_the_two_tables`, on the committed 11-work pool |
| 20 | reinstate the **pre-2026-09-08 19-name allow-list** | `test_ornaments_IS_one_of_them` — **the decisive one: the old check does not report `<ornaments>` on the real committed truth pool** |

⚠️ **#14 CAUGHT A VACUOUS TEST, which is why the rule exists.** The first
version of `test_the_rollup_walks_more_than_one_level` nested `tuplet-number`
under `tuplet-actual` under `tuplet` with none of the three emitted — and an
immediate-parent-only rollup gives the **same answer** there, because each
intermediate is missing too and the suppression chains. It passed under the
mutation. Rewritten to the one situation where the two rules differ (a middle
ancestor we emit *somewhere else* in the document, since counts are
document-wide), it goes red. **It was pinning nothing and passing.**

---

## 7. ⚠️ WHAT COULD NOT BE MEASURED HERE — commands for Sean's machine

Nothing below was run; no number is claimed for any of it.

**(a) THE FULL UNIT SUITE WITH NOTHING IGNORED.** `python3 -m pytest
tools/omr/tests/ -q`. Everything but `test_score_language.py` was run here
(2,948 passed / 2 known failures); that one file does not finish in this
container. Expect the same 2 `TestReaderSelection` failures and nothing else.

**(b) The exporter against real fixtures, and the first honest run of the
derived check.** ⚠️ **Expect it to list gaps.** That is the point: 14 entries
were added to `KNOWN_GAPS` from the committed 11-work copy, and anything the
live fixtures show beyond those is a *real finding* needing its own line — a
`KNOWN_GAPS` entry if a reader sees it, `NOT_NOTATION` if no reader ever does.
Do not suppress; write down.

```bash
python3 -m tools.omr.training.orchestral_eval --omr-ned   # rebuild fixtures
python3 -m tools.omr.export_coverage --all                # the report, with tiers
python3 -m pytest tools/omr/tests/test_export_coverage.py -q
```

**(c) Does an ornament reach the file on the engraved benchmark?** §2 predicts
**no** — the truth's ornaments are all tremolo and nothing detects a tremolo.
If `<ornaments>` does appear, its `KNOWN_GAPS` entry is stale and
`test_the_inventory_has_no_stale_entries` will say so, which is the mechanism
working.

```bash
python3 -m tools.omr.training.orchestral_eval --omr-ned --works beethoven-sym3-mvt1
grep -c '<ornaments>' benchmarks/omr-orchestral-e2e/fixtures/beethoven-sym3-mvt1.omr.musicxml
```

**(d) The scan gate — where the trills actually are.** The scan truth carries
**131 `<ornaments>` / 123 `tremolo`**, so 8 non-tremolo, and the detector reads
`ornamentTrill` on scans (8 on the Brahms 1 / Breitkopf pages, of which 4 place
— §4). ⚠️ **There is no flag on this change**, so the A/B is across the two
COMMITS, not two env settings — and ⚠️ **give each arm its own `--tag=` (it
needs the `=`)**: `scan_eval.run_pipeline` returns early when the prediction
file exists, so two arms sharing a fixtures dir with an empty tag reuse the
first arm's transcriptions and the second never runs, reporting *"identical on
every bucket and every row"* — exactly the clean no-regression result a change
like this hopes for. **The tell is wall time, not the numbers.**

```bash
git checkout <merge-base>
python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --tag=-orn-before
git checkout <this branch>
python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --tag=-orn-after
# score it with the LEDGER, not with OMR-NED (handoff §2)
python3 benchmarks/omr-symbol-ledger-2026-09/run_ledger.py
```

The prediction to test: the `ornament` family goes from **0 rows to a small
positive number** and every other family is **unchanged**, exactly as §4's A/B
shows on the one page that can be run here.

**(e) Sweep `_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS`.** Requires per-mark truth,
which requires ornament detections on a page whose reference encoding is held.
The scan gate's Brahms 1 row is the candidate: same PDF as the labeling batch
whose 8 trills are measured in §4.

**(f) `arpeggiato` at 769 detections.** Parked. `<arpeggiate/>` is a different
element in a different place, and the count looks like over-detection.

---

## 8. Files

```
tools/omr/transcribe.py       _ORNAMENT_KINDS, ornament_kind,
                              _ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS,
                              _attach_ornaments_in_cell, call site, out_d
tools/omr/voicing.py          ornaments ride up to the chord's first note
tools/omr/export.py           _MXL_ORNAMENT, _LILY_ORNAMENT,
                              _mxl_ornament_elements, _mxl_note(ornaments=),
                              call site, _lily_event
tools/omr/class_aliases.py    tremoloMark's expired reason, rewritten
tools/omr/export_coverage.py  MUSIC_SUBTREE, NOT_NOTATION, TruthElement,
                              notation_index, compare (derived + rollup),
                              gap_locations, Survey.where/.ours_counts/
                              .bookkeeping/.stale_bookkeeping, stale_entries
                              redefined, 12 new KNOWN_GAPS, bar-style removed,
                              VISIBLE deleted, main() report
tools/omr/score_translation.py  the comment that pointed at VISIBLE
tools/omr/tests/              test_transcribe_helpers.py (2 classes),
                              test_export.py (TestOrnaments),
                              test_class_aliases.py (1),
                              test_export_coverage.py (3 classes, fixtures)
benchmarks/omr-export-gaps-2026-09/probe-ornaments-2026-09-08/
                              probe_ornament_reach.py, probe_export_ab.py,
                              probe_derived_coverage.py
```
