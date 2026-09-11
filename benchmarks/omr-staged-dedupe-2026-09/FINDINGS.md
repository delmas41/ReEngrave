# One piece of ink, several elements — the contest that was never resolved

2026-09-11, no flag. Sean stopped the first cleanup pass with seven complaints;
two of them were handed to this session as one hypothesis:

> *"there are a lot of doubled notes on a staff that dont make sense (2 of the
> same note next to each other connected to the same stem)"*
> *"the score has only ff all the way down and ours has extra fs"*

**The hypothesis was: the staged path never dedupes duplicate detections.**
`grep -rn dedupe tools/omr/staged/*.py` returns two hits and both are prose;
the legacy path calls `_dedupe_cross_staff_detections` at `transcribe.py:5557`
and the staged path calls nothing. So the brief asked whether one missing
dedupe pass explains both symptoms.

⚠️⚠️ **IT DOES NOT, AND THE CORRECTION IS THE MAIN DELIVERABLE.** The staged
path is not missing the decision — `adjudicate_glyph_owner` is a real
adjudicator, it runs on every contest, and on this document it gets **245 of
248** cross-staff notehead pairs to agree on one owner. What is missing is that
**nothing consumes the verdict as a RESOLUTION.** `export._place_notes` and
`adjudicate_dynamic` both honour ownership by **MOVING** the copy to the owner's
staff, and both copies of a contest name the same owner — so one piece of ink
arrives twice, on one staff, in one bar. Deduping DELETES the loser; the staged
path RELOCATED it.

And it is not one cause. It is **three**, and two of them are upstream
divergences from the legacy path that nobody had written down:

| | what | stage | shipped here |
|---|---|---|---|
| **1** | the owner verdict is honoured by MOVING, so a contest doubles | ADJUDICATE + EXPORT | **fixed and priced** |
| **2** | `gather.py:292` asks the detector for `agnostic_nms=False, iou=0.7` where `transcribe()` asks `True, 0.5` | GATHER | **measured, recorded, NOT changed** |
| **3** | `CONTEST_IOU = 0.5` restates the measured `_CROSS_STAFF_DUPLICATE_IOU = 0.3`, citing an assumption record that does not exist | GATHER | **recorded, NOT changed** |

---

## 1. ⚠️⚠️ REACH FIRST

Measured on the committed record of the cleanup artefact
(`benchmarks/omr-cleanup-count-2026-09/out/record-p1-p4.json`, Litolff
Beethoven 5 mvt 1, pdf pages 1-4, 12 parts, 1,183 measures).

```bash
python3 benchmarks/omr-staged-dedupe-2026-09/probe/reach.py \
    benchmarks/omr-cleanup-count-2026-09/out/record-p1-p4.json
```

**The definition is borrowed, not invented**: two glyph rows of the same
FAMILY whose page boxes overlap by more than
`transcribe._CROSS_STAFF_DUPLICATE_IOU` — imported, never restated. The one
thing deliberately changed is that the legacy function opens with
`if si == sj: continue`, so a duplicate *inside one staff* is outside its scope
by construction. The two populations are reported apart because they are
different questions with different answers.

**1,418 duplicate pairs over 4,508 glyph subjects that carry a family and a
page box.**

| family | same cell | same system, other staff | total | subjects involved |
|---|--:|--:|--:|--:|
| notehead_class | 284 | 363 | **647** | 995 of 2,347 (42.4%) |
| dynamic_letter | 143 | 277 | **420** | 442 of 485 (**91.1%**) |
| arc_box | 112 | 155 | 267 | 411 of 779 (52.8%) |
| articulation_mark | 0 | 29 | 29 | 58 of 98 |
| fermata_mark | 0 | 18 | 18 | 36 of 67 |
| flag | 7 | 10 | 17 | 28 of 49 |
| rest | 15 | 3 | 18 | 35 of 646 (5.4%) |
| aug_dot | 0 | 2 | 2 | 4 of 35 |
| **TOTAL** | **561** | **857** | **1,418** | |

⚠️ **THE PROBE'S OWN FIRST RUN WAS WRONG AND IS WORTH RECORDING.** It reported
**152 extra `other_system` duplicates** — page 1's ink overlapping page 3's,
because a page-pixel box is a fact about ONE page and two pages superimpose
exactly. Comparison is now scoped to one page. The same frame fault
`Q.ONSET_COLUMN` paid for when a canonical x made two staves agree by
construction, arriving in a measuring instrument rather than in the pipeline.

⚠️ `same_staff_other_cell` is **0 in every family** — cells do not overlap
within a staff, so every duplicate is either one cell's own or a cross-staff
contest.

---

## 2. SEAN'S TWO SYMPTOMS, ATTRIBUTED BY NAME

⚠️ Counting cannot see a relocation; only naming the notes can. Both arms below
read the EXPORTED file for the symptom and the RECORD for the cause, and join
them.

### 2a. The dynamics — `ffff` is one printed `ff`, detected twice

```bash
python3 benchmarks/omr-staged-dedupe-2026-09/probe/trace_ffff.py \
    benchmarks/omr-cleanup-count-2026-09/out/record-p1-p4.json
```

The exported file carries `f` 63, `ff` 47, `pp` 17, `p` 15, **`ffff` 11**,
**`fff` 10**, `sf` 9, `mf` 1, `ppp` 1. The first traced cell, in full:

```
cell/1/0/7/0  words=['ffff']
    glyph/1/0/7/0/1   dynamicF  conf=0.898  box=[899.2, 2458.7, 42.3, 46.7]
    glyph/1/0/8/0/3   dynamicF  conf=0.861  box=[899.6, 2469.0, 32.3, 36.5]
    glyph/1/0/7/0/3   dynamicF  conf=0.852  box=[920.5, 2459.4, 43.7, 45.1]
    glyph/1/0/8/0/1   dynamicF  conf=0.878  box=[921.5, 2469.0, 35.1, 35.3]
```

Two staves (7 and 8), two x positions (899 and 920). **It is one printed `ff`.**
Staff 8's cell padding reaches the same ink, both copies name staff 7 as owner,
and `adjudicate_dynamic` kept every letter the owner was given — so a
two-letter word became a four-letter one.

**21 of 21** cells carrying a long f/p word hold an overlapping letter pair.
There is no residue to explain.

### 2b. The doubled notes — the relocation, named

The exported file holds **421 chord events** (2+ notes on one stem) of which
**182 (43.2%) carry a repeated pitch**, for **206 excess `<note>` elements**:

```
P1 m18    chord = ['D6', 'G6', 'G6']   repeated: ['G6']
P1 m22    chord = ['F5', 'F5', 'F5']   repeated: ['F5']
P2 m19    chord = ['D5', 'D5']         repeated: ['D5']
```

Two mechanisms produce them, and the record separates them exactly:

**(i) THE RELOCATION.** `glyph_owner` files **1,386** verdicts; **688 name
another staff**, and `_place_notes` moved every one of them onto a staff that
already held its own copy. That the twin is always there is not an assumption —
`glyph_owner` declares `subjects_from=Q.GLYPH_BAND_DISTANCE` and
`gather_ownership_evidence` files a band row only where two same-class
detections on different staves overlap. **0 of the 688 relocated glyphs carry
`reason="no_contest"`**, which is what that claim predicts and is checked rather
than assumed. The deciding tier is `distance` 1,279 / `ladder` 107 — the
quantity this repo has caught being a coin flip four times, which is an argument
about WHICH staff wins and not about whether the copy should exist at all.

**(ii) THE SAME-CELL TRIPLE.** One notehead, three rows, three classes:

```
glyph/1/0/3/8/1  noteheadHalfInSpace   conf=0.371  box=[1737.6, 1605.1, 25.3, 19.8]
glyph/1/0/3/8/5  noteheadBlackInSpace  conf=0.288  box=[1737.9, 1604.6, 25.1, 20.3]   IoU=0.96
glyph/1/0/3/8/6  noteheadHalfOnLine    conf=0.252  box=[1737.3, 1605.5, 26.0, 19.7]   IoU=0.93
```

Each gets its own duration verdict — 1.0, 0.5 and 1.0 — so this is not only a
doubled note, it is a note that disagrees with itself about its length. ⚠️ The
record already *knows*: all three sit in one `correlated` group on every verdict
that reads them (§6.4).

⚠️ **THE CONTRAST WITH `arc_owner` IS WHAT MAKES THE REPAIR SAFE, AND IT IS NOT
A GENERAL RULE ABOUT OWNERSHIP.** Its domain is `subjects_from=Q.ARC_BOX` —
every arc — so it CAN move an arc onto a staff that detected nothing, and
CLAUDE.md records six of its twelve moves doing exactly that. Applying this
repair there would delete real arcs. `test_staged_dedupe.py` asserts both
domains off the REGISTRY, so widening `glyph_owner`'s goes red rather than
silently making the drop unsafe.

---

## 3. WHERE THE REPAIR WENT, AND WHERE IT DID NOT

The rule is one predicate, `adjudicate.is_relocated_copy`, stated once with its
argument and read by both consumers.

**Rejected — GATHER ("do not file two rows for one piece of ink").** Deleting a
copy at gather decides the contest one stage too early, with less evidence:
`ownership.py`'s own docstring says the point of the split is that ownership is
adjudicated AFTER identity, which needs both copies on the record. That is
`A-ORDER-2`, the architecture's central claim, and this repair must not undo it.

**Rejected — a new quantity (`Q.GLYPH_TWIN`).** It is the exact fact needed and
it is a GATHER change, so it cannot be priced without two full re-gathers.
Ranked in §6.5 rather than shipped blind.

**Rejected — the exporter forming the contest groups itself.** That re-derives a
gather-stage fact with a second threshold, which is how the tree grew two
different answers to one question in the first place (§6.2).

**Taken — the consumers REFUSE the copy instead of moving it.** No new quantity,
no new constant, no gather change, and no tie-break: *a contested glyph whose
owner is another staff is a copy that staff already holds* follows from the
DOMAIN, not from a judgement. The drop is counted (`owned_by_another_staff` for
notes, `letters_dropped_as_duplicate` for dynamics) so the accounting control
stays an **EQUALITY** and can still fail — CLAUDE.md records two separate
occasions where widening it to `<=` hid a real bug.

⚠️ **THE ONE WAY IT CAN LOSE INK IS A SWAP** — every member of one contest
naming somebody else, so every copy is refused. Measured
(`probe/contest_groups.py`) over 636 cross-staff contest groups:

| members kept under the rule | groups |
|---|--:|
| 1 | 457 |
| 2 | 39 |
| 3 | 4 |
| 4 | 1 |
| **0 — a true SWAP** | **1** |
| 0 — no owner verdict at all (§6.2) | 134 |

**One swap in 636, and it is a dynamic letter; zero noteheads.** It is not
structurally impossible, only rare, so it is counted rather than assumed away.
The 39+4+1 groups keeping more than one copy are the SAME-CELL cause (§6.1),
which this repair does not reach.

---

## 4. THE PRICE — one gather, the two halves measured apart

⚠️ **THE TWO HALVES ARE MEASURED BY TWO INSTRUMENTS, EACH WITH ITS OWN
CONTROL, BECAUSE EACH HAS A BLIND SPOT THE OTHER DOES NOT.**
`export_only_arm.py` exports one record twice and is structurally blind to the
dynamics (those verdicts are baked into the saved record, so its `<dynamics>`
figures are identical BY CONSTRUCTION and not by measurement).
`dynamics_arm.py` replays the saved `Q.GLYPH_OWNER` verdicts and re-runs ONLY
`Q.DYNAMIC` — sound because that decision reads nothing else — and is blind to
the notes. `ab_arm.py` does both at once and is the slow instrument.

⚠️ **NEITHER CAN SEE A GATHER CHANGE.** The two divergences in §6.1 and §6.2
are not priced by anything here.

### 4a. The notes — `export_only_arm.py`

One record, exported twice by ONE tree, only the predicate differing:

| | base | fix |
|---|--:|--:|
| pitched `<note>` | 1,793 | **1,618** |
| chord events (2+ on one stem) | 397 | 357 |
| ... with a REPEATED pitch | **122** | **108** |
| excess `<note>` in those chords | 133 | 117 |
| rests | 825 | 842 |
| `<slur>` / `<tied>` | 70 / 171 | 64 / 158 |
| `<articulations>` | 63 | 47 |
| `<dynamics>` / `<words>` / `<fermata>` | 174 / 6 / 41 | identical |
| measures / parts | 1,183 / 12 | identical |

**176 notes refused** as `owned_by_another_staff`. The pitched count falls by
175 and the rests rise by 17: a bar emptied by a refusal correctly takes a
whole-measure rest. Slurs, ties and articulations fall because each binds a
notehead that is no longer written twice.

**The accounting control is an EQUALITY on both arms** (2,993 in log = written
+ not-written), and `status_census.unaccounted` is empty on both.

⚠️ **REPEATED-PITCH CHORDS FALL BY ONLY 14, NOT TO ZERO — AND THAT IS THE
RESULT AGREEING WITH ITSELF.** The remainder is the SAME-CELL population
(§6.1), which this repair structurally cannot reach: a same-staff pair is never
a contest, so ownership never speaks about it. A repair that took this to zero
would have been doing something it could not justify.

⚠️⚠️ **THE BASE ARM IS NOT THE ARTEFACT SEAN LOOKED AT, AND THE DIFFERENCE
CANNOT BE ATTRIBUTED.** That file reports **421 chord events / 182 repeated /
206 excess** where today's `origin/main` reports **397 / 122 / 133** on the same
record — identical pitched-note count (1,793) and identical `notes_not_written`
(339 + 215), so the difference is in chord GROUPING. It cannot be attributed
because **`export_arm.py` writes no provenance stamp**: the record names the
tree that GATHERED it and nothing names the tree that EXPORTED it, hours later
in a separate process. The base→fix delta is one tree and stands; the artefact's
absolute numbers are not this arm's baseline.

### 4b. The dynamics — `dynamics_arm.py`

**CONTROL: 1,148 of 1,148 `Q.DYNAMIC` verdicts identical** to the ones the
pipeline itself wrote, before either arm is read. **155 letters refused** as
this staff's own duplicate.

| word | base | fix | |
|---|--:|--:|---|
| `f` | 63 | 77 | |
| `ff` | 47 | **39** | ⚠️ see below |
| `p` | 15 | 31 | |
| `sf` | 9 | **34** | runs that could not be spelled now can |
| `pp` | 17 | **2** | |
| `fff` | 10 | 8 | |
| `ffff` | **11** | **2** | |
| `ppp` | 1 | 0 | |
| `mf` / `fp` | 1 / 0 | 1 / 1 | |

The mechanism is visible in the shape: the assembly rule joins letters by
x-adjacency, and two boxes of ONE letter sit at the same x — so a doubled `p`
assembled as `pp` and a doubled `s`+`f` assembled as an unspellable run that
reached no file at all. Refusing the duplicate turns `pp` into `p`, `ffff` into
`ff`, and 25 unspellable runs into `sf`.

⚠️⚠️ **AND `ff` 47 → 39 IS AN UNADJUDICATED COST, NOT A WIN. ONLY THE PRINT CAN
SAY.** Sean says the page prints `ff` and nothing else. Eight words left that
spelling, and both readings are available from the record alone: either they
were one printed `f` detected twice (the repair is right), or they were a real
`ff` whose second letter this staff detected only once (the repair is wrong and
cost a mark). **This session did not look at the page**, so it is 8 things a
human might have to put back — the same shape as the voices work's 31 refused
ties, and it must not be quoted as a recovery.

⚠️ `fff` 10 → 8 rather than to zero, for the §6.1 reason: a same-cell duplicate
survives both arms.


---

## 5. WHAT THE TESTS NOW HOLD, AND THE FIXTURE THAT WAS WRONG

⚠️⚠️ **AN EXISTING TEST ASSERTED THE BEHAVIOUR THIS REPAIR REMOVES, AND ITS
FIXTURE WAS A PAGE GATHER CANNOT PRODUCE.**
`test_staged_dynamics.TestOwnershipMovesTheLetter` filed **one** letter, filed a
contest over it, and asserted the owning staff *gained* a letter it never
detected. `gather_ownership_evidence` files a band-distance row only where TWO
same-class detections on different staves overlap, so that page does not exist —
and the behaviour the test certified is exactly how a printed `ff` reached the
file as `ffff`. *A fixture that does not match GATHER tests the test*, the shape
CLAUDE.md already records for `Q.METER_GLYPH`.

The class is rewritten around a real contest (two detections, one printed
letter) and the premise is now pinned by **running the real gatherer**, not by
restating what it is believed to do: `TestOneLetterIsNeverContested` asserts one
copy yields no contest **and** — the positive control in the same class — that
two copies do.

⚠️ **A counter naming something that no longer happens is the *control that
computes the wrong thing*.** `letters_moved_in` counted letters carried onto
this staff; those are now refused, so it is `letters_dropped_as_duplicate`.
`letters_moved_out` is unchanged and reported apart, because only one of the two
drops is redundant.

⚠️ **THE MUTATION BATTERY: 9 ARMS, ALL RED, NO BAD ANCHORS**
(`mutants.py`). *One red arm is not a battery*, and a battery of REFUSAL tests
can pass by refusing everything — so "the rule ALWAYS fires" is a **positive
control in the same class** and must fail the UNCONTESTED tests specifically,
which it does. A BAD ANCHOR exits non-zero rather than reading as a pass,
because this repo has silently mutated a different function that way twice.

⚠️ **THE FIRST RUN HAD ONE SURVIVOR AND IT WAS A GENUINE GAP**: deleting
`gather_ownership_evidence`'s `gi.staff == gj.staff` guard changed nothing,
because every fixture held at most one copy per staff — so **nothing asserted
that a contest is CROSS-staff**. `test_TWO_copies_IN_ONE_STAFF_are_NOT_a_contest`
closes it, and it matters beyond the guard: it is the property that makes §6.1
a separate job rather than part of this one.

⚠️⚠️ **AND THE FIRST A/B RUN WAS DISCARDED.** The battery checks out the files
it mutates and was running beside it — the collision CLAUDE.md already records
costing a session its first three-arm run, reproduced here by the author of the
battery's own warning. The arms were re-run alone on a clean, committed tree,
and the battery's docstring now says so at the top.


---

## 6. WHAT IS NOT ESTABLISHED, AND THE RANKED NEXT WORK

### 6.0 Limits of this measurement

* **n = 1 document, 1 publisher, 4 pages of ~16.** Litolff `984073` is the
  *low-res bitonal* scan this repo already records firing 49 flag boxes where
  Breitkopf fires 371 — so a second publisher could change the ranking and not
  only the number. Brahms 1 / Breitkopf is the document to repeat this on.
* **The record was gathered on a DIRTY tree** (`provenance.commit 9d4ccc85`,
  `dirty: true`). Both arms inherit that equally, so the DELTA stands; the
  absolute figures carry the caveat.
* **No accuracy claim.** Nothing here has been checked against the print. That
  one printed `ff` is two letters and not four is Sean's reading of the page,
  not a measurement; the 21-of-21 overlap figure is what the record says, which
  is a different thing. Removing a duplicate makes the file MORE correct only if
  the surviving copy is the right one, and this session did not test that — the
  same-cell triple above shows the copies can disagree about class and duration.
* **Both arms are adjudicate-and-export only** and are structurally blind to the
  two GATHER divergences below — each rebuilds from a saved record, so a gather
  change never enters. Do not read §4 as pricing them.
* ⚠️⚠️ **THE DYNAMICS DELTA IS NOT SHOWN TO BE AN IMPROVEMENT.** `ffff` 11 → 2
  is unambiguous (no dynamic is spelled with four `f`s), but `ff` 47 → 39 and
  `pp` 17 → 2 are REDISTRIBUTIONS whose direction only the print can settle.
  The repair is justified by what the record says — two boxes, one piece of ink
  — and not by any measurement of the file being more correct.

### 6.1 ⚠️ RANKED FIRST: the staged gather asks the detector a different question

`gather.py:292` calls `detector.detect(c, conf_threshold=..., imgsz=...)` and
passes neither `iou_threshold` nor `agnostic_nms`, taking `YoloDetector.detect`'s
own defaults — **0.7 and `False`** — where `transcribe()` defaults to **0.5 and
`True`**, which is the configuration every measured figure in this repo was
taken under. Class-wise NMS never compares `noteheadHalfInSpace` with
`noteheadBlackInSpace`, and the detector's own docstring names that as exactly
what `agnostic_nms` is for.

**Measured rather than read off the code** (`probe/nms_probe.py`, Litolff p.1,
all 192 cells, driven through the pipeline's own `prepare_pages`):

| | detections | overlapping same-category pairs |
|---|--:|--:|
| staged (0.7 / `False`) | 755 | **55** — structural 21, notehead 15, dynamic 9, accidental 6, time-sig 3, rest 1 |
| legacy (0.5 / `True`) | 709 | **16** — dynamic 7, notehead 4, structural 4, time-sig 1 |

⚠️ **The legacy arm still leaves 16, so this is not a complete fix for the
same-cell population** — a pair below IoU 0.5 survives both. And the dynamics
barely move (9 → 7), which is consistent with §6.3: most same-cell dynamic pairs
are the two adjacent `f`s of a real `ff`.

**Not changed here**, because it changes the DETECTION SET and only two full
re-gathers can price it. Recipe: `bash
benchmarks/omr-cleanup-count-2026-09/run_gather.sh 1-4 nms-base` on this tree
and again with the two arguments passed, then `export_arm.py` on each and
`benchmarks/omr-staged-notations-2026-09/regather_control.py` to prove the pair
provenanced, clean and distinct.

### 6.2 `CONTEST_IOU = 0.5` restates a measured constant at a different value

The legacy question is answered by `_CROSS_STAFF_DUPLICATE_IOU = 0.3`, swept
over three orchestral works at 0.25/0.3/0.4/0.5 and documented as the lowest
value costing no correctly-matched note on any of them. The staged gather
restates it as **0.5** and cites `(A-OWN-3)` — `grep -rn A-OWN-3 tools/
benchmarks/ docs/` returns that one line and nothing else. **The assumption
record was never written.** Nor does the commit that introduced it (`044622ca`)
argue for the value; its own message quotes the legacy population (4,521
contests) as the thing being reproduced.

The cost is measured: **134 of 636 overlapping cross-staff groups carry no
`Q.GLYPH_OWNER` verdict at all**, so both copies are written with the ownership
question never asked. Left at 0.5 and documented rather than changed, for the
same pricing reason as §6.1.

### 6.3 A flat IoU rule inside a cell would DELETE REAL INK — do not try it

The first same-cell dynamic pair this session found is two `dynamicF` at IoU
**0.317**, 21 px apart, both real: **the two `f`s of a printed `ff`**. Their
boxes are wider than the gap between them. Measured over the 255 same-cell
dynamic pairs, the centre offset in x spreads 72 / 87 / 93 / 3 across
`<0.25w` / `0.25-0.5w` / `0.5-0.75w` / `>=0.75w` — **the two populations do not
separate**, and the widest empty interval is 0.097 wide. Noteheads do separate
(405 of 458 under 0.25w), but that is a fact about noteheads, not a threshold
anyone should carry across families. It is why the repair resolves a CONTEST,
which is a question the record already answers, rather than thresholding
geometry.

### 6.4 The record already knows, and nothing reads it

Every duplicate triple sits in one `Verdict.correlated` group on every verdict
that reads it. `Verdict.correlated` is consumed by nothing — CLAUDE.md lists it
among the inputs to the proposed RECONCILE stage that are *"ALREADY BUILT AND
CONSUMED BY NOTHING"*. This session did not consume it either: correlation is
computed per verdict and does not carry the twin's identity across families, so
it is evidence that the fault was visible on the record, not a route to the fix.

### 6.5 A FOURTH SITE STILL RELOCATES, and its own comment now says something false

`arc_owner` and `wedge_anchor` build their per-staff head sets by mapping every
notehead to its OWNER, so a contested head enters the owner's set **twice**.
`arc_owner`'s comment justifies that grouping as giving *"the head set a READER
would see"* and cites the legacy path explicitly — *"on the legacy path the
same information exists only because `_dedupe_cross_staff_detections` has
already physically moved the detection"*. There the set holds ONE copy, because
dedupe deleted the other. **Here it holds two, so the claim is currently
false.**

The effect is on `clearance`'s *n covered*, which counts heads an arc covers on
each candidate staff — and the inflation is asymmetric, because every duplicate
lands on the OWNER's staff. It is **unmeasured**: no arm here touches those
decisions, and folding a one-line change into an A/B that was already running
would have made the delta unattributable. The same predicate applies and the
same swap hazard would apply with it, so it is one piece of work with §6.6
rather than a drive-by.

### 6.6 What a swap would take to make impossible

`gather_ownership_evidence` computes the twin's subject and records only the
twin's STAFF (`contests.setdefault(i, set()).add(gj.at(Kind.STAFF).to_key())`)
— *the value is computed and thrown away*, this project's signature finding, one
more time. Recording it would make the contest a GROUP on the record, and a
group can be resolved with no possibility of losing ink at all. It is a GATHER
change and therefore costs two re-gathers; it is worth doing alongside §6.1
rather than on its own.
