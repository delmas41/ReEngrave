# Status brief — labeling, movement starts, new editions, and the MXL-guided training system

**Date:** 2026-09-02 (evening). Written from the state of `main` at `6a17de7`.
**Purpose:** answer "where are we, what is mine to do, and how much of the
MXL-guided auto-label training system already exists". Findings are quoted from
the repo; nothing here is a new measurement.

---

## 1. What landed today (87 commits, 12 merges)

- [x] **Benchmark widened 3 → 11 works.** Headline now `0.1306 / 2745` (default, reader on) and `0.1399 / 2915` (`--no-direction-text`), both on `44a1745`. Boundary enforced by `accuracy_record.check()`; no figure crosses it.
- [x] **Direction text ON by default** (`4952005`). Worth −144 edits, stable across seven mains.
- [x] **Empty-measure export fix** — the eighth detected-then-dropped gap (`a907e41`, `f238ce9`). Neutral on engraved pages by construction; unit tests are the only guard.
- [x] **Nondeterminism isolated** to `contextual._labels_for_page` (`de09383`, `fc073f2`). Geometry is bit-identical with contextual off.
- [x] **Scan benchmark protocol bug** — `works.json` pinned the reader off while claiming defaults (`44a1745`).
- [x] **Hollow-notehead round 2 cut** — five 56-cell batches, five publishers, pass-mode configs (`fb4c500` … `54d19da`).
- [x] **Mahler 5 / Peters batch labeled** by Sean — 49 boxes, 55/56 cells (`52e9945`).
- [x] **Round-1 hollow batch landed as `v7`** — 24 cells / 28 boxes; 116 of 117 model pre-labels were false (`fa9853a`).
- [x] **Annotate UI single-symbol pass mode** + `inspected_passes` coverage stamp (`eb3530c`, `2b900c4`).
- [x] **Labeling survey + scope decision** — PROVE-IT-FIRST (`2a8bf79`, `benchmarks/omr-labeling-survey-2026-09/SURVEY_DESIGN.md`).

⚠️ `docs/next-steps-omr-2026-09-02.md` §6 still lists "does the 8-work corpus join the benchmark" and "direction text default-on" as open decisions. Both were decided and landed today. Treat that section as stale on those two rows.

---

## 2. Your labeling queue (hollow noteheads, round 2)

| batch | edition | cells | expected boxes | state |
|---|---|--:|--:|---|
| `benchmarks/omr-labeling-hollow2-2026-09-peters-mahler5` | Peters 3087b | 56 | 49 drawn | ✅ done, committed |
| `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1` | Breitkopf SW | 56 | ~23 | ⬜ not started |
| `benchmarks/omr-labeling-hollow2-2026-09-eulenburg-scheherazade` | Eulenburg 2957 | 56 | ~56 | ⬜ not started |
| `benchmarks/omr-labeling-hollow2-2026-09-litolff-hires` | Litolff 1870, 4× res | 56 | ~42 | ⬜ not started |
| `benchmarks/omr-labeling-hollow2-2026-09-simrock-dvorak9` | Simrock 1894 | 56 | ~19 | ⬜ not started |

Remaining: **224 cells, ~140 boxes, four sittings.** Each batch already carries a `batch_config.json`, so a click places a measured, staff-snapped box and no picker opens.

```bash
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1   # → http://127.0.0.1:5050
```

After the four batches, per the scope decision:

- [ ] Convert the four batches → `v8` with `verdicts_to_yolo_labels` (`--dry-run` first).
- [ ] One training run on v1–v4 + v7 + v8, **gated on `tools/omr/training/wtc_forgetting_eval.py`**.
- [ ] Only if the gate holds: edit `data/user-labeled/catalog-versions.txt` (open decision #13 in PROJECT_STATUS.md — v5/v6/v7 are held out on purpose today).
- [ ] Only then Option B: hollow noteheads on Durand / Universal / Jurgenson / Novello, plus one grace-note and one small-dynamics batch (~600 cells). Selector scripts for those rows do not exist yet.

**Not planned, on purpose:** time-signature digits and accidentals — geometry/template readers already close them (`SURVEY_DESIGN.md` §2).

---

## 3. Movement starts — what you need to supply, and where

The only place a PDF page is tied to a reference measure window is
`benchmarks/omr-scan-e2e-2026-09/works.json`. `catalog.json` records a page
*count* per edition and nothing about where a movement begins.

Each row needs, hand-read from the page (`SCOPING.md`: "the page is the truth,
not the file — the runner must not infer it from the OMR"):

```json
"page":   { "pdf_page_index": 1, "printed_page": 1, "n_systems": 1, "n_staves": 12 },
"window": { "first_ref_measure": 1, "last_ref_measure": 8, "how_established": "..." }
```

| work | edition (IMSLP) | state |
|---|---|---|
| beethoven-sym5-mvt1 | 984073 and 575951 | ✅ |
| dvorak-sym9-mvt1 | — | ✅ |
| brahms-sym1-mvt1 | — | ✅ |
| mahler-sym5-mvt1 | — | ✅ (no hand-read staff map yet) |
| bach-brandenburg3-mvt1 | 468678 | ⬜ system 2 count TBD |
| mozart--symphony-41 | 984556 | ⬜ system-1 count ~11 unconfirmed, page total not established |
| mozart--symphony-40 | 984555 | ⬜ extra staves above the main system, mapping unresolved |
| brahms--symphony-2 | 23103 | ⬜ "add later" |
| tchaikovsky--symphony-6 | 922722 | ⬜ "add later" |
| tchaikovsky--symphony-4 | 377460 | ⬜ "add later" |

**This is the same join the training system in §5 needs.** A page↔measure
window is what lets truth notes be attached to the right measure cells, so the
rows are not benchmark-only bookkeeping. Once §5 exists, a per-page
`movement_starts` field on the edition catalog entry (page index of each
movement's first page) would let the window be *derived* for every later page;
today only the hand-verified per-page row exists.

---

## 4. Today's downloads are not in the catalog yet

`data/score-library/catalog.json` has one commit, dated 2026-09-01, and no
entry with `added` = 2026-09-02. Whatever was downloaded today sits in the
gitignored `library/` on your machine and has not been ingested. Seven works
currently hold two editions (Beethoven 5, Brahms 1, Handel Messiah, Mozart 25,
Mozart 41, Schumann PC, Tchaikovsky 6).

On the main checkout:

```bash
python3 -m tools.library.ingest imslp ~/Downloads/IMSLP*.pdf   # provenance from the wiki API
python3 -m tools.library.ingest catalog                        # rebuild catalog.json from sidecars
python3 -m tools.library.ingest verify                         # present / missing / checksum-changed
git add data/score-library/catalog.json && git commit
```

Read the "five things that will bite" section of `data/score-library/README.md`
first: variant editions of held works are exactly where case-sensitive names,
redirect stubs and mirror HTML installed the wrong file before.

---

## 5. The MXL-guided auto-label training system — what exists, what doesn't

### The reframing that matters

The closed result — **F1 0.064, "MXL→bounding-box path is closed"** — was
about *placing truth notes in pixel space* (homography + ink snapping; the
orphaned `summary.json` files under `benchmarks/omr-mxl-autolabel/output/`
still carry `snap_to_ink` and `homography_failures` fields). ⚠️ The write-up
`benchmarks/omr-mxl-autolabel/FINDINGS.md` is cited by path in CLAUDE.md,
PROJECT_STATUS.md and the real-scan notes and **has never been committed** —
no script that produced those outputs exists on any branch either. Only the
number survives.

The system described today runs the other direction: **the detector places
the boxes; the MXL confirms or relabels them.** Detections already resolve to a
per-measure note sequence (pitch, duration); the truth measure is a note
sequence too; align the two sequences and every match becomes a verdict on a
box that already has coordinates. Nothing is placed in pixel space. That is
not the closed path, and most of its parts are already built.

### Inventory

| component | exists | where | gap |
|---|---|---|---|
| Candidate boxes with class + confidence | ✅ | `transcribe.py`, `yolo_detector.py` | — |
| Cells cut per measure, served to the UI | ✅ | `annotate/select_cells_orchestral.py`, `run_yolo.py` | — |
| Page ↔ reference measure window | 🟡 hand rows only | `omr-scan-e2e-2026-09/works.json` (5 rows) | needs your rows (§3); derive later pages from movement starts |
| Part ↔ staff join | 🟡 | `dossier.join_parts_to_slots` (abstains unless counts match), contextual part naming | condensed/divisi pages abstain — those cells go to the human queue |
| Note-sequence alignment truth ↔ prediction | ✅ built 2026-09-02 evening | `training/measure_align.py` (per measure, returns the detection each truth note matched); `training/musicxml_truth.py` (stdlib reader) | — |
| Verdict schema with a pending state | ✅ | `annotate/server.py` (`TP / FP / WRONG_CATEGORY / WRONG_BBOX / unsure`, `verdict: None` = pending, `n_pending` per cell) | — |
| Proximity matcher between detection sets | ✅ | `annotate/port_verdicts_to_yolo.py` | the pattern to reuse for truth↔detection |
| **Verdict pre-fill writer** | ✅ built 2026-09-02 evening | `training/mxl_verdicts.py` | measure on a real batch (`--score`) |
| Human queue in the UI | ✅ built 2026-09-02 evening | annotate server `prefill/`, queue order, hints layer (`h`) | — |
| Verdicts → YOLO labels | ✅ | `training/verdicts_to_yolo_labels.py` | — |
| Forgetting gate | ✅ | `training/wtc_forgetting_eval.py` | — |
| Rendered truth with exact coordinates | ❌ | Verovio SVG is rendered in `claude_vision.py` but never parsed | optional later: element-id boxes for engraved pages |
| Scan ↔ engraved image registration | ❌ | — | not needed on this design |

### What has to be built (in order) — steps 1–3 landed the same evening; step 4 is next

1. **`tools/omr/training/mxl_verdicts.py`** — given a transcription JSON, the
   reference MXL, and a page↔measure window: per (staff, measure) align the
   resolved events to the truth measure, and write `.verdict.json` files the
   existing UI and converter read unchanged. Every cell gets `n_pending` and a
   list of missing-note hints. Abstains (whole cell pending) where the part
   join abstains or the measure count disagrees.
2. **Per-measure aligner returning detection ids** — a small extension of
   `end_to_end_eval.align()`; the resolver already keeps the notehead
   detection under each event.
3. **Queue mode in the annotate UI** — order cells by pending count, show the
   hints as ghost markers. Small; the pass-mode work touched the same code.
4. **Measure it before trusting it** on the one batch that already has human
   truth: the Mahler 5 / Peters hollow batch (49 boxes). Pre-fill precision on
   those 56 cells is the number that says whether the auto-verdicts can be
   admitted without review or only with it.
5. Then the loop: ingest → transcribe → pre-fill → human clears the queue →
   convert → gated training run.

Estimated size: three new modules plus tests, one to two sessions, all of it
buildable and unit-testable on authored fixtures from a remote session. Running
it on real scans needs the machine that holds `library/`, the weights and the
two venvs.

### Two doctrines to keep in view

- "Detector fine-tuning on the sparse hand-labels is a proven dead end … the
  hand-labels are EVAL data" (`docs/followup-prompts-deterministic-and-training.md`).
  The failure was *sparse* labels shifting the density prior. The MXL-guided
  route produces **dense** labels — every note in a measure is decided — which
  is the property that dead end lacked. It still has to pass the gate.
- The engraved benchmark is byte-identical under all of this; it is a training-data
  system, not an inference change, and the OMR-NED figure will not move until a
  new checkpoint is admitted.

---

## 6. Open decisions (yours)

- [ ] Catalog admission of v5/v6/v7 (+v8) — after the gated run, not before.
- [ ] Whether pre-filled TP verdicts need a human glance or can be admitted on precision alone — decide after step 4 above.
- [ ] `claude/magical-bhabha` port (web-app measure patching) — parked until web-app time.
- [ ] Archive `claude/omr-dossier-verification-layer-eaf6d0` (superseded on main, per `docs/branch-assessments-2026-09-02.md`).

## 7. Proposed order of work

| # | who | item |
|--:|---|---|
| 1 | Sean (local) | ingest today's downloads, commit `catalog.json` |
| 2 | Sean (local) | four hollow batches, one sitting each |
| 3 | this session | ✅ built §5 steps 1–3 on `claude/score-labeling-training-system-iech0i`, 43 fixture tests |
| 4 | Sean (local) | `works.json` rows for the six works in §3 |
| 5 | Sean (local) | run the pre-fill on the Mahler batch, report precision (§5 step 4) |
| 6 | Sean (GPU) | gated training run; then the catalog decision |
