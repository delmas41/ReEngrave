# Re-gather 2026-10-14 (`20261014-night`): all stages, main `8b9eb97c`

`regather_20260930.sh` (TAG=20261014-night THROUGH=infer REF=origin/main) then `compare_20261009.sh` (BASE=20261013-night). Main includes the landed 2.131 (staccatissimo shape, ON) and 2.132/2.133 (flags OFF, so no effect). New records beside the old; not adopted into `manifest.json` / `current.json`.

| | wall | exit |
|---|---|---|
| Litolff p1-16 | 65 min (was 55) | 0 |
| Brahms p0-26 | 230 min (was 201) | 0 |
| compare: readout diff (both) | | 1 (differences, as before) |
| compare: export (both) | | 0 (was 1) -- MusicXML and LilyPond written and compiled |
| compare: acceptance | | 2 (dirty-tree refusal); `--force` exit 0 |
| regather report | | 0 |

Duration-decision control (exit 3) did not fire.

## All stages vs 20261013-night (`all-stages-vs-20261013-night.txt`)
| | Litolff | Brahms |
|---|---|---|
| notes reaching the file | 6,361 -> **6,595** (0.579) | 9,148 -> **10,918** (0.450) |
| bars held out | 861/5,022 -> **699/5,034** | 1,822/5,987 -> **975/6,073** |
| bars marked unread (red) | 1,539 (-13) | 2,315 (-191) |
| blue guessed (total) | 1,527 -> 1,818 | 1,034 -> 3,263 |
| bars add up [control] | 4,521/4,521 | 4,673/4,673 (denominator shrank from 6,060 / 6,988; not investigated) |
| definition-of-done panel (parts, staves named/held out, meter, key, clef) | unchanged | unchanged |

## Biggest movers (the report's own table)
Litolff: articulations no verdict 447 -> 0; articulations boxes 465 -> 18; bars held out 861 -> 699; blue guessed rests 0 -> 56; blue guessed total +291; export not written bar_does_not_add_up 1,973 -> 1,662.
Brahms: articulations no verdict 2,838 -> 0; blue guessed rests 9 -> 675; articulations boxes 4,101 -> 1,263; blue guessed total +2,229; blue guessed notes +1,563; bars held out 1,822 -> 975.

Full reports: `beethoven5-litolff.report.md`, `brahms1-breitkopf.report.md`.
