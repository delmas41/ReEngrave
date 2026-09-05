# Census — library pages whose printed lineup CHANGES between systems

**2026-09-05, branch `claude/structure-rnd-2026-09`. NO PIPELINE CODE TOUCHED —
`tools/` and `backend/` were read-only for this work. NO GROUND TRUTH IS AN
INPUT: no `works.json`, no dossier, no reference encoding selected or ranked a
single page.**

Every structural hypothesis in this workstream has so far been decided on
**n = 2 patterns, one of which is a re-print rather than a replication** (the two
Litolff Beethoven 5 scans are the same engraving). This census asks how many
more pages the library holds that could carry the next decision, and it spends
no human time to ask.

> ## ⚠️ HEADLINE, STATED BEFORE THE NUMBERS
>
> **The census succeeded for the unequal-count case and FAILED for the
> equal-count case.**
>
> * **Screen 1 (differing staff counts) passed validation cleanly** — 3 TP,
>   0 FP, 5 TN on the pre-registered gate — and the wide sweep finds
>   **246 tier-A candidate pages in 1,135 pages across 83 editions and 39
>   publishers.** Extrapolated over the 27,718-page library that is thousands,
>   not the 12–15 hoped for. This half of the answer is *better* than hoped.
> * **Screen 2 (equal counts, differing clef sequence) FAILED.** It fired on
>   **4 of the 5 pre-registered negative controls**, every firing with
>   `clef_source == "detector"` on **both** sides, so no source-based tier can
>   separate a lineup change from a clef misread. Its precision on the
>   equal-count subset of the gate is **2/6 = 0.33**.
> * That matters more than the first bullet, because **the highest-value known
>   page — Beethoven 5 p.4 — is an equal-count page.** The census therefore
>   *cannot* tell you where the other Beethoven-5-p.4-shaped pages are. It can
>   only tell you where the tacet-suppression pages are, and those were never
>   the scarce thing.

---

## 1. The pre-registered validation, with actual results

Run **before** the wide sweep, on the 20-row reconciliation gate at
`/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures/`
(suffix `.reconciliation.omr.json`). The probe **asserts 20 files and 396
staves** before it screens anything — the main checkout's stale 11-row
`..graft09` set has been mistaken for this gate three times, and an assertion is
cheaper than a fourth.

```bash
python3 benchmarks/omr-structure-rnd-2026-09/probe_lineup_change.py --validate \
    --out benchmarks/omr-structure-rnd-2026-09/lineup-validation.json
```

| row | must fire? | via | actual: screen 1 | screen 2 | screen 3 | counts | verdict |
|---|---|---|---|---|---|---|---|
| `beethoven-sym5-mvt1-984073-p4` | **YES** | clefs | – | **fires** | fires | 11, 11 | **PASS** |
| `beethoven-sym5-mvt1-575951-p4` | **YES** | clefs | – | **fires** | fires | 11, 11 | **PASS** |
| `beethoven-sym5-mvt1-984073-p3` | **YES** | counts | **fires** | – | fires | 11, 8 | **PASS** |
| `beethoven-sym5-mvt1-575951-p3` | **YES** | counts | **fires** | – | fires | 11, 8 | **PASS** |
| `brahms-sym1-mvt1-317803-p2` | **YES** | counts | **fires** | – | fires | 14, 13 | **PASS** |
| `brahms-sym1-mvt1-317803-p3` | no | — | – | **fires** | fires | 14, 14 | **FAIL** (screen 2) |
| `brahms-sym1-mvt1-317803-p4` | no | — | – | **fires** | fires | 14, 14 | **FAIL** (screen 2) |
| `beethoven-sym5-mvt1-984073-p2` | no | — | – | – | – | 11, 11 | **PASS** |
| `beethoven-sym5-mvt1-575951-p2` | no | — | – | **fires** | – | 11, 11 | **FAIL** (screen 2) |
| `dvorak-sym9-mvt1-405834-p7` | no | — | – | **fires** | fires | 15, 15 | **FAIL** (screen 2) |

**6 of 10 rows pass. All four failures are screen 2, and all four are false
positives on the negative controls.**

Screen 3 is measured from a fresh phase-1 run at 300 dpi
(`lineup-validation-phase1.json`) because the fixture JSON does not carry
`Staff.group_index`.

### 1.1 Screen 1 — differing staff counts. **Clean.**

|  | fires | silent |
|---|--:|--:|
| lineup really changes | **3** | 2 |
| lineup identical | **0** | **5** |

The two false negatives are by construction — both p4 rows print 11 staves in
each system, so screen 1 is definitionally blind to them; that is precisely why
screen 2 was specified. **Precision 3/3 = 1.000** on this gate. Five negatives
is a small denominator and this cannot be read as "screen 1 has no false
positives"; it can be read as "screen 1 produced none here."

### 1.2 Screen 2 — equal counts, differing clef sequence. **FAILED.**

|  | fires | silent |
|---|--:|--:|
| lineup really changes | 2 | 0 |
| lineup identical | **4** | 1 |

**Measured false-positive rate on the negative controls: 4/5 = 0.80.**
Restricted to the seven equal-count rows (2 positive, 5 negative), where screen
2 is the only pre-registered screen that can speak: **precision 2/6 = 0.333.**

⚠️ **The tier that was supposed to save it does not exist.** The probe records
each differing slot's `clef_source` on both sides, on the theory that a
difference resting on a positional default is not evidence. Every single
differing slot on every false positive reads `['detector', 'detector']`:

```
brahms-sym1-mvt1-317803-p3   slot 4  ['treble','bass'] ['detector','detector']
brahms-sym1-mvt1-317803-p3   slot 8  ['treble','bass'] ['detector','detector']
brahms-sym1-mvt1-317803-p3   slot 12 ['bass','tenor']  ['detector','detector']
brahms-sym1-mvt1-317803-p4   slot 3  ['bass','tenor']  ['detector','detector']
beethoven-sym5-mvt1-575951-p2 slot 9 ['treble','alto'] ['detector','detector']
dvorak-sym9-mvt1-405834-p7   slot 3  ['treble','bass'] ['detector','detector']
```

Over all 396 staves of the gate the source distribution is `detector` 304,
`detector_header` 51, `None` 32, `cv_locator` 7, `slot_continuity` 2 — so
"read by the detector" is the ordinary case and carries no information about
whether the reading is right. **There is no signal in the transcription that
separates a real lineup change from a clef misread**, and the pre-registered
tiering (`B` for strong, `C` for weak) collapses: every firing is `B`.

Two further observations, both against screen 2:

* **The number of differing slots does not separate either.** The true positive
  `984073-p4` differs at **1** slot; the false positive `575951-p2` also differs
  at 1. The other true positive (`575951-p4`, the same page in the other scan of
  the *same engraving*) differs at **5**.
* **The two scans of the same page do not agree with each other.** `984073-p4`
  fires at slot 9 (`bass` vs `alto`); `575951-p4` fires at slots 1, 6, 7, 8, 9
  with a different pattern. A screen whose output is not reproducible across two
  scans of one engraving is not measuring the engraving.

⚠️ **An alternative screen was tried and is also blind: the INSTRUMENT
sequence.** The fixtures carry a margin-label instrument per staff, an
independent reader. On both p4 rows the instrument sequence is **identical
between the two systems** (label coverage 6/11 and 7/11), so a screen on it
fires on neither of the two pages screen 2 exists for. Recorded here so nobody
re-tries it. It was tried *after* seeing the screen-2 failure and is therefore
exploratory, not validated.

### 1.3 Screen 3 — differing bracket-block shape. **Ranking only, as declared.**

|  | fires | silent |
|---|--:|--:|
| lineup really changes | **5** | 0 |
| lineup identical | **3** | 2 |

Recall 5/5 — it is the **only** screen that reaches both p4 rows — at precision
5/8 = 0.625. On the equal-count subset alone: TP 2, FP 3, precision 0.400,
marginally better than screen 2 and still unusable as truth. The two are not
independent: conjoining them (screen 2 **and** screen 3) gives TP 2 / FP 3, no
better than screen 3 alone. The pre-registered warning holds exactly — on
`brahms-p4` it reads `[0×9, 1×5]` against `[0×14]` for two identical systems.

**No threshold was tuned to make any of this pass.** The screens are as
specified; the failures are reported as they fell.

---

## 2. The sampling frame

**Universe.** `data/score-library/catalog.json` parsed with `json` (never a
regex): 1,980 entries, **235 of kind `edition`, all 235 present on disk** under
`library/` (27,718 catalogued pages, 39 distinct publishers).

**Cost model.** OMR **phase 1 only** — render, Sauvola binarize, deskew,
`detect_staves`, `system_grouping`. No YOLO. Measured at ~0.7 s/page on light
pages; the observed average over the run is far worse because large 300-dpi
scans reach 1.5–5 GB resident and the machine (shared with other agents) begins
to swap. That, not the algorithm, is what bounded the sweep.

**Frame.** Every present edition, **up to 14 pages per edition**, spaced evenly
across the PDF and **skipping page 1** (title / front matter). Four worker
processes over disjoint edition shards (`--shard i/4`), each walking the catalog
in order.

**What was actually reached, and its bias.** The run was stopped at the CPU
budget with **1,135 pages measured over 83 of 235 editions, 0 errors.** Because
every shard walks the catalog in the same (composer-alphabetical) order, the
coverage is **front-loaded on the alphabet**: Bach through roughly Dvořák/Dukas
is well covered, and the second half of the alphabet — Mahler, Mozart,
Tchaikovsky, Wagner — is **not sampled at all**. Every rate below is a rate over
that 83-edition sample, and the per-publisher table must be read as coverage,
not as a property of the publisher.

**Screenability.** A page enters the rate only if it is screenable at all:

| bucket | pages | why |
|---|--:|---|
| screenable | **504** | ≥ 2 systems, widest system ≥ 6 staves |
| abstain — one system | 504 | nothing to compare between systems |
| abstain — not a conductor's page | 70 | widest system < 6 staves (piano score, part, front matter) |
| abstain — no staves | 57 | blank page or phase-1 failure |

```bash
python3 benchmarks/omr-structure-rnd-2026-09/sweep_lineup_change.py \
    --out benchmarks/omr-structure-rnd-2026-09/lineup-sweep-s0.jsonl \
    --per-edition 14 --dpi 300 --shard 0/4 --time-budget-s 4800
python3 benchmarks/omr-structure-rnd-2026-09/summarize_lineup_census.py \
    --jsonl benchmarks/omr-structure-rnd-2026-09/lineup-sweep.jsonl \
    --out  benchmarks/omr-structure-rnd-2026-09/lineup-census.json
```

**Screen 2 is deliberately NOT in the wide sweep.** It needs the YOLO detector
and header reading (~30–60 s/page against ~1 s), and it failed validation. A
wide screen-2 queue would be a queue of clef misreads bought at 40× the price.

---

## 3. Results, and per-publisher counts

**1,135 pages / 83 editions / 39 publishers / 504 screenable.**

| tier | what fired | pages | share of screenable |
|---|---|--:|--:|
| **A** | screen 1 — staff counts differ | **246** | **48.8%** |
| **D** | screen 3 only — block shape differs, counts equal | 60 | 11.9% |
| none | nothing fired | 159 | 31.5% |
| doubtful | screen 1 fired but the page looks like a phase-1 failure | 39 | 7.7% |
| abstain | not screenable | 631 | — |

Tier-A size of the change, which is the ranking signal:

| |max − min| staves | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | ≥9 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| pages | **81** | 42 | 49 | 22 | 21 | 10 | 9 | 7 | 5 |

⚠️ **A difference of 8 or more staves between two systems of one conductor's
page is not a plausible tacet suppression.** Those 12 pages are far likelier to
be phase-1 over-splitting than a printed lineup change, and the `doubtful`
guard (a system of ≤ 3 beside one of ≥ 6) does not catch them. They sit at the
bottom of the ranked queue for that reason and should not be hand-read first.

### Per publisher

Read this as **coverage crossed with convention**, never as a publisher's
property — 152 of the sample's Simrock pages produced 113 single-system
abstentions because Simrock lays out one system per page on the works sampled,
which is a fact about the sampled works as much as about the house.

| publisher | pages | tier A | tier D | doubtful | abstain |
|---|--:|--:|--:|--:|--:|
| Henry Litolff's Verlag | 140 | **70** | 13 | 1 | 20 |
| Breitkopf & Härtel (Beethoven's Werke) | 56 | **31** | 4 | 8 | 1 |
| Breitkopf & Härtel (Brahms Sämtliche Werke) | 84 | **30** | 1 | 3 | 32 |
| Co-issue with Universal Edition (Philharmonia) | 42 | 17 | 2 | 1 | 19 |
| N. Simrock | 152 | 11 | 7 | 5 | **113** |
| Ernst Eulenburg | 70 | 11 | 0 | 3 | 55 |
| C.F. Peters | 48 | 8 | 4 | 1 | 12 |
| Universal Edition | 14 | 8 | 1 | 0 | 0 |
| Chausson "Catalog Part.B. 2051." | 14 | 8 | 0 | 1 | 5 |
| BerliozComplete | 28 | 7 | 0 | 1 | 18 |
| BrucknerAGA | 14 | 7 | 0 | 0 | 7 |
| Bote & Bock | 14 | 7 | 0 | 0 | 6 |
| Wiener Philharmonischer Verlag | 14 | 6 | 0 | 0 | 7 |
| Durand & Fils | 28 | 3 | 0 | 0 | 24 |
| Edition Eulenburg | 14 | 3 | 0 | 0 | 3 |
| Enoch & Cie. | 14 | 3 | 0 | 0 | 11 |
| Eulenburg | 28 | 2 | 0 | **9** | 17 |
| D. Rahter | 14 | 2 | 0 | 3 | 8 |
| Edition Peters Nr.4412 | 14 | 2 | **7** | 0 | 0 |
| Edition Peters Nr.4415 | 14 | 1 | **9** | 1 | 1 |
| Arthur P. Schmidt · Ricordi · Edition Peters | 14 each | 2 each | 0 | 0/1 | 8–12 |
| Novello & Co. · Novello and Co. · Enoch | 14–28 | 1 each | 0–2 | 0 | 11–27 |
| Breitkopf und Härtel | 42 | 0 | 5 | 0 | 31 |
| Breitkopf & Härtels Partitur-Bibliothek (2343) | 14 | 0 | 5 | 0 | 5 |
| Novello · Schott · Durand et Cie. · Schirmer · BachComplete · Knute Snortum · V. Bessel · Pierre-Antoine Renioult · E. Fromont · John S. Shaw · Hamelle | 14 each | 0 | 0 | 0–1 | 2–14 |

The five houses the prompt named all appear. Three observations that survive the
coverage caveat:

* **Litolff and the two Breitkopf complete-works series carry the queue** —
  131 of the 246 tier-A pages. They are also the best-sampled editions, so this
  is at least partly coverage.
* **Simrock is the abstention house in this sample**: 74% of its pages print a
  single system and can never be screened by *any* between-systems screen. If
  the workstream wants Simrock evidence it has to come from a cross-*page*
  comparison, not a cross-system one.
* **The two Edition Peters Bach volumes are the tier-D house** — 16 of the 60
  tier-D pages, from 28 sampled pages. On a Brandenburg the systems have equal
  counts and the block reading moves between them, which is exactly the shape
  the pre-registered warning says is noise-dominated.

---

## 4. The ranked candidate queue

`lineup-census.json` holds **306 ranked rows** (246 tier A, 60 tier D), each
with edition path, 0-based and 1-based page number, publisher, work id, staff
counts and block shapes. Tier A is ordered by the *relative* size of the change,
smallest first, because a 14→13 suppression is the plausible tacet and a 15→4 is
a phase-1 collapse.

Top of the queue (tier A, |max − min| = 1):

| counts | page | publisher | edition |
|---|--:|---|---|
| 14, 13 | 2 | Breitkopf (Brahms SW) | `brahms--symphony-1-op68--…--imslp516790.pdf` |
| 14, 13 | 20 | Breitkopf (Brahms SW) | `brahms--symphony-1-op68--…--imslp317803.pdf` |
| 13, 14 | 14 | Breitkopf (Brahms SW) | `brahms--symphony-1-op68--…--imslp516790.pdf` |
| 12, 13 | 9 | Breitkopf (Brahms SW) | `brahms--symphony-4-op98--…--imslp…pdf` |
| 13, 12 | 39 | N. Simrock | `dvorak--cello-concerto-op104--simrock-1896--…pdf` |
| 13, 12 | 69 | N. Simrock | `dvorak--symphony-7-op70--simrock-1885--…pdf` |
| 13, 12 | 80 | Breitkopf (Brahms SW) | `brahms--symphony-3-op90--…pdf` |
| 11, 12 | 51, 76 | Breitkopf (Beethoven's Werke) | `beethoven--piano-concerto-5-op73--…pdf` |
| 12, 11 | 53 | Litolff | `beethoven--symphony-4-op60--…--imslp504078.pdf` |
| 12, 11 | 14 | Litolff | `beethoven--symphony-5-op67--…pdf` |
| 11, 12 | 5 | BerliozComplete | `berlioz--le-carnaval-romain-h-95--…pdf` |
| 11, 12 | 7 | Durand & Fils | `dukas--l-apprenti-sorcier--…--imslp6574.pdf` |
| 11, 12 | 10 | Edition Peters Nr.4412 | `bach--brandenburg-concerto-3-…pdf` |

**An independent confirmation the sweep did not know it was making:** the
14-page-per-edition plan happened to land on
`brahms--symphony-1-op68--…--imslp317803.pdf` **page 2** — the pre-registered
positive `brahms-sym1-mvt1-317803-p2` — and tiered it **A** at `[14, 13]`,
matching the fixture exactly. The sweep re-found a known-informative page from
the PDF alone, with no fixture and no truth in the loop.

Editions with the most tier-A pages in the sample (candidates concentrate, so a
single edition can be opened once and read several times):

| tier-A pages | edition |
|--:|---|
| 11 | `beethoven--symphony-4-op60--litolff-1870--imslp504078.pdf` |
| 11 | `beethoven--piano-concerto-3-op37--breitkopf (Beethoven's Werke)` |
| 11 | `beethoven--violin-concerto-op61--breitkopf (Beethoven's Werke)` |
| 10 | `beethoven--symphony-3-op55--litolff-1870--imslp504077.pdf` |
| 9 | `bruckner--symphony-1-wab-101--co-issue-with-universal` |
| 8 | `bizet--symphony-in-c-major--edition-1935` · `beethoven--symphony-1-op21--litolff` · `brahms--symphony-1-op68--imslp516790` · `brahms--piano-concerto-1-op15` · `beethoven--symphony-6-op68--litolff` · `chausson--poeme-op25` |

---

## 5. Abstentions, each with its reason

Nothing was imputed. Every page that could not be screened is counted with its
reason, and the reasons are in the JSONL per page.

| reason | pages | what it means |
|---|--:|---|
| fewer than two systems | 504 | the page prints one system; a between-systems screen is silent by construction, not by failure |
| widest system < 6 staves | 70 | not a conductor's page — piano reduction, single part, front matter |
| no staves detected | 57 | blank page, plate, or a phase-1 failure; not distinguished, and not counted as either |
| structurally doubtful | 39 | screen 1 fired but a system of ≤ 3 staves sits beside one of ≥ 6 — the known Bach p1 shape. **Flagged, not counted as a lineup change**, e.g. `[2, 19]`, `[2, 2, 13]`, `[1, 1, 10, 8]` |
| pipeline error | **0** | no page raised |

Screen 3 abstains silently wherever a system carries no block information; on
this corpus it always did carry it.

Editions not reached at all: **152 of 235**, alphabetically the second half.
They are not evidence of anything and are not in any denominator.

---

## 6. How this census could have produced a falsely encouraging number

Stated as the fourth deliverable, and it is the section to read second.

**(a) The 48.8% tier-A rate rests on a 5-negative validation.** Screen 1's
precision is 3/3 with 5 true negatives. That is a clean result and a *tiny*
denominator. If screen 1's real false-positive rate on library pages were 20%,
the gate had roughly a one-in-three chance of showing zero. **The 246 is a
candidate count, not a count of confirmed lineup changes**, and nothing in this
census promotes it past candidate.

**(b) Screen 1 measures a staff count, which is exactly the quantity that moved
between DPIs.** Re-measuring the 20-row gate through the cheap phase-1 path at
300 dpi against its own 600 dpi fixtures: **16 of 20 rows identical**, and the
four that differ are the dense Peters Mahler pages, which read 17 / 13 / 18 / 17
staves at 600 dpi and 19 / 15 / 20 / 21 at 300. All four are single-system pages
so no screen verdict changed — but a 2-staff disagreement on a two-system page
would manufacture a tier-A page out of nothing. **This was the census's biggest
self-doubt and it was controlled for: §6.1 finds screen-1 verdict agreement
0.983 and tier-A persistence 20/20 across a DPI change.** The residual risk is
~3% spurious tier-A, not a headline change.

**(c) The alphabet bias is a real confound with the publisher table.** Litolff
has 70 tier-A pages partly because ten Litolff Beethoven volumes sit early in
the catalog. Mahler, Mozart, Tchaikovsky and Wagner are absent. A reader who
takes the per-publisher table as a statement about publishers will be wrong.

**(d) The two Litolff Beethoven scans are still a re-print, not a replication,
and the sweep sampled both.** `imslp575951` and `imslp984073` are the same
engraving. Any page counted twice across them is one piece of evidence, not two
— the exact error this workstream is trying to stop making. Their page
numbering differs by one in places (different front matter), so they are not
de-duplicated in the 246 and **the queue should be de-duplicated by engraving
before anyone plans hand-reading time.** This is also a free replication control
nobody has run: the same page in two scans should get the same verdict, and on
screen 2 it demonstrably does not (§1.2).

**(e) Screen 3's 5/5 recall on the gate is the most seductive number here and
the least trustworthy.** It is 5 positives, three of which screen 1 already
caught, and its precision is 0.625 overall and 0.400 where it would actually be
used. It is in the deliverable as a tier-D ranking hint and nothing else.

**(f) `doubtful` is a shape heuristic, not a diagnosis.** It catches ≤3-beside-≥6
and nothing else, so the 12 tier-A pages differing by ≥ 9 staves are almost
certainly phase-1 failures counted as candidates.

**(g) The screen-2 negative could in principle be an artefact of one gate.**
Five negative controls, three works, two publishers. The finding is that screen
2 fires where nothing changed; a larger negative set could only make that worse,
but it is honest to say the 0.80 has a ±0.2-ish width at n=5.

### 6.1 DPI-stability control — **screen 1 survives it**

A stratified random sample (seed 20260905) of **60 swept pages, 20 from each of
tiers A / none / D**, re-measured end to end at a different rasterization:

```bash
python3 benchmarks/omr-structure-rnd-2026-09/control_dpi_stability.py \
    --jsonl benchmarks/omr-structure-rnd-2026-09/lineup-sweep.jsonl \
    --out   benchmarks/omr-structure-rnd-2026-09/lineup-dpi-control.json \
    --n-per-tier 20 --dpi 450 --time-budget-s 2400
```

| | measured |
|---|--:|
| pages re-measured at 450 dpi | **60 / 60**, 0 errors |
| staff counts **byte-identical** to the 300 dpi run | 55 / 60 = **0.917** |
| screen-1 **verdict** agrees | 59 / 60 = **0.983** |
| tier-A pages that **still fire** at 450 dpi | **20 / 20 = 1.000** |

**The 246 is not a rendering artefact.** Every tier-A page in the sample fires
again at a 1.5× rasterization, and 18 of the 20 reproduce their exact counts.
The two that shift keep the difference (`[13,10] → [13,11]`, `[9,13] → [9,14]`)
— the count moved, the verdict did not.

⚠️ **The error runs the other way, and it is real but small.** One of the 20
`none` pages read `[8, 8]` at 300 dpi and `[7, 8]` at 450 — i.e. a *different*
DPI would have manufactured a tier-A page there. At 1/20 on the equal-count
population, the 159 `none` pages in the sweep imply roughly **8 spurious tier-A
pages had the sweep been run at 450 dpi instead** — against 246, a ~3%
contamination, not a headline-changing one.

⚠️ **Two tier-D pages collapsed outright** at 450 dpi: `[8,8,8] → []` (no staves
found) and `[12,12] → [9]` (two systems merged into one). Tier D already carried
the strongest health warning; this is a second, independent reason not to trust
it.

⚠️ **This control is 450 dpi, not the fixtures' 600.** A 600 dpi run was
attempted first and had to be abandoned — at 4× the pixels the workers reached
5 GB resident on a machine shared with other agents and stalled inside single
pages. 450 dpi tests the same thing (does the verdict move when the raster
moves) at a smaller step, so it is a **weaker** test than 600 would have been,
and the 1.000 persistence should be read with that discount.

---

## 7. What this means for the workstream

1. **The unequal-count case is not evidence-limited.** The library holds far
   more than the 12–15 pages hoped for — 246 candidates from a 4.1% page sample
   of a third of the editions, concentrated in editions that can be opened once
   and read several times. If a structural design can be separated by tacet
   suppression, the pages exist and the queue is in `lineup-census.json`.
2. **The equal-count case is still evidence-limited, and now measurably so.**
   The census cannot find Beethoven-5-p.4-shaped pages, because the only two
   screens that can see them have precision 0.33 and 0.40 on the gate. Finding
   more of them needs either a better clef reading or a human flipping through
   pages — this census has ruled out doing it from `clef` and from `instrument`,
   and shows `group_index` is not good enough either.
3. **De-duplicate by engraving before spending human time**, and drop the
   ≥ 9-staff-spread tail.
4. **The cheapest next measurement is the free replication control** — the two
   Litolff Beethoven 5 scans, page-aligned, screen-1 verdict compared. It costs
   ~10 minutes of CPU and would put a real number on screen 1's reproducibility,
   which is currently resting on 5 negatives.

---

## Files

| file | what it is |
|---|---|
| `probe_lineup_change.py` | the three screens + the pre-registered validation (asserts 20 files / 396 staves) |
| `sweep_lineup_change.py` | phase-1-only wide sweep, sharded, resumable, JSONL as it goes |
| `summarize_lineup_census.py` | per-publisher counts and the ranked queue |
| `control_dpi_stability.py` | §6.1 — is the screen-1 verdict a property of the page or the DPI |
| `lineup-validation.json` | §1 — screens 1 and 2 on the gate, per differing slot |
| `lineup-validation-phase1.json` | §1.3 — screen 3 on the gate, fresh phase-1 at 300 dpi |
| `lineup-sweep*.jsonl` | one record per page swept, with its abstention reason |
| `lineup-census.json` | tier counts, per-publisher table, the 306-row ranked queue |
| `lineup-dpi-control.json` | §6.1 results |
