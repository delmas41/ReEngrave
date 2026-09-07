# Recorded-refusal findings — provenance

`findings-2026-09-07.json` is generated, not written. Regenerate it with:

```bash
export OMR_DIRECTION_TEXT=0        # the OCR rung is nondeterministic; see the probe
python3 -m tools.omr.transcribe \
    library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \
    --pages 1 --out beet5-scan.json
python3 -m tools.omr.transcribe \
    benchmarks/omr-margin-window-truncation-2026-09/out/fixtures-control/brahms-sym1-mvt1.pdf \
    --pages 0 --out brahms-eng.json
python3 benchmarks/omr-pipeline-audit-2026-09/probe/extract_findings.py \
    beet5-scan.json brahms-eng.json > findings-2026-09-07.json
```

Two inputs, and the second is the CONTROL: the same numbers on a clean engraved
page are what make the scan's thin ones mean something.

| | scan (Litolff Beethoven 5 p1) | engraved (brahms-sym1-mvt1 p0) |
|---|--:|--:|
| key-signature majority, gate 0.50 | **0.5294** (+0.0294) | 0.84 (+0.34) |
| thinnest meter margin | **0.0082** (2/4 at 0.5047 over 3/4 at 0.4965) | 0.1325 |
| that winner over `min_score` 0.50 | **+0.0047** | +0.275 |
| mid-staff clef flips | **2** | 1 |
| `propose_clef` `already_in_effect` | 5 of 11 | 14 of 21 |

**The mid-staff flips are the population review found missing**, and all three
across both pages carry `n_resolved == 1` and no `disagrees` key — which is
exactly why `contest.disagrees` cannot report them and why
`clef_in_effect_before` was added. Read them with `read_clef_rung_ran`: `true` is
a staff's OPENING cell replacing the positional default (the pass working, 12
across these pages), `false` is a later cell moving a clef already established.

The sharpest single row is the scan's `staff 11, measure 3: bass -> treble on
one detection at 0.6639`.

⚠️ n = 2 pages. These are demonstrations that the quantities are now readable,
not a distribution. Nothing here is a benchmark result and no arm was run.
