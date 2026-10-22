# Diagnosis: WHO actually decided it? — why "we couldn't read it" and "a stage broke it" are currently indistinguishable

**Written 2026-09-18 in answer to Sean's question**, and written down because it
is the diagnosis a lot of recent work has been circling without stating:

> *"Right now I don't know, when something is declared as something, if the
> issue was that we couldn't read it or that it got messed up in the stages."*
> — and, of the crop pass's *"a third of one edition's note heads are not note
> heads"*: *"what do you mean by HANDED? The gather stage alone declared that?
> It went through all the stages and declared that?"*

⚠️ **Every claim here was verified against the tree at the commit this document
lands on, with the command that verifies it.** Nothing is quoted from a handoff.
Line numbers drift — the greps do not.

---

## 1. THE SHORT ANSWER

**"Handed" means the DETECTOR said so, before any stage ran, and no stage ever
re-examines it.**

A box's class — *this is a notehead* — is the YOLO detector's output. GATHER
records it as an **observation**, i.e. as a FACT about the page
(`gather.py:373`, `log.observe(g, Q.NOTEHEAD_CLASS, d.smufl_name, …)`). An
observation is not a decision: nothing weighs it, nothing can abstain on it, and
**there is no adjudicator anywhere that asks "is this ink a notehead?"**

Of **28 adjudicators** in `tools/omr/staged/adjudicators/`, exactly **one**
touches the question, and it is narrow by design:
`adjudicate_notehead_is_a_whole_rest` (`rhythm.py:3001`, the rule behind
`OMR_WHOLE_REST_INK`) asks only *"is this particular notehead actually a whole
rest?"*. **That is the only place in the pipeline where any stage second-guesses
the detector about what a piece of ink IS.**

```bash
grep -n "Q.NOTEHEAD_CLASS" tools/omr/staged/gather.py          # the class is OBSERVED
grep -rnc "^def adjudicate_" tools/omr/staged/adjudicators/    # 28 adjudicators
grep -rn "^def adjudicate_.*notehead" tools/omr/staged/adjudicators/   # exactly 1
```

⚠️ **And the misclassification is then LOAD-BEARING, because routing is BY
CLASS.** `gather_glyph_families` and `export._claims` dispatch on the class name
(`export.py:3025-3034`), so a barline the detector called a notehead **enters the
notehead family and can never become a rest or a barline row.** CLAUDE.md
already records this for the whole-rest case in exactly these terms: *"a
DETECTOR error upstream of GATHER, where routing is by class, so it can never
become a `Q.REST` row."*

**So the 46-of-180 finding is not a stage failure. It is a reading failure that
every stage inherits and none can question.**

---

## 2. WHERE EACH KIND OF "WE SAID X" IS ACTUALLY DECIDED

This is the table the question deserves, and its point is that the answer
differs per claim:

| the claim | who decides it | can it abstain? | can a later stage revisit it? |
|---|---|---|---|
| **this ink is a NOTEHEAD** (its class) | the **DETECTOR**, before GATHER | **no** — it is `observe`d as a fact | **no**, except the one whole-rest rule |
| **this ink is a STEM** | six filters **inside `detect_stems`**, in GATHER | **no** — only survivors are recorded | **no** — a rejected candidate produces no row |
| **which DIRECTION the stem points** | `adjudicate_stem_direction` (ADJUDICATE) | **yes** | yes |
| **how long the note lasts** | `adjudicate_duration`, then `reconcile_duration` may CORRECT it | yes (`narrow`, `abstain`) | yes — EVALUATE corrects ADJUDICATE here |
| **which staff owns a contested glyph** | `adjudicate_glyph_owner` | yes | yes |
| **whether it reaches the FILE** | `export.py` counters | n/a | n/a — it is the last word |

⚠️ **The pattern: the two most basic questions — *what is this* and *is there a
stem* — are the two that never reach a stage.** Everything downstream is
carefully staged, abstainable and recorded. The foundation is not.

---

## 3. THE THREE THINGS THAT CURRENTLY LOOK IDENTICAL

When the pipeline produces nothing for a symbol, it is one of three things, and
**the record cannot presently tell them apart**:

1. **THE PAGE IS BLANK.** Nothing was printed. A correct silence.
2. **WE COULD NOT READ IT.** Ink is there; no reader could name it.
3. **A STAGE DECLINED IT.** Ink is there, a reader found it, and a rule rejected
   it — a *decision*, which should be reviewable.

⚠️⚠️ **AND THERE IS A VERIFIED INSTANCE OF (3) BEING RECORDED AS (1).** At
`gather.py:1305-1311`, when every stem candidate in a cell is rejected by a
filter inside `detect_stems`, the record is written as:

```python
log.abstain(sub, quantity, reader=READERS.CV_LINES,
            frame=frame, reason=ABSTAIN.NO_INK, …)
```

**`NO_INK` — literally "no ink".** The rejection census proves the opposite: on
both publishers the dominant cause is *a component EXISTS and is the wrong
SHAPE* (**86%** Litolff, **74%** Breitkopf). The ink is there. It formed a
component. It failed a size test. **And the record says the page was empty.**

That is the ABSENT/DECLINED collapse `record.py` exists to prevent, wearing the
wrong reason word, at the base of the pipeline. **It is the single most direct
cause of Sean's confusion, and it is not fixed** (the file is owned by another
lane, and the fix is a default-affecting call).

---

## 4. WHY THE EXISTING CHECKS CANNOT ANSWER THE QUESTION

There are **ten** derived checks — `inventory`, `health`, `gather_coverage`,
`export_coverage`, `wiring`, `capture`, `reach`, `record_coverage`, `brakes`,
`no_producer` — and this is the finding:

⚠️⚠️ **EVERY ONE OF THEM IS AGGREGATE AND STATIC.** They ask *"is a declared
input read where it is filed?"*, *"does every quantity reach a consumer?"*,
*"what does no family claim?"*. **None asks: for THIS symbol on THIS page, what
did each stage do to it?** A grep for a per-subject trace returns nothing.

```bash
ls tools/omr/staged/*.py                      # the ten tools
grep -rln "def trace\|--subject" tools/omr/staged/    # nothing
```

**That is why the mapping keeps passing while the surprises keep coming.** The
connections are verified *in the abstract*. Nothing replays one symbol's
journey. So a connection can be correctly declared, correctly verified as
declared, and still deliver nothing on a real page — with every check green.
The repo's own casualty list is all one shape: `Q.STEM` gathered and read by
nothing **three separate times**; `pdf_path` dropped so a reader reported
`not_implemented` on **every staged run ever made**; `Q.METER`'s segments
reaching no file; `adjudicate_dynamic` deciding while `grep '<dynamics'` on the
exporter returned **0**.

⚠️ **And the fix was already prototyped by hand**: CLAUDE.md's five-stages
section traces ONE real note (`glyph/1/0/2/4/1`) through all five stages, in
prose, in a planning document. It is one of the clearest passages in the file.
**Nobody automated it.** That is now dispatched
(`claude/stage-trace-noteheads-2026-09`).

---

## 5. THE INSTRUMENT THAT EXISTS AND IS UNREAD

⚠️⚠️ **`Q.INK` — one row per connected piece of ink, named or not, with the
classification as an ATTRIBUTE THAT MAY BE ZERO — is default-ON and NOTHING IN
ANY STAGE READS IT.**

```bash
grep -rn 'Q\.INK' tools/omr/staged/adjudicators/ tools/omr/staged/consequences.py \
                  tools/omr/staged/export.py tools/omr/staged/inferences.py
# empty
```

It was built for exactly this question, on Sean's own principle — *"ink is ink.
There is nothing that should be classified as unseen — only unclassified"* —
and it is producer-only by deliberate discipline (a producer and its first
consumer landing together makes the reach measurement circular).

**So the machinery to distinguish "blank page" from "we declined it" already
exists, is switched on, and is connected to nothing.** It is also the ideal
INDEPENDENT witness for the `NO_INK` fault in §3, because it does not come off
the detector.

---

## 6. WHAT WOULD ACTUALLY FIX IT, in order of cost

1. **A per-subject TRACE** — replay one symbol's journey through all five
   stages. Answers the question directly, needs no pipeline change, read-only.
   **Dispatched.**
2. **Stop reporting a DECLINED candidate as an ABSENT page.** `NO_INK` must
   mean *no ink*; a filtered-out candidate needs its own reason word and,
   ideally, a row. ⚠️ Cheap to write, but it changes what every record says, so
   it is a call rather than a chore.
3. **Read `Q.INK` as the independent witness** for "is there ink where we claim
   emptiness". Its first consumer.
4. **Make the two foundational claims stageable** — *is this a notehead*, *is
   this a stem* — so they can abstain and be revisited. This is the big one, and
   it is the architecture question rather than a repair. ⚠️ The width test now
   in flight (`claude/notehead-width-2026-09`) is deliberately being built to
   **RECORD rather than silently drop**, so it does not add a seventh invisible
   filter.

---

## 7. ⚠️ WHAT THIS DOCUMENT DOES NOT CLAIM

* **It does not say the stages are the main source of bad readings.** A large
  part of the measured loss is upstream of every stage: three quarters of
  detected arcs bind fewer than two noteheads *because the notes were never
  detected*; one edition reads 22% of per-staff durations right against the
  other's 59%; and the print says a third of one edition's "note heads" are not
  noteheads. **No amount of stage plumbing fixes those**, and the trace
  instrument has been told that finding the pipeline healthier than expected is
  an equally valuable result.
* **It does not price anything.** No arm was run for this document; it is a
  reading of the tree.
* **The `NO_INK` instance is verified; whether other reason words collapse the
  same way is NOT surveyed.** That survey is part of the trace job.
* n on the contamination figure is **2 publishers, 8 pages, one adjudicator**,
  and on that plate ~60% of noteheads cannot be adjudicated by eye at all —
  see `benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md` §7.
