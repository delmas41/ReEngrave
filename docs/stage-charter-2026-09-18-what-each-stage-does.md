# The stage charter: what each stage does, what the build actually does, and the three places they disagree

**2026-09-18.** Written in answer to Sean's *"Can you tell me what you think
each stage does?"*, and to record his own statement of what they SHOULD do,
because it is the clearest statement of the architecture's intent anyone has
written and it does not otherwise exist in the tree.

Read with [docs/diagnosis-2026-09-18-who-actually-decided-it.md](diagnosis-2026-09-18-who-actually-decided-it.md),
which measures the consequence.

---

## 1. SEAN'S STATEMENT OF INTENT, 2026-09-18, in his words

> *"Shouldn't each step be asking is this what we think it is? If it is
> undefined it should be asking what could it be, what is it likely to be, what
> is the context telling us? If it is declared as something already — does what
> we know about the context confirm or question this. That is the point of the
> stages: each should add a level of certainty to the answer. **No level should
> absolutely declare something that never gets questioned again** unless in our
> testing we are getting it right 100% of the time.*
>
> *So GATHER collects it without naming or categorizing it. Its whole purpose is
> to make sure we have all the information we can get from the page — ink,
> geometry, position, CV, YOLO, dossier, instrumentation. **This is where we tune
> the size of boxes or determine if boxes are the correct way to label
> something** — all information about anything on the page without declaring what
> it is, and it should make that information available to all stages.*
>
> *`NO_INK` shows me that we are discarding information that should be black and
> white. The next stage should be where we start to use the information we know
> about symbols to determine if we can decide what something is: this is a whole
> note rest because it is a square that sits on top of the line — YOLO will help
> with this along with our rules. **Each stage needs to be clear about what it
> does and doesn't do.**"*

---

## 2. WHAT THE FIVE STAGES ARE CHARTERED TO DO

The charter in `CLAUDE.md` and in `adjudicate.py`'s docstrings. ⚠️ **Sean's
second stage is ADJUDICATE, not EVALUATE** — his description of it ("start to
use what we know about symbols to decide what something is") is ADJUDICATE's
charter almost word for word. EVALUATE is something narrower and it matters.

| stage | the question it asks | it acts when | its discipline |
|---|---|---|---|
| **GATHER** | what is on the page? | **always** | **it decides NOTHING** |
| **ADJUDICATE** | what does this ONE thing mean, and on what evidence? | it can read it | else it **ABSTAINS**, recording what it looked for and did not find |
| **EVALUATE** | what follows **NECESSARILY** from what we now know? | the answer is **FORCED** | goes **SILENT** where the answer is merely likely |
| **INFER** | what is most **LIKELY**, given everything at once? | the answer is **BEST** | may only speak where the record has **no answer**, and must **LABEL** everything it does |
| **EXPORT** | write it, and **count what did not make it** | always | the accounting control is an **EQUALITY**, not a `<=` |

**The property the split exists to keep sayable:** *everything in the record
before EXPORT was READ or ENTAILED; everything after INFER was read, entailed,
or INFERRED — and labelled.* The boundary is exactly where the guarantee
changes, which is the right place for one.

### The worked example, because it shows the stages correcting each other

One real note (`glyph/1/0/2/4/1`): the detector calls it `noteheadHalfInSpace`
at confidence 0.299, and geometry measures its staff position at 7.38 **with no
confidence at all** — a ruler reading is not a guess, and GATHER keeps that
distinction. ADJUDICATE reads it as a **QUARTER**, *against the detector's own
class name*, because a beam is attached to its stem and a beamed note cannot be
a half note — recording `missing: aug_dot, flag, rest, tuplet_ratio`. EVALUATE
then derives **F4** from position + clef (pure entailment) and, noticing the bar
does not sum, re-reads the note and **corrects it back to 2.0** — the half note
the detector called in the first place.

**So ADJUDICATE was wrong and EVALUATE fixed it.** That is Sean's principle
already working. ⚠️ And it is still not inference, because of one word in
EVALUATE's own rule: *where more than one re-reading lands the bar exactly,
NOTHING changes and the warning stands.* It acts where forced and goes quiet
where merely likely.

---

## 3. ⚠️⚠️ WHERE THE BUILD DIVERGES — THREE PLACES, AND SEAN NAMED THE FIRST

### 3a. GATHER decides, in three places, against its own charter

Its charter says *it decides NOTHING*. Verified in the tree, it does:

1. **It files the DETECTOR's class as a FACT.** `gather.py:373`,
   `log.observe(g, Q.NOTEHEAD_CLASS, d.smufl_name, …)`. An observation is not a
   decision — nothing weighs it, nothing can abstain on it. And **routing is BY
   CLASS** (`export._claims`, `gather_glyph_families`), so a barline called a
   notehead enters the notehead family and **can never become a rest row**.
   Of 28 adjudicators, exactly ONE ever questions it, narrowly
   (`adjudicate_notehead_is_a_whole_rest`).
2. **`detect_stems` discards candidates with six filters, inside GATHER**, and
   only survivors are recorded — so *whether ink is a stem* never reaches a
   stage, and a rejected candidate produces **no row at all**.
3. ⚠️⚠️ **And it reports the discard as an EMPTY PAGE.** `gather.py:1305-1311`
   writes `ABSTAIN.NO_INK` — *"no ink"* — for a cell whose every stem candidate
   was rejected by a filter, on plates where the census proves the dominant
   cause is *a component EXISTS and is the wrong SHAPE* (**86%** / **74%**).
   **This is the thing Sean identified unprompted**: *"`NO_INK` shows me that we
   are discarding information that should be black and white."* He is right, and
   it is the ABSENT/DECLINED collapse `record.py` exists to prevent.

⚠️ **`Q.INK` is the charter implemented correctly and it is READ BY NOTHING.**
One row per connected piece of ink, named or not, classification as an
*attribute that may be zero*, built on Sean's own *"ink is ink; there is nothing
that should be classified as unseen — only unclassified"*. Default-ON. Verified
absent from every adjudicator, consequence, inference and the exporter.

### 3b. ⚠️⚠️ "Each stage questions the previous" CONFLICTS WITH A MEASURED RULE — and the conflict has a clean resolution

Sean: *no level should absolutely declare something that never gets questioned
again.* The current design goes the OTHER way as the stages progress: **INFER
may NEVER overturn a DECIDED reading** (`INFERABLE` is `{NARROWED, ABSTAINED}`),
and `export.py` **refuses to argmax** a narrowed duration even though the
candidates carry support and an argmax is one line away.

**Those refusals are not timidity and must not be removed casually.** The reason
is measured: calibrated identity probabilities scored **ECE 0.1277 and failed
WORST at the top of the range** (the top bin promising 0.989 and delivering
0.692). So a later stage permitted to overturn a reading would launder a guess
over a measurement, confidently. *An uncalibrated probability is worse than
none.*

⚠️ **THE RESOLUTION IS TO SEPARATE TWO THINGS THE ARCHITECTURE CURRENTLY
CONFLATES:**

* **QUESTIONING** — recording that a later stage's evidence DISAGREES with a
  standing answer. This should be universal, and it is exactly what Sean asks
  for. It launders nothing, because it changes no value.
* **OVERTURNING** — replacing the value. This should stay restricted, and the
  restriction should stay evidence-based.

**The repo already has one instance of this done right**, and it should be the
template: the middle-line stem convention is *"not shipped as a reader — it
would inherit the position's faults — and it is good for the opposite: a
confident stem and a confident convention that disagree NAME A ZONE TO LOOK
IN."* That is questioning without overturning. There is no general mechanism
for it; it was done once, by hand, for one quantity.

### 3c. ⚠️ EVALUATE structurally CANNOT look sideways — which is where "context" lives

Every EVALUATE consequence is `cause -> effect`, **vertical**: from a settled
decision down to what depends on it. **No consequence can look at the other
eleven staves playing the same stretch of time.** Sean's own efficiency insight
— *"we don't need much info from a particular symbol because we have what we
need elsewhere"* — is entirely **horizontal**, and there is nowhere in the
current architecture for it to live.

⚠️ `Q.ONSET_COLUMN` measured that redundancy and is real (**1,483 real instants
against a phase-shuffled null's 2,409**) and **nothing consumes it.** INFER is
the stage that may look sideways, and it currently has two rules, both about
duration.

---

## 4. ⚠️ TWO PLACES SEAN'S MODEL NEEDS A QUALIFIER, both measured here

1. **"Each stage adds a level of certainty" — only if the new evidence is
   INDEPENDENT.** This repo has been bitten **four times** by witnesses that
   look independent and are not: *the bars are not an independent umpire over a
   bad reading* (a page whose meter the reader mangles is a page whose bars do
   not sum); the arc grammar can speak only about the arcs it reads best
   (available on 81 of 199, and confidence 0.408 vs 0.563 on the ones it
   cannot); an arbiter that shared the **FRAME** with one party sided with it 79
   times in 83; and two sessions agreed on a false claim through a shared
   **ASSUMPTION**. **Adding a reader that comes off the same raster adds the
   APPEARANCE of certainty.** The rule the repo settled on: *a second witness
   must not come off the same raster* — which is why `source_kind` is
   load-bearing and why the dossier and the catalog roster are admissible where
   an OMR output of the same page is not.
2. **"unless in our testing we are getting it right 100% of the time" — the
   threshold has to be per-DOMAIN, and on the plates that matter it may be
   unreachable.** Noteheads are **0.999 (856 of 856)** on the ENGRAVED family —
   genuinely the 100% case. On a scan, the crop pass measured that **~60% of
   noteheads cannot have their stem adjudicated by eye at all**, controls and
   sample alike, and that plate is bitonal at its native resolution so nothing
   better exists. **A rule allowed to declare unquestionably on engraved
   evidence would be declaring unquestionably on scans too.**

⚠️ **And his box question is live, not rhetorical.** *"This is where we tune the
size of boxes or determine if boxes are the correct way to label something"* —
the repo already has the evidence that boxes are the wrong representation for
some ink: stems and beams were moved to classical CV on the stated ground that
**YOLO bounding boxes are structurally bad at thin lines**, and a box drawn
round a fused blob measures the BLOB, which is the whole of the width-cap
problem (a stem joined to its own notehead reads as "too wide" and is
discarded). `Q.INK`'s connected components are already a different
representation, sitting unread.

---

## 5. WHAT THIS IMPLIES, ordered by cost — proposals, not decisions

1. **A per-subject TRACE** so any symbol's journey through all five stages is
   legible. **Dispatched** (`claude/stage-trace-noteheads-2026-09`). Read-only;
   answers the question directly.
2. **`NO_INK` must mean no ink.** A filtered-out candidate needs its own reason
   word — *declined*, not *absent*. Cheap, but it changes what every record
   says, so it is a call.
3. **A general mechanism for QUESTIONING without OVERTURNING** (§3b): a stage
   may record a disagreement against a standing answer without replacing it.
   This is Sean's principle made safe, and the stem-convention precedent shows
   the shape.
4. **Read `Q.INK`** as the independent witness for *is there ink where we claim
   emptiness* — its first consumer, and the one that does not come off the
   detector.
5. **Make the two foundational claims stageable** — *is this a notehead*, *is
   there a stem* — so they can abstain and be revisited. ⚠️ **This is the big
   one and it is not a repair**: routing is BY CLASS today, so unnaming GATHER
   means every family's dispatch changes. It should be costed before it is
   started.

---

## 6. ⚠️ WHAT THIS DOCUMENT DOES NOT CLAIM

* **It does not argue the stages are the main source of bad readings.** Much of
  the measured loss is upstream of all of them — three quarters of detected arcs
  bind fewer than two noteheads *because the notes were never detected*; one
  edition reads 22% of per-staff durations right against another's 59%; a third
  of one edition's "note heads" are not noteheads. **Stage plumbing cannot fix
  those**, and the trace instrument has been told that finding the pipeline
  healthier than expected is an equally valuable result.
* **Nothing here was priced.** No arm was run; it is a reading of the tree plus
  Sean's statement.
* **§3b's resolution is a PROPOSAL and has never been built or measured.**
* The record-size cost of an ink-first GATHER is real and known: `Q.INK` alone
  adds **0.6 MB/page** (Litolff) and **3.1 MB/page** (Breitkopf), against
  records already in the hundreds of MB. Sean's standing instruction is to hold
  everything **during discovery**; that is scoped, not permanent.
