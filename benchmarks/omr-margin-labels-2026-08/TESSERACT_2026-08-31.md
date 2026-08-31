# Tesseract on the margin — measured, and it beats what I said it would do

**Claim corrected.** In explaining why the margin needs a vision model I said a
conventional OCR engine would struggle with these degraded prints and
domain-specific abbreviations, and flagged it as an expectation rather than a
measurement. Measured, that expectation is **wrong about transcription**:
Tesseract reads this margin well. The gap is real but much narrower than implied,
and it lives somewhere other than where I put it.

```bash
python3 benchmarks/omr-margin-labels-2026-08/eval_tesseract.py
```

## The comparison, deliberately generous to Tesseract

It gets the **same margin pixels** the vision reader gets (same geometry as
`build_margin_crop`), at **native resolution** rather than the 1568 px the API
imposes, **without** the index gutter (an affordance for the vision model, noise
for OCR), across a **sweep** of page-segmentation modes × upscale × binarise, and
scored at its own best setting. Staff assignment is done *for* it: every word is
attached to the nearest staff centre and words on one staff are joined in reading
order, so `Fl.` above `pic.` becomes `Fl. pic.` without Tesseract knowing that.

Scoring is what the pipeline needs — does the text land on the right staff and
resolve through `instruments.lookup` to the right instrument — not string
similarity. Inventing a label on a blank staff is counted separately, because it
is worse than staying quiet.

## Labels

`psm 6` at 2× was best on **both** pages, so this is one fixed configuration, not
a per-page pick.

| page | printed labels | correct | wrong | missed | invented |
|---|---:|---:|---:|---:|---:|
| beet5-p48 | 12 | **11** | 0 | 1 | 0 |
| mahler-p4 | 17 | **15** | 1 | 1 | 0 |
| **total** | **29** | **26 (90%)** | 1 | 2 | **0** |

Against the vision reader's **29/29** on the same two pages.

Tesseract transcribes `Fl. pic.`, `C. Fag.`, `Gr. Tr.`, `A-Klar.`, `Erste Viol.`
correctly — the same domain abbreviations I claimed would defeat it. It also
never invented a label on an unlabelled staff, which is the failure that would
actually be dangerous.

Its three misses are single characters:

| printed | Tesseract | resolves to |
|---|---|---|
| `Tr. Alt.` | `A.` | *nothing* |
| `Kl.Tr.` | `Ki.Tr.` (l→i) | **Trumpet** |
| `Vcelle. get.` | `( Veelle.` (c→e) | *nothing* |

## Downstream, which is the number that matters

90% label accuracy does **not** mean 90% of the value, because a label does not
cost one staff when it is lost — it collapses the pinned block it opens.

| beet5-p48 | parts | clefs |
|---|---:|---:|
| vision | **17/17** | **17/17** |
| tesseract | 14/17 | 14/17 |

`Tr. Alt.` reading as `A.` means the trombone block starts one staff late: slot 9
gets nothing, and slots 10 and 11 both come back Alto Trombone. **One misread
character costs all three trombone clefs** — the alto, tenor and bass readings
that no detector supplies and that this entire layer exists to deliver.

On Mahler p.4 the same shape: **21/21 staves assigned from the vision labels, 15
of 21 from Tesseract's.** The `Ki.Tr.` misread resolves to Trumpet, which
collides with the real `B-Tromp.` staff — and the contradiction guard fired,
dropping both pins rather than pinning a snare drum to a trumpet part. The guard
did its job; the page still lost six staves.

## So where the gap actually is

Not transcription. Tesseract is good at that. The difference is that the vision
reader is doing three things OCR does not:

1. **Reading the margin as a running order.** `Fl. / Ob. / Cl.` above makes a
   smudged fourth entry legible as `Fag.` A per-word OCR pass has no such prior,
   which is why its errors are single characters in isolated abbreviations.
2. **Abstaining deliberately.** The prompt says return null rather than guess, and
   on p.48 it returned exactly five nulls for the five unlabelled string staves.
   Tesseract also abstained correctly here, but by accident of finding no ink
   rather than by judgement — `get.` on Mahler staves 18 and 20 is a divisi
   marking read as a label, harmless only because the lexicon drops it.
3. **Keying to staff numbers itself.** The nearest-centre assignment above is
   mine, not Tesseract's, and it is doing real work.

## What this changes

**Tesseract is a much better free tier than the PDF text layer**, and that is the
actionable finding. On p.48 the text layer gives 0 labels and Tesseract gives 11
of 12, for nothing and offline. The natural architecture is three tiers rather
than two:

1. **PDF text layer** — free, instant, when it covers the system (`_well_covered`).
2. **Tesseract on the margin crop** — free, offline, ~90% of labels.
3. **Vision** — ~1¢ per system, for the last 10%, which is where the trombones are.

Tier 3 is still needed, because the last 10% is not a random 10%: it is the
qualified abbreviations (`Tr. Alt.`, `Kl. Tr.`) that distinguish members of a
section, and those are exactly the staves whose clefs differ from their
neighbours'. But tier 2 is free and would carry most pages most of the way, and
a cheap disagreement test between tiers 2 and 3 would be a better spend than
calling tier 3 on everything.

**Built.** `tools/omr/staff_labels_tesseract.py`, wired into
`contextual._labels_for_page` as the middle tier, on by default
(`ocr_fallback=True`) and additive only — it fills staves the text layer left
unlabelled and never overwrites one it already has, because it is the least
accurate of the three and the one most likely to return a plausible wrong word.

| clef corpus (69 staves) | before | after |
|---|---:|---:|
| **free path** (no credits) | 58/69, base-3 50/52 | **66/69, base-3 52/52** |
| with `--vision-labels` | 69/69 | **69/69** |
| systems sent to the API | 4 pages' worth | **one** |

The free path now reaches on its own what previously needed paying for on three
of the four pages, and the paid tier is called for **a single system in the whole
corpus** — p.48, the page whose trombones OCR mangles. `label_tiers` in the
summary reports which tier answered, so it is never a guess.

One bug this shook out, worth keeping: the tiers were compared by RAW label
count, and on p.48 OCR and vision both return twelve. OCR's ninth is `A.` for
`Tr. Alt.` and resolves to nothing; vision's resolves to the trombones. A raw
count made them tie, the cheaper one won, and three clefs went with it.
`_usable()` compares labels the lexicon can actually turn into a part — the only
count worth comparing readers on.

## Caveats

Two pages, 29 labels, both with reasonably clean margins. `deu` language data is
not installed (only `eng`, `fra`, `osd`), which cannot have helped Mahler —
though the failures there are character-level on abbreviations, which a language
model helps least with. And the staff-assignment harness is a component Tesseract
would need written for it in production; it worked, but it is not free.
