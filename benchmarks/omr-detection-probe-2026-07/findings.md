# Detection-confidence probe — is the orchestral OMR gap a threshold problem? (2026-07-11)

**Question.** The time-signature + clef work on branch
`claude/omr-time-signature-inference-e547f1` kept safely abstaining on dense
orchestral pages because the detector barely *sees* the inputs. Before investing
in per-class threshold tuning, check the cheap hypothesis: are the missed clef /
time-sig detections simply below the confidence threshold (recoverable by
lowering it), or is the detector genuinely blind to them?

**Method.** Re-transcribed two movement *first pages* (meter + clefs printed
prominently after the clef, the best case) at `--conf 0.25` (production) vs
`--conf 0.10`, imgsz 2048, 300 DPI, production weights
(`deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`):
- **Boléro p.1** — printed **3/4** on every staff (24 staves).
- **Mahler 5 p.1** — printed **2/4** (18 staves).

## Results

| | Boléro p.1 | Mahler 5 p.1 |
|---|---|---|
| **Real time-sig digits** (x ≥ 16, i.e. after the clef) @0.25 → @0.10 | 0 → **0** | 0 → **0** |
| edge misreads (x ≈ 0, filtered out) | 0 → 8 | 3 → 31 |
| **Clefs detected** (staves) @0.25 → @0.10 | 11/24 → **11/24** | 4/18 → **10/18** |
| clef classes recovered | none | mostly `clefG` (treble); **no `clefF`/bass** |
| noteheads (false-positive cost) | 372 → **1310** (3.5×) | 5816 → **13699** (2.4×) |

## Conclusion — it's a domain gap, not a threshold problem

1. **Time-sig digits are genuinely invisible.** Lowering to 0.10 recovered
   *zero* real detections on either page — only more left-edge garbage. A 3/4
   printed across 13 staves is detected nowhere. Threshold tuning cannot fix
   this.
2. **Clef detection is only partially threshold-limited.** Mahler recovered
   4 → 10 staves, but the recovered clefs are **mostly treble**; the non-treble
   (bass/alto) clefs — the ones that shift every pitch on a staff — stay missed.
   Boléro didn't improve at all.
3. **Global conf-lowering is a non-starter** — it floods noteheads with false
   positives (2.4–3.5×), which would wreck rhythm/pitch resolution downstream.
   (A *per-class* low threshold for clef/time-sig only would avoid the notehead
   flood, but from (1)–(2) it still wouldn't recover the meters and only
   partially recovers treble clefs.)

**So:** the orchestral gap is a **synthetic→real domain gap** (DSv2 training
doesn't match real engraving), consistent with the July-2026 audit. The
deterministic post-processing layer (this branch's 6 commits) cannot reach it by
seeing more detections. Two real paths forward:

- **Deterministic, no model — clef/key/meter plausibility re-rank + a
  dossier-guided verification layer** that cross-checks OMR against known facts
  about the (canonical) score. Works *because* detection fails.
- **Training-side — ScoreAug / Augraphy domain augmentation** (composite real
  blank IMSLP pages + photometric degradation onto DSv2) to close the domain
  gap for clef, time-sig, and notehead detection at the source. Distinct from
  the proven-dead-end hand-label fine-tuning.

Raw probe JSONs were scratch (not committed); the numbers above are the record.
