# Direction words reach the file — the LAST declared stub, and it was two jobs

2026-09-11, no flag. **`adjudicate.stubs()` is now `()`.**

`direction` was the sixth and last of the original declared stubs and the only
one that was ever TWO pieces of work: `Q.DIRECTION_WORD` was the last
input-starved quantity on the record, so writing the adjudicator alone would
have produced nothing. The gatherer, the adjudicator, the emission and the
counter landed in one change.

---

## 0. ⚠️⚠️ REACH FIRST — AND THIS FAMILY HAS **THREE** WAYS OF BEING EMPTY

| | Litolff Beethoven 5 `984073` p1-3 | Breitkopf Brahms 1 `317803` p0-3 |
|---|--:|--:|
| word-shaped candidates (the CV's ink) | **42** | **56** |
| accepted by the lexicon | **2** | **10** |
| acceptance rate | 4.8% | 17.9% |
| `<words>` written to the file | **2** | **10** |
| rungs that ran | surya + tesseract | surya + tesseract |
| provenance | `6b7471ed`, dirty=**false** | `6b7471ed`, dirty=**false** |

Candidates per page — **Litolff** 9 / 25 / 8, **Brahms** 16 / 20 / 9 / 11.
Accepted per page — **Litolff** 0 / 2 / 0, **Brahms** 2 / 8 / **0 / 0**.

**The reach is THIN and it is thin for a reason this repo already records.**
Litolff `984073` is the *"low-res bitonal"* scan catalogued as firing 49 flag
boxes where Breitkopf fires 371; the same document yields 2 accepted direction
words against Breitkopf's 10. **Every figure below is one of 2 and one of 10,
and nothing here is a rate.**

⚠️⚠️ **THE THIRD EMPTINESS IS THE ONE THIS JOB IS ABOUT.** A change that moves
nothing because it is INERT and one that moves nothing because the page holds
nothing to move are the same number — and a direction reader adds a third: a
machine with neither `.venv-surya` nor Tesseract reads **zero directions on
every page**, identically to a page that prints none. `direction_arm.py` names
the rungs that ran before any other line and **exits non-zero declaring itself
DEAD** when no rung ran or no candidate was proposed. **Both rungs were live
for every figure here**, so none of these zeros is the machine's.

⚠️ **"inside a system vs a margin" is answered BY CONSTRUCTION, not by a
count: 0 candidates are ever in a margin.** `find_candidates` clamps every band
to the staff's own `x_start..x_end`, because *"left of `x_start` is the margin,
where the instrument name is printed — a reader let loose there returns
`Contrabassoon` as a direction"*. All 98 candidates across both documents are
`placement: below`; the `above` band exists and neither document put a
candidate in it.

---

## 1. WHAT LANDED — four legs, in one change

| leg | where |
|---|---|
| gatherer | `gather_direction_words`, `staged/gather.py` (replacing the declared-stub site) |
| adjudicator | `adjudicate_direction`, `staged/adjudicators/text.py` |
| emission | `_place_direction_words`, `staged/export.py` |
| counter | `counters["direction_words"]` at the render, and `FAMILIES["direction"]` |

`grep -c '<words>' tools/omr/staged/export.py` is now non-zero. Three sessions
on this path each shipped a decision that decided into no file for a day
(`adjudicate_dynamic`, `Q.ARC_KIND`, `Q.WEDGE_ANCHOR`); `direction` was the
last stub, so there is nowhere left for that pattern to hide.

**MEASURED**, one gather exported twice (`probe/reexport_identity.py`):

| | Litolff | Brahms |
|---|--:|--:|
| `<words>` | **0 → 2** | **0 → 10** |
| `<dynamics>` | 132 → **132** | 181 → **181** |
| notes | 1075 → **1075** | 2687 → **2687** |
| rests | 443 → **443** | 989 → **989** |
| words stripped from AFTER == BEFORE | **byte-identical** | **byte-identical** |

music21 reads back **exactly 2** `TextExpression` objects on the Litolff file
(`cresc.`, `Cresc.`) across 12 parts. The twelve words are `pizz.` ×3,
`dim.` ×2, `cresc.`/`Cresc.` ×3, `espr. e legato`, `pesante`, `unis.`, `arco`.

### 1b. ⚠️⚠️ THE SHIM IS EQUIVALENT TO `transcribe`'s PAGE DICT — 10 of 10, EXACT

This wiring does not re-implement the reader; it hands it a `page_dict` built
out of GATHER's own cells and detections. **The whole risk of the change is
therefore that the SHIM is not equivalent** — a wrong `bbox_page` convention
blanks the wrong rectangle, a missing measure span attributes a word to the
wrong bar, and NEITHER raises. Both failures look exactly like *"this document
has few directions"*, which is also the true answer, so no count on the staged
side alone can tell them apart.

`probe/shim_control.py` runs the LEGACY path (`tools.omr.transcribe`) over the
same four Brahms pages with the same weights and compares the accepted words:

| page | text | staged | legacy |
|---|---|--:|--:|
| 0 | `espr. e legato` | 1 | 1 |
| 0 | `pesante` | 1 | 1 |
| 1 | `Cresc.` | 1 | 1 |
| 1 | `arco` | 1 | 1 |
| 1 | `dim.` | 2 | 2 |
| 1 | `pizz.` | 3 | 3 |
| 1 | `unis.` | 1 | 1 |
| | **total** | **10** | **10** |

**7 of 7 `(page, text)` pairs agree exactly**, on two INDEPENDENT detection
runs — so this is not a cached comparison and the agreement is not trivial.

⚠️ **It is an EQUIVALENCE control, not a truth control.** Agreement means the
shim feeds the reader what `transcribe` feeds it; it says nothing about whether
either is right about the print. ⚠️ The text SET is compared as well as the
count, because a matching count over different words would be a coincidence
reported as agreement — the *"10 == 10, therefore the same ten"* shape this repo
already records under *coincidence-as-diagnosis*.

⚠️ Detector jitter is real here and is NOT cancelled: the two runs each did
their own detection, and a from-scratch rebuild of the hairpin fix once
reproduced the categorical result and not the edit count. So exact agreement is
STRONGER evidence than it would be from one shared gather, and a small
disagreement would not have been a failure.


---

## 2. ⚠️⚠️ THE STATE MACHINE IS THE PRODUCT, NOT THE TWELVE WORDS

`direction_text.read_directions` says in its own docstring that its report is
*"the only way to tell a page with no text from a reader that could not run,
and they look identical in the output otherwise."* **It returned those counts
and nothing consumed them.** CLAUDE.md's governing rule:

> **A fallback must never convert *"cannot tell"* into a definite answer** —
> not into *"same"*, and not into *"clean"*.

"This bar carries no words" is a definite answer. So the states do not share
an outcome:

| what happened | written where | as |
|---|---|---|
| no OCR rung on this machine | the PAGE **and every CELL** | `ABSTAIN.READER_UNAVAILABLE` |
| `OMR_DIRECTION_TEXT` off | the PAGE and every CELL | `ABSTAIN.OUT_OF_SCOPE` |
| the CV proposed no word-shaped ink | the CELL | `ABSTAIN.NO_INK` |
| a rung ran over this ink and it was not accepted | the CANDIDATE | `ABSTAIN.NO_READING` |
| the lexicon accepted it | the CANDIDATE | an **Observation** |

Downstream, `adjudicate_direction` returns an **ABSTENTION** for the first two
and a **DECISION with an empty value** for the other two. Both write nothing to
the file — and that is correct, because MusicXML has no way to say *"a reader
could not run over this bar"* and inventing one would be the fabrication this
family is built to avoid. **The FILE cannot tell them apart; the RECORD can,
which is where the distinction belongs.**

⚠️ **THE PAGE-WIDE REASON IS FILED ON EVERY CELL AS WELL AS ON THE PAGE, AND
THAT IS LOAD-BEARING.** A decision's subjects are the rows in the log
(`subjects_from=Q.DIRECTION_WORD`), so a page whose OCR rung could not run
would otherwise have **no `Q.DIRECTION` subject at all** — and a family that is
never ASKED reports `decided: 0, abstained: {}`, indistinguishable from one
that was asked and had nothing to say. That is the ABSENT/DECLINED collapse the
record exists to prevent, collapsing the exact distinction this gatherer is
built around. `gather_dynamic_letters` writes a row per cell for a related
reason and this follows it.

⚠️ **A NEW ABSTENTION WORD WAS ADDED: `NO_READING`.** "A rung ran over this
crop and returned NO CHARACTERS" is a different fact from "the lexicon refused
what it returned", and the direction reader is why: Surya *"either reads a crop
or says nothing"* and said nothing about **53 of 74 crops** on one 1870
Beethoven 5 page, while Tesseract read 72 of 74 and the LEXICON refused most of
them. Folding the two together would report a silent decoder and a refused
reading as one number and hide which rung is the limit.

⚠️ **AND THE SPLIT IS PAGE-LEVEL HERE, NOT PER-CROP, DECLARED RATHER THAN
FUDGED.** `read_directions` reports `n_read` and `rejected` for the PAGE, so
this gatherer cannot say which of the two a given refused candidate was. Every
unaccepted candidate is therefore filed `NO_READING` — the WEAKER claim — with
the page's counts beside it so the split is recoverable. Making it per-crop
means returning the per-rung readings from `read_directions`, which is a change
to the reader and is **not a wiring change**. See §8.

---

## 3. WHAT WAS REFUSED, AND WHY

1. **Touching the lexicon.** Not once. The 181-word gate is
   `direction_lexicon`'s, CLAUDE.md records it as never to be loosened, and a
   staged copy of it would be a second, differently spelled lexicon. A word
   that reaches the decision has already been accepted.
2. **Re-implementing the reader.** `_direction_page_dict` builds the shape
   `find_candidates` was written against out of the cells and detections
   GATHER already holds. The alternative — re-deriving the bands, the ink
   subtraction and the crop geometry — is four measured constants restated.
3. **Asking `Q.GLYPH_OWNER`**, unlike `adjudicate_dynamic`. The asymmetry is
   geometric, not an oversight: a dynamic LETTER arrives through a per-measure
   cell padded 4-6 staff spaces into the neighbour, so 24% of letters stand in
   the wrong cell and the move is an ownership question. A direction word never
   passes through that frame — `_bands_for_page` works in PAGE pixels and
   *"guarantees that no word is ever offered to two staves"*. There is also no
   contested DETECTION for an ownership rule to arbitrate: the detector never
   detected the word.
4. **Re-arbitrating the two rungs.** Where Surya and Tesseract both accept and
   name different words, the reader takes Surya by a documented precedence and
   counts the conflict. That count rides on the row; the arbitration stays in
   the reader. See §9.
5. **Nearest-note placement.** Marks go at the HEAD of the bar, the same
   DECLARED simplification the dynamics take. ⚠️ **CHECKED RATHER THAN
   ASSUMED, because the brief asked whether the frames have converged**:
   `gather_detections` does now carry `bbox_page_px` on a glyph row, so they
   are closer than they were — **but `_place_notes` indexes its heads by GLYPH
   INDEX out of the voicing, not by a box, and `Cell.directions` is consumed by
   a renderer that takes no note argument.** Placing a word against its nearest
   note is a real change to two functions and a separate, measurable question.
   Not a drive-by.
6. **Any new tuned constant.** There is none. Every threshold in this path
   belongs to `direction_text` and was measured when it shipped.

---

## 4. ⚠️⚠️ THE BUGS THIS FOUND, AND ALL FOUR WERE IN MY OWN WORK

### 4a. A declared input that could never answer — the FOURTH instance

`adjudicate_direction` read `ev.rows(Q.DIRECTION_WORD)` at the DEFAULT
`Scope.EXACT`. A word is gathered on the CANDIDATE's own **glyph** subject and
only the page-wide states on the **cell** — so at `EXACT` the decision **could
never see a word** and reported `no_words` on every bar that has one.

That is the same shape as `Q.STEM`'s 916 unread rows, `arc_owner`'s canonical
frame and `wedge_anchor`'s ORDER position: **a declared dependency that is
present, queried, and structurally unable to answer.** ⚠️ Note what did NOT
catch it: `inventory --check` passes (the `wants` entry IS read, so it is not
inert), and `gather_coverage` passes (the quantity IS gathered). Only a test
asserting that a word comes out found it. **Four instances now, each found by a
different instrument — there is no single check for this class.**

### 4b. ⚠️⚠️ AN EDIT DURING A RUN DOES NOT REACH AN ALREADY-IMPORTED MODULE — the MIRROR of the documented hazard

The first Litolff gather ran 32 minutes, finished GATHER, and then died in
**ADJUDICATE** on `AttributeError: type object 'ABSTAIN' has no attribute
'ABSENT'` — a bug already fixed on disk five minutes into the run. The
traceback's line numbers came from the NEW file and the executing code was the
OLD one.

The handoff records the outward form: *"`staged/__main__.py` imports the
exporter AFTER the gather, so a run picks up whatever `export.py` says when it
reaches EXPORT"*. **This is the other direction and it is worse**: a module
imported at process START keeps the code it was imported with for the whole
run, so an edit made mid-run silently does NOT take effect — while
`_provenance()`, which reads git at the END, will happily stamp the NEW commit.

> **A stamp taken at the end names the tree that FINISHED the run; the code
> that RAN is whatever was on disk when each module was FIRST IMPORTED. The two
> can differ in BOTH directions, and the stamp reports neither.**

Cost here: two gathers (~50 min) thrown away — the second, Brahms, was killed
by PID before it could crash the same way. **The recipe that works** is
stronger than the handoff's: land every tracked edit BEFORE the run starts, and
commit any untracked benchmark file in the first two minutes so the stamp names
a tree whose `tools/` is byte-identical to the one that ran. Both records here
are stamped `6b7471ed, dirty: false` and that claim is true of them.

### 4c. A default-ON flag spelled as an OFF test — caught by the DERIVED guard

The first version read
`os.environ.get("OMR_DIRECTION_TEXT", "1")... in ("0","","false","no","off")`
as a refusal. That is a correct deny-list and is logically identical to the
shipped spelling — and `test_flag_default_direction.py` **failed on it**:
that guard walks the AST for `os.environ.get(<FLAG>, <default>)` compared to a
literal word set and decides default-ON by **evaluating the predicate on its
own default**, so an OFF-shaped predicate reads to it as a default-OFF
deny-list and is reported as *"a typo would turn it ON"*.

⚠️ **The two spellings are equivalent and only one is CHECKABLE.** The
convention (`not in (off words)`, so the predicate is the ON test) is therefore
load-bearing rather than stylistic, and this is the guard doing exactly the job
CLAUDE.md built it for — caught on the full suite, not in review.

### 4d. `ABSTAIN.ABSENT` does not exist

The vocabulary is closed and `_Vocab.check` refuses an unknown word, which is
what turned a typo into a loud failure instead of a silent one. The
unreachable-by-construction branch uses `NO_DETECTIONS`, which the vocabulary
already has. ⚠️ **A new word was added for `NO_READING` and deliberately not
for this one**: `NO_READING` names a state nothing else names; a second
spelling of "no row here" would make a typo indistinguishable from an absent
reading, which is what the closed vocabulary is for.

---

## 5. THE CONTROLS, AND WHAT MADE EACH ABLE TO FAIL

* **`probe/reexport_identity.py`** — ⚠️ **THE OBVIOUS VERSION IS VACUOUS AND
  THE WEDGE JOB NEARLY SHIPPED ONE**: exporting committed transcriptions before
  and after and comparing md5 passes, and cannot fail, when `grep -c` for the
  element under test is zero in all of them. This **prints the element count
  FIRST and exits non-zero on zero** — 2 and 10 here — before it compares
  anything. It also refuses a record with no `Q.DIRECTION_WORD` row rather than
  reporting the clean zero that would follow, because it is an EXPORT arm and
  is structurally blind to a GATHER change (the mirror of `readjudicate.py`).
* **`direction_arm.py`** — reach and the rungs first, DEAD at zero.
* **`probe/battery.sh`** — **18 arms, ALL RED on the first run**, positive
  control SURVIVED, no BROKEN arm. Every anchor is a whole expression checked
  unique, after one fermata arm silently mutated a different function.
  ⚠️ **18/18 first-run is itself worth distrusting and is not the reassurance
  it looks like**: the battery was written from the same hazard list as the
  tests, so it measures whether the two were written consistently, not whether
  the tests are COMPLETE. The previous job's 9-of-19 came from arms aimed at
  code the tests were not written against. **Read this as "the tests reach what
  I thought of", not "the tests reach everything."**
* **The accounting controls** — `status_census.unaccounted` is **empty** and
  `balanced: true` on both documents; `decided_and_unwritten` is **{}**; the
  main `balance` holds and `Unbalanced` was not raised.

⚠️ **`direction_balance` IS AN EXACT EQUALITY WITH TWO NAMED RESIDUE
BUCKETS.** The session before last warned in writing about `<=`; the session
after it read that warning and still shipped a `<=` balance that reported
`balanced: True` while ten decided hairpins were counted by nobody. The two
buckets — `cell_not_in_any_part` and `placed_but_not_rendered` — are
DIFFERENCES rather than a sum, so they are what actually goes red. Both are
**0** on both documents. ⚠️ A **KNOWN EQUIVALENT MUTANT, named rather than
chased**: as written, `written + not_written` is `decided` by construction, so
`==` and `<=` agree on every input the code can produce today. The `==` is kept
as the guard against a future emission path that drops a word silently, and a
source-level test pins the spelling.

⚠️ **THE COUNTER SPLIT IS A CONTROL IN ITS OWN RIGHT.**
`counters["dynamics"] += len(directions)` counted every entry of the list, so
the day words arrived a `<words>` would have been billed to the `dynamic`
family — `dynamic` reading as emitting more than it does, and `direction`
reading `decided_but_unwritten` with its elements in the file. `<dynamics>` is
**unmoved at 132 and 181** across both arms, which is that control passing.

---

## 6. THE EIGHT STUB ASSERTIONS THAT WENT RED **ON SUCCESS**

Closing the last stub broke eight tests across seven files, every one of which
asserted that a stub EXISTS — `assertTrue(A.stubs())`,
`assertEqual(stubs, ["direction"])`, `assertEqual(A.stubs(), (Q.DIRECTION,))`.

**None was deleted, and none was replaced by `assertEqual(stubs(), ())`
alone.** An empty-set assertion is what a broken derivation returns too, and
*a check that cannot fail is worse than no check* is this repo's own lesson
from `health.py`'s `EMPTY CELLS: none`. Each now asserts the empty roster
**and** exercises the mechanism on a stub declared for the test —
`mock.patch.dict(A.REGISTRY, {...stub=True})` or the existing `_owns` helper —
so `stubs()`, `stub_starvation()`, `inventory`'s `stub` column and
`health.scan()`'s dynamic naming are each still proven to SEE one.

⚠️ **An assertion that a stub exists is a property of the BUILD'S PROGRESS,
not of the mechanism.** It is correct the day it is written and goes red the
day the work succeeds — a shape worth recognising before Phase 2 makes the same
move somewhere else.

---

## 7. ⚠️ WHAT IS **NOT** ESTABLISHED

* **Nothing about ACCURACY.** Not one of the twelve words has been checked
  against the print. They are plausible — all ordinary string markings for
  these pages — but plausible is not measured. The lexicon's accuracy was
  measured when it shipped; **this session MOVED the reading onto the staged
  path, it did not re-price it.**
* **Nothing about RECALL.** 42 and 56 candidates are what the CV proposed, not
  what the pages print. A word the CV never proposes is a word no reader can
  find, and that number is unknown here.
* **n = 2 documents, 2 publishers, 7 pages, 12 words.** Nothing is a rate.
* **The 46 Brahms and 40 Litolff refused candidates are NOT attributed** per
  crop; §2.
* **Brahms pages 2 and 3 yield 20 candidates and ZERO accepted words**, and
  this session did not open why. That is the largest single unexplained
  population in these two documents.
* **The `above` band is UNEXERCISED.** Both documents put every candidate
  `below`, so `above_first_measure_only` and the above-band geometry are
  inherited untested by anything here.
* **No OMR-NED figure is claimed, deliberately.** The metric is symmetric and
  rewards emitting more symbols; the legacy slur work's first cut LOWERED
  pooled OMR-NED while RAISING the edit count.

⚠️⚠️ **AND ONE REPORTED NUMBER IS WRONG IN A WAY WORTH PRINTING:
`coverage()` UNDER-REPORTS THIS FAMILY'S REACH 21× AND 5.6×.** The `direction`
row reads `cv_glyphs: 2` and `10` — because `_non_detector_ink` counts the
family's OBSERVATIONS, which are the words the lexicon ACCEPTED, while the
family's INK is the 42 and 56 CANDIDATES. It is the same shape as the wedge's
`detector_glyphs: 1` against 47 rows that the previous handoff flagged,
arriving from a different direction: there the CV READER was invisible to the
class space, here the REFUSALS are invisible to the row count. ⚠️ **Deliberately
NOT fixed in a wiring pass** — counting abstention rows as ink would change
every family's number at once, which is a cross-family reporting change and
needs its own measurement. `probe/summarise.py` prints both numbers side by
side so nobody sizes this family off the coverage row.

⚠️ `detector_glyphs: 0` on this family is **correct by construction and not an
omission**: a direction word is not in the 208-class space at all. `textDynamic`
is the class that would have supplied one and it is the class Phase 3.4's
expansion collapsed on.

---

## 8. REFUTED / REFUSED — do not re-try these

1. **Byte-identity by exporting committed transcriptions.** Vacuous unless the
   element count is printed first; §5.
2. **Restating `direction_text`'s bands, ink subtraction or crop geometry in
   the staged module.** Refused; §3.2.
3. **Testing the lexicon from the staged side.** Refused; §3.1.
4. **`ev.rows(Q.DIRECTION_WORD)` at the default scope.** It cannot see a word;
   §4a. The words are on GLYPH subjects.
5. **Joining a reading to its candidate by list position.** The two calls run
   the same pure-CV function today so the orders agree — but an index join is
   silently wrong the day either side filters, and a wrong join attributes one
   word's reading to another word's ink. Joined on `(staff, measure, x_page)`,
   the three fields `DirectionText` copies straight off its candidate.
6. **An OFF-shaped predicate for a default-ON flag.** Equivalent and
   uncheckable; §4c.
7. **`ABSTAIN.ABSENT`.** Not in the vocabulary; §4d.

---

## 9. NEXT — ranked

1. **Move the two rungs into the record as INDEPENDENT readings.** Today
   `read_directions` returns only winners, so the record cannot say what
   Tesseract read on a crop Surya won, and a refused candidate cannot be split
   into "the decoder was silent" and "the lexicon refused". `READERS.SURYA` and
   `READERS.TESSERACT` exist precisely so a decision can weigh two rungs, and
   `adjudicate_direction` is the natural home for the precedence that currently
   lives inside the reader. **This is the one change that would make the
   decision non-trivial** — almost everything it decides today is the state
   machine. It is a change to `direction_text` and was correctly out of scope
   for a wiring pass.
2. **Open Brahms pages 2-3: 20 candidates, 0 accepted.** §7.
3. **`coverage()`'s ink count for a family whose refusals are its ink.** §7.
4. **A third document, and one that prints an `above`-band direction.**
5. **Nearest-note placement**, once `_place_notes` and the renderer share a
   frame; §3.5.

---

## How to reproduce

```
OMR_SURYA_KEEP_ALIVE=0 python3 -u -m tools.omr.staged <pdf> --pages 1-3 \
    --weights .../deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
    --out /tmp/dirwords/x.json          # no --musicxml; see 4b
python3 benchmarks/omr-staged-direction-2026-09/direction_arm.py /tmp/dirwords/x.json
python3 benchmarks/omr-staged-direction-2026-09/probe/reexport_identity.py /tmp/dirwords/x.json
python3 benchmarks/omr-staged-direction-2026-09/probe/summarise.py x=/tmp/dirwords/x.json
zsh benchmarks/omr-staged-direction-2026-09/probe/battery.sh    # not during a gather
```
