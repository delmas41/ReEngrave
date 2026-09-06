# The truncated margin labels are the PAGE'S doing, not the reader's

**2026-09-06.** `benchmarks/omr-corpus-widening-2026-09/FINDINGS.md` §6 records
margin labels arriving at the lexicon with their opening characters gone —
`'larinetti in B.'`, `'mpani in C-G'`, `'orni in F I II'` — and diagnoses them:

> That is a reader/window fault, not a lexicon one, and the two should not be
> confused: adding `larinetti` as an alias would paper over it.

**Half of that is right and half of it is wrong, and the wrong half is the
actionable half.** It is emphatically not a lexicon fault. It is also not a
reader fault, and not a window fault: **the missing characters are not on the
page.** The engraved benchmark's own fixtures cut their instrument names off,
and every reader in the ladder — text layer, Surya, Tesseract, Claude — is
reading the sheet correctly.

---

## 1. The live baseline: it still reproduces, on main, today

Measured on `7ea27a4b` against the fixtures the eleven-work benchmark last
built. `probe_truncation.py` reads each fixture's first page three ways: what
the production reader returns, what PyMuPDF extracts by default, and what it
extracts once the MediaBox is widened to the left so nothing is clipped away.

```
python3 benchmarks/omr-margin-window-truncation-2026-09/probe_truncation.py \
    --fixtures benchmarks/omr-orchestral-e2e/fixtures
```

**14 truncated margin labels across 5 of the 11 engraved works.**

| work | on the sheet | printed in the source |
|---|---|---|
| `mozart-sym40-mvt1` | `larinetti in B.` | `Clarinetti in B.` |
| `mozart-sym41-mvt1` | `mpani in C–G` | `Timpani in C–G` |
| `tchaikovsky-sym6-mvt2` | `larinetti in A` | `Clarinetti in A` |
| | `orni in F I II` | `Corni in F I II` |
| | `ni in F III IV` | `Corni in F III IV` |
| | `ani in A.D.E.` | `Timpani in A.D.E.` |
| | `Alto e Tenore` | `Tromboni Alto e Tenore` |
| | `mbone Basso` | `Trombone Basso` |
| `mahler-sym5-mvt1` | `rei Klarinetten in A` ×2 | `Drei Klarinetten in A` |
| | `ier Trompeten in B.` ×2 | `Vier Trompeten in B.` |
| `dvorak-sym9-mvt4` | `ss Trombone` | `Bass Trombone` |
| | `rash Cymbal` | `Crash Cymbal` |

And end to end, through `staff_labels.read_staff_labels` on a real
staff-detected page (`--staves`, `tchaikovsky-sym6-mvt2`, 16 staves):

```
  staff  3  'larinetti in A'    -> None           none
  staff  5  'orni in F I II'    -> None           none
  staff  6  'ni in F III IV'    -> None           none
  staff  8  'Alto e Tenore'     -> Tenor          medium   alias='tenore'
  staff  9  'mbone Basso'       -> Bass voice     medium   alias='basso'
  staff 11  'ani in A.D.E.'     -> None           none
```

## 2. ⚠️ Two of them are not dropped — they resolve to a SINGER

The corpus-widening note only ever saw the labels that reached the *unmatched*
log line. **Truncation does not only cost a label; it can substitute a wrong
one, silently, at `medium` confidence.**

| printed | reaches the lexicon as | resolves to | should be |
|---|---|---|---|
| `Tromboni Alto e Tenore` | `Alto e Tenore` | **Tenor** (a voice) | Trombone |
| `Trombone Basso` | `mbone Basso` | **Bass voice** | Trombone |

Two trombone staves of a Tchaikovsky symphony become singers. This is the same
family CLAUDE.md already records twice (`Tr. Alt.` → *Alto*; the roster
regression where "7 staves read as a SINGER"), and it is worse than the
abstentions beside it: a wrong instrument feeds `clef_correction`, the
written-range veto in `_dedupe_cross_staff_detections`, and the part-staff
join, none of which can tell it from a right one.

⚠️ A third staff on the same page reads `'Basso'` → Bass voice at `high`
confidence and is **not** truncated — that is the pre-existing `Basso.`
ambiguity CLAUDE.md's edition-instrumentation section already prices at 35
rows. It is a lexicon question, `tools/omr/instruments.py` was off limits for
this work, and it is recorded here only so a future reader does not attribute
it to truncation.

## 3. The mechanism, proved rather than asserted

**LilyPond right-aligns an instrument name into `left-margin + indent`, and
does not draw what will not fit.** At these fixtures' settings that slot is
10 mm + 15 mm = **70.9 pt**, and every truncated label on the page is exactly
that wide.

Three measurements, each closing off one alternative:

1. **The glyphs are not extractable.** Widening the page's MediaBox 400 pt to
   the left and re-extracting recovers **one** character on some labels and
   none on others (`Corni in F I II` comes back whole; `rni in F III IV` does
   not). So a share of the loss is glyphs drawn past the sheet's left edge,
   which neither the rasterizer nor PyMuPDF returns — and the rest were never
   drawn at all.
2. **The glyphs are not on the paper.** Rendering `mozart-sym40-mvt1`'s
   Clarinetti band inside the page rect shows `larinetti in B.`; rendering the
   same band with the sheet widened shows the `C` sitting at negative x. And
   rendering `tchaikovsky-sym6-mvt2`'s widened brass band shows literally
   `rni in F III IV` with **blank paper to its left** — nothing was drawn.
3. **The slot is the cause.** Re-rendering `tchaikovsky-sym6-mvt2.ly` at
   `indent = 20/25/30/35\mm` walks the truncation back name by name in
   descending order of length, and at **35 mm all sixteen names come through
   whole, still on one page.**

```
--- indent 35mm : 1 page(s)
      x0=   1.00  'Tromboni Alto e Tenore'
      x0=  24.53  'Timpani in A.D.E.'
      x0=  28.78  'Corni in F III IV'
      ...
```

**No reader window is implicated.** `staff_labels.LABEL_RIGHT_MARGIN_PX` is a
RIGHT limit and can only ever drop a span whole; it cannot remove leading
characters. The `staff_labels_surya` crop — the family that genuinely did clip
`Clarinetti` to `arinetti` in 2026-08 and `Pauken in C u.G` to `ken in C u. G`
in 2026-09, and which `TestMarginCropReachesTheLabels` pins — is not implicated
either: it reads the raster, and measurement 2 shows the raster has no ink to
find. **No reader can recover a glyph that was never printed.**

## 4. Scope: this is a FIXTURE fault with no real-world exposure

The control (`probe_edge_separation.py --library`) reads the held score library:
**289 editions, 141 pages carrying margin text on p1–p3.** The smallest left
edge of any margin string in the whole store is **5.00 pt** (Simrock's
*Zauberflöte*), and **zero** spans sit at or past the sheet edge. A real score
is laid out to fit; a scan's text layer is OCR of ink that is by construction
inside the page. So this defect belongs to the benchmark's generated fixtures
and to nothing the project actually reads.

## 5. What was refused

- **Adding `larinetti` / `orni` / `mpani` / `ani` as aliases.** Refused as
  instructed, and now refused on evidence too: they are not names, no engraver
  ever printed them, and an alias for one would fire on the *next* fixture's
  differently-truncated string not at all.
- **Recovering the off-page text in `staff_labels.py`** by extracting with a
  widened clip. Refused for two reasons. It only reaches the smaller half of
  the loss (measurement 1 — the rest was never drawn), and where it does reach,
  it would have the cheapest rung read a name **the page does not print**,
  diverging from every other rung and from the ink the detector sees. On a
  benchmark fixture that is truth leaking into the input.
- **Flagging a truncated label by its left edge.** This looked like the clean
  geometric discriminator and **it does not separate**: over 375 margin spans
  on the eleven fixtures the truncated ones reach **+0.25 pt** and the intact
  ones reach **−5.08 pt** (`Clarino II in C`, whole). They overlap. Recorded
  because it is the obvious next idea.
- **Turning the fixture repair on.** See below — it changes the engraving, and
  that is a decision about what the benchmark IS.

## 6. What shipped

Two changes, neither of which moves a number.

**`tools/omr/training/orchestral_eval.py` — `OMR_EVAL_INDENT_MM`, default
off.** Sets `indent` in the generated LilyPond so the names fit. Unset, the
source is returned unchanged, so a default run is byte-identical.

⚠️ **A PREPENDED `\paper` BLOCK IS SILENTLY IGNORED** — measured. musicxml2ly
emits its own (empty) `\paper { }` after anything the harness puts at the top of
the file, and the later block wins: prepending `indent = 35\mm` rendered a
byte-identical page with every name still cut. The setting is injected into that
block, and a source with no block to inject into raises rather than rendering a
page that looks fine and is not. `test_orchestral_fixture_render.py` pins all
three cases.

**It is off by default because turning it on changes the engraving.** A wider
indent narrows the first system, so note spacing moves and the recognition it
feeds moves with it; the excerpt still fits one page at 35 mm on the worst work,
so the truth window is not at risk, but the pooled figure would move for reasons
unrelated to the pipeline. That is the kind of change `accuracy_record` stamps
and refuses to compare across. **It needs its own measured run and Sean's
decision** — the ready-to-price command is:

```
OMR_EVAL_INDENT_MM=35 python3 -m tools.omr.training.orchestral_eval --omr-ned
```

**`tools/omr/contextual.py` — the unmatched-label report no longer prescribes a
cure.** It used to end *"these are the strings to add to
tools/omr/instruments.py"*, naming one of the two causes as though it were
established. That instruction was followed once and produced a work order that
had to be retracted. It now states both causes and points here.
`test_the_report_does_not_prescribe_a_lexicon_fix` pins it, and was run RED
against the old wording before being accepted.

## 7. Reproducing

```bash
# the diagnosis, and the live baseline
python3 benchmarks/omr-margin-window-truncation-2026-09/probe_truncation.py \
    --fixtures benchmarks/omr-orchestral-e2e/fixtures \
    --out benchmarks/omr-margin-window-truncation-2026-09/truncation.json
# add --staves to run the production reader (costs one staff detect per page)

# the left-edge idea that does not separate, plus the library control
python3 benchmarks/omr-margin-window-truncation-2026-09/probe_edge_separation.py \
    --library --library-root /Users/seanjohnson/Desktop/ReEngrave
```

⚠️ `library/` is machine-local and gitignored, so **from a git worktree the
control silently reports zero pages** — which reads exactly like "no real score
has this fault", the conclusion it is supposed to be evidence for. The probe now
refuses instead of reporting an empty control; pass `--library-root` at the main
checkout.

⚠️ `benchmarks/omr-orchestral-e2e/fixtures/` is a build product, regenerated by
`excerpt()` on every run. The figures above are from the fixtures on disk on
2026-09-06; a rebuild reproduces them because the defect is in the generator,
but the exact character counts are a property of the fonts and the excerpt
length.
