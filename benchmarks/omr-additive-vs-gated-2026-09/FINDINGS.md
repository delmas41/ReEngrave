# Additive evidence or a gate — which decision points are which

**Commissioned 2026-09-06** off Sean's governing principle, recorded in
[`docs/scope-identity-upstream-2026-09-06.md`](../../docs/scope-identity-upstream-2026-09-06.md)
§8b: *"I don't want a stain from disagreement — I want additive information to
build probability."* And his qualification, which is the actual commission:
*"we will probably have to experiment to see if certain processes should be
additive and if others should be gated/abstain."*

**No pipeline behaviour is changed by this branch, and no default is touched.**
Everything here is a probe over committed artefacts, plus one instrumented
re-run of the 20-row scan gate under `OMR_CONTEST_DUMP=1` — which the pipeline
itself documents (`transcribe.py:2789`) as *"REACH INSTRUMENTATION ONLY … it
changes no verdict"*, and which reproduced that gate's recorded **4,521**
contested pairs exactly.

Builds on the five-class taxonomy in
[`docs/handoff-probability-gates-2026-09-05.md`](../../docs/handoff-probability-gates-2026-09-05.md)
(**A** never formed / **B** formed then quantised / **C** formed, consumed by
nobody / **D** exclusive tier or raw argmax / **E** structural refusal). That
document says what shape each decision *has*. This one says what shape it
*should* have, and measures the REACH of every recommendation before its
accuracy.

---

## 0. The one-line answer

> **Most of these sites should not become additive, and the reason is not
> caution — it is that the quantity an additive form would sum has been measured
> AT THAT SITE and does not separate. The conversion worth making first is not
> gate → additive at all. It is refusal → RECORDED refusal.**

Twenty decision points compute a real number and discard it at the moment they
refuse. That discard is why most of these conversions cannot be settled on
evidence — including by this document, which had to reimplement
`clef_correction.propose_clef` to learn which of its six exits each staff takes.
Recording the number is byte-identical to the output, costs nothing, and is the
prerequisite for every later decision, *including the decision not to convert*.

**Sean's principle is not in question, and its substrate already exists** —
`slots.py` and `score_layouts.py` are additive-evidence models with signed terms
and no vetoes. What is missing is not additive machinery. It is that the
evidence is destroyed before it reaches them.

---

## 1. The criterion

Stated so it can be applied to a site not examined here.

### 1.1 The distinction Sean's principle turns on

**A gate is a "stain" only when it encodes one fallible reader's opinion.** When
it encodes a law of the domain it is not a stain, it is information — and the
strongest kind, because it is the only kind that cannot be wrong.

| | | example |
|---|---|---|
| **CONSTRAINT** | what the domain permits | a monotone alignment cannot reorder staves; a run of *k* staves between two known slots spanning exactly *k+1* slots is FORCED; a player cannot sound a pitch outside the instrument's range; two equal-cost mappings that disagree carry literally zero information |
| **OPINION** | a fallible reader's reading of ink | a symmetry score, an NCC template match, a detector confidence, an OCR string, a distance to a staff band |

Softening a constraint into a penalty lets the system emit impossibilities and
buys nothing, because the constraint was never wrong. Softening an opinion into
a term is what Sean is asking for. **Every conversion recommended below is on an
OPINION; every "keep the gate" is either a CONSTRAINT, or an opinion whose
grading axis has been measured flat.**

⚠️ One boundary case, because it looks like an opinion and is not:
`slots.map_groups`' *"a tie of different meanings: no evidence"*
(`slots.py:379-382`, landed today as `a827fa36`). That is not a refusal to
choose between two plausible answers. It is the correct observation that the
evidence is **degenerate** — two assignments of equal cost that disagree — and
emitting either would be fabrication, not a graded guess. Degenerate evidence
and weak evidence want opposite treatments.

### 1.2 The five tests a site must pass to be worth converting

**All five. Each is a measurement, not a judgement.**

| # | test | how you check it | what failing it looks like |
|---|---|---|---|
| **T1 · OVERLAP** | the two outcomes' populations overlap on the candidate quantity | plot both populations | the empty-gap constants (notehead height, stem cap, dot offset, cut-common fill). A score there reports 0.99 forever and invites tuning |
| **T2 · SEPARATION AT THIS SITE** | the candidate quantity is measured *informative about this decision*, on this site's own data | §1.3, when there is no ground truth | §4.2 — `absent_instrument`'s `distance_pages` spreads 1–42 and is fully interleaved between its correct and its unadjudicable removals |
| **T3 · EMPIRICAL, NOT LOGICAL** | what is being decided is a reading, not a law | ask "could this be false of the printed page?" | §1.1 |
| **T4 · BOUNDED BLAST RADIUS** | a confidently wrong answer here stays local, or a later pass can reverse it | trace the consumers | a clef transposes every note on its staff and nothing re-reads it; `_align_by_span`'s span-reference error was inherited by 149 staff records |
| **T5 · A CALIBRATION CORPUS COULD EXIST** | the decision has an outcome that data could record | name the corpus and how you would build it | ownership of a contested glyph — **no corpus exists and none is derivable**; it would have to be hand-adjudicated |

⚠️ T1 and T2 are different tests, and the difference is the trap this survey fell
into twice. A quantity can be beautifully spread (T1 passes) and still be
uninformative, because it is spread with respect to the wrong partition.
`absent_instrument`'s page distance is the worked example: 1 to 42, no gap
anywhere, and *interleaved* between the removals that are right and the ones
nobody can adjudicate.

### 1.3 Running T2 with no ground truth — use an internal gold standard

The reusable method this document contributes. Where a site already has a tier
the pipeline *structurally trusts*, that tier is a free gold standard for any
candidate signal:

> `_dedupe_cross_staff_detections` decides 94.1% of contests by DISTANCE, which
> this project has already caught being a coin flip (5–62 px). But 5.9% are
> decided by the LEDGER LADDER — an unbroken run of ledger lines physically
> joining the glyph to a staff, the strongest evidence in the function. So: does
> the candidate signal (detection confidence) agree with the ladder more often
> than chance? If not, it carries no ownership information, and adding it at
> rank 0 is noise dressed as evidence.

Measured in §4.1: **0.617, 95% CI [0.558, 0.674], n=264.** Above chance, and
only just. This costs no labelling and is available at several other sites (the
dossier's alignment-free checks; `page_truth`; `key_signature_vote`'s
strong-weight readings).

### 1.4 The asymmetry, as a rule rather than a warning

A gate and a term fail in opposite directions, so the choice should be made on
**which failure the site can afford**:

| | fails by | its cost | detectable downstream? |
|---|---|---|---|
| **gate** | under-claiming — it declines | a correction not made | **yes** — the abstention is visible: an unnamed staff, an unread clef, a recorded `applied: False` |
| **additive sum** | over-claiming — it always answers | a confident error | **no** — it looks exactly like a correct answer |

The trade is acceptable where the abstention is *expensive and silent* and the
error is *cheap and visible*, and unacceptable the other way round. Two live
examples from opposite ends:

- `export.measure_dynamics` drops a letter run that spells no dynamic. The
  abstention is invisible (a mark that simply is not in the file); the error
  would be one wrong `<dynamics>` in one measure. **Convert.**
- `clef_correction`'s override refuses to overwrite a clef that was read. The
  abstention is visible (the staff keeps its read clef and the proposal is
  already recorded with `applied: False`); the error transposes every note on
  the staff. **Keep the gate's form; widen its admissible evidence.**

### 1.5 The third form, which is what most of these sites actually want

Neither gate nor sum: **abstain, and record the score you abstained on.**
`mxl_verdicts.prefill_cell` already does exactly this — it abstains *and* writes
`strength` / `strength_exact` onto the record — and it is the only site in this
survey whose additive-vs-gated question could be settled from committed
artefacts alone. That is not a coincidence.

⚠️ The caution that belongs with it, from the prior art: once a number exists,
consumers threshold on it and the constant becomes a decision rule nobody
revisits — the thing this exercise is trying to fix. So record the number **with
the refusal it belongs to**, and give it no consumer until a corpus has priced
one.

---

## 2. What was measured, and on what

| substrate | what it is | what it can see |
|---|---|---|
| `benchmarks/omr-scan-e2e-2026-09/fixtures/*.graft09.omr.json` | 11 committed scan-gate transcriptions — 11 pages, 5 works, 5 publishers, 193 staves, 16,706 detections | the per-page, per-staff, per-detection state of every gate that records anything |
| `benchmarks/omr-orchestral-e2e/fixtures/*.omr.json` | the 11 engraved orchestral works — 224 staves, 8,523 detections | the same, on the family whose ink is clean |
| `benchmarks/omr-absent-instrument-veto-2026-09/out/whole-report2.extract.json` | Beethoven 5 / Litolff, **88 pages**, 1,616 staff records, 962 label-evidence rows | the only committed artefact with a DOCUMENT-scope population |
| `out/contests/*.contests.json` (generated here) | the 20-row scan gate re-run under `OMR_CONTEST_DUMP=1`, ~50 s/row | every contested cross-staff pair, with both confidences and the tier that decided it |

⚠️ **What none of them can see.** Both standing benchmarks run ONE page per row,
so every document-scope gate (`absent_instrument`, span composition,
`_fill_defaulted_clefs`' cross-system unanimity) is *structurally inert* on them,
and a zero from either is coverage of nothing rather than a null. And **part
names do not reach musicdiff at all**, so the whole identity layer is invisible
to OMR-NED, to the 20-row scan gate and to `orchestral_eval` — several
recommendations below need a harness that does not exist (§6).

---

## 3. Class C is the dominant fault, now measured on BOTH families

The prior art measured 85 inert warnings on **one** scanned document. Across
both standing benchmark families:

| signal | scan (193 staves) | engraved (224 staves) | consumer |
|---|--:|--:|---|
| `rhythm_sum_warning` | 111 | 12 | `backend/modules/local_omr.py`, as a **boolean presence count** for a UI percentage |
| `time_signature_disagreement` | 17 | 1 | **none** |
| `clef_register_warning` | 7 | 4 | **none** |
| `clef_proposal` (recorded `applied: False`) | 5 | 1 | **none** |
| `key_signature_warning` | 0 | 3 | **none** |
| `measure_count_warning` | 0 | 0 | **none** — and 0 across 29 stored transcriptions in the prior survey |
| **computed and consumed by nobody** | **140** | **21** | |

`time_signature_disagreement` carries a real confidence: n=17 scan, min 0.500,
median 0.500, max 0.933. The 0.500 rows are the non-strict branch, where **every**
detected meter is flagged including the majority one — a warning whose own field
says it is not evidence, computed 17 times, read zero times.

Beneath the warnings sits the detection confidence the exporter never reads
(`grep -c '\bconfidence\b' tools/omr/export.py` → 1, a comment). The
distribution is why this matters on scans specifically:

| | scan | engraved |
|---|--:|--:|
| detections under conf 0.40 | **29.7%** | 4.9% |
| median notehead confidence | 0.733 | 0.884 |
| `structural` under 0.40 | 44.7% | 10.3% |
| `stem` under 0.40 | 88.2% | — |

**Roughly a third of a scanned page's exported symbols are marginal detections
the exporter treats as certainly true.** That is the largest single body of
discarded evidence in the pipeline.

⚠️ **This is not an argument for fusing confidence everywhere.** §4.3 finds it
separating at one site; §4.5 cites it measured flat at another. It is an argument
that the number should survive to where the question can be asked.

**Sites that discard a computed real number at the moment they refuse** —
twenty, from the module-by-module map made for this survey:
`_drop_clipped_notehead_fragments` (confidence);
`_dedupe_cross_staff_detections` (both confidences, both band distances, the
ladder rung counts); `_apply_roster_range_veto` (both confidences);
`_drop_unladdered_noteheads` (confidence and rung count);
`_reconcile_measure_to_meter` (the residual of every near-miss candidate);
`_flag_measure_count_inconsistency` (consensus strength, overridden by a tier);
`clef_locator` (ink fraction; the refined **symmetry score**; the geometry
`residual`) — ⚠️ with a wrinkle worth stating exactly: `locate_clef` takes an
optional `trace` dict and DOES record the symmetry and the rejecting branch into
it, but **neither of `transcribe.py`'s two call sites (`:1677`, `:4286`) passes
one**, so in production every one of those numbers is discarded and only
benchmark probes have ever seen them;
`clef_correction.propose_clef` (the whole `fits` dict, at every exit);
`clef_correction`'s treble override (eight boolean conjuncts sitting on top of a
proposal that already carries `fit`, `current_fit` and `margin` — none of the
three participates); `slots.map_groups` (`best_cost`);
`contextual._fill_defaulted_clefs` (the cross-system clef tally — unanimity is
required, so a 4:1 tally fills nothing and the tally is dropped);
`key_signature_vote._trustworthy` (the weight, surviving only inside a prose
`reason` string); `time_signature_locator` (every per-staff NCC score, on the
refusal path); `instruments.Match.coverage`; `roster.py:219`;
`export.measure_dynamics` (per-letter confidence); arc attribution (the
clearance numbers); `template_matcher` (two NCC floors).

---

## 4. The measurements that decide specific sites

### 4.1 `_dedupe_cross_staff_detections` — the largest overlapping population, and confidence is WEAKLY informative

20-row scan gate, `OMR_CONTEST_DUMP=1`, `out/contests/`. **4,521 contested
pairs**, matching the range-veto session's figure exactly — the control that the
re-run reproduces the gate.

| which tier decided | n | share |
|---|--:|--:|
| **distance** (the documented coin flip) | **4,255** | **94.1%** |
| ladder | 266 | 5.9% |
| range / hairpin | **0** | 0% |

⚠️ **The range tier fires zero times, as documented** — `_staff_written_ranges`
returns `{}` with no dossier and the gate runs dossier-free by protocol.

⚠️ **And a stronger statement than "94% by distance" is available.** The ladder
speaks only on noteheads and the hairpin rule only on wedges, so for most
categories distance is the *only* rule that could ever apply:

| category | n |
|---|--:|
| structural | 2,197 |
| **dynamic** | **869** |
| notehead | 816 |
| ornament | 215 |
| accidental | 198 |
| flag / rest / clef / time-sig / stem | 226 |

**3,705 of 4,521 contests (82%) are in categories where, on this corpus, no
tier above distance spoke at all.** (The hairpin rule could in principle reach a
wedge-class contest; empirically rank 1 fired zero times, so it did not.) The 869 dynamic contests are the same population the dynamics-band work
found: 83% of re-attributed letters are the target staff's *sole* evidence,
because distance had already removed the twin.

**Does confidence carry ownership information?** Tested against the ladder as an
internal gold standard (§1.3):

| tier that decided | n | P(winner conf > loser conf) | 95% CI | median &#124;Δconf&#124; |
|---|--:|--:|---|--:|
| **ladder** (trusted) | 264 (+2 exact ties) | **0.617** | [0.558, 0.674] | 0.028 |
| distance | 4,233 (+22) | 0.545 | [0.530, 0.560] | 0.069 |

**Above chance — the CI excludes 0.500 — but only just, and the margin on the
trustworthy pairs is tiny (median 0.028 against a typical inter-copy difference
of 0.069).** So confidence is real evidence about ownership and it is weak
evidence. That is the honest reading, and it is what a cross-staff duplicate
should produce a priori: both boxes are crops of the same ink, so confidence
mostly answers *"is this a notehead"*, not *"whose notehead is it"*.

Reach of a confidence tier under rank 0 — how many verdicts it would overturn:

| threshold | pairs overturned | share of distance-decided |
|---|--:|--:|
| any difference (a plain tie-break) | 1,925 | 45.5% |
| &#124;Δconf&#124; > 0.10 | 712 | 16.8% |
| &#124;Δconf&#124; > 0.20 | 302 | 7.1% |
| &#124;Δconf&#124; > 0.30 | **143** | **3.4%** |

⚠️ **A plain tie-break is refused on these numbers**: 1,925 swaps on a signal
that agrees with the trusted tier 62% of the time is a large bet at low odds,
and the precedent is exact — the roster range veto made **52** swaps and note
recall moved **+2**, "right about as often as it is wrong". A *thresholded*
tier at |Δconf| > 0.30 (143 pairs) is a bet of comparable size to that one and
can be priced the same way. **T5 fails outright**: no corpus records which staff
owns a contested glyph, so the deciding number has to be scan-gate note recall,
not a calibration curve.

### 4.2 `absent_instrument` — the graded window is REFUSED, on its own numbers

The veto Sean's principle most obviously targets: it *strips a name* rather than
lowering a total. Over the whole-work extract (88 pages, 1,616 staff records,
962 labelled): **109 veto records** — Trombone ×75, Contrabassoon ×10,
Piccolo ×6, Violin ×10, Viola ×6, Cello ×2.

It already computes the obvious grading axis, `distance_pages` (how far the
staff sits from the nearest page attesting that instrument), and uses it only
through a hard interval test at window 0. The distances spread **1 to 42**, so
T1 passes easily. **T2 fails:**

```
distance_pages: 1:3  2:6  3:2  4:3  5:8  6:3  7:8  12:8  13:7  14:3  15:3
                16:4 17:4 18:3 19:10 20:1 21:6 22:6 24:6 25:3 26:3 27:2
                28:1 32:3 42:3
```

The module's own record splits these into **91 removals of names the movement
cannot contain** (Trombone / Contrabassoon / Piccolo — Beethoven's trombones
enter in the finale) and **18 refusals on reduced finale systems that no corpus
can adjudicate** (the strings). Those two populations are *interleaved on
distance*: at distance 12 the eight records are 4 Violin + 2 Viola + 1
Contrabassoon + 1 Piccolo; at 13, four Trombone plus one each of Violin, Viola,
Cello; at 19, three Trombone + one Contrabassoon + four Violin + two Viola.

**There is nothing here for a graded window to grade on** — which independently
corroborates the module's own sweep (cost flat at 18 vetoes for every window
0–7, benefit falling monotonically 91 → 58).

⚠️ And the refinement that *does* work at this site is already there, and it is
a **logical** one rather than a graded one: `_anchored_keys` exempts a staff
whose slot its own system's arithmetic forces. That is T3 in action — the
exemption is a constraint, so it is exact and needs no threshold. It is also the
model for how the other identity gates should be widened.

### 4.3 `export.measure_dynamics` — the clearest conversion in the pipeline

The function assembles adjacent dynamic-letter detections into a word and drops
the run **entirely** unless the word is in `_DYNAMIC_WORDS`. Replayed over both
families with the function's own assembly:

| | scan | engraved |
|---|--:|--:|
| letter runs assembled | 437 | 177 |
| exported (a legal word) | 392 (89.7%) | 169 (95.5%) |
| **REFUSED, dropped whole** | **45 (10.3%)** | **8 (4.5%)** |
| refused runs at edit distance **1** from a legal dynamic | **45 / 45 = 100%** | **8 / 8 = 100%** |

What they spelled: `s` ×16, `fs` ×7, `m` ×5, `z` ×4, `mm` ×2, `ffp` ×2, then
`sff`, `ffs`, `ffm`, `fmf`, `pz`, `sm`, `fmp`, `fpp`, `ffz` — every one a legal
dynamic with a letter missing, a letter spurious, or two transposed. (The lone
`s` ×16 is an `sf` whose `f` was missed; CLAUDE.md already names that case.)

**And T2 passes on confidence as well, measured rather than assumed:**

| letter confidence (scan) | p25 | median | p75 |
|---|--:|--:|--:|
| letters in KEPT runs (n=548) | 0.699 | 0.816 | 0.861 |
| letters in REFUSED runs (n=74) | **0.398** | **0.618** | 0.762 |

So a refused run is not noise: it is a legal dynamic disturbed by one
low-confidence letter. Two independent grading axes exist and both separate.
T1 ✓ T2 ✓ T3 ✓ (empirical) T4 ✓ (one `<direction>` in one measure)
T5 ✓ (the 11 scan rows carry hand-verified truth windows and the engraved 11
carry exact truth — the corpus is free).

### 4.4 `clef_register_warning` — REFUSED as a clef-error signal, 0 of 11

`docs/scope-identity-upstream-2026-09-06.md` §9 nominates this as the best lever
available on the clef ceiling, on two structural grounds (it names no
instrument, so it survives where labels do not; it compares two staves, so it
cannot confirm itself) and records that **its reach was unmeasured**. Measured:

**Reach: 7 firings over 193 scan staves (3.6%); 4 over 224 engraved (1.8%).**

**Precision as a clef-error detector: 0 of 11.** Every firing, in both families,
sits at one of three score-order boundaries where the register inversion is what
the page correctly prints:

| the pair it flagged | n | why it is not an error |
|---|--:|---|
| bass-clef **Bassoon** above treble-clef **Horn** | 5 | horns sound above bassoons |
| bass-clef **Timpani** above treble-clef **Violin** | 5 | violins sound above timpani |
| **Horn** above **Horn** (Brahms 1, engraved) | 1 | horns 3/4 above horns 1/2 |

`_flag_clef_register_inversion` (`transcribe.py:3729`) compares **adjacent**
staves with no bracket or family guard, and an orchestral score is ordered by
FAMILY, not by register — so every family boundary is a legitimate inversion and
this check finds those and nothing else. Corroborated independently of the
pipeline's own instrument names on Brahms 1 p1: the 14-staff Breitkopf lineup
puts Pauken at index 8 and Violine I at index 9, exactly the pair reported.

⚠️ This does **not** refute Sean's arrow (`notes → "that clef cannot be right"`).
It refutes *this implementation* of it. A variant restricted to staves inside one
bracket group, or comparing a staff against ITS OWN reading on other systems,
is a different check and needs its own reach measurement before anything is
built. On the corpus here, "inside one bracket group" would have reduced the
reach from 7 to something at or near zero.

### 4.5 `clef_correction` — the fill tier reaches ZERO, and the blocker is not the gate everyone has been discussing

The funnel, replayed over both families with `propose_clef`'s own helpers and
constants:

| | scan (193 staves) | engraved (224) |
|---|--:|--:|
| clef NOT read — the ONLY population the fill tier may apply to | 30 (15.5%) | 2 (0.9%) |
| … and an instrument is known | 26 | 2 |
| **proposals the real pass produced** | **5** | **1** |
| … of which **applied** | **0** | **0** |

**All five scan proposals and the one engraved proposal sit on staves whose clef
WAS read**, so all six are recorded `applied: False`. The fill tier — the only
tier on by default — acted on **nothing, in either family.**

Which exit `propose_clef` takes, per staff:

| exit | clef unread (n=30) | clef read (n=163) |
|---|--:|--:|
| `already_in_effect` — the positional default was right | 14 (46.7%) | 87 (53.4%) |
| `too_few_noteheads` (< `MIN_NOTEHEADS` = 12) | 9 (30.0%) | 53 (32.5%) |
| no usable instrument | 4 | 12 |
| **a proposal survives** | **3** | 6 |
| `range_alone_not_decisive` | 0 | 4 |
| `would_worsen_register` | 0 | 1 |

⚠️ **The three unread-clef proposals are refused by a gate the standing
discussion does not name.** They are the three Bach Brandenburg 3 violas, and
the gate is `contextual.py:1202`'s `_not_clef_evidence = {"score_order",
"roster"}` — the §7 provenance rule as a hard exclusion. All three are
`instrument_source: score_order`, so they never reach `propose_clef` at all.

**This corrects a standing framing.** The recorded claim is that the OVERRIDE
gate's `sources.get(slot) == "label"` conjunct is *"unsatisfiable on scans —
29 of 29"*. True of the population it was measured on (unresolved NON-TREBLE
staves, which print no label), but that is **not** the population where
proposals exist: all five scan proposals are on `label`-named staves. The
measured blockers, in order:

1. `treble_override` is **off by default** (`OMR_INSTRUMENT_CLEF_DEFAULT`) and
   its `TREBLE_OVERRIDE_INSTRUMENTS` allowlist has four entries — this is what
   blocks the read-clef proposals, four of which carry real register margin;
2. the provenance exclusion at `contextual.py:1202` — this blocks all three
   unread-clef proposals;
3. `already_in_effect`, at ~50% of both populations — the positional default is
   simply right about half the time, and no gate is involved.

The proposals, all `label`-named:

```
brahms-p2  s8   Timpani  treble->bass   fits  treble 0.00  bass 1.00   HIGH
brahms-p2  s18  Bassoon  treble->bass   fits  treble 0.57  bass 1.00   HIGH
brahms-p2  s4   Bassoon  treble->bass   fits  treble 0.93  bass 1.00   medium
beet5-575951-p2 s20 Violin alto->treble fits  alto  1.00  treble 1.00  (zero margin)
brahms-p1  s12  Cello    tenor->bass    fits  tenor 1.00  bass  1.00   (zero margin)
```

The Timpani row is a staff read as treble on which **not one of its 14 noteheads
falls inside the instrument's written range under the clef in effect**, and
every one falls inside it under bass. That is the maximum evidence this
mechanism can ever produce, and it is discarded.

⚠️ **The additive term you would reach for first has already been measured and
refused at this exact site.** `clef_correction.py:430`: a confidence ceiling on
the misread treble does not separate — the misread trebles score 0.34 and 0.72
while a *correct* label-named treble (mahler-p3 s11, Violin) scores 0.61. So an
additive form here must sum `fit` / `current_fit` / `margin` and the instrument's
convention, **not** the detector's confidence in the glyph it misread. The two
zero-margin proposals are exactly the cases such a sum would still, correctly,
refuse.

⚠️ And the Bach three are a caution of their own: their `fits` are
`treble 1.00 / alto 1.00` — the register cannot separate them, so the proposal
rides entirely on the instrument's convention ("violas read alto"). They are
right, and they are right for a reason that is not evidence about *this* page.

### 4.6 `MIN_LABEL_CONFIDENCE` — the `coverage` quantisation is DEMOTED again, this time on reach

`instruments.Match.coverage` is a float, bucketed to high/medium/low
(`ocr_folded` → `low` unconditionally, else `>= 0.6` → high), then dropped at
`low` by `slots`, `roster`, `contextual` and `absent_instrument` alike, and
scored at a flat `SCORE_LABEL_MATCH = 6.0` for the two tiers that survive.
Structurally it is the cleanest Class-B site in the pipeline, and the prior art
already demoted it to "a weighting change, not a new probability".

**Measured reach: 1 label dropped at `low` across 193 scan staves; 0 across 224
engraved.** (The one is `Obol.` on beethoven-984073-p1.) A change here moves
essentially nothing on either standing corpus. **Demoted again — now on the
REACH-before-accuracy rule rather than on the calibration rule.**

⚠️ **Its neighbour is 25× larger and is a different fault.** Labels read cleanly
and matched by NO lexicon entry: **15 on the scan family, 10 engraved** —
`Yiolino II.`, `larinetti in B.`, `orni in F I II`, `mpani in C-G`,
`ani in A.D.E.`, `Contrafagott`, `Hr. (Es)`, `Trpt.`, `in C 1 2`. Most are
margin-window truncations, i.e. a reader fault with its own workstream, not a
gate fault. But the *shape* is `measure_dynamics`' shape exactly — an
exact-membership veto over a string one edit from a legal one. ⚠️ That is not
licence to loosen the matcher: CLAUDE.md records that OCR folds are admitted on
RARITY only, that common-letter pairs are refused by name, and that a gated
single-substitution matcher was prototyped, measured collision-free and **not
adopted**. The recommendation here is to RECORD the near-miss and its coverage
(Class C), not to accept it.

---

## 5. Classification table

`class` is the prior taxonomy's A–E. **blocked?** is against the calibration
constraint — *an uncalibrated probability is worse than none* — so a
recommendation is blocked only if it requires a number **called a probability**.
Additive accumulation in evidence units with a threshold, which is what
`slots.py` already does without claiming a percentage, is **not** blocked.

### 5.1 Keep the gate — it is a CONSTRAINT, not an opinion

| site | class | measurement behind the call | blocked? |
|---|---|---|---|
| `slots.align` monotone DP; `absent_instrument._anchored_keys` exact arithmetic | E | forced slots are arithmetic, not evidence — the exemption already prevents one measured regression (Beethoven 5 p1's oboe) | n/a |
| `slots.map_groups` tie-of-different-meanings abstain (`slots.py:379`) | E | degenerate evidence, §1.1. Landed today (`a827fa36`) | n/a |
| `_dedupe`'s written-range veto — *a veto on the impossible* | A | the graded extension has already been run: `OMR_ROSTER_RANGE_VETO` reach 474 of 816 noteheads, 52 swaps, **+24 edits** (`label`-only +8), note recall +2. Shipped OFF | n/a |
| `dossier.slot_facts_for_system` — staff count == part count | E | the forced join measured **F1 0.064** | n/a |
| `export._stitch_slots` refusal on disagreeing staff counts | E | joining by ordinal across suppressed staves grafts one instrument's music onto another. The slot-aware alternative exists (`OMR_SLOT_STITCH`), is measured, and is dormant for metric reasons rather than correctness ones | n/a |
| the empty-gap constants — notehead height, stem cap, dot offset, cut-common fill, the direction-text lexicon | A | prior art; **T1 fails by construction** | n/a |
| `clef_correction`'s "never let a score-order name override a clef that was READ" | A | the hazard is refused independently in three places (`clef_correction.py:396`, `dossier.py:436`, `score_layouts.py:683`) and the range-veto session priced admitting deduced identity at **three times worse** (+24 vs +8) | n/a |

### 5.2 Keep the gate — an opinion, but its grading axis is measured FLAT

| site | class | measurement behind the call | blocked? |
|---|---|---|---|
| `absent_instrument` page window | A/E | §4.2 — `distance_pages` 1–42, fully interleaved between the 91 correct removals and the 18 unadjudicable ones | no |
| `MIN_LABEL_CONFIDENCE` / `roster.py:219` `low` drop | B | §4.6 — reach **1 label / 193 scan staves, 0 / 224 engraved** | no |
| `clef_correction` treble override — the *detector-confidence* term specifically | A | measured at the site: misread trebles 0.34 and 0.72, correct treble 0.61; no threshold separates | no |
| `clef_register_warning` as a clef-error term | C | §4.4 — **0 of 11 firings is a clef error**; it detects family boundaries | no |
| `_dedupe` rank-0 confidence as a plain TIE-BREAK | D | §4.1 — 1,925 swaps (45.5%) on a signal that agrees with the trusted tier 0.617 of the time. The thresholded form is a different recommendation, §5.4 | no |

### 5.3 RECORD THE SCORE, KEEP THE GATE — free, byte-identical, and the prerequisite

| site | class | what to record | blocked? |
|---|---|---|---|
| all five internal-consistency checks | C | they already compute it — give it a home and state each consumer's cost-when-wrong. **140 signals scan / 21 engraved, all inert** (§3) | no |
| `clef_locator` symmetry, ink fraction, geometry residual | A→C | the machinery already exists — `locate_clef(trace=...)` records the score and the rejecting branch — and **neither pipeline call site passes a trace**. Cheapest item on this list | no |
| `clef_correction.propose_clef` | A→C | the `fits` dict and the exit taken, at **every** `return None`. §4.5 had to reimplement the function to learn that ~50% of both populations exit at `already_in_effect` | no |
| `_dedupe` per-pair band distances and ladder rung counts | D→C | `OMR_CONTEST_DUMP` already records confidences and the deciding tier; it does **not** record the distances, which is the quantity documented as a coin flip | no |
| `key_signature_vote` rejection weights | D | today they survive only inside a prose `reason` string. **23 of 193 scan staves have a key reading rejected** by the vote (`key_signature_unread_reason`) | no |
| `time_signature_locator` per-staff NCC scores on the refusal path | A | the 0.70 floor discards them. The docstring records that *ranking by median score* was measured and refused — a reason to keep the GATE, not to discard the SCORE | no |
| `instruments.Match.coverage`, on the `Match` consumers see | B | reach is ~0 today (§4.6), but the float is what a roster vote or a suggest-and-choose picker would need | no |
| `contextual._fill_defaulted_clefs` cross-system tally | D | unanimity is required, so a 4:1 tally fills nothing and is dropped; both standing benchmarks are single-page and cannot see this at all | no |

### 5.4 CONVERT to additive — measured, with the axis measured informative

| site | class | recommended shape | measurement | blocked? |
|---|---|---|---|---|
| `export.measure_dynamics` letter-run membership | A/E | score candidate words by letters matched minus letters inserted/deleted, **weighted by the missing or spurious letter's own confidence**; emit the best if it clears a floor, record the run otherwise | §4.3 — 45/45 and 8/8 refused runs at edit distance 1; refused letters p25 0.398 vs kept 0.699 | **no** |
| `clef_correction` treble-override allowlist | A/E | replace the four-name allowlist with an additive term over `fit − current_fit`, the instrument's convention, and `score_layouts`' already-measured treble asymmetry (`SCORE_TREBLE_CONFLICT` −0.3 vs `SCORE_CLEF_CONFLICT` −1.5) | §4.5 — 4 declined proposals with real margin, one at `current_fit 0.000` over 14 noteheads | no |
| `contextual.py:1202` provenance exclusion — **FILL tier only** | A | a `score_order` name lowers the term rather than removing the staff. The fill tier cannot overwrite a read clef, so the blast radius is bounded by construction (T4) | §4.5 — 3 refused proposals, all Bach violas, all correct. ⚠️ see §7 item 8 | no |
| `_dedupe` rank-0 confidence, **thresholded** | D | one more tier UNDER rank 0, pairwise (never a cluster winner — measured and rejected), firing only at &#124;Δconf&#124; > 0.30 | §4.1 — 143 pairs, a bet the size of the range veto's 52 | T5 fails; price on note recall, not calibration |

---

## 6. Ranked shortlist

**1 · Record the refusals.** *(§5.3, the Class-C sweep.)* Every gate above
writes the number it refused on, alongside the refusal. **Payoff:** it makes
items 2–5 decidable — and it is exactly why this document could measure
`measure_dynamics` and `absent_instrument` from disk while `_dedupe` needed a
re-run and `propose_clef` needed a reimplementation. **Risk:** near zero; no
consumer, output byte-identical. **Measured by:** an assertion that both
families' MusicXML is byte-identical, plus this benchmark's probes re-running
against the richer JSON. **Harness needed:** none. ⚠️ Ship it with no consumer,
per §1.5.

**2 · `export.measure_dynamics` → nearest legal word, confidence-weighted.**
**Payoff:** 45 scan runs and 8 engraved, every one at edit distance 1; on scans
dynamics are *under*-emitted (376 words against a truth of 491), so this pushes
the right way. **Risk:** low — one `<direction>` per measure, flag-off
byte-identical. **Measured by:** both standing benchmarks (`wrong dynamic` is a
musicdiff bucket), with the deciding number being words-correct-per-staff from
`benchmarks/omr-dynamics-band-2026-09/probe_dynamic_band.py` rather than pooled
OMR-NED — the metric rewards emitting more symbols, and a change this small
sits inside the ±6-edit noise floor either way. **Harness needed:** none.

**3 · `clef_correction`: turn the override tier on, with the allowlist replaced
by an additive margin term.** **Payoff:** the largest per-error cost in the
pipeline — a wrong clef transposes every note on its staff — against four
proposals on the scan family with real margin, one at maximum available
evidence. **Risk: the highest on this list**, and the one item where §1.4's
asymmetry cuts *against* conversion: the gate's failure (a recorded
`applied: False`) is visible, the sum's failure is not. Mitigating it,
`apply_proposal` restates pitches in place, so the change is directly visible in
note recall. **Measured by:** scan-gate note recall per row, plus
`benchmarks/omr-clef-string-staves-2026-09`'s per-staff clef truth.
**Harness needed:** none — but ⚠️ this is coupled to the held
`OMR_INSTRUMENT_CLEF_DEFAULT` decision and should not be moved unilaterally.

**4 · `_dedupe` rank-0 thresholded confidence tier.** **Payoff:** the largest
overlapping population in the pipeline — 4,233 distance-decided pairs, 82% of
them in categories no better tier can reach. **Risk:** the signal agrees with the
trusted tier only 0.617, so at a 0.30 threshold this is a 143-swap bet, the same
size as the range veto's 52 (which returned +2 matched notes for +8 edits).
**Measured by:** a `scan_eval` A/B — ⚠️ give each arm its own `--tag=` (it needs
the `=`); a cached A/B reports "identical on every bucket" and the tell is wall
time, not the numbers. Read note recall first: `wrong note` is 29.6% of this
pool and the metric alone will be ambiguous. **Harness needed:** none.

**5 · `contextual.py:1202` provenance exclusion, FILL tier only.** **Payoff:**
3 staves on one row — small, and honest about it. **Risk:** the feedback loop
three modules independently refuse, bounded here because the fill tier cannot
overwrite anything a reader read. **Measured by:** scan-gate note recall on the
Bach row (a clef fill restates pitches, so it *is* visible).
**Harness needed:** none.

**6 · The identity harness, which everything upstream of these is blocked on.**
⚠️ **Neither standing benchmark can see identity at all** — part names do not
reach musicdiff. Items 3 and 5 are measurable only because a clef change moves
*pitches*; the identity decisions that produce those clefs are not, and neither
are items in §5.3 that touch naming. Phase 0 of
`docs/scope-identity-upstream-2026-09-06.md` is the prerequisite and its gate is
the right one: *if it cannot reproduce today's known faults it is not a
harness.* It is also the corpus T5 needs before any of these sums may be called
a probability.

---

## 7. What I refused, and why

**1 · Converting everything to additive.** §1.1. A hard logical constraint is
not a stain; it is the only kind of information that cannot be wrong. Seven
sites in §5.1 are constraints, and softening them would let the pipeline emit
impossibilities.

**2 · A graded `absent_instrument` window.** Measured, §4.2 — the distance
distribution is interleaved between the correct and the unadjudicable removals.
This is the site whose *form* most offends the governing principle and it is
still the wrong site to convert; the sharpest illustration of T2.

**3 · `clef_register_warning` as a clef-error term.** Measured, §4.4 — 0 of 11.
Offered as a correction to `docs/scope-identity-upstream-2026-09-06.md` §9's
nomination, not as a disagreement with the arrow that document names.

**4 · Reviving the `coverage` quantisation as a headline item.** Measured, §4.6
— reach 1 of 193. It fails the prior art's own REACH-before-accuracy rule and
belongs in §5.3, not higher.

**5 · Loosening `instruments.lookup` or the direction-text lexicon to catch the
25 unmatched labels.** CLAUDE.md records the lexicon gate as load-bearing, OCR
folds as admissible on rarity only, common-letter folds as refused by name, and
a gated single-substitution matcher as prototyped, measured collision-free and
**not adopted**. My finding there is Class C (record the near-miss), not Class A.

**6 · Calling any of these sums a probability.** The standard stands: P(name)
ECE 0.1277, P(set) 0.1301, top bin promising 0.989 and delivering 0.692. Every
recommendation above is stated in **evidence units with a threshold**.

**7 · Converting `_dedupe`'s ladder or range tiers.** The ladder is a physical
join; the range is a veto on the impossible; and the graded version of the range
tier has already been built, measured (+8 / +24 edits) and shipped off — with a
lesson that constrains half of §5.4 and is worth restating: **a rule whose input
is a scan's resolved pitch cannot be better than that pitch is.**

**8 · Extending the provenance relaxation to the clef OVERRIDE tier.** §5.4
recommends it for FILL only, where the blast radius is bounded by construction.
On the override tier the measured hazard is on the other side and is recorded
three times independently.

**9 · A plain confidence tie-break at `_dedupe` rank 0.** §4.1 — 1,925 swaps at
0.617 reliability. The thresholded form is what is recommended, at 143.

**10 · Building any of it.** The commission said analysis. This branch changes
no pipeline behaviour and no default.

---

## 8. Reproducing

Fixtures are gitignored build products, so in a worktree point the probes at the
main checkout with `OMR_FIXTURE_ROOT`.

```
export OMR_FIXTURE_ROOT=/Users/seanjohnson/Desktop/ReEngrave
P=benchmarks/omr-additive-vs-gated-2026-09/probe

python3 $P/probe_gate_reach.py              # 3    gate firing rates, both families
python3 $P/probe_register_warning.py        # 4.4  every clef_register_warning, adjudicable
python3 $P/probe_clef_proposals.py          # 4.5  the clef funnel as the pipeline ran it
python3 $P/probe_propose_clef_branches.py   # 4.5  which `return None` each staff takes
python3 $P/probe_fill_population.py         # 4.5  is the fill population noteheadless?
python3 $P/probe_clef_provenance_gate.py    # 4.5  what contextual.py:1202 refuses
python3 $P/probe_dynamic_runs.py            # 4.3  refused dynamic runs + edit distance
python3 $P/probe_low_labels.py              # 4.6  the `low` drop and its neighbour
python3 $P/probe_absent_veto_scale.py       # 4.2  the veto at document scale

OMR_SURYA_KEEP_ALIVE=0 python3 $P/dump_contests.py   # ~50 s/row x 20 rows
python3 $P/analyse_contests.py                       # 4.1
```

Every output is committed under `out/`; the per-row contest dumps are under
`out/contests/`.

⚠️ `dump_contests.py` writes to this benchmark's own `out/`, never to the scan
gate's `fixtures/`, and sets `OMR_SURYA_KEEP_ALIVE=0` — **never blanket-kill
`llama-server`**; a shared instance is up, and killing one destroyed another
agent's multi-hour run on 2026-09-06.

⚠️ `probe_propose_clef_branches.py` REIMPLEMENTS `propose_clef`'s branch
structure (using that module's own helpers and constants) because the function
records nothing at its exits. **If those constants or that branch order move,
this probe goes silently stale** — which is itself the argument for shortlist
item 1.

⚠️ The scan family here is the 11 committed `.graft09` fixtures (11 pages); the
contest dump covers all 20 gate rows because it re-runs them. Where a figure is
quoted "over 193 staves" it is the 11-page set; where it is quoted over 4,521
pairs it is the 20-row set. They are different denominators on purpose and
should not be mixed.
