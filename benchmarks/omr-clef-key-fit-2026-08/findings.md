# Can a clef be recovered from tonal / key context? — No.

**Date:** 2026-08-28
**Verdict:** **DISPROVEN.** None of the four mechanisms tested beats the trivial
"always guess treble" baseline on real transcribe output. Do not build a
clef-from-key-fit corrector; it would fire on noise.
**Reproduce:** `python3 benchmarks/omr-clef-key-fit-2026-08/probe_clef_fit.py benchmarks/omr-real-world/*.json`

---

## The idea under test

From the 2026-08-28 contextual-analysis brainstorm, item #2:

> Pitches depend on clefs, so a tonal estimate built on a wrong clef is
> confidently wrong — which turns key-fit into a *clef* diagnostic. If staff 7's
> pitches fit no key while ten other staves fit D major, re-resolve staff 7 under
> each candidate clef and keep the one that maximizes key fit.

The appeal: it needs no hand input, no new model, no instrument identity, and it
targets the documented #1 failure mode (a missed clef silently defaults to
treble and transposes a whole staff — `transcribe.py:519`).

## Why it is cheap to test

**A clef change is a constant diatonic shift of every notehead.** With
`_CLEF_ANCHORS` mapping each clef to the pitch on the top staff line, reading a
staff under clef `c'` instead of `c` shifts every notehead by
`anchor_index(c') - anchor_index(c)` diatonic steps — a pure integer offset.

So every candidate clef can be evaluated by **arithmetic on stored transcribe
JSON**: no YOLO, no page images, no re-running the pipeline. The whole
experiment runs in about a second over `benchmarks/omr-real-world/*.json`
(5 scores, 80 staves, ~3150 resolved noteheads).

That primitive is reusable and is the one durable output of this investigation
(`clef_shift()` in the probe).

## Data

`benchmarks/omr-real-world/*.json` — stored `transcribe()` results for bach-wtc,
beethoven-5, handel-leadsheet, handel-reduction, ravel-bolero. Ground truth for
the leave-one-out runs is the clef the **detector actually found** on that staff
(all 5 scores have high clef-detection coverage: 83/87 staves).

Gates shared by all experiments: a staff needs >=10 resolved noteheads, a system
needs >=3 staves, and a prediction needs >=2 usable neighbour staves.

## Results

### A. Per-staff key-signature fit — noise

For each staff, re-apply every key signature from -7 to +7 fifths (explicit
accidentals kept, unaccidentaled notes taking the signature) and score the
resulting duration-weighted pitch-class histogram against all 24
Krumhansl-Schmuckler profiles. Take the argmax.

| metric | value |
|---|---|
| staves scored | 80 |
| median margin, best vs second-best signature | **0.0000** |
| staves whose margin is < 0.01 | **62 / 80** |
| argmax agreeing with the pipeline's own read | 5 / 80 |

The argmax is not separated from its runner-up, so it carries no information.
Mechanically: KS correlation always returns *some* best key for *any* histogram,
and sweeping the signature just re-labels mass until something lines up. On top
of that, one orchestral staff on one page is 30–70 notes of a fragment — far
less than the full texture KS was designed for.

### B. Accidental letters vs the circle of fifths — no structure

Hypothesis: a real key signature's accidentals concentrate on a circle-of-fifths
prefix (3 flats = B, E, A), and since the *letters* shift with the clef, the
true clef should show the tightest concentration.

Fraction of paired inline accidentals landing on the first three letters of the
signature order (chance = 3/7 = 0.43):

| candidate clef | flats (n=24) | sharps (n=52) |
|---|---|---|
| treble *(as detected)* | 0.38 | 0.46 |
| alto | 0.54 | 0.35 |
| tenor | 0.42 | 0.56 |
| bass | 0.42 | 0.50 |

Nothing separates from chance, and the true clef is not the winner. Beethoven 5
is the clearest illustration: it is in **C minor (3 flats)**, the pipeline read
**0 sharps / 0 flats on all 18 staves**, and its 16 paired flats scatter across
all seven letters (B:1 E:1 A:4 D:3 G:1 C:5 F:1) under every clef hypothesis.
At this detection quality the accidental letters are noise.

### C. Clef from register ordering against neighbours — below baseline

Leave one staff's clef out, then pick the candidate whose median register best
respects the high-to-low ordering of the staves around it (neighbours keep their
own detected clefs as anchors).

| | |
|---|---|
| accuracy | **38 / 67 = 56.7%** |
| always-treble baseline | **46 / 67 = 68.7%** |

**12 points worse than guessing.** The failure is structural, not a tuning
problem: staff order constrains *relative* register, not absolute register, so
the middle clefs satisfy the ordering constraint most easily and win — alto is
predicted 16 times against 5 true altos.

### D. Clef from fit to the other staves' key consensus — exactly baseline

The literal proposal. Pool the other staves' pitch classes, find the system's
consensus key, then pick the candidate clef whose pitch classes correlate best
with that key's profile.

| | |
|---|---|
| accuracy | **46 / 67 = 68.7%** |
| always-treble baseline | **46 / 67 = 68.7%** |

Identical to the baseline. It recovers the prior, not the clef.

## Why it fails — the structural reason

A staff's note geometry is **clef-invariant**. The engraver chose the clef to
centre the music, so the ink sits in the same place whichever clef you assume;
changing the clef relabels every note by the same interval and preserves every
interval *between* notes. A transposition of the whole staff leaves melodic
shape, contour, interval content and ledger-line count untouched — so scale-degree
and key-profile statistics, which are built out of exactly those quantities, move
together with the hypothesis and cannot discriminate between them.

This confirms, with numbers on real data, what `docs/dossier-verification-plan.md`
§2 already asserted from first principles:

> The only self-diagnosis of a wrong clef: one staff's geometry is clef-invariant;
> symmetry is broken only by an external register anchor (the dossier).

The two evidence sources that *could* break the symmetry are both unavailable at
current quality:

1. **Key-signature glyph positions.** These genuinely are clef-dependent (F# sits
   on the top line in treble, the fourth line in bass). But `main` stores only
   *counts* — `_detect_key_sig_from_cell` counts `keySharp`/`keyFlat` detections
   and discards their positions (`transcribe.py:590`). Positional reading exists
   on branch `claude/key-signature-recognition-57ec0a`
   (`key_signature_geometry.py`), which is where this idea should be retried.
2. **Absolute register**, which requires knowing what instrument the staff is —
   i.e. contextual-analysis item #1.

## Consequence for the roadmap

**#2 is blocked on #1, not independent of it.** The register anchor that every
mechanism here was missing is exactly what instrument identification supplies.
See NOTES.md → "Contextual analysis roadmap".

Retry conditions, if this is ever revisited:
- the key-signature branch is merged, giving glyph *positions* (a clef-dependent
  observable) instead of counts; **or**
- instrument identity exists, giving an absolute register prior; **or**
- notehead + accidental recall on dense orchestral pages improves enough that
  the tonal statistics stop being noise.

## Related dead ends

Same shape as `project_imslp_catalog_concluded` and the ScoreAug domain-augmentation
test (`benchmarks/../scoreaug-fair-test` RESULTS.md): a plausible mechanism,
measured fairly against a trivial baseline, and killed before it shipped.
