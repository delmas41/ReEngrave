# Where Brahms's 1768 edits actually come from

Brahms carries **1768 of the 2140 pooled edits — 83%** — so the orchestral
OMR-NED headline is essentially a Brahms number. This attributes it, because
"improve the pipeline" and "fix Brahms" were the same sentence and nobody knew
which problem it was.

`benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.*`, 7 bars, 21 parts,
engraved from the Gradus MusicXML so every note is known.

    OMR-NED 0.4486   edits 1768   truth 2083 syms   pred 1858 syms
    parts 21/21   measures 7/7   notes 508/505
    note recall 0.717   precision 0.713   duration 0.865

Unlike Beethoven — recall 1.000, where the errors were all notation — Brahms is
a genuine *recognition* failure. About 28% of its notes are wrong.

## The edit budget, and the op counts behind it

| category | edits | share | ops |
|---|--:|--:|---|
| wrong note | 693 | 39.2% | `notedel` 109, `noteins` 104 |
| entire measure insert/delete | 569 | 32.2% | `insbar` 20, `delbar` 20 |
| wrong direction | 130 | 7.4% | `extrains` 124 |
| wrong dot | 103 | 5.8% | `dotdel` 82, `dotins` 16 |
| wrong flag/beam | 102 | 5.8% | `editbeam` 85, `insbeam` 9, `delbeam` 8 |
| wrong slur | 70 | 4.0% | |
| wrong accidental | 46 | 2.6% | `accidentins` 46 |

`notedel` and `noteins` are near-balanced (109 / 104), which matters: we emit
about the RIGHT NUMBER of notes and get their pitch wrong. This is not a
detection-recall problem.

## Finding 1 — ONE staff produces two thirds of the pitch errors

Aligning each part's pitch sequence against the truth gives 65 replaced notes.
They are not scattered:

| | |
|---|--:|
| replaced notes, whole page | 65 |
| **of those, in part 20 alone** | **42 (65%)** |
| **exactly −4 semitones** | **41 (63%)** |

Part 20 is the **Contrabass**. Truth is 42 × `C3`; we read `A♭2`.

**The staff's five-line window is misaligned by one space.** Its geometry:

    line_ys_page      [9287, 9327, 9368, 9408, 9451]
    line_thickness_px [18.0,  5.0,  5.0,  5.0,  5.0]     <- 18 against 5
    spacing 41.0   span 164   (both normal for this page)

The window is internally consistent, which is why nothing downstream questioned
it — but rendering the page with the detected lines drawn on it shows them
sitting a space ABOVE the printed staff, with the top "line" running over the
bass clef. **That 18 px line is a beam, taken for a staff line.** The comb then
fitted four real lines below it and missed the true bottom line.

Every note therefore resolves one space low: a notehead centred at y 9430 falls
in the A2 space of the shifted window instead of the C3 space of the real one.
The key signature (C minor, three flats) then flattens the A, and `A♭2` is
exactly −4 semitones from `C3`.

**The tell is already in the data.** Line thickness is 4–5 px on 19 of the 21
staves; the two outliers are staff 20 (18 px, ratio 3.6) and staff 8 (20 px,
ratio 4.0). No other staff exceeds 1.8. A staff whose line thickness carries a
large outlier is a candidate misfit, and the check costs nothing — the numbers
are already recorded in `staff_geometry`.

## Finding 2 — the whole-measure charges are the same amplification as Beethoven

40 bar operations cost 569 edits. The pairs look like:

```
insbar cost 13 | ['[G6]4*', '[G5]4Bsr', '[A5]4Bco', '[B5]4Bsp']  Extras:['slur,off=0.0,dur=3.0']
delbar cost 12 | ['[A3]4Bpa', '[G5]4Bsr', '[A5]4Bco', '[B5]4Bsp']
```

Three of the four notes agree. The measure is charged whole because its content
signature differs — one wrong note plus a missing slur. Same trap documented for
Beethoven's fermatas: **a large `entire measure` bucket is amplification, not
severity.** Fixing finding 1 and the slurs should collapse much of this 32%
without anything targeting it directly.

## Finding 3 — 82 augmentation dots we invent

`dotdel` 82 against `dotins` 16: we emit five times more dots than we miss. On
an engraved page that is over-detection, not a reading problem, and it is worth
a separate look — 103 edits for a single symbol class.

## Finding 4 — slurs and directions are simply absent

`extrains` 124 and `wrong slur` 70 are the exporter having nowhere to put them,
the same gap Beethoven showed with dynamics and tempo. Known, unglamorous,
~11% of Brahms.

## FIXED 2026-09-01 — finding 1

`staff_detector` step 3d slides a window back when its FIRST or LAST line is a
thickness outlier, the row one spacing beyond the far end carries a real line,
and the result measures more uniformly. Staff 20 went
`[9287,9327,9368,9408,9451]` / `[18,5,5,5,5]` to
`[9327,9368,9408,9451,9492]` / `[5,5,5,5,5]`, and its notes from `Ab2` to `C3`.
Staff 8 — the fat line in the MIDDLE — is untouched, as intended.

| | before beams | + beam export | **+ this fix** |
|---|--:|--:|--:|
| pooled OMR-NED | 0.3164 | 0.3045 | **0.2716** |
| edits | 2224 | 2140 | **1908** |
| brahms | 0.4664 | 0.4486 | **0.3899** |

**Finding 2 collapsed on its own, as predicted.** `entire measure` fell
705 -> 482 (-223) while `wrong note` moved only -38: most of that 32% bucket
was one misplaced staff being charged by the bar, not 40 broken measures.
That is the amplification this file warned about, confirmed by removing its
cause rather than by arguing about it.

## FIXED 2026-09-01 — finding 3, and it was not what this file said

Finding 3 called it "82 augmentation dots we invent". It is not over-detection
at all — the dots are detected correctly and **counted twice on the way out**.
`_duration_to_lily_xml` summed two sources on a stated assumption that
"transcribe.py only sets ONE source", which stopped being true:
`rhythm._name_for_dots` builds `duration_type` FROM the dot count, so a
single-dotted quarter arrives as BOTH `dotted_quarter` and `dots=1`.

    pred [D6]4**   gt [D6]4*        x82

The count LOOKED like under-dotting — 108 dotted notes against the truth's 126 —
which is exactly why it read as a detection problem. It is neither: one fact,
counted twice. `max` instead of `+`.

An existing test asserted the wrong behaviour (`assert dots == 2  # 1 from
prefix + 1 from arg`), so the bug was locked in. Corrected in place rather than
deleted, with the reason, because the assertion looked deliberate.

    brahms `wrong dot`   103 -> 18
    pooled OMR-NED       0.2716 -> 0.2624      edits 1908 -> 1819
    brahms               0.3899 -> 0.3764

Still open: finding 4 (slurs and directions never exported). `wrong flag/beam` rose 141 -> 163, which is expected
— with the staff placed right, more notes align and their beam differences
become visible rather than being hidden inside whole-measure charges.

## What this changes

The headline was one number and looked like a wall. It is four problems, and
they are very unequally sized:

1. **One misaligned staff** — 42 of 65 pitch errors, with a ready-made detector
   (thickness outlier) already sitting in the JSON. Cheapest by a wide margin.
2. **Whole-measure amplification** — mostly downstream of 1 and 4.
3. **Spurious augmentation dots** — 103 edits, self-contained.
4. **Slurs and directions unexported** — known, bigger, shared with Beethoven.

Nothing here argues for detector retraining, which is where "28% of notes are
wrong" would normally point.
