# The coverage instrument audited a 146-name snapshot of a 208-name class space

2026-09-21. Item 6 of the symbol-dossier sweep (`docs/symbol-dossiers/INDEX.md`
§3). No page was gathered, no export was run, **no OMR-NED figure is claimed**
and none would mean anything here: this is a repair to a MEASURING INSTRUMENT,
and the pipeline's output is byte-identical either way.

Base: `28749347` (`origin/claude/part-instrument-check-2026-09`).
Branch: `claude/class-space-208-2026-09-21`.

---

## 0. ASK FIRST — the unattended block

This lane touches no engraving convention: it is a question about two lists of
strings inside our own tree, both committed, both checkable. The one judgement
call that is *convention-shaped* is which class space a coverage tool should
audit, and it is recorded here rather than buried in the mechanism.

> **CONVENTION ASSUMED:** a coverage instrument must audit the vocabulary a
> CONSUMER can actually receive — the shipped 208 names **after**
> `class_aliases.canonicalize_names`, which `yolo_detector` applies at the one
> place the model's own `names` are read. 157 distinct names.
>
> **WHAT WOULD FALSIFY IT:** any consumer that reads a detection's class name
> BEFORE canonicalization, i.e. any reader of `model.names` other than
> `yolo_detector.py:296`. `canonicalize_names` has exactly one call site
> today. If a second appeared, the raw 208 would become the right space for
> that consumer and this repair would be half wrong.
>
> **NOT CONFIRMED WITH SEAN.**

A second, smaller one:

> **CONVENTION ASSUMED:** the three coarse families the repair newly surfaces
> (`articulation`, `numeral`, `tuple`) get the treatment `class_aliases`
> already records for them — `articulation` is a real articulation and is
> gathered; `numeral` and `tuple` state no ROLE and no NUMBER respectively and
> are deliberately unrouted.
>
> **WHAT WOULD FALSIFY IT:** a page where a bare `numeral4` is printed as a
> time signature and we need it. The repair does not make that worse — those
> classes reached no quantity before either — it only makes the gap VISIBLE.
>
> **NOT CONFIRMED WITH SEAN.**

---

## 1. REACH — what this measures, and what it needs

**Needs no weights, no library, no page.** Every figure below is a property of
committed files, so it reproduces in a cloud container:

```
python3 benchmarks/omr-class-space-208-2026-09/measure_class_space.py
python3 benchmarks/omr-class-space-208-2026-09/measure_class_space.py --verify-weights
```

`--verify-weights` is the manifest's own provenance check and **skips loudly**
when the checkpoint is absent, naming the path it wanted.

---

## 2. THREE CLASS SPACES, AND CONFLATING ANY TWO IS HOW THIS HAPPENED

| space | size | what it is |
|---|--:|---|
| **SNAPSHOT** `deepscores_classes.DEEPSCORES_V2_CLASSES` | **146** | the TRAINING dataset's list, consumed by `prepare_yolo_data.py` and `verdicts_to_yolo_labels.py` |
| **RAW 208** `class_aliases.vocabulary()` | 208 ids / **168** distinct | the committed manifest of the shipped checkpoint |
| **CANONICAL** what a consumer sees | **157** | RAW 208 after `canonicalize_names` |

`gather_coverage._detector_classes()` read the **SNAPSHOT**, under a docstring
that said, in terms, *"The 208-class space"*.

⚠️ **THE TWO DISAGREE ON SPELLING AS WELL AS ON LENGTH.** The snapshot spells
the clefs `gClef` / `fClef` / `cClefAlto`; the checkpoint spells them `clefG` /
`clefF` / `clefCAlto`, and carries a whole coarse block at ids 136-207 the
snapshot does not have at all.

**The manifest is exact.** Read from
`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt` and compared
index-for-index with `class_aliases.vocabulary()`: **identical, 208 of 208**,
and `class_aliases.unaccounted(shipped)` is empty.

---

## 3. THE MEASUREMENT — the two sets, per family

### SET A — checked, but cannot fire (15 names, 5 families)

| family | n | names |
|---|--:|---|
| `c` | 4 | `cClefAlto`, `cClefAltoChange`, `cClefTenor`, `cClefTenorChange` |
| **`dynamic`** | **6** | `dynamicForte`, `dynamicMezzo`, `dynamicNiente`, `dynamicPiano`, `dynamicRinforzando`, `dynamicSforzando` |
| `f` | 2 | `fClef`, `fClefChange` |
| `g` | 2 | `gClef`, `gClefChange` |
| `unpitched` | 1 | `unpitchedPercussionClef1` |

### SET B — shipped, never checked (26 names, 7 families)

| family | n | names |
|---|--:|---|
| `articulation` | 3 | `articulationAccent`, `articulationStaccato`, `articulationTenuto` |
| **`clef`** | **6** | `clefC`, `clefCAlto`, `clefCTenor`, `clefF`, `clefG`, `clefUnpitchedPercussion` |
| `grace` | 1 | `graceNoteAcciaccatura` |
| `notehead` | 3 | `noteheadFullSmall`, `noteheadHalfSmall`, `noteheadWhole` |
| `numeral` | 11 | `numeral`, `numeral0` … `numeral9` |
| `tremolo` | 1 | `tremoloMark` |
| `tuple` | 1 | `tuple` |

---

## 4. ⚠️ THE DOSSIER'S CLAIM IS HALF FALSE, AND THE FALSE HALF DECIDES THE REPAIR

The dossier says: *"it reports six dynamic classes that cannot fire and misses
the six that can."*

* **"six dynamic classes that cannot fire" — TRUE, and exactly six.** They are
  the `dynamic` row of Set A above.
* **"misses the six that can" — FALSE.** Against the canonical space the
  dynamics family's never-checked set is **EMPTY**. The six that look missing
  are `dynamicLetterF/M/P/R/S/Z`, which exist only in the RAW 208 and
  **cannot reach a consumer under those names**: `yolo_detector.py:296` applies
  `canonicalize_names`, and they arrive as `dynamicF/M/P/R/S/Z` — all six of
  which the 146-snapshot already contained and already checked.

**This is not a quibble; it is the design decision.** Had the repair been
*"read the 208"*, `ink_present_elsewhere()` would now report six
`dynamicLetter*` classes as live detector classes for `Q.DYNAMIC_LETTER` when
by construction not one of them can ever arrive — **a new false report in
place of the old one**. A mutation arm pins the direction
(`audit the RAW 208 instead of the canonical space`, red).

---

## 5. ⚠️ THE HEADLINE IS THE CLEFS, NOT THE DYNAMICS

`_family` splits a class name at the first camel hump. So the snapshot's
`gClef` yields family **`g`**, `fClef` yields **`f`**, `cClefAlto` yields
**`c`**, `unpitchedPercussionClef1` yields **`unpitched`**.

Those four families exist **only** under the snapshot's spelling. And
`FAMILY_TO_Q` carried an entry for each — three of them mapped to
`CLEF_GLYPH`. **So the table LOOKED like it named the clefs.** Meanwhile the
real `clef` family, as the tool saw it, contained exactly two members:

```
clef family in SNAPSHOT: ['clef15', 'clef8']     # the OCTAVE MARKERS
clef family in CANON   : ['clef15', 'clef8', 'clefC', 'clefCAlto',
                          'clefCTenor', 'clefF', 'clefG', 'clefUnpitchedPercussion']
```

A coverage instrument for a pipeline whose *documented ceiling is clef
reading* was auditing a `clef` family that held only `8` and `15`.

---

## 6. THE REPAIR — in the instrument, and it is one import

`_detector_classes()` now returns the canonicalized shipped vocabulary —
**157 names, id order, duplicates collapsed**.

**Why not the training data.** The brief predicted this and it holds: the
146-list is the TRAINING dataset's vocabulary. `prepare_yolo_data.py`,
`verdicts_to_yolo_labels.py` and `test_training_pipeline.py` consume it, and
`data/user-labeled/catalog-versions.txt` is a committed membership decision.
**`deepscores_classes.py` is untouched**; `test_training_pipeline.py` is green.

**The manifest already existed** — `training/deepscoresv2_208_classes.json`,
committed in `4b9976bb`, described by `class_aliases` as *"The committed
vocabulary of record … so tests need no weights file."* The repair is to read
it. `class_aliases` is `json` + `pathlib` only.

**The stdlib-only constraint is preserved and checked.** The old function used
an AST read to dodge the vision stack. Measured: importing
`tools.omr.staged.gather_coverage` and calling `_detector_classes()` pulls
**no cv2, no torch, no ultralytics** — asserted by a test that runs it in a
subprocess. (numpy does arrive, via the package init, and did so before this
change too.)

---

## 7. NEWLY SURFACED — three real families, each a recorded decision

With the space corrected, `gather_coverage` **exited 1** where it had exited 0.
**Control run first:** it exits 0 on the pre-repair tree, so this was new, and
it was *the instrument now seeing a real gap* — three families in the shipped
space that `FAMILY_TO_Q` had no entry for at all.

Each is mapped with a reason. **None is a suppression:** `numeral` and `tuple`
still print under **NO QUANTITY NAMES IT**; what changed is that the table now
records the decision instead of the build breaking.

**`articulation` (3 classes) -> `ARTICULATION_MARK`.** Verified at the EMIT
SITE, not inferred. `gather.py:884` routes on the prefix `artic`, which
`articStaccatoAbove` and `articulationStaccato` share, and files both under
`Q.ARTICULATION_MARK` with `side=_artic_side(name)`. The coarse names state no
side and that reader returns `None` rather than guessing. The ink IS named; it
arrives carrying one fact fewer.

**`numeral` (11 classes) -> `None`.** States no ROLE — one class for time
signatures, tuplet digits, fingerings and measure numbers alike
(`COARSER_THAN_CANONICAL`). CLAUDE.md records what a spurious `timeSig4`
costs: five fired on barline fragments and shipped a 2/4 page as common time.
`gather.py` routes none of them.

**`tuple` (1 class) -> `None`.** States no NUMBER. `_TUPLET_CLASSES`
(`gather.py:690`) is an explicit list and bare `tuple` is not in it, because
renaming it to `tuplet3` would assert a triplet the page never claimed. Its
sibling `tupleBracket` is absent here because `class_aliases` renames it to
`tupletBracket`, so it lands in `tuplet`.

**And four phantom entries removed** (`c`, `f`, `g`, `unpitched`) with a
do-not-restore note in the table, guarded by
`test_no_family_in_the_table_is_dead`.

After: **all seven derived checks exit 0** again.

---

## 8. ⚠️ PRIOR ART — this was diagnosed five days ago and routed around

`benchmarks/omr-gather-vocabulary-2026-09/probe_vocabulary.py` (2026-09-16)
says it in its own docstring:

> *"`gather_coverage._detector_classes()` reads `deepscores_classes.py`, whose
> `DEEPSCORES_V2_CLASSES` holds **146** names, under a docstring calling it
> 'the 208-class space'. … So that tool's family audit is derived from 70% of
> the vocabulary."*

**The diagnosis was right and the instrument was left broken.** The probe
CORRECTED for it locally and printed a delta. That is the repo's own
anti-pattern — a workaround in a benchmark, while every other consumer of the
instrument kept reading the wrong space. It also has **no FINDINGS.md**, only
`out-full.txt`.

⚠️ **AND THE PROBE'S OWN CORRECTION IS SLIGHTLY WRONG, in the direction this
repair identifies.** It uses the **RAW** 208 (168 distinct), not the canonical
157, so it reports *"families FAMILY_Q has no entry for: arpeggio,
articulation, leger, numeral, tuple"* — **five**. Two of those
(`arpeggio`, `leger`) are **fully aliased away** — `arpeggio` to `arpeggiato`,
`legerLine` to `ledgerLine` — and can never reach a consumer. The correct
count is **three**, which is exactly what the repaired instrument surfaced,
arrived at independently. That agreement-minus-two is the strongest
corroboration here and was not designed for.

**The probe is left as it is** (it is another lane's artefact and its case-(b)
repertoire work is untouched by this). Its delta section will now read zero,
which is the repair landing.

---

## 9. CONTROLS

* **Pre-repair derived checks:** all seven exit 0. **Post-repair:** all seven
  exit 0. The intermediate state (`gather_coverage` exit 1) was resolved by
  mapping the three real families, not by suppressing them.
* **Rule 4 — did this silence the scan?** `gather_coverage.py` does **not**
  declare `DERIVED_CHECK = True` (six sibling checks do). Tested empirically
  rather than reasoned: `wiring --check` output captured before and after via a
  verified byte swap of the file — **byte-identical, 75 lines, exit 0 both
  times**. This change added no detail-key reader and silenced nothing. The
  restore was md5-verified.
* **RED proof (deliverable 3):** the pre-repair file restored from `HEAD`, the
  new test file run against it — **5 failed, 6 passed**:
  `test_the_audited_space_is_the_canonical_shipped_vocabulary`,
  `test_it_is_not_the_training_snapshot`,
  `test_the_clefs_the_pipeline_reads_are_audited`,
  `test_the_clef_family_is_not_just_the_octave_markers`,
  `test_the_coarse_articulations_are_mapped_where_gather_files_them`.
  Then restored, md5-verified.
* ⚠️ **Why the existing guard could not catch it.**
  `test_every_detector_family_is_mapped` asserts `cs["classes"] > 100` — **and
  146 > 100**. A floor cannot catch a space that is the wrong space; only an
  identity can. Every test added here is an identity or a membership.

---

## 10. MUTATION BATTERY — 11 arms, 11 red

`mutate.py`, output in `out-battery.txt`. BYTE snapshot before arm 1, restore
verified by hash after every arm and at exit, in-flight sentinel, refuses a
dirty tree without `--force`, `PYTHONDONTWRITEBYTECODE=1`.

⚠️ **THE JUDGE IS ASSERTED TO BE ABLE TO FAIL, as a permanent self-test run
BEFORE any arm.** It mutates one character of whitespace — a mutant that
cannot change behaviour — and **requires it to SURVIVE**. A judge that reports
that red is measuring run-to-run noise and every red arm is worthless; that is
the failure two batteries in this repo actually had, by comparing pytest's
summary line, which ends `" in 0.57s"`. This judge instead requires a non-zero
exit **and** the arm's own NAMED test in the FAILED set. An anchor that does
not match exactly once is **MIS-ANCHORED**, an error, never a pass.

Result: **judge self-test PASSED, positive control GREEN, 11 of 11 arms RED,
restore verified, exit 0.** Arms: revert to the snapshot · audit the RAW 208 ·
drop the dedupe · identity-alias the canonicalizer · `articulation` to None ·
`articulation` to the wrong Q · drop `articulation` · drop `numeral` · drop
`tuple` · restore phantom `g` · restore all four phantoms.

---

## 11. WHAT IS NOT ESTABLISHED

* **No page, no export, no metric.** Nothing here shows the pipeline READS any
  of the 26 newly-checked names better, or at all. This repairs what the
  instrument can SEE. The output of a real run is untouched.
* **The 26 names in Set B are not thereby gathered.** `clefG` being audited
  does not mean clefs are read well — this project's documented ceiling is
  exactly that they are not. The repair means the coverage tool can now be
  ASKED about them.
* **`noteheadWhole`, `noteheadFullSmall`, `noteheadHalfSmall`, `tremoloMark`
  and `graceNoteAcciaccatura` are newly audited and NOT investigated.** They
  land in families (`notehead`, `tremolo`, `grace`) that already had a
  mapping, so they surfaced no build break — but nobody has checked whether
  the pipeline handles those specific spellings. `noteheadWhole` with no
  `InSpace`/`OnLine` suffix is the one most worth a look: that suffix is the
  staff-position distinction, and `COARSER_THAN_CANONICAL` does not currently
  record it.
* **Only ONE checkpoint was verified** against the manifest
  (`hollow-graft-shift09`, the shipped production file). `omr-weights/` holds
  six others; `class_aliases` claims all were verified on 2026-09-04 and this
  job did not re-check that claim.
* **The canonicalization argument rests on one call site.** It is true today
  (`canonicalize_names` has exactly one caller). A second reader of raw
  `model.names` would make the raw 208 correct for that consumer, and nothing
  currently fails if one appears — a gap this job did not close.
* **`gather_coverage.py` still does not declare `DERIVED_CHECK = True`** while
  `brakes`, `capture`, `meaning`, `reach`, `trace` and `wiring` do. Reported,
  deliberately not changed: it is a shared-file question for whoever owns the
  wiring scan, and changing it could move another check's findings.
* **No second opinion on the three mappings.** `articulation` was verified at
  the emit site; `numeral` and `tuple` rest on `COARSER_THAN_CANONICAL`'s
  reasons, which are arguments rather than measurements.
