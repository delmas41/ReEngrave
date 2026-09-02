# Infer the key signature from the music — measured, and the answer is NO

**2026-09-01, phase 1 (research only — nothing in `tools/` was changed).**
Roadmap #4b / handoff item #9, explicitly wanted by Sean.

The idea does not survive its own ceiling. Measured on GROUND TRUTH, where
every printed accidental is read correctly by construction, the strongest form
of the rule **speaks on 3.4% of parts at page scale and is wrong 63% of the
time it speaks**. On the page that motivated the item it points away from the
answer; on the cleanest page in the corpus, which the pipeline already reads
perfectly, it would speak and be wrong.

That is the headline. The more useful result is what looking for the signal
found instead, because **both pages cited as evidence for #9 were attributed
wrongly**, and the real defect is somewhere nobody was looking:

> On Beethoven 5 p.15 three staves read the correct **three flats** and the
> cross-page vote threw all three away, because the page's reference was set by
> exactly **two** readings — one detector, one CV locator, each under-counting
> the same signature as **one flat** — and the three correct readings carry
> weight 0.50 because their clef was defaulted, which bars them from the
> reference by design.

The page then asserts one flat on six staves that print three, and abstains on
sixteen. Nothing in that chain is a detection problem, and nothing in it is
helped by inferring anything from the music.

---

## Reproduce

```bash
# the ceiling, on ground-truth MusicXML — no OMR, seconds
python3 benchmarks/omr-keysig-from-music-2026-09/probe_ceiling_bounds.py --works 120 --window 8
python3 benchmarks/omr-keysig-from-music-2026-09/probe_ceiling_from_truth.py --works 60 --window 8 --clean-only

# what a page actually carries, and where it sits (transcribes once, then cached)
python3 benchmarks/omr-keysig-from-music-2026-09/probe_keysig_signal.py \
    --pdf ".../IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf" \
    --page 15 --dpi 600 --label beet5-p15

# what the cross-page vote was shown, and what it did with it
python3 benchmarks/omr-keysig-from-music-2026-09/probe_vote_inputs.py \
    --pdf ".../IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf" \
    --page 15 --dpi 600 --label beet5-p15
```

`ground_truth_p15.json` is the irreplaceable part — the hand-read signature of
every staff on Beethoven 5 p.15, which had none before. Everything else
regenerates.

---

## 1. Attribution — what is actually wrong on the failing pages

### The count that has been quoted, and the two things it fuses

"33 inline flat detections on the page" is the evidence #4b rests on. Split it
by WHERE the detections sit and it stops meaning what it was read as. An
accidental in the staff-start cell, left of that cell's first notehead, is the
**printed key signature**; everything else is the music's own chromaticism, and
only the second could feed an inference layer. Measured on p.15:

| Beethoven 5 p.15, 22 staves | flats | sharps | naturals |
|---|--:|--:|--:|
| **signature region** (staff-start cell, left of the first notehead) | 21 | 3 | 2 |
| **inline** (paired to the note it alters) | 12 | 4 | 19 |

Most of the flats people have been counting are the signature itself.

### beet5 p.15 — (a) printed, detected, READ CORRECTLY, and then discarded

Not (b) undetected — that diagnosis was already corrected once, in
`benchmarks/omr-keysig-blindspot-2026-08/`, and this measurement corrects it
again in the other direction: the pipeline no longer merely detects the flats,
it **fits them to the slot table and gets the right answer**, on three staves.

The class-role half of the 2026-08-29 finding is confirmed and now has a
number. Of the 21 flats standing in the signature region, **2 carry the
`keyFlat` role and 19 are `accidentalFlat`** — 9.5%. The detector gets the
glyph right and the role wrong, as reported.

But the role is no longer what costs the page. `probe_vote_inputs.py` prints
what `key_signature_vote.reconcile` was handed:

```
sys ord  read    wt                 source   verdict
  0   7    2b  0.50  template_default_clef   rejected: 2 flats differs from the system's 1 flat
  0   8    1b  0.50  template_default_clef   kept:     agrees with the system's 1 flat
  1   1    3b  0.50  template_default_clef   rejected: 3 flats differs from the system's 1 flat
  1   7    3b  0.50  template_default_clef   rejected: 3 flats differs from the system's 1 flat
  1   8    3b  0.50  template_default_clef   rejected: 3 flats differs from the system's 1 flat
  1   9    1b  1.00               detector   kept:     agrees with the system's 1 flat
  1  10    1b  1.00             cv_locator   kept:     agrees with the system's 1 flat
  reference per system: {0: '1b', 1: '1b'}
  modal tally (weight >= 1 only): {'1b': 2.0}
```

Seven readings on a 22-staff page. Against the hand-read truth
(`ground_truth_p15.json`, corroborated by the 500 dpi crop in `crops/`):

| ordinal | part | printed | read | what happened |
|--:|---|--:|--:|---|
| 1,1 | Oboi | **−3** | −3 | **rejected** |
| 1,7 | Violino I | **−3** | −3 | **rejected** |
| 1,8 | Violino II | **−3** | −3 | **rejected** |
| 0,7 | Violino I | −3 | −2 | rejected |
| 1,9 | Viola | −3 | **−1** | kept — wrong |
| 1,10 | Violoncello e Basso | −3 | **−1** | kept — wrong |
| 0,8 | Violino II | −3 | **−1** | kept — wrong |
| 0,9 / 0,10 | Viola, Vc/Cb | −3 | **−1** | *carried* — wrong |
| 0,0 | Flauti | −3 | **−1** | measure pass — wrong |

**Final page state: 0 staves correct, 6 staves asserting one flat where the
page prints three, 16 abstaining.** Delete the vote's rejection and the same
readers give **3 exactly right**.

Two mechanisms produce that, and both are in `key_signature_vote`:

1. **`_modal_reference` drops every reading weighted below 1.0**, which is
   `DEFAULTED_CLEF_WEIGHT = 0.5` — the weight the template reader gets when it
   ran against a positional clef guess. On a page where 8 of 22 clefs are
   defaulted that is deliberate and, in isolation, right: a signature fitted
   against a guessed clef is a guess squared. Here it hands a 22-staff page to
   a two-vote minority.
2. **The two votes that survive both under-count.** Viola and Vc/Cb print three
   flats and were read as one, by the detector and the CV locator respectively.
   The module's own founding asymmetry — *"the reader loses accidentals and
   never invents them"* — is TRUE of exactly these two readings, and the vote
   nevertheless promotes them to the page's reference. `_modal_reference` even
   breaks ties toward FEWER accidentals (`-abs(f)`), which is the wrong
   direction for a corpus of under-counters.

⚠️ The rejection is also lossy in the way `omr-keysig-blindspot` predicted: a
rejected staff ends at 0, not at whatever it had. On this page it ends at 0 on
staves that had the right answer.

### bolero p.10 — (c) the page reads very nearly as printed, and the citation is wrong

Roadmap #4b and PROJECT_STATUS #9 both cite *"Boléro p.10 reads five different
signatures across 32 staves (0,1,2,4,5 sharps) for a piece in C major"* as
evidence of a missed signature. **The page prints five different signatures.**
It is Ravel's parallel-harmony passage at bar 153: the two piccolos are
notated in E and G over a C-major orchestra, with the clarinet in D.

| ordinal | part | **printed** | read | source | weight |
|--:|---|--:|--:|---|--:|
| 0 | piccolo 1 | **4♯** | 4♯ | detector | 4.00 |
| 1 | piccolo 2 | **1♯** | 1♯ | detector | 1.00 |
| 3 | clarinet | **2♯** | 2♯ | detector | 2.00 |
| 2 | Fl. | 0 | **1♭** | template | 1.00 |
| 6 | Tamb. (percussion) | – | **1♭** | template | 1.00 |
| 7 | Celesta | 0 | **1♭** | template | 1.00 |

Four of the five distinct values are read CORRECTLY, from the detector, at a
weight equal to the number of accidentals actually printed. The whole error is
**five spurious single flats, every one of them from the template reader, on
staves whose header prints nothing** — including a percussion staff.

Check (b) "catching only 1 of them" is not a miss either. 4♯ against a concert
C is outside `consistent_written_set(0) = {−3,0,1,2,3}`, so what check (b)
flags is Ravel, and that flag is the false positive.

⚠️ **An inference layer would make this page worse.** Any rule that reconciled
32 staves to one concert key would overwrite the three signatures Ravel
actually wrote.

Why nothing catches the five bad readings: the vote reports
`kept: no majority to check against`. The modal tally is
`{1♭: 5.0, 1♯: 2.0, 2♯: 4.0, 4♯: 8.0}` — the mode holds 8/19 = 42% of the
weight, under `min_majority = 0.5`, so the vote stops checking and keeps
everything. On a genuinely polytonal page that guard is structurally
unavailable, and the template reader is the one source in the stack that can
over-count.

---

## 2. The signal — measured at its ceiling first, then on the pages

### What evidence about a signature can exist at all

Only three kinds of printed mark say anything, and one of them dominates:

* a **natural** exists to cancel something, so a natural on letter L is
  evidence that the signature alters L;
* a printed **flat/sharp** on L is weak evidence that the signature does *not*
  already alter L that way;
* a bare notehead says **nothing** — which is the whole reason a signature has
  to be read rather than deduced.

Note-distribution fitting is excluded up front: per-staff key-profile fitting
was measured as noise in `benchmarks/omr-clef-key-fit-2026-08` (median
best-vs-2nd margin 0.0000) and is not reused here.

### The ceiling, on ground truth

MusicXML's `<accidental>` is exactly what is printed, so the question "could
this work with perfect recognition?" is free to answer. `probe_ceiling_bounds.py`
builds the strongest form of the rule — not a score but an INTERVAL, speaking
only when one signature survives:

* every letter carrying a clean natural must be altered by the signature, and a
  signature alters a **prefix** of the circle order, so the deepest such letter
  is a floor;
* a letter carrying a clean flat is not already flattened, so it is a ceiling;
* an accidental on the same pitch **earlier in the same bar** makes a natural a
  bar-local cancellation, not a signature cancellation — dropped;
* an accidental on the same pitch in the **previous bar** makes the natural a
  courtesy — also dropped.

118 works, 773 parts, from the Gradus reference library:

| scope | correct | wrong | silent | contradiction | acc. when it speaks | speaks on |
|---|--:|--:|--:|--:|--:|--:|
| whole movement, courtesy kept | 23 | 56 | 460 | 234 | 29.1% | 10.2% |
| whole movement, **courtesy dropped** | 49 | 36 | 489 | 199 | **57.6%** | 11.0% |
| 8-bar window, courtesy kept | 86 | 301 | 8739 | 418 | 22.2% | 4.1% |
| 8-bar window, **courtesy dropped** | 119 | 205 | 8955 | 265 | **36.7%** | 3.4% |

An 8-bar window is what one staff of one page actually offers. **36.7%** is the
ceiling there, with perfect recognition and every refinement applied.

Three things in that table are worth naming separately:

* **The courtesy filter is worth almost twice the accuracy** (22.2% → 36.7%),
  which is a good sign the model is the right shape and a bad sign about the
  headroom: the single largest correction still leaves it wrong twice as often
  as right.
* **26% of parts are self-contradictory over one movement** (199/773). No
  single signature explains their accidentals, because music modulates. That is
  not noise to be tuned away; it is the premise failing.
* **The successes are concentrated where the rule changes nothing.** Of the 49
  correct movement-scope answers, **25 are C major** — the value the pipeline
  already defaults to. On parts that are *not* C major it is 24 correct against
  33 wrong.

Scoring rather than bounding does not rescue it. `probe_ceiling_from_truth.py`,
same corpus, pooled across a movement's parts in concert space through each
part's *true* offset (the most generous assumption available):

| | correct | wrong | silent | acc. when it speaks |
|---|--:|--:|--:|--:|
| C, 8-bar window, pooled, naturals model | 13 | 103 | 315 | **11.2%** |
| C, 8-bar window, pooled, set model | 8 | 40 | 383 | 16.7% |
| C, 8-bar window, pooled, the roadmap's flats model | 3 | 42 | 386 | 6.7% |

⚠️ **A methodological correction, recorded because it nearly produced a false
positive.** The first cut of this probe reported every margin as 0.0 and I read
it as a bug. It was the model: naturals bound a signature from BELOW only — a
natural on B is equally consistent with 1, 2, 3 … flats — so every candidate
tied at the top and the tie-break silently picked one. An under-determined
model reports confident answers unless a tie is made an abstention.

### On the actual pages

`probe_keysig_signal.py` pools a page's inline evidence and runs the same two
models. The ladder is the score for every candidate signature, and the truth is
marked:

**Beethoven 5 p.15** — 22 staves, 2 systems, printed **3 flats**, 19 inline
naturals / 12 flats / 4 sharps:

```
7b:19  6b:13  5b:7  4b:-5  [3b:-7]  2b:-13  1b:-13  0:-19  1#:-13 … 7#:19
```

The truth scores **−7** on a ladder whose top is +19, and the best is a tie
between 7♭ and 7♯ (margin 0 — it would abstain, by accident rather than by
judgement). The inline evidence on the page that motivated this item points
**away** from the page's own answer.

**WTC I p.17** — the page that killed the last two inference ideas, and the
control for a page the pipeline reads perfectly: 12 staves, all 12 read 4♯
correctly, 48 signature-region sharps for 12 × 4 printed. Inline: 16 naturals,
44 sharps, 0 flats.

```
7b:16  6b:16  5b:14  4b:14  3b:6  2b:0  1b:-2  0:-16  1#:-16  2#:-14  3#:-14
[4#:-6]  5#:0  6#:2  7#:16
```

**The truth scores −6 and ranks 11th of 15**, below the neutral point, on a
ladder whose top is +16. The naturals model picks 6♭/7♭ (tied with 7♯); the
roadmap's flats model picks **7♯ with a margin of 44**, its most confident
reading anywhere in this study. A rule speaking
into gaps would not fire here (there are none) — but a rule allowed to
correct, or to set a page reference, would corrupt the one page in the corpus
that is currently perfect.

The mechanism is general and it is why no tuning fixes this: **chromatic
cancellation names letters in no circle order**, and the flat order `BEADGCF`
absorbs an arbitrary set of letters faster than the sharp order does. E major
music borrows D♮, A♮, B♮, C♮ — and the smallest prefix containing {A,B,C,D,E}
is six flats. The estimator is pulled toward many flats by construction, on
sharp pages especially.

**Boléro p.10** — the negative control: **0 inline naturals and 0 inline
flats** on 32 staves. The ladder is flat zero and the rule is silent
everywhere. It behaves correctly on the one page where it also could not have
helped, since Boléro's errors are on staves with no music-borne evidence at
all.

### Abstention, measured as carefully as accuracy

Asked directly: on a control page, how often would the rule speak, and would it
ever speak wrong?

| page | pipeline today | would the rule speak? | would it be right? |
|---|---|---|---|
| beet5 p.15 (3♭, 16 gaps) | 0 correct / 6 wrong | no — 7♭ ties 7♯ | truth ranks 10th of 15 |
| wtc p.17 (4♯, 0 gaps) | 12 correct / 0 wrong | **yes**, both models | **no** — 6♭ or 7♯ |
| bolero p.10 (mixed, 21 gaps) | 6 correct / 5 wrong | no — no evidence | n/a |

It is silent where it is needed, loud where it is not, and its one abstention
on the target page is a tie rather than a judgement.

---

## 3. Transposition reconciliation — the machinery exists and does not do this job

The design would need to turn one movement-level concert key into a **per-staff
written** signature. Two pieces of machinery are cited for that, and they are
not the same thing:

* `key_signature_vote.consistent_written_set(reference)` — check (b)'s
  circle-of-fifths logic. It returns the **set** `{K−3, K, K+1, K+2, K+3}`.
  That is enough for an abstaining consistency test, which is what check (b)
  is, and it is *not* enough to say which of five values a given staff prints.
* `instruments.Match.fifths_offset` — a genuine per-staff offset, derived from
  the "in X" in a margin label by `offset = −fifths(key)`.

So the identity the design rests on is `written = concert + offset`. Measured
across all 97 dossiers, 2462 parts with a known transposition:

| transposition | implied key | expected offset | holds | fails | rate |
|--:|---|--:|--:|--:|--:|
| 0 | C | +0 | 1540 | 68 | **96%** |
| −12 / +12 | C at the octave | +0 | 178 | 2 | 99% |
| **−7** | **F (horns)** | **+1** | 78 | 193 | **29%** |
| **−2** | **B♭** | **+2** | 105 | 164 | **39%** |
| −3 | A | −3 | 29 | 21 | 58% |
| overall | | | 1977 | 485 | **80.3%** |

**The formula holds for the parts that do not transpose and fails for the ones
it exists to serve.** The dominant failure is `printed = 0` where the formula
wants something else — natural brass and timpani are written without a key
signature regardless of the concert key, and a corpus of 19th-century music is
full of them.

Beethoven 5 p.15 is the worked example. Concert key −3, per-staff written
signature from `default_fifths_offset`:

| part | offset | formula | printed | |
|---|--:|--:|--:|---|
| Flauti, Oboi, Fagotti, Violini, Viola, Vc/Cb | +0 | −3 | −3 | ✓ (8 staves) |
| Clarinetti | +2 | −1 | −1 | ✓ |
| **Corni** | +1 | −2 | **0** | ✗ |
| **Trombe** | +2 | −1 | **0** | ✗ |
| **Timpani** | +0 | −3 | **0** | ✗ |

Eight right, three wrong — and the three wrong ones are **exactly the staves
the current C-major default gets right for free**. That is the same trade
`benchmarks/omr-unknown-keysig-2026-08` priced and declined, now with the
corpus-wide rate behind it.

⚠️ **And the labels do not carry the key.** On p.15 the Surya rung labels 14
staves and the contextual pass names all 22, but as `Clarinet`, `Horn`,
`Trumpet` — no "in B♭", no "in Es". So `lookup` falls back to
`default_fifths_offset`, which is +2 for Clarinet, +1 for Horn, +2 for Trumpet:
a default standing in for the one fact that decides the answer, on the
instrument family where the formula is right 29% of the time.

⚠️ **The dossier cannot stand in either, and for a new reason.** The dossier for
this work gives `C Trumpet` and `Timpani` `written_fifths = -3`, because the
modern MusicXML edition it was generated from normalises them — while the 1870s
print in front of the OMR gives them no signature at all. That is 3 of 11
parts, and it is an *edition difference*, not an error in either source. It is
also moot here: the work has 18 parts against a 22-staff page, so the join
abstains as designed.

Where the instrument is unknown, there is no offset at all and the staff can
only take the reference unchanged — which is the naive fallback already
rejected.

---

## 4. Verdict

### NO-GO on inferring the key signature from the music

Not "not yet", and not "blocked on better detection". The ceiling was measured
where recognition is perfect, and at the scope a page provides the rule is
wrong twice as often as it is right. Its successes concentrate on C major,
which costs nothing to get right. On the two pages where it matters it is
silent by coincidence on one and confidently wrong on the other. The failure is
structural: a bare notehead carries no information about the signature, and the
cancellations that do carry information name letters in an order the circle
does not respect.

**What the refusal costs**, stated plainly: Beethoven 5 p.15 keeps 16 abstaining
staves that print a signature, and the 1740-staves-exported-as-C-major problem
in `benchmarks/omr-unknown-keysig-2026-08` keeps its size. Nothing here shrinks
that. What this study says is that the music is not where the answer is — and
that it is still on the page, still detected, and currently being discarded.

### Corrections to the record

* **The Boléro citation for #9 is wrong.** The page prints 4♯/1♯/2♯/0 and the
  pipeline reads four of the five distinct values correctly from the detector.
  Its five errors are template-reader hallucinations of a single flat on empty
  headers. PROJECT_STATUS #9, NOTES.md #4b and
  `docs/next-steps-omr-2026-09-01.md` should stop citing it.
* **The Beethoven 5 p.15 citation is right about the symptom and wrong about
  the cause.** It is not "0 sharps / 0 flats on all 18 staves" any more; it is
  6 staves asserting one flat, 16 abstaining, and three correct readings
  rejected by the vote.
* **`benchmarks/omr-key-signature/RESULTS.md`'s closing line** — *"Inference
  from the music remains parked: the signature is in the window, legible, and
  the readers are close to it"* — is confirmed, and can now be closed rather
  than parked.

### What to do instead, ranked by what these measurements found

**R1. The vote's reference is decided by a minority of under-counters.**
The largest, cheapest and best-evidenced item. Two changes, each independently
testable against `benchmarks/omr-key-signature/eval_key_signatures.py`:

* *A reading rejected by the vote should fall back, not zero.* Already
  identified in `omr-keysig-blindspot-2026-08` as the prerequisite for any
  weak-evidence source; p.15 shows it converting three correct readings into
  three abstentions.
* *A weight-0.5 reading may not vote for the reference — but a reference
  standing on 2.0 total weight against a page of 22 staves should not be
  believed either.* `_modal_reference` returns its share already; the vote uses
  it only through `min_majority`, computed over the readings that voted rather
  than over the staves on the page. A reference resting on 2 of 22 staves is
  not a majority of anything.
* ⚠️ Do NOT simply lower `DEFAULTED_CLEF_WEIGHT`. It exists because a signature
  fitted against a guessed clef is a guess squared, measured: bass staves
  defaulted to treble read three flats as two sharps. The fault is that a
  weightless reading is barred from the reference *and* judged against one.

Expected on p.15: 6 wrong → 0, 0 correct → 3 or more. Must be 0-wrong on
beet5-p2 (10 correct), pastoral-p2 (9), wtc-p17 (10).

**R2. A single template accidental on an empty header should not assert.**
All five Boléro errors, and the guard that would normally stop them
(`strong_weight = 2.0` — "a lone accidental is never enough on its own") is
bypassed when no majority exists. The rule is already written; it is the
`majority <= min_majority` branch that opts out of applying it. Boléro is the
natural regression page: 32 staves, every clef read, three genuine signatures
that must survive and five spurious ones that must not.

**R3. Then re-measure item #8 (routing `accidental*` into the key readers).**
Its measurement — beet5-p2 10 correct → 9 — was taken with the vote in its
current state, and this study explains the loss it recorded: the one staff that
moved was rejected for departing from a system reference, and the rejection
zeroed it. Routing more readings into a vote whose reference is set by two
under-counters amplifies the defect. **Fix R1 first, then re-run #8** — the
class-role gap is real and now quantified at 19 of 21 signature flats carrying
the wrong role.

**R4. `ground_truth_p15.json` is new and should be folded into
`benchmarks/omr-key-signature/ground_truth.json`.** It is the fourth
ground-truth page and the first that is a mid-movement orchestral page carrying
three distinct written signatures for one concert key including natural brass
printing none — which is exactly the shape every candidate fix here has to
survive.

### Test plan for R1/R2, so the next session does not have to invent one

* 0-wrong, non-negotiable, on `eval_key_signatures.py --mode pipeline` over
  beet5-p2 / pastoral-p2 / wtc-p17, plus beet5-p15 from this directory.
* Boléro p.10 as the over-assertion control: 4♯, 1♯ and 2♯ must survive; the
  five 1♭ must not appear.
* `orchestral_eval --omr-ned` unchanged to the edit, or better. The engraved
  benchmark's three works read their signatures from the dossier, so a vote
  change should be invisible there — **and if it is not, that is the finding.**
* `probe_header_windows.py --scores 20 --pages 3` unchanged (233/455), since
  none of this touches the window.

### Do not spend time on these

* **Per-staff key-profile fitting** — noise, `omr-clef-key-fit-2026-08`.
* **Inferring the signature from inline accidentals** — this document.
* **Asserting an empty signature from an empty header** — retracted with
  measurements in `omr-unknown-keysig-2026-08`; a blind staff and an empty
  staff are indistinguishable in the header crop.
* **Applying a concert key to unread staves through `default_fifths_offset`** —
  §3: right 96% of the time for the parts that need no help and 29–39% for the
  horns and B♭ instruments, and wrong on precisely the staves the current
  default gets right.

---

## Method notes

**A probe that only sees one reader's input describes that reader, not the
page.** The `sigreg` column in `probe_keysig_signal.py` counts DETECTOR
detections inside the staff-start cell. The CV locator and the template reader
read a different crop — the measured header window — so a staff can show `-`
there and still have produced a reading. Boléro's five spurious flats are
exactly that case, and only `probe_vote_inputs.py`, which wraps `reconcile`
itself, shows them. This is the same shape as the four failures
`omr-keysig-blindspot-2026-08` closes with, and it caught me once here.

**The ceiling was measured before the pipeline, and that was the right order.**
Two OMR pages and one control cost about three minutes of transcription; the
ground-truth ceiling cost seconds and would have settled the question on its
own. If the answer had come back "the signal is decisive on ground truth", the
OMR measurement would have been the interesting one. It did not.

**Transcriptions here are cached** (`artifacts/*.omr.json`) so the analysis
re-runs free. The transcriptions were taken on `fe13964` with
`tools/omr/rhythm.py` and `tools/omr/dossier.py` carrying another workstream's
uncommitted edits — those touch the time-signature path, not the key-signature
path, but the tree was not pristine and that is worth knowing if a number here
is ever one edit off.
