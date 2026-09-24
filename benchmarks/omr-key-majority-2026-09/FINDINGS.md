# The key signature, read off the detector's boxes — ROADMAP 2.9

2026-09-23 · `claude/key-majority-2.9` · branched from `259773e5`

**One sentence.** `Q.KEYSIG_MARKER` — the detector's own key accidentals, on
the record since the staged pipeline was written and read by nothing — is now
the primary reader of the key signature; the header fitters corroborate it and
their disagreements are recorded; and a staff whose concert key stands alone
on its own system abstains rather than being written.

---

## 0. What this item was asked to be, and what it became

Sean decided on 2026-09-23 that *"a key signature is decided per SYSTEM by
MAJORITY of its staves, transposition-normalised; a tie abstains and carries"*
(`docs/DECISIONS.md`). Building it began there. The trace stopped it, and
Sean's second instruction — *"it seems like we don't even need the majority
rule … we just need to know what to do with the 3 boxes around the 3 flats on
every staff"* — is what shipped.

**The majority is not built, and the reason is a measurement.** On the
engraved acceptance page, normalised to concert pitch, the two readings split
**EIGHT to EIGHT** (eight treble staves reading one flat against six bass/alto
staves and two clarinets reading three): a majority would have been a coin
toss on the acceptance document's own count page. What the page actually held
was one reader counting **one** flat where the detector had already drawn
**three boxes** at score 0.91–0.94.

So the system rule shipped as a **CHECK THAT CAN FAIL**, not a vote
(`adjudicate_system_key` + `disagrees_with_system`). It never writes another
staff's value onto this one. §6 reports whether that leaves anything a
majority would have fixed.

---

## 1. Two defects, and only one of them was the rule

### 1a. The acceptance record could not exercise 2.2's rule at all

`benchmarks/acceptance/manifest.json` pointed at
`benchmarks/omr-staged-engraved-2026-09/out/engraved-p0p2.record.json`,
gathered on `7754d277` **with `dirty: True`** and before the document-identity
work. It carries **no `Q.INPUT_DOMAIN` row of any kind**, so
`_proved_engraved` answered False on every staff and roadmap 2.2's
engraved-template tier — the one measured at 47 of 50 — **never fired on the
very page the acceptance set scores**. Reasons over that record:

    fitted 30 · fitted_by_template 20 · markers_without_a_run 4
    fitted_by_template_engraved: 0

That is why the acceptance page failed a gate 2.2 had passed: 2.2's 47/50 was
measured on a record that carried the identity row, and the acceptance record
does not. It is not a regression in 2.2's rule; it is a rule that could not
reach the input.

Verify (one command):

    python3 benchmarks/omr-key-majority-2026-09/keyprobe.py \
        benchmarks/omr-staged-engraved-2026-09/out/engraved-p0p2.record.json

**Repaired by re-gathering** the fixture on today's tree
(`engraved-p0p2-20260923.record.json`, 6.6 MB against the old 17.7 MB — record
pooling, roadmap 1.1b). `Q.INPUT_DOMAIN` is now filed (`document → engraved`)
and 47 of 54 verdicts read `fitted_by_template_engraved`. The manifest's
engraved record path and md5 receipt are updated in this branch.

### 1b. The detector's boxes were read by nothing

`adjudicate_key_signature` declared `Q.KEYSIG_MARKER` in **both** `wants` and
`composed_from` from the day it was written. Every use was a DETAIL field
(`_marker_ink`), with a key literally called
`keysig_marker_count_is_not_a_reading`. On the re-gathered engraved page, p0
system 0:

| staff | label | markers (canonical x) | locator fit | template | verdict before |
|---|---|---|---|---|---|
| 0 | Flute 1 | 3 keyFlat @ 375/461/544 | `n=1 → −1` | `n=3 → −3` | −3 |
| 13 | Violin 1 | 4 keyFlat @ 375/461/**463**/545 | `n=1 → −1` | `n=3 → −3` | −3 |
| 4 | Bb Clarinet | 1 keyFlat @ 376 | `n=1 → −1` | `n=1 → −1` | −1 |
| 8 | Eb Horn 1 | none | — | `n=0 → 0` | 0 |

The locator reads **one** accidental on every treble staff of the page and
`n=3` on every bass/alto staff, which is the whole of the defect Sean saw. Its
own run positions say the same thing: `Q.KEYSIG_RUN_POSITION` is `[503]` — one
position — where the detector filed three boxes at 375, 461 and 544.

Verify:

    python3 benchmarks/omr-key-majority-2026-09/staff_table.py \
        benchmarks/omr-staged-engraved-2026-09/out/engraved-p0p2-20260923.record.json 0/0

---

## 2. The rule, in the order it runs

1. **Clef guard** — unchanged. No settled clef, no key (`needs_clef`).
2. **PRIMARY: the marker run** (`_marker_run`). The cell-0 `Q.KEYSIG_MARKER`
   rows, x-ordered, read as a ladder of **SLOTS** (convention `[C21]`: the
   accidentals stand at fixed slots in a fixed order, so the Nth is determined
   by N). *n* flats → −*n*, *n* sharps → +*n*.
   * two boxes within **0.5 cell staff spaces** are ONE slot. Violin 1's pair
     at x 461 and 463 is neighbour ink bled in through the cell's 4-space pad
     (CLAUDE.md §10); counting BOXES reads four flats.
   * the chain stops at a gap wider than **2.0 spaces**:
     `_gather_keysig_markers` reads `R.cell(p, s, i, 0)` — the whole first
     MEASURE — so an accidental printed inside bar 1 is in this population.
   * ABSTAINS with its own reason on `mixed_marker_kinds` (a standard
     signature carries one kind), `natural_markers` (a cancellation, which the
     record has nowhere to put), `too_many_markers` (> 7), and
     `no_cell_scale` (no `Q.CELL_STAFF_SPACE`, so the slot test has no unit —
     guessing the scale is how three flats become five).
   * ⚠️ the unit is `Q.CELL_STAFF_SPACE`, **never** `Q.STAFF_SPACING`: the
     marker x is `x_canonical`, and on one engraved staff those read 85 and
     22.5 px.
3. **The fitters corroborate.** An agreeing fit joins the basis; a disagreeing
   one is written into `detail["disagreeing_readers"]` with its reader and its
   fifths and is never dropped.
4. **Where the detector filed NO marker row**, the 2.2 precedence runs exactly
   as before — template first on a document measured engraved
   (`OMR_ENGRAVED_KEYSIG`), locator first otherwise — under one countable
   reason, `fitted_no_markers`, with the reader in `detail["decided_by"]`.
   ⚠️ This branch is why the marker rule is survivable on a scan: 80 of 331
   staves on Litolff and 145 of 691 on Breitkopf arrive here.
5. **SYSTEM CHECK.** `adjudicate_system_key` (`Kind.SYSTEM`, new
   `Q.SYSTEM_KEY`, ordered before `key_signature`) publishes the CONCERT keys
   its staves read and how many read each. A staff whose concert key has no
   peer abstains `disagrees_with_system`, and EXPORT writes no `<key>` — which
   in MusicXML CARRIES the part's last stated key.

### Transposition, and who may speak

Imported from `key_consensus`, never restated — `resolve_label` is made public
for it. A staff enters the check (as witness and as judged) only when

* its margin label resolves in the lexicon, **and**
* its transposition was **READ** from the label, not defaulted. ⚠️ The obvious
  test for that is wrong and `key_consensus` records why: comparing the
  matched offset against the instrument's default cannot tell *named B-flat*
  from *defaulted to B-flat*, because the default clarinet IS the B-flat one.
  Measured cost of getting it wrong on this very corpus: the engraved
  fixture's labels are `Eb Horn 1` and `C Trumpet 1`, and the lexicon defaults
  those to **+1** (horn in F) and **+2** (trumpet in B-flat) — both wrong for
  this page. A staff resting on a default may neither corroborate nor be
  contradicted.
* it is not an instrument that prints no signature by convention
  (`[C81]`, `NO_SIGNATURE_CONVENTION` = Timpani, Horn, Trumpet, Cornet,
  Flugelhorn) or one that may legitimately differ (`Harp`). A trumpet reads 0
  whatever the key; on Litolff three such staves per system would otherwise
  stand as a bloc disagreeing with the whole page.

**Why an absence is handled by the label and not by the ink.** A staff with an
empty header files no marker rows and the template answers `n=0 → 0`, which is
indistinguishable at the record from a staff nobody could read. The convention
registry's own answer is used instead (`[C81]`: *"which staves these are is
knowable from the margin label or the score order before any ink is read"*).

---

## 3. Where it lives, and why not in EVALUATE or INFER

`adjudicate_system_key` reads its staves' **marker and fit ROWS** through the
same `_staff_reading` the staff decision uses — never their key VERDICTS — so
`Q.KEY_SIGNATURE` is nowhere in `Q.SYSTEM_KEY`'s ancestry and the staff
decision may read it back as an ancestor fact. **There is no cycle and nothing
is superseded.** The reverse order (tally the verdicts, then revise them) is
the fixpoint `Log.record` refuses, and it is also the majority this item
deliberately did not build.

INFER was not available: it *"never overturns a DECIDED one"* (CLAUDE.md §4a),
and repairing Violin 1's one flat means exactly that. EVALUATE was not
available either: `check_downhill` requires the effect strictly after the
cause in `DOWNHILL`, and this cause and effect are one quantity.

`Ruling.narrow` was tried for `Q.SYSTEM_KEY` first **and is wrong here**: the
harness clears a candidate set of one (*"a single survivor is not a
narrowing"*), so a system whose staves AGREE — the common case and the
strongest possible evidence — came back ABSTAINED with nothing attached. The
value is a set instead: the concert keys more than one staff read.

---

## 4. Accuracy, on three real records

**The truth used for the two scans is a document-level fact, not a page
truth.** Beethoven 5 mvt 1 and Brahms 1 mvt 1 are both in C minor, so each
staff's printed signature follows from its instrument: −3 concert, −1 for a
B-flat clarinet, 0 for natural horn / natural trumpet / timpani on the
19th-century plates. A staff whose instrument the margin label does not name
is **not scored**.

    python3 benchmarks/omr-key-majority-2026-09/simulate.py <record> <truth>

| document | scored staves | fitters (before) | markers | markers + system check |
|---|---|---|---|---|
| engraved acceptance, 3 pages | 50 | **45 / 3 / 2** | **50 / 0 / 0** | **50 / 0 / 0** |
| Brahms 1, Breitkopf, whole mvt | 583 | **188 / 224 / 171** | **347 / 181 / 55** | **344 / 127 / 112** |
| Beethoven 5, Litolff, whole mvt | 200 | **91 / 37 / 72** | **101 / 52 / 47** | **92 / 33 / 75** |

(right / wrong / abstained.)

⚠️ **THE SYSTEM CHECK IS WHAT MAKES THE MARKER RULE SAFE, and the two scans
say so in the same direction.** On Breitkopf it converts **54 wrong readings
into abstentions for the price of 3 right** (181 → 127 wrong, 347 → 344
right); on Litolff, where the markers alone are a net loss, it takes the rule
from **52 wrong back to 33** — *better than the fitters it replaced* — again
by abstaining rather than by writing another staff's value.

⚠️ **The engraved column's `before` is the BASE ARM, not that record's own
verdicts.** The acceptance record was re-gathered on this branch and therefore
already carries the new rule, so `simulate.py` reads 50/0/0 in every column on
it. The 45/3/2 is `readjudicate.py --off all` over the same gather, which is
what "before" means here.

⚠️ **Litolff is the cost and it is not hidden.** That plate MERGES its ink, so
where the detector fires at all it under-counts a run it can see: markers
alone trade 25 abstentions for 10 more right **and 15 more wrong**, and it
takes the system check to bring that back under the fitters' wrong count. On
page 1 system 0 the Oboi, Fagotti, Violino II, Violoncello and Basso staves
each carry 2 marker boxes against three printed flats.

⚠️ **Breitkopf is the opposite and it is the larger population.** That plate
SHATTERS, which separates the flats and suits the detector.

⚠️ **The Brahms truth was CORRECTED by a crop, against its own dossier.**
`data/dossiers/brahms-sym1-mvt1.json` is generated from a MusicXML encoding
and says the timpani part is in −3; the plate prints no signature on that
staff at all (`out/print/breitkopf-p1-system0-header.png`, `Pk.`), which is
`[C81]` holding exactly as MOLA states it. CLAUDE.md §8 refuses an `encoding`
fact in any measurement path and this is the concrete instance: scoring
against the dossier charged every timpani staff of the movement as wrong.
Horn is left unscored because that page prints TWO horn keys. ⚠️ Brahms'
genuine key change at m191 and back at m217 is still not modelled, so systems
covering those bars are scored against the wrong value in EVERY column — the
same population on every side of the comparison.

### 4b. Which branch fired, per document

| branch | engraved (54) | Litolff (331) | Breitkopf (691) |
|---|---|---|---|
| `markers` | 48 | 169 | 457 |
| `fitted_no_markers` (locator) | 0 | 22 | 35 |
| `fitted_no_markers` (template) | 6 | 58 | 110 |
| `mixed_marker_kinds` | 0 | 10 | 17 |
| `no_evidence` | 0 | 48 | 70 |
| `needs_clef` | 0 | 24 | 2 |

Fit versus markers, where both spoke: **24 disagree / 6 agree** (engraved),
**45 / 31** (Litolff), **147 / 69** (Breitkopf). Every one of those
disagreements is on the record in `detail["disagreeing_readers"]`.

---

## 5. The engraved acceptance gate — 18 of 18

    python3 benchmarks/omr-key-majority-2026-09/report.py engraved --truth engraved

| | base (fitters) | arm (markers + check) | truth |
|---|---|---|---|
| key verdicts | 50 decided / 4 abstained | **54 decided / 0 abstained** | — |
| against truth | 45 / 3 / 2 | **50 / 0 / 0** | — |
| `<note>` | 672 | **672** | — |
| `<key>` elements | 20 | 18 | 18 |
| key CHANGES written | **2** (Violin 1 at m8, Violin 2 at m17) | **0** | 0 |
| `status_census` | balanced, `unaccounted: []` | balanced, `unaccounted: []` | — |

**The carry path exists and needed no export change.** `staged/export.py`
builds `<attributes>` from `_key_dict(run.fifths)`, and a `None` there makes
`_mxl_attributes_block` omit `<key>` entirely — under MusicXML's own rules the
part's last stated key then stands. Checked rather than asserted: in the base
arm the four abstaining staff-runs at page 2 emit an attributes block with a
clef and no `<key>`, and their parts keep −3.

    python3 benchmarks/omr-key-majority-2026-09/carry_check.py \
        benchmarks/omr-key-majority-2026-09/out/engraved-base.musicxml
    # P7/P8 Bassoon, P16 Viola, P17 Cello at measure 17: <key> OMITTED


Per part, the arm now writes: Flute ×2 −3, Oboe ×2 −3, Clarinet ×2 −1,
Bassoon ×2 −3, Horn ×2 0, Trumpet ×2 −3, Timpani −3, Violin ×2 −3, Viola −3,
Cello −3, Contrabass −3 — **18 of 18 against
`out/fixture/beethoven-sym5-mvt1-m1-24.musicxml`**, the encoding the page was
rendered from.

    python3 benchmarks/omr-key-majority-2026-09/fifths_table.py \
        benchmarks/omr-key-majority-2026-09/out/engraved-arm.musicxml

Before this branch the acceptance file wrote −1 on Flute ×2, Oboe ×2, Trumpet
×2 and Violin ×2 — eight parts wrong — because of §1a. With the record
re-gathered but the rule unchanged, six of those eight are repaired by 2.2
alone and the residue is **the two Violin parts, which the locator still reads
as one flat on pages 1 and 2**, written as spurious key changes at bars 8 and
17. The marker rule closes them.

---

## 6. Litolff and Breitkopf, base versus arm

    sh benchmarks/omr-key-majority-2026-09/run_scan.sh <record> <tag>
    python3 benchmarks/omr-key-majority-2026-09/report.py <tag> --truth <kind>

### 6a. Beethoven 5, Litolff, whole movement (331 staff-systems, 12 parts)

| | base (fitters) | arm (markers + check) |
|---|---|---|
| key verdicts | 212 decided / 119 abstained | 221 decided / 110 abstained |
| reasons | `fitted_no_markers` 212, `no_evidence` 76, `needs_clef` 24, `run_fits_no_slot_table` 19 | `markers` 144, `fitted_no_markers` 77, `disagrees_with_system` 28, `no_evidence` 40, `needs_clef` 24, `mixed_marker_kinds` 10, `run_fits_no_slot_table` 8 |
| `system_key` | 31 × `no_staff_read_a_key` (the readers are off) | 27 × `read`, 4 × `one_staff_only` |
| against the plate's key | 91 / 37 / 72 | **92 / 33 / 75** — the check takes the marker rule's 52 wrong back to 33 |
| `<note>` | 12,424 | **12,424** |
| `<key>` elements | 153 | 153 |
| **key CHANGES written** | **105** | **113** |
| **parts opening on the right key** | **11 of 12** | **6 of 12** |
| `status_census` | balanced, `unaccounted: []` | balanced, `unaccounted: []` |

⚠️⚠️ **LITOLFF IS THE DOCUMENT WHERE THIS RULE LOSES, AND IT LOSES ON THE
FILE.** Per staff the check holds the line — 37 wrong → 33 — but a PART's
key comes from its first system's reading, and on this plate the first
system's markers under-count: the base opens **11 of 12** parts on the
movement's key and the arm **6 of 12** (Oboe −2, Bassoon −1, Violin II −2,
Viola −2, Cello −2, Contrabass −1). The base's one error is the Viola at
−1, which is the staff `key_consensus`' own docstring was written about.

⚠️⚠️ **AND THE GATE IS NOT MET BY EITHER ARM.** Roadmap 2.9 asks
for *"0 key changes not printed on the plate"*, and Beethoven 5 mvt 1 prints
none at all: the base writes **105** spurious changes across 12 parts and the
arm writes **113**. The four the roadmap named from the 4-page record are a
small corner of it; over the whole movement this is the dominant key defect
and NEITHER arm touches it. One of the named four IS closed — Viola's `+7` at
m64 is gone — and Violin II's `+1` at m48 and Trumpet's `+1` at m82 both
survive.

**Why the system check does not reach it, measured rather than guessed.** Of
331 staff-systems, only **76 (23%)** can be stated in concert pitch at all —
the rest carry no resolvable margin label, or an instrument whose key the
label never named, or print no signature by convention. Of the 31 systems, 18
hold exactly one corroborated concert key, **12 hold none at all** (every
reading on them stands alone) and one holds three.

**And on the count page the check is not merely thin, it is INERT — because
the readers fail TOGETHER.** `out/print/litolff-p3-system0-header.png`: Flute,
Oboe and Clarinet all read one flat, which normalises to concert −1 for the
first two and −1 for the clarinet's own −1 written… so `system_key` reports
`{"corroborated": [-1], "tally": {"-1": 3}}` and every one of them is
CORROBORATED. That is CLAUDE.md §10 exactly — *two witnesses off the same
raster fall silent together* — and it is the reason a majority would not have
helped either: the majority would have been −1 too, and it would have written
−1 onto the staves that read −3.

**So the ranked next step is not a vote.** It is either the identity gap
(roadmap 2.6 — 131 of 331 staves cannot be normalised because nothing names
them) or a per-PART cross-system rule, which the convention registry already
states: `[C25 + L38]`, *"a part has many independent readings of one fact,
which a cross-system vote can reconcile"*, implemented on the LEGACY path as
`key_signature_vote.reconcile` and **deliberately unconsumed** by the staged
path. 105 changes over ~500 bars in a movement with none is a per-system
reading that nothing holds to its own part's history.

### 6b. Brahms 1, Breitkopf, whole movement (691 staff-systems, 14 parts)

Run with `run_scan_lean.py` (§ below); 5,447 s end to end.

| | base (fitters) | arm (markers + check) |
|---|---|---|
| key verdicts | 484 decided / 207 abstained | **545 decided / 146 abstained** |
| reasons | `fitted_no_markers` 484, `no_evidence` 185, `run_fits_no_slot_table` 20, `needs_clef` 2 | `markers` 405, `fitted_no_markers` 140, `disagrees_with_system` 57, `no_evidence` 64, `mixed_marker_kinds` 17, `run_fits_no_slot_table` 6, `needs_clef` 2 |
| `system_key` | 53 × `no_staff_read_a_key` (the readers are off) | **53 × `read`** |
| against the plate's key | 188 / 224 / 171 | **344 / 127 / 112** |
| **parts opening on the right key** | **11 of 14** | **14 of 14** |
| `<note>` | 23,145 | **23,145** |
| `<key>` elements | 635 | 689 |
| **key CHANGES written** | **265** | **212** |
| `status_census` | balanced, `unaccounted: []` | balanced, `unaccounted: []` |

**CONTROL: 691 of 691 clef verdicts and 691 of 691 key verdicts reproduced**
(outcome + value) with the readers off; the reasons moved
`fitted → fitted_no_markers` 261, `fitted_by_template → fitted_no_markers`
223, `markers_without_a_run → no_evidence` 121.

Every part now opens on what the plate prints — Flute −3, Oboe −3, Clarinet
−1, Bassoon −3, Contrabassoon −3, Horn 0 ×2, Trumpet 0, Timpani 0, Violin −3
×2, Viola −3, Cello −3, Contrabass −3 — against the base's Flute −2, Violin II
−1 and Cello −1. **The clarinet part writes ONE `<key>` and no change at all
over 511 bars**, which is the transposition surviving the check intact.

⚠️ **212 spurious changes remain and the movement prints two.** The direction
is right (−53) and the level is not: this is the same per-system instability
§6a diagnoses on Litolff, and the same lever — `[C25 + L38]`, a part's own
cross-system history, which the staged path does not consume. What the arm
DOES show is the real one surfacing: seven parts write `+2` at m197, which is
the genuine −3 → +2 change the dossier puts at m191, read off the plate rather
than off the file.

---

## 7. The controls, and that they can fail

`benchmarks/omr-key-majority-2026-09/readjudicate.py --control` is in two
halves because one of them cannot fail alone:

* **`clef` must reproduce exactly.** It is not under test, so a mismatch means
  the log was rebuilt wrongly and every number here measures this harness.
  Result: **54 of 54** (engraved), **331 of 331** (Litolff).
* **`key_signature` with `--off all` must reproduce every VALUE.** `--off`
  returns the two new readers to the nothing they produced before. Result:
  **331 of 331** (Litolff) and **691 of 691** (Breitkopf), with the reason
  movement printed separately
  and not counted as a failure — `fitted_by_template_engraved -> fitted_no_markers`
  `fitted_by_template -> fitted_no_markers` 108, `fitted -> fitted_no_markers`
  104, `markers_without_a_run -> no_evidence` 36 (Litolff);
  `fitted -> fitted_no_markers` 261, `fitted_by_template -> fitted_no_markers`
  223, `markers_without_a_run -> no_evidence` 121 (Breitkopf).

⚠️ **AND IT DEMONSTRABLY FAILS WHEN IT SHOULD.** The engraved acceptance
record was RE-GATHERED on this branch, so its own verdicts already carry the
new rule — and `--off all` against it reports **47 of 54 reproduced, 7
differ** (`-3(decided) -> None(abstained)` 4, `-3(decided) -> -1(decided)` 3),
which is the comparator catching exactly the change under test. Rule 7: a
control that has been seen to fail where it should is worth more than one
that has only ever passed.

    python3 benchmarks/omr-key-majority-2026-09/run_scan_lean.py \
        benchmarks/omr-staged-engraved-2026-09/out/engraved-p0p2-20260923.record.json tmp

⚠️ **Blind to GATHER**, like every tool of its shape. The marker rows this
item reads were already being gathered, which is why this instrument is the
right one — but the re-gather in §1a is a GATHER change and `readjudicate`
cannot see it. That half was measured by gathering the fixture twice.

---

## 8. What the derived checks say

    python3 -m tools.omr.staged.check      # 254 open, every part `ok`

`256 → 254`: two `KNOWN_GAPS` entries closed by removing `Q.DOSSIER_FACT` from
`key_signature`'s `wants`, which nothing read; both stale entries removed from
`inventory.KNOWN_GAPS` and `wiring`'s list so they stop describing history.
`inventory --check`, `wiring --check`, `reach`, `brakes --check` and
`conventions --check` all exit 0. `health` reports no empty cells for
`system_key`.

`pytest tools/omr/tests -m "not slow" -q`: **2841 passed, 3 skipped**
(2216 deselected), 136 s.

---

## 9. Tests, run RED first

`tools/omr/tests/test_staged_key_from_markers.py` (20 tests) was run against
`259773e5` before the rule existed: the marker tests failed with the verdict
reading the header fitter's value, and the system-check tests failed because
`Q.SYSTEM_KEY` did not exist. The transposition test **passed for the wrong
reason** on the unrepaired tree (nothing was normalising anything, so nothing
could flatten it), which is why it is paired with a case that MUST supersede.

Two existing test files record a rule this item overturned, and both are
rewritten rather than deleted:

* `test_keysig_marker_ink.py`'s `TestItIsNeverAVALUE` asserted that markers
  may never decide a key, on two measurements — seven spurious legacy key
  flips, and the marker count matching the settled `|fifths|` on only 39% /
  51% of decided staves. **Both numbers stand; what changed is which side they
  condemn** (§4). The class is now `TestTheCountBECAMETheReading` and it keeps
  the half that still protects the old warning: the overruled fit must be
  recorded.
* `benchmarks/omr-keysig-staged-reach-2026-09/check_arm.py` armed the
  2026-09-21 rule that reading the markers may only SPLIT AN ABSTENTION
  REASON. It now asks the REGISTRY whether `markers_without_a_run` is still a
  declared reason and prints **SUPERSEDED** (exit 2) when it is not — a live
  check, not a comment: restore the reason and the arm runs again. Its four
  controls collapse into one, because an arm for a rule the tree no longer
  holds cannot have live controls, and leaving them red would report a
  replacement as a regression.

---

## 10. Crops for Sean

    python3 benchmarks/omr-key-majority-2026-09/crop_system_headers.py \
        --record <record> --pdf <edition> --page <n> --dpi 600 --label <tag>

One crop per system header of each count page, under `out/print/` (not
`crops/`, which `.gitignore` excludes), at the gather's own DPI, behind a
frame control that can FAIL: every staff's recorded `Q.STAFF_LINES` must be
materially darker than a half-space off them, and a system that fails is
refused rather than cropped with a caveat. Each crop draws every staff's five
recorded lines in green, a ruler of staff spaces down the left edge, and a
caption naming, per staff, **the name our file gives it and the fifths we
wrote**. The manifest carries `VERDICT_none_yet: null`.

**The question for Sean is one line on every crop:** how many sharps or flats
does the plate print at the head of each staff?

| crop | systems | frame contrast | verdicts in the caption |
|---|---|---|---|
| `out/print/litolff-p3-system{0,1}-header.png` | 2, 0 refused | 155.7, 50.1 | the ARM (this branch's rule) |
| `out/print/breitkopf-p1-system{0,1}-header.png` | 2, 0 refused | 213.5, 103.5 | the SHIPPED record (pre-2.9) |

⚠️ The two documents' captions come from different records and each crop says
which in its own header line and in `verdicts_from`. The question — what the
PLATE prints — is the same either way; *"we wrote"* is not.

**One of them already answers a question, and it corrects a truth file.**
`breitkopf-p1-system0-header.png` is legible without adjudication: `Fl.`,
`Ob.`, `Fag.`, `K.-Fag.`, `1.Viol.`, `2.Viol.`, `Br.`, `Vcl.` and `K.-B.` each
carry **three flats**, `Klar. (B)` carries **one**, and `Hr. (C)`, `Hr. (Es)`,
`Trpt. (C)` and **`Pk.` carry NONE**. The dossier generated from the encoding
says the timpani part is in −3 (`data/dossiers/brahms-sym1-mvt1.json`), and
the plate prints no signature on it at all — `[C81]` holding exactly as MOLA
states it, and a concrete instance of CLAUDE.md §8's refusal of an `encoding`
fact in a measurement path. `simulate.py`'s `BRAHMS1` table is corrected to 0
for timpani on that evidence; the horns are left unscored because that page
prints two different horn keys.

⚠️ The Litolff crop is the opposite case and is NOT adjudicated here: on that
MERGING plate the flats run together at 600 dpi and counting them from a
render is exactly the judgement this crop exists to put in front of a human.

---

## 11. Open, and what it is not

* **Litolff still loses staves to detector under-counting** that the template
  used to read (§4). The lever is the DETECTOR on a merging plate, not this
  decision — and no derived check can see it (CLAUDE.md §4d).
* **A staff with no resolvable margin label cannot enter the system check** at
  either end: 131 of 331 Litolff staves and 108 of 691 Breitkopf staves. That
  is the same identity gap roadmap 2.6 is about; it bounds this check's reach
  and is not a defect in it.
* **`natural_markers` is a declared refusal with nowhere to go.** A run of
  naturals is a cancellation and the record has no quantity for one.
* **No print check of the keys themselves yet.** §4's truth is the movement's
  key, which is a strong document-level fact and not a reading of the plate.
  §10's crops are the instrument for turning that into one, and until Sean
  fills in `VERDICT_none_yet` nothing here has been adjudicated against print.

---

## 12. The verdict across the three documents, stated plainly

| | parts opening right | key changes written (plate prints) | per-staff wrong |
|---|---|---|---|
| engraved acceptance | 10/18 → **18/18** | 2 → **0** (0) | 3 → **0** |
| Brahms 1 / Breitkopf | 11/14 → **14/14** | 265 → **212** (2) | 224 → **127** |
| Beethoven 5 / Litolff | **11/12 → 6/12** | 105 → **113** (0) | 37 → **33** |

`<note>` is unchanged on all three (672 / 23,145 / 12,424) and every
`status_census` is balanced with an empty `unaccounted`.

**Two documents improve sharply and one regresses on the file.** Over the two
scans' 783 scored staves the wrong count falls **261 → 160**, and on the
engraved acceptance page the gate is met exactly. Litolff is the MERGING
plate: its flats run together, the detector under-counts them, and a PART
takes its key from its FIRST system — so a first-system under-count costs a
whole part even where the check repairs the staves after it.

⚠️ **The separating property is the PLATE, not the domain, so a 2.2-style
gate would not split these two scans**: Breitkopf is a scan too and it is
where the markers win biggest. There is no measured `merging vs shattering`
fact in the record to gate on, and inventing one here would be a flag with no
roadmap item and no measurement behind it.

**Recommendation, for Sean or the coordinator to take or refuse:** ship it.
The evidence is 2 of 3 documents clearly better, the worse one better per
staff and worse per part, and every wrong reading now carries its own
disagreeing reader on the record so the Litolff loss is diagnosable rather
than invisible. The named next step for that loss is not this decision: it is
the detector on a merging plate, and `[C25 + L38]`'s per-PART cross-system
rule, which would fix the first-system dependence on every document at once.
