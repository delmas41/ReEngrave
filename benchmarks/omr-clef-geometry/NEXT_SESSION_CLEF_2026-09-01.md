# Handoff — the clef layer, after the leverage list was worked to the end

> Written at the end of the 2026-08-31 session, which executed
> `NEXT_SESSION_CLEF_2026-08-31.md` in full. Everything below is measured and
> reproducible from the harnesses named in it.

## Start here — three self-contained jobs, one session each

This work is meant to be picked up by a FRESH session per item; they are
independent and each is small enough to finish. Paste one of these as the
opening message, with this file's path.

> **JOB A — DONE 2026-09-01. Surya is a fixed function of its input; load was
> never the variable.** 45 replays of frozen crop bytes — warm, cold, concurrent
> x4 and x8, mixed with other pages' crops both sequentially and concurrently,
> and 1/8/16 llama.cpp slots — returned ONE answer. The contested character is
> decided at p=0.991 with a 5.53-nat margin, so batching could not have moved
> it, and `_surya_worker` issues one request per system anyway, so a benchmark
> run is not concurrent in the first place. **`SURYA_BAKEOFF_2026-08-31.md` and
> the free-path numbers stand.** Two things it turned up that the next session
> needs: the only sampled path is surya's retry ladder (temperature 0.2 -> 0.8
> on a failed or repetitive request, and silent in production); and the two
> sessions' readings STILL disagree on identical bytes with no version
> difference, which is unexplained. Full write-up: `RESULTS.md`, "JOB A".

> **JOB B — DONE 2026-09-01. It is staff 10, and abstaining is worse than the
> bug.** The two twelves differ at exactly one label: Surya reads `'Tr. Teq.'`
> -> Trumpet (medium, bare alias `tr`) where the paid reader and the page both
> say `Tr Ten.` -> Trombone. The other eleven are character-identical, and staff
> 0 is NOT a difference today — both readers return `'Fl. pic.'`. Mechanism:
> `label_pins` drops any name claimed by two blocks, and one misread inside the
> run both splits the trombones AND gives Trumpet a second block, so four pins
> die from one character, the correct slot-7 trumpet pin among them. Correcting
> that one string reproduces the paid reader's nine dossier clefs exactly.
> DISPROVEN, so nobody re-tries it: dropping the doubtful label gives THREE, not
> nine — an unlabelled staff breaks a run by design, and the recovered trumpet
> pin then costs the three string fills. Gating pins on the lexicon's own
> confidence is exactly neutral. The only fix is reading the character, which is
> a fuzzy-lexicon change and needs the ten-edition validation this project holds
> those to. Full write-up: `RESULTS.md`, "JOB B".

> **JOB C — PARTLY DONE 2026-09-01, and the framing was wrong.**
> `correct_clefs_from_instruments` was not starved because the prior abstains —
> the prior's names were being DISCARDED on purpose, by an exclusion wider than
> its own reason. The circularity it feared needs the SLOT'S OWN clef in the
> prior's evidence, so the gate now states that (`slot not in clef_by_slot`)
> instead of dropping every deduced name. Measured both arms: `--assist none`
> 146 -> **148/166**, `--assist vision` 149 -> **151/166**, base 3 still 52/52,
> no page loses a staff, 23 already-correct defaulted staves named and none
> broken, and on La Mer p.25 it turns a Contrabass staff from treble to bass —
> confirmed against that page's hand-read part list. READ THE COST: both +2
> gains are choral staves on beet9-p120 that the prior calls "Viola", scoring
> only because the truth records the generic `c-clef` and a viola's alto clef is
> one. The clef class is right, the identity is not.
>
> STILL OPEN, and it is the same page: `MIN_NOTEHEADS = 12` in
> `clef_correction.py` now binds, refusing four of the six candidates there — a
> bassoon at 8 noteheads and two violas at 7 and 9 that would all have been
> right, and one at 3 that would have been wrong. Lowering it buys 3 and costs 1
> ON ONE PAGE, which is exactly the shape this area has been burned by three
> times. Get a second edition with hand-read clefs first — Bolero p40 is
> rendered and unread (item 7). The identity half of the original Job C —
> widening `eval_score_order`'s 12-of-33 at 0.92 — is untouched and still the
> biggest lever; note that the prior runs in production on READ CLEFS, where its
> measured precision is 0.50, not the 0.92 of position alone.
> Full write-up: `RESULTS.md`, "JOB C".

**DO NOT START** on the detector's 45-of-113 blind staves (a training problem
with three negative results already: catalog training, domain augmentation, the
clef fine-tune) without a genuinely new idea, and do not re-open the five "no
dots in the window" staves — four approaches measured and refused, in
`RESULTS.md`.

**Environment**, all host-side: weights in `omr-weights/`, the API key for
`--assist vision` in `backend/.env`, and Surya at `.venv-surya` (gitignored —
`python3 -m tools.omr.staff_labels_surya --bootstrap` in a fresh checkout).

---

## Run all of it, every time

```bash
# from the repo root — coverage, over the orchestral scores the sweeps name
python3 benchmarks/omr-clef-geometry/probe_clef_rejection.py
# precision: reference + piano + spot check + BOTH sweep editions
python3 benchmarks/omr-clef-geometry/check_clef_precision.py
```

**ORCHESTRAL SCORES ONLY.** Nottebohm is out of every harness and every test, on
Sean's instruction — for the second time; it had crept back in as the headline
coverage figure. This project processes orchestral scores, and a book of
19th-century vocal-clef counterpoint is not that. Do not reintroduce it, and do
not quote its numbers: coverage on it read 37.4% where the orchestral truth is
8.1%.

The LilyPond corpora are gitignored and built once:
`cd benchmarks/omr-clef-geometry && lilypond reference-clefs.ly
piano-false-positives.ly` — the "fatal error" it ends on is harmless.

**Current baseline** (2026-09-01, everything below re-measured after the
single-dot veto was reverted — do not quote figures from before that):

```
THE NUMBER TO STEER BY — end-to-end clef accuracy on ten hand-read
orchestral pages, 166 staves:

    eval_pipeline_clefs.py --contextual --dossier --wide --assist vision
        149 / 166  (90%)          <- best
    eval_pipeline_clefs.py --contextual --dossier --wide --assist none
        146 / 166  (88%)          <- free path, no API spend

    Job C took both to 151/148 and Job C's identity half gave the two back on
    purpose: they were beet9-p120 choral staves named "Viola" by a layout
    stretched over them, and a viola's alto clef scored against a truth that
    records the generic `c-clef`. Identity precision went 0.73 -> 0.86 for it.
    Steer by these two numbers, but do not read a 2 here as worth more than a
    13-point move in identity precision — this corpus cannot see identity.
    (base 3) 52/52 in both. The base-3 subtotal is three easy pages that
    saturated years ago; report it for continuity, steer by the 166.

THE CV LOCATOR, which supplies 3 of those 166 staves:

    probe_clef_rejection.py      68 of 720 located, Beethoven 5 + Mahler 5
    check_clef_precision.py      reference 5/5 exact | orchestral misses 5
                                 | sweep misses 8 | FALSE POSITIVES 13

    pytest tools/omr/tests                     1116 passed
    benchmarks/omr-score-order/eval_score_order.py    9/10, 2/2, 23/23
    ...and --wide --production, the arm that describes a real run:
        37 named, 32 correct, precision 0.86  (9 pages, 4 editions)
```

`--assist vision` costs a few cents a run; `--wide` needs
`orchestral-clef-truth.json`, and the API key lives in `backend/.env`. Surya is
installed here (`.venv-surya`, gitignored) — re-run
`python3 -m tools.omr.staff_labels_surya --bootstrap` in any other checkout.

---

## SHIPPED — the position rule, and what it left behind

`ClefLocatorConfig.require_cluster_on_staff`, measured on both editions:
**FALSE POSITIVES 48 → 21** (Mahler 41 → 14, Beethoven 7 → 7, exactly neutral),
and Nottebohm coverage went UP 77 → 79 — it SKIPS the margin cluster rather than
rejecting the staff, so the clef behind it is still found. The one genuine clef
it cost was then recovered by `staff_left_max_spaces`, which abstains where the
staff's left edge cannot be measured (sweep misses 9 → 8, nothing else moving).
Measuring that edge from the BAND profile instead was built and refused — it
swallows the instrument name. Guards all held. Both write-ups are the last two
sections of `RESULTS.md`.

### The F-clef veto, done the same way — 21 → 13

The answer was position again, not shape. A misread bass clef's dots sit PAST
the body's right edge (0.94–1.79 w) where a C clef has nothing at all, because a
C clef's near-pairs are fragments of its own strokes. A second, looser reading
of the same two dots is admitted only out there, and the real-clef cost is
**identically zero for every height and aspect tried, on both editions** — where
loosening height at the old 0.55 w position cost 27 clefs. Shipped as a second
tier, so every veto that fired before still fires and the reference, piano and
coverage corpora cannot regress by construction.

### The next job, in order — REWRITTEN 2026-09-01

The four-item leverage list was worked through and two items are dead. Read
`RESULTS.md`'s last three sections before starting anything here.

0. **DONE: the Surya regression is fixed.** A tie at the paid label rung now
   goes to the paid rung (`read and _usable(read) >= _usable(labels)`), because
   a count cannot see that one of the labels it counts is wrong. `--assist
   vision` is back to **149/166** with Surya installed, `--assist none` is
   **146**, and the paid reader is no longer called on every page and used on
   one. **KEEP SURYA.**

   Still open, and small: WHICH of Surya's twelve labels on beet5-p48 makes the
   two twelves behave differently. The reported cause (`Tr. Teq.` at staff 10)
   does not reproduce. The live candidate is staff 0's raw TEXT —
   `'Fl. fl. pic.'` against `'Fl. picc.'`, both resolving to Piccolo — which
   would mean something downstream reads the text rather than the resolved
   label. Worth an hour, not a day.

   TESTED 2026-09-01 and REFUSED: Surya is a fixed function of its input, and
   `--parallel 8` batching is not what moved the label. 45 replays, one answer;
   the contested character sits at p=0.991. Do not re-open the load question.

0b. **DONE: Surya is installed** (`--bootstrap`, `.venv-surya`, gitignored;
   re-run it in any other checkout). Free, ~7.6 s a page, correct where it
   reads — and **net zero end-to-end on this corpus** (145/166 either way). It
   is worth keeping: it takes the dossier from 9-right-of-12 to 9-of-9 by making
   the join abstain where it used to answer wrongly. See `RESULTS.md`.

1. **PARTLY DONE: the ladder's order.** My earlier description of it was wrong —
   the rungs are gated on `_well_covered`, not on emptiness, and Surya already
   replaces the text layer when it reads more. The real bug was that "more" meant
   RAW labels at the free rung and USABLE labels at the paid one; both now
   compare usable, which took beet9-p30 from 9/13 to 10/13. What remains is item
   0, which is a different animal.

2. **INSTRUMENT IDENTITY, which is where the errors actually are.** Seventeen of
   the twenty-one end-to-end clef errors are the positional default calling a
   bass or C-clef staff treble. `correct_clefs_from_instruments` already turns
   an instrument name into a clef, gap-fill only and vetoed by register fit, and
   it applied ZERO corrections across ten pages — starved of names, not broken.
   Hand-supply "Viola" for beet6-p20's slot 7 and it fires immediately
   (`treble -> alto`, fit 1.00, applied). `eval_score_order` says the prior
   names 12 of 33 staves at 0.92 precision, abstaining on two thirds. Every
   staff it can safely name is a staff whose clef stops being a guess. **This is
   the whole game now.**
3. **The part-staff join is NOT broken — it was starved.** The three wrong
   dossier clefs on beet5-p48 are 12/12 correct once the vision reader supplies
   that page's labels. Read this as an instance of item 0, not a separate job.
   RESOLVED 2026-09-01 (Job B): the starvation is one misread character at staff
   10, and it costs three staves because `label_pins` drops a name claimed by
   two blocks. Abstaining on it is measurably worse than the misread.
4. **The detector's blind 45 staves of 113**, where neither the measure cell nor
   the header crop yields a clef. A training question, and the project has three
   negative results on it already (catalog, domain augmentation, clef
   fine-tune). Do not start here without a new idea.
5. **DEAD: `slot_continuity`.** The same slot fails in every system it appears
   in — the same part in the same edition prints the same glyph — so there is
   never a good reading to propagate. Fixing beet9-p60's system grouping (whose
   true boundary scores 324 bridged columns against a within-system median near
   120, i.e. the signal is inverted, not weak) would gain nothing.
6. **DEAD-ish: the CV locator.** Three staves of 166. It is where a whole
   session went; it is not where the errors are.
7. **Widen the ground truth again.** It went 4 pages -> 10 and reversed two
   conclusions. Bolero p40 (34 staves) is rendered and unread.

## Standing rules in this area, none of them optional

* **Run both harnesses on every change.** Every promising change here has looked
  like a large gain on one and lost on the other.
* **Never tune a threshold on one edition.** Three sessions have now produced a
  clean-looking separation that a second corpus closed.
* **A sweep corpus is the only kind that can see a false positive**, because it
  is built from the locator's own reads. `sweep_located_clefs.py` builds one for
  a new score; `check_clef_precision.py` picks up any corpus you add, since each
  names its own PDF. A third edition is an afternoon and no code.
* **Read a sweep's MISS column with care.** At the moment of building, its
  misses are zero by construction.
* **A published measurement of a GLYPH does not transfer to a measurement of a
  CANDIDATE.** Real C clefs measure 0.50–1.26 wide-over-tall as whole glyphs and
  0.15–0.70 as the clusters that survive the morphology. This file has made that
  mistake twice; check which population a number came from before reusing it.
* **Reach for POSITION before shape.** Three times now the separating property
  has turned out to be where the ink stands, not what it looks like: the margin
  numerals (glyph-sized and genuinely symmetric — no shape gate could refuse
  them), the staff's own left edge, and the F clef's dots (whose shape overlaps
  a C clef's stroke fragments completely, and whose position does not overlap at
  all). Each time the shape threshold that looked available was refused by a
  second corpus and the position rule cost nothing.
* **When a measurement disagrees with the truth, ask whether it FAILED before
  trying to make it better.** Twice now the answer has been a bound that lets
  the rule notice its own input is unusable and abstain, not a cleverer
  operator — and the way to find the bound is to look at the whole population,
  where a failed measurement usually sits somewhere no successful one ever
  does (`staff_left_max_spaces`: 173 of 174 staves under 3.55 spaces, the
  failure at 6.77).

## Not clefs, but you will see it: one stale call in `transcribe`

A rebase during the 2026-08-31 session replayed the Surya commit (`937bd2e`) on
top of the rename that made `assist` a required argument (`3c33a32`), and the
conflict resolution kept the old parameter name in three places. Two were
repaired by the session that owns that code (`contextual.py` and
`test_staff_labels_surya.py` — the suite is green again). One remains:

* `tools/omr/transcribe.py:3523` still passes `vision_fallback=` to
  `apply_contextual_analysis`, so the contextual pass *inside* `transcribe`
  raises TypeError and is silently caught. You will see
  `contextual analysis failed: TypeError` in benchmark output. It is not clef
  work, and mapping the boolean `--contextual-vision` flag onto a tri-state
  that deliberately has no default is a design call belonging to that thread.

The clef benchmarks are unaffected: `check_clef_precision.py`,
`probe_clef_rejection.py`, `clef_symmetry_populations.py` and
`probe_false_positive_geometry.py` all run Phase 1 plus the locator and never
touch the label ladder, and `eval_pipeline_clefs.py` performs its own contextual
pass rather than the one inside `transcribe`.
