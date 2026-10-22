# Clefs — what sets each one apart, and where the pipeline decides it

**2026-09-20.** One section per symbol, five questions each, per
[the template](README.md). Read with
[the stage charter](../stage-charter-2026-09-18-what-each-stage-does.md) and
[the unit-of-enquiry breakthrough](../breakthrough-2026-09-18-the-unit-of-enquiry.md).

Three documents already answer parts of this and are cited rather than
re-derived: Sean's own mark alphabet
([position-grammar-confusables](../position-grammar-confusables-2026-09-04.md)),
the per-family position sweep
([omr-family-positions FINDINGS](../../benchmarks/omr-family-positions-2026-09/FINDINGS.md)
+ `tools/omr/staged/positions.py` + `capture.py`), and the A-CLEF assumptions
(`tools/omr/staged/ASSUMPTIONS.md` §A-CLEF-1…6). Where this dossier disagrees
with one of them it says so.

---

## Read this first — four facts that govern every section below

**1. The clef is the ONE family whose position fact already has a consumer.**
`OMR_FAMILY_POSITIONS` gave eleven families a staff-relative position quantity
and **nothing reads one**
([omr-family-positions FINDINGS §0](../../benchmarks/omr-family-positions-2026-09/FINDINGS.md)).
`Q.CLEF_POSITION` is not in that eleven, because it landed earlier and
`adjudicate_clef` reads it (`adjudicators/clef.py:176-205`). Of the **thirteen**
staff-grid position quantities `capture.py` registers, exactly **three** have a
consumer: `Q.NOTEHEAD_STAFF_POSITION` (10 references), `Q.KEYSIG_RUN_POSITION`
(4) and `Q.CLEF_POSITION` (3). The other **ten read zero**. **MEASURED HERE** —
derived by grepping `Q.<NAME>` across `adjudicators/`, `consequences.py`,
`inferences.py` and `export.py`, not from prose.

**2. The class name and the line are two different facts, and only the C
family needs both.** `clefG` / `clefF` name a clef outright; `clefCAlto` /
`clefCTenor` name a *family* and the class label cannot name the line. That is
`position-grammar §3` precedent #1, and it is right.

**3. ⚠️ The staged path drops every C clef the detector reads, twice over.**
`gather._CLEF_CLASSES` (`gather.py:258`) is
`{"clefG", "clefF", "clefC", "clefUnpitchedPercussion"}` — the **coarse**
`clefC` (208-space id 142), not the **fine** `clefCAlto`/`clefCTenor` (ids 6, 7)
that the detector actually emits. `class_aliases.ALIASES` deliberately does not
rename the fine spelling to the coarse one (it would drop the line), so nothing
closes the gap. And `adjudicate_clef._c_family_support` matches the string
`"clefC"` exactly, so even a widened gather would not reach it. Details and the
count in §3.

**4. ⚠️ A mid-staff clef CHANGE cannot be expressed on the staged path at
all**, and `gather.py:1985-1997` says so in its own comment. `Q.CLEF` is
`Kind.STAFF`-scoped, `gather_clef` skips every cell but cell 0
(`gather.py:1816`), and `gather_clef_locator` reads only the header window and
`frame_cell(0)`. The legacy path DOES carry one (`measure["clef"]`). §5.

---

## `gClef` / `clefG` — the treble clef

The G clef, printed at the head of every staff and every system, naming G4 by
the line its spiral encircles. Produced by the detector as class `clefG`
(fine id 5) or `clefG` (coarse id 141 — the same string, so nothing is lost);
resolved by `clef_geometry.resolve_clef`, which for the G family returns the
**class label**, not a measured line.

### 1. What sets it apart — and what it is confused with

The fact that sets it apart is **height**: `gClef` is **7.024 staff spaces**
tall in Bravura against `cClef`'s 4.048 and `fClef`'s 3.588
(`docs/engraving-conventions.md` `[C23 + L40]`, LITERATURE). Nothing else in a
staff header is that tall. `clef_locator` uses exactly this and nothing else to
keep G clefs out of the C-clef search: `max_height_spaces = 5.0`, with the
comment *"the ceiling is what keeps a G clef (≈7) out"*
(`clef_locator.py:100`).

Where the class is ambiguous is **line 1 vs line 2** — french violin clef vs
treble. `clef_geometry` refuses to decide it: `families = frozenset({"C"})`,
because the G anchor fraction (0.625) is *"unverified against this detector's
boxes"* and a wrong guess transposes the whole staff (`clef_geometry.py:110-135`,
ASSERTED). In practice french violin clef essentially does not occur in this
repertoire, so the refusal costs nothing measured.

Confusables, starting from Sean's mark alphabet and adding what the clef work
measured:

| confused with | where, and the measurement |
|---|---|
| **a piece of ITSELF read as a C clef** | the staff-line stripper cuts a G clef at every line it crosses, and *"a piece of a TREBLE clef is the size and shape of a C clef"* — braced piano music in all fifteen keys produced **11–15 invented C clefs** at `cluster_y_gap_spaces = 0.15` and none at 0.2; without the on-staff restriction the rule *"takes a scanned treble clef apart at the waist and reads the upper half as an alto clef — **seventeen invented clefs over twenty pages of Beethoven 5**"* (`clef_locator.py:131-160`, MEASURED HERE, n = 20 pages) |
| **a key-signature sharp** | the locator's one dangerous bug: skipping a too-tall G clef landed the search on the signature's first sharp, *"narrow, tall, and beautifully symmetric"* → **20 false `tenor` reads across WTC I pp.3–12** (`benchmarks/omr-clef-geometry/RESULTS.md`, MEASURED HERE, n = 10 pages). Fixed by *stop at the first glyph-sized cluster*. The mirror direction is measured too: a flat's outline correlates with a G clef at **0.57–0.59** against real flats' **0.65–0.76** — *"too close to separate by score"* (`[C23 + L40]`, MEASURED HERE) |
| **a meter** | on Brahms 1 / Breitkopf p.45 a 4-space bar-head window *"spells `4/4`/`9/4`/`12/16`/`5/4` **out of clef ink**"*, 0 of 16, where 14 spaces and the shipped 16.00-space header window each read 16 of 16 (`[C32]`, `benchmarks/omr-meter-cautionary-arbiter-2026-09/FINDINGS.md` §3, MEASURED HERE, n = 16 staves) |
| **an F clef, at the level of the FILE** | not a shape confusion but the dominant real error: the misread direction that costs real edits is **non-treble read as treble**, not the other way. See §fClef |

⚠️ **This dossier adds a row Sean's mark alphabet does not have.**
`position-grammar §2` lists DOT, ARC, WEDGE, HORIZONTAL STROKE, VERTICAL
STROKE, DIGIT, BOWL/BLOB — the clef body appears only as an *anchor*
(*"noteheads, stems, barlines, clef bodies"*) and as precedent #1. But the
measurements above show the clef body is itself a confusable mark: its own
fragments read as C clefs, and a key accidental reads as one. **A "TALL GLYPH"
row belongs in that alphabet**, with height (7.0 vs ~4.0 spaces) as its
discriminator and *"stop at the first glyph-sized cluster"* as its grammar.

### 2. Best method: YOLO / CV / other

**YOLO, and it is genuinely good at this.** A G clef is a real visual
distinction and the detector makes it. Over 52 hand-read staves on three pages
the detector supplied 39 clefs at **95%** accuracy
(`benchmarks/omr-clef-geometry/PIPELINE_CLEF_RESULTS.md`, MEASURED HERE,
n = 52). Over the 20-row scan gate only **34 of 396 staves (8.6%)** had no clef
read at all — i.e. some reader named a clef on ~91% of them
(`docs/ideal-reader-2026-09-07.md` §4.6, MEASURED HERE, n = 396).

Classical CV is deliberately **not** used: `clef_locator` *"identifies C clefs
and nothing else, on purpose"* because G and F *"have no comparably robust
font-independent signature, they are what the detector already reads well, and
the cost of being wrong is asymmetric"* (`clef_locator.py:23-36`, ASSERTED with
the asymmetry argument, not a measurement).

⚠️ A clef **specialist** checkpoint was built and **refused**: it fixed alto but
collapsed dense-page noteheads **2506 → 114** at the deploy threshold
(`benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md`, MEASURED HERE).
`OMR_CLEF_WEIGHTS` still exists as a knob; on the staged path
`READERS.SPECIALIST` and `W_SPECIALIST = 1.0` are **declared and written by
nothing** (`grep -rn 'READERS.SPECIALIST' tools/` returns zero hits outside the
declaration) — MEASURED HERE.

### 3. Where on the page the deciding information lives

Three places, in the order a reader uses them:

1. **The header window** — the staff's own left strip, `max_width_spaces =
   16.0` (`staff_header.py:109`). Everything left of the key signature is the
   clef (`[C23 + L40]`, LITERATURE: Gould p.152).
2. **The glyph's y against THIS staff's five lines** — `Q.CLEF_POSITION`,
   half-spaces down from the top line, a five-line staff spanning 0…+8. This is
   the family-positions "position fact" for clefs, and it already exists.
3. **The same part's other systems** — the clef is reprinted at every system
   head (`[C25 + L38]`), so a part has many independent readings of one fact.

⚠️ **The window can be EMPTY and nothing says so.** On Litolff Beethoven 5
p2/s1 **all eleven header windows measured 6.1–6.2 staff spaces** against 16.00
everywhere else, holding *"the margin label and the systemic rule, and no
music"* — because `system_left_edge` takes the **MINIMUM** of one estimate per
staff and one staff under-ran its ten siblings by ~70 px
(`benchmarks/omr-keysig-truth-2026-09/FINDINGS.md` §5, MEASURED HERE,
n = 11 of 75 staves). Repaired by anchoring on the MEDIAN
(`staff_header.system_left_consensus`); windows with a `barline` right edge went
**12 → 1**.

### 4. Stage by stage

| stage | what happens to a G clef |
|---|---|
| **GATHER** | `gather_clef` (`gather.py:1816`) — **cell 0 only**. Emits `Q.CLEF_GLYPH` (value `"clefG"`, `score` = confidence, `y_center`, `x_center`, reader `DETECTOR`, frame `cell(0)`) for **every** candidate, not just the argmax. Separately emits `Q.CLEF_POSITION` from the cell's own line grid, reader `GEOMETRY`. `gather_clef_locator` runs the CV locator on **both** crops and abstains with the locator's own branch name. `gather_clef_seed` emits `Q.CLEF_SEED` from the dossier. |
| **ADJUDICATE** | `adjudicate_clef` (ORDER position 9, after `Q.INSTRUMENT`). `_clef_of("clefG") → "treble"`, weighted `W_DETECTOR_HIGH 3.0` / `MID 1.5` / `LOW 0.4` by the three confidence tiers, plus `W_ON_THIS_STAFF 1.5` if `Q.CLEF_POSITION` puts it in −2.0…+10.0 steps. Competitive, `MARGIN_FLOOR = 1.0`. |
| **EVALUATE** | `consequences.restate_pitch` — `Q.CLEF` → `Q.PITCH` for every notehead carrying a position row. `consequences.move_glyph` re-pitches a re-owned glyph under the **winning staff's** clef. |
| **INFER** | `COLLAPSE_SLOT_INDEX_TO_FAMILY_BLOCK` reads `Q.CLEF_GLYPH` (the raw observation, **never** `Q.CLEF` — that would close a loop through `Q.INSTRUMENT`) to veto a slot alignment a staff's own clef contradicts (`inferences.py:663-710`). |
| **EXPORT** | `staged/export.py:391` `run.clef = rec.value(Q.CLEF, key)`; `_legacy._mxl_attributes_block` writes `<sign>G</sign><line>2</line>`. Written at the first measure and again whenever `run.clef` differs from the previous run's — i.e. only at a **system boundary**. |

⚠️ `Q.CLEF_REFUSAL_BRANCH` is **declared in `record.Q` and gathered by
nothing** (`reach.py:103`: *"DECLARED, UNGATHERED"*) — the locator's branch name
travels in the abstention's `locator_branch` detail instead.

### 5. Abstain or best-guess — and what leans on this

**(a) Can it abstain, and does it.** Yes, four ways: `no_candidates`,
`margin_below_floor`, `all_candidates_excluded`, and a `NARROWED` ruling
carrying the contest. **This is the single biggest behavioural difference from
the legacy path**, where the measure-cell argmax wins at any confidence
including 0.11 (`adjudicators/clef.py:6-9`, A-CLEF-3).

⚠️ Abstaining is **expensive**: `restate_pitch` gives a staff with no clef
**no pitches at all** — deliberately, not by omission (A-EVAL-2). Measured, the
cost is large and the repair is larger: on two scanned pages, resolving the
five `{treble 3.0, bass 3.0}` ties took pitches **835 → 881** and
**1,329 → 1,470**, and `no_pitch` held-back notes **67 → 54** and **75 → 0**
(`benchmarks/omr-staged-clef-position-2026-09/FINDINGS.md` §5, MEASURED HERE,
n = 22 + 27 staves).

⚠️ **The pipeline cannot say "it is one of these two".** `docs/ideal-reader`
§4.4 names this: a `Ruling` carries a value or abstains, so *"the readers
disagreed between alto and tenor"* and *"nothing was read"* are the same answer
today, mitigated only by `candidates` riding along on the verdict.

**(b) What leans on the clef, and does the clef fail on the same pages.**

| leans on it | how | fails together? |
|---|---|---|
| **every pitch on the staff** | `restate_pitch` | totally — no clef, no pitch |
| **the key signature** | `adjudicate_key_signature` reads `Q.CLEF`; the slot table is keyed on it | ⚠️ **YES, structurally.** *"a wrong clef produces wrong signatures rather than abstentions (measured: bass staves defaulted to treble read 3 flats as 2 sharps)"* (`[C22]`). And they share a crop: the **11 empty header windows** held neither clef nor key signature — **one cause, both readers down** (MEASURED HERE, n = 75) |
| **cross-staff ownership** | `glyph_owner`'s written-range veto is `composed_from=(… Q.CLEF)` | shares the clef's fate |
| **the instrument** | `Q.CLEF` implicates `Q.INSTRUMENT`; ORDER puts identity FIRST to avoid the loop | the loop is structurally blocked, not correlated |

**The clef's own second witnesses, graded by independence:**

| witness | independent of the clef reader? |
|---|---|
| **the same part on another system** (`groups.clef_across_systems`, `contextual._fill_defaulted_clefs`) | ✅ **the best one.** A different printing of the same fact, guaranteed to exist by `[C25 + L38]`. Measured worth: 48/52 → **49/52** on clefs; the sibling vote took WTC I p.17 key signatures **6/10 → 10/10**. ⚠️ Its limit is the staff→part join: `groups._slot_fact` refuses to compare systems of different staff counts, so Brahms p2's 14-and-13 systems cannot vote at all |
| **the instrument's written range** (`clef_correction.propose_clef`) | ⚠️ **fails on exactly the staves that need it, for a reason that is NOT the ink.** `instrument` abstains `no_evidence` on **22 of 22 and 27 of 27** staves of the two scanned pages measured (`omr-staged-clef-position FINDINGS` §1); and over the 20-row scan corpus the entire population it could serve — unresolved staves whose family defaults to non-treble — is **29 staves, and 29 of 29 print no label at all** (`[C...]` *Some publishers stop labelling CONTINUATION systems*, MEASURED HERE, n = 217 truth-carrying staves, 5 publishers). ⚠️ **This is a CLIFF, not a gradient** — the label is printed or it is not — which is why a study stratifying on confidence would find nothing. The cause is a CONVENTION, so it is independent of the raster; the INCIDENCE is perfectly correlated with need |
| **the CV locator** | partly. Same raster, and it needs the same five-line geometry (`_snap_to_staff_line` rejects any staff without exactly 5 lines) — but a genuinely different algorithm, and measured **complementary**: on Nottebohm the detector finds **0** C clefs at conf 0.03 and the locator supplies **7 of 7** correct |
| **`clef_register_warning`** | ⚠️ **refuted in its shipped form.** Reach **7 of 193** scan staves, precision **0 of 11** — every firing is a family boundary, because an orchestral score is ordered by family, not register (`docs/architecture-decision-map.md` §4.2, MEASURED HERE). It needs no label, which is why it keeps being nominated; the ADJACENT-PAIR form is dead. And it is **Class C**: written by `transcribe._flag_clef_register_inversion` and read by **nothing** (`grep -c clef_register_warning tools/omr/clef_correction.py` → 0) |
| **the key-signature slot fit** (`Q.KEYSIG_CLEF_FIT`) | ✅ **the one that needs no identity**, and the only new independent witness the staged path added. It runs the fit against each of four candidate clefs and contributes `W_KEYSIG_FIT 1.5` only where the answer **discriminates**; a run fitting all four, or a 0-accidental key, is recorded in `declined` rather than counted as agreement (`adjudicators/clef.py:280-296`). ⚠️ It is silent on exactly the C-major pages, and **vacuous where the run was not read** — which is the same header crop again |

⚠️ **And the sharpest independence finding is inside the detector itself:**
every `Q.CLEF_GLYPH` row on a staff shares a reader, a frame and a quantity, so
`Evidence.correlated_groups` calls them **ONE SIGNAL** and `tally` takes the
group's strongest term. Measured: a 1.5 added beside a 3.0 left the contest at
**3.0 against 3.0**. Therefore —

> **No refinement of the DETECTOR's own evidence can ever break a clef
> contest.** A tie-breaker must come from a different reader.

(`benchmarks/omr-staged-clef-position-2026-09/FINDINGS.md` §4, MEASURED HERE.)

**Evidence grade:** height discriminator LITERATURE (Bravura `glyphBBoxes`);
fragment/sharp/meter confusions MEASURED HERE; detector accuracy MEASURED HERE
(n = 52 staves, 3 pages); the G/F geometry refusal ASSERTED. Registry handles
`[C23 + L40]`, `[C25 + L38]`, `[C22]`, `[C32]`.

---

## `clef8` / `clef15` — the octave marks

The small `8` or `15` printed above or below a clef, shifting everything on the
staff by one or two octaves. Class-space ids **10** and **11**. They are
separate detections, not part of the clef glyph.

### 1. What sets it apart — and what it is confused with

It is a **DIGIT**, and it lands squarely in Sean's DIGIT row
(`position-grammar §2`): *"one glyph, five roles"* — tuplet digit, time
signature, measure number, stacked instrument number, plate number. What names
this one is **adjacency to a clef body**: within one base-clef width in x, and
above or below it in y (`transcribe._octave_shift_for_base_clef`,
`transcribe.py:364-408`).

⚠️ That is the *only* discriminator and it is **ASSERTED** — the module calls it
a *"pairing heuristic"* and no figure anywhere in the tree prices it. The known
hazard from the same DIGIT row applies directly: *"a Litolff `3` matches
Bravura's `6` — never tune a digit threshold on one edition"*.

⚠️ And the nearest confusable is the one that costs most: a **stacked
instrument number** printed left of the bracket is also a small digit beside a
clef. Those account for **24 of Mahler's 41** clef-locator false positives
(`position-grammar §2` DIGIT, MEASURED HERE).

### 2. Best method: YOLO / CV / other

YOLO finds the digit; **position** pairs it. Neither half is measured. Reach is
small but non-zero: over the five committed production-weights records
(`benchmarks/omr-real-world/*.json`, n = 99 clef-family detections),
`clef8` fires **3 times**, all on `handel-leadsheet` — a choral tenor part,
which is the textbook `treble_8vb` case. MEASURED HERE.

### 3. Where on the page the deciding information lives

Immediately above or below the clef body, in the same x column. Nothing else.

### 4. Stage by stage

| stage | what happens |
|---|---|
| **GATHER (staged)** | ⚠️ **NOTHING.** `clef8` and `clef15` are not in `_CLEF_CLASSES` (`gather.py:258`), so no row is ever filed. No quantity, no abstention, no reason word. |
| **ADJUDICATE (staged)** | nothing to read |
| **EXPORT (staged)** | a staged clef can never carry an octave suffix, so `<clef-octave-change>` is unreachable |
| **legacy** | `transcribe._octave_shift_for_base_clef` appends `_8va`/`_8vb`/`_15ma`/`_15mb`; `export._split_clef_octave` + `_MXL_CLEF_OCT_SHIFT` write `<clef-octave-change>`; LilyPond gets `^8`/`_8` |

⚠️ **`gather_coverage` reports this family as covered and it is not.**
`_family("clef8")` returns `"clef"`, and `FAMILY_TO_Q["clef"] = "CLEF_GLYPH"`,
which IS observed — so the coverage tool reports the clef family green while
two of its seven classes reach no row. The tool answers *"does any row exist for
this quantity"*, not *"does this class reach it"*. **MEASURED HERE** (derived by
reading `gather_coverage._family` + `FAMILY_TO_Q` against `_CLEF_CLASSES`).
This is the breakthrough document's §2 shape one family over: ink with **no
address** is outside the domain of every decision.

### 5. Abstain or best-guess — and what leans on this

**(a)** The staged path cannot abstain because it never asks. The legacy path
returns `""` (no marker) with no record that it looked — a silent
`cannot tell → definite answer` conversion of exactly the kind
`record.py` exists to prevent.

**(b)** Everything the base clef affects, shifted by an octave. A missed
`clef8` is a **whole-staff octave error** — the same blast radius as a wrong
clef, and invisible to any check that reasons about staff STEPS rather than
sounding pitch. The `clef_register_warning` that would catch it is refuted
(above), and `Q.CLEF_POSITION` cannot see it: the octave mark does not move the
clef body.

**Evidence grade:** reach MEASURED HERE (n = 5 documents, 3 firings);
the pairing rule ASSERTED; the staged gap MEASURED HERE (code).

---

## `fClef` / `clefF` — the bass clef

The F clef, naming F3 by the line between its two dots. Class `clefF`
(fine id 8, coarse id 143 — same string). `clef_geometry` returns the **class
label** for the F family; the line is not measured, for the same reason as G
(`ANCHOR_FRACTION_FROM_TOP["F"] = 0.285`, *"unverified against this detector's
boxes"*).

### 1. What sets it apart — and what it is confused with

**The two dots.** They straddle the line the clef names and sit **past the
glyph body's right edge**, at **0.94–1.79 notehead-widths** — *"the region
where a C clef has nothing"*. This is Sean's own DOT row, fourth entry
(`position-grammar §2` DOT, MEASURED HERE), and this dossier agrees with it
exactly; the constants are live in `clef_locator.py`
(`dot_clear_right_fraction = 1.0`, `dot_clear_max_height_spaces = 1.25`).

⚠️ **POSITION BEFORE SHAPE, and the grid proves it.** Loosening the dots'
HEIGHT at the old 0.55-width position vetoes 5 misreads and **costs 3 real C
clefs**; requiring the same dots past the body's right edge costs **zero real
clefs at every height and aspect tried, on both editions**:

| dot position | height | aspect | false positives vetoed | real clefs lost |
|---|--:|--:|--:|--:|
| ≥ 0.55 w | 0.95 | ≤ 1.5 | 5 | **3** |
| ≥ 0.55 w | 1.15 | ≤ 1.5 | 5 | **4** |
| ≥ 1.00 w | 0.95 | ≤ 1.5 | 5 | **0** |
| ≥ 1.00 w | 1.15 | ≤ 2.2 | 8 | **0** |
| ≥ 1.00 w | 1.40 | ≤ 3.0 | 8 | **0** |

(`clef_locator.py:210-248`, MEASURED HERE, two editions.) The reason is
structural: *"A C clef's near-pair is made of fragments of its OWN strokes,
which live inside the glyph; an F clef's dots are printed clear of it."*

Confusables:

| confused with | where, and the measurement |
|---|---|
| **a C clef** (the expensive direction) | a C clef's right-hand lobes, cut by the staff lines running through them, are *"round, correctly sized, aligned in x and a staff space apart — the dot signature exactly, and whether it fires is luck of where the lines fall"* (`benchmarks/omr-clef-geometry/RESULTS.md`, MEASURED HERE). The dot veto fires on real tenor clefs for this reason |
| **repeat dots** | same mark, different place: repeat dots are *"a vertical pair in spaces 2+3, adjacent to a barline"*, F-clef dots are *"header window only, straddling line 4"* (`position-grammar §2` DOT, `[C76 + L77]`). The repo has **no repeat consumer at all**, so this confusion costs nothing today |
| **a wholesale treble misread** | ⚠️ **the real damage, and it is not a shape confusion.** Every clef error in the 52-staff hand-read set is *"a non-treble clef read as treble"* — bass→treble ×2, alto→treble ×2 (MEASURED HERE, n = 52) |
| **a SPURIOUS `clefF` mid-staff** | the sharpest measured cost in the whole family — see §clef change. A `clefF` at **0.32** (just over the 0.25 floor) flipped a Violin staff to bass for three bars |

⚠️ **A worn dot is not round.** The staff-line stripper leaves a stub where the
line ran under it: the pair on Beethoven 5 p.54 staff 8 measures 0.59 × 0.86 and
0.64 × 1.00 — *"widths still exactly dot-sized, heights half again too big"*
(MEASURED HERE, n = 1 staff).

### 2. Best method: YOLO / CV / other

**YOLO for the glyph, CV for the dot VETO.** The locator never *asserts* an F
clef — it only uses the dots to refuse calling something a C clef. That
asymmetry is deliberate: *"a missed clef leaves a staff on the default it would
have had anyway, but a wrongly-invented one transposes every pitch on that
staff"* (`clef_locator.py:30-36`).

⚠️ **CLAUDE.md is stale on this and the tree is right.** CLAUDE.md records the
dot-veto arc as *"FALSE POSITIVES 48 → 13 → 5"*, with the last step being
*"a SINGLE clear dot was made enough on its own (`dot_single_clear_is_enough`)"*.
The tree has **`dot_single_clear_is_enough: bool = False`**
(`clef_locator.py:286`) — it was *"taken deliberately on 2026-08-31 and
reverted the same day"*, when `orchestral-clef-truth.json` widened from 4 pages
to 10 and measured the trade running the other way:

| | veto on | veto off |
|---|--:|--:|
| C clefs located | 8 | **13** |
| false positives | 0 | 1 |
| C clefs lost to this veto | **6** | 0 |

**Five real C clefs for one false positive.** The lesson recorded with it is
worth as much as the number: *"a sweep corpus is built from the candidates the
locator FIRES on, so it oversamples exactly the staves where it produces
something, and it cannot answer 'what does this rule cost in the wild'."*
So **the shipped false-positive figure is 13, not 5.** MEASURED HERE
(`clef_locator.py:256-286`, n = 10 hand-read pages).

### 3. Where on the page the deciding information lives

The header window, as for G — plus one thing the G clef does not have: a
**region to the right of the body**, up to 1.5 spaces past the candidate's own
box. *"The body ends exactly at the strip's right edge and both dots sit beyond
it, so the veto was being asked to find them in pixels it had never been
shown"* (`clef_locator.py:288-300`, MEASURED HERE, n = 1 staff). **Nothing was
wrong with the threshold; the evidence was outside the frame** — the same
frame-error family the breakthrough document catalogues.

### 4. Stage by stage

Identical to `clefG` except that `_clef_of("clefF") → "bass"`. `Q.CLEF_POSITION`
places it: a bass clef's box centre reads **+3.1…+3.5 steps** on the five
staves measured, which is inside the staff.

⚠️ That band is what resolved the family's commonest staged abstention: **five
of the six staves that could not decide a clef were an exact
`{treble 3.0, bass 3.0}` tie** — one `clefG` and one `clefF` detected on the
same staff at nearly the same x, 250–350 canonical px apart in y, because a
measure cell is the staff plus four staff spaces of air and the neighbour's
clef lands in it. The gap is empty: **nothing between +3.5 and +13.3, nothing
between −4.8 and +3.1**
(`benchmarks/omr-staged-clef-position-2026-09/FINDINGS.md` §3, MEASURED HERE,
n = 6 staves on 2 pages).

### 5. Abstain or best-guess — and what leans on this

**(a)** Same four abstentions as `clefG`. The `W_ON_THIS_STAFF = 1.5` term
exists specifically so the neighbour-clef tie does **not** abstain, and it is
additive rather than a filter — *"removing an off-staff glyph's term would make
an arbitration invisibly"* (`adjudicators/clef.py:181-192`).

Two controls on that, both able to fail, both from the same findings file:
over the 19 staves that already decided *and* hold more than one clef glyph the
on-staff glyph agrees **19 of 19** and **0 would flip**; and the newly-decided
staves' median MIDI lands at **48 / 52, 48, 59, 52** against established bass
staves' 50 / 52 and established treble staves' 71 / 69 — the register agreeing
from outside.

**(b)** Same dependents as `clefG`. One extra, specific to F: the **positional
default is `treble`** for every staff except the lower of a 2-staff system
(`transcribe._default_clef_for_position`), so a missed bass clef is silently
wrong in the direction the corpus actually fails.

**Evidence grade:** the dot grid MEASURED HERE (2 editions); the
`dot_single_clear_is_enough` reversal MEASURED HERE (n = 10 pages) and
**contradicts CLAUDE.md**; the `{3.0, 3.0}` tie MEASURED HERE (n = 6 staves);
the F-anchor fraction ASSERTED. Registry handle `[C76 + L77]` for the dots.

---

## `cClefAlto` / `cClefTenor` / `clefC` — the C-clef family, and the line

Alto, tenor, soprano, mezzo-soprano and baritone are **one drawing printed on
five different lines**. The class space has two of the five
(`cClefAlto`, `cClefTenor` — emitted by the detector wrapper as `clefCAlto`,
`clefCTenor`) plus a coarse `clefC`. Produced by the detector, and by
`clef_locator` as a CV reader that names the line directly.

### 1. What sets it apart — and what it is confused with

**The distinguishing fact is POSITION, and a class label discards it.** This is
`position-grammar §3` precedent #1 and `clef_geometry`'s whole reason to exist:
*"It is a mislabelled task, not an under-trained model."* Three of the five are
**unrepresentable in that label space at any level of training**.

The recognition fact is **vertical symmetry**: a C clef is symmetric about the
line it names (Bravura `cClefAlto` runs −2.0…+2.0 spaces about it), *"so
recognising the glyph and deciding between soprano, alto and tenor are the same
measurement"*. Height bounds it away from G (2.2–5.0 spaces vs G's ~7).

| confused with | where, and the measurement |
|---|---|
| **the other four C clefs** | the whole point. Against LilyPond reference staves the locator reads **5/5 exact including the alto/tenor pair**, with treble and bass declined; re-measured through the header-cell path, **4/5** (tenor declines). MEASURED HERE, n = 7 engraved staves |
| **an F clef** | via the dots — see §fClef. The C clef's own lobes, cut by the staff lines, have the dot signature |
| **a fragment of a G clef** | 11–15 invented C clefs on braced piano in fifteen keys at the wrong `cluster_y_gap`; 17 over twenty Beethoven 5 pages without the on-staff restriction. MEASURED HERE |
| **a key-signature sharp** | 20 false `tenor` reads over WTC I pp.3–12 before *stop at the first glyph-sized cluster*. MEASURED HERE, n = 10 pages |
| **stacked instrument numbers** | **24 of Mahler's 41** locator false positives — *"margin, not music"*. Closed by `require_cluster_on_staff`: false positives **48 → 21** for 2 Mahler misses. MEASURED HERE |
| **a fused header cluster** | `cluster too big` is **52.9% of orchestral header cells** and costs **1 C clef against 90 correct refusals** — *"it is a G clef being seven staff spaces tall, not a bug. Do not go after it."* MEASURED HERE |
| ⚠️ **mezzosoprano specifically** | named 5 times on a scanned Beethoven 5 and **wrong all five** — four are G clefs whose surviving fragment balances about line 2, *"which is the line a G clef curls around, so the misread is not random"*. Separated by symmetry: the one real mezzo scores **0.981**, the five misreads **0.712–0.815**. Hence `min_symmetry_mezzosoprano = 0.90`. MEASURED HERE, n = 101 candidates |

### 2. Best method: YOLO / CV / other

**Neither alone. The division is: YOLO finds the FAMILY, geometry names the
LINE — and where YOLO cannot see the glyph at all, classical CV does both.**

The domain gap is the reason the CV rung exists and it is stark: on Nottebohm
p.90, seven staves each carrying a C clef, the production model returns **one**
clef detection and it is wrong; at conf **0.03** the count of C clefs found is
**zero**, and the clef specialist finds zero too. *"A domain gap, not a
threshold"* — the archaic ladder C clef looks nothing like the fonts DSv2 was
rendered from. The locator then supplies **7 of 7** correct, and separated
soprano from alto from tenor — three clefs one line apart — repeatedly across
the page (`benchmarks/omr-clef-geometry/RESULTS.md`, MEASURED HERE).

⚠️ On ORCHESTRAL prints the locator is much weaker: **8 of 24 real C clefs
located** over 10 hand-read pages / 187 staves / 4 publishers, with the
`dot_single_clear_is_enough` reversal above accounting for 5 of the misses.
MEASURED HERE.

### 3. Where on the page the deciding information lives

**The vertical centre of the glyph's ink, against this staff's five measured
lines.** Not the box centre for G and F (their anchors are 0.625 and 0.285) —
but for C it *is* the box centre, because the glyph is symmetric. `max_residual
= 0.35` line spacings, *"comfortably inside the half-spacing that separates a
line from the space next to it"*, and the locator refines the axis to where the
ink actually balances (`axis_refine_spaces = 0.35`, *"small enough that it can
never reach the next staff line"*).

One Beethoven 5 read is the argument for the approach: *"the measured axis
landed at y = 478.0 against a staff line at exactly 478 (residual 0.00), naming
a tenor clef, on a glyph a visual estimate had put on the middle line. The
measurement was right and the eyeball wasn't."*

⚠️ **Sean's warning applies here more than anywhere**: *"position is an option
for helping us determine something but will rarely be a clear rule that
determines by itself"*
([omr-family-positions FINDINGS §0](../../benchmarks/omr-family-positions-2026-09/FINDINGS.md)).
For the C clef it comes closer to being a rule by itself than for any other
mark — but only **given** that the ink is a C clef, which is the part that
fails.

### 4. Stage by stage — ⚠️ and this is where the finding is

| stage | what happens to a C clef |
|---|---|
| **GATHER** | ⚠️⚠️ **`clefCAlto` and `clefCTenor` file NO ROW.** `_CLEF_CLASSES = {"clefG", "clefF", "clefC", "clefUnpitchedPercussion"}` (`gather.py:258`) holds the **coarse** `clefC` and not the two **fine** spellings the detector emits. `class_aliases` deliberately does not rename them (renaming would drop the line, and `COARSER_THAN_CANONICAL["clefC"]` says so). The CV locator's `Q.CLEF_LOCATED` is unaffected and is the only staged route a C clef has. |
| **ADJUDICATE** | `_clef_of` returns `None` for any C spelling — correct, a class name cannot name a C clef. `_c_family_support` then looks for the literal string `"clefC"`, so even a widened gather would still miss the fine spellings. A located C clef weighs `W_LOCATOR 2.0`; with no locator reading the clef **abstains rather than guessing alto** (A-CLEF-4, CLOSED — and this is the right call: the first cut mapped `clefC → alto` and at 3.0 it would have **outvoted the only reader that can answer the question**). |
| **INFER** | `_clef_read_on` uses the same `_clef_of`, so a viola's alto clef contributes nothing to the slot-index family-block inference either. |
| **EXPORT** | `_MXL_CLEF_SIGN` is derived from `CLEF_BY_FAMILY_LINE`, so all five C clefs reach MusicXML and LilyPond correctly once decided. |

**The reach of the gather gap, measured.** Over the five committed
production-weights transcriptions in `benchmarks/omr-real-world/` (n = **99**
clef-family detections): `clefG` 67, `clefF` 24, **`clefCAlto` 5**, `clef8` 3.
**8 of 99 (8.1%) would not reach `Q.CLEF_GLYPH`, and they are 100% of the C
clefs and 100% of the octave marks.** MEASURED HERE.

⚠️ **The staged unit test uses the coarse spelling.**
`test_staged_header_rhythm.py:73` observes `Q.CLEF_GLYPH` with `"clefC"` — a
class `class_aliases` measured firing **zero times** across 3 engraved fixtures
and a 1517-detection scanned Brahms page. *A fixture that does not match GATHER
tests the test*, the shape this repo already records for `Q.METER_GLYPH`.

⚠️ **This is not visible to any derived coverage tool.**
`gather_coverage.FAMILY_TO_Q` maps the families `"c"`, `"f"`, `"g"` and
`"clef"` to `CLEF_GLYPH`, which IS observed, so the clef family reports green.
The tool asks *does a row exist for this quantity*, never *does this class
reach it*. MEASURED HERE (derived from the code).

**Where the dossier does NOT disagree:** the accuracy figure most worth
carrying is from hand-read print truth, and it is good — over **75 printed
staves** of Litolff Beethoven 5 mvt 1 pp.1-4 the staged clef reads
**68 correct / 6 abstained / 1 wrong**, and all ten wrong key signatures sit on
a correctly-read clef
(`benchmarks/omr-keysig-truth-2026-09/FINDINGS.md` §1, MEASURED HERE). Those
pages' viola staves are alto clef, so the locator is evidently carrying them —
which is consistent with, and does not soften, the gather gap: on the staged
path a C clef has exactly **one** route in, and it is the reader that scores
8 of 24 on orchestral prints.

### 5. Abstain or best-guess — and what leans on this

**(a)** Yes, and this family abstains most. `clef_geometry` falls back to the
class label rather than inventing a clef when the snap residual exceeds 0.35 or
the staff has other than 5 lines; the locator has **eleven** named refusal
branches, all of which reach the record as abstention reasons
(`gather._LOCATOR_REASON`). ⚠️ Four vocabulary words — `CLUSTER_TOO_BIG`,
`DOT_VETO`, `OFF_STAFF`, `STAFF_LEFT_UNMEASURABLE` — are declared in
`ABSTAIN` and match no locator branch name, so they are unreachable; those
refusals fall through to `NO_CLUSTERS`. MEASURED HERE (derived by comparing
`record.ABSTAIN` against the locator's `_note` strings).

**(b)** A wrong C clef is the **most expensive single error in the family**,
because alto→treble is a 6-step shift on every note of the staff. Measured:
the Viola on Litolff 575951-p1 read `clefG` at **0.72**, shifting 13 of 16 bars
by +6 — *"~108 edits"* apportioned
(`benchmarks/omr-clef-string-staves-2026-09/FINDINGS.md` §2, MEASURED HERE).

And the second witnesses fail on exactly these staves. The damage sites are
violas, cellos and low brass; the labels that would name them are the ones the
publisher drops on continuation systems. On the two Beethoven p.2 rows *"the
page images print margin names ONLY for the seven wind/brass/timp staves — and
NOTHING at any string staff, in either system"*, so **no margin-reader
improvement can name these staves**, and score-order identity driving clef
correction is measured-rejected (it fixes one staff and breaks a correct one).
MEASURED HERE, n = 2 pages, page images inspected.

**Evidence grade:** the alto/tenor argument LITERATURE + MEASURED HERE (5/5 on
reference staves); the domain gap MEASURED HERE (n = 1 book, 2 models, conf
0.03); orchestral locator recall MEASURED HERE (8 of 24, n = 187 staves);
the gather gap MEASURED HERE (code + n = 99 detections).

---

## `unpitchedPercussionClef1` / `clefUnpitchedPercussion` — the percussion clef

The two thick vertical strokes that mark a staff as unpitched. Class-space
id **9**.

### 1. What sets it apart — and what it is confused with

⚠️ **In this pipeline it is not read from the glyph at all — it is read from
the STAFF.** *"One printed rule IS a percussion staff of one line"*
(`transcribe.py:5321-5335`), so the fact is **geometry, not recognition**, and
the clef glyph is not consulted.

The confusable, stated by the repo: the positional default for a one-line staff
comes out **`treble`**, *"which would export a bass drum as a treble staff:
silently wrong, which is worse than the staff being absent"*.

As a MARK, the glyph is two short thick vertical strokes — Sean's VERTICAL
STROKE row (`position-grammar §2`), where the discriminator is *does it run the
full height of the system*. A percussion clef does not, so the existing
`_spans_system` machinery would separate it from a barline for free. **Nothing
in the tree does this** and no figure exists for it: ASSERTED.

### 2. Best method: YOLO / CV / other

**Neither — the staff's own line count settles it, and that is a better
witness than either.** `len(staff_obj.line_ys) == 1` is measured by
`staff_detector`, needs no glyph, and cannot be wrong about a page that prints
one rule. ⚠️ It also cannot see a **five-line** unpitched staff (Mahler's
`Pauken` is five-line and *"is not flagged"* — the entry a name-matching rule
gets wrong), so the two methods cover different populations and the glyph route
is the only one for the five-line case.

### 3. Where on the page the deciding information lives

The staff itself: how many lines it has. Not the header.

### 4. Stage by stage

| stage | what happens |
|---|---|
| **GATHER (staged)** | `clefUnpitchedPercussion` IS in `_CLEF_CLASSES`, so a detection would file a `Q.CLEF_GLYPH` row. ⚠️ `Q.CLEF_POSITION` will abstain `NO_STAFF_GEOMETRY` on a one-line staff by construction — `_cell_grid` needs five lines, which `Q.CELL_POSITION_BASIS` is the declared refusal for. |
| **ADJUDICATE** | `_GLYPH_TO_CLEF["clefUnpitchedPercussion"] = "percussion"`, weighted like any detector clef. |
| **EVALUATE** | `restate_pitch` calls `_pitch_from_position(pos, "percussion")`, which returns `None` (no anchor), so **no pitch is emitted** — the right answer, reached by an abstention rather than by a rule. |
| **EXPORT** | `export.py:996-1011` has an explicit percussion branch: `<sign>percussion</sign>` plus `<staff-details><staff-lines>`, because `_MXL_CLEF_SIGN` is built from the **pitched** families only and without it a percussion staff *"falls through to the ('G', 2) default and exports as treble"*. |
| **legacy** | `transcribe` sets `staff_dict["clef"] = "percussion"` AND writes it onto **every measure**, because *"`export._staff_measures_xml` takes `measure.get("clef") or clef`, so a measure carrying the positional default wins over the staff — and the first version of this fix set only the staff, which reached a 19-part Dvorak export with ZERO `<sign>percussion</sign>` in it."* |

⚠️⚠️ **The whole path is unreachable by default.** A one-line staff produces no
cell unless `OMR_ONE_LINE_STAVES` is set, and that flag is **OFF**
(`measure_extractor._admit_one_line_staves`). The cost is already costed
elsewhere: on Mahler p.2 the four one-line percussion rules are the reason the
ledger's arity gate refused the whole page, and supplying `lines: 1` for them
moved pooled `part_unresolved` **7,985 → 7,266** with the residual 52 rows
being *"the right 52 — a five-line detector cannot find a single printed
rule, so that music is genuinely unread and the field SAYS SO"*
(CLAUDE.md *`entire staff` is four problems*, MEASURED HERE).

**Reach of the glyph itself: ZERO in every committed record.**
`clefUnpitchedPercussion` appears **0 times** across the five
`benchmarks/omr-real-world/` transcriptions and the eleven `omr-clef-demo`
records (n = 624 clef-family detections total). MEASURED HERE.

### 5. Abstain or best-guess — and what leans on this

**(a)** It abstains by producing nothing: no pitch anchor, no pitch. That is the
cleanest abstention in the family because it is a *consequence* of the clef
vocabulary rather than a rule anyone wrote.

**(b)** Nothing leans on it except the staff's own notes, which are unpitched
anyway. ⚠️ The one thing that *should* lean on it and does not is the **staff
identity chain**: a percussion clef is near-decisive evidence about the
instrument (`[C...]` score order puts percussion in one block), and
`adjudicate_instrument` does not read `Q.CLEF_GLYPH` at all. **ASSERTED** —
nobody has measured what that would be worth.

**Evidence grade:** the geometry rule ASSERTED (stated in code, no figure);
the export branch MEASURED HERE (a real 19-part artefact grepped); reach
MEASURED HERE (0 of 624).

---

## The mid-staff clef CHANGE — `gClefChange` / `cClefAltoChange` / `cClefTenorChange` / `fClefChange`

A clef printed inside a bar or after a barline, changing the staff from that
point. A cello moves between bass and tenor; a viola goes to treble for a high
passage. It is **real music**, not an error.

### 1. What sets it apart — and what it is confused with

⚠️⚠️ **THE FOUR `*Change` CLASSES ARE NOT IN THE PRODUCTION VOCABULARY.** The
DSv2 135-class snapshot (`tools/omr/training/deepscores_classes.py:49-52`) has
`gClefChange`, `cClefAltoChange`, `cClefTenorChange`, `fClefChange`; the
208-class vocabulary the shipped weights use
(`tools/omr/training/deepscoresv2_208_classes.json`) has **none** —
`grep` for `Change` across all 208 names returns **zero**. MEASURED HERE.

So a change clef, when detected, arrives under the **ordinary** class name,
typically small. `clef_geometry._clef_core` strips a `"change"` suffix, which
is correct and **unreachable against production weights**.

What distinguishes it from a header clef is therefore **position in the bar**,
not class: a header clef stands at the staff's left edge, a change clef stands
mid-bar or just after a barline. That is exactly the discriminator
`[C32]`/`[C33]` already use for the meter — *"a mid-staff CHANGE is printed
straight after a barline with no clef in front of it"* — and this dossier
**adds the clef to that family**: nothing in the tree applies it to clefs.

| confused with | where, and the measurement |
|---|---|
| **a spurious detection** | ⚠️ **this is the dominant measured cost of the whole clef family.** On Litolff 984073-p1 the Viola header reads alto CORRECTLY (`clefCAlto` 0.40 over `clefG` 0.34) and then a **spurious `clefF` at 0.59 at m4** flips the rest of the staff to bass (−6/−5, ~38 edits). On Brahms p1 the 1. Violine header reads `clefG` 0.94 correctly and a **spurious `clefF` at 0.32** — *"just above the 0.25 floor"* — flips m3–m5 to bass (−12, the clef-shaped core of that row's 359 edits). On 575951-p2 Violino II: `clefG` 0.94 correct, spurious `clefF` 0.68 at m7, damage m9–m15. MEASURED HERE (`benchmarks/omr-clef-string-staves-2026-09/FINDINGS.md` §2, n = 3 sites, 2 publishers) |
| **a REAL change the reader must not undo** | the mirror. Of the 12 uncovered mid-staff flips over the 20-row gate, several are *"ordinary engraving a consumer must not undo"* — Cello `tenor→bass` ×3, Bassoon `tenor→bass`, Trombone `bass→tenor`, Viola `alto→treble`. *"The actionable residual is nearer 5–6 than 12"* (`benchmarks/omr-clef-contest-reach-2026-09/FINDINGS.md`, MEASURED HERE, n = 396 staves, 5 documents) |
| **a second clef in the same CELL** | Dvořák p5: the plate opens the cello in BASS and prints a TENOR change *inside measure 1*, before the first notes. **Both glyphs are real and both were detected** (`clefF` 0.92, `clefCTenor` 0.88) — *"but a measure cell carries ONE clef state and the higher-confidence glyph keeps it, so the change is lost and everything after it reads −4"* (~116 edits). MEASURED HERE, n = 1 site, page image verified |

⚠️ **Confidence is not the discriminator and this is measured twice.** The
implausible flips run **0.259–0.664** and the ordinary ones **0.333–0.819** —
heavy overlap. And a confidence ceiling on the treble read was measured and
REFUSED: misread trebles score 0.34 and 0.72 while a correct label-named treble
scores 0.61. **The instrument is the discriminator, not the score.**

### 2. Best method: YOLO / CV / other

**Neither, on its own.** The glyph is found by YOLO (usually small, often at
low confidence). What decides whether to *believe* it is **identity plus
convention**: a violin staff never changes to bass; a cello changing to tenor
is ordinary. That is `MID_STAFF_CHANGE_VETOES` and it is **a hand-listed table
of two triples** — `(Violin, treble, bass)` and `(Viola, alto, bass)` —
*"strictly the verified sites"* (`clef_correction.py:500-504`).

⚠️ **The consumer already exists and is switched off.** Of 15 reachable
overturns, *"3 would be handled today by flipping `OMR_INSTRUMENT_CLEF_DEFAULT`;
12 would not — and they are blocked not by missing evidence but by
`MID_STAFF_CHANGE_VETOES`, a hand-listed table of two triples."* So the work
here is *"the consumer exists, is disabled, and its coverage table is two rows
long"*. MEASURED HERE.

### 3. Where on the page the deciding information lives

**Where in the BAR the glyph stands**, and **which instrument owns the staff**.
Neither is currently used for clefs:

* the bar-position discriminator exists for the meter (`[C33]`) and has never
  been applied to a clef — **ASSERTED, nothing in the tree does this**;
* the identity is measured unavailable on exactly the staves that need it
  (22/22 and 27/27 `no_evidence`; 29 of 29 unlabelled non-treble staves).

### 4. Stage by stage — ⚠️ and this is the plainest gap in the dossier

| stage | staged path | legacy path |
|---|---|---|
| **GATHER** | ⚠️ **nothing at all.** `gather_clef` returns at `if sub.cell != 0` (`gather.py:1816`); `gather_clef_locator` reads only the header window and `frame_cell(0)` | every cell is read |
| **ADJUDICATE** | `Q.CLEF` is `scope=Kind.STAFF` — there is no cell-scoped clef quantity, so a change has nowhere to be filed | n/a |
| **EVALUATE** | `restate_pitch` applies ONE clef to every notehead under the staff | n/a |
| **EXPORT** | `run.clef` is a per-staff-run constant; a clef can only change at a **system boundary** (`staged/export.py:2155`) | `_staff_measures_xml` writes `<clef>` at whatever measure `measure["clef"]` changes |
| **legacy reading** | — | the clef argmax runs **per cell** and is not gated by `read_clef`, so *"one detection anywhere in a staff can flip the clef mid-staff"* (`transcribe.py:1793-1856`) |

`gather.py:1985-1997` states the staged gap in terms, and corrects an earlier
claim in the same comment: the page prints two mid-staff clef changes
(to C at page x≈755, back to bass at ≈930, **adjudicated against the print by
Sean**) *"that this pipeline cannot express AT ALL, because `Q.CLEF` is
staff-scoped and no arm reads past cell 0"*.

⚠️ **So the two paths fail in opposite directions**, and both failures are
measured: the legacy path believes every mid-staff clef and pays ~38 + ~120 +
a share of 359 edits for three spurious ones; the staged path believes none and
cannot represent a real one. Neither is the right answer, and the right answer
needs a **cell-scoped clef quantity** — which `gather.py`'s own comment names
as *"the shape D18 already describes for key signatures"*, a change-position
redundancy rather than a second clef reader.

### 5. Abstain or best-guess — and what leans on this

**(a)** ⚠️ **The staged path cannot abstain about a clef change, because it
never asks.** There is no subject, so there is no verdict, no abstention and no
reason word — the breakthrough document's §2 exactly: *"ink the detector
missed has no address, therefore no verdict, no abstention, no refusal — it is
not wrongly decided, it is outside the domain of every decision in the system."*
Here it is worse than that: the ink may have been **detected** and is still
outside the domain, because the gatherer skips the cell.

The legacy path abstains in one narrow place only —
`veto_implausible_clef_changes` restates the affected measures back under the
carried clef, for two instrument/flip pairs, behind a flag that is off.

**(b)** Everything downstream of the staff's clef, from the change bar onward.
The blast radius is asymmetric and measured: a wrongly-accepted change costs
**every note after it**, while a wrongly-refused one costs only the notes it
actually governed. That asymmetry is the argument for the veto being
instrument-conditioned rather than confidence-conditioned.

And the independence question has a clean answer here, unlike anywhere else in
this file: **the cross-system carry is NOT a witness about a clef change**, by
construction. `groups.clef_across_systems` says so in its own
`legitimate_difference`: *"A CLEF CHANGE IS REAL MUSIC… two systems of one part
genuinely differing is not by itself an error… a real change would look the
same to this evidence."* So the family's one genuinely independent witness goes
silent on exactly the case that needs it — the same shape as
*the bars are not an independent umpire over a bad reading*, arriving in the
clef family.

**Evidence grade:** the missing classes MEASURED HERE (the 208-name file);
the three spurious-flip sites MEASURED HERE (n = 3, 2 publishers, shift
classifier); the 12-flip residual MEASURED HERE (n = 396 staves, 5 documents);
the bar-position discriminator ASSERTED. Registry handle `[C33]` is the meter's
and is borrowed here.

---

## What we do not know

1. **Whether widening `_CLEF_CLASSES` would help or hurt.** The gap is certain
   (code + 8 of 99 detections); its cost is not measured. A `clefCAlto` at 0.40
   weighing 3.0 against a located `alto` weighing 2.0 would **outvote the
   locator** — the exact hazard A-CLEF-4 was closed to prevent — so the repair is
   not "add two strings"; it is "add two strings AND decide what a C-family
   detection is worth." Nobody has run that.
2. **Whether the 6 abstained clefs on the 75-staff hand-read page are
   recoverable.** The keysig findings say plainly they *"are not investigated…
   and are someone else's measurement"*.
3. **The G and F anchor fractions.** 0.625 and 0.285 are Bravura proportions,
   never verified against this detector's boxes, so french / varbaritone /
   subbass are unreachable by design. No one has measured what enabling them
   would cost — the argument for leaving them off is asymmetry, not a number.
4. **Whether a clef's own bar POSITION separates a header clef from a change.**
   The meter family measures this (`[C32]`, 16 of 16 vs 0 of 16); nobody has
   measured the clef version, and it is the cheapest thing on this list.
5. **What a percussion clef is worth as identity evidence.** Never measured;
   `adjudicate_instrument` does not read `Q.CLEF_GLYPH`.
6. **Whether the `clef_register_warning` variants work.** Two are named and
   untried: restricted to one bracket group, and a staff against **its own**
   reading on other systems. The adjacent-pair form is refuted (7/193, 0/11);
   the other two need a reach measurement first.
7. **n throughout.** Every accuracy figure in this file rests on 1–5 documents.
   The best one (68/6/1) is **one publisher, one movement, four pages**.

---

## Questions for Sean

1. **A C clef reaches the staged record only through the CV locator, which
   scores 8 of 24 on orchestral prints.** If we widen the gather to admit
   `clefCAlto`/`clefCTenor`, the detector's family claim would arrive at weight
   3.0 against the locator's measured *line* at 2.0. **Should a C-family
   detection be able to outweigh the only reader that can name the line — or
   should it only ever be family support, as it is today?**

2. **Mid-staff clef changes: the two paths fail in opposite directions.** The
   legacy reader believes a `clefF` at 0.32 and destroys a violin staff; the
   staged reader cannot represent a real change at all. Building a cell-scoped
   clef would fix the second and reopen the first. **Is a printed clef change
   frequent enough in the repertoire you care about to be worth that, or would
   you rather the staged path stayed deliberately blind to it for now?**

3. **The bar-position rule we have for meters and not for clefs.** A header
   clef stands at the staff's left edge; a change clef stands after a barline.
   That is `[C33]` and it is already measured for the meter. **Is that
   distinction as clean for clefs as it is for meters on the plates you read —
   or do engravers put a change clef close enough to the barline that it looks
   like a header?**

4. **`clef8` / `clef15` reach no quantity on the staged path** and the legacy
   pairing rule (*within one base-clef width in x*) has never been measured.
   A missed octave mark is a whole-staff octave error. **How often do the
   scores you work on print one — is this worth measuring, or genuinely rare?**

5. **The percussion clef is decided by the staff having one line, and
   `OMR_ONE_LINE_STAVES` is off.** A five-line unpitched staff (Mahler's
   `Pauken`) is invisible to that rule. **Is a five-line percussion staff common
   enough that we need the glyph route as well?**

6. **The dot veto is a TRADE, and CLAUDE.md records the wrong side of it.**
   The shipped setting loses 0 real C clefs and leaves 13 false positives;
   the reverted setting would have removed 8 more at the cost of 5 real C
   clefs. **Confirm the standing preference: a declined clef leaves a staff on
   its default, an accepted wrong one transposes everything — so we keep the
   false positives?**

7. **One thing this dossier adds to your mark alphabet.** The clef body appears
   in `position-grammar` only as an *anchor*, never as a confusable mark — yet
   its own fragments read as C clefs, a key-signature sharp reads as one, and
   clef ink spells meters. **Should there be a TALL GLYPH row, with height
   (7.0 vs ~4.0 staff spaces) as its discriminator?**
