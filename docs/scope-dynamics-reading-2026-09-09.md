# Dynamics: what is actually blocked, and what the options are

*2026-09-09. Asked by Sean: "whatever process we are using it's not even
registering them. Dynamic markings are actually just fonts alphabet letters so
they should be easy to read. I'm guessing we are using the wrong tool."*

**Answer in one line: the instinct is exactly right about HAIRPINS and exactly
wrong about LETTERS, and the two have been filed as one problem — which is why
neither has moved.**

Every figure below is read off artefacts already committed to this repo. No new
arm was run.

---

## 1. The split, measured

The symbol ledger over the 20-row scan gate
(`benchmarks/omr-symbol-ledger-2026-09/out/ledger-summary.json`, the
2026-09-08 run — the first one whose accounting control is actually read):

| family | matched_exact | matched_attribute_error | missing | spurious | uncorresponded |
|---|--:|--:|--:|--:|--:|
| `dynamic` (letters) | **244** | 73 | 127 | 186 | 572 |
| `hairpin` (wedges) | **0** | 0 | 140 | 0 | 235 |

**`hairpin` matched_exact is ZERO.** Not low — zero, with zero spurious beside
it, meaning on every row whose parts join we emit no wedge at all. That is
Sean's "not even registering them", and it is one family, not the category.

**Letter dynamics register at roughly 71% truth-side recall** on the assessable
population (244 + 73 matched against 127 missing). They are not the block.

⚠️ **Do not read the two `uncorresponded` columns as failures.** They are the
`part_unresolved` bucket — 8 of 20 rows have no part correspondence at all, for
the four separate causes CLAUDE.md now separates. Those rows are unassessable
about *everything*, dynamics included.

---

## 2. Why the letters are NOT the block

`benchmarks/omr-dynamics-band-2026-09/FINDINGS.md` measured **1246 dynamic
letters across 18 scanned pages of 9 publishers.** The detector finds them. Its
own summary sentence: *"The detector is not blind to dynamics… The dynamics
failure is over-eagerness, not blindness."*

The letter shortfall that does exist is diagnosed to the mark, and it is three
different things, none of them "the tool cannot see this glyph":

| share of the 129-mark scan shortfall | cause | status |
|---|---|---|
| 14 | computed, assigned to `_dyn`, never emitted — the eventless-measure branch | **FIXED 2026-09-04** (`_mxl_directions_only`) |
| ≤31 | a letter run that spells no known word is discarded **whole** — 15 of 31 are a lone `s`, i.e. an `sf` whose `f` was missed | open, cheap |
| ~84 | never read | **137 of the shortfall is TWO pages of the same music** (the two Beethoven 5 p.2 scans). Across the other nine pages we emit 191 against a truth of 183 — *over*-emitting, exactly like the engraved arm. |

So the "never read" mass is not a general blindness; it is one edition's page 2
in two scans. A fix aimed at the category would be priced almost entirely on
that one page.

---

## 3. Why "they're just alphabet letters, use a text tool" is half right

**They are letters, but they are not TEXT.** A dynamic `f` is the SMuFL glyph
`dynamicForte` (U+E522) in Bravura or a publisher's equivalent — a bold oblique
music-font glyph, not a text-font letter, and no text OCR engine is trained on
it.

**And we already have the text rung, and it deliberately refuses this job.**
`direction_text.py` runs Surya + Tesseract on every page by default
(`OMR_DIRECTION_TEXT=1`) and its own docstring says, at line 47:

> *It does not touch the letter dynamics. `f`, `pp` and `sf` are drawn glyphs,
> the detector finds them, and `export.measure_dynamics` already emits them.*

That refusal is load-bearing rather than an oversight. The same module records
the reason two lines later: **a dynamic `p` and the `p` of `espr.` are the same
letter in the same family**, so the detector already reads the middle of that
word as `dynamicP`. Free text is gated by a 181-entry musical lexicon, which is
what stops every smudge becoming a word — and a *single character* has no
lexicon to be gated by. Pointing OCR at one-letter targets removes the only
guard that path has.

**But there IS a third tool this project has used twice and never pointed at
dynamics: Bravura template matching.**

`tools/omr/symbol_library/` holds 38 rasterised SMuFL templates and **not one
dynamic glyph.** Meanwhile `symbol_library/data/glyphnames.json` carries all
**42** of them — including the *composite* forms `dynamicFF`, `dynamicMF`,
`dynamicPP`, `dynamicSforzando`, `dynamicFortePiano`.

That matters because it dissolves the assembly problem instead of improving it.
Today `export.measure_dynamics` joins single-letter detections into a word by
x-adjacency, and a partial run (`s` for `sf`) spells nothing and is binned. A
composite template matches `sf` as **one object**.

This is precisely the move that shipped `timeSigCommon` / `timeSigCutCommon` on
2026-08-31 — a reader that could read every meter written in digits and neither
of the two written as a letter. Same shape, same library, same builder table
(`builder.py`, the `("timeSigCommon", "time_sig_digit")` line and its comment).

⚠️ **Publisher font is the open risk and it is not hypothetical.** The
key-signature template reader works because a flat is a flat; a 19th-century
Litolff `f` and Bravura's `dynamicForte` are the same letter in different
typefaces. The time-signature work already hit this — a Litolff `3` matched
Bravura's `6`. Any dynamics-template arm has to be measured across publishers
before it is believed, exactly as the band study was (nine).

---

## 4. The hairpin block — and the fix that already exists, switched off

`tools/omr/hairpin_detection.py` is a classical-CV hairpin reader, built and
measured 2026-09-04, call site added 2026-09-07. It finds **96 hairpins across
the 20-row gate against a truth of 192, versus the detector's 3.** Its three
tests (per-column open extent, outline straightness, whole-page isolation) are
each measured alone and then combined.

It is **OFF by default**: `OMR_CV_HAIRPINS`, `transcribe.py:3106`.

The reason it is off is that it costs OMR-NED: 11 rows worse, 8 unchanged, 1
better. But the docstring's own attribution says the cost is largely **not the
hairpins**:

> *Brahms 1 p2 carries 39 of the 96 hairpins this flag finds and +37 of the +76
> total edit movement — half of it — and it is one of the three rows in the gate
> where `_stitch_slots` REFUSES… On such a row no hairpin can cancel a truth
> hairpin whichever note `_wedge_anchors` picks, because the part it lands on
> pairs with nothing. **The anchor rule is not in the causal path there.***

⚠️⚠️ **THAT PRICING IS STALE BY ONE DAY, AND IN THE DIRECTION THAT MATTERS.**
The arm was run **2026-09-07**. `OMR_SLOT_STITCH` was flipped **default ON on
2026-09-08** — and Brahms 1 p2 is not merely one of the rows it reaches, it is
*the* row: 27 fragment parts → 14 continuous parts, ledger correspondence 0% →
100%. **The single row supplying half of this flag's measured cost has been
structurally repaired since the flag was priced.**

So the highest-value next action on dynamics is a **re-run, not new code.**

---

## 5. Where the staged pipeline stands on this

All three dynamics decisions are **declared stubs** — they abstain with
`ABSTAIN.NOT_IMPLEMENTED`:

| decision | file | state |
|---|---|---|
| `Q.DYNAMIC` | `adjudicators/text.py:18` | stub |
| `Q.DIRECTION` | `adjudicators/text.py:42` | stub |
| `Q.WEDGE_ANCHOR` | `adjudicators/ownership.py:265` | stub |

⚠️ **And there is nothing behind them to adjudicate.** `Q.DYNAMIC_LETTER` and
`Q.WEDGE_BOX` are declared observation quantities in `record.py` (lines 297-298)
that **no gatherer emits** — `gather.py` mentions neither. The schema is wired
and the evidence side is empty, so implementing the adjudicators first would
produce rulings with no basis.

**The composition is already declared and it is the right one**
(`adjudicate.py:77-83`):

```
Q.DYNAMIC_LETTER ─┐
                  ├─> Q.GLYPH_OWNER ──> Q.DYNAMIC
Q.WEDGE_BOX ──────┴─> Q.WEDGE_ANCHOR
```

`Q.GLYPH_OWNER` is the one piece here that is **NOT a stub** — it is a real
adjudicator with a ladder/range/distance tier stack. That is significant,
because the band study's conclusion was that dynamics placement *belongs in
ownership, not in a gate*:

> *83% of re-attributed letters are the target staff's SOLE evidence… the mark
> exists once, in the wrong cell, and the letter is sole evidence because the
> pipeline made it so. This is the same failure the ledger-ladder work found for
> noteheads — distance is wrong for exactly the case the cell padding exists
> for.*

So the staged pipeline gets the dynamics placement fix **for free** the moment
`Q.DYNAMIC_LETTER` is gathered: it flows through an ownership adjudicator that
already exists, instead of needing the re-attribution tier bolted into
`_dedupe_cross_staff_detections` by hand.

---

## 5b. Which is primary — and how the two can interact

*Added 2026-09-09 after Sean: "I'm not sure our primary issue with dynamics is
the hairpins or the dynamic letters or both — we will obviously need to have
both read and able to interact with each other in the adjudication stage."*

### Neither is primary. They are the same size.

On the assessable rows of the 20-row scan gate, the **absolute miss counts are
within 10% of each other**:

| family | truth-side | matched | attr-error | **missing** | recall | spurious |
|---|--:|--:|--:|--:|--:|--:|
| `dynamic` (letters) | 444 | 244 | 73 | **127** | 0.714 | 186 |
| `hairpin` (wedges) | 140 | 0 | 0 | **140** | **0.000** | 0 |

⚠️ **The recalls differ wildly and the misses do not.** Quoting either number
alone gives the opposite answer to the other, which is why "is it the letters
or the hairpins" has had no stable answer: **it is both, roughly equally,** and
they are different KINDS of failure —

- **letters**: 71% recall, but 186 spurious and 73 wrong-text beside it. A
  **precision and placement** problem on a family we can already see.
- **hairpins**: 0% recall with **0 spurious**. A **pure recall** problem — we
  are not wrong about hairpins, we are silent about them.

A precision problem and a blindness problem do not share a fix, and the two
have been ranked against each other as if they did.

### The obvious interaction is the wrong one, and the sweep says why

The tempting adjudication check is musical: *a crescendo runs from a quieter
dynamic to a louder one*, so the flanking letters corroborate the wedge's
direction — an implication test of exactly the shape `staged/groups.py` exists
for. Measured on the one reference encoding committed to this repo (Brahms 1 /
Breitkopf, 21 parts, 1173 `<dynamics>`, 683 hairpins) with
`benchmarks/omr-dynamics-coupling-2026-09/probe_letter_wedge_coupling.py`:

```
window   hairpins it can speak about        wrong about the TRUTH
 +/-1       34  ( 5.0% of hairpins)          0 / 34   =  0.0%
 +/-2       68  (10.0%)                      9 / 68   = 13.2%
 +/-3      108  (15.8%)                     26 / 108  = 24.1%
 +/-4      132  (19.3%)                     42 / 132  = 31.8%
```

⚠️⚠️ **The rule's accuracy is entirely a function of its reach, and that — not
any single rate — is the finding.** At one measure it is **exact, 34 for 34**;
at four it is wrong about a third of the time. The coupling is real and
strictly **local**: a dynamic one bar from a hairpin end belongs to it, one
four bars away is a different musical event the window merely reached.
`cresc.` into a subito `p` is a standard gesture and appears the moment the
window loosens.

**So the constant is a cliff, not a tuning**: keep it at ±1 measure and
ABSTAIN beyond, rather than buying reach with accuracy. And even there it is
**additive evidence over ~5% of hairpins, never a veto** — a veto on the
loosened version would fire on correctly-read hairpins, which is `groups.py`'s
own stated failure mode: *a wrong `reading` manufactures disagreement out of
correct engraving.*

⚠️ **n = 1 work**, because the score library is machine-local and gitignored.
Brahms is a heavy hairpin user, so any bias is toward *over*-stating the
coupling. And it measures the ENCODING, not the page.

### The interaction that IS strong runs the direction you would not guess

**Both families live in the same band, and only one of the two readers
respects it.**

`hairpin_detection.BAND_TOP_SPACES = 0.3` / `BAND_BOTTOM_SPACES = 6.0` below
the bottom staff line — and its own comment names the letters as sharing that
band (`+0.0 to +5.6 spaces`, which is the dynamics-band study's measured letter
population). They are the same row of the page.

But the two readers reach it differently:

| | frame | attribution |
|---|---|---|
| `hairpin_detection` | **page pixels, per staff** | right **by construction** — the band belongs to exactly one staff |
| dynamic letters | per-**measure cell**, 4–6 spaces of padding | **24% land in the staff above**, and the upstream dedupe already kept the wrong copy by distance |

**So the hairpin reader's band discipline is the fix for the letters'
placement problem** — hairpins help letters, not the other way round. That is
the opposite of the intuitive direction, and it is structural rather than
musical, which is why it does not decay with distance the way the direction
check does.

A second, weaker positional interaction is worth noting because it is free:
**67% of hairpins have a dynamic at at least one end** (40.8% one end, 13.5%
both, at ±2). A letter in the same band at the same y is a better anchor for
`_wedge_anchors` than a notehead is — and `_wedge_anchors`' documented
blindness is `duration_beats`, i.e. it is already known to be picking anchors
badly. ⚠️ Unmeasured as a fix; recorded as a candidate, not a plan.

### What this means for the staged pipeline

The composition already declared in `adjudicate.py` is the right one, and the
interaction Sean is asking for happens at **ownership**, not at spelling:

```
Q.DYNAMIC_LETTER ─┐
                  ├─> Q.GLYPH_OWNER ──> Q.DYNAMIC       (spell the word)
Q.WEDGE_BOX ──────┴─> Q.WEDGE_ANCHOR                    (anchor the wedge)
```

Gather **both** observations **in the same band frame, in page pixels**, and
they meet at `Q.GLYPH_OWNER` — the one piece of this that is already a real
adjudicator rather than a stub. The direction check then rides on top as an
additive witness at ±1 measure, where `groups.py` can record that two
independent readers (YOLO for the letters, classical CV for the wedges) agree
— genuinely independent, so the ancestor-closure rule admits it as
corroboration rather than collapsing it to `SINGLE`.

## 6. Ranked options

### A. Re-price `OMR_CV_HAIRPINS` on the current default tree — *no new code*

The only zero-recall family, a built and measured reader, and the row supplying
half its cost has been repaired since it was priced. Two steps, both with tools
already on disk:

1. `scan_eval` OFF vs ON, own `--tag=` per arm (⚠️ an empty tag silently reuses
   the first arm's transcriptions and reports a clean identical A/B — check the
   wall clock), on a tree with `OMR_SLOT_STITCH` at its new default.
2. Split each moved row's delta **by bucket** with
   `benchmarks/omr-ned-2026-08/dump_ops.py` — `entire staff` / `entire measure`
   movement is the stitch refusal, `wrong crescendo` on a row whose parts joined
   is the anchors. This is the step the docstring names as needing no new arm.

⚠️ Score it **per row**, never pooled — `scan_arm_table.py` refuses to pool on
purpose, because the two Mahler rows err in opposite directions and 8 of 20 rows
carry no truth hairpin at all.

### B. Gather the two dynamics observations into the staged pipeline

`Q.DYNAMIC_LETTER` from the detector's `dynamic*` classes, `Q.WEDGE_BOX` from
`hairpin_detection`. Unblocks three stubs, and routes placement through the
already-real `Q.GLYPH_OWNER` rather than re-implementing the band rule. This is
the item that puts dynamics *into* the staged pipeline, which is what was asked.

⚠️ `Q.DYNAMIC_LETTER` must carry `bbox_page_px` and the staff's bottom line, not
the cell frame — cell padding varies with staff crowding and would move the
number without moving the ink.

### C. Keep partial letter runs instead of binning them

A run spelling no known word is discarded whole (`_DYNAMIC_WORDS` in
`export.py:1454`). 49 letters in 31 runs, dominated by a lone `s` (15). An `sf`
whose `f` was missed is a *read* mark thrown away — the same
detected-then-dropped shape this project has now paid for ten times. Cheapest
item here; needs a decision about what a partial run exports as.

### D. Bravura dynamic templates — the "right tool" answer, measured first

Add the ~15 real dynamic glyphs (letters **and** composites) to
`builder.py`'s table, rebuild the library, and read them in the band the
placement study already established. ⚠️ **Measure reach before accuracy** — the
never-read mass is concentrated on two scans of one page, so this could be a
large amount of work priced almost entirely on Beethoven 5 p.2. Run the reach
probe first: how many truth marks sit where no detection fired, across the nine
publishers, not the one.

⚠️ **Verify the library rebuild is byte-identical for the existing 38
templates.** That was the check that mattered when common time was added, and it
matters more here because the clef and key-signature readers share this library.

### E. Refused, recorded so nobody re-tries it

- **Confidence as a filter on dynamic letters.** To remove half the 35
  unattributable letters you discard **233 of 911** good ones.
- **A band GATE** (drop out-of-band letters). Under-emits on both arms — 0.63
  engraved, 0.59 scanned — because a mark whose only surviving detection sits in
  the neighbour's cell is deleted rather than moved.
- **A column vote across staves**, the way clefs and key signatures are voted.
  An orchestral tutti prints one dynamic at one x on twenty staves, so the
  signal looks strong — but a `p` standing against neighbouring `f`s is real
  music, a soloist against a section, and a vote deletes exactly the information
  a reader wants.
- **Pointing Surya/Tesseract at the letters.** See §3.

---

## 7. What this document does not know

- **No arm was run for this.** Every number is read off a committed artefact.
  §4's claim that the hairpin pricing is stale is an argument from dates and the
  flag's own attribution, **not a measurement** — it predicts the re-run will
  come out better, and the re-run is item A precisely because that prediction
  could be wrong.
- **The scan truth's dynamics come from the reference encoding, not from reading
  the scan.** A dynamic the engraver printed and the encoder omitted counts
  against us and is not our error.
- **Nothing here prices the LilyPond exporter**, which never calls
  `measure_directions` at all and therefore drops dynamics on *every* measure —
  a wider gap than any of the above, invisible to `export_coverage` because that
  compares MusicXML.
