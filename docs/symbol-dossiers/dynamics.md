# Dynamics — one dossier per symbol

**2026-09-20.** Sean's five questions, asked of every mark in the dynamics
family. Research only: nothing here changes the pipeline, no arm was run, and
the only new numbers come from two tiny reads of files already committed (§0.3).

The family is three different problems wearing one name, and the repo has
measured the split twice. Keep them apart while reading:

| | what it is | how we fail at it |
|---|---|---|
| **the LETTERS** (`f`, `p`, `m`, `s`, `z`, `r`) | drawn music-font glyphs the detector finds well | **precision and placement** — 186 spurious, 73 wrong text, 24% standing in the wrong staff's band |
| **the WORD** (`ff`, `sfz`, `mp`) | an assembly over letters | **assembly** — it produces `ppmsf`, and a doubled letter spells a doubled word |
| **the HAIRPINS** (crescendo, diminuendo) | thin diagonal ink in the band below the staff | **pure recall** — the detector is silent, and a classical-CV reader that is not is OFF by default |

---

## 0. How to read this file

### 0.1 Where each answer comes from

Q4 is answered by reading `tools/omr/staged/` and grepping the quantity, never
from prose. Every figure carries its file and its n. Claims are graded
**MEASURED HERE** / **LITERATURE** / **ASSERTED**.

### 0.2 What the prior documents already settle, cited not re-derived

* **Q1 starts from Sean's own table.**
  [`docs/position-grammar-confusables-2026-09-04.md`](../position-grammar-confusables-2026-09-04.md)
  §2 **WEDGE** (accent vs hairpin — Sean's own example: *note-anchor vs
  span-anchor*, width alone fails) and §2 **BOWL / BLOB** (hollow heads vs
  **letters** vs grace vs specks — the bowl of a *legato* "g" is
  notehead-shaped). Each symbol section below says where it **agrees**,
  **adds**, or **disagrees** with those two entries. Two disagreements are
  recorded, in §7.1 and §10.1.
* **Q3's position fact is already built and graded.**
  [`benchmarks/omr-family-positions-2026-09/FINDINGS.md`](../../benchmarks/omr-family-positions-2026-09/FINDINGS.md),
  `tools/omr/staged/positions.py`, `tools/omr/staged/capture.py`. All three
  dynamics families have a BAND position quantity
  (`Q.DYNAMIC_BAND_POSITION`, `Q.WEDGE_BAND_POSITION`,
  `Q.DIRECTION_BAND_POSITION`), all three are **producers with no consumer**,
  `OMR_FAMILY_POSITIONS` is **default OFF**, and Sean's warning stands: a
  position is rarely a rule by itself. `Q.DYNAMIC_BAND_POSITION →
  adjudicate_glyph_owner` is that document's own **ranked first** next step
  (its §11.1).
* **The engraving conventions** are `[C45+L55]`, `[C46+L53]`, `[C47+L57]`,
  `[C48]`, `[C49]`, `[C78+L56]`, `[L54]` in
  [`docs/engraving-conventions.md`](../engraving-conventions.md) §Dynamics &
  hairpins. Handles are cited rather than restated.
* **`ASSUMPTIONS.md`** carries no `A-` entry for this family. The two that
  govern it are ownership's: **A-OWN-1** (ladder → range veto → distance;
  confidence declared and deliberately unweighted) and **A-OWN-2** (the range
  veto reads position + clef, not a resolved pitch). **D8** records `dynamic`
  and `wedge_anchor` as two of the six original stubs, both since written.
* **`docs/exploration-what-is-on-the-page-2026-09-09.md`** §B1 is the one entry
  that touches this family: a bar with a mark and no events. That bug was live
  and is fixed (`_mxl_directions_only`, 14 dynamics recovered across 5 of 11
  scanned pages) — §9.4.

### 0.3 The two probes used, and what they read

Both are reads of committed files, seconds, no pipeline:

1. `python3 -c` over
   `benchmarks/omr-dynamics-band-2026-09/results.json` → the **per-letter mix**
   in §1.0, which no committed document states. 1,246 letters, 18 pages,
   9 publishers.
2. `from tools.omr.staged import gather_coverage; gather_coverage.ink_present_elsewhere()`
   → the class inventory in §7. It reports **12** detector classes for
   `DYNAMIC_LETTER` and reads **146** class names.

### 0.4 What every dynamic LETTER shares

Each letter section below states only what is different about that letter. The
mechanics are one set and they are these.

**The band.** `[C46+L53]`. Over 1,246 letters on 18 scanned pages of 9
publishers: **73% stand in their own staff's band, 24% in the band of the staff
IMMEDIATELY above — distance exactly 1, 300 of 300, no exceptions — 2.8% in no
band, and 0% below.** The pooled widest empty interval is **−3.04 to −0.52
staff spaces**; the lower edge is a plateau (nothing moves anywhere in −1.5 …
+0.25). MEASURED HERE,
`benchmarks/omr-dynamics-band-2026-09/FINDINGS.md` §2-§4.

**Why the 24% exists.** A measure cell is the staff plus 4 (or 6) staff spaces
of air — `measure_extractor.PAD_ABOVE_STAFF_LINES` — and that air is where the
neighbour prints its dynamics. The letters reach the reader through per-measure
cells; the hairpin reader works in page pixels per staff. **The frame is the
fault, not the glyph.** MEASURED HERE, same file.

**The gate is the wrong fix, and this is the load-bearing negative.** Dropping
out-of-band letters under-emits on both arms (**0.63** engraved, **0.59**
scanned) because a mark whose only surviving detection sits in the neighbour's
cell is deleted rather than moved. Re-attribution instead: engraved staves
exact by word **52 → 83 of 107**, no work worse; **scans 16 → 16, flat.**
MEASURED HERE, same file §4.

**Confidence is refuted as a filter.** To remove 13 of 35 unattributable
letters you discard **140 of 911** good ones; at 0.60 it is 18 of 35 against
233 of 911. MEASURED HERE, same file §5.

**The letters are 91% contested.** On Litolff Beethoven 5 pp.1-4, `dynamic_letter`
carries **420 duplicate pairs** (143 same-cell, 277 cross-staff) over **442 of
485 subjects — 91.1%**, the highest rate of any family (noteheads are 42.4%).
MEASURED HERE, `benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §1.

**A same-cell IoU rule would delete real ink.** The first same-cell pair found
is two `dynamicF` at **IoU 0.317, 21 px apart, both real: the two `f`s of a
printed `ff`**. Over 255 same-cell dynamic pairs the centre offset spreads
72 / 87 / 93 / 3 across `<0.25w` / `0.25–0.5w` / `0.5–0.75w` / `≥0.75w` — the
populations **do not separate**, widest empty interval 0.097, where noteheads
DO separate (405 of 458 under 0.25w). MEASURED HERE, same file §6.1.
LITERATURE explains it exactly: Bravura `dynamicFF` is a single ligature
**2.980** staff spaces wide — wider than two `f`s are apart — and `dynamicForte`'s
bbox starts **0.564 spaces LEFT of its own origin** (`[C47+L57]`).

**A letter is blanked out of the hairpin search.** `hairpin_detection.blank_point_detections`
erases every non-span point detection before the wedge search, so a letter the
detector already found can never become a hairpin candidate. MEASURED HERE
(code), `tools/omr/hairpin_detection.py:237-252`.

**Stage-by-stage, the shared half.**

| stage | what happens to a letter |
|---|---|
| GATHER | `gather_dynamic_letters` (`tools/omr/staged/gather.py:986`) writes one `Q.DYNAMIC_LETTER` row per letter glyph, in **page pixels**, carrying `letter`, `bbox_page_px`, `band_offset_spaces`, `in_hairpin_band`, and the detector's confidence. It filters nothing by band, deliberately. `gather_ownership_evidence` (`:537`) writes the cross-staff contest. `positions.gather_band_positions` (`positions.py:662`) promotes the band offset to `Q.DYNAMIC_BAND_POSITION` — behind `OMR_FAMILY_POSITIONS`, **default OFF**. |
| ADJUDICATE | `adjudicate_dynamic` (`adjudicators/text.py:64`) is the **only** consumer. It queries `Q.GLYPH_OWNER` across the system, keeps a letter only where the owner names this cell's staff **and** it was cut from this staff, then assembles. `adjudicate_glyph_owner` (`adjudicators/ownership.py:50`) decides the contest. |
| EVALUATE | **nothing.** `grep -n 'DYNAMIC' tools/omr/staged/consequences.py tools/omr/staged/evaluate.py` returns no match. |
| INFER | **nothing.** Same grep over `infer.py` and `inferences.py`. |
| EXPORT | `_place_directions` (`staged/export.py:1585`) reads `Q.DYNAMIC` and renders through the legacy `_mxl_direction`. A **narrowed** verdict writes nothing. |

**The letter's ownership contest has no ladder and a pitch veto it should not
have.** `gather_ownership_evidence` writes `Q.GLYPH_LADDER` only where
`det.smufl_name.startswith(_NOTEHEAD_PREFIX)` (`gather.py:632`), so tier 1 is
structurally unavailable to a letter. Tier 2, `_range_veto`
(`ownership.py:148`), has **no category guard**: it converts the band row's
`position_in_candidate` into a pitch through the clef and vetoes the candidate
if that pitch is outside the instrument's written range. A dynamic letter has
no pitch. It does not fire today only because `Q.INSTRUMENT` abstains
`no_evidence` on 75 of 75 staves of the four-page Litolff artefact
(`benchmarks/omr-cleanup-count-2026-09/`, and CLAUDE.md's *measure math*
section). **So a contested letter is decided by DISTANCE alone** — which this
repo has measured being a coin flip for exactly this shape of ink (contested
hairpin copies sat 5–62 px nearer one staff than the other,
`benchmarks/omr-hairpins-2026-09/FINDINGS.md` §6). MEASURED HERE (code +
artefact); the veto's behaviour on a letter is **ASSERTED** — nobody has run it
with an instrument decided.

**The largest false claim on the record belongs to this family.**
`gather_dynamic_letters` writes `ABSTAIN.NO_INK` for a cell that HAD detections
and simply no dynamic among them — **997 firings on Litolff pp.1-4**, the
single biggest contributor to the 2,377 contradicted empty claims, while
`Q.INK` covers all 1,183 cells and its own `no_ink` fires **zero** times. Ten
lines later, `:1079` writes the honest `NO_DETECTIONS` for a cell with no
detections at all — **3 firings**. *The emptier case gets the honest word and
the fuller case gets the overclaiming one.* MEASURED HERE,
`benchmarks/omr-stage-trace-2026-09/FINDINGS.md` §4-§5.

---

## 1. `dynamicF` — the letter `f`

The music-font glyph `f` (SMuFL `dynamicForte`, U+E522), one of the letters a
dynamic word is spelled from. Produced by the YOLO detector, class `dynamicF`
(id 95 in the 208-name catalog) and its coarse twin `dynamicLetterF` (id 192),
renamed at `yolo_detector.py:296`.

### 1.0 Reach

**541 of 1,246** letters over 18 pages of 9 publishers — the second commonest
overall, and the commonest on four of the nine editions (Breitkopf Brahms 111 of
164, Litolff Beethoven 70 of 91, Simrock Dvořák 160 of 234, Jurgenson 1 of 1). MEASURED HERE, probe
over `benchmarks/omr-dynamics-band-2026-09/results.json`.

### 1.1 What sets it apart — and what it is confused with

What sets it apart is that it is **a letter standing in a strip of page outside
the staff**, and nothing else in that strip is letter-shaped except the other
dynamics and a direction word. It is *not* separated by shape from the things
it collides with.

| confused with | where the repo measured it |
|---|---|
| **its own twin across the staff gap** — one printed `f`, detected in two cells | `benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §2a: `cell/1/0/7/0` holds four `dynamicF` at conf 0.852–0.898, two staves (7 and 8), two x positions (899 and 920). **It is one printed `ff`.** **21 of 21** cells carrying a long f/p word hold an overlapping pair. MEASURED HERE |
| **the `f` of a printed word** (`espr.`, `forte`) | `direction_text.py:47` states the mechanism for `p`; the same holds for `f`. The two readers are kept apart by the LEXICON, not by geometry — `direction_lexicon` omits the letter dynamics by name so "the two readers cannot both claim one mark". MEASURED HERE (code), the collision rate is **ASSERTED** |
| **a second `f` that is really the `f` of an `sf`** | the assembly rule cannot tell them apart; see §9 |
| **the neighbouring staff's `f`** through 4–6 spaces of cell padding | 24% of all letters, distance exactly 1 (§0.4) |

**Against `[BOWL / BLOB]`:** that entry lists letters as a confuser *of hollow
noteheads* (the bowl of a *legato* "g"). This family is the same collision seen
from the other side and the repo has never measured it in this direction — how
often a notehead or a fragment is called `dynamicF`. **ASSERTED as an open
gap.**

### 1.2 Best method: YOLO / CV / other

**YOLO, and it works.** The detector is not blind to dynamics; over the nine
publishers it finds 1,246 letters and the documented failure is
*over-eagerness, not blindness* (`benchmarks/omr-dynamics-band-2026-09/FINDINGS.md`
§1). 186 spurious against 244 matched on the 20-row scan gate
(`docs/scope-dynamics-reading-2026-09-09.md` §1).

**OCR is deliberately refused and the refusal is load-bearing.** `direction_text`
runs Surya + Tesseract on every page by default and its own docstring declines
this job: a dynamic `p` and the `p` of `espr.` are the same letter, free text is
gated by a 181-term lexicon, and **a single character has no lexicon to be gated
by** — pointing OCR at one-letter targets removes the only guard that path has.
MEASURED HERE (code), `tools/omr/direction_text.py:47-50`.

**Templates are the untried third method and would dissolve the assembly
problem rather than improve it.** `tools/omr/symbol_library/` holds **38**
rasterised SMuFL templates and **zero** dynamic glyphs, while
`symbol_library/data/glyphnames.json` carries **42** `dynamic*` names —
including the composites `dynamicFF`, `dynamicSforzando`, `dynamicFortePiano`.
A composite template matches `sf` as ONE object. This is exactly the move that
shipped `timeSigCommon`/`timeSigCutCommon`. ⚠️ The risk is publisher type:
a Litolff `3` already matched Bravura's `6`. MEASURED HERE (probe over the
manifest + glyphnames); the *benefit* is **ASSERTED**.
`docs/scope-dynamics-reading-2026-09-09.md` §3.

### 1.3 Where on the page the deciding information lives

Three places, in order of how much they settle:

1. **The band below the staff's bottom line**, in page pixels — `+0.0 … +5.6`
   staff spaces, with a 2.53-space empty interval under it. This says WHICH
   STAFF. `[C46+L53]`.
2. **Its horizontal neighbours** — the letter to its left and right decide what
   word it is part of. A letter alone carries no word. `[C47+L57]`.
3. **Its twin across the staff gap** — the contest row, which says whether this
   `f` is a second piece of ink or a second view of one.

⚠️ **Height carries none of its identity.** A `p` is a `p` at any height; this
is the one thing the clef work does *not* transfer to dynamics
(`benchmarks/omr-dynamics-band-2026-09/FINDINGS.md` §1). So the band is an
ATTRIBUTION fact, never an IDENTITY one — which is Sean's own warning that a
position is rarely a rule by itself, in this family's concrete form.

### 1.4 Stage by stage

See §0.4 for the shared table. What is specific to `f`: nothing in the pipeline
treats it differently from the other five letters. `export._DYNAMIC_LETTER`
maps `dynamicF → "f"` (`tools/omr/export.py:1449`) and
`gather._DYNAMIC_LETTER_CLASSES` admits it (`gather.py:926`).

### 1.5 Abstain or best-guess — and what leans on this letter's certainty

**(a) Can it abstain? At the LETTER level, no — and that is the finding.**
`Q.DYNAMIC_LETTER` is an **observation**, not a decision. `log.observe` files
the detector's class as a fact; there is no adjudicator whose question is *"is
this ink a dynamic letter?"*, so nothing can abstain about it. That is the
stage charter's §3a fault in this family:
[`docs/stage-charter-2026-09-18-what-each-stage-does.md`](../stage-charter-2026-09-18-what-each-stage-does.md).
The only abstention available is `adjudicate_dynamic`'s, and it is about the
CELL, not the letter — plus the false `NO_INK` in §0.4.

**(b) What leans on it.** The WORD (§9) is built entirely out of letters, so an
`f` lost or doubled is a word wrong. The hairpin direction check `[C48]` would
lean on it (measured exact at ±1 measure, 34/34) and **nothing consumes that
today** — no code reads it, confirmed by grep.

**Independence.** The letter reader is the YOLO detector; the hairpin reader is
classical CV over the raster. **Genuinely different readers over the same band**
— which is the rare good case for this repo's *the bars are not an independent
umpire* hazard. But they are NOT independent about where they fail: both go
quiet on the same degraded plate. Two of nine editions illustrate it —
`jurgenson-tchaikovsky1` finds **1 letter on 2 pages**, and the hairpin reader
gives **2 candidates against 17 truth hairpins** on Mahler p3 while giving 44
against 68 on Brahms p2. So the shared failure mode is the PLATE, and neither
reader rescues the other there. MEASURED HERE,
`benchmarks/omr-dynamics-band-2026-09/FINDINGS.md` §2 and
`benchmarks/omr-hairpin-cv-2026-09/FINDINGS.md`.

---

## 2. `dynamicP` — the letter `p`

Same glyph family, the `p` of `p`/`pp`/`mp`/`fp`/`sfp`. Class `dynamicP`
(id 93), coarse twin `dynamicLetterP` (id 190).

### 2.0 Reach

**560 of 1,246 — the commonest dynamic letter in the corpus**, and the
commonest on five of the nine editions (Durand *La Mer* 79 of 104, Novello Elgar
70 of 82, Universal Mahler 1 103 of 171, Peters Mahler 5 144 of 302, Eulenburg
*Scheherazade* 56 of 97). MEASURED HERE,
probe over `benchmarks/omr-dynamics-band-2026-09/results.json`.

### 2.1 What sets it apart — and what it is confused with

`p` is the letter with the **named, measured text collision**:

> *"a dynamic `p` and the `p` of `espr.` are the same letter in the same
> family, so the detector already reads the middle of that word as
> `dynamicP`."* — `docs/scope-dynamics-reading-2026-09-09.md` §3, restating
> `direction_text.py`'s own docstring. MEASURED HERE (code and the reader's
> own statement); **the rate is not measured anywhere.**

That matters more for `p` than for `f` because the words printed in this band
are Italian expression terms, and `p` is the commonest initial in them
(`pizz.`, `poco`, `pesante`, `perdendosi`, `portato`) — the band's own
inhabitants, listed in `[C45+L55]`'s *known exceptions*: *"the band is CROWDED —
it also holds slur and tie arcs and the words `pizz.`, `espr.`, `arco`."*
**ASSERTED** as the reason; the collision itself is measured only as a
mechanism.

Everything else is the shared list (§0.4). The doubling case is visible in the
dedupe numbers: **`pp` 17 → 2** when the duplicate letters are refused, i.e. of
17 exported `pp`, 15 were one printed `p` seen twice.
`benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §4b. MEASURED HERE.

### 2.2 Best method

As §1.2. One addition specific to `p`: because a `p` inside `espr.` is real ink
correctly classed as a `p`-shaped glyph, **no detector improvement removes this
confusion** — it is a grammar question (is this letter in the dynamics row or
inside a word?) and the fact that would settle it, the direction word's own band
offset, exists as `Q.DIRECTION_BAND_POSITION` and **is read by nothing**
(`capture.KNOWN_GAPS`, `UNREAD-POSITION Q.DIRECTION_BAND_POSITION`).
MEASURED HERE (code).

### 2.3 Where the deciding information lives

As §1.3, plus: **the ink to its right.** A `p` followed within a letter-width by
more letters is a word; a `p` alone in the band is a dynamic. That test is the
assembly rule (§9) run for a different purpose, and nothing does it.
**ASSERTED.**

### 2.4 Stage by stage

Identical to §0.4. `export._DYNAMIC_LETTER["dynamicP"] = "p"`.

### 2.5 Abstain, and what leans on it

As §1.5. The one `p`-specific dependency: `p` is the only letter that both
*starts* words (`p`, `pp`, `ppp`, `pppp`) and *ends* them (`fp`, `sfp`), so a
`p` attached to the wrong run changes two words at once. **ASSERTED** — not
measured.

---

## 3. `dynamicM` — the letter `m`

The `m` of `mf` and `mp`. Class `dynamicM` (id 94), twin `dynamicLetterM` (191).

### 3.0 Reach

**67 of 1,246 (5.4%)**, and unevenly: Universal Mahler 1 has 29 of the 67 while
Litolff Beethoven 5 has **none**. MEASURED HERE, probe.

### 3.1 What sets it apart — and what it is confused with

`m` is the letter whose **partial read is unrecoverable**, and that is its one
distinguishing property in this pipeline.

> A lone `s` can only become `sf`, `sfp` or `sfz` — all of which begin `sf` —
> so `sf` is asserted by every candidate. **A lone `m` can become `mf` or `mp`,
> which agree on nothing further, so it stays dropped under every mode.**
> `tools/omr/export.py:1506` `_partial_dynamic_word`. MEASURED HERE (code, and
> the 17-word table it reads).

So `m` is the letter for which the repo's own partial-recovery rule
structurally declines — correctly, because completing it would be a coin flip
between soft and loud.

It also dominates the **unspellable** residue: on the committed Brahms 1 /
Breitkopf transcription, of 20 dropped runs the commonest single shape is
`m` × 3, and `m` appears in `mm`, `mmf`, `fmm`, `pmff`, `ppmsf`, `ppzmf` —
**6 of the 20 dropped runs contain an `m`** against its 5.4% share of letters.
MEASURED HERE, `benchmarks/omr-dynamics-staged-2026-09/FINDINGS.md` §3.

### 3.2 Best method

YOLO, as §1.2, with the note that `m` is where a **composite template** would
pay most: `dynamicMF` and `dynamicMP` are single glyphs in
`glyphnames.json`, and matching them whole removes the ambiguity the letter
cannot resolve. MEASURED HERE (the glyphs exist, probe §0.3); the payoff is
**ASSERTED**.

### 3.3 Where the deciding information lives

**Entirely to its right.** `m` carries no meaning alone. It is the clearest case
in the family of Sean's position-grammar principle: the mark's identity is the
mark next to it, not its own shape.

### 3.4 Stage by stage

As §0.4. The one branch that names it is `_partial_dynamic_word`'s common-prefix
test, which returns `None` for `m` under every `OMR_PARTIAL_DYNAMICS` mode.

### 3.5 Abstain, and what leans on it

**(a)** Yes, and it is the family's best abstention. A cell whose only run is
`m` produces `Ruling.narrow` with candidates `["mf", "mp"]` — *"there is a mark
here and I cannot spell it"*, which is a different answer from *"I saw
nothing"*. `adjudicators/text.py:223-230`. MEASURED HERE (code).

**(b)** Nothing leans on `m` specifically.

---

## 4. `dynamicS` — the letter `s`

The `s` of `sf`, `sfz`, `sfp`. Class `dynamicS` (id 96), twin `dynamicLetterS`
(193).

### 4.0 Reach

**44 of 1,246 (3.5%)**, concentrated: Peters Mahler 5 has 25 of the 44.
MEASURED HERE, probe.

### 4.1 What sets it apart — and what it is confused with

`s` is the letter the **whole partial-dynamics question was built around**, and
the population it names split differently on two corpora — which is itself the
finding.

| corpus | dropped runs | what they are |
|---|---|---|
| 11-page band corpus | 49 letters in 31 runs | **a lone `s` is 15 of 31** — an `sf` whose `f` was never detected |
| committed Brahms 1 / Breitkopf transcription | 49 letters in 20 runs | `s` × 2 only; **15 of 20 are a prefix of NOTHING** — `ppmsf`, `ppzmf`, `pmff` |

MEASURED HERE, `benchmarks/omr-dynamics-band-2026-09/FINDINGS.md` §8 and
`benchmarks/omr-dynamics-staged-2026-09/FINDINGS.md` §3. ⚠️ **Neither is *the*
mix** — the two disagree about the shape of the population, which is why the
partial-export fix was refused rather than tuned.

So a detected `s` is confused with: **an `sf` that lost its `f`** (recoverable,
because every completion agrees on `sf`), and **the `s` of an assembly
failure** (not recoverable, and the majority on one document).

### 4.2 Best method

YOLO finds it. The lever is not detection but **assembly** — and the composite
template `dynamicSforzando` would read `sf` as one object rather than two
letters, one of which is missing. MEASURED HERE (the glyph exists); the payoff
is **ASSERTED**.

### 4.3 Where the deciding information lives

To its right, as `m`'s — but with one difference that is measurable: the
completions of `s` all agree on a second letter, so **the lexicon itself
carries the information the page failed to print legibly.** That is the only
place in this family where a rule can add a letter without guessing.

### 4.4 Stage by stage

As §0.4. `_partial_dynamic_word("s")` returns `"sf"` under `complete` and
`other`, `None` under the default `off`.

**Priced and REFUSED.** Over the 20-row scan gate, re-exporting the arm's own
`.omr.json` files so the transcribe half is byte-identical: `complete`
**+15 edits** (6 rows worse, 14 unchanged, **0 better**), `other` **+30**
(11 worse, 9 unchanged, 0 better). `complete` adds 19 dynamics for +15 edits.
MEASURED HERE, `benchmarks/omr-dynamics-staged-2026-09/FINDINGS.md` §4.

⚠️ **The refusal is about the LEGACY exporter and says so.** *"The recovery is
real ink and the metric will not pay for it in the legacy exporter, which has no
ownership — and the placement fault is exactly what would stop a correctly
recovered `sf` from pairing. It is worth re-pricing on the staged path."*
**That re-pricing has never been done**, and the staged path now HAS ownership.

### 4.5 Abstain, and what leans on it

**(a)** Yes — `narrow` with `["sf", "sfp", "sfz"]`.

**(b)** Nothing leans on it. But note the dedupe arm's result: refusing
duplicate letters took **`sf` 9 → 34**, because *"25 unspellable runs"* became
spellable once the doubled letters were removed
(`benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §4b). **So a large part of
the `s` problem was never a missing `f` — it was a doubled `s`.** MEASURED HERE.

---

## 5. `dynamicZ` — the letter `z`

The `z` of `sfz`, `rfz`, `fz`. Class `dynamicZ` (id 97), twin `dynamicLetterZ`
(194).

### 5.0 Reach

**34 of 1,246 (2.7%)** — the rarest letter that fires at all, and 21 of the 34
are on one edition (Simrock Dvořák 9). Three editions yield none at all:
Litolff Beethoven 5, Universal Mahler 1, Jurgenson Tchaikovsky 1. MEASURED HERE, probe.

### 5.1 What sets it apart — and what it is confused with

`z` is the only dynamic letter that is **always word-final** — every word in the
17 that contains it ends with it (`sfz`, `rfz`, `fz`). So an isolated `z` is
always an assembly failure or a false positive, never a partial read awaiting a
letter to its right. It appears twice in the committed dropped-run census
(`z` × 2 and `pz` × 1). MEASURED HERE (the 17-word table +
`benchmarks/omr-dynamics-staged-2026-09/FINDINGS.md` §3).

Its confusers are the shared list. Nothing in the repo has measured a specific
`z` collision.

### 5.2 Best method

YOLO. **ASSERTED** — no separate measurement exists for `z`.

### 5.3 Where the deciding information lives

To its **left**, uniquely. That asymmetry is recorded nowhere in the code:
`_partial_dynamic_word` tests only PREFIXES (`w.startswith(word)`), so a run
ending in `z` whose head is missing has no rule at all, where a run starting
with `s` does. MEASURED HERE (code, `export.py:1516`). **This is a real
asymmetry in the recovery rule and nobody has named it.**

### 5.4 Stage by stage

As §0.4.

### 5.5 Abstain, and what leans on it

**(a)** A lone `z` is a prefix of nothing, so `_partial_dynamic_word` returns
`None` and `adjudicate_dynamic` narrows with an **empty candidate list**. That
is a `narrow` that says nothing, which is weaker than an abstention. **Worth a
look** — it is the one place in this family where `narrow` and `abstain` may be
the wrong way round.

**(b)** Nothing leans on it.

---

## 6. `dynamicR` — the letter `r`

The `r` of `rf` and `rfz`. Class `dynamicR` (id 98), twin `dynamicLetterR`
(195).

### 6.0 Reach — ZERO

**0 of 1,246 letters across 18 pages of 9 publishers.** `dynamicR` does not
fire once in the entire band corpus. MEASURED HERE, probe over
`benchmarks/omr-dynamics-band-2026-09/results.json`.

### 6.1 What sets it apart — and what it is confused with

It is the one gathered dynamic letter with **no evidence of ever having been
read**. `rf` and `rfz` are in `DYNAMIC_WORDS` and in `_DYNAMIC_ELEMENTS`, so the
exporter would spell them; the letter never arrives.

Two readings, and the repo cannot separate them:

* **the repertoire** — `rf`/`rfz` are rare in the nine works sampled
  (Beethoven uses `rf` and `sf` heavily but Litolff Beethoven 5 pp. sampled here
  show none);
* **the detector** — `r` is a low-contrast lowercase letterform with no
  distinctive bowl or stem, and the class may simply not be learned.

**ASSERTED.** The distinguishing measurement would be one page known to print
`rf`, cropped and looked at.

### 6.2 Best method

Unknown, because reach is zero. ⚠️ **Do not price anything on this symbol
without a page that prints it** — this is the repo's own *a change that moves
nothing because it is inert and one that moves nothing because the page holds
nothing to move are the same number* rule
(`benchmarks/omr-staged-wedge-2026-09/FINDINGS.md` §0).

### 6.3 Where the deciding information lives

As §0.4 by construction. Nothing has ever exercised it.

### 6.4 Stage by stage

`gather._DYNAMIC_LETTER_CLASSES` admits it and
`export._DYNAMIC_LETTER["dynamicR"] = "r"`. Both paths are live and neither has
ever carried a row on any page measured here.

### 6.5 Abstain, and what leans on it

**(a)** As §0.4 — no letter-level decision exists to abstain. **(b)** Nothing
leans on it. ⚠️ With reach zero, a *clean* result from this symbol would be
indistinguishable from a dead instrument.

---

## 7. `dynamicNiente`, `dynamicPiano`, `dynamicMezzo`, `dynamicForte`, `dynamicSforzando`, `dynamicRinforzando` — the composite classes

Six class names for **whole dynamic marks rather than letters** — an `n`
(niente), a complete `p`, `m`, `f`, `sfz`, `rfz`.

### 7.1 What sets them apart — and the finding

⚠️⚠️ **THEY ARE NOT IN THE PRODUCTION VOCABULARY, AND ONE COVERAGE TOOL THINKS
THEY ARE.**

* `data/user-labeled/catalog.yaml` — the 208-name class space the trained
  checkpoint carries, and the one `build_catalog_yaml` caps to the checkpoint's
  `nc` — contains **no class whose name includes `Forte`, `Piano`, `Mezzo`,
  `Sforz`, `Rinf` or `Niente`.** Its dynamics are exactly `dynamicP/M/F/S/Z/R`
  (93-98), `dynamicLetterP/M/F/S/Z/R` (190-195), and the two hairpins (124/125,
  again at 203/204). MEASURED HERE, probe §0.3.
* `tools/omr/training/deepscores_classes.py` holds a **146-name** DSv2 snapshot
  which *does* contain all six, at ids 103-108.
* `tools/omr/staged/gather_coverage.py:_detector_classes()` reads that
  146-name snapshot while its own docstring calls it *"The 208-class space"*.
  Run, `ink_present_elsewhere()["DYNAMIC_LETTER"]` reports **12** detector
  classes — the six real letters **plus** `dynamicforte`, `dynamicmezzo`,
  `dynamicniente`, `dynamicpiano`, `dynamicrinforzando`, `dynamicsforzando`.
  MEASURED HERE, probe §0.3.

So the dynamics coverage report **over-states this family's vocabulary by six
classes that cannot fire, and is blind to the six coarse spellings that can.**
It is the same fault `export_coverage.compare()` was repaired for — an
inventory that is an allow-list — inside the module whose own comment warns
against it.

⚠️ **This is a disagreement with a shipped instrument, not with a document.**
It does not change any measured figure (the six classes fire zero times because
they do not exist), but it means the coverage headline for `DYNAMIC_LETTER` is
not the vocabulary the detector has.

### 7.2 Best method

Moot — the classes do not exist in the shipped model. ⚠️ But **`dynamicNiente`
matters for a different reason**: `n` (niente) is a real mark, it is in
`glyphnames.json` (as `dynamicNiente` and `dynamicNienteForHairpin`), it is not
in `DYNAMIC_WORDS`, and there is no path by which it could reach a file.
**No quantity, no decision, no export.** ASSERTED as a gap; nobody has counted
how often it is printed.

### 7.3 Where the deciding information lives

For `dynamicNienteForHairpin` specifically: **at the closed end of a hairpin**
— a circle at the point of the wedge. That is a relation between two marks and
the record has nowhere to put it.

### 7.4 Stage by stage

**Nothing. No quantity, no adjudicator, no export.** Confirmed:
`grep -rn 'Niente\|dynamicForte\|dynamicSforzando' tools/omr/staged/` returns
nothing.

### 7.5 Abstain, and what leans on it

Neither half applies — there is no decision.

---

## 8. `dynamicLetterP / M / F / S / Z / R` — the coarse twins, ids 190-195

The same six letters under the 208-class space's second, coarser annotation
vocabulary.

### 8.1 What sets them apart

Nothing on the page — they are the identical glyphs. What sets them apart is
that **every consumer in this pipeline was written against the fine spelling**,
so a detection at id 192 was a forte the exporter could not spell: dropped with
no warning anywhere. `tools/omr/class_aliases.py:1-31`. MEASURED HERE (code).

### 8.2 Best method

Not a reading question. It is a **naming** question and it is solved:
`canonicalize_names` renames the coarse block at `yolo_detector.py:296` — the
one place the model's own `names` are read — so every consumer downstream sees
one spelling. `class_aliases.ALIASES` lists the six as exact twins; `unaccounted()`
fails the suite on any class in neither table. MEASURED HERE (code).

### 8.3 Where the information lives

In the weights file's `names` map, not on the page.

### 8.4 Stage by stage

The rename happens **before GATHER**, so `gather._DYNAMIC_LETTER_CLASSES` lists
only the fine six and says so in its own comment: *"Listing both would not be
harmless duplication, it would hide a regression in that renaming"*
(`gather.py:919-925`). MEASURED HERE.

### 8.5 Abstain, and what leans on it

⚠️ **It costs nothing today and that is not a reason to leave it.** Measured
2026-09-04 on three engraved fixtures and a scanned Brahms page (1,517
detections): the coarse block fires **zero** times. What makes it live is the
LABELING side — **26** hollow-campaign hand-drawn boxes are classed
`dynamicLetterF/P/S`, and `catalog.yaml` carries the coarse spelling at 190-195,
so the next fine-tune trains ids the pipeline could not read without the rename.
MEASURED HERE, `class_aliases.py:16-23`.

---

## 9. The dynamic WORD — `Q.DYNAMIC` (`ff`, `sfz`, `mp`, …)

Not a glyph. An **assembly over letters**, and the only thing in this family
with a real adjudicator. 17 words: `p pp ppp pppp f ff fff ffff mp mf sf sfz
fp rf rfz sfp fz` (`adjudicators/text.py:14-18`, mirrored at
`export.py:1454`).

### 9.0 Reach

| document | letters | words written |
|---|--:|--:|
| Litolff Beethoven 5 pp.1-4, 2026-09-17 artefact | **485** | **205** `<dynamics>` |
| Breitkopf Brahms 1 pp.0-3 | **531** | — |

MEASURED HERE, `benchmarks/omr-cleanup-count-2026-09/out/coverage-p1-p4-2026-09-17.json`
and `benchmarks/omr-family-positions-2026-09/FINDINGS.md` §5.

⚠️ **Read `decided` with care in that artefact: it is 1,175 and the page has
1,183 cells.** `adjudicate_dynamic`'s subjects are CELLS, not marks, so
`decided` counts bars asked, not dynamics found. `abstained: {unspellable: 8}`
completes the partition. A reader taking 1,175 for a count of dynamics would be
out by a factor of six.

### 9.1 What sets it apart — and what it is confused with

The word is confused with **itself doubled**. That is the family's headline
defect and it is Sean's own observation — *"the score has only `ff` all the way
down and ours has extra `f`s"*.

The mechanism, named rather than counted: `adjudicate_dynamic` honoured
ownership by **keeping** every letter the owner was handed, and both members of
a cross-staff contest name the same owner — so one printed `ff` arrived on one
staff as four `dynamicF` and assembled as `ffff`. MEASURED HERE,
`benchmarks/omr-staged-dedupe-2026-09/FINDINGS.md` §2a.

Refusing the duplicate (`A.is_relocated_copy`), over the same record, control
**1,148 of 1,148** verdicts reproduced before either arm is read, **155 letters
refused**:

| word | base | fix |
|---|--:|--:|
| `ffff` | **11** | **2** |
| `fff` | 10 | 8 |
| `pp` | 17 | **2** |
| `ppp` | 1 | 0 |
| `sf` | 9 | **34** |
| `f` | 63 | 77 |
| `p` | 15 | 31 |
| **`ff`** | **47** | **39** |

⚠️⚠️ **`ff` 47 → 39 is an UNADJUDICATED COST, not a win.** Eight words left that
spelling and the record supports both readings: one printed `f` detected twice
(the repair is right), or a real `ff` whose second letter this staff saw once
(the repair cost a mark). **Only the print can say, and nobody has looked.** 8
things a human might have to put back. MEASURED HERE, same file §4b.

The second confuser is the **assembly failure**: `ppmsf`, `ppzmf`, `pmff` —
five letters run together, which no dynamic is. 15 of 20 dropped runs on the
committed Brahms transcription are a prefix of nothing. Re-assembling on the
MEDIAN letter width instead of the max is **not** the lever (kept runs
159 → 162, dropped still 20, `ppmsf` intact). MEASURED HERE,
`benchmarks/omr-dynamics-staged-2026-09/FINDINGS.md` §3.

### 9.2 Best method

Not a detector question at all. Three candidate methods, ranked by what is
measured:

1. **The ownership contest** — shipped, and it moved the numbers above. It is
   the right shape because the fault is *two views of one mark*, not a
   threshold.
2. **Composite templates** — `dynamicFF`, `dynamicMF`, `dynamicPP`,
   `dynamicSforzando` exist in `glyphnames.json` and would match a word as ONE
   object, which dissolves assembly rather than improving it. Untried;
   `symbol_library/` has 38 templates and none of them dynamic (probe §0.3).
3. **A vertical spread test** — every run already carries `band_offsets` and
   `band_offset_spread`, on the stated ground that *"the letters of one word sit
   at one height, so a spread here is the signature of a run joined across two
   marks — the `ppmsf` shape"*. **Recorded, not used; no constant asserted
   because none has been measured.** `adjudicators/text.py:245-248`. MEASURED
   HERE (code). This is the cheapest of the three and the only one that needs no
   new reader.

### 9.3 Where the deciding information lives

**Horizontal adjacency in page pixels** — a gap of at most one max-letter-width,
with the letters level within the same width (`adjudicators/text.py:200-208`).
⚠️ And the LITERATURE says why the naive version misbehaves: a dynamic glyph's
bbox is not centred on its placement point and is not even entirely right of it
(`dynamicForte` SW x = **−0.564** spaces), so x-adjacency gets the spacing wrong
and a box-overlap test reports overlap where the letters are separate
(`[C47+L57]`).

### 9.4 Stage by stage

**GATHER** — `Q.DYNAMIC_LETTER` (§0.4). ⚠️ **Every cell gets a row, including
one with no letter in it**, and that is load-bearing: a decision's subjects come
from the rows in the log, so a staff carrying no letter of its own would have no
`Q.DYNAMIC` subject and a letter ownership moves onto it would be silently
lost. `gather.py:1008-1015`.

**ADJUDICATE** — `adjudicate_dynamic`, `Kind.CELL`, `Mode.ADDITIVE`,
`composed_from=(Q.DYNAMIC_LETTER, Q.GLYPH_OWNER)`. Reasons: `spelled`,
`unspellable`, `no_letters`, `no_page_frame`, `owned_elsewhere`,
`reader_unavailable`. Two drops are reported APART — `letters_moved_out` and
`letters_dropped_as_duplicate` — *because only the second is redundant*.
An unspellable run is `Ruling.narrow`, not `abstain`.

**EVALUATE** — nothing. **INFER** — nothing.

**EXPORT** — `_place_directions` (`staged/export.py:1585`). A narrowed verdict
writes nothing; ownership is **not** re-asked, because the cell the verdict is
filed on is already the answer. Marks go at the **head of the bar**, a DECLARED
simplification: the marks carry a PAGE x and the noteheads a CANONICAL one, and
comparing them is the frame error that made `Q.ONSET_COLUMN` report 1,062
columns of nothing.

⚠️ **The one bug this family used to have in EXPORT is fixed.** A measure with
no detected events took the whole-measure-rest branch, which never called the
only `<direction>` emitter — so `measure_directions()` was computed, assigned
and discarded. **14 marks on 5 of 11 scanned pages**, attribution exact (*words
formed − words in an eventless measure == words exported*, on all eleven pages
to the mark). Fixed 2026-09-04, `_mxl_directions_only`, called from both MusicXML
emitters with a source-level anti-drift test. ⚠️ It made scan OMR-NED slightly
worse and shipped anyway. MEASURED HERE,
`benchmarks/omr-dynamics-band-2026-09/FINDINGS.md` §8.

⚠️ **The LilyPond exporter never calls `measure_directions` at all**, so it drops
dynamics on *every* measure. A wider gap, invisible to `export_coverage` because
that compares MusicXML.

⚠️ A stale comment: `export.py:1453` says *"Only words MusicXML has an element
for. `sf`/`sfz`/`fp` are `<other-dynamics>`"* — but `_DYNAMIC_ELEMENTS` two
lines below includes all three and `_mxl_direction` emits `<sf/>`. Harmless, and
worth not believing.

### 9.5 Abstain, and what leans on it

**(a) Yes, and it is the best-articulated abstention in the family.** Four
distinguishable outcomes:

| outcome | means |
|---|---|
| `Ruling(value=[...], reason="spelled")` | these words are here |
| `Ruling(value=[], reason="no_letters")` | **a decision**: this bar carries none |
| `Ruling.narrow(candidates, "unspellable")` | a mark is here and I cannot spell it |
| `Ruling.abstain(READER_UNAVAILABLE)` | no reader ran |

The `no_letters` / `reader_unavailable` split is the ABSENT/DECLINED distinction
at the one place it decides something (`adjudicators/text.py:136-146`). ⚠️ But
the three-state discipline is **undone one stage earlier** by the false
`NO_INK` (§0.4): 997 cells report *"no ink"* where `Q.INK` shows ink. So the
decision's careful abstention rests on a gatherer's overclaim.

**(b) What leans on the word.**

* **The hairpin's direction** would, via `[C48]` — exact at ±1 measure (34/34),
  wrong 31.8% at ±4, reach 5.0% → 19.3% across that widening, measured on
  Brahms 1's 683 encoded hairpins. **Additive evidence over ~5% of hairpins,
  never a veto**, and `cresc.` into a subito `p` is why the window may not
  loosen. **No consumer exists** — `grep` finds none. MEASURED HERE,
  `benchmarks/omr-dynamics-coupling-2026-09/probe_letter_wedge_coupling.py`.
* **A hairpin's ANCHOR** could: **67% of hairpins have a dynamic at at least one
  end** (40.8% one end, 13.5% both, at ±2), and a letter in the same band at the
  same y is a better anchor than a notehead — which is the thing
  `_wedge_anchors` currently guesses badly. **Unmeasured as a fix.**
  `docs/scope-dynamics-reading-2026-09-09.md` §5b.

**Independence.** The word's evidence chain is letters → ownership → assembly,
and **every link is the same detector on the same raster**. The hairpin's is a
different reader. So letters and hairpins are the one genuinely independent pair
in this family — and §1.5's caveat applies: independent about *method*,
correlated through the *plate*.

---

## 10. `dynamicCrescendoHairpin` — the crescendo wedge

A thin `<` opening left-to-right, in the band below the staff. **Two readers
produce it**, and they are not interchangeable:

| reader | how | what it finds |
|---|---|---|
| YOLO, class `dynamicCrescendoHairpin` (ids 124 and 203) | a box in a measure cell | **~nothing on a scan** |
| `hairpin_detection.detect_hairpins`, `READERS.CV_HAIRPINS` | classical CV over the page band, page pixels per staff | most of them |

### 10.0 Reach — and the two readers' gap is the family's headline

| pool | truth | YOLO | CV |
|---|--:|--:|--:|
| 11 scanned pages, hand-verified windows | 99 `<wedge>` | **1** | **59** |
| 20-row scan gate | 192 | **3** | **96** |
| 11 engraved works, exact page truth (n=3 pages) | — | reading F1 **1.000** | — |
| Litolff Beethoven 5 pp.1-4, 2026-09-17 | — | **0** detector rows | **1** CV row |
| Breitkopf Brahms 1 pp.0-3 | — | **1** detector row | **46** CV rows |

MEASURED HERE: `tools/omr/hairpin_detection.py:1-45`;
`benchmarks/omr-hairpin-cv-2026-09/FINDINGS.md`;
`benchmarks/omr-cleanup-count-2026-09/out/coverage-p1-p4-2026-09-17.json`;
`benchmarks/omr-staged-wedge-2026-09/FINDINGS.md` §0 and §8.

⚠️ **Reach is PAGE-dependent, not only publisher-dependent.** Mahler p3 gives
**2 candidates against 17 truth hairpins**; Brahms p2 gives 44 against 68.

### 10.1 What sets it apart — and what it is confused with

**Start from `[WEDGE]`**, Sean's own entry: *an accent is notehead-scale and
anchored to one head; a hairpin is span-anchored, lives in the dynamics band,
covers two or more note onsets, and usually travels with a partner wedge or a
dynamic letter. Width alone fails — one-beat hairpins exist.*

**Where this dossier agrees:** the band membership and the span-anchor framing
are both built and both correct — `hairpin_detection` searches the band and
nothing else, and 8 of 8 hairpins in the engraved page truth sit below a staff
with none inside one (`[C45+L55]`).

**Where it ADDS:** the discriminator that actually ships is **not** span-anchor.
It is **isolation** — Sean's other rule, in `[C78+L56]`: *a beam joins stems, a
slur meets noteheads, a barline meets staff lines; a hairpin touches nothing.*
Measured on Brahms 1 p2's band components, full-page component area ÷ candidate
area: **p25 1.0×, p50 1.0×, p75 3248×, p90 9167×. Nothing lies between 1× and
3248×.** That is a **binary, not a threshold**. Combined with a per-column open
extent, **471 band components → 69 candidates against ~68 hairpins on the
page.** MEASURED HERE, `benchmarks/omr-hairpin-cv-2026-09/FINDINGS.md`.

⚠️ **Where it DISAGREES with `[WEDGE]`.** *Accent vs hairpin* is the entry's
named confusion, and it was measured and **REFUTED on this corpus**:

* Across the 20-row gate, **1 of 96** CV hairpins has an accent within 1.25
  staff spaces on its own staff — **and it is a crescendo, 3.51 spaces wide**.
  **Zero of 43 diminuendo-classed hairpins coincide with any accent.**
* On Dvořák p7, where the damage concentrates: 28 accents detected (the test is
  live, not vacuous), **0 of 23 CV hairpins near one** — nearest distances
  7.7–120 staff spaces.
* Sizes: accents 1.19–2.46 spaces wide (median 2.27); non-coincident hairpins
  0.81–29.83 (median 5.24). 13 of 96 hairpins are under 3.0 spaces — an
  accent-scale *shape* population — **but none of them sits where an accent is.**
* There is a **mechanistic** reason: `blank_point_detections` erases every
  point detection, accents included, before the search runs — so an accent the
  detector already called correctly **cannot survive into a hairpin candidate.**

MEASURED HERE, `benchmarks/omr-hairpin-cv-2026-09/ACCENT_CONFUSION.md`.

**So the confusion `[WEDGE]` names is structurally blocked for any accent the
detector sees, and is unmeasured for accents it does not.** The reader's real
confusers, in the order the measurements found them:

| confused with | evidence |
|---|---|
| **a beam** | the isolation gate exists for it; without the gate, extent alone leaves **302 of 312** band components (~68 real hairpins) |
| **a slur or tie arc in the band** | the outline-straightness test: a slur is one curved stroke so neither outline fits a line (`MAX_OUTLINE_RMS_SPACES = 0.10`) |
| **a staff line** | LITERATURE: `hairpinThickness` **0.16** against `staffLineThickness` **0.13** — *"on a staff-line-erased image a hairpin can be erased with the lines if the erasure is at all aggressive"* (`[C78+L56]`) |
| **a barline / stem** | the same thin-stroke family; `stemThickness` 0.12 |
| **the neighbouring staff's hairpin** | for the YOLO reader only: 3 of Mahler 5's 4 detections filed under staff 18 while standing in staff 17's band, and the contested copies were only **5–62 px** nearer one staff than the other |
| **whatever the fill-ratio test would have kept** | REFUTED: fill runs p10 0.375, median 0.437, p90 0.737 — nothing survives below 0.35 |

### 10.2 Best method: **classical CV, decisively**

This is the clearest Q2 answer in the whole family and it has two independent
arguments.

**Structural.** A hairpin is a thin, long, diagonal line — the shape Phase 4f
moved stems and beams out of the detector for, on the stated ground that YOLO
bounding boxes are structurally bad at thin lines. *Hairpins are the member of
that family that was left behind.* MEASURED HERE,
`tools/omr/hairpin_detection.py:1-10`; LITERATURE for the thickness
(`[C78+L56]`).

**Empirical.** 1 against 59, and 3 against 96, on the same pages.

⚠️ **And the CV reader's gate was re-run before its call site was added and it
reproduces**: 62 found on a fresh 600 dpi render, 57 on `PageImage.binary`,
against the original 59 — *the near-miss needs no excuse, 59 lies BETWEEN the
two arms.* The pipeline reads the second recipe because it is already rendered,
already deskewed, and already the frame every `bbox_page_px` is in.

**And attribution is right BY CONSTRUCTION**, which is the property the letters
lack: the CV reader searches one staff's band at a time in page pixels, so it
never inherits the cell padding and never needs the distance arbitration.
*The hairpin reader's band discipline is the fix for the letters' placement
problem — hairpins help letters, not the other way round.*
`docs/scope-dynamics-reading-2026-09-09.md` §5b.

### 10.3 Where on the page the deciding information lives

Four places, and the ranking is measured:

1. **The whole page** — for isolation. It MUST be the whole page: the band crop
   severs a beam from its stems and makes it look as isolated as a hairpin.
2. **The band**, `BAND_TOP_SPACES = 0.3` to `BAND_BOTTOM_SPACES = 6.0` below the
   staff's bottom line, floored at the next staff's top − 0.3 spaces. This
   BOUNDS the search; ⚠️ *it does not identify the mark* — the band also holds
   arcs and the words `pizz.`, `espr.`, `arco` (`[C45+L55]` known exceptions).
3. **The component's own outlines** — per-column open extent for the opening,
   straightness for the arms.
4. **Which end is wider** — `measure_component` compares the mean extent of the
   first and last quarter of columns: *"crescendo opens to the RIGHT"*
   (`hairpin_detection.py:143-151`). **This is the entire direction call**, and
   it is one comparison of two means with no tie-break and no abstention.

⚠️ **Q3 note, per `benchmarks/omr-family-positions-2026-09/FINDINGS.md`:**
`Q.WEDGE_BAND_POSITION` exists, is PROMOTED for the CV rung and newly MEASURED
for the detector rung (which never carried a position at all), and
`adjudicate_wedge_anchor` **does not read it** (`capture.KNOWN_GAPS`,
`UNREAD-POSITION Q.WEDGE_BAND_POSITION`). It is a producer with no consumer,
behind a flag that is default OFF.

### 10.4 Stage by stage

**GATHER** — `gather_wedge_boxes` (`gather.py:1093`) writes `Q.WEDGE_BOX` from
**both** readers, tagged by reader.

⚠️⚠️ **THE CV RUNG IS GATHERED WHATEVER `OMR_CV_HAIRPINS` SAYS** (`gather.py:1107`).
That flag guards what the LEGACY exporter does; the staged record has hairpins
either way. **So the staged path is not blocked on the flag and the legacy path
is.** MEASURED HERE (code, and `transcribe.py:3275` where the flag is read,
default `"0"`).

Three abstention states, all real: `READER_UNAVAILABLE` (no raster or no staff
geometry), `READER_UNAVAILABLE` with the exception name (the rung threw), and
`NO_INK` filed **per staff** for a staff the reader ran over and found nothing
under — *"the `0 spurious` half of the ledger's reading, and a consumer that
cannot tell it from 'the rung never ran' cannot tell silence from blindness"*.

⚠️ And the reader **asserts its input polarity** rather than trusting it,
because the wrong polarity does not crash — it searches the paper and reports a
clean zero.

**ADJUDICATE** — `adjudicate_wedge_anchor` (`adjudicators/ownership.py:850`),
`Kind.GLYPH`, `subjects_from=Q.WEDGE_BOX`,
`wants=(Q.WEDGE_BOX, Q.GLYPH_BOX, Q.GLYPH_OWNER, Q.VOICES)`. Reasons:
`nearest_either_side`, `no_anchor`, `no_page_frame`, `no_evidence`.

The rule is `export._wedge_anchors_from_candidates`, **imported and called, not
ported** — the legacy function was SPLIT so its three measured constants
(`_WEDGE_ANCHOR_PAD_NOTEHEADS = 0.25`, `_WEDGE_START_RULE = "nearest"`,
`_WEDGE_STOP_REACH_NOTEHEADS = 1.0`) exist in one place. Brahms pp.0-3: **46
decided, 1 abstained `no_page_frame`** — exactly the detector's box-less row.

⚠️ **Its ORDER position was wrong and no test could have found it.** Placed
beside `fermata_owner` and `ornament_owner` it ran BEFORE `Q.VOICES` and read
`None` every time; *"one voice"* and *"voices unknown"* give the same answer on
every one-voice fixture in the suite. `inventory --check` found it by comparing
`wants` against `ORDER`. Price of the repair, measured: **29 of 46** hairpins
now have their `Q.VOICES` read — *it is not shown that any answer changed.*
`benchmarks/omr-staged-wedge-2026-09/FINDINGS.md` §4.

**EVALUATE / INFER** — nothing.

**EXPORT** — `_place_wedges` (`staged/export.py:1184`). Brahms pp.0-3:
`<wedge>` **0 → 20**, music21 reads back exactly 20 (16 crescendo, 4
diminuendo), 13 binding two notes and 7 binding one, the file byte-identical
outside the `<wedge>` elements. `wedge_balance` is an **EQUALITY**:
20 written + 26 not = 46 decided.

⚠️ **26 of 46 decided hairpins lost an anchor `_place_notes` never wrote** — 10
with neither end written (`wedge_neither_anchor_written`), 16 with one
(`wedge_anchor_note_not_written`). **Those are READING figures, not export
ones**, the same shape as *76% of merged arcs bind fewer than two noteheads*.
On Litolff pp.1-4 it is the whole story: 1 decided, **0 written**, the single
`wedge_neither_anchor_written`.

⚠️ **A structural asymmetry worth naming.** The LEGACY candidate set is
`_measure_noteheads`, which requires `pitch is not None` **and**
`duration_beats is not None` (`export.py:2583-2587`); the STAGED candidate set
is every `Q.GLYPH_BOX` row with `category == "notehead"` and a page box
(`ownership.py:940-960`). So the staged decision can anchor onto a note the
exporter will never write — which is precisely the 26. **The two paths
disagree about what a candidate is, and nothing says so anywhere.** MEASURED
HERE (code).

### 10.5 Abstain, and what leans on it

**(a) Yes, richly, and one of the abstentions is measured to be exactly right.**
`no_page_frame` fires on 1 row of 47 — exactly the detector's box-less row —
rather than falling back to the cell frame, because two staves' canonical frames
coincide by construction. That is a consumer **declining rather than guessing**.

⚠️ **But the DIRECTION cannot abstain at all.** `measure_component` returns
`"crescendo" if right > left else "diminuendo"` — no margin, no tie, no
`None`. A wedge whose two ends measure equally becomes a diminuendo. There is no
`Q` for the direction's confidence and no branch that says *cannot tell*.
**Given that `wrong diminuendo` is where the CV reader's cost concentrates on
Dvořák p7 and accent confusion is refuted as the explanation, this is a live
candidate the repo has not opened.** MEASURED HERE (code);
the causal claim is **ASSERTED**.

**(b) What leans on the hairpin.** Almost nothing — which is itself the answer.
No other mark's reading depends on a wedge today. The two proposed dependencies
both run the other way (the letters corroborate the wedge, §9.5).

**Independence — and the hairpin's second witness is a genuinely independent
one.** The direction check `[C48]` reads the LETTERS (YOLO) while the wedge is
read by CV. That is the rare pairing that survives this repo's *a second witness
must not come off the same raster* rule in spirit if not in letter: same raster,
**different reader and different failure mode**. `groups.py`'s ancestor-closure
would admit it as corroboration rather than collapsing it to `SINGLE`
(`docs/scope-dynamics-reading-2026-09-09.md` §5b). ⚠️ It is still not built.

**And the anchor's dependency is NOT independent.** `adjudicate_wedge_anchor`
needs noteheads this staff owns in the bar or either neighbour; on the pages
where the hairpin reading is hardest the notehead reading is also hardest, so
the anchor falls silent with it. 26 of 46 on the one document with reach.

---

## 11. `dynamicDiminuendoHairpin` — the diminuendo wedge

The mirror mark: `>` closing left-to-right. Same two readers, same quantity,
same decision.

### 11.0 Reach

Brahms 1 pp.0-3: **16 of 46** decided wedges are diminuendo (30 crescendo).
Across the 20-row scan gate, **43 of 96** CV hairpins are diminuendo-classed.
MEASURED HERE, `benchmarks/omr-staged-wedge-2026-09/FINDINGS.md` §8 and
`benchmarks/omr-hairpin-cv-2026-09/ACCENT_CONFUSION.md`.

### 11.1 What sets it apart — and what it is confused with

**Only one thing separates it from the crescendo, and it is one comparison:**
whether the first quarter of columns is wider than the last
(`hairpin_detection.py:143-151`). Everything else in the reader — the band, the
open extent, the straightness, the isolation — is symmetric.

So its confusers are the crescendo's (§10.1) **plus the crescendo itself**, and
that extra confusion has a measured shadow:

⚠️ **`wrong diminuendo` is where the CV reader's cost concentrates and the
obvious explanation was refuted.** Sean's hypothesis was accent confusion;
**zero of 43 diminuendo-classed hairpins coincide with any accent**, and on
Dvořák p7 — the row where the damage concentrates — 28 accents are detected and
0 of 23 CV hairpins sit near one. The write-up names two surviving candidates
and does not distinguish them: **(a) the direction call read backwards on that
page's ink**, or **(b) a correctly-classified diminuendo anchored to the wrong
note pair** — which musicdiff charges identically. MEASURED HERE (the
refutation); the two candidates are **open**.
`benchmarks/omr-hairpin-cv-2026-09/ACCENT_CONFUSION.md`, "What this leaves open".

⚠️ A second asymmetry, engraving rather than code: a diminuendo's **closed end
is on the right**, where the next bar's first note stands. A crescendo's closed
end is on the left, at the note it opens from. The anchor rule treats the two
edges symmetrically (`nearest` on the left, `stop reach` on the right) and does
**not** know which end is the apex. **ASSERTED** — nothing measures whether that
costs anything.

### 11.2 Best method

Classical CV, exactly as §10.2 — the reader is one function and finds both kinds
in the same pass.

⚠️ One method note specific to this mark: **a bounding box is identical for a
crescendo and a diminuendo.** `capture.KNOWN_GAPS`'s
`UNREAD-POSITION Q.ARC_POSITION` makes the same point for arcs — *"a bounding
box is identical for an arc opening up and one opening down, so which end is an
END and which the APEX needs the ink"*. For the wedge the ink IS read (the
column extents), but the answer is a single boolean with no recorded margin.
**So a detector box can never settle direction, and the CV reader settles it
without saying how confident it is.** MEASURED HERE (code).

### 11.3 Where the deciding information lives

As §10.3, with the direction fact isolated: **the mean vertical extent of the
first quarter of columns against the last.** That is the only measurement that
distinguishes this symbol from §10, and it is not stored on the record — only
`open_spaces` and `outline_rms_spaces` travel on the `Q.WEDGE_BOX` row
(`gather.py:1212-1222`). **The direction's own evidence is computed and
discarded**, the shape this repo names *the value existed and nothing read it* —
here, *the value existed and nothing kept it.*

### 11.4 Stage by stage

Identical to §10.4 — one quantity, one decision, one emission. The `kind` rides
on the `Q.WEDGE_BOX` row's value and the exporter refuses a verdict whose detail
names neither kind (`wedge_verdict_names_no_kind`).

⚠️ **The element ORDER is the pairing, not a style**: music21 binds a
`crescendo`/`diminuendo` to the next note it parses and a `stop` to the last, so
the opening mark goes BEFORE its event and the stop AFTER — *and no count would
notice* a mistake. The test asserts the element SEQUENCE.

### 11.5 Abstain, and what leans on it

**(a)** The ANCHOR can abstain (four reasons). **The KIND cannot** — see §10.5.
This is the one symbol in the family where the distinguishing fact is decided by
a rule with no abstention branch.

**(b)** Nothing leans on it. `[C48]` would, and does not exist in code.

---

## 12. The text dynamic — `cresc.`, `dim.`, `forte` spelled out

Not a glyph in the class space at all. A **word**, read by OCR, exported as
`<words>`. Cross-reference: the text/direction dossier owns this; what follows
is only where it touches dynamics.

### 12.1 What sets it apart — and what it is confused with

It is confused with **the letter dynamics**, in both directions, and the repo
keeps them apart by a rule rather than by geometry:

* `direction_lexicon._DYNAMIC_WORD` lists `crescendo cresc decrescendo decresc
  diminuendo dim rinforzando rinf forte piano fortissimo pianissimo mezzo
  sforzando smorz` — and its own comment says the letter dynamics are
  **deliberately absent** *"so the two readers cannot both claim one mark"*.
  MEASURED HERE, `tools/omr/direction_lexicon.py:92-99`.
* The detector reads the `p` of `espr.` as `dynamicP` (§2.1), so the collision
  is live in the other direction and is **not** gated.

### 12.2 Best method

OCR, gated by the 181-term lexicon — and CLAUDE.md records the gate as
load-bearing and never to be loosened. ⚠️ A `cresc.` is *also* a hairpin's
verbal form, so a page using words rather than wedges produces `<words>` where
the truth has `<wedge>`, and musicdiff scores those as different KINDS
(`export.py:1625-1628`). **Nothing converts one to the other**, in either
direction. ASSERTED as a gap — unmeasured.

### 12.3 Where the deciding information lives

**The same band**, which is the whole point:
`Q.DIRECTION_BAND_POSITION` exists *"to separate a `cresc.` standing in the
dynamics row from an `Allegro con brio` printed clear above the system, which
`placement` cannot"* — and it is **read by nothing**
(`capture.KNOWN_GAPS`, `reach.KNOWN_GAPS`). It is the only one of the three band
quantities that is genuinely NEW rather than promoted, because a direction word
has **no detector row at all** (`capture.py` grades the family `shape: NO`).
MEASURED HERE (code).

### 12.4 Stage by stage

**GATHER** — `gather_direction_words` (`gather.py:2951`) writes `Q.DIRECTION_WORD`
carrying `text`, `category` (`tempo`/`expression`/**`dynamic`**), `placement`,
`x_page`, and which rung won.

**ADJUDICATE** — `adjudicate_direction` (`adjudicators/text.py:272`). It carries
`category` into the verdict detail and **nothing routes a `category == "dynamic"`
word anywhere different**: `Ruling(value=[w["text"] …])` and the exporter writes
`<words>`. So a spelled-out `forte` and an `Allegro` take the identical path.
MEASURED HERE (code). **A finding: the one field that would connect the text
dynamics to the dynamics family is recorded, carried into the verdict, and
never branched on.**

**EXPORT** — `_place_direction_words` (`staged/export.py:1647`), at the head of
the bar, through the same `_mxl_direction` with `kind="words"`.

⚠️ **Reach is dominated by whether an OCR rung exists.** On the four-page Litolff
artefact the family reads `ink_rows: 0` and `abstained: {out_of_scope: 1183}` —
every cell, because the rung was off on that run. Where the rungs are live:
Litolff pp.1-3 **42 candidates → 2 accepted**; Brahms pp.0-3 **56 → 10**.
MEASURED HERE,
`benchmarks/omr-cleanup-count-2026-09/out/coverage-p1-p4-2026-09-17.json` and
`benchmarks/omr-staged-direction-2026-09/FINDINGS.md`.

### 12.5 Abstain, and what leans on it

**(a) Yes, and this family's state machine is the product.** `READER_UNAVAILABLE`
and `OUT_OF_SCOPE` are ABSTENTIONS; `NO_INK` and `NO_READING`/`NOT_IN_LEXICON`
are a **DECISION with an empty value**, because *"this bar carries no words"* is a
definite answer. `ABSTAIN.NO_READING` is its own vocabulary word because Surya
*"either reads a crop or says nothing"* (53 of 74 crops silent on one page) while
Tesseract read 72 of 74 and the lexicon refused most — **folding the two hides
which rung is the limit.**

**(b)** A `cresc.` would corroborate a crescendo hairpin — `[C48]`'s coupling
generalised to words. Not built, not measured.

---

## What we do not know

1. **Accuracy of anything in this family.** No dynamic and no hairpin has ever
   been checked against the print. The `ff` 47 → 39 is eight unadjudicated
   words; the 20 exported `<wedge>` on Brahms have never been looked at.
2. **Whether the hairpin direction call is ever wrong**, and if so how often.
   Accent confusion is refuted; the two surviving candidates on Dvořák p7 have
   not been separated.
3. **How often a non-dynamic glyph is called a dynamic letter.** The
   `[BOWL / BLOB]` collision is measured only in the notehead direction.
4. **Whether `dynamicR`'s zero is the repertoire or the detector**, and whether
   `dynamicNiente` is ever printed in this corpus.
5. **What `OMR_PARTIAL_DYNAMICS` is worth on the STAGED path.** Its refusal was
   priced on the legacy exporter, which has no ownership, and the write-up says
   in terms that a re-pricing is warranted. It has not happened.
6. **What `Q.DYNAMIC_BAND_POSITION` is worth as an ownership tier.** It is the
   family-positions work's own ranked-first next step and no arm has been run.
7. **Whether the range veto misbehaves on a contested letter.** It has a pitch
   test with no category guard and has never run with an instrument decided.
8. **Grand staff.** `[L54]` says a shared dynamic between two staves belongs to
   BOTH, and the re-attribution rule has no way to express that. Measured
   nowhere; the whole 9-publisher corpus is orchestral.
9. **Whether `OMR_CV_HAIRPINS` should default ON.** The re-run's own
   recommendation is yes (136 truth hairpins recovered, 97 exactly, for 53
   spurious; `matched_exact` 0 → 97 with `missing` 323 → 187) and it was left
   OFF because every default flip is Sean's. **That decision is still open.**
10. **n throughout.** The band study is the widest thing here — 9 publishers,
    18 pages — and it is scans only. Every staged figure is 1 or 2 documents and
    4-8 pages, and Litolff `984073` is the *low-res bitonal* pessimistic end of
    the corpus.

---

## Questions for Sean

1. **The `ff` 47 → 39.** Eight words changed spelling when duplicate letters
   were refused, and the record supports both readings. You said the page prints
   `ff` and nothing else — does that settle all eight, or does it need the eight
   bars looked at one at a time? (This is the only question here a single glance
   at the print closes.)

2. **`OMR_CV_HAIRPINS`.** The two instruments disagree and both have been
   re-run: OMR-NED charges +82 edits (84% of it amplification in bars that
   already fail to correspond), the symbol ledger records 0 → 97 exact matches
   on a family whose recall was zero. The ratio is **136 recovered : 53
   invented**, and two pages whose truth carries no hairpin invent 6 between
   them. Is that trade acceptable? ⚠️ Note the staged path already gathers the
   CV hairpins regardless of the flag, so this decision is only about the legacy
   exporter.

3. **Can a hairpin's DIRECTION abstain?** Today `crescendo if right > left else
   diminuendo` — one comparison, no margin, no tie-break, no `cannot tell`. Is a
   wedge whose two ends measure nearly equally something you would want the file
   to be silent about, or is a best guess right there?

4. **The band as an ownership tier.** 24% of letters stand in the band of the
   staff immediately above — distance exactly 1, 300 of 300, no exceptions, with
   a 2.5-space empty interval. Today a contested letter is decided by distance
   alone. The evidence for weighing the band is already taken and only the
   wiring is missing. ⚠️ But §6 of the band study names the limit: **a dynamic
   printed ABOVE staff N sits in the same place as one printed BELOW staff N−1**,
   and the rule would always choose the second. On the editions you work with, is
   "always below" safe enough to ship, or does it need an edition-level check
   first?

5. **The composite templates.** `symbol_library/` has 38 Bravura templates and
   none of them dynamic, while `glyphnames.json` carries all 42 including
   `dynamicFF`, `dynamicSforzando`, `dynamicFortePiano`. Matching a whole word
   dissolves the assembly problem instead of improving it — the same move that
   shipped `timeSigCommon`. The known risk is that a 19th-century Litolff `f`
   and Bravura's `dynamicForte` are the same letter in different typefaces.
   **Is that worth a measured arm, and across how many publishers before you
   would believe it?**

6. **`dynamicR` and `dynamicNiente`.** `r` fires zero times across 18 pages of 9
   publishers; `n` is not in the shipped class space at all and has no quantity,
   no decision and no route to a file. Are `rf`/`rfz` and *niente* common enough
   in the repertoire you care about to be worth a page?

7. **A `cresc.` and a crescendo hairpin are the same instruction in two
   notations**, and today the first becomes `<words>` and the second `<wedge>`
   with nothing connecting them. When you clean up a score, do you want the word
   left as printed, or is a page that prints `cresc. — — —` better rendered as a
   wedge?

8. **The 997 false `NO_INK`.** The dynamic-letter gatherer says *"no ink"* for a
   cell that holds ink and simply no dynamic in it — the single biggest
   contributor to the 2,377 contradicted empty claims on one record — while ten
   lines later the emptier case gets the honest word. Changing the reason word
   changes what every record says. **Is that a change you want made?**
