# Re-gather 2026-10-13 (`20261013-night`): all stages, main `ca46eae4`

Ran `regather_20260930.sh` (TAG=20261013-night THROUGH=infer REF=origin/main) on a clean checkout of main `ca46eae46c630707ae597b9db8a14c9cdb5fba75`, then `compare_20261009.sh` (BASE=20261011-night). Records are NEW files beside the old ones in `library/_shared-records/`; not adopted into `manifest.json` or `current.json`.

| | wall | exit |
|---|---|---|
| Litolff p1-16 | 55 min | 0 |
| Brahms p0-26 | 201 min | 0 |
| compare: readout diff (both) | | 1 (as 20261011-night) |
| compare: export (both) | | **1 (new)** |
| compare: acceptance | | 2 (dirty-tree refusal, as 20261011-night); re-run with `--force` exit 0 |

Duration-decision control (exit 3) did not fire. Base is `20261011-night` (main `cb73dde2`), so the diff carries every landing between the two commits; no attribution to single landings.

## Failure: LilyPond export raises (both movements)
`staged.export` MusicXML was written, but `lilypond.to_lilypond` raised `Unbalanced`: Litolff "14272 noteheads+rests in the log, 8059 written and 6338 accounted as dropped"; Brahms "32389 ... 13818 written and 19021 accounted as dropped" -- the difference went nowhere. No `.ly`/PDF this night (20261011-night had them). Logs: `library/_shared-records/overnight-20261013-night/compare/*-export.log`. Not investigated here.

## Differences vs 20261011-night (numbers from the tools' output)
**All stages** (`all-stages-vs-20261011-night.txt`):

| | Litolff | Brahms |
|---|---|---|
| notes reaching the file | 5,782 -> **6,361** (0.558) | 8,198 -> **9,148** (0.377) |
| bars held out | 1,044/4,841 -> **861/5,022** | 2,553/5,955 -> **1,822/5,987** |
| `staff_not_identified` | 133 -> **0** | 64 -> **0** |
| bars add up [control] | 6,060/6,060, 0 short/over | 6,988/6,988, 0 short/over |
| parts named | 12/12 | 14/14 |
| empty_bars_padded | 680 -> 691 | 705 -> 684 |

**First two stages** (`*-first-two-stages.txt`): GATHER boxes matched 1:1 in both (Litolff 11,399 notes; Brahms 24,260). Litolff note duration: 135 of 11,399 changed answer (87 decided 1-beat -> abstained). Brahms note duration: 988 of 24,260 changed. Rest status: Litolff 120 kept -> refused, Brahms 97 kept -> refused. Dynamics: Litolff 16 new boxes only in this run.

**Words** (`text-words-and-markings.txt`): Litolff words read 70 -> 75, markings 9 -> 11; Brahms words 340 -> 368, markings 90 -> 97.
