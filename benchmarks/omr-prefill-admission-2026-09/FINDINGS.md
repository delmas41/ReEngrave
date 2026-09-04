# Pre-fill admission signals — what separates the 8 errors (2026-09-03)

The measured handoff left the pre-fill at **precision 0.84 exact / 0.94 kind**
over 50 boxes on six completely-labeled Brahms cells, and ranked
"confidence-banded admission" as the highest-value next idea: turn the one
number into a precision/coverage curve and admit only from the clean end.
This benchmark asks the question the idea depends on: **which recorded
signals actually separate the 8 errors from the 42 correct boxes?**

`probe_admission.py` recomputes the pre-fill live through `mxl_verdicts`'s
own functions, replicates `score_cell`'s greedy IoU matching per box (the
pooled numbers reproduce the recorded run exactly — 50 / 42 / 47), and prices
each candidate admission policy. Run from the repo root:

```bash
python3 benchmarks/omr-prefill-admission-2026-09/probe_admission.py
```

## The table

| policy | n | coverage | precision exact |
|---|--:|--:|--:|
| P0 admit everything (the recorded figure) | 50 | 1.00 | 0.840 |
| P1 exact-position alignment matches only (`near`=False) | 44 | 0.88 | **0.818** |
| P4 cell `strength_exact` ≥ 0.75 | 43 | 0.86 | 0.814 |
| P5 cell `strength_exact` ≥ 0.9 | 33 | 0.66 | 0.879 |
| S size veto alone (defer small heads to the human) | 47 | 0.94 | 0.872 |
| C parity-consistent cells only | 40 | 0.80 | 0.900 |
| V everything, variant re-derived from the reference | 50 | 1.00 | 0.880 |
| **P7 composite: matched + parity-consistent + not-small + ref-variant** | 37 | 0.74 | **1.000** |

## What the signals turned out to mean

**1. The alignment's own confidence signals are the WRONG axis — one is
anti-correlated.** All six `near` (one-step-off) matches are exact-correct,
so filtering them *lowers* precision (0.840 → 0.818). And cell
`strength_exact` misranks: the cleanest cell in the set (`p3-s5-m5`, 6/6
exact) has the LOWEST `strength_exact` (0.333), while every error sits in
cells at 0.75–0.917. Banding on the aligner's scores — the obvious reading
of "confidence-banded admission" — buys almost nothing here.

**2. Parity consistency is the cell-level signal that works.** For each
cell, ask whether its exact-correct boxes agree on ONE mapping between the
reference note's diatonic parity and the printed on-line/in-space variant.
Five of six cells agree; the one that cannot (`p2-s3-m4`, offsets {0,1}) is
exactly the cell holding all 3 unmatched phantoms and the third flip — 4 of
the 8 errors. A pairing that puts reference notes on the wrong detections
scrambles parity, so inconsistency is a symptom of exactly the failure the
admission gate needs to catch, and it separates the cell that
`strength_exact` cannot (0.75 vs the clean cell's 0.333).

**3. The reference already knows the line/space variant, and the pre-fill
throws that away.** `expected_head_class` keeps the DETECTOR's variant by
design ("position and size the detector read — only the KIND"). But the
alignment key *is* the reference's staff position: whenever the pairing is
right, the reference's variant is the printed one at exactly the same
confidence. Re-deriving the variant from the matched truth note fixes 2 of
the 3 flips outright (`p4-s10-m5` #8/#10, IoU 0.39/0.41 boxes whose class
becomes right even though the box stays where the detector put it), abstains
on the third (its cell is parity-inconsistent), and breaks nothing among the
47 checked. This is a pre-fill code change with measurable value BEFORE any
detector improvement.

**4. The size veto closes the grace ceiling as a deferral.** A box below
0.85× the cell's own median in BOTH dimensions catches both grace heads
(41×38, 44×45 against 51–83 wide neighbours) at the cost of deferring one
correct box. Deferred, not relabelled — the human decides; nothing is
claimed about what a grace note is.

## ⚠️ How to read the 1.000

The composite's 37/37 is **in-sample on n=50, on the same biased six cells
the 0.84 came from, with the policy chosen while looking at the 8 errors.**
It is a demonstration that the errors are separable by signals already in
(or derivable from) the records — a ceiling, not a claim. The out-of-sample
test is a RANDOM completion pass scored with the same probe. What survives
that pass decides what `mxl_verdicts` may admit as labels.

Two of the three error families also confirm the structural claim from the
measured handoff: the flips and phantoms are the DETECTION's placement, so
the whole curve should shift up with better weights and no pre-fill change —
tested below.

## Shipped, same day (Phase A)

The mechanisms above landed in the pre-fill itself (see version_memory.md
2026-09-03): the variant follows the matched reference note on exact pairs,
within-measure tie chains collapse by the reading — a fifth signal, found by
the conflict review, using the same gate tremolo has — every decision now
carries an admission tier (`labels` / `queue` with reasons, a flip demoting
its whole cell), and `--score` prices the tiers. Six-cell A/B: **exact
0.840 → 0.880**, kind unchanged, and the built-in labels tier reads
**22/22 = 1.000 at 0.44 coverage** — stricter than P7 above because at
pre-fill time there is no human-calibrated parity, so any detected flip
demotes its cell. Batch conflicts 5 → 4: `s3-m6`'s tie chain resolved
(both blank-paper hints gone); `s2-m2` stays a conflict because the READING
shows two heads at the position — a duplicate detection the re-ship should
clean up, at which point it resolves itself; the two accidental-glyph
conflicts remain deliberately. The tiers are still metadata: nothing is
auto-admitted until the random completion pass re-prices them out-of-sample.

## Phase B — the claim is TRUE: precision follows the detector

"Pre-fill precision is downstream of recognition" was the measured handoff's
structural finding and the reason to keep the approach open. It is now
tested against a real change of weights, **with no pre-fill code changing**.

The intended arm was the imgsz-2048 re-ship, which is not blessed yet — so
the test used a weight change that was already available and is exactly the
same shape. **The batch's committed `transcription.json` was made with the
PRE-hollow `imgsz2048-ft-30ep` checkpoint**, while scan-domain production is
now `hollow-ft-2026-09-03` (the weight-routing fork sends scans there).
Two arms through `rerun_on_weights.sh`, everything else identical:

| on the six scored cells | pre-hollow | **hollow-ft** |
|---|--:|--:|
| precision exact | 0.880 | **0.961** |
| precision kind | 0.940 | **1.000** |
| recall exact (of human boxes) | 0.468 | **0.521** |
| labels tier | 22 boxes @ 1.000 | **44 boxes @ 1.000** |
| queue tier | 28 @ 0.786 | 7 @ 0.714 |
| WRONG_CATEGORY / extra hints | 3 / 26 | **0 / 9** |

| across the batch | pre-hollow | **hollow-ft** |
|---|--:|--:|
| TP / WRONG_CATEGORY | 174 / 16 | **191 / 5** |
| extra hints (read, unexplained) | 200 | **58** |
| missing hints (reference notes not found) | 20 | **15** |
| CONFLICTs | 4 | **0** |
| admission labels : queue | 136 : 54 | **188 : 8** |

**Every channel moves the same way at once**, which is what makes this a
recognition result rather than a threshold trade: more confirmations, fewer
relabels, fewer unexplained read heads, AND fewer reference notes missed.
The coverage of the trustworthy tier doubles — 22 → 44 boxes of ~50, still
at precision 1.000.

⚠️ **The obvious objection is that hollow-ft just detects less**: noteheads
across the three pages fall 4260 → 2419. The control that settles it is the
MISSING-hint count, which asks the opposite question — how many notes the
reference holds that the reading never found. It falls too (20 → 15;
4 → 3 on the six cells). A detector losing real heads raises that number.
⚠️ **CORRECTED, same day, by the training session's independent finding: that
sentence was true of NOTEHEADS and over-general about the rest.** The
hollow-family weights are now known to suppress **rests and accidentals**,
and the cause is a labeling gap rather than the detector —
`benchmarks/omr-labeling-survey-2026-09/NEXT_ITERATION.md`: the completion
pass over these cells labeled only black noteheads and augmentation dots, so
every rest and accidental in them trained as background. The same signature
shows in this arm's own numbers, which I reported and did not read: rests
fall **1380 → 951** across the three pages. And the missing-hint control is
**weak for rests specifically**, because `prefill_cell` drops rests from the
alignment on condensed staves (`include_rests=not condensed`) and a
conductor's page is full of them — so it is a good control for noteheads and
close to blind for rests. Everything above about noteheads stands; "what it
lost was junk" does not extend to the rest of the class space.

What it lost in NOTEHEADS was junk, and the pipeline's own filters had been
saying so:
unladdered noteheads dropped 1063 → 304, clipped edge fragments 259 → 104.
Page segmentation is byte-identical between the arms (706 measures, 83
staves), so this is the detector and nothing else.

**Two predictions from the Phase A writeup, both confirmed:** `s2-m2`'s
conflict was called "a duplicate detection the re-ship should clean up" — it
is gone, along with the other three; and the labels tier's coverage was
expected to climb with the detector, which it did (0.44 → 0.86 of proposed
boxes).

**What this does NOT say.** It is not the imgsz-2048 re-ship measurement:
when that checkpoint is blessed, run `rerun_on_weights.sh` on it and add a
column. It is still the same six biased cells — the numbers move together,
but 51 boxes is 51 boxes, and only the random completion pass turns any of
this into an admission policy. And the pre-fill still proposes noteheads
only, so `recall` here remains a fraction of a complete human pass.

⚠️ **Practical consequence for the labeling batch: its committed
`transcription.json`, and therefore its committed `prefill/` hints, are
stale by one production checkpoint.** The hints being labeled against are
the 0.880 / 200-extra-hint set, not the 0.961 / 58 one. Refreshing is safe
and cheap — re-transcribe with current production weights, then
`mxl_verdicts --write-hints`, which writes `prefill/` and leaves `verdicts/`
and `detections/` untouched, so no human work and no detection id is
disturbed. Left for the batch's owner rather than done here, because the
batch is served live by another session.

## Phase C — the answer: NOT admissible. The pre-fill stays a queue.

Sean labeled **49 cells completely and blind** in one sitting — the 25
pre-registered, plus 24 more. The pre-registered analysis is the one that
counts, and it says the `labels` tier does **not** generalise:

| set | boxes | exact | labels tier |
|---|--:|--:|--:|
| **pre-registered 25 (THE committed analysis)** | **74** | **0.838** | **0.849** |
| other 24 (out-of-sample, not pre-registered) | 67 | 1.000 | 1.000 |
| **pooled out-of-sample** | **141** | **0.915** | — |
| the six (IN-sample — where the tiers were fitted) | 51 | 0.961 | 1.000 |

The bar was set in advance: **≳0.97 admits, a material drop keeps the
queue.** Every honest reading of this table is under it — the pre-registered
0.849, and even the most generous pooled 0.915. **Pre-filled boxes are a
review queue, not labels.** The in-sample 1.000 was the six dense cells
telling us about themselves.

**Two ways it could have been wrong, both ruled out.** The blind server's
access log shows all 49 cells saved through it, so the labels never saw the
hints. And for every one of the 12 errors there is **no human box of the
pre-fill's class overlapping the pre-fill box at all** — so the scorer is
not stealing a neighbour at IoU 0.3; these are genuine disagreements.

### Why it dropped — and why the admission signals could not see it

⚠️ **The Phase A tiers were fitted to the six cells' error MODES, and the
random sample fails differently.** Every policy in the probe lands between
0.815 and 0.859 — the signals simply do not fire: `near` is 0 on all 12
errors, `parity_ok` is 1 on 10 of them, `small` is 0 on 11. There is
nothing here for a confidence band to separate.

| error family | n | what it is |
|---|--:|---|
| line/space flips | 6 | the box centre sits 23–51 px (¼–½ staff space) off the human's hand-drawn box; both detector AND reference name the position from a misplaced box, and the human labels the ink |
| **rest VALUE disagreements** | 4 | `restQuarter` where the human reads `rest8th`, at IoU 0.65–0.82 — the SAME glyph, so this is the reference's rest duration against the printed one |
| a whole rest read as a notehead | 1 | genuine misread |
| unmatched grace-sized box | 1 | the known grace ceiling |

⚠️ **The reference-variant rule from Phase A is a NO-OP on this data** — it
overrode the detector on **0** boxes across all three sets, because under
`hollow-ft` the detector's variant already agrees with the reference. It
earned its keep under the older weights (2 of 3 flips) and costs nothing
now, but it is not what is holding the number up, and it cannot fix a flip
whose cause is a misplaced BOX.

**Rests are the weak class, and they are new.** Out-of-sample: noteheads
**116/123 = 0.943**, rests **13/18 = 0.722** (0.500 on the pre-registered
set's ten). The six dense cells could not have shown this — they print
almost no rests. This is the same seam the Phase B correction opened: rests
are where the reference and the page disagree most, and where
`prefill_cell` is weakest (it drops rests from the alignment on condensed
staves entirely).

### What follows

- **Do not admit pre-filled boxes as labels.** The queue reading in CLAUDE.md
  stands, now on out-of-sample evidence rather than caution.
- **A noteheads-only admission is the only variant worth another look**
  (0.943 out-of-sample), and it is still short of the bar. Rests should
  probably not be proposed at all until the reference-vs-printed value
  question is understood.
- **The 49 labeled cells are the real yield of this session** — complete,
  blind, and exactly the rests-and-accidentals completeness
  `NEXT_ITERATION.md` step 1 asks for on this batch.
