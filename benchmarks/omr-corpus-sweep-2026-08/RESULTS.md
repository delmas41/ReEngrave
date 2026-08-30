# Corpus sweep — the first wide baseline — 2026-08-30

220 pages sampled from ten scores, **3359 staves, 90 629 noteheads, 22 532
measures, 0 crashes**, 56 minutes. `sweep.jsonl` is the artefact; re-run
`sweep.py --summarize` to reproduce every table here.

For scale: the clef accuracy set is 52 hand-read staves and the key-signature
set 42. This is **64×** the former. It carries no ground truth and measures
behaviour, not correctness — but that turns out to be enough to move three open
questions.

## The headline number is worthless; read the per-score table

| | |
|---|---:|
| clefs from the detector | 67.5% |
| clefs **defaulted** (a positional guess) | **31.1%** |
| key signatures read | 48.2% |

True, and it describes no page in the corpus. Per score:

| score | pages | staves | clef detected | clef defaulted | keysig read |
|---|---:|---:|---:|---:|---:|
| wtc | 20 | 210 | 100% | 0% | **96%** |
| handel-red | 40 | 500 | 100% | 0% | 89% |
| kirchhoff | 6 | 44 | 100% | 0% | 84% |
| handel-lead | 40 | 568 | 86% | 14% | 80% |
| pastoral | 14 | 289 | 51% | 45% | 36% |
| lamer | 23 | 371 | 39% | 59% | 27% |
| mahler5 | 40 | 696 | 53% | 44% | 24% |
| beet5-imslp | 15 | 271 | 62% | 35% | 22% |
| bolero | 7 | 149 | **100%** | 0% | 19% |
| beet5 | 15 | 261 | **19%** | **79%** | **10%** |

Keyboard and small-format printing is effectively solved. Dense orchestral
scanning is not, and **Beethoven 5 rests 79% of its pitches on a positional clef
guess**. Three of the four conclusions this project corrected this week were
numbers pooled across these two populations.

## The two key-signature failure modes are separable, and they are not the same problem

Splitting the unread reasons by score separates them completely:

| score | no clef read | no accidentals found | rejected | keysig read |
|---|---:|---:|---:|---:|
| beet5 | **187** | 47 | 2 | 10% |
| lamer | 160 | 91 | 18 | 27% |
| mahler5 | 282 | 215 | 33 | 24% |
| pastoral | 100 | 81 | 5 | 36% |
| beet5-imslp | 83 | 110 | 19 | 22% |
| **bolero** | **0** | **116** | 4 | 19% |
| handel-red | 0 | 56 | 1 | 89% |
| wtc | 0 | 8 | 0 | 96% |

Corpus-wide: **892 staves blocked by the clef, 765 by finding no accidentals, 83
rejected.** The clef dependency is real and is the larger bucket — but it is not
the whole story, and on Boléro it is not the story at all.

## Boléro is the finding

**Zero staves blocked by the clef — every clef read — and 116 of 149 staves still
report no key signature. And Boléro is in C major.**

Those staves have nothing to find. The reader looked at a measured header window,
under a known clef, found no accidentals, and reported *"neither the detector's
markers nor the CV locator found key-signature accidentals"* — which is filed as
a failure to read. The pipeline was right and did not know it.

`key_signature_read` already draws exactly the distinction that is being lost:
`True` means the zeros are a reading, `False` means nothing could read the staff
and 0/0 is a default. A clean header under a known clef with no accidentals in it
is a **reading of an empty signature**, and it is being recorded as the opposite.

### Why that matters more than a truthfulness fix

It is the missing prerequisite for the C-major problem
(`benchmarks/omr-unknown-keysig-2026-08/`). Half the staves in this corpus —
**1740 of 3359** — are exported as C major without evidence, and their notes are
resolved with no key alteration. The proposed repair is to fall back to the
system's majority, and the trap identified there is that it would overwrite the
staves which genuinely print no signature: horns, trumpets, timpani, and every
part of a work like Boléro.

**A reader that can assert an empty signature removes that trap**, because the
fallback can then be applied only where the signature is genuinely unknown rather
than everywhere it is absent. The order is therefore:

1. **Let the reader confirm an empty signature** where the clef is known and the
   header window was measured, so `key_signature_read` becomes true where it
   should be and the honest count of unknown staves drops from 1740.

   > ⚠️ **The safety claim originally written here — "output pitches do not
   > change" — is FALSE, and was measured false on 2026-08-30.**
   > `transcribe.py:2926` passes
   > `skip_key_sig_detection=(cell_idx == 0 and staff_idx in voted_fifths)`, so
   > changing *membership* of `voted_fifths` changes which staves run the
   > in-measure key reader — and the two readers are not equivalent
   > (`_key_sig_read_from_dets` abstains where `_detect_key_sig_from_cell`
   > falls back to counting). Implemented as written, on La Mer p.12 it costs
   > **5 key signatures and 27 of 140 altered notes** on a single 14-staff page.
   > The trace that stopped at `alterations_for_fifths(seeded_fifths or 0)`
   > missed a second consumer sixty lines below. Anyone building this must start
   > from that gate, not from the seeding line.
2. **Then the majority fallback**, applied only to what is left, with the
   instrument transposition (`default_fifths_offset`) so it does not print the
   majority's signature on a transposing part.

Boléro is also the natural **negative control** for step 1 and for the
accidental-role work: 149 staves, perfect clefs, C major. Anything that starts
asserting signatures there is producing false positives.

## What did not go wrong

Worth recording, because a sweep that only reports problems is not a baseline.

- **Zero crashes over 220 pages**, including the one-line-staff pages that were
  raising `cv2.error` this morning.
- **Seven pages detected no staves, and all seven are page 0** — a title page per
  score. No content page was silently skipped.
- **No page detected 1-2 staves**, so there is no partial-detection failure mode
  hiding between "works" and "sees nothing".
- `phase1_warning` fires on 563 measures and `rhythm_reconciliation` corrected
  114 — both proportionate to 22 532 measures rather than symptomatic.

## Using it

This file is a snapshot; `sweep.jsonl` is the thing to diff against. Re-run the
sweep after a change and compare, and the question "what did this do outside the
three pages I was aiming at" has an answer.
