# Reading instrument labels off the margin with Claude — works

**Date:** 2026-08-28
**Verdict:** **adopted, opt-in.** 100% agreement with the text layer where both
resolve, 30 staves recovered that the text layer's OCR had garbled, zero regressions.
Wired as `vision_fallback=True` in `tools/omr/contextual.py`; off by default because
it costs money.

**Reproduce:**
```
python3 benchmarks/omr-margin-labels-2026-08/make_crops.py --limit 8     # host python
<env-with-anthropic-0.116>/bin/python benchmarks/omr-margin-labels-2026-08/read_crops.py --budget 1.00
```

---

## The problem

`staff_labels.read_staff_labels` gets instrument identity **free** from a PDF's OCR
text layer — but only **18 of 65** IMSLP score PDFs have one, and on those it resolves
**79%** of labelled staves. The residue is garbled OCR a human reads at a glance:
`V}a.` for Vla., `Ve. I I` for Vc., `/A` for Fl., `,/"` for nothing at all.

Instrument identity is the anchor for the whole contextual chain — slots, transposition,
expected clef, written range — so the 72% of scores with no text layer get none of it.

## Ground truth is free

The 18 text-layer PDFs already know the answer. So the vision reader can be **scored on
pages where the answer is known**, before being trusted on scans where it is not. No
hand labelling.

Scoring is on the **resolved instrument**, not the raw string — `Fg.` and `Fag.` are
both Bassoon and both correct.

## Design

**One call per system, not per staff.** A system's margin is a compact vertical strip,
and sending it whole gives the model the context a reader uses: labels form a known
running order, so seeing `Fl. / Ob. / Cl.` above makes a smudged fourth entry legible
as `Fag.`.

**The crop carries staff indices.** A grey gutter is drawn on the left with each staff's
index and a tick at its vertical centre, and the model keys its answer to those numbers.
Matching by order would break on the common case — strings are routinely unlabelled, so
label count and staff count disagree.

**Unlabelled staves must return null**, and the prompt says so explicitly. A model that
invents a plausible instrument is worse than one that abstains: a wrong instrument
propagates through slots into a wrong clef and wrong pitches.

## Results

8 systems, 76 staves, 4 editions of Beethoven 1 and 2. `claude-opus-5`. **$0.087 total.**

| outcome | n |
|---|--:|
| **agree** — both resolve, same instrument | **25** |
| **disagree** — both resolve, differently | **0** |
| **recovered** — vision resolved one the text layer could not | **30** |
| **missed** — text layer resolved one vision did not | **0** |
| both silent — genuinely unlabelled (strings) | 21 |

**Agreement where both resolved: 25/25 (100%).** Vision never lost a label the text
layer had, and never invented one on an unlabelled staff.

Recoveries include the exact OCR failures the text-layer path abstains on:

```
staff 3  text-layer  None            -> vision 'Fg.'       -> Bassoon
staff 4  text-layer  '.'             -> vision 'Cor. (F)'  -> Horn
staff 10 text-layer  'V e. e B.'     -> vision 'Vc. e B.'  -> Cello
```

## Cost

**~$0.011 per system**, and identity is a property of the **score**, not of each page —
slots propagate one reading across every system and page. `contextual.py` caps this with
`vision_system_budget` (default 3), so a few cents covers a whole work rather than a few
cents per page.

## What the pilot caught that nothing else would have

`Tp.` resolved to **Trumpet**, on a staff sitting directly below one labelled `Tr.`.
Rendering the crop settled it: the system reads Fl / Ob / Cl / Fag / **Cor / Tr / Tp** —
Horns, Trumpets, **Timpani**. In this German/Italian convention `Tr.` is Trombe and
`Tp.` is Timpani.

The **vision reader transcribed it correctly**; the *lexicon* was wrong. Fixed by moving
`tp` from Trumpet to Timpani, leaving `Tpt.` as the unambiguous English trumpet form
(regression test: `test_tp_is_timpani_not_trumpet`). A score-order prior (NOTES.md #3)
would settle this from position rather than by convention.

**Scoring trap this exposed:** the first re-score after the fix showed two phantom
disagreements, because the manifest stored the instrument *resolved at crop time*. The
scorer now re-resolves the ground-truth **string** on both sides, so a lexicon change
can never make an old manifest disagree with itself.

## Why this does not contradict the earlier VLM NO-GO

`benchmarks/vlm-vqa-pilot-2026-07` found Claude tops out at 89.7% on narrow visual
questions about degraded orchestral cells — **counting** noteheads, rests and
accidentals — and correctly called that a NO-GO for a symbol verifier.

This is a different task: **reading printed words in a clean margin**, which is what a
vision model is actually good at. The earlier result is why this one got its own
measurement rather than an assumption.

## Limits

- Accuracy is bounded by **staff detection**. On Beethoven 4 p59 the crop shows a
  `Cor. (Es)` label with no staff tick beside it — the detector missed that staff
  entirely. The reader can only answer about staves that exist.
- That is also a latent signal: **more labels than numbered staves is evidence of a
  missed staff.** Not yet used.
- Environment: the pilot is split into crop-making (host python, needs the OMR stack)
  and reading (needs `anthropic>=0.116` for structured outputs). The repo pins 0.116.0
  but the **host python has 0.28.0** — real drift, since the July upgrade commit only
  reached the container. Any host-side script using the current API surface will fail
  until that is reconciled.
