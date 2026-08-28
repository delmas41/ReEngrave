# ReEngrave — backlog / research notes

Forward-looking ideas. Not yet scoped, not yet scheduled. Surface these to Sean at the start of a ReEngrave session.

---

## 🧭 Contextual analysis roadmap (2026-08-28) — ACTIVE

**Sean wants all of these; they are ordered here on purpose.** The framing: a human
reading a large score deduces most of it from context — which staves are concert vs
transposing, what instrument order and groupings to expect, and once the key is known,
what the accidentals must mean. ReEngrave currently deduces none of that. Every page
re-derives clef and key from scratch, and the exporter names parts
`Page0-System1-merged` (`tools/omr/export.py:716`) because **there is no persistent
part identity anywhere in the pipeline.**

The four human deductions and where they stand:

| Human deduction | Repo status |
|---|---|
| *this staff is Clarinet in B♭* | nothing — no instrument identity at all |
| *…so it transposes, expects treble, lives in this range* | transposition math exists (`transcribe.py:1450`) but has nothing to attach it to; it guesses offsets |
| *staves run winds→brass→perc→strings in these groups* | bracket gaps are used only to split systems (`staff_detector.py:194`); the grouping is then discarded |
| *key is X, so these accidentals mean Y* | M4 re-rank does this, but off one global detected key, not per-staff |

### #1 — Persistent staff/part identity ("slots") — **IN PROGRESS**

**Step 1 DONE (2026-08-28): system grouping rebuilt on vertical connectivity.**
`tools/omr/system_grouping.py` + wired into `staff_detector.detect_staves`. Slots are
assigned per system, so correct systems are a hard prerequisite — and the gap-size
heuristic was badly wrong on exactly the scores that matter. Full writeup:
[benchmarks/omr-system-grouping-2026-08/findings.md](benchmarks/omr-system-grouping-2026-08/findings.md).

Measured on 14 pages (Beethoven 9 + Beethoven 5 p10 at 300 and 600 dpi), against
ground truth read off the **left brackets**:

| | gap heuristic | connectivity |
|---|--:|--:|
| system count correct | **6/14 (43%)** | **12/14 (86%)** |
| spurious single-staff "systems" | **19** | **0** |

The cause is named in the old code's own comment: its MAD rule deliberately split at
"a clearly-bigger-than-normal gap between bracketed sub-systems (winds vs brass vs
strings)" — but those blocks are *inside* one system. Signal used instead: **a system
break is a gap that no vertical ink crosses** (barlines and the bracket run through a
system; nothing crosses between two), the same fact
`measure_extractor._intersystem_connectivity` already uses one level downstream.

**Bonus: this also recovers the instrument-family grouping** as `Staff.group_index`.
Bridging counts are trimodal — `0` = system break, `~4-25` = bracket-group boundary
(only the bracket crosses), `~35-95` = inside a group. Visually verified on Beethoven 9
p70: two systems, each grouped **4 woodwinds | 2 horns | 5 strings**. That is direct
input to #3, and it means the old detector was finding the right *groups* and
mislabelling them as systems.

Remaining failures (2/14) are **merges** — a real break that something crosses. The old
heuristic fails the opposite way, shredding one system into as many as 12.

**Method warning, worth remembering.** Two attempts at ground truth were wrong before
the bracket crop settled it, and both produced confident numbers: a ground-truth-free
proxy ("instrumentation is constant, so staves-per-system should cluster tightly")
rewards merging everything into one system; and counting systems off a whole-page
thumbnail mislabels single 13-staff systems as 2, because at that scale the
brass-to-strings gap looks like a system break. Render the left margin and count
brackets.

Traps found, each costing a measurement, all documented in the module: `Staff.x_start`
is unusable as a scan window (p60 staff 3 reports 885 against ~275 for its neighbours);
the window must reach *past* the staff extent to see the bracket and the closing
barline; and coverage needs vertical gap-closing or it is resolution-sensitive
(B5 p10 grouped as 2 systems at 300 dpi and 4 at 600).

**Step 2 DONE (2026-08-28): stable slot ids.** `tools/omr/slots.py` +
`Staff.slot_index`. Index matching does not work, because **a system omits the staves
of instruments tacet through it** (Beethoven 9 p65 carries systems of 7 and 11 staves
on one page — the same orchestra, four parts resting). Score order is monotone, so
this is a **sequence alignment**, not a matching problem: each system aligns against a
reference layout by DP, deletions allowed on the reference side, reordering
disallowed. Driven by, in descending strength, instrument labels (a label *conflict*
is the only hard constraint available), bracket group, then relative position.

Reference layout recovered on Beethoven 9 — exactly the real orchestra:

    Flute, Oboe, Clarinet, Bassoon | Horn, Horn, Trumpet, Trumpet | 5 strings

Measured over 12 pages / 207 staves (`benchmarks/omr-system-grouping-2026-08/eval_slots.py`):
**191/207 staves assigned a slot; label purity 92% (93/101)** — of every (slot, label)
observation, the fraction agreeing with that slot's modal instrument. No hand
labelling needed: the labels come from the text layer, and the question is only
whether the alignment keeps them consistent.

**One bad system boundary poisons the whole document**, so guard the reference. The
first run built it from p25 — one of the two pages `system_grouping` merges — and got
a 24-slot reference listing Flute..Trumpet *twice*, after which 20 of 24 slots had an
unstable bracket group. Fixed by rejecting a candidate whose label sequence repeats an
instrument non-adjacently (`_looks_merged`, the precise guard) plus a permissive size
cap for documents with no labels at all. Note the cap must stay permissive — an
earlier 1.5x-of-median cap threw away the genuine full system whenever most systems
were condensed.

Remaining: 16 unassigned staves, all on the two merged pages (a 24- or 18-staff
"system" cannot fit 13 slots), and 8 single-observation label disagreements
concentrated in one misaligned system.

**VERIFIED 2026-08-28 — single-line percussion staves are invisible.**
`_group_into_staves` only accepts five-peak evenly-spaced windows, so a one-line
percussion staff produces no `Staff` at all. Synthetic proof + consequence in
`tools/omr/tests/test_system_grouping.py::test_detect_staves_misses_a_single_line_percussion_staff`:
on a page of 3 five-line staves plus one 1-line staff, the detector returns 3, and
**every staff below the missing one carries a `staff_index` one lower than its true
slot**. Not yet fixed — fixing it means relaxing the 5-peak rule without regressing
staff detection. Track as a slot-numbering hazard for Step 2. (The old "Phase 1 has
no regression baseline" objection is retired — main's 9509990 / e6a4110 corrected
the Phase-1 expectations against the pages themselves.)

### #1 (original framing) — why slots are the keystone
Assign every staff a stable part id across all systems and pages. Signals available
today: y-order, staves-per-system, bracket/brace topology at the left edge
(`system_left_edge()` in `staff_header.py` on branch
`claude/key-signature-recognition-57ec0a` already measures where the bracket ends and
the staff begins), inter-staff spacing, header-window ink signature.

Hard case — **condensed systems**: page 4 has 11 staves, page 5 has 8 because the
winds are tacet, so index 3 is now a different instrument. Naive index-matching breaks
exactly here; this is where a human stops counting and reads the labels (#2b).

Unlocks: clef continuity across page breaks instead of the silent treble default
(`transcribe.py:519`); the dossier plan's `slot→staff` join without hand input;
per-instrument range priors; **and it is the absolute register anchor that #4 turned
out to require.**

### #4c — Clef from the instrument's written range — **SHIPPED 2026-08-28**
`tools/omr/clef_correction.py` + `tools/omr/contextual.py`. The retry of the #4
negative, now that #1 supplies the **absolute register anchor** every earlier
mechanism was missing. A clef hypothesis is a constant diatonic shift of the staff's
pitches (`pitch_resolver.clef_diatonic_shift`), so this is a post-pass over built page
dicts — no image, no re-detection.

Range fit alone is not decisive: a bassoon staff fits bass 1.00 and tenor 0.95 (both
real bassoon clefs), a viola fits alto 1.00 and treble 0.98. So the **instrument's own
default clef leads and the range vetoes it** — the same reasoning a reader uses
("violas read alto, unless what I see says otherwise"). That is sound exactly where
this may act, because it only applies where no reader read the clef, and there the
clef in effect is a positional guess carrying no evidence.

**Complementary with the clef-geometry layer, not overlapping.** Measured on
Beethoven 4 p59 after merging main: main's readers supplied 5 of 11 staves
(`clef_source=detector`), all correct; 6 stayed DEFAULTED to treble. This pass fixed 3
of those 6 — Bassoon→bass (fit 0.06→1.00), Viola→alto, Contrabass→bass — restating 84
noteheads, and touched nothing main had read.

**The integration trap, worth remembering:** the gate must consult
`staff["clef_source"]`, NOT a scan for a `category == "clef"` detection. `clef_locator`
/ `clef_geometry` read a clef by shape and by which staff line it sits on and emit **no
clef detection at all**, so a detection scan calls such a staff "silent" and this pass
would overwrite a confidently-read clef.

Limit: instrument identity comes from the text layer, so this is a no-op on the ~72% of
the corpus without one. That is the argument for finishing #2.

### #2 — Margin reading (instrument names)
No OCR anywhere in the project (`backend/requirements.txt` has none). Two paths:
- **PDFs with a text layer — MEASURED 2026-08-28: 18/65 (28%) of the IMSLP corpus.**
  PyMuPDF is already imported (`preprocessing.py:18`) and used only to rasterize.
  `page.get_text()` returns the instrument abbreviations directly — sampled pages gave
  `Fl. / Ob. / Cl. / Fag. / Cor. / Tr. / Timp. / Vl. / Vla. / Vc. / Cb.`, and one gave a
  full instrumentation list: `2 Flauti / 2 Oboi / 2 Clarinetti in C / 2 Fagotti /
  2 Corni in C / 2 Trombe in C / Timpani in C.G / Violino I`. These are OCR'd text
  layers over scans (surrounding music glyphs come out as garbage), but the *labels*
  are clean. With bboxes they join to staves by y-position. **Free instrument identity
  on ~a quarter of the corpus** — do this before any OCR/VLM work.
- **Scans**: crop left of `system_left_edge` → OCR or a VLM call.

Then fuzzy-match a multilingual instrument lexicon (Flauti/Flöten/Fl., Clarinetti in
B, Corni in F, Vcl., Kb.) → canonical instrument → **transposition + expected clef +
range in one lookup**. That single join delivers three of the four deductions.

Caveat: `benchmarks/vlm-vqa-pilot-2026-07` found Claude tops out at 89.7% *counting
symbols in degraded crops*. Reading a printed word in a clean margin is an easier and
different task — but that is an assumption, not a result. The pilot harness is
reusable to test it for ~$1.

### #3 — Score-order prior as constrained alignment
Score order is **monotone** — instruments never appear out of family order. So "which
instrumentation is this?" is a dynamic-programming alignment of the observed staves
against a small library of standard layouts (Classical pairs / Romantic / large late
Romantic / string quartet / piano / lead sheet), **not** free classification. Cheap,
deterministic, and it fuses every weak signal at once: bracket groups, staff count,
margin text, detected clefs, observed register, key-signature offsets.

This is a better shape for the parked SmartScore ensemble idea above: vote on
**instrument identity**, from which clef falls out as a consequence, instead of voting
on clef directly.

### #4 — Key from the music — ⛔ **the clef half is DISPROVEN (2026-08-28)**
Sean's heuristic: *"I can determine a key signature because of the clear repetition of
a root note — it starts and ends on an A, so I look for no sharps and flats, or 3
sharps."* Proposed use: turn key-fit into a **clef** diagnostic (a tonal estimate built
on a wrong clef is confidently wrong).

**Measured and killed.** See `benchmarks/omr-clef-key-fit-2026-08/findings.md`. Four
mechanisms, none beating the trivial always-treble baseline (68.7%): per-staff KS key
fit is noise (median best-vs-2nd margin **0.0000**, 62/80 staves under 0.01);
accidental letters show no circle-of-fifths concentration under any clef hypothesis;
register-ordering scores **56.7%** (12 points *below* baseline); consensus-key fit
scores **exactly** baseline (46/67 both).

Root cause, now confirmed with numbers on real data rather than asserted: **a staff's
note geometry is clef-invariant.** Changing the clef relabels every note by the same
interval and preserves every interval between notes, so contour, interval content and
key-profile statistics all move with the hypothesis and cannot discriminate it. This
is exactly what `docs/dossier-verification-plan.md` §2 already claimed.

**So #4 is blocked on #1, not independent of it** — the absolute register anchor every
mechanism was missing is precisely what instrument identity supplies.

Two retry conditions:
- **Key-signature glyph positions** genuinely *are* clef-dependent (F# sits on the top
  line in treble, the fourth line in bass), but `main` stores only *counts* —
  `_detect_key_sig_from_cell` counts `keySharp`/`keyFlat` and discards positions
  (`transcribe.py:590`). Positional reading exists on branch
  `claude/key-signature-recognition-57ec0a`. **Retry there, not on main.**
- Notehead + accidental recall on dense orchestral pages improving enough that the
  tonal statistics stop being noise.

Still open and untouched by this result: using key context to *interpret accidentals*
once the key is known from elsewhere (that is M4's existing job, just fed a per-staff
key instead of a global one), and inferring the **key signature** itself — Beethoven 5
reads `0 sharps / 0 flats` on all 18 staves when it is in C minor.

### #4b — Infer the KEY SIGNATURE from the music — **OPEN, wanted (Sean, 2026-08-28)**
Untouched by the #4 negative, which killed only the *clef* half. Sean's heuristic:
*"the clear repetition of a root note — it starts and ends on an A, so I look for no
sharps and flats, or 3 sharps."*

Live evidence that this is a real, unflagged error class:
- **beethoven-5 p15 reads `0 sharps / 0 flats` on all 18 staves** — the movement is in
  C minor (3 flats), and there are 33 inline flat detections on the page.
- **ravel-bolero p10 reads five different signatures across 32 staves** (0,1,2,4,5
  sharps) for a piece in C major. The shipped check (b) catches only **1** of them.

Why it is a different problem from #4, and more tractable: the key signature is a
*global* property corroborated by many staves at once, so cross-staff voting applies
(check (b) already has the transposition machinery), whereas the clef is per-staff and
clef-invariant in the geometry. Candidate signals: inline-accidental letter statistics
aggregated over a whole page rather than one staff; a flat:sharp ratio far from
balanced implying the signature is missing accidentals; tonal frame of the lowest
staff. **Do not reuse per-staff KS profile fitting — measured as noise (#4).**

Prerequisite worth checking first: whether the failure is *reading* the signature or
*detecting* the glyphs at all (beethoven-5 has 1 `keySharp` detection on the whole
page, so it is likely detection, in which case the fix belongs with the positional
key-signature reader on `claude/key-signature-recognition-57ec0a`).

### #5 — Auto-populate the dossier
`docs/dossier-verification-plan.md` requires hand-input facts. #1–#3 make it
self-populating: derive the instrumentation from the score, ask Sean only to
confirm/correct — the same model-proposes / human-adjudicates loop as the annotate UI.
Plus title-page text → work lookup → measure counts and key plan (the parked GKB item).

### Training-side note — can YOLO be trained on context? Mostly no.
The pipeline feeds YOLO **canonical cells**: each measure sliced out and rescaled so
staff span is constant. That normalization buys scale invariance and 98.8% F1 and it
**destroys exactly the context in question** — margin label, neighbouring staves, page
position, everything before this bar. A per-cell detector cannot learn what it never
sees. Three fine-tune campaigns already failed (catalog training collapse; ScoreAug
worse than clean control; clef fine-tune cratering dense-page noteheads 2506 → 114).

What is *not* dead:
1. **A separate small model on a different input** — a header/margin reader trained on
   crops that actually contain context. Never touches production weights, so it
   structurally cannot cause forgetting. The clef-ft post-mortem already named this.
2. **Contextual re-scoring with the detector frozen** — everything below conf 0.25 is
   currently discarded and only the argmax class survives. Keep the pre-NMS candidates
   and let the contextual layer re-rank. M4 does this for pitch; extending to *class*
   is the same trick at zero training risk.
3. **End-to-end sequence models as a second opinion** (LEGATO / oemer / homr) — they
   read clef and meter contextually by construction. Host-side, not a replacement.

### Structural bugs noticed while surveying
- ~~five-line-only staff detection~~ — **VERIFIED, see #1 above.**
- Nothing excludes unpitched/percussion staves from the key and pitch checks
  (still unverified).

---

## ⏰ REVISIT — ensemble recognition for clef + detail prediction (2026-07-10)

> **PARTLY OVERTAKEN (2026-08-27).** The clef half of this turned out not to need
> an ensemble at all. Alto vs tenor (and soprano/mezzo/baritone) is not a
> recognition problem — they are the same glyph on different staff lines, so no
> number of classifiers voting on appearance can resolve it. Measuring the
> glyph's position does, exactly. Shipped as `tools/omr/clef_geometry.py` plus a
> classical-CV C-clef locator for scores where no model sees a clef at all;
> results in `benchmarks/omr-clef-geometry/RESULTS.md`. **Still open from this
> item:** the *time-signature* half, and clef/key/time state resets across pages
> (the continuation-page clef inheritance is handled by `_ClefContinuity`, but
> the underlying detection weakness is not).

**Sean flagged this and asked to be reminded to come back to it (dated reminder set ~2026-07-17).** **SmartScore 64 Professional** (Musitek) uses an **ensemble recognition tool** specifically to help predict **clefs and other details**. Investigate how it works and consider adopting the technique.

**Why it's worth doing:** the July 2026 audit found clef handling is a real ReEngrave weakness — clef/key/time state resets across pages and relies on the detector catching courtesy clefs; a missed continuation-page clef silently defaults to treble (or bass for staff 2 of 2), shifting every pitch on that staff. Time-sig digit detection is similarly unreliable. A voting/ensemble predictor for these fields would target both directly.

**Note the distinction:** this is an *internal* ensemble (several classifiers/heuristics voting on ONE field like clef), NOT the multi-*engine* OMR voting from the July research (Padilla et al. ISMIR 2015), which was skipped because ReEngrave has only 2 unequal engines.

**To resolve when we pick this up:**
- Research how SmartScore 64 Professional's ensemble recognition actually works before designing anything.
- Decide the cheapest ReEngrave adaptation: a per-staff clef-stability + key-signature-plausibility re-rank pass (no new model) vs an actual classifier ensemble; check whether the same voting extends to time-sig digits.

---

## ~~Staff detection on mixed text/music pages~~ — DONE (2026-08-28)

Body text was being detected as staves (147 of 1522 "staves" over 156 pages of
Nottebohm). Fixed in `staff_detector._line_ink_runs_per_space`: a staff line is
one continuous stroke (a handful of ink runs over its whole length, even
dashed), a text baseline is one run per letter. Music tops out at 1.39 runs per
staff-space, text starts at 2.02, medians 0.017 vs 2.59.

Every music-only score is byte-identical; prose pages now yield zero staves,
and p.92 went from 0 barlines / 12 cells to 10 / 26 because dropping the text
blocks let system grouping and barline voting work again.

**Two plausible discriminators that DON'T work** — don't re-propose them:
- *Ink coverage along the line.* Separates on clean pages, overlaps on real
  ones: notation ink interrupts the line, so genuine Beethoven 5 / La Mer
  staves fall to 0.62-0.70, on top of body text at 0.62-0.72.
- *Staff span vs the page median* (which this note previously recommended).
  Works only on mixed pages — on unbroken prose the median is itself
  text-derived and nothing is an outlier.

> **The related x-extent half is also fixed, twice over and on purpose.** This
> note used to pair the text-as-staves problem with `_staff_x_extent` returning
> the longest strictly-contiguous ink run, so the measure cell began past the
> clef. Both fixes are now in and they are complementary, not duplicates:
>
> - `staff_detector._staff_x_extent` now bridges breaks up to a staff space, so
>   Phase 1 returns the real extent and the cell contains the header again
>   (6/12 → 12/12 clefs on the Nottebohm ground-truth page).
> - `tools/omr/staff_header.py` measures each staff's header WINDOW beside
>   Phase 1 — left edge walked back to the system's initial rule, right edge at
>   the first barline. It was written when the Phase-1 fix looked too risky to
>   attempt without a regression baseline, and it stays because the CV readers
>   want a tight crop that Phase 1 has no reason to produce: the key-signature
>   locator reads that window, and the clef readers fall back to it only where
>   the measure cell still starts past the header, which the Phase-1 fix now
>   makes rare rather than routine.
>
> The regression baseline that blocked the Phase-1 change was itself built in
> the same round (`test_pipeline` expectations checked against the pages), so
> the reason for working around Phase 1 no longer applies to future work here.

Also: the first measurement pass labelled p.25 and p.29 as "text" when both
contain music examples, which made the separation look marginal. Check page
contents by eye before trusting a distribution built from them.

## YOLO training via symphony MusicXML × multiple IMSLP editions (2026-05-23)

**OUTCOME (2026-05-25): EXECUTED AND CONCLUDED — training part failed.** This idea was carried out as Phases A–L on branch `claude/interesting-curran-3ca1b7` (43 commits, never merged). The catalog/label-generation half worked (65/65 IMSLP editions aligned, 154k labels across 26 movements), but every training attempt on those labels collapsed the model (Phases H, I, J, K, L — including after fixing a ~50px x-offset and remapping class IDs to DSv2-free slots). Verdict: catalog-augmented YOLO training is a dead end with this recipe; structure stays with classical CV, symbol improvement comes from hand-labeling. Full story: PROJECT_STATUS.md → "The catalog-training experiment". The publisher/era research question below remains open but is no longer hooked to an active pipeline.

**Original idea**: avoid hand-labeling ~500 cells for measure-line detection by using existing symphony MusicXML as ground truth, then pulling every available PDF edition of those same symphonies from IMSLP and training YOLO to detect structural elements (measure lines, stems, rhythms) by comparing detections against the XML.

**Why it works for structural elements**:
- MusicXML *is* authoritative for measure boundaries, stem direction, rhythm.
- Sean already has the MusicXML for the symphonies in question — no labeling cost.
- IMSLP has multiple engraved editions of the canonical symphonies (Beethoven, Brahms, etc.) — instant data multiplier per work.

**Limits to remember**:
- MusicXML will likely be missing dynamics, expression marks, articulations, technique markings, and other notation the original score has. This pipeline is **only** useful for the structural classes the XML can verify. Dynamics / expression / technique training still needs another approach.

**Publisher/era as a transfer-learning axis**:
- Track edition, publisher, and publication date metadata per training PDF.
- Hypothesis: a model trained on, e.g., all Beethoven symphonies engraved by Breitkopf & Härtel in 1862–1890 will generalize to *other* composers' symphonies engraved by the same publisher in the same window — engraving conventions track the publisher/era, not the composer.
- This implies the training pipeline should be sliceable by publisher × era, not just by composer.

**Action item (research, no code yet)**:
- Investigate the major score publishers across symphonic repertoire and their active windows. Goal is a categorization scheme: publisher → era → engraving style. Likely candidates to map: Breitkopf & Härtel, Peters, Schirmer, Eulenburg, Universal Edition, Bärenreiter, Henle. For each: when active, what they engraved, distinguishing visual conventions.

**Status**: parked. No action this session — Sean wants this brought up next time he's actively working on ReEngrave.

---

## Plans surfaced 2026-05-24 from past sessions

Sean asked to recover suggestions he'd made across past YOLO-era sessions that hadn't carried into the current plan. The seven below are the ones that were absent or under-documented. Quotes are verbatim from his sessions.

### 1. Maestro Analyzer as a theory-constraint layer over OMR (highest leverage)

**Status (2026-05-24): SHIPPED M0–M4.** See [docs/maestro-integration-plan.md](docs/maestro-integration-plan.md) for the full picture. All five scholarly seed works curated. M4 in-pipeline pitch re-ranking with auto-correction is live (env-gated). Two follow-up bugs surfaced during the handel-leadsheet audit and are tracked below as separate items.

### Follow-up A — `tools/omr/export.to_musicxml` writes `<measure number="1">` for every measure

**Status: FIXED 2026-05-24.** Added "fragmented row" detection (system with >2 staves where each has exactly 1 measure) — those staves are now emitted as one part with sequential measure numbers. Piano grand-staff and orchestral systems unchanged (still share measure numbers across parallel staves). A page-global running counter ensures subsequent systems continue numbering correctly. handel-leadsheet now produces 32 distinct measure numbers; maestroAnalyst can do per-measure key resolution.

### Follow-up B — M4 candidate selection over-prefers enharmonic spellings

**Status: FIXED 2026-05-24.** Re-rank.ts now filters candidates by both pitch-class AND natural-spelling membership using maestroAnalyst's `preferredSpelling(pc, key)`. Wraps minor keys via `relativeKey()` first because maestroAnalyst's preferred-spelling tables only cover major keys (so D minor's pc 10 was returning "A#" instead of "Bb"). The bach-wtc F# → E# and G# → A# enharmonic mis-corrections are eliminated.


**Idea**: wire the existing `gradus-vercel/lib/maestroAnalyst/` TypeScript engine into ReEngrave as a *constraining* layer over YOLO output, not just as a post-hoc validator. Narrow ambiguous pitches by key + modulation + chromatic context; validate range; suggest enharmonic spellings. The MaestroAnalyst already covers cadence, enharmonicSpelling, keyDetection, modalAnalysis, pcSet, phraseSegmentation, pitch, pitchTendencyTags, rangeValidation, reduction, romanNumeral, scale, voiceLeading, xmlParser.

**Quotes**:
- "use a tool like maestro ananlyzer and determine what the potential notes couldbe based on key and even what chromatic notes would be more likely based on where the music is going by understanding modulations and the theory that is used to get there" (cool-kare)
- "I want to improve the maestroanalyzer to replace the music21 mcp by adding these functions: range validation, enharmonic spelling, xml parsing, basic pitch utilities" (jolly-noether)
- "Dose it make sense to add any access to the maestro analyzer or to the gradus vercel GKB for knowledge access to help" (hopeful-mayer)

**Current state**: not integrated. `grep maestro` in `backend/` and `tools/omr/` returns nothing. The only theory pass is reactive (`backend/modules/score_comparison.run_theory_checks`) and runs against the *final* MusicXML, not during OMR.

**What's needed to move**: decide on the integration shape — Python ↔ Node bridge vs. port the relevant analyst modules to Python vs. expose maestroAnalyst as an HTTP service. Then add a re-ranking step after `pitch_resolver` that takes the top-N candidates per notehead and asks maestroAnalyst to pick.

---

### 2. GKB (Gradus Knowledge Base) access for OMR context

**Idea**: let OMR query the GKB at gradus-vercel for context (composer/period/expected harmonic vocabulary) when transcribing.

**Quote**: "also use GKB at gradus vercel in any way that it is helpful" (jolly-noether)

**Current state**: Gradus *library* (reference MusicXMLs) is wired into ReEngrave for comparison; the GKB knowledge layer is not.

**What's needed**: bounded by item 1 — once the maestroAnalyst bridge exists, GKB access is the natural follow-on.

---

### 3. Expand training data: DoReMi + MUSCIMA++

**Idea**: don't stop at DeepScoresV2 — also train on Steinberg's DoReMi and MUSCIMA++ to broaden the model's exposure.

**Quotes**:
- "what about using a DOREMI baseline like steinberg's? https://github.com/steinbergmedia/DoReMi/releases/tag/v1.0" (objective-kare)
- "what other training can we do? more symbols from deepscore? DOREMI? MUSICIMA+++?" (objective-kare)

**Current state**: only DSv2 is in `tools/omr/training/`. DoReMi + MUSCIMA++ are not referenced anywhere.

**What's needed**: download + class-map both datasets, fold them into `prepare_yolo_data.py` and `build_catalog_yaml.py`. Re-train.

---

### 4. RTMDet / yolov8x@200ep escalation path

**Idea**: production weights are yolov8l@30ep — Sean approved the "all-the-way" run when ready.

**Quotes**:
- "I want to do this all the way full data set, yolov8x +200 epochs + the works. I can add more funds now or later but the rough estimates are ok with me" (cool-kare)
- "When we get to phase 3 should we use rtmdet instead of yolov8?" (cool-kare)
- "does our plan include using an anchor based object detector or checkpoints from github?" (objective-kare)

**Current state**: documented checkpoints stop at yolov8l-imgsz2048-ft-30ep. No RTMDet / yolov8x experiments are scheduled.

**What's needed**: define the comparison protocol (same verdict set, same imgsz) and budget a cloud run.

---

### 5. Multi-type barline classification

**Idea**: barlines aren't a single class — Sean explicitly wants single bar, double bar, final bar, and repeats distinguished. Currently classical CV detects "a barline" but not which kind.

**Quote**: "would it be bad to have a single bar line, double bar line, final bar line and repeats?" (objective-kare)

**Current state**: Phase 3.4 attempted barlines as a custom YOLO class and caused catastrophic forgetting. Currently: classical-CV barline detection, no type distinction. (See `benchmarks/omr-phase3.4b/comparison-trained-v4.md`.)

**What's needed**: either (a) post-process the classical-CV barline by inspecting pixel patterns to the left/right (double = two thin lines; final = thin + thick; repeat = thick + dots), or (b) re-introduce as YOLO classes once 200+ examples per type are labeled.

---

### 6. MusicXML repeat signs

**Idea**: MusicXML doesn't natively encode repeat marks the way humans see them — currently the export drops them.

**Quote**: "Mxl does not account for repeat signs - flag for follow up" (interesting-curran)

**Current state**: no handling in `tools/omr/export.to_musicxml()` or in the catalog labeler.

**What's needed**: detect repeats during OMR (tied to item 5) and emit `<barline location="left"><repeat direction="forward"/></barline>` etc. on export.

---

### 7. Confirm "just ink" as a label class

**Verified 2026-06-10: the annotate UI does NOT expose a noise/ink class** — the picker is the DSv2 208-class vocabulary only. The current doctrine covers most of the need by omission: dropped FPs / unboxed bleed become hard-negative background (see CLAUDE.md → "Ink-bleed / mostly-FP cells are GOOD"). Revisit an explicit "noise/ink" class only if hard-negative-by-omission proves insufficient after the v2/v3 retrain.

**Idea**: label noise/ink-artefacts explicitly during hand-labeling so the model learns to ignore them, instead of leaving them unclassified.

**Quote**: "It might be helpful also just to classify ink" (objective-kare)

**What's needed if revived**: add a "noise/ink" category and update `verdicts_to_yolo_labels.py` to either drop or remap those during YOLO label emission.
