# Re-gather 2026-10-10 (`20261010-night`): all stages, main `26fdb4d0`

Both acceptance movements were gathered through INFER: Litolff p1–16 in 46 min, Brahms p0–26 in 161 min, both exit 0. Sean asked for this run on 2026-10-09: *"run the overnight gather in stages so that we can compare to last night and have the first 2 stages comp"*. The manager ran it this once.

⚠️ **Last night's base `20261009-all` is main `00473387`, from the morning of 10-09.** So this diff carries ALL of 10-09's landings, not only this session's:
- **The other session's, 10-09:** 0.9, 2.68 dynamics stack, 2.69 hooks, 2.70/2.73 hollow heads, 2.71 tremolo slash, 2.72 meter (`OMR_METER_TEMPLATE_AT_BAR`), 2.74 beams, 2.76 dynamic-not-a-head.
- **This session's:** 2.61d, 2.12f, 2.78, 2.75, 2.77 + 2.77b.

## A. First two stages vs last night (`*-first-two-stages.txt`, `readout diff`)

**GATHER boxes are identical.** Every glyph family has the same boxes, matched 1:1, with 0 only in one run: 11,399 notes on Litolff and 24,260 on Brahms. GATHER differs only by the readings added since last night: dot stroke ink, dynamic-letter neighbours, a head cut by a line, a head on a letter's ink, and the stem-slash reach.

| | Litolff | Brahms |
|---|---|---|
| notes kept → narrowed | 388 | **1,991** |
| notes narrowed → kept | 89 | 344 |
| notes refused → kept | 107 | 247 |
| notes kept → refused | 118 | 82 |
| durations that changed answer | 2,876 of 11,399 | 8,138 of 24,260 |
| slurs that changed kind | 264 of 1,225 | 899 of 3,148 |
| ties that changed kind | 95 of 1,419 | 340 of 11,666 |
| articulation owners changed | 3 of 18 | 230 of 1,263 |
| words read | 69 → 70 | 334 → 340 |

## B. All stages vs last night's acceptance (`all-stages-vs-20261009-all.txt`)

`current.json` was written with `--force`. The checkout was dirty only with acceptance's own output files and the temporary manifest; no code changed. The figures below are proxies and controls, never objectives.

| | Litolff | Brahms |
|---|---|---|
| notes reaching the file | 5,107 → **5,589** (0.448 → 0.490) | 5,483 → **7,189** (0.226 → 0.296) |
| bars held out (2.8) | 1,323 → 1,064 | 4,180 → **2,755** (0.670 → 0.462) |
| `staff_not_identified` | 137 → 133 | 63 → 64 |
| empty bars padded | 626 → 708 | 424 → 696 |
| tacet bars not padded | 0 → 0 | 527 → 217 |
| **bars add up [control]** | 6,060 / 6,060 | **6,950 of 6,979: 29 OVERFULL** |
| LilyPond errors / warnings | 0 / 48 → 51 | 0 / 725 → 245 |

The comparison against the 2026-09-30 acceptance is in `all-stages-vs-20260930.txt`. The files are kept on this machine only, under `library/_shared-records/overnight-20261010-night/compare/`: MusicXML, LilyPond and the compiled PDF for each movement.

## Seen, not fixed

**⚠️ CONTROL BROKEN: 29 overfull Brahms bars**, in bars 10–14 of 14 parts.
- **What improved:** the meter now reads right where last night's did not. Bar 8 reads `9/8` (last night `9/4`, which carried through the following bars and held them all out), and the return to `6/8` at bar 9 is read.
- **The fault:** in bars 10–14 the parts with nothing to play (Contrabassoon, both Horns, Trumpet, Timpani, and some Oboe, Clarinet and Contrabass bars) get a whole-bar rest sized `9/8` (duration 72) under a written `6/8`.
- **Hypothesis, not traced:** the rest's length comes from a per-staff meter that did not take the bar-9 return, while the `<time>` comes from the system-wide change.
- **Why the hold-out let it through:** it treats a lone whole-bar rest as filling the bar whatever its length.
- **Status:** needs a ROADMAP item; ask Sean.

**Brahms notes kept → narrowed: 1,991.** These are notes whose value is now undecided. The figure is not yet attributed across the 13 items landed since last night. Notes reaching the file still rose, because far fewer bars are held out.
