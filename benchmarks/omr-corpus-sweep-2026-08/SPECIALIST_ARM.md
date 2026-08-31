# The clef specialist, measured on the whole corpus — 2026-08-30

Two arms of the same 220-page sweep, identical sampling, the second with
`OMR_CLEF_WEIGHTS` set. 3359 staves, 0 crashes either way.

```bash
python3 benchmarks/omr-corpus-sweep-2026-08/sweep.py --every 6 --max-per-score 40
OMR_CLEF_WEIGHTS=omr-weights/deepscoresv2-yolov8l-clef-ft-boxfix-2026-07-13.pt \
  python3 benchmarks/omr-corpus-sweep-2026-08/sweep.py --every 6 --max-per-score 40 \
  --out benchmarks/omr-corpus-sweep-2026-08/sweep-specialist.jsonl
```

## Result

"Blind" = the share of staves with no clef read at all, where the positional
default answers *treble* every time.

| score | staves | blind before | blind after | key sigs before | after |
|---|---:|---:|---:|---:|---:|
| beet5 | 261 | 79% | **25%** | 10% | **26%** |
| pastoral | 289 | 45% | **10%** | 36% | **51%** |
| lamer | 371 | 59% | **27%** | 27% | **35%** |
| beet5-imslp | 271 | 35% | **20%** | 22% | 25% |
| mahler5 | 696 | 44% | 42% | 24% | **30%** |
| bolero | 149 | 0% | 0% | 19% | 19% |
| handel-lead | 568 | 14% | 14% | 80% | 80% |
| handel-red | 500 | 0% | 0% | 89% | 89% |
| kirchhoff | 44 | 0% | 0% | 84% | 84% |
| wtc | 210 | 0% | 0% | 96% | 96% |
| **total** | **3359** | **31%** | **19%** | **48%** | **53%** |

**420 of 1043 blind staves rescued. 168 key signatures newly read** — the second
number is downstream of the first, and only exists because the specialist's clef
now reaches the key-signature pass at all (that was one of four wiring defects
fixed the same day; before it, 16 clefs supplied on La Mer p.132 bought zero key
signatures).

## Where it works, and where it does not

Four scores move and six do not, and the split is not random.

* **It moves where the pipeline was blind.** Pastoral 45%→10%, beet5 79%→25%,
  lamer 59%→27%. These are exactly the scores the sweep's first arm identified as
  broken.
* **Mahler barely moves (44%→42%) despite the specialist firing on 27% of its
  staves** — so on Mahler it fires almost entirely where the detector had already
  spoken and stays silent in the gaps. Confirmed at staff level on
  `mahler5-p72`, an Edition Peters page where every staff is blind and the
  specialist reads **none** of them
  (`benchmarks/omr-clef-geometry/ground-truth-mahler5-p72.json`).
* **The already-solved scores do not move at all**, because they have no gaps.

So this is not a general fix for orchestral clefs. It is a fix for prints
resembling what it was trained on — and that set includes Debussy and Beethoven
but not Peters Mahler, so "edition overfit" is too narrow a description. Its
failure mode is **abstention**, which is the safe direction.

## Accuracy, which this table cannot show

The sweep records `clef_source`, i.e. behaviour, not correctness. Accuracy comes
from the hand-read fixtures:

| fixture | population | baseline | specialist |
|---|---|---:|---:|
| `eval_pipeline_clefs.py` | 52 staves, pages where the detector works | 50/52 | 50/52 |
| `eval_blind_page_clefs.py` | 32 staves, pages where nothing reads a clef | **17/32** | **25/32** |

The first set is why this reader looked worthless for months: every page in it is
one where the detector already succeeds, so a gap-filler has nothing to add and
its 96% merely displaces the detector's 97%. The second set was built for this
question and shows the other half — 8/17 → 16/17 on Beethoven 5 p.48, including
both the alto and the tenor trombone.

**A benchmark can select against the thing being tested.** That is the fourth
distinct way this project has been misled by a measurement in one week, and the
reason both fixtures now ship.

## Precedence

The arm above was run with the specialist allowed to overwrite other readers,
which is how it shipped that morning. It is now **gap-fill only** — on WTC it was
taking 90% of staves from a detector reading 100% of their clefs, for a 96%-vs-97%
trade. Gap-fill keeps every number in the table above, since those staves had no
reader to displace, and restores the dossier and slot-continuity contributions on
the 52-staff set. Re-running this arm under gap-fill would change the
`clef_sources` mix and not the blind column.
