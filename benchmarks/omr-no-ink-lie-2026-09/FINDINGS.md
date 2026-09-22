# `no_ink` is a claim about the PAGE, and three readers made it about THEMSELVES

**CONVENTION ASSUMED** — *a reader may only claim what it can see.* `NO_INK`
says the page is blank here. A reader that filters a non-empty list by class,
a reader that finds candidates and refuses them, and a reader whose input is
another reader's output all know something narrower than that, and the
project's own vocabulary already makes exactly this distinction elsewhere:
`NO_READING` was split from `NOT_IN_LEXICON` because *"folding the two
together would report a silent decoder and a refused reading as one number and
hide which rung is the limit."*

**WHAT WOULD FALSIFY IT** — if a decision somewhere read `reason == no_ink`
and behaved differently under a new word, this would be a behaviour change
wearing a vocabulary change. Checked: `grep -rn "NO_INK\|no_ink" tools/
--include='*.py'` outside `gather.py` and the tests returns **the vocabulary
declaration, `gather_coverage`'s name-printer, `trace`'s own report, and four
comments.** No adjudicator, consequence, inference or exporter reads it. It
would also be falsified if the new words were *less* informative than the old
one on any cell; each strictly adds a fact (`n_detections`, `n_stems`) and
removes none.

**NOT CONFIRMED WITH SEAN** — he is asleep. ⚠️ The DIRECTION is his, recorded
twice in the tree: *"NO_INK shows me that we are discarding information that
should be black and white."* The three particular words are mine.

---

## 1. The fault, reproduced before it was touched

`python3 -m tools.omr.staged.trace --run <record> --empty-claims`, on
`library/_shared-records/beethoven5-p1-p4-ink-identity.record.json` — the one
record carrying an ink witness (`Q.INK`, default-ON since 2026-09-17,
producer-only and read by nothing, which is what makes it independent):

```
witness ink: 1183 cells carry an ink row; 1180 carry a detection
such claims on the record: 2476, of which 0 are the ink reader's own
⚠️  CONTRADICTED: 2377
     dynamic_letter/no_ink   997
     beam_stroke/no_ink      980
     stem/no_ink             400
```

**997 + 980 + 400 = 2,377 exactly**, so these three families ARE the
contradicted population and nothing else is. `wedge_box/no_ink` (74) and
`margin_label/no_ink` (25) are NOT contradicted by the witness and are
therefore **left alone** — there is no evidence they are wrong.

## 2. The three populations do not share a cause — the joint census

`probe/joint_census.py`, joining each refusal to the reader's own input:

| family | `no_ink` | had a detection | had an ink row | had a stem |
|---|--:|--:|--:|--:|
| `dynamic_letter` | 997 | **997** | 997 | 628 |
| `stem` | 400 | 398 | 400 | 0 *(by construction)* |
| `beam_stroke` | 980 | 977 | 980 | 580 |

⚠️ **`dynamic_letter` is 997 of 997 — not most, all.** That loop iterates
`detections.items()`, so the detector fired on every one of those cells and
what it returned simply held no dynamic letter. A bar of noteheads and a slur
is not a blank bar.

## 3. ⚠️⚠️ THE FINDING: two thirds of the beam claims were never the beam reader's to make

**A beam joins stem TIPS**, and `detect_beams` takes the strokes `detect_stems`
returned — so the beam reader's INPUT IS THE STEM SET. Split by that input:

| the CV reader's stem set | cells | YOLO saw a beam on that cell | share |
|---|--:|--:|--:|
| **no stem at all** | **400** | 118 | 29.5% |
| **exactly one stem** | **265** | 77 | 29.1% |
| 2+ stems — the reader could have spoken | 315 | 79 | 25.1% |
| **total** | **980** | **274** | 28.0% |

**665 of 980 (67.9%)** stand on a cell that cannot carry a beam joined within
it whatever the page holds.

⚠️⚠️ **AND THE 400 ARE EXACTLY THE 400 CELLS `stem` ITSELF REFUSED — set for
set, with zero stem refusals outside the beam population.** That silence is
DERIVED: the beam reader inherited it and then reported it as a fact about the
page.

⚠️⚠️ **A SECOND, INDEPENDENT WITNESS WAS ALREADY IN THE RECORD AND NOBODY HAD
LOOKED.** `Q.BEAM_STROKE` has **two** producers — 322 observations from
`cv_lines` and **536 from the DETECTOR** — while all 980 abstentions are
`cv_lines`'. So on **274 cells the record simultaneously holds a beam observed
by the detector and a `cv_lines` refusal saying there is no ink there**, and on
**195** of those the CV reader also found fewer than two stems. A beam cannot
be printed without stems; in those 195 the stems are printed and the CV reader
missed them. ⚠️ The detector's beam is its own claim, not truth — but it is not
`Q.INK`, so this is a *third* reading agreeing the page is not blank.
⚠️ The share is flat across the three strata (29.5 / 29.1 / 25.1%), so it is
not an artefact of the stratification.

## 4. What shipped

Three words in `ABSTAIN`, each naming what the reader actually knows:

| word | the fact | population |
|---|---|--:|
| `NO_GLYPH_OF_THIS_KIND` | the detector fired here and none of it is this family | 997 |
| `NO_LINE_ACCEPTED` | a CV line reader ran and accepted no stroke of this kind | 715 |
| `NO_STEMS_TO_JOIN` | fewer than two stems, so no beam can be joined here | 665 |

⚠️ `NO_LINE_ACCEPTED` **deliberately says less than `Q.VERTICAL_RUN` could.**
`detect_stems` names and filters in one act, so whether a cell had candidates
*refused* or none at all is on the record only under `OMR_VERTICAL_RUNS`
(default OFF). Saying less than we know would be a fault; saying more was the
old one. The flag was **not** turned on and nothing was made unconditional —
that would change `detect_stems`' argument on every run, and its faithfulness
controls (1,920 = 1,920; 2,305 = 2,305) exist precisely because that path is
load-bearing.

⚠️ `NO_STEMS_TO_JOIN` **is a claim about our stem reading, not about the
print** — and where a beam IS printed and its stems were missed it says so
exactly, which is the point of it. §3's 195 are that case.

**The population stays visible.** `trace.ink_claiming_reasons()` is derived on
the token `"ink"`, so all three drop out of *contradicted* automatically; they
are also added to `_HONEST_EMPTY` so they keep appearing in the report. Without
that they would vanish entirely — this repo's own *"the inventory written to
account for the findings closed the check that produced them."*

## 5. Controls

- **The census has a positive control** that exits 2 if no `no_ink` refusal
  reaches the join at all — a join that quietly matches nothing produces a
  clean, believable zero.
- **12 new tests, and 7 go RED on the unrepaired tree.** Verified by swapping
  in `git show HEAD:tools/omr/staged/gather.py`, running with
  `PYTHONDONTWRITEBYTECODE=1`, and restoring with an **md5 check**
  (`a8ba9b22e4f6a9d85c2bc09a3b6f4bc3` before and after). The 5 that stay green
  are the two positive controls and the three vocabulary/derivation tests,
  none of which depends on the gather change — so every test that *should*
  move, moved.
- Each refusal test is paired with an acceptance test, because **a battery of
  refusal tests passes by refusing everything.**
- ⚠️ **Two fixture faults the tests caught in themselves**, both the shape this
  repo keeps paying for: `Log.rows` returns OBSERVATIONS and `Log.refusals`
  returns ABSTENTIONS, and asking the wrong one for a refusal returns an empty
  tuple that reads exactly like a reader that never ran; and
  `gather_cv_lines` imports `detect_lines` INSIDE the function, so patching
  `gather.detect_lines` leaves the real reader running.

## 6. ⚠️ ONE EXISTING TEST PINNED THE FAULT AND WAS REWRITTEN

`test_vertical_runs.py::test_a_refused_run_gets_a_row_where_before_it_got_nothing`
asserted `stem[0].reason == ABSTAIN.NO_INK` under the comment *"⚠️ AND `Q.STEM`
STILL SAYS `NO_INK` ABOUT THE SAME CELL, which is the collapse this quantity
exists to make VISIBLE rather than to fix."* That is an honest comment about a
deliberate scope decision — and a test that pins a known-false claim keeps it
alive. It now pins the repair, and additionally asserts the two rows still say
DIFFERENT things about one cell, which is what the quantity is for.

## 7. ⚠️ PRE-REGISTERED PREDICTION — written before any re-gather exists

This is a GATHER change, so `readjudicate` and `reexport_arm` are structurally
blind to it and **no re-gather was run here**. The numbers below are a
PREDICTION, not a measurement. A fresh gather of Litolff Beethoven 5 pp.1-4 on
this tree must report, from `trace --empty-claims`:

```
CONTRADICTED:                    2377  ->  0
dynamic_letter/no_glyph_of_this_kind  997
stem/no_line_accepted                 400
beam_stroke/no_stems_to_join          665
beam_stroke/no_line_accepted          315
```

⚠️ **The split is exact rather than approximate** because the code reads
`len(found.get("stems") or [])` at the refusal site — the same quantity this
census counted from the record's `stem` observations, which are 1,920 and all
`cv_lines`. **If a re-gather does not reproduce these four numbers, something
else moved and this write-up is wrong.**

## 8. ⚠️⚠️ A LIVE BLIND SPOT IN `wiring --check`, FOUND BY NEARLY WALKING PAST IT

Both refusals now carry the number the reason word asserts, so a later reader
can check the claim — a reason word nothing can check is a story. Named
`n_detections` and `n_stems`, **`wiring --check` exited 0 and listed neither.**

`wiring`'s DETAIL question is *"a key written on a row and named nowhere else
in the tree"*, and it matches on the **bare key name**. Both names already
occur in `tools/` for entirely unrelated reasons — `n_detections` in
`transcribe.py`, `yolo_detector.py` and `annotate/server.py`; `n_stems` in
`adjudicators/rhythm.py`, on a *different* quantity's `stems_disagree`
abstention — so each read as consumed by a module that has never heard of it.

Renamed to `cell_n_detections` and `cell_n_stems`, the same tool immediately
reports **2 unaccounted**, and both are now on `KNOWN_GAPS` with their reasons.

⚠️ **This is the documented family arriving at a new door.** `wiring` already
excludes tests and `benchmarks/` as consumers, because *a test naming a key is
not a consumer of it* and *the instrument that measures a gap is not a consumer
that closes it.* **An unrelated module naming the same string is not a consumer
either**, and that case is not excluded.

⚠️ **NOT FIXED HERE, deliberately.** Making the match quantity-aware moves
every entry in a 64-problem list at once, which is a change to the instrument
that every other lane's numbers rest on — and it should be measured, not
slipped in beside a vocabulary repair. What is fixed is that these two keys are
honestly audited; the blind spot is recorded with its reproduction.

## 9. What is NOT established

- **Nothing was re-gathered, exported or scored.** No file changes, no note
  moves, no OMR-NED figure — and none is wanted: the metric is symmetric and
  could not see a reason word at all.
- **n = 1 document, 1 publisher, 4 pages**, the low-res bitonal Litolff
  `984073`. The Breitkopf shared record predates `OMR_INK` and cannot be used
  as a witness; a sibling lane is making that record tonight and these numbers
  should be re-derived on it.
- **No crop was cut and no cell was checked against the print.** §3's 195 rest
  on the detector's own beam claims; that a beam is *printed* there is not
  established, only that two of our readers say so while a third said the page
  was blank.
- **`wedge_box` (74) and `margin_label` (25) are untouched and unexamined** —
  the witness does not contradict them.
- The repair **does not improve any reading.** It stops three readers
  overclaiming. Whether the 400 missing stems and 997 filtered cells are read
  better is a different job, and §3 says where to look first.
