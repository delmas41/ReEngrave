# The staged gatherer dropped every C clef the detector reads

2026-09-21, no flag. Item 3 of the symbol-dossier sweep's ranked repair list
(`docs/symbol-dossiers/INDEX.md` §3), described there as "a wire, not a
rebuild". It is a wire — and the brief's account of **what the wire is worth**
is refuted below, which is the more useful half.

Branch `claude/staged-c-clef-2026-09-21`, off `28749347`.

---

## ASK FIRST — the convention block (§4 of `docs/ask-first-conventions.md`)

This is an unattended overnight run, so the assumption is written down rather
than confirmed.

> **CONVENTION ASSUMED:** *a C clef names the line its centre sits on; alto,
> tenor, soprano, mezzo and baritone are THE SAME GLYPH printed on different
> lines.* An engraver chooses the line, not the shape, so the shape cannot
> carry the answer and only a measurement against the staff can.
>
> **WHAT WOULD FALSIFY IT:** a plate on which the alto and tenor C clefs are
> drawn as *different glyphs*. Cheap check: crop the two C clefs on Brahms 1 /
> Breitkopf p3 system 1 — staff 11 (read `alto`) and staff 12 (read `tenor`) —
> and compare the ink. If they differ in shape rather than only in position,
> the class name is carrying real information and the refusal below is too
> strong.
>
> **NOT CONFIRMED WITH SEAN.**

⚠️ The convention is not merely assumed here: it is what `clef_geometry.py`
already exists to implement, and this lane's own measurement is consistent
with it (§4). But it has not been put to Sean, and the whole design rests on
it, so it is stated where a later reader can refute it.

---

## 1. THE FAULT, AND IT IS SHARPER THAN THE BRIEF SAID

`gather.py:258` admitted clefs by literal set membership:

```python
_CLEF_CLASSES = {"clefG", "clefF", "clefC", "clefUnpitchedPercussion"}
```

The 208-name class space is two vocabularies concatenated — fine at ids 0-135,
coarse at 136-207 (`class_aliases.FINE_BLOCK_SIZE`). Its clef entries:

| id | name | block | in the admitted set? | fires, cell 0, both records |
|---:|---|---|---|---:|
| 5 | `clefG` | fine | yes | 180 |
| 6 | **`clefCAlto`** | fine | **no** | **9** |
| 7 | **`clefCTenor`** | fine | **no** | **7** |
| 8 | `clefF` | fine | yes | 54 |
| 9 | `clefUnpitchedPercussion` | fine | yes | 0 |
| 10 | `clef8` | fine | no | 0 |
| 11 | `clef15` | fine | no | 0 |
| 141 | `clefG` | coarse | yes (same name) | — |
| 142 | **`clefC`** | coarse | **yes** | **0** |
| 143 | `clefF` | coarse | yes (same name) | — |

⚠️⚠️ **THE SET ADMITTED THE ONE SPELLING THAT NEVER OCCURS AND DROPPED THE TWO
THAT DO.** `clefC` is the coarse name, and CLAUDE.md already records the whole
coarse block firing zero times across three engraved fixtures and 29 scanned
pages of nine publishers; it fires zero times here too. The detector emits the
**fine** `clefCAlto` / `clefCTenor`, which were in neither that set nor
anything downstream of it.

**Every factual claim the brief made about the code checked out**: `gather.py:258`
is verbatim, the checkpoint's class names match the committed vocabulary
index-for-index, and `class_aliases.canonicalize_names` leaves both fine names
unchanged (they are fine spellings, so no alias applies), so `clefCAlto` is
literally the string arriving at `d.smufl_name`. The 146-name
`DEEPSCORES_V2_CLASSES` list does spell them `cClefAlto`/`cClefTenor`, and that
list is **not** what reaches the gatherer — `YoloDetector` reads the model's own
`names`.

⚠️ **One claim about the WORKTREE was false and is worth recording**: the brief
said the worktree starts at `28749347`. It started at `origin/main` = `8a2019af`
— ~150 commits behind, and precisely the four-days-stale commit the same brief
warns against. Checking `git log -1` before doing anything is what caught it.

---

## 2. REACH — measured, A/B, admission rule IMPORTED not restated

`clef_reach.py` streams both shared records (`recordstream.py`, because the
Breitkopf record is 444 MB), counts clef-**category** detections in cell 0
(`gather_clef`'s own domain), and runs both admission rules over the same rows.
Output: `out-reach.txt`.

| | Litolff Beethoven 5 p1-p4 | Breitkopf Brahms 1 p0-p3 |
|---|--:|--:|
| cell-0 clef detections | 93 | 157 |
| admitted, INCUMBENT | 91 | 143 |
| **dropped, INCUMBENT** | **2** (`clefCAlto` ×2) | **14** (`clefCAlto` ×7, `clefCTenor` ×7) |
| admitted, REPAIRED | 93 | 157 |
| **dropped, REPAIRED** | **0** | **0** |
| staves with a cell-0 clef detection | 66 | 95 |
| **staves with NO admitted clef but ≥1 dropped** | **1** | **8** |

**16 C-clef detections dropped on 9 staves → 0.**

⚠️ **Positive control**: the probe prints how many clef rows it admitted at all
(234) and **exits 2** if that is zero — a probe that cannot read the record and
a record holding nothing look identical.

⚠️ Clef detections in **later** cells are counted and reported apart (18 and 12;
one of them a `clefCTenor`). A mid-staff clef change is a different question and
this lane does not touch it.

---

## 3. ⚠️⚠️ THE BRIEF'S PREMISE IS REFUTED — nobody loses a clef

The brief asks for *how many staves gain a clef*, because "a staff whose clef
abstains gets **no pitches**, so a dropped C clef is a whole staff of missing
music."

`clef_starved_control.py` asks the **record** rather than the code. Output:
`out-starved-control.txt`.

**All 9 staves confirm the gather-side drop** — `clef_glyph` observations `[]`
on every one, so the detector's C clef really is discarded. **And all 9 carry a
DECIDED clef verdict anyway**, with a plausible value:

```
staff/3/1/6    (Litolff)   dropped clefCAlto                  verdict decided/scored/alto
staff/0/0/11   (Breitkopf) dropped clefCAlto x2               verdict decided/scored/alto
staff/0/0/12               dropped clefCTenor                 verdict decided/scored/tenor
staff/1/0/11               dropped clefCAlto                  verdict decided/scored/alto
staff/1/1/10               dropped clefCAlto x2 + clefCTenor  verdict decided/scored/alto
staff/2/1/12               dropped clefCTenor                 verdict decided/scored/tenor
staff/3/0/11               dropped clefCAlto + clefCTenor     verdict decided/scored/alto
staff/3/1/11               dropped clefCTenor                 verdict decided/scored/alto  <-- DISAGREES
staff/3/1/12               dropped clefCTenor                 verdict decided/scored/tenor
```

`clef_evidence_dump.py` names the reader: **every one of the nine is carried by
the CV locator alone** (`clef_located`, `reader=cv_locator`, 0.72–0.96), with no
`clef_glyph` row at all.

> **So the number of staves that gain a clef is ZERO, not nine.** The CV locator
> is already covering exactly this population. What the repair buys is a second,
> independent witness on nine staves that today rest on one reader — not a
> rescue.

⚠️ **HEADROOM IS ZERO TOO, AND IT WAS CHECKED RATHER THAN ASSUMED**
(`clef_headroom.py`, `out-headroom.txt`). Litolff: 69 decided, 3 `no_candidates`,
3 `margin_below_floor`. Breitkopf: **97 decided, 0 non-decided.** Of those six
non-decided staves, **0 hold a dropped C clef and 0 hold a locator reading** —
so on these two documents **the repair changes no clef verdict at all.** That is
the honest headline and it must not be dressed up.

---

## 4. WHY THE OBVIOUS REPAIR IS REFUSED — and the refusal is the measured half

The natural wire is two lines: admit the names in GATHER, and map them in
`_GLYPH_TO_CLEF` so `clefCAlto → alto`. **The second half is refused.**

`_clef_of`'s docstring already argued that a class name cannot name *which* C
clef, and it was written about the **coarse** `clefC`. The fine names look like
an exception. The measurement says they are not:

- **8 of 9 staves agree** between the dropped class name and the standing
  verdict. **1 disagrees**: Brahms 1 `p3/s1/st11`, detector `clefCTenor`,
  locator `alto` on two crops at 0.91 — staff 11 of a 14-staff system whose
  staff 12 reads `tenor`. That is **viola in alto over cello in tenor**, the
  standard layout, so the locator is very probably right and the class wrong.
- **DeepScoresV2 annotates only alto and tenor**, so soprano, mezzo and
  baritone C clefs can only ever arrive under one of those two names. The class
  is not merely unreliable about the line — **it cannot express the answer.**

So the fine names are admitted exactly as `clefC` already was: as **FAMILY
support** for a C clef the locator named (`_c_family_support`, `W_C_FAMILY` 1.5),
never as a name of their own. A wiring pass may connect a decision; it may not
let one guess.

### 4.1 ⚠️⚠️ AND MY FIRST STATEMENT OF THE COST WAS WRONG — the battery caught it

I wrote, in two docstrings and a commit message, that naming the clef from
`clefCTenor` would "flip a staff that is right today to wrong". **The mutation
battery's first run reported that arm as a SURVIVOR**
(`out-battery-run1-one-survivor.txt`), which is what sent me to measure the
claim instead of asserting it:

| locator crops | SHIPPED | with the class naming the clef |
|---:|---|---|
| 2 (the real `p3/s1/st11`) | alto **5.5**, uncontested | alto **5.5** vs tenor **4.5** — margin **exactly 1.0 = `MARGIN_FLOOR`** |
| 1 (the shape of `p1/s1/st10`) | alto **3.5** | **tenor 4.5 — the staff FLIPS** |

Two crops are two signals, so alto carries `2.0 + 2.0 + 1.5` and survives.

⚠️ The general form, which is not new to this repo but arrived here by a new
road: *a claim about a weighted contest cannot be read off the weights.* 3.0
beats 2.0 was true and irrelevant; what decides it is how many INDEPENDENT rows
each candidate has, and that is a property of the page, not of the table.

### 4.2 ⚠️⚠️ AND THE CORRECTION OVERCLAIMED TOO — ZERO staves flip

The corrected paragraph above still asserted "an outright flip wherever the
locator read one crop", naming `staff/1/1/10`. That is the SAME error one layer
down: a claim about a contest, reasoned rather than run. So it was run.

`clef_flip_arm.py` rebuilds each affected staff's evidence FROM THE RECORD —
every `clef_glyph` row `gather_clef` would now emit, plus its grid row placed
ON the staff (the case most favourable to the mutation), plus every
`clef_located` row the record holds — and calls the real adjudicator twice, the
second time with `clefCAlto`/`clefCTenor` injected into `_GLYPH_TO_CLEF`.
Output: `out-flip-arm.txt`.

| staff | glyphs dropped today | locator | shipped | with the class naming the clef |
|---|---|---|---|---|
| `3/1/6` (Litolff) | `clefCAlto` | alto ×2 | alto, margin 5.5 | alto, 7.0 |
| `0/0/11` | `clefCAlto` ×2 | alto ×2 | alto, 5.5 | alto, 8.5 |
| `0/0/12` | `clefCTenor` | tenor ×2 | tenor, 5.5 | tenor, 8.5 |
| `1/0/11` | `clefCAlto` | alto ×2 | alto, 5.5 | alto, 8.5 |
| `1/1/10` | `clefCAlto` ×2, `clefCTenor` | alto ×1 | alto, 3.5 | alto, **3.5 — unchanged** |
| `2/1/12` | `clefCTenor` | tenor ×2 | tenor, 5.5 | tenor, 8.5 |
| `3/0/11` | `clefCAlto`, `clefCTenor` | alto ×2 | alto, 5.5 | alto, **4.0 — eroded** |
| `3/1/11` | `clefCTenor` | alto ×2 | alto, 5.5 | alto, **1.0 = `MARGIN_FLOOR`** |
| `3/1/12` | `clefCTenor` | tenor ×2 | tenor, 5.5 | tenor, 8.5 |

**9 staves: 0 FLIP, 2 margins eroded.**

`staff/1/1/10` does have one locator crop — and it does NOT flip, because it
also carries **two `clefCAlto` detections that AGREE** with the locator. The
one-crop flip (tenor 4.5 against alto 3.5) is a **synthetic demonstration of
the mechanism**, and **no staff on either document has that shape**.

> So the honest refusal rests on TWO things, neither of them an observed flip:
> **(a)** the measured margin erosion — `3/1/11` goes from uncontested to
> *exactly* the floor, one crop or one confidence tier from a `NARROWED`
> verdict, i.e. from losing its clef; and **(b)** DeepScoresV2 annotating only
> alto and tenor, so the class *cannot express* soprano, mezzo or baritone at
> all.
>
> On this corpus the flip is prevented by **what the layout happens to be**
> (locators reading two crops, detectors mostly agreeing), not by anything the
> naming rule would guarantee. That is a reason to refuse it, not a reason to
> relax it.

⚠️ **POSITIVE CONTROL**: the arm exits 2 if the injected mutation moves neither
a value nor a margin anywhere — otherwise "0 FLIP" could mean the mutation was
never applied.

⚠️ **The reconstruction is the one step between this arm and a real
re-gather**, and it is stated rather than hidden: the committed records predate
this lane, so they hold no `clef_glyph` row for the dropped C clefs and the
rows are rebuilt from the `glyph_box` rows the record does hold.

**Two overclaims, two instruments.** The first was caught by the mutation
battery, the second by running the arm instead of reasoning about weights.
Neither was caught by review.

---

## 5. ⚠️⚠️ THE CATEGORY TEST IS LOAD-BEARING — 27 classes, not belt-and-braces

The repair derives admission from `clef_geometry.clef_family` rather than
restating a set. `clef_family` reads the **leading letter of the class name's
core**, and `class_aliases` already records the consequence in terms:
`graceNoteAcciaccatura` *"in isolation also reads as a treble clef — harmless
and unreachable: every caller filters `category != 'clef'` first."*

**`gather_clef` did not filter by category.** It matched a literal set, so the
trap was unreachable for a different reason — and switching to the family rule
*without* the category test would have armed it. Measured over the committed
208-name vocabulary, **27 classes** would be admitted as clefs:

- 12 × `flag*` (`flag8thUp`, `flag16thDown`, … — a `flag8thUp` entering the
  clef contest as a **BASS** clef)
- 6 × `fingering0`–`fingering5`
- 5 × `graceNote*`
- `fermataAbove`, `fermataBelow`, `coda`, `caesura`

The guard `class_aliases` says every caller keeps is now written down at the
site where the family test is actually made, with that number beside it. Four
tests pin it, including a **positive control** showing `clef_family` really does
admit all three named traps on its own — without it, three `assertFalse`s would
pass against a predicate that refuses everything.

---

## 6. `clef8` / `clef15` — a NAMED gap, not an omission

They are **octave markers that MODIFY a clef**, so admitting them would let one
compete as a clef in its own right. They are excluded because `_clef_core` names
them explicitly and returns `None`, so the exclusion is read from the shared
rule rather than restated.

**Measured reach: 0 firings on both shared records, in every cell.** So the
exclusion costs nothing today and buys nothing today; what it buys is that the
day they fire they cannot be mistaken for a reading. Recorded here with its
count so a later reader does not have to re-measure it.

**What closing it would take** (should anyone want `8va`/`15ma` transposition):
a quantity of its own — an octave mark is a *modifier on* `Q.CLEF`, not a
candidate in its contest — plus a rule pairing it with the clef it sits above or
below, plus a consumer in `restate_pitch`. None of that is wiring, and none of
it is this lane.

---

## 7. WHAT SHIPPED

**`tools/omr/staged/gather.py`** — `_CLEF_CLASSES` → `_CLEF_CLASSES_INCUMBENT`
(kept, because the shape of it is the finding) plus `_is_clef_class(name,
category)`: category must be `clef`, then `clef_family` is not None, else
`"percussion" in name`. The call site passes `d.category`.

**`tools/omr/staged/adjudicators/clef.py`** — `_c_family_support` matches
`clef_family(...) == "C"` instead of the literal `"clefC"`. `_clef_of` and
`_GLYPH_TO_CLEF` are **unchanged**; their docstrings now state why the fine
spellings are not an exception, with §4.1's numbers.

**`tools/omr/tests/test_staged_c_clef.py`** — 24 tests, including a synthetic
staff-head cell driving `gather_clef` directly (no weights).

**No flag**, and the reasoning is stated rather than assumed. The change cannot
move a verdict away from the locator: it only adds `W_C_FAMILY` to a C clef the
locator already named, and `_clef_of` still refuses to introduce a C-clef
candidate of its own. Measured, it moves **zero** verdicts on both documents
(§3). A flag would gate a behaviour whose measured blast radius is nil, and
default-direction discipline would then have to be maintained for it forever.

⚠️ It is **not structurally incapable** of changing an outcome — a staff where
the locator's C clef currently loses by less than 1.5 would flip toward it. No
such staff exists on either document. Stated rather than glossed, because that
is the sentence a later reader needs if one ever does.

---

## 8. CONTROLS

- **A/B reach**: the same probe, the same rows, both admission rules; the
  repaired rule **imported**, never restated (`clef_reach.admit_repaired`).
- **Positive control on the probe**: exits 2 at zero admitted rows.
- **The record, not the code**: `clef_starved_control.py` joins the prediction
  to the record's own observations and verdicts, prints served staves as its
  positive control, and **exits 1** if a staff it calls starved turns out to
  carry a `clef_glyph` row.
- **The flip arm** (`clef_flip_arm.py`): rebuilds each affected staff's real
  evidence and runs the adjudicator twice, shipped vs the naming mutation. It
  **exits 2** if the mutation moves nothing anywhere, so "0 FLIP" cannot be a
  dead instrument.
- **Mutation battery**: `mutate.py`, **12 arms, 12 RED, 0 survivors, 0 errors**,
  restore verified by hash (`out-battery.txt`). Run 1 is committed
  (`out-battery-run1-one-survivor.txt`) **as the proof the judge can fail**.
  - The judge runs each arm's **named test node** and reads its **exit code** —
    never pytest's summary line, which ends `" in 0.57s"` and differs between
    two runs of an unmutated tree. Two batteries in this repo were measuring
    nothing for exactly that reason.
  - A mutation that does not `ast.parse` is an **ERROR**, not a fake red.
  - An anchor not appearing **exactly once** is **BAD ANCHOR**, not a pass.
  - `refuse_everything` is an arm, because a battery of refusal tests can pass
    by refusing everything; the positive control runs the whole file green on
    the unmutated tree before any arm.
  - Byte snapshot before arm 1, **in-flight sentinel** so an interrupted run
    refuses to start and names each file with the hash it should have.
- **Derived checks**, all exit 0: `wiring --check`, `inventory --check`,
  `health --check`, `gather_coverage`, `capture --check`, `export_coverage
  --all`, `accuracy_record --check`.

---

## 9. WHAT IS NOT ESTABLISHED

- ⚠️ **ACCURACY. Nothing here was checked against the print.** That
  `p3/s1/st11` is a viola in alto is read off the *layout* (staff 11 of 14,
  with tenor below it), not off the plate. The convention block in the header
  names the crop that would settle it.
- ⚠️ **The repair changes ZERO clef verdicts on both documents.** Its value is
  correctness and corroboration, not a measured improvement. No claim is made
  that any clef is now more likely to be right.
- ⚠️ **n = 2 documents, 2 publishers, 8 pages**, both scans, and Litolff
  `984073` is the *low-res bitonal* end of the corpus. **The ENGRAVED family is
  untouched and was not measured** — no engraved fixture was read, so whether
  C clefs are dropped there is unknown. They would be, by the same code path;
  it is the *reach* that is unmeasured.
- ⚠️ **No re-gather was run.** This is a GATHER change, so `readjudicate` and
  `reexport_arm` are **structurally blind** to it. The reach figures are
  derived by re-running the admission rule over the detections already in the
  committed records — exact for *which rows would be emitted*, and silent about
  detector jitter on a fresh run.
- ⚠️ **No export arm, no MusicXML, no OMR-NED** — deliberately; the metric is
  symmetric and no file changes on these documents anyway.
- ⚠️ The **1-in-9 disagreement rate** is nine staves on two documents. It is
  enough to refuse the naming repair; it is **not** a rate for how often the
  detector misnames a C clef.
- ⚠️ `clefUnpitchedPercussion` fires **0 times** on both records, so the
  percussion clause of the predicate is pinned only by a unit test over the
  vocabulary and is never exercised on a page.
- ⚠️ **Mid-staff clef changes are out of scope** — see §11.
- ⚠️ **The flip arm RECONSTRUCTS the post-repair evidence** from the
  `glyph_box` rows in records gathered before this lane; it is exact for which
  rows `gather_clef` would emit and says nothing about detector jitter on a
  fresh run. It also places every rebuilt glyph ON the staff (4.0 steps), which
  is the shape most favourable to the mutation — so "0 FLIP" is a conservative
  answer, not a flattering one.
- ⚠️ The `_is_clef_class` predicate was checked against the **committed
  208-name vocabulary**, not against the checkpoint's own `names` (that needs
  `torch.load` of an 88 MB file). `class_aliases` asserts the two were verified
  index-for-index on 2026-09-04, and this lane relied on that assertion rather
  than re-taking it.

---

## 10. FOR SEAN — one decision, and it is one exchange

The crop named in the convention block would settle §4 permanently: **are the
alto and tenor C clefs on Brahms 1 / Breitkopf p3 system 1 the same glyph on
different lines, or different glyphs?**

- If they are the **same glyph** — as `clef_geometry` assumes throughout — the
  refusal in §4 stands permanently and this lane is closed.
- If they are **different glyphs**, the detector's fine class names carry real
  information, and how much weight they should get against the locator becomes
  an open question worth measuring.

Everything else here is settled by the record.

---

## 11. ONE THING OUTSIDE THIS LANE'S FENCE

`gather_clef` reads clefs from the staff **head cell only** (`if sub.cell != 0:
continue`). Across the two records, **30 clef detections sit in later cells**
(18 Litolff, 12 Breitkopf — including one `clefCTenor`), and they reach no
quantity at all: a printed mid-staff clef change cannot become a row, so it
cannot reach a file.

That is a producer-shaped gap rather than a wiring one — it needs a decision
about whether `Q.CLEF` is a fact about a STAFF or about a RANGE OF BARS, which
is the same shape as `Q.METER`'s `segments`. It belongs to whoever owns
`Q.CLEF`'s scope, not to this repair, and it is recorded here so it is not
re-found by accident a fourth time.
