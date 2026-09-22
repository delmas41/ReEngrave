# Handoff, 2026-09-22 — four lanes, three refutations, and one measured decision waiting

⚠️ **READ FIRST, BEFORE BUILDING ANYTHING:**
[docs/ask-first-conventions.md](ask-first-conventions.md) — say out loud how a
HUMAN reads the thing off the page, and what ENGRAVING CONVENTION governs it,
before the first line of code.

Predecessor: [docs/handoff-2026-09-21-the-fact-sheet.md](handoff-2026-09-21-the-fact-sheet.md).
**Nothing in it is superseded**; two of its ranked items are answered here and
both answers are NEGATIVE.

An overnight session ran four lanes in parallel worktrees plus a manager lane.
**Three of the five came back REFUTING the thing they were sent to do**, which
is this repo's usual and best outcome. Every lane's synthesis is in a
`FINDINGS.md`; every one of those was **transposed at integration** because the
harness blocks subagents from writing `.md` files (see §7).

---

## 1. ⚠️⚠️ THE ONE DECISION WAITING ON SEAN, AND IT IS MEASURED

**`adjudicate_key_signature` prefers the reader that is wrong, and the reason
it gives for doing so is refuted on the one input where the print cannot be
blamed.**

On an ENGRAVED render of Beethoven 5 mvt 1 (18 parts, 3 pages), over 50 decided
staff-systems:

| reason | right | wrong |
|---|--:|--:|
| **`fitted_by_template`** (`Q.KEYSIG_TEMPLATE_FIT`) | **20** | **0** |
| **`fitted`** (the locator's slot fit) | **6** | **24** |

and the adjudicator **prefers the locator**. Every wrong verdict is `-1` where
`-3` is printed. The 6 right `fitted` answers are the clarinets and horns — the
locator is right exactly where the answer is small, **because it under-counts.**

Its docstring states the precedence and its reason: *"the locator loses
accidentals to broken ink, the template can match spurious ink and over-count —
so the one that cannot invent a glyph goes first."* ⚠️⚠️ **The ink here is a
VECTOR RENDER. The locator loses them anyway, 24 times in 30. The template
over-counts nowhere.** The detector is not the problem either:
`key_accidental` reading recall is **1.000, 132 of 132 glyphs.**

**The mechanism is measured**: `min_height_spaces = 1.10` against flats that the
page truth measures at **2.57 spaces** and that read **0.94 and 1.19 after
`header_ink_mask`** — the erasure removes **54–63% of each flat's height**.

⚠️ **91% of all note errors on 20 bars of 18 parts are this one fault.**

⚠️⚠️ **NOTHING WAS FLIPPED.** The refusal behind that precedence was priced on
**SCANS**, so this is the named new evidence *A PREMISE ENCODED IN A REFUSAL
OUTLIVES ITS REASON* asks for — **and not a licence.**

✅⚠️ **THE RENDER WAS RUN THE SAME NIGHT AND THE ANSWER IS TWO-SIDED — read
this before acting on the table above.**
[benchmarks/omr-keysig-erasure-2026-09/FINDINGS.md](../benchmarks/omr-keysig-erasure-2026-09/FINDINGS.md).
**It is not Verovio**: LilyPond gives the same three flats, the same two
dropped, **to within 0.03 staff spaces** (1.22 / 0.95 / 0.96 against 1.19 /
0.94 / 0.94), and Lane A's *"observation, not a mechanism"* reproduces too —
the dropped clusters begin ON a staff line and the kept one mid-space, the same
three positions to within 5 px. **And it IS the erasure**: asked directly, with
the staff lines INTACT all three flats clear the floor on BOTH renderers, and
`erase_staff_lines` is what puts two of three under it.

⚠️⚠️ **BUT *"if it is the erasure, it is everywhere"* IS FALSE, AND THAT IS THE
FINDING.** On the real Litolff plate the same erasure takes accidental-sized
clusters from **5 to 11** — it roughly DOUBLES them — because there the staff
lines MERGE glyphs and erasing SEPARATES them, **which is why
`erase_staff_lines` exists and why the refusal that prefers the locator was
defensible when priced on scans.** The mechanism is present there (two clusters
pushed under) and **swamped**.

> **So the cost is a property of ENGRAVED input**, where the ink is thin and
> clean and the lines lie across the glyph with nothing to separate. ⚠️ **That
> does NOT license flipping the precedence globally** — the template's 20/20 is
> engraved-only. Two shapes are conceivable, a **domain-aware precedence** (the
> classifier exists and is measured: `input_domain._classify_page`) or a lower
> floor; **neither is measured and neither is proposed.**

## 2. WHAT LANDED

| lane | outcome | `tools/` |
|---|---|---|
| **A** engraved staged record | **the first reading accuracy the staged pipeline has had**, and §1 | untouched by the lane |
| **B** join a chord to its stroke | **REFUSED by the print**, and the item was mis-sized | untouched |
| **C** re-price `OMR_ROSTER_LABELS` | **premise REFUTED**; the flag is legacy-only | docstring + 2 tests |
| **D** ink-first on the shattering plate | **the governing document's §7 falsifier FIRES** | untouched |
| **mgr** the `no_ink` lie | repaired; a fourth candidate named | `gather`, `record`, `trace`, `wiring` |
| **mgr** `score_reading` page lookup | repaired — a scoring instrument that answered with a ZERO | `score_reading` + tests |

**Suite on the merged tree: see §8.** All nine derived checks exit 0.

## 3. THE THREE REFUTATIONS, and what each replaces

**(a) The governing document's own falsifier fired.**
`docs/breakthrough-2026-09-18-the-unit-of-enquiry.md` §7 said: *"IF THAT TABLE
COMES BACK UNDIFFERENTIATED … THE FRAMING IS WRONG and the detector's box is as
good a subject as the ink."* Run ink-first on the SHATTERING plate §7 names as
the test's home: **no ink-derived axis separates print-confirmed junk from
print-confirmed noteheads as well as a feature of the BOX ALONE — every arm,
both publishers, both attributions** (0.939 vs 0.747; 0.937 vs 0.736). It
**reproduces** `omr-notehead-width-2026-09`'s independent *width < 1.0 catches
39 of 46 junk at cost 0 of 63*. ⚠️ It does **not** show the box is a GOOD
subject, only that here the ink is not a BETTER one, and **the sample is
stratified on geometry**, which inflates both. ⚠️ **§3's DIAGNOSIS is
untouched — what is refuted is the REMEDY.** The correction is at the head of
that document.

**(b) The chord/stroke join is refused by the print, and was mis-sized.**
Reach **31 heads of 2,322 (1.3%)**; of the 17 candidates the print settles,
**2 are a real chord and 15 are not** — **13 are not noteheads at all**.
Controls **12 of 15 with zero wrong**, so the convention is not what failed.
⚠️ **The ranked item was sized off a population two thirds too large**: its
`73/98` figure never asks whether the shadow head is STEMLESS, and only 24/33
are. *A shadow says a partner EXISTS; it does not say a join is MISSING.*

**(c) The truncated margin label is not a truncation.** The rule fires **zero
times on all 209 Brahms labels**; `'(C)'`, `'(Es)'`, `'in C 1/2'` carry no
instrument tail, every token is under three letters, and **no threshold makes
it reachable**. It is a **braced-pair** label — four horns on two staves, 1-2 in
C, 3-4 in E♭ — **which CLAUDE.md already said no lexicon can recover.** The
predecessor handoff re-found the symptom and attributed it to the wrong
mechanism; **so did the brief built on it.**

## 4. ⚠️⚠️ A DEFAULT NOBODY KNEW WAS ON

`OMR_ROSTER_LABELS` **governs the LEGACY reader only.** `work_roster.enabled()`
has exactly **one** non-test caller (`contextual.py:629`); staged
`adjudicate_instrument` calls `WR.decide(...)` **with no reference to the
flag**, gated instead by a `Q.ROSTER_ENTRY` row **the staged CLI supplies by
default.** ⚠️ **That is the INVERSE of the sweep's *"shipped means the LEGACY
path"***, so a reader assuming the usual direction gets it backwards in both
halves. It is **structurally live and practically dormant** — the shared Brahms
record carries `roster_entry … no work id / roster supplied` once per page —
**which is the state in which nobody notices a default.** CLAUDE.md's knobs row
and the predicate's docstring are corrected and the scope is pinned by two
derived tests.

## 5. TWO INSTRUMENTS WERE ANSWERING WITH DEFINITE ANSWERS THEY DID NOT HAVE

**(a) `no_ink` — repaired.** 2,377 claims on one record that the page is empty,
on cells `Q.INK` sees ink in. Three causes, three words:
`NO_GLYPH_OF_THIS_KIND` (997, and **997 of 997** had detections),
`NO_LINE_ACCEPTED`, `NO_STEMS_TO_JOIN`. ⚠️⚠️ **The finding is the beam half**:
`detect_beams` takes the stem set as its INPUT, so **665 of 980 (67.9%) stand
on a cell with fewer than two stems** and were never the beam reader's claim to
make — **and the 400 with no stem are EXACTLY the 400 cells `stem` itself
refused, set for set.** A second witness was already on the record and nobody
had looked: `Q.BEAM_STROKE` has **two** producers, so **274 cells hold a
detector beam beside a refusal saying there is no ink there.** ⚠️ **Lane A
reproduced the whole fault on a VECTOR RENDER** (421 of 439 on engraved page
0), which removes the print-quality excuse entirely.

**(b) `score_reading.py` — repaired.** `report()` used `page_index`
**positionally** while `transcribe --pages 2` returns a **one-element list
carrying `page_index: 2` inside it**, so every family printed **F1 0.000** — and
`staff_space_px` returned **1.0**, rescaling every tolerance ~20×. ⚠️ **It never
showed because every fixture the reading lane uses is `--pages 0`** — *a test
named for a hazard it does not reach*, arriving as a whole benchmark's worth of
fixtures.

## 6. RANKED NEXT WORK

1. ✅ **§1's render is DONE** — it is the erasure, it is engraved-specific, and
   the scan inverts it. **What is left is the DECISION**, and it is Sean's:
   a domain-aware precedence, a lower floor, or neither. ⚠️ **Do not flip the
   precedence globally on the strength of the engraved 20/20.**
2. **The in-bar accidental**, now sized: on correct-key staves we still write
   only 69% of alters, and the residual **is** the in-bar accidental, which
   reaches no quantity at all. ⚠️ Its dossier
   (`docs/symbol-dossiers/accidentals-keys.md`) already answers the five
   questions; it is blocked on a RECORD-SHAPE decision (*the staged record has
   nowhere to put a span*), which is Sean's.
3. **The cross-system SLOT CARRY on the staged path** — the legacy path stamps
   one name per SLOT across every page (`contextual.py:1527`); the staged path
   is `Kind.STAFF` + `Scope.EXACT` and has no equivalent. **A sixth instance of
   *shipped means the LEGACY path*.** Measure per-slot reach on a staged record
   first.
4. **`_project`, not the chord join.** Lane B's un-refuted half: **4 + 2
   strokes would FLIP direction** because `_project` builds its group from
   overlapping heads, so a dropped member is missing from the direction
   computation too.
5. **`dynamic_letter` precision 0.491** on engraved ink — over-emission, not
   blindness (recall 0.897), measured and undiagnosed.
6. ⚠️ **Do NOT build adjacency for bare-key labels** (refused 0 of 4), **do NOT
   flip `OMR_ROSTER_LABELS`** (its whole legacy reach is 20 labels), and **do
   NOT revisit the chord/stroke join** without a third publisher.

## 7. ⚠️ OPERATIONAL — subagents cannot write `.md` files

**Eight occurrences in this repo**, four of them tonight. Every lane's synthesis
had to live in commit messages until the managing session transposed it. **The
managing session wrote the same files into the same directories with a shell
heredoc on the first attempt**, so it is a property of how the LANE writes
files, not of the repository. ⚠️ **Until it is fixed, a dispatching session
should plan to transpose** — and should say so in the brief, so the lane writes
a synthesis worth transposing rather than discovering the block at the end.

⚠️ **A second operational fact**: a fresh worktree has **no** `.venv-omrned`,
`.venv-surya`, `weights` or `library`. Four symlinks, and **three of the four
fail on the SCAN side only**, so a worktree that runs `orchestral_eval` cleanly
proves nothing. Every lane brief carried the recipe; it should keep doing so.

## 8. WHAT IS NOT ESTABLISHED

- **No print was consulted by three of the four lanes.** Lane B cut crops;
  Lanes A, C, D did not, and Lane D's verdicts are the 09-18 crop pass's.
- **Lane A is n = 1 work, 24 bars, 3 pages, ONE RENDERER**, and a render is not
  a scan. §1's mechanism may be Verovio's.
- **No OMR-NED figure anywhere tonight, deliberately** — every question was a
  reading question, and the metric is symmetric.
- **The `no_ink` repair improves no reading.** It stops three readers
  overclaiming. Its four-page prediction is **pre-registered and unmeasured**;
  only a one-page confirmation exists.
- **Lane C's "staged is live" is STRUCTURAL** (source plus roster lookup),
  **not observed in a record.**
- **Nothing was flipped. No default moved. No constant was tuned.**
