# The technology ledger — what reads what, why, and what that cost

**Agent II, round 4, 2026-09-07.** Commissioned by Sean:

> *"Does the map clarify what was decided to be CV vs YOLO vs some other process
> like importing instrumentation from IMSLP?"*

**The honest answer is: partially.** [`docs/architecture-decision-map.md`](../../docs/architecture-decision-map.md)
names the technology per STAGE (§2's spine, §5's headings) and records the
boundary refusals — most importantly that CV and YOLO deliberately read
*different images*. What it does not have, because §11 cuts it, is a
consolidated account of **why a given recognition TARGET is read by the
mechanism it is read by, what else was tried, and what that lost.** That
reasoning exists and is scattered across CLAUDE.md and a dozen benchmark
FINDINGS **in the order it was discovered rather than by what it is about** —
which is exactly how a project re-enters a refuted approach.

This document is keyed on the **target**, not the stage.

⚠️ **No behaviour changed.** Everything is source read against the tree at
`350f0532` plus one new read-only probe
(`probe/probe_mechanism_attribution.py`, output in `out/`). Every quoted
docstring was opened; every reach figure is measured here or cited to the
benchmark that measured it.

⚠️ **Companion:** [`DECISION_TYPES.md`](DECISION_TYPES.md) asks what KIND of
decision each site makes. This asks what MECHANISM makes it. Where they meet is
flagged.

⚠️ **CORRECTED 2026-09-07 after verification** (29 claims checked, 25 exact).
Five corrections and three additions, each marked in place: the arc `drop`
example was **backwards** and is repaired in §4 with the refusal grounds
separated; the `staff`-class item was called "the cheapest untried comparison"
and is **UNREACHABLE-pending-a-new-regime**, re-classified in §2.1/§3/§6; §5's
method sentence, the bracket enumeration and the ScoreAug citation are fixed;
and §3.1 (**present ≠ usable**), §2.4.1 (**the reader is a generative decoder**),
§4.1 (**adoptions have scopes too**) and §6.1 (**the wall-clock regime
reconciliation**) are new.

---

## 0. How to read a row

| field | meaning |
|---|---|
| **READ BY** | the mechanism today, with `file:line` |
| **WHY** | the reason, with its measurement and where that measurement lives |
| **ALSO TRIED** | every alternative attempted |
| **VERDICT** | ⚠️ the load-bearing field — see §0.1 |
| **FACT COMES FROM** | **PAGE** · **CATALOGUE** (IMSLP) · **REFERENCE** (a MusicXML encoding) · **HUMAN** |
| **TIER** | the provenance tier, and what it forbids |

### 0.1 The three verdicts, and why the distinction is the point

| verdict | means | what to do with it |
|---|---|---|
| **REFUTED** | tried, MEASURED, lost — **with the scope of that measurement recorded** | a trap. Do not re-enter without reading the scope first |
| **UNTRIED** | nobody has run it | an opportunity |
| **UNREACHABLE** | built, sometimes measured, and **has no call site** — or depends on something that does not exist | ⚠️ **a merge or a wiring job, not a research programme** |

⚠️ **A refutation has a SCOPE and a row without one is a superstition.**
"Erasing staff lines before YOLO is dead" was measured on **two engraved works**;
"ScoreAug/Augraphy augmentation is dead" on **one comparison whose probe JSONs
were never committed**. Both conclusions are probably right and neither is
universal. §4 tabulates every refutation against its scope, and §6 names the
rows where the scope — or the rationale itself — is not recorded anywhere.

### 0.2 The provenance tiers, restated because two vocabularies share the word

| tier | source | a **decision** may use it? | a **measurement path** may use it? |
|---|---|---|---|
| `label` / `detector` / `cv_locator` … | this page's ink | yes | yes |
| `score_order` | position alone | ⚠️ **never for a clef** (`contextual.py:1380`) | yes |
| **`catalog`** | the IMSLP work/edition page | yes | **yes — this is the point of the tier** |
| **`encoding`** | a MusicXML file | yes | ⚠️ **NO** — it is the same substrate the benchmarks score against |
| **`page`** | a roster read off a raster | yes | ⚠️ **NO** — it is an OMR output |

`instrumentation.validate_fact:574` **refuses to write a fact whose
`source_kind` disagrees with its `source`**, verbatim: *"A fact with no
`source_kind` … is indistinguishable from an encoding-derived one downstream,
so it never gets written."* Enforced, not conventional.

---

## 1. ⚠️ THE ACQUISITION AXIS — where Sean's question actually points

The interesting cell is not "CV vs YOLO". It is **which facts we gave up reading
off the page at all, and why**. Four, each with a measured margin:

| fact | pushed off-page to | the margin that justified it | what it costs |
|---|---|---|---|
| **part roster** | **CATALOGUE** — the IMSLP work page's `InstrDetail`, `tools/library/instrumentation.py` | page-side roster acquisition *fails on a minority of documents*, and this is an **independent** escalation rather than a better reader. Measured over all 223 held works: **2419 of 2518 fragments parse (96.1%), 171 works (76.7%) parse completely, 4 parse nothing** | one MediaWiki query **per WORK, not per page** — 224 requests at 6 s = 25.4 min for the whole library, 0 failures. ⚠️ Never the download gate, which is JS-protected |
| **the meter, on a constant-meter work** | **REFERENCE** — `dossier.apply_meter:229` | *"for a constant-meter work it is simply what the meter IS, so a detected meter that disagrees with it is a misread"*. Measured on an engraved Beethoven 5 excerpt the detector read **4/4, 4/24 and 7/24 across a 2/4 movement** — two of those are not meters | ⚠️ tier `encoding`: a measurement path may not read it, which is why the scan gate runs dossier-free **by protocol**. Observed: meter source is `dossier` on **203 of 224 engraved staves** and on **0 of 193 scan staves** |
| **the clef, where the join is safe** | **REFERENCE** — dossier seeding | clef detection is the documented pipeline ceiling — 2% coverage on orchestral scans, and a fine-tune, ensemble voting and a CV locator have all failed to move it. Knowing the clef beats reading it: Beethoven recall .642 → .691, Brahms .206 → .253 | same tier restriction. Observed: `clef_source == "dossier"` on **10 of 224 engraved staves, 0 of 193 scan** |
| **which staff is which part** | **REFERENCE**, and only when it is safe | the forced part↔staff join measured **F1 0.064** (`dossier.py:22`, `:375`), so slot-level checks run **only when staff count equals part count** and abstain otherwise | an abstention on exactly the pages that need it most, which `dossier.py:425` says out loud |

⚠️ **The pattern across all four: the external source wins where the page-side
reader is not merely weak but STRUCTURALLY unable** — a scan whose clef glyphs
are outside the training distribution, a page that prints its meter once, a
document whose roster page is a different document. It does **not** win where the
page-side reader merely under-performs; nothing here replaces notehead reading,
which the page does well.

⚠️ **And the tier is what keeps it honest.** Three of the four are `encoding`,
so they are invisible to the scan gate by design. Only the roster is `catalog`,
and that is precisely why the roster may feed production decisions while the
dossier may not feed a measurement.

---

## 2. The ledger

### 2.1 Page structure

| target | READ BY | WHY | ALSO TRIED → VERDICT | FROM | TIER |
|---|---|---|---|---|---|
| **staff lines** | classical CV — `staff_detector._candidate_staff_rows:210`, `_group_into_staves:243` | nothing has coordinates without it; a five-line comb is geometry, not appearance | ⚠️ **the detector HAS a `staff` class, it fires freely — 1,150 scan / 1,579 engraved — and staff detection reads none of it.** ⚠️ **But this is NOT an available alternative: it is UNREACHABLE-pending-a-new-regime.** `detect_staves(page: PageImage)` takes a raster, imports nothing detector-related, and **runs before the detector exists** — the detector reads measure CELLS cut from `detect_staves`' own output. The class is not unconsulted at that moment; it has not been produced. Comparing them needs a **full-page detector pass and an inference regime that does not exist**, not an A/B | PAGE | — |
| **systems** | classical CV — `system_grouping.assign_systems:676`, connectivity | gap DISTANCE cannot separate them: within one Brahms system gaps run 17–237 px, within one Beethoven system 130–345 px, both wider than the gaps BETWEEN systems on a piano page | distance thresholds → **REFUTED**, scope: Brahms + Beethoven orchestral, and the mechanism is arithmetic (the ranges overlap), so the refutation generalises further than most here | PAGE | — |
| **bracket groups** | ⚠️ **INFERRED, not read** — `system_grouping._assign_groups:613`, counting systemic COLUMNS (`OMR_BRACKET_COLUMNS`, on) | **nothing detects a bracket**: `bracket` is *not in the 208-class space* — the three bracket-named classes are `tupletBracket`, `tupleBracket` (its coarse twin) and `ottavaBracket`, all different objects — verified by enumerating `catalog.yaml`'s 208 names | (a) crossing-PIXEL ratio → **REFUTED**, and sharply: 22/22 and 15/15 against print truth for the column rule vs **16/22 and 0/15** for pixels. (b) **READING the bracket** (`bracket_reader.py`, 390 lines) → **REFUTED AND UNREACHABLE at once**: measured 5/22 and 1/15, worse than inferring, *and* it has **zero call sites** (`ceadb7bb`, "Reading the bracket LOSES to inferring it") | PAGE | — |
| **barlines** | classical CV — `measure_extractor._detect_barlines_in_window:104` + a cross-staff vote | **`barline` is not in the 208-class space either** — the Phase 3.4 attempt to add 6 custom classes took F1 **98.8% → 79.3%** by catastrophic forgetting (`benchmarks/omr-phase3.4b/comparison-trained-v4.md:12`), diagnosed there as ultralytics re-initialising the head on an `nc` change with 49 train images | teaching YOLO the class → **REFUTED**, scope: one training run, 49 images, and the mechanism is documented (`nc` expansion re-inits the head), so the recipe is dead rather than the idea. `train_yolo.py` now refuses an `nc` mismatch without `--allow-nc-expansion` | PAGE | — |
| **measure cells** | geometry from the above | a cell IS the staff plus padding | — | PAGE | — |

### 2.2 Notes and rhythm

| target | READ BY | WHY | ALSO TRIED → VERDICT | FROM | TIER |
|---|---|---|---|---|---|
| **noteheads** | **YOLO** — `yolo_detector.detect:345` | the thing the detector is good at: reading F1 **0.999** (856 of 856) on engravings | ⚠️ **erasing staff lines first** → **REFUTED**: pooled reading 0.876 → 0.805 and 0.921 → 0.793, noteheads to recall **0.642**, and it MANUFACTURES beam confusion (46 → 105 detections, precision 0.783 → 0.343). **Scope: n=2 engraved works, page-truth F1, the case most favourable to it** (`docs/scope-cv-hairpin-detection-2026-09-04.md:88`) | PAGE | — |
| **hollow noteheads on scans** | YOLO, with **head-graft weights** (`…hollow-graft-shift09-2026-09-04.pt`) | at 600 dpi bitonal the half-note counter closes to a sliver; the heads are **not misclassified, they are not detected** | (a) reclassify by ink fill → nothing to reclassify; (b) counters as enclosed holes → 662 candidates for 68 notes; (c) Bravura template match → 15 of 68; (d) thinning → 4→9 of 26 while inflating `noteheadWhole` 1→5. **All four REFUTED**, scope: Beethoven 5 p.1. (e) **fine-tuning on the scan-label corpus** → **REFUTED across eleven method arms**: whole classes go to exactly zero (tie 249→0, beam 188→0, restWhole 396→0). The ship is **surgery** — `merge_class_head.py` restoring untaught head rows + a bias floor | PAGE | — |
| **stems** | **classical CV** — `line_detection.detect_stems:217` | ⚠️ **a deliberate replacement of an AVAILABLE class, not a gap.** `stem` IS in the 208-class space; the docstring's reason is structural: *"YOLO bounding boxes are structurally poor at thin lines (extreme aspect ratios, mostly-empty boxes)"* | leaving it to YOLO → **REFUTED**, and now re-measured on current weights: the detector emits **76 `stem` detections on 11 scan pages and 0 on 11 engraved works**, against 5,896 noteheads. ⚠️ The docstring says *"0 detections even at conf=0.05"* on Phase 3.3 weights; on today's it is 76/0 — **the conclusion holds and the literal number has drifted** | PAGE | — |
| **beams** | ⚠️ **BOTH — a bounded union.** CV (`detect_beams:436`) plus a YOLO beam kept **only where no CV beam overlaps its x-range** (`rhythm.py:1523`) | a YOLO beam box bounds the STACK, not a stroke, so it contributes a phantom centre in the gap between two strokes; but replacing outright throws real beams away | **all three arrangements measured**: union (Phase 4f) 0.1917 / replace 0.1855 / **kept 0.1861**. ⚠️ Replace SCORES BEST by five edits and was **REFUTED anyway** — it is the only arm that regresses an authored fixture and takes the `×4` family 4 → 7. Observed today: the detector still emits **1,896 scan / 366 engraved** beams, so the union rung is live | PAGE | — |
| **ledger lines** | **YOLO** — the class exists and is consumed | `ledgerLine` detections feed the cross-staff ownership ladder directly; worth pooled 0.1506 → 0.1431 | ⚠️ hand-labelling them → **REFUTED as a method**: *"a human still cannot bbox a thin line"*; the escape is the teacher drawing them or head-row restoration. Observed: **2,461 scan / 488 engraved** | PAGE | — |
| **durations** | derived — `rhythm.resolve_rhythms_for_cell`, beams > flags > notehead class | not a recognition target: it is arithmetic over beams, dots and the head class | — | PAGE | — |
| **tuplets** | **YOLO markers** (`tuplet3` **and** `fingering3`) + the beam box for membership | the digit says a tuplet is there, the beam box says how far it reaches; the two classes are a POSITIONAL distinction the detector reproduces badly | reading the class as evidence of which → **REFUTED**: 33 `fingering3` against 16 `tuplet3` over twelve works, and all 33 sit in a cell holding a real triplet | PAGE | — |

### 2.3 The header facts — the three that got bespoke readers

⚠️ **This is the densest cluster of "the detector could not, so something else
does", and all three readers are geometric.**

| target | READ BY | WHY | ALSO TRIED → VERDICT | FROM | TIER |
|---|---|---|---|---|---|
| **which line a clef names** | **geometry** — `clef_geometry.resolve_clef:239` | ⚠️ **a mislabelled TASK, not an under-trained model**, and the docstring is unambiguous: *"They are the same glyph. An alto clef and a tenor clef are one drawing printed one staff line apart; the ink is identical."* Soprano/mezzo/baritone have **no classes at all**, so no training on that label space can emit one | a **clef-targeted fine-tune** → **REFUTED twice over**: alto/tenor confusion survived it (1/3 alto; the retrain fixed alto and flipped tenors), *and* the weights collapse dense-page notehead detection **2506 → 114** (`benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md`). Kept as an optional **decoupled specialist** (`OMR_CLEF_WEIGHTS`), never the main detector | PAGE | — |
| **finding a C clef nothing detected** | **classical CV** — `clef_locator.locate_clef:646` | on 19th-century C-clef prints the detector finds **no clef at all, at any confidence** | 8 of 24 real C clefs on hand-read orchestral pages, 163 correct declines. ⚠️ `dot_single_clear_is_enough` is a **recorded, deliberate trade**: −8 false positives for −20 declined C clefs. Observed reach: **5 of 193 scan staves** | PAGE | — |
| **key signature** | **template matching** — `key_signature_template.py`, sliding Bravura `accidentalFlat`/`Sharp` | component clustering *"falls apart on a degraded scan, where the staff-line removal leaves each glyph in pieces"* | **component clustering** (`key_signature_locator`) → **REFUTED on scans**: given the correct clef for every staff it reads **2 of 12** where templates read **11 of 12**; scope: Beethoven 5 p.1, and eight of the ten it misses print three flats plainly. ⚠️ Kept for clean engraving — this is a *routing* decision, not a replacement | PAGE | — |
| **which prefix of the slot table** | **geometry** — `key_signature_geometry._fit_exact:298` | counting believes exactly what the detector saw: on WTC p.17 counting reads 6 of 10 staves and the four failures are +1, +1, +2, +5 | counting → **REFUTED**, scope: WTC p.17 (one clean engraving where the detector fires on every staff). ⚠️ **And the fallback to counting is still live and is a live fault** — see `DECISION_TYPES.md` §R8.1: mid-staff it turns a 4-sharp staff into 1 sharp, 7 times on the scan corpus | PAGE | — |
| **time signature** | **composite template** — `time_signature_locator.py`, per-meter templates built from Bravura `timeSig0-9` | *"on a real orchestral scan the detector finds no time-signature digit anywhere in the header"* — measured on Beethoven 5 p.1, a 2/4 page printing `2` over `4` legibly on **all twelve staves**: **zero** header detections, and the five `timeSig4` boxes it did fire were **barline fragments** | (a) ink coverage as a discriminator → **REFUTED**, it inverts (engraved TRUE scores below scanned FALSE); (b) whitespace gutters → **REFUTED**, no separation; (c) ranking by median score in the vote → **REFUTED**, identical verdict table and one principle weakened. `timeSigCommon`/`CutCommon` stay with the detector, which reads those two glyphs well | PAGE | — |
| **cut common** | **position after `C` wins** — `_looks_cut:381` | withholding the ¢ template does not produce an abstention, it produces `C`; adding the template fails BOTH ways because a C is a SUBSET of a cut-C's ink | adding a ¢ template → **REFUTED**: nine false systems *and* it still loses to plain `C` on real ¢ pages | PAGE | — |

### 2.4 Expression

| target | READ BY | WHY | ALSO TRIED → VERDICT | FROM | TIER |
|---|---|---|---|---|---|
| **slurs / ties** | **YOLO** (`slur`, `tie` in the class space) + **export-time pairing** in page pixels | a barline cuts the arc, so pairing must happen in the only frame shared across cells | ⚠️ **export-time tie/slur GRAMMAR reclassification** (`OMR_ARC_RECLASS`) → **REFUTED and shipped OFF**: engraved +2 edits, scan **+130, refused**, all +130 in the tie→slur half. Scope: both standing families, per direction. ⚠️ **What is open is ANCHORS, not grammar** — measured in `DECISION_TYPES.md` §R2.1: **79.6% of scan tie detections never find two anchors** | PAGE | — |
| **arc ownership** | comparative geometry — `export._arbitrate_arcs_in_system:1770` (`OMR_ARC_ATTRIBUTION=move`, on) | an arc binds a run of noteheads and is drawn just clear of them, so it belongs to the staff whose **noteheads it hugs** — distance to the staff LINES is the trap it was for notes | `drop` (delete instead of regift) → **REFUTED at a BETTER score**: 2,388 vs 2,371 edits, and refused because it gets there by emitting 20 fewer slurs, 12 of them real | PAGE | — |
| **hairpins** | **YOLO** — `dynamicCrescendoHairpin` / `dynamicDiminuendoHairpin` are in the class space | reading F1 **1.000** against exact page truth on engravings (n=3) | ⚠️ **`hairpin_detection.py` (344 lines) — classical CV, measured at "59 of 99 hairpins against the detector's 1" — has ZERO call sites.** Verified: `grep -rn hairpin_detection tools/ backend/` returns nothing outside its own file and its tests. **UNREACHABLE, not REFUTED** — a merge, not a research programme. And it matters: observed detections are **9 on 11 engraved works and 0 on 11 scan pages**, against a scan truth of 198 `<wedge>` | PAGE | — |
| **dynamic letters** | **YOLO** + `export.measure_dynamics:1337` assembling runs by x-adjacency | the glyphs are drawn and the detector finds them | ⚠️ a run spelling no legal dynamic is **dropped whole** — 45 of 45 scan and 8 of 8 engraved refused runs are **edit distance 1** from a legal dynamic. **UNTRIED** (the nearest-legal-word conversion is shortlist item 2 and nobody has built it) | PAGE | — |
| **articulations** | **YOLO** — all ten DSv2 `artic*` classes | fired freely and were simply never exported until 2026-09-01 | attaching by the mark's own bbox → **REFUTED** by analogy with the augmentation dot; the unit is the **notehead width**, and the constant is a plateau (0.50–2.50 identical) | PAGE | — |
| **direction text** | ⚠️ **NEITHER — a GENERATIVE DECODER over subtracted ink**, gated by `direction_lexicon.lookup:139`. See §2.4.1: calling it "OCR" understates what is running | *"the class that would have supplied one, `textDynamic`, is also the class that caused the Phase 3.4 catastrophic forgetting — so this reads text WITHOUT the detector"* | a YOLO text class → **REFUTED** by the Phase 3.4 result above. ⚠️ **Loosening the lexicon** → **REFUTED and load-bearing**: OMR-NED charges an invented direction its own character count, so a guessing reader pays at the rate it is paid. Measured in `DECISION_TYPES.md` §R1.2: **89.6% of its 135 refusals carry no legal term at all** — the gate is well earned | PAGE | — |

#### 2.4.1 ⚠️ The direction reader is an LLM, and nothing in this repo constrains its decoding

An earlier draft of this row said *"OCR over subtracted ink"*. That is the CV
half. The reading half is **Surya, a generative decoder**, and the repo sets
**none** of the parameters that would bound it — verified across
`_surya_worker.py`, `staff_labels_surya.py` and `direction_text.py`:

```
temperature · top_p · max_tokens · max_new_tokens · seed · do_sample · greedy
   -> ZERO occurrences in any of the three
```

The call is `predictor([image], full_page=True)` (`_surya_worker.py:60`) at
library defaults.

⚠️ **This is not theoretical, and the evidence arrived from another workstream
this week.** A same-tree control on Litolff Beethoven 5 p68 — two runs, one
page, identical everywhere else — found the same slot of
`direction_text.pages[0].rejected` holding an **11,708-character hallucinated
English essay** in one run and the six-character string `SECRET` in the other.
So the rung is nondeterministic **in content and in length** on an unmodified
tree, at library defaults, with no cap.

**Why it is contained today, and where the containment is:** `n_accepted` was 0
in both runs. The exact-membership lexicon gate (§2.4, and `DECISION_TYPES.md`
§R1.2: **89.6% of 135 refusals carry no legal term at all**) is what stands
between a generative decoder and the exported score. ⚠️ **That reframes the
standing instruction not to loosen the lexicon**: it is not merely a precision
tuning choice, it is the only bound on an unbounded generator. The same reader
supplies **87.6% of scan margin labels** (§2.5), where the containment is
`instruments.lookup` instead.

⚠️ **Not mine to fix, and dispatched elsewhere** — it is `direction_text`'s. It
is recorded here because a ledger keyed on mechanism must not file a
constrained-decoding question under "OCR".

### 2.5 Identity — the most heterogeneous row set in the pipeline

| target | READ BY | WHY | ALSO TRIED → VERDICT | FROM | TIER |
|---|---|---|---|---|---|
| **margin labels** | **a cheapest-first cascade of four readers**: PDF text layer → Surya (local OCR) → Claude Vision (paid, off) → human (unreachable) | identity is a property of the SCORE, not of each page, so slots propagate one reading everywhere — which is what makes a paid rung affordable at all | Claude vs Surya → **measured EQUAL**: both score zero disagreements against the text layer, Surya resolves 89% of what Claude does. ⚠️ Observed split is exactly as designed and worth stating: engraved is **text_layer 124 / surya 83**, scan is **surya 134 / text_layer 12** — the free local rung carries the scans | PAGE | `label` |
| | | | ⚠️ **the human rung is UNREACHABLE from `transcribe`**: `_contextual_call_kwargs` synthesises `Assist("vision" or "none")`, so `staff_labels_human.py` (205 lines) is callable only by a tool that invokes `apply_contextual_analysis` directly. Observed: **0 / 0** | HUMAN | — |
| **instrument from a string** | **a lexicon** — `instruments.lookup:873`, a pure function of the string | deliberate blindness; every contextual repair downstream exists to patch it | ⚠️ **loosening the matcher** → **REFUTED**: a gated single-substitution matcher was prototyped, **measured collision-free, and NOT adopted**; OCR folds are admitted on RARITY only and common-letter pairs (`a/u`, `b/h`, `c/e`, `n/m`) are refused **by name** | PAGE | `label` |
| **which staff is which part** | **an additive-evidence model** — `slots._pair_score:480`, signed terms, no vetoes | the one place in the pipeline already shaped the way Sean's principle asks for | ⚠️ but `SCORE_LABEL_CONFLICT = −8.0` dominates every other term combined (max non-label positive 2.5) — **a gate wearing an additive coat** (`DECISION_TYPES.md` §5.2) | PAGE | `label` / `score_order` |
| **the work's roster** | **CATALOGUE** — IMSLP `InstrDetail`, one query per work | §1. Page-side acquisition fails on a minority of documents; this is an independent escalation | ⚠️ **deriving the roster from the reference encoding** → **FORBIDDEN, not refuted**: that would be `source_kind: "encoding"` and a measurement path may not read it. `validate_fact:574` enforces it | CATALOGUE | **`catalog`** — the only external tier a measurement path may read |
| **this EDITION's roster** | **PAGE** — `tools/library/edition_instrumentation.py`, read off the edition's own pages | a work tier is right about the piece; an edition tier is authoritative for THIS PDF (Bruckner versions, publishers absorbing parts) | acquired on 189 of 234 editions (0.808). ⚠️ **tier `page`, a THIRD kind** — a roster read off a raster is an OMR output, so a measurement path refuses it for a *different reason* than it refuses `encoding` | PAGE | **`page`** |
| **naming an unlabelled staff** | position prior + layout fit — `score_layouts.fit_layouts:582` | 29 of 29 unresolved non-treble scan staves **print no label at all** — the constraint is the engraving, not the reader | better label reading → **REFUTED as a lever** for this population, scope: 20-row scan corpus, 5 publishers (`benchmarks/omr-staff-identity-labels-2026-09/`) | PAGE | `score_order` — ⚠️ **may never feed a clef decision** |
| **a calibrated identity probability** | ⚠️ **nothing — and deliberately** | P(name) ECE 0.1277, P(set) 0.1301, n=197, top bin promising 0.989 and delivering **0.692** | shipping the estimator → **REFUTED and nothing was shipped**. ⚠️ The diagnosis was **the CORPUS, not the estimator** (the `derived` tier is empty), so this is REFUTED-for-now with a named unblock: two more hand-read works | — | — |

---

## 3. ⚠️ "Read by CV" means two different things, and the ledger separates them

Verified by enumerating the 208 names in `data/user-labeled/catalog.yaml`:

| target | in the class space? | so CV is… |
|---|---|---|
| `stem`, `beam`, `staff`, `ledgerLine`, `tie`, `slur`, both hairpins | **YES** | a **deliberate replacement** of an available class — the model *can* emit it and is structurally bad at it (thin lines, extreme aspect ratios) |
| **barline**, **family bracket** | **NO** — `barline` appears under **no spelling at all**, and the bracket-named classes are `tupletBracket` / `tupleBracket` / `ottavaBracket`, all different objects | filling an **absence**, and the attempt to remove the absence is the Phase 3.4 catastrophe |

### 3.1 ⚠️ "Present in the class space" is NOT "usable", and this ledger's own evidence says so

Membership answers whether a class *can* be emitted. It says nothing about
whether it *is*. Measured over both corpora
(`out/probe_mechanism_attribution.txt`), against 4,339 scan / 1,557 engraved
noteheads:

| class | in space | **emitted, scan** | **emitted, engraved** | usable? |
|---|:--:|--:|--:|---|
| `beam` | ✔ | 1,896 | 366 | **yes** — and consumed, as a bounded union with CV |
| `ledgerLine` | ✔ | 2,461 | 488 | **yes** — consumed by the ownership ladder |
| `tie` / `slur` | ✔ | 1,658 / 413 | 171 / 306 | **yes** — consumed, with the anchor caveat in §2.4 |
| `staff` | ✔ | 1,150 | 1,579 | ⚠️ emitted freely, **consumed by nothing** (§3's corollary) |
| **`stem`** | ✔ | **76** | **0** | ⚠️ **present and effectively absent** — 76 firings against 5,896 noteheads, and *zero* on the engraved family |
| **hairpins** | ✔ | **0** | 9 | ⚠️ **present and absent on the family that needs it** — 0 detections across 11 scan pages against a truth of 198 `<wedge>` |

**So the CV decision for stems is over-determined and the ledger should say so:**
the *architectural* reason is that YOLO boxes are bad at thin lines, and the
*empirical* one is that on today's weights the class barely fires at all. Either
alone would justify the move; together they make it very hard to reverse.

⚠️ **And the hairpin row is the same fact pointing the other way.** The class is
present, the engraved reading F1 is 1.000, and on scans it emits nothing — which
is exactly why an unwired CV reader (§5) is a live gap rather than a redundancy.
**Membership is a necessary condition for "the detector could do this" and not
close to a sufficient one.**

**This distinction predicts what a future attempt costs.** Re-teaching a class
that is absent means expanding `nc`, which re-initialises the head — priced at
**F1 98.8% → 79.3%**. Improving a class that is present is an ordinary
fine-tune — priced separately, and separately refuted (§4). *They are not the
same experiment and the ledger should not let them be confused.*

⚠️ **A corollary that an earlier draft got wrong, and the correction matters
more than the original claim.** The detector's `staff` class fires **1,150 /
1,579** times across the two corpora and staff detection reads none of it — and
I called that "the cheapest untried comparison in this ledger". **It is not
untried; it is not comparable.** `detect_staves` consumes a full-page raster and
runs *before* any detection, because the detector's input is measure cells cut
from what `detect_staves` returns. There is no moment in the current pipeline at
which both answers exist.

So the honest classification is **UNREACHABLE-pending-a-new-regime**, and the
cost is not an A/B:

| what it would take | why |
|---|---|
| a **full-page** detector pass | today the detector only ever sees canonical cells; `imgsz_for_cell` and the canonical rescale are built for that |
| a second inference regime, priced | a whole-page pass at cell resolution is a different compute profile, and `OMR_IMGSZ`'s own sweep says larger is not better |
| a reason to expect it to win | ⚠️ **none is on the record** — the `staff` class's only real consumer in the tree is inside `hairpin_detection.py`, a module with zero call sites |

⚠️ **The non-consumption is confirmed and is stronger than "nothing reads it"**:
of the sites holding the class string, one is a category map, one is a
measurement-path exclusion, two are docstring prose, and the only consumer is in
an unwired module. What is NOT established is that consuming it would help.

---

## 4. Every refutation, with its scope

⚠️ The scope column is the point. Several of these are almost certainly right
in general and **none of them was measured in general.**

| refuted approach | measured | scope | reproducible today? |
|---|---|---|---|
| erase staff lines before YOLO | 0.876→0.805, 0.921→0.793; noteheads to recall 0.642 | **2 engraved works**, page-truth F1, one monkeypatch | yes — `docs/scope-cv-hairpin-detection-2026-09-04.md` |
| add 6 custom classes to YOLO (barlines, textDynamic) | F1 **98.8% → 79.3%** | **1 training run, 49 train images**, mechanism diagnosed (`nc` expansion re-inits the head) | the artefact is committed |
| clef-targeted fine-tune | alto/tenor still confused; dense noteheads **2506 → 114** | 1 fine-tune + 1 corrected retrain | yes |
| fine-tune on the scan-label corpus | whole classes → **exactly 0** (tie 249→0, beam 188→0, restWhole 396→0) | **11 method arms** — the best-covered refutation here | yes |
| ScoreAug / Augraphy domain augmentation | dense real-cell recall **0.652 → 0.122** | ⚠️ **1 comparison, and the provenance is thinner than an earlier draft of this row said.** The figures are at `benchmarks/omr-first-run-2026-08/DURATIONS.md:105`, **not** in the detection probe, and that line cites a MEMORY FILE (`[[project_domain_augmentation]]`) rather than an artefact. The "probe JSONs were scratch" disclaimer is real but sits at `benchmarks/omr-detection-probe-2026-07/findings.md:67` and covers **that file's own numbers**, not these | ⚠️ **NO** — see §6 |
| component clustering for key signatures on scans | **2 of 12** vs templates' 11 of 12 | 1 page (Beethoven 5 p.1), given the correct clef | yes |
| counting key-signature markers | 6 of 10 staves; errors +1, +1, +2, +5 | 1 page (WTC p.17) | yes |
| gap-distance system grouping | ranges overlap (17–237 vs 130–345) | 2 works — but the refutation is **arithmetic**, so it travels | yes |
| crossing-PIXEL bracket ratio | 16/22 and **0/15** against print truth | 2 publishers, 37 systems | yes |
| **reading** the family bracket | 5/22 and 1/15 — loses to inferring | same | yes, and see §5 |
| ink coverage / whitespace gutters as meter discriminators | invert / no separation | the timesig corpus | yes |
| `OMR_ARC_RECLASS` grammar veto | engraved +2, scan **+130** | **both families, per direction** — well scoped | yes |
| arc `drop` instead of `move` | ⚠️ **2,388 vs the SHIPPED arm's 2,371 — `drop` is WORSE.** It beats only the *comparable* move arm at the same margin (2,388 vs 2,411), which is the **arm-for-arm** qualifier CLAUDE.md keeps. Refused on the **arc-count control**: pooled slurs 199 → **183** against a truth of **241**, i.e. away from the truth, where move goes 199 → 207 | pooled engraved, `benchmarks/omr-arc-attribution-2026-09/FINDINGS.md:155-178` | yes |
| beam `replace` instead of `kept` | 0.1855 vs 0.1861 — **better, and refused** | 3-work era + authored fixtures | ⚠️ the 3-work era no longer exists |
| loosening `instruments.lookup` | prototyped, **collision-free**, not adopted | 1422 margin labels | yes |
| a calibrated identity probability | ECE 0.1277 / 0.1301 | n=197, and the diagnosis is the **corpus** | yes |

⚠️ **Two arms were refused against a favourable number, and the two refusal
GROUNDS are different — which is more useful than the generalisation an earlier
draft of this row made.**

| arm | its number | refused on |
|---|---|---|
| **beam `replace`** | pooled **0.1855 / 1310 edits against `kept`'s 0.1861 / 1315** — genuinely better, by five edits | **a control**: it is the only arm that regresses an authored fixture, and it takes the `×4` family (notes that lost every beam they had) from 4 to **7** |
| **arc `drop`** | ⚠️ **NOT better than the shipped arm** — 2,388 against 2,371. Better only **arm-for-arm**, against the move arm at the same margin (2,388 vs 2,411) | **a count control**: slurs 199 → **183** against a truth of **241**, moving away from it, while move goes 199 → 207 |

⚠️ **An earlier draft of this row said `drop` was "refused at a better score" and
paired it against 2,371. That is backwards, and it is the specific error this
table exists to prevent** — a future agent checks, finds 2,388 > 2,371, concludes
the ledger is wrong, and re-opens `drop`. The qualifier CLAUDE.md carries is
**arm-for-arm**; dropping it inverts the claim. Corrected 2026-09-07 against
`FINDINGS.md:155-178`.

**What survives, and it is the useful half:** in this project a favourable
pooled number is not sufficient to ship, because OMR-NED is symmetric and rewards
emitting fewer symbols. **But the ground of refusal has to be quoted with the
arm** — one of these was refused despite a better score, the other despite a
better *comparable* score, and only a control settled either.

---

## 4.1 ⚠️ And every ADOPTION has a scope too — the thesis is symmetric

§4 scopes what was refused. An earlier draft stopped there, which is
half-applying its own argument: a shipped default is a measurement too, and a
default whose scope does not cover the population it fires on is the same
hazard pointing the other way.

| shipped default | the measurement that adopted it | scope | fires on |
|---|---|---|---|
| **`_UNLADDERED_NOTEHEAD_MAX_CONF = 0.65`** | an empty gap: fakes 0.45–0.53, lowest real 0.76 | ⚠️ **3 ENGRAVED works** (`LADDER_EVIDENCE_2026-09-01.md:72-85`) | **351 scan / 28 engraved deletions — 12.5× more often on the family it was NOT measured on**, where the surviving population is continuous through it (`DECISION_TYPES.md` §4.4) |
| `OMR_ARC_ATTRIBUTION=move` | pooled 2,473 → 2,371 edits, no work worse | 11 engraved works; the scan gate's two Brahms rows byte-identical | both families |
| `OMR_CELL_LINE_TRACE` on | ⚠️ pooled **0.8387 → 0.8345 — worse** — adopted on the attribution: −217 of −233 edits fall on exactly the three tilted rows | the widened 20-row scan gate | scans; engraved is a no-op by construction |
| `OMR_CHOIR_GROUPING` on | Bach row 0.9241 → 0.8152; 10 pooled scan rows byte-identical; engraved edit-for-edit identical | **1 stress row** + a 969-page structural probe | both |
| `OMR_BRACKET_COLUMNS` on | 22/22 and 15/15 against hand-read print truth | **2 publishers, 37 systems** | both |
| `OMR_LEFT_EDGE_SPLIT` on | 27 over-merged pages fixed vs 1 residual, 0 size-1 systems created | 964 library pages | both |
| `OMR_DIRECTION_TEXT` on | worth 144 edits, 18.8% of the pooled figure | the engraved orchestral benchmark | both — ⚠️ and see §2.4.1 |

⚠️ **The first row is the one to carry forward**: an adoption measured on the
family where it barely fires, applied to the family where it does 92.6% of its
work. That is not an argument to change it — the constant may be exactly right —
it is an argument that **the scope belongs beside the default in the knobs
table**, where today only the measurement appears.

⚠️ **The third row is the honest counter-example to the whole table**:
`OMR_CELL_LINE_TRACE` ships while making the pooled figure WORSE, because the
attribution showed the damage was concentrated where the mechanism predicts. A
scope column would have flagged it and been wrong to. **Scope is context for a
decision, never a substitute for one.**

---

## 5. UNREACHABLE — built, sometimes measured, not wired

⚠️ **Trap 2. These are merges, not research.**

⚠️ **The rows do not share one method, and an earlier draft said they did.**
Three of them (`hairpin_detection`, `bracket_reader`, `template_matcher`) are
verified by `grep -rn <module> tools/ backend/` minus the module's own file and
its tests. **`staff_labels_human` is NOT one of them** — it has real call sites
at `contextual.py:860-861`; what is unreachable is the *path to them* from
`transcribe`. The other two rows are neither: one is an unset env var and one is
an unpassed keyword. **The column below states each row's own evidence.**

| module | size | state | evidence |
|---|--:|---|---|
| **`hairpin_detection.py`** | 344 lines | classical-CV hairpin reader; its own docstring reports *"59 of 99 hairpins against the detector's 1"* | **zero call sites.** And the gap it addresses is live: **0 hairpin detections on 11 scan pages** against a truth of 198 `<wedge>` |
| **`bracket_reader.py`** | 390 lines | reads the printed bracket | **zero call sites** — and here the verdict is **REFUTED *and* UNREACHABLE**: `ceadb7bb` measured reading at 5/22 and 1/15 against inferring's 22/22 and 15/15. ⚠️ **Do not merge this one**; it is on the list to stop someone finding it and assuming it was forgotten |
| **`staff_labels_human.py`** | 205 lines | the human rung of the label cascade | ⚠️ **it HAS call sites** — `contextual.py:860-861` — and is still unreachable **from `transcribe`**, because `_contextual_call_kwargs` (`transcribe.py:4006`) synthesises `Assist("vision" if vision_fallback else "none")` and never `"human"`. Reachable only by a tool calling `apply_contextual_analysis` directly. Observed reach **0 / 0** |
| **`template_matcher.detect_symbols`** | — | the Phase-2 detector | survives only as the home of the `SymbolDetection` dataclass, which `yolo_detector.py:41` and `pitch_resolver.py:8` import. Two live env flags (`OMR_PHASE26_FIXES`, `OMR_PHASE28_FIX_TEXT_GATE`) gate dead code |
| **`OMR_ROSTER_LABELS`** | — | measured, hand-adjudicated 28/28 correct | **production reach NIL** — it needs `OMR_WORK_ID` and *nothing sets it*. ⚠️ Wiring, not measurement, is the prerequisite |
| **`locate_clef(trace=…)`** | — | the veto chain's own recorder | **no pipeline call site passes a trace** (`grep -rn "trace=" tools/omr/*.py` → nothing) |

**The distinction pays immediately:** three of these six are one merge away from
being live, one must NOT be merged, one needs an env var wired, and one needs a
keyword argument.

---

## 6. ⚠️ Where the rationale is UNDOCUMENTED — and this is itself a finding

The commission asked me to say so rather than guess. **This project records
MEASUREMENTS richly and RATIONALES thinly**, and these are the places where the
"why" is not written anywhere I could find:

| row | what is missing |
|---|---|
| **staff-line detection by CV** | ⚠️ **UNDOCUMENTED — no rationale recorded anywhere**, and an independent `git log -S` / `--grep` / prose sweep found none either. The `staff` class exists and fires 2,729 times across both corpora. ⚠️ **The ORDERING is now established (§3): `detect_staves` runs before the detector and the class does not yet exist when it decides.** That is a structural account of why the question never arose — it is **not** a recorded rationale for the design, and I am not promoting it to one |
| **stage-1 constants** (`window_size=25`, `k=0.2`, the 0.1° dead band, `max_correction_deg=5.0`) | **UNDOCUMENTED** — the decision map already calls stage 1 *"the shallowest-evidence stage in the pipeline"*; none of the four is tied to a measurement |
| **ScoreAug / Augraphy** | the NUMBER is recorded (0.652 → 0.122) and **the evidence is not** — the source says the probe JSONs were scratch and never committed. ⚠️ A refutation nobody can re-run is one bad memory away from being re-tried |
| **`_page_ink`'s grey 180** (`direction_text.py:278`) | a bare literal; the only stated reason is that Sauvola is tuned for staff lines, with no sweep |
| **why the meter specialist overwrites unconditionally while the clef specialist is gap-fill** (`transcribe.py:1769` vs `:1772`) | the comment explains only that the two are *independent*, never why the precedence differs. See `DECISION_TYPES.md` §R4 — and note it is **inert**: reach 0 on both corpora |
| **`_detect_key_sig_from_cell`'s count fallback** | documented, and **documented wrongly** — *"a reading is never lost, only improved on"* is false mid-staff, where it turns 4 sharps into 1 (`DECISION_TYPES.md` §R8.1) |

---

## 6.1 ⚠️ RECONCILED — "direction text is ~75% of wall clock" and "19.2%" are two REGIMES, not a contradiction

The decision map states **~75% of wall clock on a whole-work run** in three
places, unqualified. The verifier measured a **median of 19.2%** over the
committed transcriptions. I reproduce that independently
(`out/probe_direction_share.txt`): **n = 22, min 11.2%, median 19.2%, max
84.5%**.

⚠️ **And the decisive fact is in the same probe: all 22 are
`n_pages_processed == 1`.** Every committed transcription is a single-page
benchmark run. The 75% figure is from an **88-page whole-work run**. They are
not measurements of the same thing.

**They are consistent, and two mechanisms independently push the same way:**

1. **Fixed costs amortise in the opposite direction.** A single-page run pays
   the YOLO weights load and Surya's 650M GGUF load once, against one page of
   direction-text work — so the one-time loads dominate `total_s` and direction
   text's SHARE is suppressed. Over 88 pages the loads are still paid once while
   direction text is paid per page, so its share rises with page count.
2. **Density.** Direction text is per-candidate-crop OCR at 0.5–0.8 s a crop.
   ⚠️ The tail already proves this alone can reach the headline: the **84.5%**
   maximum is a *single-page* run (`beethoven-984073-p2`, 284.7 s of 337.1 s), so
   a dense scan gets there with no page count at all.

**Neither mechanism is isolated by the evidence available**, and I am not
claiming one dominates.

**The honest sentence, and the correction is to the FRAMING rather than the
number:**

> On a whole-work run, direction text is the dominant cost — ~75% on the
> 88-page Beethoven 5 read. On single-page benchmark runs it is a median 19.2%
> (n=22, 11.2–84.5%), because a one-page run is dominated by model loads that a
> long run amortises. **Quote the regime with the figure**; the two are
> consistent and neither is a property of the pipeline alone.

⚠️ **`n_pages_processed` is already on every result JSON**, so any future
wall-clock claim can carry its regime for free — which is the same discipline
this project already enforces for page-set regime on identity figures
(`OMR_MAX_PAGES=5` reading 4/12 where a whole-work run reads 12/12).

⚠️ **The 88-page figure itself is UNVERIFIED here** — no whole-work artefact is
committed, so I am reconciling a measured distribution against a recorded number,
not against a second measurement.

---

## 7. What this ledger does NOT cover

- **The training and labeling pipeline's own technology choices** (`annotate/`,
  the snap grid, catalog membership). Separate documents, deliberately.
- **The Maestro theory layer** — off by default, host-side, consumes the result
  JSON rather than making a recognition decision.
- **Per-constant provenance.** §4 gives each refutation its scope; it does not
  reproduce the measurements.
- **Reach for the CV internals** (`find_candidates`, `_blank_detections`) —
  unmeasurable from committed artefacts, as `DECISION_TYPES.md` §R10 records.
- **The web app's engine choice** (local YOLO vs Claude Vision OMR). CLAUDE.md's
  territory; the short version is that Vision OMR was measured too inaccurate on
  orchestral scores and the local pipeline is primary.

---

## 8. Reproducing

```bash
export OMR_FIXTURE_ROOT=/Users/seanjohnson/Desktop/ReEngrave
P=.claude/worktrees/nice-nash-085307/benchmarks/omr-pipeline-audit-2026-09/probe

python3 $P/probe_mechanism_attribution.py   # §2, §3, §3.1 — observed mechanism and emission per target
python3 $P/probe_direction_share.py        # §6.1 — wall-clock share WITH its page-set regime
```

Read-only, seconds, committed artefacts only; exits **2** rather than printing an
empty table if the fixtures are not where it looked.

The class-space enumeration behind §3 is one command:

```bash
python3 -c "import yaml; n=yaml.safe_load(open('data/user-labeled/catalog.yaml'))['names']; \
print([x for x in n if 'barline' in x.lower() or 'bracket' in x.lower()])"
```

⚠️ Every "zero call sites" claim in §5 is
`grep -rn <module> tools/ backend/` minus the module's own file and its tests,
plus `git log --all --oneline -S` for the wiring that never landed.
