# Engraving conventions — the merged registry

**What this is.** One entry per CONVENTION, merged from the two harvests that
preceded it:

| source | what it holds | entries |
|---|---|--:|
| [`docs/conventions/from-this-repo.md`](conventions/from-this-repo.md) | what THIS project has measured on real plates — with a figure, a file path, and sometimes a refutation | **87** |
| [`docs/conventions/from-the-literature.md`](conventions/from-the-literature.md) | what Gould, SMuFL/Bravura, LilyPond, MOLA, Dorico and IU STATE — with numbers in staff spaces and a citation | **79** |

**Why merged and not indexed.** The same convention usually appears in both, and
the pair is worth more than either half: the literature says what the engraver is
*supposed* to do and often gives a **numeric default in staff spaces**; this repo
says what survived contact with a 19th-century scan, with a measured figure.
Together a reader gets the rule, its default, and whether it holds here.

⚠️⚠️ **THE STANDING RULE: a convention is a HYPOTHESIS AND A CHEAP TEST, NEVER A
LICENCE.** This project has refuted conventions — including ones stated in its
own `CLAUDE.md` — and they are in this registry **on purpose**, under
`REFUTED HERE`. Read *Conventions that FAILED here* before the body. A rule that
sounds obviously true has, in this tree, repeatedly been the thing that was
wrong: *a bracket spans exactly the system* (false on 2 of 5 held editions), *a
meter stack is two digits aligned in x* (total overlap), *staff spacing separates
a system from a group* (floors at 8 sp under compression, by construction).

⚠️ **Three disciplines carried from both sources.**
1. **Never promote LITERATURE ONLY to MEASURED HERE.** A font default is not a
   measurement of a plate. Bravura's numbers are what one reference SMuFL font
   recommends; Scoring Notes measured staff-line thickness ranging **0.08–0.16
   staff spaces** across shipping applications — a factor of two.
2. **Nothing in the literature is about SCANS.** Every outside source describes
   ink as an engraver intends it. Degradation, warp, bleed and broken lines are
   outside all of it — and are most of what this project reads.
3. **Where the literature gives a number and we measured a different one, BOTH
   are shown with their documents.** Publisher spread is a real finding here:
   ledger pitch is **1.102–1.135× on Litolff and 0.975× on Breitkopf** where the
   literature says the rungs continue the staff's own spacing.

---

## Counts

**114 registry entries**, from 166 source entries.

| status | n |
|---|--:|
| **MEASURED HERE** | 67 |
| **LITERATURE ONLY (untested here)** | 27 |
| **ASSERTED (untested here)** | 13 |
| **REFUTED HERE** | 5 |
| **ENCODING (not engraving)** | 2 |

| category | entries | of which literature-only |
|---|--:|--:|
| Staff & pitch geometry | 14 | 6 |
| Stems & beams | 18 | 9 |
| Rests & bar filling | 8 | 3 |
| Accidentals & key signatures | 8 | 1 |
| Time signatures & meter | 8 | 0 |
| Slurs, ties & phrasing | 12 | 2 |
| Dynamics & hairpins | 7 | 1 |
| Articulations & ornaments | 9 | 2 |
| Score layout & systems | 18 | 1 |
| Text & margin labels | 8 | 1 |
| Barlines & repeats | 4 | 1 |
| **total** | **114** | **27** |

**Publisher- or edition-dependent, by the entry's leading word:** **10** of the
87 repo-side entries (the repo file's own count) and **6** of the 27
literature-only ones (`L6`, `L7`, `L8`, `L14`, `L15`, `L71`).

⚠️⚠️ **THE LEADING WORD UNDERCOUNTS, IN BOTH DIRECTIONS, AND THE REPO FILE SAYS
SO.** Entries that lead `RIGID` still carry a publisher or scan caveat in their
**Known exceptions**: the tie interval is empty on an engraving and **not** on a
scan; the barline is straight and the SCAN shears it; the slur pad's empty
interval is engraved and on a scan is a smooth slope. And several entries are
MEASURED *and* carry a refutation inside them. **Read the rows, never the status
word alone.** And on the literature side, the literature file's own point 3
applies: *roughly a third of those entries carry a stated exception that is
normal in 19th-century orchestral engraving* — the beaming-across-the-bar
exception and the horns-carry-no-key-signature tradition being the two that bear
directly on this repertoire.

---

## Contents

- [Conventions that FAILED here](#conventions-that-failed-here) — read this first
- [Where the two sources DISAGREE](#where-the-two-sources-disagree)
- [Staff & pitch geometry](#staff--pitch-geometry) — 14
- [Stems & beams](#stems--beams) — 18
- [Rests & bar filling](#rests--bar-filling) — 8
- [Accidentals & key signatures](#accidentals--key-signatures) — 8
- [Time signatures & meter](#time-signatures--meter) — 8
- [Slurs, ties & phrasing](#slurs-ties--phrasing) — 12
- [Dynamics & hairpins](#dynamics--hairpins) — 7
- [Articulations & ornaments](#articulations--ornaments) — 9
- [Score layout & systems](#score-layout--systems) — 18
- [Text & margin labels](#text--margin-labels) — 8
- [Barlines & repeats](#barlines--repeats) — 4
- [Conservation](#conservation) — every source entry, and where it landed

Each entry is tagged with its sources: `[C<n>]` is an entry of
`from-this-repo.md`, `[L<n>]` an entry of `from-the-literature.md` numbered in
that file's document order. The [Conservation](#conservation) section maps every
one of the 166 by name.

---

## Conventions that FAILED here

**Five entries are REFUTED outright.** They are in the registry so nobody
re-proposes them.

| entry | what failed |
|---|---|
| [A meter stack is two digits aligned in x and adjacent in y](#a-meter-stack-is-two-digits-aligned-in-x-and-adjacent-in-y--refuted) `[C34]` | TRUE `dy` **32–548** against FALSE **26–555** — **total overlap**. The sibling *"the false ones sit at `x_canonical == 0`"* collapses too: **1 of 110 TRUE vs 4 of 50 FALSE** on clean stacks. **Do not re-try either form.** |
| [Sean's S4 — an arc meeting the stem far from the head is a SLUR](#seans-s4--an-arc-connected-to-the-stems-edge-away-from-the-notehead-is-a-slur--refuted) `[C41]` | Refuted **at full width**: reach 143 → **420 of 779**, SIDE flat at **−0.001 / −0.030**, sweep never clearing **p = 0.079**, lift negative in all four strata. It is the WIDE test that fails, which is the strong negative. |
| [The tie/slur POSITION GRAMMAR as a shipped veto](#the-tieslur-position-grammar-s2s5-measured-on-both-families-and-refused) `[C43]` | The convention is sound; the veto costs **+130 edits on the scan (re-measured +149)** and is REFUSED. All of it in the tie→slur half, which is four rules that do not behave alike. |
| [A DOUBLE BARLINE as an available signal](#a-double-barline-is-a-section-mark-a-thin-thick-barline-is-a-movement-end--and-nothing-here-can-read-one) `[C77 + L45 + L76 + L79]` | The convention is not in doubt; **its readability is**. `Q.BARLINE_COLUMN` is a per-staff *count of cells* and **no barline-type classification exists**; custom barline classes cratered F1 to **79.3%** in Phase 3.4. |
| [Staff SPACING separating a system from a group](#staff-spacing-cannot-separate-a-system-from-a-group--refuted) `[C85]` | LilyPond's own defaults floor at **8 sp** under compression for both staff-inside-group and system→system — **no distance threshold can separate them, by construction**. Measured on a real page: within-system **8.09** against another page's inter-system **8.02**. |

⚠️ **And nine surviving entries carry a refutation INSIDE them.** These are the
ones most likely to be mis-quoted:

- **`[C10]`** the middle-line stem convention is **refuted as a READER** (it
  would inherit the staff position's faults) while **confirmed as a RULER**
  (0.787 against a 0.506 baseline) — and it **REVERSES** at 6+ steps, 0.939 → 0.765.
- **`[C19]`** rest aspect ratio is **ONE-SIDED**: it rules a hypothesis out and
  establishes nothing positive — `arpeggiato` fires 377 times on the same
  document as the same tall thin shape.
- **`[C42]`** Sean's S6 is **supported (0.740) and deliberately NOT promoted** —
  it would flip ~30 arcs a page and get **19 of 73 wrong**.
- **`[C64]`** the column count holds (1.62× / 1.71× / 2.29× against a null) and
  the **RESIDUAL is refuted as evidence** — 0.0734 real vs 0.0704 null, 1.00×.
- **`[C78]`** the isolation test holds as a **binary** (nothing between 1× and
  3248×); **open extent alone is REFUTED** (302 of 312 clear it against ~68
  hairpins) and **fill ratio is REFUTED** (nothing survives below 0.35).
- **`[C3]`** a **corrected CONSTANT** ledger pitch is swept and refused — no
  single factor serves Litolff's 1.03–1.11 and Breitkopf's 0.97–1.00.
- **`[C31]`** adding a **cut-C TEMPLATE** fails both ways — nine false systems,
  *and* it loses to plain `C` on real `¢` pages.
- **`[C36]`** **widening the slur pad** is measured and REFUSED — the empty
  interval is an engraved property; on a scan the same distribution is a smooth
  slope with no gap anywhere.
- **`[C86]`** **bracket-groups ALONE was FALSIFIED** on the engraved benchmark —
  pooled 0.1306 → **0.8560**, nine works' barlines deleted. The second condition
  is what makes it safe: do not loosen it.

---

## Where the two sources DISAGREE

**Carried into the entries themselves; collected here so none is lost.**

### 1. The bracket — and this one is a live error in `CLAUDE.md`

`CLAUDE.md:4897` states, in the dossier section: *"a barline runs a system's
full height and **the bracket encloses exactly it**."*
`benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md:127-132`
answers, in these words: **"[MEASURED+SOURCED] 'A bracket spans exactly the
system' is FALSE and is an error in our CLAUDE.md."** An 8-staff LilyPond test
score prints **four per-family brackets (2 staves each)** plus the systemic
barline; and read off the print at 600 dpi, **2 of the 5 editions in the scan
corpus print NO section bracket at all** (Litolff and Simrock print one bracket
for the whole orchestra).

⚠️ **THE BARLINE HALF OF THAT SENTENCE IS SOUND; THE BRACKET HALF IS NOT.** And
the falsifier is already met in the awkward direction: on Litolff and Simrock a
single whole-orchestra bracket makes *"a bracket spans the system"* accidentally
TRUE — which is precisely why it must not be relied on. The literature agrees
with the findings file and not with `CLAUDE.md`: IU specifies *"bracket each
choir … Secondary brackets on like instruments; third level for divisi"*, and
Bravura carries `bracketThickness` **0.5** against `subBracketThickness`
**0.16** — two levels, neither of them the system.
**The repo file flags this as the one entry it would raise with Sean directly.**
See [A bracket encloses a FAMILY, not the system](#a-bracket-encloses-a-family-not-the-system--and-a-brace-is-a-different-mark-and-never-a-full-column).

### 2. Ledger-line pitch — the literature says "the same spacing"; nine publishers say otherwise

Wikipedia (`L5`): ledger lines are *"spaced at the same distance as the lines
within the staff"*, and the entry's rigidity reads **"The spacing is rigid."**
Measured here (`C3`) over **three independent populations, two of them
detector-free**, it is **PUBLISHER-DEPENDENT IN BOTH DIRECTIONS**: Litolff
hi-res **1.102**, hollow-08 Litolff **1.135**, Eulenburg 1.050, Jurgenson 1.055,
Universal 1.030 — against Breitkopf **0.975**, Peters 0.977, Simrock 0.975,
Novello 0.975. Extrapolating the in-staff grid outward at 1.000× accumulates
**+0.065 / +0.223 / +0.319 / +0.541 half-steps on Litolff — it FLIPS at rung 4**
— and costs **66 of Litolff's 2,347 heads (2.81%) against 0 of Breitkopf's
3,337**, a figure the findings file calls "a FLOOR".

⚠️ **A reader that took the literature at its word would extrapolate at 1.000×,
which is exactly the bug.** And a corrected constant is refused: *"no single
factor serves Litolff's 1.03–1.11 and Breitkopf's 0.97–1.00 at once."*

### 3. Cut-C — the literature says read the HEIGHT; this repo measured that route failing both ways

Bravura (`L46`) gives `timeSigCommon` **1.676 × 2.000** and `timeSigCutCommon`
**1.672 × 2.880** and concludes: *"the same width, but cut-C is 44% taller …
**So height alone separates them; the stroke does not have to be found.**"*
Measured here (`C31`), building a cut-C TEMPLATE **fails BOTH ways** — it
produces **nine false systems**, *and* it still loses to plain `C` on the real
`¢` pages, "because a C is a SUBSET of a cut-C's ink and the template with less
to account for scores higher." What ships instead reads the stroke by
**POSITION after `C` has won**: over **87 staves that matched C, the 24 cut ones
fill 1.00 of the centre column and no other exceeds 0.48** — every threshold in
0.50–1.00 gives the same answer.

⚠️ The two are not contradictory about the INK — a cut-C really is taller — but
the literature's *mechanical* advice (separate them by height/template) is the
route this repo measured and refused. Before that fix, Mozart 40 i read **11
staves of 11** and Brahms 4 i **13 of 13** as 4/4.

### 4. Does a slur's ink overlap its noteheads? — the literature says no, the shipped rule says yes

`L48` reasons from Dorico that *"a slur and the notes it binds are on opposite
sides of the noteheads, so the arc's ink does not overlap the heads: a reader
testing for 'noteheads under the arc' by box overlap **will find none**, and
must probe toward the heads instead."* `C35` measured the opposite for slurs:
`_noteheads_under`, a box-overlap test, is the **shipped and working** anchor
rule for a slur, and it is HAIRPINS that score **0 of 4** under it. ⚠️ The
literature's instinct is nonetheless half-vindicated by `C37`: an arc over
STEMMED notes is drawn stem-top to stem-top, and adding a **stem probe** (a
reach toward the head, exactly as `L48` prescribes) took `<slur>` **32 → 40**
and `<tied>` **80 → 91**. So the overlap test works and is incomplete; the
literature named the residue and mis-stated the main case.

### 5. Stem length: one number against a measured distribution

Gould p.14 (`L11`): *"The standard length of a stem is one octave (i.e. 3½
stave-spaces)"*, LilyPond agreeing. Measured here (`C13`) over **8,746
candidates on 13 pages of 8 editions**, the population "decays smoothly to 8
spaces and stops", and the shipped cap is **`STEM_MAX_HEIGHT_LINES = 8.0`** —
because a cap at 6.0 silently un-stemmed exactly the notes furthest from their
beam. **These are compatible and the literature explains the tail** (`L12`:
*"Stems for notes on more than one ledger line extend to the middle
stave-line"*) — but a reader who took 3.5 as a gate would reproduce the
6.0-cap bug. The measured benchmark: 6.0 → 0.1861, 7.0 → 0.1601, **8.0 →
0.1601**, 9.0 → 0.1610.

### 6. Beaming as a metrical signal — Gould states the rule AND its era exception

`L22` gives Gould p.153: *"notes should never be beamed over the middle of the
bar"* — and in the same entry: **"Gould explicitly records that it is not
historical: 'Music from the Classical and Romantic periods frequently uses this
beaming'."** This repo reads 19th-century plates, so **the exception is the
corpus.** The repo file separately records beaming-as-beat-grouping as named in
the exploration doc and **consumed by nothing**. Not a disagreement between the
sources so much as a trap: the rule is real, its exception is this repertoire.

### 7. Carried from the repo file — where it prefers a findings file over `CLAUDE.md`

These are disagreements *within* this project, not between the two harvests, and
the repo file's rule is that **the tree outranks the ledger**:

- **A tie's ends at one staff position (`C39`) is stated in `CLAUDE.md` without
  its scan caveat.** The engraved empty interval (0.168 / 0.435) is quoted;
  `benchmarks/omr-tie-pairing-2026-09/FINDINGS.md`'s finding that **on a SCAN
  the interval is not empty at all** (same-pitch max **0.238** against a
  step-apart minimum of **0.013**) is not. A reader taking the rule as RIGID
  everywhere would re-tune the constant on a scan, which the findings file
  forbids.
- **Ledger pitch provenance (`C3`).** `CLAUDE.md` says the ratios were
  *"measured over the 357 hollow-campaign labels"*. The findings file is
  narrower: the PITCH was measured on **185 rung gaps over 117 notes**; the 357
  rows are the corpus the FIX was *scored* on. Two denominators, conflated.
- **`OMR_ARC_RECLASS`'s engraved cost (`C43`).** The knob row states "+2 edits";
  `CLAUDE.md` itself then flags that as **stale** and gives **+6** on the
  post-chord-tie tree with the scan at **+149**, not +130. Both are quoted in
  the entry and the headline is marked superseded.
- **Litolff p.62's printed `3/4` (`C34`, `C77`).** `CLAUDE.md` carries a cell-8
  reading in several meter sections;
  `benchmarks/omr-ink-gather-2026-09/FINDINGS.md` put a crop on it and found
  **cell 6**, with the cell-8 `timeSig3`+`timeSig4` being **one barline broken
  into two fragments** (0.35–0.40 staff spaces wide, `x_canonical = 0`), and
  **cell 6 firing ZERO `timeSig*` on any of 17 staves**. That in turn INVERTS an
  earlier correction which had called the cell-6 bar math "two cells early".
- **The stem-direction convention's reach (`C10`).** `CLAUDE.md` does not carry
  the thread at all — the measurement (0.787 overall; 0.939 at 4–6 steps; 0.765
  reversing at 6+) lives on `claude/stem-direction-sideways`, **not on main or
  on this branch**. A reader of `CLAUDE.md` alone would not know Sean's stem
  convention has been measured, nor that the reversal is a PITCH fault.
- **`C35` vs `C36` are NOT a contradiction and are kept as two entries.** *"A
  slur is drawn OVER its notes"* (`docs/ask-first-conventions.md`) against *"a
  slur is drawn BETWEEN its noteheads"* (`NOTES.md:313`) are true on **different
  axes**: a slur overlaps its notes **vertically** — which is why
  `_noteheads_under` works for slurs and scores 0 of 4 on hairpins — and stops
  inside them **horizontally**, which is why the arc box needs a 0.25-notehead
  pad. Two axes, two entries, one convention family.

---

## Staff & pitch geometry

### A notehead is one staff space tall
`[C1 + L3]`

- **Says:** a notehead is exactly one staff space tall, because that is what a notehead is.
- **Predicts (mechanically):** any notehead-shaped detection much shorter than a space, **and touching a measure cell's crop edge**, is a fragment of the neighbouring staff's ink and is not a note. A detection far from one staff space tall is a misread.
- **Numbers:** Bravura `noteheadBlack` / `noteheadHalf` **1.180 × 1.000** staff spaces, bbox SW `[0.0, −0.5]` NE `[1.18, 0.5]` — aspect **1.18 : 1**, slightly wider than tall; `noteheadWhole` **1.688 × 1.000**; `noteheadDoubleWhole` **2.396 × 1.240**. Measured here: interior noteheads **0.61–1.12 spaces**; crop fragments **0.29–0.56**; edge-grazed genuine heads **0.77–0.99**. Constant `_CLIPPED_NOTEHEAD_MAX_SPACES = 0.6`.
- **Literature:** the one-space height is rigid across all traditions; the WIDTH varies a little by font and a lot by era of plate. Grace and cue noteheads are drawn small; the breve is taller because of its flanking strokes. Source: Bravura `glyphBBoxes`.
- **Measured here:** over **594 noteheads wholly inside their cell** across the three benchmark works, heights run 0.61–1.12 spaces and **only three are below 0.80**. The constant "**sits in an empty band**" between the largest fragment (0.56) and the smallest genuine edge-touching notehead (0.77), and "the two groups differ in kind rather than degree". Worth pooled **0.2209 → 0.2137**, Brahms **1256 → 1201 edits** (ten detections, 55 edits). `tools/omr/transcribe.py:505-541`; `benchmarks/omr-ned-2026-08/probe_edge_fragments.py`; `docs/position-grammar-confusables-2026-09-04.md` §2 BOWL/BLOB.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID (height). Width is font- and era-variable.
- **Would be falsified by:** a plate whose genuine noteheads measure under 0.60 spaces, or an interior (non-edge-touching) fragment population in the 0.29–0.56 band.
- **Known exceptions:** grace noteheads are smaller (41×38 px against 51–83 in the same cell) — the rule is restricted to detections that TOUCH a cell edge for exactly this reason: "**A short notehead in the middle of a cell is some other problem and this must not have an opinion about it. Nothing is reclassified: a fragment is not a smaller notehead, it is not one.**"
- **Code:** `tools/omr/transcribe.py:537` `_CLIPPED_NOTEHEAD_MAX_SPACES = 0.6`, `:541` `_CELL_EDGE_TOLERANCE_PX = 1`, `:544` `_drop_clipped_notehead_fragments`, consumed at `:1791`.

### A notehead sits ON a line or IN a space, on a half-space lattice
`[C2]`

- **Says:** every notehead centre lands on the staff's half-space lattice — an even step is a line, an odd step is a space — and the lattice continues outside the staff.
- **Predicts (mechanically):** staff position is a **measurement, not a classification**; and a head's ink overlap with the nearest line separates ON from IN.
- **Numbers:** measured in units of the head's OWN height on **836 heads INSIDE the staff**: head ON a line (n=430) p5 **0.000**, median **0.022**, p95 **0.062**, max **0.143**; head IN a space (n=406) p5 **0.292**, median **0.374**, p95 **0.450**. The probe answers ON below **0.15**, IN-A-SPACE above **0.29**, and **ABSTAINS between**.
- **Literature:** not covered as such — but see *A glyph's baseline sits at the staff position it names* `[L2]`, which is the registration rule underneath it.
- **Measured here:** as above. `benchmarks/omr-ledger-extrapolation-2026-09/FINDINGS.md` §7.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID for the parity rule; the *outside-staff* half of the lattice is **publisher-dependent** — see *Ledger-line pitch*.
- **Would be falsified by:** the two distributions overlapping on a plate — i.e. no empty interval between 0.15 and 0.29.
- **Known exceptions:** ⚠️ a notehead box on that record is a median **2.62 half-steps tall**, "taller than the step it sits on", so "the rung is inside the box" also admits the neighbouring space — **box-based tests of this convention are wrong by construction.**
- **Code:** `tools/omr/pitch_resolver.py` (position → pitch); `tools/omr/annotate/ledger_grid.py` + the annotate `snap_to_staff` endpoint.

### Ledger-line pitch is NOT the staff spacing, and it is publisher-dependent
`[C3 + L5]`

- **Says:** the literature says ledger lines continue the staff's ruling at the same spacing. **Measured across nine publishers they do not** — the ratio is a property of the plate.
- **Predicts (mechanically):** extrapolating the in-staff grid outward at 1.000× accumulates error; a reader must **MEASURE the printed rungs** and anchor the outside grid on them. A rung is always a short horizontal run centred on a notehead's x; a run much longer than a head's width plus twice the extension is not a ledger line.
- **Numbers:** ⚠️ **the two sources give different numbers and this is disagreement #2.** Literature: "spaced at the same distance as the lines within the staff" (ratio 1.000); `legerLineExtension` **0.4** staff spaces beyond the notehead **on each side** (Bravura), which LilyPond expresses proportionally as `length-fraction` **0.25** of head width ≈ **0.30 sp**. Measured here: Litolff hi-res **1.102**, hollow-08 Litolff **1.135**, Eulenburg **1.050**, Jurgenson **1.055**, Universal **1.030**; Breitkopf **0.975**, Peters **0.977**, Simrock **0.975**, Novello **0.975**.
- **Literature:** Wikipedia, *Ledger line*: "A line slightly longer than the note head is drawn parallel to the staff, above or below, spaced at the same distance as the lines within the staff." Bravura `engravingDefaults`; LilyPond 2.24.4 `scm/lily/define-grobs.scm:1906–1910`. ⚠️ Its own rigidity row says the **spacing is rigid** and only the extension is variable — "expect roughly 0.3–0.4 sp and do not thread a threshold between them".
- **Measured here:** **three independent populations, two of them detector-free.** (a) off the ink of hand-labelled cells, **185 rung gaps over 117 notes**: edge→1st **1.055** (n=105), 1st→2nd **1.020** (n=49), 2nd→3rd **1.017** (n=26). (b) off a 600-dpi raster on **1,061 strips** (Litolff): **1.032 / 1.079 / 1.048 / 1.111**; Breitkopf over **1,354 strips**: **1.000 / 0.992 / 0.991 / 0.969 / 1.000 / 0.973**. Cumulative grid error in half-steps — Litolff **+0.065 / +0.223 / +0.319 / +0.541 (FLIPS at rung 4)**, Breitkopf **+0.000 / −0.016 / −0.034 / −0.096 / … / −0.151 at rung 6**. Cost: **66 of Litolff's 2,347 heads (2.81%) against 0 of Breitkopf's 3,337**, explicitly "a FLOOR". (c) the detector's `ledgerLine` boxes read Litolff **1.130 / 1.090 / 1.080** — same sign, same publisher split, first gap 10% too wide; **the raster wins and no headline figure comes from the detector**. `benchmarks/omr-snap-ledger-2026-09/FINDINGS.md` §2; `benchmarks/omr-ledger-extrapolation-2026-09/FINDINGS.md` §0, §4, §5.
- **Status:** MEASURED HERE — and it **contradicts the literature's rigidity claim.**
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT, in both directions**, across 9 publishers.
- **Would be falsified by:** a publisher whose measured rung gaps sit at 1.000 while the grid still mis-reads its ledger heads; or the in-staff span control failing (it does not — printed top→bottom span over the record's span is **1.00000 on Litolff, n=957**).
- **Known exceptions:** ⚠️ **a corrected CONSTANT cannot work** — swept and refused: "no single factor serves Litolff's 1.03–1.11 and Breitkopf's 0.97–1.00 at once". Usage is limited by taste — "notes that use at least four ledger lines make music more difficult to read" — so a long ladder is rarer than a short one.
- **Code:** `tools/omr/annotate/ledger_grid.py:197` `measure_ledger_rungs` — **labelling UI only**. Its only consumers are `annotate/server.py` and its own test; the READER (`pitch_resolver`) still extrapolates at 1.000×. **No reader-side consumer found.**

### A note outside the staff is joined to it by an unbroken ladder of ledger rungs
`[C4]`

- **Says:** an engraver prints every rung between the staff and the note; the ladder is continuous.
- **Predicts (mechanically):** (i) a contested cross-staff notehead belongs to the staff whose ladder reaches it *unbroken*; (ii) an outside-staff notehead with NO rung at all is not a note.
- **Numbers:** expected rungs are `int(d/spacing + 0.25)` — the `+0.25` because a note ON the first ledger measures ~1.0 spacings and truncation read **0.994** as needing none. Unladdered fakes sit at confidence **0.45–0.53** against **0.76+** for every real one.
- **Literature:** not covered directly; the adjacent geometry is in *A ledger line is drawn at the staff's own spacing* `[L5]` and *A ledger line is thicker than a staff line* `[L6]`.
- **Measured here:** pooled OMR-NED **0.1506 → 0.1431**; Beethoven notes **81/81 at recall/precision 1.000**. ⚠️ The rule is **COMPLETENESS ONLY**, not a rung count — "two broken ladders are NOT evidence either way, because a found rung can belong to the other staff's note exactly as a gap can". `CLAUDE.md` "Which staff a contested glyph belongs to"; `benchmarks/omr-ned-2026-08/LADDER_EVIDENCE_2026-09-01.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a plate that omits interior rungs, or a corpus where rung *count* out-discriminates rung *completeness*.
- **Known exceptions:** the detector fires `ledgerLine` on **1,107** ordinary staff lines inside the staff on one four-page record, and "whether that path filters them is unchecked". A tenuto is the same shape and is a live confusable.
- **Code:** `tools/omr/transcribe.py:3290` `_dedupe_cross_staff_detections` (ladder tier); `tools/omr/transcribe.py:3739` `_drop_unladdered_noteheads`.

### The engraver opens the gap above a staff PRECISELY so its ledger notes can live there
`[C5]`

- **Says:** inter-staff white space on a conductor's page is not slack — it is reserved for one staff's ledger notes and the arcs over them.
- **Predicts (mechanically):** "nearest five-line band" is the WRONG ownership rule for exactly the case the measure-cell padding exists for; ownership must be decided by **context** (ladder, written range, hugging), not distance.
- **Numbers:** measure-cell pad is **4 spaces or 6, never in between**. Contested hairpin copies sat only **5–62 px** nearer one staff than the other.
- **Literature:** not covered.
- **Measured here:** Brahms's C Horn 2 `C3` sits **4.5 spaces below a treble staff, four pixels past its own cell**; at pad 5 the note goes to Eb Horn 3 **by 19 px** while C Horn 2 stays empty. Growing the pad to 5 costs Brahms **0.3420 → 0.3732 (+128 edits)** and takes cross-staff duplicates removed **135 → 390**. For arcs the same argument is worth pooled **2,473 → 2,371 edits**, Brahms 1 **490 → 390**. "Distance is nearly a coin flip." `benchmarks/omr-ned-2026-08/WRONG_NOTE_ATTRIBUTION_2026-09-01.md`; `benchmarks/omr-hairpins-2026-09/FINDINGS.md` §6.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID (a consequence of how a system is laid out).
- **Would be falsified by:** a corpus where the nearest-band rule and the ladder/range rules agree on the contested population.
- **Known exceptions:** for **11 of 13** print-silent bars in `benchmarks/omr-phantom-notes-2026-09`, the ink was detected in ONE cell only and no contest exists at all, so no ownership rule is even asked.
- **Code:** `tools/omr/measure_extractor.py` (`PAD_ABOVE_STAFF_LINES`); `tools/omr/transcribe.py:3290`; `tools/omr/staged/ownership.py`.

### A ledger rung printed THROUGH a hollow notehead is split by the head's white counter
`[C6]`

- **Says:** a rung drawn through an open notehead is interrupted by the counter, so it is printed as two short spans rather than one.
- **Predicts (mechanically):** a contiguous-run rung detector is blind to exactly the rung that matters most (the one the note sits on); the detector must bridge a gap the width of a counter.
- **Numbers:** bridging constant **0.55 spaces — a half's counter**; white gaps up to **0.9 spaces** are bridged. A whole note is **1.72 spaces wide**, so its own rim reaches 0.55.
- **Literature:** not covered. (Bravura's `noteheadWhole` 1.688 sp width `[L4]` is the same fact from the font side.)
- **Measured here:** "a rung THROUGH an on-line hollow head is split by the white counter; contiguous-run detection was blind to exactly the rung that matters most". A "wing recentring" fix re-imported pollution and was refused (zone 0.55–1.1: recovers 10 / breaks 13). `benchmarks/omr-snap-ledger-2026-09/FINDINGS.md` §5.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID (a property of open noteheads).
- **Would be falsified by:** a plate whose counters are narrower than the bridging window, making the bridge a false-merge risk instead.
- **Known exceptions:** a head TANGENT on its ledger merges rim + rung into one band and the measured centre drifts ~0.3 spaces into the head — one of the 7 adjudicated breaks, "a real miss".
- **Code:** `tools/omr/annotate/ledger_grid.py:197` `measure_ledger_rungs` (gap-bridging). **No reader-side consumer found.**

### The staff space is the unit of everything — the em box is four staff spaces
`[C7 + L1]`

- **Says:** every dimension in engraving is a fraction of the staff space, and a music font sets its em box to four of them — so a glyph's printed size is fixed by the font at any rendering size, and a page's absolute size carries no information a reader needs.
- **Predicts (mechanically):** **recover staff spacing FIRST; every other entry in this registry depends on it.** Any constant in page pixels is a constant about one scan; any constant in staff spaces is a constant about engraving. A click-placed label box can be sized from the glyph name alone, and a template search has a known scale.
- **Numbers:** SMuFL: "if a font uses 1000 upm … one staff space is equal to 250 design units" — **1 em = 4 staff spaces**. Measured here: the committed Bravura templates trim to exactly `size_px/4` tall at every rendered size, so `noteheadHalf` is **1.000 staff spaces at aspect 1.167** and `noteheadWhole` **1.000 at 1.722**.
- **Literature:** SMuFL, *Metrics and glyph registration for scoring applications*. "Rigid as a convention of measurement. The absolute mm value is entirely variable."
- **Measured here:** ⚠️ **this is a FONT fact, not a plate fact, and the repo says so.** Sean's 29 hollow-notehead boxes measure a median **199×178 px against a 100 px staff space — 1.78 spaces**; a click places **121×102**. "**Do not 'fix' the difference by widening the default to match the older labels.**" `CLAUDE.md` "Single-symbol pass mode" / `_symbol_metrics`; `tools/omr/symbol_library/data/manifest.json`.
- **Status:** MEASURED HERE (as a font fact)
- **Rigid or publisher-dependent:** RIGID **within a SMuFL font**; historical plates differ, and the shipped click box is deliberately TIGHTER than the hand-drawn boxes.
- **Would be falsified by:** a measured plate whose noteheads are reliably 1.78 spaces wide rather than ~1.17–1.72; or a body of engraving whose symbol proportions track page size rather than staff spacing.
- **Known exceptions:** the same file records `AUDIT.md` flagging that the older hand boxes are generous and would teach "a slightly loose box prior".
- **Code:** `tools/omr/symbol_library/builder.py`; `tools/omr/annotate/` (`_symbol_metrics`, click-to-box); `tools/omr/time_signature_locator.py` and `key_signature_template.py` build templates from the same library.

### A staff's five lines are straight and evenly spaced — and on a scanned plate they are neither
`[C8]`

- **Says:** the engraver rules five parallel lines; the SCAN then tilts and bows them.
- **Predicts (mechanically):** a cell's stored line grid, copied as five ideal rows from the staff, can be **half a space off the print** at the end of a staff — so the grid must be slid onto the ink beneath it, and every *position* tolerance downstream must budget **registration error rather than engraving slack**.
- **Numbers:** a scanned staff tilts/bows **8–17 page px** across its width. The rigid-comb slide recovers all seven hand-traced displacements within **0.04 spaces**. The whole-rest slot tolerance is `WHOLE_REST_STEP_TOLERANCE = 1.0`, and it is registration error: correctly-read whole rests spread over steps **2.5–5.9** against a nominal 5.5.
- **Literature:** not covered — and the literature file says so in terms: *"Nothing here is about SCANS. Every source describes ink as an engraver intends it."*
- **Measured here:** priced on the widened scan gate: pooled **0.8387 → 0.8345 (−233 edits)**, −217 of them on exactly the three tilted rows; the widened pool holds **8.6%** of cells past the 0.25-space parity-flip line against the old corpus's **0.4%**. Per-line tracing ALIASES and was refused. `benchmarks/omr-cell-grid-tilt-2026-09/WIDENED_PRICING_2026-09-04.md`; `tools/omr/staged/adjudicators/rhythm.py:2820-2826`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** the convention is RIGID; **the deviation is a property of the SCAN, not of the publisher's engraving.**
- **Would be falsified by:** a scan corpus in which the traced comb and the ideal grid agree everywhere (the engraved family is a no-op by construction and was verified byte-identical).
- **Known exceptions:** engraved (vector) input — the fix is a no-op there by construction.
- **Code:** `OMR_CELL_LINE_TRACE` (default ON); `tools/omr/staged/adjudicators/rhythm.py:2826` `WHOLE_REST_STEP_TOLERANCE = 1.0`.

### A glyph's baseline sits at the staff position it names
`[L2]`

- **Says:** a notation glyph that belongs to a vertical staff position is drawn so that the font baseline lies exactly at that position.
- **Predicts (mechanically):** **the y a reader should extract differs per family.** For a notehead or accidental the glyph's vertical CENTRE is the pitch; for a clef the pitch it names is at the baseline; for a rest the baseline is its default staff position. **Taking a bounding-box centre for everything is wrong for at least clefs, flags, whole rests and the flat sign.** Horizontally, "all glyphs shall be horizontally registered so that their leftmost point coincides with x = 0".
- **Numbers:** none beyond the registration rule itself.
- **Literature:** SMuFL, *Metrics and glyph registration for scoring applications*.
- **Measured here:** not measured here. ⚠️ Adjacent and measured: *A notehead sits ON a line or IN a space* `[C2]` warns that a notehead box is a median **2.62 half-steps tall**, so a box centre is not a safe proxy even for a notehead on a scan.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** rigid within SMuFL-conformant fonts; it describes how engravers have always placed these glyphs, so it should hold on plates too.
- **Would be falsified by:** a font or plate where a notehead's ink is systematically offset from the staff position it sounds.
- **Known exceptions:** the whole rest, which **hangs** from the baseline rather than centring on it — see *A whole rest HANGS under the 4th line*.
- **Code:** no consumer found.

### A whole notehead is wider than a black one, and the same height
`[L4]`

- **Says:** the semibreve head is drawn wider than a crotchet/minim head, but occupies the same single staff space.
- **Predicts (mechanically):** **width, not height, separates a whole note from a half note** — 1.688 vs 1.180 staff spaces is a **43% difference and is measurable**. Height cannot separate them at all. A reader distinguishing hollow heads should use width and the presence of a stem, **never height**.
- **Numbers:** `noteheadWhole` **1.688** sp wide; `noteheadHalf` **1.180** sp wide. Same height, **1.000**.
- **Literature:** Bravura `glyphBBoxes`. Rigid in direction; the exact ratio varies by font.
- **Measured here:** **not measured here — neither harvest carries a width measurement of hollow heads on a plate.** ⚠️ The second half of this entry's own prediction is in the registry and is also untested: *No stem means a whole note* `[C15]`, which the repo files as ASSERTED with **no figure**. So the two discriminators the literature names for the hollow pair — **width, and the presence of a stem** — are **both unmeasured here**, while the one the literature rules out (height) is the one the repo's `[C1 + L3]` band is expressed in.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** rigid in direction; ratio font-dependent.
- **Would be falsified by:** a plate where whole and half heads measure the same width.
- **Known exceptions:** none recorded.
- **Code:** no consumer found.

### A ledger line is thicker than a staff line
`[L6]`

- **Says:** ledger lines are drawn somewhat heavier than the staff's own lines.
- **Predicts (mechanically):** **in a staff-line-erased image, ledger rungs should SURVIVE an erasure tuned to the staff lines**, because they are heavier. A reader that erases at the staff-line weight and loses its ledger rungs has over-erased.
- **Numbers:** Bravura `legerLineThickness` **0.16** vs `staffLineThickness` **0.13** — about **23% heavier**.
- **Literature:** SMuFL *engravingDefaults*; Bravura `engravingDefaults`. "Variable in magnitude, consistent in direction. **23% is not a large margin and may not survive a low-resolution bitonal scan.**"
- **Measured here:** not measured here. ⚠️ The repo's adjacent measurement runs the other way: `remove_staff_lines` clears only a median **55%** of a Litolff cell's line ink, and staff residue "does not come out as residue-shaped rows — **2 of 1,244 and 16 of 6,055** — because the surviving line ink is CONNECTED to everything else and lives inside the blobs".
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** **Variable** in magnitude.
- **Would be falsified by:** a plate whose ledger rungs measure thinner than its staff lines.
- **Known exceptions:** none recorded.
- **Code:** no consumer found.

### Staff line thickness is around an eighth of a staff space, and applications disagree by 2×
`[L7]`

- **Says:** a staff line is thin relative to the space it bounds.
- **Predicts (mechanically):** bounds what a staff-line detector should accept as a line — a horizontal run around **0.1 staff spaces** thick — and bounds what STAFF RESIDUE after erasure can look like. **The 2× spread across applications means a fixed thickness constant is fitted to whichever engraver you measured.**
- **Numbers:** Bravura `staffLineThickness` **0.13**. Application defaults: Finale **0.12**, Sibelius **0.1**, Dorico **0.16**, MuseScore **0.08** — a range of **0.08–0.16 staff spaces**.
- **Literature:** Bravura `engravingDefaults`; Scoring Notes, *Spaces and the units of measurement for music notation*.
- **Measured here:** not measured here as a thickness. ⚠️ The repo measures the CONSEQUENCE: `staff_detector` separates music from body text by *continuity* rather than thickness — "music tops out at **1.39 runs per staff-space**, text starts at **2.02**".
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** **Variable, and this entry exists to say how variable.** Publisher and era widen the band further.
- **Would be falsified by:** nothing — it is already a measured spread; the useful form is the band, not a value.
- **Known exceptions:** none recorded.
- **Code:** no consumer found.

### A staff is 4–8.5 mm tall, and the score end is the small end
`[L8]`

- **Says:** conductor's scores are set much smaller than parts; there are professional floors below which each is considered illegible.
- **Predicts (mechanically):** **converts a rendering DPI into an expected staff-space size in pixels, which bounds every other measurement.** A conductor's score at the 4 mm floor rendered at 300 dpi gives a staff space of about **11.8 px**; a part at 7.5 mm gives about **22 px**. **An orchestral score is at the hard end of this range by construction.**
- **Numbers:** MOLA: minimum legible staff size for scores **4 mm**; most readable **7.5 mm**; "anything smaller than 7.0 mm is unacceptable, and anything larger than 8.5 mm should be avoided". Gould p.557: "An ideal stave size in good lighting conditions is **6.7 mm**". IU: parts minimum 7.0–7.5 mm, scores minimum 4 mm.
- **Literature:** MOLA *Formatting*; Gould p.557 (*Performance conditions*); IU *Page Layout*.
- **Measured here:** not measured here as a staff size. ⚠️ **The repo has the matching cliff from the other side and it is severe:** at staff-space ≤ **7.6 px** the system-grouping analyser "reported **17 bridging columns across a real inter-system gap — a false MERGE produced purely by resolution**" (see *The only ink crossing a family gap is the SYSTEMIC BARLINE* `[C83 + L75]`). So this entry's DPI arithmetic is the input to a measured failure threshold.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** **Variable**, and these are modern professional floors. **19th-century plates predate all of them.**
- **Would be falsified by:** a held edition whose staves measure outside 4–9 mm.
- **Known exceptions:** miniature/study scores go well below 4 mm.
- **Code:** no consumer found.

### The first line of each movement is indented
`[L9]`

- **Says:** a movement's opening system is set in from the left margin relative to the systems that follow it.
- **Predicts (mechanically):** **a system whose left edge is to the RIGHT of the page's other systems is a candidate movement START** — an independent structural signal that needs no reading of the music. Conversely, **a page whose systems are indented differently is not necessarily mis-segmented**: it may print a movement boundary.
- **Numbers:** none given; the AMOUNT is house style.
- **Literature:** MOLA, *Formatting*: "The first line of each movement should be indented."
- **Measured here:** not measured here as a movement signal. ⚠️ **But the repo has paid for the second half of the prediction.** `OMR_CHOIR_GROUPING` exists because the Bach Brandenburg 3 stress row shatters (6 "systems", **122 measure-cells vs 10**) on a page "whose systems are indented differently (**792–836 vs 178–200**)" — the page-MEDIAN `x_start` lands between the modes and cuts the full-width system's bracket and systemic barline out of the scan. So differing indents are a **known hazard** here and have never been read as the movement signal this entry proposes.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** widely followed; MOLA states it as a requirement. The amount is house style.
- **Would be falsified by:** editions whose movement openings are flush with every other system.
- **Known exceptions:** the indent also accommodates the instrument-name block on a score's first system, **so on a full score an indent can mean *first page* rather than *new movement*.**
- **Code:** no consumer found as a movement signal. The hazard is handled at `tools/omr/system_grouping.py` (cue A/B) and `OMR_CHOIR_GROUPING`.

---

## Stems & beams

### A stem attaches on the RIGHT going UP, or on the LEFT going DOWN
`[C9 + L10]`

- **Says:** right-and-up, or left-and-down. Right-and-down does not exist.
- **Predicts (mechanically):** of the four (side, direction) cells only two are music; a vertical run of ink in the other two is a barline, a neighbour's stem, a beam or a slur edge. **Where exactly one legal cell is filled, the stem is DECIDED.** Conversely, given a stem direction, the notehead is on a known side of the stem — which is how to associate a stem with its head rather than a neighbour's.
- **Numbers:** Bravura makes the attachment explicit: `stemUpSE` = `[1.18, 0.168]` (the head's right edge), `stemDownNW` = `[0.0, −0.168]` (its left edge) — **x = 0 or x = notehead width, y = ∓0.168 staff spaces** from the pitch centre, i.e. the stem meets the head just off its vertical middle, not at the extreme corner.
- **Literature:** Wikipedia, *Stem (music)*: "If the stem points up from a notehead, the stem originates from the right-hand side of the note, but if it points down, it originates from the left." Bravura `glyphsWithAnchors`. **"Rigid. This is one of the most reliable conventions in all of notation."**
- **Measured here:** agreement with the stems the pipeline ALREADY reads — Litolff **95.9% (900/938)**, Breitkopf **98.2% (1,468/1,495)**. Heads where exactly one legal cell is filled: Litolff **938/1,435 (65%)**, Breitkopf **1,495/1,774 (84%)**; on the `no_stem` population **472/784 (60%)** and **653/1,442 (45%)** — reach **1,125 heads that currently abstain** — ⚠⚠ **CORRECTED 2026-09-18: that is a DOUBLE COUNT and the honest marginal is 854.** Both shared records are PRE-tier (no `beam_mate` verdict anywhere), so the 472 / 653 still contain the heads the shipped beam-mate tier now serves: the overlap is **101 / 170**, leaving a marginal **371 / 483 (pooled 854)**, so this entry **overstated the remaining job by 271 heads (24%)**. The two mechanisms are also **positively correlated in availability rather than complementary** — the convention speaks for 66.4% / 58.6% of the beam-mate population against 58.7% / 41.9% of the rest. ⚠ And the convention is **REFUSED AS A TIER**: where both mechanisms speak on the population this one is FOR they agree Litolff 97.0% (101 heads) but Breitkopf only **84.7%** (170) — **the ordering INVERTS against the 98.2% headline**, the plate with the better published figure being the worse reader exactly where it would be used, and 23 of its 26 disagreements sit INSIDE the physical gate. See `benchmarks/omr-stem-attachment-2026-09/FINDINGS.md`. It goes SILENT rather than wrong: "both cells filled" is **16%** of Litolff's `no_stem` heads and **44%** of Breitkopf's. `benchmarks/omr-stem-ink-2026-09/FINDINGS.md` §3.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID — "the only one of the four that is a rule the engraver has no freedom about".
- **Would be falsified by:** a plate on which the agreement figure falls toward the **0.506** always-the-commoner-direction baseline; or a plate with up-stems on the left of their heads.
- **Known exceptions:** whole notes are excluded throughout (9 and 87 of the `no_stem` populations correctly have no stem). ⚠️ **95.9% / 98.2% is REACH-adjacent, not accuracy** — measured where the pipeline already had an answer, "by construction, the population that was easy enough to read once". Literature adds: double-stemmed writing puts stems on both sides, and a chord containing a second puts one head on the wrong side of the stem.
- **Code:** **no consumer found.** The finding is 2026-09-17, "nothing was built and nothing was changed".

### In a single voice, a note above the middle line is stemmed DOWN
`[C10 + L16]`

- **Says:** with one voice on the staff, the note's side of the middle line decides the stem direction.
- **Predicts (mechanically):** staff position → stem direction, for free, with no ink. A detected stem contradicting it is either a multi-voice bar, a beamed group whose average pulls the other way, or a misread — **each a distinguishable hypothesis rather than noise.**
- **Numbers:** scored on **1,443 heads a stem already decided, LEAVE-ONE-OUT**: baseline (always the commoner direction) **0.506**, this convention **0.787**, "where the beam SITS" 0.829, beam-mate majority 0.938, beam-mate unanimous **0.984**. By distance from the middle line in staff steps: 0–1 **0.537** (n=231), 1–2 **0.776** (n=228), 2–4 **0.860** (n=387), **4–6 0.939** (n=261), **6+ 0.765** (n=336) — **it rises and then REVERSES.**
- **Literature:** Wikipedia, *Stem (music)*: within a single voice, stems point downward for notes **at or above** the middle line and upward for those below; for beamed notes the direction follows "the average position of the lowest and highest notes". "Rigid within single-voice writing, and **completely overridden** by multi-voice writing."
- **Measured here:** ⚠️ **REFUTED AS A READER WHILE CONFIRMED AS A RULER.** Sean: *"The convention is strong. The failure is elsewhere."* The 6+ reversal is **the POSITION, not the rule**: **44% of ledger-country heads are off-grid against 11% inside the staff**, and 14 of 25 phantom notes stand OUTSIDE the staff altogether. Crossing with the residual does not move it (off-grid 0.757, on-grid 0.771). `benchmarks/omr-stem-direction-2026-09/FINDINGS.md` §2, §4 (commit `1b01f8ec`, branch `claude/stem-direction-sideways` — **not on main**).
- **Status:** MEASURED HERE — and refuted as a reader.
- **Rigid or publisher-dependent:** RIGID for one voice; **broken constantly by two-voice writing and chords**, which Sean himself stated as the precondition.
- **Would be falsified by:** the 4–6-step band failing on a second document; or the 6+ reversal surviving a corrected staff position — **it does not**: correcting the 32 own-staff heads with ink truth changes agreement by "**exactly nothing — 17 of 32 either way**".
- **Known exceptions:** two-voice writing, chords, and ledger country. `glyph_owner` does **not** explain the reversal (owned-by-another-staff 0.825 against no-verdict 0.780).
- **Code:** **deliberately not shipped as a reader** — "it would inherit the position's faults". Its intended use is an AUDIT: "a confident stem and a confident convention that disagree name a zone to look in".

### A beam joins stem TIPS, so every stem on one stroke points the same way
`[C11]`

- **Says:** a beam is drawn across the ends of the stems it joins, so a beamed group is stem-unanimous.
- **Predicts (mechanically):** a head whose stem was not read can **borrow its direction from any head sharing its beam**.
- **Numbers:** beam-mate UNANIMOUS **0.984** accuracy, reach **152**; beam-mate MAJORITY 0.938, reach 167 — "unanimity costs 15 of 167 reach and buys 4.6 points". The `x`-CENTRE test rather than a box overlap "is worth 4 points on its own".
- **Literature:** not covered directly. The nearest is `[L16]`'s note that a beamed group's direction follows "the average position of the lowest and highest notes" — a claim about which way, not about unanimity.
- **Measured here:** `no_stem` **793 → 641**. Control **4,647 of 4,647** verdicts reproduced with the tier disabled. "The claim that works is PHYSICAL, not geometric." `benchmarks/omr-stem-direction-2026-09/FINDINGS.md` §2.
- **Status:** MEASURED HERE — **shipped.**
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a beamed group whose stems genuinely disagree — which would mean the beam is not joining tips.
- **Known exceptions:** the rule reaches nothing where no beam is read. Two beams crossing in a two-voice column are two strokes, not one.
- **Code:** `tools/omr/staged/adjudicators/rhythm.py` — a second tier in `adjudicate_stem_direction`, reason `beam_mate` (on `claude/stem-direction-sideways`, not on main).

### A beam stroke runs from the FIRST stem it joins to the LAST, and a stem stands at the SIDE of its notehead
`[C12]`

- **Says:** the beam's ink starts and stops at stems, and a stem is offset half a notehead from the head's centre.
- **Predicts (mechanically):** **a note belongs to a beam via its STEM, not via its notehead centre** — the outer note of every beamed group has its centre roughly half a notehead width past the stroke's end.
- **Numbers:** the overshoot clusters at **0.35–0.47 notehead widths** — the stem offset and nothing else. Attachment is BOX OVERLAP and needs no constant: of 707 stem/beam pairs overlapping in x, **685 also overlap in y and the 22 that do not are 35 px or more apart with nothing in 1–34**; 819 heads take exactly one stem. `BEAM_EDGE_TOLERANCE_WIDTHS = 1.0`.
- **Literature:** the stem-offset half is `[L10]`'s anchor geometry (x = 0 or x = notehead width). The beam-extent half is not covered.
- **Measured here:** on `beethoven-sym5-mvt4` m203-218 at 23 parts, **114 narrowed durations have a stem of their own head meeting a beam** that the centre test calls `none_over_this_note`. Closing it took the engraved fixture from **12 assessable / 7 correct → 16 / 16**; `narrowed` **147 → 29**, no bar right-to-wrong. On the scan the stem tier is the whole gain (per-staff readings right **401 → 430 of 733**). ⚠️ `Q.STEM` "was declared in `wants` AND `composed_from` … and was read by nothing" — 916 rows on a three-page record. `benchmarks/omr-staged-duration-beams-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a plate whose beams overhang the outer stems, putting the outer head's centre inside the stroke.
- **Known exceptions:** on the scan **54 readings go wrong → right and 26 go RIGHT → wrong** — a 2:1 trade, where on the engraving every move went one way.
- **Code:** `tools/omr/staged/adjudicators/rhythm.py:164` `_stem_joined`, `:366` `_beam_levels`, `:102` `BEAM_EDGE_TOLERANCE_WIDTHS = 1.0`. The same argument for arcs: `tools/omr/export.py` (stem probes).

### A stem is one octave long by default — and as long as the music needs it to be
`[C13 + L11]`

- **Says:** the literature gives a default of **3½ staff spaces**; measured here a stem has **no fixed length** — a note two ledger lines above the staff beamed to notes inside it carries a stem far longer than any default.
- **Predicts (mechanically):** a near-vertical run about 3.5 sp long starting at a notehead's left or right edge is a stem, and the FLAG or BEAM is expected at about 3.5 sp from the head centre. ⚠️ **But a height cap on stem candidates silently un-stems exactly the notes furthest from their beam**, and then the notehead-to-beam fallback cannot reach them either.
- **Numbers:** ⚠️ **two numbers, both real — disagreement #5.** Literature: Gould p.14 "The standard length of a stem is one octave (i.e. 3½ stave-spaces) from the centre of the notehead"; LilyPond `(lengths . (3.5 3.5 3.5 4.25 5.0 6.0 7.0 8.0 9.0))` with "3.5 (or 3 measured from note head) is standard length", the longer values for 32nds and shorter; `beamed-lengths . (3.26 3.5 3.6)`. Measured here: the cap that works is **`STEM_MAX_HEIGHT_LINES = 8.0`**, on an **11× cliff**.
- **Literature:** Gould p.14 (*Stem length*); LilyPond 2.24.4 `scm/lily/define-grobs.scm:3118`. "Rigid as a default; systematically modified by the three entries that follow" — i.e. by *A stem on ledger lines reaches the middle staff line*, *A stem is never shorter than 2.5 staff spaces*, and beaming.
- **Measured here:** over **8,746 candidates on 13 pages of 8 editions** the population "decays smoothly to 8 spaces and stops, with a second population from 10 up to the height of the cell itself — barlines and brackets crossing the crop". Benchmark: 6.0 → 0.1861, 7.0 → 0.1601, **8.0 → 0.1601**, 9.0 → 0.1610. ⚠️ **The population that forced 6.0 → 8.0 is still failing**: missing stems cross the 8.0 cap at **3.7× and 47×** the rate of read ones (Litolff `no_stem` p90 **9.97**, **16.9%** over 8.0, against DECIDED p90 6.54 / 4.6%) — but in absolute reach only **80 of 784 (10.2%)** and **31 of 1,442 (2.1%)**, "a striking ratio on a small population … it is not the bulk". `benchmarks/omr-stem-ink-2026-09/FINDINGS.md` §4.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID as a default; the tail is a property of the music, not the publisher.
- **Would be falsified by:** re-taking the measurement that set 8.0 and finding the two populations still separate there; or a plate whose in-staff stems cluster at a length other than ~3.5 sp.
- **Known exceptions:** the LilyPond beam ground truth (`benchmarks/omr-phase4-lines`) "is unchanged at every stem cap tried (6, 7, 8, 9, 12) **because its music has no long stems. It could not have caught this and does not pretend to.**"
- **Code:** `tools/omr/line_detection.py:170` `STEM_MAX_HEIGHT_LINES = 8.0`.

### Two successive notes are set further apart than one accidental's own two strokes
`[C14]`

- **Says:** the horizontal spacing between successive notes exceeds the internal spacing of a single accidental glyph.
- **Predicts (mechanically):** two vertical strokes within 0.9 staff spaces that overlap vertically are one accidental, not two stems — **so both may be dropped.**
- **Numbers:** gap **0.9 staff spaces**, vertical overlap **0.6** of the shorter.
- **Literature:** not covered. ⚠️ The literature supplies the counter-hypothesis instead: *Two voices on one staff* `[L17]` and *A stem is about a tenth of a staff space thick* `[L14]`.
- **Measured here:** the rule's own record says it takes summed |error| **from 60 to 24 on 14 cells**. ⚠️⚠️ **Against it:** evaluating the rule's predicate on the raster at every head, the MISSING stems stand beside a close vertical partner at **94.6% (Litolff, n=496) / 79.8% (Breitkopf, n=1,037)** against **80.7% (n=1,011) / 15.7% (n=1,586)** for the stems we read — an excess of **+13.8 and +64.1 points**. "**That rule DELETES BOTH MEMBERS of a pair.**" The predicted failure mode is **two-voice writing, not accidentals**: an up-stemmed upper voice and a down-stemmed lower voice in one column are two strokes within 0.9 spaces that overlap vertically. `benchmarks/omr-stem-ink-2026-09/FINDINGS.md` §0.4, §4b.
- **Status:** MEASURED HERE — **and its premise is now under direct challenge.**
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT.** "That premise is a claim about how tightly **this plate** sets its notes, measured on 14 hand-counted cells."
- **Would be falsified by:** `detect_stems(..., drop_accidental_pairs=False)` — "**THE DECIDING EXPERIMENT IS ONE ARGUMENT**", a GATHER change needing two full re-gathers, and it must score both directions.
- **Known exceptions:** the measurement is a **PROXY that over-fires** (raw 600-dpi ink, no morphological opening) — "the differential is the evidence, not the level".
- **Code:** `tools/omr/line_detection.py:173` `_drop_paired_strokes`.

### No stem means a whole note
`[C15]`

- **Says:** the absence of a stem is positive evidence of duration.
- **Predicts (mechanically):** a stemless head corroborates `whole`; the duration decision currently reads the notehead class alone.
- **Numbers:** **no figure.** The only adjacent number is that **9 and 87** of the two `no_stem` populations are whole notes and are excluded from the stem-convention work as "the decision being right".
- **Literature:** not covered as a rule — but *A whole notehead is wider than a black one* `[L4]` names exactly this pairing from the other side: a reader distinguishing hollow heads should use "**width and the presence of a stem, never height**".
- **Measured here:** not measured here. Stated in `docs/exploration-what-is-on-the-page-2026-09-09.md` §B.5: "Absence-of-stem is *positive* evidence for duration … Cheap to add as corroboration; only worth it if `adjudicate_duration` declares it."
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a measurable population of stemless heads that are not whole notes (beyond detector misses).
- **Known exceptions:** ⚠️ a head whose stem the CV rung simply missed is indistinguishable from a genuinely stemless one — **which is the whole of `[C9]`'s 1,125-head population.**
- **Code:** no consumer found.

### Stacked beams are set 0.75 staff spaces centre to centre
`[C79 + L20]`

- **Says:** a beam stroke is **half a staff space** thick and the gap between two stacked strokes is **a quarter** — so their centres are **three quarters of a space** apart.
- **Predicts (mechanically):** **clustering beam y-positions has a KNOWN correct tolerance.** Two ink rows closer than that are one fragmented stroke, not two levels. A stack of N beams spans about `0.5 + 0.75(N−1)` staff spaces. And the gap is NARROWER than the stroke, so an erosion tuned to open the gaps **will eat the strokes first**.
- **Numbers:** ✅ **the two sources agree to the number.** Bravura `beamThickness` **0.5**, `beamSpacing` **0.25** → pitch **0.75**; LilyPond `(beam-thickness . 0.48)`. Measured here the population is bimodal with an empty interval: **0.19–0.26, 460 pairs — one physical beam, fragmented**; **0.65–0.79, 69 pairs — genuinely stacked (a 16th)**. Constant `BEAM_Y_CLUSTER_FACTOR = 0.35`.
- **Literature:** Bravura `engravingDefaults`; SMuFL *engravingDefaults*; LilyPond 2.24.4 `scm/lily/define-grobs.scm:439`. "Narrow band across fonts; plates vary more."
- **Measured here:** "exactly where engraving convention puts stacked beams". `tools/omr/rhythm.py:131` carries the measurement in its docstring.
- **Status:** MEASURED HERE — **and it reproduces the font default on a real plate.**
- **Rigid or publisher-dependent:** RIGID (a typographic convention of setting).
- **Would be falsified by:** a plate whose stacked-beam separation falls in the **0.26–0.65** gap.
- **Known exceptions:** ⚠️ a **YOLO** beam box bounds the STACK, not a stroke, so it contributes a centre in the GAP between two strokes and destroys the bimodality — which is why a YOLO beam is kept only where no CV beam overlaps its x-range (union → kept: pooled **0.1917 → 0.1861**, Brahms duration rate 0.916 → 0.931).
- **Code:** `tools/omr/rhythm.py:131` `BEAM_Y_CLUSTER_FACTOR = 0.35`, consumed at `:1449`.

### A FLAG glyph NAMES A VALUE, and it hangs on the STEM
`[C80 + L23]`

- **Says:** the engraver draws one flag glyph however many hooks it carries — a sixteenth's flag is one mark with two hooks — and it is attached to the stem's far end, not to the notehead.
- **Predicts (mechanically):** **counting is right for beams and wrong for flags** — `levels = len(flags)` reads a `flag16thUp` as one level when it is two. And **a flag must be associated with a note via its STEM**, not by proximity to the head: the flag sits about 3.5 staff spaces away from it.
- **Numbers:** Gould p.15: "The engraved design of tail is **2½–3¼ stave-spaces long (3–3¼ is the norm)**. This ensures that the tail of an up-stemmed note finishes opposite or just above the notehead." Bravura `flag8thUp` bbox **1.056 × 3.276** sp, with a `stemUpNW` anchor at `[0.0, −0.04]`. SMuFL: "Flags are positioned such that y=0 corresponds to the end of a stem of normal length, and x=0 corresponds to the left-hand side of the stem."
- **Literature:** SMuFL *Metrics and glyph registration*; Gould p.15 (*Tails*); Bravura. **One flag per beam level** — two for a semiquaver — and each additional tail or beam requires the stem to be lengthened.
- **Measured here:** the bug was `levels = len(flags)`; `_FLAG_LEVELS` is now **derived** from `rhythm._FLAG_DURATIONS` rather than restated. In the same repair, **112 flags attached (109 deciding)** where before `beam_evidence == "flag"` occurred **zero times**. ⚠️ On the staged path the stem rule beats the legacy one, whose docstring says it cannot use the stem because *"the notehead's stem direction isn't reliably available from a 0-stem detector"* — **stale since `gather_cv_lines` reads 916 of them.** `tools/omr/staged/adjudicators/rhythm.py:206-216`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID in attachment; the tail's design length is a font/house matter within the stated band.
- **Would be falsified by:** a class space that split flags per hook; or flags drawn at the notehead end of the stem.
- **Known exceptions:** ⚠️ **a note under a beam carries no flag**, so a notehead with a beam level AND a flag on its stem is a contradiction — a truth-free probe. Rate: **engraved 3 of 112 flagged notes (2.7%); Litolff scan 7 of 37 (18.9%); Breitkopf 27.5%** — "ordered engraved < Litolff < Breitkopf, i.e. **the worse the ink, the more the flag half picks up**". No gate was added. Literature adds: a down-stemmed note's tail "may curve as far as to touch the notehead", **so a flag's INK can reach the head even though its attachment does not.**
- **Code:** `tools/omr/staged/adjudicators/rhythm.py:216` `_flag_levels_table`; legacy `tools/omr/rhythm.py` `_flag_for_notehead` (x-centre proximity, the weaker rule).

### A stem on ledger lines reaches the middle staff line
`[L12]`

- **Says:** for a note more than one ledger line outside the staff, the stem is drawn long enough to reach the staff's middle line.
- **Predicts (mechanically):** **a very long stem is not an error — it is positive evidence that its notehead is two or more ledger lines outside the staff**, and it PREDICTS that the far end terminates at the middle line rather than at a free height. So a stem whose far end lands on the middle line **constrains its head's pitch from the other direction**, and gives a cheap check on a ledger-note pitch reading.
- **Numbers:** none beyond "to the middle stave-line".
- **Literature:** Gould p.14 (*notes on ledger lines*): "Stems for notes on more than one ledger line extend to the middle stave-line". Corroborated by Wikipedia, *Stem (music)*. Rigid and long-standing.
- **Measured here:** not measured here. ⚠️ **But this is the literature explaining a measured population:** `[C13]`'s second mode "from 10 up to the height of the cell itself" and the missing-stem excess over the 8.0 cap (Litolff p90 **9.97**, **16.9%** over 8.0) are exactly the notes this convention describes. It is also the untested pitch check `[C3]` and `[C10]` both want: the ledger-country head is where **44% are off-grid** and where the stem convention REVERSES.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** rigid.
- **Would be falsified by:** ledger-note stems of standard 3.5 sp length, leaving a gap before the staff.
- **Known exceptions:** Gould notes that in double-stemmed writing stems outside the staff are **progressively shortened** instead (p.15).
- **Code:** no consumer found.

### A stem is never shorter than 2.5 staff spaces
`[L13]`

- **Says:** as stems fall further outside the staff they are progressively shortened, and there is a hard floor of a sixth.
- **Predicts (mechanically):** **a FLOOR on stem length: no candidate shorter than 2.5 staff spaces is a stem.** Useful as a rejection rule, and it bounds how short a stem can be when several beams have to be accommodated.
- **Numbers:** Gould p.14: "The shortest stem length is a sixth (2½ stave-spaces): **no stem should ever be shorter than this.**" LilyPond `(stem-shorten . (1.0 0.5 0.25))` — a forced-direction stem shortened by **one staff space**, a flagged stem by half — sourced in its own comment to "[Roush & Gourlay]".
- **Literature:** Gould p.14 (*double-stemmed writing*); LilyPond 2.24.4 `scm/lily/define-grobs.scm:3136–3138`. "Gould states it as absolute. LilyPond's shortening amounts are its own defaults."
- **Measured here:** not measured here. ⚠️ The repo has a cap (**8.0**) and **no floor**; `line_detection` has never been priced against one.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** stated as absolute by Gould.
- **Would be falsified by:** engraved stems measuring under 2.5 sp.
- **Known exceptions:** grace notes and cue-size notation are scaled down as a whole.
- **Code:** no consumer found.

### A stem is about a tenth of a staff space thick
`[L14]`

- **Says:** stems are thin — thinner than a beam by roughly 4×, and comparable to a staff line.
- **Predicts (mechanically):** bounds the width of a vertical-run detector's target, and ⚠️ **says thickness alone CANNOT separate a stem from a thin barline** — 0.12 against 0.16 is too close. **Height and position must.**
- **Numbers:** Bravura `stemThickness` **0.12** against `thinBarlineThickness` **0.16** and `staffLineThickness` **0.13**. Application defaults: Finale 0.12, Sibelius 0.1, Dorico 0.16, MuseScore 0.13 — range **0.10–0.16**.
- **Literature:** Bravura `engravingDefaults`; Scoring Notes. "Variable within a narrow band."
- **Measured here:** not measured here as a thickness. ⚠️ The repo reaches the same conclusion from the other side and pays for it: *A barline runs the FULL HEIGHT of its system* `[C56 + L74]` separates barline from stem by **extent**, because on WTC I Prelude 1 p.4 the right hand "read none of [the barlines] and **31 of its own stems**". And `[C83]` measures the systemic barline at **0.16 sp wide**.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** **Variable** within a narrow band.
- **Would be falsified by:** engraved stems measurably thicker than barlines.
- **Known exceptions:** none recorded.
- **Code:** no consumer found.

### Where there is no case for either direction, the stem goes DOWN
`[L15]`

- **Says:** the convention for an undetermined stem direction is down.
- **Predicts (mechanically):** **a prior with a known direction.** A reader guessing a stem direction from weak evidence should guess DOWN, not up, and a system whose ambiguous cases resolve upward is mis-calibrated.
- **Numbers:** none. LilyPond encodes it as `Stem` `(neutral-direction . ,DOWN)`.
- **Literature:** Gould p.14: "When there is no clear-cut case for either direction, the convention is to use a down-stem. Some editions use down-stems exclusively." LilyPond `define-grobs.scm:3148`.
- **Measured here:** not measured here as a prior. ⚠️ The measured baseline is adjacent and worth putting beside it: on 1,443 heads, "always the commoner direction" scores **0.506** `[C10]` — i.e. on that document the commoner direction is very close to a coin flip, so **this prior is worth almost nothing there** and the convention's own value is 0.787.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** **Variable by edition and by genre, and Gould says so in the same breath** — some editions use down-stems exclusively; "Some editions of vocal music use up-stems only, to allow the text to be placed close to the stave."
- **Would be falsified by:** nothing — the exceptions are stated with the rule.
- **Known exceptions:** vocal music set with up-stems throughout; editions that use down-stems exclusively.
- **Code:** no consumer found.

### Two voices on one staff: upper voice up, lower voice down, regardless of position
`[L17]`

- **Says:** where two voices share a staff, the upper voice takes up-stems and the lower takes down-stems, and the middle-line rule is suspended.
- **Predicts (mechanically):** **stem direction becomes a VOICE LABEL rather than a position consequence.** A bar containing both up- and down-stemmed notes at positions the middle-line rule cannot explain **is a two-voice bar** — a cheap, ink-level detector for divisi and for the `<backup>` an exporter must write. It also predicts that within such a bar every up-stemmed note is higher than or equal to its simultaneous down-stemmed note.
- **Numbers:** none.
- **Literature:** Wikipedia, *Stem (music)* ("Different stem directions serve to distinguish separate voices in polyphonic music written on the same staff") plus corroborating notation references. "Rigid where two voices genuinely share a staff."
- **Measured here:** not measured here as a detector. ⚠️ **It is, however, the named failure mode of two measured rules:** `[C10]`'s middle-line convention is "broken constantly by two-voice writing and chords", and `[C14]`'s accidental-pair stroke rule has two-voice writing as its **predicted failure mode** — "an up-stemmed upper voice and a down-stemmed lower voice in one column are two strokes within 0.9 spaces that overlap vertically", and that rule **DELETES BOTH MEMBERS of a pair**. So building this detector and fixing `[C14]` are plausibly the same job.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** rigid where two voices genuinely share a staff.
- **Would be falsified by:** a two-voice bar whose voices are not separated by stem direction.
- **Known exceptions:** unisons, where both voices may share one head; more than two voices, where the convention runs out.
- **Code:** no consumer found.

### Stem direction is held constant through a beat or half-bar
`[L18]`

- **Says:** where stem direction would otherwise vary inside a bar, notes belonging to the same beat or half-bar keep one direction.
- **Predicts (mechanically):** **stem direction is a piecewise-constant function over METRICAL units, not a per-note function.** A run of same-direction stems is evidence of a beat grouping, and a direction change inside a bar marks a beat or half-bar boundary — **a metrical signal read off geometry with no duration reading at all.**
- **Numbers:** none.
- **Literature:** Gould p.14: "When the stem direction varies within a bar, maintain the stem direction of the notes that are part of the same beat or half-bar". "Stated by Gould as the convention; strength varies by edition."
- **Measured here:** not measured here. ⚠️ It is a sibling of *Beaming follows the metre* `[L22]` — both propose a metre signal from geometry — and the repo file records that beaming-as-beat-grouping is **named in the exploration doc and consumed by nothing.** The meter family wants exactly this: `[C28]`, `[C29]` and `[C33]` all lean on bar sums as a second witness, and `[C64]`'s hazard is that **the bars fall silent exactly where the meter is worst**. A geometric metre signal does not share that failure mode.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** conventional; strength varies by edition.
- **Would be falsified by:** bars whose stem directions alternate note-by-note under the middle-line rule.
- **Known exceptions:** multi-voice bars, where voice decides.
- **Code:** no consumer found.

### In a chord containing a second, the two heads straddle the stem
`[L19]`

- **Says:** where two chord notes are a second apart, they cannot share a side: the higher goes right of the stem and the lower left.
- **Predicts (mechanically):** ⚠️⚠️ **two noteheads at ADJACENT staff positions, horizontally offset by about one notehead width, sharing one stem, are ONE CHORD — not two events and not a duplicate detection.** "This is the printed signature of a chordal second and it is **the case most likely to be misread as a spurious doubled note**."
- **Numbers:** the offset is one notehead width, **1.18 staff spaces** in Bravura. Bravura carries dedicated anchors for the case (`splitStemUpSE`, `splitStemDownNW`).
- **Literature:** Wikipedia, *Stem (music)*: "the stem runs between the two notes with the higher being placed on the right of the stem and the lower on the left." Rigid.
- **Measured here:** not measured here — **and it is a live candidate explanation for a complaint this project has.** Sean's Phase-2 observation was *"there are a lot of doubled notes on a staff that dont make sense (2 of the same note next to each other connected to the same stem)"*, which the repo diagnosed as an ownership contest being **relocated rather than resolved** (`ffff` from one printed `ff`; repeated-pitch chord events **122 → 108**). ⚠️ That repair explicitly did **not** reach zero: "the remainder is the SAME-CELL population, which a contest-based repair structurally cannot reach". **A chordal second is a same-cell, one-stem pair at adjacent positions, which is exactly that residue's shape.** Untested.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** rigid.
- **Would be falsified by:** engraved chordal seconds drawn with both heads on one side.
- **Known exceptions:** clusters of three or more adjacent notes, where "middle notes appear on the opposite side".
- **Code:** no consumer found.

### A beam is angled by the OUTER interval, and is horizontal in three named cases
`[L21]`

- **Says:** the beam's slope follows the interval between the **first and last** notes of the group, not the group's most extreme interval, and is flat in three specific situations.
- **Predicts (mechanically):** **the beam's slope PREDICTS the pitch relation of the group's outer notes, independently of reading either notehead** — a rising beam means the last note is higher than the first. And a horizontal beam is positive evidence for one of three shapes: the group begins and ends on the same note; the pitches repeat a pattern; or an inner note is closer to the beam than either outer note (a concave group). **A cross-check on a pitch reading using only the beam's geometry.**
- **Numbers:** none for the angle. LilyPond caps slope damping at `(damping . 1)` and uses `auto-knee-gap . 5.5` staff spaces as the interval at which it breaks a group into a knee.
- **Literature:** Gould p.22 (*Direction of beam angle*, *multi-directional beamed group*). "Rigid as a principle; the magnitude of the slope is house style."
- **Measured here:** not measured here. ⚠️ Worth noting that the repo already reads beams well enough to try it: `[C79]` measures 460 + 69 beam pairs on a real plate, and `[C12]` attaches **707 stem/beam pairs**. This is a pitch cross-check that needs **no pitch reader**, which is the scarce kind — `[C64]`'s hazard is that a second witness read off the same ink falls silent together with the first, and a beam's SLOPE is a different measurement from a notehead's position.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** rigid as a principle; slope magnitude is house style.
- **Would be falsified by:** engraved groups whose beam slope tracks the inner extreme rather than the outer notes.
- **Known exceptions:** the three horizontal cases are the exceptions, and they are enumerated.
- **Code:** no consumer found.

### Beaming follows the metre, and never crosses the middle of the bar
`[L22]`

- **Says:** divisions of a beat are beamed together to make beats legible, and notes are not beamed across the bar's midpoint.
- **Predicts (mechanically):** **a beam group is a METRICAL unit, so beam boundaries are beat boundaries** — a metre signal from beam geometry alone, with no duration arithmetic. And the mid-bar prohibition means **a beam that appears to span the middle of a bar is evidence that the bar segmentation is wrong**, not that the engraver was permissive.
- **Numbers:** none.
- **Literature:** Gould p.153 (*Beaming according to the metre*): "Divisions of a beat are beamed together in all metres"; "notes should never be beamed over the middle of the bar, since the third beat carries a secondary stress".
- **Measured here:** not measured here. The repo file records beaming-as-beat-grouping as **named in the exploration doc and consumed by nothing.**
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** ⚠️⚠️ **rigid in the modern convention, and GOULD EXPLICITLY RECORDS THAT IT IS NOT HISTORICAL** — "Music from the Classical and Romantic periods frequently uses this beaming – the context makes it clear that cross rhythm is not intended." **That exception matters for 19th-century plates, which is what this project reads** — see disagreement #6.
- **Would be falsified by:** nothing — the era exception is stated with the rule.
- **Known exceptions:** Classical and Romantic engraving; deliberate cross-rhythm; half-bar beaming, which Gould permits in some metres.
- **Code:** no consumer found.

---

## Rests & bar filling

### A whole rest stands for THE BAR, whatever the meter
`[C16 + L27]`

- **Says:** an engraver fills an otherwise silent bar with ONE centred whole rest of nominal 4.0 quarters, and the glyph means **"this bar"**, not "four quarters".
- **Predicts (mechanically):** a bar whose only event is a lone dotless `restWhole` takes **the BAR's** length; MusicXML writes it as `<rest measure="yes"/>` with **no `<type>` at all**. ⚠️ Conversely it carries **NO information about what the meter is** — it is the same glyph in 2/4 and 12/8 — **so it must never be counted as evidence when deriving a meter from bar sums.**
- **Numbers:** none for the geometry; the duration is the meter in force.
- **Literature:** Wikipedia, *Rest (music)*: "When a bar is devoid of notes, a whole (semibreve) rest placed at the middle of the measure is used, **regardless of the actual time signature**." Rigid in modern practice.
- **Measured here:** **558 of 618 wrong rest durations (90.3%)** on the scan gate are such a bar, 543 of them our `whole`/4.0 against a truth measure rest of 2.0. Ledger, eleven works: `rest.type` **933 → 10**, `rest.duration_ql` **328 → 4**, `matched_exact` **3,154 → 4,077**, "every non-rest family identical to the row". In the staged path the same convention as a consequence fires on **92 of 92** bars where the meter is DECIDED and **0 of 195** where it abstained. ⚠️⚠️ **OMR-NED CHARGED NOTHING FOR ANY OF IT** — engraved pooled **0.12138 / 2532 in both arms, identical in all 23 categories**; the scan gate **34,963 edits in both arms**. `benchmarks/omr-rests-2026-09/FINDINGS.md` §7-§13; `benchmarks/omr-rest-sizing-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE — one of the two largest single wins in the repo.
- **Rigid or publisher-dependent:** RIGID in modern practice.
- **Would be falsified by:** a plate that prints a half rest in a 2/4 tacet bar.
- **Known exceptions:** ⚠️ **the glyph is part of the rule** — the first cut accepted any lone rest and inflated bars holding a single detected **quarter** rest, a **34-edit** cost. `measure="yes"` is withheld where the meter is UNKNOWN. ⚠️⚠️ **The literature names historical exceptions that are real in this repertoire:** 4/2 (a breve rest), 3/2 and 6/4 (a dotted whole rest), and metres shorter than 3/16 (a rest of the true length) — "**These are real in 19th-century and earlier plates.**" And a blank bar is a third state — see *A silent bar is still PRINTED with a rest*.
- **Code:** `tools/omr/export.py:1739` `_is_lone_measure_rest` → `:1788` `_mxl_empty_measure`; staged `tools/omr/staged/consequences.py:123` `size_measure_rest`.

### A whole rest HANGS under the 4th line; a half rest SITS on the 3rd — and they are the same shape
`[C17 + L24 + L25]`

- **Says:** both are a filled rectangle half a staff space tall, and they differ **ONLY** in which line they touch.
- **Predicts (mechanically):** ⚠️⚠️ **the vertical slot is the rest's IDENTITY, not decoration — NO shape, size or aspect-ratio classifier can ever separate a whole rest from a half rest.** A reader reporting confidence in `restWhole` vs `restHalf` from a crop alone is reporting something it cannot know.
- **Numbers:** ✅ **the sources agree and the literature supplies the font geometry.** Bravura: `restWhole` and `restHalf` both **1.128 × 0.576** staff spaces — aspect w/h ≈ **1.96**, h/w ≈ **0.51** — with `restWhole` running y = **−0.540 to +0.036** (below the baseline) and `restHalf` y = **−0.008 to +0.568** (above it). Measured here: `WHOLE_REST_STEP = 5.5` (bottom line 0, one step per half space), "⚠️ **NOT TUNED** — it is the engraving convention, and it is an **obligation rather than a preference**, which is what makes it usable as a witness at all".
- **Literature:** SMuFL, *Metrics and glyph registration*: "The font baseline should represent this staff position, **with the exception of the whole note (semibreve) rest, which should hang from the font baseline.**" The whole rest hangs from the **fourth line**, the half rest sits on the **third**. Bravura `glyphBBoxes`. Rigid.
- **Measured here:** used as one of two witnesses for `OMR_WHOLE_REST_INK`: **SHAPE alone fires on 148 of 2,347 noteheads**, **POSITION alone on 310** and "is nearly uninformative: the band a whole rest hangs in is where C5 and D5 live in treble"; **together they fire on 25, and all 25 were cropped and looked at — all 25 are whole rests**. ⚠️ On the second publisher the witness **INVERTS**: `slot 20 / neighbour 5` → **`slot 1 / neighbour 11`**, and of 12 fires **one is a whole rest**. `tools/omr/staged/record.py:775-795`; `benchmarks/omr-note-where-silence-2026-09/FINDINGS.md`; `benchmarks/omr-second-publisher-pricing-2026-09/`.
- **Status:** MEASURED HERE (the slot); the *discriminator between whole and half* is ASSERTED and unused.
- **Rigid or publisher-dependent:** RIGID — "whatever the clef, key or music — the engraver has no freedom about it".
- **Would be falsified by:** a plate printing whole rests at a different slot; or any shape measurement that separates whole from half.
- **Known exceptions:** ⚠️⚠️ **the measured step is not the printed step on a warped scan** — correctly-read whole rests spread over steps **2.5–5.9** against the nominal 5.5 (see `[C8]`), and **18.3% of Breitkopf's `restWhole` detections stand outside their own staff against Litolff's 3.5%**. ⚠️ And the literature names the other killer: **in multi-voice writing rests are displaced from their default position** (LilyPond `Rest` `(voiced-position . 4)`), which **destroys the absolute-position discriminator** and leaves only the relation to the surrounding voice.
- **Code:** `tools/omr/staged/adjudicators/rhythm.py:2820` `WHOLE_REST_STEP` (behind `OMR_WHOLE_REST_INK`, default ON). `Q.REST_POSITION` at `tools/omr/staged/positions.py:303` is **PRODUCER ONLY** — `adjudicate_duration` "still reads the class name and nothing else".

### A tacet part prints a whole rest in EVERY bar
`[C18]`

- **Says:** a resting instrument's staff is filled bar by bar, not left blank.
- **Predicts (mechanically):** a real whole rest **always has a neighbouring whole rest within a bar or two at nearly the same height** — so a neighbour can vouch for ambiguous ink.
- **Numbers:** `WHOLE_REST_NEIGHBOUR_BARS = 2`, "**deliberately SHORT** … while a long reach would let one distant rest vouch for ink anywhere on the staff. **3, 4 and 8 all admit the same one extra glyph.**" `WHOLE_REST_NEIGHBOUR_STEPS = 1.5`, plateau **1.0–3.0**.
- **Literature:** not covered directly; *A multi-bar rest is an H-bar* `[L30]` is the competing convention for the same musical situation, and it is the falsifier below.
- **Measured here:** the witness pair delivers **25 of 25 hand-adjudicated whole rests, 0 real notes** on Litolff. `tools/omr/staged/adjudicators/rhythm.py:2827-2836`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a plate using multi-bar rest bars (`restHBar`) across a tacet run — the pipeline already abstains `unreadable_rest` on those.
- **Known exceptions:** `restHBar` / `restHNr` "name no single value, so the decision abstains rather than inventing one".
- **Code:** `tools/omr/staged/adjudicators/rhythm.py:2827` `WHOLE_REST_NEIGHBOUR_BARS = 2`.

### Rest shapes separate strongly by aspect ratio — except whole vs half
`[C19 + L26]`

- **Says:** the rest family's glyphs have very different proportions from one another, so aspect is a strong discriminator ACROSS rest values even though it is useless WITHIN the whole/half pair.
- **Predicts (mechanically):** aspect ratio (h/w) alone **rules out** "our 209 quarter rests are misread whole rests". A reader confusing a whole rest with a quarter rest is failing on **ink quality, not on geometry**.
- **Numbers:** ✅ **the sources agree closely.** Bravura: whole/half **1.128 × 0.576** (h/w ≈ **0.51**); quarter **1.076 × 2.992** (h/w ≈ **2.78**); 8th 0.988 × 1.700 (≈1.72); 16th 1.280 × 2.716 (≈2.12); also `restMaxima` 1.524 × 1.996, `restLonga` 0.500 × 1.996, `restDoubleWhole` 0.500 × 1.000. **A whole rest and a quarter rest differ in h/w by more than 5×.** Measured here on Litolff Beethoven 5 pp.1-4: `restWhole` median aspect **0.46, max 0.91**; `restQuarter` median **2.66, min 1.40** — **0 of 209 overlapping**, "an EMPTY INTERVAL", at the highest median confidence of any rest class.
- **Literature:** Bravura `glyphBBoxes`. "The ordering is rigid; exact ratios vary by font and by plate."
- **Measured here:** `benchmarks/omr-rest-sizing-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE — **one-sided.**
- **Rigid or publisher-dependent:** RIGID on the document measured.
- **Would be falsified by:** a plate whose quarter rests read under 1.40 aspect, or whose quarter rest is wider than tall.
- **Known exceptions:** ⚠️⚠️ **IT IS ONE-SIDED AND ESTABLISHES NOTHING POSITIVE** — "`arpeggiato` fires 377 times on this same document as *'a stem or a barline'*, the same tall thin shape". A tall thin box is not thereby a quarter rest. ⚠️ And the literature's own caveat: "**Broken or bled ink on a scan will not respect any of it.**"
- **Code:** not a shipped rule; `WHOLE_REST_INK_MIN_ASPECT = 1.63` / `MAX_ASPECT = 3.09` at `tools/omr/staged/adjudicators/rhythm.py:2807/2814` use the same axis for the inverse question. ⚠️ **Those cuts do not transfer**: the shipped band describes **89.9%** of Litolff's own whole rests and **52.5%** of Breitkopf's.

### A silent bar is still PRINTED with a rest; a genuinely blank bar means we failed to read it
`[C20]`

- **Says:** the engraver never leaves a sounding part's bar empty — **silence is written.**
- **Predicts (mechanically):** ink coverage in a cell separates "this instrument rests here" from "the detector found nothing here" — **two facts that currently produce the identical `<rest measure="yes"/>`.**
- **Numbers:** **no measurement of the discriminator.** The gap is quantified: "**66 bars hold no gathered ink at all; 178 come out with no event**", so on **112 bars the page gave us ink and no event came out**.
- **Literature:** not covered — it is the premise beneath *One whole rest fills any bar* `[L27]` rather than a stated rule.
- **Measured here:** the collapse is recorded rather than hidden: "a bar with no notes gets a measure rest because we read NOTHING in it, not because we read silence", and `empty_bars_padded` is reported apart from `measure_rests_read`. The proposed discriminator — cell ink coverage — "`direction_text._blank_detections` already computes [it] for another purpose". `docs/exploration-what-is-on-the-page-2026-09-09.md` §B.1.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** measuring ink coverage on hand-adjudicated silent vs unread bars and finding the distributions overlap.
- **Known exceptions:** a tacet bar of a part **held out of the file** is a third state again — `_pad_tacet_span` refuses to write one where the bar length is unknown, and counted **149 refused / 0 padded** on the only document available.
- **Code:** the collapse lives at `tools/omr/export.py:1788` `_mxl_empty_measure`. **No consumer of the discriminator found.**

### A whole-bar rest is centred in the bar
`[L28]`

- **Says:** the bar-filling rest is placed horizontally at the **middle** of the empty measure, not at its head.
- **Predicts (mechanically):** ⚠️ **a usable left/centre discriminator for ink at the head of an otherwise empty measure.** A rest near a bar's horizontal CENTRE with nothing else in the bar is a whole-bar rest; **a mark at the bar's LEFT EDGE is more likely a clef, key signature, meter or barline fragment.**
- **Numbers:** none.
- **Literature:** Wikipedia, *Rest (music)* / general references: the whole rest is "placed at the middle of the measure". Conventional and widely followed.
- **Measured here:** not measured here — ⚠️⚠️ **but it independently predicts a measured finding.** `[C34]`'s live consequence is that Litolff p.62's `timeSig3`+`timeSig4` are **one barline broken into two fragments, both 0.35–0.40 staff spaces wide at `x_canonical = 0`, at the head of an EMPTY REST BAR**. This entry says in advance that ink at a rest bar's left edge is not the bar's rest — and the pipeline read it as a meter. **The convention was available and unused.**
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** conventional and widely followed.
- **Would be falsified by:** bar rests engraved flush left.
- **Known exceptions:** none recorded.
- **Code:** no consumer found.

### A rest is centred on or about the middle of the staff
`[L29]`

- **Says:** rests take a default vertical position in the staff's centre region rather than tracking the pitch around them.
- **Predicts (mechanically):** **a rest's y carries no pitch information, so a reader must not resolve it as one**; and a mark in the staff's middle region that is not a notehead is a rest candidate. ⚠️ Where multiple lines or voices are in play, a rest that is part of a beat aligns **HORIZONTALLY** with adjacent notes — **so its x is meaningful even though its y is not.**
- **Numbers:** none.
- **Literature:** Gould p.284 (*placing rests*, percussion chapter): "Centre each rest around the middle space or on the middle line"; "When there are multiple lines, place a rest that is part of a beat on a horizontal level with adjacent notes."
- **Measured here:** not measured here. ⚠️ The x half is the one this project could use now: `[C64]` measured that a column through a system is one instant (1.62× / 2.29× against a null) and the INFER stage consumes it — **a rest aligning with adjacent notes is an onset the column layer currently cannot see**, because `Q.EVENT` groups noteheads.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** Gould states it for percussion staves; the same default holds generally. **Multi-voice writing displaces rests deliberately.**
- **Would be falsified by:** rests whose height varies with the surrounding pitch in single-voice writing.
- **Known exceptions:** multi-voice displacement (LilyPond's `voiced-position . 4`) — the same exception that breaks the whole/half slot discriminator.
- **Code:** no consumer found.

### A multi-bar rest is an H-bar one staff space thick
`[L30]`

- **Says:** several bars of silence are shown as a thick horizontal bar between two vertical strokes, with a number above.
- **Predicts (mechanically):** **an H-bar is the thickest horizontal ink on the staff** — 1.0 staff space, **twice a beam's 0.5** — "so an H-bar is separable from a beam by thickness alone". It also predicts a NUMERAL centred above the staff, and that **the span consumes several bars of the document's bar sequence at once, which a bar counter must account for.**
- **Numbers:** Bravura `hBarThickness` **1.0** staff space, against `beamThickness` 0.5.
- **Literature:** SMuFL *engravingDefaults*; Bravura `engravingDefaults`. "Reasonably rigid; some editions use the older stacked-rest forms instead."
- **Measured here:** not measured here. ⚠️ **The pipeline meets these glyphs and correctly refuses them:** `restHBar` / `restHNr` "name no single value, so the decision abstains `unreadable_rest` rather than inventing one" `[C18]`. So the class is reached and **the bar-count consequence is unhandled** — this entry's second prediction has no consumer.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** reasonably rigid.
- **Would be falsified by:** a plate whose multi-bar rests are drawn at beam thickness.
- **Known exceptions:** older editions use church-rest stacks rather than an H-bar. MOLA requires the number range to be printed and multi-bar rests to be broken at rehearsal landmarks.
- **Code:** the abstention is at `tools/omr/staged/adjudicators/rhythm.py` (`unreadable_rest`). No consumer for the bar-count consequence.

---

## Accidentals & key signatures

### An accidental is a SCOPE to the end of the bar — and it carries across a barline through a TIE
`[C21 + L33 + L34]`

- **Says:** an accidental is **not a property of one notehead**: once printed it governs later notes at the same letter and octave until the barline, and where a note bearing one is tied over the barline, it continues to apply to the tied note.
- **Predicts (mechanically):** reading left to right within a bar, a later notehead of the same letter+octave inherits the alteration **with no glyph of its own** — so the ABSENCE of a mark is a positive statement about pitch, and a reader attaching an accidental only to its immediate note reads every later note in the bar a semitone wrong. ⚠️⚠️ **And the tie rule gives a TRUTH-FREE SELF-CHECK: a tie whose two ends resolve to different pitches is positive evidence that the rule was not applied.**
- **Numbers:** none for the geometry — the scope is `(staff position, from this x to the next barline)`.
- **Literature:** Wikipedia, *Accidental (music)*: "Accidentals apply to subsequent notes on the same staff position for the remainder of the measure … Once a barline is passed, the effect of the accidental ends"; and "If a note with an accidental is tied, the accidental continues to apply, even if the note it is tied to is in the next measure." Rigid in common-practice notation.
- **Measured here:** implemented and exercised on every run; **no A/B prices it alone.** Its structural consequence is recorded: "an accidental is not a glyph property, it is SCOPE … **the staged record has nowhere to put the state. This is the clearest case where the missing quantity is a *span*, not a mark.**" ⚠️ **The tie half IS measured, and it is the measurement the literature predicts:** the far head of a cross-barline tie does not restate its accidental and the resolver spells it plain, so **11 of the engraved 20 and 11 of the scan cases are same-STEP, accidental-differs** — *the probe's* fault, not the pairing's. `benchmarks/omr-tie-pairing-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE (implemented and relied on) — **no isolated figure for the convention itself.**
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a plate restating accidentals per note (some modern editions do) — which is a courtesy style, not a contradiction.
- **Known exceptions:** courtesy accidentals; and other octaves, where conventions vary.
- **Code:** `tools/omr/transcribe.py:2211-2267` (`explicit_in_measure`, keyed on `(letter, octave)`). The staged record has **no span quantity** — no consumer there. `gather_coverage` files `accidental` under `FAMILY_Q_IS_ELSEWHERE` for exactly this reason: 8 detector classes with no gather quantity.

### A key signature's accidentals stand at fixed slots, in a fixed order, keyed on the CLEF
`[C22 + L36 + L37]`

- **Says:** the sharps and flats of a key signature are printed in one invariable sequence, at positions fixed by convention for each clef.
- **Predicts (mechanically):** ⚠️ **READ THE POSITIONS, DO NOT COUNT THE GLYPHS.** The signature is a **SLOT TABLE keyed on (clef, count)**, so a missed interior accidental leaves a gap the table can fill where counting cannot recover it. **The Nth accidental is fully determined by N** — the reader's job is to count and locate, never to identify each accidental's letter. A run of accidentals in the WRONG order is not a key signature. And a signature read against the WRONG clef produces a **confidently wrong answer rather than an abstention**.
- **Numbers:** sharps **F♯ C♯ G♯ D♯ A♯ E♯ B♯**; flats **B♭ E♭ A♭ D♭ G♭ C♭ F♭** (the reverse). No heights given in the literature.
- **Literature:** Wikipedia, *Key signature*. Positions differ by clef — e.g. A♯ "occasionally … notated on the top line" in bass clef, and "Sharps in the tenor clef are arranged differently to avoid using a ledger line". Rigid per clef, with the documented tenor/bass variants.
- **Measured here:** on two ground-truth orchestral pages (42 staves), **given the correct clef**: **18 correct, 0 wrong, 16 missed, 8 correct abstentions** (34 of 42 carry a signature). On WTC p.17 the three stages separate cleanly: **counting the markers 6/10, fitting their positions 7/10, reconciling across the page 10/10** — "each step fixing a different failure". Against Sean's hand-read per-staff truth on Litolff pp.1-4, the staged reading goes **16 correct / 10 wrong / 49 abstained → 35 / 15 / 25**, and the FILE **33 right → 44 of 75**. `benchmarks/omr-keysig-truth-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a plate whose signature accidentals do not sit on the conventional slots for the read clef, or print them in another order.
- **Known exceptions:** ⚠️ **it inherits the clef** — "a wrong clef produces wrong signatures rather than abstentions (measured: bass staves defaulted to treble read 3 flats as 2 sharps)", so a staff whose clef is only the positional default is **skipped**. ⚠️⚠️ **It may not INFER** — recovering slots nothing was detected at compounded five matches into **seven sharps on a four-sharp page**.
- **Code:** `tools/omr/key_signature_geometry.py` (slot-table fit); `key_signature_locator.py`; `key_signature_template.py`; `key_signature_vote.py`.

### A key signature stands BETWEEN the clef and the meter
`[C23 + L40]`

- **Says:** the header is printed in one fixed left-to-right order — **clef, then key signature, then time signature.**
- **Predicts (mechanically):** **the accidental search is a bounded 1-D strip, not a page search**, and each reader's window is bounded by the others' results. Anything left of the key signature is the clef; anything right of it and left of the first note is the meter. ⚠️ **A meter template search must start AFTER the key signature — searching from the bar's left edge will find clef ink.**
- **Numbers:** for scale, Bravura: `gClef` **2.684 × 7.024** sp, `fClef` 2.756 × 3.588, `cClef` 2.796 × 4.048 — "the clef alone consumes roughly 2.7 staff spaces of the header, and a key signature several more". The shipped header window is **16.00 staff spaces**.
- **Literature:** Gould p.152: "At the beginning of a piece, the time signature goes after a clef and any key signature." Rigid.
- **Measured here:** given the correct clef for every staff of Beethoven 5 p.1, the connected-component locator reads **2 of 12**; the bounded template search reads **11 of 12** standalone. End to end on p.1: key signatures **4/12 → 7/12 correct with 0 wrong**, exact-pitch recall **0.571 → 0.619**; over six pages, staves spoken for **29% → 39%**. ⚠️ Positions come from the **ink centroid inside the matched box**, not the box centre — "box centres leave ±0.5 step of jitter, enough for the fit to read three flats as five". And outline correlation cannot separate the glyphs: "a flat's outline correlates with a G clef at **0.57–0.59** against real flats' **0.65–0.76**, too close to separate by score".
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** an edition printing the meter before the key signature.
- **Known exceptions:** ⚠️⚠️ **the empty-window hazard** — on p2/s1, all eleven header windows measured **6.1–6.2 staff spaces** against 16.00 elsewhere, holding the margin label and the systemic rule and no music; the locator abstained and **the template answered a confident `fifths: 0`**. "*The reader that can say 'zero' is the one that must never be given an empty window*". Fixed by anchoring the margin on the MEDIAN of the per-staff left-edge estimates (`system_left_consensus`): windows with a `barline` right edge **12 → 1**.
- **Code:** `tools/omr/staff_header.py` (`measure_header_window`, `system_left_consensus`); `key_signature_template.py`; `time_signature_locator.py:400` supplies the right bound.

### A key CHANGE is printed at ONE bar of ONE system, on EVERY staff of it
`[C24]`

- **Says:** the engraver announces a key change simultaneously across the whole system, at one bar.
- **Predicts (mechanically):** ⚠️ **the BAR is the shared fact even where the VALUE differs by transposition** — so a mid-staff key change that no other staff of the same system also changes at the same bar can be reverted, **without needing the staves to agree on the key.**
- **Numbers:** `MIN_WITNESSES = 2`.
- **Literature:** not covered directly; *The key signature is reprinted at the start of every system* `[L38]` is the adjacent convention and it is about restatement, not change.
- **Measured here:** over 11 scanned + 11 engraved stored transcriptions, **7 of 7** spurious mid-staff flips on the scan corpus are stopped — 5 of the 7 "had already been rejected once by the cross-page header vote and the mid-staff reader overturned it anyway". Flag-ON changes **5 of 11 scan fixtures and 0 of 11 engraved**. Flag OFF is byte-identical by construction, verified with `diff`. `benchmarks/omr-keysig-corroboration-2026-09/`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a real mid-staff key change that fails its own witness test.
- **Known exceptions:** ⚠️⚠️ **the corpus contains ZERO real mid-staff key changes, so only the BENEFIT is measured** — and there is "concrete reason to expect [the cost] non-trivial: later-cell key markers appear on only **15 cells across 193 scanned staves with no two sharing a bar**, so a genuine mid-staff change would more likely fail its own witness test than pass it".
- **Code:** `tools/omr/key_signature_corroboration.py:202` `MIN_WITNESSES = 2` (default ON since 2026-09-07). The staged meter mirror **asserts equality** with it: `tools/omr/staged/adjudicators/rhythm.py:1423` `METER_CHANGE_MIN_STAVES = 2`.

### The clef and key signature are reprinted at the head of EVERY system
`[C25 + L38]`

- **Says:** a performer's eye cannot hold them, so they are restated at each system start within a part.
- **Predicts (mechanically):** **a part has many independent readings of one fact, which a cross-system vote can reconcile** — and therefore **a staff that reads no key signature on a continuation system is a READING failure, not an engraving fact.** ⚠️ It also means the PAGE carries more clef glyphs than the encoding declares. ⚠️⚠️ **A time signature is NOT reprinted, so the two families must not be treated alike** — see *A meter is printed at a movement's START and nowhere else*.
- **Numbers:** none.
- **Literature:** MOLA, *Parts*: "Clefs and key signatures must appear at the beginning of each line." Rigid in modern preparation and standard in engraved orchestral scores.
- **Measured here:** the cross-page vote took WTC I p.17 from **6/10 to 10/10** on key signatures. The page-vs-encoding gap is measured on the Brahms fixture: **28 G-clef glyphs against 14 `<sign>G</sign>`** in the file it was rendered from. `benchmarks/omr-reading-vs-reproduction-2026-09/FINDINGS.md`; `docs/ideal-reader-2026-09-07.md` §(b).
- **Status:** MEASURED HERE (as redundancy) / **ENCODING caveat attached** — see *A PAGE truth is not an ENCODING truth*.
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** an edition that states the clef once per page, or omits the key signature on continuation systems.
- **Known exceptions:** instruments conventionally written **without** a key signature at all (next entry). ⚠️ The staged path **consumes none of** `key_signature_vote.reconcile`, deliberately — keyed on a wrong staff→part join it "would carry the viola's 7 onto the timpani".
- **Code:** `tools/omr/key_signature_vote.py` `reconcile` (legacy path only); `tools/omr/staff_header.py`. **No staged consumer.**

### A courtesy accidental is real ink that changes nothing — and its frequency is a property of the EDITION
`[C26 + L35]`

- **Says:** editors print reminder accidentals — often in parentheses — where a previous bar's accidental might mislead; whether they do varies by publisher.
- **Predicts (mechanically):** ⚠️ **an accidental's presence does not imply a pitch change.** A reader counting accidentals as evidence of chromaticism, or using them to infer a key, will be misled. Its presence or absence is **evidence about the EDITION, not about the music**. Parenthesised accidentals are a separate glyph family and should be read as such.
- **Numbers:** none, from either source.
- **Literature:** Wikipedia, *Accidental (music)*. MOLA and IU both call for their use — IU requires "courtesy accidentals … for natural pitches in new bar following accidental in previous bar". "**Entirely editorial.** Frequency varies enormously by publisher and era."
- **Measured here:** ⚠️ **no figure anywhere in the tree.** One sentence: "**No courtesy accidental** — publisher-dependent, so its presence or absence is evidence about the EDITION rather than the music. Filed as curiosity" (`docs/exploration-what-is-on-the-page-2026-09-09.md` §B.8). The repo file searched `benchmarks/` and `tools/` and found none.
- **Status:** ASSERTED (untested here) — ✅ **and the literature independently asserts the same thing**, which raises confidence without making it a measurement.
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT.**
- **Would be falsified by:** measuring courtesy-accidental rate per publisher and finding it flat.
- **Known exceptions:** none recorded.
- **Code:** no consumer found.

### Timpani, horns and trumpets are conventionally written WITHOUT a key signature
`[C81 + L39]`

- **Says:** in this repertoire the natural-horn, natural-trumpet, timpani and tuned-percussion staves carry no key signature at all — the accidentals are written in.
- **Predicts (mechanically):** ⚠️ **a ZERO read on one of those staves is EXPLAINED, not a failure.** Such a staff must be excluded as a witness to the page's key, and its own zero must not be treated as a disagreement. **A reader that votes a system's key signature onto every staff will write a wrong signature onto exactly these staves; a reader that flags them as failures will mis-rank its own work.** Which staves these are is knowable from the margin label or the score order **before any ink is read**.
- **Numbers:** none, from either source.
- **Literature:** MOLA, *Parts*: "Traditionally, horns, tuned percussion, and timpani use any required accidentals rather than a key signature." ⚠️ **"Traditional rather than absolute" — MOLA's own word is "traditionally"**, and modern editions increasingly do print signatures for horns. "Expect it to hold on 19th-century plates and to weaken after."
- **Measured here:** ⚠️ **no measurement of the convention itself.** Declared verbatim at `tools/omr/key_consensus.py:86`: `NO_SIGNATURE_CONVENTION = frozenset({"Timpani", "Horn", "Trumpet", "Cornet", "Flugelhorn"})` — "⚠️ This is a claim about ENGRAVING PRACTICE … and it is NOT derivable from the staff … **it only ever explains a ZERO.**" Its consequence IS visible in a measured figure: of the 33 key readings counted as "right in the file" on Litolff pp.1-4, **17 are abstentions that happen to land on a horn, trumpet or timpani** — right for the wrong reason.
- **Status:** ASSERTED (untested here) — ✅ **independently asserted by MOLA**, which is the strongest corroboration in this registry short of a measurement.
- **Rigid or publisher-dependent:** RIGID for the repertoire named; **era-dependent** by both sources' own statements.
- **Would be falsified by:** a held 19th-century edition printing key signatures on its horn and timpani staves.
- **Known exceptions:** a sibling set is declared and explicitly unmeasured — `MAY_DIFFER_NOT_A_WITNESS = frozenset({"Harp"})` at `tools/omr/key_consensus.py:101`, for pedal/enharmonic reasons, "⚠️ **DECLARED, NOT MEASURED**". Literature adds: transposing instruments **other** than these carry their own transposed signature normally.
- **Code:** `tools/omr/key_consensus.py:86`, consumed `:257` (witness exclusion) and `:402` (outcome `CONVENTION_NO_SIGNATURE`). ⚠️ `MIN_WITNESSES = 3` there is **concert-pitch staves** — a different constant and unit from `key_signature_corroboration.py:202`'s 2.

### An accidental stands BEFORE its note, at the same staff position
`[L32]`

- **Says:** the accidental is printed immediately to the left of the head it alters, at that head's height.
- **Predicts (mechanically):** **two constraints, not one: SIDE and HEIGHT.** An accidental must be joined to the notehead to its RIGHT **and at its own staff position** — never to the nearest head in any direction. "**The height constraint alone rules out most mis-attachments in a dense chord.**"
- **Numbers:** none for the horizontal gap.
- **Literature:** Wikipedia, *Accidental (music)*: "An accidental applies to the note that immediately follows it." Rigid.
- **Measured here:** not measured here. ⚠️ **The join is implemented and has never been priced as a geometry** — `explicit_in_measure` is keyed on `(letter, octave)` after the pitch is resolved, i.e. downstream of the attachment. `gather_coverage` files `accidental` under `FAMILY_Q_IS_ELSEWHERE`: **8 detector classes with no gather quantity**, the largest such family. So on the staged path there is no accidental row for a side-and-height rule to act on.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** rigid.
- **Would be falsified by:** accidentals printed after their notes.
- **Known exceptions:** some 20th-century notation places accidentals above notes; not relevant to orchestral repertoire.
- **Code:** no consumer found for the geometric join.

---

## Time signatures & meter

### A time signature's placement is RIGID — and its numerals fill the staff's height
`[C27 + L42]`

- **Says:** the meter's two digits occupy fixed halves of the staff, centred on one another, and each is set large — about two staff spaces tall — in a heavy font.
- **Predicts (mechanically):** **turns a 2-D search into a 1-D one** — a composite template per candidate meter, slid along the header window in x. And it gives **a gate on SIZE that rejects small numerals outright**: a digit-shaped mark one staff space tall is a fingering, a tuplet number or a measure number, **not a meter**.
- **Numbers:** ✅ **the two sources agree and the literature adds the size.** SMuFL: "Digits for time signatures should be scaled such that each digit is **two staff spaces tall, i.e. 0.5 em**, and vertically centered on the baseline." Bravura `timeSig4` **1.720 × 2.004** sp. Gould p.152: "Time-signature numerals should exactly fill the height of the stave. Smaller numerals are not sufficiently conspicuous." Measured here: numerator in the upper two spaces, denominator in the lower two, centred on each other.
- **Literature:** Gould p.152 (*Size and placing*); SMuFL *Metrics and glyph registration*; Bravura `glyphBBoxes`. Gould notes the numerals use "a unique heavy font so that they stand out as clearly as possible against the stave" — **a further discriminator from body numerals.**
- **Measured here:** over a corpus "half of which is pages printing no meter at all": **4 correct, 0 wrong, 12 correct abstentions**, across a 600-dpi scan of 19th-century type and LilyPond pages set in a different font from the templates — "where the detector reads **zero** digits on the same page". Beethoven 5 p.1 emits 2/4 instead of 4/4 and its LilyPond bar-check failures fall **154 → 104**. Corpus total over 11 sources after the letter-meter and vote work: **12 correct, 0 wrong, 3 missed, 40 correct abstentions**, up from 3 wrong. `benchmarks/omr-timesig-2026-08/`, `benchmarks/omr-timesig-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a plate printing digits off-centre or spanning the middle line as a rule; or meters set at body-text size.
- **Known exceptions:** ⚠️ **on a bitonal plate ink bleed fuses numerator and denominator into one stroke**, so a `spans` reading "is entirely compatible with a real meter"; and the converse — two fragments in two halves **is also what a BROKEN BARLINE looks like** (Litolff p.62). Sean, 2026-09-17: *"Quick rules will give us quick results that could be poor."* ⚠️ Gould cross-references *Enlarging time-signature symbols* (p.519): **conductors' scores sometimes set the meter LARGER than the staff, spanning several staves.**
- **Code:** `tools/omr/time_signature_locator.py:400` `locate_time_signature` — ⚠️ the placement is **a constraint INSIDE the template search that is then thrown away**. `Q.METER_GLYPH_POSITION` records it (`tools/omr/staged/positions.py:357`) and **`adjudicate_meter` does not read it**.

### A meter is printed at a movement's START and nowhere else
`[C28 + L41]`

- **Says:** the time signature holds for a whole movement or until it changes, and is restated only at a new movement — **not per system.**
- **Predicts (mechanically):** ⚠️ **a continuation system printing no meter is the NORMAL CASE, not a reading failure — the exact opposite of the key signature.** So the meter must be CARRIED from an earlier system, and a reader expecting one on every system **will read noise as a meter**. It also predicts that a meter **DOES reappear at a movement start even when unchanged**, which makes a restated meter a movement-boundary signal. Carry it as a **CANDIDATE its own bars confirm or refuse**, not as a gate.
- **Numbers:** `OMR_METER_CARRY` support scores: on Litolff Beethoven 5 mvt 1 pdf p1-3, `carried` ×4 at support **+6.0 / +13.0 / +9.0 / +18.0**. Boundary case on an engraved render (Beethoven 5 mvt 4, 4/4 → 3/4 at bar 155): the TRUE meter **+8.0** (8 bars fit / 1 not), the FALSE one **−8.0** (0 / 9).
- **Literature:** Gould p.152: "It holds good for a whole movement or up to a change of metre. It should be repeated at the beginning of a new movement, even if this is the same as that of the previous movement, and even when the music follows on from the previous movement without a break". Rigid.
- **Measured here:** systems decided **1 of 5 → 5 of 5**, `<time>` **28 → 54 and ALL of them `2/4` in both arms**, bars that add up **54.4% → 81.2%** like-for-like over the 1,109 bars present in both arms, with **298 wrong→exact and 0 exact→wrong**. ⚠️ **DO NOT QUOTE THE RAW 90.8%** — it includes 1,159 tacet bars the ON arm adds, exact by construction. Rests at 4.0 go **471 → 115**, at 2.0 **109 → 465**, `empty_bars_padded_without_meter` **168 → 0**. `benchmarks/omr-staged-meter-boundary-2026-09/FINDINGS.md`; `benchmarks/omr-rest-sizing-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID — and **the opposite of the clef/key convention `[C25 + L38]`, which is why both flags exist.**
- **Would be falsified by:** a document where a carried meter propagates a misread across many systems — **which no document in the corpus supplies**: the misread-carry cell is empty in all three shapes tried.
- **Known exceptions:** ⚠️ **a carried meter must never cross a movement boundary blindly** — it needs no movement detector, because the bars refuse it: on Litolff p.63 the carried `2/4` is refused at **−6.0** while the same bars name **3.0 at +5.0**, the printed `3/4`. ⚠️ The *Andante* refusal is **SAFE but NOT discriminating**: scored against the `3/8` that page actually prints, it refuses that too (−1.0 and −1.0). ⚠️ MOLA requires meter changes to be indicated in **PARTS** even during extended rests, "which can put a meter where a score would not".
- **Code:** `tools/omr/staged/adjudicators/rhythm.py:2025` `_carry_meter`; legacy `transcribe` carries with `source="carried_from_previous_page"`.

### A meter is printed on EVERY staff of the system
`[C29]`

- **Says:** the time signature is restated on each staff, so one system carries as many independent readings as it has staves.
- **Predicts (mechanically):** **vote across the staves of a system; a reading on one staff of seventeen is not a meter.**
- **Numbers:** the agreement floor is **0.70**, a FRACTION of the system — "every one of the 12 correct readings is agreed by **0.909** of its system or more and the one wrong reading … by exactly **0.500**". `_dominant_detected_meter` takes **one vote per staff and requires half the page's staves**.
- **Literature:** not covered as such. ⚠️ It is the direct consequence of *At a system's start the order is clef, key signature, time signature* `[L40]` applying to every staff, but no consulted source states it.
- **Measured here:** "the opening reader's **16.75%** per-staff false rate is contained by the cross-staff vote": over **18 continuation header systems the shipped vote declares a meter on NONE**. A change to common time was found on **23 staves of 23, unanimous**; a `¢` on **24 staves of 24 at support 74.0**. ⚠️ A believed meter is carried onto every later measure of its staff, so counting measures counts one reading many times — "a single `timeSig4` at confidence 0.42, on one staff of nineteen, arrived at the page vote as **eighteen unanimous votes** for common time". `benchmarks/omr-meter-cautionary-arbiter-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** an edition printing the meter on only the top staff of a system.
- **Known exceptions:** ⚠️⚠️ **a fixed 3-staff quorum does NOT contain the false rate in the HEADER frame** — it fires falsely on **4 of those 18 systems, one with SEVEN staves agreeing on `C`**. The shipped vote survives because `min_staff_fraction` is a FRACTION, not a count. **Do not port `METER_TEMPLATE_AT_BAR_MIN_STAVES = 3` into the header frame.**
- **Code:** `tools/omr/time_signature_locator.py` `vote_system_time_signature`; `tools/omr/rhythm.py` `_dominant_detected_meter`, `drop_uncorroborated_meter_changes`.

### A cautionary meter printed after a system's FINAL barline governs no bar
`[C30 + L44]`

- **Says:** an engraver announcing a new meter prints it **TWICE** — as a courtesy after the last barline of the ending system, and again at the head of the next. **The first governs nothing.**
- **Predicts (mechanically):** **a meter-change candidate in a staff's LAST cell is a courtesy, not a change — unless its own bar FITS.** So a reader must not size any bar from it. ⚠️ **But it is real, correct evidence about the NEXT system's meter, read from a DIFFERENT PHYSICAL PRINTING — which makes it a genuine second witness for the same fact.**
- **Numbers:** an independent second reading of the same convention by ink fraction: the one visible cautionary reads **1.000 on all 19 staves** against **≤ 0.118 for every other segment**.
- **Literature:** Gould p.152: "When a change of time signature occurs between systems, add a cautionary indication at the end of the first system, after the last barline". MOLA generalises it to clef, key and time. "Standard modern practice; MOLA requires it. **Older plates are less consistent.**"
- **Measured here:** ⚠️ **the rule was checked against the corpus BEFORE it was written**, "which is what separates it from a story fitted to its own data": **all four TRUE changes sit at a non-last cell** (Litolff p.62 cell 8 of 13, Brahms 1 i cell 1 of 8, Beethoven 5 iv cell 3 of 9, Brahms 1 iv cell 6 of 8) and **both cautionaries at a LAST cell**. With the meter-in-force fix: **false meter changes 10 → 3, no true change lost**, and the ENGRAVED arms go to **4 printed / 4 found / 0 false**. The cautionary is **RECORDED, not discarded**. `benchmarks/omr-staged-meter-boundary-2026-09/FINDINGS.md` §4c.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID in modern practice; older plates less consistent.
- **Would be falsified by:** a genuine meter change at a system's last bar whose own bar does not fit; or editions that change metre at a system break with no courtesy.
- **Known exceptions:** ⚠️ **a cautionary's VALUE is right even though its placement is not a change** — `report_boundary.TRUTH_CHANGES` records both cautionaries as `None`, "a statement about placement, not about value. **A reader who meets that `None` and concludes the cautionary is junk has read the wrong column.**" ⚠️ Only **3 cautionaries exist in the whole committed corpus**, on ONE piece of music — and using one as an arbiter against a misread opening was measured and **could not be decided**: the two readings share no currency (`support` vs `share`), and the one quantity both state — how many staves read it — reads **9 for the correct cautionary against 10 for the wrong opening**, and **compares a DETECTOR count with a TEMPLATE count**, which makes that route incoherent rather than merely unfavourable.
- **Code:** `tools/omr/staged/adjudicators/rhythm.py:1690` `_meter_changes` (last-cell discrimination).

### A letter meter (`C`, `¢`) is a complete meter — and the stroke is what separates them
`[C31 + L46]`

- **Says:** common time and cut common are single glyphs that each state a full time signature; a `C` and a `¢` are the same glyph plus a vertical stroke.
- **Predicts (mechanically):** **a meter reader that demands two stacked digits is blind to an entire family** — the commonest metre in the repertoire. ⚠️⚠️ **The two sources then disagree about HOW to separate them — disagreement #3.**
- **Numbers:** **Literature:** `timeSigCommon` **1.676 × 2.000** and `timeSigCutCommon` **1.672 × 2.880** — same width, **cut-C 44% taller**, "so **height alone separates them; the stroke does not have to be found**". **Measured here:** over **87 staves that matched C, the 24 cut ones fill 1.00 of the centre column and no other exceeds 0.48** — *every threshold in 0.50–1.00 gives the same answer*. `C` is the strongest reading in the corpus: **five common-time pages at 0.745–0.761** against 0.50–0.62 for scanned digit meters.
- **Literature:** Bravura `glyphBBoxes`. "The glyph shapes are rigid; the height ratio will vary a little by font." ⚠️ And its own known exception: "**both are four and two crotchets' worth respectively, so a LENGTH-based reader cannot distinguish `C` from 4/4 at all — only the engraving differs.**"
- **Measured here:** a change to common time was detected on **23 staves of 23** at the right bar and proposed **nothing**, because `_meter_from_digits` needs two stacked digits; fixed, it lands at support **66.0** on the exact bar. ⚠️⚠️ **Adding a cut-C TEMPLATE fails BOTH ways** — nine false systems, *and* it still loses to plain `C` on real `¢` pages, "because a C is a SUBSET of a cut-C's ink and the template with less to account for scores higher". **Fifteen of the 97 dossier works open on a `¢`**; Mozart 40 i read **11 staves of 11** and Brahms 4 i **13 of 13** as 4/4 before the fix. `benchmarks/omr-timesig-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE — **and the literature's proposed mechanism is the one this repo measured failing.**
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a plate whose cut stroke does not reach the centre column, or whose cut-C is no taller than its C.
- **Known exceptions:** ⚠️ **it produces a false positive on a scan** — one `timeSigCommon` at confidence **0.377** on one staff of seventeen on Litolff p.61, a page printing no time signature at all. "The hazard is `METER_CHANGE_FLOOR`, not the letter path": one staff reading a complete meter clears the floor by design. Confidence separates the populations cleanly (**0.887–0.927 engraved, 0.377–0.560 scan**) and is **deliberately not gated on** — "four rows on two documents is not a threshold".
- **Code:** `tools/omr/staged/adjudicators/rhythm.py:1493` `_meter_from_letter`; `tools/omr/rhythm.py` `parse_time_signature` (`symbol=` from the glyph); `tools/omr/symbol_library/builder.py`; `_looks_cut`.

### An OPENING meter sits 10–12 staff spaces into its bar, behind the clef and the key signature
`[C32]`

- **Says:** the header's fixed order puts the opening time signature **well inside the bar**, unlike a mid-staff change.
- **Predicts (mechanically):** **the window an opening meter is read in and the window a mid-staff CHANGE is read in are different widths, and they are not interchangeable.**
- **Numbers:** **10–12 staff spaces** in; the shipped header window is **16.00**. A **4-space** bar head of cell 0 reads **0 of 16**; **14 spaces reads 16 of 16**.
- **Literature:** not covered as a distance — it is the quantified consequence of `[L40]`'s clef/key/meter order, whose scale figures (`gClef` 2.684 sp wide, "and a key signature several more") predict roughly this.
- **Measured here:** on Brahms 1 / Breitkopf p.45, a movement start **whose print was looked at** (page 46, *Adagio*, full margin names, a common-time `C` on every staff): the 4-space window spells `4/4`/`9/4`/`12/16`/`5/4` **out of clef ink**, while 14 spaces and the shipped 16.00-space header window each read **16 of 16** — the header row being the **positive control**. `benchmarks/omr-meter-cautionary-arbiter-2026-09/FINDINGS.md` §3.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a movement start whose meter is legible in a 4-space window.
- **Known exceptions:** it does **not** argue against a 4-space window for a mid-staff CHANGE — "a mid-staff CHANGE is printed straight after a barline with no clef in front of it, which is exactly why that window is four spaces".
- **Code:** `tools/omr/staff_header.py` `measure_header_window` (16.00 staff spaces).

### A mid-staff meter CHANGE is printed at the bar head, with no clef in front of it
`[C33 + L43]`

- **Says:** the new meter belongs to the bar it governs, so it stands immediately to the right of the barline that opens that bar.
- **Predicts (mechanically):** ⚠️ **a meter glyph's POSITION WITHIN ITS BAR disambiguates it, with no reading of the digits**: a meter at the HEAD of a bar (left fraction ≈ 0) governs that bar; meter-shaped ink elsewhere in a bar is not a meter change. And a **4.0-staff-space slice** of the measure cell is the right window — which can then be probed on **every staff of the system, including staves that detected nothing.**
- **Numbers:** `METER_TEMPLATE_AT_BAR_MIN_STAVES = 3`, at a window of **4.0 staff spaces**. False rate by width: **0.99% / 1.55% / 2.48% at 4 / 6 / 8**.
- **Literature:** Gould p.152 (*Placing time-signature changes*): "The new time signature is always placed after the barline." Rigid. Its named exception is the cautionary, "which is exactly the case of a meter printed before a barline".
- **Measured here:** over **1,612 mid-staff bar-head windows on ten real scanned pages of two publishers printing NO meter change**, admitted on 1 staff the reader yields **16** spurious columns, on 2 **two**, on 3 **ZERO**. ⚠️ **The quorum is safe AT 4 SPACES AND NOT AT 8** — one three-staff false consensus appears at 8; "**the width and the quorum are ONE safeguard at one operating point, not two independent ones**". Positive control: a real Bravura `3/4` stamped into 225 of the same windows — **225 answered, 225 right**. The false population is **13 of 16 `C`**, recorded and not gated on. ⚠️ `min_score` is deliberately not moved: the positive control's own minimum (**0.542**) sits BELOW the worst false answer (**0.6141**) — **the populations overlap and no score threshold separates them.** `benchmarks/omr-meter-template-changes-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE **for the FALSE-POSITIVE side only.**
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a real mid-staff change the 4-space window misses.
- **Known exceptions:** ⚠️⚠️ **ACCURACY IS UNMEASURED IN ONE DIRECTION** — "no page in reach prints a mid-staff change, so the false-positive side is measured and **it has never been shown this reads a real one**". Also **38 of 51 columns (74.5%)** on Brahms 1 p1-3 are candidates, "so candidacy is NOT where the safety is".
- **Code:** `OMR_METER_TEMPLATE_AT_BAR` (default OFF, UNPRICED — a GATHER change); `Q.METER_TEMPLATE_AT_BAR`.

### "A meter stack is two digits aligned in x and adjacent in y" — REFUTED
`[C34]`

- **Says:** the proposed rule was that a genuine numerator/denominator pair is distinguishable from two unrelated digits by their x-alignment and y-adjacency.
- **Predicts (mechanically):** it would have separated true meter stacks from fragments. **It does not.**
- **Numbers:** TRUE `dy` **32–548** against FALSE **26–555**. **Total overlap.** The sibling hypothesis — *"the false ones sit at `x_canonical == 0`"* — is decisive in a per-cell table and collapses once restricted to clean two-digit stacks: **1 of 110 TRUE vs 4 of 50 FALSE**.
- **Literature:** not covered. ⚠️ The literature's surviving discriminators for the same job are **SIZE** (`[L42]`: each digit ~2 staff spaces tall, in a heavy font) and **POSITION IN THE BAR** (`[L43]`), neither of which is a dy test.
- **Measured here:** `docs/ask-first-conventions.md` §3; `benchmarks/omr-staged-meter-boundary-2026-09/FINDINGS.md` §4c.
- **Status:** **REFUTED HERE**
- **Rigid or publisher-dependent:** n/a.
- **Would be falsified by:** it already is. **Do not re-try either form.**
- **Known exceptions:** the *placement* convention `[C27 + L42]` is a different and surviving claim — the refuted one is about separating a stack from noise **by dy alone**.
- **Code:** **nothing implements it**, deliberately. ⚠️ The live consequence: Litolff p.62's `timeSig3`+`timeSig4` are **one barline broken into two fragments**, both **0.35–0.40 staff spaces wide at `x_canonical = 0`**, and `_meter_from_digits` still accepts them — while **cell 6, where the `3/4` is actually printed, fires ZERO `timeSig*` on any of 17 staves** (`benchmarks/omr-ink-gather-2026-09/FINDINGS.md`). *A whole-bar rest is centred in the bar* `[L28]` would have refused that ink on placement alone.

---

## Slurs, ties & phrasing

### A slur is drawn OVER its notes; a hairpin is drawn BETWEEN them
`[C35 + L48]`

- **Says:** a slur arcs above (or below) the noteheads it binds and **overlaps them vertically**; a hairpin lives in the horizontal space **between** note columns, in the dynamics band.
- **Predicts (mechanically):** an overlap test (`_noteheads_under`) is the right anchor rule for a slur and **structurally cannot work** for a hairpin, whose edges must be read as **POINTERS** to the nearest note either side.
- **Numbers:** an overlap test scores **0 of 4** on the Mahler 5 hairpin fixture — the Trumpet's diminuendo spans page x **5922-6068** in a bar whose only notehead spans **5817-5897**, "not one pixel of overlap". Nearest-either-side pairs **4 of 8** truth hairpins and gets all 4 exactly right; "the last note at or before the edge" pairs **1** — the ink begins slightly BEFORE the note it starts on (**26 px left of it, 105 px right of the previous note**). Bravura: `slurEndpointThickness` **0.10**, `slurMidpointThickness` **0.22** — ⚠️ the same profile as a tie, **so thickness cannot separate a slur from a tie**. LilyPond `Slur`: `height-limit . 2.0`, `ratio . 0.25`, `thickness . 1.2`.
- **Literature:** Dorico, *General placement conventions for slurs*: "A slur on a single staff always curves upwards and is placed above the notes, unless all of the notes under the slur are up-stem, in which case it curves downwards and is placed below the notes." ⚠️⚠️ **DISAGREEMENT #4:** the literature entry reasons from this that "a slur and the notes it binds are on opposite sides of the noteheads, so the arc's ink does not overlap the heads: a reader testing for 'noteheads under the arc' by box overlap **will find none**, and must probe toward the heads instead." **Measured here, the overlap test is the shipped and working rule for slurs.** The literature's instinct is half-vindicated by the **stem probe** — see *An arc over STEMMED notes*. It also predicts that a slur's SIDE and the stem direction of the notes beneath it are linked: **a slur above a run of down-stemmed notes is anomalous.**
- **Measured here:** `benchmarks/omr-hairpins-2026-09/FINDINGS.md`; `docs/ask-first-conventions.md` §2.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID. Literature notes houses differ on the slur's side — "jazz scores sometimes treat slurs as articulations, preferring them consistently above the staff".
- **Would be falsified by:** a hairpin printed over its noteheads (a piano score's between-staves hairpin is still between note columns); an edition placing slurs on the stem side by default.
- **Known exceptions:** none recorded on the repo side. ⚠️ **This entry and the next are NOT contradictory** — *over* is a claim about the VERTICAL axis and *between* about the HORIZONTAL. They are kept apart for that reason; see disagreement note #7.
- **Code:** `tools/omr/export.py:2590` `_noteheads_under` (slurs); `:2923` `_wedge_anchors` / `:2985` `_wedge_anchors_from_candidates` (hairpins).

### A slur's ink stops INSIDE both outer notehead centres
`[C36 + L51]`

- **Says:** a slur is drawn **between** its notes, so the arc is narrower than the run it binds.
- **Predicts (mechanically):** **the arc box must be PADDED before asking which noteheads it covers, or the outer note at each end is dropped.**
- **Numbers:** ⚠️⚠️ **the literature could not supply the number and this repo measured it.** Literature: `UNSOURCED — believed true, not verified`; "**Gould's *Behind Bars* almost certainly states it in the slurs chapter, which the sample pages do not include.**" Measured here: a notehead is UNDER the arc at **0.00–0.19 notehead widths vs 0.32** — constant **`_SLUR_ARC_PAD_NOTEHEADS = 0.25`**, identical output at 0.25 or 0.5.
- **Literature:** it follows from the endpoint-offset rules Dorico and LilyPond both parameterise (`note-head-gap` **0.2**, `stem-gap` **0.35** staff spaces), but **no source consulted states the horizontal inset directly.**
- **Measured here:** unpadded, "the Contrabass read `n1 -> n4` in every bar whose truth is `n0 -> n5`". With the pad, on top of the ledger fix: pooled **0.2263 → 0.2209**, edits **1584 → 1563**, `wrong slur` **81 → 61**, Contrabass **7/7 exact**. ⚠️ Merging *without* the pad LOWERED pooled OMR-NED (0.2449 → 0.2436) while **raising** the edit count — "the metric's symmetry rewarding extra symbols". `benchmarks/omr-ned-2026-08/SLURS_2026-09-01.md`; `benchmarks/omr-arc-recovery-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE — **and it closes an `UNSOURCED` literature entry with a figure.**
- **Rigid or publisher-dependent:** RIGID for the engraving; ⚠️ **the empty interval is an ENGRAVED property.**
- **Would be falsified by:** an engraving whose slurs reach past the outer notehead centres.
- **Known exceptions:** ⚠️⚠️ **widening the pad was MEASURED and REFUSED.** The constant sits in an interval the engraved Brahms fixture left EMPTY (**54 of 75 within 0.19, the next at 0.32**) while on the Litolff scan "the same distribution is a **smooth slope with no gap anywhere**, so a pad read off it would be fitted to a wish". **Do not re-tune it on a scan.** ⚠️ The literature names a plausible cause of that bimodality/spread — see *Where the outer notes have opposite stems*.
- **Code:** `tools/omr/export.py:1875` `_SLUR_ARC_PAD_NOTEHEADS = 0.25`.

### An arc over STEMMED notes is drawn stem-top to stem-top
`[C37]`

- **Says:** the same reason as *A beam stroke runs from the FIRST stem it joins to the LAST* — the arc is anchored at the stem tips, and a stem stands at the side of its notehead.
- **Predicts (mechanically):** **a notehead can be reached through its STEM**, so the head-under test gains a stem probe; the span's endpoints stay the notehead centres, so the rule is **purely ADDITIVE and needs no new constant.**
- **Numbers:** the distance from an arc's edge to the nearest head centre **outside** it has **median 0.52 notehead widths**.
- **Literature:** ⚠️ **this is the half of `[L48]` that is right.** Dorico's rule places the slur on the side away from the stems for a single voice; where the arc reaches for stem tips instead, a reader must "probe toward the heads", which is exactly what shipped.
- **Measured here:** one record exported twice: `<slur>` **32 → 40**, `<tied>` **80 → 91**, `arc_binds_fewer_than_two_notes` **551 → 519**; notes, rests, dynamics, articulations, fermatas and accidentals **all identical**, note SEQUENCE unchanged (2460 == 2460), balance still an EQUALITY, tie starts resolving onto a note of their own pitch **27.5% → 30.8%**. ⚠️ `Q.STEM` "was gathered and read by nothing on this path (1,920 rows on one record) — **the third time that quantity has been found unread**". `benchmarks/omr-arc-recovery-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a plate drawing slurs to notehead rims rather than stem tips (which would show as a different offset distribution).
- **Known exceptions:** unstemmed (whole-note) runs; and where the notes under the arc were never detected at all — **108 of 550 refused groups sit in bars where the detector produced NO notehead.**
- **Code:** `tools/omr/export.py` (stem probes inside the arc-to-notehead binding; imports `_stem_joined`'s box-overlap attachment). Legacy path deliberately passes no probes, asserted at the seam.

### One printed arc cut by a barline is still ONE arc
`[C38 + L50]`

- **Says:** a slur or tie crossing a barline is **one curve**; the per-measure crop is ours, not the engraver's.
- **Predicts (mechanically):** **arcs must be paired over the STAFF in page pixels, not per measure** — emitting each half writes two marks where the music has one. The two fragments are recognisable: **each terminates AT the cell's own boundary rather than in open space, and they are adjacent.**
- **Numbers:** **120 arcs on the Brahms fixture against 82 slurs in the truth.** Three constants, each on a measured gap: "an arc was CUT by the boundary" **0.00–0.10 spaces vs 1.58** (constant **0.5**); "the two halves are ONE slur" **0.02–1.14 spaces vs 8.04** (constant **2.0**); "a notehead is UNDER the arc" **0.00–0.19 widths vs 0.32** (constant **0.25**). "Each is a **PLATEAU rather than a peak** — the exported score is identical for the continuation tolerance anywhere in **1.0–6.0**."
- **Literature:** Wikipedia, *Tie (music)*, which lists "when holding a note across a bar line" as the first use of a tie. ⚠️ Its own note: **"The consequence for a cell-based reader is this project's own inference and is not itself in the literature."** Rigid — it is a fact about what a tie IS.
- **Measured here:** in the staged path the partition is exact: 514 arc rows → 476 merged groups, **38 arcs (7.4%) are one half of a cross-barline pair**; on another record **270 tie arcs → 261 merged groups**, and **32 of 199 arcs (16.1%) begin at their cell's left edge**. `benchmarks/omr-ned-2026-08/SLURS_2026-09-01.md`; `benchmarks/omr-staged-arc-export-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** the continuation-tolerance gap closing on a new edition. ⚠️ "**Re-check them when the geometry beneath them moves**: the continuation cluster's top went 0.53 → 1.14 across the system-grouping change, still inside the gap and changing no note, **but it moved.**"
- **Known exceptions:** ⚠️ **a slur crossing a SYSTEM BREAK needs a different anchor** — both sources say so. Measured here: "the resuming half begins ~**5.3 staff spaces** inside its cell, because the cell opens with a clef and a key signature, so it is anchored on the FIRST NOTE instead"; heights are compared RELATIVE to each staff's own top line. LilyPond never receives one (a LilyPond slur cannot span two Staff contexts).
- **Code:** `tools/omr/export.py:2498` `_merge_arcs_across_barlines`; `annotate_slurs_in_staff`, `annotate_slurs_in_slot`; `tools/omr/transcribe.py:2421` `_pair_ties_in_staff`.

### A tie's two ends are at ONE staff position, by definition
`[C39 + L47]`

- **Says:** a tie joins two statements of the same note, so both heads sit at the same place on the staff. It is drawn on the side opposite the stems.
- **Predicts (mechanically):** ⚠️ **the decisive constraint: a curve whose flanking heads sit at different staff positions CANNOT be a tie** — it is a slur, or the pairing is wrong. **A truth-free check on both the arc's class and its pairing.** Among candidate flanking pairs, one whose heads share a staff position outranks one that does not. The secondary constraint gives the tie's side: opposite the stem, so a down-stemmed pair carries its tie above.
- **Numbers:** ✅ **the literature states the rule as absolute and this repo supplied the interval.** A measured **empty interval** on the eleven engraved fixtures, in staff spaces:

  | | n | bound |
  |---|--:|--:|
  | links whose two heads read the SAME pitch | 47 | max **0.168** |
  | …plus the same-STEP spelling pairs | 11 | max **0.034** |
  | links whose heads read ONE STEP apart | 8 | min **0.435** |
  | links whose heads read further apart | 4 | min **0.906** |

  "An **empty interval from 0.168 to 0.435**, and a diatonic step is half a staff space by construction … **0.25 sits in the middle of it**." Bravura: `tieEndpointThickness` **0.10**, `tieMidpointThickness` **0.22**; LilyPond `note-head-gap . 0.2`, `stem-gap . 0.35`.
- **Literature:** Wikipedia, *Tie (music)*: "A tie is a curved line connecting the heads of two or more notes of the same pitch"; "Ties are normally placed opposite the stem direction of the notes, unless there are two or more voices simultaneously." **"The same-pitch requirement is absolute — it is what a tie MEANS."**
- **Measured here:** ⚠️ **it was written in the code's own docstring and used by neither pairing rule for months.** Reach, as an upper bound on any pairing-choice repair: links whose two heads sit at one staff position **scan 122 → 183, engraved 58 → 59**; same-pitch **scan 98 → 150** (oracle 87 → 132), engraved 47 → 48. The engraved gain is **+1 link**. Before the repair, the 20-of-79 engraved figure decomposed into **11 SPELLING** (*the probe's* fault), **8 STEP_APART** (the arc's CLASS), **4 WIDE** (the pairing); on the scan **11 / 71 / 122**. ⚠️ **25 scan links sit at ONE staff position and disagree about pitch anyway.** `benchmarks/omr-tie-pairing-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** **RIGID on an ENGRAVING; NOT rigid on a scan.**
- **Would be falsified by:** a corpus where the two distributions overlap; or an engraved tie between two different pitches.
- **Known exceptions:** ⚠️⚠️ **ON A SCAN THE INTERVAL IS NOT EMPTY, AND THIS IS THE ENTRY'S SHARPEST CAVEAT** — "same-pitch max **0.238** against a step-apart minimum of **0.013**". The convention is still true of the ink; **what fails is our reading of the positions.** "Which is why this rule is expressed in **boxes** and never consults a pitch", and why **the constant may not be re-tuned on a scan**. ⚠️ `CLAUDE.md` states the rule without this caveat — see disagreement note #7. ⚠️ Multi-voice bars suspend the side convention. ⚠️ The scan price is unmeasured: an export-only arm is structurally blind (the pairing runs in `transcribe`).
- **Code:** `tools/omr/transcribe.py:2418` `TIE_SAME_POSITION_MAX_SPACES = 0.25`, `:2421` `_pair_ties_in_staff`; mirrored at `tools/omr/export.py:2207` `_tie_flank_pair` **with the constant IMPORTED, not restated.**

### A TIE is drawn shallow and close to its two heads; a SLUR arcs clear of the notes under it
`[C40]`

- **Says:** the two glyphs differ in **depth** relative to the notes they cover.
- **Predicts (mechanically):** `depth_steps` would be the **geometric half** of the tie/slur grammar, which today decides on class and step-equality alone.
- **Numbers:** **no figure.**
- **Literature:** not covered as a depth rule. ⚠️ The literature makes the negative statement instead: Bravura gives slur and tie **the same endpoint/midpoint thickness profile (0.10 / 0.22)**, "so **thickness cannot separate a slur from a tie**" — which is precisely why depth, not weight, is the candidate.
- **Measured here:** not measured here. Stated at `tools/omr/staged/positions.py:445-447`: "`depth_steps` is the fact worth having: a TIE is drawn shallow and close to the two heads it binds, a SLUR arcs clear of the notes under it. That is the geometric half of the `OMR_ARC_RECLASS` grammar". The row is produced (`Q.ARC_POSITION`, behind `OMR_FAMILY_POSITIONS`, default OFF) and **read by nothing, deliberately.**
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID (by assertion).
- **Would be falsified by:** measuring `depth_steps` over hand-adjudicated ties and slurs and finding the distributions overlap.
- **Known exceptions:** ⚠️ **CURVATURE IS NOT DERIVABLE FROM A BOX** — "a bounding box is identical for an arc opening up and one opening down", so `opens` is recorded as `None` rather than guessed. Reading it needs the ink, which `Q.INK` now gathers and nothing joins.
- **Code:** `tools/omr/staged/positions.py:433` `_arc_discriminator`. **No consumer** — listed as `UNREAD-POSITION Q.ARC_POSITION` in `tools/omr/staged/capture.py:630`.

### Sean's S4 — an arc connected to the stem's edge AWAY from the notehead is a SLUR — REFUTED
`[C41]`

- **Says:** where an arc meets a stem far from the head, the arc is a slur rather than a tie.
- **Predicts (mechanically):** it would have supplied a tie/slur discriminator **from geometry alone, needing no pitch**.
- **Numbers:** widened (contact dropped, projected onto the head→stem-tip axis, scored ONE-SIDED as Sean stated it): reach **143 → 420 of 779**, **SIDE flat at −0.001 / −0.030**, the sweep never clearing **p = 0.079**, lift **negative in all four strata**.
- **Literature:** not covered. ⚠️ The nearest literature claims run the other way: `[L47]` puts a tie "opposite the stem direction", and `[L48]` puts a slur on the notehead side — neither says anything about WHERE ALONG a stem an arc attaches, and the repo notes `grep` for a stem attachment POINT returns nothing.
- **Measured here:** Sean, on being shown a first narrow refutation: ***"don't give up — adjust the rules to be broader."*** ⚠️⚠️ **"It is the WIDE test that fails, which is the strong negative**; the narrow sweep's non-monotonicity was a POWER problem." ⚠️⚠️ **S4's availability gradient INVERTS the usual one** — its arcs sit at median detector confidence **0.4196** against **0.5409** for those it cannot reach, so "it speaks *preferentially about the WEAKEST readings*. **A harder shape than an arbiter that merely falls silent, and it is new.**" ⚠️ The first pass had "measured a precondition and thrown it away" — 420 stemmed → **206 on the stem's side** → 143 touching stem ink, **using the middle number as a FILTER and never scoring it.** `benchmarks/omr-arc-grammar-2026-09/FINDINGS.md` §1-§2.
- **Status:** **REFUTED HERE — at full width.**
- **Rigid or publisher-dependent:** n/a.
- **Would be falsified by:** it already is, on this document. n = 1 document.
- **Known exceptions:** **a narrow operationalisation failing is evidence about the OPERATIONALISATION, not about the convention** — which is why the wide test was run, and why the wide result is the one that counts.
- **Code:** **not implemented anywhere.**

### Sean's S6 — of two arcs stacked over each other, the LOWER is a tie and the UPPER a slur
`[C42]`

- **Says:** vertical stacking of two arcs names their kinds.
- **Predicts (mechanically):** a **pairwise** discriminator for the only population it addresses — stacked pairs whose two readings DISAGREE.
- **Numbers:** S6's precondition (a y-disjoint sibling arc overlapping in x) is met by **442 of 779 arcs (56.7%)**, of which **181 pairs** have two readings that DISAGREE. S6 **holds at 0.740** on the tight band and "survives every relaxation while gaining only 8% population — **robustness, not a bigger result**". ⚠️ **The absolute-position form is already REFUTED at 0.517, so its power is PAIRWISE.**
- **Literature:** not covered.
- **Measured here:** ⚠️⚠️ **the joint result is the largest finding of that job**: `OMR_ARC_RECLASS` (S2/S5) "scores BELOW its own majority baseline alone (**0.5043 vs 0.5275**) and reaches **0.750** where it concurs with S6 (**p = 0.0104**, 20,000-draw permutation null)". `benchmarks/omr-arc-grammar-2026-09/FINDINGS.md` §3.
- **Status:** MEASURED HERE — **supported, on a narrow and thin population, and deliberately NOT promoted.**
- **Rigid or publisher-dependent:** RIGID (by assertion); measured on one document.
- **Would be falsified by:** **seventy hand-adjudicated crops** of stacked disagreeing pairs — "**The price to settle S6 is SEVENTY CROPS, not more arcs.**"
- **Known exceptions:** **Neither is promoted**: S6 would flip ~30 arcs a page and get **19 of 73 wrong** against a detector that is not truth. ⚠️ S6 may be confounded with the hugging rule `arc_owner` already applies — "S6 might be nothing but the hugging rule". And "**S6 is a claim about ENGRAVING that our detector may not be able to see**".
- **Code:** **not implemented anywhere.**

### The tie/slur POSITION GRAMMAR (S2/S5), measured on both families and REFUSED
`[C43]`

- **Says:** an arc spanning more than two notes is a slur; an arc whose flanked heads carry different pitches is a slur.
- **Predicts (mechanically):** an export-time veto reclassifying the detector's arc class.
- **Numbers:** engraved **0.1306 → 0.1306, +2 edits, 24 firings**; scan **0.8387 → 0.8391, +130 edits — REFUSED**, with per-direction attribution putting **ALL +130 in the tie→slur half** while slur→tie alone is edit-free and moves the tie inventory toward truth (420 → 462 of 805). ⚠️ **The +2 is STALE and `CLAUDE.md` says so**: on the post-chord-tie tree engraved is **2530 → 2536, +6** and the scan **+149** (pre-mirror: +8 and +144).
- **Literature:** ✅ **the underlying convention is stated as absolute** — `[L47]`: "The same-pitch requirement is absolute — it is what a tie MEANS", and `[L48]`: a slur joins DIFFERENT pitches. **The literature supports the grammar; it is the VETO that is refused, for what it costs.**
- **Measured here:** ⚠️⚠️ **re-priced 2026-09-11: the tie→slur half is FOUR RULES that do not behave alike.** `tie_to_slur_flagged_diff_pitch` (PROVABLE: the flanked pair sits a staff step or more apart, which no tie can) fires **12** times and the three works where it fires ALONE are **−4 edits, i.e. BETTER**; every edit-positive work fires a `span` or `unpaired` rule, which are INFERRED. Scored against the tie INVENTORY the veto takes `mozart-sym41-mvt1` from **8 ties over its truth to exactly right**, summed per-work error **25 → 18**. The reason the scan side loses is structural: "**a scan's resolved pitch at an arc's ends is downstream of exactly what scans get wrong** (`wrong note` = 26% of that pool)". `benchmarks/omr-export-gaps-2026-09/FINDINGS.md`; `benchmarks/omr-tie-pairing-2026-09/FINDINGS.md` §4.
- **Status:** **REFUTED HERE** as a shipped default. **The underlying convention is sound; the veto is refused for what it costs.**
- **Rigid or publisher-dependent:** the convention is RIGID; the veto's cost is **document-dependent**.
- **Would be falsified by:** the `diff_pitch` half measured alone on a scan.
- **Known exceptions:** ⚠️ it **compares STEPS, never spelled pitches** — the naive spelled-pitch key broke truth-matched cross-barline ties (**+21 engraved edits**, every loss a same-step `F#4→F4` pair), which is *An accidental … carries across a barline through a TIE* arriving as a bug.
- **Code:** `OMR_ARC_RECLASS`, default OFF, flag-off byte-identical. Staged mirror: `adjudicate_arc_kind` **RECORDS** the grammar without acting on it — available on **81 of 199** arcs, agreeing **42** / disagreeing **39**, "a coin flip", with 28 of the 39 in the expensive direction.

### A bar's first note sits 2.0–2.5 staff spaces past the barline
`[C44]`

- **Says:** the engraver leaves a fixed indent after a barline before the first note.
- **Predicts (mechanically):** it *would* let a cross-barline arc whose continuation fragment is ~0 px wide reach the next bar's first chord — **and it is exactly why that reach is REFUSED.**
- **Numbers:** **2.0–2.5 staff spaces past the barline on all 282 edge-reaching arcs.** Modelled, the cross-barline reach is worth **+13 alone and +19 on top of the stem rule**, and the two are **SUPER-ADDITIVE (171 → 199 → 218)**.
- **Literature:** not covered. ⚠️ The nearest relevant literature entry is *A whole-bar rest is centred in the bar* `[L28]`, which makes the complementary claim about the OTHER thing that can stand at a bar's head.
- **Measured here:** "any window wide enough to admit it admits every next-bar first note and **the rule degenerates to *'an arc touching a barline lands on the next bar's first note'*. That is a tie-break among candidates the ink does not distinguish — INFER-shaped work**". `benchmarks/omr-arc-recovery-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE — and used to **REFUSE** a rule, not to build one.
- **Rigid or publisher-dependent:** RIGID on the document measured.
- **Would be falsified by:** a plate whose post-barline indent varies enough to discriminate.
- **Known exceptions:** none recorded. **The distribution is TIGHT, which is precisely the problem.**
- **Code:** **deliberately no consumer** — recorded with its reach "so a session holding the print can adjudicate it".

### Where the outer notes have opposite stems, the slur end moves toward the noteheads
`[L49]`

- **Says:** a slur spanning notes whose outer stems point in opposite directions is adjusted at the stem end so that it does not tilt against the pitch direction.
- **Predicts (mechanically):** ⚠️⚠️ **a slur's endpoints are NOT at a uniform offset from their notes** — they move toward the heads in this specific configuration. **So an endpoint-to-head distance measured across a page will be BIMODAL rather than tight, and a fixed tolerance fitted to the common case will refuse this one.**
- **Numbers:** none; the magnitude is unspecified.
- **Literature:** attributed to Gould, *Behind Bars*, via Scoring Notes and a NOTATIO forum thread: "When outer notes have opposite stem directions, move the slur at the stem end towards the noteheads so it does not tilt contrary to the direction of the pitches." ⚠️ **"The primary text was not read — this is a secondary attribution."**
- **Measured here:** not measured here — ⚠️ **but it is a candidate explanation for a measured spread this project refused to tune on.** `[C36]` found the pad distribution to be an **EMPTY INTERVAL on the engraved fixture (54 of 75 within 0.19, the next at 0.32)** and **a smooth slope with no gap anywhere on the Litolff scan**, and refused to move the constant. This entry predicts a second, further mode; whether the scan's slope is that mode or is scan noise **has not been asked.** `[C37]` measured the arc-edge-to-head distance at a **median 0.52 notehead widths** for heads outside the arc, without splitting by the outer stems' directions.
- **Status:** LITERATURE ONLY (untested here) — **and the source is secondary.**
- **Rigid or publisher-dependent:** stated as a rule; magnitude unspecified.
- **Would be falsified by:** slurs engraved at a uniform stem-end offset regardless of the outer stems.
- **Known exceptions:** none recorded.
- **Code:** no consumer found.

### A slur must begin and end in the same voice
`[L52]`

- **Says:** a phrase mark belongs to one voice and does not cross between them.
- **Predicts (mechanically):** **a candidate arc whose two ends fall in different voices of a two-voice bar is mis-paired.** ⚠️ Since voice is readable from stem direction (`[L17]`), **this is a check available before any pitch is resolved.**
- **Numbers:** none.
- **Literature:** `UNSOURCED — believed true, not verified`. "It is how MusicXML encodes slurs (within a `<voice>` stream) and how LilyPond scopes them, but **no notation source consulted states it as an engraving rule**."
- **Measured here:** not measured here. ⚠️ The repo's arc pairing **already enforces the MusicXML consequence** — `[C38]`'s merge requires both ends to land in the same voice because "MusicXML pairs `<slur>` within a `<voice>`", i.e. it is enforced as a FILE constraint rather than tested as an engraving one. The distinction matters: a mis-paired arc that crosses voices is currently **dropped as malformed**, not **re-paired**.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** believed rigid in single-staff writing.
- **Would be falsified by:** engraved slurs joining two voices of one staff.
- **Known exceptions:** **cross-staff slurs in piano and harp writing** are a real and separate case.
- **Code:** enforced as a file constraint in `tools/omr/export.py` (`_voice_of_notehead`, the `number=` allocator); **no consumer as an engraving test.**

---

## Dynamics & hairpins

### A hairpin is printed BELOW its staff, in the dynamics band — and dynamics are not placed INSIDE the staff
`[C45 + L55]`

- **Says:** a wedge lives in the band from the staff's bottom line down toward the next staff's top; the dynamic band lies **outside** the staff's five lines.
- **Predicts (mechanically):** **search staff N's own band in PAGE PIXELS** — a reader that does this **never creates the cross-staff contest in the first place.** And it is a **gate**: dynamic-shaped ink within the staff's own lines is not a dynamic. The band is a strip of page, parallel to the staff and outside it, **which a reader can look at directly rather than waiting for a detector to fire inside a measure cell.**
- **Numbers:** measured here, shipped as `BAND_TOP_SPACES = 0.3` / `BAND_BOTTOM_SPACES = 6.0` — the staff's bottom line + ~0.5 spaces down to the next staff's top. **"8 of 8 [hairpins] in the page truth sits below a staff and none inside one."**
- **Literature:** Dorico via Steinberg help: "In general, dynamics are not placed within the staff, as hairpins in particular become very hard to read." **"Strong convention; crowded 19th-century plates do violate it."**
- **Measured here:** the contrast that makes the band the *fix*: the hairpin reader "works in **page pixels per staff** so attribution is right BY CONSTRUCTION, while the letters go through per-measure cells and lose **24%** to the staff above". Reading F1 on hairpins against exact page truth is **1.000** (n=3) on engravings and **~1% on scans** (1 hairpin detected against **198 `<wedge>` of truth**). `docs/scope-cv-hairpin-detection-2026-09-04.md` §2; `benchmarks/omr-hairpin-cv-2026-09/`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID — ⚠️ with the literature's caveat that **congested 19th-century engraving does violate the inside-the-staff gate.**
- **Would be falsified by:** a hairpin printed above its staff (a piano score's between-staves hairpin is still below the upper one); a plate routinely setting hairpins across the staff lines.
- **Known exceptions:** ⚠️ **the band is CROWDED** — it also holds slur and tie arcs and the words `pizz.`, `espr.`, `arco`; on Brahms 1 p2 two tests cut **471 band components to 69**. **So the band bounds the search; it does not identify the mark.**
- **Code:** `tools/omr/hairpin_detection.py:80-81` `BAND_TOP_SPACES = 0.3`, `BAND_BOTTOM_SPACES = 6.0`; cited at `tools/omr/staged/gather.py:957`.

### A dynamic LETTER stands in its own staff's band, below the bottom line
`[C46 + L53]`

- **Says:** `p`, `f`, `sf` are printed in the same band as the hairpins, belonging to the staff **above** them. The default side depends on the kind of staff — **below an instrumental staff, above a vocal one** — so that the mark never falls between noteheads and lyrics.
- **Predicts (mechanically):** ⚠️ **a letter detected in a measure cell but standing in the band of the staff ABOVE belongs to that staff, not to the cell it was cropped in.** The literature states the same thing as a **cross-staff attribution rule that needs no confidence comparison**, and names the mechanism: "**It is exactly the geometry that makes cell padding steal dynamics from a neighbour.**"
- **Numbers:** over **1,246 letters on 18 pages of 9 publishers**, **73% of letters stand in their own staff's band, 24% in the band of the staff immediately above — distance exactly 1, no exceptions.** Pooled widest empty interval **−3.04 to −0.52 spaces**; the lower edge is a plateau (−1.5 to +0.25 changes nothing); the population runs **+0.0 to +5.6 spaces with a 2.5-space empty gap under it.**
- **Literature:** Dorico / Steinberg help and Scoring Notes; "**Gould is cited by those sources as recommending the same convention. Gould's own text was not read on this point.**" Strong convention; the vocal/instrumental split is universal.
- **Measured here:** ⚠️⚠️ **A GATE IS THE WRONG FIX**: **83% of re-attributed letters are the target staff's SOLE evidence**, because `_dedupe_cross_staff_detections` already removed the twin BY DISTANCE. Re-attribution priced: canonical 11 engraved works over-emission **1.19 → 1.04**, staves exact by word **52 → 83 of 107**, no work worse; **11 scanned pages: 16 → 16** (flat, because there we UNDER-emit — 376 words against 491). `benchmarks/omr-dynamics-band-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a plate printing dynamics above the staff as a rule; an orchestral edition setting its dynamics above the staves.
- **Known exceptions:** on a scan the dominant dynamics error is "**a mark never found, not one on the wrong staff**", and **137 of a 129-mark shortfall come from two scans of one page**. ⚠️ Literature adds two: **grand-staff instruments** (next entry but one), and **a staff carrying two players may print one part's dynamics above and the other's below.**
- **Code:** ⚠️ **the belonging rule has NO consumer** — `Q.DYNAMIC_BAND_POSITION` exists (`tools/omr/staged/positions.py`, behind `OMR_FAMILY_POSITIONS`, default OFF) and "`adjudicate_dynamic` still does not read it". The band constants are consumed only by the hairpin reader.

### A dynamic WORD is a run of adjacent letters (`f`+`f` = `ff`)
`[C47 + L57]`

- **Says:** compound dynamics are set as separate glyphs whose boxes nearly touch — **and the letterforms are italic, with flourishes that overhang their nominal position.**
- **Predicts (mechanically):** assemble adjacent `dynamic*` letters by x-adjacency into a word, then look it up. ⚠️⚠️ **And the literature explains why the naive version fails: a dynamic glyph's bounding box is not centred on its placement point and is not even entirely to the RIGHT of it, so joining letters by naive x-adjacency gets the spacing wrong, and a box-overlap test between adjacent letters reports overlap where the letters are separate.**
- **Numbers:** ✅ **the literature's font geometry predicts the repo's measurement exactly.** Bravura: `dynamicForte` bbox SW x = **−0.564** (ink **0.56 staff spaces LEFT of the origin**), `opticalCenter` anchor at x = 1.256, glyph **2.020 × 2.384** sp; `dynamicPiano` SW x = **−0.356**; and **`dynamicFF` is a single ligature glyph 2.980 wide — wider than two `f`s are apart, which is why two adjacent `f` boxes can overlap and still be two real letters.** Measured here: the first same-cell dynamic pair found is two `dynamicF` at **IoU 0.317, 21 px apart, both real: the two `f`s of a printed `ff`**.
- **Literature:** Bravura `glyphBBoxes` and `glyphsWithAnchors`. "A property of the letterforms; consistent in direction across music fonts."
- **Measured here:** ⚠️ **a flat IoU rule inside a cell would delete real ink.** Over 255 same-cell dynamic pairs the centre offset spreads **72 / 87 / 93 / 3** across `<0.25w` / `0.25-0.5w` / `0.5-0.75w` / `>=0.75w` — "**the populations do not separate**, widest empty interval 0.097", where noteheads DO separate (405 of 458 under 0.25w). ⚠️ On one committed transcription **15 of 20 dropped runs are a prefix of NOTHING and the shape is `ppmsf` / `ppzmf`** — "five letters run together, which no dynamic is", an **ASSEMBLY** failure. Re-assembling on the MEDIAN letter width is **not the lever** (kept runs 159 → 162, dropped still 20). Exporting the partial run was measured over the 20-row gate and **REFUSED**: `complete` **+15 edits**, `other` **+30**, **NOT ONE ROW BETTER**. `benchmarks/omr-dynamics-staged-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE — **and the assembly is where it breaks.**
- **Rigid or publisher-dependent:** RIGID for the engraving; the *assembly* failure is document-dependent.
- **Would be falsified by:** a same-cell letter-pair population that separates on geometry (it does not); or a font whose dynamic glyphs are box-aligned to their origin.
- **Known exceptions:** ⚠️ **the `ffff` was one printed `ff` detected twice across two staves**, resolved by the **ownership contest, not by geometry**: `ffff` **11 → 2**, `sf` **9 → 34**. ⚠️ And `ff` **47 → 39** in that repair is "**an unadjudicated COST, not a win**" — eight words where the record supports both readings and **only the print can say**.
- **Code:** `tools/omr/export.py` `measure_dynamics` (`_DYNAMIC_WORDS`, 17 words); `OMR_PARTIAL_DYNAMICS` default `off`.

### A hairpin runs quiet → loud (or loud → quiet) and travels with a dynamic letter
`[C48]`

- **Says:** a crescendo begins at a softer dynamic than it ends; the letters near it corroborate its direction.
- **Predicts (mechanically):** the letter either side of a wedge is **additive evidence** about its direction.
- **Numbers:** on the one committed reference encoding (Brahms 1, **683 hairpins**): the claim is **exact at ±1 measure (34/34)** and **wrong 31.8% at ±4**; reach **5.0% → 19.3%** across the same widening. "Keep it at ±1, ABSTAIN beyond, and it is **additive evidence over ~5% of hairpins, never a veto**."
- **Literature:** not covered.
- **Measured here:** ⚠️ an earlier pass quoted "wrong three times in ten" off ONE asymmetric window — "**a point on the curve, not a property of the rule**". `benchmarks/omr-dynamics-coupling-2026-09/probe_letter_wedge_coupling.py`; `docs/scope-dynamics-reading-2026-09-09.md`.
- **Status:** MEASURED HERE — **strictly LOCAL, and it is a rate, not a rule.**
- **Rigid or publisher-dependent:** RIGID musically; the *reach* is document-dependent.
- **Would be falsified by:** the ±1 figure falling on a second encoding.
- **Known exceptions:** **`cresc.` into a *subito* `p` is standard** — which is why the window may not be loosened.
- **Code:** no consumer found.

### An ACCENT is note-anchored; a HAIRPIN is span-anchored
`[C49]`

- **Says:** the same `<` mark is an **accent** when it is notehead-scale and stacked with one head, and a **hairpin** when it covers two or more note onsets in the dynamics band.
- **Predicts (mechanically):** *note-anchor vs span-anchor* separates the family; ⚠️ **width alone does not — one-beat hairpins exist.**
- **Numbers:** **no figure for the discriminator.** The nearest supporting number is indirect: on the scan corpus the truth carries **20 hairpins across the five verified rows and the detector fires on none**, so the confusion has never been priced.
- **Literature:** not covered as a confusable pair. ⚠️ The literature supplies two sizes that bear on it: `articStaccatoAbove` is **0.336 × 0.336 staff spaces** — "the smallest notation glyph a reader will meet" — and `hairpinThickness` is **0.16**, so the two families differ enormously in **extent** while sharing a stroke weight.
- **Measured here:** not measured here. Stated in `docs/position-grammar-confusables-2026-09-04.md` §2 WEDGE (Sean's own example): "Width alone fails — one-beat hairpins exist; *note-anchor vs span-anchor* does not. (Marcato is the vertical wedge; same family.)"
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID (by assertion).
- **Would be falsified by:** measuring width and anchor-count on hand-adjudicated accents and hairpins.
- **Known exceptions:** none recorded.
- **Code:** **no consumer found.** `gather_glyph_families` routes by CLASS (`dynamicCrescendoHairpin` carries category `dynamic`), which **sidesteps rather than solves** it.

### A beam is always connected to something; a HAIRPIN is connected to NOTHING — and it is thinner than a stem
`[C78 + L56]`

- **Says:** Sean's own test. A beam joins stems, a slur meets noteheads, a barline meets staff lines — **a hairpin touches no other ink on the page.** It is also the finest stroke in the family.
- **Predicts (mechanically):** **compare a band component's area to the area of the full-page connected component it belongs to.** For a hairpin the two are the same object; for anything attached, the page component is vastly larger. ⚠️ And the thinness prediction is a warning: **"a hairpin is a thin, long, diagonal line — the shape a bounding-box detector is structurally worst at"**, and at **0.16** sp it is close to a staff line's **0.13**, so **on a staff-line-erased image a hairpin can be erased with the lines if the erasure is at all aggressive.**
- **Numbers:** Bravura `hairpinThickness` **0.16** against `stemThickness` **0.12** and `staffLineThickness` **0.13**. Measured here, full-page component area ÷ candidate area over Brahms 1 p2's band components: **p25 1.0× (44 isolated); p50 1.0×; p75 3248.0× (25 attached); p90 9167.3×** — "**Nothing lies between 1× and 3248×.** That is what a constant read off a gap looks like, and **it is a binary rather than a threshold**." Combined with the open-extent test, **471 components with measurable outlines → 69 candidates at 0.10 staff spaces, against ~68 hairpins on the page.**
- **Literature:** SMuFL *engravingDefaults*; Bravura `engravingDefaults`. "Narrow band."
- **Measured here:** ⚠️ **Extent alone is REFUTED**: "Of 312 band components, **302** clear an open extent of 0.4 staff spaces, against ~68 hairpins." ⚠️ **Fill ratio is REFUTED**: "fill runs **p10 0.375, median 0.437, p90 0.737** — nothing survives below 0.35." End to end, truth `<wedge>` **198**, before **2**, after **106** — "**1% of the truth's wedges reached the file before; 54% do now.**" `benchmarks/omr-hairpin-cv-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE — and it comes out as a **binary, not a threshold.**
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a plate where a hairpin's arm touches a slur or a stem (the gate would then drop it); or hairpins engraved at beam weight.
- **Known exceptions:** ⚠️ **yield is PAGE-dependent, not just publisher-dependent** — over the scan gate, truth hairpins / candidates / YOLO reads **99 / 59 / 1**, and Mahler p3 gives **2 candidates against 17 truth hairpins** while Brahms p2 gives 44 against 68.
- **Code:** `tools/omr/hairpin_detection.py` (`MAX_COMPONENT_GROWTH = 2.0` at `:94`, the isolation gate; `MIN_OPEN_SPACES = 0.5` at `:84`; `MAX_OUTLINE_RMS_SPACES = 0.10` at `:86`). Behind `OMR_CV_HAIRPINS`.

### On a grand staff, dynamics go BETWEEN the two staves
`[L54]`

- **Says:** for piano and harp, a dynamic that governs **both hands** is placed in the gap between the staves.
- **Predicts (mechanically):** ⚠️ **in the inter-staff gap of a braced pair, a dynamic belongs to BOTH staves, not to the nearer one. A nearest-staff attribution rule is STRUCTURALLY WRONG there** and will assign a shared mark to one hand.
- **Numbers:** none.
- **Literature:** Dorico via Steinberg help: "For grand staff instruments, such as piano or harp, dynamics are usually placed between the two staves, but can be placed both above and below when each staff requires separate dynamics." Strong convention.
- **Measured here:** not measured here. ⚠️ **It is a named structural exception to a shipped rule.** `[C46 + L53]`'s re-attribution moves a letter to the staff whose band it stands in — measured **73% own band / 24% staff above, distance exactly 1, no exceptions** over 18 pages of 9 publishers — but that corpus is orchestral. **On a keyboard page this convention says the correct answer is BOTH**, which the rule has no way to express. The repo's brace handling is separately unreliable: *A BRACE means ONE PLAYER* `[C65]` records that all three incumbent sites decide brace-vs-bracket by `len(staves) == 2`.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** strong convention.
- **Would be falsified by:** keyboard editions placing shared dynamics only below the lower staff.
- **Known exceptions:** separate dynamics per hand, which are then placed above and below.
- **Code:** no consumer found.

---

## Articulations & ornaments

### An augmentation dot sits at the note's own space — half a space ABOVE for a note on a line — and NEVER below
`[C50 + L31]`

- **Says:** a note in a space takes its dot in the same space; a note **ON a line** takes it in the space **above**.
- **Predicts (mechanically):** ⚠️⚠️ **THE DOT-TO-NOTE WINDOW IS ASYMMETRIC, and it must be expressed in STAFF SPACES (the note's unit), not in the dot's own bounding box.** A dot is never level with an on-a-line notehead — it is **half a staff space above** it — so a dot reader keyed to the notehead's own y "will systematically miss the on-a-line case, **which is half of all notes**".
- **Numbers:** ✅ **the sources agree to the half-space.** Literature: vertical offset for an on-a-line note **+0.5 staff spaces**; Bravura `augmentationDot` **0.400 × 0.400**, bbox SW `[0.0, −0.2]` NE `[0.4, 0.2]` — symmetric about its own position, "under half a space square". Measured here over the **116 dots** of three works, the signed offsets are "**bimodal and nothing else: 52 at 0.00 spaces, 52 at +0.50, nothing between +0.57 and +3.75**". Shipped: `DOT_ABOVE_NOTE_MAX_SPACES = 0.75`, `DOT_BELOW_NOTE_MAX_SPACES = 0.25`.
- **Literature:** Wikipedia, *Dotted note*: "If dotted note is on a space, the dot is placed in that space. If the note is on a line, the dot is placed in the space above." Rigid for the single-voice case. ⚠️ Its stated exceptions: "The placement of dots need not follow this convention when space does not allow for it" — **dots on adjacent notes of a chord, and dots in multi-voice passages.** (⚠️ The literature files this entry under *Rests & bar filling*; it is filed here with the marks.)
- **Measured here:** the old gate was `max(dot.height, 12) * 1.2` — derived from the dot's own box, "which is small and mostly detector noise" — so the on-a-line case "landed within a few pixels of the threshold and went either way": **C Horn 1's dotted half read as a half in bars 1 and 5 and as a dotted half in bars 2, 3, 4 and 6.** ⚠️ **The asymmetry is forced by double stops**, which is precisely the literature's chord exception arriving as a measurement: Brahms's Viola plays two noteheads a space apart each with its own dot, "so the lower dot is equidistant from both noteheads, **a symmetric window ties**, and the upper note comes out double-dotted while the lower loses its dot".
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a dot printed under its note; dots engraved level with on-a-line noteheads.
- **Known exceptions:** ⚠️ **the pool must include RESTS** — "dots after rests are rarer but real". Widening the staged reader to match the legacy `_pair_dots_to_targets` moved **ZERO verdicts** on Litolff (20 `aug_dot` rows over three pages) and, on the 656-dot Breitkopf record, attaches **exactly ONE dot to a rest and that one is FALSE** (width **0.180** staff spaces against a median of 0.490, rank 1 of 656; the crop shows a clean UNDOTTED whole rest). **Of 691 `aug_dot` rows across two publishers, exactly one attaches to a rest, and it is wrong.**
- **Code:** `tools/omr/rhythm.py:1118` / `:1133`, applied at `:1163-1164` inside `_pair_dots_to_targets` (`:1136`); staged `tools/omr/staged/adjudicators/rhythm.py:63-64`, applied at `:335-336`. ⚠️ **The two copies are DUPLICATED LITERALS, not a shared import** — every other measured constant in this area is imported specifically to prevent drift, **so this pair is the odd one out.** ⚠️ The old box-derived gate cost **193 edits**.

### A staccato or accent is printed on the notehead side, opposite the stem, and CENTRED on the head in x
`[C51 + L58 + L61]`

- **Says:** the mark sits at the head end of the note, away from the stem, and its **x is the head's x**.
- **Predicts (mechanically):** ⚠️⚠️ **THE X OFFSET BETWEEN A MARK AND ITS NOTE IS ZERO, which makes x a strong, TIGHT join key, while y is the LOOSE one. A join built on x with a y side-test is better conditioned than a Euclidean nearest-neighbour.** The SIDE is determined by the stem direction, so "a nearest-notehead attachment that ignores the side will take marks from the wrong note **about half the time**"; and **a mark with no notehead on the correct side must be left UNATTACHED** rather than given to the nearest thing available.
- **Numbers:** ✅ **the literature's "x offset is zero" and the repo's swept window are the same claim.** Measured here, swept over eight works and scored against truth by index, the window is a **flat plateau from 0.50 to 2.50** — 197 placed, precision **0.980**, placement rate **0.904** — "with a cliff below it" at 0.30 (106 placed, placement 0.486). The shipped `_ARTIC_MAX_DX_NOTEHEAD_WIDTHS = 0.75` "sits in the middle of the plateau rather than on either edge". Bravura `articStaccatoAbove` **0.336 × 0.336** staff spaces.
- **Literature:** Dorico, *Positions of articulations*: "Articulations are placed on the notehead side by default"; "Articulations on the notehead side are always centered horizontally on the notehead". IU, *Articulations*: "Place on note head side, outside staff (except staccato)."
- **Measured here:** **21 of 218** marks across the corpus have no notehead on the correct side and are abstained on — "**and abstaining there is why precision is 0.980**". Mozart 40 detects **exactly 102 staccati and was charged exactly 102 `insarticulation` edits** before this shipped. `tools/omr/transcribe.py:2560-2573` (the sweep table is in the source comment); `benchmarks/omr-corpus-widening-2026-09/probe_articulations.py`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** strong modern convention; RIGID on the corpus measured.
- **Would be falsified by:** the plateau disappearing on a plate that sets marks off-centre; single-voice engraving placing articulations at the stem end.
- **Known exceptions:** ⚠️ **this shipped while making pooled OMR-NED WORSE by 97 edits** — −122 across eight works and **+219 on `boulanger-printemps-mvt1` alone**, whose bars do not pair, "so every correct symbol added to one raises a charge already being levied whole". ⚠️ **The side taken off the class NAME is not a ruler** — "`side` is DERIVED FROM THE CLASS so it fails together with the classification, and above/below is a BIT where the question is a distribution". ⚠️ Literature names three more: **multi-voice bars**, where Dorico places articulations at the **stem** end so the reader can tell which voice they belong to; **marcato**, which "is always placed above the staff, regardless of the stem direction"; and **stem-side staccato/staccatissimo, which centre on the STEM itself, not the head** — the one case that breaks the zero-x-offset join. Dorico also offsets notehead-side articulations by an extra **1/4 space** to avoid the end of a tie.
- **Code:** `tools/omr/transcribe.py:2573` `_ARTIC_MAX_DX_NOTEHEAD_WIDTHS = 0.75`, `:2594` `_attach_articulations_in_cell`, `:2577` `articulation_kind`. The independent ruler (`measured_side`, `steps_clear_of_staff`) exists at `tools/omr/staged/positions.py:473` and is **read by nothing**.

### A FERMATA hangs over whatever sounds beneath it — which is often a whole-bar rest, not a note
`[C52 + L62]`

- **Says:** unlike an articulation, a fermata does not attach to a notehead; it is drawn **above** the staff by default, inverted below only for a lower voice or a shared staff.
- **Predicts (mechanically):** ⚠️ **the articulation attach rule (nearest notehead on the class's side) STRUCTURALLY CANNOT REACH MORE THAN HALF of this population**, so fermatas need their own router and their own distribution. ⚠️ And the literature adds a contest the repo has not modelled: **a fermata is expected in the band ABOVE its staff, which on a conductor's page is the same band the staff above's DYNAMICS occupy — so fermata and dynamic detections in one gap are competing for the same ink and need arbitration, not independent attribution.**
- **Numbers:** Bravura `fermataAbove` **2.408 × 1.328** staff spaces — "wide and low, an easily separated shape", bbox SW `[0.012, −0.012]`, i.e. entirely above the baseline.
- **Literature:** ⚠️ `UNSOURCED — believed true, not verified` **for the "above by default" claim; no source consulted states it.** "**The GEOMETRY is sourced**" (Bravura `glyphBBoxes`; SMuFL's above/below registration rule), and SMuFL's provision of paired `fermataAbove` / `fermataBelow` glyphs implies the two-sided convention.
- **Measured here:** ✅ **the literature's "a fermata carrier can be a REST as readily as a note" is measured here and it is the majority case: 26 of 51 fermata carriers are RESTS** on Litolff pp.1-3 — "and **that is why the router is by CLASS**": `fermataAbove` carries the detector's `ornament` CATEGORY, shared with all ten `artic*` classes, so a category-keyed router would apply the articulation rule to them. Reach: **63 glyphs on Litolff p1-3, 0 on Brahms**; 51 decided → **37 `<fermata>`**, byte-identical outside them. ⚠️ The `nearest_in_bar` fallback **fired ZERO times**. ⚠️ The 13 "absorbed" marks are **DUPLICATE DETECTIONS, not chords**. `benchmarks/omr-staged-fermata-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a corpus where fermata carriers are overwhelmingly noteheads; orchestral engraving placing fermatas below by default.
- **Known exceptions:** the two populations must not be pooled — "pooling them would average a mark that attaches to a notehead with one that does not". Literature: lower voice of a shared staff; below-staff placement when the music above is congested.
- **Code:** `tools/omr/staged/gather.py` `gather_glyph_families` (routed by CLASS); `adjudicate_fermata_owner`. `Q.FERMATA_POSITION` is kept **APART** from the articulation's, deliberately, and is read by nothing.

### A TUPLET digit stands OUTSIDE the staff over its beam; a TIME-SIGNATURE digit stands INSIDE it; a FINGERING sits beside its notehead
`[C53]`

- **Says:** one printed digit has at least four roles, and **where it stands** is the only thing that separates them.
- **Predicts (mechanically):** both `tuplet3` and `fingering3` may be read, **because a positional gate — not the class name — keeps it safe.**
- **Numbers:** over twelve engraved works, **33 `fingering3` against 16 `tuplet3`, and all 33 sit in a cell that holds a real triplet**; the single detection that does not is a `tuplet3`.
- **Literature:** ✅ **the literature gives the SIZE half of the same discriminator and it is a strong one:** *Time-signature numerals fill the staff's height* `[L42]` — each meter digit **about 2 staff spaces tall**, in "a unique heavy font", so "**a digit-shaped mark one staff space tall is a fingering, a tuplet number or a measure number — not a meter**". And *A measure number sits at the START of a system, upper left* `[L68]` separates the fourth role by position.
- **Measured here:** admitting the class took Mahler **0.0455 → 0.0331** with its duration rate **0.864 → 1.000**, and `tchaikovsky-sym6-mvt2` **0.2321 → 0.1958**. ⚠️ **This corrected a claim that stood in `CLAUDE.md` for a day** — the Mahler group said to "carry no marker at all, at any confidence" carries a `fingering3` at **0.72**, the highest-confidence tuplet marker on that page. `benchmarks/omr-corpus-widening-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a real fingering centred over a beamed group of exactly three — "**no conductor's score in the corpus prints one to price that against**".
- **Known exceptions:** ⚠️ one **`numeral`** class in the coarse half of the 208-class space covers meters, tuplet digits, fingerings **and measure numbers** under one name — `numeral4` is NOT `timeSig4`, and a spurious `timeSig4` once shipped a 2/4 page as common time at **390 bar-check failures**. ⚠️ `adjudicate_tuplet` fired **zero times across 286 runs** of the plumbing matrix.
- **Code:** `tools/omr/rhythm.py` `resolve_rhythms_for_cell` (positional gate); `tools/omr/class_aliases.py` `COARSER_THAN_CANONICAL`; `tools/omr/staged/positions.py:410` (recorded, unread).

### A tuplet DIGIT is printed over the middle of its group; a tuplet BRACKET encloses it
`[C54]`

- **Says:** the two markers of the same fact sit differently, so **they must be read differently.**
- **Predicts (mechanically):** the digit's **CENTRE must fall inside the group's span**; the **GROUP must fall inside the BRACKET's span.**
- **Numbers:** "detected brackets are far wider than the notes they cover (**one measured at 1846px over a 478px group**) and testing a bracket's centre rejects every one of them".
- **Literature:** not covered.
- **Measured here:** which notes are in the group comes from the **BEAM box**, not the marker, **padded by a notehead width** "because it bounds beam INK, which starts at the first stem — unpadded, every stem-up group loses its first note" — the same stem-offset argument as *A beam stroke runs from the FIRST stem it joins to the LAST*. Tuplets overall: pooled **0.2595 → 0.2489**, Mahler **0.0826 → 0.0455**, duration rate **0.318 → 0.864**, Beethoven and Brahms byte-identical.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** an edition centring the bracket tightly on its group.
- **Known exceptions:** ⚠️ **a GROUP is a set of notes, not a beam stroke** — a sixteenth carries two beam strokes and the ratio was applied once per stroke, giving `(1/4) × (2/3) × (2/3) = 1/9`; `mozart-sym41-mvt1` prints 40 groups of triplet sixteenths and cost **464 edits** for it. Identical member sets are now collapsed.
- **Code:** `tools/omr/rhythm.py` `resolve_rhythms_for_cell` / `_beamed_groups`.

### A TREMOLO rides the stem, so it has no side at all
`[C55]`

- **Says:** unlike every other ornament, a tremolo is drawn **on the stem** rather than above or below the note.
- **Predicts (mechanically):** **for this class the class name carries no position of any kind, so a ruler is the only thing that can place it.**
- **Numbers:** **no figure, and none is possible today.** The reach is zero: the detector produces **ZERO tremolo detections over 34,115**, against an eleven-work truth whose only ornaments are **twelve `<tremolo>`**.
- **Literature:** not covered.
- **Measured here:** stated at `tools/omr/staged/capture.py:665-669`. ⚠️ `tremolo1`-`5` "ARE ornaments whose class names do not begin `ornament`". The label corpus carries **46** hand-labelled tremolo boxes **the checkpoint does not reproduce.**
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID (by assertion).
- **Would be falsified by:** a detector that fires on tremolos, then measuring their offsets.
- **Known exceptions:** LilyPond is deliberately not given tremolo at all — `c4:32` is a duration **SUBDIVISION**, "so a wrong mapping writes a different rhythm rather than a different mark".
- **Code:** `tools/omr/transcribe.py` `_ORNAMENT_KINDS` (asks the kind list rather than prefix-matching); position recorded and unread.

### A TRILL, TURN or MORDENT is printed clear ABOVE its note, centred on it
`[C87]`

- **Says:** unlike an articulation, whose side its class name states, an ornament's side is **fixed by convention — above**.
- **Predicts (mechanically):** it is "an articulation's geometry with the side fixed by convention rather than stated by the class name" — so the same nearest-notehead-in-x rule applies, with `above` **hard-coded rather than parsed**.
- **Numbers:** ⚠️ **the convention carries no sweep and no plateau, and the code says so**: `_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS = 1.0` is **"declared UNMEASURED"**, "against the articulations' swept-plateau `0.75`" — "unlike the articulation constant it copies, **no corpus exists to sweep it on**".
- **Literature:** not covered for these classes. ⚠️ The adjacent literature rule is *An articulation above SITS on its position; one below HANGS from it* `[L59]`, which says the glyph name carries its side and determines which edge of the box is the meaningful y.
- **Measured here:** **REACH only.** **4 of the 8 `ornamentTrill` detections find a notehead** within 1.0 notehead widths on the printed-above side (dx **4–13.5 px** against a median notehead width of ~30–40 px); placed confidences 0.70, 0.34, 0.74, 0.36, unplaced 0.31, 0.49, 0.56, 0.41. A/B: ledger rows **6086 → 6090**, `<ornaments>` in the XML **0 → 4**, **non-ornament rows identical (6086 / 6086)**. `benchmarks/omr-export-gaps-2026-09/FINDINGS-2026-09-08-ornaments-and-the-derived-check.md`.
- **Status:** ASSERTED (untested here) — **the side is a convention; only its REACH was measured.**
- **Rigid or publisher-dependent:** RIGID (by assertion).
- **Would be falsified by:** a plate printing trills below the staff for a stem-up voice.
- **Known exceptions:** ⚠️ **a TREMOLO is the exception in the same family** — it rides the stem, so `above=None` means "do not test the side" at all.
- **Code:** `tools/omr/transcribe.py:2677` `_ORNAMENT_KINDS`, `:2699` `_ORNAMENT_MAX_DX_NOTEHEAD_WIDTHS = 1.0`.

### An articulation above SITS on its position; one below HANGS from it
`[L59]`

- **Says:** the two orientations of an articulation glyph are registered differently.
- **Predicts (mechanically):** ⚠️ **the glyph name carries its side (`…Above` / `…Below`), and the side determines WHICH EDGE of the glyph's box is the meaningful y.** So a reader can recover the intended staff position from a detected box **only if it knows which variant it has** — "taking a box centre gives an answer that is **wrong by the glyph's own half-height** in one direction or the other".
- **Numbers:** SMuFL: "Articulations to be positioned above a note should sit on the baseline (y=0), while articulations to be positioned below should hang from the baseline." Bravura `fermataAbove` bbox SW `[0.012, −0.012]` — entirely above the baseline, confirming it.
- **Literature:** SMuFL, *Metrics and glyph registration*; Bravura `glyphBBoxes`. Rigid within SMuFL fonts.
- **Measured here:** not measured here. ⚠️ **But the repo has the matching warning from the other side and it is stronger:** `[C51]`'s known exception is that "`side` is **DERIVED FROM THE CLASS so it fails together with the classification**", and the independent ruler that would fix it (`measured_side`, `steps_clear_of_staff`, `tools/omr/staged/positions.py:473`) is **read by nothing**. So this entry's registration rule is available, its hazard is documented here, and **neither is consumed.**
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** rigid within SMuFL fonts.
- **Would be falsified by:** a font registering both variants identically.
- **Known exceptions:** none recorded.
- **Code:** no consumer found.

### A small articulation near the middle line is centred in the next free SPACE
`[L60]`

- **Says:** where a note sits near the staff's centre, a small articulation is moved into an unoccupied space rather than being drawn over a line.
- **Predicts (mechanically):** ⚠️⚠️ **an articulation's vertical offset from its notehead is NOT CONSTANT — for notes near the middle line it is QUANTISED to the next free space, so the mark-to-head distance is DISCRETE rather than smooth. A fixed-distance window will therefore succeed for outer notes and fail for middle ones, which is a SYSTEMATIC AND POSITION-DEPENDENT failure rather than noise.**
- **Numbers:** applies to "articulations that are less than a space in height", i.e. in practice staccato and tenuto; the offset is to "the next unoccupied space".
- **Literature:** Dorico, *Positions of articulations*: "If a note is placed on the middle staff line or on the space immediately on either side, articulations that are less than a space in height are centered in the next unoccupied space." Strong convention.
- **Measured here:** not measured here — ⚠️ **and it explains why the shipped rule is built the way it is.** `[C51 + L58 + L61]` joins on **x** with a **side** test and a **flat plateau from 0.50 to 2.50 notehead widths**; it does not test the y distance at all. This entry says that is the correct design: **y is quantised and position-dependent, x is not.** Whether the discrete y could be *used* (as a corroborator, or to separate a middle-line mark from a neighbour's) is unmeasured.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** strong convention.
- **Would be falsified by:** engraved staccato dots drawn over staff lines.
- **Known exceptions:** larger articulations go outside the staff entirely — "If an articulation cannot fit within a staff space, or if the note is placed high or low on the staff, the articulation is placed outside the staff."
- **Code:** no consumer found.

---

## Score layout & systems

### A barline runs the FULL HEIGHT of its system, and nothing else does
`[C56 + L74]`

- **Says:** an ordinary barline spans exactly its staff, and a systemic barline spans the system; a stem, a slur or a measure number does not. ⚠️ **The BRACKET half of `CLAUDE.md`'s version of this sentence is FALSE — see disagreement #1.**
- **Predicts (mechanically):** **a column of ink inked through the whole of an inter-staff gap VETOES a distance-based system break**; and on a braced two-staff system, a stroke spanning from the top of the upper staff to the bottom of the lower is a barline rather than a stem. ⚠️ **The literature gives the single-staff version as an EXTENT test that separates barline from stem where thickness cannot:** a barline is **4.0 staff spaces and anchored at the staff's edges**, a stem ~3.5 and anchored at a notehead.
- **Numbers:** literature: height **4.0 staff spaces** for a single-staff barline; `thinBarlineThickness` **0.16** against `stemThickness` **0.12** — "**thickness alone cannot separate a stem from a barline; height and position must**". Measured here: within one Brahms system the inter-staff gaps run **17–237 px** and within one Beethoven system **130–345 px** — "both wider than the gaps BETWEEN systems on a piano page — and x-overlap is 1.00 for every pair, so **no distance threshold can separate them**".
- **Literature:** Wikipedia, *Bar (music)*: "Regular bar lines consist of a thin vertical line extending from the top line to the bottom line of the staff, sometimes also extending between staves in the case of a grand staff or a family of instruments in an orchestral score." Rigid.
- **Measured here:** connectivity grouping took Brahms **12 → 1 system**, Beethoven **4 → 1**, and Beethoven's measure count **14/8 → 8/8 exact**. For the brace case: on WTC I Prelude 1 p.4 the left hand read all four barlines of every system and the right hand "read none of them and **31 of its own stems**", so five systems of three bars came out as ONE bar (now 4,4,4,4,4,4). ⚠️ **The gap test alone is NOT enough there** — "a fugue's long stem crosses the brace gap and scores **1.00** connectivity". `docs/position-grammar-confusables-2026-09-04.md` §2 VERTICAL STROKE.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a non-barline object spanning a whole system — **a full-system bracket is one, and 2 of 5 held editions print exactly that.**
- **Known exceptions:** the rescue is **ADDITIVE**: "letting the span test filter instead costs every system its opening rule, which often does not span the brace". Literature: systemic barlines spanning a whole family; **Mensurstrich, which spans only BETWEEN staves.**
- **Code:** `tools/omr/staff_detector.py` `_gap_is_bridged`; `tools/omr/measure_extractor.py` `_spans_system`.

### A barline is a STRAIGHT line, not a vertical one
`[C57]`

- **Says:** the engraver rules it straight; the SCAN then shears it.
- **Predicts (mechanically):** **a barline column must be FITTED to the staves that observed it and probed along the fit, not sampled at a mean x.**
- **Numbers:** one barline's x drifts **monotonically by up to 40 px** between the top staff and the bottom, **over three times the clustering tolerance** — so three real barlines that had passed the vote (9, 12 and 10 of 12 staves) scored **0.27–0.36** against a 0.40 gate and were thrown away.
- **Literature:** not covered — *"Nothing here is about SCANS."*
- **Measured here:** page 1: **17/17 barlines, 0 false, 16 measures of 16**; pages 2-6 unchanged. ⚠️ The fit uses **Theil-Sen and not least squares**, "because a note stem that joins the cluster votes too and two such among nine still dragged a least-squares fit off the line". `docs/ask-first-conventions.md` §2.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** the convention is RIGID; **the drift is a property of the SCAN.**
- **Would be falsified by:** a corpus where the mean-x column and the fitted line agree (engraved input, by construction).
- **Known exceptions:** none recorded.
- **Code:** `tools/omr/measure_extractor.py:321` `_barline_x_at`.

### Interior barlines STOP at instrument-family boundaries
`[C58 + L63]`

- **Says:** in a full score the barline runs unbroken through each instrumental family and **BREAKS between families**.
- **Predicts (mechanically):** ⚠️ **the family grouping is readable from where the interior barlines STOP — no bracket detection required.** A system's staves partition into runs rather than being a flat list; a gap that every barline crosses is INSIDE a family. And a "choir-barred" system (interior barlines stopping at choir edges) **must never be flipped into open-score mode.**
- **Numbers:** measured against hand-read print truth: Bach / Peters printed **3|3|3** — bracket reader **5 of 22** exact, incumbent pixel rule **16/22**, the columns rule **22/22** (21 exactly `[2,5,8,9]`); Brahms / Breitkopf printed **9|5** — bracket reader **1 of 15**, pixel rule **0/15**, columns rule **15/15** exactly `[8]`. Within-page instability **0.384 → 0.055** over 144 pages and five publishers.
- **Literature:** MOLA, *Formatting — Full Score*: "The barlines should be continuous within each family of instruments." IU, *Barlines*: "Break between choirs per large group bracketing." ⚠️ **"Some editions bar through the entire system, and early-music editions use Mensurstrich (barlines only BETWEEN staves), so the signal can be absent."**
- **Measured here:** ⚠️⚠️ **the pixel rule could never have worked**: the numerator is ~3 spanning objects and the denominator is how many bars the system prints, so the ratio is ≈ `3/(n_bars+3)` and crosses 0.5 near three bars a system — over **2841 gaps the largest value below the cut is 0.4962 and the smallest above is 0.5000**. `benchmarks/omr-bracket-stability-2026-09/FINDINGS.md`; `benchmarks/omr-bracket-reading-2026-09/FINDINGS.md`; `NOTES.md:199`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** ⚠️ **PUBLISHER-DEPENDENT, and both sources say so** — "'what crosses this gap' is a property of the edition's convention, not of whether a system ends. **B9 and B5 happen to run barlines across group gaps, which is why every signal looked perfect on them.**"
- **Would be falsified by:** an edition whose interior barlines cross family boundaries — **B9 and B5 do.**
- **Known exceptions:** ⚠️ `BRACKET_COLUMN_MIN_EVIDENCE = 3` is **load-bearing** — a LilyPond render bars per staff and "a 25-staff Bruckner system carries two crossing columns total", from which the rule manufactured **11 groups** without the floor. Literature adds: **Mensurstrich editions**; **choir-barred vocal scores**, where the breaks fall at choir edges rather than family edges; and **divisi staves, where MOLA requires the barline to be CONTINUOUS between the split staves.**
- **Code:** `tools/omr/system_grouping.py`; `tools/omr/measure_extractor.py` (cue C); `OMR_BRACKET_COLUMNS` (default ON).

### A bracket BLOCK is an engraving unit, not an instrument family
`[C59]`

- **Says:** publishers bracket by page layout, not by orchestral family.
- **Predicts (mechanically):** **a consumer must not read a bracket block as "these staves are one family".**
- **Numbers:** Brahms 1 p.1 reads blocks **`[2,2,2,2,2,7,1,3]`** — **five PAIRS** that are `2 Flöten`, `2 Oboen` and so on.
- **Literature:** ⚠️ **the literature asserts the opposite as its headline** — *A bracket encloses each instrumental family, with sub-brackets inside it* `[L64]`, citing IU: "Orchestra: bracket each choir (woodwinds, brass, percussion, strings); Secondary brackets on like instruments". **Read as a two-level scheme the two agree**: the five Brahms PAIRS are IU's *secondary* brackets on like instruments. What the repo measured is that **a reader cannot tell which level it is looking at.**
- **Measured here:** "Breitkopf brackets **winds + brass + timpani as ONE block** against the strings (`out/crops/brahms-p3-gap2.png`: the bracket runs straight through the clarinet/bassoon boundary; `brahms-p3-gap8.png`: it terminates between timpani and violin I while the systemic barline runs on)." `benchmarks/omr-bracket-reading-2026-09/FINDINGS.md` headline 1; `tools/omr/staged/ASSUMPTIONS.md` A-GROUP-2.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT.**
- **Would be falsified by:** an edition whose brackets track families exactly (Peters's 3|3|3 nearly does).
- **Known exceptions:** none recorded.
- **Code:** consumed as a **refusal** — `group_symbol` abstains without identity rather than reading a 2-staff block as a brace.

### Some publishers print NO section bracket at all
`[C60]`

- **Says:** whether family brackets are printed is an **edition property**.
- **Predicts (mechanically):** **a reader that requires a bracket to find family boundaries fails outright on those editions** — which is why the boundary is inferred from where the barlines stop instead.
- **Numbers:** read off the print at **600 dpi, by hand**, over the five editions in the scan corpus: **Peters (Bach) yes, 3; Breitkopf (Brahms 1) yes, 2; unidentified Mahler 5 scan yes; Litolff (Beethoven 5) NO — one bracket, whole orchestra; Simrock (Dvořák 9) NO — one bracket, whole orchestra, + braces on pairs.** **Two of the five.**
- **Literature:** ✅ **the literature agrees, and says the variability IS the finding**: `[L64]`'s rigidity row reads "**Variable by publisher, and some editions print no family bracket at all**", and its *Would be falsified by* is "Nothing — the variability is the finding."
- **Measured here:** `benchmarks/omr-bracket-reading-2026-09/FINDINGS.md` headline 1.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT.**
- **Would be falsified by:** re-reading those plates and finding section brackets.
- **Known exceptions:** none recorded.
- **Code:** the bracket reader `tools/omr/bracket_reader.py` exists with **no consumer, no flag** — "**Recommendation: do not wire it in.**"

### No left-edge object ever bridges a system break
`[C61]`

- **Says:** a bracket, brace or systemic barline belongs to **exactly one system**.
- **Predicts (mechanically):** **the connectivity VETO is safe** — an object at the left edge can merge two staves but **never two systems**.
- **Numbers:** over **57 pages, 0 of 147 read blocks span two systems**.
- **Literature:** not covered directly; it is the structural premise beneath `[L64]`'s bracket levels.
- **Measured here:** ⚠️ **Sean's stronger hypothesis — that these objects define a system's EXTENT — is only half right**: "on a section-bracketed edition the maximal left-edge object is a section bracket, so the reading **over-splits on 27 of 57 pages** (Bach **0 of 11** exact, against Litolff's one-bracket pages at **7 of 12**)". `benchmarks/omr-bracket-reading-2026-09/FINDINGS.md` headline 4.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a left-edge object crossing a system gap.
- **Known exceptions:** **the property licences a VETO only, not a positive system reader.**
- **Code:** `tools/omr/staff_detector.py` `_gap_is_bridged` (the existing veto relies on exactly this property).

### A printed score may OMIT a tacet part; it may never REORDER one
`[C62 + L66]`

- **Says:** a printed score omits staves whose instruments are silent for a whole system — and the staves that remain map to the full lineup **in strictly increasing order**.
- **Predicts (mechanically):** ⚠️⚠️ **the number of staves in a system is NOT the number of instruments in the work, and it varies system to system on one page.** So joining staves to parts by **ORDINAL position is unsafe on any system shorter than the full lineup**; the suppression can be **INTERIOR**, which shifts every staff below it. What is safe: a short system's unnamed staves are constrained by their **named neighbours above and below** — enumerate every order-preserving assignment and take a slot only where **every surviving assignment agrees.**
- **Numbers:** the name rule reproduces its probe "in every cell — **50 placed / 50 correct / 0 wrong / 25 abstained**", against the ordinal incumbent's **75 placed, 63 correct, 12 WRONG, 0 abstained** on the same 75 staves; the arms differ on **28 of 75**. **75 fragments → 37 parts, 12 grafts → 0.**
- **Literature:** ⚠️ `UNSOURCED — believed true, not verified` **as a stated rule; no source consulted states it directly.** It is implied by MOLA's requirement that score pages "indicate the prevailing instrumentation" and IU's "Use staff styles to indicate prevailing instrumentation on every score page", **both of which presuppose that the instrumentation shown varies by page.** "Universal in engraved orchestral scores."
- **Measured here:** ⚠️ **"'It fixes 12' would be FALSE"**: 3 grafts become the right slot, **9 become abstentions**, **16 staves the ordinal placed correctly are withdrawn**, and **0 new grafts**. Both offending systems are **interior suppression** (p3/s1 suppresses Oboi/Trombe/Timpani; p4/s0 suppresses Timpani). Placing unnamed staves by position instead scores *more* correct (66 vs 50) and **grafts 9 staves** doing it — "**the guess wearing a number, priced**". `benchmarks/omr-slot-index-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** a plate that reorders staves between systems; or an orchestral edition printing every staff on every system.
- **Known exceptions:** ⚠️ the ordinal join is **right** for a score that suppresses only its LAST staves. ⚠️ **The graft is silent and fragments are loud** — "a Timpani part holding the Viola's bars and key signature reads as wrong notes, and **mis-ranking the work is the one failure a cleanup count exists to prevent**". Literature: some editions print all staves throughout; study scores vary.
- **Code:** `adjudicate_slot_index` (`_forced_pairing`); `tools/omr/export.py` `_stitch_slots` / `_slots_are_ordinals`.

### The strings are the LAST block of a system, and a short string section is short at its FOOT
`[C63]`

- **Says:** orchestral score order puts the strings at the bottom; where the section is short, the missing staff is the lowest.
- **Predicts (mechanically):** a bottom-contiguous unnamed block that exactly fills the reference's trailing same-family run has **ONE order-preserving map and takes it (FORCED)**; a block one slot short sits on that run five ways (**NARROWED**, to be resolved by INFER).
- **Numbers:** one gather decided four ways, CONTROL **75 of 75** committed slot verdicts reproduced with the branch disabled: **25 abstained → 5 DECIDED + 20 NARROWED → 15 collapsed, 5 left narrowed**; **25 of 25 placements correct against the hand-read PRINT, ZERO grafts.** In the FILE, running alone: `staff_not_identified` **783 → 141 (−642)**, `events_written` **1472 → 2114 (+642)**, every other bucket identical, `balanced: True` in every arm; pitched notes **965 → 1527**; parts stay 12 and measures 1332. Per part: Violin I +189, Violin II +176, Viola +74, Contrabass +27.
- **Literature:** ✅ **`[L65]` states the ordering independently** — "**Woodwind · Brass · Timpani/Percussion/Harp/Keyboard · Vocal · Strings**", and "Within these broad categories, instruments should be vertically ordered, for the most part, **by sounding pitch high to low**", which is the second half of Sean's clef reinforcement.
- **Measured here:** Sean, 2026-09-17: *"If we had 4 or 5 staves that showed up last in the system without a name in the margin they are almost surely strings. If the first 2 clefs are treble the 3rd is alto and the 4th is bass clef it is further reinforcement."* The 5 left narrowed are the condensed `Violoncello e Basso` — "**abstained on, not picked**". Commit `a3e064ce`; `benchmarks/omr-unnamed-staves-2026-09/`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID for the ordering; the **LABELLING** of it is publisher-dependent.
- **Would be falsified by:** a short string section short at its HEAD.
- **Known exceptions:** ⚠️⚠️ **the second publisher has NO POPULATION** — Breitkopf Brahms 1 p0-3 reaches **ZERO**, because **97 of 97 slot verdicts are already DECIDED**: "that plate labels nearly every staff on every system. **n = 1 document for correctness.**" ⚠️ The CLEF is a term "that can pull into abstention and **never as a gate**".
- **Code:** `adjudicate_slot_index` (`family_block`, `family_block_not_forced`); INFER rule `collapse_slot_index_to_family_block`.

### A column through a system is one INSTANT of music
`[C64]`

- **Says:** on a conductor's page, notes at the same x across different staves sound together. "**That is not a convention, it is the defining property of a conductor's score.**"
- **Predicts (mechanically):** a 21-staff system is **twenty-one independent readings of one stretch of time** — the only large source of **REDUNDANT** evidence on the page.
- **Numbers:** on the committed Brahms 1 / Breitkopf transcription (51 bars, 6 systems, **3,006 events**), against a **circular-shift null** that keeps every within-staff interval and destroys only the PHASE: columns needed for the same events **1,483 real vs 2,409 null (1.62×)**; corroboration rate **0.498 vs 0.292 (1.71×)**; events standing alone **744 vs 1,706 (2.29×)**. `ONSET_COLUMN_MIN_WITNESSES = 2`.
- **Literature:** not covered — it is a property of the score format rather than an engraving convention, and no consulted source states it.
- **Measured here:** ⚠️ **the rate rises with density while the information falls** — sparse bars 0.437 vs 0.212 (**2.06×**), dense bars 0.530 vs 0.348 (1.52×) — "a consumer reading corroboration without [density] **cannot tell evidence from crowding**". ⚠️⚠️ **DO NOT READ THE RESIDUAL AS EVIDENCE**: median residual **0.0734 real vs 0.0704 null (1.00×)** — "**a column is BUILT to lie within the tolerance**". Independently reproduced from a different population (ink components rather than note events, different document): unclassified ink aligns at **0.63× the columns and 0.43× the rows standing alone**. `benchmarks/omr-onset-columns-2026-09/FINDINGS.md`; `benchmarks/omr-ink-gather-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE — the column count holds; **the residual is refuted as evidence.**
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** the real/null ratio approaching 1.0.
- **Known exceptions:** ⚠️ **a column is an instant on the SYSTEM, so a staff playing a half note while its neighbours play eighths SKIPS columns** — the INFER stage's first rule required strict adjacency and inferred **1** of 357; generalised to "the witness ENDS WHERE THIS NOTE ENDS" it reached **7**.
- **Code:** `Q.ONSET_COLUMN` + `adjudicate_onset_column` (`Kind.SYSTEM`, `Mode.ADDITIVE`); consumed by `tools/omr/staged/inferences.py` `collapse_duration_by_column` and `collapse_duration_to_barline` behind `OMR_INFER` (default OFF). `ONSET_COLUMN_MIN_WITNESSES = 2` at `tools/omr/staged/adjudicators/rhythm.py:2459`.

### A BRACE means ONE PLAYER
`[C65]`

- **Says:** a brace states **who plays**, not how many staves.
- **Predicts (mechanically):** the brace/bracket choice should key on the group's **INSTRUMENT FAMILY** (keyboard or harp → brace), **never on `len(staves) == 2`.**
- **Numbers:** **no measurement — the assumption is declared with its falsifier and is a pure no-op.** The counter-evidence to the incumbent IS measured: "All three incumbent sites decide it by **staff count** — `export.py:681` and `:3523` on `len(staves) == 2`, `:3446` on `len(slots) == 2`. A bracket block of two staves is *not* a grand staff: Brahms 1 p.1 reads blocks **`[2,2,2,2,2,7,1,3]`**, five **pairs** that are `2 Flöten`, `2 Oboen` and so on, and **consuming 'block of 2' as a brace DECLARES FIVE WIND PAIRS TO BE PIANOS.**"
- **Literature:** ✅ **`[L64]` states the same distinction** — "**A brace (rather than a bracket) marks a grand staff**" — and `[L54]` builds on it (grand-staff dynamics go between the staves). Neither gives a geometric test; `[C84 + L64]` supplies one: **a brace is curved and can never form a full column.**
- **Measured here:** `tools/omr/staged/ASSUMPTIONS.md` A-GROUP-2.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID (by assertion).
- **Would be falsified by:** its own stated test — "Count pages whose 2-staff group is a real keyboard against those whose 2-staff group is a wind pair. Also: find a braced instrument outside `BRACE_FAMILIES` (organ with pedal is 3 staves; celesta; accordion)."
- **Known exceptions:** organ-with-pedal is three staves.
- **Code:** `Q.GROUP_SYMBOL` — "With identity stubbed this **always abstains**, so today it is a pure no-op and **the incumbent rule stands everywhere.**"

### An engraver spaces notes roughly in PROPORTION TO DURATION
`[C66]`

- **Says:** a wide horizontal gap after a notehead is evidence the note is long.
- **Predicts (mechanically):** **a duration signal INDEPENDENT of every other one** — it needs neither the stem, the beam, nor the notehead class.
- **Numbers:** **none.** "⚠️ **Measured nowhere** — `grep` for proportional spacing in `tools/omr/` returns only unrelated hits. **This is the one entry here that is a genuine *measurement* of the raster nobody takes.**"
- **Literature:** not covered — the literature file's own filter dropped "spacing aesthetics … unless they bound a measurement", so proportional spacing is absent from both harvests.
- **Measured here:** not measured here. `docs/exploration-what-is-on-the-page-2026-09-09.md` §B.7. The repo file re-ran the grep across `tools/` and `benchmarks/` and found no measurement.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** RIGID musically; **strongly perturbed by justification.**
- **Would be falsified by:** measuring inter-onset x-gaps against known durations **on an engraved fixture, where the truth is exact.**
- **Known exceptions:** two, unmeasured: "**scanned spacing is noisy and justification stretches the last bar of a line**".
- **Code:** no consumer found.

### Whether one printed staff label means ONE part or TWO is a property of the ENCODING, not the engraving
`[C67 + L67]`

- **Says:** a condensed staff (`Flauti`, `Violoncello e Basso`) carries several players; **how many `<part>` elements a reference file splits it into is an editorial decision about the FILE.**
- **Predicts (mechanically):** ⚠️⚠️ **NOTHING ON THE PAGE CAN SUPPLY THE COUNT. Do not build a page-side rule for it.** In a SCORE one printed staff may carry several players, so **the staff count and the part count are different quantities and neither implies the other**; any reader joining a score's staves to a reference encoding must allow for this many-to-one.
- **Numbers:** "Staves carrying the SAME printed label are encoded as 1 part in some editions and >1 in others (**Litolff/Simrock/Breitkopf `Viola` = 1, Peters `Violen` = 2**) … **a label-derived rule is 74/74 on Beethoven/Brahms and +2,181 edits on Dvořák**, and **eleven page-side signals separate the two populations no better than chance (best ensemble 0.526 vs the `always 1` baseline's 0.538)**." What IS a convention and is measured: over every condensed staff-measure in the truths, **silent 51.5% + unison 18.3% = 69.8% is exact duplication** (divisi 27.6% is approximated by duplication, so these are a floor). Ceiling with oracle counts: scan pool **−4,195 edits alone, −4,557 with `OMR_SLOT_STITCH`**; `entire staff` **8,453 → 2,060**.
- **Literature:** MOLA, *Formatting*: "Do not create wind parts with multiple instruments on a single staff; for instance, flutes 1 and 2 should be separate parts"; "String parts should be created with one part per section"; "Complicated string divisions should be written on separate staves." ⚠️ **"MOLA's rules are for PARTS. Scores condense freely and always have"** — and its *Would be falsified by* is "**Nothing — the score/part asymmetry is the point.**"
- **Measured here:** `benchmarks/omr-condensed-parts-2026-09/FINDINGS.md`; `docs/ask-first-conventions.md` §3.
- **Status:** **ENCODING (not engraving)**
- **Rigid or publisher-dependent:** **neither — it is a property of the encoder.**
- **Would be falsified by:** a page-side signal that separates the populations (**eleven were tried**).
- **Known exceptions:** the duplication convention (**69.8%**) is real and page-side; **only the COUNT is encoding-side.**
- **Code:** `OMR_CONDENSED_PARTS`, default `0` (off) — "Measured, dormant, and blocked on a count source." Flag-off is byte-identical (22/22 fixtures).

### A PAGE truth is not an ENCODING truth
`[C68]`

- **Says:** MusicXML and the engraver count the same music differently — a `<slur>` is written at each END while the engraver draws **ONE** arc; a clef is printed at every system and declared once.
- **Predicts (mechanically):** ⚠️⚠️ **any recall or precision figure taken by counting elements in a reference file against glyphs on a page is measuring the DIFFERENCE BETWEEN TWO NOTATIONS as well as the reader.**
- **Numbers:** on the Brahms fixture, against the file it was rendered from: dynamics **19 glyphs vs 19 `<dynamics>` (agree)**; G clefs **28 glyphs vs 14 `<sign>G</sign>`**; slurs **82 arcs vs 164 `<slur>` tags**. A second instance: Verovio draws **one accidental per `<alter>`, not per `<accidental>`** — Brahms 1 has **54 `<accidental>` and 149 `<alter>`** and it drew 149; Beethoven 5 has **ZERO `<accidental>` and 13 `<alter>`** and it drew 13, so the `accidental` family scored recall **0.257** and is **excluded from the pooled reading F1 (0.898 → 0.919)**. A third: the Litolff plate condenses **18 encoded parts onto 12 printed staves**, so the four-page arc denominator (truth **111 slurs and 300 tie links** against our 32 and 80) supports "an understatement of the right sign" and **no recall rate.**
- **Literature:** not covered — but the literature independently supplies the two facts it is built on: the clef and key signature are reprinted every system (`[L38]`, `[C25]`) while the meter is not (`[L41]`, `[C28]`), and a slur crossing a barline is ONE mark drawn in two pieces (`[L50]`, `[C38]`).
- **Measured here:** `benchmarks/omr-reading-vs-reproduction-2026-09/FINDINGS.md`; `benchmarks/omr-arc-recovery-2026-09/FINDINGS.md`.
- **Status:** **ENCODING (not engraving)** — measured as a discrepancy.
- **Rigid or publisher-dependent:** n/a.
- **Would be falsified by:** n/a — **it is an observation about two notations.**
- **Known exceptions:** ⚠️ **what caught the accidental artefact was a CONTRADICTION with an existing number** — `wrong pitch` is zero on those works, "which cannot be true of a reader missing three quarters of the accidentals".
- **Code:** `tools/omr/page_truth.py` `render_fidelity` (measures the disagreement per work and declares a family unreliable); `score_reading` marks it `(RENDER)` and keeps it out of the pool.

### SCORE ORDER is a convention strong enough to resolve a label by
`[C82 + L65]`

- **Says:** an orchestral score lists its instruments in a fixed family order — **woodwind, brass, percussion, voices, strings** — and within each family from high to low.
- **Predicts (mechanically):** **a monotone alignment of a page's staves against a canonical layout is a positional identity channel, INDEPENDENT of the margin text.** And it is a **prior on each staff's clef, written range and whether it carries a key signature, before any ink is read.** Because the order is monotone, the join can be a monotone alignment rather than a free assignment.
- **Numbers:** literature's five groups, in order: **Woodwind · Brass · Timpani/Percussion/Harp/Keyboard · Vocal · Strings**. Measured here against the Gradus MusicXML library (**507 works**): lexicon coverage **93% → 99%** of **2,345** real part names, and symphonic works in score order **74 → 95 of 105**.
- **Literature:** MOLA, *The Performance Material*: "the generally accepted layout is as follows", adding "Any instrument that does not easily fit in the layout above will usually be placed in the third group" and "Within these broad categories, instruments should be vertically ordered, for the most part, **by sounding pitch high to low**". ⚠️ **"Variable — MOLA itself says 'While it is possible to find many exceptions'"**, and it describes modern practice; **19th-century placement of timpani, harp and solo instruments differs by publisher.**
- **Measured here:** ⚠️ **every one of the 30 order violations fixed there was a LEXICON misreading, not a layout** — "the 10 that remain are real variation and were left alone", and **Baroque is confirmed as a genuinely different layout**. `benchmarks/omr-score-order-2026-08/findings.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** **RIGID for symphonic repertoire, with one named exception class (Baroque) and a measured residue of real variation.**
- **Would be falsified by:** the 95-of-105 figure falling when the lexicon improves further (**it rose, which is the test passing**).
- **Known exceptions:** ⚠️⚠️ **THE PRIOR CAN OVERTURN A CORRECT LEXICON READING** — the canonical layout puts the timpani after the trombones while Litolff's Beethoven 5 prints it BETWEEN the trumpets and the trombones, so a correctly-read `Tp.` was aligned onto a second-trumpet slot. **The repair was the one-abbreviation-per-system guard, not a change to the order.** ⚠️ The residual 7 errors on an 88-page run are **MIS-SLOTTING, not mis-naming**: "an off-by-three in the monotone DP over a reduced system: 12 staves against a 17-slot reference needs five deletions and it deleted 12/13/14 instead of 9/10/11". Literature adds: **solo instruments sit above the strings**; percussion may be ordered by player rather than pitch.
- **Code:** `tools/omr/score_layouts.py`, `tools/omr/slots.py` (`align`, `assign_slots`); `tools/omr/instruments.py` supplies the names.

### The only ink crossing a family gap is the SYSTEMIC BARLINE, and it is about 0.16 staff spaces wide
`[C83 + L75]`

- **Says:** where interior barlines stop, one thin rule still runs the full height at the system's left edge — and it sits at exactly the x where the staff lines begin.
- **Predicts (mechanically):** **a family gap is bridged by ONE NARROW COLUMN at `x_start` and nothing else; an inter-system gap is bridged by NOTHING at all.** ⚠️ And the weights give a further separation: **a thick barline is exactly as heavy as a beam (both 0.5) and three times a thin barline — so the thin/thick distinction is robust to a coarse measurement while the thick-barline/beam distinction is not; the latter needs ORIENTATION.**
- **Numbers:** ✅ **the sources agree and the repo reproduced the font numbers on a render.** Bravura: `staffLine` **0.13**, `thinBarlineThickness` **0.16**, `thickBarlineThickness` **0.5**, `bracketThickness` **0.5**, `barlineSeparation` **0.4**, `thinThickBarlineSeparation` **0.4**; application defaults span **0.12–0.24** for a thin barline. In pixels, a 4 mm pocket score at 300 dpi is **1.9 / 5.9**, at 600 dpi 3.8 / 11.8 — "**a bracket is ~3× the barline's ink everywhere**". Measured here on an 8-staff LilyPond score at 200 dpi (staff space 13.8 px), columns ≥99% inked: gaps INSIDE a bracket at **bracket 218–224, systemic bar 235–237, final barline 1493–1495**; gaps BETWEEN groups at **235–237 only**; the **inter-system gap at nothing (max column ink 0.16)**. "**The systemic barline sits at exactly `x_start`**" — mimicking `Staff.x_start` gave **235**, "the same 3 px".
- **Literature:** Bravura `engravingDefaults`; SMuFL *engravingDefaults*; Scoring Notes. "The ratio is consistent; absolute values vary by a factor of two across applications."
- **Measured here:** ⚠️⚠️ **DEGRADATION IS MEASURED AND IT INVERTS THE ANSWER**: "At staff-space ≤7.6 px … the analyser reported **17 bridging columns across a real inter-system gap — a false MERGE produced purely by resolution.**" `benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md`.
- **Status:** MEASURED HERE (on a synthetic LilyPond score) + SOURCED (Bravura metrics).
- **Rigid or publisher-dependent:** stated as "**near-universal across publishers and eras**"; ⚠️ **19th-century plate practice is explicitly UNSOURCED** — "the agent found NO authoritative source … Refused to guess. **This is the biggest hole.**"
- **Would be falsified by:** its own published prediction table (per-boundary detect rate × boundaries: 0.97 → 0.913 / 0.885; 0.96 → 0.885 / **0.849**; 0.95 → 0.857 / 0.815); or a plate whose final barline's thick stroke is not markedly heavier.
- **Known exceptions:** **vocal staves are never joined by barlines even when bracketed**, so a choir gap is bridged by the bracket and the systemic rule and **by no barline at all.**
- **Code:** `tools/omr/staff_detector.py` `_gap_is_bridged`; `tools/omr/system_grouping.py` (cue A/B); `OMR_BRACKET_COLUMNS`.

### A bracket encloses a FAMILY, not the system — and a brace is a different mark and never a full column
`[C84 + L64]`

- **Says:** ⚠️⚠️ **the two left-edge enclosures are different objects.** A **bracket** is a straight-sided rule spanning **a family group** (with a second, lighter level for like instruments within a family), not the system; a **brace** is a curved flourish spanning one player's staves.
- **Predicts (mechanically):** **a brace can never satisfy a "column of ink through the whole gap" test**, and **a bracket's extent must not be read as the system's extent.** The two bracket levels are separable by weight.
- **Numbers:** ✅ **the sources agree on the two-level scheme and on the weights.** Bravura `bracketThickness` **0.5** against `subBracketThickness` **0.16** — **a 3× difference, so the two levels are separable by thickness alone.** Measured here on the test render: bracket geometry relative to `x_start` — outer edge ≈ **1.23 sp** left, inner ≈ **0.87 sp** left, **thickness ≈ 0.4 sp**; braces "peaked **0.5–0.7**" of the gap and **never a full column**.
- **Literature:** IU, *Brackets*: "Orchestra: bracket each choir (woodwinds, brass, percussion, strings); Secondary brackets on like instruments; third level for divisi". Bravura / SMuFL `engravingDefaults`. ⚠️ **"Variable by publisher, and some editions print no family bracket at all."**
- **Measured here:** ⚠️⚠️ **"[MEASURED+SOURCED] 'A bracket spans exactly the system' is FALSE and is an error in our CLAUDE.md"** — the test score prints "per-family brackets (**2 staves each in the test, 4 brackets for an 8-staff system**) plus the systemic barline". Independently, **0 of 147 read left-edge blocks span two systems** over 57 pages, and reading the bracket **over-splits on 27 of 57 pages**. `benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md`; `benchmarks/omr-bracket-reading-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE — **and it is disagreement #1, against `CLAUDE.md` rather than against the literature.**
- **Rigid or publisher-dependent:** RIGID for the geometry; **WHICH brackets are printed is publisher-dependent.**
- **Would be falsified by:** an edition printing one bracket per system — **Litolff and Simrock do exactly that.**
- **Known exceptions:** ⚠️⚠️ **the falsifier is already met on two of five editions** — Litolff and Simrock print ONE bracket for the whole orchestra, **where "a bracket spans the system" is accidentally TRUE**. "That is why the claim must not be relied on: **it holds on some plates and not others, and `CLAUDE.md` states it unconditionally.**" **This is the one entry the repo file would raise with Sean directly.**
- **Code:** the brace/bracket choice is `Q.GROUP_SYMBOL` (always abstains today); `export.py:681`, `:3523`, `:3446` still decide it by `len(staves) == 2`.

### Staff SPACING cannot separate a system from a group — REFUTED
`[C85]`

- **Says:** the proposed rule was that the vertical gap between systems is larger than the gap between staves.
- **Predicts (mechanically):** it would have given a distance threshold for system grouping. **It cannot, BY CONSTRUCTION.**
- **Numbers:** **[SOURCED]** LilyPond's shipped defaults (staff spaces), **basic / minimum**: staff-inside-group **9 / 7**; across-group-boundary **10.5 / 8**; system→system **12 / 8** — "**Under compression both floor at 8 → no distance threshold can separate them, by construction.**" **[MEASURED]** on a real 2-system page: within-group **4.98**, across-group **6.50**, between-system **8.02** — "and a denser variant's within-system gap hit **8.09**, larger than the other page's inter-system gap".
- **Literature:** LilyPond 2.24.4's own grob defaults, read directly. ⚠️ The literature's positive alternative is `[L9]`: a movement's first system is **INDENTED**, which is a horizontal signal rather than a vertical one — untested here.
- **Measured here:** independently, within one Brahms system the gaps run **17–237 px** and within one Beethoven system **130–345 px**, "both wider than the gaps BETWEEN systems on a piano page". Verdict: "**Demote spacing to a tie-breaker at most.**" `benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md`.
- **Status:** **REFUTED HERE**
- **Rigid or publisher-dependent:** n/a.
- **Would be falsified by:** it already is, **twice** — from LilyPond's own defaults and from a real page.
- **Known exceptions:** none. **This is why grouping is decided by CONNECTIVITY rather than distance.**
- **Code:** `tools/omr/staff_detector.py` — distance proposes a break and **connectivity vetoes it**; the veto can merge an over-split page, never split a correct one.

### Tempo marks stand above the top staff AND above the first violins
`[L69]`

- **Says:** a tempo indication is printed **twice** on a full-score system — once at the top and once above the strings.
- **Predicts (mechanically):** ⚠️⚠️ **text found above the first violin staff in mid-score is a TEMPO mark, not a direction belonging to that staff** — and it **duplicates** text that also appears at the top of the system. "A reader that attributes it to the violins will attach a **system-level fact to one part**, and a reader counting distinct directions **will double-count it**." IU adds a horizontal rule: "The left edge of the tempo indication should align with the left edge of the meter or the first notational element."
- **Numbers:** none.
- **Literature:** MOLA, *The Performance Material*: "All tempo indications should appear above the top staff and above the first violin line (or similarly positioned staff in the absence of strings) on each score page." IU, *Rehearsal Marks*. "Standard in modern preparation; older plates are less consistent but the practice is old."
- **Measured here:** not measured here — ⚠️ **and the reader that would meet it currently cannot.** *Direction words are printed INSIDE the system* `[C73 + L73]` clamps every candidate band to the staff's own `x_start..x_end`, and measured **all 98 candidates as `placement: below`, with the `above` band UNEXERCISED by both documents**. A tempo mark printed clear above a system is exactly the case that entry names as its falsifier, and **this convention says there are TWO of them per system.** Neither the duplication nor the attribution hazard has been priced.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** standard in modern preparation; older plates less consistent.
- **Would be falsified by:** held editions printing tempo marks only once per system.
- **Known exceptions:** scores with no strings place the second copy at the equivalent position.
- **Code:** no consumer found.

---

## Text & margin labels

### An instrument label is printed in the MARGIN — in FULL on the first system, ABBREVIATED thereafter
`[C69 + L70]`

- **Says:** the name stands outside the system, left of the staff's own start; a full score names each instrument **in full** at the beginning and uses **abbreviations** on subsequent pages.
- **Predicts (mechanically):** crop the margin band per staff and OCR it; **and conversely, anything found INSIDE the system's x-range is not a label.** ⚠️ **The first system of a work is the one page where the margin label is unambiguous, so identity should be established there and CARRIED**, rather than re-read per system — and a continuation system's labels are short, "**which is exactly the population a truncation-prone reader mishandles**".
- **Numbers:** the cascade reads **50 labels over 75 staves** on Litolff pp.1-4 — **12 of 12 on the opening system, naming the full lineup** — against **50 of 50 CORRECT** on a truth assembled from hand-read suppression lists and `works.json`'s hand-confirmed names (**deliberately NOT `printed-lineups.json`, whose own provenance says its names came from the OCR**). The free text-layer rung reads **0 of 75** on this 1870 scan.
- **Literature:** MOLA, *The Performance Material*: "At the beginning of the full score, the full name of each instrument should be listed to the left of the corresponding staff/staves. On subsequent pages, abbreviations of the instrument names should be used." Universal in orchestral engraving.
- **Measured here:** ⚠️ **a block taller than half the system's tick span is not a label** — two bad reads sat at **1.04×** the span against **1.5–4.7%** for all 17 blocks Surya correctly split on Boléro's dense page, "**a ~22× gap with 0.5 in the middle of it**". `benchmarks/omr-margin-labels-blob-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID for placement; **PUBLISHER-DEPENDENT for whether it is printed at all** — next entry.
- **Would be falsified by:** an edition printing names above the staff rather than beside it, or full names on every system.
- **Known exceptions:** ⚠️ **stacked instrument NUMBERS are printed left of the bracket and are not labels** — **24 of Mahler's 41** clef-locator false positives. ⚠️ The margin also holds **plate numbers**. ⚠️ And the literature's own exception is the next entry, measured: "Some editions omit labels on continuation systems for some families — **commonly the strings**".
- **Code:** `tools/omr/staff_labels.py`, `staff_labels_surya.py`, `staff_labels_vision.py`; `tools/omr/contextual.py` `_labels_for_page`.

### Some publishers stop labelling CONTINUATION systems — and the family they drop is the strings
`[C70]`

- **Says:** after the opening system a plate may name only some staves, and **which it drops is systematic**.
- **Predicts (mechanically):** ⚠️⚠️ **LABEL EVIDENCE IS STRUCTURALLY UNAVAILABLE EXACTLY WHERE IT WOULD HELP MOST** — the families that default to treble (winds, brass) **keep** their labels; the families that need a non-treble clef (strings, low brass) **lose** them.
- **Numbers:** over the 20-row scan corpus (**217 truth-carrying staves, 5 publishers**), the unresolved staves whose family defaults to something OTHER than treble — "the entire population [`clef_correction`] could ever be handed" — number **29, and 29 of 29 are in the class 'no label printed at all'**. "None is a lexicon refusal, a group-label fragment or an OCR miss."
- **Literature:** ✅ **stated as `[L70]`'s own known exception**, in almost these words: "Some editions omit labels on continuation systems for some families — **commonly the strings** — leaving those staves with no label at all."
- **Measured here:** contrast: Breitkopf Brahms 1 p0-3 has **97 of 97** slot verdicts already DECIDED — "that plate labels nearly every staff on every system". And page 3's 8-stave system reads `Fl.` `Cl.` `Fag.` `Cor.` — **no `Ob.`: the PRINT itself confirming the suppression.** `benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT.**
- **Would be falsified by:** an edition labelling its strings on every system — "**that would move it**", stated as the explicit limit.
- **Known exceptions:** ⚠️ this establishes only that the labels are **ABSENT**; "this says nothing about whether `clef_correction` would get those staves RIGHT if handed them".
- **Code:** consumed as a **reason to prefer a label-free second witness** — `clef_register_warning` "needs NO instrument label, which is what makes it worth having". No direct consumer of the publisher property.

### An engraver does not name one section with two different abbreviations on ONE system
`[C71]`

- **Says:** within a system, one instrument section gets one abbreviation.
- **Predicts (mechanically):** **a positional prior may NOT move a staff onto an instrument that a different alias on the same system already names.**
- **Numbers:** over the **1422-label corpus**, **86 of 158** ambiguous-alias occurrences clash — 52 `cor`, 18 `tp`, 9 `tr bas`, 7 `basso`/`bassi` — and hand-adjudicated the rule "**keeps or restores the right answer in 86 of 86 and blocks a correct overturn in 0**". Same-tree A/B on `--pages 23,44`: **24/29 → 26/29 correct**, the 17-staff finale system **16/17 → 17/17 exact**, `Timpani -> Trumpet` ×2 eliminated, **exactly 3 staff records change**.
- **Literature:** not covered as a rule. ⚠️ The literature supplies the hazard it guards against: `[L72]`, "the SAME abbreviation means different instruments across [traditions] — **`Tp.` is timpani in one tradition and trumpet in another**", which is precisely the `Tp.` case this rule fixes.
- **Measured here:** ⚠️ **the constraint is ASYMMETRIC** — it refuses only an OVERTURN and never removes the lexicon's own answer, because on p.48 `Tr. Bas.`'s two candidates (Trombone, Trumpet) are **both** separately named on its system. `probe_ambiguous_cooccurrence.py`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID.
- **Would be falsified by:** an orchestral page naming one section two ways — "**The probe FAILS if an orchestral source ever joins that list.**"
- **Known exceptions:** ⚠️ **Handel's *Messiah* prints `BASSO` (the bass VOICE) and `Bassi` (the string basses) on one page** and needs both first answers as they stand; there the two labels block each other, "which is the rule doing the right thing". ⚠️ A real *tromba bassa* on a page that also prints `Tr.` would be blocked from a correct overturn — "nothing in either corpus prints one".
- **Code:** `tools/omr/contextual.py` (the uniqueness guard); pinned by `tools/omr/tests/test_contextual_ambiguity_uniqueness.py`.

### A TROMBONE section is scored by REGISTER; a TRUMPET section by NUMBER AND KEY
`[C72]`

- **Says:** `Tr. Alt. / Tr. Ten. / Tr. Bas.` names trombones; `Tr. I`, `Trombe in C` names trumpets. **The abbreviation is the same; the qualifier names the family.**
- **Predicts (mechanically):** `tr alt` / `tr ten` / `tr bas` must **outrank** the bare `tr`; and **a size word may not beat an instrument noun.**
- **Numbers:** validated on **1380 margin labels across 10 editions**. Beethoven 5 p.48 went 0 → 12 labels and **three resolved to the wrong instrument**.
- **Literature:** not covered as a scoring convention. ⚠️ `[L72]` supplies the shape of the problem — abbreviations are "two to five characters, often with a trailing period", median length 3, and "at that length, **OCR errors and truncation are both likely to produce a string that is a valid abbreviation for a DIFFERENT instrument**, so a match must be scored against the work's roster rather than accepted on its own".
- **Measured here:** `Tr. Alt.` had been reading as **Alto, a singer, at high confidence**. Beethoven 5 p.47 prints both `Tr.` (trumpets) and `Tr. Alt. / Tr. Ten. / Tr. Bas.` (trombones) four staves below. ⚠️ **`Tr. B.` is deliberately NOT among the trombone aliases — that is a trumpet in B-flat.** The second half was a mechanism gap: `VOICE_QUALIFIERS` was HAND-LISTED with spelled-out `alto`/`tenor`, so an abbreviated `Alt.` never reached it; **derived** from the voice instruments' own aliases it also fixes `Fl. Alt.`, `Cl. Alt.` and `Trb. Tenore`. `benchmarks/omr-margin-labels-2026-08/LEXICON_TR_ALT_2026-08-31.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID (a convention of scoring, not of one plate) — and **the fix is reader-independent**: "the lexicon is reader-independent … which means the paid reader returned the same answer for the same printed string".
- **Would be falsified by:** a plate numbering its trombones and registering its trumpets.
- **Known exceptions:** ⚠️ **a cross product must be DERIVED, not hand-listed** — the contrabassoon is a bassoon noun plus a contra- qualifier across four languages, the hand list held **six of about twenty-five**, and the missing ones "did not abstain": `Contra-Fagott` and `Cont. Fag.` read as **Bassoon at HIGH confidence**. The live cost was **ten staves** of the scan benchmark's Brahms 1 (`K. Fag.`).
- **Code:** `tools/omr/instruments.py` (`_CONTRA_ALIASES` generated from `_BASSOON_ALIASES`; `VOICE_QUALIFIERS` derived).

### Direction words are printed INSIDE the system, in a conventional language
`[C73 + L73]`

- **Says:** `legato`, `Allegro con brio`, `cresc.` stand within the staff's own x-range — and tempo, dynamic, technique and expression instructions use a conventional language (Italian, English, German or French).
- **Predicts (mechanically):** **clamp every candidate band to the staff's `x_start..x_end`** — which makes "inside a system vs a margin" true **BY CONSTRUCTION** rather than a test. ⚠️ And the gate must be a **MULTILINGUAL lexicon**, not an English one; "**the printing TRADITION of a document is inferable from the words it uses**, which in turn predicts which abbreviation set its margin labels are drawn from".
- **Numbers:** reach — Litolff p1-3 **42 word-shaped candidates, 2 accepted**; Breitkopf p0-3 **56 candidates, 10 accepted**. Equivalence against the legacy path over the same four Brahms pages: **10 accepted vs 10, and 7 of 7 `(page, text)` pairs agree exactly**.
- **Literature:** MOLA, *The Performance Material*: "All instructions for tempi, dynamics, technique, and expression should be in a conventional language such as English, Italian, German, or French." "Conventional; a single document is usually consistent in one language."
- **Measured here:** "`find_candidates` clamps every band to the staff's own `x_start..x_end`, so **0 candidates are ever in a margin**; **all 98 are `placement: below`** and the `above` band is **UNEXERCISED by both documents**." `benchmarks/omr-staged-direction-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** RIGID for placement; the language is document-dependent.
- **Would be falsified by:** a tempo mark printed clear above the system that the clamped band cannot reach — ⚠️ **which `[L69]` says is printed TWICE on every full-score system**, and which neither document exercises.
- **Known exceptions:** ⚠️ `Q.DIRECTION_BAND_POSITION` is the fact "that separates a `cresc.` standing in the dynamics row from an `Allegro con brio` printed clear above the system, which `placement` cannot" — **recorded and read by nothing**. ⚠️⚠️ **EQUIVALENCE, not truth: no word has been checked against the print.** Literature: mixed-language editions, "and Italian dynamics with German expression marks in the same score, **which is common in 19th-century German publishing**".
- **Code:** `tools/omr/direction_text.py` `find_candidates`; `OMR_DIRECTION_TEXT` (default ON).

### The printing TRADITION is a property of the document — and the same abbreviation means different instruments across traditions
`[C74 + L72]`

- **Says:** a plate that prints `Flauti/Corni/Trombe` is Italian-tradition throughout; one printing `Flöten/Hörner/Trompeten` is German. **The abbreviations used in margins are conventional and few — and they collide across languages.**
- **Predicts (mechanically):** **a document-level language read off its own unambiguous labels settles abbreviations the global lexicon resolves one way for every score.** ⚠️ And the literature bounds the lexicon and names the hazard: the strings are **two to five characters, median length 3**, so "**OCR errors and truncation are both likely to produce a string that is a valid abbreviation for a DIFFERENT instrument, so a match must be scored against the WORK'S ROSTER rather than accepted on its own**".
- **Numbers:** IU's English list: **Picc., Fl., Ob., E.Hn., Cl., Bcl., Bn., Hn., Tp., Trb., Btrb., Tba., Timp., Pc., Hp., Pn., Vn., Va., Vc., Cb.** — 20 entries, median length 3. Measured here: **167 of 1422 labels ambiguous, 167 reachable, 9 re-decided** — all `Tb.` → Trombone on Litolff's Beethoven 6, "a work whose IMSLP roster has 2 trombones and no tuba".
- **Literature:** IU, *Instrument Names*. ⚠️⚠️ **"Highly variable by language and publisher — this is one English-language house list.** Italian (`Fl.`, `Ob.`, `Cor.`, `Tr.`, `Vni`), German (`Fl.`, `Hb.`, `Hr.`, `Trp.`, `Vl.`) and French traditions all differ, and **the SAME abbreviation means different instruments across them (`Tp.` is timpani in one tradition and trumpet in another)**." Its *Would be falsified by* is "Nothing — the variability is the finding, **and it is the main hazard in reading margin labels**."
- **Measured here:** ⚠️ it decides **ONLY aliases `AMBIGUOUS_ALIASES` does not declare** — "a declared one is owned by the clef-informed position channel, and **two signals sharing an ancestor are one signal**". DETECTION is unconditional and recorded; only the re-decision is behind the flag. `benchmarks/omr-score-language-2026-09/FINDINGS.md`.
- **Status:** MEASURED HERE
- **Rigid or publisher-dependent:** **PUBLISHER/DOCUMENT-DEPENDENT by definition.**
- **Would be falsified by:** a plate mixing traditions.
- **Known exceptions:** none recorded on the repo side; the 9 re-decisions are one work. ⚠️ The literature's cross-language collisions are the standing hazard, and the `Tp.` one is measured under *An engraver does not name one section with two different abbreviations*.
- **Code:** `OMR_SCORE_LANGUAGE` (default OFF); `contextual.score_language`.

### Measure numbers are printed at system starts
`[C75 + L68]`

- **Says:** bar numbers are printed at the beginning of each system — or below the system if every bar is numbered. **The engraver has already told us how many bars are on the line.**
- **Predicts (mechanically):** ⚠️⚠️ **an INDEPENDENT WITNESS to `measure_partition`, which is currently decided from barline columns alone** — "the only page-side quantity that could corroborate a bar count without a reference file". And the literature adds the discriminator: **a small numeral at a system's top-left corner, OUTSIDE the staff, is a measure number, not a fingering, tuplet or meter digit** — position separates it from every other numeral family on the page. "**And it names the DOCUMENT's bar index for that system, which is the join between a printed system and a reference encoding.**" Rehearsal marks do the same and anchor ACROSS parts.
- **Numbers:** **one sentence, no table**: "the row-drafting work found **three of four editions** print them" (`docs/position-grammar-confusables-2026-09-04.md:113`). ⚠️ The repo file searched and "could find no other statement of it and no per-edition measurement".
- **Literature:** MOLA, *The Performance Material*: "If every measure is to be numbered it should be placed below the system. Often just the first measure of each system is numbered, placed in the upper left corner and sometimes additionally … on a specific line of the grand staff, such as above the first violins." IU: "Place at system start." **Two accepted placements, both stated; MOLA requires only that the choice be consistent throughout a work.**
- **Measured here:** not measured here.
- **Status:** ASSERTED (untested here)
- **Rigid or publisher-dependent:** **PUBLISHER-DEPENDENT** (by assertion) — and the literature agrees there are two accepted placements.
- **Would be falsified by:** counting printed system-start numbers per edition.
- **Known exceptions:** ⚠️ **it is not trivially reachable**: the numbers are small text (the `direction_text` rung's problem) and the coarse `numeral*` class "covers meters, tuplet digits, fingerings *and* measure numbers under one name". Literature: **film and music-theatre scores number every bar**, in both score and parts.
- **Code:** **no consumer found.**

### A running head names the instrument on every page of a part
`[L71]`

- **Says:** each page after the first carries the instrument name as a header.
- **Predicts (mechanically):** **in a PART, identity is available from page text independent of any staff label — a second, non-margin source for the same fact.** ⚠️ **On a SCORE this does not apply, and the margin is the only source.**
- **Numbers:** none.
- **Literature:** Gould p.558 (*Labelling the part*): "For subsequent pages it is good policy to label the top centre of each page with instrument name and player number, in case pages become separated later (this is known as a 'running head')." MOLA: "Include instrument names as a header on each subsequent page." ⚠️ **"Recommended practice rather than universal; Gould's word is 'good policy'."**
- **Measured here:** not measured here, **and it is out of scope for this project as currently aimed** — every document in the corpus is a conductor's SCORE, for which this entry itself says the margin is the only source. It is filed because it bounds what a future parts-reading path could expect.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** recommended rather than universal.
- **Would be falsified by:** parts with no running head — **which are common.**
- **Known exceptions:** for a doubling part "it is necessary to give only the principal instrument for the running head", **so the running head can be LESS SPECIFIC than the staff label.**
- **Code:** no consumer found.

---

## Barlines & repeats

### Repeat dots are a vertical PAIR in the two middle spaces, adjacent to a barline
`[C76 + L77]`

- **Says:** the repeat sign's dots straddle the middle line, beside the barline they belong to — one between the second and third lines, one between the third and fourth.
- **Predicts (mechanically):** **the dots are at FIXED staff positions**, one space above and one below the centre line, so "a repeat sign is recognisable from two small round marks at known heights beside a heavy barline, **with no need to read the barline's own structure**". ⚠️ **And the SIDE the dots fall on tells which way the repeat faces.** The barline is already a classical-CV object, "**so the anchor exists without the model**" — dots + CV barline is the anchor pair, with no model change.
- **Numbers:** dots centred in **spaces 2 and 3**, i.e. at **±1 space from the centre line**. Bravura `repeatBarlineDotSeparation` **0.16** staff spaces — "the default horizontal distance between the dots and the inner barline".
- **Literature:** Wikipedia, *Bar (music)* and *Repeat sign*: "The dots will be on the same side of the line as the material which is to be repeated." Bravura `engravingDefaults`. **"Rigid on a five-line staff. Undefined for staves of other sizes"** — i.e. one-line percussion staves.
- **Measured here:** ⚠️ **no figure.** The reach limit IS recorded: "the `repeat` family is **`repeatDot` ONLY — we have the dots, not the sign** — and **`volta` is not in the class space at all** (checked, not assumed)", and an earlier audit of the class space found `repeatDot` ×4 on the benchmark. "MusicXML repeat signs are dropped on export" has stayed a TODO "**because the ink for the barline half is not detected either**". `docs/position-grammar-confusables-2026-09-04.md` §2 DOT and §5.
- **Status:** ASSERTED (untested here) — ✅ **the POSITIONS are sourced from the literature; nothing is measured on a plate.**
- **Rigid or publisher-dependent:** RIGID on a five-line staff.
- **Would be falsified by:** measuring detected `repeatDot` positions against the middle line on a plate that prints repeats; or repeat dots at other staff positions.
- **Known exceptions:** ⚠️ **F-clef dots are the confusable — but they are separable**: they are **header-window only, straddling line 4, past the clef body's right edge (0.94–1.79 notehead-widths — the region where a C clef has nothing)**, which the dot-veto work priced exactly (clef-locator false positives **48 → 13 → 5**). Literature: one-line percussion and other non-standard staves.
- **Code:** **no consumer found** for repeats. The F-clef half is live in `tools/omr/clef_locator.py` (`dot_clear_right_fraction`, `dot_single_clear_is_enough`).

### A double barline is a SECTION mark; a thin-thick barline is a movement END — and nothing here can read one
`[C77 + L45 + L76 + L79]`

- **Says:** the thin double barline is a **structural** mark placed at tempo changes, modulations and section divisions; a thin-then-**thick** barline ends a piece or movement. ⚠️ **It is NOT a consequence of the metre changing, and the two must not be inferred from each other.**
- **Predicts (mechanically):** ⚠️⚠️ **the classification is a THICKNESS COMPARISON between two adjacent vertical runs, which needs no context**: thin-thin = section division, thin-thick = end of a piece or movement. "**Getting it right matters structurally: a thin-thick barline is a MOVEMENT BOUNDARY, which is exactly where a carried meter, key and lineup must all stop being carried.**" It is "**the cheapest structural landmark on a page**". ⚠️ And the negative prediction: **"a reader that treats every double barline as a metre change, or that expects one at every metre change, is wrong in both directions."**
- **Numbers:** the second stroke is either **0.16** (section) or **0.5** (final); `barlineSeparation` **0.4**, `thinThickBarlineSeparation` **0.4**. **A thick barline is exactly as heavy as a BEAM (both 0.5) and three times a thin barline**, so thin/thick is robust to a coarse measurement while thick-barline-vs-beam is not — **that one needs orientation.**
- **Literature:** Wikipedia, *Bar (music)*: "A double bar line … consists of two single bar lines drawn close together, separating two sections within a piece, or a bar line followed by a thicker bar line, indicating the end of a piece or movement." Gould p.152: "A thin double barline precedes a change of time signature **only when one coincides with a new musical section**." IU, *Barlines*: "Double barlines for tempo changes and modulations … **Do not use at meter changes**"; "Heavy single barlines for phrase divisions". ⚠️ **"Variable by house — IU's rules are one department's; other houses use double barlines at metre changes, which IU forbids. The presence of a double barline is meaningful; its ABSENCE is not."**
- **Measured here:** ⚠️⚠️ **`tools/omr/staged/ASSUMPTIONS.md` A-DUR-6 named the double barline as "the cheap independent reader" and THAT ENTRY IS CORRECTED**: "the double barline is **not** the cheap independent reader that entry calls it (`Q.BARLINE_COLUMN` is a per-staff *count of cells*, and **no barline-type classification exists**)". Independently: `barlineSingle` is the only barline class the labelling guidance mentions; custom barline classes were tried in Phase 3.4 and "**caused catastrophic forgetting (F1 cratered to 79.3%)**"; and barlines are classical-CV, which **measures columns rather than classifying them**. ⚠️ The one place a double barline is visibly load-bearing went the other way: Litolff p.62's printed `3/4` stands "right after the double barline under *Tempo I.*" at **cell 6**, and the pipeline's own record put it at **cell 8** — on **one barline broken into two fragments** read as `timeSig3` + `timeSig4`.
- **Status:** **REFUTED HERE as an available signal** — the convention itself is not in doubt; **its readability is.**
- **Rigid or publisher-dependent:** the thin/thick distinction is RIGID; **WHERE a house puts a double barline is variable.**
- **Would be falsified by:** a barline-type classifier existing and working; an edition ending a movement with a thin-thin barline; an edition using a double barline at every metre change.
- **Known exceptions:** IU's stricter practice, which is one reading of the same principle.
- **Code:** **no consumer found.** `tools/omr/measure_extractor.py` detects barline COLUMNS and **does not type them.**

### VOCAL staves are not joined by barlines, even when they are bracketed
`[C86]`

- **Says:** in a choral system the barlines stop at each vocal staff (the "choir-barred" or **Mensurstrich** practice), so **the bracket encloses staves that no barline connects.**
- **Predicts (mechanically):** ⚠️ **a bracketed group whose interior gap NOTHING IN-WINDOW CROSSES is the choir-barred signature — "impossible for a true open score"** — so such a system must never be flipped into open-score mode by aligned stems out-voting its barlines.
- **Numbers:** the convention is stated with a source but **no count**. In the LilyPond test score the **S–B gap inside the ChoirStaff is bridged by bracket 218–224 and systemic bar 235–237 — and by NO barline.** Over a 969-page library probe, **757 examined break-gaps read 0 ×735 / ≥4 ×22 with nothing at 1–3.**
- **Literature:** ✅ **corroborated from the encodings' own vocabulary and from `[L63]`** — MusicXML `<group-barline>` ∈ {`yes`, `no`, **`Mensurstrich`**}, MEI `@bar.thru`; and `[L63]`'s known exceptions name "**Mensurstrich editions** … [and] **choir-barred vocal scores, where the breaks fall at choir edges rather than family edges**", plus Wikipedia, *Bar (music)* on a barline that "stretches only between staves of a score, not through each staff".
- **Measured here:** what IS measured is the **repair it forces**: `OMR_CHOIR_GROUPING` cue C takes the Bach Brandenburg 3 stress row from **0.9241 → 0.8152** OMR-NED, **6735 → 6236 edits**, and measure-cells **122 → 11 against a true 10**; all ten pooled scan rows byte-identical and the 11-work engraved benchmark **edit-for-edit identical (0.1306 / 2745)**. The 10 pages that change were each hand-adjudicated toward the truth (7 exact heals including both operas' vocal systems; **zero false merges**).
- **Status:** ASSERTED (untested here) as a convention; **its consequence is MEASURED.**
- **Rigid or publisher-dependent:** RIGID for vocal music; **it is a property of the MUSIC's layout, not of one publisher.**
- **Would be falsified by:** a choral edition running barlines through its vocal staves.
- **Known exceptions:** ⚠️⚠️ **bracket-groups ALONE was FALSIFIED on the engraved benchmark** — "LilyPond open scores manufacture 'groups' from bridging jitter; pooled **0.1306 → 0.8560**, nine works' barlines deleted". **The second condition (a window-blind internal gap) is what makes it safe: do not loosen it.**
- **Code:** `tools/omr/measure_extractor.py` (`OMR_CHOIR_GROUPING` cue C, default ON since 2026-09-05).

### A dashed barline has a dash twice the length of its gap
`[L78]`

- **Says:** dashed barlines are drawn with a specific dash-to-gap ratio.
- **Predicts (mechanically):** ⚠️ **a broken vertical run at a bar position is a DASHED BARLINE, not a damaged solid one, if its dashes and gaps are REGULAR at roughly 2:1.** "That distinguishes an **engraving choice** from **scan damage** — which otherwise look identical to a run-length detector."
- **Numbers:** Bravura `dashedBarlineDashLength` **0.5**, `dashedBarlineGapLength` **0.25**, `dashedBarlineThickness` **0.16**.
- **Literature:** Bravura `engravingDefaults`; SMuFL *engravingDefaults*. "Font default; **dashed barlines are rare in the orchestral repertoire.**"
- **Measured here:** not measured here. ⚠️ **The distinction it draws is one this project pays for repeatedly in the other direction** — *A barline is a STRAIGHT line, not a vertical one* `[C57]` exists because scan shear breaks a barline's column, and *"A meter stack is two digits aligned in x"* `[C34]`'s live consequence is **one barline broken into two fragments** read as a meter. **A regularity test on a broken vertical run has never been tried.** Reach is likely tiny in this repertoire, by the literature's own note.
- **Status:** LITERATURE ONLY (untested here)
- **Rigid or publisher-dependent:** font default; rare in this repertoire.
- **Would be falsified by:** dashed barlines with irregular dashes.
- **Known exceptions:** none recorded.
- **Code:** no consumer found.

---

## Conservation

⚠️⚠️ **EVERY ONE OF THE 166 SOURCE ENTRIES IS ACCOUNTED FOR BELOW, BY NAME.**
A merge that silently drops entries is a failure this repository has paid for
repeatedly, so the ledger is the deliverable, not a courtesy. **Nothing could
not be placed; the unplaced list is empty.**

### The arithmetic

```
  87  entries from  docs/conventions/from-this-repo.md      (C1 – C87)
+ 79  entries from  docs/conventions/from-the-literature.md (L1 – L79)
─────
 166  source entries

    46  repo entries that ABSORBED a literature entry
  + 52  literature entries absorbed into them   (6 repo entries took two or more)
  + 41  repo entries kept standalone (literature: not covered)
  + 27  literature entries kept standalone (untested here)
─────
 166  source entries accounted for            ✅ BALANCES

    46  merged entries
  + 41  repo-only entries
  + 27  literature-only entries
─────
 114  registry entries
```

**Check both ways:** repo side `46 + 41 = 87` ✅ · literature side `52 + 27 = 79` ✅ ·
output `46 + 41 + 27 = 114` ✅.

**The six repo entries that absorbed more than one literature entry:**
`C17` (+L24, L25) · `C21` (+L33, L34) · `C22` (+L36, L37) · `C51` (+L58, L61) ·
`C77` (+L45, L76, L79 — three) · and no others. `46 + 6 = 52` ✅.

**Unplaced: NONE.** Every source entry has a destination row below.

### `from-this-repo.md` — all 87

| src | source entry name | landed in | with |
|---|---|---|---|
| C1 | A notehead is one staff space tall | *A notehead is one staff space tall* | L3 |
| C2 | A notehead sits ON a line or IN a space, on a half-space lattice | *(same title)* | kept standalone |
| C3 | Ledger-line pitch is NOT the staff spacing, and it is publisher-dependent | *(same title)* | L5 |
| C4 | A note outside the staff is joined to it by an unbroken ladder of ledger rungs | *(same title)* | kept standalone |
| C5 | The engraver opens the gap above a staff PRECISELY so its ledger notes can live there | *(same title)* | kept standalone |
| C6 | A ledger rung printed THROUGH a hollow notehead is split by the head's white counter | *(same title)* | kept standalone |
| C7 | The SMuFL em box is four staff spaces | *The staff space is the unit of everything — the em box is four staff spaces* | L1 |
| C8 | A staff's five lines are straight and evenly spaced — and on a scanned plate they are neither | *(same title)* | kept standalone |
| C9 | A stem attaches on the RIGHT going UP, or on the LEFT going DOWN | *(same title)* | L10 |
| C10 | In a single voice, a note above the middle line is stemmed DOWN | *(same title)* | L16 |
| C11 | A beam joins stem TIPS, so every stem on one stroke points the same way | *(same title)* | kept standalone |
| C12 | A beam stroke runs from the FIRST stem it joins to the LAST, and a stem stands at the SIDE of its notehead | *(same title)* | kept standalone |
| C13 | A stem is as long as the music needs it to be | *A stem is one octave long by default — and as long as the music needs it to be* | L11 |
| C14 | Two successive notes are set further apart than one accidental's own two strokes | *(same title)* | kept standalone |
| C15 | No stem means a whole note | *(same title)* | kept standalone |
| C16 | A whole rest stands for THE BAR, whatever the meter | *(same title)* | L27 |
| C17 | A whole rest HANGS under the 4th line; a half rest SITS on the 3rd; they are the same shape | *A whole rest HANGS under the 4th line; a half rest SITS on the 3rd — and they are the same shape* | L24, L25 |
| C18 | A tacet part prints a whole rest in EVERY bar | *(same title)* | kept standalone |
| C19 | A quarter rest and a whole rest are different shapes, and the box aspect separates them | *Rest shapes separate strongly by aspect ratio — except whole vs half* | L26 |
| C20 | A silent bar is still PRINTED with a rest; a genuinely blank bar means we failed to read it | *(same title)* | kept standalone |
| C21 | An accidental holds for its letter and octave to the end of the bar | *An accidental is a SCOPE to the end of the bar — and it carries across a barline through a TIE* | L33, L34 |
| C22 | A key signature's accidentals stand at fixed slots, and which slots depends on the CLEF | *A key signature's accidentals stand at fixed slots, in a fixed order, keyed on the CLEF* | L36, L37 |
| C23 | A key signature stands BETWEEN the clef and the meter | *(same title)* | L40 |
| C24 | A key CHANGE is printed at ONE bar of ONE system, on EVERY staff of it | *(same title)* | kept standalone |
| C25 | The clef and key signature are reprinted at the head of EVERY system | *(same title)* | L38 |
| C26 | A courtesy accidental is a property of the EDITION, not of the music | *A courtesy accidental is real ink that changes nothing — and its frequency is a property of the EDITION* | L35 |
| C27 | A time signature's placement is RIGID — numerator upper, denominator lower | *A time signature's placement is RIGID — and its numerals fill the staff's height* | L42 |
| C28 | A meter is printed at a movement's START and nowhere else | *(same title)* | L41 |
| C29 | A meter is printed on EVERY staff of the system | *(same title)* | kept standalone |
| C30 | A cautionary meter printed after a system's FINAL barline governs no bar | *(same title)* | L44 |
| C31 | A letter meter (`C`, `¢`) is a complete meter, and the stroke is what separates them | *A letter meter (`C`, `¢`) is a complete meter — and the stroke is what separates them* | L46 |
| C32 | An OPENING meter sits 10–12 staff spaces into its bar | *(same title)* | kept standalone |
| C33 | A mid-staff meter CHANGE is printed at the bar head with no clef in front of it | *(same title)* | L43 |
| C34 | "A meter stack is two digits aligned in x and adjacent in y" — REFUTED | *(same title)* | kept standalone |
| C35 | A slur is drawn OVER its notes; a hairpin is drawn BETWEEN them | *(same title)* | L48 |
| C36 | A slur's ink stops INSIDE both outer notehead centres | *(same title)* | L51 |
| C37 | An arc over STEMMED notes is drawn stem-top to stem-top | *(same title)* | kept standalone |
| C38 | One printed arc cut by a barline is still ONE arc | *(same title)* | L50 |
| C39 | A tie's two ends are at ONE staff position, by definition | *(same title)* | L47 |
| C40 | A TIE is drawn shallow and close to its two heads; a SLUR arcs clear of the notes under it | *(same title)* | kept standalone |
| C41 | Sean's S4: an arc connected to the stem's edge AWAY from the notehead is a SLUR — REFUTED | *(same title)* | kept standalone |
| C42 | Sean's S6: of two arcs stacked over each other, the LOWER is a tie and the UPPER a slur | *(same title)* | kept standalone |
| C43 | The tie/slur POSITION GRAMMAR (S2/S5) — measured on both families and REFUSED | *The tie/slur POSITION GRAMMAR (S2/S5), measured on both families and REFUSED* | kept standalone |
| C44 | A bar's first note sits 2.0–2.5 staff spaces past the barline | *(same title)* | kept standalone |
| C45 | A hairpin is printed BELOW its staff, in the dynamics band | *A hairpin is printed BELOW its staff, in the dynamics band — and dynamics are not placed INSIDE the staff* | L55 |
| C46 | A dynamic LETTER stands in its own staff's band, below the bottom line | *(same title)* | L53 |
| C47 | A dynamic WORD is a run of adjacent letters (`f`+`f` = `ff`) | *(same title)* | L57 |
| C48 | A hairpin runs quiet → loud and travels with a dynamic letter | *(same title)* | kept standalone |
| C49 | An ACCENT is note-anchored; a HAIRPIN is span-anchored | *(same title)* | kept standalone |
| C50 | An augmentation dot sits at the note's own space — half a space ABOVE for a note on a line — and NEVER below | *(same title)* | L31 |
| C51 | A staccato or accent is printed directly above or below its notehead, on the side its class names | *A staccato or accent is printed on the notehead side, opposite the stem, and CENTRED on the head in x* | L58, L61 |
| C52 | A FERMATA hangs over whatever sounds beneath it — which is often a whole-bar rest, not a note | *(same title)* | L62 |
| C53 | A TUPLET digit stands OUTSIDE the staff over its beam; a TIME-SIGNATURE digit stands INSIDE it; a FINGERING sits beside its notehead | *(same title)* | kept standalone |
| C54 | A tuplet DIGIT is printed over the middle of its group; a tuplet BRACKET encloses it | *(same title)* | kept standalone |
| C55 | A TREMOLO rides the stem, so it has no side at all | *(same title)* | kept standalone |
| C56 | A barline runs the FULL HEIGHT of its system, and nothing else does | *(same title)* | L74 |
| C57 | A barline is a STRAIGHT line, not a vertical one | *(same title)* | kept standalone |
| C58 | Interior barlines STOP at instrument-family boundaries | *(same title)* | L63 |
| C59 | A bracket BLOCK is an engraving unit, not an instrument family | *(same title)* | kept standalone |
| C60 | Some publishers print NO section bracket at all | *(same title)* | kept standalone |
| C61 | No left-edge object ever bridges a system break | *(same title)* | kept standalone |
| C62 | A printed score may OMIT a tacet part; it may never REORDER one | *(same title)* | L66 |
| C63 | The strings are the LAST block of a system, and a short string section is short at its FOOT | *(same title)* | kept standalone |
| C64 | A column through a system is one INSTANT of music | *(same title)* | kept standalone |
| C65 | A BRACE means ONE PLAYER | *(same title)* | kept standalone |
| C66 | An engraver spaces notes roughly in PROPORTION TO DURATION | *(same title)* | kept standalone |
| C67 | Whether one printed staff label means ONE part or TWO is a property of the ENCODING, not the engraving | *(same title)* | L67 |
| C68 | A PAGE truth is not an ENCODING truth | *(same title)* | kept standalone |
| C69 | An instrument label is printed in the MARGIN, at the left of its staff | *An instrument label is printed in the MARGIN — in FULL on the first system, ABBREVIATED thereafter* | L70 |
| C70 | Some publishers stop labelling CONTINUATION systems — and the family they drop is the strings | *(same title)* | kept standalone |
| C71 | An engraver does not name one section with two different abbreviations on ONE system | *(same title)* | kept standalone |
| C72 | A TROMBONE section is scored by REGISTER; a TRUMPET section by NUMBER AND KEY | *(same title)* | kept standalone |
| C73 | Direction words are printed INSIDE the system, not in the margin | *Direction words are printed INSIDE the system, in a conventional language* | L73 |
| C74 | The printing TRADITION (Italian vs German) is a property of the document | *The printing TRADITION is a property of the document — and the same abbreviation means different instruments across traditions* | L72 |
| C75 | Measure numbers are printed at system starts | *(same title)* | L68 |
| C76 | Repeat dots are a vertical PAIR in spaces 2 and 3, adjacent to a barline | *Repeat dots are a vertical PAIR in the two middle spaces, adjacent to a barline* | L77 |
| C77 | A DOUBLE BARLINE marks a section end — and nothing in this pipeline can read one | *A double barline is a SECTION mark; a thin-thick barline is a movement END — and nothing here can read one* | L45, L76, L79 |
| C78 | A beam is always connected to something; a HAIRPIN is connected to NOTHING | *… — and it is thinner than a stem* | L56 |
| C79 | Stacked beams are set 0.75 staff spaces centre to centre | *(same title)* | L20 |
| C80 | A FLAG glyph NAMES A VALUE; it is not a tally of hooks | *A FLAG glyph NAMES A VALUE, and it hangs on the STEM* | L23 |
| C81 | Timpani, horns and trumpets are conventionally written WITHOUT a key signature | *(same title)* | L39 |
| C82 | SCORE ORDER is a convention strong enough to resolve a label by | *(same title)* | L65 |
| C83 | The only ink crossing a family gap is the SYSTEMIC BARLINE, and it is about 0.16 staff spaces wide | *(same title)* | L75 |
| C84 | A BRACE is curved, so it never forms a full column — and "a bracket spans exactly the system" is FALSE | *A bracket encloses a FAMILY, not the system — and a brace is a different mark and never a full column* | L64 |
| C85 | Staff SPACING cannot separate a system from a group — REFUTED as a discriminator | *Staff SPACING cannot separate a system from a group — REFUTED* | kept standalone |
| C86 | VOCAL staves are not joined by barlines, even when they are bracketed | *(same title)* | kept standalone |
| C87 | A TRILL, TURN or MORDENT is printed clear ABOVE its note, centred on it | *(same title)* | kept standalone |

**Repo tally: 46 merged + 41 standalone = 87** ✅

### `from-the-literature.md` — all 79

Numbered `L1–L79` in that file's own document order.

| src | source entry name | landed in | how |
|---|---|---|---|
| L1 | The staff space is the unit of everything | *The staff space is the unit of everything — the em box is four staff spaces* | merged into C7 |
| L2 | A glyph's baseline sits at the staff position it names | *(same title)* | kept standalone |
| L3 | A notehead is exactly one staff space tall | *A notehead is one staff space tall* | merged into C1 |
| L4 | A whole notehead is wider than a black one, and the same height | *(same title)* | kept standalone |
| L5 | A ledger line is drawn at the staff's own spacing, slightly longer than the notehead | *Ledger-line pitch is NOT the staff spacing…* | merged into C3 — **DISAGREEMENT #2** |
| L6 | A ledger line is thicker than a staff line | *(same title)* | kept standalone |
| L7 | Staff line thickness is around an eighth of a staff space, and applications disagree by 2× | *(same title)* | kept standalone |
| L8 | A staff is 4–8.5 mm tall, and the score end is the small end | *(same title)* | kept standalone |
| L9 | The first line of each movement is indented | *(same title)* | kept standalone |
| L10 | A stem attaches on the right going up and on the left going down | *A stem attaches on the RIGHT going UP, or on the LEFT going DOWN* | merged into C9 |
| L11 | A stem is one octave long — 3.5 staff spaces | *A stem is one octave long by default — and as long as the music needs it to be* | merged into C13 — **DISAGREEMENT #5** |
| L12 | A stem on ledger lines reaches the middle staff line | *(same title)* | kept standalone |
| L13 | A stem is never shorter than 2.5 staff spaces | *(same title)* | kept standalone |
| L14 | A stem is about a tenth of a staff space thick | *(same title)* | kept standalone |
| L15 | Where there is no case for either direction, the stem goes DOWN | *(same title)* | kept standalone |
| L16 | A note at or above the middle line takes a down-stem | *In a single voice, a note above the middle line is stemmed DOWN* | merged into C10 |
| L17 | Two voices on one staff: upper voice up, lower voice down, regardless of position | *(same title)* | kept standalone |
| L18 | Stem direction is held constant through a beat or half-bar | *(same title)* | kept standalone |
| L19 | In a chord containing a second, the two heads straddle the stem | *(same title)* | kept standalone |
| L20 | A beam is half a staff space thick, with a quarter-space gap between beams | *Stacked beams are set 0.75 staff spaces centre to centre* | merged into C79 — **sources AGREE to the number** |
| L21 | A beam is angled by the OUTER interval, and is horizontal in three named cases | *(same title)* | kept standalone |
| L22 | Beaming follows the metre, and never crosses the middle of the bar | *(same title)* | kept standalone — **DISAGREEMENT #6 (era exception)** |
| L23 | A flag hangs on the stem, starting at the stem's end | *A FLAG glyph NAMES A VALUE, and it hangs on the STEM* | merged into C80 |
| L24 | A whole rest HANGS from its line; a half rest SITS on it | *A whole rest HANGS under the 4th line…* | merged into C17 |
| L25 | The whole and half rest glyphs are the same shape and the same size | *A whole rest HANGS under the 4th line…* | merged into C17 |
| L26 | Rest shapes separate strongly by aspect ratio, except whole vs half | *(same title)* | merged into C19 |
| L27 | One whole rest fills any bar, in any metre | *A whole rest stands for THE BAR, whatever the meter* | merged into C16 |
| L28 | A whole-bar rest is centred in the bar | *(same title)* | kept standalone |
| L29 | A rest is centred on or about the middle of the staff | *(same title)* | kept standalone |
| L30 | A multi-bar rest is an H-bar one staff space thick | *(same title)* | kept standalone |
| L31 | An augmentation dot goes in a SPACE — above the line if the note is on one | *An augmentation dot sits at the note's own space…* | merged into C50 — ⚠️ **re-filed from *Rests* to *Articulations*** |
| L32 | An accidental stands BEFORE its note, at the same staff position | *(same title)* | kept standalone |
| L33 | An accidental holds to the end of the bar, at that staff position | *An accidental is a SCOPE to the end of the bar…* | merged into C21 |
| L34 | An accidental carries across a barline through a TIE | *An accidental is a SCOPE to the end of the bar…* | merged into C21 |
| L35 | A courtesy accidental is real ink that changes nothing | *A courtesy accidental is real ink that changes nothing — and its frequency is a property of the EDITION* | merged into C26 |
| L36 | The order of sharps and flats in a key signature is fixed | *A key signature's accidentals stand at fixed slots, in a fixed order, keyed on the CLEF* | merged into C22 |
| L37 | Key-signature accidentals occupy fixed staff positions that depend on the clef | *(same)* | merged into C22 |
| L38 | The key signature is reprinted at the start of every system | *The clef and key signature are reprinted at the head of EVERY system* | merged into C25 |
| L39 | Horns, trumpets, timpani and tuned percussion traditionally carry NO key signature | *Timpani, horns and trumpets are conventionally written WITHOUT a key signature* | merged into C81 |
| L40 | At a system's start the order is clef, key signature, time signature | *A key signature stands BETWEEN the clef and the meter* | merged into C23 |
| L41 | A time signature is printed once per movement and NOT repeated per system | *A meter is printed at a movement's START and nowhere else* | merged into C28 |
| L42 | Time-signature numerals fill the staff's height — two staff spaces per digit | *A time signature's placement is RIGID — and its numerals fill the staff's height* | merged into C27 |
| L43 | A time-signature change is placed AFTER the barline | *A mid-staff meter CHANGE is printed at the bar head…* | merged into C33 |
| L44 | A cautionary time signature stands at the END of the previous system, after its last barline | *A cautionary meter printed after a system's FINAL barline governs no bar* | merged into C30 |
| L45 | A double barline precedes a metre change ONLY at a new section | *A double barline is a SECTION mark; a thin-thick barline is a movement END…* | merged into C77 |
| L46 | `C` and cut-`C` are letter meters, and cut-C is measurably taller | *A letter meter (`C`, `¢`) is a complete meter — and the stroke is what separates them* | merged into C31 — **DISAGREEMENT #3** |
| L47 | A tie joins two heads of the SAME pitch and curves away from the stem | *A tie's two ends are at ONE staff position, by definition* | merged into C39 |
| L48 | A slur joins DIFFERENT pitches and is drawn on the notehead side | *A slur is drawn OVER its notes; a hairpin is drawn BETWEEN them* | merged into C35 — **DISAGREEMENT #4** |
| L49 | Where the outer notes have opposite stems, the slur end moves toward the noteheads | *(same title)* | kept standalone |
| L50 | A slur or tie broken by a barline is ONE mark drawn in two pieces | *One printed arc cut by a barline is still ONE arc* | merged into C38 |
| L51 | A slur is narrower than the notes it binds | *A slur's ink stops INSIDE both outer notehead centres* | merged into C36 — ⚠️ **`UNSOURCED` in the literature; this repo supplied the number** |
| L52 | A slur must begin and end in the same voice | *(same title)* | kept standalone (`UNSOURCED`) |
| L53 | Dynamics go BELOW an instrumental staff and ABOVE a vocal one | *A dynamic LETTER stands in its own staff's band, below the bottom line* | merged into C46 |
| L54 | On a grand staff, dynamics go BETWEEN the two staves | *(same title)* | kept standalone |
| L55 | Dynamics are not placed INSIDE the staff | *A hairpin is printed BELOW its staff… — and dynamics are not placed INSIDE the staff* | merged into C45 |
| L56 | A hairpin is a thin line, thinner than a stem | *…a HAIRPIN is connected to NOTHING — and it is thinner than a stem* | merged into C78 |
| L57 | A dynamic letter's ink extends LEFT of its own origin | *A dynamic WORD is a run of adjacent letters (`f`+`f` = `ff`)* | merged into C47 — **the font geometry predicts the repo's IoU 0.317 pair** |
| L58 | An articulation goes on the notehead side, opposite the stem | *A staccato or accent is printed on the notehead side…* | merged into C51 |
| L59 | An articulation above SITS on its position; one below HANGS from it | *(same title)* | kept standalone |
| L60 | A small articulation near the middle line is centred in the next free SPACE | *(same title)* | kept standalone |
| L61 | An articulation is horizontally centred on the notehead | *A staccato or accent is printed on the notehead side… and CENTRED on the head in x* | merged into C51 |
| L62 | A fermata is drawn above the staff by default | *A FERMATA hangs over whatever sounds beneath it…* | merged into C52 (`UNSOURCED` for the "above" half) |
| L63 | Barlines are continuous within each family of instruments | *Interior barlines STOP at instrument-family boundaries* | merged into C58 |
| L64 | A bracket encloses each instrumental family, with sub-brackets inside it | *A bracket encloses a FAMILY, not the system…* | merged into C84 — **DISAGREEMENT #1, against `CLAUDE.md`** |
| L65 | The vertical order of a full score is woodwind, brass, percussion, voices, strings | *SCORE ORDER is a convention strong enough to resolve a label by* | merged into C82 |
| L66 | A tacet staff is SUPPRESSED from a system | *A printed score may OMIT a tacet part; it may never REORDER one* | merged into C62 (`UNSOURCED`) |
| L67 | A part is one instrument, and divisi go on separate staves | *Whether one printed staff label means ONE part or TWO is a property of the ENCODING…* | merged into C67 |
| L68 | A measure number sits at the START of a system, upper left | *Measure numbers are printed at system starts* | merged into C75 |
| L69 | Tempo marks stand above the top staff and above the first violins | *Tempo marks stand above the top staff AND above the first violins* | kept standalone |
| L70 | Instrument names are printed IN FULL on the first system and ABBREVIATED thereafter | *An instrument label is printed in the MARGIN — in FULL on the first system…* | merged into C69 |
| L71 | A running head names the instrument on every page of a part | *(same title)* | kept standalone |
| L72 | Instrument abbreviations are drawn from a short standard set | *The printing TRADITION is a property of the document — and the same abbreviation means different instruments across traditions* | merged into C74 |
| L73 | Performance directions are printed in Italian, English, German or French | *Direction words are printed INSIDE the system, in a conventional language* | merged into C73 |
| L74 | A barline runs from the top staff line to the bottom one | *A barline runs the FULL HEIGHT of its system, and nothing else does* | merged into C56 |
| L75 | A thin barline is 0.16 staff spaces; a thick one is 0.5 | *The only ink crossing a family gap is the SYSTEMIC BARLINE…* | merged into C83 |
| L76 | A final barline is thin then thick; a section barline is thin then thin | *A double barline is a SECTION mark; a thin-thick barline is a movement END…* | merged into C77 |
| L77 | Repeat dots sit in the two middle spaces, flanking the middle line | *Repeat dots are a vertical PAIR in the two middle spaces, adjacent to a barline* | merged into C76 |
| L78 | A dashed barline has a dash twice the length of its gap | *(same title)* | kept standalone |
| L79 | A double barline is a SECTION mark, not a consequence of anything else | *A double barline is a SECTION mark; a thin-thick barline is a movement END…* | merged into C77 |

**Literature tally: 52 merged + 27 standalone = 79** ✅

### Two bookkeeping notes

1. ⚠️ **One entry changed CATEGORY.** `L31` (*An augmentation dot goes in a
   SPACE*) is filed by the literature under **Rests & bar filling** and by this
   repo (`C50`) under **Articulations & ornaments**. The merged entry is filed
   with the marks, and the change is flagged in the entry itself. **No other
   entry crosses a category boundary**, and the per-category counts above are
   computed after that single move.
2. ⚠️ **The four literature entries marked `UNSOURCED — believed true, not
   verified` are carried with that label intact** and are: *A slur is narrower
   than the notes it binds* (`L51`, now MEASURED HERE via `C36` — **the one
   `UNSOURCED` entry this merge closes with a figure**), *A slur must begin and
   end in the same voice* (`L52`, still standalone and unsourced), *A tacet
   staff is SUPPRESSED from a system* (`L66`, now carried inside a MEASURED
   entry but **still unsourced as a stated rule**), and *A fermata is drawn
   above the staff by default* (`L62`, unsourced for the "above" half; its
   GEOMETRY is sourced). **None was promoted on the strength of the merge
   alone.**

---

## How to use this registry

1. **A convention is a hypothesis and a cheap test, never a licence.** Read
   [Conventions that FAILED here](#conventions-that-failed-here) before the body,
   and read the **Known exceptions** row before quoting a **Says** line.
2. **Prefer entries whose "Predicts" is a CONSTRAINT over those whose is a
   prior.** A constraint (*a tie's two ends are at one staff position*) can
   REFUSE a reading; a prior (*stems go down when ambiguous*) can only tilt one.
3. **`Numbers` is where the two halves earn their keep together.** The
   literature usually supplies the default in staff spaces; this repo usually
   supplies what it measures on a plate. **Where they differ, both are printed
   with their documents** — that difference is a finding, not an error to
   resolve.
4. **Never promote `LITERATURE ONLY` to `MEASURED HERE`.** A font default is
   not a measurement of a 19th-century plate, and Scoring Notes measured a **2×
   spread** across shipping applications for something as basic as staff-line
   thickness.
5. **Check `Rigid or publisher-dependent` before building.** Ten repo entries
   and six literature entries lead with a variability warning, and many more
   carry one in **Known exceptions** — the tie interval that is empty on an
   engraving and not on a scan, the beaming rule Gould herself exempts for
   Classical and Romantic plates, the bracket that 2 of 5 held editions do not
   print.
6. **`Code` says whether anything reads it.** A large number of entries here end
   in **no consumer found** — including several the repo has measured. That is
   the registry doing its job: *the value existed and nothing read it* is this
   tree's highest-yield bug class, and this document is a list of the values.




