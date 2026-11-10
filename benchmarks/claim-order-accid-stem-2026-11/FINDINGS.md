# 2.282 — accidentals vs stems/heads: claim order (lane-2.282-claim-order 505c4885e, OMR_CLAIM_ORDER, OFF)

Filed by the manager from the lane report (the hook refused the lane's write).

## Cause and process lesson
- **Cause (STAGED).** Heads already stand before accidentals, and stems, beams and flags only read ink nobody claimed. Where two families both fit a stroke, today's code leaves it contested rather than picking by order.
- **Where the false stems come from.** On the five sharps Sean flagged (3 Brahms, 2 Litolff), the detector drew only a head box, scored 0.25–0.46, and no accidental box. The head claims the sharp's blobs. The sharp's two ~2.9 sp verticals stay unclaimed, so the stem reader takes them.
- **Lesson.** Check that both claimants exist at the places that hurt before testing an order. A claim order can only order claims that exist.

## Step 1: contested pieces
I re-adjudicated the 20261104-night slices on this tree (2.277 ON), and re-gathered nothing. A contested piece here is a stroke that an accidental box covers together with another claimant.

| kind | Brahms p0/4/5/8/14 | Litolff p2/6/11 |
|---|---|---|
| (b) accidental box + head/ledger box | 24 strokes in 17 cells (p0 1, p4 4, p5 4, p8 1, p14 14) | 6 strokes, all p6 |
| (a) accidental box + a vertical left to stems or another family | 9 strokes | 2 strokes (p6) |
| beside, not tested: accidental box + rest ink | 69 strokes (50 contested) | 6 |

**10-crop check (my own look, not evidence).**
- **Kind (b):** 3 of 6 crops are a sharp or natural split between a head box and an accidental box.
- **Kind (a):** of 9 crops, none is a sharp's stem. Six are eighth rests under an accidental box, 2 are real note stems and 1 is a barline. So the boxed (a) cases are false accidental boxes, which today's "longer than an accidental stem" refusal rightly keeps out.
- **Unboxed pool (the dominant population):** kept head boxes with no stem, a kept head just to their right, and score under 0.7 (under 0.6 for Litolff). Brahms sample pages have 26. Litolff, over all 9 pages in the slice, has 39. A look at 12 crops each gave:
  - Brahms: 6 sharps, 1 eighth rest, 1 dynamic letter, 4 real heads.
  - Litolff: about 5–6 of 12 were sharp pieces, rests or fragments.
  - That is roughly 25–30 accidentals written as heads on these pages, an extrapolation from 24 crops and not a count.
- **Sharp-reader test:** I ran `accidental_family.read_type` on head boxes. It finds the Brahms sharps but also reads stem pairs as sharps, and it misses Litolff's merged ones. It is not a safe claimant as it stands.

## Step 2: the two arms
The flag is `OMR_CLAIM_ORDER=heads_first|accidentals_first`, default OFF, and unset gives today's behaviour. The order decides only head/ledger-versus-accidental contests. `accidentals_first` also moves the accidental tier before the head tier and lets a decided accidental claim refuse a head box (`claimed_by:page_claim`). My first build resolved every contest and moved 326 Litolff strokes; I fixed that before measuring.

| arm | Litolff | Brahms |
|---|---|---|
| `accidentals_first` | 5 strokes go to the accidental, 0 heads | 10 strokes go to the accidental; 8 head boxes refused (p19 6, p5 1, p25 1); 8 durations lost, 4 accidental verdicts and 4 stem_values changed |
| `heads_first` | 1 stroke to a head, 1 head's refusal changes barline → too_narrow | 6 strokes (4 ledger, 2 head); no head or verdict change |

In the crops of the Brahms refusals, most look like flats or naturals boxed as heads, which is correct. At least one is a real head under a large accidental box, which is wrong. Litolff's 5 strokes are mixed.

## Fixed checks
All eight are unchanged under both arms and under today's order. None has an accidental box, so there is nothing for an order to act on.
- **Wrong today and under both arms:** the 3 Brahms sharps, the 2 Litolff sharp pieces, and the Litolff eighth rest.
- **Right today and under both arms:** the 2 Brahms seconds, which are real heads. Their problem is the stem ruler, not claim order.

## Three measures
`lane_report` ran `accidentals_first` against OFF on the frozen sample.
1. **File:**
   - **Litolff:** nothing changed.
   - **Brahms:** notes −4; accidentals +1/−3; flags −2; articulations +1/−1; pitches ~1; blue marks +1/−1; words −2; red bars 153→151.
   - **`heads_first`:** not run through `lane_report`; the re-adjudication changed no head or verdict, so no file change is expected.
2. **Judged (Sean's earlier answers):** right→wrong 0 and unwritten→wrong 0 (Litolff 302 tiles, Brahms 256). Thirteen Brahms changed places have no judged tile.
3. **`staged.check`:** TOTAL 229 on this tree; I did not run it against main, so it is not a like-for-like comparison.

The lane report's control line says neither arm reproduces the record, because the tree has moved since 11-04. Both arms were re-run on the same tree, so the ON-versus-OFF comparison stands.

**Fast tier:** 10,061 passed. One failure, because the new flag had no row in `docs/flags-2026-09.md`; I added the row and re-ran `test_flag_triage.py` plus the new test file (11 passed). I did not re-run the whole tier.

## Sean's tiles (2026-11-09, main 5d882f939)
accidentals_first right on 4 and 8 (the same stroke as 3), wrong on 1, 5 and 12, tile 6 mixed; heads_first right only on 7. DONE OFF. Cause carried to 2.285 (HELD until 2.284 lands): an accidental claims its own ink where the detector drew no accidental box.
