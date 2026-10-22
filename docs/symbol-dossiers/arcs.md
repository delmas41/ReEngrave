# Arcs — slur, tie, the chain, and the three ways one curve stops being one curve

Six sections. The first two are the two SMuFL classes the detector produces
(`slur`, `tie`). The other four are not classes — they are the four ways the
repo has found a single printed curve getting lost between the plate and the
file: the CHAIN it makes across events, the BARLINE that cuts it, the SYSTEM
BREAK that cuts it, and the NEIGHBOURING STAFF that steals it. Each is treated
as its own symbol because each has its own reader, its own constants and its
own failure.

**Read alongside, not instead of.** Three documents already answer parts of
these five questions for this family and are cited rather than re-derived:

* [`docs/position-grammar-confusables-2026-09-04.md`](../position-grammar-confusables-2026-09-04.md)
  §"ARC — tie vs slur" — **Sean's own Q1**, and the question that started that
  whole document: *"slurs and ties look exactly the same — what makes them
  different are the notes they connect."* Every §1 below starts from that entry
  and says where this reading **agrees, adds or disagrees**. There are two
  disagreements and both are stated.
* [`benchmarks/omr-family-positions-2026-09/FINDINGS.md`](../../benchmarks/omr-family-positions-2026-09/FINDINGS.md)
  + `tools/omr/staged/positions.py` + `capture.py` — the per-family POSITION
  fact. For arcs it is `Q.ARC_POSITION`: *the arc's own vertical extent,
  `depth_steps`, which side*. **779 rows on Litolff, 2,207 on Brahms; ten
  producers and no consumers**, `OMR_FAMILY_POSITIONS` default OFF. Sean's own
  warning travels with it: *"position is an option for helping us determine
  something but will rarely be a clear rule that determines by itself."*
* `tools/omr/staged/ASSUMPTIONS.md` — which ranked the arcs **last** of the
  wiring items, *"because they are self-contained and **nothing else waits on
  them**."* This dossier's §5(b) finding is that statement, re-checked by grep
  and still true. `docs/exploration-what-is-on-the-page-2026-09-09.md` says
  nothing about arcs.

**The one thing to read first.** The class space has exactly two arc classes —
`_ARC_CLASSES = ("tie", "slur")`, `tools/omr/staged/gather.py:743` — and
`adjudicate_arc_kind` **returns the detector's class unchanged on every arc it
can see**. Its `reasons` tuple is `("tie", "slur", "no_arc_box",
"no_evidence")`: the reason for a decided arc *is* the kind. So the pipeline
has no way to say "this is an arc but I cannot tell which". Everything else
here follows from that.

---

## slur

A curve joining two or more notes of different pitch, drawn clear of the
noteheads on the side away from the stems. Produced by one class, `slur`
(`tools/omr/training/deepscores_classes.py:169`, index 130 of the embedded
146-class DSv2 snapshot — its neighbours there are `beam` and `tie`), gathered
as `Q.ARC_BOX` alongside `tie`.

### 1. What sets it apart — and what it is confused with

**Sean already wrote this entry, and it is right.**
`docs/position-grammar-confusables-2026-09-04.md` §ARC: *"Identical glyph.
Discriminator: an arc whose ends land on exactly two adjacent same-pitch heads
is a tie; an arc spanning more heads or different pitches is a slur; the
model's class breaks genuine ties."* Corroborated since from the font side:
Bravura gives a slur and a tie the **same** endpoint and midpoint thickness
(0.10 / 0.22), so weight cannot separate them (`[C35 + L48]`, LITERATURE).

**What this dossier ADDS: the two halves of that sentence do not behave
alike.** The veto was built (`OMR_ARC_RECLASS`) and re-priced per rule, and
`tie_to_slur_flagged_diff_pitch` — the **PROVABLE** half, *the flanked pair
sits a staff step or more apart, which no tie can* — fires 12 times and the
three works where it fires ALONE are **−4 edits, i.e. better**; every
edit-positive work fires a `span` or `unpaired` rule, which are **INFERRED**
(a measure the detector left empty spends no ordinal). `[C43]`, MEASURED HERE.
So *"spanning more heads ⇒ slur"* is the weaker half on our output, and it is
weaker for a reason about US, not about engraving: we do not reliably know how
many heads are under an arc.

**The problem underneath both halves is that "what it binds" is a fact about
the NOTES, not about the curve** — so the discriminator is downstream of
notehead detection, staff position and (for the pitch form) clef. See §5(b).

**What it is confused with, concretely, ranked by measured cost:**

| confused with | evidence |
|---|---|
| **not an arc at all** — bleed from the staff above/below at a cell edge, and jagged scanned staff lines | **MEASURED HERE.** Sean adjudicated arc candidates over 126 cells of Breitkopf Brahms 1 (`benchmarks/omr-queue-arcs-2026-09/verdicts/`, tallied for this dossier): **437 candidates, 176 real, 260 not real.** The 260 is `ROUND7_FINDINGS.md`'s own "260 fake (staff-above/below bleed at cell edges, jagged scanned staff lines)", reproduced to the unit from the committed files. |
| **a tie** (the kind is wrong on real arc ink) | **MEASURED HERE.** In that same batch the human was explicitly asked to fix the kind (`batch_config.json`: *"fix the class with `c` if it is the OTHER arc"*) and did so on **2 of 172** confirmed arcs — both `slur → tie`. So on real ink the kind is right ~99% of the time on that plate; the errors are overwhelmingly arc/not-arc. |
| **a slur read as a tie on a page that prints no ties** | **MEASURED HERE**, `benchmarks/omr-tie-pairing-2026-09/FINDINGS.md` §2: `mozart-sym41-mvt1` prints **1 tie and 44 slurs** and the detector fires **13 `tie`** — 12 of 13 false, and a false `tie` lands on whatever two notes a slur connects. |
| **a beam** | `beam` sits literally between `slur` and `tie` in the class list. **ASSERTED** — no measurement of arc/beam confusion exists in the tree, and the two are read by different rungs (beams by classical CV), so nothing would currently notice one. |

⚠️ **The detector is LONG on arcs, not short.** 721 merged arc groups against
an encoding truth of 411 curves on Litolff Beethoven 5 pp.1-4
(`benchmarks/omr-arc-recovery-2026-09/FINDINGS.md` §2, MEASURED HERE, n = 1
document). A session starting from *"we do not detect enough slurs"* goes the
wrong way.

### 2. Best method: YOLO / CV / other

**YOLO is the incumbent and it is measured bad at this, twice, in two different
ways.**

* **Precision 0.232** for production tie/slur detections against human boxes on
  126 scan cells, IoU 0.3, conf 0.25 — *in sample*, i.e. on the model's own
  training cells (`benchmarks/omr-queue-arcs-2026-09/ROUND7_FINDINGS.md`,
  MEASURED HERE).
* **A frozen-head specialist cannot separate real arcs from edge-bleed.** Two
  regimes trained on 176 human-certified positives and 260 human-certified
  negatives: lr0.01 bought +9 true positives with **3,550 extra false arcs**
  (precision 0.037); lr0.001 halved recall for no precision gain. The argument
  in that file is a pincer and it is sound: a frozen head is a linear readout
  of production's features, so if it cannot separate them **the features do
  not** — and training the trunk is measured to delete whole classes
  (`benchmarks/omr-labeling-survey-2026-09/ROUND5_METHOD_2026-09-04.md`).

⚠️⚠️ **AND THE PRIOR DOCUMENT ALREADY RANKED THE LEVERS, CORRECTLY: the
measured order is `noteheads → pairing → arc detection`, not the reverse.**
*"The detector already emits ~249 tie arcs on the 5 scan pages while the export
carries 60 of 271 truth ties, and the hollow graft moved that to 97–106 without
touching the tie class"* (`position-grammar-confusables` §ARC, MEASURED HERE).
**This dossier agrees with the ranking and SIZES the first step, which that
entry did not**: splitting the refused arcs on Litolff pp.1-4 gives **170 of
361 (47%) with no head anywhere in the arc's own bars** and **109 + 82 = 191
where the heads are present and the span misses them**
(`benchmarks/omr-staged-arc-split-2026-09/FINDINGS.md` §2, MEASURED HERE).
So *better noteheads let existing arcs pair* is right and is worth **about
half**; the other half is arc-box localisation, and §3's pad sweep says that
half is not a constant either.

**So the recommendation in the tree is classical CV, and it has not been
tried.** ROUND7's own closing line: *"the likeliest live lever for arcs is
classical CV, not the detector … a slur IS a thin curved line"*, which is the
same ground on which stems and beams left YOLO in Phase 4f. The 260 adjudicated
fakes exist as a ready-made false-positive gauntlet for such a reader.
Grade: **MEASURED HERE** for the negative (YOLO is bad), **ASSERTED** for the
positive (CV would be better) — nobody has built an arc tracer.

⚠️ **One thing a CV tracer would give that a box cannot: CURVATURE.** A
bounding box is identical for an arc opening up and one opening down, so
`positions._arc_discriminator` records `opens: None` rather than guessing
(`tools/omr/staged/positions.py:433`). Which end of the box is an ENDPOINT and
which is the APEX is unavailable today.

### 3. Where on the page the deciding information lives

Not in the arc. In four places around it, in three different frames:

| the fact | where it lives | frame |
|---|---|---|
| the arc's extent | `Q.ARC_BOX` | canonical (cell) **and** page px, both carried |
| **which noteheads it flanks** — the discriminator | the notes' boxes and `Q.NOTEHEAD_STAFF_POSITION` | canonical, same cell |
| **the stem tips it is actually drawn to** | `Q.STEM` | canonical only, **no page box** |
| whether it was cut in two | `Q.CELL_BOX` — the measure cell's own rectangle | page px |
| whether it belongs to this staff | the other staves' noteheads | page px |

**The arc's OWN position fact exists and is unread.** `Q.ARC_POSITION` —
`depth_steps`, which side of the staff — is produced for **779 arcs on Litolff
and 2,207 on Brahms** behind `OMR_FAMILY_POSITIONS` (default OFF) and read by
nothing (`benchmarks/omr-family-positions-2026-09/FINDINGS.md` §1, §5). It is
the largest-reach unread position quantity in the project. ⚠️ Sean's own
caveat applies in full here: *position will rarely be a clear rule by itself* —
and for an arc that is not a caution but a measurement, since `[C40]`'s depth
claim has no figure at all.

⚠️ **An arc over stemmed notes is drawn STEM-TOP TO STEM-TOP**, and a stem
stands at the side of its head — so the arc's ink stops *outside* the outer head
centres by the stem offset. Measured: the distance from an arc's edge to the
nearest head centre outside it has **median 0.52 notehead widths**
(`benchmarks/omr-arc-recovery-2026-09/FINDINGS.md` §6, MEASURED HERE). This is
`[C37]`, and the repair was a stem PROBE, not a wider pad.

⚠️ **The arc is also NARROWER than the run it binds** — it is drawn *between*
its outer heads — so the box must be padded before asking what is under it, or
the outer note at each end is lost (`[C36]`, `_SLUR_ARC_PAD_NOTEHEADS = 0.25`,
`tools/omr/export.py:1875`). ⚠️ **Widening that pad was measured and refused
twice**: on the engraved Brahms fixture it sits in an empty interval (54 of 75
within 0.19, next at 0.32), and on the Litolff scan the same distribution is a
smooth slope with no gap anywhere — a sweep out to 3.0 notehead widths decays
smoothly with no plateau (`benchmarks/omr-staged-arc-split-2026-09/FINDINGS.md`
§4, MEASURED HERE).

### 4. Stage by stage

| stage | what happens | where |
|---|---|---|
| **GATHER** | `gather_glyph_families` files `Q.ARC_BOX` with the detector's class as the VALUE, its confidence as `score`, canonical box, and page box where the cell has one (else `frame_note`, never a defaulted frame). `Q.CELL_BOX` is filed separately. `Q.ARC_POSITION` (the arc's own `depth_steps`, side) is produced by `positions.py` behind `OMR_FAMILY_POSITIONS`, **default OFF, and read by nothing** — listed as `UNREAD-POSITION Q.ARC_POSITION` in `capture.py:648`. | `gather.py:883`, `positions.py:433` |
| **ADJUDICATE** | Two decisions, in `ORDER` right after `Q.GLYPH_OWNER` and before pitch, duration and voices: **`arc_owner`** (which staff) and **`arc_kind`** (tie or slur). `arc_kind` **returns the detector's class** and records the grammar beside it. | `adjudicators/ownership.py:191`, `:571`; `adjudicate.py:757-758` |
| **EVALUATE** | **Nothing.** `grep -n "arc\|ARC" tools/omr/staged/consequences.py` returns no arc rule. No arc quantity is in `DOWNHILL`. | — |
| **INFER** | **Nothing.** `grep -n "arc" tools/omr/staged/infer.py` / `inferences.py` returns no rule; the only mentions are in prose citing `arc_kind` as an example of a correlated witness. | — |
| **EXPORT** | Everything else. `_place_arcs` puts each arc in the cell its OWNER names; `_pair_arcs` merges across barlines and system breaks per PART, partitions by kind, calls the legacy `_paired_spans` and `_number_spans`, and marks the notes. | `staged/export.py:840`, `:1031` |

⚠️ **The load is on EXPORT and it is not a stage boundary anyone chose.** The
merge and the pairing need the PART, and the part is built inside
`staged/export.build` — which runs *after* `staged/__main__.py` has already
written the record JSON. §"the tie CHAIN" below is the argued consequence.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a) Can it abstain, and does it?**

* **`arc_kind` cannot abstain about the KIND at all.** Its only abstentions are
  `no_arc_box` and `no_evidence` — *"there is no arc row here"*. Once there is
  a row, the answer is the detector's class name. This is the breakthrough
  document's claim in its cleanest form: the class is `log.observe`d as a FACT
  in GATHER, so the decision downstream has nothing to be uncertain about.
  There is no `NARROWED` outcome for an arc.
* **`arc_owner` abstains properly** — `no_page_frame` when the arc has no page
  box, `no_evidence` when there are no arc rows. And it distinguishes a
  DECISION from an abstention where a weaker design would not: *"no other staff
  explains this better"* returns `Ruling(value=own, reason="no_rival_staff")`,
  not an abstention, because that is a real answer.
* **EXPORT abstains loudly, and this is the biggest number in the family.**
  **550 of 721 merged arcs (76.3%) bind fewer than two noteheads and are
  refused** (`benchmarks/omr-arc-recovery-2026-09/FINDINGS.md` §2, MEASURED
  HERE, Litolff pp.1-4). That refusal is correct — one end leaves an unpaired
  `<slur type="start">` and an invalid file — but it is silence in the file,
  counted as `arc_binds_fewer_than_two_notes`.
* **Neither pairing abstains.** On the STAGED path `_paired_spans` REFUSES
  (the two-note minimum, above) rather than abstaining — refusal and abstention
  are the same silence in a MusicXML file. On the LEGACY path
  `transcribe._pair_ties_in_staff` falls through to the old nearest-in-x answer
  where no candidate pair sits at one staff position; its own docstring says
  abstaining *"would change the population and is a separate, unpriced
  decision"*.

**(b) What leans on this mark, and is the witness independent?**

⚠️ **Almost nothing leans on an arc, and that is itself the finding.** Grepped:
no EVALUATE consequence, no INFER rule and no other adjudicator reads
`Q.ARC_KIND` or `Q.ARC_OWNER`. The only consumers are `staged/export.py` and
the coverage census. **The dependency runs the other way** — `arc_owner` reads
`Q.GLYPH_OWNER`, `arc_kind` reads `Q.NOTEHEAD_STAFF_POSITION` and `Q.STEM`, and
`_pair_arcs` reads `Q.VOICES`.

**Two things the arc's certainty *ought* to reach and does not:**

1. **An accidental carries across a barline through a TIE.** The convention is
   recorded and `consequences.respell_accidental` does not know about ties
   (`grep -n tie tools/omr/staged/consequences.py` — nothing). So a tied-over
   note is respelled from the key signature alone. This is exactly how the
   SPELLING artefact arises (below).
2. **LilyPond.** `export._lily_*` appends `~` to a chord from the event-level
   `any()` flag, deliberately left divergent from MusicXML
   (`benchmarks/omr-chord-tie-2026-09/FINDINGS.md`).

**The independence check, honestly:** the tie/slur grammar's input is
`Q.NOTEHEAD_STAFF_POSITION` — a **ruler reading taken in GATHER with no
confidence attached** (`gather.py:448`), measured off the staff lines and
clef-free. That is genuinely more independent than `Q.PITCH` would be, and it
is why `OMR_ARC_RECLASS`'s pitch form is refused on scans while the step form
is admissible. **But it is not independent of DETECTION**, and that is where
the correlation lives:

| | available | median detector confidence, available | unavailable |
|---|--:|--:|--:|
| the grammar (two flanked heads) | 345 of 779 | 0.5306 | 0.4955 |
| **S4** (arc endpoint on a stem) | **143 of 779** | **0.4196** | **0.5409** |

(`benchmarks/omr-arc-grammar-2026-09/FINDINGS.md` §1, MEASURED HERE, Litolff
pp.1-4.) The grammar follows the repo's known pattern — it goes quiet where the
first reader is worst. **S4 inverts it**: it speaks preferentially about the
weakest arcs, which is a harder failure than falling silent.

**Evidence grade:** class-space facts and stage wiring, MEASURED HERE (read
from the tree). Human adjudication counts, MEASURED HERE (tallied from
`benchmarks/omr-queue-arcs-2026-09/verdicts/`, 126 cells, 1 publisher).
Precision 0.232 and the specialist result, MEASURED HERE (ROUND7). Thickness
identity, LITERATURE (Bravura). *CV would beat YOLO*, ASSERTED.
Registry: `[C35]` `[C36]` `[C37]` `[C40]` `[C41]` `[C42]` `[C43]` `[L48]`
`[L49]` `[L52]`.

---

## tie

A curve joining two statements of the SAME pitch. One class, `tie`
(`deepscores_classes.py:171`, two entries after `slur`), gathered into the same
`Q.ARC_BOX` as `slur`.

### 1. What sets it apart — and what it is confused with

**Sean's entry again, and this is the half it states most strongly:** *"an arc
whose ends land on exactly two adjacent same-pitch heads is a tie"*
(`position-grammar-confusables` §ARC). This dossier **agrees**, and supplies
the interval that entry did not have.

**The decisive fact, and it is truth-free:** a tie's two ends are at ONE STAFF
POSITION, by definition. A curve whose flanking heads sit at different staff
positions cannot be a tie. `[C39 + L47]`, and this repo supplied the interval
the literature could not:

| | n | bound (staff spaces) |
|---|--:|--:|
| links whose two heads read the SAME pitch | 47 | max **0.168** |
| …plus the same-STEP spelling pairs | 11 | max 0.034 |
| links whose heads read ONE STEP apart | 8 | min **0.435** |
| links whose heads read further apart | 4 | min 0.906 |

An **empty interval from 0.168 to 0.435**, on the eleven engraved fixtures —
`TIE_SAME_POSITION_MAX_SPACES = 0.25` sits in the middle of it
(`tools/omr/transcribe.py:2418`; `benchmarks/omr-tie-pairing-2026-09/FINDINGS.md`
§5a, MEASURED HERE).

⚠️⚠️ **ON A SCAN THAT INTERVAL IS NOT EMPTY, and the rule still holds — it is
our READING of the positions that fails.** Same-pitch max 0.238 against a
step-apart minimum of 0.013. That is why the rule is expressed in BOXES and
never consults a resolved pitch.

**What it is confused with:**

| confused with | evidence |
|---|---|
| **not an arc at all** | the 260 human-certified fakes above; ties are the larger half (179 of the 260). **MEASURED HERE.** |
| **a slur, on a page that prints few ties** | Mozart 41: 1 printed tie, 13 detected, **12 false**. Exposure orders by **tie OVER-detection**, not by slur share: `brahms-sym1-mvt1` prints more slurs than Mozart and produces **zero** step-apart links. `benchmarks/omr-tie-pairing-2026-09/FINDINGS.md` §2, MEASURED HERE. |
| **its own two ends, mis-paired** | the y window was three notehead heights — five staff positions either way — with nothing preferring the position the arc binds. **WIDE (heads genuinely far apart): 4 of 70 engraved links, 122 of 302 scan links.** MEASURED HERE, §3 of the same file. |
| **a spelling artefact that is not a confusion at all** | the far head of a cross-barline tie does not restate its accidental, so `pitch_resolver` spells it plain: `F#4 → F4`. **11 of the engraved 20 "different-pitch" links are this.** The published "25% of tie pairings bind different pitches" is **at most 9 of 70**. MEASURED HERE. |

### 2. Best method: YOLO / CV / other

Same as the slur, with one addition that is specific to ties: **the tie's
defining fact needs no classifier at all.** Two heads at one staff position,
adjacent in x, one voice — that is geometry, available from the boxes, and it
is what `TIE_SAME_POSITION_MAX_SPACES` uses. A CV reader that traced arcs would
combine with it directly.

⚠️ The one thing that CANNOT be recovered this way is **a tie whose notes were
never detected**, and that is the dominant population: see §5.

### 3. Where on the page the deciding information lives

In the **two flanked noteheads' y positions**, and nowhere else. Everything
about the curve — its thickness, its length, its confidence — is either
identical to a slur's or measured not to separate:

* thickness: identical profile to a slur (Bravura, LITERATURE);
* detector confidence: refused arcs are **more** confident than bound ones
  (median 0.522 vs 0.473), so confidence is not a quality proxy here
  (MEASURED HERE, `omr-arc-recovery` §3);
* width: refused 6.23 vs bound 6.40 staff spaces — no separation (same file);
* depth relative to the heads (`[C40]`: a tie hugs, a slur arcs clear) —
  **no figure exists.** `Q.ARC_POSITION` produces `depth_steps` for 779 and
  2,207 arcs behind `OMR_FAMILY_POSITIONS` (default OFF) and nothing reads it
  (`benchmarks/omr-family-positions-2026-09/FINDINGS.md`). **ASSERTED**, and it
  is the cheapest unmeasured discriminator left in this family because the
  measurement is already on the page.

⚠️ **CURVATURE is explicitly NOT claimed** by that module: a bounding box is
identical for an arc opening up and one opening down, so `opens` is `None`.
Which end of an arc is an ENDPOINT and which the APEX — the fact `[C40]` would
actually need — requires the ink, which `Q.INK` gathers and nothing joins.

### 4. Stage by stage

Identical wiring to the slur — one quantity, one decision — with three
divergences worth naming:

* **EXPORT partitions by kind before pairing.** `_arcs_by_kind` pools ties and
  slurs separately, because a tie and a slur starting on the same head are one
  entry in a head-keyed map and the later silently renames the earlier
  (`staged/export.py:1094`).
* **A tie is not numbered.** MusicXML `<tie>`/`<tied>` join the two notes they
  name and carry no `number=`, so there is no ceiling to drop past — the one
  place a tie and a slur are genuinely different spanners.
* **A tie lands on a specific NOTE of a chord, not on the chord.** Repaired
  2026-09-11: both renderers read `tied_to_next` off the HEAD instead of the
  event's `any()`. **62 marks relocate and 12 are added** over 11 scan rows;
  ONE on the 11 engraved works, and that one tied `G2 → D5` before and
  `D5 → D5` after (`benchmarks/omr-chord-tie-2026-09/FINDINGS.md`, MEASURED
  HERE).

⚠️ **The LEGACY path has a second, older tie pairing that the staged path does
not use** — `transcribe._pair_ties_in_staff` (`:2421`) sets `tied_to_next` /
`tied_from_prev` directly on detections, before `_dedupe_cross_staff_detections`
runs. §"the arc that belongs to a neighbouring staff" records what that
ordering costs.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** `arc_kind` cannot abstain about tie-vs-slur (above). The PAIRING does
not abstain either — it falls through to nearest-in-x. The only honest
abstention in the tie path is EXPORT's refusal to bind fewer than two notes.

⚠️⚠️ **THE ONE PLACE THIS DOSSIER DISAGREES WITH SEAN'S OWN ENTRY, and it is a
disagreement about SCOPE rather than about music.** `position-grammar-
confusables` §ARC names the ambiguity floor and prescribes the best guess:
*"a two-note phrasing slur on a repeated pitch is undecidable from print alone
— default to tie (the duration-semantic reading, the safer error)."*
**Two things:**

1. **We do not do it.** There is no default-to-tie anywhere; `arc_kind` returns
   the detector's class, and where the detector says `slur` over two same-pitch
   heads we write a slur. The prescribed guess is unimplemented.
2. **On a page that prints no ties, defaulting to tie is the WRONG error, and
   the error is a property of the PAGE not of the arc.** `mozart-sym41-mvt1`
   prints 1 tie and 44 slurs; the detector fires 13 ties and **12 are false**,
   and all 8 of the corpus's engraved step-apart links are that one page's. The
   exposure orders by **tie over-detection**, not by slur share — `brahms-sym1-
   mvt1` prints *more* slurs than Mozart and produces **zero** step-apart links
   (`benchmarks/omr-tie-pairing-2026-09/FINDINGS.md` §2, MEASURED HERE).

   So *"default to tie"* is safe for ONE undecidable arc in isolation and is
   the losing bet on a page whose tie detections are mostly false. If we ever
   implement it, the default should be conditioned on the page, not fixed —
   which is a question for Sean (Q&A item 1).

⚠️ **A truth-free self-check exists and is run, and it is one-sided.** A tie
whose two ends resolve to different pitches is certainly wrong; one that
resolves cleanly may still be invented. On the scan corpus **115 of 237 links
(49%) have no end in the next event at all**, and scored on that invariant the
pre-repair arm *"resolves 60 ties where the record supports at most 58"*
(`benchmarks/omr-chord-tie-2026-09/FINDINGS.md`, MEASURED HERE).

**(b)** ⚠️ `ASSUMPTIONS.md` ranked the arcs last of the wiring items *"because
they are self-contained and nothing else waits on them"* — re-checked by grep
here and **still true**. The tie is the one arc that *should* have consumers
and does not:
`respell_accidental` ignores it (§ slur 5b). What DOES lean on the tie is
`Q.VOICES`, in the refusing direction: `_paired_spans`'s one-voice rule
**refuses 22 ties and 9 slurs on Brahms 1** against one tie on Litolff
(`benchmarks/omr-staged-voices-2026-09/FINDINGS.md` §4b, MEASURED HERE). Each
is either a correct refusal or a wrong voice split, and **the print is the only
thing that can say which** — 31 things a human might have to put back.

**Independence:** the same `Q.NOTEHEAD_STAFF_POSITION` argument as the slur,
plus one hard number specific to ties. The box reading and the pitch reading
were cross-tabulated with no truth file:

* **ENGRAVED: 70 of 70 on the diagonal, zero off it.** Two independent readings
  agreeing on every link.
* **SCAN: the diagonal breaks in one direction — 25 links sit at ONE staff
  position and their resolved pitches disagree anyway.**

(`benchmarks/omr-tie-pairing-2026-09/FINDINGS.md` §4, MEASURED HERE.) That is
the cleanest statement in the repo of why the box form is admissible and the
pitch form is refused.

**Evidence grade:** the empty interval and the three-population split, MEASURED
HERE (11 engraved works, 11 scan rows). The absolute same-pitch rule,
LITERATURE. `[C40]`'s depth discriminator, **ASSERTED** — no figure.
Registry: `[C39]` `[C40]` `[C43]` `[L47]`.

---

## the tie CHAIN

Not a mark. The relation that makes `A ~ B ~ C` one sounding note across three
written ones. Produced by no reader; assembled in EXPORT from paired tie spans.

### 1. What sets it apart — and what it is confused with

A chain is the transitive closure of tie LINKS over shared note ends. **A chain
is not a link and the numbers differ by one per chain**: on Breitkopf Brahms 1
pp.0-3, **632 links make 275 chains, 82 of them longer than two notes**; on
Litolff Beethoven 5 pp.1-3, 59 links make 46 chains, 4 longer than two
(`benchmarks/omr-staged-tie-chain-2026-09/FINDINGS.md` §1, MEASURED HERE).
**Quoting links as "ties" over-counts every chain of three or more** — a 30%
error on the second document.

**Confused with:** itself, computed wrong. The reach probe's first cut keyed the
closure on a `start → stop` dict, which loses a head that begins two links, and
read `{2: 50}` on a document whose chains run to four notes. The tell was that
not one chain exceeded two. It is union-find now.

⚠️ **Litolff alone would have made the chain look like a pair** (longest 4, 4 of
46 exceed two) and would have made the system-break case look impossible (zero
there, **two** on Brahms).

### 2. Best method

Neither. It is bookkeeping over already-paired spans — `_chain_sizes`, union-find
over shared ends (`staged/export.py:1306`, called at `:1124`).

### 3. Where on the page the deciding information lives

Nowhere on the page. It lives in the PART: **10 of 59 links cross a barline on
Litolff and 140 of 632 on Brahms; 2 cross a system break.**

### 4. Stage by stage

⚠️⚠️ **THERE IS NO QUANTITY AND THIS IS DELIBERATE.** `tied_to_next` and
`tied_from_prev` are the last two entries in `gather_coverage.NO_VOCABULARY`
(`tools/omr/staged/gather_coverage.py:382`), and they stay there. The argument,
from `benchmarks/omr-staged-tie-chain-2026-09/FINDINGS.md` §3:

* a chain is a fact about a **PART**;
* the part is built in `staged/export.build` from `Q.PART_PARTITION`;
* `staged/__main__.py` serialises the record at `:277`, writes it at `:279`,
  and imports the exporter at `:285` — **EXPORT cannot contribute a record
  row.** ⚠️ The FINDINGS document cites `:140` / `:148`; the lines have moved
  and the ORDER is unchanged, re-checked here against the tree.

Three routes were considered and each refused with a stated reason: an EVALUATE
consequence would depend on EXPORT (backwards, and `_paired_spans` contains a
tie-break, which the plan's own boundary forbids in EVALUATE); a per-arc
decision adds nothing, since `arc_kind` already records the flanked pair within
a cell and the cross-cell chain is exactly what it cannot see; a `Kind.STAFF`
decision reaches 630 of 632 links but would be **a second pairing that can
disagree with the exporter's**, with the file following the exporter.

**What shipped instead is that the exporter SAYS what it did**:
`tie_links_marked`, `tie_links_crossing_a_barline`,
`tie_links_crossing_a_system_break`, `tie_chains_marked`,
`tie_chains_over_two_notes`.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** There is nothing to abstain. The chain is derived, not read.

**(b)** ⚠️ **The refusal has already been paid for once.** Repairing the tie
pairing in `transcribe` required mirroring it by hand into
`export._tie_flank_pair` — because **the two copies already exist** — with the
constant imported so only the arithmetic is restated. That is the concrete cost
of the "second pairing" hazard, arriving the same day the refusal was written.

**Evidence grade:** every figure MEASURED HERE, 2 documents, 2 publishers, 7
pages. The architectural argument is a reading of the tree (`__main__.py` line
order), verifiable in one `grep`.

---

## the cross-barline arc

One printed curve, detected as two, because the measure cell is our cut and not
the engraver's.

### 1. What sets it apart — and what it is confused with

⚠️ `position-grammar-confusables` §ARC disposes of this in one clause —
*"pairing across barlines and system breaks already exists for both"* — and it
is right that the mechanism exists. What that line does not carry is **the
three constants, their gaps, and the rate**, which is what this section is for.

**The two fragments are recognisable: each terminates AT its cell's own
boundary rather than in open space, and they are adjacent and at the same
height.** Three constants, each read off a measured gap on the Brahms fixture
(`benchmarks/omr-ned-2026-08/SLURS_2026-09-01.md`, MEASURED HERE):

| what it decides | the two clusters (staff spaces) | constant |
|---|---|--:|
| an arc was CUT by the boundary | 0.00–0.10 vs 1.58 | `_SLUR_BOUNDARY_SPACES` 0.5 |
| the two halves are ONE arc | 0.02–1.14 vs 8.04 | `_SLUR_CONTINUATION_DY_SPACES` 2.0 |
| a notehead is UNDER the arc | 0.00–0.19 widths vs 0.32 | `_SLUR_ARC_PAD_NOTEHEADS` 0.25 |

Each is a **PLATEAU, not a peak** — the export is identical for the continuation
tolerance anywhere in 1.0–6.0. ⚠️ **Re-check them when the geometry beneath
moves**: the continuation cluster's top went 0.53 → 1.14 across the
system-grouping change, still inside the gap, but it moved.

**Rate:** **38 of 514 arcs (7.4%) are one half of a cross-barline pair** on
Litolff pp.1-3; **32 of 199 (16.1%) begin at their cell's left edge** on one
page; **31 of 261 tie groups** and **329 of 1,227** on Brahms were merged from
two detected halves. All MEASURED HERE.

**Confused with:** two separate arcs. Emitting each half writes two marks where
the music has one — which is why an implemented and tested `annotate_slurs` was
kept OUT of the legacy exporter until 2026-09-01. ⚠️ **And OMR-NED would not
have caught it**: the metric is symmetric, so emitting more is rewarded; the
legacy slur work's first cut LOWERED pooled OMR-NED while RAISING the edit
count.

### 2. Best method

Geometry, and it is already geometry. Nothing to change.

### 3. Where on the page the deciding information lives

**In `Q.CELL_BOX` — the cell's own rectangle in page pixels — and this is the
one frame nothing can stand in for.** `record.py:331` states it: deriving the
edge from the glyphs inside would put it wherever the outermost detection
happens to fall, so an arc genuinely reaching the barline would test as ending
in open space, *and the wider the empty margin the more certainly the two halves
stay two slurs*.

⚠️ **`gather_detections` had read `cell.bbox_page_px` since the day page boxes
arrived and threw it away after converting one glyph.** That is why `arc_kind`
and `arc_owner` could decide 199 arcs a page with no route to a file.

⚠️ **`Q.CELL_BOX` is a GATHER change, so `readjudicate.py` and
`reexport_arm.py` are both STRUCTURALLY BLIND to the arc merge.** An A/B there
needs two full re-gathers.

### 4. Stage by stage

**GATHER** files `Q.CELL_BOX`. **ADJUDICATE does not touch it** — `arc_kind`
reads the flanked heads in the cell's own canonical frame, which is correct
because both were cut from one cell. **EXPORT** merges:
`_legacy._merge_arcs_across_barlines` (`tools/omr/export.py:2498`), called from
`staged/export._pair_arcs`, **imported and not ported**, so the three constants
live in one place.

⚠️ **The merge is a PART pass, not a measure pass**, because only a part spans
the junctions.

⚠️ **A bar whose geometry is missing swallows its arcs silently** — the merge
opens each bar with *"no box, or no spacing, break the chain and move on"*,
which is right, but its `continue` skips that bar's arcs entirely. They are now
counted as `arc_bar_has_no_geometry`.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** Yes, structurally: a fragment that finds no partner simply stays its own
arc and is then refused for binding fewer than two notes. That is a safe
failure. ⚠️ But it is **indistinguishable in the file** from an arc that was
never cut.

⚠️⚠️ **THE ONE REACH THAT IS REFUSED, AND THE REASON IS WORTH KEEPING.** The
same crops show a second failure: a slur running from the chord at the end of
bar N to the chord at the start of bar N+1, whose continuation fragment is ~0 px
wide because that chord sits at the bar's very beginning — so the merge has
nothing to join to. Modelled, it is worth **+13 alone and +19 on top of the stem
rule, and the two are SUPER-ADDITIVE (171 → 199 → 218)**. It is **refused**
because the window it needs sits on a distribution of ENGRAVING, not of this
arc: a bar's first note is **2.0–2.5 staff spaces past the barline on all 282
edge-reaching arcs** (`[C44]`, MEASURED HERE), so any window wide enough to
admit it admits *every* next-bar first note and the rule degenerates to *"an arc
touching a barline lands on the next bar's first note"*. **The distribution is
TIGHT, which is precisely the problem.** That is INFER-shaped work.

**(b)** Nothing leans on it. It changes only whether one `<slur>` or two are
written.

**Evidence grade:** all three constants MEASURED HERE on an engraved fixture;
the rates MEASURED HERE on 2 scanned documents. `[C38 + L50]`, `[C44]`.

---

## the cross-system-break arc

The same curve, cut by the end of a system instead of by a barline — and the
two halves are NOT symmetric.

### 1. What sets it apart — and what it is confused with

⚠️ Same one-clause coverage in `position-grammar-confusables` §ARC, and the
same gap: **the two halves are not symmetric and that entry treats them as one
mechanism.**

⚠️ **A cell edge cannot be used on the resuming side.** The new system's first
cell opens with a clef and a key signature, so the resuming arc begins well
inside it — **measured at 5.28 staff spaces** on the `systems` fixture, and
further on any score with more accidentals. *A constant for that would be a
constant for how wide a clef is.*

**So the anchor is the FIRST NOTE**, which is what the fragment actually
attaches to and is independent of the header's width. A resuming fragment lies
entirely BEFORE that note (measured: arc x [400, 503] against a first notehead
centred at 504); a slur that merely BEGINS on the first note runs the other way.
**The two are told apart by which side of the note the ink is on, not by a
threshold** (`tools/omr/export.py:2467` `_resumes_after_system_break`, MEASURED
HERE, n = 1 fixture).

⚠️ **Heights are compared RELATIVE to each staff's own top line.** Absolute page
y is meaningless across a break — the two staves are different objects a whole
system apart.

**Confused with:** an arc that simply starts the new system.

**Reach — and it is thin.** **0 links cross a system break on Litolff
pp.1-3; 2 on Brahms pp.0-3** (`omr-staged-tie-chain` §1, MEASURED HERE).
⚠️ **Litolff alone would have made this case look impossible.**

### 2. Best method

Geometry. Already geometry.

### 3. Where on the page the deciding information lives

In the resuming bar's **first notehead**, and in each staff's **own top line**.
Note this is the one arc rule whose deciding fact is a *note*, not a cell edge —
and it therefore inherits notehead detection directly.

### 4. Stage by stage

EXPORT only. `annotate_slurs_in_slot` runs the merge along a SLOT (the same
printed part across systems), which exists because `_stitch_slots` made a part
the same staff on every system.

⚠️ **LilyPond deliberately never receives one** — it emits one `\new Staff` per
system-staff and a LilyPond slur cannot span two Staff contexts.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** Same as the barline case: no partner found, the fragment stands alone
and is then refused.

⚠️ A system break is also where `_merge_arcs_across_barlines` resets `pending`
on a bar with no geometry — so a bad bar at a junction loses the join silently,
and that is now counted.

**(b)** Nothing.

**Evidence grade:** the 5.28-space figure and the first-note anchor, MEASURED
HERE on **one authored fixture** (`e2e_fixtures.build_systems`, the only
multi-system fixture in the repo). The reach, MEASURED HERE, n = 2 documents.
⚠️ **This rule has never been measured on a scanned multi-system page with a
hand-read truth.** `[C38]`'s "known exceptions".

---

## the arc that belongs to a NEIGHBOURING staff

A slur or tie printed over one staff's ledger notes, drawn in the gap between
two staves, and detected in the WRONG staff's measure cell.

### 1. What sets it apart — and what it is confused with

⚠️ **No prior document covers this one.** `position-grammar-confusables` is
organised by MARK and this is a failure of the CROP, not of the mark; the
family-positions work measures the arc's own position and not its neighbours'.
Everything here is from `benchmarks/omr-arc-attribution-2026-09/` and
`adjudicators/ownership.py`.

⚠️⚠️ **It need not be detected twice, and that is what makes it different from
the notehead contest.** A measure cell is padded 4–6 staff spaces above and
below (`measure_extractor.PAD_*_STAFF_LINES`), and where the gap is wide the
upper cell reaches ink the lower cell does not — so **the arc exists ONLY in
the wrong staff and no duplicate-resolution rule can see it.**

**The worked example, with the print consulted** (`brahms-sym1-mvt1` system 0):

| | page y |
|---|---|
| Timpani staff, top → bottom line | 7093 → 7259 |
| the disputed arcs | 7272 → 7460 |
| Violin 1's ledger noteheads | ~7300 → 7400 |
| Violin 1 staff, top line | 7580 |

The Timpani exported **4 slurs and 1 tie against a truth of ZERO**; every one is
Violin 1's, drawn over ITS four-ledger-line notes in the 7.7-space gap. ⚠️ **The
earlier guess — "the staff BELOW's arcs caught in the padding" — was wrong, and
rendering the page is what corrected it.**

⚠️⚠️ **DISTANCE TO THE STAFF LINES IS THE TRAP, exactly as it was for notes.**
An engraver opens the gap above a staff *precisely so* its ledger notes and
their slurs can live there — which puts them nearer the staff above. Four of the
Timpani's arcs sit 1.1–3.3 spaces below the Timpani's bottom line, *exactly
where a real slur under a staff would sit*.

**The evidence is the arc's own job: it belongs to the staff whose NOTEHEADS IT
HUGS.** Clearance in staff spaces to the nearest covered head, 11 engraved works
(`benchmarks/omr-arc-attribution-2026-09/FINDINGS.md`, MEASURED HERE):

| own clearance | part whose truth has NO arc | part whose truth has arcs |
|---|--:|--:|
| [0.00, 0.25) | 5 | 165 |
| [0.25, 0.50) | 0 | 31 |
| [0.50, 0.75) | 1 | 8 |
| [0.75, 1.00) | 1 | 0 |
| [1.00, 1.50) | 2 | 1 |
| [1.50, 2.00) | 0 | 2 |
| [2.00, 3.00) | 6 | 0 |
| [3.00, inf) | 2 | 30 |

**204 of 237 arcs on arc-bearing parts sit under half a space.** ⚠️ **That tail
is not clean enough to threshold on** — 33 sit above 0.5 — **so the rule is
COMPARATIVE**: an arc leaves a staff only where another staff of the same system
explains it better. It cannot fire at all on a one-staff page.

### 2. Best method

Neither YOLO nor CV. **A contest between already-arbitrated notehead sets** —
the same shape as the notehead ownership rule, which is why `arc_owner` runs
*after* `glyph_owner` in `ORDER` and reads its verdicts.

### 3. Where on the page the deciding information lives

**In the OTHER staves' noteheads, in PAGE PIXELS.** This is the only arc
question that cannot be answered inside one cell.

⚠️⚠️ **The input was in the wrong frame until 2026-09-09.**
`gather_glyph_families` emitted canonical coordinates only — measured inside ONE
cell, where two staves' frames coincide by construction — so `arc_owner`'s
declared input was present and **could not answer its own question**. A row with
no page box now abstains `no_page_frame`; it is never compared in the cell
frame. *A quantity can be gathered in the WRONG FRAME and look fed.*

⚠️ **The head sets are grouped by the head's OWNER, not by the staff its cell
was cut from**, because the noteheads have already been arbitrated and each
staff's set is *the one a reader would see*.

### 4. Stage by stage

| stage | |
|---|---|
| GATHER | `Q.ARC_BOX` with `bbox_page_px`; `Q.STAFF_SPACING` per staff |
| ADJUDICATE | **`adjudicate_arc_owner`** (`ownership.py:191`), after `glyph_owner`. Constants `_ARC_RIVAL_NEAR_SPACES` 0.75, `_ARC_RIVAL_MARGIN_SPACES` 0.5, `_ARC_RIVAL_MIN_COVERED` 2 — **IMPORTED from `tools/omr/export.py`, never restated** |
| EVALUATE / INFER | nothing |
| EXPORT | `_place_arcs` puts each arc in the cell its OWNER names |

⚠️ **`OMR_ARC_ATTRIBUTION` is a LEGACY-path flag only** (`export.py:1944`). On
the staged path the rule is a decision that always runs; there is no flag. The
two share their constants.

⚠️ **IT MOVES, IT NEVER DELETES.** `drop` measured **2,388 edits against
`move`'s 2,371** — better arm-for-arm — and was **REFUSED**, because it gets
there by emitting 20 fewer slurs, **12 of them real**: the symmetric metric's
under-prediction reward. Keeping the loser addressable is what lets a later
identity correction reach it.

**Reach:** `arc_owner` moves **12 of 199 arcs** on one page, and **every move is
to an ADJACENT staff — ±1, six each way, zero exceptions.** Nothing in the rule
knows about adjacency; it fell out, and it is the measure-cell padding
signature. Moved arcs sit 3.80–9.24 spaces from their own heads (6 of 12 cover
NOTHING there); arcs that stay sit at a median 0.530. MEASURED HERE.

### 5. Abstain or best-guess — and what leans on this mark's certainty

**(a)** Yes, and it distinguishes three things a weaker design would merge:
`no_page_frame` (an abstention — I cannot see this in the right frame),
`no_rival_staff` (a DECISION — nobody else explains it, and on a one-staff page
this is the only possible answer), and `no_better_staff` (a DECISION — somebody
else was considered and lost). `Ruling(value=own, reason="no_rival_staff")` is
deliberately not an abstention.

**(b)** ⚠️⚠️ **The staged and legacy paths disagree about ordering, and the
legacy one leaves ORPHANED FLAGS.**

```
transcribe.py:2289  _pair_ties_in_cell              sets tie flags
transcribe.py:5428  _pair_ties_in_staff             sets tie flags
transcribe.py:5557  _dedupe_cross_staff_detections  REMOVES the losing copy
```
(call sites re-checked against this tree; the FINDINGS document cites `:5356`
for the middle one and the order is unchanged.)

Both copies pair; then dedupe deletes one **and the flags it set stay behind**.
**27 of 148 engraved tie flags (18%) sit in a staff holding no tie glyph, and 27
of 27 are explained by the next staff down holding it** — zero exceptions, the
same signature `arc_owner` reported for its twelve moves. Scan side: 5 of 460
(1.1%), because there the duplicate is usually never detected at all.
**NOT REPAIRED** — nothing can clear a flag without knowing which glyph set it,
which is `Q.TIE_LINK`, which is the argued negative above. This is the chain's
third symptom. (`benchmarks/omr-tie-pairing-2026-09/FINDINGS.md` §6, MEASURED
HERE.)

⚠️ **A fourth relocation site still exists and is unpriced:** `arc_owner` and
`wedge_anchor` build their per-staff head sets by mapping every notehead to its
OWNER, so a contested head enters the owner's set TWICE.

⚠️ **`_place_arcs` has no dedupe.** 48 pairs of arcs land in one cell at
IoU ≥ 0.7, **19 detected on two different staves**, several disagreeing about
their own kind (one slur and one tie at IoU 0.995). Where one printed curve is
detected twice, BOTH copies are placed — the shape `_place_notes` was repaired
for the same day (`A.is_relocated_copy`), one family over. An arc has no
`is_relocated_copy` equivalent. MEASURED HERE, not repaired.

**Independence:** `arc_owner`'s witness is the *other staves' noteheads*, read
off the same raster as the arc. It fails on the same pages — a page whose notes
are not detected gives it nothing to compare. ⚠️ **But the failure mode is
benign**: with no rival it returns `no_rival_staff` and the arc stays where it
was found, which is the status quo ante rather than a wrong move.

**Evidence grade:** clearance table and both plateaus MEASURED HERE (11 engraved
works). The 12-moves-all-adjacent figure MEASURED HERE (1 scanned page). The
27-of-27 orphan figure MEASURED HERE (11 engraved works). `[C35]`, and the rule
is in `ownership.py` rather than the registry.

---

## What we do not know

1. **Whether "default to tie" is the right guess.** Sean's own ambiguity floor
   (`position-grammar-confusables` §ARC) is unimplemented, and the one
   measurement bearing on it says the safe direction is page-dependent. Nobody
   has adjudicated an undecidable two-note same-pitch arc against a print.
2. **Whether any arc we write is PRINTED.** Every figure in this dossier except
   the 126-cell human adjudication and the Brahms Timpani crop is an
   **agreement rate between two readings of the same ink**. `arc_kind`'s grammar
   agrees with the detector on 42 of 81 and disagrees on 39 — *a coin flip* —
   and neither is truth. S6 agreeing 74% in the tight band is consistent with
   both being right and with both sharing a bias.
3. **Whether a classical-CV arc tracer would work.** It is the tree's own
   recommendation and **nobody has built one.** The 260 adjudicated fakes are
   sitting there as its gauntlet.
4. **`[C40]` — does a tie sit shallower than a slur?** `depth_steps` is produced
   behind `OMR_FAMILY_POSITIONS` (default OFF) and read by nothing. **No figure
   exists.** It is the only untested geometric discriminator left that does not
   touch a pitch.
5. **Curvature.** Which way an arc opens — and therefore which corners of its
   box are its ENDPOINTS — is not derivable from a box, is recorded as `None`,
   and needs `Q.INK`, which gathers it and which nothing joins.
6. **The system-break rule on a scan.** Measured on one authored fixture, n = 2
   real crossings in the whole corpus.
7. **The second publisher for S4 and S6.** Both measured on Litolff `984073`
   only — the *low-res bitonal* end of the corpus. A print whose slurs are drawn
   over noteheads rather than over stems would give S4 a different distribution
   entirely.
8. **Whether the 31 spanners the voice rule refuses on Brahms are real.** Each
   is either a correct refusal or a wrong voice split. Only the print can say.
9. **Whether the arc BOXES are mislocalised on a scan, or the pad is wrong.**
   The pad sweep says B decays smoothly with no plateau, which is consistent
   with either, and the split probe could not separate them.

## Questions for Sean

1. **Your own ambiguity floor: "default to tie, the safer error."** We never
   implemented it, and the measurement since says the safe direction depends on
   the PAGE — Mozart 41 prints one tie and we detect thirteen, so on that page
   defaulting to tie is the losing bet. Would you accept the rule conditioned
   on the page (*"default to tie unless this staff's tie detections outnumber
   what a page like this prints"*), or is the fixed default still the one you
   want?
2. **Should `arc_kind` be allowed to abstain?** Today the detector's class IS
   the answer, so *"this is an arc but I cannot tell which"* is unsayable —
   which is the same shape as your *"the model's class breaks genuine ties"*,
   except that the model breaks ALL of them, not only the genuine ones. A
   truth-free test would license an abstention (the flanked heads' staff
   positions, available on **345 of 779 arcs**). The cost is that a refused arc
   writes nothing, which on a cleanup count is a gap rather than a wrong mark.
   Is a gap cheaper for you than a wrong kind?
3. **`[C40]`, the depth rule — is it real?** *A tie is drawn shallow and close
   to its two heads; a slur arcs clear of the notes under it.* We measure
   `depth_steps` already and read it nowhere. If you would back it as an
   engraving fact, it is the last geometric discriminator we have that needs no
   pitch, and it would be cheap to price.
4. **The cross-barline reach (`[C44]`) is worth +19 arcs and we refused it**,
   because a bar's first note is 2.0–2.5 spaces past the barline on *all 282*
   edge-reaching arcs — so any window that admits it admits every next-bar first
   note. Is *"an arc touching a barline binds the next bar's first note"* a rule
   you would accept as a stated approximation, labelled as inferred?
5. **S6 needs seventy crops**, not more arcs. Of two arcs stacked over the same
   notes, is the lower always the tie? It holds at 0.740 on 73 disagreeing pairs
   within three staff spaces, and it is NOT the hugging rule restated (the
   control ran and the two arms coincide on under half of all pairs). Seventy
   hand-adjudicated stacked pairs would settle it.
6. **The 27 orphaned tie flags** — a note carrying `tied_to_next` in a staff
   holding no tie glyph, because dedupe deleted the glyph after the flags were
   set. Fixing it properly needs a tie LINK quantity, which we argued against
   building. Would you rather we simply CLEAR a tie flag on a staff with no tie
   glyph anywhere near it, accepting that we may clear a real one?
7. **`ff` vs `ffff` had an equivalent here and we do not know its size**:
   `_place_arcs` has no dedupe, so one printed curve detected twice is written
   twice — 48 pairs in one cell at IoU ≥ 0.7 on one page. Is a doubled slur
   something you would notice on a cleanup pass, or does it read as one?
