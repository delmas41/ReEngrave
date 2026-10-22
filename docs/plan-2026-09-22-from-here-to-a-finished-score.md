# From here to a finished score — the assessment, and the process

2026-09-22. Written by the project-manager session at Sean's request: *"take a
step back, look at the whole, and put together a detailed process for how we
get from where we are to a finished product where we tell it to import a score
from IMSLP and it gives us a clean MXL and LilyPond print."*

Every number in §1–§4 was derived from the tree on `origin/main` at `2adf309c`
this morning by four read-only research passes (tests, flags and paths, the
derived checks, the product chain). Nothing here was read off a handoff.

⚠️ **This is a PROCESS document, not a handoff.** It does not carry findings
forward; it says what the system is, what is blocking the product, and the
order of work. It is meant to be the thing a session reads *instead of* the
chronicle.

---

## 0. The one-paragraph version

The reading architecture is good and the product is not connected to it.
There are two pipelines: the LEGACY reader (`transcribe.py`, 6,184 lines) is
what the web app, the LilyPond exporter, and every benchmark run; the STAGED
pipeline (30,794 lines) is where every decision of the last three weeks
landed, and **nothing in the product calls it, it has no LilyPond exporter,
and 18 of the 20 legacy mechanisms we call "shipped" are not on it.** The
metric was retired on 2026-09-08 and its replacement, the cleanup count, has
never been taken, so ~1,200 commits since then were steered by local
measures — reach, agreement with our own readings, byte-identity — and *"no
print was consulted"* closes 41 sections of the instruction file. The
instruction file itself is 132,000 words ordered by date of discovery, with
four competing "start here" pointers, and briefs get written from it. That is
where the bad premises come from: not from carelessness, but from a chronicle
being read as a spec, on a system with two paths that the chronicle does not
always distinguish. The foundation nobody has touched since 2026-09-04 is the
detector, and every stage is rigorous over the population it invents.

The way out is not another lane. It is: pick one pipeline, freeze the flag
surface, take the cleanup count, and connect the chain end to end before
improving any link of it.

---

## 1. Where we are — measured

### 1a. Size and velocity

| | |
|---|--:|
| commits to main, 2026-09-01 → 09-22 | ~1,900 (50–228 per day) |
| benchmark directories created in September | 206 (of 257 total) |
| `REFUSED` in CLAUDE.md / `REFUTED` / `NOT ESTABLISHED` | 137 / 41 / 41 |
| environment flags `OMR_*` read in the tree | **60** (20 default-on) |
| flags read on the legacy path only / staged only / both | 39 / 14 / 1 |
| lines under `tools/omr/` (excluding tests) | 94,160 |
| of which `tools/omr/staged/` | 30,794 |
| tests collected / test files / test lines | 4,826 / 185 / 66,559 |
| test functions asserting on SOURCE TEXT rather than behaviour | ~170 |
| mutation batteries under `benchmarks/` (none run by the suite) | 52 |
| CLAUDE.md | 850 KB, 132,000 words, 1,208 ⚠️, 4 "START HERE"s |
| handoff documents in `docs/` | 38 |
| staged record size with the ink layer (Breitkopf) | **115 MB per page** |

A whole 86-page Brahms 1 as a staged record would be ~10 GB. That is a
research artefact's shape, not a product's.

### 1b. The product chain, link by link

The product sentence is seven links. Here is each one against the tree.

| # | link | exists | path | missing |
|---|---|---|---|---|
| 1 | acquire from IMSLP | provenance from the wiki API; `ingest imslp` takes PDFs already on disk; wishlist ranks editions | manual | **no download** — the JS gate; a human clicks |
| 2 | catalog + identity | 289 editions, publisher / plate / year / `image_type` / `has_text_layer`; rosters for 223 works | staged (producer only) | `OMR_DOCUMENT_IDENTITY` default OFF and **read by nothing** |
| 3 | read | legacy `transcribe()` → JSON; staged → JSON + MusicXML | both | **staged has no LilyPond**; web app caps at 5 pages |
| 4 | web app | `local_omr.py` → legacy `transcribe` + legacy `to_musicxml`; export → legacy `to_lilypond` → `lilypond` binary | legacy only | **staged is structurally unreachable from the product** |
| 5 | review | Verovio render vs PDF page, Claude Vision diffs, accept/reject UI | web | `apply_corrections_to_musicxml` is a **stub** (copies the file, adds an XML comment) |
| 6 | LilyPond print | `export.to_lilypond`; renders to PDF only inside the backend | legacy only | drops dynamics, direction words, tremolo, cross-break hairpins by design; no CLI render |
| 7 | whole work | one 88-page run exists (13 min, slot alignment only) | benchmark | no end-to-end whole-movement MXL + PDF has ever been produced |

Two links are dead (1, 5), one is broken in the middle (4: the product runs
the reader we stopped improving), and the newest one (3, staged) stops at
MusicXML.

### 1c. What is wired, and what is not

The staged registry: **28 decisions, 1 stub** (`join_parts`); **92 quantities
declared, 47 observed by a gatherer, 17 declared and never gathered, 2 with no
vocabulary**; 13 detector families (36 classes) with no quantity at all
(accidental, grace, ottava, tuple, numeral, …).

The eleven derived self-checks **all exit 0** this morning, and between them
report: 66 wiring problems, 26 quantities with no live consumer, 44 of 114
conventions read by nothing, 8 brakes unresolved, 18 capture gaps, 3 open
trace problems, 37 parameters with no producer. They exit 0 because every one
of those sits on a `KNOWN_GAPS` list. **The checks have become inventories of
what is not wired, and they are always green.** They were built to make the
gap loud; the gap lists made it quiet again. (One check, the dashboard, exits 1
because the committed page is stale.)

The legacy-only list, verified by grep this morning — each has a definition
and call site on the legacy path and **no call from `tools/omr/staged/`**:
`_dedupe_cross_staff_detections` (superseded by `glyph_owner`, fine),
`_drop_clipped_notehead_fragments`, `_drop_unladdered_noteheads`,
`key_signature_corroboration`, `apply_contextual_analysis`, `_stitch_slots`,
`annotate_slurs_in_staff`, `_attach_articulations_in_cell`,
`_pair_ties_in_staff`, `_reconcile_measure_to_meter`,
`drop_uncorroborated_meter_changes`, weight routing (`input_domain`),
`clef_correction`, `label_contradiction`, `_wedge_anchors`, `condensed_parts`,
`score_layouts`, `slots.align`. Some have staged equivalents (arcs, wedges,
meter reconciliation, ownership); several do not (weight routing, the two
notehead-precision filters, the cross-system slot carry, the key corroboration).
Whether the staged path is *better* than legacy on a scan has never been
measured, because nothing scores it.

### 1d. What works well

Say it plainly, because the chronicle buries it under its own warnings:

- **The staged architecture is sound.** GATHER decides nothing; every decision
  abstains rather than guesses; the record keeps ABSENT apart from DECLINED;
  the accounting control is an equality that has caught real bugs three times;
  provenance is stamped; a fourth stage exists for "best rather than forced".
  On engraved input: pooled reading F1 0.933, **notehead recall 1.000**, meter
  carry right on both carried systems, `<beam>` exact on 18 parts. Nothing
  about the design needs revisiting.
- **The structural reading is essentially done.** Staves, systems (left-edge
  split, choir grouping, bracket columns 22/22 and 15/15 against print),
  barlines on warped scans, measure cells, staff-line localisation. Two months
  ago this was the problem.
- **The legacy pipeline is a working product end to end** — PDF → MusicXML →
  LilyPond → PDF, through a web app with review. Engraved 11-work OMR-NED
  0.1122. It is what we would ship today.
- **The library is real**: 289 editions across 29 publishers with provenance,
  1,745 reference encodings, rosters at `source_kind: "catalog"`, the id-space
  discipline. Acquisition is the only manual step.
- **The engraving-convention discipline works when it is used** (the whole rest
  means the bar; a dot sits a space higher on a line note; a beam runs stem to
  stem; a cautionary governs no bar; the key change is on every staff at one
  bar). Sean's `ask-first` instruction is the highest-yield rule in the repo.
- **The refusal discipline is right and should stay.** 137 refusals are the
  reason the file does not contain 137 guesses.
- The labeling tooling, the head-surgery recipe for weights, weight routing,
  the reading-vs-reproduction split, the engraved page truth.

### 1e. What does not work

- **Identity on scans** — on Litolff, 988 of 2,347 noteheads never reach the
  file because nobody could name the staff. In flight (Sean's session).
- **Key signature precedence** — the adjudicator prefers the reader that is
  wrong 24 times in 30 on engraved input. In flight (the other session).
- **The detector on scans** — hollow noteheads (68 printed, 8 found), hairpins
  (1 of 198), 76% of arcs binding fewer than two heads, 46 of 180 sampled
  "notehead" boxes not noteheads, a third of Breitkopf's stemless heads being
  barlines. Fine-tuning deletes classes; head surgery is the only recipe that
  has worked. **Untouched since 2026-09-04**, and every stage is downstream of
  it.
- **Durations on scans** — `duration_narrowed` 537 on Breitkopf, INFER's
  population, with zero notes of either INFER rule checked against a print.
- **No whole-movement run of anything on the staged path**; 93 s/page for
  labels, 267 s/page for direction words on a scan, 115 MB/page of record.
- **The product does not run the pipeline being built** (§1b).

---

## 2. Why the premises went bad — the mechanism, not the blame

Sean's diagnosis is right and it is worth naming the mechanism precisely,
because the process below is designed against it.

1. **Two pipelines, one vocabulary.** "Shipped", "default ON", "measured" all
   mean *on the legacy path* about two thirds of the time and *on staged* the
   rest, and the chronicle does not always say which. Six recorded instances
   of a brief built on the wrong half; the seventh (`OMR_ROSTER_LABELS`) ran
   the other way. Every measurement instrument (OMR-NED, the scan gate, the
   engraved benchmark, the ledger) scores the legacy path; every new decision
   lands on staged. **A change can be measured on one and shipped on the
   other, and nothing in the repo notices.**
2. **The finish line has had no number for two weeks.** OMR-NED was retired
   on 09-08 for a good reason. The cleanup count that replaced it was designed
   (the categories are committed, the artefact was built) and then never
   counted. Without it every lane chose a local measure it could compute
   alone, and the local measures reward what they can see: reach, agreement
   with another of our own readings, byte-identity. Those are controls, not
   objectives.
3. **The chronicle is read as a spec.** CLAUDE.md is larger than most
   sessions' entire context, ordered by discovery date, corrected in place
   (so a stale sentence and its correction sit paragraphs apart), with four
   "start here"s pointing at different days. A brief written from it inherits
   whichever paragraph the author read last. Three of the named
   documentation failure shapes (*fixed-then-kept-open-in-prose*, *a rule
   described and never built*, *a premise encoded in a refusal outlives its
   reason*) are all forms of one thing: **the document is the only place
   the system's current state lives, and it cannot be kept current at this
   size.**
4. **Chasing the loudest thing, in parallel.** 206 benchmark directories in
   three weeks. Four lanes independently reached the vertical stroke; three
   independently found the notehead contamination; two found the C-clef
   gatherer fault the same night. Parallel discovery is not waste, but it is
   the signature of no ranked list being the thing everyone reads.
5. **The foundation is avoided because it is expensive.** Every stage works
   over the detector's output list; missed ink has no address. The ink layer
   was built as the answer and its own falsifier fired. Detector work is slow
   (labeling, weights, GPU time), so the last three weeks went to the stages,
   which are fast to change and honest to measure — and which cannot fix a
   box the detector never drew.

The process below has one design goal: **make the current state of the system
derivable, make the finish line a number Sean owns, and make every lane a
step on one ranked list.**

---

## 3. Tests — what helps, what does not, what to simplify

**Helpful, keep:**
- Behavioural tests on adjudicators and exporters that carry a positive
  control (the "this input is accepted" beside every refusal). Most of the
  staged suite is this shape and it is why the stage contract holds.
- The two end-to-end fixtures that read real pages
  (`test_left_edge_split_e2e`, `test_recut_cells_e2e`) — the only tests that
  can fail on a real plate.
- The derived flag-direction guard, and the gather-shape assertions that
  check a fixture actually matches what GATHER files (that class of test has
  caught two real "the fixture tests the test" faults).
- The accounting-equality and partition tests (`Unbalanced`, `status_census`).

**Not helpful, or costly:**
- **~170 source-text tests** (`inspect.getsource`, AST walks, substring
  checks on module source). They prove a line exists, not that it fires; they
  fail on any mid-run edit of the file (recorded twice); and they are the
  reason a refactor cannot move a function without a red suite. Cap at zero
  new ones; convert or delete on touch.
- **The eleven derived checks in their current form.** Each maintains its
  own `KNOWN_GAPS`, each has had its own vacuous-control bug, and the union
  is always green. They cost a lane a day each to keep consistent.
- **52 mutation batteries** that live in `benchmarks/`, do not run in CI, have
  had at least three judge bugs (elapsed-time judge, `__pycache__`, restoring
  from the index), and two of which are recorded as *VOID as published*. They
  were one-off proofs; keeping the scripts live invites re-running them on a
  tree they do not fit.
- Tests that assert a stub EXISTS, tests that pin the CONTENTS of a gap list,
  and four separate hand-rolled `_log(...)` record builders.
- `test_export.py` at 3,206 lines and `test_staged_export.py` at 2,698 —
  unnavigable, and both test the exporter that the product will not use.

**Simplify (concrete, in Phase 0):**
1. One `tools/omr/tests/staged_fixtures.py` with one record builder and one
   page builder; delete the four `_log` copies.
2. Fold the derived checks into **one** command, `python3 -m
   tools.omr.staged.check`, with three exit states — *broken* (a control
   cannot run or contradicts itself), *open* (N findings, printed), *clean* —
   and write N to a committed `open-findings.json` the way
   `accuracy_record` writes the accuracy figure. A finding leaves the list
   when it is wired, not when it is explained. **The number must go down.**
3. Tier the suite: `pytest -m fast` (target under two minutes) runs on every
   commit; everything touching a PDF, weights, Surya or a 100 MB record is
   `slow` and nightly.
4. Archive the mutation batteries: keep every `FINDINGS.md`, move the
   `mutate*.py` under `benchmarks/_archive/`, and stop writing new ones.
   Replace the practice with the one thing they were proving — every new test
   is run RED first, by hand, against the unrepaired tree, and the commit
   message says so.
5. No test may read a `.py` file's source unless it is the flag-direction
   guard or the gather-shape check. Enforce with one grep in `check`.

---

## 4. The definition of done, and the acceptance set

**Done:** given an IMSLP work (or a PDF on disk), one command produces, for a
whole movement, a MusicXML file and a LilyPond-engraved PDF, in which
- every bar the reader could not read is marked as unread (a measure rest
  with no `<type>`, and a count in the report), never invented;
- every staff is named, or held out and counted;
- the meter, key and clef of every staff are correct or abstained;
- and the cleanup a musician has to do, counted in fix-actions per page on
  the categories already committed, is small enough that Sean would rather
  fix than re-enter. That threshold is his to set after the first count.

**The acceptance set is three documents, whole movements, fixed for the rest
of the build:**

| document | why |
|---|---|
| Beethoven 5 mvt 1, Litolff `984073` (scan, bitonal, MERGING plate) | the pessimistic end; identity-dominated; the only hand-verified windows |
| Brahms 1 mvt 1, Breitkopf `317803` (scan, SHATTERING plate) | duration-dominated; labels every staff; 6/8 |
| Beethoven 5 mvt 1 bars 1–24, Verovio render, 18 parts (engraved) | the only input with an exact page truth; reading accuracy is measurable |

Three measures, and only three:
- **Engraved:** reading F1 from the page truth, and musicdiff against the
  encoding. Machine, every run.
- **Scans, machine proxies (no print needed):** notes reaching the file /
  gathered; bars that add up to the meter in force; parts named; `held_out`;
  `unread_bars`. These are *controls* — a proxy that improves while the count
  worsens is what the count exists to catch.
- **Scans, the count:** Sean adjudicates **one fixed page per document**
  against the print, on `CATEGORIES.md`, roughly thirty minutes, every two
  weeks, results committed under `benchmarks/omr-cleanup-count-2026-09/counts/`.
  The first count is the baseline and it should be taken **this week, before
  any further repair** — the plan of 09-10 asked for it and it is twelve days
  overdue.

Nothing else is a headline. A lane may measure whatever it likes internally;
it reports against these.

---

## 5. The process, in phases

Each phase has a gate. A phase is not entered until the previous gate is met,
and a lane may not be dispatched without a phase item number.

### Phase 0 — Stop and consolidate (this week; no new reading work)

**0.1 One pipeline.** The staged pipeline is the product path from today. The
legacy reader is frozen: bug fixes only, no new mechanisms, no new flags. It
stays as a reference reader and as the thing the old benchmarks score until
Phase 3 replaces it. *Rationale:* everything since 09-08 is on staged; its
architecture is the one that can say why a note is wrong; and the product
cannot ship a reader whose decisions cannot be traced. The cost is that the
legacy path is better on scans today in several places (§1c) and Phase 3
pays that back deliberately.

**0.2 Flag triage.** 60 flags become at most 15 product flags. Every flag
gets one of three verdicts, recorded in one table
(`docs/flags-2026-09.md`, replacing the knobs table):
- *promote*: it is on by default and its off arm has not been used for a
  measurement in two weeks → delete the flag, keep the behaviour, keep the
  FINDINGS.
- *delete*: it was measured and refused → delete the code path, keep the
  FINDINGS.
- *research*: it is a producer-only or an unpriced experiment → it moves
  behind one `OMR_RESEARCH=` umbrella, may not be read by the product path,
  and carries a review date.
The `allow-list / deny-list` convention goes away with the flags it protects.

**0.3 Documents.** CLAUDE.md is archived byte for byte as
`docs/chronicle-2026-09.md` and replaced by a SPEC of at most 6,000 words:
what the product is; the five stages and their contracts; the quantity
vocabulary (generated by `gather_coverage`, not typed); how to run each
entry point; the acceptance set and the three measures; the ten rules (§6);
and a pointer to `ROADMAP.md`. Two further files, both append-only:
`docs/DECISIONS.md` (one dated line per decision, Sean's or a session's,
with the reason) and `ROADMAP.md` (this document's phases with status per
item). **Handoffs stop.** A session ends by updating the roadmap line for
its item and, if it learned something general, adding a rule or a decision.
Benchmark `FINDINGS.md` files stay where they are; the spec points at them
by phase item, never restates them.

**0.4 Tests** — §3 items 1–5.

**0.5 Lanes.** *(Amended 2026-09-22 by Sean: no lane cap while a manager
session is in charge — see `docs/DECISIONS.md`.)* A brief is
written from the tree (`git log --all -S`, `ls benchmarks/`, and the
`check` output), names its phase item and its gate, and ends with a print
check or a sentence saying why one was impossible. A lane that discovers its
brief is wrong stops and says so; that is a result.

*Gate for Phase 0:* the spec exists and is shorter than 6,000 words;
`tools.omr.staged.check` runs and writes `open-findings.json`; the flag
table is committed with a verdict on every flag; the fast tier runs under
two minutes.

### Phase 1 — The acceptance harness (weeks 1–2)

**1.1 Whole-movement staged records** for the three acceptance documents,
gathered once on a clean tree, provenance-stamped, kept under
`library/_shared-records/` with md5 receipts. Before gathering: the persisted
record must not carry the ink rows (115 MB/page) — persist the ink *summary*
(`ink_n_components`, coverage per cell) and re-derive rows on demand. Target
under 20 MB/page.

**1.2 Run-time budget.** A scan page costs ~93 s for labels and ~267 s for
direction words. `OMR_DIRECTION_TEXT_SCAN_GATE` is built and off; turn it on
for the acceptance runs and record the per-page cost. Target: a 16-page
movement in under an hour on the desktop, unattended, with
`OMR_SURYA_KEEP_ALIVE=0` so the run owns its own process.

**1.3 `python3 -m tools.omr.acceptance`**: one command that runs the three
documents (or reuses the shared records), exports MusicXML, converts to
LilyPond and renders the PDF (Phase 3 makes this native; until then via
`musicxml2ly`), builds the side-by-side PNGs for the fixed count pages, and
writes the machine proxies and the engraved scores to a committed
`benchmarks/acceptance/current.json`. It refuses to write on a dirty tree.
Nightly.

**1.4 The first cleanup count** (§4). Sean, three pages, thirty minutes each.
This is the baseline every later phase is measured against.

*Gate:* `current.json` exists with all three documents; a baseline count is
committed.

### Phase 2 — Close the foundation, in funnel order (weeks 2–5)

The trace tells us where noteheads are lost, per document. Work the funnel
from the top, largest loss first, and re-read the funnel after each item —
the ranking is the trace's, not this document's.

**2.1 Identity: staff → instrument → part** *(in flight, Sean's session).*
*Corrected the same day by that session: the loss is PLACEMENT, never
naming — every part on both shared records is already named — and the
residual after the family-block rule is five condensed `Violoncello e
Basso` staves, a convention decision for Sean, not a channel.*
Gate: `staff_not_identified` on Litolff from 783 to under 100 **with zero
grafts against the print**, and no part reading `Staff p1-s0-N`. The
ingredients are all measured: score order, margin labels, roster, clef
glyphs, bracket blocks, the family-block rule. The rule from the identity
brief stands — evidence contributes, never gates.

**2.2 Key signature precedence** *(in flight, the other session).* Gate:
engraved acceptance document 20 of 20 staves; Litolff hand-truth page no
worse than 44 of 75; the erasure cost on engraved input paid by a one-sided
rule (template preferred only where the document is *proved* engraved).

**2.3 Durations that INFER narrows.** The two INFER duration rules have
never had a note checked against a print. Crop the 17 (Litolff) and 41
(Breitkopf) inferred notes, adjudicate, and either default the rules on or
delete them. Gate: a hand-adjudicated precision on both plates, and a
default decision recorded in `DECISIONS.md`.

**2.4 The detector on scans — the systemic item.** Three tracks, none of
them a fine-tune:
- *Precision on the staged path, this week's work:* port the two legacy
  notehead-precision filters, and ship the measured width floor (1.0 staff
  space: catches 39 of 46 confirmed non-noteheads at a cost of 0 of 103
  confirmed noteheads) as an ADJUDICATE decision that refuses a box, not a
  GATHER filter. Gate: notehead precision on the hand-labeled cells does not
  fall; `no_stem` population shrinks by the barline share.
- *Recall on hollow noteheads and hairpins:* the labeling campaign plus head
  surgery is the only recipe that has moved a class without deleting others.
  Run one more round on the hollow-notehead and hairpin classes against the
  three-axis gate that already exists. Gate: half-noteheads on Litolff p1
  from 31 toward 68; hairpins on scans from 1 of 198 toward the CV reader's
  106.
- *A subject for missed ink:* the ink-first remedy was falsified as a
  replacement for the box; it stands as a **second population**. One narrow
  consumer: a zero-coverage, mark-sized ink component at a column where two
  or more neighbouring staves have an onset becomes an `unread mark` in the
  report and a marked bar in the file — never a note. This is the honest
  form of "we saw ink we could not name" reaching the human.

**2.5 Arcs** fall out of 2.4 — 76% of refused arcs are detector recall.
Re-measure after 2.4; do not build for it before.

*Gate for Phase 2:* on the acceptance set, notes reaching the file above 80%
of gathered noteheads on both scans, parts all named, and the second cleanup
count lower than the first on every category but `would-not-notice`.

### Phase 3 — The staged pipeline becomes the product (weeks 4–6, overlaps 2)

**3.1 LilyPond from staged.** The staged MusicXML exporter already reuses
the legacy `_mxl_*` renderers over its own positions; do the same with the
`_lily_*` renderers. Gate: the LilyPond output of the engraved acceptance
document compiles with zero bar-check failures, and its rendered page shows
the same notes as its MusicXML through Verovio.

**3.2 Port the legacy-only list deliberately**, one item per lane, each
measured on the acceptance set before and after: weight routing (cheap,
mandatory); the cross-system slot carry; key-signature corroboration (as a
recorded abstention first, a revert only after a decision); articulation and
tie pairing where the staged equivalents are weaker; `label_contradiction`
as a report. Skip what staged already does better (`glyph_owner` over the
distance dedupe; `arc_owner`/`arc_kind`; the meter machinery).

**3.3 The web app runs staged.** `local_omr.py` gets `omr_engine=staged`;
the page cap becomes a job budget with progress; the default flips when
the acceptance proxies on staged match or beat legacy on all three
documents. Gate: a whole movement through the web app, staged, to a
downloadable MusicXML and PDF.

**3.4 The correction loop, done the right way.** Do not patch XML. A human's
accept / reject / edit in the review UI is **evidence** — a reader with
`source_kind: "human"` filed against the subject the diff names — and the
export is re-run over the record. That is the architecture the staged
pipeline already has, it makes every correction traceable, and it is what
turns the analytics layer's auto-accept rules into real rules over recorded
verdicts. Gate: an accepted correction changes the re-exported file and the
record says who decided it.

### Phase 4 — Import from IMSLP (weeks 6–7)

**4.1 `reengrave import <work>`**: rank the editions from the wishlist logic,
open the chosen file's IMSLP page in the browser for the one click the gate
requires (Claude-in-Chrome can do it as the user; the tool must not defeat
the gate), watch the download directory, ingest, catalog, identity, run,
export, render. Everything except the click is one command.

**4.2 Movements.** A whole work is several movements; the dossiers carry
per-movement bar counts and meters, the catalog carries page counts, and the
meter/tempo cues at a movement start are measurable. The record needs a
`Kind.MOVEMENT` between DOCUMENT and PAGE so a meter carry cannot cross one
and a movement can be exported as its own file. Gate: Beethoven 5, all four
movements, four MusicXML files and four PDFs, page ranges right.

**4.3 Budget.** Measured seconds per page times pages, printed before the run
starts, with an unattended mode that owns its own processes.

### Phase 5 — Clean (ongoing)

The review loop on our own engraved output against the print, corrections
filed as evidence (3.4), the cleanup count every two weeks, and the
auto-accept rules learned from recorded human verdicts. The count trending
down on a fixed page set is the product getting finished. When Sean would
rather fix a page than re-enter it, it is done for that publisher.

---

## 6. The ten rules every session works under

These replace the 1,208 warnings. Each one is the general form of something
this repo has paid for at least twice.

1. **Brief from the tree, not from a document.** `git log --all -S`, `ls
   benchmarks/`, and `python3 -m tools.omr.staged.check` before the first
   line. A withdrawn investigation changes no code and is invisible to a
   code search, so read the benchmark directory named after the thing.
2. **Say which path.** Every claim about a mechanism names legacy or staged.
   "Shipped" without a path is not a claim.
3. **Ask first.** How would a human read this off the page, and which
   engraving convention governs it. One line to Sean before code; if nobody
   can be asked, write the assumption and what would falsify it at the top.
4. **One objective, three measures.** Report against the acceptance set. A
   local measure is a control; it may not be a headline.
5. **Reach before accuracy, and print before default.** No default flips on
   agreement with our own reading. A crop is cheaper than a lane.
6. **Connect, never guess.** A wiring change may connect a decision; it may
   not let one guess. Guessing lives in INFER and is labelled.
7. **A control must be able to fail.** Run it in a state where it fails
   before trusting it in the state where it passes. A number that is exactly
   another number is a computation, not a measurement.
8. **A fallback never converts "cannot tell" into an answer** — not into
   "same", not into "clean", not into a whole rest that means silence.
9. **No new flag, benchmark directory, derived check, or handoff** without a
   phase item number. Findings go in the benchmark's `FINDINGS.md`; general
   lessons become a rule here or a line in `DECISIONS.md`; nothing else is
   restated.
10. **The tree outranks every ledger**, including a commit message, a report,
    and this file. `git merge-base --is-ancestor` settles where work is.

---

## 7. What is deliberately NOT in this plan

- A new metric. OMR-NED stays as the engraved control; the count is the
  objective; nothing else is invented.
- A new stage, quantity family, or reader. The architecture has what the
  product needs; the product does not have the architecture.
- Fine-tuning the detector on the label corpus. Measured eleven ways to
  delete classes.
- Splitting condensed parts, a probability calibration, the tie chain
  quantity, the residue adjudicator, the meter template at bar heads —
  research items that stay behind the research umbrella until a count says
  they are worth it.
- Further work on the shared four-page records as baselines. Their committed
  verdicts no longer reproduce on today's tree (2,760 of 2,993); Phase 1
  replaces them with whole-movement records on one tree.

---

## 8. Decisions Sean owns (one line each; answers go in `DECISIONS.md`)

1. The staged pipeline is the product path and legacy is frozen — yes / no.
2. Archive CLAUDE.md and replace it with a spec under 6,000 words — yes / no.
3. The acceptance set is the three documents in §4 — confirm or substitute.
4. The first cleanup count is taken this week on three fixed pages — which
   pages.
5. Lane cap of two plus the manager — yes / no.
6. Flag triage verdicts — approve the table when it is written (Phase 0.2).

---

## 9. What the two running sessions should know

- **Instrument / staff identity:** it is Phase 2.1 and the first gate in the
  funnel. Its brief already carries the right rule (evidence contributes,
  never gates). Its gate is zero grafts against the print, not a reach count.
  It should not add a flag; a new default is a decision line.
- **Key signature docs and push:** it is Phase 2.2. The engraved-only
  precedence is right; the documentation it writes should be a `FINDINGS.md`
  and a decision line, not a new CLAUDE.md section — Phase 0.3 is about to
  archive that file.
