# Symbol dossier — accidentals & key signatures

**2026-09-20.** Nine detector classes plus three CV readers plus one span that
has no representation at all. Written to the template in
[README.md](README.md); every figure carries its file and its n.

This family is unusual in two ways and both shape everything below.

1. **The same ink has two class names, on purpose.** `accidentalFlat` and
   `keyFlat` are the identical glyph in two grammatical ROLES. DSv2 encodes the
   role; the detector, which sees one cell at a time, is the worst-placed thing
   in the pipeline to decide it.
2. **A printed accidental is a SPAN, not a mark.** It governs its letter+octave
   to the barline. The staged record has nowhere to put a span, so the in-bar
   accidental is the largest detector family in the class space with **no
   gather quantity of its own** (`gather_coverage`: *"accidental — 8 classes —
   no quantity names this family"*,
   `benchmarks/omr-shared-records-2026-09/out/gather_coverage.txt:70`).

---

## The one-paragraph headline, because it is the same fault in every section

**On the staged path a printed accidental reaches no file, and a key-signature
alteration reaches the file as a PRINTED accidental with no sounding
alteration.** On the committed cleanup-count artefact Sean read
(`benchmarks/omr-cleanup-count-2026-09/out/beethoven5-mvt1-p1-p4-2026-09-17.musicxml`,
Litolff Beethoven 5 mvt 1, pdf pp.1-4): **3,005 `<note>`, 1,610 pitched,
`<alter>` = 0, `<accidental>` = 334** (302 flat, 32 sharp, 0 natural), 36
`<fifths>`. A real score inverts that ratio — the Mahler reference in
`benchmarks/omr-one-line-staves-2026-09/derived-truth/` holds 177 `<alter>`
against 83 `<accidental>`, because most alterations come from the key signature
and are *not* printed.

A note in that staged file looks like this, verbatim:

```xml
<note>
  <pitch><step>E</step><octave>5</octave></pitch>
  <duration>192</duration><voice>1</voice><type>half</type>
  <accidental>flat</accidental>
</note>
```

It SOUNDS E natural and PRINTS a flat sign. **MEASURED HERE** (the file above,
n = 334 such notes on 4 pages). Mechanism, read from the tree:
`consequences.restate_pitch` writes a plain diatonic name (`_pitch_from_position`
returns letter+octave only), `consequences.respell_accidental` writes the
alteration into a *separate* quantity `Q.ACCIDENTAL`, and
`staged/export.py:790` hands that to `_legacy._mxl_note(accidental=…)`, which
renders it as the printed glyph. Confirmed with a one-second probe calling
`_mxl_note('B4', …, accidental='b')` directly — see *Probes used* at the end.

**This is export gap #7 running backwards.** `export_coverage.py:24` records the
seventh gap as *"printed accidentals — folded into `<alter>`, `<accidental>`
dropped"*, closed on the legacy path at `d112052`. The staged path drops the
other half.

**And the check that would catch it exists and is pointed elsewhere.**
`export_coverage.compare` reports any in-measure element the truth has and we
have zero of, after rollup — `<alter>` qualifies exactly, and rollup would not
absorb it because `<note>` and `<pitch>` are both present. Its inputs are the
eleven engraved fixtures exported by the LEGACY `export.to_musicxml`, which does
emit `<alter>`; **no caller anywhere in the tree feeds it a file written by
`staged/export.py`** (`grep -rln export_coverage benchmarks/ tools/`: twelve
hits, none of them a staged export arm).

---

## accidentalSharp

The ♯ printed before a notehead, altering that note and every later note at the
same letter+octave until the barline. Detector classes **63 / 172** in the
208-class space (an exact twin at two ids — a name lookup sees both). Bravura
template: **2.80 × 1.00 staff spaces**
(`tools/omr/symbol_library/data/manifest.json`, em 120 px, space = 30 px).

### 1. What sets it apart — and what it is confused with

`docs/position-grammar-confusables-2026-09-04.md` is Sean's own Q1 table and
**it has no row for an accidental.** Its alphabet is dot / arc / wedge /
horizontal stroke / vertical stroke / digit / bowl-blob; accidentals appear only
in R2, as the family-closure note that *"an accidentals family must include the
key-signature twins {keySharp, keyFlat} — the literally identical glyph"*. So
this section **adds a missing row** rather than disagreeing with one. A sharp
is a *vertical-stroke pair crossed by two horizontal strokes* — it belongs in
the VERTICAL STROKE row, where only stem-vs-barline is currently written.

| confused with | why | where measured |
|---|---|---|
| **two short stems** | a sharp is two parallel verticals ~0.5–0.7 sp apart and ~2 sp tall — *exactly* a pair of short stems, and `detect_stems` reported them as such. `line_detection._drop_paired_strokes` exists only for this. | its own docstring: summed \|error\| **60** over 14 hand-counted cells, and on two Mahler cells the stem count read 16 and 14 against a truth of 5 and 3 |
| **a natural, cross-staff** | the same ink detected in two staves' cells through the 4–6 space padding, and the two staves disagree about which glyph it is | `benchmarks/omr-additive-vs-gated-2026-09/out/contests/`, 20 scan-gate pages: **4 of 198 accidental contests are sharp↔natural** |
| **a `keySharp`** — the role, not the shape | one cell cannot see whether the glyph stands after the clef or before a note | `benchmarks/omr-keysig-blindspot-2026-08/FINDINGS.md`: on Beethoven 5 p.15 staff 0, at conf 0.25, `keyFlat` = **0** and `accidentalFlat` = **3** |
| **a `accidentalDoubleSharp`** | 2 of 198 contests are doubleSharp↔sharp on one piece of ink | same contest table |

⚠️ **The detector reads sharps measurably worse than flats or naturals.** Over
the contested glyphs of the 20-row scan gate: `accidentalSharp` median
confidence **0.649** (n = 54) against `accidentalFlat` **0.831** (n = 205),
`accidentalNatural` **0.815** (n = 111), `noteheadBlackInSpace` **0.818**
(n = 805). **MEASURED HERE**, same contest table. ⚠️ The population is
contested glyphs only, which is not a random sample.

### 2. Best method: YOLO / CV / other

**YOLO for FIND, grammar for ROLE.** This is R1/R3 of the confusables doc and
this family is the strongest case for it: the model gets the glyph right and the
role wrong, measured (the 0-vs-3 above). What no method here currently does is
*attach* it — see §4.

**Not the CV header readers.** `key_signature_template.ACCIDENTAL_GLYPHS` is
`(("b","accidentalFlat"), ("#","accidentalSharp"))`, and its search is bounded
between the clef and the meter, so it cannot see an in-bar accidental by
construction.

### 3. Where on the page the deciding information lives

Two constraints, and the registry entry `[L32]` says they are both required:
**SIDE** (immediately left of the head it alters) and **HEIGHT** (at that head's
staff position). *"The height constraint alone rules out most mis-attachments in
a dense chord"* — `docs/engraving-conventions.md`, *An accidental stands BEFORE
its note, at the same staff position*, status **LITERATURE ONLY, not measured
here**.

⚠️ **The per-family position layer skipped this family.**
`benchmarks/omr-family-positions-2026-09/FINDINGS.md` lists ten families with a
position fact (rest, time, tuplet, articulation, fermata, ornament, arc,
dynamic, wedge, direction). **Accidental is not one of them**, and `key` maps to
`Q.KEYSIG_RUN_POSITION`, the per-staff header run. So the one layer built to
answer "where does this family sit" has no row for an in-bar accidental —
`OMR_FAMILY_POSITIONS` is default OFF and has no consumer anyway.

### 4. Stage by stage

| stage | what happens | evidence |
|---|---|---|
| **GATHER** | one anonymous `Q.GLYPH_BOX` row, like any detection. **No `Q.ACCIDENTAL_*` of any kind.** | `grep -rn 'Q\.ACCIDENTAL' tools/omr/staged/` → 6 hits, none a gather site |
| **ADJUDICATE** | **nothing.** No decision takes an in-bar accidental as a subject. | `adjudicate.REGISTRY` has 28 decisions; none names one |
| **EVALUATE** | `respell_accidental` writes `Q.ACCIDENTAL` — but its cause is `Q.KEY_SIGNATURE`, not a printed glyph | `consequences.py:417-465` |
| **INFER** | nothing. Three rules exist: two duration, one slot index | `staged/inferences.py`, `@rule` ×3 |
| **EXPORT** | `rec.value(Q.ACCIDENTAL, sub)` → `<accidental>`. A printed sharp contributes nothing | `staged/export.py:790` |

⚠️ **`Q.ACCIDENTAL` has exactly ONE writer** (`consequences.py:460`), so every
`<accidental>` in a staged file is a key-signature respelling and **not one is a
glyph the page prints.**

⚠️ **The rule's own guard is dead.** `respell_accidental` skips a note *"that
already carries one"* — `if log.verdict(Q.ACCIDENTAL, pitch.subject) is not
None`. Nothing else ever writes that verdict, so on a single pass the guard
fires zero times. The docstring states the correct rule (*"an inline accidental
is bar-scoped AND pitch-scoped and OVERRIDES it"*); the branch that would honour
it has no input. **This is the `part_partition` shape from
`docs/RESUME-HERE-2026-09-20.md` §1.2 — a docstring stating a rule the body
cannot reach — arriving in a second decision.**

**The legacy path DOES read it**, and correctly:
`transcribe._pair_accidentals_to_noteheads` (`transcribe.py:932`) pairs each
accidental to the nearest head at or right of its right edge, within **0.6 ×
the accidental's own height** in y, scoring `x_dist + 3·y_dist`. ⚠️ The y window
is measured against the *accidental's own box height*, which is the unit the
augmentation-dot work already paid to abandon (*"the dot's own bounding box is
small and mostly detector noise"*, `[C51]`). The join has **never been priced as
a geometry** (`[L32]`, status *not measured here*).

### 5. Abstain or best-guess — and what leans on it

**(a) Can it abstain? There is nothing to abstain.** On the staged path no
decision has an in-bar accidental as a subject, so there is no verdict, no
abstention and no recorded refusal — *the breakthrough doc's §2 exactly: ink
outside the domain of every decision in the system*. On the legacy path
`_pair_accidentals_to_noteheads` abstains silently: an accidental with no head
to its right simply produces no entry, and nothing counts those.

**(b) What leans on it.** The pitch of every later note at that letter+octave in
the bar. A missed sharp is not one wrong note; it is every subsequent note on
that step in the bar, a semitone out. **Independence: bad.** The accidental, the
notehead it attaches to and the staff grid it is measured against all come off
the same raster, so a plate that loses the sharp usually also loses its head —
*the bars are not an independent umpire over a bad reading*, applied here. The
one genuinely independent witness is the **tie self-check** (`[C21]`): a tie
whose two ends resolve to different pitches proves the scope rule was not
applied, and it needs no truth file. Measured at
`benchmarks/omr-tie-pairing-2026-09/FINDINGS.md`: **11 of 20 engraved and 11 of
the scan cases are same-STEP, accidental-differs** — and there it was the
probe's fault, not the pairing's, which is itself the convention showing through.

---

## accidentalFlat

The ♭ — a bowl with a thin ascender. Detector classes **59 / 170** (exact twin).
Bravura **2.47 × 0.90 staff spaces**.

### 1. What sets it apart — and what it is confused with

It is the one member of the family with a **strongly asymmetric ink
distribution**, and the pipeline uses that: `key_signature_locator.
_accidental_shape` measures the share of ink below the box's middle, with
`FLAT_SHAPE_THRESHOLD = 0.62`, *"a flat is a bowl with an ascender… a sharp is
two horizontal bars crossed by two verticals, balanced about its centre"*.

⚠️ **That is exactly the shape of a stem-up notehead**, and nothing in this
repo has measured the collision. A stem-up note's head sits at the bottom of its
bounding box with a thin stroke above — bottom-heavy, well past 0.62.
**ASSERTED** (derived from the shipped constant and the Bravura metrics, not
measured). What bounds it is the locator's size gate
(`min_height_spaces 1.10 … max_height_spaces 3.60`) against stem lengths of
**2.16 → 6.78 sp, median 3.93, n = 1,919**
(`benchmarks/omr-stem-ink-2026-09`): a head plus a median stem is ~4.9 sp and is
rejected, a head plus the shortest stems is ~3.2 sp and is not.

| confused with | why | where measured |
|---|---|---|
| **a natural, cross-staff** | **15 of 198** accidental contests on the 20-row scan gate are flat↔natural — the single commonest cross-class disagreement in this family, ~4× commoner than sharp↔natural | `benchmarks/omr-additive-vs-gated-2026-09/out/contests/` |
| **a G clef** | outline correlation puts a flat against a `gClef` at **0.57–0.59** against real flats' **0.65–0.76** — *"too close to separate by score"*, which is why the template search is bounded rather than thresholded | `benchmarks/omr-first-run-2026-08/KEY_SIGNATURES.md` |
| **a hollow notehead** | the reverse direction, measured live: two accidental glyphs (*"a flat's loop, a natural"*) were detected as hollow heads over empty-and-correct human verdicts | `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/CONFLICT_REVIEW.md` |
| **a `keyFlat`** — the role | **8 of 198** contests are `keyFlat`↔`accidentalFlat` on one piece of ink: two staves, two roles, same glyph | the contest table |

### 2. Best method

**YOLO finds it well.** Median confidence **0.831** on contested scan glyphs
(n = 205), level with black noteheads. **Template matching finds it when the
detector does not**: on Beethoven 5 p.1, given the correct clef, the
connected-component locator reads **2 of 12** staves and the Bravura template
reads **11 of 12** (`KEY_SIGNATURES.md`) — but only inside the header window.
**There is no template pass for an in-bar flat anywhere in the tree.**

### 3. Where on the page

Same SIDE + HEIGHT rule as the sharp. One flat-specific fact the repo already
knows and does not use downstream: *"a flat's bowl is centred while its ascender
rises a full space above, so a flat's box centre sits well above the note it
alters"* (`key_signature_geometry.py` module docstring). In the header this is
solved by solving for **one shared anchor offset across the run**; for a lone
in-bar flat there is no run, and no correction is applied at all.
`docs/engraving-conventions.md:411` states the general form: *"taking a
bounding-box centre for everything is wrong for at least clefs, flags, whole
rests and the flat sign."*

### 4. Stage by stage

Identical to `accidentalSharp` — no quantity, no decision, no export.

### 5. Abstain / leans

Same as the sharp. One flat-specific asymmetry: on the Litolff plate the printed
key is three FLATS, so `respell_accidental` writes **302 flats against 32
sharps** into the cleanup artefact, and 302 of the 334 wrong `<accidental>`
elements Sean would have to delete are flats.

---

## accidentalNatural

The ♮ — the narrowest glyph in the family. Detector classes **61 / 171**.
Bravura **2.70 × 0.67 staff spaces** — two thirds the width of a sharp and the
only member that is *narrow*.

### 1. What sets it apart — and what it is confused with

**Width is the discriminator nobody uses.** 0.67 sp against the sharp's 1.00 and
the flat's 0.90 is a 33% gap, and it is the only purely metric separation in the
family. **MEASURED HERE** from the committed template manifest; **never
exercised in any reader**.

⚠️ **The locator cannot name it at all, by construction.**
`_accidental_shape`'s own docstring: *"Sharps and naturals measure close to 0.5
by construction (they are symmetric about their centre)"*, and
`fit_key_signature` takes `accidental` ∈ {"#", "b"}. So a natural is either
called a sharp or not called.

| confused with | why | where measured |
|---|---|---|
| **a flat** | 15 of 198 cross-staff contests | contest table |
| **a sharp** | 4 of 198 | contest table |
| **two short stems** | a natural is also two verticals joined by two horizontals; when the pair rule ate a real stem the partner was **a natural 7 times, a flat 5, a sharp 2** — naturals are the commonest accidental partner | `benchmarks/omr-stem-pair-rule-2026-09/FINDINGS.md` §3 |

### 2. Best method

YOLO reads it as confidently as a flat (median **0.815**, n = 111). A width gate
would be free and is untried. CV shape analysis is measurably the wrong tool
here: the one feature the locator has (bottom-heaviness) is *designed* not to
separate it from a sharp.

### 3. Where on the page

Side + height, as above. **Plus one role the family's other members do not
have**: a run of naturals in the HEADER is a *cancellation* signature, at the
slots of the key being cancelled.

### 4. Stage by stage — and the natural is the family's clean zero

| | |
|---|---|
| in-bar natural | no quantity, no decision, no export — as above |
| `keyNatural` (header) | gathered into `Q.KEYSIG_MARKER` (`gather.py:2090`, `_KEYSIG_CLASSES = ("keySharp","keyFlat","keyNatural")`) and **read by nothing** |
| legacy header | filtered out at every site: `_detect_key_sig_from_cell` selects only `startswith("keysharp")` / `("keyflat")` |
| export | `_MXL_ACCIDENTAL` has `"natural": "natural"`, and `Q.ACCIDENTAL` only ever takes `"#"` or `"b"` — **0 `<accidental>natural</accidental>` in the 334** |

⚠️ **A cancellation signature reads as the key it cancels.** Naturals cancelling
three flats are printed at the *flat* slots, so the locator's position pattern
fits the flat zigzag and returns **−3** where the page says *"back to none"*.
**ASSERTED** — derived from `key_signature_locator.py:395-412` and the slot
tables; no page in the corpus has been checked for one. `keyNatural` appears
**zero times** in 4,521 contests across 20 scan pages, so this repo has no
evidence it has ever been detected.

### 5. Abstain / leans

**(a)** The header path abstains honestly (`no_run` / `run_fits_no_slot_table`).
The in-bar path has nothing to abstain. **(b)** A natural is the one accidental
whose job is to *cancel*, so a missed natural leaves the earlier alteration
standing — the same damage as a missed sharp, but the carry makes it silent. The
tie self-check reaches it; nothing else does.

---

## accidentalDoubleSharp

The 𝄪 — a small saltire. Detector classes **65 / 173**. Bravura **1.00 × 1.00
staff spaces**: **the only square glyph in the family, and the only one under
1.1 sp tall.**

### 1. What sets it apart — and what it is confused with

Size and aspect alone separate it from everything else here, cleanly and
without position. That is unusual in this repo and worth saying plainly.

| confused with | why | where measured |
|---|---|---|
| **a notehead** | 1.00 × 1.00 sp is a notehead's own size band (genuine heads 0.60+ sp tall, `_drop_clipped_notehead_fragments`) | `docs/position-grammar-confusables-2026-09-04.md`, BOWL/BLOB row |
| **an `accidentalSharp`, cross-staff** | 2 of 198 contests | contest table |
| **a staccato / augmentation dot** at low resolution | both are small compact marks; no measurement exists | ASSERTED |

⚠️ **It is below the header locator's own floor.** `min_height_spaces = 1.10`
against 1.00 sp, so a double sharp in a header window is rejected as too small
whatever else is true of it. Harmless for key signatures (which never contain
one) and a hard stop for any future reuse of that reader.

### 2. Best method

Undetermined and probably a size gate rather than a classifier. **Reach first:
this glyph appears 2 times in 4,521 cross-staff contests across 20 scanned pages
and 0 times in every other committed artefact searched.** It is rare in this
repertoire. Do not invest here before measuring reach on a chromatic work.

### 3. Where on the page

Side + height, as all inline accidentals.

### 4. Stage by stage

No quantity, no decision, no export — as above. Two partial paths exist and both
are dead ends:

* `transcribe._parse_inline_accidental` maps it to `"##"` and
  `export._MXL_ACCIDENTAL` maps `"##"` → `double-sharp`, so the **legacy** path
  is complete for it.
* The **symbol library ships an `accidentalDoubleSharp` template at three em
  sizes** (`manifest.json`) and nothing loads it —
  `key_signature_template._templates` requests only the clefs, `accidentalFlat`
  and `accidentalSharp`.

### 5. Abstain / leans

**(a)** Nothing to abstain. **(b)** Nothing reads it; a missed double sharp is
one wrong note plus its scope. The mark's own rarity is its bound.

---

## accidentalDoubleFlat

The 𝄫 — two flats side by side. Detector classes **66 / 174**. Bravura **2.43 ×
1.67 staff spaces** — nearly **twice** the width of a single flat and the widest
glyph in the family.

### 1. What sets it apart — and what it is confused with

Width, and only width: its height is within 0.04 sp of a single flat's.

| confused with | why | where measured |
|---|---|---|
| **two adjacent flats** of a key signature | the template reader keeps **one candidate per x-column** at `column_merge_spaces = 0.7` sp; two flats of a signature are set closer than a double flat is wide | `key_signature_template.py` config; ASSERTED that they collide, not measured |
| **an `accidentalFlat`, cross-staff** | 2 of 198 contests | contest table |
| **a flat plus a notehead** merged into one component | 1.67 sp is inside the locator's `max_width_spaces = 1.70` by 0.03 sp — a merge that widens it *at all* falls out of the gate | derived from `key_signature_locator.KeySignatureLocatorConfig` |

⚠️ That 0.03 sp margin is the tightest constant-to-glyph clearance found
anywhere in this family, and on a plate where *"Litolff MERGES"* (median cell's
largest component holds 46% of its ink,
`docs/breakthrough-2026-09-18-the-unit-of-enquiry.md` §6) a merged double flat
is outside the gate.

### 2. Best method

As the double sharp: reach before accuracy. 2 occurrences in 4,521 contests.

### 3. Where on the page

Side + height.

### 4. Stage by stage

No quantity, no decision, no export. `_parse_inline_accidental` → `"bb"`;
`_MXL_ACCIDENTAL["bb"]` → `flat-flat` (the correct MusicXML token). Template
ships and is unloaded.

### 5. Abstain / leans

As above.

---

## accidentalSharpSmall / accidentalFlatSmall / accidentalNaturalSmall

The cautionary-sized or grace-sized accidental. Detector classes **60, 62, 64** —
and note what is NOT there: **the coarse block of the 208-class space carries the
five plain accidentals a second time (ids 170–174) and carries NO `*Small`
twin.** So a `*Small` class has exactly one id, where its full-size sibling has
two. **MEASURED HERE** from `data/user-labeled/catalog.yaml`.

### 1. What sets it apart — and what it is confused with

**Size, relative to the cell's other accidentals** — and the repo already has
the shape of that rule from a neighbouring family: *"a grace head is smaller
than its neighbours (41×38 px against 51–83 in the same cell)"*
(`docs/position-grammar-confusables-2026-09-04.md`, BOWL/BLOB, recorded as the
one untried route). Nothing equivalent has been tried for accidentals.

Its role is the harder half. A small accidental is one of:

| role | what it means for the music |
|---|---|
| **courtesy accidental** | real ink that changes nothing — `[C26 + L35]` |
| **grace-note accidental** | alters a grace note, not the main note |
| **editorial accidental** | often parenthesised; a separate glyph family per `[C26]` |

⚠️ **The courtesy case has no figure anywhere in the tree.**
`docs/engraving-conventions.md`, *A courtesy accidental is real ink that changes
nothing*: status **ASSERTED**, *"no figure anywhere in the tree… the repo file
searched `benchmarks/` and `tools/` and found none"*, and its frequency is a
property of the EDITION rather than of the music.

### 2. Best method

Neither, today — the question is the ROLE and the role is a parenthesis or a
size ratio, both of which are grammar. ⚠️ **A size gate needs the cell's own
accidentals as its reference**, which is the same in-cell-relative form the
grace-head lead proposes. There is no in-cell accidental population on the
staged path to compute a ratio against, because there is no quantity.

### 3. Where on the page

Same side and height as a full-size accidental. The parentheses, when printed,
are the decisive ink and nothing in the class space names them.

### 4. Stage by stage — and this is where the *Small variants are actively wrong

| stage | what happens |
|---|---|
| **GATHER (staged)** | one anonymous `Q.GLYPH_BOX` |
| **legacy pairing** | ⚠️ **treated as a full accidental.** `_parse_inline_accidental` tests `s.startswith("accidental")` then `"sharp" in s` — so `accidentalSharpSmall` → `"#"`, indistinguishable from a printed full-size sharp |
| **header readers** | invisible: the symbol library ships **no `*Small` templates** (manifest holds exactly `accidentalFlat`, `Natural`, `Sharp`, `DoubleSharp`, `DoubleFlat`), and the locator's `min_height_spaces = 1.10` sits above a reduced glyph |
| **EXPORT** | via the legacy path only, as a full accidental with no `size="cue"` and no parentheses |

⚠️ **So on the legacy path a courtesy accidental and a real one are the same
fact**, and since a courtesy accidental restates what is already in force it is
harmless *if* the scope rule is right and *wrong* if a grace accidental is
mistaken for the main note's. Neither direction is measured.

### 5. Abstain / leans

**(a)** No. There is no branch that says *this mark is small and I cannot tell
what it is for*. **(b)** The legacy exporter's LilyPond arm actually leans on
this: `_pitch_to_lily` appends `!` where an accidental was READ, *"because a
COURTESY accidental restates what the key signature already implies and is
exactly what the derivation drops (the 3: A-flats restating the key on three
Brahms staves)"* (`export.py:468-476`). **Measured**: 62 of 65 recorded glyphs
re-print from pitch alone; the 3 that do not are courtesies. So the courtesy
population *is* visible there, at n = 3.

---

## keySharp / keyFlat / keyNatural — the key-signature RUN

Detector classes **67 (keyFlat), 68 (keyNatural), 69 (keySharp)** — fine block
only, **no coarse twin**, unlike the five plain accidentals. All three map to
detector category `accidental` (`yolo_detector._CATEGORY_MAP`).

**This is not a glyph fact. It is a POSITION-SET fact**, and the repo says so in
its own words: *"READ THE POSITIONS, DO NOT COUNT THE GLYPHS… the Nth accidental
is fully determined by N — the reader's job is to count and locate, never to
identify each accidental's letter"* (`[C22 + L36 + L37]`).

Three readers produce it, and a fourth reconciles it on the legacy path only:

| reader | what it does | where |
|---|---|---|
| the DETECTOR's `keySharp`/`keyFlat` markers | glyph boxes in the staff's first cell | `gather._gather_keysig_markers` → `Q.KEYSIG_MARKER` |
| `key_signature_locator` | thresholds the header to an ink mask, clusters, keeps accidental-sized runs | → `Q.KEYSIG_CLEF_FIT` + `Q.KEYSIG_RUN_POSITION` |
| `key_signature_template` | slides the Bravura `accidentalFlat`/`accidentalSharp` templates in a window bounded by the clef and the meter | → `Q.KEYSIG_TEMPLATE_FIT` |
| `key_signature_vote.reconcile` | pools readings across systems for one part | **legacy only** — imported by `transcribe.py` and by nothing under `staged/` |

### 1. What sets it apart — and what it is confused with

**The run is the evidence, not the glyph.** Members are the same size and shape,
evenly spaced, in a short run after the clef. `_candidate_runs` breaks a run on a
wide gap *or a change of glyph size*, `size_tolerance = 0.35` — *"the gate that
rejects a stem, then a notehead, then a rest"*.

| confused with | why | where measured |
|---|---|---|
| **an in-bar accidental in the header cell** | the header cell contains music as well as the header; *"one inline accidental inside the header cell, and three flats read as four"* | `key_signature_geometry.py` docstring; and on Litolff **one of the three `decided_by: shape` readings sits on a header that prints nothing** — a spurious run of one, `benchmarks/omr-keysig-truth-2026-09/FINDINGS.md` §4 |
| **the clef** | a flat's outline correlates with a `gClef` at 0.57–0.59 vs real flats' 0.65–0.76; matched over a whole header it produced *a column of eleven "flats" at one x* | `KEY_SIGNATURES.md` |
| **the time signature's digits** | why the template's right bound is `locate_time_signature` | `key_signature_template.py` |
| **the margin label and the systemic rule** | ⚠️ the sharpest one, and it is a WINDOW fault rather than a glyph fault — see §3 | `benchmarks/omr-keysig-truth-2026-09/FINDINGS.md` §5 |
| **noteheads further into the bar** | `max_start_after_clef_spaces = 2.00` exists because *"reading one as a lone accidental is the locator's easiest way to invent a key signature that isn't there"* | `key_signature_locator.py` |

⚠️⚠️ **The role confusion is measured in both directions.** Downward: on
Beethoven 5 p.15 the model finds the flats and calls them `accidentalFlat`, so
the key-signature path — which consumes only `keyFlat`/`keySharp` — discards
them before anything positional runs (`keyFlat` **0**, `accidentalFlat` **3**,
at conf 0.25). Upward: **8 of 198** cross-staff accidental contests pair a
`keyFlat` against an `accidentalFlat` on one piece of ink, i.e. the detector
itself assigns both roles to the same mark seen twice.

⚠️ **The fix for the downward direction was built, measured and REFUSED**:
routing `accidentalFlat` into the key-signature fit took beet5-p2 from **10
correct to 9**, pastoral-p2 9 → 9, wtc-p17 10 → 10
(`benchmarks/omr-keysig-blindspot-2026-08/FINDINGS.md`). The missing constraint
it names is positional — *only accidentals left of the first notehead can be a
signature* — and that x-cut is still not applied.

### 2. Best method: all three, and they are COMPLEMENTARY not ranked

**MEASURED HERE**, Litolff pp.1-4, 75 printed staves against Sean's hand-read
print truth (`benchmarks/omr-keysig-truth-2026-09/FINDINGS.md`):

| reader | decides correctly |
|---|--:|
| `key_signature_locator` (CV ink clusters) | **16** |
| `key_signature_template` (Bravura NCC) | **28** |

*"On page 1 the template reads all twelve staves right and the locator two; on
page 2 system 0 the locator reads five right and the template four different
ones."* They fail in **opposite directions** — the locator loses accidentals to
broken ink and under-counts, the template can match spurious ink and
over-count — which is why the precedence is *gaps only, locator first*, and why
the two are filed under separate quantities.

⚠️ **The precedence is inherited, not chosen.** Letting the fuller reading win
is already priced on the legacy path: *"+1 on beet5-p2 and +2 on the Pastoral
and a WRONG reading on the cleanest page in the corpus"*.

**Cost of the second reader, measured**: 48 calls, **2.06 s** against the
locator's 2.23 s on a 12-staff page — GATHER's key-signature stage roughly
doubles, ~2 s per page.

### 3. Where on the page the deciding information lives

**The header strip, clef → key → meter** (`[C23 + L40]`, Gould p.152). Each
reader's window is bounded by the others' results, which turns a 2-D search into
a 1-D one.

⚠️⚠️ **The single largest defect measured in this family was the WINDOW, not any
reader.** On Litolff p2 system 1, **all eleven header windows measured 6.1–6.2
staff spaces against 16.00 everywhere else**, and held the margin label and the
systemic rule and no music. Cause: `measure_header_window` took the system's left
edge from the **MINIMUM** of one estimate per staff, and one staff under-ran its
ten siblings by ~70 px (estimates 331, 345, 345, **263**, 334, 334, 335, 347,
336, 336, 346). `system_left_edge`'s own docstring asserted the invariant that
makes a minimum safe — *"can only ever be too far right and never too far
left"* — **and it is false.** Repaired by anchoring the margin on the MEDIAN
(`system_left_consensus`): windows with a `barline` right edge **12 → 1**, the
eleven windows 6.2 → 16.0 sp, **no other window moved**.

⚠️ **And it made the two readers fail in different-looking ways with one cause.**
The locator abstained; the template found a *clean* window and answered a
confident `fifths: 0` — **a key signature fabricated out of a crop containing
none**, on a system printing three flats on eight staves. *The reader that can
say "zero" is the one that must never be given an empty window.*

One more position fact the repo knows and uses: **positions come from the ink
centroid inside the matched box, not the box centre** — box centres leave ±0.5
step of jitter, *"enough for the fit to read three flats as five"*.

### 4. Stage by stage

| stage | what happens | rows, Breitkopf Brahms 1 pp.0-3 (97 staves) |
|---|---|--:|
| **GATHER** | `gather_key_signature` asks BOTH CV readers **once per candidate clef** (`_SLOT_TABLE_CLEFS`), because the reader returns `None` when the fit fails and discards the boxes it already found | `keysig_marker` **146**, `keysig_run_position` **41**, `keysig_clef_fit` **130**, `keysig_template_fit` **108** |
| **ADJUDICATE** | `adjudicate_key_signature` (`adjudicators/header.py`) reads the fit for the clef that WON; template answers gaps only | **76 decided**, 20 `no_evidence`, 1 `run_fits_no_slot_table` |
| **EVALUATE** | `respell_accidental` — the key settles, so this staff's notes carry its alterations | `accidental` **671** verdicts against `pitch` 4,828 |
| **INFER** | nothing | — |
| **EXPORT** | `<key><fifths>` per staff-run; `_key_dict(None)` returns None, so an abstained staff gets **no `<key>` at all** | — |

Litolff pp.1-4 (75 staves), for comparison: `keysig_run_position` **37 observed
/ 38 abstained**, `keysig_marker` 105 rows
(`benchmarks/omr-family-positions-2026-09/out/reach-litolff-p1p4.json`).

**The reading, graded against print truth** (Litolff pp.1-4, 75 staves):

| | correct | wrong | abstained |
|---|--:|--:|--:|
| READING, locator alone | 16 | 10 | 49 |
| READING, + template into gaps | **35** | **15** | **25** |
| FILE, before → after | 33 right → **44** | 42 → 31 | — |

⚠️ **17 of the 33 "right" rows are abstentions that happen to land on a horn,
trumpet or timpani** — instruments that print no signature by convention
(`[C81 + L39]`, MOLA). Right in the file, for the wrong reason. **A count of
parts reading −3 is not the score.**

⚠️ **`Q.KEYSIG_MARKER` is declared in `wants` and never read** — the detector's
own key accidentals are a THIRD reader, on the record, consumed by nothing
(`out/inventory-run.txt:81`; `reach.KNOWN_GAPS` calls it an inert declaration).
So is `Q.DOSSIER_FACT`.

⚠️ **`DETAIL Q.KEYSIG_RUN_POSITION.clefs_tried` is written and unread**
(`wiring.py:548`). It separates two states the abstention collapses — *a run
that fits NO table* and *a header with no run at all* — and the comment at the
write site says so.

⚠️⚠️ **Three `checked_by` claims on `adjudicate_key_signature` do not run, and
one of them names the wrong pipeline.** It declares *"a key CHANGE is printed on
every staff at the same bar (key_signature_corroboration — CONSUMED,
default-ON)"*. **Verified by grep: there is exactly one import of
`key_signature_corroboration` in the tree and it is in `transcribe.py`.** The
staged path mentions it in three docstrings and imports it nowhere. So:
`docs/RESUME-HERE-2026-09-20.md` §1.2 is **right**, and CLAUDE.md's
`OMR_KEYSIG_CORROBORATION` row is right *about the legacy path* and wrong if
read as a statement about the staged one. The flag is real, default-ON since
2026-09-07, measured at **7 of 7** spurious mid-staff flips stopped on the scan
corpus — **in `transcribe`**. ⚠️ And its own known limit stands: *the corpus
contains ZERO real mid-staff key changes*, so only the benefit is measured.

⚠️ `mode` is hard-coded `major` in `_mxl_attributes_block`, so a three-flat
signature exports as E♭ major on a movement in C minor.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) It abstains, in four named ways, and one of them is a contradiction
rather than a gap.**

| reason | what it means |
|---|---|
| `needs_clef` | the clef abstained, so there is no slot table. **The guard moved; it was not removed** — `key_signature_locator.py:310` is `if not clef: return None` |
| `no_run` | the run was read and fits nothing |
| `no_evidence` | no run at all |
| `run_fits_no_slot_table` | ⚠️ the run fits SOME slot table but not the settled clef's — recorded as a **contradiction**, with both `clef` and `fits` in the detail |

⚠️ **Two refusals are load-bearing and neither may be relaxed casually.**
*It may not INFER*: `key_signature_template` returns `None` the moment
`fit_key_signature` fills a slot, because *"five matches on one staff were
fitted as SEVEN sharps"* and letting it stand took WTC p.17 from 10 correct to
5 correct and 5 wrong. *It may not CARRY across systems*:
`StaffCandidate.can_carry` keeps an over-count on its own staff, because one
staff's spurious fifth sharp was otherwise carried onto every treble staff of
five systems.

⚠️ **And the abstention is invisible in the file.** A staff whose key abstained
exports no `<key>`, which is C major to any reader —
`benchmarks/omr-unknown-keysig-2026-08/FINDINGS.md`: *"nothing downstream can
tell 'this staff is in C major' from 'nobody could read this staff'. Both arrive
as `<fifths>0</fifths>.'"* On Beethoven 5 p.2, 22 staves carrying notes, a
signature was read on 10 and **12 were exported as C major**. This is the
ABSENT/DECLINED collapse in the music rather than the metadata.

**(b) What leans on the key signature — three consumers, one of them upstream.**

1. **Every pitch on the staff.** `consequences.respell_accidental` re-spells
   them. `benchmarks/omr-keysig-truth-2026-09/FINDINGS.md` §10 names this edge
   and **explicitly does not measure it**: 12 more staff-systems settle a key on
   those four pages and what that does to the pitches was never checked.
2. **The CLEF, upstream.** `adjudicate_clef` reads `Q.KEYSIG_CLEF_FIT` at
   `W_KEYSIG_FIT = 1.5` and contributes it **only when the fit
   discriminates** — a run that fits every candidate is recorded in `declined`
   so silence cannot read as support. **The direction is clean and is not a
   cycle**: the run's POSITIONS are clef-free GATHER rows → the clef verdict →
   the key verdict. `Q.KEYSIG_TEMPLATE_FIT` is deliberately kept *out* of the
   clef contest, asserted by a test with a positive control, because a second
   reader's rows would silently double that evidence's weight.
3. **The cross-system redundancy group** `key_signature_across_systems`
   (`groups.py:889`), which compares the WRITTEN key of one part across systems.
   On Brahms pp.0-3 it **disagrees on 10 of 27 facts** (4 split, 6 majority)
   against `clef_across_systems`' 2
   (`benchmarks/omr-shared-records-2026-09/FINDINGS.md`, *"three findings this
   record hands on"* item 3 — *"the key-signature reader is the weaker of the
   two on this document"*).

**Independence — and on the page that was measured, it is GOOD in one direction
and BAD in the other.**

*Good:* the clef and the key do **not** fail together on the reading. Over the
same 75 staves the clef reads **68 correct / 6 abstained / 1 wrong**, and *all
ten wrong key readings sit on a staff whose clef was read CORRECTLY.* The one
wrong clef produced an abstention, not a wrong key. The documented *"the reader
inherits the clef problem"* is true as a mechanism and is **not** what is
happening on this document.

*Bad, three ways:*

* the 6 abstained clefs cost 6 key signatures by construction (`needs_clef`);
* the header CROP is a **shared upstream failure**: the eleven broken windows
  cost the clef *and* the key at once, one cause, two symptoms that look
  unrelated;
* the natural second witness — a cross-system vote — **is deliberately not
  built**, and the reason is a third quantity: **12 of 75 staff-systems are
  joined to the wrong instrument**, so a vote keyed on that join would carry the
  **Viola's seven sharps onto the Timpani's part**. It already does, in the
  file: `P7`, the part reading `fifths 7`, is the Timpani's part carrying a
  reading taken from the Viola. **The key signature's next gain is downstream of
  the part join, not of any key reader.**

⚠️ One refused redundancy is worth restating because it will be re-proposed:
**a key signature across the staves of ONE system is refused** — transposing
parts genuinely print different written keys at the same bar, and on the Litolff
page `-3`, `-1` and `0` all stand in one system. What IS redundant across a
system is the POSITION of a key CHANGE, and `ASSUMPTIONS.md` **D18** records
that the group cannot be built because nothing emits a mid-staff key change as a
measurement.

⚠️ **The narrower witness set that WOULD work is measured and unwired.**
`tools/omr/key_consensus.py` establishes the concert key from concert-pitch
staves (`chromatic % 12 == 0`, never `== 0` — Contrabass is −12, an octave) and
deduces each staff's written key as `concert + fifths_offset`: **10 of 12 staves
predicted exactly** on Beethoven 5 p.1, and the two failures are the same single
convention (natural brass and timpani print none). False-positive rate over 152
orchestral encodings: **5.9%**. **It is imported by nothing but its own tests.**

---

## The accidental's SCOPE — the span with no quantity

Not a glyph. The fact that a printed accidental governs its letter+octave to the
barline, and across a barline through a tie. `[C21 + L33 + L34]`, status RIGID,
Wikipedia *Accidental (music)*.

### 1. What sets it apart

It is the only member of this family that is not ink. **The absence of a mark is
a positive statement about pitch** — a later notehead at the same letter+octave
inherits the alteration with no glyph of its own, and a reader that attaches an
accidental only to its immediate note reads every later note in the bar a
semitone wrong.

### 2. Best method

Neither YOLO nor CV. It is bookkeeping over a left-to-right walk, and the legacy
path does it correctly.

### 3. Where the information lives

In the **order of the glyphs within the bar**, and in the **barline** that ends
it. The legacy implementation gets the barline for free: `explicit_in_measure` is
a dict created per CELL, and a cell is a measure. ⚠️ That also means the scope is
**exactly as good as the measure segmentation** — two bars merged into one cell
carry an accidental too far; one bar split into two resets it early. Unmeasured.

### 4. Stage by stage

| stage | what happens |
|---|---|
| **GATHER** | nothing. `gather_coverage.FAMILY_Q_IS_ELSEWHERE` says why, verbatim: *"it is SCOPE rather than a mark: it holds to the barline (`transcribe.py:2210` implements exactly that), which is a span the record has nowhere to put"* |
| **ADJUDICATE** | nothing |
| **EVALUATE** | `Q.ACCIDENTAL` exists but its cause is the KEY, not a printed glyph |
| **INFER** | nothing |
| **EXPORT** | nothing |
| **legacy** | `transcribe.py:2211-2267`, a four-level precedence: inline > carried-in-measure > key signature > diatonic. Keyed on `(letter, octave)` |

⚠️ **The cross-barline TIE half is not implemented on either path.** The
convention says an accidental continues through a tie into the next bar;
`explicit_in_measure` is rebuilt per cell and nothing consults the tie flags.
The consequence is measured from the other side:
`benchmarks/omr-tie-pairing-2026-09/FINDINGS.md` — **11 of 20 engraved links and
11 scan links are same-STEP, accidental-differs**, `F#4 → F4` pairs, *"the
accidental-EXPIRY artifact, not a different note"*. `export._tie_flank_pair`
compares STEPS, never spelled pitches, precisely so the expiry does not break a
truth-matched tie (+21 engraved edits when it did).

⚠️ **This is the clearest case in the whole record where the missing quantity is
a SPAN.** Two siblings share the shape and are named in
`docs/exploration-what-is-on-the-page-2026-09-09.md` §A: `ottava` (a span that
shifts every note under it by an octave — *"highest damage-per-instance of
anything in this list"*) and the accidental. A `Kind.CELL`-scoped span quantity
would serve both.

### 5. Abstain / leans

**(a)** There is nothing to abstain — the walk always produces an answer, and
where no accidental was read it produces *diatonic*, which is a definite answer
where *cannot tell* would be honest. **This is the repo's own governing rule
violated in the music rather than in the metadata**: *a fallback must never
convert "cannot tell" into a definite answer.*

**(b)** Everything downstream that reads a pitch. And the tie check is the one
truth-free consumer that can catch it.

---

## Where this dossier disagrees with, or adds to, existing documents

1. **`docs/position-grammar-confusables-2026-09-04.md` has no accidental row.**
   Its alphabet covers dot / arc / wedge / horizontal stroke / vertical stroke /
   digit / bowl-blob; the accidental is a vertical-stroke-plus-bowl mark and
   belongs in it. The doc's R2 already says the family must be closed over
   {accidentalX, keyX}; the alphabet itself was never extended. **Addition, not
   disagreement.**
2. **CLAUDE.md's `OMR_KEYSIG_CORROBORATION` row reads as a statement about the
   pipeline and is true only of the legacy one.** `RESUME-HERE-2026-09-20` §1.2
   is correct: one import, in `transcribe.py`. **Agreement with §1.2, explicit
   disagreement with the CLAUDE.md row as phrased.**
3. **`benchmarks/omr-family-positions-2026-09` has no accidental family.** Its
   ten families exclude it, and its `key` row is the per-staff header run, not a
   per-accidental position. The manager's note that *position is rarely a rule by
   itself* is exactly right here: for an accidental, position (SIDE + HEIGHT
   relative to a head) is close to the whole rule, and it is the one family the
   position layer skipped.
4. **The brief's Q1 asks about "sharp vs natural (very close shapes)".** On the
   only measurement available, **flat↔natural is the commoner confusion**
   (15 of 198) and sharp↔natural is 4 of 198. The sharp's real weakness is
   detector confidence (0.649 vs 0.83), not shape confusion with a natural.
5. **`benchmarks/omr-stem-notehead-gate-2026-09` §5a is confirmed and worth
   repeating here**: the pair rule's first fixture,
   `benchmarks/omr-phase4-lines/reference-lines.ly`, **prints no accidental at
   all in 48 stems** — so the rule's cited win there was never a measurement of
   accidental rejection. On the plate where it was measured, of the 244 strokes
   it deletes, **57 (23.4%) are paired with an accidental glyph** and
   **62 of the 80 that carry a notehead (77.5%) are two genuine stems eating
   each other**. `OMR_STEM_NOTEHEAD_GATE` is default OFF.

---

## What we do not know

* **Accuracy of the in-bar accidental, anywhere.** No page has been read against
  the print for accidentals. Every figure above is REACH, a class count, or a
  cross-staff contest.
* **Whether the missing `<alter>` changes the notes as much as it looks.** 334
  notes on four pages carry a printed accidental with no sounding alteration; a
  reader that honours `<alter>` hears them wrong, and nothing has scored that.
* **The courtesy-accidental rate, per publisher.** Zero figures in the tree;
  `[C26]` is ASSERTED on both sides.
* **Whether a cancellation (naturals) signature has ever been detected.**
  `keyNatural` is 0 in 4,521 contests over 20 scan pages, and no reader can name
  one.
* **What a size gate would be worth for the `*Small` variants.** No reach figure
  for them exists.
* **The double sharp and double flat outside two contests each.** Reach unknown;
  this repertoire is mostly C minor and 6/8.
* **n throughout.** Litolff `984073` pp.1-4 (75 staves) and Breitkopf `317803`
  pp.0-3 (97 staves) are two scans of two publishers; the contest table is 20
  scan-gate rows. The engraved family is untouched here.
* **Whether the ten wrong key readings would change under a better window.** The
  window repair and the template wiring were priced together, not apart.

## Questions for Sean

1. **`<accidental>` on a key-altered note.** We currently print a flat sign on
   every note the key signature alters, and write no `<alter>`. I read the
   engraving convention as: *the key signature's alteration is not printed at
   all on the note*. Is that right without exception in this repertoire — or is
   there a case where an engraver restates it that is not a courtesy?
2. **The role split.** `keyFlat` and `accidentalFlat` are the same ink. Is there
   ever a printed accidental *inside the header window* (after the clef, before
   the first note) that is NOT part of the signature? If not, the x-cut the
   blindspot work named is safe and the role question dissolves into position.
3. **Cancellation signatures.** Does this repertoire print naturals to cancel a
   key at a change, or does it just print the new signature? If cancellations
   are rare here, `keyNatural` can stay unread with a recorded reason rather
   than as a gap.
4. **Small accidentals.** When you clean up a page, does a courtesy accidental we
   invented cost you the same as one we missed, or less? That decides whether
   the `*Small` classes are worth a size gate at all.
5. **The scope span.** If we build one span quantity, it serves the accidental
   and the ottava. Is there a third span in this repertoire worth designing for
   at the same time (pedal? 8va bassa? a `loco`)?
6. **The 44-of-75 key page.** The measured next lever is the part join, not a
   key reader. Do you want the key work held until the join is right, or is a
   staff-level key reading useful to you even in a part that is grafted?

---

## Probes used

One, and it took under a second. `python3 -c` calling
`tools.omr.export._mxl_note('B4', …, accidental='b')` and again with `'Bb4'`,
to confirm that a plain pitch string plus a separate accidental renders
`<pitch><step>B</step><octave>4</octave></pitch>` with **no `<alter>`** and
`<accidental>flat</accidental>`. Nothing was gathered, transcribed or scored.
The same shape was then confirmed on the **committed** artefact
`benchmarks/omr-cleanup-count-2026-09/out/beethoven5-mvt1-p1-p4-2026-09-17.musicxml`
by `grep -c`, which is where the 0 / 334 / 36 figures come from.

Everything else is read from the tree or from committed benchmark outputs:
`benchmarks/omr-additive-vs-gated-2026-09/out/contests/` (20 files, 4,521
contests), `benchmarks/omr-shared-records-2026-09/out/` (Brahms record
inventory), `benchmarks/omr-family-positions-2026-09/out/reach-*.json`,
`tools/omr/symbol_library/data/manifest.json`, `data/user-labeled/catalog.yaml`.
