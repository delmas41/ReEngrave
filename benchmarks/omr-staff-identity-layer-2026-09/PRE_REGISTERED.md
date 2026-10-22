# Pre-registered kill criteria — staff identity layer

Written **before** `probe_heldout_identity.py` was run for the first time.
Committed in the same commit as its first results so the bar cannot move
after the number is known.

## The measurement

Hide the margin labels. Predict each staff's instrument from clef (only where a
reader actually read one), score order and staff position. Score against the
hand-read page truth in `works.json` `staves[]`, which no arm consults.

Fixtures: the 20-row human-verified scan gate,
`<row>.reconciliation.omr.json`, which lives ONLY in the `reconciliation`
worktree. The probe prints the tag and the row count it loaded.

## KC-1 — is the score-order prior a foundation at all?

`HELDOUT` (labels hidden, read clefs kept) must reach **precision ≥ 0.75 at
coverage ≥ 0.60** pooled.

- The bar is the prior 11-row `.graft09` figure for the same signal
  (S5, coverage 0.626 / precision 0.753,
  `benchmarks/omr-staff-identity-2026-09/FINDINGS.md`). It is a REPRODUCTION
  bar, not an improvement bar. ⚠️ The two are different row sets and different
  denominators — a pass means "the signal is what it was said to be", never
  "0.7xx > 0.753".
- **If precision < 0.70**: the page cannot name its own staves from order and
  clef, the layer must be label-gated, and everything downstream of a
  label-free identity is refused. Report and stop.

## KC-2 — does it transfer across publishers?

Reported per publisher, never pooled-only. Breitkopf (Brahms) labels every
staff; Litolff labels winds and brass only; Simrock labels the movement's first
page only.

- **If Breitkopf precision exceeds the worst other publisher's by > 0.20**, the
  rule is reading Breitkopf's engraving conventions and no pooled figure may be
  quoted as the layer's accuracy.
- Two scans of the Litolff plate are ONE engraving. The probe prints staff
  counts per engraving; any claim rests on the engraving count, not the row
  count.

## KC-3 — does a consumer move?

A layer that changes no output is not worth shipping. The consumer is priced in
EDITS on the 20-row gate.

- **If the consumer moves 0 edits**, report the negative and do not ship.
- **If it moves edits in the wrong direction on any row where identity
  abstained**, the abstention is not honest and the layer is refused.
- A small honest number is the expected outcome and is a pass.

## Standing exclusions (asserted, not assumed)

- `staff["instrument"]`, `staff["slot_index"]`, `staff["instrument_source"]`,
  `staff["instrument_family"]` are JOIN OUTPUTS. Read only for arm `SHIPPED`.
- A clef whose `clef_source` is `slot_continuity` or `dossier` is join-derived
  and is not evidence. Only `detector` / `detector_header` / `specialist` /
  `cv_locator` count.
- Dossiers are not read at all — they are generated from the same MusicXML the
  gate scores against.
- A truth name the lexicon cannot resolve is EXCLUDED from the denominator and
  counted, never scored as a miss.
- A system whose staff count differs from the truth lineup ABSTAINS. Pairing a
  suppressed-tacet system to a full lineup by position names the wrong
  instrument.
