# Position grammar — glyph identity is context, not shape

**Date:** 2026-09-04 · **Origin:** Sean's question in the second-opinion review
session ("slurs and ties look exactly the same — what makes them different are
the notes they connect"), generalized across the mark alphabet the same hour.
**Status:** design principle + inventory. Nothing here is a work order; each
"where this bites" item carries its own measured hook and must be priced on
both benchmark families before it ships.

---

## 1. The principle

Engraved music is a **positional writing system built from a tiny mark
alphabet** — dot, stroke, wedge, arc, bowl, digit. The engraver reuses the
same physical mark in several grammatical roles, and the reader disambiguates
by **where the mark stands** relative to the staff lattice and its anchors
(noteheads, stems, barlines, clef bodies) — never by staring harder at the
ink. A pixel classifier asked to name the role is being asked to learn a fuzzy
proxy for a rule that is exact.

So the architecture this project has been converging on piecemeal, stated as
a principle:

> **The detector's job is to find and localize ink events, with a class
> PRIOR. For confusable families, identity is assigned — or vetoed — by a
> grammar layer that knows the lattice and the anchors.**

This is not a proposal for something new. It is the project's most successful
recurring move, made roughly nine times without being named (§3). What is new
is designing toward it instead of rediscovering it one symbol at a time.

**A free dividend:** a mark that matches *no* grammatical position is a
principled rejection. Scan bleed, specks, and letter fragments — the
false-positive family the labeling campaign fights with hard negatives — fail
every context test at once. "Matches nothing → drop" is a blob filter that
costs no training.

**The counterweight, stated plainly:** grammar needs anchors. Every rule below
keys off noteheads and staff geometry, so anchor recall is the foundation the
grammar multiplies — it cannot replace it. That ordering is why the notehead
head-graft shipped first (2026-09-04) and resolver work comes after.

---

## 2. The mark alphabet — confusable families and their discriminators

Every discriminator below is positional or metric, and where a number is
given it was measured in this repo.

### DOT — one mark, four roles, plus noise

| role | position that names it |
|---|---|
| augmentation dot | right of a head, at the head's space — or **half a space above** for a head on a line; the window is asymmetric (0.75 spaces above / 0.25 below, `DOT_ABOVE_NOTE_MAX_SPACES`) because a dot never sits under its note. Measured bimodal over 116 dots: 52 at 0.00, 52 at +0.50, nothing between +0.57 and +3.75 |
| staccato | stacked vertically with **one** head, on the opposite side from the stem, within ~a space; never to the head's right |
| F-clef dots | header window only, straddling line 4, **past the clef body's right edge** (0.94–1.79 notehead-widths — the region where a C clef has nothing; the dot-veto work priced this exactly) |
| repeat dots | vertical pair in spaces 2+3, adjacent to a barline (barlines are classical-CV, so the anchor exists without the model) |
| none of the above | ink noise — drop |

### ARC — tie vs slur

Identical glyph. Discriminator: an arc whose ends land on **exactly two
adjacent same-pitch heads** is a tie; an arc spanning more heads or different
pitches is a slur; the model's class breaks genuine ties. Ambiguity floor: a
two-note phrasing slur on a repeated pitch is undecidable from print alone —
default to tie (the duration-semantic reading, the safer error). Pairing
across barlines and system breaks already exists for both
(`_pair_ties_in_staff`, `annotate_slurs_in_slot`).

⚠️ The measured leverage order for ties is **noteheads → pairing → arc
detection**, not the reverse: the detector already emits ~249 tie arcs on the
5 scan pages while the export carries 60 of 271 truth ties, and the hollow
graft moved that to 97–106 **without touching the tie class** — better
noteheads let existing arcs pair.

### WEDGE — accent vs hairpin (Sean's example)

Same `<` mark. An **accent** is notehead-scale and anchored to one note:
stacked with a single head, close to it. A **hairpin** is span-anchored: it
lives in the dynamics band (below the staff or between staves), covers two or
more note onsets, and usually travels with a partner wedge or a dynamic
letter. Width alone fails — one-beat hairpins exist; *note-anchor vs
span-anchor* does not. (Marcato is the vertical wedge; same family.)

### HORIZONTAL STROKE — tenuto vs ledger line (Sean's example)

Both short horizontal strokes, and the discriminating measurements **already
exist in the pipeline's JSON**: a ledger line lies ON the extended half-space
lattice, continues a ladder run toward a head or has a head centered through
it, and matches the staff's own measured line thickness (recorded per staff
since the frame-retention work). A tenuto sits OFF the lattice about a space
beyond its head, with nothing centered through it.

⚠️ This confusion is live in the **evidence chain**, not just the export: the
ledger-ladder arbitration reads `ledgerLine` detections to decide which staff
owns a contested note, so a tenuto misread as a ledger feeds false rungs into
attribution, and the reverse starves it.

### VERTICAL STROKE — stem vs barline (already solved; the precedent)

Nothing but a barline runs from the top of the upper staff to the bottom of
the lower — a fugue's stem crosses the brace gap and scores 1.00 connectivity,
which is why the span test exists (`_spans_system`). Classical CV owns both
marks; the model never had to.

### DIGIT — one glyph, five roles

Tuplet digit vs fingering (positional gate shipped: 33 `fingering3` on the
widened corpus, **all 33 in cells holding a real triplet**); time-signature
digits (read by header slot geometry + system vote, 12 correct / 0 wrong / 40
correct abstentions); measure numbers at system starts (the row-drafting work
found three of four editions print them); stacked instrument numbers left of
the bracket (24 of Mahler's 41 clef-locator false positives — margin, not
music); plate numbers (margin). ⚠️ Type design moves under you: a Litolff `3`
matches Bravura's `6` — never tune a digit threshold on one edition.

### BOWL / BLOB — hollow heads vs letters vs grace vs specks

The bowl of a *legato* "g", the lower bowl of a 6/8's "8", and a clipped
neighbor-staff head are all hollow-notehead-shaped. Shipped discriminators: a
notehead is **a staff space tall** (fragments 0.29–0.56 spaces, genuine heads
0.60+, nothing between — `_drop_clipped_notehead_fragments`, and now the
third labeling audit); an outside-staff head with **no ledger rung at all**
is not a note (fakes at conf 0.45–0.53 vs 0.76+ for every real one — neither
signal sufficient alone). Recorded lead, untried: a grace head is smaller
than its neighbors (41×38 px against 51–83 in the same cell) — the one route
left after two label-side fixes were refuted.

---

## 3. The precedents — this move has won nine times

1. **Clef identity by measured line** (`clef_geometry`) — alto/tenor/soprano
   are one glyph on different lines; "a class label can never separate them."
   End-to-end clef accuracy 92%.
2. **tuplet3 vs fingering3** — DSv2's own labels encode a positional
   distinction; both classes are read, position gates them.
3. **Aug-dot attachment** — keyed to the *note* and the staff-space unit
   because "the dot's own bounding box is small and mostly detector noise."
4. **F-clef dot veto** — "POSITION BEFORE SHAPE" is that thread's recorded
   slogan; false positives 48 → 13 → 5.
5. **Ledger ladder + unladdered veto** — context decides both ownership and
   existence of a contested head; pooled 0.1506 → 0.1431.
6. **Edge fragments** — a height band plus *where in the cell* settles what
   pixels cannot; found live in the training corpus, no image needed.
7. **Body text vs staves / stem vs barline** — continuous strokes vs glyph
   runs (1.39 vs 2.02 runs per space); only a barline spans the system.
8. **Time signatures by header slot + vote** — after the detector filled
   mid-bar barline fragments in as 4/4.
9. **Key signatures by slot fit + page vote** — counting markers 6/10, fitting
   positions 7/10, reconciling across the page 10/10.

Each time, context beat making the classifier smarter — and several of the
attempts to make the classifier smarter instead are recorded refusals
(clef fine-tune: dense recall 2506 → 114; domain augmentation; the catalog
recipe).

---

## 4. Design rules

**R1 — The class space is frozen at 208; classes are priors, not verdicts.**
No `curvedLine` or `dot` superclass in the model: an nc change silently
re-initializes the classification head (the Phase 3.4 collapse). The grammar
layer lives downstream, where it costs no training and can be priced per rule.

**R2 — Families must be closed under confusability.** A labeling pass or a
specialist corpus that boxes one twin and leaves the other unboxed teaches
"this exact shape is background" on half the evidence — contradictory
supervision. Round 6 measured the primary specialist-collapse mechanism as
self-incompleteness (corpora 41–61% unboxed in their **own** symbol); family
closure is the secondary mechanism and the cheap one to honor from now on.
Concrete closures: arcs {tie, slur}; dots {augmentationDot, articStaccato*,
repeatDot} (F-clef dots ride inside the clef's box); wedges {accents,
marcato, hairpins}; and an accidentals family must include the key-signature
twins {keySharp, keyFlat} — the literally identical glyph. Adjudication
batches should present a family **together**, so the human makes the
role call once, in context.

**R3 — Resolver order: veto the impossible first, reclass only when
decisive, abstain otherwise.** Vetoes are additive and safe (the range veto,
the ladder, the fragment drop all follow this shape). Reclassification must
be decisive-configuration-only, with the model's class standing wherever the
grammar abstains — and every rule is priced on **both** benchmark families
(scan e2e and the 11-work engraved pool) before it defaults on, because the
engraved side's classifier is good and must not be regressed by a rule tuned
on scans.

**R4 — Anchors before grammar.** Notehead recall and staff geometry are the
inputs to every rule above. When choosing between anchor work and resolver
work, anchor work wins — the 2026-09-04 graft ship before any arc resolver is
the worked example.

**R5 — "Matches nothing" is an output.** Measure the blob filter's kill rate
on the bleed cells the labeling campaign uses as hard negatives; if the
grammar rejects most of them, labeling effort can shift from teaching the
model "this is nothing" to teaching it things only a detector can know.

**R6 — Never tune a positional threshold on one edition.** The clef-threshold
lesson (a tenor symmetry floor separated cleanly on Beethoven, impossible on
Mahler) and the Litolff/Bravura digit collision both say the same thing: a
sweep corpus per edition, or the threshold moves with the printing.

---

## 5. Where this bites next — each with its measured hook

| opportunity | the hook that already exists |
|---|---|
| tie/slur re-derivation at export | 249 arcs detected vs 60→97 exported vs 271 truth; pairing logic exists in both frames |
| accents reach the file | ~~KNOWN_GAPS open item: truth 6, detected exactly 6, consumed **0**~~ **STALE ON ARRIVAL — already closed** (corrected 2026-09-04): the articulations work (`0eb1271`, 2026-09-01) consumes `articAccent*` and Mahler exports 6 of 6; the KNOWN_GAPS entry left the same day it was written. This row inherited CLAUDE.md's stale copy of that entry, and a work order was issued off it — see `benchmarks/omr-export-gaps-2026-09/FINDINGS.md` §1 |
| hairpin vs accent split | hairpins 6 truth / 4 detected in KNOWN_GAPS; export work in flight on 09-03/04 branches — the wedge grammar decides which family a detection joins |
| tenuto vs ledger | thickness + lattice-parity inputs already recorded per staff; protects the ladder arbitration as well as the export |
| repeatDot → repeat barlines | repeat signs are NOTES item 6, dropped on export today; dots + CV barline = the anchor pair, no model change |
| grace by size | the pre-fill's recorded ceiling; 41×38 vs 51–83 in-cell is the untried geometric route |

---

*Written by the advisor session at Sean's request, from the measurements
cited; the specialist/labeling campaign (round 6+) is the intended first
consumer, via R2's family closures and the adjudication-batch shape.*
