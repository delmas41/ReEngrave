# Two stems measured as one run — Sean's diagnosis, priced

**Read [FINDINGS.md](FINDINGS.md).** In one line: Sean is RIGHT about the case
he was shown — the crop confirms two voices fused into one vertical run — and
across 8 pages of 2 publishers the fault reaches **3 runs of 4,225**, costing
at most **13 noteheads of 5,684**. **Nothing under `tools/` changes.**

It also corrects the measurement it was sent to act on: the prior lane's
Breitkopf staff-space figures were computed with a **flat 100 px** instead of
`Q.CELL_STAFF_SPACE`, and recomputing under the wrong unit reproduces them to
the third decimal.

| file | what it is |
|---|---|
| `probe_two_stems_as_one.py` | the re-derivation, the reach and the downstream cost, off the committed records |
| `mutate.py` | 13 arms (12 scored, 1 declared equivalent and held out) |
| `out/{litolff,breitkopf}.json` | every stroke with its claimants, both overshoots, and its own staff space |
| `out/ADJUDICATED.md` | the 17 both-ends runs against the print, 13 of 17 opened |
| `out/strips-*/`, `out/manifest-*.json` | the strips, rendered with the prior lane's `crop_strips.py` |
| `out/mutate.txt` | the battery |

```bash
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
python3 benchmarks/omr-stem-run-split-2026-09/probe_two_stems_as_one.py \
    --record $LIB/_shared-records/beethoven5-p1-p4.record.json \
    --label Litolff --json benchmarks/omr-stem-run-split-2026-09/out/litolff.json
python3 benchmarks/omr-stem-run-split-2026-09/mutate.py
```

No weights, no re-gather, no detector. The probe reads the two committed shared
records; the strips need the PDFs.
