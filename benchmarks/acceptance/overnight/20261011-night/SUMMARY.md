# Re-gather 2026-10-11 (`20261011-night`): all stages, main `cb73dde2`

Both acceptance movements were gathered through INFER on a clean checkout of main `cb73dde2`. Litolff p1–16 took 52 min and Brahms p0–26 took 182 min, both exit 0. Sean asked for the run on 2026-10-11 (*"Once that lands, let's go ahead and run the regathers tonight"*), and the manager ran it with `regather_20260930.sh` and `compare_20261009.sh` (TAG=20261011-night, BASE=20261010-night).

**The base is `20261010-night` (main `26fdb4d0`)**, so this diff carries every landing between the two runs, not only this session's:
- **Other sessions:** 2.79 fix; 1.7 D1 scorer; 2.82 beam width; 1.7 stems; q883; crops-bar-drift; 2.84 tenuto; 2.87 stem finder (switch ON); 2.85 repeats and endings; 2.13b printed bar number; 2.83 flag tip; 2.12m.
- **This session:** 2.81 phase 2 (`OMR_BARE_STEM_BAR` ON); 2.80 + 2.80b (a missed rest, not a changed note; a narrow box read as an eighth rest); 2.89 (a chord whose heads disagree is refused, never voted); 2.90 (two voices at one x written as two voices); 2.88 (a hollow half read from its own head).

No attribution to single landings is made here.

## A. First two stages vs last night (`*-first-two-stages.txt`, `readout diff`)

**GATHER boxes are identical.** Every family has the same boxes, matched 1:1: 11,399 notes on Litolff and 24,260 on Brahms. GATHER differs only by the new readings: narrow-box shape (2.80b), cell ink pieces (2.80), stem/cross ink.

Brahms notes at ADJUDICATE: narrowed → kept 762, kept → narrowed 315, kept → refused 49, narrowed → refused 28, refused → kept 2. Litolff is in its own file.

## B. All stages vs last night (`all-stages-vs-20261010-night.txt`)

`current.json` was written with `--force`, as on 10-10. The checkout was dirty only with acceptance's own output files and the temporary manifest; no code changed. The figures below are proxies and controls, never objectives.

| | Litolff | Brahms |
|---|---|---|
| notes reaching the file | 5,589 → **5,782** (0.507) | 7,189 → **8,198** (0.338) |
| bars held out (2.8) | 1,064 / 4,813 → **1,044 / 4,841** | 2,755 / 5,964 → **2,553 / 5,955** |
| **bars add up [control]** | 6,060 / 6,060 | **29 overfull → 0** (6,988 / 6,988; 2.79 landed 10-10) |
| parts named | 12 / 12 | 14 / 14 |
| `staff_not_identified` (notes+rests) | 133 → 133 | 64 → 64 |

## What the held parts are (manager, from the records)

**Staves held out as unidentified:** 7 whole staves, 6 on Litolff and 1 on Brahms. Crops are in `out/print/held-staves-20261011/`.
- **Litolff bottom string staff, 5 staves.** `Q.SLOT_INDEX` is narrowed to {cello, bass} (`family_block_not_forced`), while 15 like it are doubled. One prints "Bassi." → ROADMAP 2.93.
- **Litolff "Ob."** on a worn plate, `not_in_lexicon` → 2.94.
- **Brahms "(C)" horn staff** under a shared bracketed "Hr." → 2.95.

**Held bars:** mostly SHORT, off by one event.
- **Litolff (2/4):** short 678, over 297. By size: −1q 428, −½q 200, +1q 118. 55 bars are exactly 2× the bar.
- **Brahms (6/8):** short 1,544, over 954. By size: +1q 586, −½q 418, −1½q 343, −1q 340.
- Causes are not yet partitioned → ROADMAP 2.96.

The large files are kept on this machine only, under `library/_shared-records/overnight-20261011-night/compare/`: MusicXML, LilyPond and PDF per movement, plus the coloured count pages.
