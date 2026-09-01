# Handoff — the clef locator, after position beat shape three times

> Written at the end of the 2026-08-31 session, which executed
> `NEXT_SESSION_CLEF_2026-08-31.md` in full. Everything below is measured and
> reproducible from the harnesses named in it.

## Run all of it, every time

```bash
# from the repo root — coverage
python3 benchmarks/omr-clef-geometry/probe_clef_rejection.py \
    --pdf ~/Downloads/Nottebohm-Beethovens-Studien-1873.pdf
# precision: reference + piano + spot check + BOTH sweep editions
python3 benchmarks/omr-clef-geometry/check_clef_precision.py \
    --nottebohm ~/Downloads/Nottebohm-Beethovens-Studien-1873.pdf
```

The LilyPond corpora are gitignored and built once:
`cd benchmarks/omr-clef-geometry && lilypond reference-clefs.ly
piano-false-positives.ly` — the "fatal error" it ends on is harmless.

**Current baseline, shipped config (clustering ON, position rule ON):**

```
77 of 206 located (37.4%)
reference 5/5 exact | coverage 7/9 | orchestral misses 7 | sweep misses 24
                                                        | FALSE POSITIVES 5
                                       (1 Beethoven + 4 Mahler)
```

Plus: `pytest tools/omr/tests` — **1118 passed, 0 failed**.
`benchmarks/omr-score-order/eval_score_order.py` 11/12, **3/8**, 23/23.
`eval_pipeline_clefs.py --contextual --dossier --assist vision` 69/69, base-3
52/52, about a cent.

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

### The next job, in order

1. **DO NOT re-open the five staves with no dots in the window.** Four ideas
   were built and measured and all four are refused — the merged-pair
   signature (109 of 123 real C clefs carry one), a harder staff-line strip
   (zero effect at any dilation), a bigger search window (zero effect at any
   padding), and a proportion floor on the candidate (real clefs run narrower
   than the misreads). The dots are on the page and not in the mask, so the
   only route left is a reader that goes back to the grayscale print rather
   than the shared ink mask — a real piece of work with a ceiling of four false
   positives. Full write-up in `RESULTS.md`; do not spend the afternoon again.
2. **TAKEN: the single-dot veto** (`dot_single_clear_is_enough`), FALSE
   POSITIVES 13 → 5. The only non-free change in this area: 8 removed for 20
   declined C clefs. Watch two things if you revisit it — `eval_score_order`'s
   read-clefs arm fell from 10 named/5 correct to 8/3, the one number that got
   worse; and `eval_pipeline_clefs` holds 69/69 only because `slot_continuity`
   picks up what the locator drops, which is worth knowing before leaning on
   the locator alone anywhere new.
3. **The other shape cases** are turned away on aspect or height even by the
   loose tier. The sweep table in `RESULTS.md` shows the cost column staying at
   zero out to aspect 3.0 and height 1.40, so there may be a little room — but
   re-measure rather than extrapolating off that table, which was taken on a
   different survivor population.
4. **The two treble false positives are out of reach of any dot rule.** A G clef
   has no dots. They need a different veto or nothing.
5. **A third edition.** Two editions have now each shown a false-positive family
   the other could not. `sweep_located_clefs.py` builds the corpus and
   `check_clef_precision.py` picks it up with no code change; the cost is an
   afternoon of reading glyphs. Pick a different publisher again.

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
