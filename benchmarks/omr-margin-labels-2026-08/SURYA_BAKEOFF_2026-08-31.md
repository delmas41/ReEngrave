# Surya 2 vs Claude on the margin — and the crop bug the comparison exposed

**2026-08-31.** `findings.md` adopted the Claude margin reader at about a cent a
system. Surya 2 (datalab-to/surya, Apache-2.0 code, 650M, llama.cpp on Apple
Silicon) is a local OCR VLM, so if it can read a margin the per-page cost of
instrument identity goes to zero. This scores it on the same crops, against the
same free text-layer truth, with the scoring lifted into a shared script so the
two readers are judged by the same code.

```bash
.venv-surya/bin/python benchmarks/omr-margin-labels-2026-08/read_crops_surya.py
python3 benchmarks/omr-margin-labels-2026-08/score_readers.py \
    results.json results-surya.json --detail
```

## Bake-off — the 8 original crops, 76 staves

| reader | agree | disagree | recovered | missed | both silent | accuracy where both resolve | cost | speed |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| `claude-opus-5` | 25 | **0** | 30 | 0 | 21 | 25/25 (100%) | ~1¢/system | ~3 s/system |
| **Surya 2** | 24 | **0** | 23 | 1 | 28 | 24/24 (100%) | **$0** | **1.5 s/system** |

Surya is exactly as accurate as Claude where the text layer can check it — zero
disagreements for both — and resolves 49 staves against Claude's 55. On the
first crop it returned `Fl., Ob., Cl., Fag., Cor., Tr., Tp.`, character for
character what Claude returned.

Getting there needed two things the docs do not lead with: `RecognitionPredictor`
must be called with `full_page=True` (without it Surya finds no regions on a
margin strip and returns nothing at all), and the text comes back as **HTML per
block**, not as plain lines.

## Where Claude wins is not OCR quality

Eight staves separate them. Six are the same failure:

| Surya read | printed | Claude read |
|---|---|---|
| `arinetti in C` | Clarinetti in C | `Clarinetti in C` |
| `ani in C.G` | Timpani in C.G | `Timpani in C.G` |
| `bombe in C` | Trombe in C | `Trombe in C` |
| `Fola` | Viola | `Viola` |
| `concello trabasso` | Violoncello e Contrabasso | `Violoncello e Contrabasso` |
| `II` | Violino II | `Violino II` |

**The crop was cutting the first letters off.** Surya transcribes what is in the
image and the lexicon rejects the fragment; Claude silently repairs it from the
running order. So the gap measured the crop, not the reader — and the damage was
invisible for as long as a model that repairs it was the only reader.

## The width sweep, and the finding that reverses the obvious fix

12 fresh systems from Beethoven 5 and 6 (107 staves), cropped at three widths,
every other thing held constant.

| reader | width | agree | disagree | recovered | missed | both silent | accuracy |
|---|--:|--:|--:|--:|--:|--:|--:|
| Surya | 14 | 32 | 3 | **24** | 1 | 47 | 32/35 (91%) |
| Surya | **20** | **33** | **2** | **16** | 1 | 55 | **33/35 (94%)** |
| Surya | 26 | 33 | 2 | 16 | 1 | 55 | 33/35 (94%) |
| Claude | 14 | 36 | 0 | 19 | 0 | 52 | 36/36 (100%) |
| Claude | **20** | 36 | 0 | 19 | 0 | 52 | 36/36 (100%) |

Widening made `recovered` go **down**, 24 → 16, which looks like a loss and is
the opposite. The narrow crop was provoking **repetition**:

```
beethoven-symphony-5_p40_s0   w14: ['Fag.','Fag.','Fag.','Fag.','Fag.','Fag.','Fag.']
beethoven-symphony-5_p40_s0   w26: ['Fag.']
```

2 of 12 systems, 20 surplus lines, and the row assignment then spread those
copies across staves that carry no label at all. Every one counted as a
"recovery". At width 20 there are **zero** repeated lines.

The half that can be checked moves the right way at the same time: agreement
with the text layer 91% → 94%, disagreements 3 → 2.

**Claude scored identically at both widths** — 36/0/19/0, the same tally twice —
so widening costs the paid reader nothing and is worth three points to the free
one. 20 and 26 measured the same, so 20 is the smaller change that gets the whole
benefit. `staff_labels_vision.MARGIN_SPACINGS` is now **20.0**.

## The methodological problem this turned up

**`recovered` is unverifiable by construction.** It counts staves where the free
ground truth is silent — so a genuine recovery and an invented label are the
same number. That is exactly the failure the vision prompt is written to prevent
("an invented label is worse than none"), and the tally cannot see it.

It bit here: 8 of Surya's 24 w14 "recoveries" were one hallucinated token
stamped across a section. It applies equally to the 30 recoveries in
`findings.md` — nothing in that measurement rules out the same artifact, though
Claude's outputs carry no repeats.

**`disagree` is the number that can be trusted, and `agree/(agree+disagree)` is
the accuracy to quote.** Read `recovered` as an upper bound on yield, never as
correctness, and check `diagnostics.raw_lines` before believing a jump in it.

## Verdict

**Surya 2 is a viable free tier and is worth wiring in as one.** It is as
accurate as Claude on everything the text layer can check, at 89% of the yield,
for nothing, locally, at 1.5 s a system. The natural shape is the one the theory
layer already uses: text layer → Surya → Claude, each falling through to the next
only where the previous abstains, so the paid call is made for the hard tail
rather than the whole page.

Two things stand between here and that, both small and both measured rather than
guessed:

- **Two of the four residual errors are one-character slips** the lexicon
  rejects outright — `Oh.` for `Ob.`, `Fug.` for `Fag.`. A fuzzy match at edit
  distance 1 against the instrument lexicon would take both.
- **The other two are row assignment**, not reading: `Cl. Ob.` landed on one
  staff because two lines fell within the tick tolerance. The tolerance is
  currently half the tick spacing and takes no account of a label's own height.

## What is where

| file | role |
|---|---|
| `read_crops_surya.py` | Surya reader; measures the gutter, maps blocks to staves by tick |
| `score_readers.py` | shared scorer — any reader, same code, same truth |
| `make_crops.py` | now takes `--margin-spacings`, `--corpus`, `--pages` |
| `results-surya.json`, `results-surya-w{14,20,26}.json` | Surya runs, with `raw_lines` kept for exactly the reason above |
| `results-vision-w{14,20}.json` | Claude at both widths, $0.27 total |

Surya runs in `.venv-surya` (Python ≥ 3.10, gitignored) and needs
`brew install llama.cpp`; it auto-spawns the server and pulls the GGUF on first
use.
