# The clef sessions, 2026-08-31 → 09-01

Nineteen commits over two days. What shipped, what was refused, what is still
open, and — the part worth reading — where the effort went that should not have.

The detailed measurements live in
[`../omr-clef-geometry/RESULTS.md`](../omr-clef-geometry/RESULTS.md); the
forward-looking list is
[`../omr-clef-geometry/NEXT_SESSION_CLEF_2026-09-01.md`](../omr-clef-geometry/NEXT_SESSION_CLEF_2026-09-01.md).

---

## The headline, in the order it became true

| | |
|---|---|
| CV locator false positives (sweep corpora) | **48 → 13** |
| End-to-end clef accuracy, first ever measured on hard pages | **144/166 (87%)** |
| …after the day's remaining work | **146 free / 149 with the paid reader** |
| Hand-read ground truth | 4 pages, 74 staves, 10 C clefs → **10 pages, 187 staves, 24 C clefs** |
| Tests | 1107 → **1108** |

## What shipped

* **Header clustering on** (`cluster_y_gap_spaces = 1.0`) — held back for two
  sessions on a count taken before any corpus could see it. 69 → 77 located for
  one extra false positive; the rate is flat.
* **A second sweep edition** — `mahler5-clef-sweep.json`, 105 staves of Edition
  Peters, built with a committed tool so a third costs an afternoon.
* **The margin rule** (`require_cluster_on_staff`) — a cluster ending before the
  staff's printed lines is margin ink. FP 48 → 21, and coverage went *up*,
  because it SKIPS rather than rejects.
* **An abstention on the staff's left edge** (`staff_left_max_spaces`) — where
  the lines are too broken to measure, the rule turns itself off.
* **The F-clef dots by position** (`dot_clear_right_fraction`) — FP 21 → 13 at
  zero cost, where loosening the same shape bounds at the old position had cost
  27 clefs.
* **The header crop as a detector gap-fill** — 12 staves move from guessing to
  reading, at 100%.
* **`_usable` at the free label rung** — the paid rung already compared labels
  the lexicon can resolve; the free rung compared raw counts, and `8 > 7` kept a
  worse read. +1 staff.
* **Nottebohm out of every harness and test**, on Sean's instruction — for the
  second time; it had crept back as the headline coverage figure and was
  flattering it by more than 4×.

## What was measured and refused

Nine ideas, each with numbers on both sides. The tenor symmetry floor (a clean
+0.015 gap on one edition, a 0.137 overlap on the second). The band profile for
the staff's left edge (it swallows the instrument name). A merged-dot-pair
signature (109 of 123 real clefs carry one). A harder staff-line strip (zero
effect at any dilation). A bigger dot search window (zero effect at any
padding). A proportion floor on the candidate (real clefs run *narrower* than
the misreads). And the single-dot veto, which was taken on Sean's call and then
reverted when a wider corpus measured it the other way round.

## Where the effort went that should not have

**The CV clef locator supplies three staves of 166.**

Both days went into it — the margin rule, the staff's left edge, the F-clef
dots, the veto and its revert. The work is sound and every measurement holds.
It was aimed at the component with the least end-to-end leverage in the layer,
and taking it from 13-of-24 C clefs to a hypothetical 20 would move the number
that matters by about one percent.

Nothing available at the time said so. The end-to-end benchmark that could have
said so was reporting `52/52 = 100%` on three easy pages — **a benchmark that
cannot go down cannot show an improvement either**, and it had been the headline
for several sessions. The first hour spent widening it would have redirected the
next twelve.

## The transferable lessons

1. **Reach for POSITION before shape.** Three separate fixes, one answer: the
   margin numerals (glyph-sized and *genuinely symmetric* — no shape gate could
   refuse them), the staff's left edge, the F clef's dots. Every shape threshold
   that looked available here was refused by a second corpus; every position
   rule cost nothing.
2. **A corpus built from a reader's own output cannot price that reader.** The
   sweep corpora contain only staves the locator fires on, which makes them
   right for "how often is a read wrong" and systematically misleading for
   "what does this rule cost". They said the single-dot veto removed 8 false
   positives for 16 declined clefs; the unbiased corpus said it lost 5 real
   clefs to gain 1. Ask which staves a corpus contains before trusting it.
3. **Measure end-to-end before optimising a component**, and keep the
   end-to-end benchmark unsaturated.
4. **A published measurement of a GLYPH does not transfer to a CANDIDATE.** Real
   C clefs are 0.50–1.26 wide-over-tall as whole glyphs and 0.15–0.70 as the
   clusters that survive the morphology. This file's predecessors made that
   mistake twice.
5. **When a measurement disagrees with the truth, ask whether it FAILED** before
   trying to make it better. Twice the answer was a bound letting the rule
   notice its own input was unusable.
6. **Never tune a threshold on one edition** — the oldest rule here, and it
   caught the tenor floor.

## Open, and honestly stuck

* **The Surya regression.** Installing the free label reader costs three staves
  in the paid arm — 149 → 146 — and the labels are byte-identical to the paid
  reader's on the page that loses them. The mechanism is not found. `.venv-surya`
  is the switch; the best number this corpus has produced needs Surya absent.
* **45 staves of 113 where the detector sees no clef in either crop.** A
  training problem, with three negative results already on the board (catalog
  training, domain augmentation, the clef fine-tune). Do not start without a new
  idea.
* **beet9-p120 gets no label from any tier**, vision included — seven of the
  remaining errors sit on that one page.
* **The positional default is still the largest error class**: 17 of 21
  end-to-end errors, every one a bass or C-clef staff called treble. Instrument
  identity is worth roughly twelve of them and is blocked on label coverage.
