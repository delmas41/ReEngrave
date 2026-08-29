# Choosing the cross-staff duplicate threshold

A measure cell is cut 4 staff-spaces above and below its staff so ledger-line
notes are not sliced off. On a keyboard score those bands never meet; on a
conductor's score they overlap, and nothing arbitrated between them — the
detector ran on both cells, found the same ink twice, and both staves kept it.

`transcribe._dedupe_cross_staff_detections` keeps such a glyph on the staff it
is nearest, by distance from its centre to that staff's five-line band.
`_CROSS_STAFF_DUPLICATE_IOU` decides what counts as "the same glyph".

## The sweep

All three orchestral works, single-page excerpts, seeding and the connectivity
grouping fix already in place. `None` = no dedupe.

| iou | brahms notes | matched | F1 | beethoven notes | matched | F1 | mahler notes | matched | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| None | 661 | 221 | 0.443 | 88 | 56 | 0.662 | 54 | 3 | 0.079 |
| 0.25 | 395 | **199** | 0.544 | 80 | 56 | 0.695 | 35 | 3 | **0.105** |
| **0.3** | 400 | 202 | **0.548** | 80 | 56 | **0.695** | 36 | 3 | 0.103 |
| 0.4 | 407 | 202 | 0.543 | 80 | 56 | **0.695** | 37 | 3 | 0.102 |
| 0.5 | 417 | 202 | 0.535 | 82 | 56 | 0.687 | 38 | 3 | 0.100 |

**0.3 chosen.** Best on Brahms, tied-best on Beethoven, within 0.002 of best on
Mahler — and the lowest value that costs no correctly-matched note anywhere.
At 0.25 Brahms loses three matched notes, which is the threshold starting to
merge genuinely distinct neighbouring noteheads rather than duplicates.

## What it does not fix

Brahms still loses 19 matched notes to deduplication at every threshold from
0.3 to 0.6 (221 → 202). That is not a threshold artifact: those notes are being
kept on the *wrong* staff of the overlapping pair, so they no longer align to
the right part. The nearest-band rule mis-assigns a note that sits between two
staves — exactly the ledger-line case the padding exists for.

Deciding that properly needs the ledger lines themselves, or the stem, to say
which staff the note hangs off. Until then the trade is strongly positive: 244
false notes removed against 19 real ones misfiled, F1 0.443 → 0.548.

Note also that the pre-dedupe recall was partly an artifact — a note duplicated
onto two staves had two chances to match, so some of the "lost" recall was never
real.
