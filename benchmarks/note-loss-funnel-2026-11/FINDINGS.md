# Note-loss funnel -- ROADMAP 2.311 (diagnosis, 2026-11-16)

STAGED, main with default flags. Measurement only; no reader changed. Written by the manager from the
measurement agent's report (the agent's own FINDINGS write was refused by the worktree hook); scripts in
this directory, branch `lane-2.311-note-loss-funnel` b44b81ca6.

**Why.** Sean: "Correctly diagnosing the problem is my main concern now." Three stems rounds and three arc
rounds each ended at "the notes handed to the reader"; nobody had measured it against truth.

**Truth.** Sean's hand-labelled Brahms page 0, ONLY the 104 measure cells he swept completely (382 heads).
Limit: 369 of those 382 heads are the detector's own boxes he confirmed, so "never boxed" cannot be measured
from this page. No fully judged Litolff cell exists.

## 1. The count: wrong / right / unread (Brahms p0, product file today)

note 3 / 373 / 9 - note value 4 / 369 / 9 - rest 1 / 15 / 1 - accidental 4 / 31 / 2 - dot 0 / 114 / 5 -
stem (record's direction) 5 / 359 / 16 - beam 22 / 161 / 2 - flag 19 / 32 / 0 - tie 4 / 33 / 8 -
slur 26 / 29 / 9 - clef / key / meter 0 wrong, 11 / 6 / 10 right.

- **On this page the notes are not the loss: 98 of 100 printed notes are written, values right.** The loss is
  in the marks between notes: slurs (26 wrong: 10 a second arc on the same two notes, 15 matching no labelled
  arc -- 5 of 6 crops a real slur with a wrong end), flags/beams (20 notes printed with a flag are written
  beamed, 5 of 5 checked real), ties (8 unread).
- Note wrongs: 1 tremolo slash written as a note; 2 real heads Sean did not box (label gaps). Unread notes,
  first stage: one box for two heads 3, value held 3, refused as not a note 3.
- Who says: Sean's labels for the marks; every ATTACHMENT (stem/beam/flag/dot/accidental to a head) is the
  scorer's own geometry, print-checked and corrected four times. Pitch is not scored (his labels carry none).
  Values are coarse (half / quarter / shorter + dots). Not scorable by place: ledger lines, barlines, words,
  dynamics, braces, tremolo.
- **Paused readers, same page, one gather per arm:** stems ON (25c244dac) stem wrong 5 -> 4, right 359 -> 367,
  unread 16 -> 9. Arcs ON (f0c9e499f) slur wrong 25 -> 18 (double arcs 10 -> 4), tie wrong 3 -> 2, unread
  unchanged. Nothing worse; neither touches the flag-written-beamed notes or the wrong-ended slurs.

## 2. Why a red bar is red (20 random red bars per plate, by crop; Brahms 276 red bars, Litolff 309)

Brahms / Litolff: a whole or bar rest not read 5 / 3; real notes whose value is held in doubt 4 / 4; every
mark written but the values do not add up 2 / 9; a real note refused as not a note 2 / 1; pitch unread after a
mid-bar clef change 1 / 0; a real note never boxed 0 / 1; cannot tell from the crop 6 / 2.
The agent's look, not Sean's. The record-only tally over ALL red bars was withdrawn (matched the crops on only
11 of 20 Brahms bars: it blames rightly refused slivers and neighbouring staves' notes in the cell's padding).

## 3. Noise floor

Same page set, two gathers: identical files (the detector cache makes that part identical by design). A page
gathered ALONE vs inside a larger run differs: Litolff p1-2, 39 pitches and 92 blue marks, mostly two staves.
**22 of the stems lane's 29 gathers ran with Surya not installed** (no `.venv-surya` link in that worktree):
staff names could not be read there -- a likely part of the "gather variation" 2.306 r12 reported.

## 4. Process lessons

- The page we tune and check on most is the page we read best; the hand truth says notes are fine THERE and
  cannot say whether they are fine elsewhere. Red bars (the visible loss) are about rests, held values and sums.
- `lane_report.parse_symbols` reads every beamed chord member as a flagged note (53 of 228 short notes on
  Brahms p0): every flag/beam count in past lane reports inherits it.
- A lane worktree without the OCR link silently reads no staff names; the lane's numbers then measure that.
- Sean's tile answers are biased toward what lanes have since fixed: they guard regressions, they give no rate.

## 5. How to run the count for any lane

`PYTHONPATH=. python3 benchmarks/note-loss-funnel-2026-11/extract.py REC.record.json REC.facts.json` (from the
tree and flags that made the record), then
`PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/judge.py REC.facts.json`.

## 6. Open

12 random written-note tiles (seed 2311, 6 per plate) in `out/print/2.311-written`, with Sean. Smallest extra
labelling with the largest payoff: one Litolff page swept all-ink; then the 8 unswept Brahms p0 cells.

## Sean's answers on the 12 random written-note tiles (2026-11-16)

All 12 are real notes and all 12 carry the value we wrote (dots included; tile 3 was blue and is right; tile 6 a unison).
Who says: Sean. Limit: 12 tiles cannot show a fake rate below about one in five; it agrees with the judged page
(3 wrong / 373 right notes). `answers-2.311-written.json`; DECISIONS 2026-11-16.

## 12 random red bars read by Sean, and two small tests (2026-11-16)

Tiles `out/print/2.311-redbars` (seed 2311002, 6 per plate, pools 309 Litolff / 269 Brahms without page 0), answers
`answers-2.311-redbars.json`, key and scripts on branch `lane-2.311-redbars-tiles` (399c98770): `redbars_tiles.py`,
`farhead.py`, `dotcheck.py` and their results json.

Sean's reading against the record's first cause (our scoring):
- Brahms 7, 10, 11, 12: "two dotted quarters", tied. Record: one or both written a plain quarter READ (7, 10, 12) or
  narrowed (11); the bar sums short. A printed augmentation dot is not in the record.
- Litolff 1, 2: heads up to the 4th ledger line; record refuses a `clipped_fragment`. Litolff 5: note 3 spaces above,
  `duration_narrowed`, counted 8.
- Litolff 3 (quarter + rest): another staff's marks make a second voice. 4 (one half note, tied): `too_narrow`.
  6 (chord + rest): counted 2.25. Brahms 8: `chord_value_undecided`. 9: `flag_ink_unread`.

Test A -- Sean's hypothesis "red because the notes are far from the staff": NOT SUPPORTED as a general cause. Share of
bars red by farthest kept head: Brahms within staff 14.8%, 1-2 ledger lines 16.6%, 3+ 13.6%; Litolff 11.6 / 14.7 /
19.1% (19.3% on real heads only, 140 bars). Busy bars track red (6+ heads 24-31% red, 1-2 heads 7-11%). All 321
`clipped_fragment` refusals sit on a cell's top or bottom edge; 6 random ones are tips of a NEIGHBOUR staff's head,
rightly refused. Cell pad is 4 staff spaces, 6 where there is room (`measure_extractor.PAD_*`). clipped/too_narrow is the
first cause of 40 Litolff and 35 Brahms red bars (13% each). NOT MEASURED: whether a head beyond the pad (tiles 1, 2) is
ever seen whole by its own staff; the records hold no page-wide boxes.

Test B -- manager's hypothesis "a dot is missed because an arc is beside it": REFUTED as worded. The dot is printed and
clear of the arc; on tiles 7, 10, 12 the detector drew NO box on it (unclassified dot-size ink); on 11 the dot was boxed
and `dot_role_ambiguous`. Brahms: 21 of 276 red bars are quarters-only bars short by half-beats (11 of 16 on page 8);
Litolff 11 of 309. 117 decided augmentation dots have no dot written on a head (not checked). Why the detector skips
these dots: not measured. Note: tiles 7, 10, 12 wrote the undotted quarter PLAIN -- a wrong value, not an unread one.

Who says: the 12 readings are Sean's; the counts are ours from one saved gather per plate.

## Every red bar ranked by first cause (2026-11-16)

Branch `lane-2.311-redbar-ranking` (1fe933a53): `redbar-ranking.md` / `.json`, `redbar_classify.py`. All 585 red bars
(Litolff 309, Brahms 276), rows add up, 32 unexplained (5.5%). Against Sean's 12 readings: 11 agree, 1 partial.
The record's reasons are ours; rows resting on arithmetic only are labelled so in the file.

By family (the manager's grouping of the 38 rows):
- a note's value held or wrong because of its beam, flag or stem, or a chord on one stem left undecided: about 180 (31%)
  -- `chord_value_undecided` 48, `beam_discounted_uncertain` 47, `beams_ambiguous` 41, short with beamed values 23, small rows 22.
  Owner `rhythm.py::adjudicate_duration`; this is the stems/beams lane's ground (2.306).
- rests (a stroke read as a rest, a rest refused, shape and place disagree, a whole rest beside notes): about 85 (14%).
- bookkeeping, not reading (all marks given to another staff 28, a rightly refused neighbour mark filed as a gap 21,
  the same boxes written in two voices 20, edge note 5, double head 3): about 77 (13%).
- never boxed by the detector (heads/rests 46, dots 23): about 69 (12%).
- a narrow mark refused as not a note, or refused as barline/word/dynamic ink: 66 (11%).
- dots decided wrongly or held: 20 (3%). Meter may be stale: 14. Pitch not placed: 12. Other small rows.

Correction: the manager told Sean stems were a small part of red bars (from 12 tiles). The ranking says the
beam/stem/chord-value family is the largest.

## Second 12 red bars read by Sean (2026-11-16)

`answers-2.311-redbars-b.json`; DECISIONS same date. Over his 24 bars (our grouping of his readings against the record):
beam / flag / chord value 7; a neighbouring staff's marks counted here, or far notes 5; a printed dot not in the record 4;
a rest not read 4 (two bars are nothing but a whole rest); a Litolff half note read black or refused 3; unknown 1.
The classifier agreed with him on 11 of the first 12 but only about 6 of the second 12: rows "every mark owned by
another staff" and "refused as barline ink" hid two bars that hold only a whole rest. The ranking's family sizes hold
roughly; its bookkeeping rows need the question "what is printed here that the record does not hold" before a count.

## 2.311 small test: are far-above-the-staff notes read at the wrong height? (2026-11-17, STAGED, saved records, no gather)

**Records used:** `library/_shared-records/claim-readout-slices-2306-smp4-{lit,bra}` (2306 frozen-sample gather, Nov 13; Litolff pages 1 2 4 6 8 9 10 11 16,
Brahms 0 4 5 8 12 14 19 25). **Litolff p13 is in no saved record**, so the nine unread ties and Sean's tie pairs could NOT be measured. Scripts:
`ledger_heights.py`, `ledger_ink_count.py`, `ledger_sample40.py`, `ledger_parity_brahms.py`, `ledger_tiles.py`.

**Prior work (5 lines).** 2.56 / 2.44: far heads are counted off their printed ledgers (`gather_far_head_ledger_positions`, `far_head_reader`), decided by
`adjudicators.position.adjudicate_notehead_position`, read by `consequences.restate_pitch`; where the ledger read refuses, `restate_pitch` rounds the
GEOMETRY row (`gather_notehead_positions`: box centre against the staff spacing extended outward). 2.216/2.255: ledger lines name the owner / better ledger reads.
2.248: ink centre of a far head only as a candidate (WRONG as a mover; page-facts: ledger lines only). 2.284: page ledger owns the ink. page-facts: Litolff ledgers sit
~0.27 sp further out than the staff spacing extends. Dropped: `combine_farhead_position`. Rule owning the value: far head placed by ledger lines only.

**Cause (a musician's words).** On Litolff the staff spacing extended upward does not land on the printed ledger lines (they sit about a quarter space further out),
so where we extend the spacing instead of counting the lines the note comes out one step wrong; where we count the lines we are mostly right. The loss is where the
count REFUSES (line count does not fit, no line at the box) and the extrapolation is written. Litolff matter much more than Brahms.

**Numbers (heads the record places outside the staff; geometry = round(box centre), ledger = counted).**
- Litolff above, ledger-read vs round(geometry): 1 line 192/442 differ by one step (43%), 2 lines 103/172, 3+ 88/132; below 1 line 42/189 (22%), 2 lines 19/96.
  Brahms: 3%, 9%, 10% above; ~1% below. Fractional residue of the box centre from the grid: Litolff far above mean 0.27-0.29 (inside the staff 0.15); Brahms 0.16-0.21 (0.11).
- How decided: Litolff far-above 746 by ledger count, 241 by geometry (24%); far-below 286 vs 201 (41% geometry). Brahms above 1000 vs 165 (14%), below 323 vs 152.
- Our own stroke count (not truth): of ledger-decided Litolff above 589/746 agree with the record's count (geometry would agree 474); of the geometry-decided 63/241 and
  29/201 -- most disagree by 2 or more, so that set holds many non-notes / far-off boxes, not only height errors (not separated here).
- Truth, Brahms p0 (Sean's OnLine/InSpace class = position parity; 145 far labelled heads matched): ledger-decided 143, parity wrong 0; geometry-decided 2, both wrong;
  inside staff 1 of 254. No pitch truth exists for Litolff (no labelled page).
- Our eye on the seeded 40-per-plate sheets was NOT completed (time): only the automated count above; do not read it as a rate.

**Does the diagnosis survive?** Partly. Not on Brahms (parity right 143/145). On Litolff the extrapolated height is wrong about half the time when it is used (43-70% of far-above heads
differ by one step from the counted ledger), and it is used for about a quarter of far-above and 40% of far-below heads -- a real cause of unreadable tie pairs (C6 vs D6 is exactly a one-step miss). But
for the notes the ledger reader DOES count, our stroke count agrees ~79%. Who says it is right: the 12 tiles (`out/print/2.311-ledger`, key `out/print/2.311-ledger-key.json`; pitch we read, clef, and the geometry pitch beside it).
**Process lesson:** a fallback that rounds an extrapolation is the same rule-8 fault as "cannot tell becomes an answer"; a count by place (not by rate) per decider was missing.
Limit: tile clef is the staff's first printed clef; heads were filtered to head-shaped boxes over dark ink after the first sheet showed a word and a brace boxed.
