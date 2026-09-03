# ReEngrave — Version Memory

A running log of changes made to this project, newest first. Updated after
every commit alongside CLAUDE.md and PROJECT_BRIEF.md.

---

## 2026-09-03 — Phase B: the pre-fill's precision follows the detector (0.88 → 0.96)

- **"Pre-fill precision is downstream of recognition" is now TESTED, and true** — the measured
  handoff's structural finding, and the reason Sean kept the approach open. A change of
  WEIGHTS alone, with no pre-fill code touched, takes the six-cell figure **exact 0.880 →
  0.961, kind 0.940 → 1.000**, the `labels` tier from 22 boxes to **44 of ~50** (still
  precision 1.000), batch CONFLICTs 4 → **0**, TP/WRONG_CATEGORY 174/16 → **191/5**, extra
  hints 200 → **58** and missing hints 20 → **15**.
- **The arm is not the imgsz-2048 re-ship** — that checkpoint is not blessed yet (the cloud
  run's directories hold per-epoch files and in-flight gate logs). It is the same shape of
  change and was already available: the batch's committed `transcription.json` was made with
  the PRE-hollow `imgsz2048-ft-30ep`, while scan-domain production is now `hollow-ft`.
  `benchmarks/omr-prefill-admission-2026-09/rerun_on_weights.sh` runs one arm per checkpoint
  against a symlinked scratch bench (nothing written inside the batch); add the re-ship column
  when it lands.
- ⚠️ **The objection is that hollow-ft simply detects less** (noteheads 4260 → 2419 on the same
  three pages). The control that settles it asks the opposite question — the MISSING-hint
  count, reference notes the reading never found — and it falls too (20 → 15; 4 → 3 on the six
  cells), while page segmentation is byte-identical (706 measures, 83 staves). The pipeline's
  own filters corroborate: unladdered noteheads dropped 1063 → 304, clipped fragments 259 →
  104. Every channel moves the same way at once, which is what separates a recognition gain
  from a threshold trade.
- Both Phase A predictions confirmed: `s2-m2`'s conflict (called "a duplicate detection the
  re-ship should clean up") is gone, and the labels tier's coverage climbed with the detector.
- ⚠️ **A batch's hints AGE with the weights.** This batch's committed `prefill/` is a
  checkpoint stale — the hints being labeled against are the 0.880 set. Refreshing is a
  re-transcribe plus `mxl_verdicts --write-hints`, which writes `prefill/` only and leaves
  `verdicts/` and `detections/` untouched (no human work, no detection id disturbed). Left to
  the batch's owner: it is served live by another session.

## 2026-09-03 — Phase A of the admission plan lands in the pre-fill

Sean approved the widening plan; its pre-fill half shipped, measured on the six-cell A/B
before and after, 206 tests green across the eight related suites.

- **The on-line/in-space variant follows the reference on exact pairs**
  (`expected_head_class(..., variant=)`, wired in `_decide`): the alignment key IS the
  reference's staff position, so on an exactly-paired note the reference knows the variant at
  the confidence of the pairing itself. Near pairs keep the detector's variant — measured, all
  six near matches were exact-correct and the truth's parity is wrong there by construction.
  Fixes 2 of 3 flips (six-cell exact **0.84 → 0.88**, kind unchanged), and it repairs the
  misread-clef case's variant along the way (both cello heads sit in bass-staff SPACES; the
  treble misreading had implied OnLine). Two test fixtures carried musically impossible
  variant/pitch pairs (E5 "OnLine", D5 "InSpace" in treble) that the new rule exposed —
  fixed to what the pitches actually print.
- **Within-measure tie chains collapse by the reading** (`measure_align.collapse_tie_chains`,
  run before the tremolo collapse): tied fragments become one head of the summed value only
  where the reading placed ≤ 1 head at the position; a chain may enter tied from the previous
  bar and leave tied onward; a total with no single written value (2.5 beats) is left as
  written because the page prints it as tied heads. On the batch: conflicts 5 → 4 and missing
  hints 22 → 20 — `s3-m6` resolved (its two hints pointed at blank paper); `s2-m2` STAYS
  because the reading shows TWO heads at the position (a duplicate detection) and the gate
  believes the reading — Phase B's re-ship is the expected resolver. The two accidental-glyph
  conflicts remain deliberately.
- **Every decision now carries an admission tier** — `admission: labels|queue` +
  `admission_reasons` (near match / variant corrected / grace-sized head < 0.85× the cell's
  median in both dims / cell-level: any flip demotes its whole cell) — and `--score` prints a
  per-tier table. Six-cell result: **labels tier 22/22 = 1.000 exact** at 0.44 coverage,
  queue 28 at 0.786. Stricter than the probe's 0.74-coverage composite because pre-fill time
  has no human-calibrated parity. ⚠️ Metadata only: verdict-writing is unchanged and nothing
  is auto-admitted until the random completion pass prices the tiers out-of-sample.

## 2026-09-03 — the five CONFLICTs reviewed: ties and accidentals, not tremolos

- **The measured handoff's hypothesis ("Breitkopf tremolo abbreviations") is refuted for all
  five conflicts**, corrected in place in that handoff and recorded with the evidence in
  `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/CONFLICT_REVIEW.md`. Three
  conflicts (2 on `s2-m2`, 1 on `s3-m6`) are the REFERENCE's tie-splits — one printed
  dotted-half encoded as tied eighth+quarter+quarter, `<tie>` on every fragment, no
  `<tremolo>` — so the hollow heads Sean had already boxed are right and the aligner was
  fighting fragments (its two "missing" hints on `s3-m6` point at blank paper). Two
  (`s26-m0`, `s15-m7`) are a flat's loop and a natural sign the base transcription misread as
  hollow noteheads, over already-empty (correct) human verdicts. **Nothing needs re-clicking.**
- Actionable residue: **tie chains need the reconcile-by-the-reading collapse tremolo already
  gets** (collapse to one summed-value head only where the reading placed one head) — that
  turns the three tie conflicts into confirmations. The two accidental fakes are the same
  family as the admission probe's phantom TPs.
- The optional `tremolo1`–`5` labeling pass gets **no support from this sample** — zero strokes
  in the four cells; parked until a batch shows strokes the detector mishandles.
- batch_config on Sean's Mac: the ACTIVE file is a STALE 9-class completion palette
  (pre-`fd28a76`, missing slur/tie/hairpins); continuing completion work needs
  `cp batch_config.completion.json batch_config.json` + server restart, not the hollow restore.

## 2026-09-03 — PR #5 landed; pre-fill admission signals measured

- **PR #5 (the pre-fill / labeling-system branch) is merged into main** — the branch had gone
  CONFLICTING against main after the weight-routing commits; the one conflict was
  `version_memory.md` (both sides' 2026-09-03 entries, resolved as a union, weight routing
  first), 196 tests green on the merged tree, merged as `711d3ff`. The main checkout on Sean's
  Mac still sits on the branch (now behind); `git pull` there when the cloud training session
  is done with it.
- **The pre-fill's 8 errors were separated by signals already in the records**
  (`benchmarks/omr-prefill-admission-2026-09/`): the aligner's own confidence is the WRONG
  admission axis — all six `near` matches are exact-correct (filtering them lowers precision
  0.840 → 0.818) and `strength_exact` ranks the cleanest cell below every error cell. What
  works: per-cell parity consistency (the one inconsistent cell holds 4 of 8 errors), a
  < 0.85×-median size veto (2/2 grace heads deferred for 1 good box), and re-deriving the
  on-line/in-space variant from the matched reference note rather than the detector (fixes
  2 of 3 flips, zero regressions — the alignment key already trusts that position). Composite:
  **37/37 exact at 0.74 coverage, in-sample** — a ceiling demonstration on the same biased
  six cells, not a claim; the out-of-sample test is a random completion pass scored by
  `probe_admission.py`, which reproduces the recorded 50/42/47 before it prices any policy.

---

## 2026-09-03 — The labeling survey widens: inventory, grace selector, click-first passes

**Why:** Sean's direction — extend the proven single-symbol × publisher
campaign toward every score element, with click-to-box as the standard.

**What:** (1) `benchmarks/omr-labeling-survey-2026-09/symbol_inventory.py`
generates `INVENTORY.md` — all 208 catalog classes + classless elements, each
with an owner (detector / CV / template-reader / specialist-slot / parked),
labeled-box counts, and publisher coverage; 106 detector-owned classes have
zero boxes, and the `numeral*` family surfaced as genuinely unassessed.
(2) `grace_score.py` — survey Row 2's selector (small solid head near a full
head, all thresholds in staff spaces, PROVISIONAL until first real labels) —
plus the honest first measurement in `GRACE_SELECTOR_2026-09-03.md`: the
280-cell hollow pool cannot validate it (top-ranked candidates are fragments
and dots), because cells selected FOR sparse sustained bars anti-correlate
with ornamentation; next step is a cut from grace-rich movements.
(3) The single-symbol pass UI now opens every cell **already in draw mode** —
click the symbols directly, no per-cell "add missed" step (`cell.js`; Esc
steps out; verdict hotkeys unaffected; 52 annotate tests green).
(4) NOTES.md gained the 🅿️ PARKED item Sean asked not to lose: re-try the
template-read elements (time signatures first) under the new labeling system,
detector as an added voter, harness ready-made.

---

## 2026-09-03 — Scan vs engraved weight routing (on by default)

**Why:** the hollow fine-tune ship left the two domains preferring different
checkpoints — scans want the hollow weights (half-notes 8→27 on beet5-p1),
digitally engraved input the prior production weights (11-work OMR-NED 0.1399
vs 0.1421) — and one weights slot forced one side to pay the other's cost.

**What:** when no weights are pinned (`--weights` / `OMR_WEIGHTS_PATH` /
`weights=` all absent), `transcribe()` now classifies its input by where the
ink comes from — a scanned page is one full-page raster image (total coverage
≥ 0.95 on every scan measured), an engraved page is vector drawings (428–2058
paths vs 0–4, gap empty over 147 probed pages) — and routes: scanned →
hollow-ft, engraved → prior production, ambiguous/blank → default. Any scan
page wins the document verdict (an IMSLP scan behind a digital cover is a
scan); a missing engraved file falls back soft; explicit choice always skips
classification. Verdict + evidence recorded in the result JSON as
`weight_routing`. New: `tools/omr/input_domain.py`,
`transcribe._route_weights`, env `OMR_WEIGHT_ROUTING` / `OMR_ENGRAVED_WEIGHTS`,
35 tests. Costs ≤ 77 ms per document. Side effect: default engraved runs use
the same weights the recorded accuracy headline was measured with, so the
record describes shipped behavior again. Measurements + A/B verification:
`benchmarks/omr-weight-routing-2026-09/FINDINGS.md`. The strategy decision —
why exactly ONE fork, why publisher/era weights are deferred and what
measured triggers reopen them, and the checklist future specialist weights
must pass — is recorded in
[docs/weight-routing-and-specialization-2026-09-03.md](docs/weight-routing-and-specialization-2026-09-03.md).

## 2026-09-03 — pre-fill / labeling-system work

- **the pre-fill has a number: precision 0.84 exact / 0.94 kind** — Sean labeled six Brahms
  cells COMPLETELY by hand (every symbol, not just hollow heads) and `--score --score-classes
  all` scored 50 pre-filled boxes against 94 human ones, 42 exactly right. Recall (0.447) is
  meaningless and always will be: the pre-fill proposes only noteheads. Diagnosed box by box,
  the 8 errors are **concentrated, not diffuse** — 2 grace notes (IoU 0.73-0.80, right place,
  wrong size), 3 on-line/in-space flips (IoU 0.31-0.41, box half a notehead off) and 3
  unmatched, with six of the eight inside two of the six cells; excluding grace, 44/50 = 0.88.
  ⚠️ The sample is BIASED by my own cell choice — ranked by how much the pre-fill decided, so
  the densest bars, where alignment slips most; n=50 gives ~0.71-0.93 at 95%. **Verdict: a
  queue, not labels, today** — and the structural finding is that **six of eight errors are the
  DETECTION's placement**, which the pre-fill inherits, so its precision is downstream of
  recognition and should rise with the imgsz-2048 re-ship untouched.
- **grace notes are a ceiling, not a bug, and two plausible fixes were refuted by measurement**
  — the transcription holds **0 `Small` detections on any page** and the reference **0 grace
  notes in 28,579**, so neither source knows. First guess (the pre-fill overwrote a `Small` the
  detector gave) is false: `expected_head_class` already preserves size. Second guess
  (`include_grace=True` so `<grace/>` supplies it) was implemented, **changed nothing**, and was
  **reverted** rather than kept — it alters alignment for every cell and bought nothing
  measurable. ⚠️ Recorded because `truth_tokens` justifies the skip on the grounds that "the
  detector labels them `*Small`", which is FALSE on a scan and makes the skip harmful on the
  first reference that does carry grace notes. Untried route: geometry — a grace head is
  smaller than its neighbours (41×38 against 51-83 in the same cell).
  Full writeup, the checklist state and six ideas for widening this:
  `docs/handoff-2026-09-03-prefill-measured.md`.
- **`--score` can now be widened past the batch's own pass, and refuses to be widened
  misleadingly** — chasing the open checklist item "can pre-filled TPs be admitted without a
  glance". Running `--score` on the Brahms batch answers **precision 0.60, recall 0.333 — over
  5 pre-filled boxes against 9 human ones, in the four hollow-notehead classes only**, because
  scoring was hard-filtered to the batch's `batch_config` pass. That batch is a single-symbol
  hollow sweep, so the black heads and rests that make up the bulk of the 179 confirmations are
  not in the comparison and no way of running it could put them there. `--score-classes
  pass|all|<list>` widens it; ⚠️ **and widening is refused** unless `--cells` or
  `--score-inspected-for PASS` restricts it to cells a human actually swept for those classes.
  The trap is silent and would have looked like a verdict on the pre-fill: a hollow-only pass
  drew no black noteheads, so scoring every class against it charges each correctly pre-filled
  black head as a false positive, and the precision that comes out measures which pass the
  human ran. `inspected_passes` is the evidence used, since it is stamped on the way out of a
  cell and so means "looked and moved on" even where nothing was drawn. The default is
  byte-identical to before (pinned by a test comparing it to the explicit `pass` spec), and the
  report line now always names the classes and cell selection the number covers. 8 new tests,
  191 green across the pre-fill, annotate and training suites.
  **So the deciding number still needs Sean:** a handful of cells labeled COMPLETELY, then
  `--score --score-classes all --score-inspected-for <that pass>`.
- **a checked-out batch shows no music, and now there is a tool for it** —
  `tools/omr/annotate/recut_cells.py`. Sean opened the Brahms batch and got a blank canvas.
  `benchmarks/*/cells/` is gitignored (`.gitignore:77`) and **no batch has ever had a PNG
  committed**, so a checkout that did not CUT a batch has its manifest, detections and
  verdicts and not one image; the server answers 404 for every `/api/cell/{id}/image` and
  the canvas draws nothing, with the sidebar, hotkeys and hints all working. It affects all
  six hollow batches, not just Brahms. The tool re-renders only the ids `cells.json` already
  holds, and **never writes `cells.json` or deletes anything** — the obvious repair, re-running
  the cutter, is the dangerous one: `rank_and_trim.py` rewrites the manifest and deletes the
  PNGs it did not keep, so it can renumber the cell set and orphan every verdict in a labeled
  batch. ⚠️ **The frame is checked, not assumed.** Boxes are stored in the cell's CANONICAL
  frame, so an image re-cut at a different padding puts every box in the batch somewhere else
  on it and nothing downstream would say so. The two cutters disagree on padding on purpose
  and the manifest does not record which was used — but it records `cell_canonical_w`/`_h` and
  `staff_line_ys_canonical`, so the mode is DERIVED by cutting under each and keeping the one
  the manifest agrees with; no match, no write (`--allow-partial` to write the rest anyway).
  33 tests: the decisions with the cut injected, plus an end-to-end suite that cuts a
  synthesized page, deletes the images and re-cuts them **byte-identically** under both modes.
  ⚠️ That fixture crowds its staves to ~5 staff spaces on purpose — `measure_extractor` grows
  the pad where the neighbour is over 6 spaces off, so the first draft (33 spaces apart) had
  both modes returning the same height and could not have tested the detection at all.
  Verified against the real Brahms batch here: it refuses with exit 1 and names the one
  unfound PDF, because the score library is machine-local. Suite: 1752 passed, 4 pre-existing
  failures (identical with the branch stashed), 2 collection errors from no music21.
- **merged main's training gate; Brahms hints refreshed** — `origin/main` brought Sean's gate
  run (`ef51612`, `benchmarks/omr-labeling-survey-2026-09/GATE_RESULTS.md`): hollow scan labels
  PASS (half-note detection 8 → 25 on Beethoven, 9 → 23 on held-out Mahler, `with_duration`
  recall 0.388 → 0.456); the dense-page narrowing belongs to the imgsz-640 fine-tune recipe,
  not the labels, so **v8 stays out of the catalog** until an imgsz-matched fine-tune re-gates.
  Zero conflicts with the branch. Then `prefill/` on the Brahms 1 / Breitkopf batch was
  re-written with `--write-hints` so the committed hints carry the tremolo / tremolando
  collapse and the red `CONFLICT` hints (it had been written from `73f9970`, before either):
  all 57 files changed, totals identical to the handoff (179 TP, 10 relabels, 189 added, 22
  missing, 200 extra, 5 conflicts — on **4 cells**, one carrying two), 5 abstentions unchanged.
  ⚠️ The handoff's re-run command passed `--work-id brahms-sym1-mvt1` and the CLI refused it
  with "no usable window rows": the window rows carry the LIBRARY id `brahms--symphony-1`,
  not the dossier id. The runbook's form (no `--work-id`, one work per file) is right; the
  handoff is corrected. 124 tests green across the pre-fill, drafter and annotate suites.
- **session handoff written** — `docs/handoff-2026-09-03-prefill-session.md`: what the branch
  built, the seven rules the pre-fill decides by, what is measured (Brahms 1: 51 of 56, 5
  conflicts) and what is not (black heads and rests), Sean's checklist, and the environment
  notes for a fresh cloud session. CLAUDE.md and PROJECT_BRIEF.md point at it. This session
  ran out of context and closes here; the next one starts from that file.
- **pre-fill: tremolando — two pitches alternating collapse to two heads** — Sean: "Tremolo
  and tremolando". A reference run `A B A B …` (≥4 equal values, two pitches) is the page's
  two-pitch tremolando: two heads, each written with the FIGURE's full value (a bar of
  alternating sixteenths prints two whole notes joined by beams, not two halves). `tremolo_runs`
  now reports a run's kind (`single` / `pair`); `collapse_tremolo_runs` emits one synthetic
  note for a single-pitch run and two for a pair, each `duration_ql = total/2` with the type of
  the full total, and only where the reading placed ≤1 head at each of the run's positions —
  a page that printed the alternation out is left as written. Same conflict rule as the
  single-pitch case. Brahms 1 dry run unchanged (51 of 56, 5 conflicts); 56 tests green.
- **pre-fill: the READING decides whether a run is abbreviated; a hollow-vs-black conflict goes
  to the human** — Sean's proposal: keep labeling a tremolo head as the hollow head it is (the
  class space already has `tremolo1-5`/`tremoloMark` for the strokes) and let the MXL side
  reconcile. Now a run of ≥3 repeated notes (any value: three eighths as much as six) is
  collapsed to one note of its total value only where the reading placed ≤1 head at that
  staff position, and left as written where the page printed them out. A black head read where
  the collapsed reference says hollow is relabelled (the scan's usual miss); a HOLLOW head read
  where the reference says black is neither trusted nor overruled — the detection stays pending
  with `CONFLICT` in its note and a red hint. Brahms 1: 51 of 56, 5 conflicts for Sean's eyes.
- **pre-fill: tremolo abbreviations, and the first score against Sean's boxes** — Sean had
  labeled all four remaining hollow batches on main (55 Brahms verdict files, 14 hollow boxes).
  Scored: of the pre-fill's hollow boxes 3 agreed, and where it disagreed the reference spells
  a tremolo out as six repeated eighths where the page prints one hollow head with slashes —
  the pre-fill had even relabelled two correctly detected hollow heads to black. A run of ≥3
  repeated notes adding to a half or more is now ONE unit: a hollow head read over it keeps
  its class (note says why), the run counts once for recall, and a missed run becomes one
  hint typed as the abbreviation (`6× eighth → half.`). Brahms 1: 52 of 56 pre-filled.
- **pre-fill run on the Brahms 1 batch from this session** (inputs pushed by Sean): 51 of 56
  cells pre-filled, 179 TP, 15 relabels, 22 missing-note hints, 5 abstentions all on the right
  bar. Three fixes on the way: a weighted LCS that tolerates a half-space of rounding but needs
  at least one EXACT match before near ones count (a wrong bar's notes often sit a step away);
  recall over the reference's NOTES, not its rests; a rests-only bar pre-fills with hints instead
  of abstaining. `prefill/` (hints only) committed into the batch so labeling can start.
- **pre-fill: the gate is recall of the reference, and neighbours' heads stay out of the
  alignment** — a flute bar of 4 reference notes read 21 heads, 17 of them the oboe's and
  piccolo's from the cell's padding (positions 7 spaces off the staff); only heads within the
  reference's own vertical range align, and a bar passes when ≥ 50% of its reference notes
  (and at least 2) are found. Also fixed: `bbox_page_px` is `[x0, y0, x1, y1]`, not
  `[x, y, w, h]` — the x-scale into the batch frame and the width check were wrong.
- **pre-fill: diagnostics for the abstentions** — `--debug-cell` prints both token sequences
  and the geometry for a cell; every cell records a width ratio that says whether the batch
  cell and the transcription measure are the same bar (the batch was cut by a separate
  segmentation run). A reference part with no clef (percussion) falls back to step keys on
  BOTH sides. Second Brahms run: 29 of 56 pre-filled.
- **training: pre-fill aligns on STAFF POSITION, not pitch** — the reference's written clef
  (now parsed by `musicxml_truth`, per note) places each truth note; a detection's position
  comes from its box. Sean's first Brahms 1 run: 26 of 56 cells pre-filled, 30 abstained with
  `0 of N matched` — the misread-clef signature. `--match step|exact` kept as options; the
  summary now lists abstained cells with their match ratio.

## 2026-09-02 — pre-fill / labeling-system work (this branch)

- **training: draft fills an unnamed staff by ORDER** — on a shorter system, a staff the reader
  could not name takes the only unused base entry between its paired neighbours (Sean's page 1
  bottom system: the Kontrafagott between the Fagotte and the Hörner); two candidates → still
  empty for the human. Brahms 1 batch draft now needs no hand edits.
- **training: page-global staff numbering** — `transcribe` numbers `staff_index` across the
  page; the draft summed bars per index across systems (page 1 of the Brahms batch came out
  as 7 bars instead of 15) and the pre-fill joined a staff to the row by index. Both now go by
  position within the system; a full-lineup system pairs by position with the reader's word as
  a cross-check only. Found on Sean's first real draft of the Brahms 1 batch.
- **training: `draft_windows.py` + `--write-hints`** — window rows are drafted from the
  transcription and a base benchmark row (measure window chained page by page, staves paired
  to parts by instrument name, everything marked `draft` with a `check` list); hints-only
  mode writes `prefill/` without touching `verdicts/`. Runbook for the first real-batch
  measurement (Brahms 1 / Breitkopf): `docs/runbook-prefill-brahms1.md`. Finding: the Mahler
  batch cannot be scored — the library has no Adagietto reference.
- **training: MXL-guided verdict pre-fill** — `tools/omr/training/mxl_verdicts.py`
  (+ `measure_align.py`, `musicxml_truth.py`): the detector's boxes are confirmed or
  relabelled by the reference encoding through per-measure sequence alignment; unmatched
  detections stay pending, unmatched reference notes become ghost hints. Annotate server
  serves `<bench>/prefill/`; the cell list gains a queue order and the cell page a hints
  layer (`h`). `--score` measures the pre-fill against human verdicts. 43 new tests, full
  annotate + training suites green. Not yet run on a real batch — that measurement is
  Sean's next step on the Mahler 5 / Peters hollow batch.
- **docs: status brief, project brief, version memory** — consolidated where
  the labeling campaign, the movement-start data, the score-library ingest and
  the MXL-guided auto-label training system stand; created `PROJECT_BRIEF.md`
  and this file. No code change.
- `6a17de7` docs: export-gap ordinal moves out of prose into the numbered list.
- `b5b7db3` / `0a6382c` / `d282371` **eleven-work benchmark landed** — headline
  3 → 11 works; `0.1306 / 2745` default (reader on), `0.1399 / 2915` reader off,
  both on `44a1745`; boundary stamped and checked by `accuracy_record`.
- `52e9945` labeling: Mahler 5 Adagietto (Peters) hollow batch — 49 boxes, 55/56 cells.
- `2a8bf79` labeling survey: symbol × publisher-family plan; scope decision
  PROVE-IT-FIRST (finish the 280 cut cells, one gated training run, extend only if it holds).
- `54d19da` labeling: `batch_config.json` (single-symbol hollow pass) on all five round-2 batches.
- `44a1745` scan-e2e: `works.json` pinned the direction reader off while claiming defaults; now pins `null`.
- `fb4c500` … `59c1eca` labeling: hollow-notehead round 2 cut — five 56-cell batches
  (Peters, Eulenburg, Litolff 4×, Breitkopf, Simrock); enclosed-counter ranker replaces
  meter shortfall (did not transfer).
- `fa9853a` labeling: round-1 hollow batch landed as `data/user-labeled/v7-2026-09-02-hollow`
  (24 cells / 28 boxes); 116 of 117 model pre-labels were false.
- `2b900c4` annotate: `inspected_passes` stamp — a swept-empty cell is provably distinct from a never-opened one.
- `eb3530c` / `9b3cec4` / `6cad993` / `9998390` annotate UI: single-symbol pass mode —
  click places a measured, staff-snapped box; tests 18 → 52.
- `96df4fb` / `a907e41` / `f238ce9` export: a bar with no detected notes still carries its
  `<direction>` and dynamics (eighth detected-then-dropped gap). Neutral on engraved pages by construction.
- `4952005` direction text ON by default (−144 edits, stable across seven mains).
- `de09383` / `fc073f2` finding: same scan page transcribed twice differs; isolated to
  `contextual._labels_for_page`; geometry bit-identical with contextual off.
- `d3d5ec5` export_coverage surveys all eleven works.
- `bc4214d` gitignore: alternate `--work-dir` fixtures are scratch.

## 2026-09-01 — pre-fill / labeling-system work (this branch)

- Overnight generalization session: engraved corpus widened 3 → 10 (opened at ~2× the
  incumbents' error), first five-row scan benchmark (pooled 0.7960), cut-common meter
  bug fixed (3 wrong → 0), two key-signature vote bugs fixed, fermata render completed
  in the Beethoven fixture (0.1519 → 0.0727). See `docs/overnight-2026-09-01-summary.md`.
- Evening queue: edge fragments, dot height, YOLO beam stack, stem cap, beam-bar mask,
  ledger evidence (Beethoven 81/81), viola double stops, slurs paired per staff,
  Tesseract union rung, accuracy figure made single-sourced.

---

## 2026-09-03 — Diagnosed and addressed the failing `Deploy ReEngrave` GitHub Actions workflow

**Why it was asked:** every one of 123 runs of `.github/workflows/deploy.yml`
had failed since it was added on 2026-09-01.

**Root causes found (two independent failures, one per job):**

- [x] **Backend job (Docker build) — wrong build context.** The workflow ran
  `docker build .` from inside `working-directory: backend`, so the build
  context was `backend/`. But `backend/Dockerfile` (and `docker-compose.yml`,
  which builds it correctly) both assume the context is the **repo root** —
  `COPY backend/requirements.txt .` and `COPY tools/ ./tools/` need `tools/`
  and a nested `backend/` folder to exist in the context, neither of which
  exists inside `backend/` itself. Every run failed at `COPY tools/
  ./tools/` with `"/tools": not found`.
  **Fixed:** build from the repo root with `-f backend/Dockerfile .`
  instead of `cd`-ing into `backend/` first.
- [x] **Frontend job (Vercel) — missing repo secrets.** Failed immediately
  with `Error: Input required and not supplied: vercel-token` — the
  `VERCEL_TOKEN` GitHub Actions secret (and likely `VERCEL_ORG_ID` /
  `VERCEL_PROJECT_ID`) was never configured for this repo. Same is true of
  `RAILWAY_TOKEN` for the backend job, just masked by the Docker build
  failing first.

**Decision (asked Sean, he chose):** this workflow targets Vercel + Railway,
but ReEngrave's actual production path is the self-hosted VPS
(`scripts/deploy.sh` + `docker-compose.prod.yml` + Traefik) — Vercel/Railway
were never the real deploy target. Rather than wire up the missing secrets,
**disabled the workflow's automatic trigger** (`on: push` → `on:
workflow_dispatch`, manual-only) so it stops failing loudly on every push,
while fixing the Docker context bug anyway so it isn't left broken if it's
ever triggered by hand or revisited later.

**Files touched:** `.github/workflows/deploy.yml`.

**Follow-up, not done here:** if Vercel/Railway deploys are ever wanted for
real, the four secrets above still need to be added under repo Settings →
Secrets and variables → Actions before a manual run would get past both
jobs.

---

## 2026-09-03 — Added standing docs: `PROJECT_BRIEF.md` and this file

Created per standing preference: CLAUDE.md, `PROJECT_BRIEF.md`, and
`version_memory.md` should all exist and be kept current after every commit.
`PROJECT_BRIEF.md` is the short "what is this project" overview;
CLAUDE.md remains the full technical/working reference; this file is the
running changelog.

---

*Earlier project history (OMR pipeline phases, benchmark results, the
theory layer, etc.) predates this file and is not backfilled here — see
[PROJECT_STATUS.md](PROJECT_STATUS.md) for the narrative history and
`git log` for the full commit record.*
