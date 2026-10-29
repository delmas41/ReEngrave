# 2.222 upper limit on a notehead box: measure (STAGED, saved records only, nothing re-run)

Cause and lesson. Wide boxes are junk and tall boxes are not: of the written-as-note boxes over any size cap, those wider
than ~2.4 staff spaces are blobs, ff letters and beams; those merely TALL are mostly real half notes whose box includes the
stem. One cap on "size" would lose notes; the cap is a WIDTH cap. Lesson: split width and height before choosing a cut.
Also: the two "oversized" boxes of Sean's 2.221 tiles 4 and 6 were 0b unions drawn by the census, not detector head boxes
(their head boxes are 1.67x1.41 and 1.76x2.04 sp), so the cap cannot catch them.

## Populations (names = where they came from)
Source: `census.py extract` pickle (branch lane-2.221-m0) of the 2.202f ON-arm saved gathers + exported MusicXML; sizes in own
staff spaces. `python3 benchmarks/notehead-box-cap-2026-10/pops.py` (distributions), `cap.py numbers` (table, numbers.json).
- A: head box with exactly ONE exported note (litolff 3580, brahms 4419; 0 notes unmatched).
- B: head box with 2+ exported notes (159 / 11). B boxes are NORMAL size (w 1.2-2.0, h ~1.3): they are not blobs, no cap affects them.
- C: detector clef / dynamic-letter boxes with centre on the staff (litolff 180 / 95, brahms 208 / 77).
- D: head-class boxes overlapping a clef/dynamic box by >=25% (40 / 43; 12 / 1 of them written). Mostly normal or small boxes: a UPPER cap cannot rule them out.
Own-space sizes of A: width p50 1.47 / 1.40, p99.5 2.09 / 1.73; height p99.5 2.59 / 1.37 (litolff boxes are taller: stems). There is NO empty gap in A; the tail is continuous. C_clef: height p5 1.9 / 3.2, width p50 2.95 / 2.66. C_dyn: width 0.8-5.0, many letters are head sized (p, m, s ~1x1.1).

## Candidate caps (over = rule out). Keep = share of A kept
| cap | litolff keep (lost) | brahms keep (lost) | clef over | dyn over |
|---|---|---|---|---|
| W 2.2 | 99.58% (15) | 99.98% (1) | 161/180, 206/208 | 53/95, 35/77 |
| **W 2.4 (candidate)** | 99.69% (11) | 99.98% (1) | 160/180, 202/208 | 47/95, 26/77 |
| W 2.6 | 99.83% (6) | 99.98% (1) | 157/180, 132/208 | 44/95, 11/77 |
| W 2.6 or H 2.8 | 99.53% (17) | 99.93% (3) | 164, 207 | 60, 15 |
| H 2.8 only | 99.66% (12) | 99.95% (2) | 163, 205 | 59, 6 |
Candidate: width > 2.4 sp is over. Keeps >=99.69% / 99.98% of A; loses 11 + 1 written notes, which are the tiles' question. It rules out
every wide blob / beam / ff seen (4.69, 5.85, 3.88, 3.44, 3.24 sp). It does NOT rule out most dynamic letters (they are head sized) or a tall
narrow clef (F clef written as a note, 1.95 x 3.16, under the width cap). Height alone cannot separate that clef from a stemmed half (4.2 sp):
no height cap is proposed until Sean's tiles 4, 11 say whether tall-narrow boxes are notes.
Controls: blob 4.69x2.60, ff 3.88x1.03, beam 5.85x0.55 land OVER W2.4; the clef 1.95x3.16 lands over H2.8 only; Sean's 2.221 tiles 4/6 boxes land UNDER.
The hand-looked sheet of the 20 largest A (preview.py) is my own eye, not Sean's: 5 wide ones junk, ~7 tall ones look like real halves.

## Caveat (CLAUDE 4)
A cut tuned on two plates (Litolff 1870, Brahms/Breitkopf) may only NARROW (blue / hand to the stacked-pair readers 2.129/2.132) until another
publisher confirms. Never decide a refusal on it.

## Tiles: out/print/2.222-cap/ (12; key.json lists over/under; 6 over W2.4, 4 just under by width, 2 tall-narrow probes)
Sean's answers not yet recorded.
