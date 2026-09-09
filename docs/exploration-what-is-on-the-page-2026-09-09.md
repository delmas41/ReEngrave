# What is on the page — present, left out, implied

Sean, 2026-09-09: *"exploratory thinking — what is on the page? present, left
out or implied that we should gather?"*

⚠️ **THIS IS THINKING, NOT A MEASUREMENT.** The companion inventory
(`tools/omr/staged/gather_coverage.py`) is derived from the code and can be
re-run; this document is the other direction — reasoning from the printed page
toward the vocabulary — and most of it is UNPRICED. Where a figure appears it
comes from an artefact and is marked. Nothing here ranks work on its own; it
proposes candidates and says which are cheap.

⚠️ **AND "GATHER EVERYTHING" IS THE WRONG CONCLUSION.** A quantity nobody
adjudicates is a Class-C finding — *the value existed and nothing read it* —
which the handoff names as the highest-yield bug class of the week and which
this architecture exists to kill. The test for admitting a quantity is not "is
it on the page" but **"will a decision declare it in `wants=`"**. Several
entries below fail that test today and are marked.

---

## The frame

Sean's three words are the right axes and they are genuinely different kinds:

| | what it is | what a reader does |
|---|---|---|
| **PRESENT** | ink we do not gather | read it |
| **LEFT OUT** | the engraver OMITS something and the omission carries the meaning | infer it |
| **IMPLIED** | never ink at all — a relation between things that are | derive it |

The third is where the chord finding lives, and it is the largest.

---

## A. PRESENT — ink with no name

The derived list is 16 detector families. Sorting them by what they *do* rather
than what they are:

**Load-bearing on a decision we already make**

* **`rest` (11 classes)** — half of every duration decision, and a whole-rest
  glyph means the BAR. No quantity of any kind.
* **`accidental` (8 classes)** — and ⚠️ **an accidental is not a glyph
  property, it is SCOPE**: it applies to its letter+octave for the rest of the
  bar. `transcribe.py:2210` implements exactly that and the staged record has
  nowhere to put the state. This is the clearest case where the missing
  quantity is a *span*, not a mark.
* **`ottava` (1 class)** — a span that shifts every note under it by an octave.
  A missed one is not one wrong note, it is every note in the span wrong by
  twelve semitones. Highest damage-per-instance of anything in this list.

**Free printed ground truth for a decision we currently GUESS**

* **measure numbers** — ⚠️ **the engraver has already told us how many bars are
  on the line, and we count them with geometry instead.** `measure_partition`
  is decided from barline columns; the printed number is an independent witness
  in the record's own sense — a different reader, no shared ancestor. It is
  also the only page-side quantity that could corroborate a bar count without a
  reference file.
* **rehearsal marks** — the same again, and they anchor ACROSS parts.

⚠️ Both are genuinely reachable but neither is trivial: they are small text in
the margin/above the staff, which is the `direction_text` rung's problem, and
`numeral*` classes cover meters, tuplet digits, fingerings *and* measure
numbers under one name (the `class_aliases` `COARSER_THAN_CANONICAL` trap). So
this is a REACH question first, as usual.

**The page's traversal order — printed, and modelled nowhere**

* `segno` and `coda` are single classes; ⚠️ **the `repeat` family is
  `repeatDot` ONLY — we have the dots, not the sign** — and **`volta` is not in
  the class space at all** (checked, not assumed). Together these mean **the
  printed order is not the playing order**, and no part of either pipeline
  represents that. This is a whole axis, not a gap; noted for completeness, not
  proposed. It also explains why "MusicXML repeat signs are dropped on export"
  has stayed a TODO: the ink for the barline half is not detected either.

**Performance marks** — `keyboard` (pedal), `strings` (bowings), `caesura`,
`arpeggiato`. Low structural leverage, real for fidelity. ⚠️ **`breath` and
`glissando` are NOT in the class space** — a first draft of this list named
them from musical memory rather than from the vocabulary, which is the same
mistake as auditing a coverage tool against an allow-list. Checked now: a mark
we cannot detect is a detection question, not a gathering one.

**Known ceilings, restated so they are not re-discovered** — `grace` (0 `Small`
detections on any page; the reference encodings hold 0 grace notes in 28,579)
and `tremolo` (the checkpoint produces zero, though the label corpus carries
46 boxes).

---

## B. LEFT OUT — the omission IS the signal

⚠️ **THIS IS THE CATEGORY THE RECORD WAS BUILT FOR, AND IT IS ALREADY THE
PROJECT'S BEST-PAYING BUG SHAPE.** `record.py` opens by insisting that READ,
DECLINED and ABSENT are three states; music engraving is a notation in which
**absence is a value**, and every one of these is the same distinction wearing
a musical costume.

**1. An empty staff-measure means the instrument is SILENT — and we cannot tell
that from having read nothing.**

`export._mxl_empty_measure` turns a bar with no detected events into a
whole-measure rest. So *"this instrument rests here"* and *"the detector found
nothing here"* produce the identical output. ⚠️ **That is the ABSENT/DECLINED
collapse the whole record exists to prevent, occurring in the musical content
rather than in the metadata** — and it is the single most exact instance of the
project's own thesis that I can find on the page. On a conductor's score it is
also common: most staves rest in most bars.

What separates them is available and unused: a genuinely silent bar is *blank*,
a failed read is a bar with **ink we did not resolve**. Ink coverage in the
cell, which `direction_text._blank_detections` already computes for another
purpose, distinguishes them.

**2. No accidental means the earlier one still applies.** See §A. Absence of a
mark is a positive statement about pitch.

**3. No clef / key / meter on a continuation system means UNCHANGED.** Already
handled, and handled *well* — `source="carried_from_previous_page"` tags the
carry so it cannot be mistaken for a reading. **This is the precedent every
other entry here should copy**, and it is worth stating as the pattern: *an
inferred value is kept, and it is labelled with the fact that it was inferred.*

**4. A suppressed tacet staff.** The page prints fewer staves than the work
has parts, and the absence names which instrument is silent for the system.
Known (`_stitch_slots` refuses; `OMR_SLOT_STITCH` repairs) — listed because it
belongs to this family and reads as a structural bug until you see that.

**5. No stem means a whole note.** ⚠️ Absence-of-stem is *positive* evidence
for duration, and the duration decision consumes stems and beams as things that
are THERE. A whole note is currently read from its notehead class alone. Cheap
to add as corroboration; only worth it if `adjudicate_duration` declares it.

**6. No beam between two eighths** — they are flagged instead, which says
something about beat grouping, which says something about the METER. Beaming is
meter evidence the meter vote does not consult.

**7. Blank horizontal space.** An engraver spaces notes roughly in proportion
to duration, so a wide gap after a notehead is evidence it is long. ⚠️ Measured
nowhere — `grep` for proportional spacing in `tools/omr/` returns only
unrelated hits. This is the one entry here that is a genuine *measurement* of
the raster nobody takes, and it is independent of every other duration signal
(it does not need the stem, the beam, or the notehead class). Speculative:
scanned spacing is noisy and justification stretches the last bar of a line.

**8. No courtesy accidental** — publisher-dependent, so its presence or absence
is evidence about the EDITION rather than the music. Filed as curiosity.

---

## C. IMPLIED — the relations, and the big one

### ⚠️ C1. VERTICAL ALIGNMENT ACROSS STAVES IS SIMULTANEITY, AND NOTHING READS IT

**This is the generalisation of Sean's chord finding and I think it is the most
valuable idea in this document.**

⚠️ **SHARPENED BY THE MERGE, NOT WEAKENED BY IT.** `Q.EVENT` landed on main
while this was written — but it is scoped `Kind.CELL`, one measure of one
staff. So simultaneity is now read WITHIN a staff and still nowhere ACROSS
staves, which makes this the remaining half of the same mechanism rather than
a competing idea. Re-checked after the merge: no `SYSTEM`-scope simultaneity
quantity exists.

Within one staff, noteheads at the same x are a chord — that is the gap already
found. **Across the staves of a system, notes at the same x are the same
MOMENT.** That is not a convention, it is the defining property of a
conductor's score: a column through a system is an instant of music.

Verified: nothing in either pipeline compares event x-positions across staves.
The only cross-staff reasoning in the tree is
`_dedupe_cross_staff_detections` — which asks **which staff owns a glyph**, an
ownership question, never a simultaneity one.

**Why it matters more than one more symbol family:** every other signal on the
page is read ONCE. This one is read up to twenty-five times. A 21-staff Brahms
system is twenty-one independent readings of the same stretch of time, and they
must agree about where the beats fall. That makes it the only large source of
**redundant** evidence on the page — and redundancy is precisely what lets a
record say *which decision* went wrong, which the handoff names as the reason
the staged pipeline replaced the metric.

⚠️ **The coarse version of this check already exists and is SATURATED, which is
what makes the fine version interesting rather than duplicative.**
`measure_count_warning` — do the staves agree how many bars are on the line —
fired **ZERO times across all 29 stored transcriptions**, corroborated by 0
disagreeing staves over 27 systems in the majority-steering benchmark. The
staves already agree at bar granularity. The disagreement lives *inside* the
bar, where `rhythm_sum_warning` fires **78 times on one document and is inert**.
So: the constraint is unexploited exactly at the resolution where the errors
are.

**What it would decide.** Given a bar read by twenty staves, with onsets in x:
a staff whose events cannot be placed on the same time grid as its neighbours
is the one that misread — and *which* event fails to align localises it to a
note rather than a bar. That is attribution at the decision level, from page
geometry alone, with no reference file.

⚠️ **Honest difficulties, none of them fatal but none of them free.** A scan is
warped, so a "column" is a fitted line, not a vertical — `measure_extractor.
_barline_x_at` already fits barlines with Theil-Sen for exactly this reason and
is the precedent to copy. Engravers stagger seconds and accidentals off the
true column deliberately. A tuplet against duplets is genuinely non-aligned in
a way that is correct. And rests are placed for legibility rather than
precisely on their onset. So the quantity to gather is a **measured column
membership with a residual**, not a boolean — the same shape as
`NOTEHEAD_STAFF_POSITION`, which keeps its fraction so a later reader can see
that a note sat between two positions.

**Where it would live.** As a gathered measurement it is
`Q.ONSET_COLUMN` at `Kind.SYSTEM` scope (a column is a property of the system,
not of a staff) with per-glyph membership and residual. It composes with — and
does not replace — the within-staff chord grouping, which is the same operation
one level down. ⚠️ **Both are needed and they are one mechanism at two scopes**:
same-x-within-staff is a chord, same-x-across-staves is an instant.

### C2. The other implied relations, briefly

* **A barline is one event for the whole system**, not one per staff. Partly
  used (`_spans_system` rescues braced systems); not represented as a shared
  fact.
* **The meter is a property of the SYSTEM.** Used in the vote — good precedent
  for C1, and the same shape.
* **Beat positions inside a bar** follow from the meter, and notes cluster on
  them. A weaker, second-order version of C1.
* **A part continues across systems and pages** — the stitch problem, well
  covered.
* **Written vs sounding pitch** — transposition; handled through the dossier
  and `instruments`, and worth noting the record has `CLEF_SEED` but no
  transposition quantity while `<transpose>` is the second-largest element the
  repaired `export_coverage` surfaced (92).

---

## What I would actually propose, and in what order

Ranked by (evidence gained) ÷ (cost), and marked against the "will a decision
want it" test:

1. **`Q.ONSET_COLUMN` — cross-staff simultaneity.** Pure geometry over boxes
   already gathered; needs no new reader, no weights, no reference. It is the
   only proposal here that creates *redundant* evidence rather than one more
   fact, and the coarse check being saturated is the argument that the fine one
   is where the errors are. ✅ A duration or meter adjudicator would declare it.
2. **Chord grouping as a declared decision** (the original finding) — the same
   mechanism one scope down, and the input for C1.
3. **`Q.REST_*`** — 11 classes, half of every duration decision, currently
   anonymous. ✅ `adjudicate_duration` would want it today.
4. **Silent-vs-unread on an empty bar.** Cheapest of all — ink coverage is
   already computed elsewhere — and it repairs the project's own thesis
   violation. ✅
5. **Accidental scope as a span quantity.** Legacy implements the logic; staged
   has nowhere to keep it.
6. **Measure numbers as an independent witness on `measure_partition`.**
   Attractive because it corroborates a decision made by geometry alone —
   ⚠️ but REACH first: it is small text, and `numeral*` is a coarse class.
7. **Blank space as duration evidence.** The one unexploited raster
   measurement. Speculative; would need pricing before anything is built.

⚠️ **Not proposed:** traversal order (repeats/voltas), performance marks,
multi-measure rests. Real, and none of them is what is currently wrong.
