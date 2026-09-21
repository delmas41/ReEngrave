# Symbol dossier — TEXT

Every printed mark on a score page that is made of **letters or digits** rather
than of music glyphs: the instrument name in the margin, the direction word
inside a system, the tempo and metronome marks, the measure number, the
rehearsal letter, fingerings, and the lyric. Plus the mirror case — text the
detector reads as a musical symbol.

**Read first, because this family is different from every other one.**
For every other family the reader is YOLO or classical CV and the class name
is an opinion about a shape. Here the reader is **OCR**, and the thing that
actually decides is a **LEXICON** — 495 instrument aliases for the margin, 140
terms + 25 connectives for the words inside a system. The OCR rung proposes a
string; the lexicon says whether that string is music. Loosen the lexicon and
every smudge on a scan becomes a symbol.

Two sources already answer parts of Q1 and Q3 for this family and are cited
rather than re-derived:

* **[docs/position-grammar-confusables-2026-09-04.md](../position-grammar-confusables-2026-09-04.md)**
  §2 **DIGIT** (one glyph, five roles) and §2 **BOWL / BLOB** (hollow heads vs
  letters vs grace vs specks). Those are the Q1 entries for the measure number,
  the fingering, and text-read-as-a-symbol. Where this dossier adds to them or
  disagrees, it says so in the section.
* **[benchmarks/omr-family-positions-2026-09/FINDINGS.md](../../benchmarks/omr-family-positions-2026-09/FINDINGS.md)**,
  `tools/omr/staged/positions.py` and `tools/omr/staged/capture.py` — the
  per-family POSITION fact, ten producers and **no consumers**
  (`OMR_FAMILY_POSITIONS`, default OFF). With Sean's own warning, quoted there:
  *"position is an option for helping us determine something but will rarely
  be a clear rule that determines by itself."*

---

## The one-page summary

| symbol | detector class | staged quantity | staged decision | reaches a file |
|---|---|---|---|---|
| margin instrument label | **none** | `Q.MARGIN_LABEL` | `adjudicate_instrument` → `slot_index` → `part_partition` | `<part-name>` |
| direction word | **none** | `Q.DIRECTION_WORD` | `adjudicate_direction` | `<words>` |
| tempo mark | none | `Q.DIRECTION_WORD` (`category: tempo`) | same | `<words>` |
| metronome mark | none | **none** | **none** | **no** |
| measure number | `numeral*` (coarse only) | **none** | **none** | **no** |
| `fingering3` | `fingering3` | `Q.TUPLET_MARKER` | `adjudicate_tuplet_ratio` | `<time-modification>` |
| `fingering0/1/2/4/5` | yes | **none** | **none** | **no** |
| rehearsal letter | **none** | **none** | **none** | **no** |
| `numeral0`–`numeral9`, `numeral` | yes (ids 136-207) | **none** | **none** | **no** |
| lyric | **none** | **none** | **none** | **no** |

**Four of the ten symbols in this family have no quantity, no decision and no
export on the staged path.** Two of the four (the measure number, the rehearsal
letter) are named in
[docs/exploration-what-is-on-the-page-2026-09-09.md](../exploration-what-is-on-the-page-2026-09-09.md)
as *free printed ground truth for a decision we currently guess*.

---

## The margin instrument LABEL

`Fl.`, `Tr. Alt.`, `Basso.`, `Hörner in Es`. The instrument's name printed to
the left of its staff — in full on the first system, abbreviated afterwards
`[C69 + L70]`. **No detector class produces it.** Four readers, cheapest first:
the PDF's own text layer (`staff_labels.py`), Surya 2 (`staff_labels_surya.py`),
Tesseract (`staff_labels_tesseract.py`), Claude Vision (`staff_labels_vision.py`,
paid, off by default). The cascade is `contextual._read_labels_for_page`.

### 1. What sets it apart — and what it is confused with

**The distinguishing fact is POSITION, and it is a page-frame fact, not a
staff-grid one**: the label stands OUTSIDE the system, left of the staff's own
`x_start`. That is one half of `[C69 + L70]`, and its converse is the rule the
direction reader depends on — *anything found INSIDE the system's x-range is
not a label.*

What it is confused with, concretely:

| confused with | where measured |
|---|---|
| **stacked instrument NUMBERS** printed left of the bracket (`I`, `III`) — margin ink that is not a name | 24 of Mahler's 41 clef-locator false positives; CLAUDE.md "the CV clef locator", `benchmarks/omr-clef-geometry/RESULTS.md` (MEASURED HERE) |
| **plate numbers** in the same margin | `[C69 + L70]` *Known exceptions* (ASSERTED) |
| the **bracket / brace ink itself** | the class-(a) ink test had to exclude bracket and brace "otherwise the test is vacuous" — `benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md` (MEASURED HERE) |
| **the WHOLE system's margin arriving as ONE OCR block** — every name at once | 2 bad blocks at **1.04×** the system's tick span against **1.5–4.7%** for all 17 blocks Surya correctly split on Boléro, "a ~22× gap with 0.5 in the middle of it"; `benchmarks/omr-margin-labels-blob-2026-09/FINDINGS.md` (MEASURED HERE) |
| **another instrument's abbreviation** — the lexicon-side confusion, and the real one | see below |

**The lexicon confusion is the dangerous half, because it is silent and
confident.** Three shapes, all measured here:

1. **Cross-tradition collision.** `Tp.` is Timpani in the Italian/German
   tradition and Trumpet in the English one `[C74 + L72]`; `Tr.` is Trombe AND
   Tromboni. 167 of 1,422 real margin labels (11.7%) are ambiguous
   (`benchmarks/omr-score-language-2026-09/FINDINGS.md`, MEASURED HERE).
2. **A qualifier lost to a substring.** `Tromboni Alto e Tenore` cut to
   `Alto e Tenore` reads as **Tenor, a singer**, at `medium`; `Trombone Basso`
   cut to `mbone Basso` as **Bass voice**. Both reproduced live in this session:
   `instruments.lookup('Alto e Tenore')` → `('Tenor','medium','tenore')`,
   `lookup('mbone Basso')` → `('Bass voice','medium','basso')`
   (`benchmarks/omr-margin-window-truncation-2026-09/FINDINGS.md`, MEASURED HERE;
   re-run here, n = 2 strings).
3. **A right answer that is the wrong instrument for this score.** `Basso.` →
   **Bass voice** at `high` confidence, live today
   (`lookup('Basso.')` → `('Bass voice','high','basso')`). On an orchestral page
   that is the bottom string staff. 35 rows on the edition tier (CLAUDE.md,
   the edition-instrumentation section).

⚠️ **The truncation family is a FIXTURE fault, not a real-corpus one, and that
was measured**: over the held library — **289 editions, 141 pages carrying
margin text** — the smallest left edge of any margin string is 5.00 pt and
**zero** spans sit at or past the sheet edge
(`benchmarks/omr-margin-window-truncation-2026-09/FINDINGS.md` §4, MEASURED
HERE). The 14 truncated labels are LilyPond's own `indent` clipping the
benchmark's generated fixtures.

⚠️ **The single largest cause of "no label" is not a reader fault at all.**
Over 407 staves and 5 publishers, **115 staves print no label** and 0 are a
crop miss (`benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md`, MEASURED
HERE). Which family a publisher drops is systematic `[C70]`: Litolff labels
winds and brass on every system and **strings never** after p.1; Simrock labels
the movement's first page only; Breitkopf labels every staff.

### 2. Best method: YOLO / CV / other

**OCR, and then a lexicon — and the lexicon is the reader that matters.**
YOLO cannot help: there is no label class in the 208-class space, and the class
that would have supplied one (`textDynamic`) is the class the Phase 3.4
expansion collapsed on. Classical CV finds the band; it cannot read a name.

Measured on the tree in this session (live probe, `tools/omr/instruments.py`):
**38 instruments, 495 aliases.** Spot readings: `Fl.` → Flute/high,
`Tr. Alt.` → Trombone/high (the 2026-08-31 fix holds), `K. Fag.` →
Contrabassoon/high, `Hr.` → Horn/high, `Yiolino` → Violin/**low** (the OCR fold).

⚠️ **The four rungs do not make the same KIND of claim, and `record.py` is the
only place in the vocabulary that says so.** `Q.MARGIN_LABEL` is the single
reader-split CLAIM in the whole quantity vocabulary
(`tools/omr/staged/record.py:1151`):

| rung | claim | can it be wrong because the plate is bad? |
|---|---|---|
| PDF text layer | `CLAIM.EXTERNAL` | **no** — it reads no ink |
| Surya / Tesseract / Vision | `CLAIM.IDENTIFICATION` | **yes** |

That split is what makes one free rung genuinely independent of the raster. It
is also the reason it must not be collapsed: *"declaring one word for both
would have to pick the WEAKER claim to stay safe, which silently denies the
free rung the standing `source_kind` doctrine gives it."*

⚠️ **Reach per rung is publisher-dependent and the free rung is often zero.**
On Litolff Beethoven 5 (1870 scan) the **text layer reads 0 of 75** and the
cascade reads **50 of 75**, 12 of 12 on the opening system
(`benchmarks/omr-part-join-phase2-2026-09/probe/margin_label_reach.py`, quoted
in `benchmarks/omr-slot-index-2026-09/FINDINGS.md` §1, MEASURED HERE).

⚠️ **The OCR rung is a generative model and it degenerates.** Surya has
returned an English essay from a crop a few staff spaces tall, and
`'- 8 - - 9 - - 10 - …'` from another. `RUNAWAY_TEXT_MAX_CHARS = 120` sits in
an empty interval measured over 438 strings from 45 committed transcriptions
(distinct lengths ≥ 30 are 34, 41, 47, 48, 55, **144, 854**; accepted strings
run 3–17 characters, so the headroom against a genuine direction is **7×**).
`tools/omr/staff_labels_surya.py:104`. MEASURED HERE.

⚠️⚠️ **Two documents in this repo disagree about whether that decoder is
deterministic, and the disagreement is a finding.**
`benchmarks/omr-direction-text-2026-09/NONDETERMINISM_2026-09-02.md` says in
terms *"It does not say Surya is non-deterministic"* and reports a tight test
of 20 crops with **0 of 20 differing**. Fifteen days later
`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §6a records the same
page's hallucinated text **differing between runs** — *"Computer Science
Programming Course"* one run, *"Consulting Companies for Consulting Companies"*
the next — and concludes the pipeline is not deterministic on
`Q.DIRECTION_WORD` with the flag ON or OFF. The tight test measured crops the
model read normally; the later observation is about a crop it **ran away on**.
The honest statement is that the rung is a fixed function of its input where it
behaves and samples where it degenerates, and **no control of the flag-A/B
shape can say anything about this family**.

### 3. Where on the page the deciding information lives

| where | what it decides | frame |
|---|---|---|
| left of `staff.x_start`, within `LABEL_RIGHT_MARGIN_PX = 40` of the staves | this ink is a label at all | page pixels |
| the block's y-centre against the staff's band, within `MAX_STAFF_DISTANCE_FRAC = 0.5` of the inter-staff distance | **which staff** owns it | page pixels |
| the block's HEIGHT against the system's own tick span | is this one label or the whole margin? (`> 0.5` → reject) | ratio, scale-free |
| off-centre distance in the LOCAL gap (`_SHARE_CENTREDNESS = 0.15`) | is this one name printed once across a braced pair? ⚠️ **not in this tree — see below** | ratio |
| spans joined PER STAFF before lookup | `Cor.` over `(Es)` is one name on two lines | — |
| the rest of the page's labels | the document's printing TRADITION `[C74 + L72]` | document |
| the work's catalog roster | which readings are possible at all | **not this raster** |

⚠️⚠️ **THAT ROW IS A RULE THIS TREE DOES NOT HAVE, AND THE FINDINGS FILE
CALLS IT SHIPPED.** `benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md`
records *"Phase 2 (ii-a) SHIPPED"* with the numbers — shared blocks 0.017–0.133
against ordinary one-staff labels 0.431+, **13 shared blocks and 0 in the band
between**, over 255 blocks / 20 pages / 5 publishers; `+11 labels, 0 lost, 0 new
wrong`; coverage **0.654 → 0.681**, reachable 0.924 → **0.955**; Brahms 1 p1
naming **14 of 14**. `grep -rn SHARE_CENTRED tools/omr/` returns **nothing** on
the integration branch. The commit exists — `672607c9`, *"a margin block centred
BETWEEN two staves belongs to both"* — and
`git branch -r --contains 672607c9` names **one branch**,
`origin/claude/staff-identity-labels-2026-09-05`, which is **2 commits ahead of
integration and 1,222 behind**. It is not on `origin/main` either. MEASURED HERE.

This is CLAUDE.md's *fixed-then-kept-open-in-prose* inverted — **described as
shipped and absent from the tree** — and it is the shape that file says is
mechanically falsifiable in one command. Two effects follow: the **12
group-label fragments** (`(Es)`, `I`, `III`) that Phase 2 was built to close are
still unresolved here, and Brahms's `4 Hörner` is still **discarded as belonging
to no staff** (0.565 mean spacings from its nearer tick, 0.043 off centre in its
own local gap — ⚠️ *the unit changed the answer*).

`capture.py` grades `MARGIN_LABEL` as `NOT_A_MARK`: *"a staff-GRID position is
meaningless outside the staff"*. It carries `y_center_px` for the join and
nothing else. That is the right grading and it is why this symbol has no entry
in `benchmarks/omr-family-positions-2026-09`.

### 4. Stage by stage

**GATHER** — `gather.gather_margin_labels` (`tools/omr/staged/gather.py:2646`).
It calls the CASCADE, not the readers, so the cheap rungs stay cheap. It emits
**only the STRING** (`Q.MARGIN_LABEL`); the reader's own resolved `instrument`,
`confidence` and `alias` go into `detail` as annotation. *That separation is the
whole design of this family* — it is exactly the fusion that let `Tr. Alt.`
become a singer with the raw text sitting beside it.

Four states for an empty staff, all reachable:

| what happened | written |
|---|---|
| a requested rung is not installed here | `READER_UNAVAILABLE` |
| a requested rung was installed and threw | `READER_UNAVAILABLE` |
| no OCR rung was requested at all | `OUT_OF_SCOPE` |
| every requested rung ran and read nothing | `NO_INK` |

⚠️ The **weaker claim wins**: one missing rung poisons the whole page, not only
the staves it would have read.

**ADJUDICATE** — `adjudicate_instrument` (`adjudicators/identity.py:17`),
**ORDER position 6 of 28, before `Q.CLEF` (10) and before `Q.GLYPH_OWNER` (12)**. That
inversion is `A-ORDER-2` and is the reason the split exists at all: on the
legacy path the instrument arrives 647 lines after the note. It reads
`Q.MARGIN_LABEL` + `Q.ROSTER_ENTRY`, calls `instruments.lookup`, then
`work_roster.decide`. Five reasons: `label`, `roster`, `not_in_lexicon`,
`no_evidence`, `vetoed_by_the_work_roster` (`score_order` is DECLARED and
unreachable — the score-order tier is a named gap).

Then `adjudicate_slot_index` (7), `adjudicate_part_partition` (8),
`adjudicate_group_symbol` (9).

**EVALUATE** — `consequences.name_part` (`Q.INSTRUMENT` → `Q.PART_NAME`).
`join_parts` is the last declared stub in `consequences.py` and returns `[]`.

**INFER** — `inferences.collapse_slot_index_to_family_block`: a bottom-contiguous
block of UNNAMED staves that the reference's trailing family run matches SHORT
by one is collapsed with the deficit at its FOOT (`Violoncello e Basso`). This
is the one place a staff with **no label at all** gets placed, and it is
labelled as an inference. It reads `Q.CLEF_GLYPH` (the raw detection) and
explicitly **not** `Q.CLEF` (the verdict), because the verdict already weighs
the instrument this rule is placing.

**EXPORT** — `Q.PART_NAME` → `<part-name>`. `Q.SLOT_INDEX` decides the part
join; a staff with no slot is stranded as its own fragment part.

⚠️⚠️ **`Q.TEXT_LAYER` IS DECLARED, IS NAMED AS A DIRECT READING FOR THREE
DECISIONS, AND IS GATHERED BY NOTHING.** `adjudicate.READINGS` lists it for
`Q.INSTRUMENT`, `Q.SLOT_INDEX` and `Q.PART_PARTITION`
(`tools/omr/staged/adjudicate.py:65,75,76`); `gather_coverage` reports it under
*DECLARED, UNGATHERED*. The text-layer rung's output reaches the record as a
`Q.MARGIN_LABEL` row with `reader=TEXT_LAYER`, so nothing is lost — but the
circularity filter's `READINGS` table names a quantity that cannot exist.
`reach.py:106` already flags it and says why it is easy to confuse with
`READERS.TEXT_LAYER`. MEASURED HERE (grep + `gather_coverage`).

⚠️ **`OMR_ROSTER_LABELS` gates the LEGACY path only.** `work_roster.enabled()`
is read at `contextual.py:629` and nowhere else; `adjudicate_instrument` calls
`WR.decide` **unconditionally** whenever a `Q.ROSTER_ENTRY` row exists. Since
2026-09-17 the staged CLI supplies a roster by default (`--no-roster` turns it
off), so **the roster layer is ON by default on the staged path and OFF by
default on the legacy one.** MEASURED HERE (grep).

⚠️ **And that makes three known label defects fixable on the staged path
TODAY — unmeasured.** Live probe here against the committed Beethoven 5 roster
(`work_roster.work_roster('beethoven--symphony-5')`, 10 instruments,
`source_kind: catalog`, `complete: True`):

| printed | lexicon alone | with the roster |
|---|---|---|
| `Basso.` | Bass voice | **disambiguated → Contrabass** |
| `Alto e Tenore` | Tenor (a singer) | **vetoed** — no voice in the roster |
| `mbone Basso` | Bass voice | **recovered → Trombone** |

The `Bass voice` that reached the exported `<part-name>` in
`benchmarks/omr-slot-index-2026-09/FINDINGS.md` §3 came from a gather run on
**2026-09-14**, three days before the roster producer landed. **No staged run
since has been measured.** (Probe used: `work_roster.decide` over three strings
against the committed catalog. No page read, no weights.)

⚠️ **The ambiguity channel and the language channel are NOT on the staged
path.** `grep -rn "score_language\|AMBIGUOUS_ALIASES\|resolve_ambiguous_label"
tools/omr/staged/` returns nothing. So `[C71]` (an engraver does not name one
section two ways on one system) and `[C74]` (the document's tradition) — both
measured, both shipped, one default-ON and one default-OFF — govern the legacy
exporter and not this one. MEASURED HERE.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) It abstains, thoroughly, and it cannot say "best guess".**
Four GATHER states and five ADJUDICATE reasons, and they are genuinely used:
on Litolff pp.1-4, **50 of 75 staff-systems observe a label and 25 abstain
`unnamed_in_short_system`** (`benchmarks/omr-slot-index-2026-09/FINDINGS.md` §1,
MEASURED HERE).

What it cannot do is hedge. `adjudicate_instrument` returns a NAME or abstains —
no `Ruling.narrow`, no candidates, no support. The reader's own `coverage`
(a float) and `confidence` (`high`/`medium`/`low`) are put in `detail` and
**read by nothing** on the staged path. That is Class B and Class C of
[docs/handoff-probability-gates-2026-09-05.md](../handoff-probability-gates-2026-09-05.md)
arriving together in one decision — and it is deliberate: that document's own
pre-registered standard is *an uncalibrated probability is WORSE than none*
(identity probabilities measured ECE **0.1277**, failing worst at the top of
the range, n = 197).

The one place a "best guess" IS made is INFER's
`collapse_slot_index_to_family_block`, and it is labelled as one.

**(b) The fan-out is the largest of any quantity in this family, and probably
in the pipeline.** `Q.INSTRUMENT` is read by:

| consumer | what it does with it |
|---|---|
| `adjudicate_clef` | `Term("instrument", W_INSTRUMENT=1.0)` for the expected clef — against `W_DETECTOR_HIGH = 3.0` and `W_DOSSIER = 4.0` |
| `ownership._range_veto` | DISCARDS ink outside the instrument's written range |
| `adjudicate_slot_index` | the name pairing for a short system |
| `adjudicate_group_symbol` | brace vs bracket, by family |
| `consequences.name_part` | the `<part-name>` |
| `inferences.collapse_slot_index_to_family_block` | the placement of unnamed staves |

**One wrong slot renames a part across a whole document**, because a name is
stamped per SLOT onto every staff of that slot on every page — 93 `Tp.` staves
exported as Trumpet on one 88-page Beethoven run (`consequences.py:467`,
MEASURED HERE).

**Independence — and this is where the family is at its best and its worst.**

*Best:* the label has two witnesses that do **not** come off this raster — the
PDF text layer (`CLAIM.EXTERNAL`) and the catalog roster (`CLAIM.EXTERNAL`,
`source_kind: "catalog"`). Both survive a bad plate. That is the
`source_kind` doctrine working as designed, and this family is the clearest
instance of it in the repo.

*Worst:* **where the label is absent it is absent by CONVENTION, and the
convention correlates exactly with need.** Over the 20-row scan corpus, the
unresolved staves whose family defaults to something other than treble — the
entire population `clef_correction` could ever be handed — number **29, and 29
of 29 print no label at all** `[C70]`. The families that KEEP their labels
(winds, brass) already default to the right clef; the families that LOSE them
(strings, low brass) are the ones that need a non-treble clef.

⚠️ That is the *"two readers can fall silent together"* hazard in its
**cliff** form rather than its gradient form — the distinction the stage
charter §4 draws. A study that stratified on OCR confidence would see a flat,
uninformative population and find nothing, which is roughly how 29 of 29 stayed
invisible until somebody counted them.

**The check that needs no truth file, and is not on this path.**
`tools/omr/label_contradiction.py` asks whether a staff whose OWN margin label
was read on THIS page was exported under a different name. 158 firings over two
whole works, **138 (0.873) the EXPORT is wrong, 20 (0.127) the LABEL is, 0 both
right**, every one hand-adjudicated. `adjudicate_instrument` names it in
`checked_by` — but `checked_by` is a DECLARATION of what could check the fact,
not a check that runs, and `grep -rn label_contradiction tools/omr/staged/`
returns **nothing**. MEASURED HERE (grep).

**Evidence grade:** MEASURED HERE throughout except where marked ASSERTED.
Registry handles: `[C69 + L70]`, `[C70]`, `[C71]`, `[C72]`, `[C74 + L72]`,
`[L71]`.

---

## The direction WORD inside a system

`legato`, `arco`, `pizz.`, `cresc.`, `Allegro con brio`. Words printed in the
band above or below a staff `[C73 + L73]`. **No detector class.** Read by
`tools/omr/direction_text.py`: subtract every detection from the page's ink,
refuse the curves by fill ratio, OCR the residue, and accept only what
`direction_lexicon.lookup` names. `OMR_DIRECTION_TEXT`, **default ON**.

### 1. What sets it apart — and what it is confused with

**Two facts, and the first is answered by construction rather than tested.**

*(i) It is INSIDE the system.* `find_candidates` clamps every band to the
staff's own `x_start..x_end` — *"left of `x_start` is the margin, where the
instrument name is printed — a reader let loose there returns `Contrabassoon`
as a direction."* Measured: **0 of 98 candidates across two documents are ever
in a margin** (`benchmarks/omr-staged-direction-2026-09/FINDINGS.md` §0,
MEASURED HERE).

*(ii) It is a word the LEXICON names.* Everything else in the band is refused
by that gate.

Confused with, concretely, each with its shipped discriminator:

| confused with | discriminator | where measured |
|---|---|---|
| a **slur arc** read by OCR as `~` | `min_fill_ratio = 0.16` — a letter fills a fifth of its box, a slur crossing the same box a fortieth | `direction_text.py:141` (MEASURED HERE) |
| a **beam group** read as `IIII` | the lexicon | `test_direction_text.py:74` |
| a **broken horizontal rule** whose pieces each pass the letter tests | `min_word_height_spaces = 0.55` — every true direction 1.1–1.8 spaces, both false runs **0.2** | `direction_text.py:161` (MEASURED HERE) |
| the **TITLE** above the first staff | NOT distance — the populations overlap (Mahler's title sits closer to its staff than Beethoven's `Allegro con brio` does to that one). It is `above_first_measure_only`: a heading is centred on the PAGE, a direction is left-aligned to its music | `direction_text.py:95-104` (MEASURED HERE) |
| the **margin label** | the x-clamp | above |
| a **dynamic LETTER** — and this one runs both ways | see below |

⚠️⚠️ **The dynamic letter is the sharpest confusion in this family and it is
mutual.** The detector reads the `p` of `espr.` as `dynamicP` at confidence
**0.87** — correctly, on the evidence it has, because a dynamic `p` and the `p`
of a word are the same letter in the same font. Blanking that detection took
`espr. e legato` off two of Brahms's four string staves, **worth 56 edits**.
The separator is a GAP, not a shape: `f` sits ~1.7 spaces from the `legato`
beside it, `es` sits against the `p` inside `espr.` with nothing between, and
`inside_word_gap_spaces = 0.5` sits well inside that. Only dynamics are
excused — *"a notehead in a beamed run also has ink on both sides, and letting
the test excuse THOSE would put the notes back into the very mask that exists
to have them taken out."* `direction_text.py:178-197`. MEASURED HERE.

⚠️ **And a slur's BOX erases a word.** On a scanned Beethoven 5 page a slur
detected at 24.2 × 4.0 spaces (conf 0.48) sat over the word `sempre` and blanked
all nine of its components; the word went from nine pieces of ink to none and no
filter downstream ever saw it. `max_blank_width_spaces = 4.0` sits in a gap the
class space puts there — widest GLYPH box 3.2 spaces (notehead, clef) against
7.7 (pedal bracket), 24.2 (slur), 37.2 (beam). `direction_text.py:200-218`.
MEASURED HERE.

### 2. Best method: YOLO / CV / other

**Classical CV proposes; OCR reads; the LEXICON decides.** YOLO is not an
option and that is structural, not a preference: a direction word is **not in
the 208-class space**, and `textDynamic` — the class that would have supplied
one — is the class the Phase 3.4 expansion collapsed on.
`tools/omr/staged/capture.py --check` (run here) grades this the **only family
of fourteen with `shape: NO`** and the only one whose `location` is `page`.

⚠️⚠️ **The lexicon is the reader, and the number the tree quotes for it is
wrong.** Three places say *"181 musical terms"*
(`tools/omr/staged/adjudicators/text.py:278`,
`docs/scope-dynamics-reading-2026-09-09.md:80`, CLAUDE.md). Counted here from
`tools/omr/direction_lexicon.py`: **140 `TERMS`** (76 expression, 49 tempo,
15 dynamic-word) **+ 25 `CONNECTIVE`**, overlapping by 9, so **156 distinct
strings**. It has never been 181 — the first commit of the file
(`ceb6714c`) had 140 + 28 = 159 and the second (`3522d32f`) removed three
English connectives. **MEASURED HERE** (live import, plus `git show` of both
revisions). The GATE is correct and load-bearing; only its cited size is wrong.

The narrowness is argued on arithmetic rather than taste, and the argument is
worth keeping: *OMR-NED charges a direction its own character count on BOTH
sides — a `legato` we miss costs 6 and a `IIII` we invent costs 4 — so the
reader that abstains and the reader that guesses trade one for one, and only
the gated one is safe on material nobody has measured.*

⚠️ **Cost, and it is the most expensive thing in a staged run on a scan.**
Litolff Beethoven 5 pp.1-4: **~267 s/page for 6 accepted words, and the six
words are one word** — `CRESC.` ×3, `Cresc.` ×2, `cresc.` ×1. ~178 seconds per
word. Against the margin-label reader's 93 s/page for 50 instrument identities.
With the `<words>` and the emptied `<direction>` wrappers removed the two files
are **byte-identical**. `benchmarks/omr-surya-staged-cost-2026-09/FINDINGS.md`
§5 and §Part B, MEASURED HERE. ⚠️ **This is not an argument for turning it
off**: on the ENGRAVED benchmark the same reader is worth **144 edits, 18.8% of
the pooled figure**, and `wrong direction` is the third-largest bucket
(`benchmarks/omr-direction-text-2026-09/DEFAULT_2026-09-02.md`). The domain gate
that reconciles the two now exists — `OMR_DIRECTION_TEXT_SCAN_GATE`,
**default OFF**, `gather.py:2940` — and gates on a POSITIVE proof of scan so a
hybrid or an unopenable PDF keeps the reader ON.

### 3. Where on the page the deciding information lives

`direction_text._bands_for_page`, in **page pixels**:

* one band **below** every staff, and one **above** the topmost staff of each
  system;
* within a system the below-band owns the **whole gap**, because a word between
  two staves of one system belongs to the upper one. ⚠️ It used to be capped at
  3 spaces and that **cost five of the seven printed directions on one scanned
  page** — Litolff prints `arco` and `dolce` 3.5 to 7 spaces down;
* where the next staff starts a NEW system both claims are live, so the gap is
  **split at its midpoint** — *"guarantees that no word is ever offered to two
  staves"*;
* clearance `0.25` spaces from the lines, so the band never contains line ink;
* the crop is cut **per MEASURE**, not per band, for a mechanical reason: a band
  across a 21-staff Brahms page is 5900×183 px (32:1) and an OCR model resizes
  to a fixed frame, so a six-letter word survives as ~4 px of height. Cut at the
  barlines the same word arrives at 4:1. Measure attribution then comes free.

⚠️ **The one staff-relative fact this family has is too coarse to use.**
`placement` is `above`/`below`; `capture.py` grades it `coarse_band_only`. The
OFFSET — what would separate a `cresc.` standing in the dynamics row from an
`Allegro con brio` printed clear above the system — is `Q.DIRECTION_BAND_POSITION`,
**the only one of the ten family positions that is genuinely new rather than
promoted from an existing row**, and it is produced by
`positions._promote_from_log` and **read by nothing**
(`benchmarks/omr-family-positions-2026-09/FINDINGS.md`; reach **6** rows on
Litolff pp.1-4, **10** on Brahms pp.0-3). MEASURED HERE.

⚠️ And `[C73 + L73]`'s own *Known exception* is that the `above` band is
**UNEXERCISED by both documents**: all 98 candidates are `placement: below`.

### 4. Stage by stage

**GATHER** — `gather_direction_words` (`gather.py:2951`). It sits behind one of
the three forced ordering edges (`A-GATHER-1`): `_blank_detections` erases every
detected glyph before looking for words, so it cannot run before detection, and
`gather()` orders it last.

It calls `find_candidates` (pure CV) **and** `read_directions` separately, at
the cost of a second CV pass, deliberately — *"a word the CV never proposes is a
word no reader can find, and that is a different failure from one the OCR got
wrong."* Candidate rows are filed at `_DIRECTION_GLYPH_BASE = 90000` so the OCR
rung and the detector can never collide in one cell's key space.

Five states, four of them refusals:

| what happened | written | where |
|---|---|---|
| no OCR rung on this machine | `READER_UNAVAILABLE` | PAGE **and** every cell |
| the flag is off / the scan gate fired | `OUT_OF_SCOPE` | PAGE and every cell |
| the CV proposed no word-shaped ink | `NO_INK` | PAGE / cell |
| a rung read a crop and returned nothing | `NO_READING` | the CANDIDATE |
| a rung read it and the lexicon refused | `NOT_IN_LEXICON` | PAGE |
| accepted | an OBSERVATION | the CANDIDATE |

⚠️ The page-wide reason is written on **every cell** as well as the page,
because `adjudicate_direction` takes its domain from `Q.DIRECTION_WORD` — a
blind page would otherwise have no subject at all and would report
`decided: 0, abstained: {}`, which is a family never ASKED.

⚠️ **`NO_READING` vs `NOT_IN_LEXICON` cannot be split per candidate today.**
`read_directions` reports `n_read` and `rejected` for the PAGE, so every
unaccepted candidate is filed with the WEAKER claim and the page's counts beside
it. Making it per-crop is a change to the reader, not a wiring change.

**ADJUDICATE** — `adjudicate_direction` (`adjudicators/text.py:255`), **ORDER
position 28 of 28, last**. It does not re-test the text — *"re-testing the text
here would be a second, differently spelled lexicon."* What it decides is the
three-state answer. It reads `Q.DIRECTION_WORD` at
`Scope.SELF_AND_DESCENDANTS`; the default `Scope.EXACT` *"would have reported
`no_words` on every bar that HAS a word"* — the fourth instance of *a declared
input that could never answer*.

⚠️ **Ownership is NOT re-asked**, unlike the dynamic letter, and the asymmetry
is geometric: a letter reaches the exporter through a per-measure cell padded
4–6 staff spaces into its neighbour (24% of letters stand in the wrong cell), a
word never does — `_bands_for_page` answered ownership once, in page pixels,
before any cell existed.

**EVALUATE / INFER** — nothing. No consequence, no inference reads `Q.DIRECTION`.

**EXPORT** — `_place_direction_words` → `_mxl_direction(x, "words", text)`.
⚠️ **At the HEAD of the bar**, a declared simplification: the words carry a PAGE
x and the noteheads a CANONICAL one, and *"mixing the two frames is the fault
that made `Q.ONSET_COLUMN` report 1,062 columns of nothing."* The balance is an
EQUALITY with two named residue buckets.

⚠️ **An abstaining cell and a `no_words` decision both write nothing**, and the
exporter says why: *"MusicXML has no way to say 'a reader could not run over
this bar', and inventing one would be the fabrication this family is built to
avoid."*

Measured, committed arms (`benchmarks/omr-staged-direction-2026-09/out/`):

| | Litolff Beethoven 5 p1-3 | Breitkopf Brahms 1 p0-3 |
|---|--:|--:|
| word-shaped candidates | **42** | **56** |
| accepted | **2** | **10** |
| `<words>` written | 2 | 10 |
| refusals | `no_reading` 40, `no_ink` 812, `not_in_lexicon` 2 | `no_reading` 46, `no_ink` 768, `not_in_lexicon` 2 |
| accepted texts | `cresc.`, `Cresc.` | `pizz.`×3, `dim.`×2, `espr. e legato`, `pesante`, `unis.`, `arco`, `Cresc.` |

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) It abstains, and this family's state machine is the product.** Three ways
of being empty — *the page prints none*, *the reader could not run*, *the reader
ran and the lexicon refused* — and all three are distinguishable on the record
and indistinguishable in the file. `direction_arm.py` **exits non-zero declaring
itself DEAD** when no rung ran or no candidate was proposed, which is the
control this family needs and most families lack.

It cannot say "best guess", and should not: the lexicon is binary by design.

**(b) NOTHING reads `Q.DIRECTION`.** `grep -rn 'Q.DIRECTION\b'` under
`tools/omr/staged/` returns only `export.py` and the registry tables. MEASURED
HERE. So no other mark's reading depends on this one today.

The thing that WOULD lean on it is `[C74 + L72]`: *the printing TRADITION of a
document is inferable from the words it uses, which in turn predicts which
abbreviation set its margin labels are drawn from.* That channel exists
(`contextual.score_language`, `OMR_SCORE_LANGUAGE`, default OFF, 9 of 1,422
labels re-decided) and is **legacy-only**.

**Independence — and this family fails the test against the label reader.**
The direction word and the margin label are read by the **same two rungs** on
the same raster. `adjudicate.Evidence.correlated_groups` treats *"the same
reader on the same crop"* as ONE signal, which is exactly right here: a page whose OCR is bad gives
bad labels and bad words together. Worse, the two compete for the same
subprocess — `benchmarks/omr-surya-staged-cost-2026-09` measures the direction
reader spawning Surya on every page whether or not the label reader wants it.

**Evidence grade:** MEASURED HERE throughout. `[C73 + L73]`, `[L69]`.

---

## The TEMPO mark

`Allegro con brio`, `Un poco sostenuto`, `Poco andante`. Not a separate symbol
to the pipeline: it is a `Q.DIRECTION_WORD` whose lexicon hit carries
`category: "tempo"` (49 of the 140 terms). It exports as `<words>`, exactly as
an expression mark does — *"the categories exist to say what a hit IS, not to
change whether it is accepted."*

### 1. What sets it apart — and what it is confused with

The convention `[L69]` says a tempo indication is printed **TWICE** on a
full-score system — once above the top staff and once above the first violins —
and IU adds that its left edge aligns with the meter or the first notational
element. So the two things it is confused with are:

* **the TITLE / heading**, which is the discriminator `above_first_measure_only`
  exists for (see the direction-word section — distance does NOT separate them);
* **itself.** `[L69]`'s own mechanical prediction: *"a reader that attributes it
  to the violins will attach a system-level fact to one part, and a reader
  counting distinct directions will double-count it."*

Neither the duplication nor the attribution hazard has been priced. LITERATURE
(MOLA, IU) for the convention; **not measured here**.

### 2. Best method

The direction reader's, unchanged.

### 3. Where on the page the deciding information lives

⚠️⚠️ **A mid-score tempo change printed above a staff is unreachable by
construction, and this dossier states it as a finding because nothing in the
tree does.** `find_candidates` drops any `above`-band candidate whose measure is
not the staff's FIRST:

```python
if (placement == "above" and config.above_first_measure_only
        and measure_index != spans[0][0]):
    continue
```

That rule was measured against TITLES on three pages and it does what it was
built for. But a `Poco andante` printed above bar 40 of a system is an
above-band candidate outside the first measure, and it is discarded before any
OCR runs. MEASURED HERE (read from `direction_text.py:540-543`); **reach is 0 on
both committed documents either way**, since the `above` band is unexercised by
both, so nothing observable has been lost yet.

### 4. Stage by stage

Identical to the direction word. The `tempo` category rides on the row and on
the verdict's detail and **is read by nothing** — the exporter writes `<words>`
for every category.

### 5. Abstain or best-guess — and what leans on it

Same as the direction word: it abstains well, and nothing leans on it. A tempo
mark is the one direction whose value is a **system-level** fact rather than a
staff-level one, and the record has nowhere to say that — `Q.DIRECTION` is
scoped `Kind.CELL`.

**Evidence grade:** `[L69]` LITERATURE; the `above_first_measure_only` limit
MEASURED HERE; everything else inherited from the direction word.

---

## The METRONOME mark

`♩ = 108`, `(d = 108)` as OCR renders it. A note glyph, an equals sign and a
number, printed with the tempo mark.

### 1. What sets it apart — and what it is confused with

It is the only text in this family that **contains a digit and a glyph**, and
that is exactly what refuses it. `direction_lexicon.lookup` opens with

```python
if not re.fullmatch(r"[A-Za-zÀ-ÿ' .,\-]+", text.strip()):
    return None
```

with the comment *"A digit or a bracket means a bar number, a metronome mark or
a rehearsal letter — all of which are somebody else's problem."* Verified live
here: `lookup('(d = 108)')` → `None`, and a committed test pins it
(`tools/omr/tests/test_direction_text.py:73`). MEASURED HERE.

So it is not confused with anything — it is refused with the bar numbers and the
rehearsal letters, as one class of "text with digits in it".

### 2. Best method

Unbuilt. It needs a reader that is allowed to see digits, which means it needs
its own gate — the lexicon cannot be the gate for a string that is mostly a
number. The note glyph beside the `=` is in the class space (`notehead*`,
`flag*`) and would be a strong anchor: a notehead standing alone above a system
with no staff under it is not a note.

### 3. Where on the page the deciding information lives

With the tempo mark, above the top staff `[L69]`. Untested here.

### 4. Stage by stage — NONE

**No quantity, no gatherer, no decision, no export.** `<metronome>` is an
entry in `export_coverage.KNOWN_GAPS` and it is **UNCONDITIONAL** — it was in
`FLAG_DEPENDENT` and was taken out, measured rather than reasoned: *"on a full
`--direction-text` eval `<metronome>` is still absent from the export"*
(`tools/omr/export_coverage.py:423,555`). Two committed tests pin that it stays
a gap under both configurations. MEASURED HERE.

⚠️ **The KNOWN_GAPS wording is half right and worth correcting.** It reads *"A
tempo mark is read by the direction reader and emitted as `<words>`; the
structured `<metronome>` form is not built."* True of the TEMPO mark. The
metronome mark itself is **refused at the lexicon**, so it is not one gap but
two: a READ gap and an export gap. The entry describes only the second.

### 5. Abstain or best-guess — and what leans on it

It does not abstain; it is never asked. Nothing leans on it. A metronome mark is
the only thing on the page that states a TEMPO numerically, so its absence costs
nothing this pipeline measures — MusicXML `<metronome>` is not scored by
musicdiff and no decision reads a tempo.

**Evidence grade:** MEASURED HERE (the lexicon refusal, the KNOWN_GAPS status);
the "confused with" is ASSERTED.

---

## The MEASURE NUMBER

A small numeral at a system's top-left corner, outside the staff — or below
every bar where an edition numbers all of them `[C75 + L68]`.

### 1. What sets it apart — and what it is confused with

**Start from `docs/position-grammar-confusables-2026-09-04.md` §2 DIGIT**: one
printed glyph, five roles — tuplet digit, time-signature digit, measure number,
stacked instrument number, plate number — and *"where the mark stands is the
only thing that separates them."* This dossier **agrees and adds two things**:

*(a) The literature supplies a SIZE discriminator the repo's own entry does
not.* `[L42]` (*Time-signature numerals fill the staff's height*, each digit
~2 staff spaces tall in a unique heavy font) gives the converse directly: **a
digit-shaped mark one staff space tall is a fingering, a tuplet number or a
measure number — not a meter.** That is a shape test where §2 DIGIT offers only
position, and it is the cheap first cut.

*(b) The measure number is confused with something §2 DIGIT does not list: a
BARLINE.* `system_grouping.py:120` records it by name — *"music ink out in the
staff body — a stem, an `a 2.` marking, **a measure number**, a brace curve —
can be counted as a crossing column and fake a connection across a real system
boundary, MERGING two stacked systems into one."* That is the confusion
`OMR_LEFT_EDGE_SPLIT` (default ON) exists to repair, and it is measured: on
Beethoven 9 p60 the true break had 324 crossing columns at the wide window and
ZERO at the shared left edge. MEASURED HERE (read from the tree).

So a measure number's damage today is not that we misread it — it is that we
**read it as structure**.

### 2. Best method

⚠️ **Not YOLO, because the class it would arrive under cannot name it.** The
fine half of the 208-class space has `timeSig0`–`9`, `tuplet1`–`9` and
`fingering0`–`5` and **no measure-number class at all**; the coarse half has
`numeral0`–`numeral9`, which covers all four roles under one name and is
explicitly forbidden from being mapped to `timeSig` (see the `numeral` section
below). So a measure-number reading has to come from **position applied to a
digit detection of some other class**, or from the OCR rung.

Both routes are blocked today: `Q.TUPLET_MARKER_POSITION` — the one position
fact that asks *does this digit clear the staff* — is produced behind
`OMR_FAMILY_POSITIONS` (default OFF) and read by nothing; and the direction
lexicon refuses any string with a digit in it.

### 3. Where on the page the deciding information lives

Top-left corner of the system, **outside** the staff, left of or above the first
barline — two accepted placements, both stated in `[L68]`, with MOLA requiring
only that an edition be consistent. The key fact for us is that it is *outside*
the staff and near a system's left edge, which is where nothing else numeric
stands except the stacked instrument numbers — and those are in the MARGIN,
left of the bracket.

### 4. Stage by stage — NONE

**No quantity, no gatherer, no decision, no export.**
`grep -rn 'measure number' tools/omr/staged/` returns only the *export's own*
`<measure number=>` attribute, which is the document's bar sequence computed by
`export._document_bar_offsets` — **derived from barline geometry, not read off
the page.** `[C75 + L68]`'s *Code:* line says **"no consumer found"** and this
dossier confirms it. MEASURED HERE.

### 5. Abstain or best-guess — and what leans on it

Nothing can abstain because nothing asks.

**What would lean on it is the thing it is most worth having for.**
`Q.MEASURE_PARTITION` is decided from barline columns alone.
`docs/exploration-what-is-on-the-page-2026-09-09.md` puts this first among
*free printed ground truth for a decision we currently guess*: *"the engraver
has already told us how many bars are on the line, and we count them with
geometry instead… the only page-side quantity that could corroborate a bar
count without a reference file."*

⚠️ **And it would be a genuinely INDEPENDENT witness in the record's own
sense** — a different reader (OCR or a digit detection), no shared ancestor
with the barline columns. That is rare in this repo and is why it is worth the
reach measurement. `[C75 + L68]`'s own *Predicts* adds the second prize: *"it
names the DOCUMENT's bar index for that system, which is the join between a
printed system and a reference encoding"* — the join `works.json`'s window rows
are hand-verified for today.

⚠️ **The counter-argument is REACH, and the number is one sentence.** `[C75 +
L68]` is graded **ASSERTED**: the only statement anywhere is *"the row-drafting
work found three of four editions print them"*
(`docs/position-grammar-confusables-2026-09-04.md:113`), and the repo file
*"could find no other statement of it and no per-edition measurement."*

**Evidence grade:** `[C75 + L68]` ASSERTED (untested here); the barline
confusion MEASURED HERE; the class-space gap MEASURED HERE.

---

## `fingering0` – `fingering5`

Six classes in the 208-class space. A small digit printed beside a notehead to
name a finger `[C53]`.

### 1. What sets it apart — and what it is confused with

`[C53]` again: a fingering **sits beside its notehead**, a tuplet digit stands
OUTSIDE the staff over its beam, a time-signature digit stands INSIDE the staff.

⚠️⚠️ **On this repertoire the confusion runs the OTHER WAY from the class name,
and that is the whole finding.** The detector reproduces the DSv2 positional
split badly on orchestral pages, because the training data has almost no
orchestral fingerings to contrast against. Measured over twelve engraved works:
**33 `fingering3` against 16 `tuplet3`, and ALL 33 sit in a cell holding a real
triplet**; the single detection that does not is a `tuplet3`
(`tools/omr/rhythm.py:1219-1244`, `benchmarks/omr-corpus-widening-2026-09/FINDINGS.md`,
MEASURED HERE). `mozart-sym41-mvt1` alone hands back **30 `fingering3` against
13 `tuplet3`** on a page printing 40 triplet groups.

So `fingering3` is, on this corpus, a **misspelled triplet digit** — and
`_TUPLET_DIGIT_PREFIXES = ("tuplet", "fingering")` reads it as one. Admitting the
class took Mahler 5 from OMR-NED 0.0455 to **0.0331** with its duration rate
0.864 → **1.000**.

⚠️ *"This admits the class; it does not relax the gate."* `_tuplet_groups` still
requires the digit's centre inside a BEAMED group's span and the group to hold
exactly as many notes as the digit claims. **A real fingering `3` centred over a
beamed group of exactly three would still be misread** — the corpus contains no
such case to price it against, and the honest statement is that the risk is
unmeasured rather than absent. Conductor's scores do not carry fingerings.

### 2. Best method

YOLO finds the ink; **position decides the role** `[C53]`. This is the
project's recurring winning move (position-grammar §3), and here it is already
shipped on the legacy path.

### 3. Where on the page the deciding information lives

Beside its notehead, INSIDE or just outside the staff, at the note's own height.
The tuplet gate uses the x-span of the BEAMED group, padded by a notehead width.
`Q.TUPLET_MARKER` records `x0`, `x1`, `x_center` and **no `y` at all** — so the
staged record cannot even ask *does this digit clear the staff*.
`Q.TUPLET_MARKER_POSITION` (default OFF, read by nothing) is the fact that
would.

### 4. Stage by stage — ONE OF SIX REACHES A QUANTITY

⚠️⚠️ **`_TUPLET_CLASSES = ("tuplet3", "fingering3", "tupletBracket",
"tupleBracket")`** (`gather.py:690`). So on the staged path:

* **`fingering3`** → `Q.TUPLET_MARKER` → `adjudicate_tuplet_ratio` →
  `<time-modification>`;
* **`fingering0`, `1`, `2`, `4`, `5`** → **no quantity, no decision, no export**.
  `export.NOT_NOTATION["fingering"]` declares the family *"a performance
  marking, not a notation family we export"*, and `_claims` is
  longest-prefix-wins so `fingering3` still routes to `tuplet`.

⚠️ **And that tuple is NARROWER than the legacy rule, which is a staged/legacy
divergence worth naming.** `rhythm._TUPLET_DIGIT_PREFIXES = ("tuplet",
"fingering")` reads *any* tail, and `_tuplet_groups` uses a `fingering1` or
`fingering2` deliberately — *"taking the first digit inside the group meant an
unreadable one VETOED a readable one sitting in the same group… Mozart 41
detects a `fingering1` and a `fingering2` beside its 30 `fingering3`."* Those
rows do not exist on the staged record at all, and neither do `tuplet1`,
`tuplet2`, `tuplet4`–`tuplet9`. MEASURED HERE (grep).

⚠️ `adjudicate_tuplet_ratio` **fired ZERO times across 286 runs** of the
plumbing matrix on fixtures printing explicit tuplets
(`tools/omr/staged/positions.py:420`, `reach.py`). So the staged reach of this
whole path is unestablished.

### 5. Abstain or best-guess — and what leans on it

`adjudicate_tuplet_ratio` abstains rather than guesses a normal-count: only
`3:2` is acted on at all, and `COARSER_THAN_CANONICAL["tuple"]` refuses to
rename a countless `tuple` to `tuplet3` because that *"would assert a triplet
the page never claimed."*

**What leans on it: `Q.DURATION`.** `TUPLET_RATIO` is ORDER 20 and `DURATION`
is 21, *"because a tuplet decided afterwards would arrive too late and every
triplet would export at its written value."* A wrong tuplet is a wrong RHYTHM
for three notes; a missed one is three notes 50% too long.

**Independence:** the digit and the beam group come off the same raster and the
same detector. A page whose beams are unreadable is a page whose beamed-group
span is wrong, so the positional gate goes silent exactly where the digit is
most likely misclassified. That is *the bars are not an independent umpire*
in a new family. ASSERTED — not measured.

**Evidence grade:** `[C53]`, `[C54]` MEASURED HERE; the staged/legacy class-list
divergence MEASURED HERE; the independence claim ASSERTED.

---

## The REHEARSAL letter

A boxed or bare capital — `A`, `B`, `[12]` — printed above a system to anchor a
rehearsal point across every part.

### 1. What sets it apart — and what it is confused with

It is a **single character**, above the staff, at a bar head, and it is the same
shape as a dynamic letter, a clef, or a fragment of anything. `[C75 + L68]`'s
sibling: position is the only separator, and the position is the same one a
measure number occupies.

Confused with: a **dynamic letter** (`f`, `p` are single characters in the same
band on the other side of the staff); a **measure number** (same corner); an
**instrument number** in the margin.

### 2. Best method

Untried. ⚠️ **A lexicon cannot gate a single character**, which is the reason
this repo already gives for not reading letter dynamics with OCR: *"a single
character has no lexicon to be gated by"* (CLAUDE.md, the dynamics scope). So
every argument that makes the direction reader safe fails here, and something
else would have to do the gating — most plausibly the SEQUENCE (`A`, `B`, `C`…
in order across a movement), which is a document-level fact and not a page one.

### 3. Where on the page the deciding information lives

Above the top staff at a bar head, and — per `[C75 + L68]` and IU — *"sometimes
additionally on a specific line of the grand staff, such as above the first
violins"*, i.e. the same doubling `[L69]` gives the tempo mark.

### 4. Stage by stage — NONE

**Not in the 208-class space** (verified here: no class name contains
`rehears`). **No quantity, no gatherer, no decision, no export.** The direction
lexicon refuses it twice over — by the digit/bracket regex for `[12]`, and by
the *at least one real term* rule for `A` (`lookup('A')` → `None`, verified
live). MEASURED HERE.

### 5. Abstain or best-guess — and what leans on it

Nothing asks; nothing leans. **What it would buy** is stated in
`docs/exploration-what-is-on-the-page-2026-09-09.md`: it corroborates
`measure_partition` exactly as a measure number does, **and it anchors ACROSS
PARTS** — which a measure number does not, because our measure numbers are
per-part until `export._document_bar_offsets` renumbers them. A rehearsal letter
is the only printed mark on the page that names one instant in every part at
once.

**Evidence grade:** class-space absence MEASURED HERE; lexicon refusal MEASURED
HERE; everything else LITERATURE (`[L68]`) or ASSERTED.

---

## `numeral0` – `numeral9` and `numeral` — the coarse class

Eleven of the 208 class names (ids 136-207, the coarse annotation vocabulary).
Not a symbol on the page: a **spelling** the detector may return for a digit
whose role it is not committing to.

### 1. What sets it apart — and what it is confused with

It is the class-space expression of the DIGIT confusion:
`COARSER_THAN_CANONICAL[f"numeral{d}"]` says it in terms — *"The coarse
vocabulary has one numeral class for time signatures, tuplet digits, fingerings
and measure numbers alike, and the fine one splits them (`timeSig4`, `tuplet4`,
`fingering4`)."*

⚠️⚠️ **`numeral4` is NOT `timeSig4`, and the entry states the cost of getting
that wrong**: five `timeSig4` once fired on **barline fragments** and shipped a
2/4 page as common time at **390 LilyPond bar-check failures against 164 for no
meter at all** (`tools/omr/class_aliases.py:90-101`, MEASURED HERE).

### 2. Best method

Not applicable — it is an alias question. `class_aliases.unaccounted()` fails
the suite on any class name in neither `ALIASES` (11 exact twins, renamed) nor
`COARSER_THAN_CANONICAL` (21 entries, kept apart with what closing each would
take). **A wider class space is a loud failure, not a silent drop.**

### 3. Where on the page the deciding information lives

Nowhere new — the same positional facts as `[C53]`. The point of the entry is
that the class name may not stand in for them.

### 4. Stage by stage — NONE

Nothing gathers a `numeral*`. It is not in `_TUPLET_CLASSES`, not in
`_METER_CLASSES`, not in any family prefix.

⚠️ **Live exposure is ZERO today and the risk is on the LABELING side.** The
coarse block (ids 136-207) fires **zero times across 3 engraved fixtures and 29
scanned pages of 9 publishers** (CLAUDE.md, the 208-class-space entry, MEASURED
THERE). What makes it live is that `data/user-labeled/catalog.yaml` carries
coarse spellings at ids 190-195, so **the next fine-tune trains ids the exporter
cannot read**.

### 5. Abstain or best-guess — and what leans on it

The refusal to alias IS the abstention, and it is enforced by a derived check
rather than by discipline.

**Evidence grade:** MEASURED HERE (class list, alias tables); the zero-firing
figure MEASURED elsewhere and quoted.

---

## The LYRIC

Sung text under a vocal staff, syllable by syllable, hyphenated across notes.
**Not in the 208-class space, no reader, no quantity, no decision** — and the
tree says so deliberately. `export_coverage.KNOWN_GAPS["lyric"]`: *"We do not
read vocal text at all and there is no detector for it. **Out of scope rather
than missing.**"* MEASURED HERE (class list verified here; KNOWN_GAPS read).

That is the right status for a corpus of conductor's scores of orchestral
symphonies. It gets a section for two reasons: the band it would occupy is
already searched by something else, and vocal text already bites this pipeline
somewhere unexpected.

### 1. What sets it apart — and what it is confused with

⚠️ **The lyric line occupies the same band the direction reader searches** — the
strip below the staff — and it is made of the same ink: letters, word-shaped,
letter-height, passing every one of `BandConfig`'s shape tests. So on a vocal
page a lyric syllable IS a direction candidate, and the only thing separating
them is the lexicon: `legato` is in it, `-ri-` is not.

What a lyric has that a direction does not is a MECHANICAL relation to the
notes — one syllable per notehead, in x order, hyphenated where a word spans
several. Nothing in this repo has ever looked for it. ASSERTED.

### 2. Best method

Unbuilt. It would be the direction reader's own pipeline with a different gate:
the lexicon cannot be the gate (a syllable is not a word), so the gate would
have to be the one-syllable-per-notehead alignment.

### 3. Where on the page the deciding information lives

Immediately under the staff, above the dynamics row, aligned in x to the
noteheads. That is the collision: the direction reader's below-band runs from
`0.25` spaces clear of the bottom line all the way to the next staff.

### 4. Stage by stage — NONE

No quantity, no gatherer, no decision, no export, and no detector class.

### 5. Abstain or best-guess — and what leans on it

Nothing asks; nothing leans. ⚠️ **What the direction reader would do is the
part worth predicting**: the lexicon would refuse every syllable (correct), but
the CANDIDATE count would explode — the reader's cost is ~0.5–5.1 s per
candidate crop, and on an opera page every bar of every vocal staff proposes
one. Predicted consequence, **ASSERTED, not measured**: acceptance rate crashes
toward zero and wall-clock cost rises by roughly the number of sung bars. The
corpus already holds two operas (`OMR_CHOIR_GROUPING`'s library probe names
them), so this is testable without new material.

⚠️ And the converse is worth recording: `[C71]`'s known exception is
**Handel's *Messiah* printing `BASSO` (the bass VOICE) and `Bassi` (the string
basses) on one page** — so the one place vocal text already bites this pipeline
is the INSTRUMENT LEXICON, not a lyric reader.

**Evidence grade:** class-space absence and KNOWN_GAPS status MEASURED HERE;
the band-collision prediction ASSERTED.

---

## Text read AS a musical symbol — the mirror case

⚠️ **This section is a failure MODE, not a symbol, so it does not take the
five-question template** — there is no stage that decides "is this ink a
letter?", which is the finding. It is the one this family contributes most of.

**Start from `docs/position-grammar-confusables-2026-09-04.md` §2 BOWL / BLOB**
— *"The bowl of a legato `g`, the lower bowl of a 6/8's `8`, and a clipped
neighbour-staff head are all hollow-notehead-shaped."* This dossier agrees, and
adds the cases found since that entry was written.

### The inventory, every entry measured

| the ink | read as | where measured |
|---|---|---|
| the bowl of the **`g` in `legato`**, printed between staves | `noteheadWholeInSpace` | `transcribe.py:509` — 2 of the 7 whole-notehead detections on a Brahms page whose truth holds **no whole note at all** |
| the **lower bowl of the `8`** of a 6/8 above | `noteheadWholeInSpace` | same list, 1 of 7 |
| the descender bowl of the **`g` in `Allegro`** | a whole note on Beethoven's Flute 1 | `transcribe.py:3617` |
| the word **`legato`** between Brahms's oboe staves | a `D6` | `transcribe.py:3618` |
| the **`e` of the printed word `cresc`** | a notehead | `benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md:109` — 1 of 46 non-notehead boxes on Breitkopf |
| a printed capital **`B`** | a notehead | same, 1 of 46 |
| a **trill wavy line** | a notehead | same, 1 of 46 |
| **the two round counters of a printed time-signature `8`** | two noteheads | same §5 — **8 of 17** adjudicated whole-heads-with-a-direction, three of them on one cautionary `9/8` |
| the **`p` of `espr.`** | `dynamicP` at confidence **0.87** | `direction_text.py:178` |

⚠️⚠️ **The time-signature counters are the case that does not fit the family,
and the breakthrough document is right about why.** Every other row is *a
non-music mark read as a notehead* — a boundary error of the ordinary kind. The
counters are a **sub-part carved out of a bigger glyph**: nothing inside the box
disagrees with `notehead`, and only the surrounding INK does
([docs/breakthrough-2026-09-18-the-unit-of-enquiry.md](../breakthrough-2026-09-18-the-unit-of-enquiry.md)
§3). A width or height test cannot reach it; a test that asks what the box is
PART OF can.

### The two shipped discriminators, and what they do not reach

1. **A notehead is a staff space tall.** `_drop_clipped_notehead_fragments`,
   restricted to detections that TOUCH a cell edge. Fragments 0.29–0.56 spaces,
   genuine interior heads 0.61–1.12, notes a crop merely grazes 0.77–0.99 —
   *nothing in between*, measured over 594 noteheads across three works. Worth
   pooled OMR-NED **0.2209 → 0.2137**. MEASURED HERE (CLAUDE.md, `transcribe.py:495`).
2. **A notehead outside the staff must hang on a ledger ladder.**
   `_drop_unladdered_noteheads`, needing ALL of: centre outside the band, at
   least one rung expected, none found, confidence below
   `_UNLADDERED_NOTEHEAD_MAX_CONF = 0.65`. The four measured fakes run 0.45–0.53;
   the lowest real outside-staff notehead is **0.76**. This is the rule that
   catches the `Allegro` `g` and the `legato` `D6`. MEASURED HERE.

⚠️ **Neither rule can reach ink printed INSIDE the staff band**: the first
fires only on a detection TOUCHING a cell edge, the second only on a centre
OUTSIDE the five lines. A time-signature `8` fills the staff's height by
construction `[L42]`, so its counters are out of reach of both — and the
crop-pass record does not say where on its cells the `e` of `cresc` and the
capital `B` fell, so those two are **unattributed**, not shown to be reachable.
`position-grammar` §2 BOWL/BLOB lists the two rules above and does not claim
more; this dossier confirms the gap is still open, and names the measured floor
that would reach most of it: **a width floor at `< 1.0` staff spaces catches 39
of the 46 non-notehead boxes at a cost of 0 of 63 real stems**
(`benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md:115`) — *"measured and NOT
proposed: it is a GATHER change."*

### Why this belongs in the TEXT dossier

Because the fix that would reach all of it already exists, in this family, and
is pointed the other way. `direction_text._blank_detections` subtracts every
detection from the page's ink so that *"find the text"* becomes *"find the
ink"*. The inverse — subtract the ACCEPTED WORDS from the ink before the
detector's noteheads are believed — has never been tried, and it would be
ordering-impossible today: `A-GATHER-1` records **detection before direction
text** as one of only three forced edges in GATHER, because the word reader
needs the detections to subtract. ASSERTED; nobody has costed breaking that
cycle.

---

## What we do not know

1. **Accuracy of any accepted word.** Twelve words over two documents, and
   `benchmarks/omr-staged-direction-2026-09/FINDINGS.md` says it plainly:
   *"EQUIVALENCE, not truth: no word has been checked against the print."*
2. **Recall of the word reader.** 42 and 56 candidates are what the CV
   PROPOSED, not what the pages print. Nobody has counted the printed
   directions on either page.
3. **Whether the staged roster layer fixes the three known label defects
   end to end.** The probe in this session says `Basso.`, `Alto e Tenore` and
   `mbone Basso` all resolve correctly against the committed Beethoven 5
   roster — but the only staged run measured against print truth predates the
   roster producer by three days.
4. **Whether the OCR rungs sample.** Two committed documents disagree (see the
   margin-label §2). It matters because every end-to-end scan number this
   project holds was taken from a single run, and the label rungs are on by
   default.
5. **Reach of the measure number and the rehearsal letter.** `[C75 + L68]` is
   ASSERTED on one sentence about three of four editions. Nobody has counted
   printed system-start numbers per edition, and that is the first measurement
   either symbol needs.
6. **Whether a mid-score tempo change is ever printed in the `above` band on a
   document we hold.** The `above` band is unexercised by both committed
   documents, so `above_first_measure_only`'s cost is unmeasured in both
   directions.
7. **What a vocal score does to the direction reader's candidate count.**
   Predicted, not measured; the corpus holds two operas.
8. **How much of the label ladder's measured Phase-2 work is actually in the
   tree.** One rule reported as SHIPPED (the shared/brace-centred block, +11
   labels) lives only on `claude/staff-identity-labels-2026-09-05`. Nobody has
   checked the rest of that FINDINGS file the same way.
9. **Whether `[C71]` and `[C74]` are worth porting to the staged path.** Both
   are measured and shipped on the legacy path and neither exists in
   `tools/omr/staged/`. Their reach there is unknown because no staged run has
   had margin labels AND a roster AND a second system on a document that
   collides.

---

## Questions for Sean

1. **A rule this repo measured and reported as SHIPPED is on a branch only** —
   the shared/brace-centred margin block, `672607c9`, +11 labels and coverage
   0.654 → 0.681, not on integration and not on main. Do you want it landed, or
   re-measured first? It has been 15 days.

2. **`Basso.` → Bass voice is still live in the lexicon at `high` confidence,
   and three different channels can overturn it** — the roster (staged,
   default ON since 09-17), the score-order ambiguity guard (legacy only), and
   the document-language reading (legacy, default OFF). Should the staged path
   get one of the other two, or is the roster enough? The roster is the only
   one of the three that does not come off this raster.

3. **The direction reader costs ~267 s/page on a Litolff scan and returns six
   words, all `cresc.` in three casings — and 144 edits on the engraved
   benchmark.** `OMR_DIRECTION_TEXT_SCAN_GATE` is built and default OFF. Do you
   want it on? It gates on a positive proof of scan, so a hybrid page keeps the
   reader.

4. **The measure number is the only printed witness to a bar count that we
   currently derive from barline geometry alone.** Is it worth a reach pass —
   *how many of our held editions print one, and is it legible?* — before
   anything is built? The convention is graded ASSERTED on one sentence.

5. **A rehearsal letter anchors across PARTS, which nothing else on the page
   does.** A single character cannot be gated by a lexicon. Is the SEQUENCE
   (`A`, `B`, `C`… in order down the movement) the gate you would trust, or is
   there an engraving fact about rehearsal marks that separates them from every
   other single character on the page?

6. **`fingering3` is, on orchestral scores, a misspelled triplet digit — 33 of
   33 sit in a cell holding a real triplet.** The staged gatherer reads only
   `fingering3` and `tuplet3`; `fingering1`, `fingering2` and `tuplet4`–`9` are
   detected and reach no record row at all. Is there a conductor's-score case
   where a real fingering is printed, or is the class simply mislabelled for
   this repertoire?

7. **A metronome mark is refused at the lexicon before it is an export gap.**
   Reading it needs a gate that is allowed to see digits. Is the note glyph
   beside the `=` the anchor you would use — *a notehead standing above a
   system with no staff under it is not a note* — or is there something better?

8. **The label vanishes exactly where the clef needs it: 29 of 29 unresolved
   non-treble staves print no label.** That is a publisher convention, not a
   reader fault, and it means the label channel and the clef channel go silent
   together. Is there a printed fact on a continuation system that names a
   string staff, other than the clef itself?
