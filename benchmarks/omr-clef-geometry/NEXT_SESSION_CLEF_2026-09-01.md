# Handoff — the clef locator's false positives are a POSITION problem

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

**Current baseline, shipped config (clustering ON):**

```
77 of 206 located (37.4%)
reference 5/5 exact | coverage 7/9 | orchestral misses 5 | sweep misses 7
                                                        | FALSE POSITIVES 48
                                       (7 Beethoven + 41 Mahler)
```

Plus: `pytest tools/omr/tests` — 1095 passed when this was written, with 9
failures in `test_staff_labels_surya.py` that are not clef work and were being
repaired by another session at the time; see the last section.
`benchmarks/omr-score-order/eval_score_order.py` 11/12, 5/10, 23/23.
`eval_pipeline_clefs.py --contextual --dossier --assist vision` 69/69, base-3
52/52, about a cent.

---

## The job: refuse a cluster that ends before the staff begins

**Measured ceiling, on both editions** — `probe_false_positive_geometry.py`,
which reports how far each located cluster's right edge sits from the first
column of the staff's own printed lines, in staff spaces:

| corpus | removes | costs |
|---|---:|---:|
| mahler5-clef-sweep | **27 of 40** false positives | **2 of 64** real clefs |
| beethoven5-clef-sweep | 0 of 6 | 0 of 59 |

Neutral on Beethoven for a reason worth understanding rather than working
around: every Beethoven false positive is a real clef misread, sitting on the
staff where a clef belongs. The rule is aimed at a family Beethoven does not
contain — Edition Peters prints the stacked instrument numbers (`1/2`, `1/2/3`)
and the brace's curl to the LEFT of the system's bracket, close enough to fall
inside the header window, and a column of numerals is glyph-sized and
vertically symmetric, so the leftmost-glyph-sized-cluster rule takes them.

**Why this and not a symmetry threshold.** The previous handoff's lead was a
tenor symmetry floor. It separates the two populations cleanly on Beethoven
(gap +0.015) and is impossible on Mahler (overlap 0.137) — real tenor clefs run
down to 0.708 there and tenor misreads reach 0.845. Refused with numbers; see
`clef_symmetry_populations.py` and `RESULTS.md`. Shape cannot separate a numeral
stack from a C clef, because the numeral stack really is symmetric. Position
can.

### What it has to clear before it ships

1. **Nottebohm coverage must not fall.** 77/206 today. There the clef sits at
   the staff start, so the rule ought to be free — but that is the prediction,
   not the measurement, and this area has a long record of predictions like it.
2. **reference 5/5 and piano 0.** Non-negotiable.
3. **Both sweeps.** The Mahler number should improve and Beethoven's should not
   move; anything else means the rule is doing something other than what the
   probe measured.
4. **The 2 real clefs it costs.** Look at them before accepting the trade — if
   they share a cause (a staff whose lines are traced short, say) the rule may
   be fixable rather than merely priced.

### The measurement trap it already fell into once

The probe's first version took the staff's left edge to be the leftmost
horizontal ink and concluded every staff begins at column 0. At canonical scale
a bold serif's crossbar clears a 1.5-space horizontal opening, so the instrument
name and the numerals leave "horizontal" fragments at the far left. Keeping only
components at least four staff spaces wide fixed it, and the misread median
moved from −1.00 to +0.90. **When a geometric probe says a property holds for
everything, suspect the operator before the data.**

---

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

## Not clefs, and moving while this was written: the label ladder

A rebase during the 2026-08-31 session replayed the Surya commit (`937bd2e`,
"labels: wire Surya in as the free tier") on top of the rename that made
`assist` a required argument (`3c33a32`, "human and vision are both tiers now"),
and the conflict resolution kept the old parameter name in three places:
`contextual.py` (`can_read_margin = vision_fallback`, a NameError on every
call), `transcribe.py:3523` (still passes `vision_fallback=` to
`apply_contextual_analysis`, so the contextual pass inside `transcribe` raises
TypeError and is silently caught — "contextual analysis failed"), and nine tests
in `test_staff_labels_surya.py` calling `_labels_for_page(...,
vision_fallback=...)`.

**Another session was actively repairing this while the clef work was being
committed** — `contextual.py` and the tests both changed under it. None of it is
touched by the clef commits, and the state above may already be stale: check it
rather than trusting this paragraph. It is recorded only so that a
"contextual analysis failed: TypeError" line in a benchmark run, or a red
`test_staff_labels_surya.py`, is recognised as that and not as clef work.

The clef benchmarks are unaffected either way: `check_clef_precision.py`,
`probe_clef_rejection.py`, `clef_symmetry_populations.py` and
`probe_false_positive_geometry.py` all run Phase 1 plus the locator and never
touch the label ladder, and `eval_pipeline_clefs.py` performs its own contextual
pass rather than the one inside `transcribe`.
