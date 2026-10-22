# The page frame — vertical runs read with no crop

The ranked next work of `benchmarks/omr-vertical-runs-2026-09` §3: read the
vertical runs off the WHOLE PAGE so a barline's ends are the ink's and not the
measure cell's, and re-ask Sean's barline test with nothing else moved.

**Read [FINDINGS.md](FINDINGS.md).** The one-line result: in the cell frame the
test fired on **0 of 19** print-settled barlines and **0 of 58** stems below a
1.00-space tolerance; in the page frame it fires on **11-13 of 19** barlines and
**0 of 63** stems between 0.25 and 0.60 spaces. The window was the whole of it.

| file | what it is |
|---|---|
| `page_run_arm.py` | the arm: reach, three controls, Sean's test in both forms, the print join |
| `mutate.py` | 17 arms, two subjects, two judges — 17 RED, 0 survivors |
| `out/litolff.{txt,json}` | Litolff Beethoven 5 pp.1-4 |
| `out/breitkopf.{txt,json}` | Breitkopf Brahms 1 pp.0-3 |
| `out/mutate.txt` | the battery, restore md5-verified |

The reader itself is `tools/omr/vertical_runs_page.py` — **read by nothing**,
deliberately; it writes no record row and changes no file.

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 benchmarks/omr-vertical-runs-page-2026-09/page_run_arm.py --help
```

No weights. `--blind-the-reader` and `--clip-like-a-cell` are the two positive
controls; both must make a table below go to its failing value.
